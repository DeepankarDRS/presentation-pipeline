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
from src.agents.planner_schema import PlannerComponent, PlannerOutput, PlannerSlide
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


def _make_planner_llm(case: dict):
    """Mock planner LLM that returns a plan matching the case components."""
    components = []
    for comp_name in case.get("components", ["title"]):
        comp_name = comp_name.replace("-", "_")
        if comp_name not in (
            "title", "narrative", "caption", "kpi_row", "bullet_list",
            "chart", "table", "timeline", "flow", "layer",
            "tree", "matrix", "process_arrow", "pyramid",
        ):
            comp_name = "title"
        components.append(PlannerComponent(kind=comp_name, count=1))

    output = PlannerOutput(slides=[
        PlannerSlide(
            components=components,
            density="normal",
            font_tier="standard",
            layout_hint="Standard layout",
        ),
    ])
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = output
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
@patch("src.agents.planner.get_llm")
def test_pipeline_runs_for_case(
    mock_planner_llm,
    mock_gen_llm,
    mock_compile,
    mock_validate,
    mock_critic_llm,
    case,
):
    """Each test case loads, runs through the full graph, and produces a valid evaluation."""
    mock_planner_llm.return_value = _make_planner_llm(case)
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


@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
@patch("src.agents.planner.get_llm")
def test_pipeline_with_planner_enabled(
    mock_planner_llm,
    mock_gen_llm,
    mock_compile,
    mock_validate,
    mock_critic_llm,
):
    """Pipeline runs through planner for free-form prompts (no test_case components)."""
    case = next((c for c in _CASES if c.get("name") == "maximal-density"), _CASES[0])

    mock_planner_llm.return_value = _make_planner_llm(case)
    mock_gen_llm.return_value = _make_gen_llm()
    mock_validate.return_value = {
        "ok": True, "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/planner-test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_critic_llm.return_value = _make_critic_llm()

    state = initial_state(
        run_id="planner-e2e",
        raw_request="Create a dense KPI dashboard with charts and tables",
    )
    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert len(result["slide_plans"]) > 0


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
