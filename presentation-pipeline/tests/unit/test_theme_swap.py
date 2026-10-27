"""Theme switching on a finished deck (src/compiler/theme_swap.py) and seed palettes
(palette_tokens.expand_seed), 2026-10-22."""

import re
from pathlib import Path

import pytest

from src.agents.style_resolver import resolve_theme, theme_names
from src.compiler.normalizer import _THEME_RE
from src.compiler.palette_tokens import contrast, expand_seed, guard_chart_colors, parse_color
from src.compiler.theme_swap import swap_theme, theme_tokens

OLD = resolve_theme("gj-h1")["element"]
OLD_T = theme_tokens(OLD)
GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "gj-h1-deck"
SEEDS = ["boardroom-orange", "paper-clay", "bone-copper", "ocean-light", "terracotta-light",
         "ink-copper", "lime-ink", "ocean-dark", "tropic-dark", "terracotta-dark"]


def test_theme_tokens_parses_and_uppercases():
    assert theme_tokens('<Theme accent="#2563eb" surface="F7F9FC" />') == {"accent": "2563EB", "surface": "F7F9FC"}


def test_exact_hex_becomes_a_token_by_attribute_role():
    xml = (f'<Slide><VStack backgroundColor="FFFFFF" border.color="{OLD_T["border"]}">'
           f'<Text color="{OLD_T["textMuted"]}">x</Text></VStack></Slide>')
    out = swap_theme(xml, OLD, OLD, False).xml
    assert 'backgroundColor="$surfaceAlt"' in out
    assert 'border.color="$border"' in out
    assert 'color="$textMuted"' in out


def test_unmatched_hex_maps_to_the_nearest_role_token():
    r = swap_theme('<Slide><VStack backgroundColor="E0F2EC"><Text color="4F46E5">a</Text></VStack></Slide>',
                   OLD, OLD, False)
    assert 'backgroundColor="$surface"' in r.xml        # a pale tint is a surface
    assert 'color="$accent"' in r.xml                    # an off-palette blue becomes the accent
    assert "E0F2EC->surface" in r.approximated


def test_dark_tinted_panel_and_its_ink_flip_together():
    xml = ('<Slide><VStack backgroundColor="1E3A5F"><Text color="FFFFFF">a</Text>'
           '<Text color="60A5FA">b</Text></VStack></Slide>')
    out = swap_theme(xml, OLD, OLD, True).xml
    assert 'backgroundColor="$panelDark"' in out
    assert '<Text color="$onPanelDark">a</Text>' in out
    assert '<Text color="$accent">b</Text>' in out


def test_text_main_panel_from_an_old_theme_becomes_panel_dark():
    # gj-h1 golden: <Theme> without derived tokens, dark panels as $textMain and dark hex.
    old = '<Theme surface="F0F5F3" surfaceAlt="FFFFFF" accent="0D6B4E" textMain="141F1C" textMuted="5F706B" />'
    xml = ('<Slide><VStack backgroundColor="$textMain"><Text color="FFFFFF">a</Text></VStack>'
           '<VStack backgroundColor="1E3A5F"><Text color="$textMuted">b</Text></VStack></Slide>')
    out = swap_theme(xml, old, OLD, True).xml
    assert out.count('backgroundColor="$panelDark"') == 2
    assert "$textMain" not in out.split("<Text")[0]
    assert '<Text color="$onPanelDark">a</Text>' in out


def test_ink_on_an_accent_fill_becomes_on_accent():
    xml = f'<Slide><VStack backgroundColor="{OLD_T["accent"]}"><Text color="FFFFFF">a</Text></VStack></Slide>'
    out = swap_theme(xml, OLD, OLD, False).xml
    assert 'backgroundColor="$accent"' in out and '<Text color="$onAccent">a</Text>' in out


def test_text_outside_a_panel_keeps_its_own_role():
    xml = ('<Slide><VStack backgroundColor="1E3A5F"><Text color="FFFFFF">in</Text></VStack>'
           '<Text color="FFFFFF">out</Text></Slide>')
    out = swap_theme(xml, OLD, OLD, False).xml
    assert '<Text color="$onPanelDark">in</Text>' in out
    assert '<Text color="$surfaceAlt">out</Text>' in out


def test_chart_colors_keep_the_focus_pair_and_become_chart_tokens():
    xml = ("<Slide><Chart w=\"400\" h=\"300\" chartColors='[\"%s\",\"%s\",\"123456\",\"$chart4\"]'></Chart></Slide>"
           % (OLD_T["accent"], OLD_T["neutral"]))
    out = swap_theme(xml, OLD, resolve_theme("paper-clay")["element"], False).xml
    assert """chartColors='["$accent","$neutral","$chart3","$chart4"]'""" in out


def test_chart_colors_untouched_when_the_new_theme_has_no_chart_tokens():
    xml = """<Slide><Chart w="400" h="300" chartColors='["0D6B4E"]'></Chart></Slide>"""
    assert """chartColors='["0D6B4E"]'""" in swap_theme(xml, OLD, '<Theme surface="FFFFFF" />', False).xml


def test_dark_target_wraps_a_chart_once():
    xml = '<Slide><VStack><Chart w="400" h="300" grow="1" chartType="bar"></Chart></VStack></Slide>'
    r = swap_theme(xml, OLD, OLD, True)
    assert r.charts_wrapped == 1
    assert '<VStack w="400" h="300" grow="1" padding="12" backgroundColor="$chartSurface"' in r.xml
    assert '<Chart h="276" w="376" chartType="bar">' in r.xml
    again = swap_theme(r.xml, OLD, OLD, True)
    assert again.charts_wrapped == 0 and again.xml == r.xml


def test_light_target_does_not_wrap():
    assert swap_theme('<Slide><Chart w="max" h="300"></Chart></Slide>', OLD, OLD, False).charts_wrapped == 0


def test_golden_deck_leaves_no_literal_hex():
    files = sorted(GOLDEN.glob("*.xml"))
    assert files
    new = resolve_theme("ink-copper")["element"]
    for f in files:
        xml = f.read_text(encoding="utf-8")
        out = swap_theme(xml, _THEME_RE.search(xml).group(0), new, True).xml
        assert "<Theme" not in out
        assert re.findall(r'[A-Za-z.]*[Cc]olor="#?[0-9A-Fa-f]{6}"', out) == [], f.name
        for colors in re.findall(r"chartColors='([^']*)'", out):
            assert re.fullmatch(r'\[("\$\w+",?)+\]', colors), (f.name, colors)


# --- seed palettes ----------------------------------------------------------------

def test_parse_color_css_forms_and_alpha():
    assert parse_color("#c46a3f") == "C46A3F"
    assert parse_color("F00") == "FF0000"
    assert parse_color("rgba(0, 0, 0, 0.5)", "FFFFFF") == "808080"
    assert parse_color("#00000080", "FFFFFF") == "7F7F7F"
    with pytest.raises(ValueError):
        parse_color("red")


def test_seed_fills_missing_colours_and_keeps_meanings_apart():
    p = expand_seed({"mode": "light", "background": "#FFFFFF", "ink": "#111111",
                     "accent": "#2A9D8F", "positive": "#2A9D8F"})
    for k in ("surfaceAlt", "textMuted", "border", "accentAlt", "negative", "warning"):
        assert len(p[k]) == 6, k
    assert p["positive"] != p["accent"]                  # A4: positive repeated the accent
    assert 3 <= len(p["chartColors"]) <= 6


def test_seed_steps_a_failing_colour_until_it_reads():
    p = expand_seed({"mode": "light", "background": "FFFFFF", "ink": "073B4C",
                     "accent": "118AB2", "warning": "FFD166"})     # gold on white: 1.4:1
    assert contrast(p["warning"], "FFFFFF") >= 3.0


def test_chart_guard_repairs_in_place_and_drops_near_duplicates():
    out = guard_chart_colors(["C9F24D", "C7572C", "C7572D", "6E7E6D"], "F8F6F1")
    assert contrast(out[0], "F8F6F1") >= 2.0            # lime stays first, stepped darker
    assert out[1] == "C7572C" and "C7572D" not in out


@pytest.mark.parametrize("name", theme_names())
def test_every_palette_resolves_with_chart_tokens(name):
    theme = resolve_theme(name)
    tokens = theme_tokens(theme["element"])
    assert {"chartSurface", "chartInk", "chart1", "panelDark", "onPanelDark"} <= tokens.keys()
    assert theme["chart_colors_json"].startswith('["$chart1"')


@pytest.mark.parametrize("name", SEEDS)
def test_seed_palettes_meet_their_contrast_targets(name):
    theme = resolve_theme(name)
    t = theme_tokens(theme["element"])
    for k in ("textMain", "textMuted"):
        assert min(contrast(t[k], t["surface"]), contrast(t[k], t["surfaceAlt"])) >= 4.5, k
    for k in ("accent", "accentAlt", "positive", "negative", "warning"):
        assert min(contrast(t[k], t["surface"]), contrast(t[k], t["surfaceAlt"])) >= 3.0, k
    for c in theme["chart_colors"]:
        assert contrast(c, t["chartSurface"]) >= 2.0, c


# Brand oranges kept on purpose (palettes.yaml comment on saascolor: 2.3-2.6:1 as text).
ACCENT_BELOW_3 = {"saascolor", "navy-orange"}


@pytest.mark.parametrize("name", theme_names())
def test_every_palette_meets_its_accent_chart_and_meaning_targets(name):
    # 2026-10-27, scripts/palette_contrast.py: hand-written palettes are stepped too, not only seeds.
    from src.compiler.theme_swap import _lab

    theme = resolve_theme(name)
    t = theme_tokens(theme["element"])
    keys = ("accentAlt", "positive", "negative", "warning") + (() if name in ACCENT_BELOW_3 else ("accent",))
    for k in keys:
        assert min(contrast(t[k], t["surface"]), contrast(t[k], t["surfaceAlt"])) >= 3.0, k
    for c in theme["chart_colors"]:
        assert contrast(c, t["chartSurface"]) >= 2.0, c
    for role in ("positive", "negative"):     # a focus number must not read as good / bad
        de = sum((x - y) ** 2 for x, y in zip(_lab(t["accent"]), _lab(t[role]))) ** 0.5
        assert de >= 15, role
