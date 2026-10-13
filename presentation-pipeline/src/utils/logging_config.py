"""Structured logging with contextvars for run_id, step, and model.

Usage:
    from src.utils.logging_config import setup_logging, set_context

    setup_logging()
    set_context(run_id="abc123", step="generator", model="gpt-4.1-mini")
    logger.info("generating XML")
    # => generator | [abc123] [generator] [gpt-4.1-mini] generating XML
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from pathlib import Path

run_id_var: ContextVar[str] = ContextVar("run_id", default="")
step_var: ContextVar[str] = ContextVar("step", default="")
model_var: ContextVar[str] = ContextVar("model", default="")


def set_context(
    *,
    run_id: str | None = None,
    step: str | None = None,
    model: str | None = None,
) -> None:
    """Set one or more context variables for structured log output."""
    if run_id is not None:
        run_id_var.set(run_id)
    if step is not None:
        step_var.set(step)
    if model is not None:
        model_var.set(model)


class ContextFilter(logging.Filter):
    """Injects run_id, step, model from contextvars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = run_id_var.get("")  # type: ignore[attr-defined]
        record.step = step_var.get("")  # type: ignore[attr-defined]
        record.model = model_var.get("")  # type: ignore[attr-defined]
        return True


_FORMAT = "%(name)s | [%(run_id)s] [%(step)s] [%(model)s] %(message)s"
_FORMAT_COMPACT = "%(name)s | %(message)s"


def setup_logging(*, level: int = logging.INFO, use_context: bool = True) -> None:
    """Configure root logger with contextvars filter.

    Args:
        level: Logging level (default INFO).
        use_context: If True, log lines include [run_id] [step] [model].
                     If False, use compact format (for tests).
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    fmt = _FORMAT if use_context else _FORMAT_COMPACT
    handler.setFormatter(logging.Formatter(fmt))

    if use_context:
        handler.addFilter(ContextFilter())

    root.setLevel(level)
    root.addHandler(handler)
    # fontTools' subsetter (font_embed) logs every glyph list at INFO: thousands of lines per deck
    logging.getLogger("fontTools").setLevel(max(level, logging.WARNING))


def add_file_log(path: str | Path, *, level: int = logging.INFO) -> logging.Handler:
    """Also write every log line to `path` in UTF-8, uncut. A console log saved by PowerShell
    (`2>&1 | Tee-Object`) cuts each line at the window width, which lost the start of the
    unreadable planner text in the 2026-10-13 paid runs. Returns the handler; remove and close
    it when the run is done."""
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(ContextFilter())
    logging.getLogger().addHandler(handler)
    return handler
