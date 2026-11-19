"""Component capacity — the single source for how much each component kind can draw.

Loaded from knowledge/core/capacity.yaml. The slide component planner prompt renders
these numbers, and the plan checks enforce them, so a limit is never restated in prose.
"""

from __future__ import annotations

import functools
import math
import re
from pathlib import Path
from typing import Any

import yaml

_CAPACITY_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "capacity.yaml"


@functools.lru_cache(maxsize=1)
def capacity() -> dict[str, dict[str, Any]]:
    """{kind: {limit: value}}; ranges are [min, max] lists."""
    return yaml.safe_load(_CAPACITY_FILE.read_text(encoding="utf-8")) or {}


def span(kind: str, key: str = "items") -> str:
    """A range as prompt text: [3, 5] -> "3-5"; a diagram's items by direction -> "3-7 horizontal, up to 9 vertical"."""
    c = capacity()[kind]
    if key == "items" and "max_items" in c:
        m = c["max_items"]
        return f"{c['min_items']}-{m['horizontal']} horizontal, up to {m['vertical']} vertical"
    lo, hi = c[key]
    return f"{lo}-{hi}"


_PLACES = (("band", "the main band"), ("under_kpi", "under a KPI row"), ("split_60", "a 60 % column"),
           ("split_40", "a 40 % column"), ("card", "a card"))


def placements(kind: str) -> str:
    """Items that hold per placement as prompt text: "the main band 7 across / 9 down; under a KPI row 7 / 6; ...";
    tree's two layouts are its directions (capacity.yaml `placement`, measured by the node break map)."""
    p = capacity()["placement"][kind]
    first, *rest = _PLACES
    out = [f"{first[1]} {p['horizontal'][first[0]]} across / {p['vertical'][first[0]]} down"]
    out += [f"{name} {p['horizontal'][key]} / {p['vertical'][key]}" for key, name in rest]
    return "; ".join(out)


def direction_of(comp: dict[str, Any]) -> str:
    """A planned diagram's direction: content_data.direction, else the plan's orientation, else POM's default."""
    d = (comp.get("content_data") or {}).get("direction") or comp.get("orientation") or "horizontal"
    return "vertical" if str(d).lower() == "vertical" else "horizontal"


def max_of(kind: str, key: str = "items", direction: str | None = None) -> int:
    """The largest value; a diagram's items by direction (no direction: horizontal, POM's default)."""
    c = capacity()[kind]
    if key == "items" and "max_items" in c:
        return c["max_items"]["vertical" if direction == "vertical" else "horizontal"]
    value = c[key]
    return value[1] if isinstance(value, list) else value


# ── Plan check: components past their capacity become cards ────────────────
# Chevrons with 7 items or sentence labels break words into letters ("Consume r",
# XTSY slide 7); a timeline past its items collides. A card_grid holds the same items
# legibly, so the plan is fixed in code — no re-plan call. Each limit is the one for the
# component's own direction (2026-10-21): a 7-step vertical chevron column is kept.
# A flow past capacity is only reported, not switched (2026-10-04): as cards it lost
# its arrows and stopped reading as a sequence (XTSY slide 6, two UI decks).

def _label(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("label") or item.get("title") or item.get("name") or "")
    return str(item)


def _detail(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("description") or item.get("detail") or "")
    return ""


def _as_cards(items: list[Any], tag_key: str | None = None) -> list[dict[str, str]]:
    cards = []
    for item in items:
        card = {"title": _label(item)}
        if tag_key and isinstance(item, dict) and item.get(tag_key):
            card["tag"] = str(item[tag_key])
        if _detail(item):
            card["body"] = _detail(item)
        cards.append(card)
    return cards


def per_row(n: int, most: int) -> int:
    """Cards per row for n cards, at most `most`, rows as even as possible (7 -> 4, 9 -> 3)."""
    rows = math.ceil(n / most)
    return math.ceil(n / rows)


def _to_cards(comp: dict[str, Any], cards: list[dict[str, str]]) -> None:
    """The component becomes a card_grid of `cards`. Its summary and hint were written for the old kind
    (chevrons, a rail, bands): left as they were, they steer the generator back to that kind (a switched
    table drawn as ruled rows, 2026-11-16), so both now say the component is cards."""
    was = comp.get("kind") or "diagram"
    comp["content_summary"] = (f"{len(cards)} items as cards, in their order (code changed this {was} to cards: "
                               f"its items could not be drawn as a {was})")
    if comp.get("design_hint"):
        comp["design_hint"] = f"Drawn as cards, not as a {was}; apply this to the cards: {comp['design_hint']}"
    comp["kind"] = "card_grid"
    comp["items"] = len(cards)
    comp.pop("orientation", None)
    comp["content_data"] = {"card_layout": "steps" if len(cards) <= max_of("card_grid", "steps_max") else "grid",
                            "cards": cards}


# ── units of a figure (plan_ledger's shape check) ───────────────────────────
# Code never switches a kind the brief asked for (2026-11-16, user): the table -> kpi_row switch of
# decision L5 was removed. A Metric | Value table the brief asks for stays a table; with no direction the
# planner's routing table already chooses tiles. Switches left in code are renderer limits only (items or
# words that cannot be drawn), never a judgement of taste.

_UNITS = (("₹", re.compile(r"₹|\brs\.?\s*\d|\$|€|£", re.I)), ("%", re.compile(r"%")),
          ("x", re.compile(r"\d\s*x\b", re.I)))


def _unit(value: str) -> str:
    return next((u for u, pat in _UNITS if pat.search(value)), "n")


def _placeholder_matrix(cd: dict[str, Any]) -> bool:
    """Every cell of a card matrix is just its row and / or column name ("Visibility — Zepto")."""
    names = [str(x) for x in (cd.get("rows") or []) + (cd.get("columns") or [])]
    vocab = {w for n in names for w in re.findall(r"\w+", n.lower())}
    cards = cd.get("cards") or []
    return bool(cards and vocab) and all(
        set(re.findall(r"\w+", _label(c).lower())) <= vocab and not (isinstance(c, dict) and c.get("body"))
        for c in cards)


def enforce_capacity(components: list[dict[str, Any]]) -> list[str]:
    """Fix the plan in place where a component cannot draw its items (capacity.yaml)
    or a named visual does not suit the data. Returns one plain-words note per change."""
    notes: list[str] = []
    out: list[dict[str, Any]] = []
    card_max = max_of("card_grid", "per_row")
    for comp in components:
        kind, data = comp.get("kind"), comp.get("content_data") or {}
        cid = comp.get("component_id") or kind
        direction = direction_of(comp)
        if kind == "process_arrow":
            steps = data.get("process_steps") or []
            most = max_of("process_arrow", direction=direction)
            too_many = len(steps) > most
            max_words = capacity()["process_arrow"]["max_label_words"]
            long = [s for s in map(_label, steps) if len(s.split()) > max_words]
            if steps and (too_many or long):
                why = f"{len(steps)} steps ({direction} holds {most})" if too_many else f"label '{long[0]}' over {max_words} words"
                _to_cards(comp, _as_cards(steps))
                notes.append(f"{cid}: process_arrow with {why} -> card_grid ({comp['content_data']['card_layout']})")
        elif kind == "timeline":
            items = data.get("timeline_items") or []
            most = max_of("timeline", direction=direction)
            if len(items) > most:
                _to_cards(comp, _as_cards(items, tag_key="date"))
                notes.append(f"{cid}: timeline with {len(items)} items ({direction} holds {most}) "
                             f"-> card_grid ({comp['content_data']['card_layout']})")
        elif kind == "flow":
            steps = data.get("flow_steps") or []
            most = max_of("flow", direction=direction)
            if len(steps) > most:
                notes.append(f"{cid}: flow with {len(steps)} nodes is over its {direction} capacity ({most}); kept as a flow")
        # every grid knows its cards per row; a steps row past its capacity becomes a grid
        if comp.get("kind") == "card_grid":
            cd = comp.setdefault("content_data", {})
            if cd.get("card_layout") == "matrix" and _placeholder_matrix(cd):
                cd.update({"card_layout": "grid",
                           "cards": [{"title": str(r)} for r in cd.get("rows") or []]})
                cd.pop("rows", None)
                notes.append(f"{cid}: matrix cells only repeated the row / column names -> one card per row")
            cards = cd.get("cards") or []
            if cd.get("card_layout") == "steps" and len(cards) > max_of("card_grid", "steps_max"):
                cd["card_layout"] = "grid"
                notes.append(f"{cid}: {len(cards)} steps are too many for one row -> card_grid (grid)")
            if cd.get("card_layout", "grid") == "grid" and cards:
                cd["per_row"] = per_row(len(cards), card_max)
        out.append(comp)
    components[:] = out
    return notes


# ── The generator's layout rules (capacity.yaml `layout`, 2026-10-07) ──────
def layout_rules() -> str:
    """Prompt text for the generator: how to lay any slide out, numbers from capacity.yaml (the same on every slide).
    The lines for one component kind are kind_layout_rules'."""
    lay = capacity()["layout"]
    return "\n".join([
        f"- A takeaway card beside a chart or table takes {lay['side_card_w'][0]}-{lay['side_card_w'][1]} "
        f"of the width; the evidence takes the rest.",
        f"- Two-column slides: {' or '.join(lay['split'])}, the evidence side wider.",
        "- Everything ends inside the slide padding; the slide's main band takes the spare height.",
    ])


def kind_layout_rules() -> dict[str, dict[str, list[str]]]:
    """kind -> {"code": lines when code draws it, "hand": lines when the LLM draws it}, numbers from capacity.yaml.
    The generator's prompt carries a kind's lines only on a slide that has one (context_builder)."""
    k, lay = capacity()["kpi_row"], capacity()["layout"]
    lo, hi = lay["hero_number_px"]
    g0, g1 = lay["grid_gap_px"]
    r0, r1 = lay["table_row_px"]
    half = (f"at most {lay['table_cols_half']} columns in a half-width card (more -> give the table the full "
            "width)")
    return {
        "kpi_row": {
            "code": [f"KPI tiles: one <KpiRow ref> per kpi_row; code lays out its rows (at most {k['per_row'][1]} "
                     "per row) and sizes the numbers.",
                     "One number the headline rests on: variant=\"bento\" (the plan's emphasis item large); "
                     f"{lay['paired_cards']} compared metrics: {lay['paired_cards']} equal cards side by side."],
            "hand": [f"KPI tiles: at most {k['per_row'][1]} per row, each at least {lay['kpi_tile_min_w']}px wide; "
                     "more metrics -> rows of equal tiles (w as %: 2 per row 49%, 3 per row 32%).",
                     f"One number the headline rests on: a hero tile, number {lo}-{hi}px; "
                     f"{lay['paired_cards']} compared metrics: {lay['paired_cards']} equal cards side by side."],
        },
        "card_grid": {
            "hand": [f"Card grids: equal widths per row, gaps {g0}-{g1}px; never a lone narrow card beside a wide one."],
        },
        "table": {
            "code": [f"Tables: {half}."],
            "hand": [f"Tables: {half}; body rows {r0}-{r1}px."],
        },
    }
