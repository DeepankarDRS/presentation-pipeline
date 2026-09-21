"""Deck multi-slide nodes — slide_router and deck_assembler.

slide_router: saves the completed slide's *normalized* XML + critic verdict,
increments index, resets per-slide state.
deck_assembler: extracts <Slide> blocks from all completed slides, combines them
under one <Theme> (re-running normalize so per-slide auto-fixes stick), runs the
final compile. Falls back to ZIP-level merge of per-slide PPTXs if the combined
compile fails — guaranteeing a PPTX is always produced.

These nodes are only active when len(slide_plans) > 1.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.compiler.compiler_client import CompilerError, compile_xml
from src.compiler.normalizer import ensure_single_theme, normalize_xml, strip_theme
from src.compiler.pptx_merge import merge_pptx_files
from src.state import PresentationState

logger = logging.getLogger(__name__)

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent


def assemble_deck_xml(slide_xmls: list[str], theme_element: str) -> tuple[str, int]:
    """Combine per-slide XML into one normalized multi-slide POM document.

    Extracts each <Slide> block, drops per-slide themes, concatenates under a
    single top-level <Theme>, then runs the same normalize + ensure_single_theme
    pass the per-slide validator uses — so br/hr, #-hex, spacing=, fontWeight=,
    and zero-spacing contamination that was auto-fixed per slide cannot reach
    the deck compile. Returns ("", 0) if no <Slide> block is found.
    """
    blocks: list[str] = []
    for xml in slide_xmls:
        block = _extract_slide_block(xml)
        if block:
            blocks.append(strip_theme(block))
        else:
            logger.warning("assemble_deck_xml: slide had no <Slide> block — dropped")
    if not blocks:
        return "", 0

    theme = (theme_element or "").strip()
    if not theme:
        for xml in slide_xmls:
            theme = _extract_theme(xml)
            if theme:
                break

    combined = (theme + "\n" if theme else "") + "\n".join(blocks)
    return ensure_single_theme(normalize_xml(combined)["cleaned_xml"], theme), len(blocks)


def slide_router_node(state: PresentationState) -> dict[str, Any]:
    """Save current slide result and advance to next slide index."""
    idx = state.get("current_slide_index", 0)
    # Save the normalized XML the validator actually compiled, not the raw LLM
    # output — otherwise per-slide auto-fixes (br/hr, #-hex, spacing=, …) are lost
    # and resurface as deck-compile failures.
    norm = state.get("normalize_result") or {}
    xml = norm.get("cleaned_xml") or state.get("current_xml", "")

    logger.info(f"slide_router: saving slide {idx}, advancing to {idx + 1}")

    compile_result = state.get("compile_result") or {}
    compile_ok = bool(compile_result.get("ok"))
    pptx_path = compile_result.get("pptx_path") if compile_ok else None

    completed = {
        "slide_index": idx,
        "xml": xml,
        "speaker_notes": state.get("speaker_notes", ""),
        "compile_ok": compile_ok,
        "pptx_path": pptx_path,
    }

    return {
        "completed_slides": [completed],
        "slide_critic_results": [state.get("critic_result") or {"passed": True}],
        "current_slide_index": idx + 1,
        "current_xml": "",
        "speaker_notes": "",
        "normalize_result": None,
        "validate_result": None,
        "compile_result": None,
        "critic_result": None,
        "visual_critic_result": None,
        "retry_tier": 0,
        "retry_count": 0,
        "visual_repair_count": 0,
        "visual_repair_outcome": "noop",
        "pre_critic_xml": "",
        "pre_critic_slide_plans": [],
        "pre_critic_contract": None,
        "pre_critic_score": 0,
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


def _zip_merge_fallback(
    good_slides: list[dict[str, Any]], output_dir: Path,
) -> dict[str, Any] | None:
    """Merge per-slide PPTXs at the ZIP level. Returns compile_result or None."""
    slide_pptx_paths = []
    for s in good_slides:
        p = s.get("pptx_path")
        if p and Path(p).exists():
            slide_pptx_paths.append(Path(p))
        else:
            logger.warning(
                f"deck_assembler: slide {s['slide_index']} has no PPTX on disk, "
                "skipping in ZIP merge"
            )

    if not slide_pptx_paths:
        return None

    merge_output = output_dir / "presentation.pptx"
    try:
        merged_path = merge_pptx_files(slide_pptx_paths, merge_output)
    except Exception as exc:
        logger.error(f"deck_assembler: ZIP merge failed: {exc}")
        return None

    logger.info(f"deck_assembler: ZIP merge succeeded → {merged_path}")
    return {
        "ok": True,
        "pptx_path": str(merged_path),
        "diagnostics": [],
        "warnings": [{"type": "ZIP_MERGE", "message": "Combined compile failed; used ZIP-level merge of per-slide PPTXs"}],
        "retryable": False,
    }


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

    good_slides = [s for s in sorted_slides if s.get("compile_ok", True)]
    excluded = [s for s in sorted_slides if not s.get("compile_ok", True)]
    for s in excluded:
        logger.warning(f"deck_assembler: excluding slide {s['slide_index']} (compile_ok=False)")

    if not good_slides:
        logger.error("deck_assembler: all slides failed compile — none to assemble")
        return {
            "excluded_slides": [s["slide_index"] for s in excluded],
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "EMPTY", "message": "All slides failed compile"}],
                "warnings": [], "retryable": False,
            },
        }

    theme = (state.get("resolved_theme") or {}).get("element") or state.get("theme_element", "")

    combined_xml, assembled_count = assemble_deck_xml([s["xml"] for s in good_slides], theme)
    if not combined_xml:
        logger.error("deck_assembler: no valid <Slide> blocks found")
        return {
            "excluded_slides": [s["slide_index"] for s in excluded],
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "ASSEMBLY", "message": "No valid Slide blocks"}],
                "warnings": [], "retryable": False,
            },
        }
    if assembled_count < len(good_slides):
        logger.warning(
            f"deck_assembler: {len(good_slides) - assembled_count} slide(s) "
            "had malformed XML and were dropped during block extraction"
        )
    if not theme:
        theme = _extract_theme(combined_xml)
    logger.info(f"deck_assembler: assembled {assembled_count}/{len(sorted_slides)} slides, {len(combined_xml)} chars")

    run_id = state.get("run_id", "unknown")
    output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "deck"

    try:
        compile_result = compile_xml(combined_xml, output_dir)
    except CompilerError as exc:
        logger.error(f"deck_assembler: compile error: {exc}")
        compile_result = {
            "ok": False, "pptx_path": None,
            "diagnostics": [{"type": "HARNESS_ERROR", "message": str(exc)}],
            "warnings": [], "retryable": False,
        }

    if not compile_result.get("ok", False):
        logger.warning("deck_assembler: combined compile failed, attempting ZIP merge fallback")
        merge_result = _zip_merge_fallback(good_slides, output_dir)
        if merge_result:
            compile_result = merge_result

    status = "OK" if compile_result.get("ok", False) else "FAILED"
    logger.info(f"deck_assembler: final {status}")
    if compile_result.get("pptx_path"):
        logger.info(f"deck_assembler: pptx → {compile_result['pptx_path']}")

    return {
        "current_xml": combined_xml,
        "compile_result": compile_result,
        "pptx_path": compile_result.get("pptx_path"),
        "excluded_slides": [s["slide_index"] for s in excluded],
    }
