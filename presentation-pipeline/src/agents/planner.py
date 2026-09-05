"""Planner agent — determines slide components, density, and layout hint.

Component-based planning (NO archetypes). The planner outputs a component
list + density + freeform layout_hint. The generator has full creative freedom
to arrange components into POM XML.

Reads:  raw_request, theme_name, supplied_content, deck_min_threshold
Writes: deck_plan, slide_plans, mode
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.planner_schema import LayoutPatternLiteral, PlannerOutput, PlannerSlide
from src.state import ComponentPlan, DeckPlan, PresentationState, SlidePlan
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "planner"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _render_system() -> str:
    return _jinja_env.get_template("system.j2").render()


def _render_user(state: PresentationState) -> str:
    supplied = state.get("supplied_content") or {}
    test_case = state.get("test_case") or {}
    components_hint = ""
    if test_case.get("components"):
        components_hint = ", ".join(test_case["components"])

    return _jinja_env.get_template("user.j2").render(
        raw_request=state.get("raw_request", ""),
        theme_name=state.get("theme_name", ""),
        supplied_content=supplied,
        components_hint=components_hint,
        audience_context=state.get("audience_context") or {},
    )


def _compute_provenance(
    content_data: dict[str, Any],
    supplied: dict[str, Any],
) -> dict[str, str]:
    """Tag each content_data key as 'user' (from supplied_content) or 'sample'."""
    provenance: dict[str, str] = {}
    supplied_keys = set(supplied) if supplied else set()
    for key in content_data:
        provenance[key] = "user" if key in supplied_keys else "sample"
    return provenance


def _slide_to_state(
    idx: int,
    slide: PlannerSlide,
    supplied_content: dict[str, Any] | None = None,
) -> SlidePlan:
    """Convert Pydantic PlannerSlide to state SlidePlan TypedDict."""
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
        logger.warning("planner: invalid content_data_json, using empty dict")
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
        data_provenance=_compute_provenance(content_data, supplied_content or {}),
    )


_LAYOUT_PATTERNS: list[str] = list(LayoutPatternLiteral.__args__)
_VARIETY_SKIP_TYPES = {"cover", "section_break", "closing"}


def _enforce_layout_variety(plans: list[SlidePlan]) -> int:
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


def planner_node(state: PresentationState) -> dict[str, Any]:
    """Plan slide components using an LLM with structured output."""
    logger.info("planner: generating slide plan")

    system_msg = _render_system()
    user_msg = _render_user(state)

    llm = get_llm("planner")
    structured_llm = llm.with_structured_output(PlannerOutput, method="json_schema")

    result: PlannerOutput = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])

    core_hook = result.core_hook
    supplied = state.get("supplied_content") or {}
    slide_plans = [
        _slide_to_state(i, s, supplied_content=supplied)
        for i, s in enumerate(result.slides)
    ]

    swaps = _enforce_layout_variety(slide_plans)
    if swaps:
        logger.info(f"planner: layout variety — swapped {swaps} adjacent duplicate(s)")

    slide_count = len(slide_plans)
    threshold = state.get("deck_min_threshold", 3)

    if slide_count >= threshold and threshold > 0:
        mode = "deck"
        deck_plan = DeckPlan(
            core_hook=core_hook,
            slide_count=slide_count,
            theme=state.get("theme_name", ""),
            slides=slide_plans,
        )
    else:
        mode = "single"
        deck_plan = None

    logger.info(
        f"planner: {slide_count} slide(s), mode={mode}, "
        f"core_hook='{core_hook[:60]}...', "
        f"density={slide_plans[0].get('density', '?') if slide_plans else '?'}"
    )

    return {
        "mode": mode,
        "core_hook": core_hook,
        "deck_plan": deck_plan,
        "slide_plans": slide_plans,
    }
