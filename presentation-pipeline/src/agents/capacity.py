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
    """A range as prompt text: [3, 5] -> "3-5"."""
    lo, hi = capacity()[kind][key]
    return f"{lo}-{hi}"


def max_of(kind: str, key: str = "items") -> int:
    value = capacity()[kind][key]
    return value[1] if isinstance(value, list) else value


# ── Plan check: components past their capacity become cards ────────────────
# Chevrons with 7 items or sentence labels break words into letters ("Consume r",
# XTSY slide 7); a horizontal timeline past 5 items collides. A card_grid holds the
# same items legibly, so the plan is fixed in code — no re-plan call.
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
    comp["kind"] = "card_grid"
    comp["items"] = len(cards)
    comp.pop("orientation", None)
    comp["content_data"] = {"card_layout": "steps" if len(cards) <= max_of("card_grid", "steps_max") else "grid",
                            "cards": cards}


# ── a named visual that doesn't suit the data is switched (user decision L5) ─
# One entity's metrics asked as "Show table: Metric | Value" read better as KPI
# tiles. The switch is recorded in the plan (capacity_fixes) so the user can see why.
# The icon list -> cards switch was removed 2026-10-04: it put a second card grid
# beside the main one (narrow cards, broken words; XTSY slides 2, 3 and 6).

_UNITS = (("₹", re.compile(r"₹|\brs\.?\s*\d|\$|€|£", re.I)), ("%", re.compile(r"%")),
          ("x", re.compile(r"\d\s*x\b", re.I)))


def _unit(value: str) -> str:
    return next((u for u, pat in _UNITS if pat.search(value)), "n")


def _metric_table_to_kpis(comp: dict[str, Any]) -> list[dict[str, Any]] | None:
    """A 2-column label | number table whose values mix units (₹, %, x: one entity's
    metrics, not one measure across entities) -> one kpi_row, in the table's order, keeping
    the table's weight. None if not such a table."""
    data = comp.get("content_data") or {}
    cols, rows = data.get("table_columns") or [], data.get("table_rows") or []
    if len(cols) != 2 or len(rows) < 3 or any(not isinstance(r, list) or len(r) != 2 for r in rows):
        return None
    labels, values = [str(r[0]) for r in rows], [str(r[1]) for r in rows]
    if not all(re.search(r"\d", v) for v in values) or len({_unit(v) for v in values}) < 2:
        return None
    n, most = len(rows), max_of("kpi_row", "per_row")
    kpis = {k: v for k, v in comp.items() if k not in ("content_data", "columns", "rows", "chart_type")}
    kpis["kind"], kpis["count"] = "kpi_row", n
    kpis["content_data"] = {"kpi_labels": labels, "kpi_values": values,
                            "kpi_deltas": [""] * n, "kpi_directions": [""] * n}
    if n > most:
        kpis["content_data"]["per_row"] = per_row(n, most)
    return kpis


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
        if kind == "process_arrow":
            steps = data.get("process_steps") or []
            too_many = len(steps) > max_of("process_arrow")
            max_words = capacity()["process_arrow"]["max_label_words"]
            long = [s for s in map(_label, steps) if len(s.split()) > max_words]
            if steps and (too_many or long):
                why = f"{len(steps)} steps" if too_many else f"label '{long[0]}' over {max_words} words"
                _to_cards(comp, _as_cards(steps))
                notes.append(f"{cid}: process_arrow with {why} -> card_grid ({comp['content_data']['card_layout']})")
        elif kind == "timeline":
            items = data.get("timeline_items") or []
            if len(items) > max_of("timeline"):
                _to_cards(comp, _as_cards(items, tag_key="date"))
                notes.append(f"{cid}: timeline with {len(items)} items -> card_grid ({comp['content_data']['card_layout']})")
        elif kind == "flow":
            steps = data.get("flow_steps") or []
            if len(steps) > max_of("flow"):
                notes.append(f"{cid}: flow with {len(steps)} nodes is over its capacity ({max_of('flow')}); kept as a flow")
        elif kind == "table":
            kpis = _metric_table_to_kpis(comp)
            if kpis:
                out.append(kpis)
                notes.append(f"{cid}: 2-column metric table of one entity -> kpi_row ({kpis['count']} tiles); "
                             "the brief's table switched because the metrics read better as tiles")
                continue
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
    """Prompt text for the generator: how to lay components out, numbers from capacity.yaml."""
    k, lay = capacity()["kpi_row"], capacity()["layout"]
    lo, hi = lay["hero_number_px"]
    g0, g1 = lay["grid_gap_px"]
    r0, r1 = lay["table_row_px"]
    return "\n".join([
        f"- KPI tiles: at most {k['per_row'][1]} per row, each at least {lay['kpi_tile_min_w']}px wide; "
        f"more metrics -> rows of equal tiles (w as %: 2 per row 49%, 3 per row 32%).",
        f"- One number the headline rests on: a hero tile, number {lo}-{hi}px; "
        f"{lay['paired_cards']} compared metrics: {lay['paired_cards']} equal cards side by side.",
        f"- Card grids: equal widths per row, gaps {g0}-{g1}px; never a lone narrow card beside a wide one.",
        f"- Tables: at most {lay['table_cols_half']} columns in a half-width card (more -> give the table "
        f"the full width); body rows {r0}-{r1}px.",
        f"- A takeaway card beside a chart or table takes {lay['side_card_w'][0]}-{lay['side_card_w'][1]} "
        f"of the width; the evidence takes the rest.",
        f"- Two-column slides: {' or '.join(lay['split'])}, the evidence side wider.",
        "- Everything ends inside the slide padding; the slide's main band takes the spare height.",
    ])
