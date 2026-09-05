"""Tests for slide_router and deck_assembler nodes."""

from unittest.mock import patch

from src.agents.deck_nodes import (
    _extract_slide_block,
    _extract_theme,
    deck_assembler_node,
    slide_router_node,
)
from src.state import initial_state


_SLIDE_XML_1 = (
    '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n'
    '<Slide><VStack w="1280" h="720"><Text>Slide 1</Text></VStack></Slide>'
)
_SLIDE_XML_2 = (
    '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n'
    '<Slide><VStack w="1280" h="720"><Text>Slide 2</Text></VStack></Slide>'
)


def test_extract_theme():
    theme = _extract_theme(_SLIDE_XML_1)
    assert theme.startswith("<Theme")
    assert 'surface="F7F9FC"' in theme


def test_extract_slide_block():
    block = _extract_slide_block(_SLIDE_XML_1)
    assert block.startswith("<Slide>")
    assert block.endswith("</Slide>")
    assert "Slide 1" in block


def test_slide_router_saves_and_advances():
    state = initial_state(run_id="sr1", raw_request="test")
    state["current_slide_index"] = 0
    state["current_xml"] = _SLIDE_XML_1
    state["compile_result"] = {"ok": True}
    state["critic_result"] = {"passed": True, "issues": []}
    state["retry_count"] = 2
    state["retry_tier"] = 1

    result = slide_router_node(state)

    assert len(result["completed_slides"]) == 1
    assert result["completed_slides"][0]["slide_index"] == 0
    assert result["completed_slides"][0]["xml"] == _SLIDE_XML_1
    assert result["current_slide_index"] == 1
    assert result["current_xml"] == ""
    assert result["retry_count"] == 0
    assert result["retry_tier"] == 0
    assert result["compile_result"] is None
    assert result["critic_result"] is None


@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_combines_slides(mock_compile):
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/deck.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="da1", raw_request="test")
    state["completed_slides"] = [
        {"slide_index": 0, "xml": _SLIDE_XML_1},
        {"slide_index": 1, "xml": _SLIDE_XML_2},
    ]

    result = deck_assembler_node(state)

    assert result["compile_result"]["ok"] is True
    assert result["pptx_path"] == "/tmp/deck.pptx"
    assert "<Slide>" in result["current_xml"]
    assert "Slide 1" in result["current_xml"]
    assert "Slide 2" in result["current_xml"]
    assert result["current_xml"].count("<Theme") == 1

    compiled_xml = mock_compile.call_args[0][0]
    assert compiled_xml.count("<Slide>") == 2
    assert compiled_xml.count("<Theme") == 1


def test_deck_assembler_no_slides():
    state = initial_state(run_id="da2", raw_request="test")
    state["completed_slides"] = []

    result = deck_assembler_node(state)
    assert result["compile_result"]["ok"] is False


@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_sorts_by_index(mock_compile):
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/deck.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="da3", raw_request="test")
    state["completed_slides"] = [
        {"slide_index": 1, "xml": _SLIDE_XML_2},
        {"slide_index": 0, "xml": _SLIDE_XML_1},
    ]

    result = deck_assembler_node(state)
    compiled_xml = mock_compile.call_args[0][0]
    idx1 = compiled_xml.index("Slide 1")
    idx2 = compiled_xml.index("Slide 2")
    assert idx1 < idx2
