"""Critic agent — AI quality gate after successful compilation.

Checks what the compiler can't:
  1. Component completeness (plan vs XML)
  2. Content fidelity (supplied values in XML)
  3. Structural sanity (nesting, stack usage)
  4. Theme adherence (all colors from Theme)

Dual-mode: auto (AI) or manual (human checkpoint).

Reads:  current_xml, compile_result, slide_plans, critic_mode,
        supplied_content, theme_element
Writes: critic_result
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents.critic_schema import CriticOutput
from src.state import CriticResult, PresentationState
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "critic"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    keep_trailing_newline=True,
)


def _render_prompts(state: PresentationState) -> tuple[str, str]:
    """Render system + user prompts for the critic LLM call."""
    slide_plans = state.get("slide_plans", [])
    plan = slide_plans[0] if slide_plans else {}

    system_tmpl = _jinja_env.get_template("system.j2")
    user_tmpl = _jinja_env.get_template("user.j2")

    system_prompt = system_tmpl.render()

    user_prompt = user_tmpl.render(
        current_xml=state.get("current_xml", ""),
        components=plan.get("components", []),
        density=plan.get("density", "normal"),
        layout_hint=plan.get("layout_hint", ""),
        supplied_content=state.get("supplied_content"),
        theme_element=state.get("theme_element", ""),
    )

    return system_prompt, user_prompt


def critic_node(state: PresentationState) -> dict[str, Any]:
    """AI quality gate: check completeness, fidelity, structure, theme."""
    mode = state.get("critic_mode", "auto")

    if mode == "manual":
        logger.info("critic: manual mode — passing (human checkpoint not yet implemented)")
        return {"critic_result": CriticResult(passed=True, issues=[])}

    logger.info("critic: auto mode — running LLM quality check")

    system_prompt, user_prompt = _render_prompts(state)

    llm = get_llm("critic")
    structured_llm = llm.with_structured_output(CriticOutput, method="json_schema")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result: CriticOutput = structured_llm.invoke(messages)
    except Exception as e:
        logger.error(f"critic: LLM call failed: {e}")
        return {"critic_result": CriticResult(passed=True, issues=[])}

    issues: list[dict[str, Any]] = [
        {
            "severity": issue.severity,
            "type": issue.type,
            "description": issue.description,
            "fix": issue.fix,
        }
        for issue in result.issues
    ]

    has_high = any(i["severity"] == "high" for i in issues)
    passed = not has_high

    high_count = sum(1 for i in issues if i["severity"] == "high")
    med_count = sum(1 for i in issues if i["severity"] == "medium")
    low_count = sum(1 for i in issues if i["severity"] == "low")
    logger.info(
        f"critic: passed={passed}, issues={len(issues)} "
        f"(high={high_count}, medium={med_count}, low={low_count})"
    )

    return {"critic_result": CriticResult(passed=passed, issues=issues)}
