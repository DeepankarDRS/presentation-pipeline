"""Tests for the style resolver — theme resolution utility and graph node."""

from src.agents.style_resolver import DEFAULT_THEME, resolve_theme, style_resolver_node
from src.state import initial_state


def test_resolve_default_theme():
    theme = resolve_theme("")
    assert theme["name"] == "corporate-slate"
    assert theme["mode"] == "light"
    assert theme["is_dark"] is False
    assert "<Theme" in theme["element"]
    assert 'surface="F7F9FC"' in theme["element"]


def test_resolve_corporate_slate_explicit():
    theme = resolve_theme("corporate-slate")
    assert theme["name"] == "corporate-slate"
    assert theme["element"] == DEFAULT_THEME["element"]


def test_resolve_named_light_palette():
    theme = resolve_theme("sky-minimal")
    assert theme["name"] == "sky-minimal"
    assert theme["mode"] == "light"
    assert theme["is_dark"] is False
    assert 'surface="F5F9FD"' in theme["element"]
    assert 'accent="0284C7"' in theme["element"]
    assert 'textMain="18202B"' in theme["element"]


def test_resolve_named_dark_palette():
    theme = resolve_theme("graphite-dark")
    assert theme["name"] == "graphite-dark"
    assert theme["mode"] == "dark"
    assert theme["is_dark"] is True
    assert "chartSurface" in theme["element"]
    assert "chartInk" in theme["element"]


def test_resolve_unknown_falls_back():
    theme = resolve_theme("nonexistent-theme")
    assert theme["name"] == "corporate-slate"
    assert theme["element"] == DEFAULT_THEME["element"]


def test_resolve_chart_colors():
    theme = resolve_theme("sky-minimal")
    assert isinstance(theme["chart_colors"], list)
    assert len(theme["chart_colors"]) >= 3
    assert "0284C7" in theme["chart_colors"]


def test_resolve_returns_copy():
    a = resolve_theme("")
    b = resolve_theme("")
    a["name"] = "mutated"
    assert b["name"] == "corporate-slate"


def test_style_resolver_node_writes_state():
    state = initial_state(run_id="sr1", raw_request="test", theme_name="sky-minimal")
    result = style_resolver_node(state)
    assert "theme_element" in result
    assert "resolved_theme" in result
    assert result["resolved_theme"]["name"] == "sky-minimal"
    assert 'surface="F5F9FD"' in result["theme_element"]
