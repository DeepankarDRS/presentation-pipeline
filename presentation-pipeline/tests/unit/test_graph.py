"""Tests for the LangGraph pipeline with stub agents."""

from unittest.mock import MagicMock, patch

from langgraph.types import Send

from src.agents.planner_schema import PlannerComponent, PlannerSlide
from src.graph import (
    build_graph, compile_graph,
    route_after_start, route_after_validator, route_after_critic,
    route_after_repairer, route_after_slide_router,
    route_after_visual_repairer,
)
from src.agents.critic import compute_critic_score
from src.state import initial_state


def _mock_visual_critic_pass(*args, **kwargs):
    """Return a clean-pass 3-tuple matching run_visual_critic's signature."""
    return (
        [],
        {"tokens_in": 50, "tokens_out": 20, "model": "gpt-4.1"},
        {"strategy": "none", "assessment": "good", "affected_nodes": []},
    )


class _MockSlide:
    def __init__(self, png_path):
        self.png_path = png_path


class _MockBatch:
    def __init__(self, png_path):
        self.ok = True
        self.error = None
        self.slides = [_MockSlide(png_path)]


def _mock_screenshot_batch(png_path="/tmp/slide-0.png"):
    return _MockBatch(png_path)


def test_graph_builds():
    graph = build_graph()
    assert graph is not None


def test_graph_compiles():
    app = compile_graph()
    assert app is not None


def test_route_after_start_skips_planner():
    state = initial_state(run_id="r1", raw_request="test",
                          test_case={"components": ["title", "chart"]})
    assert route_after_start(state) == "style_resolver"


def test_route_after_start_uses_elicitor():
    state = initial_state(run_id="r2", raw_request="test")
    assert route_after_start(state) == "elicitor"


def test_route_after_start_uses_elicitor_no_test_case():
    state = initial_state(run_id="r2b", raw_request="test", test_case={})
    assert route_after_start(state) == "elicitor"


def test_route_after_start_interactive_questionnaire():
    state = initial_state(run_id="r2c", raw_request="test", interactive=True)
    assert route_after_start(state) == "questionnaire"


def test_route_after_start_preloaded_skips_questionnaire():
    state = initial_state(
        run_id="r2d", raw_request="test", interactive=True,
        audience_context={"audience": "Board"},
    )
    assert route_after_start(state) == "elicitor"


def test_route_after_start_preloaded_outline_fans_out():
    """A user-edited outline (e.g. via PUT /plan/{run_id}/outline) skips
    elicitor + outline_planner entirely and fans straight out to per-slide
    planning, so the edited outline is never overwritten by a fresh LLM call.
    """
    state = initial_state(
        run_id="r2e", raw_request="test",
        outline_plan={
            "deck_title": "Test Deck", "core_hook": "hook",
            "slides": [
                {"slide_index": 0, "slide_title": "Cover", "slide_type": "cover",
                 "section": "", "narrative_role": "", "key_messages": [],
                 "visual_emphasis": ""},
            ],
        },
    )
    result = route_after_start(state)
    assert isinstance(result, list)
    assert all(isinstance(s, Send) for s in result)
    assert result[0].node == "slide_component_planner"


def test_route_after_validator_ok_to_critic():
    state = initial_state(run_id="r3", raw_request="test", critic_mode="auto")
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
    assert route_after_validator(state) == "placeholder"


def test_route_after_validator_fail_stall_breaks_loop():
    state = initial_state(run_id="r5s", raw_request="test")
    state["compile_result"] = {"ok": False, "retryable": True, "diagnostics": [{"type": "OVERFLOW", "message": "err"}], "warnings": []}
    state["retry_count"] = 1
    state["stall_detected"] = True
    assert route_after_validator(state) == "placeholder"


def test_route_after_critic_pass():
    state = initial_state(run_id="r7", raw_request="test")
    state["critic_result"] = {"passed": True, "issues": []}
    assert route_after_critic(state) == "evaluator"


def test_route_after_critic_fail():
    state = initial_state(run_id="r8", raw_request="test")
    state["critic_result"] = {"passed": False, "issues": [{"severity": "high"}]}
    assert route_after_critic(state) == "visual_repairer"


def test_route_after_critic_fail_visual_budget_exhausted():
    state = initial_state(run_id="r8s", raw_request="test")
    state["critic_result"] = {"passed": False, "issues": [{"severity": "high"}]}
    state["visual_repair_count"] = 2  # matches default budget=2
    assert route_after_critic(state) == "evaluator"


@patch("src.agents.critic.run_visual_critic", side_effect=_mock_visual_critic_pass)
@patch("src.agents.critic.render_screenshots")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_full_graph_runs_with_mocked_llm(mock_gen_llm, mock_compile, mock_validate, mock_screenshots, mock_vc):
    """End-to-end: the graph runs to completion with mocked LLM + compiler."""
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")
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
        test_case={"components": ["title"]},
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


@patch("src.agents.critic.run_visual_critic", side_effect=_mock_visual_critic_pass)
@patch("src.agents.critic.render_screenshots")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
def test_full_graph_with_preloaded_plans(mock_gen_llm, mock_compile, mock_validate, mock_screenshots, mock_vc):
    """End-to-end: graph runs with pre-provided slide_plans (skips planning phase)."""
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")

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
    state["slide_plans"] = [
        {
            "slide_index": 0, "slide_type": "data",
            "components": [
                {"kind": "title", "count": 1, "content_summary": "Dashboard"},
                {"kind": "kpi_row", "count": 4, "content_summary": "Key metrics"},
            ],
            "layout_hint": "Title at top, KPI tiles in row below",
            "content_data": {}, "data_provenance": {},
        }
    ]

    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert len(result["slide_plans"]) > 0


def test_route_after_repairer_goes_to_validator():
    state = initial_state(run_id="r9", raw_request="test")
    assert route_after_repairer(state) == "validator"


# ── Multi-slide routing tests ──────────────────────────────────────────────

def _multi_slide_state(**overrides):
    """Create a state with 2 slide_plans (multi-slide mode)."""
    state = initial_state(run_id="ms1", raw_request="test")
    state["slide_plans"] = [
        {"slide_index": 0, "components": [{"kind": "title"}]},
        {"slide_index": 1, "components": [{"kind": "chart"}]},
    ]
    state.update(overrides)
    return state


def test_route_validator_ok_critic_off_multi_slide():
    state = _multi_slide_state(
        critic_mode="off",
        compile_result={"ok": True, "retryable": False, "diagnostics": [], "warnings": []},
    )
    assert route_after_validator(state) == "slide_router"


def test_route_validator_budget_exhausted_multi_slide():
    state = _multi_slide_state(
        compile_result={"ok": False, "retryable": True, "diagnostics": [{"type": "X", "message": "e"}], "warnings": []},
        retry_count=3,
        retry_budget=3,
    )
    assert route_after_validator(state) == "placeholder"


def test_route_validator_stall_breaks_loop_multi_slide():
    state = _multi_slide_state(
        compile_result={"ok": False, "retryable": True, "diagnostics": [{"type": "OVERFLOW", "message": "e"}], "warnings": []},
        retry_count=1,
        stall_detected=True,
    )
    assert route_after_validator(state) == "placeholder"


def test_route_critic_pass_multi_slide():
    state = _multi_slide_state(
        critic_result={"passed": True, "issues": []},
    )
    assert route_after_critic(state) == "slide_router"


def test_route_critic_fail_budget_exhausted_multi_slide():
    state = _multi_slide_state(
        critic_result={"passed": False, "issues": [{"severity": "high"}]},
        visual_repair_count=2,  # matches default budget=2
    )
    assert route_after_critic(state) == "slide_router"


def test_route_slide_router_more_slides():
    state = _multi_slide_state(current_slide_index=1)
    assert route_after_slide_router(state) == "context_builder"


def test_route_slide_router_all_done():
    state = _multi_slide_state(current_slide_index=2)
    assert route_after_slide_router(state) == "deck_assembler"


def test_route_single_slide_still_goes_evaluator():
    state = initial_state(run_id="ss1", raw_request="test")
    state["slide_plans"] = [{"slide_index": 0, "components": [{"kind": "title"}]}]
    state["critic_result"] = {"passed": True, "issues": []}
    assert route_after_critic(state) == "evaluator"


@patch("src.agents.critic.run_visual_critic", side_effect=_mock_visual_critic_pass)
@patch("src.agents.critic.render_screenshots")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
@patch("src.agents.deck_nodes.compile_xml")
def test_multi_slide_e2e(
    mock_deck_compile, mock_gen_llm,
    mock_compile, mock_validate, mock_screenshots, mock_vc,
):
    """Multi-slide: 2 pre-loaded slides, both compile, deck assembles."""
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")

    slide_xmls = [
        '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n<Slide><VStack w="1280" h="720"><Text>Cover</Text></VStack></Slide>',
        '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n<Slide><VStack w="1280" h="720"><Text>Revenue</Text></VStack></Slide>',
    ]
    call_count = {"n": 0}

    def gen_side_effect(messages):
        resp = MagicMock()
        resp.content = slide_xmls[min(call_count["n"], len(slide_xmls) - 1)]
        resp.response_metadata = {
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model_name": "gpt-4.1-mini",
        }
        call_count["n"] += 1
        return resp

    gen_llm = MagicMock()
    gen_llm.invoke.side_effect = gen_side_effect
    mock_gen_llm.return_value = gen_llm

    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/slide.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_deck_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/deck.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="ms-e2e", raw_request="Create a 2-slide deck")
    state["slide_plans"] = [
        {
            "slide_index": 0, "slide_type": "cover",
            "components": [{"kind": "title", "count": 1, "content_summary": "Cover"}],
            "layout_hint": "centered title",
            "content_data": {}, "data_provenance": {},
        },
        {
            "slide_index": 1, "slide_type": "data",
            "components": [{"kind": "chart", "count": 1, "content_summary": "Revenue"}],
            "layout_hint": "chart full width",
            "content_data": {}, "data_provenance": {},
        },
    ]
    app = compile_graph()
    result = app.invoke(state)

    assert result["passed"] is True
    assert len(result["completed_slides"]) == 2
    assert result["completed_slides"][0]["slide_index"] == 0
    assert result["completed_slides"][1]["slide_index"] == 1
    assert mock_deck_compile.called


@patch("src.agents.critic.run_visual_critic", side_effect=_mock_visual_critic_pass)
@patch("src.agents.critic.render_screenshots")
@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
@patch("src.agents.generator.get_llm")
@patch("src.agents.deck_nodes.compile_xml")
def test_8_slide_deck_no_recursion_error(
    mock_deck_compile, mock_gen_llm,
    mock_compile, mock_validate, mock_screenshots, mock_vc,
):
    """8-slide deck completes without hitting the recursion limit."""
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")

    xml_tpl = '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n<Slide><VStack w="1280" h="720"><Text>Slide {n}</Text></VStack></Slide>'

    call_count = {"n": 0}

    def gen_side_effect(messages):
        resp = MagicMock()
        resp.content = xml_tpl.format(n=call_count["n"])
        resp.response_metadata = {
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model_name": "gpt-4.1-mini",
        }
        call_count["n"] += 1
        return resp

    gen_llm = MagicMock()
    gen_llm.invoke.side_effect = gen_side_effect
    mock_gen_llm.return_value = gen_llm

    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/slide.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    mock_deck_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/deck-8.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="ms-8slide", raw_request="Create an 8-slide deck")
    state["slide_plans"] = [
        {
            "slide_index": i, "slide_type": "data",
            "components": [{"kind": "title", "count": 1, "content_summary": f"Slide {i}"}],
            "layout_hint": "standard layout",
            "content_data": {}, "data_provenance": {},
        }
        for i in range(8)
    ]
    app = compile_graph()
    result = app.invoke(state, config={"recursion_limit": 150})

    assert result["passed"] is True
    assert len(result["completed_slides"]) == 8
    for i in range(8):
        assert result["completed_slides"][i]["slide_index"] == i


# ── Visual repairer routing (re-screenshot loop) ─────────────────────────


def test_route_visual_repairer_improved_routes_to_critic():
    state = initial_state(run_id="vr1", raw_request="test")
    state["visual_repair_outcome"] = "improved"
    state["visual_repair_count"] = 1
    assert route_after_visual_repairer(state) == "critic"


def test_route_visual_repairer_noop_skips_critic():
    state = initial_state(run_id="vr2", raw_request="test")
    state["visual_repair_outcome"] = "noop"
    state["visual_repair_count"] = 1
    assert route_after_visual_repairer(state) == "evaluator"


def test_route_visual_repairer_failed_skips_critic():
    state = initial_state(run_id="vr3", raw_request="test")
    state["visual_repair_outcome"] = "failed"
    state["visual_repair_count"] = 1
    assert route_after_visual_repairer(state) == "evaluator"


def test_route_visual_repairer_budget_exhausted():
    state = initial_state(run_id="vr4", raw_request="test")
    state["visual_repair_outcome"] = "improved"
    state["visual_repair_count"] = 2  # matches budget=2
    assert route_after_visual_repairer(state) == "evaluator"


def test_route_visual_repairer_multi_slide():
    state = initial_state(run_id="vr5", raw_request="test")
    state["slide_plans"] = [
        {"slide_index": 0, "components": []},
        {"slide_index": 1, "components": []},
    ]
    state["visual_repair_outcome"] = "failed"
    state["visual_repair_count"] = 1
    assert route_after_visual_repairer(state) == "slide_router"


# ── Critic scoring ───────────────────────────────────────────────────────


def test_critic_score_good():
    assert compute_critic_score([], "good") == 0


def test_critic_score_high_issues():
    issues = [{"severity": "high"}, {"severity": "medium"}]
    assert compute_critic_score(issues, "needs_tuning") == -(10 + 3 + 5)


def test_critic_score_layout_broken():
    issues = [{"severity": "high"}, {"severity": "high"}]
    assert compute_critic_score(issues, "layout_broken") == -(10 + 10 + 15)


def test_critic_score_low_only():
    issues = [{"severity": "low"}, {"severity": "low"}]
    assert compute_critic_score(issues, "good") == -2


# ── Critic rollback on regression ────────────────────────────────────────


@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_rollback_when_repair_worsens(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")
    mock_vc.return_value = (
        [
            {"severity": "high", "type": "visual", "description": "New issue A",
             "fix": "fix A", "affected_nodes": [], "source": "visual"},
            {"severity": "high", "type": "structure", "description": "New issue B",
             "fix": "fix B", "affected_nodes": [], "source": "visual"},
        ],
        {"tokens_in": 100, "tokens_out": 50, "model": "gpt-4.1"},
        {"strategy": "patch", "assessment": "layout_broken", "affected_nodes": []},
    )

    state = initial_state(run_id="rb1", raw_request="test", critic_mode="auto")
    state["current_xml"] = "<Slide><VStack>repaired</VStack></Slide>"
    state["compile_result"] = {"ok": True, "pptx_path": "/tmp/t.pptx", "diagnostics": [], "warnings": []}
    state["slide_plans"] = [{"slide_index": 0, "components": []}]
    state["visual_repair_count"] = 1  # re-review round
    state["pre_critic_xml"] = "<Slide><VStack>original</VStack></Slide>"
    state["pre_critic_slide_plans"] = [{"slide_index": 0, "components": []}]
    state["pre_critic_contract"] = {"theme_element": ""}
    state["pre_critic_score"] = -13  # original had 1 HIGH + needs_tuning
    state["visual_critic_result"] = {
        "issues": [{"severity": "high", "type": "visual", "description": "Old issue",
                     "fix": "fix", "affected_nodes": [], "source": "visual"}],
    }

    from src.agents.critic import critic_node
    result = critic_node(state)

    assert result["critic_result"]["passed"] is True  # rollback forces pass
    assert result["current_xml"] == "<Slide><VStack>original</VStack></Slide>"


@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_saves_snapshot_on_first_run(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")
    mock_vc.return_value = (
        [{"severity": "high", "type": "visual", "description": "Issue",
          "fix": "fix", "affected_nodes": [], "source": "visual"}],
        {"tokens_in": 100, "tokens_out": 50, "model": "gpt-4.1"},
        {"strategy": "patch", "assessment": "needs_tuning", "affected_nodes": []},
    )

    state = initial_state(run_id="snap1", raw_request="test", critic_mode="auto")
    state["current_xml"] = "<Slide>original</Slide>"
    state["compile_result"] = {"ok": True, "pptx_path": "/tmp/t.pptx", "diagnostics": [], "warnings": []}
    state["slide_plans"] = [{"slide_index": 0, "components": []}]

    from src.agents.critic import critic_node
    result = critic_node(state)

    assert result["pre_critic_xml"] == "<Slide>original</Slide>"
    assert result["pre_critic_score"] == -(10 + 5)  # 1 HIGH + needs_tuning


@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_round2_forces_patch_strategy(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")
    mock_vc.return_value = (
        [{"severity": "high", "type": "structure", "description": "Broken layout",
          "fix": "rebuild", "affected_nodes": ["VStack"], "source": "visual"}],
        {"tokens_in": 100, "tokens_out": 50, "model": "gpt-4.1"},
        {"strategy": "regenerate", "assessment": "layout_broken", "affected_nodes": []},
    )

    state = initial_state(run_id="r2strat", raw_request="test", critic_mode="auto")
    state["current_xml"] = "<Slide>repaired</Slide>"
    state["compile_result"] = {"ok": True, "pptx_path": "/tmp/t.pptx", "diagnostics": [], "warnings": []}
    state["slide_plans"] = [{"slide_index": 0, "components": []}]
    state["visual_repair_count"] = 1  # re-review round
    state["pre_critic_xml"] = "<Slide>original</Slide>"
    state["pre_critic_slide_plans"] = [{"slide_index": 0, "components": []}]
    state["pre_critic_contract"] = None
    state["pre_critic_score"] = -50  # worse than -25, so score improved → no rollback
    state["visual_critic_result"] = {"issues": []}

    from src.agents.critic import critic_node
    result = critic_node(state)

    # Strategy constrained from regenerate to patch on round 2
    assert result["visual_critic_result"]["repair_hints"]["strategy"] == "patch"


@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_rollback_on_equal_score(mock_vc, mock_screenshots):
    """Equal score means repair didn't help — rollback to original."""
    mock_screenshots.return_value = _mock_screenshot_batch("/tmp/slide-0.png")
    mock_vc.return_value = (
        [{"severity": "high", "type": "visual", "description": "Different issue",
          "fix": "fix", "affected_nodes": [], "source": "visual"}],
        {"tokens_in": 100, "tokens_out": 50, "model": "gpt-4.1"},
        {"strategy": "patch", "assessment": "needs_tuning", "affected_nodes": []},
    )

    state = initial_state(run_id="eq1", raw_request="test", critic_mode="auto")
    state["current_xml"] = "<Slide><VStack>repaired</VStack></Slide>"
    state["compile_result"] = {"ok": True, "pptx_path": "/tmp/t.pptx", "diagnostics": [], "warnings": []}
    state["slide_plans"] = [{"slide_index": 0, "components": []}]
    state["visual_repair_count"] = 1
    state["pre_critic_xml"] = "<Slide><VStack>original</VStack></Slide>"
    state["pre_critic_slide_plans"] = [{"slide_index": 0, "components": []}]
    state["pre_critic_contract"] = {"theme_element": ""}
    state["pre_critic_score"] = -15  # same: 1 HIGH + needs_tuning = -15
    state["visual_critic_result"] = {"issues": []}

    from src.agents.critic import critic_node
    result = critic_node(state)

    assert result["critic_result"]["passed"] is True
    assert result["current_xml"] == "<Slide><VStack>original</VStack></Slide>"
