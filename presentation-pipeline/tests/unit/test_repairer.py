"""Tests for the repairer agent with mocked LLM responses."""

from unittest.mock import MagicMock, patch

from src.agents.repairer import (
    repairer_node, _collect_problems, _select_template, build_patch_prompts,
    _get_pre_issues, _get_compile_diags, _choose_strategy, PATCH, REGENERATE,
)
from src.compiler.repair_guidance import (
    build_error_guidance, error_signatures, is_stalled, needs_regeneration,
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


# ── Strategy choice ──────────────────────────────────────────────────────

def _choose(**kw):
    base = dict(attempt=2, prev_strategy=PATCH, prev_noop=False, prev_truncated=False,
                regen_error=False, stalled=False, compile_ok=False)
    base.update(kw)
    return _choose_strategy(**base)


def test_choose_strategy_attempt1_always_patch():
    assert _choose(attempt=1, regen_error=True, stalled=True) == PATCH


def test_choose_strategy_patch_after_regenerate():
    assert _choose(prev_strategy=REGENERATE, attempt=3) == PATCH


def test_choose_strategy_noop_or_truncated_forces_regenerate():
    assert _choose(prev_noop=True) == REGENERATE
    assert _choose(prev_truncated=True) == REGENERATE


def test_choose_strategy_attempt2_regenerates_only_when_broken():
    assert _choose(attempt=2, compile_ok=False) == REGENERATE     # still won't compile → rebuild
    assert _choose(attempt=2, compile_ok=True) == PATCH           # compiles, critic-only → stay PATCH
    assert _choose(attempt=3, compile_ok=True) == PATCH


def test_choose_strategy_structural_or_stall_regenerates():
    assert _choose(regen_error=True, compile_ok=True) == REGENERATE
    assert _choose(stalled=True, compile_ok=True) == REGENERATE


# ── Regenerate classification ─────────────────────────────────────────────

def test_needs_regeneration_structural():
    assert needs_regeneration([], [{"type": "INVALID_CHILD", "message": "Unknown child element <Td> inside <Table>"}]) is True
    assert needs_regeneration([], [{"type": "PARSE_ERROR", "message": "<Shape>: Unexpected child elements. <Shape> does not accept child elements"}]) is True


def test_needs_regeneration_local_errors_false():
    assert needs_regeneration([], [{"type": "UNKNOWN_TAG", "message": "Unknown tag: <div>"}]) is False
    assert needs_regeneration([], [{"type": "UNKNOWN_ATTRIBUTE", "message": '<VStack>: Unknown attribute "flex"'}]) is False
    assert needs_regeneration([], []) is False


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


# ── Shared tier-1 patch prompts ──────────────────────────────────────────

def test_build_patch_prompts():
    system, user = build_patch_prompts(
        failing_xml='<Slide><div>x</div></Slide>',
        problems=["UNKNOWN_TAG: div"],
        pre_issues=[{"code": "HTML_TAG", "message": "Found HTML tag <div>.", "auto_fixed": False}],
        compile_diags=[{"type": "UNKNOWN_TAG", "message": "Unknown tag: <div>"}],
        objective="Fix the layout",
        forbidden_tags=["div", "p"],
        theme_element='<Theme surface="F7F9FC" />',
    )
    assert "PATCH" in user
    assert "Fix the layout" in user
    assert "UNKNOWN_TAG: div" in user
    assert "div, p" in system  # forbidden tags
    assert "F7F9FC" in system  # theme element
    assert "TARGETED FIX GUIDANCE" in user  # build_error_guidance output injected


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

    # Prior attempt failed with the exact same errors _make_state() carries now
    # (a compile diag + two normalize issues). The stored canonical signatures
    # must round-trip so is_stalled() fires — the compile diag is the case that
    # the old display-string reconstruction got wrong.
    state = _make_state(retry_tier=1, retry_count=1)
    prior_sigs = sorted(error_signatures(
        _get_pre_issues(state), _get_compile_diags(state)
    ))
    assert "COMPILE:UNKNOWN_TAG:Unknown tag: <div>" in prior_sigs  # guard the fixture
    state["generation_history"] = [{
        "attempt": 1,
        "tier": 1,
        "errors_in": ["HTML_TAG: Found HTML tag <div>."],
        "errors_out": [],
        "error_sigs": prior_sigs,
        "stalled": False,
        "tokens_in": 500,
        "tokens_out": 200,
        "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE
    assert result["stall_detected"] is True


@patch("src.agents.repairer.get_llm")
def test_repairer_stall_detected_from_compile_diags(mock_get_llm):
    """Regression: a recurring compiler diagnostic must be recognised as a stall.

    The old code rebuilt prev_sigs from display strings, turning a stored
    "COMPILE:UNKNOWN_TAG:..." into "UNKNOWN_TAG:div", which never matched the
    structured curr_sigs — so is_stalled() stayed False forever on compile-error
    loops and REGENERATE was unreachable.
    """
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>x</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 800, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_tier=1, retry_count=1)
    state["normalize_result"]["issues"] = []  # only the compile diag remains
    prior_sigs = sorted(error_signatures(
        _get_pre_issues(state), _get_compile_diags(state)
    ))
    assert prior_sigs == ["COMPILE:UNKNOWN_TAG:Unknown tag: <div>"]
    state["generation_history"] = [{
        "attempt": 1, "tier": 1, "errors_in": ["UNKNOWN_TAG: Unknown tag: <div>"],
        "errors_out": [], "error_sigs": prior_sigs, "stalled": False,
        "tokens_in": 500, "tokens_out": 200, "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["stall_detected"] is True
    assert result["retry_tier"] == REGENERATE


@patch("src.agents.repairer.get_llm")
def test_repairer_no_stall_when_errors_change(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>x</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 800, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_tier=1, retry_count=1)
    state["generation_history"] = [{
        "attempt": 1, "tier": 1, "errors_in": ["something else"],
        "errors_out": [], "error_sigs": ["ZERO_DIM", "UNKNOWN_ATTR:Chart:flex"],
        "stalled": False, "tokens_in": 500, "tokens_out": 200, "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["stall_detected"] is False  # different errors → not a stall
    # attempt 2 still doesn't compile → REGENERATE by the budget-2 gate, not by stall
    assert result["retry_tier"] == REGENERATE


def _mock_llm(mock_get_llm, content='<Theme />\n<Slide><VStack><Text>x</Text></VStack></Slide>'):
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 800, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm
    return mock_llm


@patch("src.agents.repairer.get_llm")
def test_repairer_flags_noop_patch(mock_get_llm):
    state = _make_state(retry_tier=0, retry_count=0)
    identical = state["normalize_result"]["cleaned_xml"]
    _mock_llm(mock_get_llm, content=identical)

    result = repairer_node(state)

    assert result["generation_history"][0]["noop"] is True


@patch("src.agents.repairer.get_llm")
def test_repairer_regenerates_after_noop(mock_get_llm):
    _mock_llm(mock_get_llm)
    state = _make_state(retry_tier=PATCH, retry_count=1)  # attempt 2
    state["generation_history"] = [{
        "attempt": 1, "tier": PATCH, "errors_in": ["x"], "errors_out": [],
        "error_sigs": ["HTML_TAG:div"], "stalled": False, "noop": True,
        "tokens_in": 1, "tokens_out": 1, "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE


@patch("src.agents.repairer.get_llm")
def test_repairer_flags_truncation(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>x</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 4000},
        "model_name": "gpt-4.1-mini",
        "finish_reason": "length",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    result = repairer_node(_make_state(retry_count=1))

    assert result["generation_history"][0]["truncated"] is True


@patch("src.agents.repairer.get_llm")
def test_repairer_regenerate_uses_skeleton(mock_get_llm):
    mock_llm = _mock_llm(mock_get_llm)

    # attempt 2 still not compiling → REGENERATE; title + kpi_row → kpi-slide skeleton
    state = _make_state(retry_tier=PATCH, retry_count=1)
    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE
    user_msg = mock_llm.invoke.call_args[0][0][1]["content"]
    assert "REGENERATE" in user_msg
    assert "VERIFIED SKELETON" in user_msg


@patch("src.agents.repairer.get_llm")
def test_repairer_regenerate_without_skeleton(mock_get_llm):
    mock_llm = _mock_llm(mock_get_llm)

    state = _make_state(retry_tier=PATCH, retry_count=1)  # attempt 2 → REGENERATE
    state["slide_plans"][0]["components"] = [{"kind": "timeline", "count": 1}]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE
    user_msg = mock_llm.invoke.call_args[0][0][1]["content"]
    assert "REGENERATE" in user_msg
    assert "VERIFIED SKELETON" not in user_msg  # no template for timeline
    assert "SIMPLER layout" in user_msg


@patch("src.agents.repairer.get_llm")
def test_repairer_regenerate_on_structural_error(mock_get_llm):
    mock_llm = _mock_llm(mock_get_llm)

    state = _make_state(retry_tier=PATCH, retry_count=1)  # attempt 2
    state["normalize_result"]["issues"] = []
    state["compile_result"]["diagnostics"] = [{
        "type": "INVALID_CHILD",
        "message": "Unknown child element <Td> inside <Table>. Expected: <Col>, <Tr>",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE  # structural → skip straight to rebuild


@patch("src.agents.repairer.get_llm")
def test_repairer_patch_cleanup_after_regenerate(mock_get_llm):
    mock_llm = _mock_llm(mock_get_llm)

    state = _make_state(retry_tier=REGENERATE, retry_count=2)  # attempt 3
    state["generation_history"] = [{
        "attempt": 2, "tier": REGENERATE, "errors_in": ["x"], "errors_out": [],
        "error_sigs": ["HTML_TAG:section"], "stalled": False,
        "tokens_in": 1, "tokens_out": 1, "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] == PATCH  # one cleanup pass on the regenerated XML
    user_msg = mock_llm.invoke.call_args[0][0][1]["content"]
    assert "PATCH" in user_msg


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
    assert isinstance(record["error_sigs"], list) and record["error_sigs"]
