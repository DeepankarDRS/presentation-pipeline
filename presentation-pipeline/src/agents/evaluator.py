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

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from src.compiler.font_embed import embed_deck_fonts
from src.compiler.screenshot import render_screenshots
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


def _git(*args: str) -> str | None:
    """Output of a git command in the pipeline folder, or None when git is unavailable."""
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10, cwd=_PIPELINE_ROOT)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _run_provenance(state: PresentationState) -> dict[str, Any]:
    """What produced this run: code version, theme and a fingerprint of the request."""
    commit = _git("rev-parse", "--short", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=no", "--", ".")
    request = json.dumps(
        {"request": state.get("raw_request", ""), "supplied_content": state.get("supplied_content")},
        sort_keys=True, ensure_ascii=False, default=str,
    )
    return {
        "git_commit": commit or "unknown",
        "git_uncommitted_changes": None if status is None else bool(status),
        "theme": state.get("theme_name") or (state.get("resolved_theme") or {}).get("name") or "",
        "request_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest()[:16],
    }


def _build_step_summary(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build per-attempt step summary with costs."""
    steps: list[dict[str, Any]] = []
    for record in history:
        tokens_in = record.get("tokens_in", 0)
        tokens_out = record.get("tokens_out", 0)
        model = record.get("model", "unknown")
        cost = _compute_cost(tokens_in, tokens_out, model)

        steps.append({
            "step": record.get("step", "unknown"),
            "slide_index": record.get("slide_index"),
            "attempt": record.get("attempt", 0),
            "tier": record.get("tier", 0),
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_reasoning": record.get("tokens_reasoning", 0),
            "tokens_cached": record.get("tokens_cached", 0),
            "reask": bool(record.get("reask", False)),
            "cost": cost,
            "stalled": record.get("stalled", False),
            "errors_in_count": len(record.get("errors_in", [])),
            "errors_out_count": len(record.get("errors_out", [])),
        })
    return steps


def _write_slides_data(state: PresentationState, run_id: str) -> str | None:
    """Write per-slide XML and metadata to slides.json for the edit session."""
    output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    slide_plans = state.get("slide_plans", [])
    completed = state.get("completed_slides", [])
    screenshots = state.get("slide_screenshots", {})

    slides_data: list[dict[str, Any]] = []

    if completed:
        sorted_slides = sorted(completed, key=lambda s: s.get("slide_index", 0))
        for slide in sorted_slides:
            idx = slide.get("slide_index", 0)
            plan = slide_plans[idx] if idx < len(slide_plans) else {}
            slides_data.append({
                "slide_index": idx,
                "xml": slide.get("xml", ""),
                "speaker_notes": slide.get("speaker_notes", ""),
                "screenshot_path": screenshots.get(idx),
                "slide_plan": plan,
            })
    else:
        xml = state.get("current_xml", "")
        if xml:
            plan = slide_plans[0] if slide_plans else {}
            slides_data.append({
                "slide_index": 0,
                "xml": xml,
                "speaker_notes": state.get("speaker_notes", ""),
                "screenshot_path": screenshots.get(0),
                "slide_plan": plan,
            })

    slides_path = output_dir / "slides.json"
    try:
        slides_path.write_text(
            json.dumps(slides_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(slides_path)
    except (OSError, TypeError, ValueError) as e:
        logger.warning(f"evaluator: failed to write slides.json: {e}")
        return None


def _generate_final_screenshots(
    state: PresentationState, run_id: str,
) -> dict[int, str]:
    """Generate screenshots from the final assembled PPTX.

    Always (re)renders from compile_result.pptx_path — the single fully
    assembled deck — rather than reusing the critic's per-slide screenshots
    from generation time. Those are each rendered from a standalone
    single-page PPTX into a shared output directory, so for a multi-slide
    deck every one of them collides on the same "slide-0.png" filename and
    ends up pointing at whichever slide was critiqued last. Rendering once
    against the final N-page deck gives correctly numbered 0..N-1 screenshots
    in a single pass.
    """
    cr = state.get("compile_result") or {}
    pptx_path = cr.get("pptx_path")

    if pptx_path:
        output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "screenshots"
        batch = render_screenshots(pptx_path, str(output_dir))
        if batch.ok:
            result: dict[int, str] = {}
            for s in batch.slides:
                if s.ok and s.png_path:
                    result[s.slide_index] = s.png_path
            logger.info(f"evaluator: generated {len(result)} final screenshot(s)")
            return result
        logger.warning(f"evaluator: final screenshots failed: {batch.error}")

    # Fall back to whatever the critic captured during generation, if any.
    return dict(state.get("slide_screenshots", {}))


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
    history = state.get("generation_history", [])

    # a one-slide run ends here with the slide's own file (decks are embedded by deck_assembler)
    if not state.get("completed_slides") and compile_result.get("ok") and compile_result.get("pptx_path"):
        embed_deck_fonts(Path(compile_result["pptx_path"]))

    # Deck path: the critic runs per-slide and slide_router captures each verdict.
    # Single-slide path: the critic's verdict is on state directly.
    slide_critic_results = state.get("slide_critic_results") or []
    if state.get("completed_slides"):
        critic_ok = all(r.get("passed", True) for r in slide_critic_results)
        critic_issues = [i for r in slide_critic_results for i in r.get("issues", [])]
    else:
        critic_result = state.get("critic_result") or {}
        critic_ok = critic_result.get("passed", True)
        critic_issues = critic_result.get("issues", [])

    compile_ok = compile_result.get("ok", False)
    excluded_slides = state.get("excluded_slides") or []
    slides_complete = len(excluded_slides) == 0
    passed = compile_ok and critic_ok and slides_complete

    total_tokens_in = sum(r.get("tokens_in", 0) for r in history)
    total_tokens_out = sum(r.get("tokens_out", 0) for r in history)

    models_used = list({r.get("model", "unknown") for r in history})
    primary_model = models_used[0] if models_used else "unknown"
    total_cost = sum(
        _compute_cost(r.get("tokens_in", 0), r.get("tokens_out", 0), r.get("model", "unknown"))
        for r in history
    )

    step_summary = _build_step_summary(history)

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
        **_run_provenance(state),
        "passed": passed,
        "compile_ok": compile_ok,
        "critic_ok": critic_ok,
        "slides_complete": slides_complete,
        "excluded_slides": excluded_slides,
        "retry_count": state.get("retry_count", 0),
        "max_tier": state.get("retry_tier", 0),
        "stall_detected": state.get("stall_detected", False),
        "tokens": {
            "total_in": total_tokens_in,
            "total_out": total_tokens_out,
            "total": total_tokens_in + total_tokens_out,
            # parts of total_out / total_in, for reading only (cost uses total_in / total_out)
            "total_reasoning": sum(r.get("tokens_reasoning", 0) for r in history),
            "total_cached": sum(r.get("tokens_cached", 0) for r in history),
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
            # the texts, to review a critic-on run from the bundle (2026-10-07)
            "issues": [{k: str(i.get(k, ""))[:300] for k in ("severity", "type", "description", "fix")}
                       for i in critic_issues],
        },
        "steps": step_summary,
        "pptx_path": compile_result.get("pptx_path"),
        "data_provenance": {
            "user": user_count,
            "sample": sample_count,
        },
        "warnings": compile_result.get("warnings", []),
    }

    # Generate final screenshots if not already captured by the critic
    screenshots = _generate_final_screenshots(state, run_id)

    manifest["theme_element"] = state.get("theme_element", "")
    manifest["resolved_theme"] = state.get("resolved_theme") or {}
    manifest["screenshots"] = {str(k): v for k, v in screenshots.items()}

    manifest_path = _write_manifest(manifest, run_id)
    if manifest_path:
        logger.info(f"evaluator: manifest written to {manifest_path}")

    # Persist per-slide data for the edit session
    updated_state = dict(state)
    if screenshots:
        updated_state["slide_screenshots"] = screenshots
    slides_path = _write_slides_data(updated_state, run_id)
    if slides_path:
        logger.info(f"evaluator: slides data written to {slides_path}")

    logger.info(
        f"evaluator: passed={passed}, retries={state.get('retry_count', 0)}, "
        f"tokens={total_tokens_in}+{total_tokens_out}, cost=${total_cost:.4f}"
    )

    result: dict[str, Any] = {
        "evaluation": manifest,
        "pptx_path": compile_result.get("pptx_path"),
        "passed": passed,
    }
    if screenshots:
        result["slide_screenshots"] = screenshots
    return result
