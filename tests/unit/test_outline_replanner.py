"""Tests for the outline replanner — per-slide outline regeneration from feedback."""

from unittest.mock import MagicMock, patch

from src.agents.outline_planner_schema import OutlineSlide
from src.agents.outline_replanner import regenerate_outline_slide


def _make_structured_llm(output):
    structured = MagicMock()
    structured.invoke.return_value = output
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


@patch("src.agents.outline_replanner.get_llm")
def test_regenerate_outline_slide_preserves_slide_index(mock_get_llm):
    output = OutlineSlide(
        slide_index=0,
        slide_title="Competitive Landscape",
        section="",
        narrative_role="Addresses the competitive pressure half of the core hook.",
        key_messages=["New entrants are undercutting on price in the mid-market segment."],
        visual_emphasis="side-by-side comparison",
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    original_slide = {
        "slide_index": 2,
        "slide_title": "Fable 5.1 Revenue Performance",
        "section": "",
        "narrative_role": "Establishes traction.",
        "key_messages": ["Fable 5.1 generated $38M in revenue last year."],
        "visual_emphasis": "one dominant number",
    }

    updated = regenerate_outline_slide(
        original_slide, core_hook="Test hook", feedback="Cover competitive pressure instead.",
    )

    assert updated["slide_index"] == 2
    assert updated["slide_title"] == "Competitive Landscape"
    assert updated["key_messages"] == ["New entrants are undercutting on price in the mid-market segment."]


@patch("src.agents.outline_replanner.get_llm")
def test_regenerate_outline_slide_defaults_index_when_missing(mock_get_llm):
    output = OutlineSlide(
        slide_index=5,
        slide_title="Revised Title",
        section="",
        narrative_role="Role",
        key_messages=["A message"],
        visual_emphasis="big statement",
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    updated = regenerate_outline_slide({}, core_hook="hook", feedback="make it punchier")

    assert updated["slide_index"] == 0
