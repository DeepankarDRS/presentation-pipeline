"""Tests for the no-LLM theme swap (src/compiler/theme_swap.py)."""

import re
from pathlib import Path

import pytest

from src.agents.style_resolver import resolve_theme
from src.compiler.normalizer import _THEME_RE
from src.compiler.theme_swap import swap_theme, theme_tokens, with_chart_tokens

OLD = ('<Theme surface="F0F5F3" surfaceAlt="FFFFFF" accent="0D6B4E" accentAlt="34D399" '
       'positive="0D6B4E" negative="E54D2E" warning="F59E0B" textMain="141F1C" '
       'textMuted="5F706B" border="D5DDD9" />')
GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "gj-h1-deck"


def test_theme_tokens_parses_and_uppercases():
    assert theme_tokens('<Theme accent="#2563eb" surface="F7F9FC" />') == {"accent": "2563EB", "surface": "F7F9FC"}


def test_exact_hex_becomes_token_by_attribute_role():
    xml = ('<Slide><VStack backgroundColor="FFFFFF" border.color="D5DDD9">'
           '<Text color="0D6B4E">x</Text><Shape fill.color="0D6B4E" /></VStack></Slide>')
    out = swap_theme(xml, OLD, [], False).xml
    assert 'backgroundColor="$surfaceAlt"' in out
    assert 'border.color="$border"' in out
    # accent and positive share 0D6B4E — both roles prefer accent
    assert ' color="$accent"' in out and 'fill.color="$accent"' in out


def test_unmatched_hex_maps_to_nearest_role_token():
    xml = ('<Slide><VStack backgroundColor="E0F2EC"><Text color="3B82F6">a</Text>'
           '<Text color="F8FAFC">b</Text></VStack></Slide>')
    r = swap_theme(xml, OLD, [], False)
    assert 'backgroundColor="$surface"' in r.xml     # light tint -> surface
    assert 'color="$accent"' in r.xml                # off-palette blue -> accent
    assert 'color="$surfaceAlt"' in r.xml            # near-white text stays light
    assert "E0F2EC->surface" in r.approximated


def test_chart_colors_replaced_by_position():
    xml = """<Slide><Chart w="400" h="300" chartColors='["0D6B4E","3B82F6"]'></Chart></Slide>"""
    out = swap_theme(xml, OLD, ["AAAAAA", "BBBBBB", "CCCCCC"], False).xml
    assert """chartColors='["AAAAAA","BBBBBB"]'""" in out


def test_dark_target_wraps_chart_once():
    xml = '<Slide><VStack><Chart w="400" h="300" grow="1" chartType="bar"></Chart></VStack></Slide>'
    r = swap_theme(xml, OLD, [], True)
    assert r.charts_wrapped == 1
    assert '<VStack w="400" h="300" grow="1" padding="12" backgroundColor="$chartSurface"' in r.xml
    assert '<Chart h="276" w="376" chartType="bar">' in r.xml
    again = swap_theme(r.xml, OLD, [], True)
    assert again.charts_wrapped == 0 and again.xml == r.xml


def test_light_target_does_not_wrap():
    xml = '<Slide><Chart w="max" h="300"></Chart></Slide>'
    assert swap_theme(xml, OLD, [], False).charts_wrapped == 0


@pytest.mark.parametrize("name", ["corporate-slate", "teal-slate", "warm-editorial"])
def test_with_chart_tokens_completes_light_palettes(name):
    el = with_chart_tokens(resolve_theme(name)["element"])
    tokens = theme_tokens(el)
    assert tokens["chartSurface"] and tokens["chartInk"]
    assert el.endswith("/>") and el.count("chartSurface=") == 1


def test_golden_deck_leaves_no_literal_hex():
    files = sorted(GOLDEN.glob("*.xml"))
    assert files
    theme = resolve_theme("graphite-dark")
    for f in files:
        xml = f.read_text(encoding="utf-8")
        old = _THEME_RE.search(xml).group(0)
        out = swap_theme(xml, old, theme["chart_colors"], True).xml
        assert "<Theme" not in out
        leftovers = re.findall(r'[A-Za-z.]*[Cc]olor="#?[0-9A-Fa-f]{6}"', out)
        assert leftovers == [], (f.name, leftovers)


def test_dark_tinted_panel_inverts_with_its_text():
    xml = ('<Slide><VStack backgroundColor="1E3A5F"><Text color="FFFFFF">x</Text>'
           '<Text color="60A5FA">y</Text></VStack><Shape fill.color="FFF7ED" /></Slide>')
    out = swap_theme(xml, OLD, [], True).xml
    # inverted panel: panel and its white text flip together
    assert 'backgroundColor="$textMain"' in out and 'color="$surfaceAlt"' in out
    assert 'color="$accent"' in out
    assert 'fill.color="$surface' in out              # pale tint -> neutral surface
