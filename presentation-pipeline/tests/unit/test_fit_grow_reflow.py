"""fit-grow's reflow of code-drawn rows too narrow for their words (docs/syntax-audit-2026-11-04.md, decision 2)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.compiler.nodes import composed, tiles
from src.compiler.normalizer import normalize_xml
from src.agents.style_resolver import resolve_theme

_COMPILER = Path(__file__).resolve().parents[2] / "src" / "node" / "compile-pom.js"
KPIS = {"component_id": "kpis", "kind": "kpi_row", "content_data": {
    "kpi_labels": ["ARR", "Net revenue retention", "Gross margin", "CAC payback"], "kpi_values": ["$48.2M", "114%", "72.1%", "14 months"],
    "kpi_deltas": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"]}}
TABLE = {"component_id": "gaps", "kind": "table", "content_data": {
    "table_columns": ["Area", "Marketplace", "Fix"], "table_rows": [["Reach", "Sponsored placement", "Reallocate"], ["Spend", "Category banners", "Consolidate"]]}}
NOTE = '<VStack grow="1" w="1"><Text fontSize="16" color="$textMain">The note beside the block.</Text></VStack>'


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "kpi_row,table")
    monkeypatch.setenv("POM_BLOCKS", "tiles")


def compile_tag(tmp_path, body, comp):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    plan = {"components": [comp], "slide_title": "H"}
    filled = tiles.fill(composed.expand(body, plan)["xml"], plan)
    slide = (f'<Slide><VStack w="1280" h="720" padding="48" gap="20" alignItems="stretch" backgroundColor="$surface">'
             f'<Text fontSize="36" color="$textMain" bold="true">Heading</Text>{filled["xml"]}</VStack></Slide>')
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + normalize_xml(slide)["cleaned_xml"], encoding="utf-8")
    out = tmp_path / "out"
    subprocess.run(["node", str(_COMPILER), str(xml), str(out)], capture_output=True, timeout=120)
    return json.loads((out / "compile-result.json").read_text(encoding="utf-8"))


def reflows(r):
    return [x for x in r.get("fitGrow") or [] if "too narrow" in x]


def test_a_strip_in_a_narrow_box_compiles_and_reflows(tmp_path):
    body = f'<HStack grow="1" gap="20"><VStack w="280"><KpiRow ref="kpis" variant="strip" grow="1"/></VStack>{NOTE}</HStack>'
    r = compile_tag(tmp_path, body, KPIS)
    assert reflows(r) and not [x for x in r["fitGrow"] if "failed to build" in x]
    assert (tmp_path / "out" / "presentation.pptx").exists()


def test_a_row_with_room_stays_a_row(tmp_path):
    r = compile_tag(tmp_path, '<KpiRow ref="kpis" variant="strip" grow="1"/>', KPIS)
    assert not reflows(r)


def test_table_cells_are_not_taken_apart(tmp_path):
    body = f'<HStack grow="1" gap="20"><VStack w="280"><Table ref="gaps" variant="grid" grow="1"/></VStack>{NOTE}</HStack>'
    assert not reflows(compile_tag(tmp_path, body, TABLE))
