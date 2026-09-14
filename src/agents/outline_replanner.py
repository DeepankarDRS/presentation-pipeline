"""Outline replanner — regenerates a single outline slide from user feedback.

Pre-generation counterpart to slide_replanner.py: that module revises an
already-generated SlidePlan (components/layout/content_data) for the
post-generation "slide editor" flow. This module revises an OutlineSlide
(title/key_messages/etc.) while the user is still editing the outline,
before any component-level planning has happened. Purely user-triggered —
no tier-gate, no content merge; always replaces the full OutlineSlide.

Reads:  outline_slide, core_hook, feedback, deck_settings
Writes: nothing (pure function, caller persists the result)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.outline_planner_schema import OutlineSlide
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "outline_replanner"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def regenerate_outline_slide(
    outline_slide: dict[str, Any],
    core_hook: str,
    feedback: str,
    deck_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Regenerate one OutlineSlide's content per user feedback, preserving its position."""
    logger.info(f"outline_replanner: regenerating slide {outline_slide.get('slide_index')}")

    user_msg = _jinja_env.get_template("user.j2").render(
        outline_slide=outline_slide,
        core_hook=core_hook,
        feedback=feedback,
        deck_settings=deck_settings or {},
    )
    system_msg = _jinja_env.get_template("system.j2").render()

    llm = get_llm("outline_planner")
    structured_llm = llm.with_structured_output(OutlineSlide, method="json_schema")

    result: OutlineSlide = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])

    updated = result.model_dump()
    updated["slide_index"] = outline_slide.get("slide_index", 0)

    logger.info(f"outline_replanner: slide {updated['slide_index']} regenerated")
    return updated
