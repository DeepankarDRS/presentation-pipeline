"""Native fillers (§3.1): every native kind -> POM children copied from the plan; one slide of all of them compiles."""

import json
import re
import shutil
from pathlib import Path

import pytest

from src.compiler.nodes import native
from src.compiler.nodes.validate import words

_RUNS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nodes" / "runs" / "decks"


def _comps() -> dict:
    out = {}
    for case in ("deck-qbr-data", "gate-deck-all-nodes-dense"):
        for s in json.loads((_RUNS / f"{case}__r1" / "slides.json").read_text(encoding="utf-8")):
            for c in s["slide_plan"]["components"]:
                out.setdefault(c["kind"], c)
    return out


TAG = {"narrative": "Text", "caption": "Text", "bullet_list": "Ul", "table": "Table", "chart": "Chart",
       "timeline": "Timeline", "process_arrow": "ProcessArrow", "flow": "Flow", "pyramid": "Pyramid",
       "tree": "Tree", "matrix": "Matrix"}


def _strings(v):
    if isinstance(v, dict):
        return [s for x in v.values() for s in _strings(x)]
    if isinstance(v, list):
        return [s for x in v for s in _strings(x)]
    return [str(v)]


@pytest.mark.parametrize("kind", sorted(TAG))
def test_filler_copies_only_plan_words(kind):
    comp = _comps()[kind]
    xml = native.fill(TAG[kind], comp, {"ref": comp["component_id"], "grow": "1"}, {"chart_colors": ["2563EB"]})
    assert xml.startswith(f"<{TAG[kind]}" if kind != "chart" else "<")
    assert 'ref="' not in xml and "variant=" not in xml
    seen = set(words(re.sub(r"<[^>]+>", " ", xml)))
    for a in re.findall(r'\b(?:label|title|text|date|name|topLeft|topRight|bottomLeft|bottomRight|x|y)="([^"]*)"', xml):
        seen |= set(words(a))
    allowed = {w for s in _strings(comp["content_data"]) for w in words(s)}
    numbers = {w for w in seen if re.fullmatch(r"[\d.]+", w)}   # matrix positions, chart values
    assert seen - allowed - numbers == set(), seen - allowed
    for item in [i for i in __import__("src.compiler.nodes.spec", fromlist=["items"]).items(comp)]:
        assert all(w in seen for w in words(item)), item


def test_chart_values_parse_units():
    assert native.number("0.29x") == 0.29 and native.number("₹1,234") == 1234 and native.number(2.6) == 2.6
    assert native.number("-1.4 pts") == -1.4 and native.number("n/a") == 0.0


def test_matrix_positions():
    assert native._pos("low") == 0.2 and native._pos("high") == 0.8 and native._pos(0.99) == 0.95


def test_layout_attributes_go_on_the_chart_box():
    comp = _comps()["chart"]
    xml = native.fill("Chart", comp, {"ref": "x", "w": "60%", "h": "max", "minH": "200"}, {})
    if comp["content_data"].get("chart_title"):
        assert xml.startswith('<VStack w="60%" h="max" minH="200"') and "<Chart chartType=" in xml


def test_all_native_kinds_compile_on_one_slide(tmp_path):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    from src.agents.style_resolver import resolve_theme
    from src.agents.validator import normalize_and_compile
    comps = _comps()
    body = "".join(f'<VStack grow="1">{native.fill(TAG[k], comps[k], {"grow": "1"}, {"chart_colors": ["2563EB"]})}</VStack>'
                   for k in ("table", "chart", "timeline", "process_arrow", "flow"))
    body2 = "".join(f'<VStack grow="1">{native.fill(TAG[k], comps[k], {"grow": "1"}, {})}</VStack>'
                    for k in ("pyramid", "tree", "matrix", "bullet_list", "narrative", "caption"))
    xml = (f'<Slide><VStack w="1280" h="720" padding="20" gap="8" alignItems="stretch"><HStack grow="1" gap="8" alignItems="stretch">{body}</HStack>'
           f'<HStack grow="1" gap="8" alignItems="stretch">{body2}</HStack></VStack></Slide>')
    ok, cr = normalize_and_compile("<!-- fit-grow: off -->\n" + xml, resolve_theme("corporate-slate")["element"], tmp_path)
    assert ok, cr.get("diagnostics")
