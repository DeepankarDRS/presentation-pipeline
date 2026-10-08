"""Deck-quality fixes from the hand-written QBR comparison (docs/eval/hand-qbr, 2026-10-08)."""
from __future__ import annotations

from pydantic import BaseModel

from src.compiler.compiler_client import deck_font
from src.compiler.normalizer import normalize_xml, strip_control_chars
from src.utils.llm_client import unpack_raw


def test_control_chars_become_one_space():
    assert strip_control_chars("Q2 FY26 42.3\x7f Q3 FY26") == ("Q2 FY26 42.3 Q3 FY26", 1)
    assert strip_control_chars("a\tb\nc") == ("a\tb\nc", 0)


def test_normalizer_removes_control_chars():
    xml = '<Slide><VStack w="1280" h="720"><Text fontSize="16">$28.1M\x7f$14.4M</Text></VStack></Slide>'
    out = normalize_xml(xml)
    text = out["cleaned_xml"]
    assert "\x7f" not in text and "$28.1M $14.4M" in text


class _Slide(BaseModel):
    subtitle: str
    items: list[str]


def test_parsed_llm_result_is_cleaned():
    parsed, _ = unpack_raw({"parsed": _Slide(subtitle="A\x7f B", items=["x\x14y"]), "raw": None})
    assert parsed.subtitle == "A B" and parsed.items == ["x y"]


def test_deck_font_fills_missing_family_only():
    xml = '<Text fontSize="14">a</Text><Td fontFamily="X">b</Td><TextBox>'
    assert deck_font(xml, "Inter") == '<Text fontFamily="Inter" fontSize="14">a</Text><Td fontFamily="X">b</Td><TextBox>'
    assert deck_font(xml, "none") == xml


def test_examples_off_by_default():
    import src.agents.context_builder as cb
    assert cb.EXAMPLES_ON is False


# second pass, from paid run deck-qbr-data-30cd7b (2026-10-08)

def test_lone_card_in_growing_band_grows():
    from src.compiler.grow_fallback import fill_lone_child
    xml = ('<VStack grow="3"><VStack padding="24" backgroundColor="$surfaceAlt">'
           '<Chart h="max" chartType="bar"></Chart></VStack></VStack>')
    out, note = fill_lone_child(xml)
    assert note and '<VStack grow="1" padding="24"' in out
    assert fill_lone_child(out)[1] is None


def test_time_series_focus_moves_to_latest_period():
    from src.compiler.normalizer import _focus_latest_period
    chart = ('<Text>Revenue grew</Text><Chart chartType="bar" chartColors=\'["A","B","B","B","A"]\'><ChartSeries name="R">'
             + "".join(f'<ChartDataPoint label="FY2{i}" value="{i}" />' for i in range(1, 6))
             + "</ChartSeries></Chart>")
    out, n = _focus_latest_period(chart)
    assert n == 1 and '\'["B","B","B","B","A"]\'' in out


def test_named_period_keeps_its_focus():
    from src.compiler.normalizer import _focus_latest_period
    chart = ('<Text>FY22 was the dip</Text><Chart chartType="bar" chartColors=\'["B","A","B","B","B"]\'><ChartSeries name="R">'
             + "".join(f'<ChartDataPoint label="FY2{i}" value="{i}" />' for i in range(1, 6))
             + "</ChartSeries></Chart>")
    assert _focus_latest_period(chart)[1] == 0


def test_numeric_columns_share_width():
    from src.compiler.normalizer import _share_numeric_columns
    rows = "".join(f"<Tr><Td>{a}</Td><Td>{b}</Td><Td>{c}</Td></Tr>" for a, b, c in
                   [("Segment", "ARR", "Customers"), ("Enterprise", "$28.1M", "142"), ("SMB", "$5.7M", "2,341")])
    xml = f'<Table><Col width="180" /><Col width="140" /><Col width="120" />{rows}</Table>'
    out, n = _share_numeric_columns(xml)
    assert n == 2 and '<Col width="180" /><Col /><Col />' in out


def test_card_body_repeating_title_and_tag_is_dropped():
    from src.agents.written_lines import drop_repeated_bodies
    plan = {"components": [{"kind": "card_grid", "content_data": {"cards": [
        {"title": "Close 3 enterprise logos", "tag": "$4M+ combined ARR",
         "body": "Close 3 enterprise logos worth $4M+ combined ARR"}]}}]}
    assert drop_repeated_bodies(plan) and "body" not in plan["components"][0]["content_data"]["cards"][0]


# third pass, from the six-case run quality-1008 (2026-10-08)

_THEME = ('<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" accentAlt="0EA5E9" positive="15803D" '
          'negative="DC2626" warning="B45309" textMain="16202E" textMuted="55627A" border="CAD5E4" '
          'chartSurface="FFFFFF" chartInk="16202E" />\n')


def test_later_dark_panels_become_tinted_cards():
    from src.compiler.normalizer import soften_dark_panels
    xml = ('<VStack><VStack padding="20" backgroundColor="$textMain"><Text color="$surfaceAlt">A</Text>'
           '<HStack><Text color="$neutral">b</Text></HStack></VStack><Text color="$surfaceAlt">outside</Text></VStack>')
    out, n = soften_dark_panels(xml)
    assert n == 1 and 'backgroundColor="$accentSoft"' in out
    assert '<Text color="$textMain">A</Text>' in out and '<Text color="$textMuted">b</Text>' in out
    assert '<Text color="$surfaceAlt">outside</Text>' in out


def _fit(xml, tmp_path):
    import json, shutil
    import pytest
    if not shutil.which("node"):
        pytest.skip("node not installed")
    from src.compiler.compiler_client import compile_xml
    r = compile_xml(_THEME + xml, tmp_path)
    return r, (tmp_path / "fitted.xml").read_text(encoding="utf-8") if (tmp_path / "fitted.xml").exists() else xml


def test_kpi_numbers_never_grow_off_the_slide(tmp_path):
    tile = ('<VStack w="max" padding="20" gap="8" backgroundColor="$surfaceAlt" justifyContent="center" alignItems="center">'
            '<Text fontSize="14" color="$textMuted">Spend</Text>'
            '<Text fontSize="32" bold="true" color="$textMain">₹129.4<Span fontSize="18">L</Span></Text></VStack>')
    xml = ('<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
           '<Text fontSize="36" bold="true" color="$textMain">Seven KPIs</Text>'
           f'<HStack gap="18" alignItems="stretch" grow="1">{tile * 7}</HStack></VStack></Slide>')
    r, _ = _fit(xml, tmp_path)
    assert r["ok"] and not [w for w in r["warnings"] if w.get("code") == "NODE_OUT_OF_BOUNDS"]


def test_small_layer_scales_into_its_card(tmp_path):
    xml = ('<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
           '<Text fontSize="36" bold="true" color="$textMain">Hub</Text>'
           '<VStack grow="1" padding="24" backgroundColor="$surfaceAlt" alignItems="center">'
           '<Layer w="400" h="200"><Shape id="hub" shapeType="ellipse" x="150" y="50" w="100" h="100" text="Hub" fontSize="14" />'
           '</Layer></VStack></VStack></Slide>')
    r, fitted = _fit(xml, tmp_path)
    assert r["ok"] and '<Layer w="400"' not in fitted
