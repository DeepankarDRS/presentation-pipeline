"""Tests for the pre-generation questionnaire node."""

from unittest.mock import patch

from src.agents.questionnaire import questionnaire_node
from src.state import initial_state


def test_questionnaire_skips_non_interactive():
    state = initial_state(run_id="q1", raw_request="test", interactive=False)
    result = questionnaire_node(state)
    assert result == {}


def test_questionnaire_skips_when_preloaded():
    state = initial_state(
        run_id="q2", raw_request="test", interactive=True,
        audience_context={"audience": "Board", "data_density": "Deep-dive"},
    )
    result = questionnaire_node(state)
    assert result == {}


@patch("builtins.input", side_effect=["1", "2", "1", "1", "1"])
def test_questionnaire_collects_answers(mock_input):
    state = initial_state(run_id="q3", raw_request="Quarterly report", interactive=True)
    result = questionnaire_node(state)

    ctx = result["audience_context"]
    assert ctx["audience"] == "Board"
    assert ctx["data_density"] == "Balanced"
    assert ctx["theme"] == "corporate-slate"
    assert ctx["slide_count"] == "Single slide"
    assert ctx["focus"] == "Overview"
    assert result["theme_name"] == "corporate-slate"
    assert result["deck_min_threshold"] == 0


@patch("builtins.input", side_effect=["", "", "", "", ""])
def test_questionnaire_default_on_empty_input(mock_input):
    state = initial_state(run_id="q4", raw_request="A slide", interactive=True)
    result = questionnaire_node(state)

    ctx = result["audience_context"]
    assert ctx["audience"] == "General"
    assert ctx["data_density"] == "Balanced"
    assert ctx["theme"] == "corporate-slate"
    assert ctx["slide_count"] == "Single slide"
    assert ctx["focus"] == "Overview"


@patch("builtins.input", side_effect=["4", "3", "1", "2", "3"])
def test_questionnaire_non_default_choices(mock_input):
    state = initial_state(run_id="q5", raw_request="Sales deck", interactive=True)
    result = questionnaire_node(state)

    ctx = result["audience_context"]
    assert ctx["audience"] == "External"
    assert ctx["data_density"] == "Deep-dive"
    assert ctx["slide_count"] == "3-5 slides"
    assert ctx["focus"] == "Comparison"
    assert result["deck_min_threshold"] == 3
