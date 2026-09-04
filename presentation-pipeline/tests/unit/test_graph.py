"""Tests for the LangGraph pipeline with stub agents."""

from unittest.mock import MagicMock, patch

from src.agents.critic_schema import CriticOutput
from src.agents.planner_schema import PlannerComponent, PlannerOutput, PlannerSlide
from src.graph import build_graph, compile_graph, route_after_start, route_after_validator, route_after_critic, route_after_repairer
from src.state import initial_state


def _mock_critic_llm():
    """Return a mock LLM that passes through with_structured_output for the critic."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = CriticOutput(issues=[])
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


def test_graph_builds():
    graph = build_graph()
    assert graph is not None


def test_graph_compiles():
    app = compile_graph()
    assert app is not None


def test_route_after_start_skips_planner():
    state = initial_state(run_id="r1", raw_request="test", deck_min_threshold=0)
    assert route_after_start(state) == "context_builder"


def test_route_after_start_uses_planner():
    state = initial_state(run_id="r2", raw_request="test", deck_min_threshold=3)
    assert route_after_start(state) == "planner"


def test_route_after_validator_ok_to_critic():
    state = initial_state(run_id="r3", raw_request="test")
    state["compile_result"] = {"ok": True, "retryable": False, "diagnostics": [], "warnings": []}
    assert route_after_validator(state) == "critic"


def test_route_after_validator_ok_critic_off():
    state = initial_state(run_id="r4", raw_request="test", critic_mode="off")
    state["compile_result"] = {"ok": True, "retryable": False, "diagnostics": [], "warnings": []}
    assert route_after_validator(state) == "evaluator"


def test_route_after_validator_fail_retryable():
    state = initial_state(run_id="r5", raw_request="test")
    state["compile_result"] = {"ok": False, "retryable": True, "diagnostics": [{"type": "UNKNOWN_TAG", "message": "err"}], "warnings": []}
    state["retry_count"] = 0
    assert route_after_validator(state) == "repairer"


def test_route_after_validator_fail_budget_exhausted():
    state = initial_state(run_id="r6", raw_request="test", retry_budget=3)
    state["compile_result"] = {"ok": False, "retryable": True, "diagnostics": [{"type": "UNKNOWN_TAG", "message": "err"}], "warnings": []}
    state["retry_count"] = 3
    assert route_after_validator(state) == "evaluator"


def test_route_after_critic_pass():
    state = initial_state(run_id="r7", raw_request="test")
    state["critic_result"] = {"passed": True, "issues": []}
    assert route_after_critic(state) == "evaluator"


def test_route_after_critic_fail():
    state = initial_state(run_id="r8", raw_request="test")
    state["critic_result"] = {"passed": False, "issues": [{"severity": "high"}]}
    state["retry_count"] = 0
    assert route_after_critic(state) == "repairer"


@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_full_graph_runs_with_mocked_llm(mock_gen_llm, mock_compile, mock_validate, mock_critic_llm):
    """End-to-end: the graph runs to completion with mocked LLM + compiler."""
    mock_critic_llm.return_value = _mock_critic_llm()
    mock_response = MagicMock()
    mock_response.content = '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n<Slide><VStack w="1280" h="720" padding="48" backgroundColor="$surface"><Text fontSize="32" bold="true" color="$textMain">Title</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 500, "completion_tokens": 200},
        "model_name": "gpt-4.1-mini",
    }
    llm = MagicMock()
    llm.invoke.return_value = mock_response
    mock_gen_llm.return_value = llm

    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(
        run_id="e2e-001",
        raw_request="Create a simple title slide",
        deck_min_threshold=0,
        critic_mode="auto",
    )

    app = compile_graph()
    result = app.invoke(state)

    assert result["run_id"] == "e2e-001"
    assert result["passed"] is True
    assert result["current_xml"] != ""
    assert len(result["generation_history"]) >= 1
    assert result["evaluation"] is not None
    assert result["evaluation"]["passed"] is True
    assert result["retry_count"] == 0


@patch("src.agents.critic.get_llm")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
@patch("src.agents.planner.get_llm")
def test_full_graph_with_planner(mock_planner_llm, mock_gen_llm, mock_compile, mock_validate, mock_critic_llm):
    """End-to-end: graph runs through planner (mocked LLM) when threshold > 0."""
    mock_critic_llm.return_value = _mock_critic_llm()
    output = PlannerOutput(slides=[
        PlannerSlide(
            components=[
                PlannerComponent(kind="title", count=1, content_summary="Dashboard"),
                PlannerComponent(kind="kpi_row", count=4, content_summary="Key metrics"),
            ],
            density="dense",
            font_tier="compact",
            layout_hint="Title at top, KPI tiles in row below",
        ),
    ])
    mock_planner_llm.return_value = MagicMock()
    mock_planner_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    mock_gen_response = MagicMock()
    mock_gen_response.content = '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n<Slide><VStack w="1280" h="720" padding="48"><Text fontSize="32" bold="true" color="$textMain">Dashboard</Text></VStack></Slide>'
    mock_gen_response.response_metadata = {
        "token_usage": {"prompt_tokens": 600, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    gen_llm = MagicMock()
    gen_llm.invoke.return_value = mock_gen_response
    mock_gen_llm.return_value = gen_llm

    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/dashboard.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(
        run_id="e2e-002",
        raw_request="Create a dense KPI dashboard",
        deck_min_threshold=3,
    )

    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert len(result["slide_plans"]) > 0
    assert result["slide_plans"][0]["density"] == "dense"


def test_route_after_repairer_goes_to_validator():
    state = initial_state(run_id="r9", raw_request="test")
    assert route_after_repairer(state) == "validator"
