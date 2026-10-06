"""Step 0.1: every LLM call is named by pipeline step and slide, with reasoning and cached tokens."""

import json
from unittest.mock import MagicMock, patch

from src.agents.evaluator import _build_step_summary
from src.agents.generator import generator_node
from src.state import initial_state
from src.utils.llm_client import extract_usage, unpack_raw, usage_record


def _response(prompt=1000, completion=300, reasoning=0, cached=0, model="gpt-5-mini-2025-08-07"):
    r = MagicMock()
    r.content = "<Slide><VStack><Text>x</Text></VStack></Slide>"
    r.response_metadata = {
        "token_usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "completion_tokens_details": {"reasoning_tokens": reasoning},
            "prompt_tokens_details": {"cached_tokens": cached},
        },
        "model_name": model,
    }
    return r


def test_extract_usage_reads_reasoning_and_cached_tokens():
    usage = extract_usage(_response(prompt=4096, completion=900, reasoning=700, cached=3072))
    assert usage["tokens_in"] == 4096
    assert usage["tokens_out"] == 900
    assert usage["tokens_reasoning"] == 700
    assert usage["tokens_cached"] == 3072


def test_extract_usage_without_details_defaults_to_zero():
    r = MagicMock()
    r.response_metadata = {"token_usage": {"prompt_tokens": 5, "completion_tokens": 2}, "model_name": "m"}
    usage = extract_usage(r)
    assert usage["tokens_reasoning"] == 0
    assert usage["tokens_cached"] == 0


def test_unpack_raw_fallback_has_every_field():
    _, usage = unpack_raw(object())
    assert {"tokens_in", "tokens_out", "tokens_reasoning", "tokens_cached", "model"} <= set(usage)


def test_usage_record_names_step_and_slide():
    usage = extract_usage(_response(cached=64))
    rec = usage_record(usage, "slide_component_planner", 3, reask=True)
    assert rec["step"] == "slide_component_planner"
    assert rec["slide_index"] == 3
    assert rec["reask"] is True
    assert rec["tokens_cached"] == 64
    assert usage_record(usage, "outline_planner")["slide_index"] is None


@patch("src.agents.generator.get_llm")
def test_generator_record_carries_step_slide_and_tokens(mock_get_llm):
    mock_get_llm.return_value.invoke.return_value = _response(prompt=500, completion=200, reasoning=0, cached=128,
                                                              model="gpt-4.1")
    state = initial_state(run_id="u", raw_request="x", deck_min_threshold=0)
    state["slide_plans"] = [{"slide_index": 0, "components": [], "layout_hint": ""}]
    state["contract"] = {"allowed_nodes": ["Slide"], "allowed_attributes": {}, "forbidden_tags": [],
                         "forbidden_attributes": [], "theme_element": "<Theme />", "component_count": 0,
                         "house_style": "", "notes": []}
    state["current_slide_index"] = 2
    record = generator_node(state)["generation_history"][0]
    assert record["step"] == "generator"
    assert record["slide_index"] == 2
    assert record["tokens_cached"] == 128
    assert record["tokens_reasoning"] == 0


def test_step_summary_carries_the_new_fields():
    history = [
        usage_record(extract_usage(_response(cached=10, reasoning=5)), "outline_planner"),
        {"attempt": 0, "tier": 0, "tokens_in": 1, "tokens_out": 1, "model": "gpt-4.1"},  # an old-style record
    ]
    steps = _build_step_summary(history)
    assert steps[0]["step"] == "outline_planner" and steps[0]["slide_index"] is None
    assert steps[0]["tokens_cached"] == 10 and steps[0]["tokens_reasoning"] == 5
    assert steps[1]["step"] == "unknown" and steps[1]["tokens_cached"] == 0


def _manifest(tmp_path, name, steps):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "run-manifest.json").write_text(json.dumps({"steps": steps}), encoding="utf-8")
    return folder


def test_usage_report_totals_per_step_and_old_manifests(tmp_path):
    from scripts.usage_report import collect, find_manifests, render

    new = _manifest(tmp_path, "deck-a__r1", [
        {"step": "generator", "slide_index": 0, "tokens_in": 100, "tokens_out": 10, "tokens_cached": 40,
         "tokens_reasoning": 0, "cost": 0.5},
        {"step": "generator", "slide_index": 1, "tokens_in": 200, "tokens_out": 20, "tokens_cached": 0,
         "tokens_reasoning": 0, "cost": 0.25},
    ])
    old = _manifest(tmp_path, "old__r1", [{"model": "gpt-4.1", "tokens_in": 7, "tokens_out": 3, "cost": 0.1}])
    manifests = find_manifests([tmp_path])
    assert len(manifests) == 2
    rows = collect(manifests)
    assert rows[("deck-a__r1", "generator", None)]["tokens_in"] == 300
    assert rows[("deck-a__r1", "generator", None)]["tokens_cached"] == 40
    assert rows[("old__r1", "unknown", None)]["calls"] == 1
    per_slide = collect(find_manifests([new]), per_slide=True)
    assert set(per_slide) == {("deck-a__r1", "generator", 0), ("deck-a__r1", "generator", 1)}
    assert "**total**" in render(rows)
    assert old.exists()
