"""Generator agent — produces POM XML from the plan + contract + data.

Uses tiered Jinja2 prompt assembly:
  - minimal (sparse): theme + allowed nodes + 1 example (~1K tokens)
  - standard (normal/dense): + component rules + layout (~2.5K tokens)
  - dense (tight_fit): + all pitfalls + shrink checklist (~3.2K tokens)

Reads:  contract, theme_element, slide_plans, supplied_content
Writes: current_xml, generation_history
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.state import AttemptRecord, PresentationState
from src.utils.llm_client import get_llm

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "generator"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    keep_trailing_newline=True,
)


def _render_prompts(state: PresentationState) -> tuple[str, str]:
    """Render system + user prompts from the contract and slide plan."""
    contract = state.get("contract") or {}
    slide_plans = state.get("slide_plans", [])
    idx = state.get("current_slide_index", 0)
    plan = slide_plans[idx] if slide_plans and idx < len(slide_plans) else {}

    system_tmpl = _jinja_env.get_template("system.j2")
    user_tmpl = _jinja_env.get_template("user.j2")

    system_prompt = system_tmpl.render(
        forbidden_tags=contract.get("forbidden_tags", []),
        forbidden_attributes=contract.get("forbidden_attributes", []),
        theme_element=contract.get("theme_element", state.get("theme_element", "")),
        allowed_nodes=contract.get("allowed_nodes", []),
        allowed_attributes=contract.get("allowed_attributes", {}),
        density_tier=contract.get("density_tier", "standard"),
        layout_pattern=contract.get("layout_pattern", ""),
        example=contract.get("example", ""),
        notes=contract.get("notes", []),
    )

    components = plan.get("components", [])
    user_prompt = user_tmpl.render(
        objective=state.get("raw_request", ""),
        components=components,
        density=plan.get("density", "normal"),
        font_tier=plan.get("font_tier", "standard"),
        layout_hint=plan.get("layout_hint", ""),
        content_data=plan.get("content_data", {}),
        supplied_content=state.get("supplied_content"),
    )

    return system_prompt, user_prompt

def generator_node(state: PresentationState) -> dict[str, Any]:
    """Generate POM XML via LLM using tiered prompts from the contract."""
    logger.info("generator: rendering prompts and calling LLM")

    system_prompt, user_prompt = _render_prompts(state)

    llm = get_llm("generator")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.invoke(messages)
    raw_xml = response.content

    token_usage = response.response_metadata.get("token_usage", {})
    tokens_in = token_usage.get("prompt_tokens", 0)
    tokens_out = token_usage.get("completion_tokens", 0)
    model = response.response_metadata.get("model_name", "unknown")

    logger.info(f"generator: {model} tokens_in={tokens_in} tokens_out={tokens_out}")

    record = AttemptRecord(
        attempt=state.get("retry_count", 0),
        tier=state.get("retry_tier", 0),
        errors_in=[],
        errors_out=[],
        stalled=False,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
    )

    return {
        "current_xml": raw_xml,
        "generation_history": [record],
    }
