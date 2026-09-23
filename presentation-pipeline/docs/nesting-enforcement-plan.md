# Nesting enforcement: make invalid node combinations impossible

> **For Cursor:** implement Steps 1–7 in order, then run the checks in "Verify". Every code block is final code, not a sketch. `content_model.py` (Step 1) was prototyped and tested on 2026-09-23 against the real `nodes.yaml`, the Node compiler and all 51 example slides in `src/knowledge/` (zero false positives). Follow `.cursor/rules/00-working-approach.mdc`: surgical changes only, and no unrelated cleanup.

## The bug

The generator produced this inside a table (planner hint: "use platform logos as row icons"):

```xml
<Td backgroundColor="$surface" color="$textMain" fontSize="14">
  <HStack gap="8" alignItems="center">
    <Icon name="store" size="22" color="C62828" />
    <Text fontSize="14" color="$textMain">ZAROMA</Text>
  </HStack>
</Td>
```

`<Td>` holds text + inline tags only. What POM v10.3.0 does with this (verified):
- `HStack`/`Icon` inside `Td`: **the whole table fails** with `<Table>: Missing required attribute "rows"`. That error is misleading, so the repairer fixes the wrong thing.
- `Icon`/`Shape` inside `Li`: **silently stripped**. No error; the icon just vanishes.

## Root cause (three gaps that line up)

| # | Where | Gap |
|---|---|---|
| 1 | `src/prompts/slide_component_planner/system.j2:125` | Tells the planner the generator can add icons "using nested VStack/HStack" for any component. So it writes icon hints for tables and lists. |
| 2 | `src/prompts/generator/system.j2:250` | The "add icons beside labels" recipe (`HStack`+`Icon`+`Text`) has no context condition, so it gets pasted into `<Td>`. |
| 3 | `src/agents/validator.py`, `src/compiler/layout_audit.py` | `nodes.yaml` already defines `children:` for every node, but nothing enforces it. The only check (`_check_li_children`) covers `Li` alone, is a hardcoded copy of the rule, and runs **after** compile. So the compiler's misleading error reaches the repairer first. |

## The design

One source of truth, one enforcer, used at every stage:

```
nodes.yaml `children:`  ──►  content_model.py
                               ├─ flatten_text_containers()  → normalizer   (safe auto-fix, no LLM call)
                               ├─ find_violations()          → validator    (BLOCKING, before parseXml)
                               └─ INVALID_CHILD message      → repair_guidance (correct fix instruction)
prompts (planner + generator + user.j2)  → never ask for layout inside Td/Li/Text
tests  → every restricted parent covered; knowledge-base examples must stay clean
```

Defense in depth: prompts make it **rare**, the normalizer makes the common case **free**, and the validator makes it **impossible to reach the compiler**.

Default for icons in tables (the user can change this in Step 6): keep the table and drop the icons; express the intent with color/bold. Only switch to HStack rows when the icons are central to the message.

---

## Step 1: New file `src/compiler/content_model.py`

```python
"""POM content model — which children each node may contain.

Single source of truth: the `children` field of every node in
knowledge/core/nodes.yaml. Used by the validator (blocking check that runs
BEFORE parseXml) and by the normalizer (safe flattening of text-only
containers). Never hardcode parent/child rules anywhere else.
"""

from __future__ import annotations

import functools
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

_NODES_YAML = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "nodes.yaml"
_SECTIONS = ("structural", "layout", "content", "phase_b", "phase_c", "phase_d", "post_mvp")

INLINE_TAGS: frozenset[str] = frozenset({"B", "I", "A", "U", "S", "Sub", "Sup", "Span", "Mark"})
# Containers whose body is text + inline tags only. POM either fails (Td) or
# silently strips (Li) any layout/leaf node placed inside them.
TEXT_ONLY: frozenset[str] = frozenset({"Text", "Li", "Td"})
# Nodes that may be dropped/unwrapped when flattening a text-only container.
# Anything else (Chart, Table, ...) is left for the blocking check + repair.
_FLATTEN_SAFE: frozenset[str] = frozenset({"HStack", "VStack", "Text", "Icon", "Shape"}) | INLINE_TAGS

_ANY = None  # sentinel: parent accepts any node


@functools.lru_cache(maxsize=1)
def content_model() -> dict[str, frozenset[str] | None]:
    """node -> allowed child tags (None = any node allowed)."""
    data = yaml.safe_load(_NODES_YAML.read_text(encoding="utf-8")) or {}
    model: dict[str, frozenset[str] | None] = {}
    for section in _SECTIONS:
        for name, meta in (data.get(section) or {}).items():
            if not isinstance(meta, dict):
                continue
            raw = meta.get("children")
            if raw is None or raw == "none":
                model[name] = frozenset()
            elif isinstance(raw, list):
                model[name] = frozenset(raw)
            elif isinstance(raw, str) and "any" in raw.lower():
                model[name] = _ANY
            elif isinstance(raw, str) and "svg" in raw.lower():
                model[name] = frozenset({"svg"})
    # Inline tags may nest other inline tags (e.g. <B><Span>..</Span></B>).
    for name in data.get("inline") or {}:
        model[name] = INLINE_TAGS
    return model


def _message(parent: str, child: str, allowed: frozenset[str]) -> str:
    if parent in TEXT_ONLY:
        alt = {"Td": "build the rows as <HStack> (Icon + Text + value) inside a VStack instead of a <Table>",
               "Li": "use <HStack> rows (Icon + Text) inside a VStack instead of <Ul>/<Ol>",
               "Text": "split into sibling nodes inside an <HStack>/<VStack>"}[parent]
        return (f"<{child}> is not allowed inside <{parent}>. <{parent}> holds text + inline tags only "
                f"({', '.join(sorted(INLINE_TAGS))}). Put plain text there; to show icons/layout, {alt}.")
    kids = ", ".join(sorted(allowed)) if allowed else "none (leaf node)"
    return f"<{child}> is not allowed inside <{parent}>. Allowed children of <{parent}>: {kids}."


def find_violations(xml: str) -> list[dict[str, Any]]:
    """Every parent/child pair that breaks nodes.yaml. One issue per distinct pair.

    Returns normalizer-style issues: {code, message, auto_fixed, parent, child}.
    XML that does not parse returns [] — parse errors are reported elsewhere.
    """
    try:
        root = ET.fromstring(f"<_root_>{xml}</_root_>")
    except ET.ParseError:
        return []
    model = content_model()
    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _walk(elem: ET.Element) -> None:
        if elem.tag == "Svg":  # raw <svg> subtree is not POM
            return
        allowed = model.get(elem.tag, _ANY)  # unknown tags: UNKNOWN_TAG check owns them
        for child in elem:
            if allowed is not _ANY and child.tag not in allowed and (elem.tag, child.tag) not in seen:
                seen.add((elem.tag, child.tag))
                issues.append({
                    "code": "INVALID_CHILD",
                    "message": _message(elem.tag, child.tag, allowed),
                    "auto_fixed": False,
                    "parent": elem.tag,
                    "child": child.tag,
                })
            _walk(child)

    for top in root:
        _walk(top)
    return issues


_TEXT_CONTAINER_RE = re.compile(r"(<(Td|Li)\b[^>]*>)(.*?)(</\2>)", re.DOTALL)
_INNER_TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9]*)\b")


def flatten_text_containers(xml: str) -> tuple[str, int]:
    """Collapse <Td>/<Li> bodies that contain layout/leaf nodes into plain text.

    Only rewrites when every nested tag is in _FLATTEN_SAFE (e.g. HStack of
    Icon + Text — the icon is dropped, the label kept). Returns (xml, count).
    """
    count = 0

    def _fix(m: re.Match) -> str:
        nonlocal count
        open_tag, _, inner, close_tag = m.groups()
        tags = set(_INNER_TAG_RE.findall(inner))
        if tags <= INLINE_TAGS or not tags <= _FLATTEN_SAFE:
            return m.group(0)
        try:
            frag = ET.fromstring(f"<_f_>{inner}</_f_>")
        except ET.ParseError:
            return m.group(0)
        text = " ".join(" ".join(frag.itertext()).split())
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        count += 1
        return f"{open_tag}{text}{close_tag}"

    return _TEXT_CONTAINER_RE.sub(_fix, xml), count
```

Notes:
- Inline tags may nest inline tags (`<B><Span>`), so `nodes.yaml` doesn't need a `children:` for them.
- A tag that isn't in the model is skipped here. The existing `UNKNOWN_TAG` check owns unknown tags.
- `flatten_text_containers` only rewrites when **every** nested tag is in `_FLATTEN_SAFE`. A `<Td><Chart/></Td>` is left alone, so the blocking check and repair handle it.
- Regex (not an ElementTree round-trip) keeps the rest of the XML byte-identical. `deck_nodes.py:75` reads the `<!-- archetype: X -->` comment, and ElementTree would drop it.

## Step 2: `src/compiler/normalizer.py`: auto-flatten the safe case

Add the import after `from typing import Any`:

```python
from src.compiler.content_model import flatten_text_containers
```

In `normalize_xml()`, insert this directly **after** the `for m in _ZERO_DIM_RE.finditer(xml):` loop and **before** the `# ---- font-floor` comment:

```python
    xml, flattened = flatten_text_containers(xml)
    if flattened:
        issues.append({
            "code": "TEXT_CONTAINER_FLATTENED",
            "message": (
                f"Flattened {flattened} <Td>/<Li> that contained layout nodes (e.g. HStack + Icon) "
                "to plain text — Td/Li hold text + inline tags only."
            ),
            "auto_fixed": True,
        })
```

## Step 3: `src/agents/validator.py`: block before parseXml

Add the import next to the other compiler imports:

```python
from src.compiler.content_model import find_violations
```

In `validator_node()`, insert this **after** the `if norm["issues"]:` logging block and **before** `val_result = validate_xml(cleaned, output_dir)`:

```python
    nesting = find_violations(cleaned)
    if nesting:
        logger.info(f"validator: {len(nesting)} nesting violation(s) — blocking before parseXml")
        for i in nesting:
            logger.info(f"  ! INVALID_CHILD: <{i['parent']}> > <{i['child']}>")
        norm = {**norm, "issues": norm["issues"] + nesting, "blocking": True}
        diags = [{"type": i["code"], "message": i["message"]} for i in nesting]
        return {
            "normalize_result": norm,
            "validate_result": {"ok": False, "diagnostics": diags, "warnings": []},
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": diags, "warnings": [], "retryable": True,
            },
            "layout_issues": [],
        }
```

Also add a line to the module docstring's pipeline list, between steps 1 and 2:
`  1b. find_violations() — nodes.yaml content model; blocks before parseXml`

Why before parseXml: for these errors the compiler is either wrong (`Missing required attribute "rows"`) or silent (Li). Our message is the accurate one, and the violations are copied into `normalize_result.issues` so the repairer reads them as `pre_issues`.

## Step 4: `src/compiler/repair_guidance.py`: correct fix instruction and stall signature

In `build_error_guidance()`, in the `for issue in pre_issues:` loop, add a branch after the `elif code == "ZERO_DIM":` branch:

```python
        elif code == "INVALID_CHILD":
            key = f"invalid_child_{issue.get('parent')}_{issue.get('child')}"
            if key not in seen:
                seen.add(key)
                sections.append(f"NESTING FIX: {message}")
```

In `error_signatures()`, in the `for issue in pre_issues:` loop, add this before the final `else:`:

```python
        elif code == "INVALID_CHILD":
            sigs.add(f"INVALID_CHILD:{issue.get('parent')}>{issue.get('child')}")
```

## Step 5: `src/compiler/layout_audit.py`: remove the duplicate Li rule

The content model now covers `Li` (and every other node), before compile.
- Delete the constant `_LI_VALID_CHILDREN`.
- Delete the function `_check_li_children`.
- Delete the call `_check_li_children(root, issues)` in `audit_layout()`.

Then:
- `tests/unit/test_layout_audit.py`: delete the two Li tests (the one asserting `LI_INVALID_CHILD` and `test_li_inline_children_ok`). Their cases move to Step 7.
- `tests/unit/test_layout_audit.py`: `test_font_at_minimum_ok` already fails before this change. Leave it; it's not part of this work.
- `scripts/verify_li_nesting.py`:
  - Replace the import `from src.compiler.layout_audit import audit_layout  # noqa: E402` with `from src.compiler.content_model import find_violations  # noqa: E402`.
  - Docstring line 1: `"""Verify that the content model (INVALID_CHILD) catches silently-stripped block elements.`
  - Docstring line 5: `and present in the good case. Also confirms find_violations catches the bad one.`
  - Replace everything from `        # --- Check 3: Audit catches bad, passes good ---` up to (not including) the final `print()` / `RESULT:` block with the code below. The new check reports one issue per distinct parent/child pair (3 Icons in Li → 1 issue) and has no `severity` field, so the old CHECK 3 and 4 assertions no longer apply:

```python
        # --- Check 3: content model catches bad, passes good ---
        print()
        print("=" * 60)
        print("CHECK 3: content_model INVALID_CHILD detection")
        print("-" * 60)
        bad_li = [i for i in find_violations(BAD_XML) if i["code"] == "INVALID_CHILD"]
        good_li = [i for i in find_violations(GOOD_XML) if i["code"] == "INVALID_CHILD"]
        print(f"  bad  INVALID_CHILD issues: {len(bad_li)}")
        for i in bad_li:
            print(f"    {i['message']}")
        print(f"  good INVALID_CHILD issues: {len(good_li)}")
        # One issue per distinct parent/child pair: 3 Icons in Li -> 1 (Li, Icon) issue.
        if [(i["parent"], i["child"]) for i in bad_li] == [("Li", "Icon")] and not good_li:
            print("  PASS — Icon-in-Li caught, clean on good pattern")
            passed += 1
        else:
            print(f"  FAIL — expected [(Li, Icon)] / [], got {[(i['parent'], i['child']) for i in bad_li]} / {len(good_li)}")
            failed += 1

        # --- Check 4: Bad issues are blocking (validator stops before parseXml) ---
        print()
        print("=" * 60)
        print("CHECK 4: Issues are blocking (feed the repair loop, never reach compile)")
        print("-" * 60)
        all_blocking = all(i["auto_fixed"] is False for i in bad_li)
        print(f"  all blocking: {all_blocking}")
        if all_blocking and bad_li:
            print("  PASS — validator blocks before parseXml and routes to repair")
            passed += 1
        else:
            print("  FAIL")
            failed += 1

```

## Step 6: Prompts: stop asking for it at the source

### 6a. `src/prompts/generator/system.j2`

Insert this section **directly before** `## VISUAL-INTENT TRANSLATION` (leave the translation table itself unchanged):

```markdown
## NESTING
<Text>, <Td>, <Li>: text + inline tags only, never HStack/Icon/Shape/Chart. Visual-intent never overrides this (icons in Table/Ul → use color/bold).

```

⚠️ **Keep it exactly this short.** `tests/unit/test_context_builder.py` enforces prompt token budgets (8000/9000/12000), and the current prompt has almost no headroom. A longer version was tested and pushed `test_prompt_standard_components` over the limit (9005 < 9000 failed). This two-line version passes all budgets. Don't raise the budgets to fit extra wording. The full rules already reach the model through `NODE HIERARCHY` (built from `nodes.yaml`), the `user.j2` nesting line (6c), and the validator's `NESTING FIX` message on repair.

### 6b. `src/prompts/slide_component_planner/system.j2`

Replace the sentence at line ~125:

> The generator CAN enrich individual components with decorative elements (Icon, Shape, sparkline Chart) using nested VStack/HStack. Express this as a design_hint — describe the visual intent, not the POM structure.

with:

> The generator CAN enrich layout-based components (kpi_row tiles, cards, narrative blocks) with decorative elements (Icon, Shape, sparkline Chart). It CANNOT put anything but text inside a `table` cell or a `bullet_list` item. Express enrichment as a design_hint — describe the visual intent, not the POM structure.

Under `### What design_hint must NOT do:`, add a bullet:

```markdown
- Ask for icons, logos, shapes, charts or layout inside a `table` or `bullet_list` component — cells and list items hold text only. For these, express emphasis with color, bold or highlight.
```

### 6c. `src/prompts/generator/user.j2`: guard at the seam where the hint meets the component

Replace:

```jinja
{% if comp.design_hint %}  visual-intent: {{ comp.design_hint }}
{% endif %}
```

with:

```jinja
{% if comp.design_hint %}  visual-intent: {{ comp.design_hint }}
{% if comp.kind in ("table", "bullet_list") %}  nesting: cells/items hold text + inline tags only — apply this intent with color/bold/Mark, never Icon/HStack inside <Td>/<Li> (see NESTING RULES)
{% endif %}
{% endif %}
```

(Confirm `comp.kind` is the attribute name used in the template's loop. It is on the line above: `{{ comp.kind }}`.)

## Step 7: Tests: new file `tests/unit/test_content_model.py`

```python
"""Content model: nodes.yaml `children` is the only authority on nesting."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest

from src.agents.validator import validator_node
from src.compiler.content_model import (
    TEXT_ONLY, content_model, find_violations, flatten_text_containers,
)
from src.compiler.normalizer import normalize_xml
from src.state import initial_state

_ROOT = Path(__file__).resolve().parents[2]


def _slide(body: str) -> str:
    return f'<Slide><VStack w="1280" h="720" padding="36">{body}</VStack></Slide>'


# The exact regression from 2026-09-23 (platform ROAS table with logo icons).
TD_HSTACK = _slide(
    '<Table defaultRowHeight="54"><Col /><Col />'
    '<Tr><Td bold="true">PLATFORM</Td><Td bold="true">ROAS</Td></Tr>'
    '<Tr><Td><HStack gap="8" alignItems="center"><Icon name="store" size="22" color="C62828" />'
    '<Text fontSize="14" color="$textMain">ZAROMA</Text></HStack></Td><Td>0.32x</Td></Tr>'
    '</Table>'
)


def test_model_comes_from_nodes_yaml():
    m = content_model()
    assert m["Tr"] == {"Td"}
    assert m["Table"] == {"Col", "Tr"}
    assert m["Icon"] == frozenset()
    assert m["VStack"] is None  # any child
    for parent in TEXT_ONLY:
        assert "HStack" not in m[parent] and "Icon" not in m[parent]


@pytest.mark.parametrize("body,parent,child", [
    ('<Table><Tr><Td><HStack><Text>x</Text></HStack></Td></Tr></Table>', "Td", "HStack"),
    ('<Table><Tr><Td><Icon name="zap" /></Td></Tr></Table>', "Td", "Icon"),
    ('<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>', "Td", "Chart"),
    ('<Ul><Li><Icon name="zap" /> Fast</Li></Ul>', "Li", "Icon"),
    ('<Ul><Li><VStack><Text>x</Text></VStack></Li></Ul>', "Li", "VStack"),
    ('<Text>a<Icon name="zap" /></Text>', "Text", "Icon"),
    ('<Shape shapeType="rect"><Text>x</Text></Shape>', "Shape", "Text"),
    ('<Table><Td>x</Td></Table>', "Table", "Td"),
    ('<Ul><Text>x</Text></Ul>', "Ul", "Text"),
])
def test_invalid_child_detected(body, parent, child):
    issues = find_violations(_slide(body))
    assert [(i["parent"], i["child"]) for i in issues] == [(parent, child)]
    assert issues[0]["code"] == "INVALID_CHILD"
    assert issues[0]["auto_fixed"] is False


@pytest.mark.parametrize("body", [
    '<Table><Col /><Tr><Td>Plain <B>bold</B> <Span color="$accent">x</Span></Td></Tr></Table>',
    '<Ul><Li>Item <Mark>hot</Mark></Li></Ul>',
    '<Text>$84<B><Span fontSize="20">M</Span></B></Text>',
    '<HStack gap="8"><Icon name="zap" size="20" /><Text>label</Text></HStack>',
    '<Svg w="40" h="40"><svg viewBox="0 0 10 10"><rect width="10" height="10" /></svg></Svg>',
])
def test_valid_nesting_passes(body):
    assert find_violations(_slide(body)) == []


def test_knowledge_examples_have_no_violations():
    """Guards against false positives: every example slide we teach must pass."""
    for path in (_ROOT / "src" / "knowledge").rglob("*.yaml"):
        for slide in re.findall(r"<Slide>.*?</Slide>", path.read_text(encoding="utf-8"), re.DOTALL):
            try:
                ET.fromstring(f"<r>{slide}</r>")
            except ET.ParseError:
                continue  # template fragments with placeholders
            assert find_violations(slide) == [], f"{path.name}: {find_violations(slide)}"


def test_flatten_fixes_regression_case():
    fixed, n = flatten_text_containers(TD_HSTACK)
    assert n == 1
    assert "<Td>ZAROMA</Td>" in fixed
    assert "<Icon" not in fixed
    assert find_violations(fixed) == []


def test_flatten_escapes_and_handles_li():
    fixed, n = flatten_text_containers('<Ul><Li><Icon name="zap" /> Fast &amp; safe</Li></Ul>')
    assert n == 1 and "<Li>Fast &amp; safe</Li>" in fixed


def test_flatten_leaves_inline_only_and_unsafe_alone():
    inline = '<Table><Tr><Td>Plain <B>bold</B></Td></Tr></Table>'
    unsafe = '<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>'
    assert flatten_text_containers(inline) == (inline, 0)
    assert flatten_text_containers(unsafe) == (unsafe, 0)


def test_normalizer_auto_flattens():
    result = normalize_xml(TD_HSTACK)
    assert "TEXT_CONTAINER_FLATTENED" in {i["code"] for i in result["issues"]}
    assert find_violations(result["cleaned_xml"]) == []


@patch("src.agents.validator.compile_xml")
@patch("src.agents.validator.validate_xml")
def test_validator_blocks_before_parsexml(mock_validate, mock_compile):
    state = initial_state(run_id="nest1", raw_request="test")
    state["current_xml"] = _slide(
        '<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>'
    )
    result = validator_node(state)
    mock_validate.assert_not_called()
    mock_compile.assert_not_called()
    assert result["compile_result"]["ok"] is False
    assert result["compile_result"]["retryable"] is True
    assert result["compile_result"]["diagnostics"][0]["type"] == "INVALID_CHILD"
    assert any(i["code"] == "INVALID_CHILD" for i in result["normalize_result"]["issues"])
```

Also add a repair-guidance test to `tests/unit/test_repairer.py` (or wherever `build_error_guidance` is tested):

```python
def test_invalid_child_guidance_and_signature():
    from src.compiler.repair_guidance import build_error_guidance, error_signatures
    issue = {"code": "INVALID_CHILD", "message": "<HStack> is not allowed inside <Td>. ...",
             "auto_fixed": False, "parent": "Td", "child": "HStack"}
    assert "NESTING FIX" in build_error_guidance([issue], [])
    assert "INVALID_CHILD:Td>HStack" in error_signatures([issue], [])
```

---

## Verify (definition of done)

**Tested result on 2026-09-23.** This whole plan was applied to a copy of the repo at commit `1fc3044` and checked:
- `test_content_model.py`: all 21 tests pass; the new repairer test passes.
- Full unit suite: 271 passed, 8 failed. **The same 8 failed before the change** (`test_evaluator` cost tests ×6, `test_critic_medium_only_passes`, `test_font_at_minimum_ok`), so there are zero new failures. `test_api.py`, `test_deck_nodes.py` and `test_graph.py` don't load because `lxml` isn't in `.venv`. That's also pre-existing (`uv pip install lxml` fixes it).
- `python -m scripts.verify_li_nesting`: 4/4.
- `validator_node` on the original bug slide: `TEXT_CONTAINER_FLATTENED`, then **compiles OK**. The `<!-- archetype: C -->` comment is preserved.

Commands:

```bash
pytest tests/unit -q --ignore=tests/unit/test_api.py --ignore=tests/unit/test_deck_nodes.py --ignore=tests/unit/test_graph.py
```
Expect exactly the 8 pre-existing failures listed above and nothing else.

```bash
python -m scripts.verify_li_nesting
```
Expect `RESULT: 4/4 checks passed`.

End-to-end (needs `OPENAI_API_KEY`): generate a data slide with a table plus a hint like "use platform logos as row icons". Expected: either no `HStack`/`Icon` inside `<Td>` at all (prompt fix), or a log line `TEXT_CONTAINER_FLATTENED` and a clean compile. Never `Missing required attribute "rows"`.

Checklist:
- [ ] No parent/child rule is hardcoded outside `nodes.yaml` (grep: `_LI_VALID_CHILDREN` must return nothing).
- [ ] `find_violations` runs before `validate_xml` in `validator_node`.
- [ ] Prompts: the generator has the 2-line `## NESTING` section; the planner doesn't ask for icons in tables or lists; `user.j2` adds the nesting line for `table`/`bullet_list`.
- [ ] Adding a new node later needs only a `children:` entry in `nodes.yaml` plus a test case. No code change.
