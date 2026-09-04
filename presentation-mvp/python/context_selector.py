"""Deterministic context selection: SlideIR -> GenerationContract.

Reads the YAML knowledge base and assembles only the pieces the requested slide
needs — a small, targeted contract (component-specific nodes, attributes,
examples, layout, theme) rather than one giant reference prompt.

Knowledge base: core/{document,nodes,attributes,validation}, theme/palettes,
components/{text,shape,chart,table,list}, layouts/{title-content,kpi-row,
two-column,chart-table}. Phase A nodes always; Chart/Table/List nodes pulled in
when the SlideIR asks for a chart / table / bullet_list.
"""

from __future__ import annotations

import functools
import sys
from typing import Any

import yaml

import config
import theme as theme_lib
from models import ComponentKind, GenerationContract, SlideIR

_K = config.KNOWLEDGE_DIR


@functools.lru_cache(maxsize=None)
def _load_yaml(relpath: str) -> dict[str, Any]:
    path = _K / relpath
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_example(name: str) -> str:
    path = config.EXAMPLES_DIR / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


# ── attribute assembly ──────────────────────────────────────────────────────
# A curated subset of the common box model — enough for Phase A layouts without
# drowning the prompt. Full list lives in core/attributes.yaml.
_COMMON_BOX_ATTRS = [
    "w", "h", "grow", "padding", "margin", "backgroundColor",
    "borderRadius", "border.color", "border.width", "alignSelf",
]
_STACK_EXTRA = ["gap", "alignItems", "justifyContent"]


def _node_attributes(nodes_yaml: dict[str, Any]) -> dict[str, list[str]]:
    """node name -> its node-specific attributes, from core/nodes.yaml."""
    out: dict[str, list[str]] = {}
    for section in ("layout", "content", "phase_b", "phase_c", "phase_d", "post_mvp"):
        for name, meta in (nodes_yaml.get(section) or {}).items():
            if not isinstance(meta, dict):
                continue
            out[name] = list(meta.get("node_attributes") or [])
    # inline tags carry their own small typed attribute sets
    for name, meta in (nodes_yaml.get("inline") or {}).items():
        attrs = meta.get("attributes")
        if isinstance(attrs, dict):
            out[name] = list(attrs.keys())
        elif isinstance(attrs, list):
            out[name] = [a for a in attrs if a != "none"]
        else:
            out[name] = []
    return out


# ── layout + example selection ──────────────────────────────────────────────
def _select_layout(kinds: list[ComponentKind]) -> tuple[str, list[str]]:
    """Return (layout_pattern_text, notes)."""
    notes: list[str] = []
    has_chart = ComponentKind.chart in kinds
    has_table = ComponentKind.table in kinds
    has_narr = ComponentKind.narrative in kinds

    if ComponentKind.timeline in kinds:
        pick = "layouts/timeline-roadmap.yaml"
    elif ComponentKind.layer in kinds:
        pick = "layouts/diagram-annotated.yaml"
    elif has_chart and has_table:
        pick = "layouts/chart-table.yaml"
    elif (has_chart or has_table) and has_narr:
        pick = "layouts/two-column.yaml"
    elif ComponentKind.kpi_row in kinds:
        pick = "layouts/kpi-row.yaml"
    else:
        pick = "layouts/title-content.yaml"

    layout = _load_yaml(pick)
    if not layout:
        layout = _load_yaml("layouts/title-content.yaml")
    return _render_layout(layout), notes


def _render_layout(layout_yaml: dict[str, Any]) -> str:
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
    if layout_yaml.get("verified_example"):
        parts.append("Verified example:\n" + str(layout_yaml["verified_example"]).strip())
    return "\n\n".join(parts)


def _select_examples(kinds: list[ComponentKind]) -> list[str]:
    picks: list[str] = []
    if ComponentKind.timeline in kinds:
        picks.append("timeline-slide.xml")
    if ComponentKind.flow in kinds:
        picks.append("flow-slide.xml")
    if ComponentKind.layer in kinds:
        picks.append("drawing-slide.xml")
    if ComponentKind.chart in kinds and ComponentKind.table in kinds:
        picks.append("mixed-slide.xml")
    elif ComponentKind.chart in kinds:
        picks.append("chart-slide.xml")
    elif ComponentKind.table in kinds:
        picks.append("table-slide.xml")
    if ComponentKind.kpi_row in kinds:
        picks.append("kpi-slide.xml")
    if not picks and (ComponentKind.narrative in kinds or ComponentKind.title in kinds):
        picks.append("text-slide.xml")
    if not picks:
        picks.append("minimal-slide.xml")

    seen: set[str] = set()
    out: list[str] = []
    for name in picks:
        if name in seen:
            continue
        seen.add(name)
        xml = _load_example(name)
        if xml:
            out.append(xml)
    return out[:2]


# ── node selection ──────────────────────────────────────────────────────────
# canonical emit order for nodes beyond the Phase A allowlist
_EXTRA_NODE_ORDER = [
    "Chart", "ChartSeries", "ChartDataPoint", "Ul", "Ol", "Li",
    "Table", "Col", "Tr", "Td",
    # Phase D
    "Layer", "Line", "Arrow", "Svg",
    "A", "U", "S", "Sub", "Sup",
    "Timeline", "TimelineItem",
    "Flow", "FlowNode", "FlowConnection",
    # Post-MVP
    "Matrix", "MatrixAxes", "MatrixQuadrants", "MatrixItem",
    "Tree", "TreeItem",
    "ProcessArrow", "ProcessArrowStep",
    "Pyramid", "PyramidLevel",
]


def _select_nodes(kinds: list[ComponentKind], phase_a: list[str]) -> list[str]:
    # Shape is in the base set: layouts use it for the accent rule, and it is a
    # cheap Phase A node.
    needed = {"Slide", "Theme", "VStack", "Text", "Shape"}

    if ComponentKind.kpi_row in kinds:
        needed.update({"HStack", "Span"})
    if ComponentKind.chart in kinds:
        needed.update({"HStack", "Chart", "ChartSeries", "ChartDataPoint"})
    if ComponentKind.table in kinds:
        needed.update({"HStack", "Table", "Col", "Tr", "Td"})
    if ComponentKind.bullet_list in kinds:
        needed.update({"Ul", "Li"})
    if {ComponentKind.chart, ComponentKind.table} & set(kinds) and \
            ComponentKind.narrative in kinds:
        needed.add("HStack")

    # Phase D
    if ComponentKind.timeline in kinds:
        needed.update({"Timeline", "TimelineItem"})
    if ComponentKind.flow in kinds:
        needed.update({"Flow", "FlowNode", "FlowConnection"})
    if ComponentKind.layer in kinds:
        needed.update({"Layer", "Line", "Arrow", "Svg"})

    # Post-MVP
    if ComponentKind.tree in kinds:
        needed.update({"Tree", "TreeItem"})
    if ComponentKind.matrix in kinds:
        needed.update({"Matrix", "MatrixAxes", "MatrixQuadrants", "MatrixItem"})
    if ComponentKind.process_arrow in kinds:
        needed.update({"ProcessArrow", "ProcessArrowStep"})
    if ComponentKind.pyramid in kinds:
        needed.update({"Pyramid", "PyramidLevel"})

    # Always keep the inline set available — it is cheap and the model expects it.
    needed.update({"B", "I", "Span", "Mark", "A", "U", "S", "Sub", "Sup"})

    ordered = [n for n in phase_a if n in needed]
    ordered += [n for n in _EXTRA_NODE_ORDER if n in needed and n not in ordered]
    return ordered


# ── public entry point ─────────────────────────────────────────────────────
def select_context(ir: SlideIR) -> GenerationContract:
    kinds = ir.component_kinds

    nodes_yaml = _load_yaml("core/nodes.yaml")
    validation = _load_yaml("core/validation.yaml")
    text_yaml = _load_yaml("components/text.yaml")
    comp_yaml = {
        ComponentKind.chart: _load_yaml("components/chart.yaml"),
        ComponentKind.table: _load_yaml("components/table.yaml"),
        ComponentKind.bullet_list: _load_yaml("components/list.yaml"),
        ComponentKind.kpi_row: _load_yaml("components/shape.yaml"),
        ComponentKind.timeline: _load_yaml("components/timeline.yaml"),
        ComponentKind.flow: _load_yaml("components/flow.yaml"),
        ComponentKind.layer: _load_yaml("components/drawing.yaml"),
        ComponentKind.tree: _load_yaml("components/tree.yaml"),
        ComponentKind.matrix: _load_yaml("components/matrix.yaml"),
        ComponentKind.process_arrow: _load_yaml("components/process-arrow.yaml"),
        ComponentKind.pyramid: _load_yaml("components/pyramid.yaml"),
    }

    phase_a = nodes_yaml.get("phase_a_allowlist") or [
        "Slide", "Theme", "VStack", "HStack", "Text", "B", "I", "Span", "Mark", "Shape",
    ]
    allowed_nodes = _select_nodes(kinds, phase_a)

    node_attrs = _node_attributes(nodes_yaml)
    allowed_attributes: dict[str, list[str]] = {}
    for node in allowed_nodes:
        if node in ("Slide", "Theme"):
            continue
        base = list(node_attrs.get(node, []))
        _NO_BOX = ("B", "I", "Span", "Mark", "A", "U", "S", "Sub", "Sup",
                   "ChartSeries", "ChartDataPoint",
                   "Table", "Col", "Tr", "Td", "Li",
                   "TimelineItem", "FlowNode", "FlowConnection",
                   "MatrixAxes", "MatrixQuadrants", "MatrixItem",
                   "TreeItem", "ProcessArrowStep", "PyramidLevel",
                   "Line", "Arrow")
        _SIZE_ONLY = ("Chart", "Ul", "Ol",
                      "Timeline", "Flow", "Matrix", "Tree",
                      "ProcessArrow", "Pyramid")
        if node in ("VStack", "HStack"):
            attrs = _STACK_EXTRA + _COMMON_BOX_ATTRS
        elif node in _NO_BOX:
            attrs = base  # own attributes only
        elif node in _SIZE_ONLY:
            attrs = base + ["w", "h", "grow", "padding", "margin"]
        else:  # Text, Shape
            attrs = base + _COMMON_BOX_ATTRS
        # de-dup, keep order
        seen: set[str] = set()
        allowed_attributes[node] = [a for a in attrs if not (a in seen or seen.add(a))]

    forbidden_tags = _clean_list(validation.get("forbidden_tags"))
    forbidden_attributes = _clean_list(validation.get("forbidden_attributes"))

    # Theme: slide IR name > project theme.yaml > library default.
    cfg_name, cfg_overrides = config.load_theme_config()
    resolved = theme_lib.resolve(ir.theme or cfg_name, cfg_overrides)
    for w in resolved.warnings:
        print(f"theme: {w}", file=sys.stderr)
    theme_element = theme_lib.theme_element(resolved)

    layout_pattern, layout_notes = _select_layout(kinds)
    examples = _select_examples(kinds)

    notes: list[str] = []
    for row in (validation.get("translations") or []):
        notes.append(f"NOT {row.get('wrong')}  ->  {row.get('right')}")
    for rule in (validation.get("semantic_rules") or []):
        notes.append(rule)
    for pitfall in (text_yaml.get("pitfalls") or []):
        notes.append(pitfall)
    if ComponentKind.kpi_row in kinds and text_yaml.get("kpi_numeral_note"):
        notes.append(str(text_yaml["kpi_numeral_note"]).strip())

    # Component-specific pitfalls / structure hints for whatever this slide needs.
    for kind in kinds:
        cy = comp_yaml.get(kind)
        if not cy:
            continue
        struct = cy.get("structure")
        if struct:
            notes.append(f"{kind.value} structure:\n" + str(struct).strip())
        for pitfall in (cy.get("pitfalls") or []):
            notes.append(pitfall)

    notes.extend(layout_notes)

    # Theme-specific guidance.
    notes.append(
        f"Theme palette: {resolved.name} ({resolved.mode}). Emit the <Theme> "
        "element above verbatim; use $tokens for every color."
    )
    if ComponentKind.chart in kinds:
        notes.append(
            "Chart chartColors must be LITERAL hex (no $tokens). Use this palette's "
            f"sequence: chartColors='{resolved.chart_colors_json}' "
            "(take as many leading entries as you have series)."
        )
        if resolved.is_dark:
            notes.append(
                "DARK theme: POM v10.3.0 draws chart axis text in black. Wrap the "
                '<Chart> in <VStack backgroundColor="$chartSurface" padding="16" '
                'borderRadius="12"> so the axis labels stay readable. Any caption '
                'text inside that wrapper uses color="$chartInk".'
            )
    if ComponentKind.table in kinds:
        notes.append(
            "EVERY <Td> needs an explicit backgroundColor AND color — unstyled "
            "cells render with PowerPoint's default white table style. Header row: "
            'backgroundColor="$surfaceAlt" color="$textMain" bold="true". Body rows: '
            'backgroundColor="$surface", color="$textMuted" for labels / "$textMain" '
            'for values. Use cellBorder.color="$border".'
        )

    return GenerationContract(
        allowed_nodes=allowed_nodes,
        allowed_attributes=allowed_attributes,
        forbidden_tags=forbidden_tags,
        forbidden_attributes=forbidden_attributes,
        theme_element=theme_element,
        theme_name=resolved.name,
        theme_mode=resolved.mode,
        chart_colors=resolved.chart_colors,
        layout_pattern=layout_pattern,
        examples=examples,
        notes=notes,
    )


def _clean_list(values: Any) -> list[str]:
    """Drop the pseudo-entries in validation.yaml (e.g. 'span_lowercase')."""
    out: list[str] = []
    for v in values or []:
        s = str(v)
        if "_lowercase" in s:
            s = s.split("_lowercase")[0]
        if "_on_" in s:  # src_on_non_image
            s = s.split("_on_")[0]
        s = s.strip().strip('"')
        if s and s not in out:
            out.append(s)
    return out
