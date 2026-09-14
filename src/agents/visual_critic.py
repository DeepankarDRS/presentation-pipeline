"""Visual critic — screenshot-based quality review using a vision LLM.

Encodes the slide screenshot as base64, sends to gpt-4.1-mini (vision-capable)
alongside the POM XML and slide plan context. Returns issues in the same
format as the text-based critic so they merge seamlessly.

Called from critic_node() when a screenshot is available.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents.critic_schema import CriticOutput
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "visual_critic"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    keep_trailing_newline=True,
)


def _encode_image(image_path: str) -> str:
    """Read an image file and return its base64 encoding."""
    return base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")


def run_visual_critic(
    screenshot_path: str,
    current_xml: str,
    slide_plan: dict[str, Any],
    theme_element: str,
) -> list[dict[str, Any]]:
    """Run vision LLM on the screenshot and return visual issues.

    Returns an empty list on any failure (fail-open, same as text critic).
    """
    if not Path(screenshot_path).exists():
        logger.warning(f"visual_critic: screenshot not found: {screenshot_path}")
        return []

    system_tmpl = _jinja_env.get_template("system.j2")
    user_tmpl = _jinja_env.get_template("user.j2")

    system_prompt = system_tmpl.render()
    user_text = user_tmpl.render(
        current_xml=current_xml,
        slide_type=slide_plan.get("slide_type", ""),
        components=slide_plan.get("components", []),
    )

    image_b64 = _encode_image(screenshot_path)

    llm = get_llm("visual_critic")
    structured_llm = llm.with_structured_output(CriticOutput, method="json_schema")

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
        result: CriticOutput = structured_llm.invoke(messages)
    except Exception as e:
        logger.error(f"visual_critic: LLM call failed: {e}")
        return []

    issues = []
    for issue in result.issues:
        issues.append({
            "severity": issue.severity,
            "type": issue.type,
            "description": f"[Visual] {issue.description}",
            "fix": issue.fix,
            "source": "visual",
        })

    logger.info(f"visual_critic: found {len(issues)} visual issue(s)")
    return issues
