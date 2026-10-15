"""fit-grow fillLoneRows: a lone row of cards still short of the band it sits in after growth takes the band
(tile same-plan check pair 1.2, QBR: four <Kpi> tags in the LLM's own HStack inside grow="3", numbers width-bound
at 65 px, ~150 px of the band empty). LLM-free, real compiler."""

import re

import pytest

from src.agents.style_resolver import resolve_theme
from tests.unit.test_fit_grow_tables import _compile

_PLAN = {"components": [{"component_id": "k", "kind": "kpi_row", "count": 4, "content_data": {
    "kpi_labels": ["ARR", "NRR", "Gross Margin", "CAC Payback"], "kpi_values": ["$48.2M", "114%", "72.1%", "14 months"],
    "kpi_deltas": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"]}}]}


@pytest.fixture(autouse=True)
def tiles_on(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")


def _fit(tmp_path, band):
    from src.compiler.nodes import tiles
    from src.compiler.normalizer import normalize_xml
    res = tiles.fill('<Slide><VStack w="1280" h="720" padding="48" gap="28" alignItems="stretch" backgroundColor="$surface">'
                     '<Text fontSize="36" color="$textMain" bold="true">ARR and NRR up; Gross Margin down slightly</Text>'
                     f'{band}<VStack grow="1" backgroundColor="$textMain" padding="24"><Text fontSize="16" color="$surface">'
                     'Momentum is driven by ARR growth and rising NRR.</Text></VStack></VStack></Slide>', _PLAN)
    assert res["ok"], res["issues"]
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + normalize_xml(res["xml"])["cleaned_xml"], encoding="utf-8")
    return _compile(xml, tmp_path / "on")


def test_lone_tile_row_in_a_growing_band_takes_the_band(tmp_path):
    kpis = "".join(f'<Kpi ref="k.{i}" variant="filled"/>' for i in range(4))
    res = _fit(tmp_path, f'<VStack grow="3"><HStack gap="28" alignItems="stretch">{kpis}</HStack></VStack>')
    row = re.search(r'<HStack\b[^>]*gap="28"[^>]*>', res["xml"]).group(0)
    assert 'grow="1"' in row and any("lone row" in r for r in res["fitGrow"])


def test_row_whose_tiles_grow_into_the_band_is_left_alone(tmp_path):
    """A KPI row not wrapped in its own band grows by content (shareHeight / growStats): nothing left to stretch."""
    kpis = "".join(f'<Kpi ref="k.{i}" variant="filled"/>' for i in range(4))
    res = _fit(tmp_path, f'<HStack gap="28" alignItems="stretch">{kpis}</HStack>')
    assert not any("lone row" in r for r in res["fitGrow"])


_ENERGY_GRID = (  # corpus slide befb484584 (LLM-drawn 3 + 3 grid in a grow="2" band), as saved
    '<Slide>'
    '<VStack w="1280" h="720" padding="40" gap="22" alignItems="stretch" backgroundColor="$surface">'
    '<VStack gap="8">'
    '<Text fontFamily="Inter" fontSize="14" color="$accentText" bold="true" letterSpacing="2">CATEGORY</Text>'
    '<Text fontFamily="Inter" fontSize="36" color="$textMain" bold="true" lineHeight="1.15">Why the Energy Drink Category is Built for <Span color="$accentText">Quick Commerce</Span></Text>'
    '</VStack>'
    '<VStack grow="2" gap="18">'
    '<VStack gap="18">'
    '<HStack gap="18" alignItems="stretch">'
    '<VStack w="32%" padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" justifyContent="center">'
    '<Icon name="clock" size="28" color="$accent" alignSelf="start" />'
    '<Text fontFamily="Inter" fontSize="18" color="$textMain" bold="true">Pre-workout consumption</Text>'
    '</VStack>'
    '<VStack w="32%" padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" justifyContent="center">'
    '<Icon name="clock" size="28" color="$accent" alignSelf="start" />'
    '<Text fontFamily="Inter" fontSize="18" color="$textMain" bold="true">Gaming sessions</Text>'
    '</VStack>'
    '<VStack w="32%" padding="20" gap="10" backgroundColor="$textMain" borderRadius="14" justifyContent="center">'
    '<Icon name="clock" size="28" color="$accentAlt" alignSelf="start" />'
    '<Text fontFamily="Inter" fontSize="18" color="$surfaceAlt" bold="true">Late-night work/study</Text>'
    '</VStack>'
    '</HStack>'
    '<HStack gap="18" alignItems="stretch">'
    '<VStack w="32%" padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" justifyContent="center">'
    '<Icon name="clock" size="28" color="$accent" alignSelf="start" />'
    '<Text fontFamily="Inter" fontSize="18" color="$textMain" bold="true">Travel &amp; commuting</Text>'
    '</VStack>'
    '<VStack w="32%" padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" justifyContent="center">'
    '<Icon name="clock" size="28" color="$accent" alignSelf="start" />'
    '<Text fontFamily="Inter" fontSize="18" color="$textMain" bold="true">Party &amp; social occasions</Text>'
    '</VStack>'
    '<VStack w="32%" padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" justifyContent="center">'
    '<Icon name="clock" size="28" color="$accent" alignSelf="start" />'
    '<Text fontFamily="Inter" fontSize="18" color="$textMain" bold="true">Instant energy requirements</Text>'
    '</VStack>'
    '</HStack>'
    '</VStack>'
    '</VStack>'
    '<VStack gap="16">'
    '<VStack padding="20" gap="8" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" shadow.blur="6" shadow.offset="2" shadow.color="000" justifyContent="center">'
    '<Text fontFamily="Inter" fontSize="16" color="$textMain" bold="true">Key Insight</Text>'
    '<Text fontFamily="Inter" fontSize="16" color="$textMain" lineHeight="1.4">Energy drinks have one of the strongest <Span color="$accentText">instant-need consumption behaviors</Span>, making them highly compatible with Quick Commerce.</Text>'
    '</VStack>'
    '<VStack padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" borderLeft.color="$accent" borderLeft.width="4" justifyContent="center">'
    '<HStack gap="10" alignItems="center">'
    '<Icon name="trending-up" size="18" color="$accent" />'
    '<Text fontFamily="Inter" fontSize="14" color="$textMain">Category growth drivers</Text>'
    '</HStack>'
    '<HStack gap="10" alignItems="center">'
    '<Icon name="clock" size="18" color="$accent" />'
    '<Text fontFamily="Inter" fontSize="14" color="$textMain">Consumer demand moments</Text>'
    '</HStack>'
    '<HStack gap="10" alignItems="center">'
    '<Icon name="zap" size="18" color="$accent" />'
    '<Text fontFamily="Inter" fontSize="14" color="$textMain">Impulse purchase behaviour</Text>'
    '</HStack>'
    '</VStack>'
    '</VStack>'
    '</VStack>'
    '</Slide>'
)


def test_stretched_grid_grows_its_cards_as_one_group(tmp_path):
    """The cards of a grid fillLoneRows stretched share one size across rows: regrown row by row, this grid drew
    row 1 at 22 px and row 2 at 11 (corpus 2026-10-14)."""
    xml = tmp_path / "g.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + _ENERGY_GRID, encoding="utf-8")
    res = _compile(xml, tmp_path / "on")
    assert any("lone row" in r for r in res["fitGrow"])
    names = ["Pre-workout", "Gaming", "Late-night", "Travel", "Party", "Instant"]
    sizes = [float(re.search(r'fontSize="([\d.]+)"[^>]*>' + n, res["xml"]).group(1)) for n in names]
    assert len(set(sizes)) == 1 and sizes[0] > 18, sizes
