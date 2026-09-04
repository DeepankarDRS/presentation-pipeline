"""Pydantic models for the critic's structured LLM output.

Used with ChatOpenAI.with_structured_output(CriticOutput) to get
guaranteed-valid JSON from the LLM via OpenAI's json_schema response format.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CriticSeverityLiteral = Literal["high", "medium", "low"]
CriticTypeLiteral = Literal["completeness", "fidelity", "structure", "theme"]


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
