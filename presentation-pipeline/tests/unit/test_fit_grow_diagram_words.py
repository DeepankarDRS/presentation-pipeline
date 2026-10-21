"""fit-grow phase 2d: chevrons and flow nodes as wide as their longest word (user, 2026-10-21; LLM-free, real compiler).

XTSY slide 4 broke "Profitability" in four runs: the generator left itemWidth at 150 (a 94 px label box) with
fontSize 16 bold, and the renderer keeps its default 0.1 in text inset each side (facts process_arrow.label_inset),
so 75 px held the word. The phase raises itemWidth / nodeWidth (nodeHeight for a second line) within the box, a
row that cannot widen lowers its fontSize toward 14, never below; it never changes direction, kind or node count.
Fixtures: tests/fixtures/diagram_words/.
"""

import re
from pathlib import Path

import pytest

from src.compiler.node_facts import drawn_shapes
from tests.unit.test_shrink_guard import _compile, _warnings

_FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "diagram_words"


def _attrs(xml: str, tag: str, node_id: str) -> dict[str, str]:
    open_tag = re.search(rf'<{tag}\b[^>]*\sid="{node_id}"[^>]*>', xml).group(0)
    return dict(re.findall(r'\s([\w.]+)="([^"]*)"', open_tag))


def _phase_lines(result: dict) -> list[str]:
    return [r for r in result["fitGrow"] if "longest word" in r or "label box" in r]


def test_profitability_in_a_four_step_row_gets_a_wider_chevron_not_a_smaller_font(tmp_path):
    r = _compile(_FIX / "d1-arrow-row.xml", tmp_path)
    a = _attrs(r["xml"], "ProcessArrow", "row")
    assert a["direction"] == "horizontal" and a["fontSize"] == "16" and a["bold"] == "true"
    assert int(a["itemWidth"]) > 150, r["fitGrow"]
    assert any("itemWidth 150 ->" in x and "fits its label box" in x for x in _phase_lines(r)), r["fitGrow"]
    assert not _warnings(r)
    label = next(s for s in drawn_shapes(tmp_path / "presentation.pptx") if s.text == "Profitability")
    assert label.font == 16 and label.w - label.pad >= 91.6   # "Profitability" at 16 px bold Inter is 91.1 px; a word needs 0.5 px spare


def test_a_row_that_cannot_widen_lowers_its_font_only_as_far_as_the_word_needs(tmp_path):
    # 161 px chevrons leave a middle label 161 - 56 - 19.2 = 85.8 px: "Profitability" (bold Inter) is 85.4 px at
    # 15 px (0.4 px spare, under WORD_MARGIN) and 79.7 px at 14, so the row stops at 14 and the word fits
    # (measured without POM's 10 px box padding, node break map §4 C1)
    r = _compile(_FIX / "d2-arrow-narrow.xml", tmp_path)
    a = _attrs(r["xml"], "ProcessArrow", "narrow")
    assert a["w"] == "560" and a["fontSize"] == "14"
    assert int(a["itemWidth"]) == 161   # (560 + 3 x 28) / 4: the widest the row can be without shrinking
    assert any("fits its label box" in x for x in _phase_lines(r)), r["fitGrow"]
    assert not _warnings(r)


def test_a_row_whose_word_never_fits_stops_at_14_and_warns(tmp_path):
    # "Reconciliation" is 97 px at 14 px bold Inter: wider than the 85.8 px label at any allowed size
    xml = (_FIX / "d2-arrow-narrow.xml").read_text(encoding="utf-8").replace("Profitability", "Reconciliation")
    (tmp_path / "d2b.xml").write_text(xml, encoding="utf-8")
    r = _compile(tmp_path / "d2b.xml", tmp_path / "out")
    a = _attrs(r["xml"], "ProcessArrow", "narrow")
    assert a["fontSize"] == "14" and int(a["itemWidth"]) == 161
    assert any("as far as its box allows" in x for x in _phase_lines(r)), r["fitGrow"]
    assert any("Reconciliation" in w and "process step" in w for w in _warnings(r))


def test_a_chevron_row_grows_only_as_tall_as_its_words_allow(tmp_path):
    # A taller chevron has a narrower label box (itemWidth - 0.7 x itemHeight): growing 9 steps to 120 px tall
    # left "customer" 62 px in 59 (node break map §4 C2). The row grows to the tallest height every word fits at.
    r = _compile(_FIX / "d7-arrow-nine-steps.xml", tmp_path)
    a = _attrs(r["xml"], "ProcessArrow", "row")
    assert 88 < int(a["itemHeight"]) < 120, r["fitGrow"]
    assert not any("still wider" in x for x in _phase_lines(r)), r["fitGrow"]
    assert not _warnings(r)


def test_a_seven_step_vertical_column_stays_vertical_and_widens(tmp_path):
    r = _compile(_FIX / "d3-arrow-column.xml", tmp_path)
    a = _attrs(r["xml"], "ProcessArrow", "column")
    assert a["direction"] == "vertical" and a["fontSize"] == "20" and int(a["itemWidth"]) > 150
    assert r["xml"].count("<ProcessArrowStep") == 7
    assert not _warnings(r)


def test_a_seven_node_vertical_flow_keeps_its_nodes_and_every_word_fits(tmp_path):
    r = _compile(_FIX / "d4-flow-vertical.xml", tmp_path)
    a = _attrs(r["xml"], "Flow", "flow")
    assert a["direction"] == "vertical" and int(a["nodeWidth"]) > 110
    assert r["xml"].count("<FlowNode") == 7
    assert not _warnings(r)
    nodes = [s for s in drawn_shapes(tmp_path / "presentation.pptx") if s.text in ("Placement optimization", "Budget reallocation")]
    assert len(nodes) == 2 and all(s.font >= 13.9 for s in nodes)   # drawn at full size: not shrunk to fit


def test_a_flow_row_widens_its_nodes_within_its_box(tmp_path):
    r = _compile(_FIX / "d6-flow-row.xml", tmp_path)
    a = _attrs(r["xml"], "Flow", "row")
    assert a.get("direction", "horizontal") == "horizontal"
    assert 100 < int(a["nodeWidth"]) <= (1168 - 3 * 60) / 4
    assert any("flow nodeWidth 100 ->" in x and "fits its label box" in x for x in _phase_lines(r)), r["fitGrow"]
    assert not _warnings(r)


def test_a_word_no_node_can_hold_is_reported_and_the_flow_gets_no_font_size(tmp_path):
    """A decision diamond's text gets half its width (OOXML preset text rectangle); Flow has no fontSize."""
    r = _compile(_FIX / "d5-flow-diamond.xml", tmp_path)
    assert "fontSize" not in _attrs(r["xml"], "Flow", "diamond")
    assert any("flow node" in w and "Reconciliation" in w for w in _warnings(r))


@pytest.mark.parametrize("name", ["d1-arrow-row", "d2-arrow-narrow", "d6-flow-row"])
def test_compiling_the_fitted_xml_again_changes_nothing(tmp_path, name):
    first = _compile(_FIX / f"{name}.xml", tmp_path / "a")
    fitted = tmp_path / f"{name}-fitted.xml"
    fitted.write_text(first["xml"], encoding="utf-8")
    second = _compile(fitted, tmp_path / "b")
    assert not _phase_lines(second), second["fitGrow"]
    keys = ("itemWidth", "nodeWidth", "nodeHeight", "fontSize")
    tags = re.findall(r"<(?:ProcessArrow|Flow) [^>]*>", first["xml"]), re.findall(r"<(?:ProcessArrow|Flow) [^>]*>", second["xml"])
    pick = lambda t: {k: v for k, v in re.findall(r'\s([\w.]+)="([^"]*)"', t) if k in keys}  # noqa: E731
    assert [pick(t) for t in tags[0]] == [pick(t) for t in tags[1]]
