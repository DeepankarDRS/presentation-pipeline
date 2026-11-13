"""Every palette's *Soft tints keep their colour's hue (palette_tokens._soft_hue_floor) and text still reads
on them. Paid run 2026-11-12: mbb-blue's accentSoft was D3D5D3 (grey), so diagrams and tinted cards read grey."""

import re

import pytest

from src.agents.style_resolver import resolve_theme, theme_names
from src.compiler.palette_tokens import SOFT_CHROMA_DARK, SOFT_CHROMA_LIGHT, _lch, contrast

ROLES = ("accent", "positive", "negative", "warning")


def _tokens(name):
    return dict(re.findall(r'(\w+)="([0-9A-F]{6})"', resolve_theme(name)["element"]))


@pytest.mark.parametrize("name", theme_names())
def test_soft_tints_are_tinted_and_readable(name):
    t = _tokens(name)
    floor = (SOFT_CHROMA_DARK if resolve_theme(name)["is_dark"] else SOFT_CHROMA_LIGHT) - 0.003   # sRGB rounding
    for role in ROLES:
        soft = t[f"{role}Soft"]
        if _lch(t[role])[1] >= 0.04:
            assert _lch(soft)[1] >= floor, f"{name} {role}Soft {soft} is grey"
        assert contrast(t["textMain"], soft) >= 4.5, f"{name} textMain on {role}Soft"
        assert contrast(t[f"{role}Text"], soft) >= 4.5, f"{name} {role}Text on {role}Soft"


def test_mbb_blue_accent_soft_is_blue_not_grey():
    soft = _tokens("mbb-blue")["accentSoft"]
    L, C, h = _lch(soft)
    assert C >= 0.02 and soft != "D3D5D3"
    assert abs(h - _lch("042440")[2]) < 0.3     # the accent's own hue
