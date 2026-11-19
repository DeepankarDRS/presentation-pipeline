"""1a tooling (§4) still used by the galleries and replays: variety signatures, scorer helpers, Phase 0b blocks."""

import json
import shutil
from pathlib import Path

import pytest

from scripts import variety
from scripts.from_plans import load_run
from scripts.node_test_score import invented, node_regions

_FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nodes"






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




# "rail" was the native timeline in the 1a names; since 2026-11-02 it is the alternating drawing (no Phase 0b block),
# the line + boxes (old `cards`) is `columns`, and the native one is `native`
@pytest.mark.parametrize("tag,variant,block", [("Timeline", "cards", True), ("Timeline", "columns", True),
                                               ("Timeline", "rail", False),
                                               ("Timeline", "native", False),
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
          '<Timeline ref="brand_timeline" variant="columns" h="200" /><Flow ref="conversion_flow" grow="1" />'
          '</VStack></Slide>')
    m = Measurer()
    try:
        xml, rep = expand_nodes(sk, plan, run["theme"]["element"], m, run["theme"])
    finally:
        m.close()
    assert 'id="slot-brand_timeline"' in xml and "<Timeline" not in xml       # drawn as a block
    assert 'id="node-conversion_flow"' in xml                                 # no variant: native
