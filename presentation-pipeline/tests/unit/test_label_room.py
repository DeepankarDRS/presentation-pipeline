"""Plan check on each diagram label's longest word, measured in px (user decision 2026-10-21; LLM-free).

Rooms are the node break map's (docs/eval/node-break-map/README.md §3 item 2); words are measured by POM's own
text measurement in the deck font (src/node/break-map.js measure), so these tests need node.
"""

import shutil

import pytest

from src.agents.label_room import arrow_room, enforce_label_room, measure_words, pyramid_rooms

needs_node = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


def _arrow(steps: list[str], direction: str = "horizontal") -> dict:
    return {"component_id": "steps", "kind": "process_arrow",
            "content_data": {"direction": direction, "process_steps": steps}}


def test_a_chevron_label_room_shrinks_with_the_steps_across_the_band():
    # the map's band row of one long word ("Reconciliation", 97 px at 14 px bold) holds 7 chevrons, not 8
    assert arrow_room(7) > 97.5 > arrow_room(8)
    assert pyramid_rooms(4, "up")[0] < pyramid_rooms(4, "up")[-1]
    assert pyramid_rooms(4, "down") == pyramid_rooms(4, "up")[::-1]


@needs_node
def test_words_are_measured_in_the_deck_font_at_their_size():
    (word, w), = measure_words([("Account reconciliation", 14, True)])
    assert word == "reconciliation" and 85 < w < 100


@needs_node
def test_a_row_whose_long_word_does_not_fit_across_turns_vertical_with_every_word():
    steps = ["Plan", "Reconciliation", "Build", "Test", "Launch", "Scale", "Audit", "Train"]
    comp = _arrow(list(steps))
    notes = enforce_label_room([comp])
    assert comp["kind"] == "process_arrow" and comp["content_data"]["direction"] == "vertical"
    assert comp["content_data"]["process_steps"] == steps   # nothing dropped or shortened
    assert len(notes) == 1 and "Reconciliation" in notes[0] and "-> vertical" in notes[0]


@needs_node
def test_a_row_past_the_vertical_count_too_becomes_card_steps_in_order():
    steps = ["Plan", "Reconciliation", "Build", "Test", "Launch", "Scale", "Audit", "Train", "Hire", "Grow"]
    comp = _arrow(list(steps))
    enforce_label_room([comp])
    assert comp["kind"] == "card_grid" and [c["title"] for c in comp["content_data"]["cards"]] == steps


@needs_node
def test_short_labels_and_a_matrix_are_left_as_planned():
    row = _arrow(["Plan", "Build", "Test"])
    matrix = {"component_id": "map", "kind": "matrix",
              "content_data": {"matrix_items": [{"label": "Cost", "x": 0.2, "y": 0.8}, {"label": "Reach", "x": 0.7, "y": 0.3}]}}
    assert enforce_label_room([row, matrix]) == []
    assert row["content_data"]["direction"] == "horizontal" and matrix["kind"] == "matrix"


@needs_node
def test_a_pyramid_whose_top_band_cannot_hold_its_word_becomes_card_steps():
    levels = ["Profitability", "Operations", "People", "Systems", "Data"]
    comp = {"component_id": "tiers", "kind": "pyramid", "content_data": {"direction": "up", "pyramid_levels": list(levels)}}
    notes = enforce_label_room([comp])
    assert comp["kind"] == "card_grid" and [c["title"] for c in comp["content_data"]["cards"]] == levels
    assert "Profitability" in notes[0]
