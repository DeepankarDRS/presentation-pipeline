"""Slide component planner — plans ONE slide in detail (fan-out target).

Called once per slide via LangGraph Send() fan-out. Receives the rich
OutlineSlide from the outline_planner and produces a full SlidePlan:
components (each with component_id + content_data), layout_hint, density,
font_tier.

Each slide gets its own focused LLM call with full attention budget.

Concurrency is controlled by:
  SLIDE_PLANNER_MAX_PARALLEL  (env, default 6)  — semaphore for fan-out path
  SLIDE_PLANNER_MAX_CONCURRENCY (env, default 10) — hard ceiling
  SLIDE_PLANNER_SERIALIZE (env, default false)  — run sequentially instead

Reads (from Send input):
  outline_plan, deck_settings, supplied_content, theme_name, current_outline_slide
Writes:
  assembled_slide_plans (Annotated accumulator — fan-in via operator.add)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.planner_schema import PlannerSlide
from src.agents.settings_mapper import DeckSettings, compute_provenance, settings_to_constraints
from src.state import ComponentPlan, PresentationState, SlidePlan
from src.utils.llm_client import get_llm, unpack_raw

logger = logging.getLogger(__name__)

# ── Concurrency configuration ───────────────────────────────────────────────

MAX_PARALLEL_LLM_CALLS: int = int(os.getenv("SLIDE_PLANNER_MAX_PARALLEL", "6"))
MAX_CONCURRENCY: int = int(os.getenv("SLIDE_PLANNER_MAX_CONCURRENCY", "10"))
SERIALIZE_SLIDES: bool = os.getenv("SLIDE_PLANNER_SERIALIZE", "false").lower() == "true"

# ── Prompt env ──────────────────────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "slide_component_planner"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)

# ── Conversion helpers ──────────────────────────────────────────────────────

def _planner_slide_to_state(
    idx: int,
    slide: PlannerSlide,
    supplied_content: dict[str, Any] | None = None,
    slide_title: str = "",
) -> SlidePlan:
    """Convert PlannerSlide Pydantic model to SlidePlan TypedDict."""
    components: list[ComponentPlan] = []
    merged_content_data: dict[str, Any] = {}

    for c in slide.components:
        comp = ComponentPlan(
            component_id=c.component_id,
            kind=c.kind,
            count=c.count,
            content_summary=c.content_summary,
        )
        if c.chart_type:
            comp["chart_type"] = c.chart_type
        if c.series_count:
            comp["series_count"] = c.series_count
        if c.columns:
            comp["columns"] = c.columns
        if c.rows:
            comp["rows"] = c.rows
        if c.items:
            comp["items"] = c.items
        if c.orientation:
            comp["orientation"] = c.orientation
        if c.design_hint:
            comp["design_hint"] = c.design_hint
        if c.weight:
            comp["weight"] = c.weight

        try:
            comp_data = json.loads(c.content_data_json) if c.content_data_json else {}
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                f"slide_component_planner: invalid content_data_json for "
                f"component '{c.component_id}', using empty dict"
            )
            comp_data = {}

        comp["content_data"] = comp_data
        merged_content_data.update(comp_data)
        components.append(comp)

    return SlidePlan(
        slide_index=idx,
        slide_title=slide_title,
        slide_type=slide.slide_type,
        components=components,
        density=slide.density,
        font_tier=slide.font_tier,
        layout_hint=slide.layout_hint,
        content_data=merged_content_data,
        data_provenance=compute_provenance(merged_content_data, supplied_content or {}),
    )


# ── Per-slide planning ──────────────────────────────────────────────────────

def _filter_supplied_content_for_slide(
    supplied_content: dict[str, Any] | None,
    slide: dict[str, Any],
) -> dict[str, Any]:
    """Return subset of supplied_content relevant to this slide's key_messages."""
    if not supplied_content:
        return {}
    messages_text = " ".join(slide.get("key_messages") or []).lower()
    suggested = set()
    for key in supplied_content:
        if key.lower() in messages_text or any(
            part in messages_text for part in key.lower().split("_")
        ):
            suggested.add(key)
    return {k: v for k, v in supplied_content.items() if k in suggested} if suggested else {}


def plan_single_slide(
    slide: dict[str, Any],
    *,
    outline_plan: dict[str, Any],
    deck_settings: dict[str, Any] | None = None,
    supplied_content: dict[str, Any] | None = None,
) -> SlidePlan:
    """Plan one slide and return a SlidePlan TypedDict.

    Can be called directly (e.g. for serial batch planning) or via the graph node.
    """
    constraints: dict[str, Any] = {}
    if deck_settings:
        try:
            settings = DeckSettings.model_validate(deck_settings)
            constraints = settings_to_constraints(settings)
        except Exception:
            pass

    all_slide_titles = [s.get("slide_title", "") for s in (outline_plan.get("slides") or [])]
    total_slides = len(all_slide_titles)

    supplied_for_slide = _filter_supplied_content_for_slide(supplied_content, slide)

    user_msg = _jinja_env.get_template("user.j2").render(
        slide=slide,
        core_hook=outline_plan.get("core_hook", ""),
        deck_context=all_slide_titles,
        total_slides=total_slides,
        deck_settings=deck_settings or {},
        constraints=constraints,
        supplied_content_for_slide=supplied_for_slide if supplied_for_slide else None,
    )
    system_msg = _jinja_env.get_template("system.j2").render()

    llm = get_llm("slide_component_planner")
    structured_llm = llm.with_structured_output(
        PlannerSlide, method="json_schema", include_raw=True,
    )

    raw_result = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])
    result, usage = unpack_raw(raw_result)

    logger.info(
        f"slide_component_planner: slide {slide.get('slide_index', 0)} "
        f"{usage['model']} tokens_in={usage['tokens_in']} tokens_out={usage['tokens_out']}"
    )

    plan = _planner_slide_to_state(
        slide.get("slide_index", 0),
        result,
        supplied_content=supplied_content,
        slide_title=slide.get("slide_title", ""),
    )
    return plan, usage


# ── Serial batch node (used when SERIALIZE_SLIDES=True) ────────────────────

def slide_plan_serial_node(state: PresentationState) -> dict[str, Any]:
    """Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path)."""
    outline = state.get("outline_plan") or {}
    slides = outline.get("slides") or []
    deck_settings = state.get("deck_settings") or {}
    supplied_content = state.get("supplied_content")

    logger.info(f"slide_plan_serial: planning {len(slides)} slide(s) sequentially")

    assembled: list[SlidePlan] = []
    history: list[dict[str, Any]] = []
    for slide in slides:
        plan, usage = plan_single_slide(
            slide,
            outline_plan=outline,
            deck_settings=deck_settings,
            supplied_content=supplied_content,
        )
        assembled.append(plan)
        history.append({"attempt": 0, "tier": 0, **usage})
        logger.info(
            f"slide_plan_serial: slide {slide.get('slide_index', 0) + 1}/{len(slides)} done "
            f"({len(plan.get('components', []))} components)"
        )

    return {"assembled_slide_plans": assembled, "generation_history": history}


# ── Fan-out node (used when SERIALIZE_SLIDES=False, default) ───────────────

def slide_component_planner_node(state: PresentationState) -> dict[str, Any]:
    """Plan ONE slide (receives specific slide via Send() state injection).

    The routing function injects 'current_outline_slide' via Send().
    This node writes to 'assembled_slide_plans' which uses operator.add
    for fan-in accumulation.
    """
    slide = state.get("current_outline_slide")
    if not slide:
        logger.warning("slide_component_planner: no current_outline_slide in state")
        return {"assembled_slide_plans": []}

    outline = state.get("outline_plan") or {}
    deck_settings = state.get("deck_settings") or {}
    supplied_content = state.get("supplied_content")

    logger.info(
        f"slide_component_planner: planning slide {slide.get('slide_index', 0) + 1} "
        f"'{slide.get('slide_title', '')}'"
    )

    plan, usage = plan_single_slide(
        slide,
        outline_plan=outline,
        deck_settings=deck_settings,
        supplied_content=supplied_content,
    )

    logger.info(
        f"slide_component_planner: slide {slide.get('slide_index', 0) + 1} done "
        f"({len(plan.get('components', []))} components, "
        f"density={plan.get('density', '?')})"
    )

    return {
        "assembled_slide_plans": [plan],
        "generation_history": [{"attempt": 0, "tier": 0, **usage}],
    }
