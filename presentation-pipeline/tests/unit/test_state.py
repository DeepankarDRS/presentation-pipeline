"""Tests for PresentationState schema and initial_state factory."""

from src.state import (
    AttemptRecord,
    CompileResult,
    ComponentPlan,
    CriticResult,
    DeckPlan,
    PresentationState,
    SlidePlan,
    ValidateResult,
    initial_state,
)


def test_initial_state_has_all_keys():
    state = initial_state(run_id="test-001", raw_request="Make a slide")
    assert state["run_id"] == "test-001"
    assert state["raw_request"] == "Make a slide"
    assert state["mode"] == "single"
    assert state["deck_min_threshold"] == 3
    assert state["slide_plans"] == []
    assert state["current_xml"] == ""
    assert state["generation_history"] == []
    assert state["retry_tier"] == 0
    assert state["retry_count"] == 0
    assert state["retry_budget"] == 3
    assert state["passed"] is False
    assert state["critic_mode"] == "auto"


def test_initial_state_custom_values():
    state = initial_state(
        run_id="test-002",
        raw_request="A dense KPI slide",
        theme_name="corporate-slate",
        deck_min_threshold=0,
        critic_mode="off",
        retry_budget=5,
        supplied_content={"title": "Q4 Results"},
    )
    assert state["theme_name"] == "corporate-slate"
    assert state["deck_min_threshold"] == 0
    assert state["critic_mode"] == "off"
    assert state["retry_budget"] == 5
    assert state["supplied_content"] == {"title": "Q4 Results"}


def test_component_plan_structure():
    plan = ComponentPlan(
        kind="chart",
        count=2,
        chart_type="bar",
        series_count=3,
        content_summary="Revenue by quarter",
    )
    assert plan["kind"] == "chart"
    assert plan["series_count"] == 3


def test_slide_plan_structure():
    plan = SlidePlan(
        slide_index=0,
        components=[ComponentPlan(kind="title", count=1)],
        density="dense",
        font_tier="compact",
        layout_hint="Title top, KPIs in 2x2 grid below",
        content_data={"title": "Q4 Revenue"},
    )
    assert plan["density"] == "dense"
    assert len(plan["components"]) == 1
    assert plan["layout_hint"].startswith("Title")


def test_compile_result_structure():
    cr = CompileResult(ok=True, pptx_path="/out/slide.pptx",
                       diagnostics=[], warnings=[], retryable=False)
    assert cr["ok"] is True
    assert cr["pptx_path"] == "/out/slide.pptx"


def test_validate_result_structure():
    vr = ValidateResult(ok=False, diagnostics=[
        {"type": "UNKNOWN_TAG", "message": '<Layer>: Unknown tag "Layerr"'}
    ], warnings=[])
    assert vr["ok"] is False
    assert len(vr["diagnostics"]) == 1


def test_critic_result_structure():
    cr = CriticResult(passed=False, issues=[
        {"severity": "high", "type": "missing_component",
         "description": "Plan specified chart but none in XML"}
    ])
    assert cr["passed"] is False
    assert cr["issues"][0]["severity"] == "high"


def test_attempt_record_structure():
    rec = AttemptRecord(
        attempt=1, tier=1,
        errors_in=["UNKNOWN_TAG: Layerr"],
        errors_out=[],
        stalled=False,
        tokens_in=1500, tokens_out=800,
        model="gpt-4.1-mini",
    )
    assert rec["tier"] == 1
    assert rec["model"] == "gpt-4.1-mini"


def test_generation_history_is_appendable():
    state = initial_state(run_id="test-003", raw_request="test")
    assert state["generation_history"] == []
    rec = AttemptRecord(attempt=0, tier=0)
    state["generation_history"].append(rec)
    assert len(state["generation_history"]) == 1
