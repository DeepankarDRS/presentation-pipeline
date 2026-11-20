"""Pydantic models for the critic's structured LLM output.

Used with ChatOpenAI.with_structured_output(CriticOutput) to get
guaranteed-valid JSON from the LLM via OpenAI's json_schema response format.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.state import CriticTypeLiteral
from src.state import SeverityLiteral as CriticSeverityLiteral


class CriticIssue(BaseModel):
    """One issue found by the critic."""
    severity: CriticSeverityLiteral = Field(
        description="high = must fix (triggers retry), "
                    "medium = should fix (warning), "
                    "low = minor (informational)."
    )
    type: CriticTypeLiteral = Field(
        description="Which checklist item this issue falls under."
    )
    description: str = Field(
        description="What is wrong — be specific about the element or value."
    )
    fix: str = Field(
        description="How to fix this issue in the XML."
    )


class CriticOutput(BaseModel):
    """Complete critic review output."""
    issues: list[CriticIssue] = Field(
        default_factory=list,
        description="All issues found. Empty list means the XML passed all checks."
    )


class ComponentVerdict(BaseModel):
    """The critic's verdict on one numbered component, or on the slide as a whole (id "slide")."""
    id: str = Field(description='The component id from the COMPONENTS list, or "slide" for the whole slide.')
    verdict: Literal["ok", "issue"]
    severity: Literal["none", "low", "medium", "high"] = Field(
        description="none for ok; high = broken / unreadable / fails the headline; medium = a clear quality problem; "
                    "low = polish.")
    check: Literal["message", "hierarchy", "visible_defect", "colour", "variant_fit", "balance", "completeness",
                   "none"] = Field(description="The checklist item; none for ok.")
    what_i_see: str = Field(description="ok: one line of evidence. issue: what is wrong, where, and why it hurts. "
                                        "No XML.")
    owner: Literal["slide", "code_defect"] = Field(
        description="slide: the slide's own choices cause it. code_defect: a code-drawn component draws itself "
                    "wrongly although its tag looks reasonable.")
    better_variant: str = Field(default="", description="variant_fit only: the catalogue variant that would fit, "
                                                         "else empty.")


class VisualCriticOutput(BaseModel):
    """The visual critic's review of one slide (2026-11-20): observations first, then a verdict per component."""
    observations: str = Field(description="2-5 sentences on what the slide shows and how it reads, written before "
                                          "the verdicts.")
    verdicts: list[ComponentVerdict] = Field(description="One per numbered component plus one with id \"slide\".")
    regenerate: bool = Field(description="true only when the plan is wrong for the message (wrong component kinds, "
                                         "far more content than one slide shows readably).")
    regenerate_reason: str = Field(default="", description="Why, when regenerate is true.")
