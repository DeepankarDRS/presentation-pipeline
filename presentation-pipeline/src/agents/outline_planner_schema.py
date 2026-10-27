"""Pydantic models for the outline planner's structured output.

The outline planner produces a rich per-slide skeleton (header, key_messages — or, with
OUTLINE_ITEMS=on, items of a kind + text — narrative_role) but NOT slide_type, component-level details,
or content_data JSON. Those are the slide_component_planner's job.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class _OutlineHeader(BaseModel):
    """The slide header and story fields, shared by both outline routes."""

    slide_index: int = Field(description="Zero-based position in the deck.")
    label: str = Field(
        default="",
        description="Kicker shown above the headline: 2-4 words naming the slide's "
                    "place in the deck, e.g. 'EXECUTIVE SUMMARY', 'PLATFORM DEEP-DIVE · 01'. "
                    "Use the request's own label when it gives one. Empty on the cover.",
    )
    slide_title: str = Field(
        description="The slide's headline, shown on the slide. When the request gives "
                    "this slide a headline, copy it exactly, word for word; a chart or "
                    "table title is not a headline. Otherwise write one claim (not a topic) "
                    "that says what the data shows, at most ~12 words. E.g. 'Enterprise carries the quarter while SMB "
                    "churn rises', not 'Segment Performance'."
    )
    subtitle: str = Field(
        default="",
        description="One short line under the headline that adds what it does not say: "
                    "the period or base of comparison, or one more fact from this slide. "
                    "Never a list of the figures the slide already shows, never a "
                    "description of the slide ('Performance overview'). Empty on the cover "
                    "or when there is nothing to add.",
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


class OutlineSlide(_OutlineHeader):
    """Rich outline entry for one slide — enough context for slide_component_planner."""

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


ItemKind = Literal["metric", "series", "records", "steps", "point", "visual", "note"]


class OutlineItem(BaseModel):
    """One piece of a slide's content and what kind of content it is (OUTLINE_ITEMS=on,
    docs/outline-items-design-2026-10-27.md). The slide component planner chooses the component."""

    kind: ItemKind = Field(
        description="metric = one number with its label and change; series = one measure over labels "
                    "(periods or entities); records = one table, rows split by ' | '; steps = an ordered "
                    "sequence, dated events too; point = a qualitative statement or named items; visual = the "
                    "brief's own drawing direction; note = a caveat, data note or formula the brief states."
    )
    text: str = Field(description="The content, copied exactly from the request: same numbers, units, formats, "
                                  "names and placeholders.")


class OutlineItemsSlide(_OutlineHeader):
    """One slide of the outline whose content is items (OUTLINE_ITEMS=on)."""

    items: list[OutlineItem] = Field(
        min_length=1,
        description="The content this slide carries, in order: every figure, series and table row it needs, "
                    "copied exactly from the request. Hero/intro slides: 1-2 items.",
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


class OutlinePlannerItemsOutput(BaseModel):
    """Complete deck outline, slides with items (OUTLINE_ITEMS=on)."""

    deck_title: str = Field(description="The deck's overall title shown on the cover slide.")
    core_hook: str = Field(
        description="One narrative tension sentence tying the entire deck together. "
                    "Must have tension or contrast. "
                    "E.g. 'Revenue is growing, but customer acquisition costs are growing faster.'"
    )
    slides: list[OutlineItemsSlide] = Field(
        min_length=1,
        description="One outline entry per slide, in presentation order.",
    )
