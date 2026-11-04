"""The composition nodes switched on by POM_NODES (left-blocks spec §2.5), behind one interface for the validator,
generator and context builder: chart (charts.py), timeline / process_arrow / flow (sequences.py), kpi_row /
card_grid (tile_groups.py), table (tables.py), bullet_list (bullets.py)."""

from __future__ import annotations

from typing import Any

from src.compiler.nodes import bullets, charts, sequences, tables, tile_groups

# plan-level content_data keys a drawn kind no longer needs in the prompt
PLAN_KEYS = {"chart": ("chart_",), "timeline": ("timeline_items",), "process_arrow": ("process_steps",),
             "flow": ("flow_steps",), "kpi_row": ("kpi_",), "card_grid": ("card", "per_row", "focus_card"),
             "table": ("table_",), "bullet_list": ("bullets",)}

# kind -> module for the one-kind nodes after chart, the sequences and the tile groups (each: on, TAG, components,
# expand, node_lines, prompt_line, tag_attributes)
MORE = {"table": tables, "bullet_list": bullets}


def kinds_on() -> list[str]:
    return (["chart"] if charts.on() else []) + sequences.kinds_on() + tile_groups.kinds_on() \
        + [k for k, m in MORE.items() if m.on()]


def tag(kind: str) -> str:
    if kind in tile_groups.KINDS:
        return tile_groups.node(kind)["tag"]
    if kind in MORE:
        return MORE[kind].TAG
    return charts.TAG if kind == "chart" else sequences.TAGS[kind]


def drawn(plan: dict | None, kind: str) -> dict[str, dict]:
    """The components of a switched-on kind that code draws (those with an id)."""
    if kind not in kinds_on():
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


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    out = {"xml": xml, "issues": [], "ok": True, "components": {}}
    fns = ((charts.expand,) if charts.on() else ()) + ((sequences.expand,) if sequences.kinds_on() else ()) \
        + ((tile_groups.expand,) if tile_groups.kinds_on() else ()) + tuple(m.expand for m in MORE.values() if m.on())
    for fn in fns:
        r = fn(out["xml"], plan)
        out = {"xml": r["xml"], "issues": out["issues"] + r["issues"], "ok": out["ok"] and r["ok"],
               "components": {**out["components"], **r["components"]}}
    return out


def node_lines() -> str:
    return "\n\n".join(([charts.node_lines()] if charts.on() else []) + ([sequences.node_lines()] if sequences.kinds_on() else [])
                       + ([tile_groups.node_lines()] if tile_groups.kinds_on() else [])
                       + [m.node_lines() for m in MORE.values() if m.on()])


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
