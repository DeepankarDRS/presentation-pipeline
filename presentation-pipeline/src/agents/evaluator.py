"""Evaluator agent — mechanical scoring and run manifest. No LLM.

Computes:
  - Component completion rate (plan vs generation_history)
  - Compile/critic status
  - Per-step token usage and cost (from models.yaml pricing)
  - Total cost estimate
  - Retry/tier summary

Writes run-manifest.json to output/runs/{run_id}/ when output_dir is set.

Reads:  all state slices
Writes: evaluation, pptx_path, passed
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.state import PresentationState
from src.utils.llm_client import get_pricing

logger = logging.getLogger(__name__)

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent


def _compute_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    """Compute cost in dollars from token counts and model pricing."""
    pricing = get_pricing(model)
    cost_in = (tokens_in / 1_000_000) * pricing.get("input", 0.0)
    cost_out = (tokens_out / 1_000_000) * pricing.get("output", 0.0)
    return round(cost_in + cost_out, 6)


def _build_step_summary(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build per-attempt step summary with costs."""
    steps: list[dict[str, Any]] = []
    for record in history:
        tokens_in = record.get("tokens_in", 0)
        tokens_out = record.get("tokens_out", 0)
        model = record.get("model", "unknown")
        cost = _compute_cost(tokens_in, tokens_out, model)

        steps.append({
            "attempt": record.get("attempt", 0),
            "tier": record.get("tier", 0),
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
            "stalled": record.get("stalled", False),
            "errors_in_count": len(record.get("errors_in", [])),
            "errors_out_count": len(record.get("errors_out", [])),
        })
    return steps


def _write_manifest(manifest: dict[str, Any], run_id: str) -> str | None:
    """Write run-manifest.json to output/runs/{run_id}/."""
    output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "run-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(manifest_path)
    except OSError as e:
        logger.warning(f"evaluator: failed to write manifest: {e}")
        return None


def evaluator_node(state: PresentationState) -> dict[str, Any]:
    """Score the run and produce a manifest."""
    run_id = state.get("run_id", "")
    compile_result = state.get("compile_result") or {}
    critic_result = state.get("critic_result") or {}
    history = state.get("generation_history", [])

    compile_ok = compile_result.get("ok", False)
    critic_ok = critic_result.get("passed", True)
    passed = compile_ok and critic_ok

    total_tokens_in = sum(r.get("tokens_in", 0) for r in history)
    total_tokens_out = sum(r.get("tokens_out", 0) for r in history)

    models_used = list({r.get("model", "unknown") for r in history})
    primary_model = models_used[0] if models_used else "unknown"
    total_cost = sum(
        _compute_cost(r.get("tokens_in", 0), r.get("tokens_out", 0), r.get("model", "unknown"))
        for r in history
    )

    step_summary = _build_step_summary(history)

    critic_issues = critic_result.get("issues", [])
    critic_high = sum(1 for i in critic_issues if i.get("severity") == "high")
    critic_medium = sum(1 for i in critic_issues if i.get("severity") == "medium")
    critic_low = sum(1 for i in critic_issues if i.get("severity") == "low")

    slide_plans = state.get("slide_plans", [])
    user_count = 0
    sample_count = 0
    for plan in slide_plans:
        for source in (plan.get("data_provenance") or {}).values():
            if source == "user":
                user_count += 1
            else:
                sample_count += 1

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "passed": passed,
        "compile_ok": compile_ok,
        "critic_ok": critic_ok,
        "retry_count": state.get("retry_count", 0),
        "max_tier": state.get("retry_tier", 0),
        "stall_detected": state.get("stall_detected", False),
        "tokens": {
            "total_in": total_tokens_in,
            "total_out": total_tokens_out,
            "total": total_tokens_in + total_tokens_out,
        },
        "cost": {
            "total_usd": round(total_cost, 6),
            "models_used": models_used,
        },
        "critic": {
            "issues_total": len(critic_issues),
            "high": critic_high,
            "medium": critic_medium,
            "low": critic_low,
        },
        "steps": step_summary,
        "pptx_path": compile_result.get("pptx_path"),
        "data_provenance": {
            "user": user_count,
            "sample": sample_count,
        },
        "warnings": compile_result.get("warnings", []),
    }

    manifest_path = _write_manifest(manifest, run_id)
    if manifest_path:
        logger.info(f"evaluator: manifest written to {manifest_path}")

    logger.info(
        f"evaluator: passed={passed}, retries={state.get('retry_count', 0)}, "
        f"tokens={total_tokens_in}+{total_tokens_out}, cost=${total_cost:.4f}"
    )

    return {
        "evaluation": manifest,
        "pptx_path": compile_result.get("pptx_path"),
        "passed": passed,
    }
