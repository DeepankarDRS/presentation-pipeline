"""Tests for the slide replanner's two-tier gate."""

from unittest.mock import patch

from src.agents.slide_replanner import resolve_slide_plan

_THEME_INFO = {
    "name": "corporate-slate", "mode": "light", "is_dark": False,
    "chart_colors": ["2563EB"], "chart_colors_json": '["2563EB"]',
    "element": '<Theme accent="2563EB" />',
}


def _slide_plan(**overrides):
    plan = {
        "slide_index": 2,
        "slide_type": "content",
        "components": [{"kind": "title", "count": 1}, {"kind": "bullet_list", "count": 1}],
        "density": "normal",
        "font_tier": "standard",
        "layout_pattern": "hero_statement",
        "layout_hint": "title then bullets",
        "content_data": {"bullets": ["Point A", "Point B"]},
        "data_provenance": {"bullets": "user"},
    }
    plan.update(overrides)
    return plan


# ── Guards ─────────────────────────────────────────────────────────────────

def test_resolve_slide_plan_empty_slide_plan_returns_empty_contract():
    plan, contract = resolve_slide_plan({}, "move title", _THEME_INFO, "run-1")
    assert plan == {}
    assert contract == {}


def test_resolve_slide_plan_empty_theme_info_returns_empty_contract():
    plan = _slide_plan()
    result_plan, contract = resolve_slide_plan(plan, "move title", {}, "run-1")
    assert result_plan == plan
    assert contract == {}


# ── Tier 0 — no new component kind, reuse existing plan ────────────────────

@patch("src.agents.slide_replanner.plan_single_slide")
def test_tier0_no_new_kind_skips_replan(mock_plan_single_slide):
    plan = _slide_plan()
    updated_plan, contract = resolve_slide_plan(plan, "make the title bigger", _THEME_INFO, "run-1")

    mock_plan_single_slide.assert_not_called()
    assert updated_plan == plan
    assert "Slide" in contract["allowed_nodes"]


@patch("src.agents.slide_replanner.plan_single_slide")
def test_tier0_removal_feedback_skips_replan(mock_plan_single_slide):
    """Feedback that only mentions kinds already on the slide never triggers a replan."""
    plan = _slide_plan(components=[{"kind": "title"}, {"kind": "bullet_list"}])
    updated_plan, contract = resolve_slide_plan(plan, "remove the bullet list", _THEME_INFO, "run-1")

    mock_plan_single_slide.assert_not_called()
    assert updated_plan == plan


# ── Tier 2 — new component kind triggers a scoped replan ───────────────────

@patch("src.agents.slide_replanner.plan_single_slide")
def test_tier2_new_kind_triggers_replan(mock_plan_single_slide):
    plan = _slide_plan()
    replanned_slide = {
        "slide_index": 0,  # plan_single_slide re-enumerates from 0; caller restores real index
        "slide_type": "data",
        "components": [{"kind": "title"}, {"kind": "bullet_list"}, {"kind": "kpi_row", "count": 3}],
        "density": "normal",
        "font_tier": "standard",
        "layout_pattern": "two_column",
        "layout_hint": "title, bullets, KPI row",
        "content_data": {"bullets": ["Regenerated bullet"], "kpi_values": [10, 20, 30]},
        "data_provenance": {"bullets": "sample", "kpi_values": "sample"},
    }
    mock_plan_single_slide.return_value = replanned_slide

    updated_plan, contract = resolve_slide_plan(plan, "add a KPI row", _THEME_INFO, "run-1")

    mock_plan_single_slide.assert_called_once()
    # slide_index restored to the real position, not the planner's re-enumerated 0
    assert updated_plan["slide_index"] == 2
    # new component present
    assert any(c["kind"] == "kpi_row" for c in updated_plan["components"])
    # original content_data preserved over the replan's fresh guess
    assert updated_plan["content_data"]["bullets"] == ["Point A", "Point B"]
    # new key from the replan is still present
    assert updated_plan["content_data"]["kpi_values"] == [10, 20, 30]
    # contract now covers the new component's nodes
    assert "kpi_row" not in contract["allowed_nodes"]  # kpi_row isn't a node name itself
    assert "HStack" in contract["allowed_nodes"]  # but its underlying nodes are included


@patch("src.agents.slide_replanner.plan_single_slide")
def test_tier2_passes_prior_plan_and_feedback_to_state(mock_plan_single_slide):
    plan = _slide_plan()
    mock_plan_single_slide.return_value = dict(plan, slide_index=0)

    resolve_slide_plan(plan, "add a chart", _THEME_INFO, "run-42")

    # plan_single_slide(outline_slide, outline_plan=..., deck_settings=...)
    outline_slide_arg = mock_plan_single_slide.call_args[0][0]
    kwargs = mock_plan_single_slide.call_args[1]

    # outline_slide preserves the original slide's key fields
    assert outline_slide_arg["slide_index"] == plan["slide_index"]
    assert outline_slide_arg["slide_type"] == plan["slide_type"]
    assert set(outline_slide_arg["suggested_components"]) == {
        c["kind"] for c in plan["components"]
    }
    # outline_plan is passed as kwarg and contains the outline slide
    assert "outline_plan" in kwargs
    assert kwargs["outline_plan"]["slides"] == [outline_slide_arg]
    # theme is forwarded via deck_settings
    assert kwargs["deck_settings"]["theme"] == _THEME_INFO["name"]
