"""Tests for the FastAPI + SSE API layer."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.critic_schema import CriticOutput
from src.agents.planner_schema import PlannerComponent, PlannerSlide
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


def _make_elicitor_llm():
    from src.agents.elicitor_schema import ElicitorOutput
    out = ElicitorOutput(is_sufficient=True, reasoning="Prompt is specific.", questions=[])
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = out
    return llm


def _make_outline_llm():
    from src.agents.outline_planner_schema import OutlinePlannerOutput, OutlineSlide
    out = OutlinePlannerOutput(
        deck_title="Test Deck",
        core_hook="Test hook.",
        slides=[
            OutlineSlide(
                slide_index=0, slide_title="Title Slide", slide_type="cover",
                section="", narrative_role="", key_messages=["Hello"],
                data_anchors=[], layout_intent="", suggested_components=["title"],
            )
        ],
    )
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = out
    return llm


def _make_slide_component_llm():
    out = PlannerSlide(
        slide_type="cover",
        components=[PlannerComponent(kind="title", count=1, content_summary="Title")],
        density="sparse", font_tier="display",
        layout_pattern="hero_statement",
        layout_hint="Centered title",
    )
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = out
    return llm


def _make_plan_reviewer_llm():
    from src.agents.plan_reviewer_schema import PlanReviewerOutput
    out = PlanReviewerOutput(confidence_score=0.9, approved=True, summary="OK", issues=[])
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = out
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

def _make_sse_generate_request(prompt: str = "Create a title slide") -> dict:
    """Return a generate request body that bypasses the planning pipeline via test_case."""
    return {
        "prompt": prompt,
        "test_case": {"components": ["title"]},
    }


# Note: generate tests use test_case to bypass the multi-step planning pipeline.
# The planning pipeline (elicitor → outline_planner → slide_component_planner → plan_reviewer)
# is tested separately in test_planner.py.

@patch("src.agents.plan_reviewer.get_llm")
@patch("src.agents.slide_component_planner.get_llm")
@patch("src.agents.outline_planner.get_llm")
@patch("src.agents.elicitor.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_generate_returns_sse_stream(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_elicitor, mock_outline, mock_slide_planner, mock_reviewer,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_elicitor.return_value = _make_elicitor_llm()
    mock_outline.return_value = _make_outline_llm()
    mock_slide_planner.return_value = _make_slide_component_llm()
    mock_reviewer.return_value = _make_plan_reviewer_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    response = client.post("/generate", json={"prompt": "Create a title slide"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _parse_sse_events(response.text)
    event_types = [e["event"] for e in events]
    assert "complete" in event_types
    assert len(events) >= 3


@patch("src.agents.plan_reviewer.get_llm")
@patch("src.agents.slide_component_planner.get_llm")
@patch("src.agents.outline_planner.get_llm")
@patch("src.agents.elicitor.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_generate_events_are_valid_json(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_elicitor, mock_outline, mock_slide_planner, mock_reviewer,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_elicitor.return_value = _make_elicitor_llm()
    mock_outline.return_value = _make_outline_llm()
    mock_slide_planner.return_value = _make_slide_component_llm()
    mock_reviewer.return_value = _make_plan_reviewer_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    response = client.post("/generate", json={"prompt": "Create a title slide"})
    events = _parse_sse_events(response.text)
    for event in events:
        assert "data" in event
        data = event["data"]
        assert "run_id" in data
        assert "event" in data
        assert "timestamp" in data


@patch("src.agents.plan_reviewer.get_llm")
@patch("src.agents.slide_component_planner.get_llm")
@patch("src.agents.outline_planner.get_llm")
@patch("src.agents.elicitor.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_generate_complete_has_passed(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_elicitor, mock_outline, mock_slide_planner, mock_reviewer,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_elicitor.return_value = _make_elicitor_llm()
    mock_outline.return_value = _make_outline_llm()
    mock_slide_planner.return_value = _make_slide_component_llm()
    mock_reviewer.return_value = _make_plan_reviewer_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    from src.graph import compile_graph as real_compile
    mock_compile_graph.return_value = real_compile()

    response = client.post("/generate", json={"prompt": "Create a title slide"})
    events = _parse_sse_events(response.text)
    complete_events = [e for e in events if e["event"] == "complete"]
    assert len(complete_events) == 1
    assert "passed" in complete_events[0]["data"]["data"]


# ── Run status ──────────────────────────────────────────────────────────────

@patch("src.agents.plan_reviewer.get_llm")
@patch("src.agents.slide_component_planner.get_llm")
@patch("src.agents.outline_planner.get_llm")
@patch("src.agents.elicitor.get_llm")
@patch("src.api.compile_graph")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_run_status_after_complete(
    mock_gen_llm, mock_compile, mock_validate, mock_critic_llm, mock_compile_graph,
    mock_elicitor, mock_outline, mock_slide_planner, mock_reviewer,
):
    mock_gen_llm.return_value = _make_gen_llm()
    mock_critic_llm.return_value = _make_critic_llm()
    mock_elicitor.return_value = _make_elicitor_llm()
    mock_outline.return_value = _make_outline_llm()
    mock_slide_planner.return_value = _make_slide_component_llm()
    mock_reviewer.return_value = _make_plan_reviewer_llm()
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


# ── Plan refinement ─────────────────────────────────────────────────────────

_REFINE_BODY = {
    "prompt": "A 3-slide deck",
    "core_hook": "Original hook.",
    "run_id": "refine-run-01",
    "slides": [
        {
            "slide_index": 0,
            "slide_type": "cover",
            "components": [{"kind": "title"}],
        }
    ],
    "feedback": "Add a closing slide with next steps.",
}


@patch("src.agents.outline_planner.get_llm")
def test_refine_plan_returns_revised_plan(mock_outline_llm):
    from src.agents.outline_planner_schema import OutlinePlannerOutput, OutlineSlide
    output = OutlinePlannerOutput(
        deck_title="Revised Deck",
        core_hook="Test presentation hook.",
        slides=[
            OutlineSlide(
                slide_index=0, slide_title="Cover", slide_type="cover",
                section="", narrative_role="", key_messages=["Hello"],
                data_anchors=[], layout_intent="", suggested_components=["title"],
            )
        ],
    )
    mock_outline_llm.return_value = MagicMock()
    mock_outline_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    response = client.post("/plan/refine", json=_REFINE_BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "refine-run-01"
    assert "outline" in data


@patch("src.agents.outline_planner.get_llm")
def test_refine_plan_passes_feedback_to_planner(mock_outline_llm):
    from src.agents.outline_planner_schema import OutlinePlannerOutput, OutlineSlide
    output = OutlinePlannerOutput(
        deck_title="Revised", core_hook="Hook.",
        slides=[
            OutlineSlide(
                slide_index=0, slide_title="Cover", slide_type="cover",
                section="", narrative_role="", key_messages=["Msg"],
                data_anchors=[], layout_intent="", suggested_components=[],
            )
        ],
    )
    mock_outline_llm.return_value = MagicMock()
    mock_outline_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    client.post("/plan/refine", json=_REFINE_BODY)
    # Verify the LLM was called (feedback passed through)
    assert mock_outline_llm.return_value.with_structured_output.return_value.invoke.called


def test_refine_plan_rejects_empty_feedback():
    body = {**_REFINE_BODY, "feedback": "   "}
    response = client.post("/plan/refine", json=body)
    assert response.status_code == 422


def _planner_prompts(mock_planner_llm):
    """Extract (system, user) prompt strings from the mocked planner LLM call."""
    invoke = mock_planner_llm.return_value.with_structured_output.return_value.invoke
    messages = invoke.call_args[0][0]
    return messages[0].content, messages[1].content


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


# ── Edit session: theme_info reconstruction ──────────────────────────────

def _write_run_files(run_id: str, manifest: dict, slides: list[dict]) -> Path:
    run_dir = Path(__file__).resolve().parent.parent.parent / "output" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "slides.json").write_text(json.dumps(slides), encoding="utf-8")
    return run_dir


def test_load_edit_session_populates_theme_info():
    from src.api import _load_edit_session

    run_dir = _write_run_files(
        "edit-theme-test",
        manifest={
            "theme_element": '<Theme accent="2563EB" />',
            "resolved_theme": {"name": "corporate-slate", "mode": "light", "element": '<Theme accent="2563EB" />'},
            "pptx_path": None,
        },
        slides=[{"slide_index": 0, "xml": "<Slide></Slide>", "slide_plan": {"components": []}}],
    )
    try:
        session = _load_edit_session("edit-theme-test")
        assert session is not None
        assert session.theme_info["name"] == "corporate-slate"
        assert not hasattr(session, "contract")
    finally:
        shutil.rmtree(run_dir)


def test_load_edit_session_legacy_manifest_no_resolved_theme():
    """Backward-compat: a manifest written before this change has no resolved_theme key."""
    from src.api import _load_edit_session

    run_dir = _write_run_files(
        "edit-legacy-test",
        manifest={"theme_element": '<Theme accent="2563EB" />', "pptx_path": None},
        slides=[{"slide_index": 0, "xml": "<Slide></Slide>", "slide_plan": {}}],
    )
    try:
        session = _load_edit_session("edit-legacy-test")
        assert session is not None
        assert session.theme_info == {}
        assert session.theme_element == '<Theme accent="2563EB" />'
    finally:
        shutil.rmtree(run_dir)


def test_edit_endpoint_screenshot_failure_does_not_go_stale_looking():
    """A screenshot render failure must not produce a "fresh-looking" URL for stale content.

    Regression test: edit_slide_xml can succeed (xml compiles, is correct in
    the eventual download) while its own screenshot render fails. Before the
    fix, the response's screenshot_url was built from the edit version number
    (which always bumps), making a stale screenshot look like a fresh one to
    the frontend even though the file on disk hadn't changed.
    """
    from src.agents.slide_edit_service import SlideEditResult
    from src.api import _edit_sessions

    run_dir = _write_run_files(
        "edit-screenshot-stale-test",
        manifest={"theme_element": "<Theme />", "resolved_theme": {}, "pptx_path": None},
        slides=[{
            "slide_index": 0, "xml": "<Slide></Slide>", "screenshot_path": None,
            "slide_plan": {"components": [{"kind": "title"}]},
        }],
    )
    try:
        resp = client.post("/runs/edit-screenshot-stale-test/edit-session")
        assert resp.status_code == 200

        results = iter([
            SlideEditResult(ok=True, xml="<Slide>v1</Slide>", compile_ok=True, screenshot_path="/tmp/v1.png"),
            SlideEditResult(ok=True, xml="<Slide>v2</Slide>", compile_ok=True, screenshot_path=None),
        ])

        with patch("src.agents.slide_edit_service.edit_slide_xml", side_effect=lambda **kw: next(results)):
            resp1 = client.post("/runs/edit-screenshot-stale-test/slides/0/edit", json={"feedback": "add a paragraph"})
            resp2 = client.post("/runs/edit-screenshot-stale-test/slides/0/edit", json={"feedback": "add a pyramid"})

        body1, body2 = resp1.json(), resp2.json()

        assert body1["ok"] is True and body1["screenshot_updated"] is True
        assert body2["ok"] is True and body2["screenshot_updated"] is False

        # The edit itself succeeded and the XML moved forward both times...
        assert body1["xml"] == "<Slide>v1</Slide>"
        assert body2["xml"] == "<Slide>v2</Slide>"
        assert body2["version"] > body1["version"]

        # ...but since edit 2's screenshot failed, its URL must be identical to
        # edit 1's (same underlying file), not a new-looking URL for stale content.
        assert body2["screenshot_url"] == body1["screenshot_url"]
    finally:
        _edit_sessions.pop("edit-screenshot-stale-test", None)
        shutil.rmtree(run_dir)
