"""Pydantic models for the outline planner's structured output.

The outline planner produces a rich per-slide skeleton (key_messages, data_anchors,
narrative_role, layout_intent) but NOT component-level details or content_data JSON.
That is the slide_component_planner's job.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.agents.planner_schema import SlideTypeLiteral


class OutlineSlide(BaseModel):
    """Rich outline entry for one slide — enough context for slide_component_planner."""

    slide_index: int = Field(description="Zero-based position in the deck.")
    slide_title: str = Field(
        description="Short headline for the slide (≤8 words). "
                    "E.g. 'Revenue Grew 40% — At What Cost?'"
    )
    slide_type: SlideTypeLiteral = Field(
        description="cover | content | data | section_break | closing"
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
                    "Use supplied data verbatim when available.",
    )

    data_anchors: list[str] = Field(
        default_factory=list,
        description="Specific numbers, facts, or named comparisons to feature prominently. "
                    "Source directly from supplied_content when available; otherwise mark with "
                    "'[estimate]' suffix. E.g. ['$42.8M ARR (+40% YoY)', 'CAC $3,200 (+18% QoQ)']."
                    "Empty list is fine for purely qualitative slides (cover, section_break).",
    )

    layout_intent: str = Field(
        description="Plain English spatial description for the slide component planner. "
                    "Describe the visual layout without POM syntax. "
                    "E.g. 'Three-column comparison grid, one column per model, verdict column on right.' "
                    "E.g. 'Large headline number top-center, supporting context bullets below, small bar chart bottom-right.'"
    )

    suggested_components: list[str] = Field(
        default_factory=list,
        description="Soft hints for the slide component planner. Use component vocabulary: "
                    "title, narrative, caption, kpi_row, bullet_list, chart, table, timeline, "
                    "flow, layer, tree, matrix, process_arrow, pyramid. Not binding — planner may override.",
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
        description="One rich outline entry per slide, in presentation order. "
                    "First slide must be 'cover' and last must be 'closing' for decks >1 slide.",
    )
