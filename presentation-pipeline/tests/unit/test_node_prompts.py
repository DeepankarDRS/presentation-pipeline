"""The prompts and the repair path of a slide whose components code draws (POM_NODES): what the generator and the
repairer are actually given. Found by running the graph with a fake LLM, 2026-11-04."""

import pytest

from src.agents import context_builder, generator
from src.compiler.nodes import composed

ALL = "kpi_row,card_grid,chart,table,timeline,bullet_list"
KPIS = {"component_id": "kpis", "kind": "kpi_row", "count": 3, "weight": "main", "content_summary": "x", "design_hint": "ARR as the hero",
        "content_data": {"kpi_labels": ["ARR", "NRR", "CAC"], "kpi_values": ["$48M", "114%", "14 months"], "kpi_tones": ["good", "", "bad"]}}
CARDS = {"component_id": "levers", "kind": "card_grid", "count": 2, "weight": "main", "content_summary": "x", "design_hint": "",
         "content_data": {"card_layout": "grid", "cards": [{"title": "Search", "body": "a"}, {"title": "Pricing", "body": "b"}]}}
TABLE = {"component_id": "gaps", "kind": "table", "count": 1, "weight": "main", "content_summary": "x", "design_hint": "",
         "content_data": {"table_columns": ["Gap", "Fix"], "table_rows": [["CPC", "Bid"]]}}
LIST = {"component_id": "pts", "kind": "bullet_list", "count": 2, "weight": "main", "content_summary": "x", "design_hint": "icons per point",
        "content_data": {"bullets": ["Search fell", "Pricing rose"]}}
LINE = {"component_id": "road", "kind": "timeline", "count": 2, "weight": "main", "content_summary": "x", "design_hint": "",
        "content_data": {"direction": "horizontal", "timeline_items": [{"date": "Jul", "label": "Build"}, {"date": "Nov", "label": "Ship"}]}}


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")
    monkeypatch.setenv("POM_NODES", ALL)


def plan(*comps):
    return {"slide_index": 0, "slide_title": "Head", "label": "", "subtitle": "", "slide_type": "content", "layout_hint": "",
            "components": list(comps), "content_data": {}}


def prompts(*comps):
    state = {"slide_plans": [plan(*comps)], "current_slide_index": 0, "raw_request": "r", "theme_name": "corporate-slate",
             "completed_slides": [], "core_hook": ""}
    state["contract"] = context_builder.context_builder_node(state)["contract"]
    return generator._render_prompts(state)


def test_kpi_and_card_lines_carry_the_plan_not_an_empty_copy():
    _, user = prompts(KPIS, CARDS)
    assert "0 items" not in user and "0 cards" not in user
    assert "KPI TILES kpis: 3 items" in user and "0 ARR" in user and "CARDS levers: 2 cards" in user and "0 Search" in user
    assert "$48M" not in user                                          # the words stay out of the prompt


def test_prompt_names_the_composition_tag_and_overrules_hand_drawing():
    system, _ = prompts(KPIS)
    assert "<KpiGrid" not in system and "<KpiRow" in system and 'size="hero"' not in system
    assert "CODE-DRAWN NODES" in system


def test_table_and_timeline_lines_drop_the_hand_drawn_limits():
    _, user = prompts(TABLE, LINE)
    assert "never grow on its card" not in user and "put the detail beside them" not in user


def test_no_hand_recipe_for_a_drawn_icon_list():
    assert "icon_rows" not in prompts(LIST)[0]


def test_hand_drawn_kind_keeps_its_rules(monkeypatch):
    monkeypatch.setenv("POM_NODES", "kpi_row")
    _, user = prompts(TABLE, LINE)
    assert "never grow on its card" in user and "put the detail beside them" in user


@pytest.mark.parametrize("xml", ['<Text fontSize="20">Head</Text>', '<Ul><Li>Search fell</Li><Li>Pricing rose</Li></Ul>'])
def test_a_component_left_out_or_typed_by_hand_is_an_error(xml):
    r = composed.expand(f'<Slide><VStack w="1280" h="720">{xml}</VStack></Slide>', plan(LIST))
    assert not r["ok"] and [i["code"] for i in r["issues"]] == ["NODE_ITEM_MISSING"] and '<Ul ref="pts"/>' in r["issues"][0]["message"]


def test_placed_components_and_element_refs_are_not_missing():
    assert composed.expand('<Slide><VStack w="1280" h="720"><Ul ref="pts"/></VStack></Slide>', plan(LIST))["ok"]
    xml = '<Slide><VStack w="1280" h="720"><Text ref="kpis.0.value"/><Text ref="kpis.1.value"/><Text ref="kpis.2.value"/></VStack></Slide>'
    assert not [i for i in composed.expand(xml, plan(KPIS))["issues"] if i["code"] == "NODE_ITEM_MISSING"]


def test_a_component_with_no_data_is_not_missing():
    empty = dict(LIST, content_data={"bullets": []})
    assert composed.expand('<Slide><VStack w="1280" h="720"/></Slide>', plan(empty))["ok"]


def test_the_repairer_gets_the_tags_not_the_expansion(tmp_path, monkeypatch):
    from src.agents import validator
    monkeypatch.chdir(tmp_path)
    tags = '<Slide><VStack w="1280" h="720"><Ul ref="pts" nosuch="1"/></VStack></Slide>'
    out = validator.validator_node({"current_xml": tags, "slide_plans": [plan(LIST)], "current_slide_index": 0, "retry_count": 0,
                                    "run_id": "t", "completed_slides": []})
    assert out["normalize_result"]["tags_xml"] == tags and "<Li" in out["normalize_result"]["cleaned_xml"]


def test_paid_check_cases_hold_every_node_and_its_arms_switch():
    from scripts import composition_paid as CP
    items = CP.items()
    held = {k for it in items for k in it["kind"].split("+")}
    assert held == set(CP.NODES) and all(it["request"] for it in items) and "gj-h1-regen" not in {it["case"] for it in items}
    CP.set_arm("B")
    assert sorted(composed.kinds_on()) == sorted(CP.NODES)
    CP.set_arm("A")
    assert not composed.kinds_on()


def test_paid_check_word_loss_reads_split_numbers_and_finds_a_real_loss():
    from scripts import composition_paid as CP
    p = plan(KPIS)
    xml = '<Text>ARR</Text><Text>$48<Span>M</Span></Text><Text>NRR</Text><Text>114%</Text><Text>14 months</Text>'
    assert [m for m in CP.missing_words(xml, p)] == ["kpis: CAC"]
