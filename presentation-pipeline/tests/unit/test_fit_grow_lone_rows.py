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
