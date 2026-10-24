"""Typed planner output: each component's content is an object, not JSON inside a string.

The planner plans with `PlannerSlideTyped` (default since the 2026-10-15 paid check); `PLANNER_SCHEMA=string`
(env) keeps the old `PlannerSlide` (`content_data_json`). Why: gpt-5-mini under strict json_schema wrote `content_data_json` as a bare `{` or a
give-up placeholder on ~8 of ~125 planner calls (choice-plans run, 2026-10-15) — the prompt's examples show
the field as an object, the model starts one inside the string and the grammar closes the string at the first
unescaped quote. Research and the choice of this design: docs/planner-output-schema-research-2026-10-15.md.

Design: `components` is a union (JSON-schema anyOf) of one component model per kind. Each starts with
`component_id` and a `kind` const, carries only the fields its kind uses (chart_type / series_count for a
chart, columns / rows for a table, items / orientation for list kinds) and a typed `content` whose keys are
today's content_data keys, so `content_data_of` gives plan_checks / generator / tile nodes the same dict.
Optional keys are nullable (strict mode requires every key); None is dropped on the way out.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, create_model

from src.state import ChartTypeLiteral, OrientationLiteral, SlideTypeLiteral, WeightLiteral

ToneLiteral = Literal["good", "bad", "watch", ""]
LevelLiteral = Literal["low", "mid", "high"]
LineLiteral = Literal["horizontal", "vertical"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── content per kind (keys = today's content_data keys) ─────────────────────

class TitleContent(_Strict):
    title: str
    subtitle: Optional[str] = None


class TextContent(_Strict):
    """narrative / caption: one paragraph or note copied from the key_messages."""
    text: str


class KpiRowContent(_Strict):
    """One entry per tile in every list, same order."""
    kpi_labels: list[str]
    kpi_values: list[str]
    kpi_deltas: Optional[list[str]] = None
    kpi_directions: Optional[list[Literal["", "up", "down", "neutral"]]] = None
    kpi_tones: Optional[list[ToneLiteral]] = None
    kpi_icons: Optional[list[str]] = None


# a number, or the brief's own text of one ("0.34x", "₹8.2"): the chart node parses it, plan checks match it
ChartValue = Union[float, str, None]


class ChartSeries(_Strict):
    name: str
    values: list[ChartValue]


class ChartContent(_Strict):
    """chart_values for one series, chart_series for several (the chart's type is the component's chart_type)."""
    chart_title: Optional[str] = None
    chart_labels: list[str]
    chart_values: Optional[list[ChartValue]] = None
    chart_series: Optional[list[ChartSeries]] = None


class TableContent(_Strict):
    table_columns: list[str]
    table_rows: list[list[str]]


class BulletListContent(_Strict):
    bullets: list[str]


class TimelineItem(_Strict):
    date: str
    label: str
    description: Optional[str] = None


class TimelineContent(_Strict):
    direction: LineLiteral
    timeline_items: list[TimelineItem]


class FlowContent(_Strict):
    direction: LineLiteral
    flow_steps: list[str]


class ProcessArrowContent(_Strict):
    direction: LineLiteral
    process_steps: list[str]


class PyramidContent(_Strict):
    direction: Literal["up", "down"]
    pyramid_levels: list[str]


class TreeNode(_Strict):
    label: str
    children: Optional[list[TreeNode]] = None


class TreeContent(_Strict):
    layout: LineLiteral
    tree_nodes: list[TreeNode]


class Quadrants(_Strict):
    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str


class MatrixItem(_Strict):
    label: str
    x: LevelLiteral
    y: LevelLiteral


class MatrixContent(_Strict):
    x_axis: str
    y_axis: str
    quadrants: Optional[Quadrants] = None
    matrix_items: list[MatrixItem]


class Card(_Strict):
    """tag / body / bullets only when the key_messages give them."""
    title: str
    tag: Optional[str] = None
    body: Optional[str] = None
    bullets: Optional[list[str]] = None
    tone: Optional[ToneLiteral] = None
    key_phrase: Optional[str] = None
    icon: Optional[str] = None


class CardGridContent(_Strict):
    """matrix layout: columns and rows name the grid, cards in row order (one per row x column)."""
    card_layout: Literal["grid", "steps", "matrix"]
    cards: list[Card]
    focus_card: Optional[int] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[str]] = None


class Layer(_Strict):
    title: str
    items: list[str]


class LayerNode(_Strict):
    label: str
    detail: Optional[str] = None


class LayerLink(_Strict):
    source: str
    target: str
    label: Optional[str] = None


class LayerContent(_Strict):
    """Free-form diagram, one of two shapes: stacked layers (top first), or nodes with links between them
    (by label) around an optional centre node. description = what the picture shows."""
    description: Optional[str] = None
    layers: Optional[list[Layer]] = None
    center: Optional[str] = None
    nodes: Optional[list[LayerNode]] = None
    connections: Optional[list[LayerLink]] = None


CONTENT_BY_KIND: dict[str, type[_Strict]] = {
    "title": TitleContent, "narrative": TextContent, "caption": TextContent,
    "kpi_row": KpiRowContent, "chart": ChartContent, "table": TableContent,
    "bullet_list": BulletListContent, "timeline": TimelineContent, "flow": FlowContent,
    "process_arrow": ProcessArrowContent, "pyramid": PyramidContent, "tree": TreeContent,
    "matrix": MatrixContent, "card_grid": CardGridContent, "layer": LayerContent,
}

# ── one component model per kind ────────────────────────────────────────────

# repeated in all 15 component models, so no descriptions: the system prompt explains each field
_ID = (str, ...)
_COUNT = (int, Field(default=1, ge=1, le=20))
_ITEMS = (int, Field(default=0, ge=0))
_TAIL = {
    "content_summary": (str, ""),
    "design_hint": (str, ""),
    "weight": (WeightLiteral, "peer"),
}
# fields of today's PlannerComponent each kind keeps (the rest are always empty for it)
_KIND_FIELDS: dict[str, dict[str, Any]] = {
    "chart": {"chart_type": (ChartTypeLiteral, ...), "series_count": (int, Field(default=1, ge=0))},
    "table": {"columns": (int, Field(default=0, ge=0)), "rows": (int, Field(default=0, ge=0))},
    "bullet_list": {"items": _ITEMS}, "pyramid": {"items": _ITEMS}, "card_grid": {"items": _ITEMS},
    "timeline": {"items": _ITEMS, "orientation": (OrientationLiteral, "")},
    "flow": {"items": _ITEMS, "orientation": (OrientationLiteral, "")},
    "process_arrow": {"items": _ITEMS, "orientation": (OrientationLiteral, "")},
    "tree": {"items": _ITEMS, "orientation": (OrientationLiteral, "")},
}


def _component_name(kind: str) -> str:
    return "".join(p.capitalize() for p in kind.split("_")) + "Component"


COMPONENT_BY_KIND: dict[str, type[BaseModel]] = {
    kind: create_model(
        _component_name(kind), __config__=ConfigDict(extra="forbid"),
        component_id=_ID, kind=(Literal[kind], ...), **_KIND_FIELDS.get(kind, {}),
        count=_COUNT, content=(content, ...), **_TAIL,
    )
    for kind, content in CONTENT_BY_KIND.items()
}

TypedComponent = Union[tuple(COMPONENT_BY_KIND.values())]  # type: ignore[valid-type]


def _trim(node: Any) -> Any:
    """A schema without `title` / `default` keywords: every key is required in strict mode, so a default only
    costs prompt tokens (about a third of the schema). Property names are kept (a property may be called title)."""
    if isinstance(node, list):
        return [_trim(v) for v in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        if key in ("title", "default") and not isinstance(value, dict):
            continue
        if key in ("properties", "$defs"):
            out[key] = {name: _trim(sub) for name, sub in value.items()}
        else:
            out[key] = _trim(value)
    return out


class PlannerSlideTyped(BaseModel):
    """Plan for a single slide (typed content)."""

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:  # what the openai SDK sends
        return _trim(super().model_json_schema(*args, **kwargs))

    slide_type: SlideTypeLiteral = Field(
        description="cover | content | data | section_break | closing (see the system prompt)."
    )
    components: list[Annotated[TypedComponent, Field()]] = Field(  # type: ignore[valid-type]
        min_length=1,
        description="Components this slide contains, each with a unique component_id, its kind and its own "
                    "content. Never merge data across components."
    )
    layout_hint: str = Field(
        description="Freeform layout INTENT: which regions carry the most weight and how the components relate "
                    "(a priority statement, not pixel dimensions)."
    )


# ── adapter: typed content <-> today's content_data ─────────────────────────

def content_data_of(component: BaseModel) -> dict[str, Any]:
    """The component's content as today's content_data dict (None keys dropped; a chart's type copied in,
    as `_settle_chart_type` expects)."""
    data = component.content.model_dump(exclude_none=True)  # type: ignore[attr-defined]
    chart_type = getattr(component, "chart_type", "")
    if chart_type:
        data = {"chart_type": chart_type, **data}
    return data


def content_from_data(kind: str, data: dict[str, Any]) -> _Strict:
    """A saved content_data dict as the kind's typed content (raises ValidationError when it does not fit).
    The reverse of `content_data_of`, for the round-trip test over saved plans."""
    data = {k: v for k, v in data.items() if not (kind == "chart" and k == "chart_type")}
    return CONTENT_BY_KIND[kind].model_validate(data)
