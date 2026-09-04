"""Multi-model LLM client. Reads models.yaml for per-step config.

Usage:
    from src.utils.llm_client import get_llm

    llm = get_llm("planner")          # ChatOpenAI configured for the planner step
    llm = get_llm("generator")        # different model/temp for generator
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml
from langchain_openai import AzureChatOpenAI, ChatOpenAI

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


def get_llm(step: str, **overrides: Any) -> ChatOpenAI | AzureChatOpenAI:
    """Build a LangChain chat model for the given pipeline step.

    Reads models.yaml for model/temperature/max_tokens, falls back to env vars,
    then applies any explicit overrides.
    """
    cfg = get_step_config(step)
    cfg.update(overrides)

    provider = cfg.get("provider", "openai")
    model = cfg.get("model", os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    temperature = cfg.get("temperature", 0.2)
    max_tokens = cfg.get("max_tokens", 2000)

    if provider == "azure_openai":
        return AzureChatOpenAI(
            azure_deployment=model,
            azure_endpoint=cfg.get("azure_endpoint", os.environ.get("AZURE_OPENAI_ENDPOINT", "")),
            api_version=cfg.get("azure_api_version", "2024-12-01-preview"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.environ.get("OPENAI_API_KEY", "not-set"),
    )


def get_pricing(model: str) -> dict[str, float]:
    """Return {input, output} cost per 1M tokens for a model name."""
    cfg = _load_models_config()
    pricing = cfg.get("pricing") or {}
    return pricing.get(model, {"input": 0.0, "output": 0.0})
