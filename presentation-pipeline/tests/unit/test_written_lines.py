"""Card lines the planner writes itself are flagged, never trusted (user decision 2026-09-29)."""

from src.agents.planning.written_lines import flag_written_lines, from_brief

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

from src.agents.planning.written_lines import content_lines, drop_visual_directions, visual_directions  # noqa: E402

COVER = {"key_messages": ["Prepared by our agency",
                          "Visual: Marketplace growth theme with FLIPCART and ZAROMA visual cues."]}


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


def test_a_visual_line_is_not_a_content_line():
    dirs = visual_directions(COVER)
    assert dirs == ["Marketplace growth theme with FLIPCART and ZAROMA visual cues."]
    assert content_line_list(COVER, dirs) == ["Prepared by our agency"]


def test_unlabelled_content_is_never_a_direction():
    slide = {"key_messages": ["Late fixes is the fastest-growing moment"]}
    plan = {"components": [{"kind": "narrative", "content_data": {"text": "Late fixes is the fastest-growing moment"}}]}
    dirs = visual_directions(slide)
    assert dirs == [] and drop_visual_directions(plan, dirs, content_lines(slide, dirs)) == []


# ── the outline copies a brief "Visual:" line without its label (XTSY 2026-10-20) ──

from src.agents.planning.written_lines import (brief_content, brief_instructions, content_line_list,  # noqa: E402
                                      copies_visual, settle_direction_lines)

XTSY_BRIEF = ("SLIDE 1  TITLE: Unlocking the Next Phase of Growth for XTSY on Quick Commerce  Visual: Quick Commerce "
              "ecosystem showing Zepto, Blinkit and Instamart connected to XTSY growth engine.  Key Message: Quick "
              "Commerce is becoming a primary consumption channel for impulse and instant-need beverage categories.  "
              "SLIDE 4  TITLE: Our 4-Phase Framework to Build Category Share  Visual: 4-stage growth roadmap  "
              "Phase 1: Foundation & Hygiene  SLIDE 5  Visual: Opportunity Matrix  Rows: Visibility Conversion")


def test_brief_instructions_keep_the_text_of_labelled_directions():
    assert brief_instructions(XTSY_BRIEF)["visuals"] == [
        "Quick Commerce ecosystem showing Zepto, Blinkit and Instamart connected to XTSY growth engine.",
        "4-stage growth roadmap", "Opportunity Matrix"]


def test_outline_copy_without_its_label_gets_the_label_back():
    ins = brief_instructions(XTSY_BRIEF)
    slide = {"key_messages": [
        "Quick Commerce is becoming a primary consumption channel for impulse and instant-need beverage categories.",
        "Quick Commerce ecosystem — Zepto, Blinkit and Instamart connected to XTSY growth engine.",
        "4-stage growth roadmap", "Opportunity Matrix"]}
    notes = settle_direction_lines(slide, ins, brief_content(XTSY_BRIEF, ins))
    assert len(notes) == 3
    dirs = visual_directions(slide)
    assert dirs == ["Quick Commerce ecosystem — Zepto, Blinkit and Instamart connected to XTSY growth engine.",
                    "4-stage growth roadmap", "Opportunity Matrix"]
    assert content_line_list(slide, dirs) == [slide["key_messages"][0]]


def test_a_content_line_that_only_mentions_the_direction_stays_content():
    ins = brief_instructions(XTSY_BRIEF)
    line = ("Zepto, Blinkit and Instamart together reach most urban energy-drink buyers within ten minutes, and each "
            "platform rewards visibility, availability and repeat purchase in its own way")
    assert not copies_visual(line, ins["visuals"])


def test_a_direction_copy_with_figures_stays_content():
    visuals = brief_instructions("Visual: bar chart of ROAS by city: Bengaluru 0.45x, Hyderabad 0.31x")["visuals"]
    assert not copies_visual("ROAS by city: Bengaluru 0.45x, Hyderabad 0.31x", visuals)
    assert copies_visual("4-stage growth roadmap", ["4-stage growth roadmap"])


def test_planner_prompt_gives_directions_apart_from_the_key_messages():
    from src.agents.planning.slide_component_planner import _jinja_env
    slide = {"slide_index": 0, "slide_title": "Unlocking growth", "narrative_role": "r",
             "key_messages": ["Quick Commerce is a primary consumption channel.",
                              "Visual: Quick Commerce ecosystem showing Zepto, Blinkit and Instamart"]}
    dirs = visual_directions(slide)
    text = _jinja_env.get_template("user.j2").render(
        content_field="content", slide=slide, content_messages=content_line_list(slide, dirs),
        visual_directions=dirs, core_hook="", deck_context=[], total_slides=1, deck_settings={}, constraints={})
    messages, direction = text.split("Visual direction from the brief", 1)
    assert "1. Quick Commerce is a primary consumption channel." in messages and "Zepto" not in messages
    assert "- Quick Commerce ecosystem showing Zepto, Blinkit and Instamart" in direction
    assert "visual_emphasis" not in text
