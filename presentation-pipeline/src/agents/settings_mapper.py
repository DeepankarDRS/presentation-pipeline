"""DeckSettings — Gamma-style pre-generation form model and constraint mapping.

DeckSettings is what the frontend sends before outline generation. It captures
global deck preferences that shape how all slides are planned and generated:
text handling mode, density, audience, tone, theme, and slide count.

The helper functions here map DeckSettings values to the planner constraints
that flow into outline_planner and slide_component_planner prompts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Gamma-style deck settings form ─────────────────────────────────────────

class DeckSettings(BaseModel):
    # Gamma "textcontent" — how to handle existing content
    text_mode: Literal["generate", "condense", "preserve"] = Field(
        default="generate",
        description="generate = LLM invents content freely; "
                    "condense = LLM compresses supplied_content to slide-friendly length; "
                    "preserve = LLM uses supplied_content verbatim, only adds structure.",
    )

    # Gamma "amountoftext" — density target for all slides
    amount_of_text: Literal["minimal", "concise", "detailed", "extensive"] = Field(
        default="concise",
        description="minimal = 1 key message per slide (sparse); "
                    "concise = 2 messages per slide (normal); "
                    "detailed = 3-4 messages per slide (dense); "
                    "extensive = 4-6 messages per slide (tight_fit).",
    )

    # Gamma "writefor" — audience tags (multi-select)
    write_for: list[str] = Field(
        default_factory=list,
        description="Audience tags. Options: Board, C-suite, Investors, All-hands, "
                    "Sales, Engineering, General public.",
    )

    # Gamma "tone" — tone tags (multi-select)
    tone: list[str] = Field(
        default_factory=list,
        description="Tone tags. Options: Professional, Persuasive, Inspiring, "
                    "Data-driven, Conversational, Executive.",
    )

    # Theme selection — dynamic from palettes.yaml
    theme: str = Field(
        default="corporate-slate",
        description="Named palette from palettes.yaml.",
    )

    # Gamma "userprompt" — mirrored here for the form, primary value is in raw_request
    user_prompt: str = Field(
        default="",
        description="The main generation request (mirrors raw_request in state).",
    )

    # Gamma "additionalinstructions"
    additional_instructions: str = Field(
        default="",
        description="Free-text additional constraints or context for the planner.",
    )

    # Target slide count
    slide_count: Literal["1", "3-5", "6-10", "10-15", "15+"] = Field(
        default="6-10",
        description="Target number of slides.",
    )


# ── Mapping tables ──────────────────────────────────────────────────────────

TEXT_MODE_TO_PROVENANCE_RULE: dict[str, str] = {
    "generate": "llm_generates_freely",
    "condense": "llm_compresses_supplied",
    "preserve": "llm_preserves_verbatim",
}

AMOUNT_TO_DENSITY: dict[str, str] = {
    "minimal":   "sparse",
    "concise":   "normal",
    "detailed":  "dense",
    "extensive": "tight_fit",
}

AMOUNT_TO_KEY_MESSAGES_PER_SLIDE: dict[str, str] = {
    "minimal":   "1",
    "concise":   "2",
    "detailed":  "3-4",
    "extensive": "4-6",
}

SLIDE_COUNT_TO_THRESHOLD: dict[str, int] = {
    "1":     1,
    "3-5":   4,
    "6-10":  8,
    "10-15": 12,
    "15+":   16,
}


def settings_to_constraints(settings: DeckSettings) -> dict[str, Any]:
    """Convert DeckSettings to a flat dict of planner constraints."""
    return {
        "text_mode": settings.text_mode,
        "provenance_rule": TEXT_MODE_TO_PROVENANCE_RULE[settings.text_mode],
        "density": AMOUNT_TO_DENSITY[settings.amount_of_text],
        "key_messages_per_slide": AMOUNT_TO_KEY_MESSAGES_PER_SLIDE[settings.amount_of_text],
        "write_for": settings.write_for,
        "tone": settings.tone,
        "theme": settings.theme,
        "additional_instructions": settings.additional_instructions,
        "deck_min_threshold": SLIDE_COUNT_TO_THRESHOLD[settings.slide_count],
    }


def compute_provenance(
    content_data: dict[str, Any],
    supplied: dict[str, Any],
) -> dict[str, str]:
    """Tag each content_data key as 'user' (from supplied_content) or 'sample'."""
    supplied_keys = set(supplied) if supplied else set()
    return {key: ("user" if key in supplied_keys else "sample") for key in content_data}
