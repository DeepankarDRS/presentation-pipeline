"""Structured LLM outputs for planning v2.

Field order matters: OpenAI writes structured output in schema order, so the reasoning fields
come first and the model thinks before it commits (audience → argument → gaps → slides;
reading → components).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IntentLiteral = Literal[
    "cover", "agenda", "section_divider", "executive_summary", "big_statement", "kpi_dashboard",
    "trend", "ranking", "breakdown", "comparison", "detailed_table", "deep_dive", "process",
    "timeline", "roadmap", "framework", "case_study", "risks", "recommendation", "ask", "closing",
    "appendix",
]
DesignKindLiteral = Literal[
    "kpi_row", "table", "chart", "bullet_list", "narrative", "timeline", "process_arrow", "flow",
    "pyramid", "matrix", "tree",
]
RoleLiteral = Literal["strip", "hero", "support", "readout", "minor"]


class SetAside(BaseModel):
    block_id: str = Field(description="Id of a block that is not shown, e.g. 'L12'.")
    reason: str = Field(description="Why: 'instruction to the writer', 'style direction', "
                                    "'duplicate of T3', 'moved to speaker notes', ...")


# ── Storyline (one call per deck) ───────────────────────────────────────────

class StorySlide(BaseModel):
    slide_index: int = Field(description="0-based position in the deck.")
    intent: IntentLiteral = Field(description="What kind of slide this is.")
    label: str = Field(description="Short kicker above the headline, e.g. 'PLATFORM DEEP-DIVE · 01'. "
                                   "Copy it when the brief gives one. Empty for a cover.")
    headline_block: str = Field(description="Id of the block whose text IS this slide's headline when the "
                                            "brief states one (code copies it verbatim). Empty when you write "
                                            "the headline yourself.")
    headline: str = Field(description="The claim this slide proves — a conclusion, not a topic. For a "
                                      "cover: the deck title.")
    subtitle: str = Field(description="One line of context (period, scope, source). Copy when the brief gives one.")
    block_ids: list[str] = Field(description="Every block whose content appears on this slide.")
    so_what: str = Field(description="One sentence: what the audience should take from this slide.")
    emphasis: list[str] = Field(description="At most 2 things to highlight, each naming its value "
                                            "(e.g. 'ROAS 6.35x'). Usually 0 or 1.")
    parallel_group: str = Field(description="Same name for slides that repeat one structure on purpose "
                                            "(e.g. 'platform_deep_dive'); empty otherwise.")
    notes: str = Field(description="Speaker notes: what to say, and detail that does not fit on the slide.")


class Storyline(BaseModel):
    audience_and_use: str = Field(description="Who reads this deck and how: presented live (sparse, big type) "
                                              "or read as a pre-read (dense).")
    deck_argument: str = Field(description="One sentence: what the audience must believe or do after the deck.")
    gaps: list[str] = Field(description="Data the brief refers to but does not contain (e.g. an attached "
                                        "sheet that is not attached). Never fill a gap with invented numbers.")
    style_directives: list[str] = Field(description="The brief's instructions about look and brand "
                                                    "(background, colours, tone, number format), copied.")
    deck_title: str = Field(description="The deck's title.")
    slides: list[StorySlide] = Field(description="One entry per slide, in order.")
    set_aside: list[SetAside] = Field(description="Blocks with numbers that no slide shows, with the reason.")


# ── Slide design (one call per slide) ───────────────────────────────────────

class Kpi(BaseModel):
    label: str
    value: str = Field(description="Copied exactly as written in the block, e.g. '₹1.32 Cr', '6.35x'.")
    note: str = Field(default="", description="Short context line copied from the blocks, e.g. '▼ 18.4% vs May'.")


class Series(BaseModel):
    name: str
    values: list[str] = Field(description="One value per label, copied from the blocks (numbers only, no units).")


class Item(BaseModel):
    label: str = Field(description="timeline: the date or period ('Jul '26'); other kinds: the step or level "
                                   "name, 1-3 words.")
    detail: str = Field(default="", description="timeline only: the event text. process_arrow / flow / "
                                                "pyramid / tree / matrix draw labels only — leave empty and put "
                                                "details in a table or bullets.")


class DesignComponent(BaseModel):
    id: str = Field(description="Short unique slug, e.g. 'kpis', 'category_table', 'readout'.")
    kind: DesignKindLiteral
    role: RoleLiteral = Field(description="strip = row of tiles; hero = the focal point (max 1 per slide); "
                                          "support; readout = the takeaway panel; minor.")
    block_ids: list[str] = Field(description="The blocks this component shows.")
    title: str = Field(default="", description="Card title, copied from the brief when it gives one.")
    kpis: list[Kpi] = Field(default_factory=list, description="kpi_row only.")
    columns: list[str] = Field(default_factory=list,
                               description="table: ONLY for a table you build from text blocks — its header. "
                                           "Leave empty for a parsed table block (it is shown whole).")
    rows: list[list[str]] = Field(default_factory=list,
                                  description="table: ONLY when you build it from text blocks. Leave empty "
                                              "for a parsed table block — code fills it.")
    chart_type: str = Field(default="", description="chart: bar, column, line, area, pie, doughnut.")
    labels: list[str] = Field(default_factory=list, description="chart: category labels, ONLY when not "
                                                                "bound to a parsed chart block.")
    series: list[Series] = Field(default_factory=list, description="chart: ONLY when not bound to a parsed "
                                                                   "chart block.")
    bullets: list[str] = Field(default_factory=list, description="bullet_list: one line each.")
    text: str = Field(default="", description="narrative: 1-3 sentences.")
    items: list[Item] = Field(default_factory=list,
                              description="timeline / process_arrow / flow / pyramid / matrix / tree.")
    emphasis: str = Field(default="", description="Only for one of the slide's emphasis items: what to "
                                                  "highlight in this component. Usually empty.")


class SlideDesign(BaseModel):
    reading: str = Field(description="Think first: what must this slide prove, which block is the proof "
                                     "(the focal point), how much content there is, how it splits into "
                                     "components.")
    components: list[DesignComponent] = Field(description="The slide's components. The header (label, "
                                                          "headline, subtitle) is already decided — no title "
                                                          "component.")
    layout: str = Field(description="1-2 sentences: the focal point and the arrangement "
                                    "(top strip, main band, side, bottom readout).")
    not_shown: list[SetAside] = Field(default_factory=list,
                                      description="Assigned blocks deliberately left off the slide "
                                                  "(they go to speaker notes), with the reason.")
