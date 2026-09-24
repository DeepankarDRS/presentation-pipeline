"""Content model: nodes.yaml `children` is the only authority on nesting."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest

from src.agents.validator import validator_node
from src.compiler.content_model import (
    TEXT_ONLY, content_model, find_violations, flatten_text_containers,
)
from src.compiler.normalizer import normalize_xml
from src.state import initial_state

_ROOT = Path(__file__).resolve().parents[2]


def _slide(body: str) -> str:
    return f'<Slide><VStack w="1280" h="720" padding="36">{body}</VStack></Slide>'


# The exact regression from 2026-09-23 (platform ROAS table with logo icons).
TD_HSTACK = _slide(
    '<Table defaultRowHeight="54"><Col /><Col />'
    '<Tr><Td bold="true">PLATFORM</Td><Td bold="true">ROAS</Td></Tr>'
    '<Tr><Td><HStack gap="8" alignItems="center"><Icon name="store" size="22" color="C62828" />'
    '<Text fontSize="14" color="$textMain">ZAROMA</Text></HStack></Td><Td>0.32x</Td></Tr>'
    '</Table>'
)


def test_model_comes_from_nodes_yaml():
    m = content_model()
    assert m["Tr"] == {"Td"}
    assert m["Table"] == {"Col", "Tr"}
    assert m["Icon"] == frozenset()
    assert m["VStack"] is None  # any child
    for parent in TEXT_ONLY:
        assert "HStack" not in m[parent] and "Icon" not in m[parent]


@pytest.mark.parametrize("body,parent,child", [
    ('<Table><Tr><Td><HStack><Text>x</Text></HStack></Td></Tr></Table>', "Td", "HStack"),
    ('<Table><Tr><Td><Icon name="zap" /></Td></Tr></Table>', "Td", "Icon"),
    ('<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>', "Td", "Chart"),
    ('<Ul><Li><Icon name="zap" /> Fast</Li></Ul>', "Li", "Icon"),
    ('<Ul><Li><VStack><Text>x</Text></VStack></Li></Ul>', "Li", "VStack"),
    ('<Text>a<Icon name="zap" /></Text>', "Text", "Icon"),
    ('<Shape shapeType="rect"><Text>x</Text></Shape>', "Shape", "Text"),
    ('<Table><Td>x</Td></Table>', "Table", "Td"),
    ('<Ul><Text>x</Text></Ul>', "Ul", "Text"),
])
def test_invalid_child_detected(body, parent, child):
    issues = find_violations(_slide(body))
    assert [(i["parent"], i["child"]) for i in issues] == [(parent, child)]
    assert issues[0]["code"] == "INVALID_CHILD"
    assert issues[0]["auto_fixed"] is False


@pytest.mark.parametrize("body", [
    '<Table><Col /><Tr><Td>Plain <B>bold</B> <Span color="$accent">x</Span></Td></Tr></Table>',
    '<Ul><Li>Item <Span color="$accent">hot</Span></Li></Ul>',
    '<Text>$84<B><Span fontSize="20">M</Span></B></Text>',
    '<HStack gap="8"><Icon name="zap" size="20" /><Text>label</Text></HStack>',
    '<Svg w="40" h="40"><svg viewBox="0 0 10 10"><rect width="10" height="10" /></svg></Svg>',
])
def test_valid_nesting_passes(body):
    assert find_violations(_slide(body)) == []


def test_knowledge_examples_have_no_violations():
    """Guards against false positives: every example slide we teach must pass."""
    for path in (_ROOT / "src" / "knowledge").rglob("*.yaml"):
        for slide in re.findall(r"<Slide>.*?</Slide>", path.read_text(encoding="utf-8"), re.DOTALL):
            try:
                ET.fromstring(f"<r>{slide}</r>")
            except ET.ParseError:
                continue  # template fragments with placeholders
            assert find_violations(slide) == [], f"{path.name}: {find_violations(slide)}"


def test_flatten_fixes_regression_case():
    fixed, n = flatten_text_containers(TD_HSTACK)
    assert n == 1
    assert "<Td>ZAROMA</Td>" in fixed
    assert "<Icon" not in fixed
    assert find_violations(fixed) == []


def test_flatten_escapes_and_handles_li():
    fixed, n = flatten_text_containers('<Ul><Li><Icon name="zap" /> Fast &amp; safe</Li></Ul>')
    assert n == 1 and "<Li>Fast &amp; safe</Li>" in fixed


def test_flatten_leaves_inline_only_and_unsafe_alone():
    inline = '<Table><Tr><Td>Plain <B>bold</B></Td></Tr></Table>'
    unsafe = '<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>'
    assert flatten_text_containers(inline) == (inline, 0)
    assert flatten_text_containers(unsafe) == (unsafe, 0)


def test_normalizer_auto_flattens():
    result = normalize_xml(TD_HSTACK)
    assert "TEXT_CONTAINER_FLATTENED" in {i["code"] for i in result["issues"]}
    assert find_violations(result["cleaned_xml"]) == []


@patch("src.agents.validator.compile_xml")
@patch("src.agents.validator.validate_xml")
def test_validator_blocks_before_parsexml(mock_validate, mock_compile):
    state = initial_state(run_id="nest1", raw_request="test")
    state["current_xml"] = _slide(
        '<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>'
    )
    result = validator_node(state)
    mock_validate.assert_not_called()
    mock_compile.assert_not_called()
    assert result["compile_result"]["ok"] is False
    assert result["compile_result"]["retryable"] is True
    assert result["compile_result"]["diagnostics"][0]["type"] == "INVALID_CHILD"
    assert any(i["code"] == "INVALID_CHILD" for i in result["normalize_result"]["issues"])


_TD_CHART = _slide('<Table><Tr><Td><Chart chartType="bar" w="80" h="32" /></Td></Tr></Table>')


def test_normalizer_reports_unfixable_nesting_as_blocking():
    result = normalize_xml(_TD_CHART)
    assert [i["code"] for i in result["issues"] if not i["auto_fixed"]] == ["INVALID_CHILD"]
    assert result["blocking"] is True


def test_nesting_compile_failure_shape():
    from src.compiler.content_model import nesting_compile_failure
    assert nesting_compile_failure([{"code": "FONT_FLOOR", "message": "x", "auto_fixed": True}]) is None
    fail = nesting_compile_failure(normalize_xml(_TD_CHART)["issues"])
    assert fail["ok"] is False and fail["retryable"] is True
    assert fail["diagnostics"][0]["type"] == "INVALID_CHILD"


@patch("src.agents.validator.compile_xml")
@patch("src.agents.validator.validate_xml")
def test_normalize_and_compile_skips_compiler_on_bad_nesting(mock_validate, mock_compile, tmp_path):
    from src.agents.validator import normalize_and_compile
    ok, result = normalize_and_compile(_TD_CHART, "", output_dir=tmp_path)
    assert ok is False and result["diagnostics"][0]["type"] == "INVALID_CHILD"
    mock_validate.assert_not_called()
    mock_compile.assert_not_called()
