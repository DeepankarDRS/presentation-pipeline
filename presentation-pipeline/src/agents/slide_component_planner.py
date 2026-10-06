"""Slide component planner — plans ONE slide in detail (fan-out target).

Called once per slide via LangGraph Send() fan-out. Receives the rich
OutlineSlide from the outline_planner and produces a full SlidePlan:
components (each with component_id + content_data) and layout_hint.

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

from src.agents.capacity import capacity, enforce_capacity, span
from src.agents.hint_capabilities import planner_capabilities_section
from src.agents.planner_schema import PlannerSlide
from src.agents.settings_mapper import DeckSettings, compute_provenance, settings_to_constraints
from src.agents.plan_checks import PLAN_EMPTY, find_problems, finalize_plan, reask_context
from src.agents.written_lines import (content_line_list, content_lines, drop_visual_directions,
                                      flag_written_lines, visual_directions)
from src.state import ComponentPlan, PresentationState, SlidePlan
from src.utils.llm_client import get_llm, unpack_raw, usage_record

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
# component capacity (knowledge/core/capacity.yaml) — the prompt's limits come from here
_jinja_env.globals.update(cap=capacity(), span=span)

# ── Conversion helpers ──────────────────────────────────────────────────────

def _planner_slide_to_state(
    idx: int,
    slide: PlannerSlide,
    supplied_content: dict[str, Any] | None = None,
    slide_title: str = "",
    label: str = "",
    subtitle: str = "",
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
        components.append(comp)

    capacity_fixes = enforce_capacity(components)
    for note in capacity_fixes:
        logger.info(f"slide_component_planner: slide {idx + 1} capacity fix: {note}")
    for comp in components:
        merged_content_data.update(comp["content_data"])

    plan = SlidePlan(
        slide_index=idx,
        slide_title=slide_title,
        label=label,
        subtitle=subtitle,
        slide_type=slide.slide_type,
        components=components,
        layout_hint=slide.layout_hint,
        content_data=merged_content_data,
        data_provenance=compute_provenance(merged_content_data, supplied_content or {}),
    )
    if capacity_fixes:
        plan["capacity_fixes"] = capacity_fixes
    return plan


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


def brief_text_for(slide: dict[str, Any], supplied_content: dict[str, Any] | None) -> str:
    """Everything the brief says for this slide: what a plan line has to come from."""
    supplied_for_slide = _filter_supplied_content_for_slide(supplied_content, slide)
    return " ".join([*(slide.get("key_messages") or []), slide.get("slide_title", ""),
                     slide.get("subtitle", ""), slide.get("visual_emphasis", ""),
                     json.dumps(supplied_for_slide or {}, ensure_ascii=False)])


def plan_single_slide(
    slide: dict[str, Any],
    *,
    outline_plan: dict[str, Any],
    deck_settings: dict[str, Any] | None = None,
    supplied_content: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
    finalize: bool = True,
) -> tuple[SlidePlan, dict[str, Any]]:
    """Plan one slide; returns (SlidePlan, usage).

    Can be called directly (e.g. for serial batch planning) or via the graph node.
    `finalize=False` leaves out the plan checks' code fixes so `plan_with_reask` can look at the
    raw plan first (step 0); every other caller gets the fixes.
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
        repair_context=repair_context,
    )
    system_msg = _jinja_env.get_template("system.j2").render(
        hint_capabilities=planner_capabilities_section(),
    )

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
        label=slide.get("label", ""),
        subtitle=slide.get("subtitle", ""),
    )
    brief_text = brief_text_for(slide, supplied_content)
    directions = visual_directions(slide)
    notes = (drop_visual_directions(plan, directions, content_lines(slide, directions))
             + flag_written_lines(plan, brief_text))
    if finalize:
        notes += finalize_plan(plan, brief_text)
    for note in notes:
        logger.info(f"slide_component_planner: slide {slide.get('slide_index', 0) + 1} {note}")
    if notes:
        plan["capacity_fixes"] = [*plan.get("capacity_fixes", []), *notes]
    return plan, usage


# ── Re-ask ──────────────────────────────────────────────────────────────────

def fallback_plan(slide: dict[str, Any]) -> SlidePlan:
    """What a slide gets when the planner failed twice: the outline's own content lines as one
    bullet list (copied, nothing written), or no components when it has none. Replaces the silent
    `components: []` of before, which let the generator invent the slide."""
    lines = content_line_list(slide, visual_directions(slide))
    comps: list[ComponentPlan] = []
    if lines:
        comps = [ComponentPlan(
            component_id="fallback_points", kind="bullet_list", count=len(lines),
            content_summary="the slide's own brief lines (the planner failed twice)",
            items=len(lines), weight="hero", content_data={"bullets": lines},
        )]
    return SlidePlan(
        slide_index=slide.get("slide_index", 0),
        slide_title=slide.get("slide_title", "Slide"),
        label=slide.get("label", ""),
        subtitle=slide.get("subtitle", ""),
        slide_type="content",
        components=comps,
        layout_hint="",
        content_data={"bullets": lines} if lines else {},
        plan_source="fallback",
    )


def plan_with_reask(
    slide: dict[str, Any],
    *,
    outline_plan: dict[str, Any],
    deck_settings: dict[str, Any] | None = None,
    supplied_content: dict[str, Any] | None = None,
) -> tuple[SlidePlan, list[dict[str, Any]]]:
    """Plan one slide, asking once more when the plan is empty or holds instruction text.

    Returns (plan, history records). Never raises: when both calls fail the plan is
    `fallback_plan`. Of the two plans the one with fewer problems wins (a tie keeps the first),
    then the code fixes of `finalize_plan` run on it.
    """
    idx = slide.get("slide_index", 0)
    brief_text = brief_text_for(slide, supplied_content)
    history: list[dict[str, Any]] = []
    best: SlidePlan | None = None
    best_count = 0
    problems: list[dict[str, str]] = []
    for attempt in range(2):
        try:
            plan, usage = plan_single_slide(
                slide, outline_plan=outline_plan, deck_settings=deck_settings,
                supplied_content=supplied_content,
                repair_context=reask_context(problems) if attempt else None, finalize=False,
            )
        except Exception as exc:
            logger.error(f"slide_component_planner: slide {idx + 1} attempt {attempt + 1} failed: {exc}")
            problems = [{"code": PLAN_EMPTY, "component_id": "", "detail": "the previous planner call failed"}]
            continue
        history.append(usage_record(usage, "slide_component_planner", idx, reask=bool(attempt)))
        problems = find_problems(plan, brief_text)
        if best is None or len(problems) < best_count:
            best, best_count = plan, len(problems)
        if not problems:
            break
        if attempt == 0:
            logger.info(f"slide_component_planner: slide {idx + 1} re-ask: "
                        + "; ".join(p["detail"] for p in problems))
    if best is None:
        logger.error(f"slide_component_planner: slide {idx + 1} failed twice, using the fallback plan")
        best = fallback_plan(slide)
    notes = finalize_plan(best, brief_text)
    if best.get("plan_source") == "fallback":
        notes.append("planner failed twice: fallback plan")
    elif len(history) > 1:
        notes.append("planner re-asked")
    for note in notes:
        logger.info(f"slide_component_planner: slide {idx + 1} {note}")
    if notes:
        best["capacity_fixes"] = [*best.get("capacity_fixes", []), *notes]
    return best, history


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
        plan, records = plan_with_reask(
            slide, outline_plan=outline, deck_settings=deck_settings, supplied_content=supplied_content,
        )
        history.extend(records)
        assembled.append(plan)
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

    plan, history = plan_with_reask(
        slide, outline_plan=outline, deck_settings=deck_settings, supplied_content=supplied_content,
    )

    logger.info(
        f"slide_component_planner: slide {slide.get('slide_index', 0) + 1} done "
        f"({len(plan.get('components', []))} components)"
    )

    return {"assembled_slide_plans": [plan], "generation_history": history}
