"""Pydantic models for the outline planner's structured output.

The outline planner produces a rich per-slide skeleton (header, key_messages,
narrative_role, visual_emphasis) but NOT slide_type, component-level details,
or content_data JSON. Those are the slide_component_planner's job.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OutlineSlide(BaseModel):
    """Rich outline entry for one slide — enough context for slide_component_planner."""

    slide_index: int = Field(description="Zero-based position in the deck.")
    label: str = Field(
        default="",
        description="Kicker shown above the headline: 2-4 words naming the slide's "
                    "place in the deck, e.g. 'EXECUTIVE SUMMARY', 'PLATFORM DEEP-DIVE · 01'. "
                    "Use the request's own label when it gives one. Empty on the cover.",
    )
    slide_title: str = Field(
        description="The slide's headline, shown on the slide. When the request gives "
                    "this slide a headline or title, copy it exactly, word for word. "
                    "Otherwise write one claim (not a topic) that names its subject, "
                    "at most ~14 words. E.g. 'Enterprise carries the quarter while SMB "
                    "churn rises', not 'Segment Performance'."
    )
    subtitle: str = Field(
        default="",
        description="One line under the headline that carries the evidence: 2-4 key "
                    "figures from this slide's content, copied exactly as the request "
                    "writes them, e.g. '<figure> · <figure> · <figure>'. Not a description "
                    "of the slide ('Performance overview'). Empty on the cover or when the "
                    "slide has no figures.",
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
        description="The points this slide makes and the content it carries, in order. "
                    "The slide component planner reads each message to choose a component "
                    "and copies its values, so every figure, series and table row the slide "
                    "needs must appear here exactly as the request writes it (same numbers, "
                    "units, formats, names and placeholders).\n"
                    "\n"
                    "The SHAPE of a message tells the planner which component fits:\n"
                    "  • one metric → '<metric>: <value> (<change>)'\n"
                    "  • a series → '<measure> by <period>: <label> <value>, <label> <value>, …'\n"
                    "  • a record set → '<entity>: <measure> <value>, <measure> <value> | "
                    "<entity>: …'\n"
                    "  • a qualitative point → a plain sentence\n"
                    "  • ordered steps → '<step> → <step> → <step>'\n"
                    "\n"
                    "Rules:\n"
                    "  - Specific, not vague summaries ('Shows strong growth' is not a message).\n"
                    "  - Figures come only from the request, the supplied content or the "
                    "clarification answers. When a point needs a figure they do not give, "
                    "state the point without a number. Never make up a number, and never "
                    "write placeholders like '[estimate]' or '[TBD]'.\n"
                    "  - Count per slide: one message per data group the slide carries, plus "
                    "the narrative the amount_of_text setting asks for.\n"
                    "  - Hero/intro slides: 1-2 messages.",
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
                    "E.g. 'Revenue is growing, but customer acquisition costs are growing faster.'"
    )
    slides: list[OutlineSlide] = Field(
        min_length=1,
        description="One rich outline entry per slide, in presentation order.",
    )
