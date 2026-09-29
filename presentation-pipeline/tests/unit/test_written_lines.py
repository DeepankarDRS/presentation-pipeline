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


# ── design directions are not content (fix 6, CHEFFIN cover) ────────────────

from src.agents.written_lines import content_lines, drop_visual_directions, visual_directions  # noqa: E402

COVER = {"key_messages": ["Prepared by our agency",
                          "Visual: Marketplace growth theme with FLIPCART and ZAROMA visual cues."],
         "visual_emphasis": "Marketplace growth theme with FLIPCART and ZAROMA visual cues."}


def _cover_plan():
    return {"components": [
        {"kind": "caption", "component_id": "prep", "content_data": {"text": "Prepared by our agency"}},
        {"kind": "narrative", "component_id": "theme",
         "content_data": {"text": "Marketplace growth theme with FLIPCART and ZAROMA visual cues."}}]}


def test_visual_line_printed_as_a_card_is_dropped():
    plan = _cover_plan()
    dirs = visual_directions(COVER)
    notes = drop_visual_directions(plan, dirs, content_lines(COVER, dirs))
    assert [c["component_id"] for c in plan["components"]] == ["prep"] and "design direction" in notes[0]


def test_direction_copied_into_key_messages_without_label_still_counts():
    slide = {**COVER, "key_messages": ["Prepared by our agency", COVER["visual_emphasis"]]}
    plan = _cover_plan()
    dirs = visual_directions(slide)
    drop_visual_directions(plan, dirs, content_lines(slide, dirs))
    assert [c["component_id"] for c in plan["components"]] == ["prep"]


def test_content_that_is_also_in_the_visual_emphasis_is_kept():
    slide = {"key_messages": ["Late fixes is the fastest-growing moment", "Stand-up and review drive daily use"],
             "visual_emphasis": "Late fixes is the fastest-growing moment"}
    plan = {"components": [{"kind": "narrative", "content_data": {"text": "Stand-up and review drive daily use"}}]}
    dirs = visual_directions(slide)
    assert drop_visual_directions(plan, dirs, content_lines(slide, dirs)) == [] and len(plan["components"]) == 1


def test_emphasis_that_restates_content_never_drops_it():
    slide = {"key_messages": ["Late fixes is the fastest-growing moment"],
             "visual_emphasis": "Late fixes is the fastest-growing moment"}
    plan = {"components": [{"kind": "narrative", "content_data": {"text": "Late fixes is the fastest-growing moment"}}]}
    dirs = visual_directions(slide)
    assert dirs == [] and drop_visual_directions(plan, dirs, content_lines(slide, dirs)) == []
