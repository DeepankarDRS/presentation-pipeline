"""The planner's re-ask is for failures that hold for any brief (2026-11-17, user).

A re-ask fires only when the call failed (an error, the output limit, an answer the schema rejects: an unknown kind,
unparsable JSON), the plan has no components, or a component or the whole plan holds no content. Wording heuristics
drawn from past decks (instruction text, a sentence as a tile value, a tile cut from a sentence, a dropped card line,
a missing item, a shape misfit) never re-ask: code fixes or flags them in `finalize_plan`."""

from unittest.mock import patch

from src.agents import slide_component_planner as scp
from src.agents.plan_checks import PLAN_EMPTY, REASK_CODES, find_problems, reask_context
from src.compiler.normalizer import _restore_legends

USAGE = {"tokens_in": 100, "tokens_out": 10, "tokens_reasoning": 3, "tokens_cached": 0, "model": "m"}


def comp(cid, kind, data, weight="peer"):
    return {"component_id": cid, "kind": kind, "count": 1, "content_summary": "", "weight": weight,
            "content_data": data}


def plan(components, slide_type="data"):
    return {"slide_index": 0, "slide_type": slide_type, "components": components}


SLIDE = {"slide_index": 1, "slide_title": "A strong year", "label": "", "subtitle": "",
         "key_messages": ["Sales reached $50M, up 9% from $46M.", "returning buyers placed 62% of orders"]}
OUTLINE = {"core_hook": "h", "slides": [SLIDE]}


def run(side_effects):
    with patch.object(scp, "plan_single_slide", side_effect=side_effects) as m:
        result = scp.plan_with_reask(SLIDE, outline_plan=OUTLINE)
    return result, m


def tiles():
    return plan([comp("k", "kpi_row", {"kpi_labels": ["Sales"], "kpi_values": ["$50M"]}, "hero")])


# ── what re-asks ────────────────────────────────────────────────────────────

def test_only_emptiness_is_a_reask_code():
    assert REASK_CODES == (PLAN_EMPTY,)


def test_no_components_an_empty_component_or_no_content_re_ask():
    assert [p["code"] for p in find_problems(plan([]))] == [PLAN_EMPTY]
    assert [p["code"] for p in find_problems(plan([comp("k", "kpi_row", {})]))] == [PLAN_EMPTY]
    assert [p["code"] for p in find_problems(plan([comp("l", "layer", {})]))] == [PLAN_EMPTY]   # nothing holds content
    assert find_problems(plan([comp("c", "caption", {}), *tiles()["components"]])) == []    # an empty caption is dropped


def test_a_failed_call_re_asks_and_plans_again():
    (p, history), m = run([RuntimeError("schema rejected the answer"), (tiles(), USAGE)])
    assert m.call_count == 2 and p["components"][0]["kind"] == "kpi_row"
    ctx = m.call_args_list[1].kwargs["repair_context"]
    assert ctx["directive"].startswith("Plan this slide again") and ctx["previous_plan"] == ""


def test_an_empty_plan_re_asks_and_the_filled_one_wins():
    (p, history), m = run([(plan([comp("k", "kpi_row", {})]), USAGE), (tiles(), USAGE)])
    assert m.call_count == 2 and history[1]["reask_outcome"]["kept"] == "reask"
    assert p["components"][0]["content_data"]["kpi_values"] == ["$50M"]


def test_two_failed_calls_give_the_fallback_list():
    (p, _), _ = run([RuntimeError("x"), RuntimeError("y")])
    assert p["plan_source"] == "fallback" and p["components"][0]["kind"] == "bullet_list"


# ── what never re-asks ──────────────────────────────────────────────────────

def test_content_judgements_never_re_ask():
    sentence_value = comp("a", "kpi_row", {"kpi_labels": ["Setup"], "kpi_values": ["it fell to 15 min a week"]})
    fragment = comp("b", "kpi_row", {"kpi_labels": ["returning buyers placed"], "kpi_values": ["62%"],
                                     "kpi_deltas": ["of orders"]})
    direction = comp("c", "narrative", {"text": "Walk the audience through the three phases"})
    title_only = comp("d", "card_grid", {"cards": [{"title": "Late fixes"}]})
    p = plan([sentence_value, fragment, direction, title_only])
    (out, history), m = run([(p, USAGE)])
    assert m.call_count == 1 and len(history) == 1
    assert find_problems(p, "returning buyers placed 62% of orders\nLate fixes: urgent edits go to the on-call editor") == []


def test_reask_context_names_what_was_empty():
    ctx = reask_context([{"code": PLAN_EMPTY, "component_id": "k", "detail": "kpi_row 'k' has no content"}])
    assert ctx["failed_kinds"] == ["kpi_row"] and ctx["errors"] == ["kpi_row 'k' has no content"]


# ── charts: a pie or doughnut is always told apart by its legend ────────────

def test_a_doughnut_with_its_legend_off_gets_it_back_even_when_its_names_are_on_the_slide():
    xml = ('<Slide><Text>Stores lead; online grows</Text><Chart chartType="doughnut" showLegend="false">'
           '<ChartSeries name="Mix"><ChartDataPoint label="Stores" value="63"/><ChartDataPoint label="Online" '
           'value="29"/></ChartSeries></Chart></Slide>')
    out, restored = _restore_legends(xml)
    assert 'showLegend="true"' in out and restored == ["Stores", "Online"]


def test_a_one_series_bar_chart_keeps_its_legend_off():
    xml = ('<Slide><Chart chartType="bar" showLegend="false"><ChartSeries name="Sales">'
           '<ChartDataPoint label="Q1" value="4"/></ChartSeries></Chart></Slide>')
    assert _restore_legends(xml) == (xml, [])


# ── derived KPI labels are listed for review (content policy: inferred / derived is flagged) ──

def test_a_kpi_label_the_brief_does_not_write_is_listed_for_review():
    from src.agents.written_lines import flag_written_labels
    brief = "ARR: $48.2M (+18% QoQ)\n62% of revenue comes from repeat customers, up from 41% a year ago"
    p = plan([comp("k", "kpi_row", {"kpi_labels": ["ARR", "Repeat-revenue share"], "kpi_values": ["$48.2M", "62%"]})])
    notes = flag_written_labels(p, brief)
    assert p["written_labels"] == ["Repeat-revenue share: 62%"] and len(notes) == 1


def test_labels_copied_from_the_brief_are_not_listed():
    from src.agents.written_lines import flag_written_labels
    p = plan([comp("k", "kpi_row", {"kpi_labels": ["Gross Margin", "CAC Payback"], "kpi_values": ["72.1%", "14 months"]})])
    assert flag_written_labels(p, "Gross Margin: 72.1% (-1.4 pts)\nCAC Payback: 14 months") == []
    assert "written_labels" not in p
