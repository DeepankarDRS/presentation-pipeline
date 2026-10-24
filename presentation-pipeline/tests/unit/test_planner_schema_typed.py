"""Typed planner output (PLANNER_SCHEMA=typed, docs/planner-output-schema-research-2026-10-15.md): the schema keeps
OpenAI's strict rules, every kind's content gives today's content_data dict, and the planner switches on the env."""

from __future__ import annotations

import json
from typing import get_args
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from src.agents.schemas.planner_schema import PlannerComponent, PlannerSlide
from src.agents.schemas.planner_schema_typed import (COMPONENT_BY_KIND, CONTENT_BY_KIND, PlannerSlideTyped,
                                             content_data_of, content_from_data)
from src.agents.planning.slide_component_planner import _planner_slide_to_state, plan_single_slide, planner_schema
from src.state import ComponentKindLiteral
from src.utils.strict_schema import sent_schema, strict_problems

# one content_data per kind, in the shape the system prompt documents
SAMPLES = {
    "title": {"title": "The app grew its base and kept it", "subtitle": "Q3 at a glance"},
    "narrative": {"text": "Billing is the only queue above target."},
    "caption": {"text": "Source: support desk export, 30 Sep"},
    "kpi_row": {"kpi_labels": ["ARR", "NRR"], "kpi_values": ["$42.8M", "114%"], "kpi_deltas": ["+18% QoQ", ""],
                "kpi_directions": ["up", ""], "kpi_tones": ["good", ""], "kpi_icons": ["wallet", "repeat"]},
    "chart": {"chart_type": "bar", "chart_title": "Revenue by quarter", "chart_labels": ["Q1", "Q2"],
              "chart_values": [28.4, "₹31.2"]},
    "table": {"table_columns": ["Segment", "Revenue"], "table_rows": [["Enterprise", "$28.1M"]]},
    "bullet_list": {"bullets": ["First", "Second"]},
    "timeline": {"direction": "horizontal", "timeline_items": [{"date": "Q1 2025", "label": "Launch"}]},
    "flow": {"direction": "horizontal", "flow_steps": ["Discover", "Build"]},
    "process_arrow": {"direction": "horizontal", "process_steps": ["Intake", "Review"]},
    "pyramid": {"direction": "up", "pyramid_levels": ["Strategy", "Tactics"]},
    "tree": {"layout": "vertical", "tree_nodes": [{"label": "Root", "children": [{"label": "A"}, {"label": "B"}]}]},
    "matrix": {"x_axis": "Effort", "y_axis": "Impact",
               "quadrants": {"top_left": "Plan", "top_right": "Do first", "bottom_left": "Skip",
                             "bottom_right": "Quick wins"},
               "matrix_items": [{"label": "Search", "x": "low", "y": "high"}]},
    "card_grid": {"card_layout": "matrix", "columns": ["Web", "App"], "rows": ["Visibility"], "focus_card": 1,
                  "cards": [{"title": "Search", "tone": "good", "icon": "search"},
                            {"title": "Home screen", "body": "Placement on day 1", "key_phrase": "day 1", "tone": ""}]},
    "layer": {"description": "Three layers", "layers": [{"title": "Channels", "items": ["Website", "App"]}]},
}


def test_every_kind_has_a_typed_component():
    assert set(COMPONENT_BY_KIND) == set(CONTENT_BY_KIND) == set(get_args(ComponentKindLiteral)) == set(SAMPLES)


@pytest.mark.parametrize("model", [PlannerSlide, PlannerSlideTyped])
def test_schemas_keep_openai_strict_rules(model):
    problems, sizes = strict_problems(sent_schema(model))
    assert problems == []
    assert sizes["depth"] <= 10 and sizes["properties"] <= 5000 and sizes["enum_values"] <= 1000


def test_strict_check_catches_what_openai_rejects():
    class Bad(BaseModel):
        kind: str = Field(json_schema_extra={"oneOf": [{"type": "string"}]})
    schema = sent_schema(Bad)
    schema["properties"]["extra"] = {"type": "object", "properties": {"a": {"type": "string"}}}
    problems, _ = strict_problems(schema)
    assert any("oneOf" in p for p in problems)
    assert any("additionalProperties" in p for p in problems)
    assert any("required" in p for p in problems)


def test_typed_schema_has_no_titles_or_defaults_but_keeps_a_property_called_title():
    text = json.dumps(sent_schema(PlannerSlideTyped))
    assert '"default"' not in text and '"title": "' not in text
    assert "title" in sent_schema(PlannerSlideTyped)["$defs"]["TitleContent"]["properties"]


def test_each_component_starts_with_its_id_and_kind():
    for kind, model in COMPONENT_BY_KIND.items():
        assert list(model.model_fields)[:2] == ["component_id", "kind"], kind


@pytest.mark.parametrize("kind", sorted(SAMPLES))
def test_typed_content_gives_todays_content_data(kind):
    data = SAMPLES[kind]
    content = content_from_data(kind, data)
    extra = {"chart_type": data["chart_type"]} if kind == "chart" else {}
    comp = COMPONENT_BY_KIND[kind](component_id="c", kind=kind, content=content, **extra)
    assert content_data_of(comp) == data


def test_typed_content_rejects_keys_of_another_kind_and_bad_values():
    with pytest.raises(ValidationError):
        content_from_data("title", {"title": "x", "bullets": ["y"]})
    with pytest.raises(ValidationError):
        content_from_data("kpi_row", {"kpi_labels": ["a"], "kpi_values": ["1"], "kpi_tones": ["great"]})
    with pytest.raises(ValidationError):   # kind and content must match
        PlannerSlideTyped.model_validate({"slide_type": "data", "layout_hint": "", "components": [
            {"component_id": "t", "kind": "table", "count": 1, "columns": 0, "rows": 0, "content": {"bullets": ["a"]},
             "content_summary": "", "design_hint": "", "weight": "peer"}]})


def _typed_reply() -> PlannerSlideTyped:
    return PlannerSlideTyped.model_validate({"slide_type": "data", "layout_hint": "kpis on top", "components": [
        {"component_id": "slide_title", "kind": "title", "count": 1, "content": {"title": "Q3", "subtitle": None},
         "content_summary": "", "design_hint": "", "weight": "minor"},
        {"component_id": "rev", "kind": "chart", "chart_type": "bar", "series_count": 1, "count": 1,
         "content": {"chart_title": None, "chart_labels": ["Q1", "Q2"], "chart_values": [1.5, 2.0],
                     "chart_series": None},
         "content_summary": "revenue", "design_hint": "", "weight": "hero"},
    ]})


def test_typed_reply_and_string_reply_give_the_same_plan():
    typed = _planner_slide_to_state(0, _typed_reply())
    string = _planner_slide_to_state(0, PlannerSlide(slide_type="data", layout_hint="kpis on top", components=[
        PlannerComponent(component_id="slide_title", kind="title", weight="minor",
                         content_data_json='{"title": "Q3"}'),
        PlannerComponent(component_id="rev", kind="chart", chart_type="bar", series_count=1, weight="hero",
                         content_summary="revenue",
                         content_data_json='{"chart_type": "bar", "chart_labels": ["Q1", "Q2"], "chart_values": [1.5, 2.0]}'),
    ]))
    assert typed == string
    assert typed["components"][1]["content_data"] == {"chart_type": "bar", "chart_labels": ["Q1", "Q2"],
                                                      "chart_values": [1.5, 2.0]}


@pytest.mark.parametrize("env,expected", [(None, "typed"), ("typed", "typed"), ("STRING ", "string"), ("string", "string"), ("x", "typed")])
def test_planner_schema_switch(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("PLANNER_SCHEMA", raising=False)
    else:
        monkeypatch.setenv("PLANNER_SCHEMA", env)
    assert planner_schema() == expected


@pytest.mark.parametrize("env,model,field", [("typed", PlannerSlideTyped, "content"),
                                             ("string", PlannerSlide, "content_data_json")])
@patch("src.agents.planning.slide_component_planner.get_llm")
def test_plan_single_slide_uses_the_chosen_schema_and_names_its_field(mock_get_llm, monkeypatch, env, model, field):
    monkeypatch.setenv("PLANNER_SCHEMA", env)
    reply = _typed_reply() if model is PlannerSlideTyped else PlannerSlide(
        slide_type="data", layout_hint="", components=[
            PlannerComponent(component_id="slide_title", kind="title", content_data_json='{"title": "Q3"}')])
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = reply
    mock_get_llm.return_value = llm
    slide = {"slide_index": 0, "slide_title": "Q3", "key_messages": ["Revenue Q1 1.5, Q2 2.0"]}
    plan, _ = plan_single_slide(slide, outline_plan={"slides": [slide]})
    assert llm.with_structured_output.call_args.args[0] is model
    system, user = llm.with_structured_output.return_value.invoke.call_args.args[0]
    for msg in (system.content, user.content):
        assert f'"{field}"' in msg or f" {field}" in msg
        if field == "content":
            assert "content_data_json" not in msg
    assert plan["components"][0]["content_data"]["title"] == "Q3"
