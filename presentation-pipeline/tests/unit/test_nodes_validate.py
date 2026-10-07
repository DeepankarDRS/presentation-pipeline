"""Node contract checks (docs/derived-blocks-planning-2026-10-06.md §3.2, §3.6): one test per NODE_* code."""

import json
from pathlib import Path

import pytest

from src.compiler.nodes import spec
from src.compiler.nodes.validate import check_skeleton, ref_tags

_RUNS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nodes" / "runs" / "decks"


def _plan(case: str, n: int) -> dict:
    slides = json.loads((_RUNS / f"{case}__r1" / "slides.json").read_text(encoding="utf-8"))
    return slides[n - 1]["slide_plan"]


QBR2 = lambda: _plan("deck-qbr-data", 2)          # noqa: E731  arr_hero_kpi (1 tile), supporting_kpis (3 tiles)
QBR4 = lambda: _plan("deck-qbr-data", 4)          # noqa: E731  segment_table, segment_insight, kicker_caption
DENSE4 = lambda: _plan("gate-deck-all-nodes-dense", 4)  # noqa: E731  fulfilment_flow, org_chart, architecture_layers


def _slide(inner: str) -> str:
    return f'<Slide><VStack w="1280" h="720" alignItems="stretch"><Text fontSize="30">Head</Text>{inner}</VStack></Slide>'


def _codes(res: dict) -> list[str]:
    return [i["code"] for i in res["issues"]]


def test_clean_skeleton_is_all_ok():
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" h="200" /><KpiRow ref="supporting_kpis" grow="1" />'), QBR2())
    assert res["ok"] and not res["issues"]
    assert {c["status"] for c in res["components"].values()} == {"ok"}
    assert all(c["family"] == "derived" for c in res["components"].values())


def test_unknown_ref_is_an_error_and_the_component_is_missing():
    res = check_skeleton(_slide('<KpiRow ref="hero" h="200" /><KpiRow ref="supporting_kpis" grow="1" />'), QBR2())
    assert not res["ok"] and res["unknown_refs"] == 1
    assert "NODE_REF_UNKNOWN" in _codes(res) and res["components"]["arr_hero_kpi"]["status"] == "missing"
    assert 'ref="hero"' not in res["xml"]


def test_duplicate_ref_keeps_the_first():
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" h="200" /><KpiRow ref="supporting_kpis" grow="1" />'
                                '<KpiRow ref="arr_hero_kpi" h="80" />'), QBR2())
    assert "NODE_REF_DUPLICATE" in _codes(res) and not res["ok"]
    assert res["xml"].count('ref="arr_hero_kpi"') == 1 and 'h="200"' in res["xml"]


def test_bypassed_when_the_items_are_written_by_hand():
    rows = "".join(f"<Tr><Td>{s}</Td></Tr>" for s in ("Enterprise", "Mid-Market", "SMB"))
    res = check_skeleton(_slide(f'<Table>{rows}</Table><Callout ref="segment_insight" /><Text ref="kicker_caption" />'), QBR4())
    assert res["components"]["segment_table"]["status"] == "bypassed" and res["ok"]   # a warning, kept


def test_missing_when_nothing_carries_it():
    res = check_skeleton(_slide('<Callout ref="segment_insight" /><Text ref="kicker_caption" />'), QBR4())
    assert res["components"]["segment_table"]["status"] == "missing" and not res["ok"]


def test_kind_mismatch_uses_the_plan_kind_tag():
    res = check_skeleton(_slide('<Chart ref="segment_table" /><Callout ref="segment_insight" /><Text ref="kicker_caption" />'), QBR4())
    assert res["components"]["segment_table"]["status"] == "kind_mismatch"
    assert '<Table ref="segment_table"' in res["xml"]


def test_ref_on_a_layer_is_an_error():
    res = check_skeleton(_slide('<ProcessArrow ref="fulfilment_flow" h="90" /><Tree ref="org_chart" grow="1" />'
                                '<VStack ref="architecture_layers" grow="1" />'), DENSE4())
    assert "NODE_KIND_NO_REF" in _codes(res) and not res["ok"]
    assert "architecture_layers" not in res["components"]   # a layer is never counted as a node


def test_children_dropped_and_content_attributes_removed():
    plan = _plan("deck-qbr-data", 3)
    res = check_skeleton(_slide('<Chart ref="revenue_chart" chartType="line" h="max" minH="200" showLegend="true">'
                                '<ChartSeries name="x"><ChartDataPoint label="a" value="1" /></ChartSeries></Chart>'
                                '<Callout ref="trend_note" />'), plan)
    assert {"NODE_CHILDREN_DROPPED", "NODE_ATTR_IGNORED"} <= set(_codes(res))
    tag = ref_tags(res["xml"])[0]
    assert tag["body"] == "" and "chartType" not in tag["attrs"] and tag["attrs"]["showLegend"] == "true"


def test_derived_tag_keeps_layout_attributes_only():
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" h="200" backgroundColor="$accent" />'
                                '<KpiRow ref="supporting_kpis" grow="1" />'), QBR2())
    assert res["components"]["arr_hero_kpi"]["status"] == "attr"
    assert "backgroundColor" not in res["xml"]


def test_unknown_variant_falls_back_to_the_default():
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" variant="glossy" h="200" /><KpiRow ref="supporting_kpis" grow="1" />'), QBR2())
    assert "NODE_VARIANT_UNKNOWN" in _codes(res) and res["components"]["arr_hero_kpi"]["variant"] == "plain"


def test_unmet_variant_follows_the_fallback_chain():
    # hero needs exactly one tile; supporting_kpis has three -> hero's fallback inverted needs one singled out -> plain
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" h="200" /><KpiRow ref="supporting_kpis" variant="hero" grow="1" />'), QBR2())
    assert "NODE_VARIANT_UNMET" in _codes(res) and res["components"]["supporting_kpis"]["variant"] == "plain"
    ok = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" variant="hero" h="200" /><KpiRow ref="supporting_kpis" grow="1" />'), QBR2())
    assert ok["components"]["arr_hero_kpi"]["variant"] == "hero" and not ok["issues"]


def test_no_size_gets_grow():
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" /><KpiRow ref="supporting_kpis" grow="1" />'), QBR2())
    assert "NODE_NO_SIZE" in _codes(res) and '<KpiRow ref="arr_hero_kpi" variant="plain" grow="1" />' in res["xml"]


def test_empty_plan_draws_nothing():
    plan = QBR2()
    plan["components"][1]["content_data"] = {"kpi_labels": ["ARR"], "kpi_values": [""]}
    res = check_skeleton(_slide('<KpiRow ref="arr_hero_kpi" h="200" /><KpiRow ref="supporting_kpis" grow="1" />'), plan)
    assert "NODE_EMPTY_PLAN" in _codes(res) and 'ref="arr_hero_kpi"' not in res["xml"]


def test_every_plan_kind_has_a_tag_except_title_and_layer():
    from src.agents.planner_schema import ComponentKindLiteral
    import typing
    kinds = set(typing.get_args(ComponentKindLiteral))
    for k in kinds - spec.NO_REF_KINDS:
        assert spec.tags_for(k), k


@pytest.mark.parametrize("name", ["count_eq_1", "count_ge_3", "one_singled_out", "not_matrix", "all_titles_numbered_ok", "has_tones"])
def test_every_requires_check_is_implemented(name):
    spec.check(name, QBR2()["components"][1])
