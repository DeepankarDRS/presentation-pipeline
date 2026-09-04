"""Tests for the validator agent.

Unit tests mock the compiler; integration tests use the real compiler
when Node is available.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agents.validator import validator_node
from src.compiler.normalizer import normalize_xml, pre_validate
from src.state import initial_state


VALID_XML = """\
<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" accentAlt="0EA5E9" positive="15803D" negative="DC2626" warning="B45309" textMain="16202E" textMuted="55627A" border="E2E8F0" />
<Slide>
  <VStack w="1280" h="720" padding="72" gap="24" backgroundColor="$surface" alignItems="start" justifyContent="center">
    <Text fontSize="44" bold="true" color="$textMain">Test Title</Text>
    <Text fontSize="22" color="$textMuted">Test subtitle text</Text>
  </VStack>
</Slide>
"""

FENCED_XML = f"```xml\n{VALID_XML}```"

HTML_LEAK_XML = """\
<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />
<Slide>
  <div style="display:flex">
    <p>This is HTML not POM</p>
  </div>
</Slide>
"""

HASH_COLOR_XML = """\
<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />
<Slide>
  <VStack w="1280" h="720" padding="48" backgroundColor="#F7F9FC">
    <Text fontSize="32" color="#16202E">Hello</Text>
  </VStack>
</Slide>
"""

ZERO_DIM_XML = """\
<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />
<Slide>
  <VStack w="0" h="720" padding="48">
    <Text fontSize="0">Zero dims</Text>
  </VStack>
</Slide>
"""


# ── Normalizer unit tests ─────────────────────────────────────────────────

def test_normalize_strips_fences():
    result = normalize_xml(FENCED_XML)
    assert "```" not in result["cleaned_xml"]
    assert "<Slide>" in result["cleaned_xml"]
    codes = [i["code"] for i in result["issues"]]
    assert "MARKDOWN_FENCE" in codes


def test_normalize_strips_hash_colors():
    result = normalize_xml(HASH_COLOR_XML)
    assert "#F7F9FC" not in result["cleaned_xml"]
    assert 'backgroundColor="F7F9FC"' in result["cleaned_xml"]
    assert "#16202E" not in result["cleaned_xml"]
    codes = [i["code"] for i in result["issues"]]
    assert "HASH_COLOR" in codes


def test_normalize_flags_zero_dims():
    result = normalize_xml(ZERO_DIM_XML)
    codes = [i["code"] for i in result["issues"]]
    assert "ZERO_DIM" in codes
    assert result["blocking"] is True


def test_normalize_clean_xml_passes():
    result = normalize_xml(VALID_XML)
    assert not result["blocking"]
    non_auto = [i for i in result["issues"] if not i["auto_fixed"]]
    assert len(non_auto) == 0


def test_normalize_removes_br_hr():
    xml = '<Theme />\n<Slide><VStack><br/><Text>A</Text><hr></VStack></Slide>'
    result = normalize_xml(xml)
    assert "<br" not in result["cleaned_xml"]
    assert "<hr" not in result["cleaned_xml"]


def test_normalize_removes_zero_spacing():
    xml = '<Theme />\n<Slide><VStack gap="0" padding="0"><Text>A</Text></VStack></Slide>'
    result = normalize_xml(xml)
    assert 'gap="0"' not in result["cleaned_xml"]
    assert 'padding="0"' not in result["cleaned_xml"]


def test_normalize_fixes_border_accent():
    xml = '<VStack border.width="1" border.color="$accent" borderTop.width="4" borderTop.color="$accent">'
    result = normalize_xml(xml)
    assert 'border.color="$border"' in result["cleaned_xml"]
    assert 'borderTop.color="$accent"' in result["cleaned_xml"]
    codes = [i["code"] for i in result["issues"]]
    assert "BORDER_ACCENT_FIX" in codes


# ── Pre-validate fallback tests ───────────────────────────────────────────

def test_pre_validate_detects_html_tags():
    result = pre_validate(HTML_LEAK_XML)
    codes = [i["code"] for i in result["issues"] if not i["auto_fixed"]]
    assert "HTML_TAG" in codes
    assert result["blocking"] is True


def test_pre_validate_detects_forbidden_attrs():
    result = pre_validate(HTML_LEAK_XML)
    codes = [i["code"] for i in result["issues"] if not i["auto_fixed"]]
    assert "HTML_ATTR" in codes


def test_pre_validate_detects_miscased_tags():
    xml = '<Theme />\n<Slide><vstack w="1280" h="720"><text>bad case</text></vstack></Slide>'
    result = pre_validate(xml)
    codes = [i["code"] for i in result["issues"]]
    assert "MISCASED_TAG" in codes


def test_pre_validate_with_contract_checks_attrs():
    xml = '<Theme />\n<Slide><VStack w="1280" h="720"><Text uppercase="true" fontSize="14">Hi</Text></VStack></Slide>'
    contract = {
        "allowed_nodes": ["Slide", "Theme", "VStack", "Text"],
        "allowed_attributes": {
            "VStack": ["gap", "alignItems"],
            "Text": ["fontSize", "color", "bold"],
        },
    }
    result = pre_validate(xml, contract)
    codes = [i["code"] for i in result["issues"]]
    assert "UNKNOWN_ATTR" in codes


# ── Validator node tests (mocked compiler) ────────────────────────────────

def test_validator_empty_xml():
    state = initial_state(run_id="v1", raw_request="test")
    state["current_xml"] = ""
    result = validator_node(state)
    assert result["compile_result"]["ok"] is False
    assert result["compile_result"]["retryable"] is True


@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
def test_validator_success_path(mock_compile, mock_validate):
    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="v2", raw_request="test")
    state["current_xml"] = VALID_XML
    result = validator_node(state)

    assert result["compile_result"]["ok"] is True
    assert result["compile_result"]["pptx_path"] == "/tmp/test.pptx"
    mock_validate.assert_called_once()
    mock_compile.assert_called_once()


@patch("src.agents.validator.validate_xml")
def test_validator_parsexml_failure_skips_compile(mock_validate):
    mock_validate.return_value = {
        "ok": False,
        "diagnostics": [{"type": "UNKNOWN_TAG", "message": "Unknown tag: <div>"}],
        "warnings": [],
        "retryable": True,
    }

    state = initial_state(run_id="v3", raw_request="test")
    state["current_xml"] = HTML_LEAK_XML
    result = validator_node(state)

    assert result["compile_result"]["ok"] is False
    assert result["compile_result"]["retryable"] is True
    assert len(result["compile_result"]["diagnostics"]) > 0


@patch("src.agents.validator.validate_xml")
def test_validator_falls_back_to_pre_validate(mock_validate):
    mock_validate.return_value = None

    state = initial_state(run_id="v4", raw_request="test")
    state["current_xml"] = HTML_LEAK_XML
    result = validator_node(state)

    assert result["compile_result"]["ok"] is False
    assert result["compile_result"]["retryable"] is True


@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
def test_validator_compile_error_not_retryable(mock_compile, mock_validate):
    from src.compiler.compiler_client import CompilerError
    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.side_effect = CompilerError("Node not found")

    state = initial_state(run_id="v5", raw_request="test")
    state["current_xml"] = VALID_XML
    result = validator_node(state)

    assert result["compile_result"]["ok"] is False
    assert result["compile_result"]["retryable"] is False
    assert "HARNESS_ERROR" in result["compile_result"]["diagnostics"][0]["type"]


@patch("src.agents.validator.validate_xml")
@patch("src.agents.validator.compile_xml")
def test_validator_normalizes_before_compile(mock_compile, mock_validate):
    mock_validate.return_value = {"ok": True, "diagnostics": [], "warnings": [], "retryable": False}
    mock_compile.return_value = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }

    state = initial_state(run_id="v6", raw_request="test")
    state["current_xml"] = FENCED_XML
    result = validator_node(state)

    assert result["compile_result"]["ok"] is True
    norm_issues = result["normalize_result"]["issues"]
    assert any(i["code"] == "MARKDOWN_FENCE" for i in norm_issues)
