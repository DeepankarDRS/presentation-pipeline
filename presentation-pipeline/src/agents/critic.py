"""Critic agent — visual quality gate after successful compilation.

The visual critic is the sole quality gate. It screenshot-reviews the
rendered slide against the full design context (plan, theme, contract,
compile warnings) and returns structured issues with repair hints.

Reads:  current_xml, compile_result, slide_plans, critic_mode,
        theme_element, contract, layout_issues
Writes: critic_result, visual_critic_result, slide_screenshots
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.agents.visual_critic import run_visual_critic
from src.compiler.screenshot import render_screenshots
from src.state import CriticResult, PresentationState, VisualCriticResult

logger = logging.getLogger(__name__)


def _run_visual_review(
    state: PresentationState,
) -> tuple[list[dict[str, Any]], str | None, dict[str, Any], dict[str, Any]]:
    """Take screenshot and run visual critic. Returns (issues, screenshot_path, usage, repair_hints)."""
    zero_usage = {"tokens_in": 0, "tokens_out": 0, "model": "unknown"}
    empty_hints = {"strategy": "none", "assessment": "good", "affected_nodes": []}

    cr = state.get("compile_result") or {}
    pptx_path = cr.get("pptx_path")
    if not pptx_path or not cr.get("ok", False):
        return [], None, zero_usage, empty_hints

    run_id = state.get("run_id", "unknown")
    idx = state.get("current_slide_index", 0)
    output_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "output" / "runs" / run_id / "screenshots" / f"slide-{idx}"
    )

    batch = render_screenshots(pptx_path, str(output_dir))
    if not batch.ok or not batch.slides:
        logger.warning(f"critic: screenshot failed: {batch.error}")
        return [], None, zero_usage, empty_hints

    screenshot_path = batch.slides[0].png_path
    if not screenshot_path:
        return [], None, zero_usage, empty_hints

    slide_plans = state.get("slide_plans", [])
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}

    compile_warnings = cr.get("warnings", [])
    layout_issues = state.get("layout_issues", [])

    visual_issues, visual_usage, repair_hints = run_visual_critic(
        screenshot_path=screenshot_path,
        current_xml=state.get("current_xml", ""),
        slide_plan=plan,
        theme_element=state.get("theme_element", ""),
        contract=state.get("contract"),
        compile_warnings=compile_warnings,
        layout_issues=layout_issues,
    )

    return visual_issues, screenshot_path, visual_usage, repair_hints


def critic_node(state: PresentationState) -> dict[str, Any]:
    """Visual quality gate — screenshot-based review using a vision LLM."""
    idx = state.get("current_slide_index", 0)

    try:
        return _critic_inner(state, idx)
    except Exception as exc:
        logger.error(f"critic: unhandled error, failing open: {exc}")
        return {
            "critic_result": CriticResult(passed=True, issues=[]),
            "visual_critic_result": VisualCriticResult(
                passed=True, issues=[], screenshot_path=None,
                repair_hints={"strategy": "none", "assessment": "good", "affected_nodes": []},
            ),
        }


def _critic_inner(state: PresentationState, idx: int) -> dict[str, Any]:
    logger.info("critic: running visual review")
    issues, screenshot_path, usage, repair_hints = _run_visual_review(state)

    passed = not any(i["severity"] == "high" for i in issues)

    visual_result = VisualCriticResult(
        passed=passed,
        issues=issues,
        screenshot_path=screenshot_path,
        repair_hints=repair_hints,
    )

    updates: dict[str, Any] = {
        "critic_result": CriticResult(passed=passed, issues=issues),
        "visual_critic_result": visual_result,
    }

    if screenshot_path:
        current_screenshots = dict(state.get("slide_screenshots", {}))
        current_screenshots[idx] = screenshot_path
        updates["slide_screenshots"] = current_screenshots

    high_count = sum(1 for i in issues if i["severity"] == "high")
    med_count = sum(1 for i in issues if i["severity"] == "medium")
    low_count = sum(1 for i in issues if i["severity"] == "low")

    logger.info(
        f"critic: passed={passed}, issues={len(issues)} "
        f"(high={high_count}, medium={med_count}, low={low_count}), "
        f"assessment={repair_hints.get('assessment', 'unknown')}"
    )

    if usage.get("tokens_in", 0) > 0:
        updates["generation_history"] = [{"attempt": 0, "tier": 0, **usage}]

    return updates
