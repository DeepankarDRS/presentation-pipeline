"""Deck multi-slide nodes — slide_router and deck_assembler.

slide_router: saves the completed slide's *normalized* XML + critic verdict,
increments index, resets per-slide state.
deck_assembler: extracts <Slide> blocks from all completed slides, combines them
under one <Theme> (re-running normalize so per-slide auto-fixes stick), runs the
final compile with a bounded compile-repair loop.

These nodes are only active when len(slide_plans) > 1.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.agents.repairer import build_patch_prompts
from src.compiler.compiler_client import CompilerError, compile_xml
from src.compiler.normalizer import ensure_single_theme, normalize_xml, strip_theme
from src.state import PresentationState
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent

MAX_DECK_REPAIR_ATTEMPTS = 2


def _call_deck_repair_llm(
    failing_xml: str,
    diags: list[dict[str, Any]],
    *,
    forbidden_tags: list[str],
    theme_element: str,
) -> str:
    """Fix compile errors in the assembled multi-slide document, preserving all slides.

    Reuses the repairer's shared PATCH prompt builder so the deck repair gets the
    same forbidden-tag rules, error-scoped node knowledge, and targeted fix
    guidance that a single-slide repair gets.
    """
    system_prompt, user_prompt = build_patch_prompts(
        failing_xml=failing_xml,
        problems=[f"{d.get('type', 'ERROR')}: {d.get('message', '')}" for d in diags],
        pre_issues=[],
        compile_diags=diags,
        objective=(
            "Repair the assembled multi-slide deck. Preserve every <Slide> block "
            "and the single top-level <Theme>."
        ),
        forbidden_tags=forbidden_tags,
        theme_element=theme_element,
    )
    response = get_llm("repairer").invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return response.content


def assemble_deck_xml(slide_xmls: list[str], theme_element: str) -> str:
    """Combine per-slide XML into one normalized multi-slide POM document.

    Extracts each <Slide> block, drops per-slide themes, concatenates under a
    single top-level <Theme>, then runs the same normalize + ensure_single_theme
    pass the per-slide validator uses — so br/hr, #-hex, spacing=, fontWeight=,
    and zero-spacing contamination that was auto-fixed per slide cannot reach
    the deck compile. Returns "" if no <Slide> block is found.
    """
    blocks: list[str] = []
    for xml in slide_xmls:
        block = _extract_slide_block(xml)
        if block:
            blocks.append(strip_theme(block))
        else:
            logger.warning("assemble_deck_xml: slide had no <Slide> block — dropped")
    if not blocks:
        return ""

    theme = (theme_element or "").strip()
    if not theme:
        for xml in slide_xmls:
            theme = _extract_theme(xml)
            if theme:
                break

    combined = (theme + "\n" if theme else "") + "\n".join(blocks)
    return ensure_single_theme(normalize_xml(combined)["cleaned_xml"], theme)


def slide_router_node(state: PresentationState) -> dict[str, Any]:
    """Save current slide result and advance to next slide index."""
    idx = state.get("current_slide_index", 0)
    # Save the normalized XML the validator actually compiled, not the raw LLM
    # output — otherwise per-slide auto-fixes (br/hr, #-hex, spacing=, …) are lost
    # and resurface as deck-compile failures.
    norm = state.get("normalize_result") or {}
    xml = norm.get("cleaned_xml") or state.get("current_xml", "")

    logger.info(f"slide_router: saving slide {idx}, advancing to {idx + 1}")

    completed = {
        "slide_index": idx,
        "xml": xml,
        "speaker_notes": state.get("speaker_notes", ""),
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
        "retry_tier": 0,
        "retry_count": 0,
        "stall_detected": False,
        "best_attempt": -1,
        "best_score": [0, 0, 0, 0],
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

    # The pipeline owns the single top-level <Theme>. Prefer the resolved theme
    # from state; fall back to scraping a slide only if state has none.
    theme = (state.get("resolved_theme") or {}).get("element") or state.get("theme_element", "")

    combined_xml = assemble_deck_xml([s["xml"] for s in sorted_slides], theme)
    if not combined_xml:
        logger.error("deck_assembler: no valid <Slide> blocks found")
        return {
            "compile_result": {
                "ok": False, "pptx_path": None,
                "diagnostics": [{"type": "ASSEMBLY", "message": "No valid Slide blocks"}],
                "warnings": [], "retryable": False,
            },
        }
    if not theme:
        theme = _extract_theme(combined_xml)
    logger.info(f"deck_assembler: assembled {len(sorted_slides)} slides, {len(combined_xml)} chars")

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

    forbidden_tags = (state.get("contract") or {}).get("forbidden_tags", [])
    working_xml = combined_xml
    attempt = 0
    while (
        not compile_result.get("ok", False)
        and compile_result.get("retryable", False)
        and attempt < MAX_DECK_REPAIR_ATTEMPTS
    ):
        attempt += 1
        diags = compile_result.get("diagnostics", [])
        logger.info(f"deck_assembler: compile failed, repair attempt {attempt}/{MAX_DECK_REPAIR_ATTEMPTS}")

        try:
            repaired = _call_deck_repair_llm(
                working_xml, diags,
                forbidden_tags=forbidden_tags, theme_element=theme,
            )
        except Exception as exc:
            logger.error(f"deck_assembler: repair LLM call failed: {exc}")
            break

        working_xml = ensure_single_theme(normalize_xml(repaired)["cleaned_xml"], theme)
        try:
            compile_result = compile_xml(working_xml, output_dir / f"repair-{attempt}")
        except CompilerError as exc:
            logger.error(f"deck_assembler: repair compile error: {exc}")
            break

    status = "OK" if compile_result.get("ok", False) else "FAILED"
    logger.info(f"deck_assembler: final compile {status}")
    if compile_result.get("pptx_path"):
        logger.info(f"deck_assembler: pptx → {compile_result['pptx_path']}")

    return {
        "current_xml": working_xml,
        "compile_result": compile_result,
        "pptx_path": compile_result.get("pptx_path"),
    }
