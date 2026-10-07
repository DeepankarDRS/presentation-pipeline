"""1a tooling (§4): slide selection, variety signatures, scorer helpers, and a scripted dry run end to end."""

import json
import shutil
from pathlib import Path

import pytest

from scripts import variety
from scripts.from_plans import find_runs, load_run
from scripts.node_test_score import invented, node_regions
from scripts.node_test_select import example_titles, select

_FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nodes"


def test_example_titles_come_from_the_prompt():
    t = example_titles()
    assert len(t) == 4 and "h1 2026 snapshot" in t


def test_selection_rule_on_fixture_runs():
    runs = find_runs(_FIX / "runs")
    r = select(runs, {"repeat customers now drive most of brewly s revenue"})
    left = {(x["case"], x["slide"]): x["reason"] for x in r["left_out"]}
    assert left[("deck-qbr-data", 1)].startswith("nothing to place")
    assert r["counts"]["slides"] == 9   # 11 slides - QBR cover - one example source


def test_load_run_uses_the_saved_theme():
    run = load_run(_FIX / "runs" / "decks" / "deck-qbr-data__r1")
    assert run["theme"]["element"].startswith("<Theme ") and len(run["slides"]) == 5


def test_variety_signature():
    a = '<Slide><VStack><Text>h</Text><HStack><KpiRow ref="a" w="62%" /><Ul ref="b" grow="1" /></HStack></VStack></Slide>'
    b = '<Slide><VStack><Text>h</Text><HStack><KpiRow ref="a" w="30%" /><Ul ref="b" grow="1" /></HStack></VStack></Slide>'
    assert variety.signature(a) == "H(kpi@wide,bullets@flex)"
    assert variety.signature(a, fine=False) == variety.signature(b, fine=False) != "unparsed"
    rep = variety.report([{"deck": "d1", "xml": a, "kinds": ["kpi_row", "bullet_list"]},
                          {"deck": "d1", "xml": b, "kinds": ["kpi_row", "bullet_list"]},
                          {"deck": "d2", "xml": a, "kinds": ["kpi_row", "bullet_list"]}])
    assert rep["within_deck"] == 1.0 and rep["cross_deck_sameness"] == 1.0 and rep["house_template_share"] == 1.0


def test_invented_words_inside_nodes():
    plan = {"components": [{"component_id": "n1", "kind": "narrative", "content_data": {"text": "Revenue grew 22%"}}]}
    good = '<VStack id="slot-n1"><Text>Revenue grew 22%</Text></VStack>'
    bad = '<Text id="node-n1">Revenue grew 22% fast</Text>'
    assert invented(good, plan) == {} and invented(bad, plan) == {"n1": ["fast"]}
    assert set(node_regions(good + bad)) == {"n1"}
    icon = '<VStack id="slot-n1"><Icon name="arrow-right" /><Text>Revenue grew 22%</Text></VStack>'
    assert invented(icon, plan) == {}


def test_scripted_dry_run_end_to_end(tmp_path):
    """Every NODE_* code the fixtures aim at is reported on its slide; repairs fix the errors; all compile."""
    if not shutil.which("node"):
        pytest.skip("node not installed")
    from scripts import node_test
    from scripts.phase0b.fit import Measurer
    llm = node_test.ScriptedLLM(_FIX / "scripted")
    expect = {("deck-qbr-data", 2): "NODE_REF_UNKNOWN", ("deck-qbr-data", 3): "NODE_CHILDREN_DROPPED",
              ("deck-qbr-data", 4): "NODE_BYPASSED", ("gate-deck-all-nodes-dense", 1): "NODE_MISSING",
              ("gate-deck-all-nodes-dense", 2): "NODE_REF_DUPLICATE", ("gate-deck-all-nodes-dense", 4): "NODE_KIND_NO_REF"}
    measure = Measurer()
    calls = []
    try:
        for (case, n), code in expect.items():
            run = load_run(_FIX / "runs" / "decks" / f"{case}__r1")
            slide = next(s for s in run["slides"] if s["number"] == n)
            r = node_test.run_slide(run, slide, llm, measure, tmp_path / case / str(n), "Inter", True, calls, repairs=2)
            assert code in r["issues_first"], (case, n, r["issues_first"])
            assert r["compiled"], (case, n)
            errors = {"NODE_REF_UNKNOWN", "NODE_MISSING", "NODE_REF_DUPLICATE", "NODE_KIND_NO_REF"}
            assert r["repairs"] == (1 if code in errors else 0), (case, n)
            assert not errors & set(r["issues_final"]), (case, n, r["issues_final"])
    finally:
        measure.close()
    assert {c["step"] for c in calls} == {"generator", "node_repair"}


def test_expand_failure_leaves_an_empty_box(monkeypatch):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    from scripts.phase0b import expand
    from scripts.phase0b.fit import Measurer
    run = load_run(_FIX / "runs" / "decks" / "deck-qbr-data__r1")
    plan = run["slides"][1]["plan"]
    monkeypatch.setattr(expand, "draw", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    sk = ('<Slide><VStack w="1280" h="720" alignItems="stretch"><Text fontSize="30">H</Text>'
          '<KpiRow ref="arr_hero_kpi" h="200" /><KpiRow ref="supporting_kpis" grow="1" /></VStack></Slide>')
    m = Measurer()
    try:
        xml, rep = expand.expand_nodes(sk, plan, run["theme"]["element"], m, run["theme"])
    finally:
        m.close()
    codes = [i["code"] for i in rep["issues"]]
    assert codes.count("NODE_EXPAND_FAILED") == 2 and '<VStack h="200" />' in xml


def test_first_try_only_by_default(tmp_path):
    """D12: 1a records an error on the first try and does not repair it."""
    if not shutil.which("node"):
        pytest.skip("node not installed")
    from scripts import node_test
    from scripts.phase0b.fit import Measurer
    assert node_test.MAX_REPAIRS == 0
    run = load_run(_FIX / "runs" / "decks" / "deck-qbr-data__r1")
    slide = next(s for s in run["slides"] if s["number"] == 2)
    calls, m = [], Measurer()
    try:
        r = node_test.run_slide(run, slide, node_test.ScriptedLLM(_FIX / "scripted"), m, tmp_path, "Inter", True, calls)
    finally:
        m.close()
    assert r["repairs"] == 0 and len(calls) == 1 and "NODE_REF_UNKNOWN" in r["issues_final"]


@pytest.mark.parametrize("tag,variant,block", [("Timeline", "cards", True), ("Timeline", "rail", False),
                                               ("Ul", "tiles", True), ("Ul", "icon", False),
                                               ("ProcessArrow", "step_cards", True), ("ProcessArrow", "alternating", False)])
def test_block_variants_drawn_where_phase0b_has_one(tag, variant, block):
    from scripts.phase0b.expand import as_block
    comp = {"kind": "x", "content_data": {}}
    assert as_block({"tag": tag, "attrs": {"ref": "c", "variant": variant}}, comp) is block


def test_timeline_cards_variant_expands_to_a_block():
    if not shutil.which("node"):
        pytest.skip("node not installed")
    from scripts.phase0b.expand import expand_nodes
    from scripts.phase0b.fit import Measurer
    run = load_run(_FIX / "runs" / "decks" / "gate-deck-all-nodes-dense__r1")
    plan = run["slides"][4]["plan"]   # brand_timeline, conversion_flow, conversion_rules
    sk = ('<Slide><VStack w="1280" h="720" alignItems="stretch"><Text fontSize="30">H</Text>'
          '<Timeline ref="brand_timeline" variant="cards" h="200" /><Flow ref="conversion_flow" grow="1" />'
          '<Ul ref="conversion_rules" variant="tiles" /></VStack></Slide>')
    m = Measurer()
    try:
        xml, rep = expand_nodes(sk, plan, run["theme"]["element"], m, run["theme"])
    finally:
        m.close()
    assert 'id="slot-brand_timeline"' in xml and "<Timeline" not in xml       # drawn as a block
    assert 'id="slot-conversion_rules"' in xml and "<Ul" not in xml
    assert 'id="node-conversion_flow"' in xml                                 # no variant: native
