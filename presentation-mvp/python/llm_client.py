"""OpenAI Chat Completions wrapper.

Chat Completions only (`client.chat.completions.create`) — never the Responses
API. temp / model / max_tokens come from config (env). No key is ever hardcoded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import config
from models import TokenUsage


@dataclass
class LLMResponse:
    text: str
    tokens: TokenUsage
    model: str
    finish_reason: str | None = None
    raw: object | None = None


class LLMClient:
    def __init__(self, settings: config.Settings | None = None):
        self.settings = settings or config.settings
        self._client = None  # lazy — importing openai should not be required for --dry-run

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The 'openai' package is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self.settings.require_api_key()
        kwargs = {"api_key": self.settings.openai_api_key}
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        client = OpenAI(**kwargs)

        # LangSmith tracing: when LANGSMITH_TRACING=true (see .env), wrap the
        # client so every chat.completions.create call is logged as a run in
        # the LANGSMITH_PROJECT project. No-op if langsmith is not installed
        # or tracing is disabled.
        if os.environ.get("LANGSMITH_TRACING", "").strip().lower() == "true":
            try:
                from langsmith.wrappers import wrap_openai

                client = wrap_openai(client)
            except ImportError:  # pragma: no cover
                pass

        self._client = client
        return self._client

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        client = self._ensure_client()
        try:
            from openai import OpenAIError
        except ImportError:  # pragma: no cover
            OpenAIError = Exception  # type: ignore
        try:
            resp = client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except OpenAIError as exc:  # network / auth / quota / rate limit
            raise RuntimeError(f"OpenAI API call failed: {exc}") from exc
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=(choice.message.content or "").strip(),
            tokens=TokenUsage(
                input=getattr(usage, "prompt_tokens", 0) or 0,
                output=getattr(usage, "completion_tokens", 0) or 0,
            ),
            model=resp.model,
            finish_reason=choice.finish_reason,
            raw=resp,
        )
