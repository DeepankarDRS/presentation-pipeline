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


def test_system_prompt_includes_notes_and_house_style():
    tmpl = _env.get_template("system.j2")
    out = tmpl.render(notes=["Tables need explicit column widths."], house_style="COMPOSITION\n2-4 horizontal bands.")
    assert "NOTES" in out
    assert "column widths" in out
    assert "LAYOUT GRAMMAR" in out
    assert "horizontal bands" in out


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


# ── _call_edit_llm / _call_repair_llm prompt wiring ─────────────────────

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
def test_call_repair_llm_builds_patch_prompts(mock_get_llm):
    from src.agents.slide_edit_service import _call_repair_llm

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="<Slide></Slide>")
    mock_get_llm.return_value = mock_llm

    result = _call_repair_llm(
        failing_xml="<Slide><div>x</div></Slide>",
        problems=["UNKNOWN_TAG: div"],
        pre_issues=[{"code": "HTML_TAG", "message": "Found HTML tag <div>.", "auto_fixed": False}],
        compile_diags=[{"type": "UNKNOWN_TAG", "message": "Unknown tag: <div>"}],
        objective="Metrics — apply user edit: move left",
        theme_element="<Theme />",
        contract={"forbidden_tags": ["div"]},
    )
    assert result == "<Slide></Slide>"

    system_msg, user_msg = (m["content"] for m in mock_llm.invoke.call_args[0][0])
    assert "PATCH" in user_msg
    assert "div" in system_msg  # forbidden tags rendered into the repairer system prompt


# ── Theme injection ────────────────────────────────────────────────────────
#
# current_xml is theme-less (the generator never emits <Theme>, matching the
# main pipeline's convention — see edit_slide_xml's comment). Without
# ensure_single_theme() injecting the deck's theme_element before compiling,
# $tokens in the edited XML never resolve.

@patch("src.agents.slide_edit_service.render_screenshots")
@patch("src.agents.slide_edit_service.compile_xml")
@patch("src.agents.slide_edit_service.get_llm")
def test_edit_slide_xml_injects_theme_before_compiling(mock_get_llm, mock_compile_xml, mock_render_screenshots):
    from src.agents.slide_edit_service import edit_slide_xml

    edited_xml = '<Slide><VStack backgroundColor="$surface"><Text color="$textMain">T</Text></VStack></Slide>'
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=edited_xml)
    mock_get_llm.return_value = mock_llm
    mock_compile_xml.return_value = {"ok": True, "pptx_path": "/tmp/out.pptx", "diagnostics": [], "warnings": []}
    mock_render_screenshots.return_value = MagicMock(ok=True, slides=[MagicMock(png_path="/tmp/slide-0.png")])

    result = edit_slide_xml(
        current_xml="<Slide><VStack><Text>T</Text></VStack></Slide>",
        feedback="make title bigger",
        theme_element='<Theme surface="F7F9FC" textMain="16202E" />',
        contract={}, slide_plan={}, run_id="theme-inject-test", slide_index=0, version=1,
    )

    assert result.ok is True
    compiled_xml = mock_compile_xml.call_args[0][0]
    assert compiled_xml.count("<Theme") == 1
    assert 'surface="F7F9FC"' in compiled_xml
    assert result.xml.count("<Theme") == 1


# ── Screenshot retry ───────────────────────────────────────────────────────

@patch("src.agents.slide_edit_service.time.sleep")
@patch("src.agents.slide_edit_service.render_screenshots")
def test_try_screenshot_retries_once_with_delay(mock_render_screenshots, mock_sleep):
    from src.agents.slide_edit_service import _try_screenshot

    failing = MagicMock(ok=False, error="COM error: Presentations.Open failed", slides=[])
    succeeding = MagicMock(ok=True, slides=[MagicMock(png_path="/tmp/slide-0.png")])
    mock_render_screenshots.side_effect = [failing, succeeding]

    result = _try_screenshot("/tmp/out.pptx", "/tmp/screenshots")

    assert result == "/tmp/slide-0.png"
    assert mock_render_screenshots.call_count == 2
    mock_sleep.assert_called_once_with(2)


@patch("src.agents.slide_edit_service.time.sleep")
@patch("src.agents.slide_edit_service.render_screenshots")
def test_try_screenshot_gives_up_after_two_failures(mock_render_screenshots, mock_sleep):
    from src.agents.slide_edit_service import _try_screenshot

    failing = MagicMock(ok=False, error="COM error", slides=[])
    mock_render_screenshots.return_value = failing

    result = _try_screenshot("/tmp/out.pptx", "/tmp/screenshots")

    assert result is None
    assert mock_render_screenshots.call_count == 2
