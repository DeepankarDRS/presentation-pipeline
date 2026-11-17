"""Fixes from the layer-decision paid run (2026-11-17, e27ff85, 3 runs of decision-flowchart-free):

1. every run wrote backgroundColor / border.* on the diamond <Shape>: those style the node's rectangular box, so the
   diamond was drawn as a square (render-checked). The normalizer moves them to fill.* / line.* on any non-rect
   Shape, and our own knowledge stops teaching them (shape.yaml note, the layer recipe's hub ellipse).
2. An Arrow joins the side-midpoints nearest the other box's centre, so wide routes side by side below a condition
   crossed (runs 1 and 3); boxes sharing a row or a column give straight arrows (render-checked). A flowchart layer
   places connected boxes on a row / column grid and keeps Arrows. LINE_END_LOOSE reports a hand-placed Line end
   that touches no box edge, diamond tip or other Line, should a layer use Lines.
"""

from __future__ import annotations

from pathlib import Path

from src.compiler.layout_audit import REPORT_ONLY_CODES, audit_layout
from src.compiler.normalizer import _box_attrs_to_shape, normalize_xml

_ROOT = Path(__file__).resolve().parents[2]


def test_box_attributes_move_to_the_shape_on_non_rect_shapes():
    xml = ('<Shape shapeType="diamond" x="0" y="0" w="200" h="100" backgroundColor="$accentSoft" '
           'border.color="$accent" border.width="2" text="In stock?" />')
    out, n = _box_attrs_to_shape(xml)
    assert n == 1
    assert 'fill.color="$accentSoft"' in out and 'line.color="$accent"' in out and 'line.width="2"' in out
    assert "backgroundColor" not in out and "border." not in out


def test_rect_is_left_alone_and_the_shapes_own_fill_wins():
    rect = '<Shape shapeType="rect" w="120" h="6" backgroundColor="$accent" />'
    assert _box_attrs_to_shape(rect) == (rect, 0)
    out, _ = _box_attrs_to_shape('<Shape shapeType="ellipse" w="10" h="10" fill.color="$positive" '
                                 'backgroundColor="$accent" borderRadius="12" />')
    assert 'fill.color="$positive"' in out and "$accent" not in out and "borderRadius" not in out


def test_normalize_reports_the_move():
    res = normalize_xml('<Slide><VStack w="1280" h="720"><Layer w="400" h="200"><Shape shapeType="ellipse" '
                        'x="0" y="0" w="100" h="100" backgroundColor="$accent" text="Hub" /></Layer></VStack></Slide>')
    assert "SHAPE_FILL_FROM_BOX" in [i["code"] for i in res["issues"]]


def test_our_knowledge_no_longer_teaches_box_fills_on_shapes():
    recipes = (_ROOT / "src/knowledge/core/recipes.yaml").read_text(encoding="utf-8")
    hub = next(line for line in recipes.splitlines() if 'id="hub"' in line)
    assert "fill.color" in hub and "backgroundColor" not in hub
    layer = recipes[recipes.index("layer_diagram:"):recipes.index("\ntree:")]
    assert "every two connected nodes share a ROW" in layer and "or a COLUMN" in layer
    assert "Every connection is one <Arrow" in layer
    assert "<Text id=\"...\" x y w h> </Text>" in layer        # the diamond's connectable overlay
    assert "never <Arrow>" not in layer
    shape = (_ROOT / "src/knowledge/components/shape.yaml").read_text(encoding="utf-8")
    assert "on any other shapeType it draws a rectangle behind it" in shape


def _layer(lines: str) -> str:
    return ('<Slide><VStack w="1280" h="720" padding="36"><Layer w="1000" h="600">'
            '<Shape shapeType="diamond" x="400" y="0" w="200" h="100" fill.color="$accentSoft" text="In stock?" />'
            '<Shape id="a" shapeType="roundRect" x="100" y="200" w="200" h="80" text="Store" />'
            '<Shape id="b" shapeType="roundRect" x="700" y="200" w="200" h="80" text="Warehouse" />'
            '<Text x="300" y="20" w="60" h="24" fontSize="14">Yes</Text>'
            + lines + '</Layer></VStack></Slide>')


def _loose(xml: str) -> list[dict]:
    return [i for i in audit_layout(xml) if i["code"] == "LINE_END_LOOSE"]


def test_elbows_from_the_diamond_tips_to_the_box_tops_pass():
    xml = _layer('<Line x1="400" y1="50" x2="200" y2="50" /><Line x1="200" y1="50" x2="200" y2="200" endArrow="true" />'
                 '<Line x1="600" y1="50" x2="800" y2="50" /><Line x1="800" y1="50" x2="800" y2="200" endArrow="true" />')
    assert _loose(xml) == []
    assert "LINE_END_LOOSE" in REPORT_ONLY_CODES


def test_a_line_that_stops_short_or_leaves_the_diamond_off_its_tip_is_reported():
    short = _layer('<Line x1="500" y1="100" x2="200" y2="170" endArrow="true" />')   # tip ok, end in empty space
    assert len(_loose(short)) == 1
    off_tip = _layer('<Line x1="450" y1="100" x2="200" y2="200" endArrow="true" />')  # diamond bbox edge, not a tip
    assert len(_loose(off_tip)) == 1
    label = _layer('<Line x1="500" y1="100" x2="330" y2="44" />')                     # a label Text is not a box
    assert len(_loose(label)) == 1
