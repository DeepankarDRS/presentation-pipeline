"""The prompts and the repair path of a slide whose components code draws (POM_NODES): what the generator and the
repairer are actually given. Found by running the graph with a fake LLM, 2026-11-04."""

from pathlib import Path

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


# ── from the paid check, 2026-11-04 ──────────────────────────────────────────

def slide(body, align="stretch"):
    return f'<Slide><VStack w="1280" h="720" alignItems="{align}">{body}</VStack></Slide>'


def test_the_attribute_names_the_llm_reached_for_are_read_not_errors():
    cards = dict(CARDS, content_data={"card_layout": "grid", "cards": [{"title": "A", "bullets": ["one"]}, {"title": "B", "bullets": ["two"]}]})
    r = composed.expand(slide('<Timeline ref="road" variant="columns" connector.color="$neutral"/>'
                              '<CardGrid ref="levers" bullets.color="$surface"/>'), plan(LINE, cards))
    assert r["ok"], r["issues"]
    assert sum(i["code"] == "NODE_ATTR_ALIAS" for i in r["issues"]) == 2
    assert 'fill.color="$neutral"' in r["xml"]
    assert 'color="$surface"' in r["xml"]


def test_the_real_attribute_name_wins_over_its_alias():
    cards = dict(CARDS, content_data={"card_layout": "grid", "cards": [{"title": "A", "bullets": ["one"]}, {"title": "B", "bullets": ["two"]}]})
    r = composed.expand(slide('<CardGrid ref="levers" body.color="$textMain" bullets.color="$surface"/>'), plan(cards))
    assert r["ok"] and 'color="$surface"' not in r["xml"]


@pytest.mark.parametrize("align,held", [("start", True), ("center", True), ("end", True), ("stretch", False)])
def test_a_node_keeps_the_width_under_a_parent_that_does_not_stretch(align, held):
    out = composed.hold_width(slide('<Timeline ref="road" grow="1"/>', align), plan(LINE))
    assert ('alignSelf="stretch"' in out) is held


def test_a_node_sized_by_the_llm_or_in_a_row_is_left_alone():
    p = plan(LINE)
    for xml in (slide('<Timeline ref="road" w="600"/>', "start"), slide('<Timeline ref="road" alignSelf="end"/>', "start"),
                slide('<HStack alignItems="start"><Timeline ref="road"/></HStack>', "stretch"),
                slide('<VStack alignItems="start"><Text>x</Text></VStack><Timeline ref="road"/>', "stretch")):
        assert composed.hold_width(xml, p) == xml


def test_a_ref_on_a_component_code_does_not_draw_says_how_to_write_it():
    note = {"component_id": "callout", "kind": "narrative", "count": 1, "content_summary": "x",
            "content_data": {"text": "What gets measured gets scaled."}}
    r = composed.expand(slide('<CardGrid ref="levers"/><CardGrid ref="callout"/>'), plan(CARDS, note))
    msg = next(i["message"] for i in r["issues"] if i["code"] == "NODE_REF_UNKNOWN")
    assert not r["ok"] and "narrative" in msg and "by hand" in msg and "What gets measured gets scaled." in msg


def test_a_ref_under_the_wrong_tag_names_the_right_tag():
    r = composed.expand(slide('<CardGrid ref="kpis"/><CardGrid ref="levers"/>'), plan(KPIS, CARDS))
    msg = next(i["message"] for i in r["issues"] if i["code"] == "NODE_REF_UNKNOWN")
    assert '<KpiRow ref="kpis"/>' in msg


class _Reply:
    def __init__(self, xml):
        self.content, self.seen = xml, []
        self.response_metadata = {"token_usage": {"prompt_tokens": 1, "completion_tokens": 1}, "model_name": "fake"}

    def invoke(self, messages):
        self.seen.append(messages)
        return self


def _regen_state(**extra):
    from src.state import initial_state
    state = initial_state(run_id="regen", raw_request="r", deck_min_threshold=0, theme_name="corporate-slate")
    state.update(slide_plans=[plan(LINE, LIST)], current_slide_index=0, retry_count=1, retry_tier=1, **extra)
    from src.agents.style_resolver import resolve_theme
    state["resolved_theme"] = resolve_theme("corporate-slate")
    state["contract"] = context_builder.context_builder_node(state)["contract"]
    state["normalize_result"] = {"issues": [], "cleaned_xml": "<Slide/>", "tags_xml": "<Slide/>"}
    state["compile_result"] = {"ok": False, "diagnostics": [{"type": "INVALID_VALUE", "message": "width must be positive"}]}
    return state


def test_regenerate_with_no_outline_keeps_the_plan_and_asks_for_the_node_tags(monkeypatch):
    from src.agents import repairer
    llm = _Reply("<Slide/>")
    monkeypatch.setattr(repairer, "get_llm", lambda step: llm)
    planned = []
    monkeypatch.setattr(repairer, "plan_single_slide", lambda *a, **k: planned.append(a))
    result = repairer.repairer_node(_regen_state())
    assert result["retry_tier"] == repairer.REGENERATE and not planned
    assert result["slide_plans"][0]["components"][0]["content_data"]["timeline_items"][0]["label"] == "Build"
    system, user = (m["content"] for m in llm.seen[0])
    assert "CODE-DRAWN NODES" in system and '<Timeline ref="road"' in user and '<Ul ref="pts"' in user
    assert "width must be positive" in user


def test_regenerate_with_an_outline_replans_from_it_and_counts_the_planner(monkeypatch):
    from src.agents import repairer
    llm = _Reply("<Slide/>")
    monkeypatch.setattr(repairer, "get_llm", lambda step: llm)
    usage = {"tokens_in": 1, "tokens_out": 1, "tokens_reasoning": 0, "tokens_cached": 0, "model": "fake"}
    planned = []
    monkeypatch.setattr(repairer, "plan_single_slide", lambda s, **k: (planned.append(s), (plan(KPIS), usage))[1])
    slide0 = {"slide_index": 0, "slide_title": "Head", "key_messages": ["ARR is $48M"]}
    result = repairer.repairer_node(_regen_state(outline_plan={"slides": [slide0]}))
    assert planned[0]["key_messages"] == ["ARR is $48M"]
    assert result["slide_plans"][0]["components"][0]["kind"] == "kpi_row"
    assert [getattr(h, "step", h.get("step") if isinstance(h, dict) else None) for h in result["generation_history"]][0] == "slide_component_planner"
    assert "KPI TILES kpis" in llm.seen[0][1]["content"]


def test_paid_check_can_rerun_some_plans_on_one_arm():
    from scripts import composition_paid as CP
    assert CP.estimate(6, 1, ("B",))[0] == 6 and CP.estimate(22, 1)[0] == 44


# ── after the rerun, 2026-11-04 ──────────────────────────────────────────────

def test_a_bare_connector_style_is_dropped_and_its_dotted_form_kept():
    from src.compiler.normalizer import normalize_xml
    r = normalize_xml('<Slide><VStack><Flow connectorStyle="straight" connectorStyle.color="$neutral"><FlowNode id="a" text="A"/></Flow></VStack></Slide>')
    assert 'connectorStyle="straight"' not in r["cleaned_xml"] and 'connectorStyle.color="$neutral"' in r["cleaned_xml"]


def test_a_thin_bar_in_a_row_stays_thin():
    from src.compiler.grow_fallback import keep_bars_thin
    out, note = keep_bars_thin('<HStack><Shape shapeType="rect" w="4" h="max"/><VStack grow="1"/></HStack>')
    assert note and 'h="max"' not in out and 'w="4"' in out and 'alignSelf="stretch"' in out


@pytest.mark.parametrize("xml", [
    '<VStack><Shape w="4" h="max"/></VStack>',                 # h="max" in a column is its main axis, as asked
    '<HStack><Shape w="max" grow="1" h="2"/></HStack>',        # a connector line
    '<HStack><Shape w="4" h="max" grow="1"/></HStack>',
    '<HStack><VStack w="4" h="max"/></HStack>',
])
def test_other_max_sizes_are_left_alone(xml):
    from src.compiler.grow_fallback import keep_bars_thin
    assert keep_bars_thin(xml) == (xml, None)


def test_prompt_says_what_has_no_ref_tag_and_that_peers_share_a_panel():
    system, _ = prompts(KPIS)
    assert "never as a ref tag" in system and "Peers look alike" in system and "border.color" in system


def test_table_line_gives_the_words_for_a_heading():
    _, user = prompts(dict(TABLE, content_summary="FLIPCART vs ZAROMA Key Metrics"))
    assert "about: FLIPCART vs ZAROMA Key Metrics" in user and "short heading" in user


# ── what the test PC's PowerPoint renders showed, 2026-11-05 ─────────────────

CHART3 = '<Slide><VStack>{}<Chart showLegend="false" chartType="bar"><ChartSeries name="Actual CPC"><ChartDataPoint label="A" value="1"/></ChartSeries><ChartSeries name="Allowable CPC"><ChartDataPoint label="A" value="1"/></ChartSeries></Chart></VStack></Slide>'


def test_a_chart_of_several_series_with_no_key_gets_its_legend():
    from src.compiler.normalizer import _restore_legends
    out, names = _restore_legends(CHART3.format(""))
    assert 'showLegend="true"' in out and names == ["Actual CPC", "Allowable CPC"]


def test_a_chart_with_a_key_on_the_slide_or_one_series_keeps_its_legend_off():
    from src.compiler.normalizer import _restore_legends
    keyed = CHART3.format('<Text>Actual CPC</Text><Text>Allowable CPC</Text>')
    assert _restore_legends(keyed) == (keyed, [])
    one = '<Chart showLegend="false"><ChartSeries name="Revenue"><ChartDataPoint label="A" value="1"/></ChartSeries></Chart>'
    assert _restore_legends(one) == (one, [])


def test_a_drawn_chart_keeps_the_legend_when_the_llm_turns_it_off():
    from src.compiler.normalizer import normalize_xml
    chart = {"component_id": "c", "kind": "chart", "count": 1, "content_summary": "x", "design_hint": "",
             "content_data": {"chart_type": "bar", "chart_labels": ["A", "B"],
                              "chart_series": [{"name": "Actual CPC", "values": ["1", "2"]}, {"name": "Allowable CPC", "values": ["3", "4"]}]}}
    r = composed.expand(slide('<Chart ref="c" showLegend="false"/>'), plan(chart))
    out = normalize_xml(r["xml"])
    assert 'showLegend="true"' in out["cleaned_xml"] and any(i["code"] == "CHART_LEGEND_RESTORED" for i in out["issues"])


def test_the_word_check_counts_series_names_only_when_a_reader_can_see_them():
    from scripts import composition_paid as CP
    chart = {"component_id": "c", "kind": "chart", "content_data": {"chart_labels": ["A"], "chart_series": [{"name": "Actual CPC"}, {"name": "Allowable CPC"}]}}
    hidden = CHART3.format("").replace('label="A"', 'label="A"')
    assert [m for m in CP.missing_words(hidden, plan(chart))] == ["c: Actual CPC", "c: Allowable CPC"]
    assert CP.missing_words(hidden.replace('showLegend="false"', 'showLegend="true"'), plan(chart)) == []
    assert CP.missing_words(CHART3.format("<Text>Actual CPC</Text><Text>Allowable CPC</Text>"), plan(chart)) == []


def _node(js):
    import json
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("node not installed")
    r = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_zero_width_lines_become_no_line_on_any_table_or_shape_and_real_lines_stay():
    out = _node("""import { noHairlines as f } from './src/node/pptx-post.js';
      console.log(JSON.stringify([
        f('<a:tcPr><a:lnL w="0"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:lnL><a:lnB w="12700"><a:solidFill><a:srgbClr val="CAD5E4"/></a:solidFill></a:lnB></a:tcPr>'),
        f('<p:spPr><a:ln w="0"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln></p:spPr>'),
        f('<p:spPr><a:ln w="0"/></p:spPr>'),
        f(f('<a:lnL w="0"><a:solidFill/></a:lnL>'))]));""")
    assert '<a:lnL w="0"><a:noFill/></a:lnL>' in out[0] and 'w="12700"><a:solidFill><a:srgbClr val="CAD5E4"/>' in out[0]
    assert out[1] == '<p:spPr><a:ln w="0"><a:noFill/></a:ln></p:spPr>' and out[2] == out[1]
    assert out[3] == '<a:lnL w="0"><a:noFill/></a:lnL>'


def test_every_table_loses_the_default_style_and_its_bands():
    out = _node("""import { plainTableStyle as f } from './src/node/pptx-post.js';
      console.log(JSON.stringify([
        f('<a:tblPr firstRow="1" bandRow="1"><a:tableStyleId>{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}</a:tableStyleId></a:tblPr>'),
        f('<a:tblPr bandRow="1"/>')]));""")
    assert out[0] == '<a:tblPr firstRow="1"><a:tableStyleId>{2D5ABB26-0587-4C30-8999-92F81FD0307C}</a:tableStyleId></a:tblPr>'
    assert out[1] == "<a:tblPr/>"


def test_a_compiled_native_table_has_no_zero_lines_or_default_style(tmp_path):
    import re
    import zipfile
    from src.agents.style_resolver import resolve_theme
    from src.agents.validator import normalize_and_compile
    r = composed.expand(slide('<Table ref="gaps"/>'), plan(TABLE))
    ok, cr = normalize_and_compile(r["xml"], resolve_theme("corporate-slate")["element"], tmp_path)
    assert ok, cr
    z = zipfile.ZipFile(tmp_path / "presentation.pptx")
    x = z.read("ppt/slides/slide1.xml").decode("utf-8")
    assert not re.search(r'<a:ln[LRTB] w="0"><a:solidFill', x) and "<a:noFill/></a:lnL>" in x
    assert "5C22544A" not in x and 'bandRow="1"' not in x


def test_all_six_composition_nodes_are_the_default(monkeypatch):
    from src.compiler.nodes import composed, element_refs
    monkeypatch.delenv("POM_NODES", raising=False)
    monkeypatch.delenv("POM_BLOCKS", raising=False)
    assert sorted(composed.kinds_on()) == sorted(["chart", "timeline", "kpi_row", "card_grid", "table", "bullet_list"])
    assert element_refs.mode() == "tiles"
    monkeypatch.setenv("POM_NODES", "")   # set but empty still turns them off
    assert composed.kinds_on() == []
