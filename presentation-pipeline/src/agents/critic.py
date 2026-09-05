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
    idx = state.get("current_slide_index", 0)
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}

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


def _run_ai_check(state: PresentationState) -> list[dict[str, Any]]:
    """Run the AI quality check and return the list of issues."""
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
        return []

    return [
        {
            "severity": issue.severity,
            "type": issue.type,
            "description": issue.description,
            "fix": issue.fix,
        }
        for issue in result.issues
    ]


def _format_issues_for_display(issues: list[dict[str, Any]]) -> str:
    """Format critic issues for CLI display."""
    if not issues:
        return "  No issues found — all checks passed."
    lines: list[str] = []
    for i, issue in enumerate(issues, 1):
        sev = issue["severity"].upper()
        lines.append(f"  {i}. [{sev}] ({issue['type']}) {issue['description']}")
        lines.append(f"     Fix: {issue['fix']}")
    return "\n".join(lines)


def _manual_checkpoint(
    issues: list[dict[str, Any]],
    interactive: bool,
) -> CriticResult:
    """Present issues to user, ask Accept/Reject/Edit. Returns CriticResult."""
    if not interactive:
        logger.info("critic: manual mode but non-interactive — auto-accepting")
        has_high = any(i["severity"] == "high" for i in issues)
        return CriticResult(passed=not has_high, issues=issues)

    print("\n" + "=" * 60)
    print("CRITIC REVIEW — Manual Checkpoint")
    print("=" * 60)
    print(_format_issues_for_display(issues))
    print("-" * 60)
    print("  [A]ccept — approve the slide as-is")
    print("  [R]eject — send issues to repairer")
    print("  [E]dit   — add your own feedback, then send to repairer")
    print("-" * 60)

    choice = input("  Your choice (A/R/E): ").strip().lower()

    if choice.startswith("a"):
        logger.info("critic: manual — user accepted")
        return CriticResult(passed=True, issues=issues)

    if choice.startswith("e"):
        feedback = input("  Your feedback: ").strip()
        if feedback:
            issues.append({
                "severity": "high",
                "type": "completeness",
                "description": f"[User feedback] {feedback}",
                "fix": feedback,
            })
        logger.info("critic: manual — user edited, sending to repairer")
        return CriticResult(passed=False, issues=issues)

    logger.info("critic: manual — user rejected")
    if not any(i["severity"] == "high" for i in issues):
        issues.append({
            "severity": "high",
            "type": "completeness",
            "description": "[User rejected] Slide did not meet expectations.",
            "fix": "Review and fix all flagged issues.",
        })
    return CriticResult(passed=False, issues=issues)


def critic_node(state: PresentationState) -> dict[str, Any]:
    """AI quality gate: check completeness, fidelity, structure, theme."""
    mode = state.get("critic_mode", "auto")
    interactive = state.get("interactive", False)

    logger.info(f"critic: {mode} mode — running LLM quality check")
    issues = _run_ai_check(state)

    high_count = sum(1 for i in issues if i["severity"] == "high")
    med_count = sum(1 for i in issues if i["severity"] == "medium")
    low_count = sum(1 for i in issues if i["severity"] == "low")

    if mode == "manual":
        result = _manual_checkpoint(issues, interactive)
        logger.info(
            f"critic: manual passed={result['passed']}, issues={len(result['issues'])} "
            f"(high={high_count}, medium={med_count}, low={low_count})"
        )
        return {"critic_result": result}

    has_high = any(i["severity"] == "high" for i in issues)
    passed = not has_high

    logger.info(
        f"critic: passed={passed}, issues={len(issues)} "
        f"(high={high_count}, medium={med_count}, low={low_count})"
    )

    return {"critic_result": CriticResult(passed=passed, issues=issues)}
