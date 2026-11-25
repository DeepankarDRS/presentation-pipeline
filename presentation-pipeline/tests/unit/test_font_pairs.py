"""Font pairs (palettes.yaml `font_pairs`): what a font must have to be offered, and that the choice reaches the file."""

import re
import shutil
import zipfile
from pathlib import Path

import pytest
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from src.agents.style_resolver import font_pairs, resolve_theme, style_resolver_node
from src.compiler.compiler_client import compile_xml, deck_font
from src.compiler.font_embed import available_fonts, embed_deck_fonts
from src.compiler.normalizer import ensure_single_theme, strip_theme

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend/src/app/constants/theme.constants.ts"
_SAMPLE = "The quick brown fox reviews Q3 revenue growth of 12.4% across regions"
_FAMILIES = sorted({p[k] for p in font_pairs().values() for k in ("heading", "body")})
_SLIDE = ('<Slide><VStack w="1280" h="720" padding="56" gap="12"><Text fontSize="14" bold="true">KICKER</Text>'
          '<Text fontSize="36" bold="true">Revenue grew 12% on <Span color="2563EB">retail</Span></Text>'
          '<Text fontSize="48" bold="true">₹4.2 Cr</Text><Text fontSize="18">Body text</Text></VStack></Slide>')
_CHART = ('<Slide><VStack w="1280" h="720" padding="56"><!-- chart-post {"labels":"true","fmt":"0","ink":"$textMain"} -->'
          '<Chart chartType="bar" w="800" h="400"><ChartSeries name="A"><ChartDataPoint label="Q1" value="3"/>'
          '<ChartDataPoint label="Q2" value="4"/></ChartSeries></Chart></VStack></Slide>')


def _width(font: TTFont) -> float:
    cmap, adv = font.getBestCmap(), font["hmtx"]
    return sum(adv[cmap[ord(c)]][0] for c in _SAMPLE) / font["head"].unitsPerEm / len(_SAMPLE)


@pytest.mark.parametrize("family", _FAMILIES)
def test_every_family_can_draw_a_deck(family):
    faces = available_fonts()[family]
    assert {"regular", "bold"} <= faces.keys()
    for face in ("regular", "bold"):
        font = TTFont(faces[face])
        cmap, glyphs = font.getBestCmap(), font.getGlyphSet()
        assert ord("₹") in cmap
        assert not font["OS/2"].fsType & 0x0002          # its licence lets us embed it

        def box(char):
            pen = BoundsPen(glyphs)
            glyphs[cmap[ord(char)]].draw(pen)
            return pen.bounds
        cap = box("H")[3]
        for digit in "0123456789":                       # lining figures: PowerPoint cannot switch them on
            assert box(digit)[3] > 0.85 * cap and box(digit)[1] > -0.05 * cap, digit


@pytest.mark.parametrize("pair", sorted(font_pairs()))
def test_a_body_is_never_wider_than_inter(pair):
    """capacity.yaml and label_room are measured in Inter."""
    have = available_fonts()
    for face in ("regular", "bold"):
        body = _width(TTFont(have[font_pairs()[pair]["body"]][face]))
        assert body <= _width(TTFont(have["Inter"][face])) + 1e-6
    assert {"italic", "boldItalic"} <= have[font_pairs()[pair]["body"]].keys()


def test_the_frontend_offers_the_same_pairs():
    ts = re.findall(r"\{ id: '([\w-]+)',.*?heading: '([^']+)',\s*body: '([^']+)' \}", _FRONTEND.read_text(encoding="utf-8"))
    assert {i: (h, b) for i, h, b in ts} == {i: (p["heading"], p["body"]) for i, p in font_pairs().items()}


@pytest.mark.parametrize("pair", sorted(font_pairs()))
def test_a_headline_is_never_wider_than_inter(pair):
    """Headlines are bold: one in a wider family is drawn smaller (`scale`)."""
    have, p = available_fonts(), font_pairs()[pair]
    assert _width(TTFont(have[p["heading"]]["bold"])) * p.get("scale", 1) <= _width(TTFont(have["Inter"]["bold"])) + 1e-6


def test_the_default_deck_is_unchanged():
    plain = resolve_theme("corporate-slate")
    for pair in ("", "inter", "no-such-pair", '"/><Slide>'):
        assert resolve_theme("corporate-slate", pair) == plain
    assert "deck-fonts" not in plain["element"]
    assert style_resolver_node({"theme_name": "corporate-slate", "deck_settings": None})["resolved_theme"] == plain


def test_the_pair_stays_with_the_theme():
    out = style_resolver_node({"theme_name": "navy-orange", "deck_settings": {"font_pair": "fraunces"}})
    el = out["theme_element"]
    assert out["resolved_theme"]["font_pair"] == "fraunces" and el.endswith('body="Inter" -->')
    twice = ensure_single_theme(ensure_single_theme(_SLIDE, el), el)
    assert twice.count("deck-fonts") == 1 and strip_theme(twice) == _SLIDE
    assert ensure_single_theme(twice, "") == twice      # no theme given: the one in the XML, fonts included


def test_only_the_headline_takes_the_heading_font():
    el = resolve_theme("corporate-slate", "montserrat")["element"]
    xml = deck_font(el + "\n" + _SLIDE + "\n" + _SLIDE)
    assert xml.count('<Text fontFamily="Montserrat" fontSize="34" bold="true">Revenue') == 2   # 36 x 0.945
    assert xml.count('fontFamily="Montserrat"') == 2 and xml.count('fontFamily="Source Sans Pro"') == 6
    assert deck_font(xml) == xml
    serif = deck_font(resolve_theme("corporate-slate", "source-serif")["element"] + _SLIDE)
    assert '<Text fontFamily="Source Serif 4" fontSize="36" bold="true">Revenue' in serif         # no scale


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_the_chosen_fonts_are_in_the_file(tmp_path):
    res = compile_xml(resolve_theme("corporate-slate", "source-serif")["element"] + "\n" + _SLIDE + _CHART, tmp_path)
    assert res["ok"], res["diagnostics"]
    pptx = Path(res["pptx_path"])
    with zipfile.ZipFile(pptx) as z:
        slide = z.read("ppt/slides/slide1.xml").decode("utf-8")
        chart = z.read("ppt/charts/chart1.xml").decode("utf-8")
    assert set(re.findall(r'<a:latin typeface="([^"]+)"', chart)) == {"Source Sans Pro"}
    runs = {t: f for f, t in re.findall(r'<a:latin typeface="([^"]+)"[^>]*/>.*?<a:t[^>]*>([^<]*)</a:t>', slide)}
    assert runs["Revenue grew 12% on "] == runs["retail"] == "Source Serif 4"
    assert runs["Body text"] == runs["₹4.2 Cr"] == runs["KICKER"] == "Source Sans Pro"
    embedded = {e["family"] for e in embed_deck_fonts(pptx)["embedded"]}
    assert embedded == {"Source Serif 4", "Source Sans Pro"}
