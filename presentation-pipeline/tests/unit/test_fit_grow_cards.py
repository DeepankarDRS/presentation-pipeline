"""fit-grow on code-laid cards (cards.py, POM_BLOCKS=tiles; card gallery 2026-10-13; LLM-free, real compiler).

regridCards: cards.py picks a <CardGrid>'s columns from its text alone; four short cards in one row of a tall
band, or in a half-width column, stayed at 16-20 px in empty cards. A layout with fewer columns is kept when its
smallest title ends >= 15% larger. A card's numeral ("01") grows as text, never as a KPI number.
"""

import re

import pytest

from tests.unit.test_fit_grow_kpi_row import _THEME
from tests.unit.test_fit_grow_tables import _compile

_PILLARS = {"components": [{"component_id": "pillars", "kind": "card_grid", "count": 4, "content_data": {
    "card_layout": "grid", "cards": [{"title": "Visibility", "body": "Search and home placement"},
                                     {"title": "Pricing", "body": "Price-pack fit"},
                                     {"title": "Assortment", "body": "Range per city"},
                                     {"title": "Supply", "body": "Fill rate above 95%"}]}}]}


@pytest.fixture(autouse=True)
def tiles_on(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")


def _slide(tmp_path, body, plan=_PILLARS):
    from src.compiler.nodes import tiles
    res = tiles.fill(f'<Slide><VStack w="1280" h="720" padding="48" gap="28" alignItems="stretch" backgroundColor="$surface">'
                     f'<Text fontSize="34" color="$textMain" bold="true">Four levers decide the quarter</Text>{body}</VStack></Slide>',
                     plan)
    assert res["ok"], res["issues"]
    xml = tmp_path / "t.xml"
    xml.write_text(_THEME + res["xml"], encoding="utf-8")
    return _compile(xml, tmp_path / "on")


def _titles(xml):
    return [int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)"[^>]*\sid="cardt-pillars-\d"', xml)]


def test_four_short_cards_in_a_tall_band_take_two_rows(tmp_path):
    on = _slide(tmp_path, '<CardGrid ref="pillars"/>')
    assert any("cards of pillars 2 per row" in r for r in on["fitGrow"]), on["fitGrow"]
    titles = _titles(on["xml"])
    assert len(titles) == 4 and len(set(titles)) == 1 and titles[0] >= 44, (titles, on["fitGrow"])


def test_columns_the_llm_asked_for_are_kept(tmp_path):
    on = _slide(tmp_path, '<CardGrid ref="pillars" cols="4"/>')
    assert not any("cards of" in r for r in on["fitGrow"]), on["fitGrow"]


def test_a_card_numeral_grows_as_text_not_as_a_kpi_number(tmp_path):
    on = _slide(tmp_path, '<CardGrid ref="pillars" variant="numerals" cols="4"/>')
    assert not any("KPI values" in r or "hero stat" in r for r in on["fitGrow"]), on["fitGrow"]
    nums = [int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)"[^>]*\sid="cardn-pillars-\d"', on["xml"])]
    titles = _titles(on["xml"])
    assert nums and titles and max(nums) <= 72 and min(titles) > 20, (nums, titles, on["fitGrow"])
