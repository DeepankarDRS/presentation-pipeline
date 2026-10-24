"""Component-choice fixes of 2026-10-15 (docs/eval/structure-loss/README.md, "Changes"): rule K4 (many short cards on
a full slide -> list), direction lines out of the slide content, a tolerant content_data_json read, and card lines
read within one message."""

import json

import pytest

from src.agents.planning.plan_checks import (
    CARDS_TO_LIST, CARD_LINES_DROPPED, DENSE_REST_WORDS, cards_to_list, find_problems, finalize_plan,
)
from src.agents.planning.slide_component_planner import brief_text_for, parse_content_data
from src.agents.planning.written_lines import content_line_list, settle_direction_lines, visual_directions


def comp(cid, kind, data, weight="peer"):
    return {"component_id": cid, "kind": kind, "count": 1, "content_summary": "", "weight": weight,
            "content_data": data}


def plan(components, slide_type="data"):
    return {"slide_index": 1, "slide_type": slide_type, "components": components}


CITIES = ["Bengaluru", "Hyderabad", "Chennai", "Jaipur", "Surat", "Nashik", "Mumbai", "Delhi", "Pune"]


def city_cards():
    cards = [{"title": "Bengaluru", "body": "Best large city at around 0.45x ROAS, still below target", "tone": "watch"}]
    cards += [{"title": c, "body": "Needs immediate review", "tone": "bad", "icon": "map-pin"} for c in CITIES[1:]]
    return comp("city_cards", "card_grid", {"card_layout": "grid", "cards": cards})


def full_rest():
    """The rest of the agency Keyword & City slide: a 3 x 6 table, two long bullets, three paragraphs."""
    return [
        comp("match_table", "table", {"table_columns": ["Match", "Spend", "Rev", "ROAS", "CPC", "CVR"],
                                      "table_rows": [["Phrase", "₹45.5L", "₹14.6L", "0.32x", "₹62.0", "8.6%"],
                                                     ["Exact", "₹21.3L", "₹8.8L", "0.41x", "₹59.5", "10.9%"],
                                                     ["Broad", "₹1.9L", "₹0.4L", "0.23x", "₹64.7", "6.2%"]]}),
        comp("terms", "bullet_list", {"bullets": [
            "Winners: brand phrase, brand exact, paneer makhani, curry, shahi paneer gravy",
            "Weak terms: butter chicken phrase, instant food phrase, ready to cook paneer phrase, mix phrase"]}),
        comp("reco", "narrative", {"text": "Scale exact winners, reduce phrase and broad leakage, and create strict "
                                           "budgets for competitor and generic discovery terms."}),
        comp("threshold", "narrative", {"text": "No major high-spend city crossed 0.5x ROAS."}),
        comp("city_reco", "narrative", {"text": "Reallocate budget based on city-level ROAS, SKU availability, "
                                                "delivery strength, inventory depth and organic demand."}),
    ]


# ── K4 ──────────────────────────────────────────────────────────────────────

def test_k4_many_short_cards_on_a_full_slide_become_one_list_word_for_word():
    p = plan([comp("slide_title", "title", {"title": "Exact match wins"}), city_cards(), *full_rest()])
    notes = finalize_plan(p, "")
    lst = next(c for c in p["components"] if c["component_id"] == "city_cards")
    assert lst["kind"] == "bullet_list"
    assert lst["content_data"]["bullets"] == [
        "Bengaluru: Best large city at around 0.45x ROAS, still below target",
        "Hyderabad, Chennai, Jaipur, Surat, Nashik, Mumbai, Delhi, Pune: Needs immediate review",
    ]
    assert lst["items"] == 2 and "card" not in lst["design_hint"]
    assert CARDS_TO_LIST in [f["code"] for f in p["plan_flags"]]
    assert any("city_cards: card_grid of 9 short cards" in n for n in notes)


def test_k4_keeps_cards_on_a_slide_with_room():
    """XTSY impact slide: seven title-only cards and one line beside them - the cards fill the slide."""
    cards = [{"title": t} for t in ["Visibility ↑", "Search Share ↑", "Placement ↑", "New Consumers ↑",
                                    "Repeat Rate ↑", "Market Share ↑", "Sales Velocity ↑"]]
    p = plan([comp("impact", "card_grid", {"card_layout": "grid", "cards": cards}),
              comp("msg", "narrative", {"text": "Intelligence and automation create a scalable growth engine."})])
    assert cards_to_list(p) == []
    assert p["components"][0]["kind"] == "card_grid"


def test_k4_keeps_cards_with_lines_steps_and_small_grids_on_a_full_slide():
    long_cards = comp("pillars", "card_grid", {"card_layout": "grid", "cards": [
        {"title": f"Pillar {i}", "body": "A line of detail that runs to nine words in all"} for i in range(6)]})
    steps = comp("plan", "card_grid", {"card_layout": "steps", "cards": [{"title": f"Step {i}"} for i in range(6)]})
    few = comp("few", "card_grid", {"card_layout": "grid", "cards": [{"title": c} for c in CITIES[:5]]})
    for grid in (long_cards, steps, few):
        p = plan([grid, *full_rest()])
        assert cards_to_list(p) == [], grid["component_id"]


def test_k4_threshold_counts_only_the_other_components():
    rest = [comp("note", "narrative", {"text": " ".join(["word"] * (DENSE_REST_WORDS - 1))})]
    assert cards_to_list(plan([city_cards(), *rest])) == []
    rest = [comp("note", "narrative", {"text": " ".join(["word"] * DENSE_REST_WORDS)})]
    assert cards_to_list(plan([city_cards(), *rest]))


# ── direction lines ─────────────────────────────────────────────────────────

def test_presenter_notes_leave_key_messages_and_show_labels_become_content_labels():
    slide = {"slide_index": 5, "key_messages": [
        "Speaker Notes: Explain each pillar in one line",
        "Talking points - lead with the CPC gap",
        "Show Benefits: Faster optimization cycles; Reduced manual intervention",
        "Show capabilities: TRACKING: Share of Search; Share of Shelf",
        "Show: Category growth drivers, Consumer demand moments",
        "Highlight: Automation allows brands to react in hours instead of weeks.",
        "Note: Some pivot metrics were recalculated from raw data.",
    ]}
    notes = settle_direction_lines(slide)
    assert len(notes) == 2
    assert slide["key_messages"] == [
        "Benefits: Faster optimization cycles; Reduced manual intervention",
        "Capabilities: TRACKING: Share of Search; Share of Shelf",
        "Show: Category growth drivers, Consumer demand moments",
        "Highlight: Automation allows brands to react in hours instead of weeks.",
        "Note: Some pivot metrics were recalculated from raw data.",
    ]


def test_show_how_and_plain_sentences_are_not_labels():
    slide = {"key_messages": ["Show how the funnel narrows: 1,200 leads, 300 trials", "Show the gap: ₹31.1 vs ₹10.7"]}
    settle_direction_lines(slide)
    assert slide["key_messages"] == ["Show how the funnel narrows: 1,200 leads, 300 trials",
                                     "Show the gap: ₹31.1 vs ₹10.7"]


def test_visual_suggestion_and_bare_show_are_directions_not_content():
    slide = {"key_messages": [
        "Visual Suggestion: Six-icon row, one icon per pillar",
        "Show: Category growth drivers, Consumer demand moments, Impulse purchase behaviour",
        "Speaker Notes: End with confidence.",
        "Include: Pre-workout consumption; Gaming sessions; Late-night work",
    ]}
    directions = visual_directions(slide)
    assert directions == ["Six-icon row, one icon per pillar",
                          "Category growth drivers, Consumer demand moments, Impulse purchase behaviour"]
    assert content_line_list(slide, directions) == ["Include: Pre-workout consumption; Gaming sessions; Late-night work"]


# ── content_data_json read ──────────────────────────────────────────────────

def test_content_data_with_the_field_name_glued_in_front_is_read():
    text = 'content_data_json\': {"title": "Growth Opportunities", "subtitle": "PLATFORM OPPS"}'
    assert parse_content_data(text) == {"title": "Growth Opportunities", "subtitle": "PLATFORM OPPS"}
    assert parse_content_data('{"text": "plain"}') == {"text": "plain"}


@pytest.mark.parametrize("text", ["{", "not json", '["a", "b"]'])
def test_unreadable_content_data_still_raises(text):
    with pytest.raises((json.JSONDecodeError, TypeError)):
        parse_content_data(text)


# ── card lines within one message ───────────────────────────────────────────

def test_card_line_check_does_not_read_across_messages_or_sentences():
    slide = {"key_messages": [
        "Include: Pre-workout consumption; Gaming sessions; Instant energy requirements",
        "Key Insight: Energy drinks have one of the strongest instant-need consumption behaviors",
        "6 Pillars: Raw-data reporting and weekly diagnostics. Intent-layer campaign structure. Break-even CPC bidding.",
    ]}
    brief = brief_text_for(slide, None)
    grid = comp("cards", "card_grid", {"card_layout": "grid", "cards": [
        {"title": "Instant energy requirements"}, {"title": "Raw-data reporting and weekly diagnostics"}]})
    assert not [p for p in find_problems(plan([grid]), brief) if p["code"] == CARD_LINES_DROPPED]


def test_card_line_check_still_finds_a_dropped_line():
    slide = {"key_messages": ["Late fixes (after 20:00): urgent edits from mobile, the fastest-growing moment"]}
    grid = comp("cards", "card_grid", {"card_layout": "grid", "cards": [{"title": "Late fixes"}]})
    assert [p for p in find_problems(plan([grid]), brief_text_for(slide, None)) if p["code"] == CARD_LINES_DROPPED]
