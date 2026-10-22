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


# --- seeds, contrast repair, chart tokens --------------------------------------

import pytest

from src.agents.style_resolver import (
    contrast, derive_tokens, guard_chart_colors, palette_names, parse_color,
)
from src.compiler.theme_swap import theme_tokens


def test_parse_color_css_forms_and_alpha():
    assert parse_color("#c46a3f") == "C46A3F"
    assert parse_color("F00") == "FF0000"
    assert parse_color("rgba(0, 0, 0, 0.5)", "FFFFFF") == "808080"
    assert parse_color("#00000080", "FFFFFF") == "7F7F7F"
    with pytest.raises(ValueError):
        parse_color("red")


def test_seed_derives_missing_tokens_and_semantic_defaults():
    tokens, chart = derive_tokens({"mode": "light", "background": "#FFFFFF", "ink": "#111111", "accent": "#2563EB"})
    for k in ("surfaceAlt", "textMuted", "border", "accentAlt", "positive", "negative", "warning",
              "chartSurface", "chartInk"):
        assert len(tokens[k]) == 6
    assert tokens["positive"] == "15803D"
    assert chart[0] == "2563EB" and 3 <= len(chart) <= 5


def test_seed_repairs_failing_contrast():
    # gold on white is ~1.4:1 — must be darkened to >= 3:1, hue kept
    tokens, _ = derive_tokens({"mode": "light", "background": "FFFFFF", "ink": "073B4C",
                               "accent": "118AB2", "warning": "FFD166"})
    assert tokens["warning"] != "FFD166"
    assert contrast(tokens["warning"], "FFFFFF") >= 3.0


def test_chart_guard_repairs_in_place_and_drops_near_duplicates():
    out = guard_chart_colors(["C9F24D", "C7572C", "C7572D", "6E7E6D"], "F8F6F1")
    assert contrast(out[0], "F8F6F1") >= 2.0       # lime kept first, darkened
    assert out[1] == "C7572C" and "C7572D" not in out


@pytest.mark.parametrize("name", palette_names())
def test_every_palette_resolves_with_chart_tokens(name):
    theme = resolve_theme(name)
    assert theme["name"] == name
    tokens = theme_tokens(theme["element"])
    assert {"chartSurface", "chartInk", "chart1", "chart3"} <= tokens.keys()
    assert theme["chart_colors_json"].startswith('["$chart1"')


SEEDS = ["boardroom-orange", "paper-clay", "bone-copper", "ocean-light", "terracotta-light",
         "ink-copper", "lime-ink", "ocean-dark", "tropic-dark", "terracotta-dark"]


@pytest.mark.parametrize("name", SEEDS)
def test_seed_palettes_meet_contrast_targets(name):
    theme = resolve_theme(name)
    t = theme_tokens(theme["element"])
    surfaces = [t["surface"], t["surfaceAlt"]]
    for k in ("textMain", "textMuted"):
        assert min(contrast(t[k], s) for s in surfaces) >= 4.5, k
    for k in ("accent", "accentAlt", "positive", "negative", "warning"):
        assert min(contrast(t[k], s) for s in surfaces) >= 3.0, k
    for c in theme["chart_colors"]:
        assert contrast(c, t["chartSurface"]) >= 2.0, c
    assert theme["is_dark"] == (contrast(t["surface"], "000000") < contrast(t["surface"], "FFFFFF"))
