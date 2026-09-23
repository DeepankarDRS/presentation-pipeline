"""Icon names: only POM's real icon set reaches the compiler — no retry for a bad name."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from src.compiler.content_model import find_violations
from src.compiler.icons import canonical_icon_name, fix_icon_names, valid_icon_names
from src.compiler.normalizer import normalize_xml

_ROOT = Path(__file__).resolve().parents[2]
_POM_ICON_DATA = _ROOT / "src" / "node" / "node_modules" / "@hirokisakabe" / "pom" / "dist" / "icons" / "iconData.js"


def _row(icon: str) -> str:
    return (f'<Slide><VStack w="1280" h="720"><HStack gap="8" alignItems="center">{icon}'
            f'<Text fontSize="14">Label</Text></HStack></VStack></Slide>')


def test_valid_name_untouched():
    xml = _row('<Icon name="store" size="22" color="C62828" />')
    assert fix_icon_names(xml) == (xml, [], [])


@pytest.mark.parametrize("raw,slug", [
    ("ShoppingBag", "shopping-bag"),
    ("shopping_bag", "shopping-bag"),
    ("Shopping Bag", "shopping-bag"),
    ("TRENDING-UP", "trending-up"),
])
def test_other_spelling_rewritten_to_exact_slug(raw, slug):
    fixed, renamed, removed = fix_icon_names(_row(f'<Icon name="{raw}" size="22" />'))
    assert renamed == [(raw, slug)] and removed == []
    assert f'name="{slug}"' in fixed


@pytest.mark.parametrize("icon,label", [
    ('<Icon name="flipkart-logo" size="22" />', "flipkart-logo"),
    ('<Icon name="shoping-bag" size="22" />', "shoping-bag"),  # near-miss: no fuzzy guessing
    ('<Icon size="22" />', "(no name)"),
    ('<Icon name="zomato" size="22"></Icon>', "zomato"),
])
def test_unknown_icon_removed_and_rest_kept(icon, label):
    fixed, renamed, removed = fix_icon_names(_row(icon))
    assert removed == [label] and renamed == []
    assert "<Icon" not in fixed
    assert '<Text fontSize="14">Label</Text>' in fixed
    assert find_violations(fixed) == []


def test_normalizer_reports_icon_fixes_as_auto_fixed():
    xml = ('<Slide><VStack w="1280" h="720">'
           '<Icon name="ShoppingBag" size="20" /><Icon name="flipkart-logo" size="20" />'
           '</VStack></Slide>')
    result = normalize_xml(xml)
    codes = {i["code"]: i for i in result["issues"]}
    assert codes["ICON_NAME_NORMALIZED"]["auto_fixed"] is True
    assert codes["UNKNOWN_ICON_REMOVED"]["auto_fixed"] is True
    assert result["blocking"] is False
    assert 'name="shopping-bag"' in result["cleaned_xml"]
    assert "flipkart-logo" not in result["cleaned_xml"]


def test_canonical_name():
    assert canonical_icon_name("  CheckCircle ") == "check-circle"
    assert canonical_icon_name("bar_chart_3") == "bar-chart-3"


def test_recommended_names_all_exist():
    groups = yaml.safe_load((_ROOT / "src/knowledge/components/icon.yaml").read_text(encoding="utf-8"))["recommended_names"]
    names = [n for g in groups.values() for n in g]
    assert names and not set(names) - valid_icon_names()


def test_every_icon_taught_in_prompts_and_knowledge_exists():
    taught = set()
    for path in list((_ROOT / "src/knowledge").rglob("*.yaml")) + list((_ROOT / "src/prompts").rglob("*.j2")):
        taught |= set(re.findall(r'<Icon\b[^>]*\bname="([^"]*)"', path.read_text(encoding="utf-8")))
    placeholders = {"N", "NAME"}
    assert not (taught - placeholders) - valid_icon_names()


@pytest.mark.skipif(not _POM_ICON_DATA.exists() or not shutil.which("node"), reason="POM/node not installed")
def test_icon_list_matches_installed_pom():
    """Fails after a POM upgrade until `python -m scripts.export_icon_names` is re-run."""
    js = "const {ICON_DATA}=await import(process.argv[1]);console.log(JSON.stringify(Object.keys(ICON_DATA)));"
    out = subprocess.run(["node", "--input-type=module", "-e", js, _POM_ICON_DATA.as_uri()],
                         capture_output=True, text=True, check=True).stdout
    assert set(json.loads(out)) == valid_icon_names()
