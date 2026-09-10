"""Slide replanner — decides whether an edit needs a richer SlidePlan.

Feedback on an already-generated slide can ask for anything, including a
component kind the slide's original SlidePlan never had (e.g. "add a KPI
row"). A stale plan would under-cover exactly that edit when building the
generation contract (missing node types, missing pitfall notes). This module
gates on that: cheap keyword detection decides whether the existing plan
already covers the feedback, and only replans (one extra LLM call) when it
doesn't — calling slide_component_planner for the single slide.

Reads:  slide_plan, feedback, theme_info
Writes: nothing (pure function, caller persists the result)
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.context_builder import _detect_components_from_text, build_contract
from src.agents.slide_component_planner import plan_single_slide
from src.state import SlidePlan

logger = logging.getLogger(__name__)


def _merge_content_data(original: dict[str, Any], replanned: dict[str, Any]) -> dict[str, Any]:
    """Keep original values for existing keys; only take new keys from the replan.

    The replan has no access to the deck's original supplied_content, so its
    own content_data is a fresh guess — trusting it over already-confirmed
    values would silently overwrite real user data.
    """
    return {**replanned, **original}


def _slide_plan_to_outline_slide(slide_plan: SlidePlan) -> dict[str, Any]:
    """Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.

    visual_emphasis is left empty rather than back-filling from layout_hint,
    because layout_hint is a spatial priority statement (e.g. "KPI row across
    the top; chart below") that would anchor the planner on a stale layout.
    The slide_component_planner re-derives it from the content.
    """
    return {
        "slide_index": slide_plan.get("slide_index", 0),
        "slide_title": slide_plan.get("content_data", {}).get("title", ""),
        "section": "",
        "narrative_role": "",
        "key_messages": [],
        "data_anchors": [],
        "visual_emphasis": "",
    }


def resolve_slide_plan(
    slide_plan: SlidePlan,
    feedback: str,
    theme_info: dict[str, Any],
    run_id: str,
) -> tuple[SlidePlan, dict[str, Any]]:
    """Return (possibly-updated slide_plan, generation contract) for an edit.

    Degrades to (slide_plan, {}) when slide_plan or theme_info is missing
    (legacy runs generated before these were persisted). Callers should wrap
    this in try/except for any other failure (e.g. a malformed theme_info).
    """
    if not slide_plan or not theme_info:
        return slide_plan, {}

    existing_kinds = {c.get("kind") for c in slide_plan.get("components", [])}
    detected_kinds = set(_detect_components_from_text(feedback))
    needs_replan = bool(detected_kinds - existing_kinds)

    if not needs_replan:
        return slide_plan, build_contract(slide_plan, theme_info)

    logger.info(f"slide_replanner: feedback introduces new kind(s) {detected_kinds - existing_kinds}, replanning")

    outline_slide = _slide_plan_to_outline_slide(slide_plan)
    outline_plan = {"core_hook": "", "slides": [outline_slide]}

    try:
        updated_plan = plan_single_slide(
            outline_slide,
            outline_plan=outline_plan,
            deck_settings={"theme": theme_info.get("name", "")},
        )
    except Exception as exc:
        logger.warning(f"slide_replanner: plan_single_slide failed, using original: {exc}")
        return slide_plan, build_contract(slide_plan, theme_info)

    updated_plan["slide_index"] = slide_plan.get("slide_index", 0)
    updated_plan["content_data"] = _merge_content_data(
        slide_plan.get("content_data", {}), updated_plan.get("content_data", {}),
    )

    return updated_plan, build_contract(updated_plan, theme_info)
