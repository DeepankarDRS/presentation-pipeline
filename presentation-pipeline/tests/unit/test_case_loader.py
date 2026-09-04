"""Tests for the YAML test case loader."""

import pytest

from src.utils.case_loader import load_case, load_all_cases, case_to_state


def test_load_case_text_only():
    case = load_case("text-only")
    assert case["name"] == "text-only"
    assert "request" in case
    assert "components" in case


def test_load_case_kpi_row():
    case = load_case("kpi-row")
    assert case["name"] == "kpi-row"
    assert "kpi_row" in case["components"]
    assert "supplied_content" in case


def test_load_case_maximal_density():
    case = load_case("maximal-density")
    assert case["name"] == "maximal-density"
    assert len(case["components"]) >= 4


def test_load_case_not_found():
    with pytest.raises(FileNotFoundError):
        load_case("nonexistent-case-xyz")


def test_load_all_cases():
    cases = load_all_cases()
    assert len(cases) >= 17
    names = [c["name"] for c in cases]
    assert "text-only" in names
    assert "kpi-row" in names
    assert "maximal-density" in names


def test_case_to_state_basic():
    case = load_case("text-only")
    state = case_to_state(case)
    assert state["run_id"] == "case-text-only"
    assert state["raw_request"] != ""
    assert state["test_case"] == case


def test_case_to_state_with_supplied_content():
    case = load_case("kpi-row")
    state = case_to_state(case)
    assert state["supplied_content"] is not None
    assert "title" in state["supplied_content"]


def test_case_to_state_custom_run_id():
    case = load_case("text-only")
    state = case_to_state(case, run_id="custom-123")
    assert state["run_id"] == "custom-123"


def test_case_to_state_empty_supplied():
    case = load_case("text-only")
    state = case_to_state(case)
    assert state["supplied_content"] is None


def test_case_to_state_with_theme():
    case = load_case("kpi-row")
    state = case_to_state(case)
    assert state["theme_name"] == "corporate-slate"
