"""Timeline / process_arrow / flow composition nodes (composition spec §8), POM_NODES: every composition word, the
default chosen from the content, every alias, requires / fallback, the head / detail split (C10), the numbered
ordinal rule, emphasis, attributes, peer ids, and the generator / context / validator hooks (LLM-free)."""

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
PILLARS = {"component_id": "pillars", "kind": "process_arrow", "content_data": {"process_steps": [
    "Format rebalance", "City re-allocation", "Day-part rollout", "SKU discipline", "Measurement uplift"]}}
PHASES = {"component_id": "phases", "kind": "process_arrow", "content_data": {"process_steps": [
    "Phase 1: Foundation and hygiene — track availability, cut out-of-stocks",
    "Phase 2: Share capture — win search, widen sponsored placements",
    "Phase 3: Consumer expansion — new-to-brand buyers, new platforms",
    "Phase 4: Scale and profit — automate bidding, grow repeat"]}}
FLOW = {"component_id": "chain", "kind": "flow", "content_data": {"flow_steps": [
    "Visibility", "Offtake", "Market share", "Profitability"]}}
MANY = {"component_id": "many", "kind": "process_arrow", "content_data": {"process_steps": [f"S{i}" for i in range(8)]}}


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
    monkeypatch.setenv("POM_NODES", "timeline,process_arrow,flow")


# ── shared text rules (C10) ───────────────────────────────────────────────────

@pytest.mark.parametrize("s,head,detail", [
    ("Phase 1: Foundation — detail here", "Phase 1: Foundation", "detail here"),
    ("Head: detail", "Head", "detail"), ("Plain step", "Plain step", ""), ("Ratio 3:1 — up", "Ratio 3:1", "up"),
    ("Growth activation — search scaling", "Growth activation", "search scaling"),
])
def test_split_dash_before_colon(s, head, detail):
    assert compose.split(s) == (head, detail)


@pytest.mark.parametrize("s,own", [("Phase 2: x", True), ("01. Format", True), ("3) Step", True), ("Step 4 go", True),
                                    ("Format rebalance", False), ("2x growth", False)])
def test_own_ordinal(s, own):
    assert compose.own_ordinal(s) == own


def test_requires_checks():
    assert spec.check("labels_short", PILLARS) and not spec.check("labels_short", PHASES)
    assert spec.check("labels_short", SHORT_TL) and not spec.check("labels_short", ROADMAP)
    assert spec.check("no_own_numbers", PILLARS) and not spec.check("no_own_numbers", PHASES)
    assert not spec.check("no_own_numbers", SHORT_TL)          # dated points
    assert not spec.check("no_own_numbers", {"kind": "process_arrow", "content_data": {"process_steps": ["Q1: a", "Q2: b"]}})
    assert spec.check("count_le_7", MANY) is False and spec.check("count_le_6", PILLARS)


# ── default chosen from the content ───────────────────────────────────────────

def test_bare_timeline_with_details_draws_rail():
    res = run('<Timeline ref="roadmap" />', ROADMAP)
    assert used(res, "roadmap") == "rail" and "NODE_DEFAULT_FROM_CONTENT" in codes(res) and res["ok"]
    assert "NODE_TEXT_SPLIT" in codes(res) and "NODE_VARIANT_UNMET" not in codes(res)


def test_bare_short_timeline_draws_native():
    res = run('<Timeline ref="short" />', SHORT_TL)
    assert used(res, "short") == "native" and codes(res) == []
    assert res["xml"].count("<TimelineItem") == 3 and 'title="Scale"' in res["xml"]


def test_bare_process_short_native_long_steps():
    assert used(run('<ProcessArrow ref="pillars" />', PILLARS), "pillars") == "native"
    res = run('<ProcessArrow ref="phases" />', PHASES)
    assert used(res, "phases") == "steps" and "NODE_DEFAULT_FROM_CONTENT" in codes(res)


def test_bare_flow_native():
    res = run('<Flow ref="chain" />', FLOW)
    assert used(res, "chain") == "native" and res["xml"].count("<FlowConnection") == 3


# ── every composition draws its words, in order, with peer ids ─────────────────

@pytest.mark.parametrize("comp,tag,variant", [
    (ROADMAP, "Timeline", "rail"), (ROADMAP, "Timeline", "rows"), (ROADMAP, "Timeline", "banded"),
    (PILLARS, "ProcessArrow", "steps"), (PILLARS, "ProcessArrow", "steps numbered"), (PILLARS, "ProcessArrow", "rail"),
    (PHASES, "ProcessArrow", "steps"), (PHASES, "ProcessArrow", "rail"),
    (FLOW, "Flow", "steps"), (FLOW, "Flow", "steps numbered"),
])
def test_code_drawn_compositions(comp, tag, variant):
    cid = comp["component_id"]
    res = run(f'<{tag} ref="{cid}" variant="{variant}" />', comp)
    x = res["xml"]
    assert used(res, cid) == variant and res["ok"] and f"<{tag}" not in x
    heads = [h for _, h, _ in S.items(comp)]
    pos = [x.index(f">{h}<") for h in heads]
    assert pos == sorted(pos)                                                  # plan order
    for _, _, d in S.items(comp):
        if d:
            assert f">{d}<" in x                                               # every word of the detail kept
    for k in range(len(heads)):
        assert f'id="card-{cid}-{k}"' in x
    if variant in ("rows", "banded"):
        assert re.search(rf'id="card-{cid}x-\d+"', x)                           # inner boxes: one peer group (C11)


def test_numbers_only_when_numbered():
    x = run('<ProcessArrow ref="pillars" variant="steps numbered" />', PILLARS)["xml"]
    assert all(f'text="{k}"' in x for k in range(1, 6))
    assert 'text="1"' not in run('<ProcessArrow ref="pillars" variant="steps" />', PILLARS)["xml"]


# ── emphasis ──────────────────────────────────────────────────────────────────

def test_emphasis_destination_and_timeline_now():
    assert S.emphasis_index(PILLARS) == 4 and S.emphasis_index(FLOW) == 3
    assert S.emphasis_index(ROADMAP) == 2 and S.emphasis_index(SHORT_TL) is None
    x = run('<ProcessArrow ref="pillars" variant="steps" />', PILLARS)["xml"]
    assert re.search(r'id="card-pillars-4"[^>]*backgroundColor="\$panelDark"', x)
    assert not re.search(r'id="card-pillars-3"[^>]*\$panelDark', x)


def test_banded_done_now_ahead():
    x = run('<Timeline ref="roadmap" variant="banded" />', ROADMAP)["xml"]
    bands = re.findall(r'<HStack padding="12" backgroundColor="(\$\w+)"', x)
    assert bands == ["$accent", "$accent", "$panelDark", "$neutral"]


def test_native_colours_from_parts():
    x = run('<ProcessArrow ref="pillars" />', PILLARS)["xml"]
    assert x.count('color="$accentSoft"') == 4 and 'color="$accent" textColor="$onAccent"' in x


# ── fallbacks, aliases, unknown ───────────────────────────────────────────────

@pytest.mark.parametrize("comp,tag,variant,got", [
    (PHASES, "ProcessArrow", "native", "steps"),               # labels_short
    (PHASES, "ProcessArrow", "steps numbered", "steps"),       # own ordinals (C10)
    (MANY, "ProcessArrow", "steps", "native"),                 # count_le_6
    (MANY, "ProcessArrow", "rail", "native"),                  # count_le_7 -> steps -> native
    (ROADMAP, "Timeline", "native", "rail"),                   # details
])
def test_fallbacks(comp, tag, variant, got):
    res = run(f'<{tag} ref="{comp["component_id"]}" variant="{variant}" />', comp)
    assert used(res, comp["component_id"]) == got and "NODE_VARIANT_UNMET" in codes(res)


@pytest.mark.parametrize("comp,tag,old,new", [
    (PILLARS, "ProcessArrow", "chevrons", "native"), (PILLARS, "ProcessArrow", "numbered", "steps numbered"),
    (PILLARS, "ProcessArrow", "alternating", "rail"), (PILLARS, "ProcessArrow", "step_cards", "steps"),
    (FLOW, "Flow", "boxes", "native"), (FLOW, "Flow", "numbered", "steps numbered"), (FLOW, "Flow", "step_cards", "steps"),
    (ROADMAP, "Timeline", "cards", "rail"), (ROADMAP, "Timeline", "columns", "banded"),
    (SHORT_TL, "Timeline", "vertical", "native"),
])
def test_aliases(comp, tag, old, new):
    res = run(f'<{tag} ref="{comp["component_id"]}" variant="{old}" />', comp)
    assert used(res, comp["component_id"]) == new and "NODE_ATTR_ALIAS" in codes(res)


def test_vertical_alias_turns_native_timeline():
    assert 'direction="vertical"' in run('<Timeline ref="short" variant="vertical" />', SHORT_TL)["xml"]


def test_unknown_variant():
    res = run('<Flow ref="chain" variant="zigzag" />', FLOW)
    assert used(res, "chain") == "native" and "NODE_VARIANT_UNKNOWN" in codes(res)


# ── attributes ────────────────────────────────────────────────────────────────

def test_attributes_layer_and_codes():
    res = run('<ProcessArrow ref="pillars" variant="steps" item.backgroundColor="$accentSoft" grow="2" '
              'label.fontSize="40" connector.color="#FF0000" wiggle="1" />', PILLARS)
    assert sorted(codes(res)) == ["LITERAL_COLOR", "NODE_ATTR_DROPPED", "NODE_ATTR_UNKNOWN"] and not res["ok"]
    x = res["xml"]
    assert x.count('backgroundColor="$accentSoft"') == 4 and 'backgroundColor="$panelDark"' in x   # emphasis kept
    assert 'grow="2"' in x and 'fontSize="40"' not in x


def test_code_owned_native_attributes_dropped():
    res = run('<Timeline ref="short" connectorColor="$accent" />', SHORT_TL)
    assert codes(res) == ["NODE_ATTR_DROPPED"]


def test_ref_errors_and_hand_drawn():
    assert codes(run('<Flow ref="nope" />', FLOW)) == ["NODE_REF_UNKNOWN"]
    assert codes(run('<Flow ref="chain" /><Flow ref="chain" />', FLOW)) == ["NODE_REF_DUPLICATE"]
    empty = {"component_id": "e", "kind": "flow", "content_data": {"flow_steps": []}}
    assert codes(run('<Flow ref="e" />', empty)) == ["NODE_ITEM_MISSING"]
    hand = '<Flow direction="horizontal"><FlowNode id="a" text="x" /></Flow>'
    assert hand in run(hand, FLOW)["xml"]


def test_kind_switched_off_is_left_alone(monkeypatch):
    monkeypatch.setenv("POM_NODES", "timeline")
    res = run('<Flow ref="chain" />', FLOW)
    assert '<Flow ref="chain" />' in res["xml"] and res["components"] == {}


# ── prompt, hooks ─────────────────────────────────────────────────────────────

def test_yaml_names_match():
    for k in S.KINDS:
        assert list(spec.blocks()[k]["variants"]) == list(S.node(k)["compositions"])


def test_prompt_lines_carry_no_text():
    line = S.prompt_line(PHASES)
    assert "variants steps | rail" in line and "Foundation" not in line and '<ProcessArrow ref="phases"/>' in line
    assert "native | rail | rows | banded" in S.prompt_line(SHORT_TL)
    lines = S.node_lines()
    assert "<Timeline ref" in lines and "<Flow ref" in lines and "steps numbered" in lines


def test_generator_prompt_hides_sequence_text(monkeypatch):
    from src.agents import generator
    state = {"slide_plans": [plan(PHASES, ROADMAP)], "current_slide_index": 0, "contract": {}, "raw_request": "x"}
    system, user = generator._render_prompts(state)
    assert "## TIMELINES, PROCESSES, FLOWS" in system and "PROCESS ARROW phases:" in user and "TIMELINE roadmap:" in user
    assert "Foundation and hygiene" not in user and "Festive push" not in user
    monkeypatch.setenv("POM_NODES", "")
    assert "Foundation and hygiene" in generator._render_prompts(state)[1]


def test_context_builder_takes_the_tags():
    from src.agents.context_builder import build_contract
    from src.agents.style_resolver import resolve_theme
    c = build_contract(plan(PHASES, FLOW), resolve_theme("corporate-slate"))
    assert "variant" in c["allowed_attributes"]["ProcessArrow"] and "item.*" in c["allowed_attributes"]["Flow"]


def test_validator_expands(monkeypatch):
    from src.agents import validator
    seen = {}

    def fake_norm(xml):
        seen["xml"] = xml
        return {"issues": [], "auto_fixed": 0, "blocking": True, "cleaned_xml": xml}
    monkeypatch.setattr(validator, "normalize_xml", fake_norm)
    monkeypatch.setattr(validator, "nesting_compile_failure", lambda issues: {"diagnostics": [], "ok": False})
    validator.validator_node({"current_xml": '<Slide><VStack><Flow ref="chain" variant="steps" /></VStack></Slide>',
                              "run_id": "t", "slide_plans": [plan(FLOW)], "current_slide_index": 0})
    assert 'id="card-chain-3"' in seen["xml"]


def test_composed_registry():
    assert composed.kinds_on() == ["timeline", "process_arrow", "flow"]
    assert composed.all_drawn(plan(FLOW), "flow") and not composed.all_drawn(plan(FLOW), "timeline")
