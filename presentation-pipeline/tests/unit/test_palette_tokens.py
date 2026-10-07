"""Derived colour roles (src/compiler/palette_tokens.py, 2026-10-07) and the palette fixes
of docs/palette-quality-research-2026-10-06.md §5.1 (P3)."""

from __future__ import annotations

import colorsys
from pathlib import Path

import pytest
import yaml

from src.agents.style_resolver import DEFAULT_THEME, resolve_theme
from src.compiler.palette_tokens import (
    DERIVED_KEYS, STATUS_ROLES, TEXT_MIN, contrast, derive_tokens,
)

_PALETTES = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "src" / "knowledge" / "theme" / "palettes.yaml")
    .read_text(encoding="utf-8"))["palettes"]
NAMES = sorted(_PALETTES)


def _hue(hex_: str) -> float:
    return colorsys.rgb_to_hls(*(int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4)))[0] * 360


@pytest.mark.parametrize("name", NAMES)
def test_text_tokens_readable_on_every_background(name):
    p = _PALETTES[name]
    d = derive_tokens(p)
    for role in STATUS_ROLES:
        text = d[f"{role}Text"]
        for bg in (p["surface"], p["surfaceAlt"], d[f"{role}Soft"]):
            assert contrast(text, bg) >= TEXT_MIN, (name, role, text, bg)


@pytest.mark.parametrize("name", NAMES)
def test_text_tokens_keep_the_hue(name):
    p = _PALETTES[name]
    d = derive_tokens(p)
    for role in STATUS_ROLES:
        diff = abs(_hue(d[f"{role}Text"]) - _hue(p[role]))
        assert min(diff, 360 - diff) <= 8, (name, role)


@pytest.mark.parametrize("name", NAMES)
def test_on_accent_readable(name):
    p = _PALETTES[name]
    assert contrast(derive_tokens(p)["onAccent"], p["accent"]) >= TEXT_MIN


@pytest.mark.parametrize("name", NAMES)
def test_meaning_roles_have_distinct_colours(name):
    """house-style color_roles: never give two meanings one colour (A4)."""
    p = _PALETTES[name]
    roles = [p["accent"], p["positive"], p["negative"], p["warning"]]
    assert len({c.upper() for c in roles}) == 4, name


def test_gj_h1_status_colours_read_as_text():
    p = _PALETTES["gj-h1"]
    for role in ("positive", "negative", "warning"):
        assert contrast(p[role], p["surface"]) >= TEXT_MIN, role


def test_authored_neutral_wins():
    p = dict(_PALETTES["corporate-slate"], neutral="ABCDEF")
    assert derive_tokens(p)["neutral"] == "ABCDEF"


@pytest.mark.parametrize("name", NAMES)
def test_theme_element_carries_derived_tokens(name):
    el = resolve_theme(name)["element"]
    for key in DERIVED_KEYS + ("chartSurface", "chartInk"):
        assert f' {key}="' in el, (name, key)


def test_default_theme_is_the_yaml_entry():
    built = resolve_theme("corporate-slate")
    assert DEFAULT_THEME["element"] == built["element"]
    assert DEFAULT_THEME["chart_colors"] == _PALETTES["corporate-slate"]["chartColors"]
    assert resolve_theme("no-such-palette")["element"] == DEFAULT_THEME["element"]


def test_chart_focus_pair_is_literal_hex():
    focus = resolve_theme("navy-orange")["chart_focus"]
    assert focus["focus"] == _PALETTES["navy-orange"]["accent"]
    assert not focus["rest"].startswith("$")


@pytest.mark.parametrize("name", NAMES)
def test_card_edge_is_visible(name):
    """A card's hairline reads on the slide AND on the card (corporate-slate's was 1.17:1)."""
    p = _PALETTES[name]
    border = derive_tokens(p)["border"]
    assert contrast(border, p["surface"]) >= 1.4 and contrast(border, p["surfaceAlt"]) >= 1.4
    diff = abs(_hue(border) - _hue(p["border"]))
    assert min(diff, 360 - diff) <= 8 or len({p["border"][i:i + 2] for i in (0, 2, 4)}) == 1
