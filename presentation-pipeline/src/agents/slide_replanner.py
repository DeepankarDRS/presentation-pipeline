"""Slide replanner — decides whether an edit needs a richer SlidePlan.

Feedback on an already-generated slide can ask for anything, including a
component kind the slide's original SlidePlan never had (e.g. "add a KPI
row"). A stale plan would under-cover exactly that edit when building the
generation contract (missing node types, missing pitfall notes). This module
gates on that: cheap keyword detection decides whether the existing plan
already covers the feedback, and only replans (one extra LLM call) when it
doesn't — reusing the same planner_node the plan-editor's refine loop uses.

Reads:  slide_plan, feedback, theme_info
Writes: nothing (pure function, caller persists the result)
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.context_builder import _detect_components_from_text, build_contract
from src.agents.planner import planner_node
from src.state import SlidePlan, initial_state

logger = logging.getLogger(__name__)


def _merge_content_data(original: dict[str, Any], replanned: dict[str, Any]) -> dict[str, Any]:
    """Keep original values for existing keys; only take new keys from the replan.

    The replan has no access to the deck's original supplied_content, so its
    own content_data is a fresh guess — trusting it over already-confirmed
    values would silently overwrite real user data.
    """
    return {**replanned, **original}


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
    state = initial_state(run_id=run_id, raw_request="", theme_name=theme_info.get("name", ""))
    state["prior_plan"] = {"core_hook": "", "slides": [dict(slide_plan)]}
    state["refine_feedback"] = feedback

    result = planner_node(state)
    updated_plan = result["slide_plans"][0]
    updated_plan["slide_index"] = slide_plan.get("slide_index", 0)
    updated_plan["content_data"] = _merge_content_data(
        slide_plan.get("content_data", {}), updated_plan.get("content_data", {}),
    )

    return updated_plan, build_contract(updated_plan, theme_info)
