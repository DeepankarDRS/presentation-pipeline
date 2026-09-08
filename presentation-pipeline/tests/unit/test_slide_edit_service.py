"""Tests for slide_editor prompt rendering and the enriched contract/slide_plan wiring."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from jinja2 import Environment, FileSystemLoader

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "prompts" / "slide_editor"
_env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), keep_trailing_newline=True)


# ── system.j2 rendering ───────────────────────────────────────────────────

def test_system_prompt_includes_forbidden_attributes():
    tmpl = _env.get_template("system.j2")
    out = tmpl.render(forbidden_attributes=["style", "class"])
    assert "FORBIDDEN ATTRIBUTES" in out
    assert "style" in out


def test_system_prompt_includes_allowed_nodes():
    tmpl = _env.get_template("system.j2")
    out = tmpl.render(allowed_nodes=["VStack", "Text"])
    assert "ALLOWED NODES" in out
    assert "VStack" in out


def test_system_prompt_includes_notes_and_layout_pattern():
    tmpl = _env.get_template("system.j2")
    out = tmpl.render(notes=["Tables need explicit column widths."], layout_pattern="two_column reference")
    assert "NOTES" in out
    assert "column widths" in out
    assert "LAYOUT VOCABULARY" in out
    assert "two_column reference" in out


def test_system_prompt_omits_empty_sections():
    tmpl = _env.get_template("system.j2")
    out = tmpl.render()
    assert "FORBIDDEN ATTRIBUTES" not in out
    assert "ALLOWED NODES" not in out
    assert "LAYOUT VOCABULARY" not in out
    assert "NOTES" not in out


def test_system_prompt_targeted_edit_framing():
    tmpl = _env.get_template("system.j2")
    out = tmpl.render()
    assert "TARGETED EDIT" in out


# ── user.j2 rendering ─────────────────────────────────────────────────────

def test_user_prompt_includes_slide_intent():
    tmpl = _env.get_template("user.j2")
    out = tmpl.render(
        current_xml="<Slide></Slide>", theme_element="<Theme />", feedback="move chart left",
        slide_type="data", components=[{"kind": "chart", "count": 1, "content_summary": "Q3"}],
        density="normal", layout_hint="chart on left",
    )
    assert "SLIDE INTENT" in out
    assert "chart" in out
    assert "Q3" in out


def test_user_prompt_omits_slide_intent_when_empty():
    """Legacy edit sessions (no slide_plan persisted) render byte-identical to before."""
    tmpl = _env.get_template("user.j2")
    out = tmpl.render(current_xml="<Slide></Slide>", theme_element="<Theme />", feedback="x")
    assert "SLIDE INTENT" not in out
    assert "<Slide></Slide>" in out


# ── _call_edit_llm / _call_repair_llm accept slide_plan ──────────────────

@patch("src.agents.slide_edit_service.get_llm")
def test_call_edit_llm_accepts_slide_plan(mock_get_llm):
    from src.agents.slide_edit_service import _call_edit_llm

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="<Slide></Slide>")
    mock_get_llm.return_value = mock_llm

    result = _call_edit_llm(
        current_xml="<Slide></Slide>", feedback="move left", theme_element="<Theme />",
        contract={"forbidden_tags": ["div"]},
        slide_plan={"slide_type": "data", "components": [{"kind": "chart"}]},
    )
    assert result == "<Slide></Slide>"


@patch("src.agents.slide_edit_service.get_llm")
def test_call_repair_llm_accepts_slide_plan(mock_get_llm):
    from src.agents.slide_edit_service import _call_repair_llm

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="<Slide></Slide>")
    mock_get_llm.return_value = mock_llm

    result = _call_repair_llm(
        failing_xml="<Slide></Slide>", problems=["BAD_TAG: div"], guidance="Use VStack instead.",
        feedback="move left", theme_element="<Theme />",
        contract={"forbidden_tags": ["div"]},
        slide_plan={"slide_type": "data", "components": [{"kind": "chart"}]},
    )
    assert result == "<Slide></Slide>"
