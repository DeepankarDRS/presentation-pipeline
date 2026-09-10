"""Pydantic models for the outline planner's structured output.

The outline planner produces a rich per-slide skeleton (key_messages, data_anchors,
narrative_role, visual_emphasis) but NOT slide_type, component-level details, or
content_data JSON. Those are the slide_component_planner's job.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OutlineSlide(BaseModel):
    """Rich outline entry for one slide — enough context for slide_component_planner."""

    slide_index: int = Field(description="Zero-based position in the deck.")
    slide_title: str = Field(
        description="Short headline for the slide (≤8 words). "
                    "E.g. 'Revenue Grew 40% — At What Cost?'"
    )
    section: str = Field(
        default="",
        description="Optional grouping label, e.g. 'Problem', 'Solution', 'Deep Dive', "
                    "'Recommendation'. Leave empty if no sections apply.",
    )

    narrative_role: str = Field(
        description="1-2 sentences: how this slide advances or supports the core_hook. "
                    "E.g. 'Establishes the revenue growth context, setting up the CAC "
                    "tension introduced in the core hook.'"
    )

    key_messages: list[str] = Field(
        min_length=1,
        description="2–4 specific, concrete statements this slide must land. These become "
                    "bullets, KPI labels, or narrative paragraphs in the final slide. "
                    "MUST be specific and falsifiable — not vague summaries. "
                    "BAD: 'Shows strong growth.' "
                    "GOOD: 'Revenue grew 40% YoY to $42.8M in FY2025.' "
                    "Use supplied data verbatim when available; otherwise invent a plausible "
                    "concrete number. Never write literal placeholder syntax like '[estimate]' "
                    "or '[TBD]' here — that tag belongs only in data_anchors. Do not restate "
                    "a data_anchor verbatim; write the full sentence it supports instead.",
    )

    data_anchors: list[str] = Field(
        default_factory=list,
        description="Specific numbers, facts, or named comparisons to feature prominently. "
                    "Source directly from supplied_content when available; otherwise mark with "
                    "'[estimate]' suffix. E.g. ['$42.8M ARR (+40% YoY)', 'CAC $3,200 (+18% QoQ)']."
                    "Empty list is fine for purely qualitative slides.",
    )

    visual_emphasis: str = Field(
        description="One short phrase describing the slide's visual weight — NOT a layout. "
                    "Examples: 'side-by-side comparison', 'one dominant number', "
                    "'timeline progression', 'data table with callout'. The slide component "
                    "planner uses this to pick components and density."
    )


class OutlinePlannerOutput(BaseModel):
    """Complete deck outline from the outline planner."""

    deck_title: str = Field(
        description="The deck's overall title shown on the cover slide."
    )
    core_hook: str = Field(
        description="One narrative tension sentence tying the entire deck together. "
                    "Must have tension or contrast. "
                    "E.g. 'Revenue grew 40% YoY but customer acquisition costs are rising faster than revenue.'"
    )
    slides: list[OutlineSlide] = Field(
        min_length=1,
        description="One rich outline entry per slide, in presentation order.",
    )
