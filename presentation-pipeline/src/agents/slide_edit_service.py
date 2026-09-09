"""Slide edit service — LLM-powered XML editing with mini repair loop.

Takes user NL feedback + current XML, produces modified XML that compiles.
Reuses the same normalizer, compiler, and repair guidance as the main pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents.repairer import build_patch_prompts
from src.compiler.compiler_client import CompilerError, compile_xml
from src.compiler.normalizer import ensure_single_theme, normalize_xml
from src.compiler.repair_guidance import error_signatures, is_stalled
from src.compiler.screenshot import render_screenshots
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "slide_editor"
_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    keep_trailing_newline=True,
)

MAX_REPAIR_ATTEMPTS = 2


@dataclass
class SlideEditResult:
    ok: bool
    xml: str = ""
    pptx_path: str | None = None
    screenshot_path: str | None = None
    compile_ok: bool = False
    repair_attempts: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def _render_system_prompt(contract: dict[str, Any]) -> str:
    system_tmpl = _jinja_env.get_template("system.j2")
    return system_tmpl.render(
        forbidden_tags=contract.get("forbidden_tags", []),
        forbidden_attributes=contract.get("forbidden_attributes", []),
        allowed_nodes=contract.get("allowed_nodes", []),
        notes=contract.get("notes", []),
        layout_pattern=contract.get("layout_pattern", ""),
    )


def _call_edit_llm(
    current_xml: str,
    feedback: str,
    theme_element: str,
    contract: dict[str, Any],
    slide_plan: dict[str, Any],
) -> str:
    """Call the LLM to apply the user's edit instruction to the XML."""
    user_tmpl = _jinja_env.get_template("user.j2")

    system_prompt = _render_system_prompt(contract)
    user_prompt = user_tmpl.render(
        current_xml=current_xml,
        theme_element=theme_element,
        feedback=feedback,
        slide_type=slide_plan.get("slide_type", ""),
        components=slide_plan.get("components", []),
        density=slide_plan.get("density", ""),
        layout_hint=slide_plan.get("layout_hint", ""),
    )

    llm = get_llm("slide_editor")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.invoke(messages)
    return response.content


def _call_repair_llm(
    failing_xml: str,
    problems: list[str],
    pre_issues: list[dict[str, Any]],
    compile_diags: list[dict[str, Any]],
    objective: str,
    theme_element: str,
    contract: dict[str, Any],
) -> str:
    """Fix compile errors with the shared tier-1 patch prompt.

    Reuses the main pipeline repairer's prompt and error-scoped node reference,
    so the repair LLM sees attribute docs and a verified syntax example for
    exactly the nodes that failed.
    """
    system_prompt, user_prompt = build_patch_prompts(
        failing_xml=failing_xml,
        problems=problems,
        pre_issues=pre_issues,
        compile_diags=compile_diags,
        objective=objective,
        forbidden_tags=contract.get("forbidden_tags", []),
        theme_element=contract.get("theme_element") or theme_element,
    )

    llm = get_llm("slide_editor")
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return response.content


def edit_slide_xml(
    current_xml: str,
    feedback: str,
    theme_element: str,
    contract: dict[str, Any],
    slide_plan: dict[str, Any],
    run_id: str,
    slide_index: int,
    version: int,
) -> SlideEditResult:
    """Apply a user's NL edit to a slide XML, validate, and repair if needed.

    Returns SlideEditResult — never raises.
    """
    output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "edits" / f"slide-{slide_index}-v{version}"

    try:
        edited_xml = _call_edit_llm(current_xml, feedback, theme_element, contract, slide_plan)
    except Exception as e:
        logger.error(f"slide_editor: LLM edit call failed: {e}")
        return SlideEditResult(ok=False, xml=current_xml, error=f"LLM edit failed: {e}")

    # Normalize + ensure the theme is present for compilation. current_xml is
    # theme-less (the generator never emits <Theme>, and the main pipeline
    # only injects it locally for compilation, same as here) — without it
    # $tokens won't resolve. finalize_deck strips it back out per-slide later.
    norm = normalize_xml(edited_xml)
    working_xml = ensure_single_theme(norm.get("cleaned_xml", edited_xml), theme_element)

    # Compile
    try:
        cr = compile_xml(working_xml, output_dir)
    except CompilerError as e:
        return SlideEditResult(ok=False, xml=current_xml, error=f"Compiler error: {e}")

    if cr.get("ok", False):
        screenshot_path = _try_screenshot(cr.get("pptx_path"), str(output_dir / "screenshots"))
        return SlideEditResult(
            ok=True,
            xml=working_xml,
            pptx_path=cr.get("pptx_path"),
            screenshot_path=screenshot_path,
            compile_ok=True,
        )

    # Mini repair loop
    if not cr.get("retryable", False):
        return SlideEditResult(
            ok=False, xml=current_xml, compile_ok=False,
            issues=cr.get("diagnostics", []),
            error="Compile failed with non-retryable errors",
        )

    title = slide_plan.get("content_data", {}).get("title", "")
    objective = f"{title} — apply user edit: {feedback}".lstrip(" —")

    prev_sigs: set[str] = set()
    for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
        logger.info(f"slide_editor: repair attempt {attempt}/{MAX_REPAIR_ATTEMPTS}")

        diags = cr.get("diagnostics", [])
        pre_issues = [i for i in norm.get("issues", []) if not i.get("auto_fixed", False)]
        problems = [f"{d['type']}: {d['message']}" for d in diags]

        sigs = error_signatures(pre_issues, diags)
        if prev_sigs and is_stalled(prev_sigs, sigs):
            logger.info("slide_editor: repair stalled (errors unchanged), stopping")
            break
        prev_sigs = sigs

        try:
            repaired_xml = _call_repair_llm(
                working_xml, problems, pre_issues, diags, objective, theme_element, contract,
            )
        except Exception as e:
            logger.error(f"slide_editor: repair LLM call failed: {e}")
            break

        norm = normalize_xml(repaired_xml)
        working_xml = ensure_single_theme(norm.get("cleaned_xml", repaired_xml), theme_element)

        repair_dir = output_dir / f"repair-{attempt}"
        try:
            cr = compile_xml(working_xml, repair_dir)
        except CompilerError:
            break

        if cr.get("ok", False):
            screenshot_path = _try_screenshot(cr.get("pptx_path"), str(repair_dir / "screenshots"))
            return SlideEditResult(
                ok=True,
                xml=working_xml,
                pptx_path=cr.get("pptx_path"),
                screenshot_path=screenshot_path,
                compile_ok=True,
                repair_attempts=attempt,
            )

    return SlideEditResult(
        ok=False, xml=current_xml, compile_ok=False,
        repair_attempts=MAX_REPAIR_ATTEMPTS,
        issues=cr.get("diagnostics", []),
        error=f"Compile failed after {MAX_REPAIR_ATTEMPTS} repair attempts",
    )


def _try_screenshot(pptx_path: str | None, output_dir: str) -> str | None:
    """Attempt screenshot, retrying once on failure. Returns path or None.

    A failure here doesn't fail the edit (the XML already compiled fine and
    is what ends up in the download) — but it does leave the review UI
    showing a stale preview, so log clearly and give transient rendering
    failures one retry before giving up. The retry waits briefly first:
    back-to-back PowerPoint COM automation calls commonly hit "call rejected
    by callee" if the previous call's PowerPoint instance hasn't fully
    released before the next one starts — an instant retry just repeats
    the same rejection.
    """
    if not pptx_path:
        return None
    for attempt in (1, 2):
        if attempt > 1:
            time.sleep(2)
        batch = render_screenshots(pptx_path, output_dir)
        if batch.ok and batch.slides:
            return batch.slides[0].png_path
        logger.warning(f"slide_editor: screenshot attempt {attempt}/2 failed: {batch.error}")
    return None
