"""Visual repairer — one-shot repair after visual critic failure.

Respects the critic's repair_hints.strategy:
  - "patch"      → in-place PATCH fix (1 LLM call)
  - "regenerate" → replan + regenerate the slide (3 LLM calls)

Separate from the main repairer so visual repairs never re-enter the
compile repair loop. If the repaired XML breaks compilation, the repair
is discarded and the original compiled XML is kept.

Reads:  current_xml, visual_critic_result, contract, slide_plans
Writes: current_xml, visual_repair_count, generation_history,
        compile_result, slide_plans, contract (REGENERATE only)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents.context_builder import build_contract
from src.agents.repairer import build_patch_prompts, _build_repair_context, _plan_to_outline_slide
from src.agents.slide_component_planner import plan_single_slide
from src.agents.validator import normalize_and_compile
from src.compiler.repair_guidance import cap_diag_msg
from src.state import AttemptRecord, PresentationState
from src.utils.llm_client import extract_usage, get_llm

logger = logging.getLogger(__name__)

_GENERATOR_DIR = Path(__file__).resolve().parent.parent / "prompts" / "generator"
_gen_env = Environment(
    loader=FileSystemLoader(str(_GENERATOR_DIR)),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _build_visual_problems(visual_issues: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    for issue in visual_issues:
        sev = issue.get("severity", "")
        msg = cap_diag_msg(issue.get("description", ""))
        line = f"VISUAL_{sev.upper()}: {msg}"
        fix_hint = issue.get("fix", "")
        if fix_hint:
            line += f" | Fix: {fix_hint}"
        problems.append(line)
    return problems


def _do_patch(state, plan, problems, visual_issues, contract, theme_el, original_xml, objective):
    """PATCH: one LLM call to fix visual issues in-place."""
    system_prompt, user_prompt = build_patch_prompts(
        failing_xml=original_xml, problems=problems,
        pre_issues=[], compile_diags=[], objective=objective,
        forbidden_tags=contract.get("forbidden_tags", []),
        theme_element=theme_el, visual_issues=visual_issues,
        house_style=contract.get("house_style", ""),
        component_recipes=contract.get("component_recipes", ""),
        visual_only=True,
    )
    response = get_llm("repairer").invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return response.content, extract_usage(response), response, {}


def _do_regenerate(state, plan, problems, contract, theme_el, idx):
    """REGENERATE: replan the slide + generate fresh XML."""
    repair_ctx = _build_repair_context(plan, problems, visual_failure=True, has_compile_errors=False)
    outline_slide = _plan_to_outline_slide(plan)
    outline_plan = {"core_hook": state.get("core_hook", ""), "slides": [outline_slide]}

    new_plan, _ = plan_single_slide(
        outline_slide,
        outline_plan=outline_plan,
        deck_settings=state.get("deck_settings"),
        supplied_content=state.get("supplied_content"),
        repair_context=repair_ctx,
    )
    new_plan["slide_index"] = plan.get("slide_index", 0)

    theme_info = state.get("resolved_theme") or {}
    new_contract = build_contract(new_plan, theme_info)

    system_prompt = _gen_env.get_template("system.j2").render(
        forbidden_tags=new_contract.get("forbidden_tags", []),
        forbidden_attributes=new_contract.get("forbidden_attributes", []),
        theme_element=new_contract.get("theme_element", theme_el),
        allowed_nodes=new_contract.get("allowed_nodes", []),
        allowed_attributes=new_contract.get("allowed_attributes", {}),
        node_hierarchy=new_contract.get("node_hierarchy", ""),
        component_count=new_contract.get("component_count", 0),
        house_style=new_contract.get("house_style", ""),
        component_recipes=new_contract.get("component_recipes", ""),
        notes=new_contract.get("notes", []),
        core_hook=state.get("core_hook", ""),
        slide_type=new_plan.get("slide_type", ""),
    )
    user_prompt = _gen_env.get_template("user.j2").render(
        objective=state.get("raw_request", ""),
        slide_title=new_plan.get("slide_title", ""),
        core_hook=state.get("core_hook", ""),
        components=new_plan.get("components", []),
        layout_hint=new_plan.get("layout_hint", ""),
        content_data=new_plan.get("content_data", {}),
        supplied_content=state.get("supplied_content"),
        slide_type=new_plan.get("slide_type", ""),
    )

    response = get_llm("generator").invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    slide_plans = list(state.get("slide_plans", []))
    slide_plans[idx] = new_plan

    return response.content, extract_usage(response), response, {
        "slide_plans": slide_plans, "contract": new_contract,
    }


def visual_repairer_node(state: PresentationState) -> dict[str, Any]:
    """One-shot repair for visual issues. Discards if compile breaks."""
    visual_cr = state.get("visual_critic_result") or {}
    visual_issues = visual_cr.get("issues", [])
    hints = visual_cr.get("repair_hints") or {}
    strategy = hints.get("strategy", "patch")
    count = state.get("visual_repair_count", 0) + 1

    contract = state.get("contract") or {}
    slide_plans = state.get("slide_plans", [])
    idx = state.get("current_slide_index", 0)
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}
    objective = plan.get("slide_title") or state.get("raw_request", "")
    original_xml = state.get("current_xml", "")
    theme_el = contract.get("theme_element", state.get("theme_element", ""))

    problems = _build_visual_problems(visual_issues)
    logger.info(f"visual_repairer: {strategy.upper()}, {len(problems)} visual problem(s)")

    try:
        if strategy == "regenerate":
            xml, usage, response, extra = _do_regenerate(
                state, plan, problems, contract, theme_el, idx,
            )
        else:
            xml, usage, response, extra = _do_patch(
                state, plan, problems, visual_issues, contract,
                theme_el, original_xml, objective,
            )
    except Exception as exc:
        logger.error(f"visual_repairer: {strategy} failed: {exc}")
        return {"visual_repair_count": count}

    if response.response_metadata.get("finish_reason") == "length":
        logger.warning("visual_repairer: output truncated — discarding")
        return {"visual_repair_count": count}

    if strategy != "regenerate" and xml.strip() == original_xml.strip():
        logger.warning("visual_repairer: identical XML — no progress")
        return {"visual_repair_count": count}

    run_id = state.get("run_id", "unknown")
    _pipeline_root = Path(__file__).resolve().parent.parent.parent
    out_dir = _pipeline_root / "output" / "runs" / run_id / f"visual-repair-{count}"
    compile_ok, new_cr = normalize_and_compile(xml, theme_el, out_dir)

    tier = 2 if strategy == "regenerate" else 1
    record = AttemptRecord(
        attempt=state.get("retry_count", 0) + 1, tier=tier,
        errors_in=problems, errors_out=[], error_sigs=[],
        stalled=False, truncated=False, noop=False,
        tokens_in=usage["tokens_in"], tokens_out=usage["tokens_out"],
        model=usage["model"],
    )

    if not compile_ok:
        logger.warning("visual_repairer: repair broke compilation — discarding")
        return {"visual_repair_count": count, "generation_history": [record]}

    logger.info(f"visual_repairer: compiled OK — accepting ({usage['model']})")
    result = {
        "current_xml": xml,
        "compile_result": new_cr,
        "visual_repair_count": count,
        "generation_history": [record],
    }
    result.update(extra)
    return result
