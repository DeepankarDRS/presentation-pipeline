"""LangGraph pipeline definition.

Hierarchical planning topology:
    START → route_after_start
        → elicitor  (if query vague and no answers yet)
        → outline_planner  (deck skeleton)
        → fan_out_slide_plans  (Send() per slide, parallel by default)
            → slide_component_planner  (one focused LLM call per slide)
            → [fan-in via assembled_slide_plans operator.add]
        → slide_plan_sorter  (sort + layout variety)
        → plan_reviewer  (confidence score)
        → route_after_plan_review
            → style_resolver → context_builder → generator → validator
              → (compile fail & retryable) repairer → validator  (loop)
              → (compile ok) critic → evaluator → END

Serial mode (SLIDE_PLANNER_SERIALIZE=true):
    outline_planner → slide_plan_serial → slide_plan_sorter → ...

Multi-slide generation topology (unchanged from prior):
    slide_router → context_builder  (loop per slide)
    slide_router → deck_assembler → evaluator → END

Skip-planner path (test_case.components or slide_plans already set):
    START → style_resolver  (planning skipped entirely)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.agents.context_builder import context_builder_node
from src.agents.critic import critic_node
from src.agents.deck_nodes import deck_assembler_node, slide_router_node
from src.agents.elicitor import elicitor_node
from src.agents.evaluator import evaluator_node
from src.agents.generator import generator_node
from src.agents.outline_planner import outline_planner_node
from src.agents.plan_reviewer import plan_reviewer_node
from src.agents.questionnaire import questionnaire_node
from src.agents.repairer import repairer_node
from src.agents.slide_component_planner import (
    SERIALIZE_SLIDES,
    enforce_layout_variety,
    slide_component_planner_node,
    slide_plan_serial_node,
)
from src.agents.style_resolver import style_resolver_node
from src.agents.validator import validator_node
from src.state import DeckPlan, PresentationState, SlidePlan, initial_state

logger = logging.getLogger(__name__)


# ── Routing functions ───────────────────────────────────────────────────────

def route_after_start(state: PresentationState) -> str:
    """Route to planning pipeline, questionnaire, or skip directly to generation."""
    # Skip all planning when slide_plans already provided externally
    if state.get("slide_plans"):
        logger.info("route: skipping planning (slide_plans already provided)")
        return "style_resolver"

    test_case = state.get("test_case") or {}
    if test_case.get("components"):
        logger.info("route: skipping planning (test_case has components)")
        return "style_resolver"

    # Interactive CLI mode — legacy questionnaire path
    if state.get("interactive") and not state.get("audience_context"):
        logger.info("route: → questionnaire (interactive)")
        return "questionnaire"

    logger.info("route: → elicitor")
    return "elicitor"


def route_after_elicitor(state: PresentationState) -> str:
    """If elicitation is needed and no answers yet, suspend; else proceed."""
    if state.get("elicitation_needed") and not state.get("elicitation_answers"):
        logger.info("route: elicitation needed — suspending for API answers")
        return "elicitation_wait"
    return "outline_planner"


def fan_out_slide_plans(state: PresentationState) -> list[Send] | str:
    """Fan-out to one slide_component_planner per outline slide."""
    if SERIALIZE_SLIDES:
        return "slide_plan_serial"

    outline = state.get("outline_plan") or {}
    slides = outline.get("slides") or []
    if not slides:
        logger.warning("fan_out: no slides in outline_plan, falling back to serial")
        return "slide_plan_serial"

    logger.info(f"fan_out: dispatching {len(slides)} slide(s) in parallel")
    return [
        Send("slide_component_planner", {
            **state,
            "current_outline_slide": slide,
        })
        for slide in slides
    ]


def slide_plan_sorter_node(state: PresentationState) -> dict[str, Any]:
    """Sort assembled_slide_plans by slide_index, enforce layout variety, write slide_plans."""
    assembled: list[SlidePlan] = list(state.get("assembled_slide_plans") or [])
    assembled.sort(key=lambda p: p.get("slide_index", 0))

    swaps = enforce_layout_variety(assembled)
    if swaps:
        logger.info(f"slide_plan_sorter: {swaps} layout swap(s) for variety")

    outline = state.get("outline_plan") or {}
    core_hook = outline.get("core_hook", "")
    deck_title = outline.get("deck_title", "")
    mode = "deck" if len(assembled) > 1 else "single"

    deck_plan = DeckPlan(
        core_hook=core_hook,
        slide_count=len(assembled),
        theme=state.get("theme_name", ""),
        slides=assembled,
    )

    logger.info(f"slide_plan_sorter: {len(assembled)} slide(s) sorted, mode={mode}")
    return {
        "slide_plans": assembled,
        "core_hook": core_hook,
        "deck_plan": deck_plan,
        "mode": mode,
    }


def route_after_plan_review(state: PresentationState) -> str:
    """After plan review, always proceed to style_resolver (issues are advisory)."""
    review = state.get("plan_review") or {}
    score = review.get("confidence_score", 1.0)
    approved = review.get("approved", True)
    logger.info(f"route_after_plan_review: confidence={score:.2f}, approved={approved} → style_resolver")
    return "style_resolver"


def _slide_done_target(state: PresentationState) -> str:
    slide_plans = state.get("slide_plans", [])
    if len(slide_plans) > 1:
        return "slide_router"
    return "evaluator"


def route_after_validator(state: PresentationState) -> str:
    cr = state.get("compile_result") or {}
    if not cr.get("ok", False) and cr.get("retryable", False):
        budget = state.get("retry_budget", 3)
        count = state.get("retry_count", 0)
        if count < budget:
            logger.info(f"route: compile failed, retry {count+1}/{budget} → repairer")
            return "repairer"
        target = _slide_done_target(state)
        logger.info(f"route: compile failed but retry budget exhausted → {target}")
        return target

    mode = state.get("critic_mode", "off")
    if mode == "off":
        target = _slide_done_target(state)
        logger.info(f"route: compile ok, critic off → {target}")
        return target
    logger.info("route: compile ok → critic")
    return "critic"


def route_after_critic(state: PresentationState) -> str:
    cr = state.get("critic_result") or {}
    if not cr.get("passed", True):
        budget = state.get("retry_budget", 3)
        count = state.get("retry_count", 0)
        if count < budget:
            logger.info(f"route: critic failed, retry {count+1}/{budget} → repairer")
            return "repairer"
        target = _slide_done_target(state)
        logger.info(f"route: critic failed but retry budget exhausted → {target}")
        return target
    target = _slide_done_target(state)
    logger.info(f"route: critic passed → {target}")
    return target


def route_after_slide_router(state: PresentationState) -> str:
    idx = state.get("current_slide_index", 0)
    total = len(state.get("slide_plans", []))
    if idx < total:
        logger.info(f"route: slide {idx}/{total} → context_builder")
        return "context_builder"
    logger.info(f"route: all {total} slides done → deck_assembler")
    return "deck_assembler"


def route_after_repairer(state: PresentationState) -> str:
    return "validator"


# ── Graph construction ──────────────────────────────────────────────────────

def _elicitation_wait_node(state: PresentationState) -> dict[str, Any]:
    """Placeholder node — pipeline suspends here when elicitation is needed.

    In practice the API layer uses checkpointing or a run queue to resume
    the graph after the user answers. This node is a no-op in the graph
    execution; its presence makes the topology explicit.
    """
    return {}


def build_graph() -> StateGraph:
    """Construct the presentation pipeline graph (uncompiled)."""
    graph = StateGraph(PresentationState)

    # ── Planning phase ──
    graph.add_node("questionnaire", questionnaire_node)
    graph.add_node("elicitor", elicitor_node)
    graph.add_node("elicitation_wait", _elicitation_wait_node)
    graph.add_node("outline_planner", outline_planner_node)
    graph.add_node("slide_component_planner", slide_component_planner_node)
    graph.add_node("slide_plan_serial", slide_plan_serial_node)
    graph.add_node("slide_plan_sorter", slide_plan_sorter_node)
    graph.add_node("plan_reviewer", plan_reviewer_node)

    # ── Generation phase ──
    graph.add_node("style_resolver", style_resolver_node)
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("generator", generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("repairer", repairer_node)
    graph.add_node("slide_router", slide_router_node)
    graph.add_node("deck_assembler", deck_assembler_node)
    graph.add_node("evaluator", evaluator_node)

    # ── Planning edges ──
    graph.add_conditional_edges(
        START, route_after_start,
        ["questionnaire", "elicitor", "style_resolver"],
    )
    graph.add_edge("questionnaire", "elicitor")
    graph.add_conditional_edges(
        "elicitor", route_after_elicitor,
        ["elicitation_wait", "outline_planner"],
    )
    graph.add_edge("elicitation_wait", END)
    graph.add_conditional_edges(
        "outline_planner", fan_out_slide_plans,
        ["slide_component_planner", "slide_plan_serial"],
    )
    graph.add_edge("slide_component_planner", "slide_plan_sorter")
    graph.add_edge("slide_plan_serial", "slide_plan_sorter")
    graph.add_edge("slide_plan_sorter", "plan_reviewer")
    graph.add_conditional_edges(
        "plan_reviewer", route_after_plan_review,
        ["style_resolver"],
    )

    # ── Generation edges ──
    graph.add_edge("style_resolver", "context_builder")
    graph.add_edge("context_builder", "generator")
    graph.add_edge("generator", "validator")
    graph.add_conditional_edges(
        "validator", route_after_validator,
        ["repairer", "critic", "evaluator", "slide_router"],
    )
    graph.add_conditional_edges(
        "critic", route_after_critic,
        ["repairer", "evaluator", "slide_router"],
    )
    graph.add_conditional_edges("repairer", route_after_repairer, ["validator"])
    graph.add_conditional_edges(
        "slide_router", route_after_slide_router,
        ["context_builder", "deck_assembler"],
    )
    graph.add_edge("deck_assembler", "evaluator")
    graph.add_edge("evaluator", END)

    return graph


def compile_graph():
    """Return a compiled, runnable graph."""
    return build_graph().compile()


# ── CLI entry point ─────────────────────────────────────────────────────────

def run(
    request: str = "Create a simple title slide",
    *,
    theme: str = "",
    critic_mode: Literal["auto", "manual", "off"] = "off",
    deck_min_threshold: int = 1,
    run_id: str | None = None,
    supplied_content: dict[str, Any] | None = None,
    test_case: dict[str, Any] | None = None,
    audience_context: dict[str, str] | None = None,
    deck_settings: dict[str, Any] | None = None,
    interactive: bool = False,
) -> PresentationState:
    """Run the pipeline end-to-end and return the final state."""
    from src.utils.logging_config import setup_logging, set_context

    setup_logging()

    rid = run_id or uuid.uuid4().hex[:12]
    set_context(run_id=rid)

    state = initial_state(
        run_id=rid,
        raw_request=request,
        theme_name=theme,
        deck_min_threshold=deck_min_threshold,
        critic_mode=critic_mode,
        supplied_content=supplied_content,
        test_case=test_case,
        audience_context=audience_context,
        deck_settings=deck_settings,
        interactive=interactive,
    )

    app = compile_graph()
    config = {
        "run_name": f"pom-pipeline-{rid}",
        "tags": ["presentation-pipeline"],
        "metadata": {"run_id": rid, "theme": theme, "critic_mode": critic_mode},
    }
    final = app.invoke(state, config=config)
    return final


if __name__ == "__main__":
    import json
    import sys

    request = sys.argv[1] if len(sys.argv) > 1 else "Create a simple title slide"
    result = run(request, interactive=True)

    print("\n== Final State ==")
    print(f"  run_id:      {result.get('run_id')}")
    print(f"  passed:      {result.get('passed')}")
    print(f"  pptx_path:   {result.get('pptx_path')}")
    print(f"  retry_count: {result.get('retry_count')}")
    print(f"  retry_tier:  {result.get('retry_tier')}")
    print(f"  xml length:  {len(result.get('current_xml', ''))}")

    plan_review = result.get("plan_review") or {}
    if plan_review:
        print(f"\n== Plan Review ==")
        print(f"  confidence:  {plan_review.get('confidence_score', 0):.2f}")
        print(f"  approved:    {plan_review.get('approved')}")
        print(f"  summary:     {plan_review.get('summary', '')}")

    eval_data = result.get("evaluation")
    if eval_data:
        print("\n== Evaluation ==")
        print(json.dumps(eval_data, indent=2))
