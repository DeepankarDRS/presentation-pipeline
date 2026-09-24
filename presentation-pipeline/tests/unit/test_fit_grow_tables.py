"""Phase 5 Step 3 — fit-grow sizes a Table without h from its text (LLM-free, real compiler).

Fixtures in tests/fixtures/fit_grow/: s6 (phase-1 slide 10, over-full slide), s7 (phase-1 slide 11,
stretched table card), s8 (synthetic: fat generator rows squeeze the table), s1/s2/s5 (old-style
Table h, handled by fitTables as before); tests/fixtures/layout_sizing/s1-dashboard (three peer tables).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.eval_metrics import empty_cells, table_spill

_ROOT = Path(__file__).resolve().parents[2]
_FIT = _ROOT / "tests" / "fixtures" / "fit_grow"
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"


def _compile(xml: Path, out: Path, fit_grow: bool = True) -> dict:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    subprocess.run(["node", str(_COMPILER), str(xml), str(out)], check=True, capture_output=True, timeout=120,
                   env={**os.environ, "POM_FIT_GROW": "1" if fit_grow else "0"})
    result = json.loads((out / "compile-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "success"
    fitted = out / "fitted.xml"
    result["xml"] = fitted.read_text(encoding="utf-8") if fitted.exists() else xml.read_text(encoding="utf-8")
    return result


def _td_fonts(xml: str) -> list[int]:
    return [int(f) for f in re.findall(r'<Td\b[^>]*?\sfontSize="(\d+)"', xml)]


def test_squeezed_table_is_tightened_and_protected(tmp_path):
    xml = _FIT / "s8-fat-rows-squeezed.xml"
    off = _compile(xml, tmp_path / "off", fit_grow=False)
    on = _compile(xml, tmp_path / "on")
    assert table_spill(tmp_path / "off" / "presentation.pptx") > 40  # rows 460 px in a ~403 px box
    assert table_spill(tmp_path / "on" / "presentation.pptx") == 0
    assert any("box protected (minH)" in r for r in on["fitGrow"])
    assert re.search(r'<Table\b[^>]*\sminH="\d+"', on["xml"])
    assert _td_fonts(on["xml"]) == _td_fonts(off["xml"])  # fonts untouched


def test_over_full_slide_is_reported_not_protected(tmp_path):
    """Phase-1 slide 10: header + table + chart band (minH 180) + note exceed 720 even with tight rows.
    Protecting the table would make POM's autoFit shrink fonts, so rows are only tightened and reported."""
    xml = _FIT / "s6-wrapped-table-phase1.xml"
    on = _compile(xml, tmp_path / "on")
    assert any("over-full slide" in r for r in on["fitGrow"])
    assert "minH" not in re.search(r"<Table\b[^>]*>", on["xml"]).group(0)
    spill_off = 105  # measured on the phase-1 replay: 280 px of rows in a 175 px frame
    assert 0 < table_spill(tmp_path / "on" / "presentation.pptx") < spill_off
    assert min(_td_fonts(on["xml"])) >= 14
    # rows never taller than the generator's (40 px): taller rows would only squeeze the rest of the slide
    assert all(int(h) <= 40 for h in re.findall(r'<Tr\b[^>]*\sheight="(\d+)"', on["xml"]))


def test_main_table_grows_into_its_card(tmp_path):
    """Phase-1 slide 11: the widths that wrap fewer lines, then text (<= 18 px) and rows into dead space."""
    xml = _FIT / "s7-stretched-table-card-phase1.xml"
    before = _td_fonts(xml.read_text(encoding="utf-8"))
    on = _compile(xml, tmp_path / "on")
    assert any("main table into spare height" in r for r in on["fitGrow"])
    after = _td_fonts(on["xml"])
    assert all(b <= a <= max(b, 18) for b, a in zip(before, after)) and after != before
    widths = [int(w) for w in re.findall(r'<Col\b[^>]*\swidth="(\d+)"', on["xml"])]
    assert widths.index(max(widths)) == 2  # "Key Actions", the longest text, gets the widest column
    assert table_spill(tmp_path / "on" / "presentation.pptx") == 0


@pytest.mark.parametrize("name", ["s1-performance-overview.xml", "s2-flipcart-kpis.xml", "s5-review-edge-cases.xml"])
def test_old_style_table_h_keeps_fit_tables(tmp_path, name):
    on = _compile(_FIT / name, tmp_path / "on")
    table = [r for r in on["fitGrow"] if "table" in r]
    assert table and all("box clamped to rows" in r for r in table)


def test_peer_tables_keep_one_size(tmp_path):
    """Three equal tables in stacked panels: no table is 'the main one', so none grows alone."""
    on = _compile(_ROOT / "tests" / "fixtures" / "layout_sizing" / "s1-dashboard.xml", tmp_path / "on")
    assert not [r for r in on["fitGrow"] if "table" in r]


def test_grown_text_never_breaks_a_word(tmp_path):
    """gj-h1 golden 11: 13 px cells grow to 18 px; the fixed 90 px city column must widen so that
    'Hyderabad' (bold 18 px = 107 px in POM's measure) does not break mid-word."""
    on = _compile(_ROOT / "tests" / "fixtures" / "golden" / "gj-h1-deck" / "11-geo-daypart.xml", tmp_path / "on")
    first_col = int(re.search(r'<Col\b[^>]*\swidth="(\d+)"', on["xml"]).group(1))
    if max(_td_fonts(on["xml"])) >= 18:
        assert first_col >= 108


def test_cells_without_font_get_body_size(tmp_path):
    """POM's Td default is 18 px, bigger than the 14 px body text: fit-grow writes 14 (never below it)."""
    xml = tmp_path / "t.xml"
    xml.write_text(
        '<Slide><VStack w="1280" h="720" padding="36" gap="14">'
        '<VStack w="560" padding="16"><Table defaultRowHeight="40"><Col width="140" /><Col /><Col /><Col /><Col /><Col />'
        '<Tr><Td bold="true">Platform</Td><Td>Spend</Td><Td>Sales</Td><Td>ROI</Td><Td>ACOS</Td><Td>Share</Td></Tr>'
        '<Tr><Td>Hyderabad</Td><Td>23.2 L</Td><Td>1.20 Cr</Td><Td>5.16x</Td><Td>19.4%</Td><Td>67%</Td></Tr>'
        '</Table></VStack>'
        '<VStack grow="1" padding="16"><Text fontSize="14">Notes</Text></VStack></VStack></Slide>', encoding="utf-8")
    on = _compile(xml, tmp_path / "on")
    assert any("without fontSize -> 14px" in r for r in on["fitGrow"])
    fonts = _td_fonts(on["xml"])
    assert len(fonts) == 12 and all(14 <= f <= 18 for f in fonts)


def test_empty_cells_counts_dropped_data(tmp_path):
    """A blank cell (the normalizer fills empty <Td> with a space) is counted; filled cells are not."""
    xml = tmp_path / "t.xml"
    xml.write_text(
        '<Slide><VStack w="1280" h="720" padding="36"><Table><Col /><Col /><Col />'
        '<Tr><Td fontSize="14">Blinkit</Td><Td fontSize="14"> </Td><Td fontSize="14">6.69x</Td></Tr>'
        '<Tr><Td fontSize="14">Swiggy</Td><Td fontSize="14"> </Td><Td fontSize="14"> </Td></Tr>'
        '</Table></VStack></Slide>', encoding="utf-8")
    _compile(xml, tmp_path / "on")
    assert empty_cells(tmp_path / "on" / "presentation.pptx") == 3
