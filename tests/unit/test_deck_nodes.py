"""Tests for slide_router and deck_assembler nodes."""

from unittest.mock import patch

from src.agents.deck_nodes import (
    _extract_slide_block,
    _extract_theme,
    assemble_deck_xml,
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


def test_assemble_deck_xml_strips_contamination():
    theme = '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />'
    dirty_1 = f'{theme}\n<Slide><VStack w="1280" h="720"><Text color="#FF0000">a<br/>b</Text></VStack></Slide>'
    dirty_2 = f'{theme}\n<Slide><VStack w="1280" h="720" spacing="8"><Text>Slide 2</Text></VStack></Slide>'

    combined = assemble_deck_xml([dirty_1, dirty_2], theme)

    assert "<br" not in combined
    assert "#FF0000" not in combined
    assert "spacing=" not in combined
    assert combined.count("<Theme") == 1
    assert combined.lstrip().startswith("<Theme")
    assert combined.count("<Slide>") == 2


def test_assemble_deck_xml_no_slide_block():
    assert assemble_deck_xml(["<Theme />", "no slide here"], "<Theme />") == ""


def test_slide_router_saves_normalized_xml():
    """slide_router must persist the validator's cleaned XML, not the raw output."""
    state = initial_state(run_id="sr-norm", raw_request="test")
    state["current_slide_index"] = 0
    state["current_xml"] = '<Slide><VStack w="1280" h="720"><Text>a<br/>b</Text></VStack></Slide>'
    state["normalize_result"] = {
        "cleaned_xml": '<Slide><VStack w="1280" h="720"><Text>ab</Text></VStack></Slide>\n',
    }

    result = slide_router_node(state)

    saved = result["completed_slides"][0]["xml"]
    assert "<br" not in saved
    assert saved == state["normalize_result"]["cleaned_xml"]


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
    # no normalize_result in state → falls back to raw current_xml
    assert result["completed_slides"][0]["xml"] == _SLIDE_XML_1
    assert result["current_slide_index"] == 1
    assert result["current_xml"] == ""
    assert result["retry_count"] == 0
    assert result["retry_tier"] == 0
    assert result["compile_result"] is None
    assert result["critic_result"] is None
    assert result["slide_critic_results"] == [{"passed": True, "issues": []}]


def test_slide_router_captures_failing_critic_verdict():
    state = initial_state(run_id="sr2", raw_request="test")
    state["current_xml"] = _SLIDE_XML_1
    state["critic_result"] = {"passed": False, "issues": [{"severity": "high"}]}

    result = slide_router_node(state)
    assert result["slide_critic_results"][0]["passed"] is False


def test_slide_router_defaults_verdict_when_critic_off():
    state = initial_state(run_id="sr3", raw_request="test")
    state["current_xml"] = _SLIDE_XML_1
    # critic never ran → critic_result stays None
    result = slide_router_node(state)
    assert result["slide_critic_results"] == [{"passed": True}]


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


@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_normalizes_before_compile(mock_compile):
    """A per-slide <br/> that reached completed_slides must be stripped before the deck compile."""
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/deck.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="da-norm", raw_request="test")
    state["completed_slides"] = [
        {"slide_index": 0, "xml": _SLIDE_XML_1},
        {"slide_index": 1, "xml": _SLIDE_XML_2.replace("Slide 2", "Slide<br/>2")},
    ]

    deck_assembler_node(state)

    compiled_xml = mock_compile.call_args[0][0]
    assert "<br" not in compiled_xml


@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_dedupes_theme_inside_slide(mock_compile):
    """LLM sometimes emits <Theme> as the first child of <Slide>; assembler must strip it."""
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/deck.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    theme = '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />'
    slide_with_nested = (
        f'<Slide>{theme}<VStack w="1280" h="720"><Text>Slide 1</Text></VStack></Slide>'
    )
    slide_paired_theme = (
        '<Theme surface="F7F9FC" accent="2563EB"></Theme>\n'
        '<Slide><VStack w="1280" h="720"><Text>Slide 2</Text></VStack></Slide>'
    )

    state = initial_state(run_id="da4", raw_request="test")
    state["resolved_theme"] = {"element": theme}
    state["completed_slides"] = [
        {"slide_index": 0, "xml": slide_with_nested},
        {"slide_index": 1, "xml": slide_paired_theme},
    ]

    result = deck_assembler_node(state)
    compiled_xml = mock_compile.call_args[0][0]
    assert compiled_xml.count("<Theme") == 1
    assert compiled_xml.startswith("<Theme")
    assert compiled_xml.count("<Slide>") == 2
    assert "Slide 1" in compiled_xml and "Slide 2" in compiled_xml


@patch("src.agents.deck_nodes._call_deck_repair_llm")
@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_repairs_retryable_compile_failure(mock_compile, mock_repair):
    good_slide = '<Slide><VStack w="1280" h="720"><Text>Fixed</Text></VStack></Slide>'
    mock_repair.return_value = (
        '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />\n' + good_slide
    )
    mock_compile.side_effect = [
        {"ok": False, "pptx_path": None,
         "diagnostics": [{"type": "UNKNOWN_TAG", "message": "div"}],
         "warnings": [], "retryable": True},
        {"ok": True, "pptx_path": "/tmp/deck.pptx",
         "diagnostics": [], "warnings": [], "retryable": False},
    ]

    state = initial_state(run_id="da-repair", raw_request="test")
    state["completed_slides"] = [
        {"slide_index": 0, "xml": _SLIDE_XML_1},
        {"slide_index": 1, "xml": _SLIDE_XML_2},
    ]

    result = deck_assembler_node(state)

    assert mock_repair.call_count == 1
    assert result["compile_result"]["ok"] is True
    assert result["pptx_path"] == "/tmp/deck.pptx"
    assert "Fixed" in result["current_xml"]


@patch("src.agents.deck_nodes._call_deck_repair_llm")
@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_gives_up_after_two_repairs(mock_compile, mock_repair):
    mock_repair.return_value = "<Theme />\n<Slide><VStack w='1280' h='720'/></Slide>"
    mock_compile.return_value = {
        "ok": False, "pptx_path": None,
        "diagnostics": [{"type": "X", "message": "y"}],
        "warnings": [], "retryable": True,
    }

    state = initial_state(run_id="da-giveup", raw_request="test")
    state["completed_slides"] = [{"slide_index": 0, "xml": _SLIDE_XML_1}]

    result = deck_assembler_node(state)
    assert mock_repair.call_count == 2
    assert result["compile_result"]["ok"] is False


@patch("src.agents.deck_nodes._call_deck_repair_llm")
@patch("src.agents.deck_nodes.compile_xml")
def test_deck_assembler_skips_repair_when_not_retryable(mock_compile, mock_repair):
    mock_compile.return_value = {
        "ok": False, "pptx_path": None, "diagnostics": [],
        "warnings": [], "retryable": False,
    }
    state = initial_state(run_id="da-noretry", raw_request="test")
    state["completed_slides"] = [{"slide_index": 0, "xml": _SLIDE_XML_1}]

    deck_assembler_node(state)
    assert mock_repair.call_count == 0


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
