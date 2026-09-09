"""Best-of-N attempt tracking.

The repair loop can drift — a later attempt may compile worse, or fail the
critic worse, than an earlier one, and the pipeline would otherwise ship the
*last* attempt. validator (critic off) and critic (critic on) call
``keep_best_attempt`` after each attempt is fully assessed; the evaluator ships
whichever attempt scored highest.

Score is a list compared lexicographically, higher = better:
    [compile_ok, critic_passed, -high_count, -attempt]
A truncated or non-compiling attempt is not a candidate. The ``-attempt`` term
means an earlier attempt wins ties (least drift from the plan).
"""

from __future__ import annotations

from typing import Any

_NOT_A_CANDIDATE = [0, 0, 0, 0]


def score_attempt(
    *,
    compile_ok: bool,
    critic_passed: bool,
    high_count: int,
    attempt: int,
    truncated: bool,
) -> list[int]:
    if truncated or not compile_ok:
        return list(_NOT_A_CANDIDATE)
    return [1, 1 if critic_passed else 0, -high_count, -attempt]


def keep_best_attempt(state: dict[str, Any], updates: dict[str, Any]) -> None:
    """If this attempt beats the stored best, record it into ``updates`` in place."""
    cr = updates.get("compile_result") or state.get("compile_result") or {}
    critic = updates.get("critic_result") or {}
    history = state.get("generation_history") or []
    attempt = state.get("retry_count", 0)

    score = score_attempt(
        compile_ok=bool(cr.get("ok")),
        critic_passed=bool(critic.get("passed", True)),
        high_count=sum(1 for i in critic.get("issues", []) if i.get("severity") == "high"),
        attempt=attempt,
        truncated=bool(history[-1].get("truncated")) if history else False,
    )
    if score == _NOT_A_CANDIDATE:
        return
    if score > (state.get("best_score") or _NOT_A_CANDIDATE):
        updates["best_attempt"] = attempt
        updates["best_score"] = score
