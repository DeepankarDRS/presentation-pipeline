"""Tests for the evaluator agent — scoring, cost tracking, manifest."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.agents.evaluator import evaluator_node, _compute_cost, _build_step_summary
from src.state import initial_state


def _make_state(**overrides):
    state = initial_state(run_id="eval-test", raw_request="Test slide")
    state["compile_result"] = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    state["critic_result"] = {"passed": True, "issues": []}
    state["generation_history"] = [{
        "attempt": 0, "tier": 0, "model": "gpt-4.1-mini",
        "tokens_in": 500, "tokens_out": 200,
        "errors_in": [], "errors_out": [], "stalled": False,
    }]
    state.update(overrides)
    return state


# ── Cost computation ─────────────────────────────────────────────────────

def test_compute_cost_mini():
    cost = _compute_cost(1_000_000, 1_000_000, "gpt-4.1-mini")
    assert cost == 2.0  # 0.40 input + 1.60 output


def test_compute_cost_unknown_model():
    cost = _compute_cost(1000, 1000, "unknown-model")
    assert cost == 0.0


def test_compute_cost_zero_tokens():
    cost = _compute_cost(0, 0, "gpt-4.1-mini")
    assert cost == 0.0


# ── Step summary ─────────────────────────────────────────────────────────

def test_build_step_summary():
    history = [
        {"attempt": 0, "tier": 0, "model": "gpt-4.1-mini",
         "tokens_in": 500, "tokens_out": 200,
         "errors_in": [], "errors_out": [], "stalled": False},
        {"attempt": 1, "tier": 1, "model": "gpt-4.1-mini",
         "tokens_in": 800, "tokens_out": 300,
         "errors_in": ["ERR1"], "errors_out": [], "stalled": True},
    ]
    summary = _build_step_summary(history)
    assert len(summary) == 2
    assert summary[0]["attempt"] == 0
    assert summary[0]["cost"] > 0
    assert summary[1]["stalled"] is True
    assert summary[1]["errors_in_count"] == 1


# ── Evaluator node ───────────────────────────────────────────────────────

def test_evaluator_pass():
    state = _make_state()
    result = evaluator_node(state)
    assert result["passed"] is True
    assert result["pptx_path"] == "/tmp/test.pptx"
    assert result["evaluation"]["compile_ok"] is True
    assert result["evaluation"]["critic_ok"] is True


def test_evaluator_fail_compile():
    state = _make_state()
    state["compile_result"] = {
        "ok": False, "pptx_path": None,
        "diagnostics": [{"type": "ERR", "message": "broken"}],
        "warnings": [], "retryable": False,
    }
    result = evaluator_node(state)
    assert result["passed"] is False
    assert result["evaluation"]["compile_ok"] is False


def test_evaluator_fail_critic():
    state = _make_state()
    state["critic_result"] = {
        "passed": False,
        "issues": [{"severity": "high", "type": "completeness", "description": "missing", "fix": "add"}],
    }
    result = evaluator_node(state)
    assert result["passed"] is False
    assert result["evaluation"]["critic"]["high"] == 1


def test_evaluator_token_totals():
    state = _make_state()
    state["generation_history"] = [
        {"attempt": 0, "tier": 0, "model": "gpt-4.1-mini",
         "tokens_in": 500, "tokens_out": 200,
         "errors_in": [], "errors_out": [], "stalled": False},
        {"attempt": 1, "tier": 1, "model": "gpt-4.1-mini",
         "tokens_in": 800, "tokens_out": 300,
         "errors_in": ["e1"], "errors_out": [], "stalled": False},
    ]
    result = evaluator_node(state)
    assert result["evaluation"]["tokens"]["total_in"] == 1300
    assert result["evaluation"]["tokens"]["total_out"] == 500
    assert result["evaluation"]["tokens"]["total"] == 1800


def test_evaluator_cost_tracking():
    state = _make_state()
    result = evaluator_node(state)
    assert result["evaluation"]["cost"]["total_usd"] > 0
    assert "gpt-4.1-mini" in result["evaluation"]["cost"]["models_used"]


def test_evaluator_steps_detail():
    state = _make_state()
    result = evaluator_node(state)
    steps = result["evaluation"]["steps"]
    assert len(steps) == 1
    assert steps[0]["model"] == "gpt-4.1-mini"
    assert steps[0]["tokens_in"] == 500
    assert steps[0]["cost"] > 0


def test_evaluator_retry_info():
    state = _make_state(retry_count=2, retry_tier=2, stall_detected=True)
    result = evaluator_node(state)
    assert result["evaluation"]["retry_count"] == 2
    assert result["evaluation"]["max_tier"] == 2
    assert result["evaluation"]["stall_detected"] is True


def test_evaluator_writes_manifest():
    state = _make_state(run_id="manifest-test-001")
    result = evaluator_node(state)

    manifest_path = Path(__file__).resolve().parent.parent.parent / "output" / "runs" / "manifest-test-001" / "run-manifest.json"
    assert manifest_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["run_id"] == "manifest-test-001"
    assert data["passed"] is True
    assert "tokens" in data
    assert "cost" in data
    assert "steps" in data

    # Cleanup
    manifest_path.unlink()
    manifest_path.parent.rmdir()


def test_evaluator_empty_history():
    state = _make_state()
    state["generation_history"] = []
    result = evaluator_node(state)
    assert result["evaluation"]["tokens"]["total"] == 0
    assert result["evaluation"]["cost"]["total_usd"] == 0
    assert result["evaluation"]["steps"] == []


def test_evaluator_provenance_stats():
    state = _make_state()
    state["slide_plans"] = [
        {
            "slide_index": 0,
            "data_provenance": {"title": "user", "chart_data": "sample", "subtitle": "sample"},
        },
        {
            "slide_index": 1,
            "data_provenance": {"title": "user", "kpi_labels": "user"},
        },
    ]
    result = evaluator_node(state)
    prov = result["evaluation"]["data_provenance"]
    assert prov["user"] == 3
    assert prov["sample"] == 2


def test_evaluator_provenance_no_plans():
    state = _make_state()
    state["slide_plans"] = []
    result = evaluator_node(state)
    prov = result["evaluation"]["data_provenance"]
    assert prov["user"] == 0
    assert prov["sample"] == 0
