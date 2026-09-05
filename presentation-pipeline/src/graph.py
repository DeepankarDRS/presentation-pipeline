"""LangGraph pipeline definition.

Single-slide topology:
    START → [questionnaire] → planner → style_resolver → context_builder
      → generator → validator
      → (compile fail & retryable) repairer → validator  (loop)
      → (compile ok) critic → evaluator → END

Multi-slide topology (len(slide_plans) > 1):
    START → [questionnaire] → planner → style_resolver → context_builder
      → generator → validator → critic → slide_router
      → (more slides) → context_builder  (loop per slide, theme already resolved)
      → slide_router → (all done) → deck_assembler → evaluator → END

Conditional edges:
    - Questionnaire: only when interactive=True and no audience_context
    - Planner: skipped when test_case provides components (→ style_resolver)
    - style_resolver: runs once; multi-slide loop re-enters context_builder directly
    - Critic: skipped when critic_mode="off"
    - slide_router: only reachable when slide_plans has >1 entry
    - deck_assembler: combines all slides into one PPTX, runs final compile
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import END, START, StateGraph

from src.agents.context_builder import context_builder_node
from src.agents.critic import critic_node
from src.agents.deck_nodes import deck_assembler_node, slide_router_node
from src.agents.evaluator import evaluator_node
from src.agents.generator import generator_node
from src.agents.planner import planner_node
from src.agents.questionnaire import questionnaire_node
from src.agents.repairer import repairer_node
from src.agents.style_resolver import style_resolver_node
from src.agents.validator import validator_node
from src.state import PresentationState, initial_state

logger = logging.getLogger(__name__)


# ── Routing functions ───────────────────────────────────────────────────────

def route_after_start(state: PresentationState) -> str:
    """Route to questionnaire (interactive), planner, or style_resolver."""
    test_case = state.get("test_case") or {}
    if test_case.get("components"):
        logger.info("route: skipping planner (test_case has components)")
        return "style_resolver"
    if state.get("interactive") and not state.get("audience_context"):
        logger.info("route: → questionnaire")
        return "questionnaire"
    logger.info("route: → planner")
    return "planner"


def _slide_done_target(state: PresentationState) -> str:
    """Return 'slide_router' for multi-slide decks, 'evaluator' for single."""
    slide_plans = state.get("slide_plans", [])
    if len(slide_plans) > 1:
        return "slide_router"
    return "evaluator"


def route_after_validator(state: PresentationState) -> str:
    """If compile failed and retryable → repairer; else → critic or done."""
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

    mode = state.get("critic_mode", "auto")
    if mode == "off":
        target = _slide_done_target(state)
        logger.info(f"route: compile ok, critic off → {target}")
        return target
    logger.info("route: compile ok → critic")
    return "critic"


def route_after_critic(state: PresentationState) -> str:
    """If critic failed → repairer (within budget); else → done."""
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
    """If more slides remain → context_builder; else → deck_assembler."""
    idx = state.get("current_slide_index", 0)
    total = len(state.get("slide_plans", []))
    if idx < total:
        logger.info(f"route: slide {idx}/{total} → context_builder")
        return "context_builder"
    logger.info(f"route: all {total} slides done → deck_assembler")
    return "deck_assembler"


def route_after_repairer(state: PresentationState) -> str:
    """Loop back to validator — repairer already called the LLM and produced XML."""
    return "validator"


# ── Graph construction ──────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct the presentation pipeline graph (uncompiled)."""
    graph = StateGraph(PresentationState)

    graph.add_node("questionnaire", questionnaire_node)
    graph.add_node("planner", planner_node)
    graph.add_node("style_resolver", style_resolver_node)
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("generator", generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("repairer", repairer_node)
    graph.add_node("slide_router", slide_router_node)
    graph.add_node("deck_assembler", deck_assembler_node)
    graph.add_node("evaluator", evaluator_node)

    graph.add_conditional_edges(START, route_after_start,
                                ["questionnaire", "planner", "style_resolver"])
    graph.add_edge("questionnaire", "planner")
    graph.add_edge("planner", "style_resolver")
    graph.add_edge("style_resolver", "context_builder")
    graph.add_edge("context_builder", "generator")
    graph.add_edge("generator", "validator")
    graph.add_conditional_edges("validator", route_after_validator,
                                ["repairer", "critic", "evaluator", "slide_router"])
    graph.add_conditional_edges("critic", route_after_critic,
                                ["repairer", "evaluator", "slide_router"])
    graph.add_conditional_edges("repairer", route_after_repairer,
                                ["validator"])
    graph.add_conditional_edges("slide_router", route_after_slide_router,
                                ["context_builder", "deck_assembler"])
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
    critic_mode: Literal["auto", "manual", "off"] = "auto",
    deck_min_threshold: int = 3,
    run_id: str | None = None,
    supplied_content: dict[str, Any] | None = None,
    test_case: dict[str, Any] | None = None,
    audience_context: dict[str, str] | None = None,
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

    eval_data = result.get("evaluation")
    if eval_data:
        print("\n== Evaluation ==")
        print(json.dumps(eval_data, indent=2))
