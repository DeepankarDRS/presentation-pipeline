"""Outline planner agent — produces the deck skeleton (replaces planner.py).

Takes the enriched request (raw_request + deck_settings + elicitation_answers +
supplied_content) and produces a rich per-slide outline: slide_title, slide_type,
section, narrative_role, key_messages, data_anchors, layout_intent, suggested_components.

Does NOT produce component-level details or content_data JSON. Those are the
slide_component_planner's job.

Reads:  raw_request, deck_settings, elicitation_answers, supplied_content, theme_name
Writes: outline_plan
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.outline_planner_schema import OutlinePlannerOutput
from src.agents.settings_mapper import DeckSettings, settings_to_constraints
from src.state import PresentationState
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "outline_planner"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _get_constraints(deck_settings_dict: dict[str, Any]) -> dict[str, Any]:
    """Parse DeckSettings dict → constraints dict for prompt injection."""
    try:
        settings = DeckSettings.model_validate(deck_settings_dict)
        return settings_to_constraints(settings)
    except Exception:
        return {
            "density": "normal",
            "key_messages_per_slide": "2",
            "text_mode": "generate",
            "provenance_rule": "llm_generates_freely",
        }


def outline_planner_node(state: PresentationState) -> dict[str, Any]:
    """Plan the deck outline using an LLM with structured output."""
    logger.info("outline_planner: generating deck outline")

    deck_settings = state.get("deck_settings") or {}
    constraints = _get_constraints(deck_settings)

    target_slides = constraints.get("deck_min_threshold") or state.get("deck_min_threshold", 6)
    # Request override: if test_case specifies a slide count, honour it
    test_case = state.get("test_case") or {}
    if test_case.get("slide_count"):
        target_slides = test_case["slide_count"]

    user_msg = _jinja_env.get_template("user.j2").render(
        raw_request=state.get("raw_request", ""),
        deck_settings=deck_settings,
        constraints=constraints,
        elicitation_answers=state.get("elicitation_answers") or {},
        supplied_content=state.get("supplied_content"),
        target_slides=target_slides,
    )
    system_msg = _jinja_env.get_template("system.j2").render()

    llm = get_llm("outline_planner")
    structured_llm = llm.with_structured_output(OutlinePlannerOutput, method="json_schema")

    result: OutlinePlannerOutput = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])

    outline = {
        "deck_title": result.deck_title,
        "core_hook": result.core_hook,
        "slides": [s.model_dump() for s in result.slides],
    }

    logger.info(
        f"outline_planner: {len(result.slides)} slide(s), "
        f"core_hook='{result.core_hook[:60]}...'"
    )

    return {"outline_plan": outline}
