"""Planning v2 as its own LangGraph graph (Test 1). M2 plugs it into src/graph.py as one node.

START → index_brief → plan_storyline ⇄ check_storyline → Send × N → design_slide → to_slide_plans → END

- check_storyline sends the storyline back once with the issue list.
- design_slide runs its own check-and-re-ask loop, so each Send branch returns exactly one design
  (the fan-in reducer merges by slide index; a graph-level retry would not duplicate either).
- Concurrency of the fan-out is capped with `max_concurrency` in the invoke config.
"""

from __future__ import annotations

import json
import logging
import operator
from pathlib import Path
from typing import Annotated, Any, TypedDict

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.planning.adapter import to_slide_plan
from src.planning.brief_index import by_id, index_brief, render_blocks
from src.planning.checks import apply_headline_blocks, check_slide, check_storyline, fill_design
from src.planning.schemas import SlideDesign, Storyline
from src.utils.llm_client import get_llm, unpack_raw

logger = logging.getLogger(__name__)

STORYLINE_RETRIES = 1
SLIDE_RETRIES = 2
MAX_CONCURRENCY = 6

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
_env = Environment(loader=FileSystemLoader(str(_PROMPTS)), trim_blocks=True, lstrip_blocks=True)


def _merge(a: dict | None, b: dict | None) -> dict:
    return {**(a or {}), **(b or {})}


class PlanningState(TypedDict, total=False):
    brief: str
    target_slides: int | None
    deck_settings: dict[str, Any]
    index: dict[str, Any]
    storyline: dict[str, Any]
    storyline_issues: list[str]
    storyline_attempts: int
    designs: Annotated[dict[int, dict[str, Any]], _merge]
    slide_plans: list[dict[str, Any]]
    calls: Annotated[list[dict[str, Any]], operator.add]


def _call(step: str, schema, system: str, user: str):
    llm = get_llm(step).with_structured_output(schema, method="json_schema", include_raw=True)
    result, usage = unpack_raw(llm.invoke([SystemMessage(content=system), HumanMessage(content=user)]))
    return result.model_dump(), {"step": step, **usage}


# ── Nodes ───────────────────────────────────────────────────────────────────

def index_brief_node(state: PlanningState) -> dict[str, Any]:
    index = index_brief(state["brief"])
    logger.info(f"index_brief: {len(index['blocks'])} blocks, {len(index['numbers'])} numbers")
    return {"index": index}


def plan_storyline_node(state: PlanningState) -> dict[str, Any]:
    attempts = state.get("storyline_attempts", 0)
    retry = attempts > 0 and state.get("storyline")
    user = _env.get_template("storyline/user.j2").render(
        target_slides=state.get("target_slides"), deck_settings=state.get("deck_settings") or {},
        blocks=render_blocks(state["index"]["blocks"]),
        previous=json.dumps(state["storyline"], ensure_ascii=False) if retry else "",
        issues=state.get("storyline_issues") or [])
    story, usage = _call("storyline", Storyline, _env.get_template("storyline/system.j2").render(), user)
    logger.info(f"plan_storyline: attempt {attempts + 1}, {len(story['slides'])} slides")
    return {"storyline": story, "storyline_attempts": attempts + 1, "calls": [usage]}


def check_storyline_node(state: PlanningState) -> dict[str, Any]:
    story = state["storyline"]
    apply_headline_blocks(story, state["index"])
    issues = check_storyline(story, state["index"], state.get("target_slides"))
    logger.info(f"check_storyline: {len(issues)} issue(s)")
    return {"storyline": story, "storyline_issues": issues}


def route_after_storyline_check(state: PlanningState) -> str | list[Send]:
    if state.get("storyline_issues") and state.get("storyline_attempts", 0) <= STORYLINE_RETRIES:
        return "plan_storyline"
    story, index = state["storyline"], state["index"]
    blocks = by_id(index)
    groups: dict[str, list[int]] = {}
    for s in story["slides"]:
        if s.get("parallel_group"):
            groups.setdefault(s["parallel_group"], []).append(s["slide_index"] + 1)
    sends = []
    for s in story["slides"]:
        own = [blocks[b] for b in s.get("block_ids", []) if b in blocks]
        sends.append(Send("design_slide", {
            "slide": s, "slide_blocks": own, "index": {"blocks": own, "numbers": index["numbers"]},
            "deck": {"deck_argument": story.get("deck_argument", ""),
                     "audience_and_use": story.get("audience_and_use", ""),
                     "total_slides": len(story["slides"])},
            "parallel": groups.get(s.get("parallel_group") or "", []),
        }))
    return sends


def design_slide(payload: dict[str, Any]) -> dict[str, Any]:
    """Design one slide: LLM → fill → check → re-ask with the issues (≤ SLIDE_RETRIES). Keeps the best try."""
    story, index, deck = payload["slide"], payload["index"], payload["deck"]
    system = _env.get_template("slide_designer/system.j2").render()
    best, calls, previous, issues = None, [], "", []
    for attempt in range(SLIDE_RETRIES + 1):
        user = _env.get_template("slide_designer/user.j2").render(
            story=story, total_slides=deck["total_slides"], deck_argument=deck["deck_argument"],
            audience_and_use=deck["audience_and_use"], parallel=payload.get("parallel") or [],
            blocks=render_blocks(payload["slide_blocks"]) or "(no blocks: a statement slide)",
            previous=previous, issues=issues)
        design, usage = _call("slide_designer", SlideDesign, system, user)
        calls.append(usage)
        filled = fill_design(design, index)
        issues = check_slide(filled, story, index)
        if best is None or len(issues) < len(best["issues"]):
            best = {**filled, "issues": issues}
        if not issues:
            break
        previous = json.dumps(design, ensure_ascii=False)
    best["attempts"] = len(calls)
    logger.info(f"design_slide {story['slide_index'] + 1}: {len(calls)} call(s), {len(best['issues'])} issue(s) left")
    return {"designs": {story["slide_index"]: best}, "calls": calls}


def to_slide_plans_node(state: PlanningState) -> dict[str, Any]:
    story = state["storyline"]
    plans = [to_slide_plan(s, state["designs"].get(s["slide_index"], {"components": []})) for s in story["slides"]]
    return {"slide_plans": plans}


# ── Graph ───────────────────────────────────────────────────────────────────

def build_planning_graph() -> StateGraph:
    g = StateGraph(PlanningState)
    g.add_node("index_brief", index_brief_node)
    g.add_node("plan_storyline", plan_storyline_node)
    g.add_node("check_storyline", check_storyline_node)
    g.add_node("design_slide", design_slide)
    g.add_node("to_slide_plans", to_slide_plans_node)
    g.add_edge(START, "index_brief")
    g.add_edge("index_brief", "plan_storyline")
    g.add_edge("plan_storyline", "check_storyline")
    g.add_conditional_edges("check_storyline", route_after_storyline_check, ["plan_storyline", "design_slide"])
    g.add_edge("design_slide", "to_slide_plans")
    g.add_edge("to_slide_plans", END)
    return g


def run_planning(brief: str, *, target_slides: int | None = None, deck_settings: dict[str, Any] | None = None,
                 max_concurrency: int = MAX_CONCURRENCY) -> PlanningState:
    app = build_planning_graph().compile()
    return app.invoke({"brief": brief, "target_slides": target_slides, "deck_settings": deck_settings or {},
                       "storyline_attempts": 0, "designs": {}, "calls": []},
                      config={"max_concurrency": max_concurrency, "recursion_limit": 50})
