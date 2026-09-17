"""Repairer agent — two repair strategies.

PATCH:      feed back failing XML + errors + guidance → fix in place.
REGENERATE: re-plan the slide (via slide_component_planner with error context),
            rebuild the contract, and call the generator LLM fresh. This avoids
            repeating the same structural mistakes that caused the original failure.

The loop is "PATCH, REGENERATE (replan+generate), cleanup PATCH"
(retry_budget = 3). Strategy per attempt (see _choose_strategy):
- attempt 1 is always PATCH (a cheap in-place fix often works);
- a no-op or truncated previous PATCH, a structural error (needs_regeneration), a
  detected stall, or reaching attempt 2 while still not compiling → REGENERATE;
- the attempt right after a REGENERATE is a PATCH cleanup pass.

When all attempts fail, route_after_validator inserts a placeholder slide.

Reads:  current_xml, normalize_result, validate_result, compile_result,
        critic_result, contract, slide_plans, retry_tier, retry_count,
        generation_history
Writes: current_xml, retry_tier, retry_count, stall_detected, generation_history,
        slide_plans (REGENERATE only), contract (REGENERATE only)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents.context_builder import build_contract
from src.agents.slide_component_planner import plan_single_slide
from src.compiler.repair_guidance import (
    build_error_guidance,
    cap_diag_msg,
    error_signatures,
    is_stalled,
    needs_regeneration,
    select_repair_knowledge,
)
from src.state import AttemptRecord, PresentationState
from src.utils.llm_client import extract_usage, get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_REPAIRER_DIR = _PROMPTS_DIR / "repairer"
_GENERATOR_DIR = _PROMPTS_DIR / "generator"

_repair_env = Environment(
    loader=FileSystemLoader(str(_REPAIRER_DIR)),
    keep_trailing_newline=True,
)
_gen_env = Environment(
    loader=FileSystemLoader(str(_GENERATOR_DIR)),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

_SRC_DIR = Path(__file__).resolve().parent.parent
_EXAMPLES_DIR = _SRC_DIR / "knowledge" / "examples"

PATCH, REGENERATE = 1, 2
_STRATEGY_NAME = {PATCH: "PATCH", REGENERATE: "REGENERATE"}

_MAX_XML_CHARS = 8000
_TRUNC_MARKER = "\n<!-- ... XML truncated for prompt size — middle section omitted ... -->\n"


def _cap_xml(xml: str) -> str:
    """Keep head + tail of XML so root setup and closing tags are visible."""
    if len(xml) <= _MAX_XML_CHARS:
        return xml
    half = (_MAX_XML_CHARS - len(_TRUNC_MARKER)) // 2
    return xml[:half] + _TRUNC_MARKER + xml[-half:]


def _collect_problems(state: PresentationState) -> list[str]:
    """Collect error strings from normalize_result, compile_result, and critic_result."""
    problems: list[str] = []

    norm = state.get("normalize_result") or {}
    for issue in norm.get("issues", []):
        if not issue.get("auto_fixed", False):
            problems.append(f"{issue['code']}: {cap_diag_msg(issue['message'])}")

    cr = state.get("compile_result") or {}
    for diag in cr.get("diagnostics", []):
        problems.append(f"{diag['type']}: {cap_diag_msg(diag['message'])}")

    critic = state.get("critic_result") or {}
    for issue in critic.get("issues", []):
        severity = issue.get("severity", "")
        msg = cap_diag_msg(issue.get("message", str(issue)))
        problems.append(f"CRITIC_{severity.upper()}: {msg}")

    return problems


def _get_pre_issues(state: PresentationState) -> list[dict[str, Any]]:
    norm = state.get("normalize_result") or {}
    return [i for i in norm.get("issues", []) if not i.get("auto_fixed", False)]


def _get_compile_diags(state: PresentationState) -> list[dict[str, Any]]:
    cr = state.get("compile_result") or {}
    return cr.get("diagnostics", [])


def _build_repair_context(plan: dict[str, Any], problems: list[str]) -> dict[str, Any]:
    """Build error context for the slide component planner during REGENERATE."""
    failed_kinds = [c.get("kind", "") for c in plan.get("components", [])]
    return {
        "failed_kinds": failed_kinds,
        "errors": problems[:5],
        "directive": (
            f"The previous plan used components [{', '.join(failed_kinds)}] which "
            f"caused compilation errors. Choose simpler, more reliable component "
            f"types. Prefer text, bullet_list, table over timeline, flow, matrix, "
            f"tree, pyramid."
        ),
    }


def _plan_to_outline_slide(plan: dict[str, Any]) -> dict[str, Any]:
    """Convert a SlidePlan back to a minimal OutlineSlide dict for re-planning."""
    content_data = plan.get("content_data", {})
    key_messages = []
    for comp in plan.get("components", []):
        summary = comp.get("content_summary", "")
        if summary:
            key_messages.append(summary)
    return {
        "slide_index": plan.get("slide_index", 0),
        "slide_title": plan.get("slide_title", content_data.get("title", "")),
        "section": "",
        "narrative_role": "",
        "key_messages": key_messages,
        "visual_emphasis": "",
    }


def build_patch_prompts(
    *,
    failing_xml: str,
    problems: list[str],
    pre_issues: list[dict[str, Any]],
    compile_diags: list[dict[str, Any]],
    objective: str,
    forbidden_tags: list[str],
    theme_element: str,
) -> tuple[str, str]:
    """Build the (system, user) prompts for a PATCH (in-place fix) repair.

    Shared by repairer_node's PATCH branch and the slide edit service's mini
    repair loop, so both get the same error-scoped node reference (attribute
    docs, pitfalls, a verified syntax example) injected into the system prompt.
    """
    failing_xml = _cap_xml(failing_xml)

    knowledge = select_repair_knowledge(pre_issues, compile_diags)
    if knowledge["nodes_involved"]:
        logger.info(f"repairer: knowledge loaded for nodes: {knowledge['nodes_involved']}")

    system_prompt = _repair_env.get_template("system.j2").render(
        forbidden_tags=forbidden_tags,
        theme_element=theme_element,
        knowledge_text=knowledge.get("knowledge_text", ""),
        reference_example=knowledge.get("example", ""),
    )
    user_prompt = _repair_env.get_template("patch.j2").render(
        objective=objective,
        failing_xml=failing_xml,
        problems=problems,
        guidance=build_error_guidance(pre_issues, compile_diags),
    )
    return system_prompt, user_prompt


def _render_repair_system(state: PresentationState, knowledge: dict) -> str:
    """Build a focused repair system prompt with only error-relevant knowledge.

    Instead of re-rendering the full generator system.j2 (all design rules,
    all node attributes, layout vocabulary), this loads the repairer's own
    system.j2 and injects only the knowledge slices for the nodes that had
    errors — attribute docs, pitfalls, and a verified syntax example.
    """
    contract = state.get("contract") or {}
    system_tmpl = _repair_env.get_template("system.j2")
    return system_tmpl.render(
        forbidden_tags=contract.get("forbidden_tags", []),
        theme_element=contract.get("theme_element", state.get("theme_element", "")),
        knowledge_text=knowledge.get("knowledge_text", ""),
        reference_example=knowledge.get("example", ""),
    )


def _choose_strategy(
    *,
    attempt: int,
    prev_strategy: int | None,
    prev_noop: bool,
    prev_truncated: bool,
    regen_error: bool,
    stalled: bool,
    compile_ok: bool,
) -> int:
    """Pick PATCH or REGENERATE for this attempt.

    The loop is "PATCH, REGENERATE (replan+generate), cleanup PATCH". attempt 1 is
    a cheap in-place PATCH. A structural error, a stall, or a previous PATCH that
    was a no-op / got truncated escalates straight to REGENERATE. The attempt right
    after a REGENERATE is a PATCH cleanup pass. Falling back to REGENERATE by attempt
    number only applies while the slide still doesn't compile — rebuilding a slide
    that compiles (only the critic is unhappy) risks losing a working result.
    """
    if attempt == 1:
        return PATCH
    if prev_strategy == REGENERATE:
        return PATCH
    if prev_noop or prev_truncated or regen_error or stalled:
        return REGENERATE
    if attempt >= 2 and not compile_ok:
        return REGENERATE
    return PATCH


def _call_llm_and_return(
    strategy: int,
    current_count: int,
    problems: list[str],
    curr_sigs: set[str],
    stalled: bool,
    failing_xml: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Call the repairer LLM and build the return dict (used by PATCH)."""
    llm = get_llm("repairer")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = llm.invoke(messages)
    repaired_xml = response.content

    usage = extract_usage(response)
    tokens_in = usage["tokens_in"]
    tokens_out = usage["tokens_out"]
    model = usage["model"]
    truncated = response.response_metadata.get("finish_reason") == "length"
    noop = strategy == PATCH and repaired_xml.strip() == failing_xml.strip()
    if truncated:
        logger.warning("repairer: LLM output truncated at max_tokens — repair is incomplete")
    if noop:
        logger.warning("repairer: PATCH returned identical XML — no progress this attempt")

    logger.info(f"repairer: {model} tokens_in={tokens_in} tokens_out={tokens_out}")

    record = AttemptRecord(
        attempt=current_count + 1,
        tier=strategy,
        errors_in=problems,
        errors_out=[],
        error_sigs=sorted(curr_sigs),
        stalled=stalled,
        truncated=truncated,
        noop=noop,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
    )

    return {
        "current_xml": repaired_xml,
        "retry_tier": strategy,
        "retry_count": current_count + 1,
        "stall_detected": stalled,
        "generation_history": [record],
    }


def repairer_node(state: PresentationState) -> dict[str, Any]:
    """Choose a repair strategy, build the prompt, call the LLM, update state."""
    current_count = state.get("retry_count", 0)
    problems = _collect_problems(state)
    pre_issues = _get_pre_issues(state)
    compile_diags = _get_compile_diags(state)

    curr_sigs = error_signatures(pre_issues, compile_diags)

    prev_history = state.get("generation_history", [])
    prev_sigs: set[str] = set()
    for record in reversed(prev_history):
        if record.get("error_sigs"):
            prev_sigs = set(record["error_sigs"])
            break
    prev_strategy = next(
        (r.get("tier") for r in reversed(prev_history)
         if r.get("tier") in (PATCH, REGENERATE)),
        None,
    )
    prev_noop = bool(prev_history[-1].get("noop")) if prev_history else False
    prev_truncated = bool(prev_history[-1].get("truncated")) if prev_history else False

    stalled = current_count > 0 and is_stalled(prev_sigs, curr_sigs)
    regen_error = needs_regeneration(pre_issues, compile_diags)
    compile_ok = bool((state.get("compile_result") or {}).get("ok"))
    strategy = _choose_strategy(
        attempt=current_count + 1,
        prev_strategy=prev_strategy,
        prev_noop=prev_noop,
        prev_truncated=prev_truncated,
        regen_error=regen_error,
        stalled=stalled,
        compile_ok=compile_ok,
    )

    reasons = [r for r, on in
               (("stall", stalled), ("structural", regen_error),
                ("prev-noop", prev_noop), ("prev-truncated", prev_truncated)) if on]
    logger.info(
        f"repairer: attempt {current_count + 1}, {_STRATEGY_NAME[strategy]}"
        + (f" ({', '.join(reasons)})" if reasons else "")
        + f", {len(problems)} problem(s)"
    )

    contract = state.get("contract") or {}
    failing_xml = ""

    slide_plans = state.get("slide_plans", [])
    idx = state.get("current_slide_index", 0)
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}
    objective = plan.get("slide_title") or state.get("raw_request", "")

    if strategy == PATCH:
        norm = state.get("normalize_result") or {}
        failing_xml = norm.get("cleaned_xml", state.get("current_xml", ""))
        system_prompt, user_prompt = build_patch_prompts(
            failing_xml=failing_xml,
            problems=problems,
            pre_issues=pre_issues,
            compile_diags=compile_diags,
            objective=objective,
            forbidden_tags=contract.get("forbidden_tags", []),
            theme_element=contract.get("theme_element", state.get("theme_element", "")),
        )
    else:
        # REGENERATE: re-plan the slide with error context, then re-generate.
        repair_ctx = _build_repair_context(plan, problems)
        outline_slide = _plan_to_outline_slide(plan)
        outline_plan = {
            "core_hook": state.get("core_hook", ""),
            "slides": [outline_slide],
        }

        logger.info(f"repairer: REGENERATE — re-planning slide {idx} with repair context")
        try:
            new_plan, _usage = plan_single_slide(
                outline_slide,
                outline_plan=outline_plan,
                deck_settings=state.get("deck_settings"),
                supplied_content=state.get("supplied_content"),
                repair_context=repair_ctx,
            )
        except Exception as exc:
            logger.warning(f"repairer: plan_single_slide failed, falling back to PATCH: {exc}")
            norm = state.get("normalize_result") or {}
            failing_xml = norm.get("cleaned_xml", state.get("current_xml", ""))
            system_prompt, user_prompt = build_patch_prompts(
                failing_xml=failing_xml,
                problems=problems,
                pre_issues=pre_issues,
                compile_diags=compile_diags,
                objective=objective,
                forbidden_tags=contract.get("forbidden_tags", []),
                theme_element=contract.get("theme_element", state.get("theme_element", "")),
            )
            strategy = PATCH
            return _call_llm_and_return(
                strategy, current_count, problems, curr_sigs, stalled,
                failing_xml, system_prompt, user_prompt,
            )

        new_plan["slide_index"] = plan.get("slide_index", 0)
        updated_plans = list(slide_plans)
        updated_plans[idx] = new_plan

        try:
            theme_info = state.get("resolved_theme") or {}
            new_contract = build_contract(new_plan, theme_info)

            system_prompt = _gen_env.get_template("system.j2").render(
                forbidden_tags=new_contract.get("forbidden_tags", []),
                forbidden_attributes=new_contract.get("forbidden_attributes", []),
                theme_element=new_contract.get("theme_element", state.get("theme_element", "")),
                allowed_nodes=new_contract.get("allowed_nodes", []),
                allowed_attributes=new_contract.get("allowed_attributes", {}),
                node_hierarchy=new_contract.get("node_hierarchy", ""),
                density_tier=new_contract.get("density_tier", "standard"),
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
                density=new_plan.get("density", "normal"),
                font_tier=new_plan.get("font_tier", "standard"),
                layout_hint=new_plan.get("layout_hint", ""),
                content_data=new_plan.get("content_data", {}),
                supplied_content=state.get("supplied_content"),
                slide_type=new_plan.get("slide_type", ""),
            )

            llm = get_llm("generator")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = llm.invoke(messages)
        except Exception as exc:
            logger.warning(f"repairer: REGENERATE failed (contract/render/generate), falling back to PATCH: {exc}")
            norm = state.get("normalize_result") or {}
            failing_xml = norm.get("cleaned_xml", state.get("current_xml", ""))
            patch_sys, patch_user = build_patch_prompts(
                failing_xml=failing_xml,
                problems=problems,
                pre_issues=pre_issues,
                compile_diags=compile_diags,
                objective=objective,
                forbidden_tags=contract.get("forbidden_tags", []),
                theme_element=contract.get("theme_element", state.get("theme_element", "")),
            )
            return _call_llm_and_return(
                PATCH, current_count, problems, curr_sigs, stalled,
                failing_xml, patch_sys, patch_user,
            )

        regenerated_xml = response.content

        usage = extract_usage(response)
        tokens_in = usage["tokens_in"]
        tokens_out = usage["tokens_out"]
        model = usage["model"]
        truncated = response.response_metadata.get("finish_reason") == "length"
        if truncated:
            logger.warning("repairer: REGENERATE output truncated at max_tokens")

        logger.info(f"repairer: REGENERATE {model} tokens_in={tokens_in} tokens_out={tokens_out}")

        record = AttemptRecord(
            attempt=current_count + 1,
            tier=strategy,
            errors_in=problems,
            errors_out=[],
            error_sigs=sorted(curr_sigs),
            stalled=stalled,
            truncated=truncated,
            noop=False,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
        )

        return {
            "current_xml": regenerated_xml,
            "retry_tier": strategy,
            "retry_count": current_count + 1,
            "stall_detected": stalled,
            "generation_history": [record],
            "slide_plans": updated_plans,
            "contract": new_contract,
        }

    return _call_llm_and_return(
        strategy, current_count, problems, curr_sigs, stalled,
        failing_xml, system_prompt, user_prompt,
    )
