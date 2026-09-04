"""Pydantic models for the planner's structured LLM output.

Used with ChatOpenAI.with_structured_output(PlannerOutput) to get
guaranteed-valid JSON from the LLM via OpenAI's json_schema response format.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ComponentKindLiteral = Literal[
    "title", "narrative", "caption", "kpi_row", "bullet_list",
    "chart", "table", "timeline", "flow", "layer",
    "tree", "matrix", "process_arrow", "pyramid",
]

DensityLiteral = Literal["sparse", "normal", "dense", "tight_fit"]
FontTierLiteral = Literal["display", "standard", "compact", "micro"]


class PlannerComponent(BaseModel):
    """One component the slide should contain."""
    kind: ComponentKindLiteral = Field(
        description="Component type from the vocabulary."
    )
    count: int = Field(
        default=1, ge=1, le=20,
        description="How many instances (e.g. 4 KPI tiles, 3 chart series)."
    )
    chart_type: str = Field(
        default="",
        description="bar, line, pie, donut, area. Only when kind=chart."
    )
    series_count: int = Field(
        default=0, ge=0,
        description="Number of data series in the chart. Only when kind=chart."
    )
    columns: int = Field(
        default=0, ge=0,
        description="Column count. Only when kind=table."
    )
    rows: int = Field(
        default=0, ge=0,
        description="Data row count (excluding header). Only when kind=table."
    )
    items: int = Field(
        default=0, ge=0,
        description="Item count for bullet_list, timeline, flow, process_arrow, pyramid."
    )
    content_summary: str = Field(
        default="",
        description="Compact description of what this component shows. "
                    "Used by the generator for context."
    )


class PlannerSlide(BaseModel):
    """Plan for a single slide."""
    components: list[PlannerComponent] = Field(
        min_length=1,
        description="Components this slide contains, in visual order top-to-bottom."
    )
    density: DensityLiteral = Field(
        description="How packed the slide is. "
                    "sparse=few elements with large fonts. "
                    "normal=typical business slide. "
                    "dense=many elements, smaller fonts. "
                    "tight_fit=maximum packing, micro fonts, minimal gaps."
    )
    font_tier: FontTierLiteral = Field(
        description="Font size tier. "
                    "display=title 36+, body 22+. "
                    "standard=title 28-32, body 18-20. "
                    "compact=title 22-26, body 14-16. "
                    "micro=title 18-20, body 11-13."
    )
    layout_hint: str = Field(
        description="Freeform natural language description of how components "
                    "should be arranged. E.g. 'KPIs in a row across top, "
                    "chart and table side by side below, footnote at bottom'."
    )
    content_data_json: str = Field(
        default="{}",
        description="JSON string of compact content for the generator. Use "
                    "supplied_content values verbatim when available; derive "
                    "plausible values for anything not supplied. Keys should "
                    "match component needs (e.g. kpi_values, chart_data, "
                    "table_rows). Must be valid JSON object string."
    )


class PlannerOutput(BaseModel):
    """Complete plan output from the planner agent."""
    slides: list[PlannerSlide] = Field(
        min_length=1,
        description="One plan per slide. Single-slide requests have exactly one entry."
    )
