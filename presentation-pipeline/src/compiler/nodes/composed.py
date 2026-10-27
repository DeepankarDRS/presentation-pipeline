"""The composition nodes switched on by POM_NODES (left-blocks spec §2.5), behind one interface for the validator,
generator and context builder: chart (charts.py), timeline / process_arrow / flow (sequences.py)."""

from __future__ import annotations

from typing import Any

from src.compiler.nodes import charts, sequences

# plan-level content_data keys a drawn kind no longer needs in the prompt
PLAN_KEYS = {"chart": ("chart_",), "timeline": ("timeline_items",), "process_arrow": ("process_steps",),
             "flow": ("flow_steps",)}


def kinds_on() -> list[str]:
    return (["chart"] if charts.on() else []) + sequences.kinds_on()


def tag(kind: str) -> str:
    return charts.TAG if kind == "chart" else sequences.TAGS[kind]


def drawn(plan: dict | None, kind: str) -> dict[str, dict]:
    """The components of a switched-on kind that code draws (those with an id)."""
    if kind not in kinds_on():
        return {}
    return charts.chart_components(plan) if kind == "chart" else sequences.components(plan, kind)


def all_drawn(plan: dict | None, kind: str) -> bool:
    """Every component of the kind on this slide is drawn by code (none without an id)."""
    n = sum(c.get("kind") == kind for c in (plan or {}).get("components") or [])
    return bool(n) and len(drawn(plan, kind)) == n


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    out = {"xml": xml, "issues": [], "ok": True, "components": {}}
    for fn in ((charts.expand,) if charts.on() else ()) + ((sequences.expand,) if sequences.kinds_on() else ()):
        r = fn(out["xml"], plan)
        out = {"xml": r["xml"], "issues": out["issues"] + r["issues"], "ok": out["ok"] and r["ok"],
               "components": {**out["components"], **r["components"]}}
    return out


def node_lines() -> str:
    return "\n\n".join(([charts.node_lines()] if charts.on() else []) + ([sequences.node_lines()] if sequences.kinds_on() else []))


def prompt_line(comp: dict, headline: str = "") -> str:
    return charts.prompt_line(comp, headline) if comp["kind"] == "chart" else sequences.prompt_line(comp, headline)


def tag_attributes(kind: str) -> list[str]:
    return charts.tag_attributes() if kind == "chart" else sequences.tag_attributes(kind)
