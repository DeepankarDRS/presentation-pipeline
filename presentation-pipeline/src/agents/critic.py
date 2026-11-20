"""Critic: the slide's quality gate after it compiled (2026-11-20 redesign).

Code first, then eyes:
  1. What code measured and could not fix (fit-grow's SLIDE_DENSE spills, a geometry-audit spill / collision / off-slide
     at tier error, POM shrinking the slide) goes straight to the fixer as a re-layout: no vision call.
  2. Otherwise the vision critic judges the slide per component (slide_facts: ids, boxes, marks, measured facts).
Findings a code-drawn component causes by drawing itself wrongly (owner code_defect) are also written to the run's
code-defects.jsonl, for a fix in code. One fix per slide; the fixer keeps or rolls back its own edit (code checks).

Reads:  compile_result, normalize_result, layout_issues, slide_plans, current_slide_index, theme_element, run_id
Writes: critic_result, visual_critic_result, slide_screenshots, generation_history
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.agents import slide_facts
from src.agents.visual_critic import run_visual_critic
from src.compiler.screenshot import render_screenshots
from src.state import CriticResult, PresentationState, VisualCriticResult
from src.utils.llm_client import usage_record

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent


def slide_context(state: PresentationState) -> tuple[dict, list[slide_facts.Component], list[slide_facts.Fact]]:
    """The slide's plan, its components (ids, boxes, marks) and what code measured about them."""
    idx = state.get("current_slide_index", 0)
    plans = state.get("slide_plans") or []
    plan = plans[idx] if idx < len(plans) else {}
    cr = state.get("compile_result") or {}
    norm = state.get("normalize_result") or {}
    geo = Path(cr["pptx_path"]).parent / "geometry.json" if cr.get("pptx_path") else None
    comps = slide_facts.components(plan, norm, geo, norm.get("tags_xml") or "")
    facts = slide_facts.measured_facts(comps, cr.get("warnings"), state.get("layout_issues"))
    return plan, comps, facts


def _screenshot(state: PresentationState) -> str | None:
    cr = state.get("compile_result") or {}
    out = _ROOT / "output" / "runs" / state.get("run_id", "unknown") / "screenshots" / f"slide-{state.get('current_slide_index', 0)}"
    batch = render_screenshots(cr["pptx_path"], str(out))
    if not batch.ok or not batch.slides or not batch.slides[0].png_path:
        logger.warning(f"critic: screenshot failed: {batch.error}")
        return None
    return batch.slides[0].png_path


def _log_code_defects(state: PresentationState, issues: list[dict[str, Any]]) -> None:
    """Append the code_defect findings to output/runs/<run_id>/code-defects.jsonl (one fix in code covers every deck)."""
    found = [i for i in issues if i.get("owner") == "code_defect"]
    if not found:
        return
    path = _ROOT / "output" / "runs" / state.get("run_id", "unknown") / "code-defects.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for i in found:
            f.write(json.dumps({"slide": state.get("current_slide_index", 0), "component": i.get("component"),
                                "severity": i["severity"], "check": i.get("check"),
                                "description": i["description"]}, ensure_ascii=False) + "\n")
    logger.info(f"critic: {len(found)} code defect(s) logged to {path}")


def _result(passed: bool, issues: list[dict[str, Any]], shot: str | None, hints: dict[str, Any]) -> dict[str, Any]:
    return {"critic_result": CriticResult(passed=passed, issues=issues),
            "visual_critic_result": VisualCriticResult(passed=passed, issues=issues, screenshot_path=shot,
                                                       repair_hints=hints)}


def critic_node(state: PresentationState) -> dict[str, Any]:
    """Quality gate: code-measured defects first, then the vision critic."""
    try:
        return _critic_inner(state)
    except Exception as exc:
        logger.error(f"critic: unhandled error, failing open: {exc}")
        return _result(True, [], None, {"strategy": "none", "assessment": "good", "affected_nodes": []})


def _critic_inner(state: PresentationState) -> dict[str, Any]:
    idx = state.get("current_slide_index", 0)
    cr = state.get("compile_result") or {}
    if not cr.get("ok") or not cr.get("pptx_path"):
        return _result(True, [], None, {"strategy": "none", "assessment": "good", "affected_nodes": []})

    plan, comps, facts = slide_context(state)
    shot = _screenshot(state)
    updates: dict[str, Any] = {}
    if shot:
        updates["slide_screenshots"] = {**(state.get("slide_screenshots") or {}), idx: shot}

    defects = [f for f in facts if f.defect]
    if defects:
        # code measured it: the fixer re-lays the slide out, no vision call (user decision 2026-11-20)
        issues = [{"severity": "high", "type": "structure", "description": f"[Measured] {f.text}", "fix": "",
                   "affected_nodes": [f.component] if f.component else [], "source": "code",
                   "component": f.component, "owner": "slide", "check": "visible_defect"} for f in defects]
        for f in defects:
            logger.info(f"critic: measured defect: {f.text}")
        logger.info(f"critic: passed=False, issues={len(defects)}, strategy=relayout "
                    f"({len(defects)} measured defect(s), no vision review)")
        updates.update(_result(False, issues, shot, {"strategy": "relayout", "assessment": "layout_broken",
                                                     "affected_nodes": sorted({f.component for f in defects if f.component})}))
        return updates

    if not shot:   # without a picture there is nothing to judge: the slide passes (logged above)
        updates.update(_result(True, [], None, {"strategy": "none", "assessment": "good", "affected_nodes": []}))
        return updates

    marked = slide_facts.draw_marks(shot, comps, Path(shot).with_name("marked.png"))
    norm = state.get("normalize_result") or {}
    issues, usage, hints = run_visual_critic(
        screenshot_path=shot,
        current_xml=norm.get("tags_xml") or state.get("current_xml", ""),
        slide_plan=plan,
        theme_element=state.get("theme_element", ""),
        compile_warnings=cr.get("warnings"),
        components=comps,
        facts=[f.text for f in facts],
        marked_path=marked,
    )
    _log_code_defects(state, issues)
    passed = hints.get("strategy") == "none"
    logger.info(f"critic: passed={passed}, issues={len(issues)}, strategy={hints.get('strategy')}")
    updates.update(_result(passed, issues, shot, hints))
    if usage.get("tokens_in", 0) > 0:
        updates["generation_history"] = [usage_record(usage, "critic", idx)]
    return updates
