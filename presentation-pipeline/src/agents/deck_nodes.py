"""Deck multi-slide nodes — slide_router and deck_assembler.

slide_router: saves completed slide XML, increments index, resets per-slide state.
deck_assembler: extracts <Slide> blocks from all completed slides, combines with
one <Theme>, runs final compile.

These nodes are only active when len(slide_plans) > 1.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.compiler.compiler_client import CompilerError, compile_xml
from src.state import PresentationState

logger = logging.getLogger(__name__)

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent


def slide_router_node(state: PresentationState) -> dict[str, Any]:
    """Save current slide result and advance to next slide index."""
    idx = state.get("current_slide_index", 0)
    xml = state.get("current_xml", "")

    logger.info(f"slide_router: saving slide {idx}, advancing to {idx + 1}")

    completed = {
        "slide_index": idx,
        "xml": xml,
        "speaker_notes": state.get("speaker_notes", ""),
    }

    return {
        "completed_slides": [completed],
        "current_slide_index": idx + 1,
        "current_xml": "",
        "speaker_notes": "",
        "normalize_result": None,
        "validate_result": None,
        "compile_result": None,
        "critic_result": None,
        "retry_tier": 0,
        "retry_count": 0,
        "stall_detected": False,
    }


def _extract_theme(xml: str) -> str:
    """Extract the <Theme .../> element from XML."""
    m = re.search(r'<Theme\s[^>]*/>', xml)
    return m.group(0) if m else ""


def _extract_slide_block(xml: str) -> str:
    """Extract the <Slide>...</Slide> block from XML."""
    m = re.search(r'(<Slide\b[^>]*>.*?</Slide>)', xml, re.DOTALL)
    return m.group(1) if m else ""


def deck_assembler_node(state: PresentationState) -> dict[str, Any]:
    """Combine all completed slide XMLs into one multi-slide POM document and compile."""
    completed = state.get("completed_slides", [])
    sorted_slides = sorted(completed, key=lambda s: s.get("slide_index", 0))

    if not sorted_slides:
        logger.warning("deck_assembler: no completed slides")
        return {
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "EMPTY", "message": "No slides to assemble"}],
                "warnings": [], "retryable": False,
            },
        }

    theme = _extract_theme(sorted_slides[0]["xml"])
    if not theme:
        for slide in sorted_slides:
            theme = _extract_theme(slide["xml"])
            if theme:
                break

    slide_blocks: list[str] = []
    for slide in sorted_slides:
        block = _extract_slide_block(slide["xml"])
        if block:
            slide_blocks.append(block)
        else:
            logger.warning(f"deck_assembler: no <Slide> block in slide {slide.get('slide_index')}")

    if not slide_blocks:
        logger.error("deck_assembler: no valid <Slide> blocks found")
        return {
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "ASSEMBLY", "message": "No valid Slide blocks"}],
                "warnings": [], "retryable": False,
            },
        }

    combined_xml = theme + "\n" + "\n".join(slide_blocks)
    logger.info(f"deck_assembler: combined {len(slide_blocks)} slides, {len(combined_xml)} chars")

    run_id = state.get("run_id", "unknown")
    output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "deck"

    try:
        compile_result = compile_xml(combined_xml, output_dir)
    except CompilerError as exc:
        logger.error(f"deck_assembler: compile error: {exc}")
        return {
            "current_xml": combined_xml,
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "HARNESS_ERROR", "message": str(exc)}],
                "warnings": [], "retryable": False,
            },
        }

    status = "OK" if compile_result["ok"] else "FAILED"
    logger.info(f"deck_assembler: final compile {status}")
    if compile_result.get("pptx_path"):
        logger.info(f"deck_assembler: pptx → {compile_result['pptx_path']}")

    return {
        "current_xml": combined_xml,
        "compile_result": compile_result,
        "pptx_path": compile_result.get("pptx_path"),
    }
