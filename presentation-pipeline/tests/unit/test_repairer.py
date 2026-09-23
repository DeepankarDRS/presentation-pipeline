"""Tests for the repairer agent with mocked LLM responses."""

from unittest.mock import MagicMock, patch

from src.agents.repairer import (
    repairer_node, _collect_problems, build_patch_prompts,
    _get_pre_issues, _get_compile_diags, _choose_strategy,
    _build_repair_context, _plan_to_outline_slide, _cap_xml,
    PATCH, REGENERATE,
)
from src.compiler.repair_guidance import (
    build_error_guidance, cap_diag_msg, error_signatures, is_stalled,
    needs_regeneration, select_repair_knowledge,
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
        "layout_hint": "Title at top, KPI tiles below",
    }]
    state["contract"] = {
        "allowed_nodes": ["Slide", "Theme", "VStack", "HStack", "Text", "Shape", "Span"],
        "allowed_attributes": {"VStack": ["gap"], "Text": ["fontSize", "color", "bold"]},
        "forbidden_tags": ["div", "p", "span", "br"],
        "forbidden_attributes": ["style", "class"],
        "theme_element": '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />',
        "component_count": 2,
        "house_style": "",
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


def test_build_error_guidance_band_height_sum():
    layout_issues = [{"code": "BAND_HEIGHT_SUM", "message": "heights ~= 800 > 720"}]
    guidance = build_error_guidance([], [], layout_issues)
    assert "LAYOUT OVERFLOW" in guidance


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


# ── Repair context helpers ────────────────────────────────────────────────

def test_build_repair_context():
    plan = {
        "components": [
            {"kind": "timeline", "count": 1},
            {"kind": "title", "count": 1},
        ],
    }
    ctx = _build_repair_context(plan, ["UNKNOWN_TAG: div", "INVALID_CHILD: Td"])
    assert "timeline" in ctx["failed_kinds"]
    assert "title" in ctx["failed_kinds"]
    assert len(ctx["errors"]) == 2
    assert "directive" in ctx


def test_plan_to_outline_slide():
    plan = {
        "slide_index": 2,
        "slide_title": "Revenue",
        "components": [
            {"kind": "chart", "content_summary": "Q4 revenue chart"},
            {"kind": "title", "content_summary": "Revenue Overview"},
        ],
    }
    outline = _plan_to_outline_slide(plan)
    assert outline["slide_index"] == 2
    assert outline["slide_title"] == "Revenue"
    assert len(outline["key_messages"]) == 2
    assert "Q4 revenue chart" in outline["key_messages"]


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


def _mock_replan(mock_plan, mock_contract):
    """Set up mocks for the REGENERATE path (plan_single_slide + build_contract)."""
    mock_plan.return_value = (
        {
            "slide_index": 0,
            "slide_title": "KPI Dashboard",
            "slide_type": "data",
            "components": [{"kind": "table", "count": 1, "content_summary": "Metrics"}],
            "layout_hint": "",
            "content_data": {},
        },
        {"tokens_in": 100, "tokens_out": 50, "model": "test"},
    )
    mock_contract.return_value = {
        "allowed_nodes": ["Slide", "VStack", "Text", "Table"],
        "allowed_attributes": {},
        "forbidden_tags": ["div"],
        "forbidden_attributes": [],
        "theme_element": "",
        "component_count": 1,
        "house_style": "",
        "component_recipes": "",
        "notes": [],
        "node_hierarchy": "",
    }


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_escalates_on_stall(mock_get_llm, mock_plan, mock_contract):
    _mock_replan(mock_plan, mock_contract)
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
    prior_sigs = sorted(error_signatures(
        _get_pre_issues(state), _get_compile_diags(state)
    ))
    assert "COMPILE:UNKNOWN_TAG:Unknown tag: <div>" in prior_sigs
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
    assert mock_plan.called  # REGENERATE now calls plan_single_slide


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_stall_detected_from_compile_diags(mock_get_llm, mock_plan, mock_contract):
    """Regression: a recurring compiler diagnostic must be recognised as a stall."""
    _mock_replan(mock_plan, mock_contract)
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
    state["normalize_result"]["issues"] = []
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


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_no_stall_when_errors_change(mock_get_llm, mock_plan, mock_contract):
    _mock_replan(mock_plan, mock_contract)
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

    assert result["stall_detected"] is False
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


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_regenerates_after_noop(mock_get_llm, mock_plan, mock_contract):
    _mock_replan(mock_plan, mock_contract)
    _mock_llm(mock_get_llm)
    state = _make_state(retry_tier=PATCH, retry_count=1)  # attempt 2
    state["generation_history"] = [{
        "attempt": 1, "tier": PATCH, "errors_in": ["x"], "errors_out": [],
        "error_sigs": ["HTML_TAG:div"], "stalled": False, "noop": True,
        "tokens_in": 1, "tokens_out": 1, "model": "gpt-4.1-mini",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE
    assert mock_plan.called


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


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_regenerate_replans_slide(mock_get_llm, mock_plan, mock_contract):
    """REGENERATE now calls plan_single_slide + generator LLM instead of repairer LLM."""
    _mock_replan(mock_plan, mock_contract)
    mock_llm = _mock_llm(mock_get_llm)

    state = _make_state(retry_tier=PATCH, retry_count=1)
    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE
    assert mock_plan.called
    assert mock_contract.called
    # REGENERATE returns updated slide_plans and contract
    assert "slide_plans" in result
    assert "contract" in result


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_regenerate_passes_repair_context(mock_get_llm, mock_plan, mock_contract):
    """REGENERATE passes repair_context to plan_single_slide with failed component kinds."""
    _mock_replan(mock_plan, mock_contract)
    _mock_llm(mock_get_llm)

    state = _make_state(retry_tier=PATCH, retry_count=1)
    state["slide_plans"][0]["components"] = [{"kind": "timeline", "count": 1, "content_summary": "Events"}]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE
    call_kwargs = mock_plan.call_args
    repair_ctx = call_kwargs.kwargs.get("repair_context") or call_kwargs[1].get("repair_context")
    assert repair_ctx is not None
    assert "timeline" in repair_ctx["failed_kinds"]


@patch("src.agents.repairer.build_contract")
@patch("src.agents.repairer.plan_single_slide")
@patch("src.agents.repairer.get_llm")
def test_repairer_regenerate_on_structural_error(mock_get_llm, mock_plan, mock_contract):
    _mock_replan(mock_plan, mock_contract)
    mock_llm = _mock_llm(mock_get_llm)

    state = _make_state(retry_tier=PATCH, retry_count=1)
    state["normalize_result"]["issues"] = []
    state["compile_result"]["diagnostics"] = [{
        "type": "INVALID_CHILD",
        "message": "Unknown child element <Td> inside <Table>. Expected: <Col>, <Tr>",
    }]

    result = repairer_node(state)

    assert result["retry_tier"] == REGENERATE


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


# ── select_repair_knowledge ──────────────────────────────────────────────────

def test_select_repair_knowledge_icon_error():
    pre_issues = [{"code": "UNKNOWN_ATTR",
                   "message": '"bgcolor" not valid on <Icon>',
                   "auto_fixed": False}]
    result = select_repair_knowledge(pre_issues, [])
    assert "Icon" in result["nodes_involved"]
    assert result["knowledge_text"] != ""
    assert "name" in result["knowledge_text"]


def test_select_repair_knowledge_parse_error():
    compile_diags = [{"type": "PARSE_ERROR", "message": "unclosed tag at line 12"}]
    result = select_repair_knowledge([], compile_diags)
    assert result["knowledge_text"] == ""


def test_select_repair_knowledge_chart_error():
    compile_diags = [{"type": "UNKNOWN_ATTRIBUTE",
                      "message": 'attribute "foo" not valid on <Chart>'}]
    result = select_repair_knowledge([], compile_diags)
    assert "Chart" in result["nodes_involved"]
    assert result["example"] != ""


# ── cap_diag_msg ─────────────────────────────────────────────────────────────

def test_cap_diag_msg_strips_expected_enum():
    """The Lucide icon-name INVALID_VALUE message must not pass through raw."""
    long_msg = '<Icon>: Invalid value for attribute "name". Expected: ' + ", ".join(
        f'"{n}"' for n in ["a-arrow-down", "a-arrow-up", "activity"] * 100
    )
    result = cap_diag_msg(long_msg)
    assert len(result) <= 225  # _MAX_MSG_LEN + ellipsis
    assert "repair knowledge" in result


def test_cap_diag_msg_preserves_parse_error_context():
    """Single-value 'expected: <tag>' in parse errors must NOT be stripped."""
    msg = 'unexpected token at line 5; expected: </VStack>'
    result = cap_diag_msg(msg)
    assert "VStack" in result
    assert "repair knowledge" not in result


def test_cap_diag_msg_short_message_unchanged():
    msg = 'w must be > 0'
    assert cap_diag_msg(msg) == msg


def test_collect_problems_caps_large_invalid_value():
    """INVALID_VALUE enum listing must not inflate the problems list."""
    huge_enum = ", ".join(f'"{n}"' for n in ["icon-slug"] * 500)
    state = initial_state(run_id="cap1", raw_request="test")
    state["normalize_result"] = {"issues": [], "cleaned_xml": "<Slide/>"}
    state["compile_result"] = {
        "success": False,
        "diagnostics": [{"type": "INVALID_VALUE",
                          "message": f'<Icon>: Invalid value for "name". Expected: {huge_enum}'}],
    }
    from src.agents.repairer import _collect_problems
    problems = _collect_problems(state)
    assert len(problems) == 1
    assert len(problems[0]) <= 250  # must be capped, not thousands of chars
    assert "Expected" not in problems[0]


# ── _cap_xml ───────────────────────────────────────────────────────────────────

def test_cap_xml_short_unchanged():
    xml = '<Slide><VStack w="1280" h="720"><Text>Hello</Text></VStack></Slide>'
    assert _cap_xml(xml) == xml


def test_cap_xml_truncates_middle():
    head = '<Slide><VStack w="1280" h="720" padding="40" gap="16" alignItems="stretch">\n'
    tail = '</VStack></Slide>'
    middle = '<Text fontSize="14">x</Text>\n' * 1000  # ~30,000 chars
    huge_xml = head + middle + tail
    result = _cap_xml(huge_xml)
    assert len(result) <= 8200  # _MAX_XML_CHARS + marker
    assert result.startswith(head[:50])
    assert result.endswith(tail)
    assert "truncated" in result


def test_cap_xml_applied_in_build_patch_prompts():
    """build_patch_prompts must cap failing_xml before rendering."""
    huge_xml = "<Slide>" + "<Text>x</Text>" * 2000 + "</Slide>"
    _, user_prompt = build_patch_prompts(
        failing_xml=huge_xml,
        problems=["UNKNOWN_TAG: bad"],
        pre_issues=[],
        compile_diags=[],
        objective="Test",
        forbidden_tags=[],
        theme_element="",
    )
    assert len(user_prompt) < len(huge_xml)
    assert "truncated" in user_prompt


def test_invalid_child_guidance_and_signature():
    from src.compiler.repair_guidance import build_error_guidance, error_signatures
    issue = {"code": "INVALID_CHILD", "message": "<HStack> is not allowed inside <Td>. ...",
             "auto_fixed": False, "parent": "Td", "child": "HStack"}
    assert "NESTING FIX" in build_error_guidance([issue], [])
    assert "INVALID_CHILD:Td>HStack" in error_signatures([issue], [])
