"""Context builder agent — assembles knowledge base into a generation contract.

Reads YAML knowledge base and selects only the nodes, attributes, examples,
and notes relevant to THIS slide's component plan. No phase gating — all POM
nodes available, selection is purely component-driven from the SlidePlan.

Reads:  slide_plans, theme_name
Writes: contract, theme_element, resolved_theme
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any

import yaml

from src.state import ComponentPlan, PresentationState, SlidePlan

logger = logging.getLogger(__name__)

_MVP_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "presentation-mvp"
_KNOWLEDGE_DIR = _MVP_ROOT / "pom-knowledge"
_EXAMPLES_DIR = _KNOWLEDGE_DIR / "examples"

# ── Component kind → POM node mapping ────────────────────────────────────────

_KIND_TO_NODES: dict[str, list[str]] = {
    "title":         [],
    "narrative":     [],
    "caption":       [],
    "kpi_row":       ["HStack", "Span"],
    "bullet_list":   ["Ul", "Li"],
    "chart":         ["HStack", "Chart", "ChartSeries", "ChartDataPoint"],
    "table":         ["HStack", "Table", "Col", "Tr", "Td"],
    "timeline":      ["Timeline", "TimelineItem"],
    "flow":          ["Flow", "FlowNode", "FlowConnection"],
    "layer":         ["Layer", "Line", "Arrow", "Svg"],
    "tree":          ["Tree", "TreeItem"],
    "matrix":        ["Matrix", "MatrixAxes", "MatrixQuadrants", "MatrixItem"],
    "process_arrow": ["ProcessArrow", "ProcessArrowStep"],
    "pyramid":       ["Pyramid", "PyramidLevel"],
}

_KIND_TO_COMPONENT_FILE: dict[str, str] = {
    "kpi_row":       "components/shape.yaml",
    "bullet_list":   "components/list.yaml",
    "chart":         "components/chart.yaml",
    "table":         "components/table.yaml",
    "timeline":      "components/timeline.yaml",
    "flow":          "components/flow.yaml",
    "layer":         "components/drawing.yaml",
    "tree":          "components/tree.yaml",
    "matrix":        "components/matrix.yaml",
    "process_arrow": "components/process-arrow.yaml",
    "pyramid":       "components/pyramid.yaml",
}

_KIND_TO_LAYOUT: dict[str, str] = {
    "timeline": "layouts/timeline-roadmap.yaml",
    "layer":    "layouts/diagram-annotated.yaml",
}

_KIND_TO_EXAMPLE: dict[str, str] = {
    "timeline":    "timeline-slide.xml",
    "flow":        "flow-slide.xml",
    "layer":       "drawing-slide.xml",
    "chart":       "chart-slide.xml",
    "table":       "table-slide.xml",
    "kpi_row":     "kpi-slide.xml",
    "bullet_list": "text-slide.xml",
}

_BASE_NODES = ["Slide", "Theme", "VStack", "Text", "Shape"]
_INLINE_NODES = ["B", "I", "Span", "Mark", "A", "U", "S", "Sub", "Sup"]

_COMMON_BOX_ATTRS = [
    "w", "h", "grow", "padding", "margin", "backgroundColor",
    "borderRadius", "border.color", "border.width", "alignSelf",
]
_STACK_ATTRS = ["gap", "alignItems", "justifyContent", "flexWrap"]

_NO_BOX_NODES = frozenset([
    "B", "I", "Span", "Mark", "A", "U", "S", "Sub", "Sup",
    "ChartSeries", "ChartDataPoint",
    "Table", "Col", "Tr", "Td", "Li",
    "TimelineItem", "FlowNode", "FlowConnection",
    "MatrixAxes", "MatrixQuadrants", "MatrixItem",
    "TreeItem", "ProcessArrowStep", "PyramidLevel",
    "Line", "Arrow",
])

_SIZE_ONLY_NODES = frozenset([
    "Chart", "Ul", "Ol",
    "Timeline", "Flow", "Matrix", "Tree",
    "ProcessArrow", "Pyramid",
])


@functools.lru_cache(maxsize=32)
def _load_yaml(relpath: str) -> dict[str, Any]:
    path = _KNOWLEDGE_DIR / relpath
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_example(name: str) -> str:
    path = _EXAMPLES_DIR / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _compress_example(xml: str, max_lines: int = 25) -> str:
    """Compress a full XML example to a skeleton with <!-- ... --> comments."""
    lines = xml.split("\n")
    if len(lines) <= max_lines:
        return xml
    keep: list[str] = []
    skip_count = 0
    prev_tag = ""
    for line in lines:
        stripped = line.strip()
        tag = stripped.split("<")[-1].split(" ")[0].split(">")[0].rstrip("/") if "<" in stripped else ""
        if tag == prev_tag and skip_count < 3:
            skip_count += 1
            continue
        if skip_count > 0:
            indent = len(line) - len(line.lstrip())
            keep.append(" " * indent + f"<!-- ... {skip_count} more {prev_tag} entries ... -->")
            skip_count = 0
        keep.append(line)
        prev_tag = tag
    if skip_count > 0:
        keep.append(f"    <!-- ... {skip_count} more entries ... -->")
    return "\n".join(keep)


# ── Node selection ───────────────────────────────────────────────────────────

def _select_nodes(kinds: list[str]) -> list[str]:
    """Select POM nodes needed for the given component kinds."""
    needed = set(_BASE_NODES)
    for kind in kinds:
        extra = _KIND_TO_NODES.get(kind, [])
        needed.update(extra)
        if kind in ("chart", "table", "kpi_row"):
            needed.add("HStack")
    needed.update(_INLINE_NODES)

    order = _BASE_NODES + ["HStack"] + [
        "Chart", "ChartSeries", "ChartDataPoint", "Ul", "Ol", "Li",
        "Table", "Col", "Tr", "Td",
        "Layer", "Line", "Arrow", "Svg",
        "Timeline", "TimelineItem",
        "Flow", "FlowNode", "FlowConnection",
        "Matrix", "MatrixAxes", "MatrixQuadrants", "MatrixItem",
        "Tree", "TreeItem",
        "ProcessArrow", "ProcessArrowStep",
        "Pyramid", "PyramidLevel",
    ] + _INLINE_NODES
    seen: set[str] = set()
    result: list[str] = []
    for n in order:
        if n in needed and n not in seen:
            result.append(n)
            seen.add(n)
    return result


# ── Attribute assembly ───────────────────────────────────────────────────────

def _build_node_attributes(nodes_yaml: dict) -> dict[str, list[str]]:
    """node name -> node-specific attributes from nodes.yaml."""
    out: dict[str, list[str]] = {}
    for section in ("layout", "content", "phase_b", "phase_c", "phase_d", "post_mvp"):
        for name, meta in (nodes_yaml.get(section) or {}).items():
            if not isinstance(meta, dict):
                continue
            out[name] = list(meta.get("node_attributes") or [])
    for name, meta in (nodes_yaml.get("inline") or {}).items():
        attrs = meta.get("attributes")
        if isinstance(attrs, dict):
            out[name] = list(attrs.keys())
        elif isinstance(attrs, list):
            out[name] = [a for a in attrs if a != "none"]
        else:
            out[name] = []
    return out


def _select_attributes(allowed_nodes: list[str], nodes_yaml: dict) -> dict[str, list[str]]:
    """Build per-node attribute lists for only the nodes we selected."""
    node_attrs = _build_node_attributes(nodes_yaml)
    result: dict[str, list[str]] = {}
    for node in allowed_nodes:
        if node in ("Slide", "Theme"):
            continue
        base = list(node_attrs.get(node, []))
        if node in ("VStack", "HStack"):
            attrs = _STACK_ATTRS + _COMMON_BOX_ATTRS
        elif node in _NO_BOX_NODES:
            attrs = base
        elif node in _SIZE_ONLY_NODES:
            attrs = base + ["w", "h", "grow", "padding", "margin"]
        else:
            attrs = base + _COMMON_BOX_ATTRS
        seen: set[str] = set()
        result[node] = [a for a in attrs if not (a in seen or seen.add(a))]  # type: ignore[func-returns-value]
    return result


# ── Notes selection ──────────────────────────────────────────────────────────

def _select_notes(kinds: list[str], validation: dict, text_yaml: dict,
                  component_yamls: dict[str, dict], theme_info: dict) -> list[str]:
    """Select only notes relevant to the components in this slide."""
    notes: list[str] = []

    for row in (validation.get("translations") or []):
        notes.append(f"NOT {row.get('wrong')}  ->  {row.get('right')}")

    for rule in (validation.get("semantic_rules") or []):
        notes.append(rule)

    for pitfall in (text_yaml.get("pitfalls") or []):
        notes.append(pitfall)

    if "kpi_row" in kinds and text_yaml.get("kpi_numeral_note"):
        notes.append(str(text_yaml["kpi_numeral_note"]).strip())

    for kind in kinds:
        cy = component_yamls.get(kind)
        if not cy:
            continue
        struct = cy.get("structure")
        if struct:
            notes.append(f"{kind} structure:\n{str(struct).strip()}")
        for pitfall in (cy.get("pitfalls") or []):
            notes.append(pitfall)

    theme_name = theme_info.get("name", "")
    theme_mode = theme_info.get("mode", "light")
    if theme_name:
        notes.append(
            f"Theme palette: {theme_name} ({theme_mode}). Emit the <Theme> "
            "element above verbatim; use $tokens for every color."
        )

    if "chart" in kinds:
        chart_colors = theme_info.get("chart_colors_json", "")
        notes.append(
            "Chart chartColors must be LITERAL hex (no $tokens). Use: "
            f"chartColors='{chart_colors}'"
        )
        if theme_info.get("is_dark"):
            notes.append(
                "DARK theme: POM v10.3.0 draws chart axis text in black. Wrap "
                '<Chart> in <VStack backgroundColor="$chartSurface" padding="16" '
                'borderRadius="12"> so axis labels stay readable.'
            )

    if "table" in kinds:
        notes.append(
            "EVERY <Td> needs explicit backgroundColor AND color. Unstyled "
            "cells render with PowerPoint's default white table style."
        )

    return notes


# ── Layout selection ─────────────────────────────────────────────────────────

def _select_layout(kinds: list[str]) -> str:
    """Pick a layout pattern YAML and render it as text."""
    has_chart = "chart" in kinds
    has_table = "table" in kinds
    has_narr = "narrative" in kinds

    for kind in kinds:
        if kind in _KIND_TO_LAYOUT:
            pick = _KIND_TO_LAYOUT[kind]
            break
    else:
        if has_chart and has_table:
            pick = "layouts/chart-table.yaml"
        elif (has_chart or has_table) and has_narr:
            pick = "layouts/two-column.yaml"
        elif "kpi_row" in kinds:
            pick = "layouts/kpi-row.yaml"
        else:
            pick = "layouts/title-content.yaml"

    layout = _load_yaml(pick)
    if not layout:
        layout = _load_yaml("layouts/title-content.yaml")
    return _render_layout(layout)


def _render_layout(layout_yaml: dict) -> str:
    if not layout_yaml:
        return ""
    parts: list[str] = []
    name = (layout_yaml.get("meta") or {}).get("name") or "layout"
    parts.append(f"Pattern: {name}")
    if layout_yaml.get("structure"):
        parts.append(str(layout_yaml["structure"]).strip())
    rules = layout_yaml.get("rules") or []
    if rules:
        parts.append("Rules:\n" + "\n".join(f"  - {r}" for r in rules))
    return "\n\n".join(parts)


# ── Example selection ────────────────────────────────────────────────────────

def _select_example(kinds: list[str], compress: bool = True) -> str:
    """Pick at most 1 example, compressed."""
    for kind in kinds:
        name = _KIND_TO_EXAMPLE.get(kind)
        if name:
            xml = _load_example(name)
            if xml:
                return _compress_example(xml) if compress else xml

    xml = _load_example("minimal-slide.xml")
    return _compress_example(xml) if compress and xml else xml


# ── Forbidden lists ──────────────────────────────────────────────────────────

def _clean_list(values: Any) -> list[str]:
    out: list[str] = []
    for v in values or []:
        s = str(v)
        if "_lowercase" in s:
            s = s.split("_lowercase")[0]
        if "_on_" in s:
            s = s.split("_on_")[0]
        s = s.strip().strip('"')
        if s and s not in out:
            out.append(s)
    return out


# ── Default theme (when theme.py is not yet ported) ──────────────────────────

_DEFAULT_THEME = {
    "name": "corporate-slate",
    "mode": "light",
    "is_dark": False,
    "chart_colors": ["2563EB", "0EA5E9", "10B981", "F59E0B", "EF4444", "8B5CF6"],
    "chart_colors_json": '["2563EB","0EA5E9","10B981","F59E0B","EF4444","8B5CF6"]',
    "element": '<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" '
               'accentAlt="0EA5E9" positive="15803D" negative="DC2626" '
               'warning="B45309" textMain="16202E" textMuted="55627A" '
               'border="E2E8F0" chartSurface="FFFFFF" chartInk="334155" />',
}


def _resolve_theme(theme_name: str) -> dict[str, Any]:
    """Resolve theme — uses default for now, will port theme.py later."""
    if not theme_name or theme_name == "corporate-slate":
        return _DEFAULT_THEME

    palettes = _load_yaml("theme/palettes.yaml")
    palette_data = (palettes.get("palettes") or {}).get(theme_name)
    if not palette_data:
        logger.warning(f"theme '{theme_name}' not found, using default")
        return _DEFAULT_THEME

    tokens = palette_data.get("tokens", {})
    mode = palette_data.get("mode", "light")
    chart_colors = palette_data.get("chartColors", _DEFAULT_THEME["chart_colors"])

    token_attrs = " ".join(f'{k}="{v}"' for k, v in tokens.items())
    element = f"<Theme {token_attrs} />"

    return {
        "name": theme_name,
        "mode": mode,
        "is_dark": mode == "dark",
        "chart_colors": chart_colors,
        "chart_colors_json": str(chart_colors).replace("'", '"'),
        "element": element,
    }


# ── Public entry point ───────────────────────────────────────────────────────

def build_contract(slide_plan: SlidePlan, theme_name: str) -> dict[str, Any]:
    """Build a generation contract for one slide from its plan.

    Returns a dict with: allowed_nodes, allowed_attributes, forbidden_tags,
    forbidden_attributes, theme_element, theme_name, theme_mode, notes,
    example, layout_pattern, density_tier.
    """
    kinds = [c.get("kind", "") for c in slide_plan.get("components", [])]
    density = slide_plan.get("density", "normal")

    nodes_yaml = _load_yaml("core/nodes.yaml")
    validation = _load_yaml("core/validation.yaml")
    text_yaml = _load_yaml("components/text.yaml")

    component_yamls = {}
    for kind in kinds:
        path = _KIND_TO_COMPONENT_FILE.get(kind)
        if path:
            component_yamls[kind] = _load_yaml(path)

    allowed_nodes = _select_nodes(kinds)
    allowed_attributes = _select_attributes(allowed_nodes, nodes_yaml)
    forbidden_tags = _clean_list(validation.get("forbidden_tags"))
    forbidden_attributes = _clean_list(validation.get("forbidden_attributes"))

    theme = _resolve_theme(theme_name)
    notes = _select_notes(kinds, validation, text_yaml, component_yamls, theme)

    compress = density != "tight_fit"
    example = _select_example(kinds, compress=compress)

    layout_pattern = _select_layout(kinds)

    if density in ("sparse",):
        tier = "minimal"
    elif density in ("normal", "dense"):
        tier = "standard"
    else:
        tier = "dense"

    return {
        "allowed_nodes": allowed_nodes,
        "allowed_attributes": allowed_attributes,
        "forbidden_tags": forbidden_tags,
        "forbidden_attributes": forbidden_attributes,
        "theme_element": theme["element"],
        "theme_name": theme["name"],
        "theme_mode": theme["mode"],
        "chart_colors": theme["chart_colors"],
        "notes": notes,
        "example": example,
        "layout_pattern": layout_pattern,
        "density_tier": tier,
    }


def context_builder_node(state: PresentationState) -> dict[str, Any]:
    """LangGraph node: build contract from slide_plans[0]."""
    slide_plans = state.get("slide_plans", [])
    theme_name = state.get("theme_name", "")

    if not slide_plans:
        logger.info("context_builder: no slide plans, building default contract (title + narrative)")
        slide_plans = [SlidePlan(
            slide_index=0,
            components=[
                ComponentPlan(kind="title", count=1),
                ComponentPlan(kind="narrative", count=1),
                ComponentPlan(kind="bullet_list", count=1),
            ],
            density="normal",
            font_tier="standard",
            layout_hint="Title at top, narrative and bullets below",
        )]

    plan = slide_plans[0]
    contract = build_contract(plan, theme_name)

    logger.info(
        f"context_builder: {len(contract['allowed_nodes'])} nodes, "
        f"{len(contract['notes'])} notes, tier={contract['density_tier']}"
    )

    return {
        "contract": contract,
        "theme_element": contract["theme_element"],
        "resolved_theme": {
            "name": contract["theme_name"],
            "mode": contract["theme_mode"],
        },
    }
