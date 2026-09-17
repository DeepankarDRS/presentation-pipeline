"""Pydantic models for the critic's structured LLM output.

Used with ChatOpenAI.with_structured_output(CriticOutput) to get
guaranteed-valid JSON from the LLM via OpenAI's json_schema response format.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CriticSeverityLiteral = Literal["high", "medium", "low"]
CriticTypeLiteral = Literal["completeness", "fidelity", "structure", "theme", "visual"]


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


class VisualCriticIssue(BaseModel):
    """One issue found by the visual critic — includes repair context."""
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
    affected_nodes: list[str] = Field(
        default_factory=list,
        description="POM node names involved (e.g. 'Chart', 'HStack', 'Text')."
    )
    fix_xml_snippet: str = Field(
        default="",
        description="Concrete XML patch suggestion for the repairer."
    )


class VisualCriticOutput(BaseModel):
    """Complete visual critic review output — drives the repair loop."""
    issues: list[VisualCriticIssue] = Field(
        default_factory=list,
        description="All issues found. Empty list means the slide passed all checks."
    )
    overall_assessment: Literal["layout_broken", "needs_tuning", "good"] = Field(
        description="layout_broken = severe structural problems, "
                    "needs_tuning = minor fixes needed, "
                    "good = slide is acceptable."
    )
    repair_strategy: Literal["patch", "regenerate", "none"] = Field(
        description="Recommended repair approach: patch (fix in place), "
                    "regenerate (rebuild from plan), none (no repair needed)."
    )
