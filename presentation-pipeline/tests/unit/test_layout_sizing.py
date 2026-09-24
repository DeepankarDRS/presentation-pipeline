"""Phase 1 sizing grammar — LLM-free: the hand-written fixtures in tests/fixtures/layout_sizing/
compile, pass the layout audit, and size by POM's flexbox alone (fit-grow off)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import json

import yaml

from scripts.eval_metrics import card_metrics
from src.compiler.layout_audit import audit_layout

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "layout_sizing"
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"
_THEME = ('<Theme surface="F3F4F6" surfaceAlt="FFFFFF" accent="C2410C" accentAlt="1E3A5F" positive="15803D" '
          'negative="B91C1C" warning="B45309" textMain="1F2937" textMuted="6B7280" border="E5E7EB" />')


def _references() -> dict[str, str]:
    """Blueprint reference_xml + golden examples — the whole slides the generator is shown."""
    core = _ROOT / "src" / "knowledge" / "core"
    blueprints = yaml.safe_load((core / "blueprints.yaml").read_text(encoding="utf-8"))
    golden = yaml.safe_load((core / "golden-examples.yaml").read_text(encoding="utf-8"))
    refs = {name: bp["reference_xml"] for name, bp in blueprints.items() if isinstance(bp, dict)}
    refs.update({f"golden_{name}": xml for name, xml in golden.items()})
    return refs


def _recipe_slides() -> dict[str, str]:
    """Every recipe in core/recipes.yaml as the only region of a slide (comment lines dropped)."""
    recipes = yaml.safe_load((_ROOT / "src" / "knowledge" / "core" / "recipes.yaml").read_text(encoding="utf-8"))
    return {name: '<Slide><VStack w="1280" h="720" padding="36" gap="14" alignItems="stretch" '
                  'backgroundColor="$surface">'
                  + "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
                  + "</VStack></Slide>"
            for name, body in recipes.items()}


def _compile(name: str, out: Path) -> list[dict]:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    subprocess.run(["node", str(_COMPILER), str(_FIXTURES / name), str(out)], check=True, capture_output=True,
                   timeout=120, env={**os.environ, "POM_FIT_GROW": "0"})
    return card_metrics(out / "presentation.pptx")


@pytest.mark.parametrize("name", sorted(p.name for p in _FIXTURES.glob("*.xml")))
def test_fixture_is_audit_clean(name):
    xml = re.sub(r"<Theme\b[^>]*/>", "", (_FIXTURES / name).read_text(encoding="utf-8"))
    assert audit_layout(xml) == []


def test_recipes_are_audit_clean():
    issues = {name: audit_layout(xml) for name, xml in _recipe_slides().items()}
    assert {name: found for name, found in issues.items() if found} == {}


def test_references_are_audit_clean():
    issues = {name: audit_layout(xml) for name, xml in _references().items()}
    assert {name: found for name, found in issues.items() if found} == {}


@pytest.mark.parametrize("source", ["recipes", "references"])
def test_prompt_xml_compiles(source, tmp_path):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    slides = _recipe_slides() if source == "recipes" else _references()
    deck = tmp_path / "deck.xml"
    deck.write_text(_THEME + "\n" + "\n".join(xml.strip() for xml in slides.values()), encoding="utf-8")
    subprocess.run(["node", str(_COMPILER), str(deck), str(tmp_path)], capture_output=True, timeout=120)
    result = json.loads((tmp_path / "compile-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "success", result.get("diagnostics")


def test_blueprint_structure_matches_reference_grow():
    """The band list the prompt shows ([grow=N]) and the reference XML agree."""
    import xml.etree.ElementTree as ET
    blueprints = yaml.safe_load((_ROOT / "src" / "knowledge" / "core" / "blueprints.yaml").read_text(encoding="utf-8"))
    for name, bp in blueprints.items():
        bands = bp["structure"]["bands"]
        assert all(b.get("type") in ("auto", "grow", "fill") for b in bands), name
        if bp["structure"]["root"] != "VStack":
            continue
        want = sorted(str(b.get("grow", 1)) for b in bands if b.get("type") == "grow")
        got = sorted(c.get("grow") for c in ET.fromstring(bp["reference_xml"])[0] if c.get("grow"))
        assert want == got, name


def test_dashboard_kpi_row_and_chart_size_without_pixels(tmp_path):
    cards = _compile("s1-dashboard.xml", tmp_path)
    tiles = [c for c in cards if c["pattern"] == "kpi_tile"]
    assert len(tiles) == 4 and all(c["fill"] > 0.9 for c in tiles)  # no F1 height growth
    chart = next(c for c in cards if c["pattern"] == "chart_card")
    assert chart["fill"] > 0.95  # h="max" Chart fills its card


def test_table_card_is_content_sized(tmp_path):
    cards = _compile("s2-table-text.xml", tmp_path)
    table = next(c for c in cards if c["pattern"] == "table_card")
    assert abs(table["frame"][3] - (40 + 6 * 64 + 2 * 16)) <= 2  # header + 6 rows + padding, no dead box


def test_flow_card_takes_the_spare_height(tmp_path):
    cards = _compile("s3-flow.xml", tmp_path)
    assert max(cards, key=lambda c: c["frame"][3])["frame"][2] == 1208  # the full-width hero card
