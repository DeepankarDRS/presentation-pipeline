"""llm.md (POM's own reference) is the audit source for our knowledge — not a prompt.

- every llm.md example must compile once it has gone through our normalizer
- our knowledge/prompts must never teach a pattern POM rejects (zero strokes)
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.compiler.normalizer import ensure_single_theme, normalize_xml

_ROOT = Path(__file__).resolve().parents[2]
_LLM_MD = _ROOT / "llm.md"
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"
_POM = _ROOT / "src" / "node" / "node_modules" / "@hirokisakabe" / "pom"
_THEME = '<Theme surface="0F172A" accent="38BDF8" textMain="F8FAFC" textMuted="94A3B8" />'


@pytest.mark.parametrize("attrs,gone,kept", [
    ('line.width="0" line.color="000"', ["line."], []),
    ('outline.size="0.0" outline.color="000"', ["outline."], []),
    ('border.width="0" border.color="333"', ["border."], []),
    ('borderLeft.width="0" borderLeft.color="F00" borderTop.width="4"', ["borderLeft."], ['borderTop.width="4"']),
    ('line.width="2"', [], ['line.width="2"']),
])
def test_zero_strokes_removed_as_a_group(attrs, gone, kept):
    xml = f'<Slide><VStack w="1280" h="720"><Shape shapeType="rect" w="10" h="10" {attrs} /></VStack></Slide>'
    result = normalize_xml(xml)
    for prefix in gone:
        assert prefix not in result["cleaned_xml"]
    for attr in kept:
        assert attr in result["cleaned_xml"]
    assert ("ZERO_STROKE_REMOVED" in {i["code"] for i in result["issues"]}) == bool(gone)


def test_table_cell_border_zero_is_valid_and_kept():
    xml = '<Slide><VStack w="1280" h="720"><Table cellBorder.width="0"><Tr><Td>a</Td></Tr></Table></VStack></Slide>'
    assert 'cellBorder.width="0"' in normalize_xml(xml)["cleaned_xml"]


def test_knowledge_never_teaches_zero_strokes():
    bad = re.compile(r'\b(?:line|outline|border|borderTop|borderRight|borderBottom|borderLeft)\.(?:width|size)="0')
    for path in list((_ROOT / "src/knowledge").rglob("*.yaml")) + list((_ROOT / "src/prompts").rglob("*.j2")):
        hits = bad.findall(path.read_text(encoding="utf-8"))
        assert not hits, f"{path.relative_to(_ROOT)} teaches {hits}"


def _llm_md_examples() -> list[str]:
    blocks = re.findall(r"```xml\n(.*?)```", _LLM_MD.read_text(encoding="utf-8"), re.DOTALL)
    return [re.sub(r"^> ?", "", b, flags=re.M) for b in blocks]


@pytest.mark.skipif(not _POM.exists() or not shutil.which("node"), reason="POM/node not installed")
def test_every_llm_md_example_compiles_after_normalize(tmp_path):
    """All examples compiled as one deck (one node spawn); diagnostics name the failing slide."""
    examples = _llm_md_examples()
    assert len(examples) >= 25
    slides = [
        block if "<Slide>" in block
        else f'<Slide><VStack w="1280" h="720" padding="40" gap="16">{block}</VStack></Slide>'
        for block in examples
    ]
    cleaned = ensure_single_theme(normalize_xml("\n".join(slides))["cleaned_xml"], _THEME)
    src = tmp_path / "llm_md_examples.xml"
    src.write_text(cleaned, encoding="utf-8")
    subprocess.run(["node", str(_COMPILER), str(src), str(tmp_path / "out")],
                   capture_output=True, encoding="utf-8", errors="replace")
    result = json.loads((tmp_path / "out" / "compile-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "success", result["diagnostics"][:3]
