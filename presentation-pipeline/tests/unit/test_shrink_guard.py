"""Step 0.3: fit-grow's shrink guard (LLM-free, real compiler, Inter measured from src/node/fonts/).

A word wider than its box is widened for (table columns), then shrunk for (never below the floor),
then reported as a WORD_TOO_WIDE compile warning. It never grows anything and runs twice to the same XML.
Fixtures: tests/fixtures/shrink_guard/.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_FIX = _ROOT / "tests" / "fixtures" / "shrink_guard"
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"


def _compile(xml: Path, out: Path) -> dict:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    subprocess.run(["node", str(_COMPILER), str(xml), str(out)], check=True, capture_output=True, timeout=120,
                   env={**os.environ, "POM_FIT_GROW": "1"})
    result = json.loads((out / "compile-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "success"
    fitted = out / "fitted.xml"
    result["xml"] = fitted.read_text(encoding="utf-8") if fitted.exists() else xml.read_text(encoding="utf-8")
    return result


def _guard_lines(result: dict) -> list[str]:
    return [r for r in result["fitGrow"] if "wider than" in r or "a word is wider" in r]


def _warnings(result: dict) -> list[str]:
    return [w["message"] for w in result.get("warnings", []) if w["code"] == "WORD_TOO_WIDE"]


def _size(xml: str, node_id: str) -> int:
    return int(re.search(rf'<\w+\b[^>]*\sid="{node_id}"[^>]*?\sfontSize="(\d+)"', xml).group(1))


def test_a_word_wider_than_its_box_shrinks_to_fit_and_a_fitting_word_is_left_alone(tmp_path):
    r = _compile(_FIX / "g1-text-list.xml", tmp_path)
    # "Recommendation" at 22px is ~180px in a ~140px box: the largest size that fits, above the 14px floor
    assert 14 < _size(r["xml"], "rec") < 22
    assert not any("Recommendation" in w for w in _warnings(r))
    assert _size(r["xml"], "fits") >= 22     # never shrunk (text growth may enlarge a word that still fits)
    assert _size(r["xml"], "hyphen") >= 22   # "Cost-per-acquisition" breaks at its hyphens, so no piece is too wide


def test_a_text_without_fontsize_gets_one_written(tmp_path):
    r = _compile(_FIX / "g1-text-list.xml", tmp_path)
    unsized = re.search(r'<Text\b[^>]*>Implementation</Text>', r["xml"]).group(0)
    assert re.search(r'fontSize="(\d+)"', unsized) and int(re.search(r'fontSize="(\d+)"', unsized).group(1)) < 24


def test_a_big_number_never_goes_below_28px(tmp_path):
    r = _compile(_FIX / "g1-text-list.xml", tmp_path)
    assert _size(r["xml"], "narrow-num") >= 28          # the number's floor


def test_a_word_that_cannot_fit_even_at_its_floor_goes_to_the_floor_and_is_reported(tmp_path):
    r = _compile(_FIX / "g1-text-list.xml", tmp_path)
    assert _size(r["xml"], "list") == 14                 # the body floor: less overflow than at 20px
    assert any("Internationalization" in m and "smallest allowed" in m for m in _warnings(r))


def test_a_table_column_is_widened_from_the_columns_with_spare(tmp_path):
    r = _compile(_FIX / "g2-table.xml", tmp_path)
    first_table = r["xml"].split("</Table>")[0]
    widths = [int(w) for w in re.findall(r'<Col width="(\d+)"', first_table)]
    assert widths[0] > 110 and sum(widths) == 700       # "Recommendation" got room, the table kept its width
    assert any("table columns widened" in line for line in _guard_lines(r))


def test_a_table_with_no_spare_that_cannot_be_fixed_is_reported(tmp_path):
    r = _compile(_FIX / "g2-table.xml", tmp_path)
    assert any("table cell" in m and "Recommendation" in m for m in _warnings(r))


def test_chevron_labels_shrink_to_fit_or_are_reported(tmp_path):
    r = _compile(_FIX / "g3-arrow.xml", tmp_path)
    assert 14 < _size(r["xml"], "fits-smaller") < 18    # a smaller size is enough: not the floor
    msgs = _warnings(r)
    assert len(msgs) == 1 and "process step" in msgs[0] and "smallest allowed" in msgs[0]


@pytest.mark.parametrize("name", ["g1-text-list", "g2-table", "g3-arrow"])
def test_compiling_the_fitted_xml_again_changes_nothing(tmp_path, name):
    """Idempotent: the font sizes and warnings of a second pass equal the first's, so the guard never
    ping-pongs with the growers and never shrinks again what already fits. (Column widths are left out:
    fit-grow's own column planning re-plans them when the cell type changed, which is not the guard.)"""
    first = _compile(_FIX / f"{name}.xml", tmp_path / "a")
    fitted = tmp_path / f"{name}-fitted.xml"
    fitted.write_text(first["xml"], encoding="utf-8")
    second = _compile(fitted, tmp_path / "b")
    sizes = lambda xml: re.findall(r'fontSize="(\d+)"', xml)  # noqa: E731
    assert sizes(second["xml"]) == sizes(first["xml"])
    if name != "g2-table":  # a table's columns are re-planned by fit-grow's own pass, so its warning may differ
        assert _warnings(second) == _warnings(first)


def test_a_slide_where_every_word_fits_has_no_guard_edits(tmp_path):
    xml = tmp_path / "fits.xml"
    xml.write_text(
        '<Theme surface="FFFFFF" textMain="111827" />\n<Slide><VStack w="1280" h="720" padding="40" gap="12">'
        '<Text fontSize="30" bold="true" fontFamily="Inter">All words fit their boxes</Text>'
        '<Text fontSize="16" fontFamily="Inter">A short paragraph with ordinary words only.</Text>'
        '</VStack></Slide>', encoding="utf-8")
    r = _compile(xml, tmp_path / "out")
    assert _guard_lines(r) == [] and _warnings(r) == []


def test_a_pinned_column_takes_width_from_its_wider_pinned_neighbour(tmp_path):
    """2026-10-07 (gj-h1 slide 14 in R1's replay): growing the left column's text pinned both w="max" columns, and
    the KPI numbers in the narrow right column ("₹59.8", "5.30x", 28px, at their floor) broke. The guard widens a
    box fit-grow pinned, innermost first, from its wider pinned neighbour; the second pass makes no guard edit."""
    first = _compile(_FIX / "g4-pinned-columns.xml", tmp_path / "a")
    assert any("column widened" in r for r in first["fitGrow"]), first["fitGrow"]
    assert _warnings(first) == []
    assert all(int(v) >= 28 for v in re.findall(r'fontSize="(\d+)" color="\$(?:positive|accent)" bold="true"[^>]*>[₹\d-]', first["xml"]))
    fitted = tmp_path / "g4-fitted.xml"
    fitted.write_text(first["xml"], encoding="utf-8")
    second = _compile(fitted, tmp_path / "b")
    assert not any("column widened" in r or "wider than" in r for r in second["fitGrow"]) and _warnings(second) == []
