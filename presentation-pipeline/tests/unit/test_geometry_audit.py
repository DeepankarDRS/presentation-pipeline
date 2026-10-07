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


# --- the spill fix in fit-grow (item 2 step 2): same slides, fit-grow on -----------------------

def _fit(xml: str, tmp_path: Path) -> tuple[dict[str, list[str]], dict]:
    import json
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = tmp_path / "in.xml"
    src.write_text(xml, encoding="utf-8")
    subprocess.run(["node", str(COMPILER), str(src), str(tmp_path / "out")], capture_output=True,
                   timeout=180, check=True)
    result = json.loads((tmp_path / "out" / "compile-result.json").read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for i in audit_run_folder(tmp_path / "out"):
        found.setdefault(i["code"], []).append(i["message"])
    return found, result


def test_fit_grow_gives_a_squeezed_table_its_rows(tmp_path):
    xml = (f'<Slide><VStack w="1280" h="720" padding="40" gap="20">'
           f'<VStack h="120" backgroundColor="FFFFFF"><Table>{_rows(5)}</Table></VStack>'
           f'<VStack h="80" backgroundColor="FFFFFF"><Text>next card</Text></VStack></VStack></Slide>')
    found, result = _fit(xml, tmp_path)
    assert "GEOM_SPILL" not in found and "GEOM_COLLISION" not in found
    assert any("spill fixed" in m or "box protected" in m for m in result["fitGrow"])


def test_fit_grow_widens_a_table_card_into_its_row(tmp_path):
    head = "".join(f"<Td>Header {i}</Td>" for i in range(6))
    cells = "".join(f"<Td>₹{i}9.5L</Td>" for i in range(6))
    xml = (f'<Slide><VStack w="1280" h="720" padding="40"><HStack gap="20" h="300">'
           f'<VStack w="max" padding="16" backgroundColor="FFFFFF"><Table><Tr>{head}</Tr><Tr>{cells}</Tr></Table></VStack>'
           f'<VStack w="max" padding="16" backgroundColor="FFFFFF"><Text>' + "beside " * 60 + '</Text></VStack>'
           f'</HStack></VStack></Slide>')
    found, _ = _fit(xml, tmp_path)
    assert "GEOM_SPILL" not in found


def test_too_dense_slide_is_left_and_reported(tmp_path):
    body = "".join(f'<VStack h="60" backgroundColor="FFFFFF"><Text fontSize="14">{"word " * 200}</Text></VStack>'
                   for _ in range(7))
    xml = f'<Slide><VStack w="1280" h="720" padding="40" gap="20">{body}</VStack></Slide>'
    _, result = _fit(xml, tmp_path)
    assert any(w["code"] == "SLIDE_DENSE" for w in result.get("warnings") or [])


def test_placeholders_and_tiers():
    from src.compiler.geometry_audit import _placeholders
    brief = "compare [Platform B] and [Platform A]"
    assert _placeholders("₹X.XX Cr", brief) == ["X.XX"]
    assert _placeholders("[Platform B] CPC", brief) == []          # the brief's own anonymised name
    assert _placeholders("[Insert chart here]", brief) == ["[Insert chart here]"]
    assert _placeholders("Insight 1 — lead with the number", brief) == ["Insight 1"]
    assert _placeholders("XTSY growth, ROAS 0.33x, XXL", brief) == []


def test_squeezed_table_spill_is_tier_error(tmp_path):
    xml = (f'<Slide><VStack w="1280" h="720" padding="40" gap="20">'
           f'<VStack h="120" backgroundColor="FFFFFF"><Table>{_rows(5)}</Table></VStack>'
           f'<VStack h="80" backgroundColor="FFFFFF"><Text>next</Text></VStack></VStack></Slide>')
    src = tmp_path / "in.xml"
    src.write_text(xml, encoding="utf-8")
    subprocess.run(["node", str(COMPILER), str(src), str(tmp_path / "out")], capture_output=True,
                   timeout=120, check=True, env={**os.environ, "POM_FIT_GROW": "0"})
    spill = [i for i in audit_run_folder(tmp_path / "out") if i["code"] == "GEOM_SPILL"]
    assert spill and spill[0]["tier"] == "error"


def test_invisible_text_is_tier_error():
    from src.compiler.layout_audit import audit_layout
    xml = ('<Theme surface="FFFFFF" /><Slide><VStack w="1280" h="720" backgroundColor="FFFFFF">'
           '<Text color="F8F8F8">white on white</Text><Text color="9A9A9A">grey on white</Text></VStack></Slide>')
    tiers = {i["message"].split(" on ")[0].split()[-1]: i["tier"] for i in audit_layout(xml) if i["code"] == "LOW_CONTRAST"}
    assert tiers == {"F8F8F8": "error", "9A9A9A": "warning"}


def test_sparse_table_slide_grows_the_table_then_centres(tmp_path):
    rows = "".join(f"<Tr><Td>Segment {i}</Td><Td>${i}.2M</Td><Td>+{i}%</Td></Tr>" for i in range(3))
    xml = ('<Slide><VStack w="1280" h="720" padding="40" gap="16">'
           '<VStack gap="4"><Text fontSize="14" bold="true">SEGMENTS</Text>'
           '<Text fontSize="28" bold="true">Enterprise leads ARR</Text></VStack>'
           f'<VStack padding="16" backgroundColor="FFFFFF"><Table>{rows}</Table></VStack>'
           '</VStack></Slide>')
    found, result = _fit(xml, tmp_path)
    log = " ".join(result["fitGrow"])
    assert "main table into spare height" in log
    assert "GEOM_SLIDE_SPARSE" not in found
    import json
    geo = json.loads((tmp_path / "out" / "geometry.json").read_text(encoding="utf-8"))
    assert geo["slides"][0]["children"][0]["y"] == 40  # the header stays at the top
