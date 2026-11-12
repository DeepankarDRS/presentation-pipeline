"""Typed planner output: each component's content is an object, not JSON inside a string.

The planner plans with `PlannerSlideTyped` (default since the 2026-10-15 paid check); `PLANNER_SCHEMA=string`
(env) keeps the old `PlannerSlide` (`content_data_json`). Why: gpt-5-mini under strict json_schema wrote `content_data_json` as a bare `{` or a
give-up placeholder on ~8 of ~125 planner calls (choice-plans run, 2026-10-15) — the prompt's examples show
the field as an object, the model starts one inside the string and the grammar closes the string at the first
unescaped quote. Research and the choice of this design: docs/planner-output-schema-research-2026-10-15.md.

Design: `components` is a union (JSON-schema anyOf) of one component model per kind. Each starts with
`component_id` and a `kind` const, carries only the fields its kind uses (chart_type for a chart; counts and orientation are read from the content by code) and a typed `content` whose keys are
today's content_data keys, so `content_data_of` gives plan_checks / generator / tile nodes the same dict.
Optional keys are nullable (strict mode requires every key); None is dropped on the way out.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, create_model

from src.state import ChartTypeLiteral, SlideTypeLiteral, WeightLiteral

ToneLiteral = Literal["good", "bad", "watch", ""]
LevelLiteral = Literal["low", "mid", "high"]
LineLiteral = Literal["horizontal", "vertical"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── content per kind (keys = today's content_data keys) ─────────────────────

class TitleContent(_Strict):
    """The slide's headline as the brief gives it."""
    title: str
    subtitle: Optional[str] = None


class TextContent(_Strict):
    """narrative / caption: one paragraph or note copied from the key_messages."""
    text: str


class KpiRowContent(_Strict):
    """One entry per tile in every list, in the brief's order. Labels and values word for word."""
    kpi_labels: list[str]
    kpi_values: list[str] = Field(description='The figure only ("$42.8M", "38%"), never a sentence.')
    kpi_deltas: Optional[list[str]] = Field(default=None, description='Change or short note per tile, "" when none.')
    kpi_directions: Optional[list[Literal["", "up", "down", "neutral"]]] = None
    kpi_tones: list[ToneLiteral] = Field(
        default_factory=list,
        description='What each number means for the slide\'s story, not which way it moved: good (a win or fix), bad (a loss, leak or risk), '
                    'watch (mixed, near a limit), "" (neutral context, a target, or no judgement in the brief).')
    kpi_icons: list[str] = Field(
        default_factory=list,
        description='One generic Lucide icon name per tile for what it measures (wallet, users, clock), '
                    'or "" on every tile when no symbol fits. No brand logos.')


# a number, or the brief's own text of one ("0.34x", "₹8.2"): the chart node parses it, plan checks match it
ChartValue = Union[float, str, None]


class ChartSeries(_Strict):
    name: str
    values: list[ChartValue]


class ChartContent(_Strict):
    """chart_values for one series, chart_series for several (the chart's type is the component's chart_type).
    All series share one unit; values copied from the brief."""
    chart_title: Optional[str] = None
    chart_labels: list[str]
    chart_values: Optional[list[ChartValue]] = None
    chart_series: Optional[list[ChartSeries]] = None


class TableContent(_Strict):
    """Entities as rows, measures as columns; cells copied from the brief."""
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
    """tag / body / bullets only when the brief gives them (or a written body, see the system prompt)."""
    title: str
    tag: Optional[str] = Field(default=None, description="A time window, phase or step label from the brief.")
    body: Optional[str] = None
    bullets: Optional[list[str]] = Field(default=None, description="The brief's items that belong to this card.")
    tone: ToneLiteral = Field(default="", description='As kpi_tones: good / bad / watch / "" (neutral).')
    key_phrase: Optional[str] = Field(
        default=None, description="The few words of body the audience should catch, copied exactly; null when none.")
    icon: str = Field(default="", description='Generic Lucide icon name for the card, or "" on every card.')


class CardGridContent(_Strict):
    """grid = parallel items; steps = an ordered sequence joined by arrows; matrix = named rows x columns of words
    (columns and rows name the grid, cards in row order, one per row x column)."""
    card_layout: Literal["grid", "steps", "matrix"]
    cards: list[Card]
    focus_card: Optional[int] = Field(
        default=None, description="Index of the ONE card the headline or brief singles out; null when the cards are "
                                  "equal, and on steps when the focus is the last step.")
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

# repeated in all 15 component models, so no descriptions: the system prompt explains each field once.
# Order = decide, then fill: weight and design_hint come before content. Counts (count / items / rows / columns /
# series_count) and orientation are not asked: code reads them from the content
# (`slide_component_planner.derive_counts`), so they never disagree with it.
_ID = (str, ...)
_HEAD = {
    "weight": (WeightLiteral, "peer"),
    "design_hint": (str, ""),
    "content_summary": (str, ""),
}
_KIND_FIELDS: dict[str, dict[str, Any]] = {
    "chart": {"chart_type": (ChartTypeLiteral, ...)},
}


def _component_name(kind: str) -> str:
    return "".join(p.capitalize() for p in kind.split("_")) + "Component"


COMPONENT_BY_KIND: dict[str, type[BaseModel]] = {
    kind: create_model(
        _component_name(kind), __config__=ConfigDict(extra="forbid"),
        component_id=_ID, kind=(Literal[kind], ...), **_HEAD, **_KIND_FIELDS.get(kind, {}),
        content=(content, ...),
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
    layout_hint: str = Field(
        description="The composition, decided before the components: which component carries the most weight and "
                    "how the others relate to it, by component_id (a priority statement, no pixels)."
    )
    components: list[Annotated[TypedComponent, Field()]] = Field(  # type: ignore[valid-type]
        min_length=1,
        description="Components this slide contains, each with a unique component_id, its kind and its own "
                    "content. Never merge data across components."
    )


# ── adapter: typed content <-> today's content_data ─────────────────────────

def content_data_of(component: BaseModel) -> dict[str, Any]:
    """The component's content as today's content_data dict (None keys dropped; a chart's type copied in,
    as `_settle_chart_type` expects)."""
    # defaults (None, [], "") mean "not given": dropped, so a saved content_data round-trips unchanged
    data = component.content.model_dump(exclude_none=True, exclude_defaults=True)  # type: ignore[attr-defined]
    chart_type = getattr(component, "chart_type", "")
    if chart_type:
        data = {"chart_type": chart_type, **data}
    return data


def content_from_data(kind: str, data: dict[str, Any]) -> _Strict:
    """A saved content_data dict as the kind's typed content (raises ValidationError when it does not fit).
    The reverse of `content_data_of`, for the round-trip test over saved plans."""
    data = {k: v for k, v in data.items() if not (kind == "chart" and k == "chart_type")}
    return CONTENT_BY_KIND[kind].model_validate(data)
