"""Timeline composition node (composition spec §8), POM_NODES=timeline: every composition word, the default chosen
from the content, every alias, requires / fallback, the head / detail split (C10), emphasis, attributes, peer ids,
and the generator / context / validator hooks (LLM-free). process_arrow and flow have no node (user, 2026-11-02)."""

import re

import pytest

from src.compiler.nodes import compose, composed, spec
from src.compiler.nodes import sequences as S

ROADMAP = {"component_id": "roadmap", "kind": "timeline", "design_hint": "highlight Nov, where we are now",
           "content_data": {"direction": "horizontal", "timeline_items": [
               {"date": "Jul–Aug", "label": "Growth activation — search scaling, placement expansion"},
               {"date": "Sep–Oct", "label": "Festive push — bundles, competitor conquesting"},
               {"date": "Nov", "label": "Post-festive retention — retarget new-to-brand buyers"},
               {"date": "Dec", "label": "Year-end consolidation — set next year's plan"}]}}
SHORT_TL = {"component_id": "short", "kind": "timeline", "content_data": {"timeline_items": [
    {"date": "Q1", "label": "Pilot"}, {"date": "Q2", "label": "Scale"}, {"date": "Q3", "label": "Review"}]}}
MANY = {"component_id": "many", "kind": "timeline", "content_data": {"timeline_items": [
    {"date": f"W{i}", "label": f"Week {i} — detail {i}"} for i in range(8)]}}


def plan(*comps):
    return {"slide_title": "Four phases", "components": [{"component_id": "title", "kind": "title", "count": 1},
                                                          *(dict(c, count=1) for c in comps)]}


def run(tag, *comps):
    return S.expand(f'<Slide><VStack w="1280" h="720">{tag}</VStack></Slide>', plan(*comps))


def codes(res):
    return [i["code"] for i in res["issues"]]


def used(res, cid):
    return res["components"][cid]["composition"]


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "timeline")


# ── shared text rules (C10) ───────────────────────────────────────────────────

@pytest.mark.parametrize("s,head,detail", [
    ("Phase 1: Foundation — detail here", "Phase 1: Foundation", "detail here"),
    ("Head: detail", "Head", "detail"), ("Plain step", "Plain step", ""), ("Ratio 3:1 — up", "Ratio 3:1", "up"),
    ("Growth activation — search scaling", "Growth activation", "search scaling"),
])
def test_split_dash_before_colon(s, head, detail):
    assert compose.split(s) == (head, detail)


def test_requires_checks():
    assert spec.check("labels_short", SHORT_TL) and not spec.check("labels_short", ROADMAP)
    assert spec.check("count_le_7", ROADMAP) and not spec.check("count_le_7", MANY)


# ── default chosen from the content: native -> rail -> columns ─────────────────

def test_bare_short_timeline_draws_native():
    res = run('<Timeline ref="short" />', SHORT_TL)
    assert used(res, "short") == "native" and codes(res) == []
    assert res["xml"].count("<TimelineItem") == 3 and 'title="Scale"' in res["xml"]


def test_bare_timeline_with_details_draws_rail():
    res = run('<Timeline ref="roadmap" />', ROADMAP)
    assert used(res, "roadmap") == "rail" and "NODE_DEFAULT_FROM_CONTENT" in codes(res) and res["ok"]
    assert "NODE_TEXT_SPLIT" in codes(res) and "NODE_VARIANT_UNMET" not in codes(res)


def test_bare_timeline_past_seven_points_draws_columns():
    assert used(run('<Timeline ref="many" />', MANY), "many") == "columns"


# ── every composition draws its words, in order, with peer ids ─────────────────

@pytest.mark.parametrize("variant", ["rail", "columns", "rows", "banded"])
def test_code_drawn_compositions(variant):
    res = run(f'<Timeline ref="roadmap" variant="{variant}" />', ROADMAP)
    x = res["xml"]
    assert used(res, "roadmap") == variant and res["ok"] and "<Timeline" not in x
    for d, h, detail in S.items(ROADMAP):
        assert f">{h}<" in x and f">{detail}<" in x and f">{d.upper()}<" in x     # every word kept
    for k in range(4):
        assert f'id="card-roadmap-{k}"' in x
    if variant != "rail":                                                         # rail alternates above / below
        pos = [x.index(f">{h}<") for _, h, _ in S.items(ROADMAP)]
        assert pos == sorted(pos)                                                 # plan order
    if variant in ("rows", "banded"):
        assert re.search(r'id="card-roadmapx-\d+"', x)                            # inner boxes: one peer group (C11)


def test_rail_alternates_above_and_below():
    x = run('<Timeline ref="roadmap" variant="rail" />', ROADMAP)["xml"]
    top, dots, bottom = re.findall(r'<HStack gap="0" alignItems="(?:end|center|start)">(.*?)</HStack>(?=<HStack gap="0"|</VStack>)',
                                   x)[:3]
    assert "Growth activation" in top and "Post-festive retention" in top
    assert "Festive push" in bottom and "Year-end consolidation" in bottom
    assert dots.count('shapeType="ellipse"') == 4
    assert top.count('<VStack w="1" grow="1" />') == 2 and bottom.count('<VStack w="1" grow="1" />') == 2


# ── emphasis ──────────────────────────────────────────────────────────────────

def test_emphasis_is_the_hinted_point():
    assert S.emphasis_index(ROADMAP) == 2 and S.emphasis_index(SHORT_TL) is None
    x = run('<Timeline ref="roadmap" variant="columns" />', ROADMAP)["xml"]
    assert re.search(r'id="card-roadmap-2"[^>]*backgroundColor="\$panelDark"', x)
    assert not re.search(r'id="card-roadmap-1"[^>]*\$panelDark', x)
    rail = run('<Timeline ref="roadmap" variant="rail" />', ROADMAP)["xml"]
    assert rail.count('shapeType="ellipse" w="22" h="22" fill.color="$accent"') == 1


def test_banded_done_now_ahead():
    x = run('<Timeline ref="roadmap" variant="banded" />', ROADMAP)["xml"]
    bands = re.findall(r'<HStack padding="12" backgroundColor="(\$\w+)"', x)
    assert bands == ["$accent", "$accent", "$panelDark", "$neutral"]


# ── fallbacks, aliases, unknown ───────────────────────────────────────────────

@pytest.mark.parametrize("comp,variant,got", [
    (ROADMAP, "native", "rail"),                   # details
    (MANY, "rail", "columns"),                     # count_le_7
    (MANY, "native", "columns"),                   # details -> rail -> past 7 points
])
def test_fallbacks(comp, variant, got):
    res = run(f'<Timeline ref="{comp["component_id"]}" variant="{variant}" />', comp)
    assert used(res, comp["component_id"]) == got and "NODE_VARIANT_UNMET" in codes(res)


@pytest.mark.parametrize("comp,old,new", [
    (ROADMAP, "cards", "columns"), (ROADMAP, "alternating", "rail"), (SHORT_TL, "vertical", "native"),
])
def test_aliases(comp, old, new):
    res = run(f'<Timeline ref="{comp["component_id"]}" variant="{old}" />', comp)
    assert used(res, comp["component_id"]) == new and "NODE_ATTR_ALIAS" in codes(res)


def test_vertical_alias_turns_native_timeline():
    assert 'direction="vertical"' in run('<Timeline ref="short" variant="vertical" />', SHORT_TL)["xml"]


def test_unknown_variant():
    res = run('<Timeline ref="short" variant="zigzag" />', SHORT_TL)
    assert used(res, "short") == "native" and "NODE_VARIANT_UNKNOWN" in codes(res)


# ── attributes ────────────────────────────────────────────────────────────────

def test_attributes_layer_and_codes():
    res = run('<Timeline ref="roadmap" variant="columns" item.backgroundColor="$accentSoft" grow="2" '
              'label.fontSize="40" connector.fill.color="#FF0000" wiggle="1" />', ROADMAP)
    assert sorted(codes(res)) == ["LITERAL_COLOR", "NODE_ATTR_DROPPED", "NODE_ATTR_UNKNOWN", "NODE_TEXT_SPLIT"]
    assert not res["ok"]
    x = res["xml"]
    assert x.count('backgroundColor="$accentSoft"') == 3 and 'backgroundColor="$panelDark"' in x   # emphasis kept
    assert 'grow="2"' in x and 'fontSize="40"' not in x


def test_code_owned_native_attributes_dropped():
    res = run('<Timeline ref="short" connectorColor="$accent" />', SHORT_TL)
    assert codes(res) == ["NODE_ATTR_DROPPED"]


def test_ref_errors_and_hand_drawn():
    assert codes(run('<Timeline ref="nope" />', SHORT_TL)) == ["NODE_REF_UNKNOWN"]
    assert codes(run('<Timeline ref="short" /><Timeline ref="short" />', SHORT_TL)) == ["NODE_REF_DUPLICATE"]
    empty = {"component_id": "e", "kind": "timeline", "content_data": {"timeline_items": []}}
    assert codes(run('<Timeline ref="e" />', empty)) == ["NODE_ITEM_MISSING"]
    hand = '<Timeline direction="horizontal"><TimelineItem date="Q1" title="x" /></Timeline>'
    assert hand in run(hand, SHORT_TL)["xml"]


def test_switched_off_is_left_alone(monkeypatch):
    monkeypatch.setenv("POM_NODES", "chart")
    res = run('<Timeline ref="short" />', SHORT_TL)
    assert '<Timeline ref="short" />' in res["xml"] and res["components"] == {}


def test_process_and_flow_have_no_node(monkeypatch):
    monkeypatch.setenv("POM_NODES", "timeline,process_arrow,flow")
    assert S.kinds_on() == ["timeline"] and "process_arrow" not in spec.nodes() and "flow" not in spec.nodes()
    assert list(spec.blocks()["process_arrow"]["variants"]) == ["chevrons", "numbered", "alternating", "step_cards"]
    assert list(spec.blocks()["flow"]["variants"]) == ["boxes", "numbered", "step_cards"]


# ── prompt, hooks ─────────────────────────────────────────────────────────────

def test_yaml_names_match():
    assert list(spec.blocks()["timeline"]["variants"]) == list(S.node("timeline")["compositions"])


def test_prompt_lines_carry_no_text():
    line = S.prompt_line(ROADMAP)
    assert "variants rail | columns | rows | banded" in line and "Festive" not in line and '<Timeline ref="roadmap"/>' in line
    assert "native | rail | columns | rows | banded" in S.prompt_line(SHORT_TL)
    lines = S.node_lines()
    assert "<Timeline ref" in lines and "alternating above and below" in lines and "ProcessArrow" not in lines


def test_generator_prompt_hides_timeline_text(monkeypatch):
    from src.agents import generator
    state = {"slide_plans": [plan(ROADMAP)], "current_slide_index": 0, "contract": {}, "raw_request": "x"}
    system, user = generator._render_prompts(state)
    assert "## TIMELINES" in system and "TIMELINE roadmap:" in user
    assert "Festive push" not in user
    monkeypatch.setenv("POM_NODES", "")
    assert "Festive push" in generator._render_prompts(state)[1]


def test_context_builder_takes_the_tag():
    from src.agents.context_builder import build_contract
    from src.agents.style_resolver import resolve_theme
    c = build_contract(plan(ROADMAP), resolve_theme("corporate-slate"))
    assert "variant" in c["allowed_attributes"]["Timeline"] and "item.*" in c["allowed_attributes"]["Timeline"]


def test_validator_expands(monkeypatch):
    from src.agents import validator
    seen = {}

    def fake_norm(xml):
        seen["xml"] = xml
        return {"issues": [], "auto_fixed": 0, "blocking": True, "cleaned_xml": xml}
    monkeypatch.setattr(validator, "normalize_xml", fake_norm)
    monkeypatch.setattr(validator, "nesting_compile_failure", lambda issues: {"diagnostics": [], "ok": False})
    validator.validator_node({"current_xml": '<Slide><VStack><Timeline ref="roadmap" variant="columns" /></VStack></Slide>',
                              "run_id": "t", "slide_plans": [plan(ROADMAP)], "current_slide_index": 0})
    assert 'id="card-roadmap-3"' in seen["xml"]


def test_composed_registry():
    assert composed.kinds_on() == ["timeline"]
    assert composed.all_drawn(plan(ROADMAP), "timeline") and not composed.all_drawn(plan(ROADMAP), "chart")


def test_h_for_another_drawing_becomes_a_floor():
    x = run('<Timeline ref="roadmap" h="92" />', ROADMAP)["xml"]          # a native dot row's height, drawn as rail
    outer = re.search(r'<VStack w="1280" h="720"><VStack([^>]*)>', x).group(1)
    assert 'minH="92"' in outer and 'grow="1"' in outer and ' h="92"' not in outer
    x = run('<Timeline ref="roadmap" variant="rows" h="300" />', ROADMAP)["xml"]   # asked for: kept
    assert ' h="300"' in re.search(r'<VStack w="1280" h="720"><VStack([^>]*)>', x).group(1)
