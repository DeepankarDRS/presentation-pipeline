"""Multi-model LLM client. Reads models.yaml for per-step config.

Usage:
    from src.utils.llm_client import get_llm

    llm = get_llm("planner")          # ChatOpenAI configured for the planner step
    llm = get_llm("generator")        # different model/temp for generator
"""

from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from langchain_openai import AzureChatOpenAI, ChatOpenAI

logger = logging.getLogger(__name__)

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_FILE = _PIPELINE_ROOT / "models.yaml"


@functools.lru_cache(maxsize=1)
def _load_models_config() -> dict[str, Any]:
    if not _MODELS_FILE.exists():
        return {}
    return yaml.safe_load(_MODELS_FILE.read_text(encoding="utf-8")) or {}


def get_step_config(step: str) -> dict[str, Any]:
    """Return the merged config for a pipeline step (step overrides + defaults)."""
    cfg = _load_models_config()
    defaults = dict(cfg.get("defaults") or {})
    step_cfg = dict((cfg.get("steps") or {}).get(step) or {})
    merged = {**defaults, **step_cfg}
    return merged


_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _is_reasoning_model(model: str) -> bool:
    """OpenAI reasoning models (GPT-5 family, o-series) reject temperature and take reasoning_effort."""
    return model.lower().startswith(_REASONING_PREFIXES)


def _sampling_kwargs(step: str, model: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """temperature for chat models; reasoning_effort (default medium) for reasoning models.

    Reasoning tokens count against max_tokens, so a reasoning step needs a far larger
    max_tokens than the same step on gpt-4.1 (see models.yaml).
    """
    if _is_reasoning_model(model):
        effort = cfg.get("reasoning_effort", "medium")
        logger.info("get_llm: %s uses reasoning model %s (reasoning_effort=%s)", step, model, effort)
        return {"reasoning_effort": effort}
    return {"temperature": cfg.get("temperature", 0.2)}


def get_llm(step: str, **overrides: Any) -> ChatOpenAI | AzureChatOpenAI:
    """Build a LangChain chat model for the given pipeline step.

    Reads models.yaml for model/temperature/max_tokens (reasoning_effort for
    reasoning models), falls back to env vars, then applies any explicit overrides.
    """
    cfg = get_step_config(step)
    cfg.update(overrides)

    provider = cfg.get("provider", "openai")
    model = cfg.get("model", os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    max_tokens = cfg.get("max_tokens", 2000)
    sampling = _sampling_kwargs(step, model, cfg)

    if provider == "azure_openai":
        return AzureChatOpenAI(
            azure_deployment=model,
            azure_endpoint=cfg.get("azure_endpoint", os.environ.get("AZURE_OPENAI_ENDPOINT", "")),
            api_version=cfg.get("azure_api_version", "2024-12-01-preview"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
            max_tokens=max_tokens,
            **sampling,
        )

    return ChatOpenAI(
        model=model,
        max_tokens=max_tokens,
        api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
        **sampling,
    )


_ZERO_USAGE: dict[str, Any] = {"tokens_in": 0, "tokens_out": 0, "tokens_reasoning": 0, "tokens_cached": 0,
                               "model": "unknown"}


def extract_usage(response) -> dict[str, Any]:
    """Extract tokens_in, tokens_out, tokens_reasoning, tokens_cached, model from an AIMessage's metadata.

    tokens_out already includes tokens_reasoning (OpenAI bills them as output) and tokens_in
    already includes tokens_cached (billed at a discount), so cost stays tokens_in / tokens_out;
    tokens_reasoning and tokens_cached are for reading only.
    """
    meta = getattr(response, "response_metadata", None) or {}
    token_usage = meta.get("token_usage") or {}
    details = token_usage.get("completion_tokens_details") or {}
    prompt_details = token_usage.get("prompt_tokens_details") or {}
    return {
        "tokens_in": token_usage.get("prompt_tokens", 0),
        "tokens_out": token_usage.get("completion_tokens", 0),
        "tokens_reasoning": details.get("reasoning_tokens") or 0,
        "tokens_cached": prompt_details.get("cached_tokens") or 0,
        "model": meta.get("model_name", "unknown"),
    }


def usage_record(usage: dict[str, Any], step: str, slide_index: int | None = None, **extra: Any) -> dict[str, Any]:
    """One generation_history entry for an LLM call, named by pipeline step and slide.

    `step` is the pipeline step (elicitor, outline_planner, slide_component_planner,
    plan_reviewer, generator, repairer, critic, visual_repairer); `slide_index` is 0-based,
    None for a deck-level call. The run manifest and scripts/usage_report.py read these.
    """
    return {"attempt": 0, "tier": 0, **usage, "step": step, "slide_index": slide_index, **extra}


def unpack_raw(result) -> tuple[Any, dict[str, Any]]:
    """Unpack a with_structured_output(include_raw=True) result.

    Returns (parsed_object, usage_dict). Falls back gracefully when the
    result is already a parsed Pydantic model (e.g. in test mocks that
    don't use include_raw).
    """
    if isinstance(result, dict) and "parsed" in result and "raw" in result:
        return result["parsed"], extract_usage(result["raw"])
    return result, dict(_ZERO_USAGE)


def get_pricing(model: str) -> dict[str, float]:
    """Return {input, output} cost per 1M tokens for a model name."""
    cfg = _load_models_config()
    pricing = cfg.get("pricing") or {}
    if model in pricing:
        return pricing[model]
    candidates = [k for k in pricing if model.startswith(k)]
    if candidates:
        return pricing[max(candidates, key=len)]
    logger.warning("get_pricing: no pricing entry for %r; cost will be 0", model)
    return {"input": 0.0, "output": 0.0}
