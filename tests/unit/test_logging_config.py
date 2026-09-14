"""Tests for the contextvars logging utility."""

import logging

from src.utils.logging_config import set_context, ContextFilter, run_id_var, step_var, model_var


def test_set_context_run_id():
    set_context(run_id="test-123")
    assert run_id_var.get() == "test-123"
    set_context(run_id="")


def test_set_context_step():
    set_context(step="generator")
    assert step_var.get() == "generator"
    set_context(step="")


def test_set_context_model():
    set_context(model="gpt-4.1-mini")
    assert model_var.get() == "gpt-4.1-mini"
    set_context(model="")


def test_set_context_partial():
    set_context(run_id="r1")
    set_context(step="planner")
    assert run_id_var.get() == "r1"
    assert step_var.get() == "planner"
    set_context(run_id="", step="")


def test_context_filter_injects_fields():
    filt = ContextFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )

    set_context(run_id="abc", step="gen", model="mini")
    filt.filter(record)

    assert record.run_id == "abc"  # type: ignore[attr-defined]
    assert record.step == "gen"  # type: ignore[attr-defined]
    assert record.model == "mini"  # type: ignore[attr-defined]

    set_context(run_id="", step="", model="")


def test_context_filter_defaults():
    set_context(run_id="", step="", model="")
    filt = ContextFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    filt.filter(record)
    assert record.run_id == ""  # type: ignore[attr-defined]
    assert record.step == ""  # type: ignore[attr-defined]
    assert record.model == ""  # type: ignore[attr-defined]
