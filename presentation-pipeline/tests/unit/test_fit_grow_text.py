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
