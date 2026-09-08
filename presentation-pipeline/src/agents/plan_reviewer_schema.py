"""Pydantic models for the plan reviewer agent's structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlanReviewIssue(BaseModel):
    severity: Literal["high", "medium", "low"] = Field(
        description="high = plan should be revised before generation; "
                    "medium = noticeable quality gap; "
                    "low = minor improvement opportunity."
    )
    slide_index: int | None = Field(
        default=None,
        description="Which slide has the issue. None = deck-level issue.",
    )
    type: Literal[
        "narrative_gap",
        "density_low",
        "layout_repeat",
        "component_mismatch",
        "content_weak",
        "missing_data",
    ] = Field(
        description="narrative_gap: slide doesn't support the core_hook. "
                    "density_low: too few components for the stated density. "
                    "layout_repeat: adjacent slides with same layout_pattern (after variety enforcement). "
                    "component_mismatch: wrong component kind for the data type. "
                    "content_weak: content_data values are generic/placeholder. "
                    "missing_data: required content_data keys absent for a component.",
    )
    description: str = Field(description="Specific description of the issue.")
    suggestion: str = Field(description="Concrete suggestion to fix it.")


class PlanReviewerOutput(BaseModel):
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall confidence that the assembled plan will produce a high-quality deck. "
                    "0.0 = very low confidence (many high issues), 1.0 = excellent plan.",
    )
    approved: bool = Field(
        description="True if confidence_score >= 0.70 AND no high-severity issues. "
                    "False does NOT block generation — it triggers a re-plan attempt or "
                    "logs issues for downstream monitoring.",
    )
    summary: str = Field(
        description="1-2 sentence overall assessment. "
                    "E.g. 'Strong narrative arc with 3 data slides. Slide 4 content_data "
                    "is placeholder — recommend adding real numbers before generation.'"
    )
    issues: list[PlanReviewIssue] = Field(
        default_factory=list,
        description="All identified issues, ranked high → medium → low.",
    )
