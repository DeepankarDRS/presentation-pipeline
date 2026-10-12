"""Step 0.2: plan checks (empty, instruction text, repeated card body, duplicates, thin) and the re-ask."""

import copy
import json
from unittest.mock import MagicMock, patch

from src.agents import slide_component_planner as scp
from src.agents.plan_checks import (
    PLAN_DUPLICATE_ITEMS, PLAN_EMPTY, PLAN_INSTRUCTION_TEXT, SLIDE_SPARSE,
    find_problems, finalize_plan, is_instruction_text, label_overlap, reask_context,
)
from src.agents.planner_schema import PlannerSlide
from src.agents.written_lines import drop_repeated_bodies

BRIEF = "Q3 review. ARR $48.2M. Close 3 enterprise logos. Ship analytics v2 before the board meeting."


def comp(cid, kind, data, weight="peer"):
    return {"component_id": cid, "kind": kind, "count": 1, "content_summary": "", "weight": weight,
            "content_data": data}


def plan(components, slide_type="data"):
    return {"slide_index": 0, "slide_type": slide_type, "components": components}


def codes(p):
    return [f["code"] for f in p.get("plan_flags", [])]


# ── instruction text: the strings the hold-out plans carried ────────────────

def test_instruction_text_from_the_holdout_plans():
    for text in (
        "Deepen the growth story by showing the six-quarter revenue trend and highlighting the acceleration.",
        "Break down ARR by segment to show where the growth is coming from.",
        "Speaker Notes: Lead with the governance diagnosis - show how generic and CPD are consuming budget.",
        "Walk through match-type performance first (Exact > Phrase > Broad).",
        "Use this slide to align stakeholders on common causes.",
        "Walk the audience through Stabilize, Rebuild, Scale.",
        "End with confidence - the audit already shows immediate improvement areas.",
    ):
        assert is_instruction_text(text, BRIEF), text


def test_slide_content_is_not_instruction_text():
    for text in (
        "These problems increase operational overhead, raise outage risk, and leave teams without a single source of truth.",
        "Close 3 enterprise logos worth $4M+ combined ARR",
        "Ship analytics v2 dashboard before Jan board meeting",
        "Recommendation: Scale exact winners, reduce phrase/broad leakage",
        "ARR grew 18% QoQ to $48.2M",
    ):
        assert not is_instruction_text(text, BRIEF), text


def test_planner_verb_is_fine_when_the_brief_says_it():
    brief = "Highlight the three winning cities in the closing note."
    assert not is_instruction_text("Highlight the three winning cities in the closing note.", brief)
    assert is_instruction_text("Highlight the three winning cities in the closing note.", "unrelated brief text")


# ── problems and fixes ──────────────────────────────────────────────────────

def test_empty_kpi_row_is_a_problem_and_an_empty_caption_is_not():
    p = plan([comp("title", "title", {}), comp("k", "kpi_row", {}, "hero"), comp("cap", "caption", {})])
    problems = find_problems(p, BRIEF)
    assert [(x["code"], x["component_id"]) for x in problems] == [(PLAN_EMPTY, "k")]
    notes = finalize_plan(p, BRIEF)
    assert any("empty caption" in n for n in notes)
    assert [c["component_id"] for c in p["components"]] == ["title", "k"]


def test_no_components_is_empty():
    assert find_problems(plan([]), BRIEF)[0]["code"] == PLAN_EMPTY


def test_title_with_no_data_is_not_empty():
    assert find_problems(plan([comp("t", "title", {})]), BRIEF) == []


def test_finalize_drops_instruction_text_and_bullets():
    p = plan([
        comp("n", "narrative", {"text": "Break down ARR by segment to show where the growth is coming from."}, "supporting"),
        comp("b", "bullet_list", {"bullets": ["Close 3 enterprise logos", "Walk through the pipeline first"]}, "hero"),
    ])
    finalize_plan(p, BRIEF)
    assert [c["component_id"] for c in p["components"]] == ["b"]
    assert p["components"][0]["content_data"]["bullets"] == ["Close 3 enterprise logos"]
    assert PLAN_INSTRUCTION_TEXT in codes(p)


def test_card_body_that_repeats_its_title_is_dropped_but_an_extension_stays():
    p = plan([comp("c", "card_grid", {"cards": [
        {"title": "Intent-layer campaign structure", "body": "Intent-layer campaign structure."},
        {"title": "Raw-data reporting", "body": "Raw-data reporting and weekly diagnostics."},
    ]})])
    notes = drop_repeated_bodies(p)
    cards = p["components"][0]["content_data"]["cards"]
    assert len(notes) == 1 and "body" not in cards[0]
    assert cards[1]["body"] == "Raw-data reporting and weekly diagnostics."


def test_duplicate_items_keep_the_richer_component_and_its_better_weight():
    steps = ["Connect", "Route", "Secure", "Monitor", "Scale"]
    chevrons = comp("flow", "process_arrow", {"process_steps": steps}, "hero")
    cards = comp("cards", "card_grid", {"cards": [{"title": s, "body": f"{s} the APIs with automatic checks"}
                                                  for s in steps]}, "supporting")
    assert label_overlap(chevrons, cards) == 1.0
    p = plan([chevrons, cards])
    finalize_plan(p, BRIEF)
    assert [c["component_id"] for c in p["components"]] == ["cards"]
    assert p["components"][0]["weight"] == "hero"
    assert PLAN_DUPLICATE_ITEMS in codes(p)


def test_short_lists_are_never_duplicates():
    a = comp("a", "bullet_list", {"bullets": ["Speed", "Cost"]})
    b = comp("b", "bullet_list", {"bullets": ["Speed", "Cost"]})
    assert label_overlap(a, b) == 0.0


def test_thin_slides_are_reported_not_changed():
    thin = plan([comp("b", "bullet_list", {"bullets": ["Close 3 enterprise logos worth $4M ARR",
                                                       "Launch self-serve onboarding to cut CAC payback",
                                                       "Ship analytics v2 before the board meeting"]}, "hero")])
    before = copy.deepcopy(thin["components"])
    finalize_plan(thin, BRIEF)
    assert SLIDE_SPARSE in codes(thin) and thin["components"] == before


def test_full_slides_and_single_tables_are_not_thin():
    kpis = plan([comp("k1", "kpi_row", {"kpi_labels": ["ARR"], "kpi_values": ["$48.2M"]}, "hero"),
                 comp("k2", "kpi_row", {"kpi_labels": ["NRR", "GM", "CAC"], "kpi_values": ["114%", "72%", "14m"]})])
    table = plan([comp("t", "table", {"table_columns": ["a", "b"], "table_rows": [["1", "2"], ["3", "4"]]}, "hero")])
    cover = plan([comp("t", "title", {"title": "x"})], slide_type="cover")
    for p in (kpis, table, cover):
        finalize_plan(p, BRIEF)
        assert SLIDE_SPARSE not in codes(p)


def test_reask_context_names_the_failures():
    ctx = reask_context(find_problems(plan([comp("k", "kpi_row", {}, "hero")]), BRIEF))
    assert ctx["failed_kinds"] == ["kpi_row"] and "no content" in ctx["errors"][0]
    assert "speaker notes" in ctx["directive"]


# ── the re-ask wrapper ──────────────────────────────────────────────────────

SLIDE = {"slide_index": 2, "slide_title": "Growth", "label": "KPIS", "subtitle": "",
         "key_messages": ["ARR $48.2M, +18% QoQ", "Visual: dark hero tile"]}
OUTLINE = {"core_hook": "h", "slides": [SLIDE]}
USAGE = {"tokens_in": 100, "tokens_out": 10, "tokens_reasoning": 3, "tokens_cached": 0, "model": "gpt-5-mini"}


def good():
    return plan([comp("k", "kpi_row", {"kpi_labels": ["ARR"], "kpi_values": ["$48.2M"]}, "hero")])


def bad():
    return plan([comp("k", "kpi_row", {}, "hero")])


def run(side_effects):
    with patch.object(scp, "plan_single_slide", side_effect=side_effects) as m:
        result = scp.plan_with_reask(SLIDE, outline_plan=OUTLINE)
    return result, m


def test_a_good_plan_is_asked_once():
    (p, history), m = run([(good(), USAGE)])
    assert m.call_count == 1 and len(history) == 1 and history[0]["reask"] is False
    assert history[0]["step"] == "slide_component_planner" and history[0]["slide_index"] == 2


def test_an_empty_plan_is_asked_again_once_and_the_better_plan_wins():
    (p, history), m = run([(bad(), USAGE), (good(), USAGE)])
    assert m.call_count == 2
    assert [h["reask"] for h in history] == [False, True]
    assert p["components"][0]["content_data"]["kpi_values"] == ["$48.2M"]
    assert any(n.startswith("planner re-asked because: kpi_row") for n in p["capacity_fixes"])
    ctx = m.call_args_list[1].kwargs["repair_context"]
    assert ctx["failed_kinds"] == ["kpi_row"]


def test_the_wrapper_never_asks_a_third_time_and_keeps_the_first_on_a_tie():
    first, second = bad(), bad()
    second["components"][0]["component_id"] = "second"
    (p, history), m = run([(first, USAGE), (second, USAGE), (good(), USAGE)])
    assert m.call_count == 2 and len(history) == 2
    assert p["components"][0]["component_id"] == "k"
    assert PLAN_EMPTY in codes(p)


def test_a_raising_planner_is_asked_again_then_falls_back_to_the_briefs_own_lines():
    (p, history), m = run([RuntimeError("boom"), RuntimeError("boom")])
    assert m.call_count == 2 and history == []
    assert p["plan_source"] == "fallback"
    assert p["components"][0]["content_data"]["bullets"] == ["ARR $48.2M, +18% QoQ"]  # the Visual: line stays out
    assert p["slide_title"] == "Growth" and p["slide_index"] == 2


def test_failing_twice_with_no_content_lines_gives_no_components_but_is_flagged():
    slide = dict(SLIDE, key_messages=["Visual: dark hero tile"])
    with patch.object(scp, "plan_single_slide", side_effect=[RuntimeError("x"), RuntimeError("x")]):
        p, _ = scp.plan_with_reask(slide, outline_plan=OUTLINE)
    assert p["components"] == [] and PLAN_EMPTY in codes(p)


def test_a_failed_first_call_then_a_good_second_one_works():
    (p, history), _ = run([RuntimeError("boom"), (good(), USAGE)])
    assert len(history) == 1 and history[0]["reask"] is True and "plan_source" not in p


# ── through the real plan_single_slide with a scripted LLM ──────────────────

def _planner_slide(kpi_json: str) -> PlannerSlide:
    return PlannerSlide.model_validate({
        "slide_type": "data", "layout_hint": "kpi row",
        "components": [{"component_id": "k", "kind": "kpi_row", "count": 1, "weight": "hero",
                        "content_data_json": kpi_json}],
    })


def test_scripted_llm_end_to_end_reasks_with_the_repair_context_in_the_prompt():
    raw = MagicMock()
    raw.response_metadata = {"token_usage": {"prompt_tokens": 50, "completion_tokens": 5}, "model_name": "m"}
    replies = [{"parsed": _planner_slide("{}"), "raw": raw},
               {"parsed": _planner_slide(json.dumps({"kpi_labels": ["ARR"], "kpi_values": ["$48.2M"]})), "raw": raw}]
    structured = MagicMock()
    structured.invoke.side_effect = replies
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    with patch.object(scp, "get_llm", return_value=llm):
        p, history = scp.plan_with_reask(SLIDE, outline_plan=OUTLINE)
    assert structured.invoke.call_count == 2
    second_prompt = structured.invoke.call_args_list[1].args[0][1].content
    assert "REPAIR CONTEXT" in second_prompt and "no content" in second_prompt
    assert p["components"][0]["content_data"]["kpi_values"] == ["$48.2M"]
    assert [h["reask"] for h in history] == [False, True]


def test_a_bare_note_prefix_is_a_footnote_not_an_instruction():
    brief = "Apr 2027: SOC2 + HIPAA certification"
    assert not is_instruction_text("Note: SOC2 + HIPAA certification targeted for Apr 2027", brief)
    assert is_instruction_text("Speaker Notes: SOC2 + HIPAA certification", brief)   # the strong labels always count
    assert is_instruction_text("Talking points: lead with the enterprise story", brief)


def test_kpi_tones_are_settled_one_per_value():
    """tile-nodes spec §6: the planner's kpi_tones as code reads them (good / bad / watch / "")."""
    k = comp("kpis", "kpi_row", {"kpi_labels": ["ARR", "NRR", "Margin", "CAC"], "kpi_values": ["$48.2M", "114%", "72.1%", "14"],
                                 "kpi_tones": ["Positive", "good", "NEGATIVE", "warning", "bad"]})
    finalize_plan(plan([k]), BRIEF)
    assert k["content_data"]["kpi_tones"] == ["good", "good", "bad", "watch"]   # synonyms mapped, trimmed
    short = comp("k2", "kpi_row", {"kpi_labels": ["A", "B"], "kpi_values": ["1%", "2%"], "kpi_tones": ["meh"] * 1 + ["bad"]})
    finalize_plan(plan([short]), BRIEF)
    assert short["content_data"]["kpi_tones"] == ["", "bad"]   # unknown -> ""
    pad = comp("k3", "kpi_row", {"kpi_labels": ["A", "B"], "kpi_values": ["1%", "2%"], "kpi_tones": ["watch"]})
    finalize_plan(plan([pad]), BRIEF)
    assert pad["content_data"]["kpi_tones"] == ["watch", ""]
    none = comp("k4", "kpi_row", {"kpi_labels": ["A"], "kpi_values": ["1%"], "kpi_tones": ["", None]})
    finalize_plan(plan([none]), BRIEF)
    assert "kpi_tones" not in none["content_data"]   # no tone at all: none kept


def test_the_planner_prompt_asks_for_kpi_tones_by_meaning():
    from pathlib import Path
    text = (Path(scp.__file__).resolve().parents[1] / "prompts" / "slide_component_planner" / "system.j2").read_text(encoding="utf-8")
    assert '"kpi_tones": ["good", "good", "bad"]' in text and "not which way it moved" in text
    assert "kpi_tones" in PlannerSlide.model_json_schema()["$defs"]["PlannerComponent"]["properties"]["content_data_json"]["description"]


# ── what the log keeps when a planner call fails (tile-nodes wide eval, 2026-10-12) ──

def _length_error(reasoning=16000, out=16000):
    from openai import LengthFinishReasonError
    from openai.types import CompletionUsage
    from openai.types.chat import ChatCompletion
    from openai.types.completion_usage import CompletionTokensDetails
    usage = CompletionUsage(prompt_tokens=900, completion_tokens=out, total_tokens=900 + out,
                            completion_tokens_details=CompletionTokensDetails(reasoning_tokens=reasoning))
    return LengthFinishReasonError(completion=ChatCompletion.model_construct(model="gpt-5-mini", usage=usage))


def test_a_length_limit_failure_logs_and_records_its_reasoning_tokens(caplog):
    with caplog.at_level("ERROR"):
        (p, history), m = run([_length_error(), (good(), USAGE)])
    assert m.call_count == 2 and len(history) == 2
    assert history[0]["failed"] == "length" and history[0]["tokens_reasoning"] == 16000
    assert history[0]["tokens_out"] == 16000 and history[0]["model"] == "gpt-5-mini"
    assert "16000 of 16000 output tokens were reasoning" in caplog.text
    assert any(n == "planner re-asked because: the previous planner call failed" for n in p["capacity_fixes"])


def test_an_unreadable_content_data_json_logs_its_start_and_the_text_near_the_error(caplog):
    bad_json = '{"kpi_labels": ["ARR", "NRR"], "kpi_values": ["$48.2M" "114%"]}'
    with caplog.at_level("WARNING"):
        state = scp._planner_slide_to_state(0, _planner_slide(bad_json))
    assert state["components"][0]["content_data"] == {}
    assert "invalid content_data_json for component 'k'" in caplog.text
    assert '{"kpi_labels": ["ARR", "NRR"]' in caplog.text and "chars)" in caplog.text and "near" in caplog.text
