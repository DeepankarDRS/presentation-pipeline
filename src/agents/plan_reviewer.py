"""Plan reviewer agent — evaluates assembled deck plan quality.

Runs after all slide plans are assembled and sorted. Reviews the complete
deck holistically: narrative coherence, content density, component
appropriateness, layout variety, and cross-slide consistency.

Provides a confidence_score and issues list. Always routes to style_resolver
after review — the score/issues inform downstream monitoring and the existing
critic/repairer handle quality at the XML level.

Reads:  slide_plans, outline_plan (for core_hook)
Writes: plan_review
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.plan_reviewer_schema import PlanReviewerOutput
from src.state import PresentationState
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "plan_reviewer"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def plan_reviewer_node(state: PresentationState) -> dict[str, Any]:
    """Review the assembled slide plans and emit a confidence score."""
    slide_plans = state.get("slide_plans") or []
    if not slide_plans:
        logger.warning("plan_reviewer: no slide_plans to review")
        return {
            "plan_review": {
                "confidence_score": 0.5,
                "approved": True,
                "summary": "No slide plans to review.",
                "issues": [],
            }
        }

    outline = state.get("outline_plan") or {}
    core_hook = outline.get("core_hook") or state.get("core_hook", "")

    user_msg = _jinja_env.get_template("user.j2").render(
        slide_plans=slide_plans,
        core_hook=core_hook,
    )
    system_msg = _jinja_env.get_template("system.j2").render()

    llm = get_llm("plan_reviewer")
    structured_llm = llm.with_structured_output(PlanReviewerOutput, method="json_schema")

    result: PlanReviewerOutput = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])

    high_issues = [i for i in result.issues if i.severity == "high"]
    medium_issues = [i for i in result.issues if i.severity == "medium"]

    logger.info(
        f"plan_reviewer: confidence={result.confidence_score:.2f}, "
        f"approved={result.approved}, "
        f"issues={len(result.issues)} (high={len(high_issues)}, medium={len(medium_issues)})"
    )
    if high_issues:
        for issue in high_issues:
            slide_ref = f"slide {issue.slide_index + 1}" if issue.slide_index is not None else "deck"
            logger.warning(
                f"plan_reviewer: HIGH [{issue.type}] on {slide_ref}: {issue.description}"
            )

    return {
        "plan_review": {
            "confidence_score": result.confidence_score,
            "approved": result.approved,
            "summary": result.summary,
            "issues": [i.model_dump() for i in result.issues],
        }
    }
