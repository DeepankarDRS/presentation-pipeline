"""Elicitor agent — detects vague queries and generates clarifying questions.

Design: reusable utility function first, graph node wrapper second.
Any agent that needs to check for ambiguity can call check_and_elicit()
directly — the critic, the slide editor, or future agents.

Reads:  raw_request, deck_settings (optional), supplied_content (optional)
Writes: elicitation_needed, elicitation_questions
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.elicitor_schema import ElicitorOutput
from src.state import PresentationState
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "elicitor"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


# ── Public utility function ─────────────────────────────────────────────────

def check_and_elicit(
    context: str,
    *,
    additional_instructions: str = "",
    deck_settings: dict[str, Any] | None = None,
    supplied_content: dict[str, Any] | None = None,
    domain_hint: str = "",
    llm_role: str = "elicitor",
) -> ElicitorOutput:
    """Check if context is sufficient and return clarifying questions if not.

    Pure LLM call — no graph state dependency. Any agent can call this.

    Args:
        context: The query / instruction / situation to evaluate.
        additional_instructions: Extra constraints the user typed.
        deck_settings: Serialized DeckSettings (to know what's already captured).
        supplied_content: Already-provided data (reduces elicitation need).
        domain_hint: Optional hint to the LLM about the context domain
                     ("slide edit", "critique", "planning", etc.).
        llm_role: LLM config role to use (default "elicitor").

    Returns:
        ElicitorOutput with is_sufficient=True (no questions) or
        is_sufficient=False + targeted questions.
    """
    user_prompt = _jinja_env.get_template("user.j2").render(
        raw_request=context,
        additional_instructions=additional_instructions,
        deck_settings=deck_settings or {},
        supplied_content=supplied_content,
        domain_hint=domain_hint,
    )
    system_prompt = _jinja_env.get_template("system.j2").render()

    llm = get_llm(llm_role)
    structured_llm = llm.with_structured_output(ElicitorOutput, method="json_schema")

    result: ElicitorOutput = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    logger.info(
        f"elicitor: is_sufficient={result.is_sufficient}, "
        f"reasoning='{result.reasoning[:80]}', "
        f"questions={len(result.questions)}"
    )
    return result


# ── Graph node ──────────────────────────────────────────────────────────────

def elicitor_node(state: PresentationState) -> dict[str, Any]:
    """Graph node: run elicitor and write results to state.

    If elicitation_answers are already present (user answered the questions),
    this node is a no-op — it marks elicitation as complete.
    """
    # If user has already answered, don't re-elicit
    if state.get("elicitation_answers"):
        logger.info("elicitor: answers already present, skipping")
        return {"elicitation_needed": False}

    deck_settings = state.get("deck_settings") or {}
    result = check_and_elicit(
        context=state.get("raw_request", ""),
        additional_instructions=deck_settings.get("additional_instructions", ""),
        deck_settings=deck_settings,
        supplied_content=state.get("supplied_content"),
    )

    if result.is_sufficient:
        return {"elicitation_needed": False, "elicitation_questions": []}

    questions = [q.model_dump() for q in result.questions]
    return {
        "elicitation_needed": True,
        "elicitation_questions": questions,
    }
