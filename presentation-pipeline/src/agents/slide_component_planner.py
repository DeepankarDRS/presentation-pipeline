"""Slide component planner — plans ONE slide in detail (fan-out target).

Called once per slide via LangGraph Send() fan-out. Receives the rich
OutlineSlide from the outline_planner and produces a full SlidePlan:
components, layout_pattern, layout_hint, density, font_tier, content_data.

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

from src.agents.planner_schema import LayoutPatternLiteral, PlannerSlide
from src.agents.settings_mapper import DeckSettings, compute_provenance, settings_to_constraints
from src.state import ComponentPlan, PresentationState, SlidePlan
from src.utils.llm_client import get_llm

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

# ── Layout variety enforcement ──────────────────────────────────────────────

_LAYOUT_PATTERNS: list[str] = list(LayoutPatternLiteral.__args__)
_VARIETY_SKIP_TYPES = {"cover", "section_break", "closing"}


def enforce_layout_variety(plans: list[SlidePlan]) -> int:
    """Swap layout_pattern on adjacent content/data slides that repeat. Returns swap count."""
    swaps = 0
    for i in range(1, len(plans)):
        prev, curr = plans[i - 1], plans[i]
        if prev.get("slide_type") in _VARIETY_SKIP_TYPES:
            continue
        if curr.get("slide_type") in _VARIETY_SKIP_TYPES:
            continue
        if prev.get("layout_pattern") != curr.get("layout_pattern"):
            continue
        used = {prev.get("layout_pattern")}
        if i + 1 < len(plans):
            used.add(plans[i + 1].get("layout_pattern"))
        for alt in _LAYOUT_PATTERNS:
            if alt not in used and alt != "hero_statement":
                curr["layout_pattern"] = alt
                swaps += 1
                break
    return swaps


# ── Conversion helpers ──────────────────────────────────────────────────────

def _planner_slide_to_state(
    idx: int,
    slide: PlannerSlide,
    supplied_content: dict[str, Any] | None = None,
) -> SlidePlan:
    """Convert PlannerSlide Pydantic model to SlidePlan TypedDict."""
    components: list[ComponentPlan] = []
    for c in slide.components:
        comp = ComponentPlan(kind=c.kind, count=c.count, content_summary=c.content_summary)
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
        components.append(comp)

    try:
        content_data = json.loads(slide.content_data_json) if slide.content_data_json else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("slide_component_planner: invalid content_data_json, using empty dict")
        content_data = {}

    return SlidePlan(
        slide_index=idx,
        slide_type=slide.slide_type,
        components=components,
        density=slide.density,
        font_tier=slide.font_tier,
        layout_pattern=slide.layout_pattern,
        layout_hint=slide.layout_hint,
        content_data=content_data,
        data_provenance=compute_provenance(content_data, supplied_content or {}),
    )


# ── Per-slide planning ──────────────────────────────────────────────────────

def _filter_supplied_content_for_slide(
    supplied_content: dict[str, Any] | None,
    slide: dict[str, Any],
) -> dict[str, Any]:
    """Return subset of supplied_content relevant to this slide's data_anchors."""
    if not supplied_content:
        return {}
    # Heuristic: include all keys that are mentioned in data_anchors text
    anchors_text = " ".join(slide.get("data_anchors") or []).lower()
    suggested = set()
    for key in supplied_content:
        if key.lower() in anchors_text or any(part in anchors_text for part in key.lower().split("_")):
            suggested.add(key)
    # Always include key-value types that match component hints
    hints = [c.lower() for c in (slide.get("suggested_components") or [])]
    component_key_prefixes = {
        "kpi_row": ["kpi_"],
        "chart": ["chart_"],
        "table": ["table_"],
        "bullet_list": ["bullets"],
        "timeline": ["timeline_"],
        "flow": ["flow_"],
        "process_arrow": ["process_"],
        "pyramid": ["pyramid_"],
        "tree": ["tree_"],
    }
    for hint in hints:
        for prefix in component_key_prefixes.get(hint, []):
            for key in supplied_content:
                if key.startswith(prefix):
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
    structured_llm = llm.with_structured_output(PlannerSlide, method="json_schema")

    result: PlannerSlide = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])

    return _planner_slide_to_state(
        slide.get("slide_index", 0),
        result,
        supplied_content=supplied_content,
    )


# ── Serial batch node (used when SERIALIZE_SLIDES=True) ────────────────────

def slide_plan_serial_node(state: PresentationState) -> dict[str, Any]:
    """Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path)."""
    outline = state.get("outline_plan") or {}
    slides = outline.get("slides") or []
    deck_settings = state.get("deck_settings") or {}
    supplied_content = state.get("supplied_content")

    logger.info(f"slide_plan_serial: planning {len(slides)} slide(s) sequentially")

    assembled: list[SlidePlan] = []
    for slide in slides:
        plan = plan_single_slide(
            slide,
            outline_plan=outline,
            deck_settings=deck_settings,
            supplied_content=supplied_content,
        )
        assembled.append(plan)
        logger.info(
            f"slide_plan_serial: slide {slide.get('slide_index', 0) + 1}/{len(slides)} done "
            f"({len(plan.get('components', []))} components)"
        )

    return {"assembled_slide_plans": assembled}


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

    plan = plan_single_slide(
        slide,
        outline_plan=outline,
        deck_settings=deck_settings,
        supplied_content=supplied_content,
    )

    logger.info(
        f"slide_component_planner: slide {slide.get('slide_index', 0) + 1} done "
        f"({len(plan.get('components', []))} components, "
        f"layout={plan.get('layout_pattern', '?')})"
    )

    return {"assembled_slide_plans": [plan]}
