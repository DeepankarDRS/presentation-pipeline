"""Component-level geometry check (src/compiler/geometry_audit.py, 2026-10-07): each rule on a
small slide compiled by the real compiler (fit-grow off, so the defect stays in place)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from src.compiler.geometry_audit import audit_run_folder

ROOT = Path(__file__).resolve().parents[2]
COMPILER = ROOT / "src" / "node" / "compile-pom.js"

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


def _audit(xml: str, tmp_path: Path, slide_type: str = "") -> dict[str, list[str]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = tmp_path / "in.xml"
    src.write_text(xml, encoding="utf-8")
    subprocess.run(["node", str(COMPILER), str(src), str(tmp_path / "out")], capture_output=True,
                   timeout=120, check=True, env={**os.environ, "POM_FIT_GROW": "0"})
    out: dict[str, list[str]] = {}
    for i in audit_run_folder(tmp_path / "out", slide_type=slide_type):
        out.setdefault(i["code"], []).append(i["message"])
    return out


def _rows(n: int) -> str:
    return "".join(f"<Tr><Td>row {i}</Td><Td>{i}</Td></Tr>" for i in range(n))


def test_squeezed_table_spills_into_the_next_card(tmp_path):
    xml = (f'<Slide><VStack w="1280" h="720" padding="40" gap="20">'
           f'<VStack h="120" backgroundColor="FFFFFF"><Table>{_rows(5)}</Table></VStack>'
           f'<VStack h="80"><Flow direction="horizontal"><FlowNode id="a" shape="flowChartProcess" text="One"/>'
           f'<FlowNode id="b" shape="flowChartProcess" text="Two"/><FlowConnection from="a" to="b"/></Flow></VStack>'
           f'<VStack grow="1" backgroundColor="FFFFFF"><Text>tail</Text></VStack></VStack></Slide>')
    found = _audit(xml, tmp_path)
    assert any("bottom by 40px" in m and "rows 160px in a 120px frame" in m for m in found["GEOM_SPILL"])
    assert any("draws over flow" in m for m in found["GEOM_COLLISION"])


def test_wide_table_runs_under_the_card_beside_it(tmp_path):
    cols = "".join('<Col width="160" />' for _ in range(5))
    cells = "".join(f"<Td>value {i}</Td>" for i in range(5))
    xml = (f'<Slide><VStack w="1280" h="720" padding="40"><HStack gap="20" h="300">'
           f'<VStack w="400" backgroundColor="FFFFFF"><Table>{cols}<Tr>{cells}</Tr></Table></VStack>'
           f'<VStack grow="1" backgroundColor="FFFFFF"><Text>beside</Text></VStack></HStack></VStack></Slide>')
    found = _audit(xml, tmp_path)
    if "GEOM_SPILL" not in found:
        pytest.skip("POM fitted the columns into the box on this version")
    assert any("right by" in m for m in found["GEOM_SPILL"])


def test_text_over_text_in_a_layer_and_off_the_slide(tmp_path):
    xml = ('<Slide><VStack w="1280" h="720" padding="40"><Layer w="600" h="200">'
           '<Text x="0" y="0" w="300" h="30" fontSize="20">Channels label</Text>'
           '<Text x="20" y="5" w="300" h="30" fontSize="20">Website text</Text>'
           '<Text x="500" y="100" w="900" h="30" fontSize="20">far right</Text>'
           '</Layer></VStack></Slide>')
    found = _audit(xml, tmp_path)
    assert any('"Channels label" and text "Website text"' in m for m in found["GEOM_COLLISION"])
    assert "GEOM_OFF_SLIDE" in found


def test_tall_card_with_little_content_and_a_sparse_slide(tmp_path):
    xml = ('<Slide><VStack w="1280" h="720" padding="40" gap="20">'
           '<HStack h="300" gap="20"><VStack w="max" padding="16" backgroundColor="FFFFFF"><Text fontSize="20">ARR</Text></VStack>'
           '<VStack w="max" padding="16" backgroundColor="FFFFFF"><Text fontSize="20">NRR</Text></VStack></HStack>'
           '</VStack></Slide>')
    found = _audit(xml, tmp_path)
    assert len(found["GEOM_CARD_EMPTY"]) == 2
    assert "GEOM_SLIDE_SPARSE" in found
    assert "GEOM_SLIDE_SPARSE" not in _audit(xml, tmp_path / "cover", slide_type="cover")


def test_a_full_clean_slide_has_no_findings(tmp_path):
    xml = ('<Slide><VStack w="1280" h="720" padding="40" gap="20">'
           '<Text fontSize="32" bold="true">Headline</Text>'
           '<HStack grow="1" gap="20">'
           + "".join('<VStack w="max" padding="16" gap="8" backgroundColor="FFFFFF" justifyContent="center">'
                     '<Text fontSize="24">Label</Text><Text fontSize="24">' + "A sentence of body text. " * 22 + '</Text></VStack>'
                     for _ in range(3))
           + '</HStack></VStack></Slide>')
    assert _audit(xml, tmp_path) == {}
