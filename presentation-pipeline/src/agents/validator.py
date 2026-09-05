"""Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.

This is the ground truth for whether XML is valid POM. The retry decision
is based solely on compile_result.ok and compile_result.retryable.

Pipeline:
  1. normalize_xml() — strip fences, fix colors, remove br/hr, flag zero dims
  2. validate_xml() — parseXml structural check (fast, no PPTX gen)
  3. compile_xml() — buildPptx (only if validation passed)

Falls back to regex pre_validate() when parseXml is unavailable.

Reads:  current_xml, contract
Writes: normalize_result, validate_result, compile_result
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.compiler.compiler_client import CompilerError, compile_xml, validate_xml
from src.compiler.normalizer import normalize_xml, pre_validate
from src.state import PresentationState

logger = logging.getLogger(__name__)


def validator_node(state: PresentationState) -> dict[str, Any]:
    """Run the normalize → validate → compile pipeline on current_xml."""
    xml = state.get("current_xml", "")
    if not xml.strip():
        logger.warning("validator: empty XML")
        return {
            "normalize_result": {"issues": [], "auto_fixed": 0, "blocking": False},
            "validate_result": {"ok": False, "diagnostics": [{"type": "EMPTY", "message": "Empty XML"}], "warnings": []},
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "EMPTY", "message": "Empty XML"}],
                "warnings": [], "retryable": True,
            },
        }

    run_id = state.get("run_id", "unknown")
    _pipeline_root = Path(__file__).resolve().parent.parent.parent
    output_dir = _pipeline_root / "output" / "runs" / run_id
    attempt = state.get("retry_count", 0)
    if attempt > 0:
        output_dir = output_dir / f"retry-{attempt}"

    norm = normalize_xml(xml)
    cleaned = norm["cleaned_xml"]
    speaker_notes = norm.get("speaker_notes", "")

    if norm["issues"]:
        auto = norm["auto_fixed"]
        total = len(norm["issues"])
        logger.info(f"validator: normalize {total} issue(s), {auto} auto-fixed"
                     + (" [BLOCKING]" if norm["blocking"] else ""))

    val_result = validate_xml(cleaned, output_dir)

    if val_result is None:
        logger.info("validator: parseXml unavailable, using pre_validate fallback")
        contract = state.get("contract")
        fallback = pre_validate(xml, contract)
        cleaned = fallback["cleaned_xml"]
        norm = fallback

        if fallback["blocking"]:
            blocking_issues = [i for i in fallback["issues"] if not i["auto_fixed"]]
            logger.info(f"validator: pre_validate found {len(blocking_issues)} blocking issue(s)")
            return {
                "normalize_result": norm,
                "validate_result": {
                    "ok": False,
                    "diagnostics": [{"type": i["code"], "message": i["message"]} for i in blocking_issues],
                    "warnings": [],
                },
                "compile_result": {
                    "ok": False, "pptx_path": None,
                    "diagnostics": [{"type": i["code"], "message": i["message"]} for i in blocking_issues],
                    "warnings": [], "retryable": True,
                },
            }

    elif not val_result["ok"]:
        logger.info(f"validator: parseXml FAILED — {len(val_result['diagnostics'])} error(s)")
        for d in val_result["diagnostics"]:
            logger.info(f"  ! {d['type']}: {d['message']}")
        return {
            "normalize_result": norm,
            "validate_result": val_result,
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": val_result["diagnostics"],
                "warnings": [], "retryable": val_result.get("retryable", True),
            },
        }

    try:
        compile_result = compile_xml(cleaned, output_dir)
    except CompilerError as exc:
        logger.error(f"validator: compiler harness error: {exc}")
        return {
            "normalize_result": norm,
            "validate_result": val_result or {"ok": True, "diagnostics": [], "warnings": []},
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "HARNESS_ERROR", "message": str(exc)}],
                "warnings": [], "retryable": False,
            },
        }

    status = "OK" if compile_result["ok"] else "FAILED"
    logger.info(f"validator: compile {status}"
                + (f" ({len(compile_result['diagnostics'])} diag)" if not compile_result["ok"] else ""))
    if compile_result["ok"] and compile_result.get("pptx_path"):
        logger.info(f"validator: pptx → {compile_result['pptx_path']}")

    return {
        "normalize_result": norm,
        "validate_result": val_result or {"ok": True, "diagnostics": [], "warnings": []},
        "compile_result": compile_result,
        "speaker_notes": speaker_notes,
    }
