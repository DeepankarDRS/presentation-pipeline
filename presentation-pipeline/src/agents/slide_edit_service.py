"""Slide edit service — LLM-powered XML editing with mini repair loop.

Takes user NL feedback + current XML, produces modified XML that compiles.
Reuses the same normalizer, compiler, and repair guidance as the main pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.compiler.compiler_client import CompilerError, compile_xml
from src.compiler.normalizer import normalize_xml
from src.compiler.repair_guidance import (
    build_error_guidance,
    select_repair_knowledge,
)
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


def _call_edit_llm(
    current_xml: str,
    feedback: str,
    theme_element: str,
    contract: dict[str, Any],
) -> str:
    """Call the LLM to apply the user's edit instruction to the XML."""
    system_tmpl = _jinja_env.get_template("system.j2")
    user_tmpl = _jinja_env.get_template("user.j2")

    system_prompt = system_tmpl.render(
        forbidden_tags=contract.get("forbidden_tags", []),
    )
    user_prompt = user_tmpl.render(
        current_xml=current_xml,
        theme_element=theme_element,
        feedback=feedback,
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
    guidance: str,
    feedback: str,
    theme_element: str,
    contract: dict[str, Any],
) -> str:
    """Call the LLM to fix compile errors while preserving the user's edit intent."""
    system_tmpl = _jinja_env.get_template("system.j2")
    system_prompt = system_tmpl.render(
        forbidden_tags=contract.get("forbidden_tags", []),
    )

    user_prompt = (
        f"## FAILING XML\n{failing_xml}\n\n"
        f"## COMPILE ERRORS\n" + "\n".join(f"- {p}" for p in problems) + "\n\n"
        f"## ERROR GUIDANCE\n{guidance}\n\n"
        f"## ORIGINAL USER INSTRUCTION\n{feedback}\n\n"
        f"## THEME\n{theme_element}\n\n"
        "Fix the compile errors while keeping the user's edit intent. "
        "Return the complete corrected XML."
    )

    llm = get_llm("slide_editor")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.invoke(messages)
    return response.content


def edit_slide_xml(
    current_xml: str,
    feedback: str,
    theme_element: str,
    contract: dict[str, Any],
    run_id: str,
    slide_index: int,
    version: int,
) -> SlideEditResult:
    """Apply a user's NL edit to a slide XML, validate, and repair if needed.

    Returns SlideEditResult — never raises.
    """
    output_dir = _PIPELINE_ROOT / "output" / "runs" / run_id / "edits" / f"slide-{slide_index}-v{version}"

    try:
        edited_xml = _call_edit_llm(current_xml, feedback, theme_element, contract)
    except Exception as e:
        logger.error(f"slide_editor: LLM edit call failed: {e}")
        return SlideEditResult(ok=False, xml=current_xml, error=f"LLM edit failed: {e}")

    # Normalize
    norm = normalize_xml(edited_xml)
    working_xml = norm.get("cleaned_xml", edited_xml)

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

    for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
        logger.info(f"slide_editor: repair attempt {attempt}/{MAX_REPAIR_ATTEMPTS}")

        diags = cr.get("diagnostics", [])
        pre_issues = [i for i in norm.get("issues", []) if not i.get("auto_fixed", False)]
        problems = [f"{d['type']}: {d['message']}" for d in diags]
        guidance = build_error_guidance(pre_issues, diags)

        try:
            repaired_xml = _call_repair_llm(
                working_xml, problems, guidance, feedback, theme_element, contract,
            )
        except Exception as e:
            logger.error(f"slide_editor: repair LLM call failed: {e}")
            break

        norm = normalize_xml(repaired_xml)
        working_xml = norm.get("cleaned_xml", repaired_xml)

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
    """Attempt screenshot, return path or None."""
    if not pptx_path:
        return None
    batch = render_screenshots(pptx_path, output_dir)
    if batch.ok and batch.slides:
        return batch.slides[0].png_path
    return None
