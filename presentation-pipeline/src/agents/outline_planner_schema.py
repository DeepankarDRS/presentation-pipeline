"""Pydantic models for the outline planner's structured output.

The outline planner produces a rich per-slide skeleton (key_messages,
narrative_role, visual_emphasis) but NOT slide_type, component-level details,
or content_data JSON. Those are the slide_component_planner's job.
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
        description="The ABSOLUTE source of truth for this slide's content. Every "
                    "message must be specific and data-dense — a concrete claim the "
                    "slide component planner can route directly to the right component "
                    "(KPI tile, chart series, table row, bullet, or narrative paragraph).\n"
                    "\n"
                    "Each key_message carries SEMANTIC intent — it is NOT just text for "
                    "a bullet list. The slide component planner reads the shape of the "
                    "message to decide which component type fits:\n"
                    "  • A standalone metric → KPI tile: 'ARR reached $42.8M (+18% QoQ)'\n"
                    "  • A time-series or comparison → chart: 'Revenue by quarter: "
                    "Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M'\n"
                    "  • A multi-column record set → table: 'Enterprise $28.1M +22% | "
                    "Mid-Market $10.4M +14% | SMB $4.3M +8%'\n"
                    "  • A qualitative insight → narrative or bullet: 'Self-serve "
                    "onboarding could cut CAC payback from 14 to 10 months'\n"
                    "\n"
                    "Rules:\n"
                    "  - MUST be specific and falsifiable — not vague summaries.\n"
                    "    BAD: 'Shows strong growth.'\n"
                    "    GOOD: 'Revenue grew 40% YoY to $42.8M in FY2025.'\n"
                    "  - Use supplied data VERBATIM when available.\n"
                    "  - When no data is supplied: invent a plausible concrete number. "
                    "Never write placeholder syntax like '[estimate]', '[TBD]', or "
                    "'[value]'.\n"
                    "  - For dashboard/metrics slides: provide 4-6 quantitative messages "
                    "(one per metric tile or data point).\n"
                    "  - Count per slide is governed by amount_of_text setting:\n"
                    "    minimal → 1, concise → 2, detailed → 3-4, extensive → 4-6\n"
                    "  - Hero/intro slides: 1-2 messages max regardless of setting.",
    )

    visual_emphasis: str = Field(
        description="One short phrase describing the slide's conceptual focus — "
                    "NOT a spatial layout.\n"
                    "\n"
                    "Do NOT dictate spatial layouts (e.g. 'left column', 'top row', "
                    "'right panel'). Provide only the conceptual focus.\n"
                    "\n"
                    "GOOD: 'dashboard of metrics', 'timeline progression', "
                    "'side-by-side comparison', 'one dominant number', "
                    "'data table with callout'\n"
                    "BAD: 'KPI row on top, chart in the left column, table on the right'"
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
