"""Deterministic structure fixes in normalize_xml — each input below failed POM 10.3.0 in the
Phase 0 baseline (docs/eval/baseline) and cost a repair retry or a whole slide."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.compiler.normalizer import ensure_single_theme, normalize_xml

_ROOT = Path(__file__).resolve().parents[2]
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"
_POM = _ROOT / "src" / "node" / "node_modules" / "@hirokisakabe" / "pom"
_THEME = '<Theme surface="FFFFFF" accent="2563EB" textMain="111111" textMuted="555555" border="DDDDDD" />'


def _slide(body: str) -> str:
    return f'<Slide><VStack w="1280" h="720" padding="36" gap="12">{body}</VStack></Slide>'


# (name, broken body, issue code, POM error it used to raise)
CASES = [
    ("shadow", '<VStack shadow="true" shadow.blur="6" shadow.color="000"><Text>x</Text></VStack>',
     "ATTR_CONFLICT_FIXED", 'Attribute "shadow" conflicts with dot-notation'),
    ("border", '<VStack border.width="0 0 0 5" border.color="2563EB"><Text>x</Text></VStack>',
     "BORDER_SHORTHAND_EXPANDED", 'border.width: Cannot convert "0 0 0 5" to number'),
    ("icon_cell", '<Table><Tr><Td><Icon name="star" size="14" /></Td><Td>b</Td></Tr></Table>',
     "EMPTY_CELL_FILLED", '<Table>: Missing required attribute "rows"'),
    ("empty_cell", '<Table><Tr><Td>a</Td><Td></Td></Tr></Table>',
     "EMPTY_CELL_FILLED", '<Table>: Missing required attribute "rows"'),
    ("empty_text", '<Text fontSize="14"></Text><Text>ok</Text>',
     "EMPTY_TEXT_REMOVED", '<Text>: Missing required attribute "text"'),
    ("empty_li", "<Ul><Li>a</Li><Li></Li></Ul>",
     "EMPTY_ITEM_REMOVED", '<Ul>: Missing required attribute "items"'),
    ("long_row", '<Table><Col width="200" /><Col /><Tr><Td colspan="2">a</Td><Td>b</Td></Tr></Table>',
     "TABLE_COLS_PADDED", "each row must contain one cell per grid column"),
    ("bare_amp", "<Table><Tr><Td><Text>R &amp; D</Text></Td><Td>Reporting & Governance</Td></Tr></Table>",
     "AMPERSAND_ESCAPED", "(compiles, but layout_audit's XML parser rejected the slide)"),
]


@pytest.mark.parametrize("name,body,code,_was", CASES, ids=[c[0] for c in CASES])
def test_fix_is_reported_and_idempotent(name, body, code, _was):
    first = normalize_xml(_slide(body))
    assert code in {i["code"] for i in first["issues"]}
    again = normalize_xml(first["cleaned_xml"])  # deck_assembler normalizes every slide again
    assert again["cleaned_xml"] == first["cleaned_xml"]
    assert code not in {i["code"] for i in again["issues"]}


def test_valid_xml_is_left_alone():
    body = ('<VStack shadow.blur="6" borderLeft.width="4" borderLeft.color="2563EB"><Text> </Text>'
            '<Table><Col /><Col /><Tr><Td> </Td><Td>R &amp; D</Td></Tr></Table><Ul><Li>a</Li></Ul></VStack>')
    assert normalize_xml(_slide(body))["issues"] == []


def test_border_shorthand_becomes_per_side_borders():
    out = normalize_xml(_slide('<VStack border.width="2 0" border.color="DDDDDD"><Text>x</Text></VStack>'))
    xml = out["cleaned_xml"]
    assert 'borderTop.width="2" borderTop.color="DDDDDD"' in xml
    assert 'borderBottom.width="2" borderBottom.color="DDDDDD"' in xml
    assert "border.width" not in xml and "borderLeft" not in xml


@pytest.mark.skipif(not _POM.exists() or not shutil.which("node"), reason="POM/node not installed")
def test_every_fixed_case_compiles(tmp_path):
    """All cases as one deck (one node spawn): before normalize each fails, after it compiles."""
    slides = "\n".join(_slide(body) for _, body, _, _ in CASES)
    src = tmp_path / "fixed.xml"
    src.write_text(ensure_single_theme(normalize_xml(slides)["cleaned_xml"], _THEME), encoding="utf-8")
    subprocess.run(["node", str(_COMPILER), str(src), str(tmp_path / "out")],
                   capture_output=True, encoding="utf-8", errors="replace")
    result = json.loads((tmp_path / "out" / "compile-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "success", result["diagnostics"][:3]
