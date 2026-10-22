"""Diagram text in the deck font (node break map §4 C3, 2026-10-21; LLM-free, real compiler).

POM writes Flow, Tree and Matrix text (they take no fontFamily) in "Noto Sans JP": not installed here, not
embedded, so LibreOffice drew it in Liberation Sans and bold Matrix labels in Arial Black. pptx-post.js names the
deck font (POM_DECK_FONT, default Inter) in those runs, and fit-grow measures flow words in it.
"""

import json
import os
import re
import shutil
import subprocess
import zipfile

import pytest

from src.compiler.node_facts import drawn_shapes
from tests.unit.test_fit_grow_tables import _ROOT, _COMPILER

_SLIDE = (
    '<Slide><VStack w="1280" h="720" padding="56" gap="24" alignItems="stretch">'
    '<Text fontSize="36" fontFamily="Inter">Three diagrams</Text>'
    '<HStack h="max" gap="24" alignItems="stretch">'
    '<Flow direction="horizontal" w="400"><FlowNode id="a" shape="flowChartProcess" text="Personalization"/>'
    '<FlowNode id="b" shape="flowChartProcess" text="Build"/><FlowConnection from="a" to="b" label="go"/></Flow>'
    '<Tree layout="vertical" w="350"><TreeItem label="Root"><TreeItem label="Leaf"/></TreeItem></Tree>'
    '<Matrix w="350"><MatrixAxes x="Effort" y="Impact"/><MatrixQuadrants topLeft="Quick wins" topRight="Big bets" '
    'bottomLeft="Fill-ins" bottomRight="Money pits"/><MatrixItem label="Bundles" x="0.5" y="0.5"/></Matrix>'
    '</HStack></VStack></Slide>'
)


def _typefaces(tmp_path, env: dict[str, str]) -> tuple[list[str], object]:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    xml = tmp_path / "s.xml"
    xml.write_text(_SLIDE, encoding="utf-8")
    out = tmp_path / "out"
    subprocess.run(["node", str(_COMPILER), str(xml), str(out)], check=True, capture_output=True, timeout=120,
                   env={**os.environ, **env})
    with zipfile.ZipFile(out / "presentation.pptx") as z:
        slide = z.read("ppt/slides/slide1.xml").decode("utf-8")
    return re.findall(r'<a:(?:latin|ea|cs) typeface="([^"]*)"', slide), out / "presentation.pptx"


def test_flow_tree_and_matrix_text_is_set_in_the_deck_font(tmp_path):
    faces, pptx = _typefaces(tmp_path, {"POM_DECK_FONT": "Inter"})
    assert faces and set(faces) == {"Inter"}
    shapes = {s.text: s for s in drawn_shapes(pptx)}
    for label in ("Personalization", "Leaf", "Bundles", "Quick wins", "Effort", "go"):
        assert shapes[label].family == "Inter", label


def test_flow_words_are_measured_in_the_font_they_are_drawn_in(tmp_path):
    # "Personalization" is 101.3 px at 14 px Inter: a 120 px node leaves 100.8 px, so fit-grow widens it
    _, pptx = _typefaces(tmp_path, {"POM_DECK_FONT": "Inter"})
    node = next(s for s in drawn_shapes(pptx) if s.text == "Personalization")
    assert node.font == 14 and node.w - node.pad >= 101.3 + 0.5


def test_pom_deck_font_none_keeps_poms_family(tmp_path):
    faces, _ = _typefaces(tmp_path, {"POM_DECK_FONT": "none"})
    assert "Noto Sans JP" in faces and "Inter" in faces   # the headline names Inter itself


def test_deck_typeface_only_renames_poms_default_and_is_idempotent():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    script = (
        "import { deckTypeface } from './src/node/pptx-post.js';"
        "const x = '<a:rPr><a:latin typeface=\"Noto Sans JP\"/><a:ea typeface=\"Noto Sans JP\"/>"
        "<a:cs typeface=\"Noto Sans JP\"/></a:rPr><a:rPr><a:latin typeface=\"JetBrains Mono\"/></a:rPr>"
        "<a:t>Noto Sans JP</a:t>';"
        "const once = deckTypeface(x, 'Inter');"
        "console.log(JSON.stringify([once, deckTypeface(once, 'Inter'), deckTypeface(x, null)]));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=_ROOT, check=True,
                         capture_output=True, text=True, timeout=60).stdout
    once, twice, off = json.loads(out)
    assert once == twice
    assert once.count('typeface="Inter"') == 3 and 'typeface="JetBrains Mono"' in once
    assert "<a:t>Noto Sans JP</a:t>" in once   # text is never touched
    assert off == x_of(script) and off.count('typeface="Noto Sans JP"') == 3   # no deck font: unchanged


def x_of(script: str) -> str:
    """The test XML the node script builds (its JS string literal, unescaped)."""
    return re.search(r"const x = '(.*?)';", script).group(1).replace('\\"', '"')
