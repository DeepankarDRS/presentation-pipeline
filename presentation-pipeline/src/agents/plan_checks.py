"""Code checks on one slide plan (§14.6 step 0; checks C14-C17 of docs/plan-reviewer-loop.md).

The renderer draws exactly what a plan holds, so a plan that is empty, thin, repeats itself or
carries planner instructions shows up on the slide. Two kinds of check:

* **problems** (`find_problems`) - a re-ask is justified: an empty component (`PLAN_EMPTY`) or
  text that is an instruction to the presenter, not slide content (`PLAN_INSTRUCTION_TEXT`).
* **fixes** (`finalize_plan`) - code repairs what is left: drops an empty caption and any
  instruction text still there, drops a duplicate component (`PLAN_DUPLICATE_ITEMS`) and a card
  body that repeats its title, and flags a thin slide (`SLIDE_SPARSE`, report only).

Every flag lands in `SlidePlan.plan_flags` as {code, component_id?, detail}; each fix also
writes a plain-words note into `capacity_fixes`, like the other plan checks. Thresholds are an
estimate set on the 17 hold-out plans (docs/derived-blocks-planning-2026-10-06.md §2).
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.written_lines import drop_repeated_bodies, from_brief

PLAN_EMPTY = "PLAN_EMPTY"
PLAN_INSTRUCTION_TEXT = "PLAN_INSTRUCTION_TEXT"
PLAN_DUPLICATE_ITEMS = "PLAN_DUPLICATE_ITEMS"
SLIDE_SPARSE = "SLIDE_SPARSE"
REASK_CODES = (PLAN_EMPTY, PLAN_INSTRUCTION_TEXT)

# the keys that hold a component's content; a block kind with none of them filled is empty
_CONTENT_KEYS: dict[str, tuple[str, ...]] = {
    "kpi_row": ("kpi_labels", "kpi_values"),
    "chart": ("chart_labels", "chart_series", "chart_values"),
    "table": ("table_rows",),
    "bullet_list": ("bullets",),
    "narrative": ("text",),
    "caption": ("text",),
    "timeline": ("timeline_items",),
    "flow": ("flow_steps", "nodes"),
    "process_arrow": ("process_steps",),
    "pyramid": ("pyramid_levels",),
    "tree": ("tree_nodes",),
    "card_grid": ("cards",),
    "matrix": ("matrix_items", "quadrants"),
}
_TEXT_KINDS = ("narrative", "caption", "bullet_list")
_WEIGHT_RANK = {"hero": 0, "peer": 1, "supporting": 2, "minor": 3}

# ── instruction text ────────────────────────────────────────────────────────

# a label that marks presenter notes ("Speaker Notes: Lead with ...")
_NOTES_LABEL = re.compile(r"^\W*(speaker|presenter|slide)?\s*(notes?|talking points?)\s*[:\-–—]", re.I)
# verbs that only address a presenter: always instruction text at the start of slide text
_PRESENTER_VERB = re.compile(
    r"^\W*(walk (?:the audience |them |everyone )?through|talk (?:the audience )?through|lead with|"
    r"frame (?:this|these|the)|start with|begin with|open with|end with|close with|conclude with|"
    r"remind (?:the )?(?:audience|them)|tell (?:the )?(?:audience|them)|pivot to|transition to)\b", re.I)
# verbs that direct how to build the slide: instruction text only when the brief did not say them
_PLANNER_VERB = re.compile(
    r"^\W*(deepen|break down|show(?: how| that| the| where)?|highlight|illustrate|emphasi[sz]e|stress|"
    r"explain|discuss|summari[sz]e|demonstrate|introduce|present|outline|compare|focus on|"
    r"point out|call out|use this slide|make the case)\b", re.I)
# words that address the slide or the audience, anywhere in the text
_ADDRESSES_SLIDE = re.compile(r"\b(this slide|the audience|speaker notes?|presenter|talking points?)\b", re.I)


def is_instruction_text(text: str, brief_text: str) -> bool:
    """True when `text` is a direction to the presenter or slide builder, not audience content."""
    t = (text or "").strip()
    if not t:
        return False
    if _NOTES_LABEL.match(t) or _PRESENTER_VERB.match(t) or _ADDRESSES_SLIDE.search(t):
        return True
    return bool(_PLANNER_VERB.match(t)) and not from_brief(t, brief_text)


def _text_items(comp: dict[str, Any]) -> list[str]:
    data = comp.get("content_data") or {}
    if comp.get("kind") == "bullet_list":
        return [str(b) for b in data.get("bullets") or []]
    return [str(data["text"])] if data.get("text") else []


# ── emptiness ───────────────────────────────────────────────────────────────

def _filled(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return any(_filled(v) for v in (value.values() if isinstance(value, dict) else value))
    return value is not None and value != ""


def is_empty(comp: dict[str, Any]) -> bool:
    keys = _CONTENT_KEYS.get(comp.get("kind", ""))
    if not keys:
        return False  # title (its text is the slide's headline) and kinds we do not check
    data = comp.get("content_data") or {}
    return not any(_filled(data.get(k)) for k in keys)


# ── problems that justify a re-ask ──────────────────────────────────────────

def find_problems(plan: dict[str, Any], brief_text: str) -> list[dict[str, str]]:
    """PLAN_EMPTY / PLAN_INSTRUCTION_TEXT flags for a plan. An empty caption alone is not one:
    nothing is lost by dropping it, so it is not worth a second call."""
    problems: list[dict[str, str]] = []
    comps = plan.get("components") or []
    if not comps:
        problems.append({"code": PLAN_EMPTY, "component_id": "", "detail": "the plan has no components"})
    for comp in comps:
        cid = comp.get("component_id", "")
        if is_empty(comp) and comp.get("kind") != "caption":
            problems.append({"code": PLAN_EMPTY, "component_id": cid,
                             "detail": f"{comp.get('kind')} '{cid}' has no content"})
        for item in _text_items(comp):
            if is_instruction_text(item, brief_text):
                problems.append({"code": PLAN_INSTRUCTION_TEXT, "component_id": cid,
                                 "detail": f"{comp.get('kind')} '{cid}' holds an instruction, not slide content: "
                                           f"{item[:90]}"})
                break
    return problems


def reask_context(problems: list[dict[str, str]]) -> dict[str, Any]:
    """The `repair_context` block of the planner's user prompt, naming what to fix."""
    kinds = sorted({p["detail"].split(" ")[0] for p in problems if p["component_id"]})
    return {
        "failed_kinds": kinds or ["(whole plan)"],
        "errors": [p["detail"] for p in problems],
        "directive": ("Plan this slide again. Fill every component's content_data from the key messages "
                      "(no empty components). Slide text must be what the audience reads: never an "
                      "instruction to the presenter, never speaker notes, never 'show / highlight / break down / "
                      "walk through ...' directions. Keep the other components that were right."),
    }


def problem_count(plan: dict[str, Any], brief_text: str) -> int:
    return len(find_problems(plan, brief_text))


# ── fixes ───────────────────────────────────────────────────────────────────

_TOKEN = re.compile(r"[a-z0-9₹%]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _labels(comp: dict[str, Any]) -> list[str]:
    """The item labels of a list-like component."""
    data = comp.get("content_data") or {}
    kind = comp.get("kind")
    if kind == "card_grid":
        return [str(c.get("title", "")) for c in data.get("cards") or [] if isinstance(c, dict)]
    if kind == "timeline":
        return [str(i.get("label", "")) for i in data.get("timeline_items") or [] if isinstance(i, dict)]
    key = {"process_arrow": "process_steps", "flow": "flow_steps", "bullet_list": "bullets",
           "pyramid": "pyramid_levels"}.get(kind or "")
    if not key:
        return []
    return [str(i.get("label", "") if isinstance(i, dict) else i) for i in data.get(key) or []]


def _same_label(a: set[str], b: set[str]) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= 0.6


def label_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Share of the smaller component's item labels that the other one also has (0 when either
    has fewer than 3 labels: two short lists share words by chance)."""
    la, lb = [_tokens(x) for x in _labels(a)], [_tokens(x) for x in _labels(b)]
    la, lb = [x for x in la if x], [x for x in lb if x]
    if min(len(la), len(lb)) < 3:
        return 0.0
    small, large = (la, lb) if len(la) <= len(lb) else (lb, la)
    return sum(any(_same_label(s, o) for o in large) for s in small) / len(small)


def _text_mass(comp: dict[str, Any]) -> int:
    return len(re.findall(r"\S+", str(comp.get("content_data") or {})))


def drop_duplicate_items(plan: dict[str, Any]) -> list[str]:
    """C17: two list-like components that show the same items (phase cards + chevrons of the same
    phases): keep the one with more text (a tie keeps the heavier weight) and drop the other, so
    nothing the poorer one said is lost; the kept one takes the better of the two weights."""
    notes: list[str] = []
    comps = list(plan.get("components") or [])
    dropped: set[int] = set()  # id() of a dict: plans saved before step 0 may have no component_id
    for i, a in enumerate(comps):
        for b in comps[i + 1:]:
            if id(a) in dropped or id(b) in dropped or label_overlap(a, b) < 0.7:
                continue
            keep, drop = sorted((a, b), key=lambda c: (-_text_mass(c), _WEIGHT_RANK.get(c.get("weight", "peer"), 1)))
            dropped.add(id(drop))
            if _WEIGHT_RANK.get(drop.get("weight", "peer"), 1) < _WEIGHT_RANK.get(keep.get("weight", "peer"), 1):
                keep["weight"] = drop["weight"]
            notes.append(f"dropped {drop.get('kind')} '{drop.get('component_id', '')}': it shows the same items as "
                         f"{keep.get('kind')} '{keep.get('component_id', '')}'")
            _flag(plan, PLAN_DUPLICATE_ITEMS, drop.get("component_id", ""), notes[-1])
    if dropped:
        plan["components"] = [c for c in comps if id(c) not in dropped]
    return notes


def _flag(plan: dict[str, Any], code: str, component_id: str, detail: str) -> None:
    plan.setdefault("plan_flags", []).append({"code": code, "component_id": component_id, "detail": detail})


def drop_instruction_text(plan: dict[str, Any], brief_text: str) -> list[str]:
    """What a re-ask did not remove: instruction paragraphs and bullets, and empty captions."""
    notes: list[str] = []
    keep = []
    for comp in plan.get("components") or []:
        cid, kind = comp.get("component_id", ""), comp.get("kind")
        if kind == "caption" and is_empty(comp):
            notes.append(f"dropped empty caption '{cid}'")
            continue
        if kind in ("narrative", "caption") and any(is_instruction_text(t, brief_text) for t in _text_items(comp)):
            notes.append(f"dropped {kind} '{cid}': it is an instruction to the presenter, not slide content")
            _flag(plan, PLAN_INSTRUCTION_TEXT, cid, notes[-1])
            continue
        if kind == "bullet_list":
            data = comp.get("content_data") or {}
            bullets = [b for b in data.get("bullets") or [] if not is_instruction_text(str(b), brief_text)]
            if len(bullets) != len(data.get("bullets") or []):
                data["bullets"] = bullets
                comp["items"] = len(bullets) or comp.get("items", 0)
                notes.append(f"dropped instruction bullets from '{cid}'")
                _flag(plan, PLAN_INSTRUCTION_TEXT, cid, notes[-1])
        keep.append(comp)
    plan["components"] = keep
    return notes


# ── thin slides ─────────────────────────────────────────────────────────────

SPARSE_UNITS = 9  # a slide worth less than this many "units" is reported thin
_LIST_KEYS = {"bullet_list": "bullets", "timeline": "timeline_items", "process_arrow": "process_steps",
              "flow": "flow_steps", "pyramid": "pyramid_levels"}


def _units(comp: dict[str, Any]) -> float:
    """A rough visual weight: a KPI tile counts 3, a card 2, a chart 10, a table at least the limit,
    list items grow with their length."""
    data = comp.get("content_data") or {}
    kind = comp.get("kind")
    if kind == "kpi_row":
        return 3.0 * len(data.get("kpi_values") or data.get("kpi_labels") or [])
    if kind == "card_grid":
        return 2.0 * len(data.get("cards") or [])
    if kind == "chart":
        return 10.0
    if kind == "table":
        # a table grows to fill the slide, so a table slide is never thin by itself
        return max(float(SPARSE_UNITS), len(data.get("table_rows") or []) * max(1, len(data.get("table_columns") or [])) / 3)
    if kind == "narrative":
        return 2.0
    if kind in ("matrix", "tree", "layer"):
        return 8.0
    key = _LIST_KEYS.get(kind or "")
    if key:
        items = data.get(key) or []
        if not items:
            return 0.0
        words = len(re.findall(r"\S+", str(items))) / len(items)
        return len(items) * (1 + min(words, 24) / 12)
    return 0.0


def sparse_flag(plan: dict[str, Any]) -> dict[str, str] | None:
    """SLIDE_SPARSE for a content / data slide worth fewer than SPARSE_UNITS (an estimate: the
    renderer's own SLIDE_SPARSE, content filling < 55% of the body, arrives with blocks)."""
    if plan.get("slide_type") not in ("content", "data"):
        return None
    comps = plan.get("components") or []
    if not comps or all(is_empty(c) for c in comps if c.get("kind") != "title"):
        return None  # empty, not thin: PLAN_EMPTY already says it
    total = sum(_units(c) for c in comps if c.get("kind") not in ("title", "caption"))
    if total >= SPARSE_UNITS:
        return None
    return {"code": SLIDE_SPARSE, "component_id": "",
            "detail": f"thin slide: about {total:.1f} units of content (limit {SPARSE_UNITS})"}


# ── entry point ─────────────────────────────────────────────────────────────

def finalize_plan(plan: dict[str, Any], brief_text: str) -> list[str]:
    """Run every code fix and the thin-slide report on a finished plan, in place.
    Returns the plain-words notes; `plan["plan_flags"]` lists what was found."""
    notes = drop_instruction_text(plan, brief_text)
    notes += drop_repeated_bodies(plan)
    notes += drop_duplicate_items(plan)
    for comp in plan.get("components") or []:
        if is_empty(comp):
            _flag(plan, PLAN_EMPTY, comp.get("component_id", ""), f"{comp.get('kind')} has no content")
    if not plan.get("components"):
        _flag(plan, PLAN_EMPTY, "", "the plan has no components")
    sparse = sparse_flag(plan)
    if sparse:
        plan.setdefault("plan_flags", []).append(sparse)
    return notes
