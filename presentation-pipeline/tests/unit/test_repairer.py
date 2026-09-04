"""Tests for the repairer agent with mocked LLM responses."""

from unittest.mock import MagicMock, patch

from src.agents.repairer import repairer_node, _collect_problems, _select_template
from src.compiler.repair_guidance import (
    build_error_guidance, error_signatures, is_stalled,
)
from src.state import initial_state


def _make_state(**overrides):
    state = initial_state(
        run_id="rep-test",
        raw_request="Create a KPI dashboard",
        deck_min_threshold=0,
    )
    state["slide_plans"] = [{
        "slide_index": 0,
        "components": [
            {"kind": "title", "count": 1, "content_summary": "Dashboard"},
            {"kind": "kpi_row", "count": 4, "content_summary": "Key metrics"},
        ],
        "density": "dense",
        "font_tier": "compact",
        "layout_hint": "Title at top, KPI tiles below",
    }]
    state["contract"] = {
        "allowed_nodes": ["Slide", "Theme", "VStack", "HStack", "Text", "Shape", "Span"],
        "allowed_attributes": {"VStack": ["gap"], "Text": ["fontSize", "color", "bold"]},
        "forbidden_tags": ["div", "p", "span", "br"],
        "forbidden_attributes": ["style", "class"],
        "theme_element": '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />',
        "density_tier": "dense",
        "layout_pattern": "",
        "example": "",
        "notes": [],
    }
    state["theme_element"] = state["contract"]["theme_element"]
    state["current_xml"] = '<Theme />\n<Slide><div><p>Bad HTML</p></div></Slide>'
    state["normalize_result"] = {
        "cleaned_xml": state["current_xml"],
        "issues": [
            {"code": "HTML_TAG", "message": "Found HTML tag <div>.", "auto_fixed": False},
            {"code": "HTML_TAG", "message": "Found HTML tag <p>.", "auto_fixed": False},
        ],
        "auto_fixed": 0,
        "blocking": True,
    }
    state["compile_result"] = {
        "ok": False,
        "pptx_path": None,
        "diagnostics": [
            {"type": "UNKNOWN_TAG", "message": "Unknown tag: <div>"},
        ],
        "warnings": [],
        "retryable": True,
    }
    state.update(overrides)
    return state


# ── Repair guidance tests ─────────────────────────────────────────────────

def test_build_error_guidance_html_tags():
    pre = [{"code": "HTML_TAG", "message": "Found HTML tag <div>.", "auto_fixed": False}]
    diags = []
    guidance = build_error_guidance(pre, diags)
    assert "TAG FIX" in guidance
    assert "VStack" in guidance


def test_build_error_guidance_unknown_attr():
    pre = [{"code": "UNKNOWN_ATTR", "message": '<Text>: attribute "uppercase" is not allowed.', "auto_fixed": False}]
    diags = []
    guidance = build_error_guidance(pre, diags)
    assert "ATTR FIX" in guidance
    assert "uppercase" in guidance


def test_build_error_guidance_compile_diags():
    pre = []
    diags = [{"type": "UNKNOWN_ATTRIBUTE", "message": 'Unknown attribute "flex" on <VStack>'}]
    guidance = build_error_guidance(pre, diags)
    assert "COMPILER ATTR FIX" in guidance


def test_build_error_guidance_shape_children():
    pre = []
    diags = [{"type": "PARSE_ERROR", "message": "<Shape>: Unexpected child elements. <Shape> does not accept child elements"}]
    guidance = build_error_guidance(pre, diags)
    assert "STRUCTURE FIX" in guidance
    assert "LEAF" in guidance or "leaf" in guidance
    assert "text" in guidance.lower()


def test_build_error_guidance_empty():
    assert build_error_guidance([], []) == ""


def test_build_error_guidance_skips_auto_fixed():
    pre = [{"code": "HASH_COLOR", "message": "Stripped #", "auto_fixed": True}]
    assert build_error_guidance(pre, []) == ""


# ── Stall detection tests ─────────────────────────────────────────────────

def test_error_signatures_extracts():
    pre = [
        {"code": "HTML_TAG", "message": "Found HTML tag <div>.", "auto_fixed": False},
        {"code": "ZERO_DIM", "message": "w=0", "auto_fixed": False},
    ]
    diags = [{"type": "UNKNOWN_TAG", "message": "Unknown tag: <span>"}]
    sigs = error_signatures(pre, diags)
    assert "HTML_TAG:div" in sigs
    assert "ZERO_DIM" in sigs
    assert any("COMPILE:" in s for s in sigs)


def test_is_stalled_true():
    prev = {"HTML_TAG:div", "HTML_TAG:p", "ZERO_DIM"}
    curr = {"HTML_TAG:div", "HTML_TAG:p", "ZERO_DIM"}
    assert is_stalled(prev, curr) is True


def test_is_stalled_false():
    prev = {"HTML_TAG:div", "HTML_TAG:p"}
    curr = {"UNKNOWN_ATTR:Text:bold", "ZERO_DIM"}
    assert is_stalled(prev, curr) is False


def test_is_stalled_empty():
    assert is_stalled(set(), {"A"}) is False
    assert is_stalled({"A"}, set()) is False


# ── Problem collection ────────────────────────────────────────────────────

def test_collect_problems():
    state = _make_state()
    problems = _collect_problems(state)
    assert any("div" in p for p in problems)
    assert len(problems) >= 2


def test_collect_problems_includes_critic():
    state = _make_state()
    state["critic_result"] = {
        "passed": False,
        "issues": [{"severity": "high", "message": "Missing KPI tiles"}],
    }
    problems = _collect_problems(state)
    assert any("CRITIC" in p for p in problems)


# ── Template selection ────────────────────────────────────────────────────

def test_select_template_kpi():
    state = _make_state()
    xml = _select_template(state)
    assert xml  # non-empty
    assert "<Slide>" in xml or "<Theme" in xml


def test_select_template_chart():
    state = _make_state()
    state["slide_plans"][0]["components"] = [
        {"kind": "chart", "count": 1, "chart_type": "bar"},
    ]
    xml = _select_template(state)
    assert xml
    assert "Chart" in xml or "Slide" in xml


def test_select_template_default():
    state = _make_state()
    state["slide_plans"][0]["components"] = [
        {"kind": "title", "count": 1},
    ]
    xml = _select_template(state)
    assert xml


# ── Repairer node (mocked LLM) ───────────────────────────────────────────

@patch("src.agents.repairer.get_llm")
def test_repairer_tier1_patch(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>Fixed</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 1000, "completion_tokens": 400},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_tier=0, retry_count=0)
    result = repairer_node(state)

    assert result["retry_count"] == 1
    assert result["retry_tier"] >= 1
    assert "<Slide>" in result["current_xml"]
    assert len(result["generation_history"]) == 1

    call_args = mock_llm.invoke.call_args[0][0]
    user_msg = call_args[1]["content"]
    assert "REPAIR" in user_msg
    assert "PATCH" in user_msg


@patch("src.agents.repairer.get_llm")
def test_repairer_escalates_on_stall(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>Simplified</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 800, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_tier=1, retry_count=1)
    state["compile_result"] = {
        "ok": False, "pptx_path": None,
        "diagnostics": [],
        "warnings": [], "retryable": True,
    }
    state["generation_history"] = [{
        "attempt": 1,
        "tier": 1,
        "errors_in": [
            "HTML_TAG: Found HTML tag <div>.",
            "HTML_TAG: Found HTML tag <p>.",
        ],
        "errors_out": [],
        "stalled": False,
        "tokens_in": 500,
        "tokens_out": 200,
        "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] >= 2
    assert result["stall_detected"] is True


@patch("src.agents.repairer.get_llm")
def test_repairer_tier3_template(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>Template fill</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 1200, "completion_tokens": 500},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_tier=3, retry_count=2)
    result = repairer_node(state)

    assert result["retry_tier"] == 3
    call_args = mock_llm.invoke.call_args[0][0]
    user_msg = call_args[1]["content"]
    assert "TEMPLATE" in user_msg
    assert "VERIFIED TEMPLATE" in user_msg


@patch("src.agents.repairer.get_llm")
def test_repairer_records_attempt(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Slide><Text>OK</Text></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 600, "completion_tokens": 250},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_count=1)
    result = repairer_node(state)

    record = result["generation_history"][0]
    assert record["attempt"] == 2
    assert record["tokens_in"] == 600
    assert record["tokens_out"] == 250
    assert len(record["errors_in"]) > 0
