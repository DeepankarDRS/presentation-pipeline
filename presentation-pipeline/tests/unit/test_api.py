"""Tests for the FastAPI + SSE API layer."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.critic_schema import CriticOutput
from src.agents.planner_schema import PlannerComponent, PlannerOutput, PlannerSlide
from src.api import app, _runs, RunRecord

from fastapi.testclient import TestClient

client = TestClient(app)

MOCK_XML = (
    '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n'
    '<Slide><VStack w="1280" h="720" padding="48" gap="24" '
    'backgroundColor="$surface">'
    '<Text fontSize="32" bold="true" color="$textMain">Title</Text>'
    '</VStack></Slide>'
)


def _make_gen_llm():
    mock_response = MagicMock()
    mock_response.content = MOCK_XML
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 500, "completion_tokens": 200},
        "model_name": "gpt-4.1-mini",
    }
    llm = MagicMock()
    llm.invoke.return_value = mock_response
    return llm


def _make_critic_llm():
    llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = CriticOutput(issues=[])
    llm.with_structured_output.return_value = structured
    return llm


def _make_planner_llm():
    output = PlannerOutput(
        core_hook="Test presentation hook.",
        slides=[
            PlannerSlide(
                slide_type="cover",
                components=[
                    PlannerComponent(kind="title", count=1, content_summary="Title"),
                ],
                density="sparse",
                font_tier="display",
                layout_pattern="hero_statement",
                layout_hint="Centered title",
            ),
        ],
    )
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = output
    return llm


def _parse_sse_events(text: str) -> list[dict]:
    events = []
    current: dict = {}
    for line in text.split("\n"):
        if line.startswith("event: "):
            current["event"] = line[7:]
        elif line.startswith("data: "):
            current["data"] = json.loads(line[6:])
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


# ── Health ──────────────────────────────────────────────────────────────────

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "active_runs" in data


# ── Generate SSE stream ────────────────────────────────────────────────────

@patch("src.agents.planner.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_generate_returns_sse_stream(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_planner_llm,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_planner_llm.return_value = _make_planner_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    response = client.post(
        "/generate",
        json={"prompt": "Create a title slide"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _parse_sse_events(response.text)
    event_types = [e["event"] for e in events]
    assert "complete" in event_types
    assert len(events) >= 3


@patch("src.agents.planner.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_generate_events_are_valid_json(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_planner_llm,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_planner_llm.return_value = _make_planner_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    response = client.post(
        "/generate",
        json={"prompt": "Create a title slide"},
    )
    events = _parse_sse_events(response.text)
    for event in events:
        assert "data" in event
        data = event["data"]
        assert "run_id" in data
        assert "event" in data
        assert "timestamp" in data


@patch("src.agents.planner.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_generate_complete_has_passed(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_planner_llm,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_planner_llm.return_value = _make_planner_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    response = client.post(
        "/generate",
        json={"prompt": "Create a title slide"},
    )
    events = _parse_sse_events(response.text)
    complete_events = [e for e in events if e["event"] == "complete"]
    assert len(complete_events) == 1
    assert "passed" in complete_events[0]["data"]["data"]


# ── Run status ──────────────────────────────────────────────────────────────

@patch("src.agents.planner.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_run_status_after_complete(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_planner_llm,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_planner_llm.return_value = _make_planner_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    gen_response = client.post(
        "/generate",
        json={"prompt": "Create a title slide"},
    )
    run_id = gen_response.headers["x-run-id"]

    status_response = client.get(f"/runs/{run_id}/status")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["status"] == "complete"
    assert data["passed"] is True
    assert data["progress_pct"] == 100


def test_run_status_not_found():
    response = client.get("/runs/nonexistent/status")
    assert response.status_code == 404


# ── Download ────────────────────────────────────────────────────────────────

def test_download_before_complete():
    _runs["pending-run"] = RunRecord(run_id="pending-run", status="running")
    response = client.get("/runs/pending-run/download")
    assert response.status_code == 409
    del _runs["pending-run"]


def test_download_after_complete():
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        f.write(b"PK\x03\x04fake pptx content")
        pptx_path = f.name

    _runs["dl-test"] = RunRecord(
        run_id="dl-test", status="complete", pptx_path=pptx_path,
    )
    response = client.get("/runs/dl-test/download")
    assert response.status_code == 200
    assert "presentationml" in response.headers["content-type"]
    del _runs["dl-test"]
    Path(pptx_path).unlink(missing_ok=True)


def test_download_not_found():
    response = client.get("/runs/nonexistent/download")
    assert response.status_code == 404


# ── Error handling ──────────────────────────────────────────────────────────

@patch("src.api._run_pipeline_sync")
def test_generate_error_event(mock_pipeline):
    mock_pipeline.side_effect = RuntimeError("LLM API timeout")

    response = client.post(
        "/generate",
        json={"prompt": "Create a title slide"},
    )
    events = _parse_sse_events(response.text)
    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) >= 1
    assert "timeout" in error_events[0]["data"]["data"]["message"].lower()
