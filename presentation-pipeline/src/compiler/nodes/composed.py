"""The composition nodes (left-blocks spec §2.5), behind one interface for the validator, generator and context
builder. Code draws every component of these kinds that has a component_id: chart (charts.py), timeline (sequences.py), kpi_row / card_grid
(tile_groups.py), table (tables.py), bullet_list (bullets.py)."""

from __future__ import annotations

import json
import re
from typing import Any

from src.compiler.nodes import bullets, charts, compose, sequences, spec, tables, tile_groups, validate

# plan-level content_data keys a drawn kind no longer needs in the prompt
PLAN_KEYS = {"chart": ("chart_",), "timeline": ("timeline_items",),
             "kpi_row": ("kpi_",), "card_grid": ("card", "per_row", "focus_card"),
             "table": ("table_",), "bullet_list": ("bullets",)}

# kind -> module for the one-kind nodes after chart, the sequences and the tile groups (each: on, TAG, components,
# expand, node_lines, prompt_line, tag_attributes)
MORE = {"table": tables, "bullet_list": bullets}


# the plan kinds code draws, in prompt order
KINDS = ("chart",) + sequences.KINDS + tile_groups.KINDS + tuple(MORE)
assert set(KINDS) == set(spec.CODE_DRAWN)


def tag(kind: str) -> str:
    if kind in tile_groups.KINDS:
        return tile_groups.node(kind)["tag"]
    if kind in MORE:
        return MORE[kind].TAG
    return charts.TAG if kind == "chart" else sequences.TAGS[kind]


def drawn(plan: dict | None, kind: str) -> dict[str, dict]:
    """The components of a code-drawn kind that code draws (those with an id)."""
    if kind not in KINDS:
        return {}
    if kind in tile_groups.KINDS:
        return tile_groups.components(plan, kind)
    if kind in MORE:
        return MORE[kind].components(plan)
    return charts.chart_components(plan) if kind == "chart" else sequences.components(plan, kind)


def all_drawn(plan: dict | None, kind: str) -> bool:
    """Every component of the kind on this slide is drawn by code (none without an id)."""
    n = sum(c.get("kind") == kind for c in (plan or {}).get("components") or [])
    return bool(n) and len(drawn(plan, kind)) == n


def _parent_align(before: str) -> str | None:
    """alignItems of the VStack the next tag sits in; None when it sits in anything else."""
    stack: list[tuple[str, str]] = []
    for m in compose._STACK.finditer(before):
        close, name, attrs, selfclose = m.groups()
        if close:
            if stack:
                stack.pop()
        elif not selfclose:
            stack.append((name, attrs))
    if not stack or stack[-1][0] != "VStack":
        return None
    found = re.search(r'\balignItems="([^"]*)"', stack[-1][1])
    return found.group(1) if found else None


def hold_width(xml: str, plan: dict | None) -> str:
    """A drawn node with no w in a VStack aligned start / center / end shrinks to its content: its inner w="1" columns
    get no width and the compile crashes (paid check 2026-11-04: a repair changed the slide's stretch to start)."""
    ids = {tag(k): set(drawn(plan, k)) for k in KINDS}
    out, pos = [], 0
    for t in validate.ref_tags(xml):
        a = t["attrs"]
        if a["ref"] in ids.get(t["tag"], ()) and not {"w", "alignSelf"} & set(a) \
                and _parent_align(xml[:t["start"]]) in ("start", "center", "end"):
            cut = t["start"] + 1 + len(t["tag"])
            out += [xml[pos:cut], ' alignSelf="stretch"']
            pos = cut
    return "".join(out) + xml[pos:]


def explain_unknown(issue: dict[str, Any], plan: dict | None) -> dict[str, Any]:
    """A ref tag on a component of another kind: say what the component is, and hand over its words when code does not
    draw it, because a patch sees only the XML (paid check 2026-11-04: a narrative written as <CardGrid ref>)."""
    comp = next((c for c in (plan or {}).get("components") or [] if c.get("component_id") == issue.get("ref")), None)
    if issue.get("code") != "NODE_REF_UNKNOWN" or comp is None:
        return issue
    cid, kind, head = comp["component_id"], comp.get("kind"), issue["message"].split(": ", 1)[0]
    if cid in drawn(plan, kind):
        return dict(issue, message=f'{head}: {cid} is a {kind}: place <{tag(kind)} ref="{cid}"/>.')
    words = json.dumps(comp.get("content_data") or {}, ensure_ascii=False)
    return dict(issue, message=f"{head}: {cid} is a {kind}, and code does not draw it. Remove this tag and write it by hand "
                               f"with <VStack> and <Text>, with no ref. Its content: {words}")


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    xml = hold_width(xml, plan)
    out = {"xml": xml, "issues": [], "ok": True, "components": {}}
    for fn in (charts.expand, sequences.expand, tile_groups.expand, *(m.expand for m in MORE.values())):
        r = fn(out["xml"], plan)
        out = {"xml": r["xml"], "issues": out["issues"] + r["issues"], "ok": out["ok"] and r["ok"],
               "components": {**out["components"], **r["components"]}}
    for issue in unplaced(xml, plan, out["components"]):
        out["issues"].append(issue)
        out["ok"] = False
    out["issues"] = [explain_unknown(i, plan) for i in out["issues"]]
    out["xml"] = validate.one_value(out["xml"])
    return out


def unplaced(xml: str, plan: dict | None, placed: dict[str, Any]) -> list[dict[str, Any]]:
    """NODE_ITEM_MISSING for a component code draws with no tag on the slide: left out, or typed by hand without ref (a
    whole table can vanish, or its numbers be retyped, with no other check noticing). A KPI placed by element refs
    (<Text ref="kpis.2.value"/>) counts as placed; a component with no data has nothing to draw."""
    out = []
    for kind in KINDS:
        for cid, comp in drawn(plan, kind).items():
            if cid in placed or validate.empty(comp) or re.search(rf'\bref="{re.escape(cid)}\.', xml):
                continue
            out.append({"code": "NODE_ITEM_MISSING", "severity": "error", "ref": cid,
                        "message": f'{kind} "{cid}" is not on the slide: place <{tag(kind)} ref="{cid}"/> (code draws its '
                                   "content; never type it by hand)."})
    return out


# The rules for drawing a kind by hand reach the prompt only for a component code does not draw
# (context_builder: house-style.yaml `kinds`), so this section needs no list of rules to ignore.
OVERRIDE = ("## CODE-DRAWN NODES\n"
            "A component whose line under COMPONENTS names a ref tag is drawn by code: place that tag once and size it "
            "with w / h / grow like any box. Code writes its words, numbers and items: the tag holds only the "
            "<Highlight/> or item tags its section below names. Typing its content by hand, or leaving the tag out, "
            "is an error. A component whose line names no ref tag (a narrative, a callout, a title) has no node: "
            "write it by hand with <VStack> and <Text>, never as a ref tag.\n"
            "Peers look alike: when one content component on the slide sits in a panel (a fill or a border), give the others "
            "one too. A ref tag takes it as box attributes on the tag (padding, backgroundColor, border.color, border.width, "
            "borderRadius); a hand-drawn component sits in a <VStack> with them.")


def slide_kinds(plan: dict | None) -> list[str]:
    """The code-drawn kinds with at least one component code draws on this slide, in KINDS order."""
    return [k for k in KINDS if drawn(plan, k)]


def node_lines(kinds: list[str] | tuple[str, ...]) -> str:
    """The prompt sections for `kinds` (a slide's slide_kinds): the shared rule, then one section per kind."""
    if not kinds:
        return ""
    seq = [k for k in sequences.KINDS if k in kinds]
    tg = [k for k in tile_groups.KINDS if k in kinds]
    return "\n\n".join([OVERRIDE] + ([charts.node_lines()] if "chart" in kinds else [])
                       + ([sequences.node_lines(seq)] if seq else []) + ([tile_groups.node_lines(tg)] if tg else [])
                       + [m.node_lines() for k, m in MORE.items() if k in kinds])


def prompt_line(comp: dict, headline: str = "") -> str:
    if comp["kind"] in tile_groups.KINDS:
        return tile_groups.prompt_line(comp, headline)
    if comp["kind"] in MORE:
        return MORE[comp["kind"]].prompt_line(comp, headline)
    return charts.prompt_line(comp, headline) if comp["kind"] == "chart" else sequences.prompt_line(comp, headline)


def tag_attributes(kind: str) -> list[str]:
    if kind in tile_groups.KINDS:
        return tile_groups.tag_attributes(kind)
    if kind in MORE:
        return MORE[kind].tag_attributes()
    return charts.tag_attributes() if kind == "chart" else sequences.tag_attributes(kind)


def tags_contract(kind: str) -> tuple[list[str], list[str], dict[str, list[str]]] | None:
    """A kind with an item tag (kpi_row, card_grid): its tags for ALLOWED NODES / NODE HIERARCHY; else None."""
    return tile_groups.tags_contract(kind) if kind in tile_groups.KINDS else None
