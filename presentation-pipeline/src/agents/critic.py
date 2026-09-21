"""Critic agent — visual quality gate after successful compilation.

The visual critic is the sole quality gate. It screenshot-reviews the
rendered slide against the full design context (plan, theme, contract,
compile warnings) and returns structured issues with repair hints.

With visual_repair_budget >= 2, the critic runs a re-screenshot loop:
  critic₁ → repair₁ → critic₂ → (compare scores) → ship best version.
On round 2 the critic receives the previous issues so it can confirm
fixes and only report remaining or new problems.

Reads:  current_xml, compile_result, slide_plans, critic_mode,
        theme_element, contract, layout_issues, visual_repair_count,
        visual_critic_result, pre_critic_xml
Writes: critic_result, visual_critic_result, slide_screenshots,
        pre_critic_xml, pre_critic_slide_plans, pre_critic_contract,
        pre_critic_score, current_xml, slide_plans, contract
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.agents.visual_critic import run_visual_critic
from src.compiler.layout_audit import audit_layout
from src.compiler.screenshot import render_screenshots
from src.state import CriticResult, PresentationState, VisualCriticResult

logger = logging.getLogger(__name__)

_ASSESSMENT_PENALTY = {"layout_broken": 15, "needs_tuning": 5, "good": 0}


def compute_critic_score(issues: list[dict[str, Any]], assessment: str) -> int:
    """Deterministic score from critic output. Higher is better (max 0)."""
    score = 0
    for i in issues:
        sev = i.get("severity", "low")
        if sev == "high":
            score -= 10
        elif sev == "medium":
            score -= 3
        else:
            score -= 1
    score -= _ASSESSMENT_PENALTY.get(assessment, 0)
    return score


def _run_visual_review(
    state: PresentationState,
    previous_issues: list[dict[str, Any]] | None = None,
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
    v_count = state.get("visual_repair_count", 0)
    output_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "output" / "runs" / run_id / "screenshots" / f"slide-{idx}"
    )
    if v_count > 0:
        output_dir = output_dir / f"re-review-{v_count}"

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
    if v_count > 0:
        current_xml = state.get("current_xml", "")
        try:
            layout_issues = audit_layout(current_xml)
        except Exception:
            pass

    visual_issues, visual_usage, repair_hints = run_visual_critic(
        screenshot_path=screenshot_path,
        current_xml=state.get("current_xml", ""),
        slide_plan=plan,
        theme_element=state.get("theme_element", ""),
        contract=state.get("contract"),
        compile_warnings=compile_warnings,
        layout_issues=layout_issues,
        previous_issues=previous_issues,
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
    v_count = state.get("visual_repair_count", 0)
    is_re_review = v_count > 0

    previous_issues = None
    if is_re_review:
        prev_vcr = state.get("visual_critic_result") or {}
        previous_issues = prev_vcr.get("issues", [])

    round_label = f"re-review (round {v_count + 1})" if is_re_review else "initial review"
    logger.info(f"critic: running {round_label}")

    issues, screenshot_path, usage, repair_hints = _run_visual_review(
        state, previous_issues=previous_issues,
    )

    passed = not any(i["severity"] == "high" for i in issues)
    assessment = repair_hints.get("assessment", "good")
    current_score = compute_critic_score(issues, assessment)

    if is_re_review:
        repair_hints = _constrain_round2_strategy(repair_hints)

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

    if not is_re_review:
        updates["pre_critic_xml"] = state.get("current_xml", "")
        updates["pre_critic_slide_plans"] = list(state.get("slide_plans", []))
        updates["pre_critic_contract"] = state.get("contract")
        updates["pre_critic_score"] = current_score

    if is_re_review and not passed:
        pre_score = state.get("pre_critic_score", 0)
        if current_score <= pre_score:
            verb = "no better" if current_score == pre_score else "worse"
            logger.info(
                f"critic: repair {verb} (score {current_score} vs {pre_score}) "
                f"— rolling back to original XML"
            )
            updates["current_xml"] = state["pre_critic_xml"]
            updates["slide_plans"] = state["pre_critic_slide_plans"]
            updates["contract"] = state["pre_critic_contract"]
            updates["critic_result"] = CriticResult(passed=True, issues=issues)
            visual_result["passed"] = True
            repair_hints["strategy"] = "none"
            updates["visual_critic_result"] = visual_result

    if screenshot_path:
        current_screenshots = dict(state.get("slide_screenshots", {}))
        current_screenshots[idx] = screenshot_path
        updates["slide_screenshots"] = current_screenshots

    high_count = sum(1 for i in issues if i["severity"] == "high")
    med_count = sum(1 for i in issues if i["severity"] == "medium")
    low_count = sum(1 for i in issues if i["severity"] == "low")

    logger.info(
        f"critic: passed={passed}, score={current_score}, issues={len(issues)} "
        f"(high={high_count}, medium={med_count}, low={low_count}), "
        f"assessment={assessment}"
    )

    if usage.get("tokens_in", 0) > 0:
        updates["generation_history"] = [{"attempt": 0, "tier": 0, **usage}]

    return updates


def _constrain_round2_strategy(repair_hints: dict[str, Any]) -> dict[str, Any]:
    """Force patch-only on round 2 — no double-regenerate."""
    if repair_hints.get("strategy") == "regenerate":
        logger.info("critic: downgrading round-2 strategy from regenerate to patch")
        repair_hints["strategy"] = "patch"
    return repair_hints
