"""Fill components from the brief, and map a v2 plan onto today's SlidePlan (code, no LLM).

Parsed tables and charts are filled by code from the brief, so their numbers are never retyped.
to_slide_plan() produces the SlidePlan the current generator reads (Test 2 feeds it through).
"""

from __future__ import annotations

import re
from typing import Any

from src.state import ComponentPlan, SlidePlan

_WEIGHT = {"hero": "hero", "strip": "peer", "support": "supporting", "readout": "supporting", "minor": "minor"}
_SLIDE_TYPE = {"cover": "cover", "section_divider": "section_break", "closing": "closing", "ask": "closing"}
_DATA_KINDS = {"kpi_row", "table", "chart"}


def _pick_columns(header: list[str], rows: list[list[str]], keep: list[str]) -> tuple[list[str], list[list[str]]]:
    """Keep the named header cells (case-insensitive, in the order given); unknown names are ignored."""
    if not keep or not header:
        return header, rows
    pos = {h.strip().lower(): i for i, h in enumerate(header)}
    idx = [pos[k.strip().lower()] for k in keep if k.strip().lower() in pos]
    if not idx:
        return header, rows
    return [header[i] for i in idx], [[r[i] if i < len(r) else "" for i in idx] for r in rows]


def fill_component(comp: dict[str, Any], blocks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """A copy of the component with parsed tables / charts filled from their blocks."""
    out = dict(comp)
    bound = [blocks[b] for b in comp.get("block_ids", []) if b in blocks]
    if comp["kind"] == "table" and not comp.get("rows"):
        tables = [b for b in bound if b["kind"] == "table"]
        if tables:
            t = tables[0]
            out["columns"], out["rows"] = _pick_columns(t["header"], t["rows"], comp.get("columns") or [])
            out["filled_from"] = t["id"]
    if comp["kind"] == "chart" and not comp.get("series"):
        charts = [b for b in bound if b["kind"] == "chart"]
        if charts:
            c = charts[0]
            out["labels"] = [p[0] for p in c["series"][0]["points"]] if c["series"] else []
            out["series"] = [{"name": s["name"], "values": [p[1] for p in s["points"]]} for s in c["series"]]
            out["chart_type"] = comp.get("chart_type") or c["chart_type"]
            out["filled_from"] = c["id"]
    return out


def shown_text(comp: dict[str, Any]) -> str:
    """Everything a filled component puts on the slide, as one string (for number checks)."""
    bits = [comp.get("title", ""), comp.get("text", "")]
    bits += [f"{k['label']} {k['value']} {k.get('note', '')}" for k in comp.get("kpis", [])]
    bits += comp.get("columns", []) + [" ".join(r) for r in comp.get("rows", [])]
    bits += comp.get("labels", []) + [f"{s['name']} {' '.join(s['values'])}" for s in comp.get("series", [])]
    bits += comp.get("bullets", []) + [f"{i['label']} {i.get('detail', '')}" for i in comp.get("items", [])]
    return " ".join(b for b in bits if b)


def _num(v: str) -> float | int | str:
    """Chart value as a number; integral values stay ints ("5" → 5, not 5.0, which reads as a new number)."""
    try:
        f = float(re.sub(r"[^\d.\-]", "", v)) if re.search(r"\d", v) else None
    except ValueError:
        return v
    if f is None:
        return v
    return int(f) if f.is_integer() and "." not in v else f


def _direction(note: str) -> str:
    if "▲" in note or note.strip().startswith("+"):
        return "up"
    if "▼" in note or note.strip().startswith(("-", "−")):
        return "down"
    return ""


def _content_data(c: dict[str, Any]) -> dict[str, Any]:
    kind = c["kind"]
    if kind == "kpi_row":
        return {"kpi_labels": [k["label"] for k in c["kpis"]], "kpi_values": [k["value"] for k in c["kpis"]],
                "kpi_deltas": [k.get("note", "") for k in c["kpis"]],
                "kpi_directions": [_direction(k.get("note", "")) for k in c["kpis"]]}
    if kind == "table":
        return {"table_columns": c.get("columns", []), "table_rows": c.get("rows", [])}
    if kind == "chart":
        series = [{"name": s["name"], "values": [_num(v) for v in s["values"]]} for s in c.get("series", [])]
        data = {"chart_type": c.get("chart_type") or "bar", "chart_title": c.get("title", ""),
                "chart_labels": c.get("labels", []), "chart_values": series[0]["values"] if series else []}
        if len(series) > 1:
            data["chart_series"] = series
        return data
    if kind == "bullet_list":
        return {"bullets": c.get("bullets", [])}
    if kind == "narrative":
        return {"text": c.get("text", "")}
    items = c.get("items", [])
    if kind == "timeline":
        return {"direction": "horizontal", "timeline_items": [{"date": i["label"], "label": i.get("detail", "")}
                                                              for i in items]}
    if kind == "process_arrow":
        return {"direction": "horizontal", "process_steps": [i["label"] for i in items]}
    if kind == "flow":
        return {"direction": "horizontal", "flow_steps": [i["label"] for i in items]}
    if kind == "pyramid":
        return {"direction": "up", "pyramid_levels": [i["label"] for i in items]}
    if kind == "tree":
        return {"layout": "vertical", "tree_nodes": [{"label": i["label"]} for i in items]}
    return {"items": [{"label": i["label"], "detail": i.get("detail", "")} for i in items]}


def _counts(c: dict[str, Any]) -> dict[str, int]:
    if c["kind"] == "kpi_row":
        return {"count": max(1, len(c.get("kpis", [])))}
    if c["kind"] == "table":
        return {"columns": len(c.get("columns", [])), "rows": len(c.get("rows", []))}
    if c["kind"] == "chart":
        return {"series_count": len(c.get("series", []))}
    if c["kind"] == "bullet_list":
        return {"items": len(c.get("bullets", []))}
    return {"items": len(c.get("items", []))} if c.get("items") else {}


def to_slide_plan(story: dict[str, Any], design: dict[str, Any]) -> SlidePlan:
    """Map a storyline entry + a filled slide design onto today's SlidePlan."""
    comps = design.get("components", [])
    is_cover = story.get("intent") in ("cover", "section_divider")
    header = ComponentPlan(
        component_id="slide_title", kind="title", count=1, weight="hero" if is_cover else "minor",
        content_summary="slide header", design_hint="",
        content_data={"title": story.get("headline", ""), "subtitle": story.get("subtitle", ""),
                      "kicker": story.get("label", "")})
    components: list[ComponentPlan] = [header]
    merged: dict[str, Any] = {}
    for c in comps:
        data = _content_data(c)
        cp = ComponentPlan(component_id=c["id"], kind=c["kind"], content_summary=c.get("title", ""),
                           content_data=data, weight=_WEIGHT.get(c.get("role", ""), "peer"),
                           design_hint=f"emphasise {c['emphasis']}" if c.get("emphasis") else "",
                           **{"count": 1, **_counts(c)})
        if c["kind"] == "chart":
            cp["chart_type"] = data["chart_type"]
        components.append(cp)
        merged.update(data)
    slide_type = _SLIDE_TYPE.get(story.get("intent", ""))
    if not slide_type:
        slide_type = "data" if any(c["kind"] in _DATA_KINDS for c in comps) else "content"
    return SlidePlan(slide_index=story["slide_index"], slide_title=story.get("headline", ""),
                     slide_type=slide_type, components=components, layout_hint=design.get("layout", ""),
                     content_data=merged, data_provenance={})
