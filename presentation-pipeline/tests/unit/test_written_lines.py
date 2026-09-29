"""Card lines the planner writes itself are flagged, never trusted (user decision 2026-09-29)."""

from src.agents.written_lines import flag_written_lines, from_brief

BRIEF = "Consumption occasions: Pre-workout consumption, Gaming sessions, Late-night work/study. " \
        "Travel & commuting: energy on the go between meetings"


def _plan(*cards):
    return {"components": [{"kind": "card_grid", "content_data": {"card_layout": "grid", "cards": list(cards)}}]}


def test_line_copied_from_the_brief_is_not_flagged_even_if_marked_written():
    plan = _plan({"title": "Travel & commuting", "body": "Energy on the go between meetings", "body_source": "written"})
    assert flag_written_lines(plan, BRIEF) == []
    assert "written_lines" not in plan and "body_source" not in plan["components"][0]["content_data"]["cards"][0]


def test_line_not_in_the_brief_is_flagged_even_if_unmarked():
    """The XTSY Genspark line: invented, with no marker from the model."""
    line = "Long multiplayer sessions; habitual, repeat-heavy consumption."
    plan = _plan({"title": "Gaming sessions", "body": line})
    flag_written_lines(plan, BRIEF)
    assert plan["components"][0]["content_data"]["cards"][0]["body_source"] == "written"
    assert plan["written_lines"] == [line]


def test_written_line_with_a_number_is_removed():
    plan = _plan({"title": "Pre-workout consumption", "body": "Gym cohorts top up 5-7 AM before a session"})
    notes = flag_written_lines(plan, BRIEF)
    card = plan["components"][0]["content_data"]["cards"][0]
    assert "body" not in card and "written_lines" not in plan and "with a number" in notes[0]


def test_other_components_and_empty_cards_untouched():
    plan = {"components": [{"kind": "bullet_list", "content_data": {"bullets": ["made up"]}}]}
    assert flag_written_lines(plan, BRIEF) == [] and "written_lines" not in plan
    assert from_brief("", BRIEF)
