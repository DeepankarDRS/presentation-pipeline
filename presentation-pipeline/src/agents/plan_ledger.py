"""Two general plan checks (2026-11-12), run on every slide plan before code fixes, each a reason to re-ask:

1. **Item ledger** - every item of the slide's key messages appears on the slide, and no item is drawn twice.
   Items are the brief's own pieces (lines, bullets, ";" / arrow parts, a leading "Label:" taken off). An item is
   shown when every figure it gives appears exactly and most of its other words do; it is repeated when two content
   components each hold it as a text unit of its own (a title, bullet, cell, step). Matching is by content words, so
   it holds for any domain and any component kind. ITEM_MISSING, ITEM_REPEATED.
2. **Shape check** - a component's content has the shape the routing table (knowledge/core/routing.yaml, the same
   table the planner's prompt renders) sends to another kind. Only shapes code can measure: figures or words in
   cells, point and series counts, units. SHAPE_MISFIT.

They replace one-shape patches (a list-vs-card-bullets duplicate threshold, a two-row-table switch, a matrix column
note), each of which caught one output shape. Nothing is changed here: the re-ask (plan_with_reask) gets the
problems; the code fixes that already exist stay as the last resort. Replayed on the saved outline + plan pairs
before use (output/**/runs.json).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml

from src.agents.written_lines import (BRIEF_OVERLAP, NOTES_LABEL, _words, content_line_list, matches_instruction,
                                      visual_directions)

ITEM_MISSING = "ITEM_MISSING"
ITEM_REPEATED = "ITEM_REPEATED"
SHAPE_MISFIT = "SHAPE_MISFIT"

_ROUTING = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "routing.yaml"

# keys of content_data that are settings, not text the audience reads
_NOT_TEXT = {"tone", "icon", "key_phrase", "card_layout", "chart_type", "direction", "layout", "body_source",
             "kpi_directions", "kpi_tones", "kpi_icons", "focus_card", "x", "y", "per_row"}
# a brief piece: a line, a bullet, a ";" item, an arrow step; arrows inside brackets stay ("(top -> bottom)")
_PIECES = re.compile(r"\n|(?:^|\s)[*•·]\s|;|→|->")
_BRACKETED = re.compile(r"\([^()]*\)")
# a label in front of a piece ("Key Takeaway:", "Phase 1:", "Occasions across the day:"): it names the item
_LEAD = re.compile(r"^\s*(?:\d+[.)]\s*)?[^:]{1,60}:\s+(?=\S)")
# a piece that says how to draw or present the slide (an imperative), not what the slide says
# (checked at the start of a line only: "Display banners" inside a list is an item, not a direction)
_DIRECTIVE = re.compile(r"^\W*(?:show|highlight|visuali[sz]e|illustrate|emphasi[sz]e|depict|focus on|"
                        r"use\s+(?:a|an|the|arrows?|icons?|visuals?|charts?|colou?rs?)\b)", re.I)
_FIGURE = re.compile(r"\d")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@functools.lru_cache(maxsize=1)
def routing() -> dict[str, dict[str, str]]:
    """The routing table's rows by id, limits rendered from capacity.yaml (`kind_timeline_node` kept apart)."""
    from jinja2 import Environment
    from src.agents.capacity import capacity, span
    env = Environment()
    env.globals.update(cap=capacity(), span=span)
    rows = yaml.safe_load(_ROUTING.read_text(encoding="utf-8"))["rows"]
    return {r["id"]: {k: env.from_string(str(v)).render() for k, v in r.items()} for r in rows}


def routing_rows(timeline_node: bool = False) -> list[dict[str, str]]:
    """The table as the planner's prompt shows it: `kind_timeline_node` in place of `kind` when code draws timelines."""
    return [{"id": r["id"], "states": r["states"], "not_for": r["not_for"],
             "kind": r.get("kind_timeline_node") if timeline_node and r.get("kind_timeline_node") else r["kind"]}
            for r in routing().values()]


# ── 1. item ledger ──────────────────────────────────────────────────────────

def brief_items(slide: dict[str, Any], instructions: list[str] | tuple[str, ...] = ()) -> list[str]:
    """The slide's content items: key messages that are content (not a visual direction, presenter note or brief
    instruction), cut into pieces; an imperative piece ("Show progression from ...") is a direction and skipped; a
    leading label is taken off. Pieces without a content word drop."""
    items: list[str] = []
    for line in content_line_list(slide, visual_directions(slide)):
        if NOTES_LABEL.match(line or "") or matches_instruction(line, list(instructions)):
            continue
        if "|" in line and not _FIGURE.search(line):
            continue   # a table's header row ("Metric | Value"): it names columns, it is not an item
        if _DIRECTIVE.match(line):
            continue   # "Show progression from A to B", "Use arrow visuals": how to draw, not what to say
        protected = _BRACKETED.sub(lambda m: m.group(0).replace("→", "\x00").replace("->", "\x01"), line)
        for raw in _PIECES.split(protected):
            raw = raw.replace("\x00", "→").replace("\x01", "->").strip()
            if raw.endswith(":"):
                continue   # a bare label ("Benefits:"): it heads the items after it
            piece = " ".join(raw.split()).strip(" .,-–—:")
            if not piece:
                continue
            body = _LEAD.sub("", piece, count=1)
            body = body if _words(body) else piece
            if _words(body):
                items.append(body)
    return list(dict.fromkeys(items))


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if isinstance(value, dict):
        return [s for k, v in value.items() if k not in _NOT_TEXT for s in _strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _strings(v)]
    return []


def _norm(number: str) -> str:
    n = number.replace(",", "")
    return n.rstrip("0").rstrip(".") if "." in n else n   # "0.80" = "0.8", "1.0" = "1"


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in _NUMBER.findall(text)}


def _shown(item: str, words: set[str], numbers: set[str]) -> bool:
    """The item is on the slide: every figure it gives, exactly, and most of its other words (70%; half when it has
    figures, since a sentence drawn as table cells or tiles keeps its figures, not its prose)."""
    figures = _numbers(item)
    if figures - numbers:
        return False
    need = [w for w in _words(item) if not _FIGURE.search(w)]
    if not need:
        return bool(figures)
    return sum(w in words for w in need) / len(need) >= (0.5 if figures else BRIEF_OVERLAP)


def _plain(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9₹%$€£]+", (text or "").lower()))


def _same_item(item: str, unit: str) -> bool:
    """One text unit (a title, bullet, cell, step) IS the item: each holds 70% of the other's content words; an item
    of one content word only when the unit is that item exactly (a step "Connect" as a chevron and a card title)."""
    a, b = set(_words(item)), set(_words(unit))
    if len(a) < 2:
        return bool(a) and _plain(item) == _plain(unit)
    common = len(a & b)
    return bool(b) and common / len(a) >= BRIEF_OVERLAP and common / len(b) >= BRIEF_OVERLAP


def ledger_problems(plan: dict[str, Any], slide: dict[str, Any],
                    instructions: list[str] | tuple[str, ...] = ()) -> list[dict[str, str]]:
    """ITEM_MISSING / ITEM_REPEATED for a plan against its slide's brief items. Coverage counts every component and
    the slide's header (headline, subtitle, label); a repeat is the same item as a unit of its own in two content
    components (the title component is the header's, never a repeat)."""
    comps = list(plan.get("components") or [])
    texts = [s for c in comps for s in _strings(c.get("content_data") or {})] + [
        str(plan.get(k) or slide.get(k) or "") for k in ("slide_title", "subtitle", "label")]
    words, numbers = set(_words(" ".join(texts))), _numbers(" ".join(texts))
    units = [(c.get("component_id", ""), _strings(c.get("content_data") or {})) for c in comps
             if c.get("kind") != "title"]
    problems: list[dict[str, str]] = []
    items = brief_items(slide, instructions)
    missing = [i for i in items if not _shown(i, words, numbers)]
    if missing:
        problems.append({"code": ITEM_MISSING, "component_id": "",
                         "detail": f"{len(missing)} item(s) of the key messages are on no component: "
                                   + "; ".join(m[:80] for m in missing[:5])})
    for item in items:
        holders = [cid for cid, strings in units if any(_same_item(item, s) for s in strings)]
        if len(holders) >= 2:
            problems.append({"code": ITEM_REPEATED, "component_id": holders[1],
                             "detail": f"'{item[:70]}' is shown by {len(holders)} components "
                                       f"({', '.join(holders)}); keep it in one"})
    # a figure of the brief drawn as a value of its own (a tile, a cell, a bar) in two components: the same data twice
    brief_figures = set().union(*(_numbers(i) for i in items)) if items else set()
    value_of: dict[str, set[str]] = {}
    for cid, strings in units:
        for s in strings:
            if _figure(s) or re.fullmatch(r"-?\d+(\.\d+)?", s.strip()):
                for n in _numbers(s) & brief_figures:
                    value_of.setdefault(n, set()).add(cid)
    twice = sorted(n for n, cids in value_of.items() if len(cids) >= 2)
    if len(twice) >= 2:   # one shared figure can be a deliberate callout; several are a repeated data set
        holders = sorted(set().union(*(value_of[n] for n in twice)))
        problems.append({"code": ITEM_REPEATED, "component_id": holders[-1],
                         "detail": f"{len(twice)} figures ({', '.join(twice[:5])}) are drawn as values in more than one "
                                   f"component ({', '.join(holders)}); show each data set once"})
    return problems


# ── 2. shape check ──────────────────────────────────────────────────────────

def _figure(text: str) -> bool:
    """A figure, not a sentence that holds a number: a digit and at most three words."""
    return bool(_FIGURE.search(text)) and len(text.split()) <= 3


def _misfit(cid: str, kind: str, fact: str, row: str, part: str = "kind") -> dict[str, str]:
    r = routing()[row]
    told = r["kind"] if part == "kind" else f"not for {r['not_for']}"
    return {"code": SHAPE_MISFIT, "component_id": cid,
            "detail": f"{kind} '{cid}': {fact}; the routing table row '{r['states']}' says {told}"}


def shape_problems(plan: dict[str, Any]) -> list[dict[str, str]]:
    """SHAPE_MISFIT where a component's measured content shape is routed to another kind (routing.yaml)."""
    from src.agents.capacity import _placeholder_matrix, _unit, capacity
    problems: list[dict[str, str]] = []
    for comp in plan.get("components") or []:
        kind, cid, data = comp.get("kind"), comp.get("component_id", ""), comp.get("content_data") or {}
        if kind == "table":
            cols = data.get("table_columns") or []
            rows = [r for r in data.get("table_rows") or [] if isinstance(r, list)]
            cells = [str(x) for r in rows for x in r[1:]]
            if len(cols) == 2 and rows and all(_figure(c) for c in cells):
                if len(rows) <= 2:
                    problems.append(_misfit(cid, kind, f"{len(rows)} row(s) of one figure each", "two_subjects"))
                elif len({_unit(c) for c in cells}) >= 2:
                    problems.append(_misfit(cid, kind, "one column of figures in different units (one subject's "
                                                       "measures)", "subject_measures"))
            elif cells and sum(len(c.split()) for c in cells) / len(cells) > 12:
                problems.append(_misfit(cid, kind, "its cells are sentences", "subjects_by_measures", "not_for"))
        elif kind == "chart":
            labels = data.get("chart_labels") or []
            series = [s for s in data.get("chart_series") or [] if isinstance(s, dict)]
            if 0 < len(labels) < capacity()["chart"]["min_points"] and len(series) <= 1:   # one measure, few points
                problems.append(_misfit(cid, kind, f"{len(labels)} point(s) of one measure", "ordered_points",
                                        "not_for"))
            values = _strings(data.get("chart_values") or []) + _strings([s.get("values") for s in series])
            units = {_unit(v) for v in values if _FIGURE.search(v) and not re.fullmatch(r"-?\d+(\.\d+)?", v)}
            if len(units) >= 2:
                problems.append(_misfit(cid, kind, f"values in {len(units)} units on one axis", "many_subjects",
                                        "not_for"))
        elif kind == "card_grid" and data.get("card_layout") == "matrix" and _placeholder_matrix(data):
            problems.append(_misfit(cid, kind, "every cell only repeats its row or column name", "word_grid",
                                    "not_for"))
    return problems


def plan_problems(plan: dict[str, Any], slide: dict[str, Any],
                  instructions: list[str] | tuple[str, ...] = ()) -> list[dict[str, str]]:
    """Both checks."""
    return ledger_problems(plan, slide, instructions) + shape_problems(plan)
