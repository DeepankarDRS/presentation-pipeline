"""Pydantic models for the elicitor agent's structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ElicitationQuestion(BaseModel):
    key: str = Field(description="Machine-readable slug, e.g. 'key_metric' or 'competitor_names'.")
    question: str = Field(description="Human-readable question text shown to the user.")
    type: Literal["single_choice", "multi_choice", "free_text", "numeric"] = Field(
        default="free_text",
        description="UI widget type: single_choice=radio, multi_choice=checkboxes, "
                    "free_text=open input, numeric=number input.",
    )
    options: list[str] = Field(
        default_factory=list,
        description="Suggested answers for single_choice or multi_choice. Empty for free_text/numeric.",
    )
    required: bool = Field(
        default=True,
        description="Whether the frontend must enforce an answer before proceeding.",
    )
    default: str = Field(
        default="",
        description="Pre-selected default value. Empty = no default.",
    )
    hint: str = Field(
        default="",
        description="Short tooltip or helper text shown below the question.",
    )


class ElicitorOutput(BaseModel):
    is_sufficient: bool = Field(
        description="True if the request + deck_settings together have enough specific "
                    "content information to produce a high-quality deck without clarification."
    )
    reasoning: str = Field(
        description="One sentence explaining why the request is or is not sufficient. "
                    "E.g. 'The request mentions Q3 results but provides no actual numbers or metrics.'"
    )
    questions: list[ElicitationQuestion] = Field(
        default_factory=list,
        description="Clarifying questions to ask the user. Empty when is_sufficient=True. "
                    "Maximum 5 questions. Focus only on CONTENT gaps — audience/tone are "
                    "already captured by the deck settings form.",
    )
