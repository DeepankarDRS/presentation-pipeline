"""Outline planner agent — produces the deck skeleton (replaces planner.py).

Takes the enriched request (raw_request + deck_settings + elicitation_answers +
supplied_content) and produces a rich per-slide outline: the header (label,
slide_title = headline, subtitle), section, narrative_role, key_messages,
visual_emphasis.

key_messages carry each slide's content, copied from the request — every message
carries semantic intent that the slide component planner routes to the right
component type. Figures come only from the request (never invented).

Does NOT produce slide_type, component lists, or content_data JSON. Those are
the slide_component_planner's job.

Reads:  raw_request, deck_settings, elicitation_answers, supplied_content, theme_name
Writes: outline_plan
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.outline_planner_schema import OutlinePlannerOutput
from src.agents.settings_mapper import DeckSettings, settings_to_constraints
from src.state import PresentationState
from src.utils.llm_client import get_llm, unpack_raw, usage_record
from src.utils.text_clean import clean_data

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "outline_planner"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


_NUMBER_WORDS = ("one two three four five six seven eight nine ten eleven twelve thirteen "
                 "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()
# "6-SLIDE", "14 slides", "a five-slide deck"; not "1280x720 slide" or "one slide per section"
_STATED_COUNT = re.compile(
    r"(?<![\d.x×])\b(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")\s*-?\s*slides?\b(?!\s+(?:per|each|for)\b)",
    re.I,
)
_SLIDE_HEADING = re.compile(r"\bslide\s+(\d{1,2})\s*[:\-–—]", re.I)  # "Slide 3:" anywhere in a line


def stated_slide_count(request: str) -> int | None:
    """The slide count the request states: "6-SLIDE" / "five slides", else "Slide 1:" … "Slide N:".

    None when the request states no count or states different counts.
    """
    counts = {int(m) if m.isdigit() else _NUMBER_WORDS.index(m.lower()) + 1
              for m in _STATED_COUNT.findall(request or "")}
    if len(counts) == 1:
        return counts.pop()
    if counts:
        return None
    headings = {int(m) for m in _SLIDE_HEADING.findall(request or "")}
    if len(headings) >= 2 and headings == set(range(1, max(headings) + 1)):
        return max(headings)
    return None


def _get_constraints(deck_settings_dict: dict[str, Any]) -> dict[str, Any]:
    """Parse DeckSettings dict → constraints dict for prompt injection."""
    try:
        settings = DeckSettings.model_validate(deck_settings_dict)
        return settings_to_constraints(settings)
    except Exception:
        return {
            "narrative_guidance": "data-focused — add narrative only when it reveals something the numbers alone do not",
            "text_mode": "generate",
            "provenance_rule": "llm_generates_freely",
        }


def outline_planner_node(state: PresentationState) -> dict[str, Any]:
    """Plan the deck outline using an LLM with structured output."""
    logger.info("outline_planner: generating deck outline")

    deck_settings = state.get("deck_settings") or {}
    constraints = _get_constraints(deck_settings)

    # Slide count: the test case's → the one the request states → the settings bucket
    target_slides = constraints.get("deck_min_threshold") or state.get("deck_min_threshold", 6)
    slide_count_source = "settings"
    stated = stated_slide_count(state.get("raw_request", ""))
    if stated:
        target_slides, slide_count_source = stated, "request"
    test_case = state.get("test_case") or {}
    if test_case.get("slide_count"):
        target_slides, slide_count_source = test_case["slide_count"], "test_case"

    user_msg = _jinja_env.get_template("user.j2").render(
        raw_request=state.get("raw_request", ""),
        deck_settings=deck_settings,
        constraints=constraints,
        elicitation_answers=state.get("elicitation_answers") or {},
        supplied_content=state.get("supplied_content"),
        target_slides=target_slides,
        slide_count_source=slide_count_source,
    )
    system_msg = _jinja_env.get_template("system.j2").render()

    llm = get_llm("outline_planner")
    structured_llm = llm.with_structured_output(
        OutlinePlannerOutput, method="json_schema", include_raw=True,
    )

    raw_result = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])
    result, usage = unpack_raw(raw_result)

    outline = clean_data({  # gpt-5-mini wrote NULs where a "·" belongs (step 0 run): clean what it returns
        "deck_title": result.deck_title,
        "core_hook": result.core_hook,
        "slides": [s.model_dump() for s in result.slides],
    })

    logger.info(
        f"outline_planner: {len(result.slides)} slide(s), "
        f"core_hook='{result.core_hook[:60]}...'"
    )
    logger.info(f"outline_planner: {usage['model']} tokens_in={usage['tokens_in']} tokens_out={usage['tokens_out']}")

    return {
        "outline_plan": outline,
        "generation_history": [usage_record(usage, "outline_planner")],
    }
