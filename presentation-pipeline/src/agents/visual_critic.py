"""Visual critic — screenshot-based quality review using a vision LLM.

Encodes the slide screenshot as base64, sends to gpt-4.1 (vision-capable)
alongside the POM XML, slide plan context, design contract, and compile
warnings. Returns structured issues with repair hints that drive the
repair loop.

Called from critic_node() when a screenshot is available, and from
slide_edit_service after user edits.
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents.critic_schema import VisualCriticOutput
from src.utils.llm_client import get_llm, unpack_raw

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "visual_critic"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    keep_trailing_newline=True,
)

_SKIP_NOTE_KEYWORDS = {"tag", "attribute", "forbidden", "must not use", "allowed_nodes"}


def _encode_image(image_path: str) -> str:
    """Read an image file and return its base64 encoding."""
    return base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")


def _filter_visual_notes(notes: list[str]) -> list[str]:
    """Keep only layout/visual-relevant notes from the contract."""
    return [n for n in notes if not any(kw in n.lower() for kw in _SKIP_NOTE_KEYWORDS)]


def _empty_repair_hints() -> dict[str, Any]:
    return {"strategy": "none", "assessment": "good", "affected_nodes": []}


# Size, spacing and fill are set by code after generation (fit-grow: growth, spill fix,
# centring) and re-applied after every repair, so an LLM fix there is undone or fights it
# (2026-10-07). A visible defect (overlap, clipping, unreadable text) is still kept.
_SIZE_TALK = re.compile(r"font ?size|fontsize|padding|\bgap\b|\bgrow\b|minh|\bmargin|spacing|white ?space"
                        r"|empty (space|area|band)|under-?filled|oversized|too (large|big|small)", re.IGNORECASE)
_DEFECT_TALK = re.compile(r"overlap|overflow|clip|cut ?off|truncat|collid|off the slide|outside|missing"
                          r"|invisible|contrast|unreadable|illegible", re.IGNORECASE)


def code_owned(description: str, fix: str) -> bool:
    text = f"{description} {fix}"
    return bool(_SIZE_TALK.search(text)) and not _DEFECT_TALK.search(text)


def run_visual_critic(
    screenshot_path: str,
    current_xml: str,
    slide_plan: dict[str, Any],
    theme_element: str,
    contract: dict[str, Any] | None = None,
    compile_warnings: list[dict[str, str]] | None = None,
    layout_issues: list[dict[str, str]] | None = None,
    previous_issues: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Run vision LLM on the screenshot and return (issues, usage, repair_hints).

    Returns ([], zero_usage, empty_hints) on any failure (fail-open).
    """
    zero_usage = {"tokens_in": 0, "tokens_out": 0, "model": "unknown"}
    if not Path(screenshot_path).exists():
        logger.warning(f"visual_critic: screenshot not found: {screenshot_path}")
        return [], zero_usage, _empty_repair_hints()

    contract = contract or {}

    system_tmpl = _jinja_env.get_template("system.j2")
    user_tmpl = _jinja_env.get_template("user.j2")

    slide_type = slide_plan.get("slide_type", "")
    system_prompt = system_tmpl.render(slide_type=slide_type)
    user_text = user_tmpl.render(
        current_xml=current_xml,
        slide_type=slide_type,
        components=slide_plan.get("components", []),
        theme_element=theme_element,
        component_count=contract.get("component_count", 0),
        compile_warnings=compile_warnings or [],
        layout_issues=layout_issues or [],
        visual_notes=_filter_visual_notes(contract.get("notes", [])),
        previous_issues=previous_issues or [],
    )

    image_b64 = _encode_image(screenshot_path)

    llm = get_llm("visual_critic")
    structured_llm = llm.with_structured_output(
        VisualCriticOutput, method="json_schema", include_raw=True,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "high",
                    },
                },
                {"type": "text", "text": user_text},
            ],
        },
    ]

    try:
        raw_result = structured_llm.invoke(messages)
    except Exception as e:
        logger.error(f"visual_critic: LLM call failed: {e}")
        return [], zero_usage, _empty_repair_hints()

    result, usage = unpack_raw(raw_result)

    issues = []
    all_affected_nodes: list[str] = []
    dropped = 0
    for issue in result.issues:
        if code_owned(issue.description, issue.fix):
            dropped += 1
            continue
        issues.append({
            "severity": issue.severity,
            "type": issue.type,
            "description": f"[Visual] {issue.description}",
            "fix": issue.fix,
            "affected_nodes": issue.affected_nodes,
            "source": "visual",
        })
        all_affected_nodes.extend(issue.affected_nodes)

    repair_hints = {
        "strategy": result.repair_strategy,
        "assessment": result.overall_assessment,
        "affected_nodes": sorted(set(all_affected_nodes)),
    }

    if dropped:
        logger.info(f"visual_critic: dropped {dropped} size / spacing issue(s): code owns them (fit-grow)")
    logger.info(
        f"visual_critic: {len(issues)} issue(s), "
        f"assessment={result.overall_assessment}, strategy={result.repair_strategy}"
    )
    logger.info(f"visual_critic: {usage['model']} tokens_in={usage['tokens_in']} tokens_out={usage['tokens_out']}")
    return issues, usage, repair_hints
