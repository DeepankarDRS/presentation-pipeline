"""Integration tests — run the full pipeline for each YAML test case.

All LLM calls and the compiler are mocked. These tests verify that:
  - Every test case can be loaded and converted to state
  - The pipeline runs to completion for each case
  - The evaluator produces a valid manifest
  - No exceptions are raised during graph execution
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.critic_schema import CriticOutput
from src.agents.planner_schema import PlannerComponent, PlannerSlide
from src.graph import compile_graph
from src.state import initial_state
from src.utils.case_loader import load_all_cases, case_to_state


_CASES = load_all_cases()
_CASE_NAMES = [c.get("name", "unknown") for c in _CASES]

MOCK_XML = (
    '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" '
    'textMuted="55627A" border="E2E8F0" />\n'
    '<Slide><VStack w="1280" h="720" padding="48" gap="24" '
    'backgroundColor="$surface">'
    '<Text fontSize="32" bold="true" color="$textMain">Title</Text>'
    '</VStack></Slide>'
)


def _make_gen_llm():
    """Mock generator LLM that returns valid POM XML."""
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
    """Mock critic LLM that passes."""
    llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = CriticOutput(issues=[])
    llm.with_structured_output.return_value = structured
    return llm


@pytest.mark.parametrize("case", _CASES, ids=_CASE_NAMES)
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_pipeline_runs_for_case(
    mock_gen_llm,
    mock_compile,
    mock_validate,
    mock_critic_llm,
    case,
):
    """Each test case loads, runs through the full graph, and produces a valid evaluation.

    Test cases that supply components bypass the planning pipeline entirely via
    route_after_start → style_resolver. Cases without components are expected to
    provide slide_plans directly in the case fixture (or use the new hierarchical
    planning path, which would require additional mocks not set up here).
    """
    mock_gen_llm.return_value = _make_gen_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": f"/tmp/{case.get('name', 'test')}.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_critic_llm.return_value = _make_critic_llm()

    state = case_to_state(case, deck_min_threshold=0)
    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert result["evaluation"] is not None
    assert result["evaluation"]["passed"] is True
    assert result["evaluation"]["compile_ok"] is True
    assert result["evaluation"]["tokens"]["total_in"] > 0
    assert result["evaluation"]["cost"]["total_usd"] >= 0
    assert len(result["generation_history"]) >= 1
    assert result["current_xml"] == MOCK_XML


@patch("src.agents.plan_reviewer.get_llm")
@patch("src.agents.slide_component_planner.get_llm")
@patch("src.agents.outline_planner.get_llm")
@patch("src.agents.elicitor.get_llm")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_pipeline_with_hierarchical_planner(
    mock_gen_llm,
    mock_compile,
    mock_validate,
    mock_critic_llm,
    mock_elicitor_llm,
    mock_outline_llm,
    mock_slide_planner_llm,
    mock_reviewer_llm,
):
    """Pipeline runs through the full hierarchical planning pipeline."""
    from src.agents.elicitor_schema import ElicitorOutput
    from src.agents.outline_planner_schema import OutlinePlannerOutput, OutlineSlide as OSlide
    from src.agents.plan_reviewer_schema import PlanReviewerOutput

    # Elicitor: prompt is sufficient — no questions needed
    elicitor_output = ElicitorOutput(is_sufficient=True, reasoning="Prompt is specific.", questions=[])
    mock_elicitor_llm.return_value = MagicMock()
    mock_elicitor_llm.return_value.with_structured_output.return_value.invoke.return_value = elicitor_output

    # Outline planner: one content slide
    outline_output = OutlinePlannerOutput(
        deck_title="KPI Dashboard",
        core_hook="Revenue grew 40% but margins are shrinking.",
        slides=[
            OSlide(
                slide_index=0, slide_title="Key Metrics", slide_type="data",
                section="Metrics", narrative_role="Establishes baseline.",
                key_messages=["ARR $12M", "NRR 115%"],
                data_anchors=["ARR: $12M", "NRR: 115%"],
                layout_intent="4 KPI tiles in a row below the title",
                suggested_components=["title", "kpi_row"],
            )
        ],
    )
    mock_outline_llm.return_value = MagicMock()
    mock_outline_llm.return_value.with_structured_output.return_value.invoke.return_value = outline_output

    # Slide component planner: produce a valid PlannerSlide
    slide_output = PlannerSlide(
        slide_type="data",
        components=[
            PlannerComponent(kind="title", count=1, content_summary="Key Metrics"),
            PlannerComponent(kind="kpi_row", count=4, content_summary="ARR, NRR, Margin, CAC"),
        ],
        density="normal", font_tier="standard",
        layout_hint="Title at top, 4 KPI tiles in row below",
        content_data_json='{"title": "Key Metrics", "kpi_labels": ["ARR", "NRR", "Margin", "CAC"]}',
    )
    mock_slide_planner_llm.return_value = MagicMock()
    mock_slide_planner_llm.return_value.with_structured_output.return_value.invoke.return_value = slide_output

    # Plan reviewer: approve the plan
    review_output = PlanReviewerOutput(
        confidence_score=0.9, approved=True, summary="Plan looks good.", issues=[],
    )
    mock_reviewer_llm.return_value = MagicMock()
    mock_reviewer_llm.return_value.with_structured_output.return_value.invoke.return_value = review_output

    mock_gen_llm.return_value = _make_gen_llm()
    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/hierarchical-test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_critic_llm.return_value = _make_critic_llm()

    state = initial_state(
        run_id="hierarchical-e2e",
        raw_request="Create a KPI dashboard slide with ARR and NRR metrics",
    )
    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert len(result["slide_plans"]) > 0
    plan_review = result.get("plan_review") or {}
    assert plan_review.get("approved") is True
    assert plan_review.get("confidence_score", 0) >= 0.9


@patch("src.agents.repairer.get_llm")
@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_pipeline_compile_failure_retries(
    mock_gen_llm,
    mock_compile,
    mock_validate,
    mock_critic_llm,
    mock_repairer_llm,
):
    """Pipeline retries on compile failure and eventually passes."""
    mock_gen_llm.return_value = _make_gen_llm()

    repair_response = MagicMock()
    repair_response.content = MOCK_XML
    repair_response.response_metadata = {
        "token_usage": {"prompt_tokens": 700, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    repair_llm = MagicMock()
    repair_llm.invoke.return_value = repair_response
    mock_repairer_llm.return_value = repair_llm

    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.side_effect = [
        {"ok": False, "pptx_path": None, "diagnostics": [{"type": "UNKNOWN_TAG", "message": "err"}], "warnings": [], "retryable": True},
        {"ok": True, "pptx_path": "/tmp/retry-test.pptx", "diagnostics": [], "warnings": [], "retryable": False},
    ]
    mock_critic_llm.return_value = _make_critic_llm()

    case = _CASES[0]
    state = case_to_state(case, deck_min_threshold=0)
    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert result["retry_count"] >= 1
    assert len(result["generation_history"]) >= 2
