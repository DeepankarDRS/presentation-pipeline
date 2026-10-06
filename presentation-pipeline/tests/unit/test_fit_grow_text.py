"""fit-grow text growth guards (2026-09-24, CHEFFIN gate deck review; LLM-free, real compiler).

s9  CHEFFIN slide 4: a 35%-full card on a slide already 728 px tall was never grown (the slide
    check was absolute, so every size failed).
s10 gj-h1 slide 12: growing the summary panel's text widened it and squeezed the KPI table beside
    it until its rows spilled — growth must not change any width outside the grown card.
"""

import re

from scripts.eval_metrics import table_spill
from tests.unit.test_fit_grow_tables import _FIT, _compile


def test_sparse_card_grows_on_an_already_over_full_slide(tmp_path):
    on = _compile(_FIT / "s9-sparse-card-over-full-slide-cheffin.xml", tmp_path / "on")
    assert any(re.search(r"text x1\.\d+ .*fill 35% -> [7-8]\d%", r) for r in on["fitGrow"]), on["fitGrow"]


def test_text_growth_never_squeezes_a_neighbouring_table(tmp_path):
    on = _compile(_FIT / "s10-panel-beside-table-gj-h1.xml", tmp_path / "on")
    assert table_spill(tmp_path / "on" / "presentation.pptx") == 0
    assert not any(re.search(r"text x1\.[1-9]", r) for r in on["fitGrow"]), on["fitGrow"]


def test_fixed_height_table_rows_are_sized_for_the_18px_default(tmp_path):
    """<Td> without fontSize renders at POM's 18 px; fitTables measured it at 14 px (rows 36 px for
    text that wraps to two 18 px lines)."""
    rows = "".join(f"<Tr><Td>R{i}</Td><Td>Spend is not governed tightly enough</Td></Tr>" for i in range(4))
    xml = tmp_path / "t.xml"
    xml.write_text('<Theme accent="2563EB" /><Slide><VStack w="1280" h="720" padding="40" gap="20"><HStack gap="20">'
                   f'<VStack w="400" padding="16"><Table h="400"><Col width="100" /><Col />{rows}</Table></VStack>'
                   '<VStack w="max"><Text>x</Text></VStack></HStack></VStack></Slide>', encoding="utf-8")
    on = _compile(xml, tmp_path / "on")
    assert int(re.search(r'defaultRowHeight="(\d+)"', on["xml"]).group(1)) >= 2 * 18 * 1.3


def test_kpi_values_grow_with_their_unit_span_in_a_growing_tile_row(tmp_path):
    """s11 CHEFFIN exec summary (1b306e1de67f slide 2): the KPI row takes the spare height (grow
    fallback) and its hero numbers, frozen as >= 24 px text, stayed 30 px in tall empty tiles."""
    on = _compile(_FIT / "s11-kpi-row-grows-cheffin.xml", tmp_path / "on")
    grown = [int(m.group(1)) for r in on["fitGrow"] for m in [re.search(r"KPI values x\d\.\d+ \(30 -> (\d+)px\)", r)] if m]
    assert grown and 40 <= grown[0] <= 96, on["fitGrow"]  # composer: as large as the tile allows
    value = re.search(r'<Text[^>]*\sfontSize="(\d+)"[^>]*>₹114\.9<Span fontSize="(\d+)"', on["xml"])
    assert value and int(value.group(1)) >= 40 and int(value.group(2)) > 16
    sizes = set(re.findall(r'<Text[^>]*\sfontSize="(\d+)" bold="true" color="\$(?:textMain|negative)">[₹0-9]', on["xml"]))
    assert len(sizes) == 1, sizes  # peer tiles keep one number size


def _header_slide(tmp_path, headline: str, font: str = ""):
    xml = tmp_path / "h.xml"
    xml.write_text('<Theme accent="F5821F" textMain="041E42" textMuted="4E5D6E" />'
                   '<Slide><VStack w="1280" h="720" padding="36" gap="14"><VStack gap="4">'
                   '<Text fontSize="14" bold="true" letterSpacing="2">CORE PROBLEM</Text>'
                   f'<Text fontSize="30" bold="true"{font}>{headline}</Text>'
                   '<Text fontSize="14">FLIPCART: ₹31.1 vs ₹10.7 · ZAROMA: ₹46.2 vs ₹14.8</Text></VStack>'
                   '<VStack grow="1" padding="18" backgroundColor="FFFFFF"><Text fontSize="16">Chart card</Text></VStack>'
                   '</VStack></Slide>', encoding="utf-8")
    return _compile(xml, tmp_path / "on")


def test_headline_at_the_wrap_edge_reserves_its_second_line(tmp_path):
    """CHEFFIN cf98c42b5371 slide 3: POM laid the headline out on 1 line (39 px box); the
    renderer wrapped it to 2 and the second line ran into the subtitle."""
    on = _header_slide(tmp_path, "CPC is nearly 3x higher than what current conversion economics can support.")
    assert any("heading 1 -> 2 lines reserved" in r for r in on["fitGrow"]), on["fitGrow"]
    assert re.search(r'<Text[^>]*\sminH="\d+"[^>]*>CPC is nearly', on["xml"])


def test_headline_in_a_loaded_font_is_measured_at_full_width(tmp_path):
    """§10g-1: Inter is loaded from src/node/fonts/, so POM measures its real width; at 85% of
    the box this headline (~1070 px in a 1208 px box) "wrapped" and got a line the renderer
    never drew (blank band under the headline). At full width it stays on one line."""
    on = _header_slide(tmp_path, "CPC is nearly 3x higher than what current conversion economics support",
                       ' fontFamily="Inter"')
    assert not any("lines reserved" in r for r in on["fitGrow"]), on["fitGrow"]


def test_short_headline_is_left_alone(tmp_path):
    on = _header_slide(tmp_path, "CPC is 3x too high")
    assert not any("lines reserved" in r for r in on["fitGrow"]), on["fitGrow"]


def test_lone_hero_stat_grows_past_tile_size_but_not_its_microstats_or_headline(tmp_path):
    """A (Genspark hero stat): the one number the headline rests on, 72 -> up to 120 px."""
    on = _compile(_FIT / "s12-hero-stat.xml", tmp_path / "on")
    assert sum("hero stat" in r for r in on["fitGrow"]) == 1, on["fitGrow"]
    hero = re.search(r'<Text[^>]*\sfontSize="(\d+)"[^>]*>0\.33<Span fontSize="(\d+)"', on["xml"])
    assert hero and int(hero.group(1)) >= 96 and int(hero.group(2)) > 36
    micro = re.search(r'<Text[^>]*\sfontSize="(\d+)"[^>]*>₹114\.9', on["xml"])
    assert micro and int(micro.group(1)) < 48
    assert re.search(r'<Text[^>]*\sfontSize="28"[^>]*>The account is spending', on["xml"])


def test_card_text_fills_tall_cards_like_the_composer(tmp_path):
    """2026-10-06 "Q4 Priorities": three tall cards (title 20 / body 16) grew x1.05 only. The card
    title "Ship analytics v2 dashboard" sat at its wrap edge (85% width), "headings never gain a
    line" stopped the whole group, and the space went into lineHeight 1.6. Now sized as the
    composer does (user, 2026-10-06): title <= 48px, body <= title / 1.3, peers one size."""
    on = _compile(_FIT / "s13-card-titles-at-wrap-edge.xml", tmp_path / "on")
    titles = {int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" color="\$textMain" bold="true">(?:Close|Launch|Ship)', on["xml"])}
    bodies = {int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" color="\$textMuted">', on["xml"])}
    assert len(titles) == 1 and len(bodies) == 1, (titles, bodies)  # peer cards keep one size
    title, body = titles.pop(), bodies.pop()
    assert 36 <= title <= 48, title
    assert 24 <= body <= title / 1.3, (body, title)
    assert all(float(v) <= 1.45 for v in re.findall(r'lineHeight="([\d.]+)"', on["xml"]))
    titles_lh = re.findall(r'<Text[^>]*\slineHeight="([\d.]+)"[^>]*bold="true">(?:Close|Launch|Ship)', on["xml"])
    assert not titles_lh, titles_lh               # titles keep their line height; only body text spreads


def test_kpi_row_shares_the_height_a_sparse_callout_took(tmp_path):
    """2026-10-06 exec summary: the callout had grow="1" and took all the spare height for two
    lines; the KPI tiles stayed at content height, so their numbers never grew. Then the row
    grew as one block: "ARR" (caps label) and "Gross Margin" (body) got different sizes."""
    on = _compile(_FIT / "s14-kpi-row-beside-sparse-callout.xml", tmp_path / "on")
    assert any("KPI row takes a share" in r for r in on["fitGrow"]), on["fitGrow"]
    numbers = {int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" bold="true" color="\$(?:textMain|surfaceAlt)">[$0-9]', on["xml"])}
    labels = {int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" color="\$(?:textMuted|surfaceAlt)">(?:ARR|NRR|Gross|CAC)', on["xml"])}
    deltas = {int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" bold="true" color="\$(?:positive|negative|warning)">', on["xml"])}
    assert len(numbers) == 1 and len(labels) == 1 and len(deltas) == 1, (numbers, labels, deltas)  # one size per slot
    number, label, delta = numbers.pop(), labels.pop(), deltas.pop()
    assert number >= 48
    assert 14 < label <= 0.45 * number + 1 and 14 < delta <= 0.45 * number + 1, (number, label, delta)  # only the number is big
