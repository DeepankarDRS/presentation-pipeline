"""Repairer agent — 3-tier escalating repair strategy.

Tier 1 (Patch):    feed back failing XML + errors + guidance → fix in place
Tier 2 (Simplify): regenerate with simpler constraints
Tier 3 (Template): verified example as skeleton, fill content only

Stall detection: >=65% error signature overlap between attempts → escalate.

The repairer calls the LLM with a targeted repair prompt and produces fixed
XML. The graph routes repairer → validator (skipping the generator).

Reads:  current_xml, normalize_result, validate_result, compile_result,
        critic_result, contract, slide_plans, retry_tier, retry_count,
        generation_history
Writes: current_xml, retry_tier, retry_count, stall_detected, generation_history
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.compiler.repair_guidance import (
    build_error_guidance,
    error_signatures,
    is_stalled,
    select_repair_knowledge,
)
from src.state import AttemptRecord, PresentationState
from src.utils.llm_client import get_llm

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
)

_SRC_DIR = Path(__file__).resolve().parent.parent
_EXAMPLES_DIR = _SRC_DIR / "knowledge" / "examples"

_SIMPLIFY_INSTRUCTIONS = """The previous XML was too complex or structurally broken.
Simplify the layout:
- Reduce to at most 3 visual sections (header, body, footer)
- Use body fontSize=12, heading fontSize=18 (compact tier)
- Reduce root padding to 32, gaps to 8-12
- If there are >4 KPI tiles, reduce to 3
- If there are 2 charts, keep only the most important one
- Drop the bullet list if charts+table are present
- Ensure all dimensions are positive and fit within 1280x720"""


def _collect_problems(state: PresentationState) -> list[str]:
    """Collect error strings from normalize_result, compile_result, and critic_result."""
    problems: list[str] = []

    norm = state.get("normalize_result") or {}
    for issue in norm.get("issues", []):
        if not issue.get("auto_fixed", False):
            problems.append(f"{issue['code']}: {issue['message']}")

    cr = state.get("compile_result") or {}
    for diag in cr.get("diagnostics", []):
        problems.append(f"{diag['type']}: {diag['message']}")

    critic = state.get("critic_result") or {}
    for issue in critic.get("issues", []):
        severity = issue.get("severity", "")
        msg = issue.get("message", str(issue))
        problems.append(f"CRITIC_{severity.upper()}: {msg}")

    return problems


def _get_pre_issues(state: PresentationState) -> list[dict[str, Any]]:
    norm = state.get("normalize_result") or {}
    return [i for i in norm.get("issues", []) if not i.get("auto_fixed", False)]


def _get_compile_diags(state: PresentationState) -> list[dict[str, Any]]:
    cr = state.get("compile_result") or {}
    return cr.get("diagnostics", [])


def _select_template(state: PresentationState) -> str:
    """Pick the best verified example XML for tier 3 fallback."""
    slide_plans = state.get("slide_plans", [])
    idx = state.get("current_slide_index", 0)
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}
    kinds = [c.get("kind", "") for c in plan.get("components", [])]

    has_chart = "chart" in kinds
    has_table = "table" in kinds

    if has_chart and has_table:
        name = "mixed-slide.xml"
    elif has_chart:
        name = "chart-slide.xml"
    elif has_table:
        name = "table-slide.xml"
    elif "kpi_row" in kinds:
        name = "kpi-slide.xml"
    else:
        name = "text-slide.xml"

    path = _EXAMPLES_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    fallback = _EXAMPLES_DIR / "text-slide.xml"
    return fallback.read_text(encoding="utf-8").strip() if fallback.exists() else ""


def _render_original_user(state: PresentationState) -> str:
    """Re-render the original user prompt for inclusion in repair prompts."""
    slide_plans = state.get("slide_plans", [])
    idx = state.get("current_slide_index", 0)
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}

    user_tmpl = _gen_env.get_template("user.j2")
    return user_tmpl.render(
        objective=state.get("raw_request", ""),
        components=plan.get("components", []),
        density=plan.get("density", "normal"),
        font_tier=plan.get("font_tier", "standard"),
        layout_hint=plan.get("layout_hint", ""),
        content_data=plan.get("content_data", {}),
        supplied_content=state.get("supplied_content"),
    )


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
    """Build the (system, user) prompts for a tier-1 patch repair.

    Shared by repairer_node's tier-1 branch and the slide edit service's mini
    repair loop, so both get the same error-scoped node reference (attribute
    docs, pitfalls, a verified syntax example) injected into the system prompt.
    """
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


def repairer_node(state: PresentationState) -> dict[str, Any]:
    """3-tier escalating repair: build repair prompt, call LLM, update state."""
    current_tier = state.get("retry_tier", 0)
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

    stalled = current_count > 0 and is_stalled(prev_sigs, curr_sigs)
    if stalled:
        current_tier = min(current_tier + 1, 3)
        logger.info(f"repairer: STALL detected, escalating to tier {current_tier}")
    else:
        current_tier = max(current_tier, 1)

    tier_name = {1: "PATCH", 2: "SIMPLIFY", 3: "TEMPLATE"}.get(current_tier, "PATCH")
    logger.info(f"repairer: attempt {current_count + 1}, tier {current_tier} ({tier_name}), "
                f"{len(problems)} problem(s)")

    contract = state.get("contract") or {}

    if current_tier <= 1:
        norm = state.get("normalize_result") or {}
        failing_xml = norm.get("cleaned_xml", state.get("current_xml", ""))
        system_prompt, user_prompt = build_patch_prompts(
            failing_xml=failing_xml,
            problems=problems,
            pre_issues=pre_issues,
            compile_diags=compile_diags,
            objective=state.get("raw_request", ""),
            forbidden_tags=contract.get("forbidden_tags", []),
            theme_element=contract.get("theme_element", state.get("theme_element", "")),
        )
    else:
        # Tiers 2/3 regenerate rather than patch, so they need the broader
        # knowledge slice for the system prompt and the original user prompt.
        knowledge = select_repair_knowledge(pre_issues, compile_diags)
        if knowledge["nodes_involved"]:
            logger.info(f"repairer: knowledge loaded for nodes: {knowledge['nodes_involved']}")
        previous_user = _render_original_user(state)
        if current_tier == 2:
            user_prompt = _repair_env.get_template("simplify.j2").render(
                previous_user=previous_user,
                problems=problems,
                simplify_instructions=_SIMPLIFY_INSTRUCTIONS,
                allowed_nodes=contract.get("allowed_nodes", []),
            )
        else:
            user_prompt = _repair_env.get_template("template.j2").render(
                previous_user=previous_user,
                template_xml=_select_template(state),
            )
        system_prompt = _render_repair_system(state, knowledge)

    llm = get_llm("repairer")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = llm.invoke(messages)
    repaired_xml = response.content

    token_usage = response.response_metadata.get("token_usage", {})
    tokens_in = token_usage.get("prompt_tokens", 0)
    tokens_out = token_usage.get("completion_tokens", 0)
    model = response.response_metadata.get("model_name", "unknown")

    logger.info(f"repairer: {model} tokens_in={tokens_in} tokens_out={tokens_out}")

    record = AttemptRecord(
        attempt=current_count + 1,
        tier=current_tier,
        errors_in=problems,
        errors_out=[],
        error_sigs=sorted(curr_sigs),
        stalled=stalled,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
    )

    return {
        "current_xml": repaired_xml,
        "retry_tier": current_tier,
        "retry_count": current_count + 1,
        "stall_detected": stalled,
        "generation_history": [record],
    }
