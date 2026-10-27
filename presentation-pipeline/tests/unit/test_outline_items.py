"""Outline items, gate 0 (docs/outline-items-design-2026-10-27.md): the outline's items (kind + text), the
OUTLINE_ITEMS flag, key_messages computed from items, prompt rendering, the fit list and the report-only checks."""

from __future__ import annotations

from typing import get_args
from unittest.mock import MagicMock, patch

import pytest

from src.agents.outline_items import (ITEM_KINDS, item_issues, items_for_planner, kind_fit, kind_fit_notes,
                                      messages_from_items, outline_items_on, review_points, settle_items)
from src.agents.outline_planner import outline_planner_node
from src.agents.outline_planner_schema import (OutlineItem, OutlineItemsSlide, OutlinePlannerItemsOutput,
                                               OutlinePlannerOutput)
from src.agents.planner_schema_typed import CONTENT_BY_KIND, PlannerSlideTyped
from src.agents.slide_component_planner import plan_single_slide
from src.utils.strict_schema import sent_schema, strict_problems

REVENUE = [
    {"kind": "series", "text": "Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M"},
    {"kind": "metric", "text": "ARR: $42.8M (+18% QoQ)"},
    {"kind": "metric", "text": "NRR: 114%"},
    {"kind": "visual", "text": "trend chart with KPIs on top"},
]
BRIEF = ("Slide 3 - Revenue. Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M. "
         "ARR $42.8M (+18% QoQ), NRR 114%. Self-serve onboarding cuts CAC payback to 10 months. "
         "Visual: trend chart with KPIs on top")


# ── flag ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("env,expected", [(None, False), ("off", False), ("on", True), (" ON ", True), ("x", False)])
def test_flag_is_off_by_default(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("OUTLINE_ITEMS", raising=False)
    else:
        monkeypatch.setenv("OUTLINE_ITEMS", env)
    assert outline_items_on() is expected


# ── schema ──────────────────────────────────────────────────────────────────

def test_item_kinds_are_the_seven_of_the_spec():
    assert set(ITEM_KINDS) == {"metric", "series", "records", "steps", "point", "visual", "note"}
    assert set(get_args(OutlineItem.model_fields["kind"].annotation)) == set(ITEM_KINDS)


def test_items_slide_has_items_not_key_messages():
    assert "items" in OutlineItemsSlide.model_fields
    assert "key_messages" not in OutlineItemsSlide.model_fields
    for f in ("label", "slide_title", "subtitle", "section", "narrative_role", "slide_index"):
        assert f in OutlineItemsSlide.model_fields


def test_items_output_is_a_valid_strict_schema():
    problems, _ = strict_problems(sent_schema(OutlinePlannerItemsOutput))
    assert problems == []


# ── key_messages computed from items ─────────────────────────────────────────

def test_messages_from_items_gives_today_shape():
    assert messages_from_items(REVENUE) == [
        "Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M",
        "ARR: $42.8M (+18% QoQ)",
        "NRR: 114%",
        "Visual: trend chart with KPIs on top",
    ]


def test_messages_from_items_skips_empty_and_keeps_a_visual_label_once():
    items = [{"kind": "point", "text": "  "}, {"kind": "visual", "text": "Visual: 4-stage roadmap"}]
    assert messages_from_items(items) == ["Visual: 4-stage roadmap"]


def test_settle_items_drops_speaker_notes_and_keeps_messages_in_step():
    slide = {"items": [*REVENUE, {"kind": "point", "text": "Speaker Notes: stress the Q4 jump"}]}
    notes = settle_items(slide)
    assert [i["kind"] for i in slide["items"]] == ["series", "metric", "metric", "visual"]
    assert slide["key_messages"] == messages_from_items(slide["items"])
    assert any("presenter notes" in n for n in notes)


def test_settle_items_moves_a_labelled_direction_to_visual():
    slide = {"items": [{"kind": "point", "text": "Visual: 4-stage growth roadmap"}]}
    settle_items(slide)
    assert slide["items"] == [{"kind": "visual", "text": "4-stage growth roadmap"}]
    assert slide["key_messages"] == ["Visual: 4-stage growth roadmap"]


# ── what the planner reads ───────────────────────────────────────────────────

def test_items_for_planner_when_items_match_key_messages():
    slide = {"items": REVENUE, "key_messages": messages_from_items(REVENUE)}
    assert items_for_planner(slide) == REVENUE


def test_items_for_planner_ignores_items_after_key_messages_were_edited():
    slide = {"items": REVENUE, "key_messages": [*messages_from_items(REVENUE)[:2], "NRR: 116%"]}
    assert items_for_planner(slide) is None
    assert items_for_planner({"key_messages": ["a"]}) is None


# ── fit list ─────────────────────────────────────────────────────────────────

def test_fit_list_covers_every_item_kind_and_names_real_components():
    fit = kind_fit()
    assert set(fit) == set(ITEM_KINDS)
    for kind, entry in fit.items():
        for comp in entry["options"]:
            assert comp in CONTENT_BY_KIND, f"{kind}: {comp} is not a component kind"
    assert fit["visual"]["options"] == []


def test_fit_list_is_the_widened_one():
    fit = kind_fit()
    assert fit["records"]["options"] == ["table", "chart", "kpi_row", "card_grid"]
    assert "tree" in fit["point"]["options"] and "pyramid" in fit["steps"]["options"]


def _plan(*comps):
    return {"slide_index": 0, "components": [{"component_id": f"c{i}", "kind": k, "content_data": cd}
                                             for i, (k, cd) in enumerate(comps)]}


def test_kind_fit_notes_report_a_pick_outside_the_list():
    items = [{"kind": "note", "text": "ZAROMA sheets cover campaigns only"}]
    plan = _plan(("table", {"table_columns": ["Note"], "table_rows": [["ZAROMA sheets cover campaigns only"]]}))
    notes = kind_fit_notes(plan, items)
    assert len(notes) == 1 and "KIND_OUTSIDE_FIT" in notes[0] and "note" in notes[0] and "table" in notes[0]


def test_kind_fit_notes_quiet_for_picks_inside_the_list():
    plan = _plan(("chart", {"chart_labels": ["Q1", "Q2", "Q3", "Q4"], "chart_values": [28.4, 31.2, 36.1, 42.8]}),
                 ("kpi_row", {"kpi_labels": ["ARR", "NRR"], "kpi_values": ["$42.8M", "114%"]}))
    assert kind_fit_notes(plan, REVENUE) == []


# ── report-only checks ───────────────────────────────────────────────────────

def test_review_points_flags_outline_commentary_only():
    items = [{"kind": "point", "text": "Self-serve onboarding cuts CAC payback to 10 months"},
             {"kind": "point", "text": "Momentum reflects strong enterprise adoption and expansion revenue"},
             {"kind": "metric", "text": "Pipeline coverage: 3.1x"}]
    assert review_points(items, BRIEF) == ["Momentum reflects strong enterprise adoption and expansion revenue"]


def test_item_issues_report_wrong_forms():
    items = [{"kind": "visual", "text": "chart of 42.8 and 31.2"},
             {"kind": "records", "text": "Enterprise | Mid-Market | SMB"},
             {"kind": "metric", "text": "ARR: $42.8M"}]
    codes = [c for c, _ in item_issues(items)]
    assert codes == ["VISUAL_WITH_NUMBERS", "RECORDS_WITHOUT_MEASURES"]


# ── outline planner node ─────────────────────────────────────────────────────

def _llm_returning(output):
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = output
    return llm


def _items_output():
    slide = OutlineItemsSlide(slide_index=0, label="REVENUE", slide_title="Revenue grew every quarter",
                              narrative_role="growth", items=[OutlineItem(**i) for i in REVENUE] + [
                                  OutlineItem(kind="point", text="Momentum reflects strong enterprise adoption")])
    return OutlinePlannerItemsOutput(deck_title="QBR", core_hook="Growth with a margin dip", slides=[slide])


@patch("src.agents.outline_planner.get_llm")
def test_outline_node_with_flag_on_asks_for_items_and_computes_key_messages(mock_get_llm, monkeypatch):
    monkeypatch.setenv("OUTLINE_ITEMS", "on")
    mock_get_llm.return_value = _llm_returning(_items_output())
    out = outline_planner_node({"raw_request": BRIEF})
    assert mock_get_llm.return_value.with_structured_output.call_args.args[0] is OutlinePlannerItemsOutput
    slide = out["outline_plan"]["slides"][0]
    assert slide["items"][0] == REVENUE[0]
    assert slide["key_messages"] == messages_from_items(slide["items"])
    assert slide["review_points"] == ["Momentum reflects strong enterprise adoption"]
    system = mock_get_llm.return_value.with_structured_output.return_value.invoke.call_args.args[0][0].content
    assert "## items Requirements" in system and "| metric |" in system
    assert "NARRATIVE messages add insight" not in system


@patch("src.agents.outline_planner.get_llm")
def test_outline_node_with_flag_off_is_todays_route(mock_get_llm, monkeypatch):
    monkeypatch.delenv("OUTLINE_ITEMS", raising=False)
    from src.agents.outline_planner_schema import OutlineSlide
    mock_get_llm.return_value = _llm_returning(OutlinePlannerOutput(deck_title="QBR", core_hook="x", slides=[
        OutlineSlide(slide_index=0, slide_title="Q3", narrative_role="", key_messages=["ARR: $42.8M"])]))
    out = outline_planner_node({"raw_request": BRIEF})
    assert mock_get_llm.return_value.with_structured_output.call_args.args[0] is OutlinePlannerOutput
    slide = out["outline_plan"]["slides"][0]
    assert "items" not in slide and slide["key_messages"] == ["ARR: $42.8M"]
    system = mock_get_llm.return_value.with_structured_output.return_value.invoke.call_args.args[0][0].content
    assert "NARRATIVE messages add insight" in system


# ── slide component planner prompts ──────────────────────────────────────────

def _planner_prompts(monkeypatch, slide, flag):
    if flag:
        monkeypatch.setenv("OUTLINE_ITEMS", "on")
    else:
        monkeypatch.delenv("OUTLINE_ITEMS", raising=False)
    llm = _llm_returning(PlannerSlideTyped.model_validate({"slide_type": "data", "layout_hint": "", "components": [
        {"component_id": "slide_title", "kind": "title", "count": 1, "content_summary": "", "design_hint": "",
         "weight": "peer", "content": {"title": "Revenue"}}]}))
    with patch("src.agents.slide_component_planner.get_llm", return_value=llm):
        plan, _ = plan_single_slide(slide, outline_plan={"slides": [slide]})
    system, user = llm.with_structured_output.return_value.invoke.call_args.args[0]
    return system.content, user.content, plan


def test_planner_reads_items_with_their_kind(monkeypatch):
    slide = {"slide_index": 0, "slide_title": "Revenue", "items": REVENUE, "key_messages": messages_from_items(REVENUE)}
    system, user, _ = _planner_prompts(monkeypatch, slide, flag=True)
    assert "1. [series] Revenue by quarter" in user and "2. [metric] ARR: $42.8M (+18% QoQ)" in user
    assert "trend chart with KPIs on top" in user          # still the visual direction block
    assert "[visual]" not in user
    assert "records: table, chart, kpi_row, card_grid" in system


def test_planner_without_items_is_todays_prompt(monkeypatch):
    slide = {"slide_index": 0, "slide_title": "Revenue", "key_messages": messages_from_items(REVENUE)}
    system, user, _ = _planner_prompts(monkeypatch, slide, flag=False)
    assert "[metric]" not in user and "records: table, chart, kpi_row, card_grid" not in system


def test_planner_keeps_kind_fit_notes_on_the_plan(monkeypatch):
    items = [{"kind": "note", "text": "ZAROMA sheets cover campaigns only"}]
    slide = {"slide_index": 0, "slide_title": "Caveat", "items": items, "key_messages": messages_from_items(items)}
    reply = PlannerSlideTyped.model_validate({"slide_type": "data", "layout_hint": "", "components": [
        {"component_id": "t", "kind": "table", "count": 1, "content_summary": "", "design_hint": "", "weight": "peer",
         "columns": 1, "rows": 1,
         "content": {"table_columns": ["Note"], "table_rows": [["ZAROMA sheets cover campaigns only"]]}}]})
    monkeypatch.setenv("OUTLINE_ITEMS", "on")
    llm = _llm_returning(reply)
    with patch("src.agents.slide_component_planner.get_llm", return_value=llm):
        plan, _ = plan_single_slide(slide, outline_plan={"slides": [slide]})
    assert any("KIND_OUTSIDE_FIT" in n for n in plan.get("kind_fit_notes", []))
