"""LangGraph pipeline definition.

Topology:
    START → planner → context_builder → generator → validator
      → (if compile fails & retryable) repairer → generator  (loop)
      → (if compile ok) critic
      → (if critic fails) repairer → generator  (loop)
      → evaluator → END

Conditional edges:
    - Planner: skipped when deck_min_threshold=0 AND single slide
    - Critic: skipped when critic_mode="off"
    - Repairer → Generator: loops up to retry_budget times
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from src.agents.context_builder import context_builder_node
from src.agents.critic import critic_node
from src.agents.evaluator import evaluator_node
from src.agents.generator import generator_node
from src.agents.planner import planner_node
from src.agents.repairer import repairer_node
from src.agents.validator import validator_node
from src.state import PresentationState, initial_state

logger = logging.getLogger(__name__)


# ── Routing functions ───────────────────────────────────────────────────────

def route_after_start(state: PresentationState) -> str:
    """Skip planner when deck_min_threshold=0 and single slide."""
    threshold = state.get("deck_min_threshold", 3)
    if threshold == 0:
        logger.info("route: skipping planner (deck_min_threshold=0)")
        return "context_builder"
    return "planner"


def route_after_validator(state: PresentationState) -> str:
    """If compile failed and retryable → repairer; else → critic or evaluator."""
    cr = state.get("compile_result") or {}
    if not cr.get("ok", False) and cr.get("retryable", False):
        budget = state.get("retry_budget", 3)
        count = state.get("retry_count", 0)
        if count < budget:
            logger.info(f"route: compile failed, retry {count+1}/{budget} → repairer")
            return "repairer"
        logger.info("route: compile failed but retry budget exhausted → evaluator")
        return "evaluator"

    mode = state.get("critic_mode", "auto")
    if mode == "off":
        logger.info("route: compile ok, critic off → evaluator")
        return "evaluator"
    logger.info("route: compile ok → critic")
    return "critic"


def route_after_critic(state: PresentationState) -> str:
    """If critic failed → repairer (within budget); else → evaluator."""
    cr = state.get("critic_result") or {}
    if not cr.get("passed", True):
        budget = state.get("retry_budget", 3)
        count = state.get("retry_count", 0)
        if count < budget:
            logger.info(f"route: critic failed, retry {count+1}/{budget} → repairer")
            return "repairer"
        logger.info("route: critic failed but retry budget exhausted → evaluator")
    return "evaluator"


def route_after_repairer(state: PresentationState) -> str:
    """Always loop back to generator for another attempt."""
    return "generator"


# ── Graph construction ──────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct the presentation pipeline graph (uncompiled)."""
    graph = StateGraph(PresentationState)

    graph.add_node("planner", planner_node)
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("generator", generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("critic", critic_node)
    graph.add_node("repairer", repairer_node)
    graph.add_node("evaluator", evaluator_node)

    graph.add_conditional_edges(START, route_after_start,
                                ["planner", "context_builder"])
    graph.add_edge("planner", "context_builder")
    graph.add_edge("context_builder", "generator")
    graph.add_edge("generator", "validator")
    graph.add_conditional_edges("validator", route_after_validator,
                                ["repairer", "critic", "evaluator"])
    graph.add_conditional_edges("critic", route_after_critic,
                                ["repairer", "evaluator"])
    graph.add_conditional_edges("repairer", route_after_repairer,
                                ["generator"])
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
    deck_min_threshold: int = 0,
    run_id: str | None = None,
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
    result = run(request)

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
