"""POM leaves out an <Arrow> whose id is missing or not connectable and only warns (2026-11-17, render
check on POM 10.3.0): the compile result fails it so the slide is repaired instead of shipping a diagram with a
connector missing."""

from __future__ import annotations

from src.compiler.compiler_client import _parse_result


def _result(warnings):
    return {"status": "success", "pptxPath": "x.pptx", "diagnostics": [], "warnings": warnings}


def test_lost_arrow_fails_the_compile_and_is_retryable():
    r = _parse_result(_result([{"code": "ARROW_REF_NOT_CONNECTABLE",
                                "message": 'Arrow: ID "d" does not reference a connector-compatible Shape'}]))
    assert r["ok"] is False and r["retryable"] is True
    assert r["diagnostics"] == [{"type": "ARROW_REF_NOT_CONNECTABLE",
                                 "message": 'Arrow: ID "d" does not reference a connector-compatible Shape'}]
    assert _parse_result(_result([{"code": "ARROW_REF_NOT_FOUND", "message": "m"}]))["ok"] is False


def test_other_warnings_leave_the_compile_ok():
    r = _parse_result(_result([{"code": "NODE_OUT_OF_BOUNDS", "message": "m"}]))
    assert r["ok"] is True and r["diagnostics"] == []
