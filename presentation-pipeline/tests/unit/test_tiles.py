"""KPI tile nodes (docs/tile-nodes-spec-2026-10-12.md §2, §4), POM_BLOCKS=tiles: every variant expands, the
resolution order, placement (a group and an item outside it), every NODE_* code, dropped attributes, emphasis-only
inverted / hero, token-only colours, the hand-written ref fallback, the prompt lines and the generator / validator hooks."""

import itertools
import re

import pytest

from src.compiler.nodes import element_refs as E
from src.compiler.nodes import tiles as T

PLAN = {"components": [
    {"component_id": "title", "kind": "title", "count": 1},
    {"component_id": "kpis", "kind": "kpi_row", "count": 4, "design_hint": "highlight Blended ROAS as the hero",
     "content_data": {"kpi_labels": ["Spend", "Revenue", "Blended ROAS", "Orders"],
                      "kpi_values": ["₹114.9L", "₹37.4L", "0.33x", "1,204"],
                      "kpi_deltas": ["Amazon ₹29.4L", "", "ACOS ~307%", "+12%"],
                      "kpi_tones": ["", "good", "bad", "watch"]}},
    {"component_id": "chart", "kind": "chart", "count": 1},
]}
PLAN2 = {"components": PLAN["components"] + [
    {"component_id": "more", "kind": "kpi_row", "count": 2,
     "content_data": {"kpi_labels": ["CPC", "CVR"], "kpi_values": ["₹31.1", "5.5%"]}}]}


def slide(body):
    return f'<Slide><VStack w="1280" h="720" padding="40">{body}</VStack></Slide>'


def run(body, plan=PLAN):
    return T.fill(slide(body), plan)


def codes(res):
    return [i["code"] for i in res["issues"]]


def tile_of(xml, i, cid="kpis"):
    """The tile VStack / HStack (opening tag) holding item i's value."""
    m = re.search(rf'id="kpi[vh]\d-{cid}-{i}"', xml)
    head = xml[:m.start()]
    opens = [o for o in re.finditer(r"<(VStack|HStack)\b[^>]*>", head)]
    for o in reversed(opens):
        if re.search(r'backgroundColor=|border|padding=', o.group(0)):
            return o.group(0)
    raise AssertionError("no tile")


def value_of(xml, i, cid="kpis"):
    return re.search(rf'<Text[^>]*id="kpi[vh]\d-{cid}-{i}"[^>]*>', xml).group(0)


@pytest.fixture(autouse=True)
def tiles_mode(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")


# ── every variant and arrangement ─────────────────────────────────────────────

@pytest.mark.parametrize("variant,arrange", list(itertools.product(list(T.kpi()["variants"]),
                                                                    T.kpi()["item_attributes"]["arrange"]["values"])))
def test_every_variant_and_arrange_expands(variant, arrange):
    res = run(f'<KpiGrid ref="kpis" variant="{variant}" arrange="{arrange}" icon="trending-up"/>')
    assert res["ok"], res["issues"]
    assert "<KpiGrid" not in res["xml"] and "<Kpi" not in res["xml"] and "ref=" not in res["xml"]
    stats = res["components"]["kpis"]
    assert stats["values_placed"] == 4 and stats["labels_placed"] == 4 and stats["notes_placed"] == 3
    assert stats["tile_items"] == 4 and stats["hand_items"] == 0
    # one value id per item, the same peer group as the hand-written route (fit-grow's refGroups)
    assert sorted(re.findall(r'id="(kpi[vh]\d-kpis-\d)"', res["xml"])) == [f"kpiv1-kpis-{i}" for i in range(4)]
    # colours are tokens only: no literal hex anywhere in the expansion
    assert not re.search(r'(?i)(color|backgroundColor|bgColor)="#?[0-9a-f]{6}"', res["xml"])
    assert "${role}" not in res["xml"] and "borderRadius" not in res["xml"]
    if variant == "inverted":   # not the emphasis item: every tile falls back (one warning for the group)
        assert codes(res).count("NODE_VARIANT_UNMET") == 1


def test_variant_looks_follow_the_role():
    xml = run('<KpiGrid ref="kpis" variant="filled"/>')["xml"]
    assert 'backgroundColor="$accentSoft"' in tile_of(xml, 0)      # no tone -> accent
    assert 'backgroundColor="$positiveSoft"' in tile_of(xml, 1)    # good
    assert 'backgroundColor="$negativeSoft"' in tile_of(xml, 2)    # bad
    assert 'backgroundColor="$warningSoft"' in tile_of(xml, 3)     # watch
    assert 'color="$negativeText"' in value_of(xml, 2)
    bar = run('<KpiGrid ref="kpis" variant="bar"/>')["xml"]
    assert 'borderLeft.color="$negative"' in tile_of(bar, 2) and 'borderLeft.width="6"' in tile_of(bar, 2)


def test_neutral_role_has_no_soft_or_text_token():
    xml = run('<KpiGrid ref="kpis" variant="filled" color="$neutral"/>')["xml"]
    assert 'backgroundColor="$surfaceAlt"' in tile_of(xml, 2) and 'color="$textMain"' in value_of(xml, 2)
    dot = run('<KpiGrid ref="kpis" variant="dot" color="$neutral"/>')["xml"]
    assert 'fill.color="$neutral"' in dot


def test_color_overrides_the_tone_t1():
    xml = run('<KpiGrid ref="kpis" variant="filled"><Kpi ref="kpis.2" color="$positive"/></KpiGrid>')["xml"]
    assert 'backgroundColor="$positiveSoft"' in tile_of(xml, 2)


def test_dot_draws_a_marker_and_bare_has_no_tile_fill():
    dot = run('<KpiGrid ref="kpis" variant="dot"/>')["xml"]
    assert dot.count('<Shape shapeType="ellipse" w="8" h="8"') == 4
    bare = run('<KpiGrid ref="kpis" variant="bare"/>')["xml"]
    assert "backgroundColor" not in bare and 'padding="0"' in tile_of(bare, 0)


# ── resolution order ──────────────────────────────────────────────────────────

def test_resolution_order_house_group_variant_group_attrs_item_variant_item_attrs():
    xml = run('<KpiGrid ref="kpis" variant="plain" label.color="$accentText" value.color="$accentText">'
              '<Kpi ref="kpis.1" variant="filled" label.color="$textMain"/>'
              '<Kpi ref="kpis.3" backgroundColor="$accentSoft"/></KpiGrid>')["xml"]
    # item 0: house padding, group variant (plain) fill, group attrs over the variant's colours
    t0, v0 = tile_of(xml, 0), value_of(xml, 0)
    assert 'padding="22"' in t0 and 'backgroundColor="$surfaceAlt"' in t0 and 'color="$accentText"' in v0
    assert '<Text color="$accentText" fontSize="16">Spend</Text>' in xml
    # item 1: its own variant (filled) wins over the group attrs; its own attribute wins over everything
    assert 'backgroundColor="$positiveSoft"' in tile_of(xml, 1) and 'color="$positiveText"' in value_of(xml, 1)
    assert '<Text color="$textMain" fontSize="16">Revenue</Text>' in xml
    # item 3: no item variant, so the group's attributes stay; its box attribute wins
    assert 'backgroundColor="$accentSoft"' in tile_of(xml, 3) and 'color="$accentText"' in value_of(xml, 3)


def test_group_box_attributes_are_the_groups_box():
    xml = run('<KpiGrid ref="kpis" w="62%" gap="20" backgroundColor="$surfaceAlt" padding="12"/>')["xml"]
    group = re.search(r'<(HStack|VStack)[^>]*w="62%"[^>]*>', xml).group(0)
    assert 'gap="20"' in group and 'backgroundColor="$surfaceAlt"' in group and 'padding="12"' in group


@pytest.mark.parametrize("attrs,rows", [("", [4]), ('layout="column"', None), ('cols="2"', [2, 2]),
                                        ('layout="grid"', [4])])
def test_layout_and_cols(attrs, rows):
    xml = run(f'<KpiGrid ref="kpis" {attrs}/>')["xml"]
    if rows is None:
        assert re.search(r'<VStack gap="14" alignItems="stretch"><VStack padding', xml)
        return
    body = xml[xml.index('<VStack w="1280"'):]
    got = [len(re.findall(r'id="kpiv', r)) for r in re.split(r'<HStack gap="14"', body)[1:]]
    assert got == rows


def test_five_items_default_to_a_balanced_grid():
    plan = {"components": [{"component_id": "k", "kind": "kpi_row", "content_data": {
        "kpi_labels": list("abcde"), "kpi_values": ["1", "2", "3", "4", "5"]}}]}
    xml = run('<KpiGrid ref="k"/>', plan)["xml"]
    rows = [len(re.findall(r'id="kpiv', r)) for r in re.split(r'<HStack gap="14"', xml)[1:]]
    assert rows == [3, 2] and T._balanced_cols(7) == 4 and T._balanced_cols(9) == 3


# ── placement ─────────────────────────────────────────────────────────────────

def test_group_skips_the_item_placed_outside_it():
    res = run('<HStack gap="18" grow="1"><KpiGrid ref="kpis" variant="dot" cols="2" w="max"/>'
              '<Kpi ref="kpis.2" variant="inverted" size="hero" arrange="value-first" w="36%"/></HStack>')
    assert res["ok"] and not [c for c in codes(res) if c.startswith("NODE_")], res["issues"]
    xml = res["xml"]
    assert xml.count('id="kpi') == 4 and 'id="kpih0-kpis-2"' not in xml and 'id="kpih1-kpis-2"' in xml
    focus = tile_of(xml, 2)
    assert 'backgroundColor="$panelDark"' in focus and 'w="36%"' in focus
    # value first, then the label, then the note
    after = xml[xml.index(focus):]
    assert after.index("0.33") < after.index("Blended ROAS") < after.index("ACOS")
    assert 'color="$onPanelDark"' in value_of(xml, 2)


def test_items_without_a_group_each_need_a_tag():
    res = run('<Kpi ref="kpis.0"/><Kpi ref="kpis.1"/>')
    assert not res["ok"] and codes(res).count("NODE_ITEM_MISSING") == 2
    msg = next(i["message"] for i in res["issues"] if i["code"] == "NODE_ITEM_MISSING")
    assert '<KpiGrid ref="kpis"/>' in msg and '<Kpi ref="kpis.' in msg


def test_no_tile_tags_and_no_refs_means_every_item_missing():
    res = run('<Text fontSize="20">nothing</Text>')
    assert codes(res).count("NODE_ITEM_MISSING") == 4


def test_hand_written_ref_tile_stays_valid_and_is_counted_t2():
    hand = ('<VStack padding="18" backgroundColor="$panelDark"><Text ref="kpis.3.label"/><Text ref="kpis.3.value"/>'
            '<Text ref="kpis.3.note"/></VStack>')
    res = run(f'<Kpi ref="kpis.0"/><Kpi ref="kpis.1"/><Kpi ref="kpis.2"/>{hand}')
    assert res["ok"], res["issues"]
    stats = res["components"]["kpis"]
    assert stats["tile_items"] == 3 and stats["hand_items"] == 1


def test_two_groups_of_two_components():
    res = run('<KpiGrid ref="kpis" variant="bare"/><KpiGrid ref="more" variant="bar"/>', PLAN2)
    assert res["ok"] and res["components"]["more"]["tile_items"] == 2
    assert 'id="kpiv1-more-0"' in res["xml"]


# ── every code ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body,code,severity", [
    ('<KpiGrid ref="chart"/>', "NODE_REF_UNKNOWN", "error"),                                        # not a kpi_row
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.9"/></KpiGrid>', "NODE_REF_UNKNOWN", "error"),             # index out of range
    ('<KpiGrid ref="kpis"><Kpi ref="more.0"/></KpiGrid><KpiGrid ref="more"/>', "NODE_REF_UNKNOWN", "error"),  # other group's item
    ('<KpiGrid ref="kpis"><Kpi ref="kpis"/></KpiGrid>', "NODE_REF_UNKNOWN", "error"),               # group id on an item
    ('<KpiGrid ref="kpis"/><KpiGrid ref="kpis"/>', "NODE_REF_DUPLICATE", "error"),
    ('<KpiGrid ref="kpis"/><Kpi ref="kpis.1"/><Kpi ref="kpis.1"/>', "NODE_REF_DUPLICATE", "error"),
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.1"/></KpiGrid><Kpi ref="kpis.1"/>', "NODE_REF_DUPLICATE", "error"),
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.1"/><Kpi ref="kpis.1"/></KpiGrid>', "NODE_REF_DUPLICATE", "error"),
    ('<KpiGrid ref="kpis"/><Text ref="kpis.0.value"/>', "NODE_REF_DUPLICATE", "error"),             # a tile + a hand ref
    ('<Kpi ref="kpis.0"/>', "NODE_ITEM_MISSING", "error"),
    ('<KpiGrid ref="kpis" labelColor="$accent"/>', "NODE_ATTR_UNKNOWN", "error"),                   # invented name
    ('<KpiGrid ref="kpis" value.fill.color="$accent"/>', "NODE_ATTR_UNKNOWN", "error"),             # a Shape attr on a Text part
    ('<KpiGrid ref="kpis" size="hero"/>', "NODE_ATTR_DROPPED", "report"),                           # size: an item's only
    ('<KpiGrid ref="kpis" variant="glass"/>', "NODE_VARIANT_UNKNOWN", "warning"),
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.0" variant="inverted"/></KpiGrid>', "NODE_VARIANT_UNMET", "warning"),
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.0" size="hero"/></KpiGrid>', "NODE_VARIANT_UNMET", "warning"),
    ('<KpiGrid ref="kpis" backgroundColor="FF0000"/>', "LITERAL_COLOR", "warning"),
    ('<KpiGrid ref="kpis" value.fontSize="60"/>', "NODE_ATTR_DROPPED", "report"),
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.0" fontSize="60" borderRadius="12"/></KpiGrid>', "NODE_ATTR_DROPPED", "report"),
    ('<KpiGrid ref="kpis"><Kpi ref="kpis.0">ARR 4.2</Kpi></KpiGrid>', "NODE_ATTR_DROPPED", "report"),
    ('<KpiGrid ref="kpis"><Text>x</Text></KpiGrid>', "NODE_ATTR_DROPPED", "report"),
    ('<KpiGrid ref="kpis" arrange="diagonal"/>', "NODE_ATTR_DROPPED", "report"),
    ('<KpiGrid ref="kpis" color="$accentSoft"/>', "NODE_ATTR_DROPPED", "report"),
])
def test_every_code(body, code, severity):
    res = run(body, PLAN2)
    hit = [i for i in res["issues"] if i["code"] == code]
    assert hit, res["issues"]
    assert hit[0]["severity"] == severity
    assert res["ok"] is not any(i["severity"] == "error" for i in res["issues"])


def test_dropped_font_size_is_code_owned():
    res = run('<KpiGrid ref="kpis" value.fontSize="60"><Kpi ref="kpis.0" fontSize="70"/></KpiGrid>')
    assert res["ok"] and 'fontSize="60"' not in res["xml"] and 'fontSize="70"' not in res["xml"]
    assert 'fontSize="28"' in value_of(res["xml"], 1)


def test_toned_without_tones_falls_back_to_plain():
    plan = {"components": [dict(PLAN["components"][1], content_data={
        k: v for k, v in PLAN["components"][1]["content_data"].items() if k != "kpi_tones"})]}
    res = run('<KpiGrid ref="kpis" variant="toned"/>', plan)
    assert "NODE_VARIANT_UNMET" in codes(res) and 'backgroundColor="$surfaceAlt"' in tile_of(res["xml"], 0)


# ── emphasis: the plan picks the item, never the LLM ──────────────────────────

def test_inverted_and_hero_only_on_the_emphasis_item():
    ok = run('<KpiGrid ref="kpis"><Kpi ref="kpis.2" variant="inverted" size="hero"/></KpiGrid>')
    assert ok["ok"] and not [c for c in codes(ok) if c.startswith("NODE_VARIANT")]
    assert 'backgroundColor="$panelDark"' in tile_of(ok["xml"], 2) and 'id="kpih1-kpis-2"' in ok["xml"]
    assert 'fontSize="72"' in value_of(ok["xml"], 2)
    bad = run('<KpiGrid ref="kpis"><Kpi ref="kpis.1" variant="inverted" size="hero"/></KpiGrid>')
    assert codes(bad).count("NODE_VARIANT_UNMET") == 2
    assert "$panelDark" not in bad["xml"] and "kpih" not in bad["xml"]


def test_no_emphasis_named_means_no_inverted_tile():
    plan = {"components": [dict(PLAN["components"][1], design_hint="")]}
    res = run('<KpiGrid ref="kpis" variant="inverted"/>', plan)
    assert "$panelDark" not in res["xml"] and "NODE_VARIANT_UNMET" in codes(res)


def test_inverted_needs_three_items():
    plan = {"components": [{"component_id": "k", "kind": "kpi_row", "design_hint": "highlight B as the hero",
                            "content_data": {"kpi_labels": ["A", "B"], "kpi_values": ["1", "2"]}}]}
    res = run('<KpiGrid ref="k"><Kpi ref="k.1" variant="inverted"/></KpiGrid>', plan)
    assert "$panelDark" not in res["xml"] and "count_ge_3" in " ".join(i["message"] for i in res["issues"])


def test_icons_read_on_a_dark_tile():
    xml = run('<KpiGrid ref="kpis" icon="gauge"><Kpi ref="kpis.2" variant="inverted"/>'
              '<Kpi ref="kpis.0" backgroundColor="$panelDark"/></KpiGrid>')["xml"]
    assert xml.count('<Icon name="gauge" size="22" color="$onPanelDark"/>') == 2
    assert '<Icon name="gauge" size="22" color="$positiveText"/>' in xml   # item 1, tone good, light tile


def test_icon_sits_in_the_label_row_so_fit_grow_can_stack_it():
    xml = run('<KpiGrid ref="kpis" icon="gauge"/>')["xml"]
    assert re.search(r'<HStack gap="10" alignItems="center"><Icon name="gauge"[^>]*/><Text[^>]*>Spend</Text></HStack>', xml)
    side = run('<KpiGrid ref="kpis" icon="gauge" arrange="side"/>')["xml"]
    assert re.search(r'<HStack padding="22"[^>]*alignItems="center"[^>]*><Icon name="gauge"[^>]*/><VStack gap="6" grow="1">', side)


# ── prompt, generator, validator ──────────────────────────────────────────────

def test_prompt_line_names_items_emphasis_and_tones_but_no_values():
    line = T.prompt_line(PLAN["components"][1])
    assert line.startswith("KPI TILES kpis: 4 items (0-3)")
    assert "2 Blended ROAS" in line and "emphasis 2" in line and "2=bad" in line
    assert "₹114.9L" not in line and "0.33x" not in line
    assert '<KpiGrid ref="kpis"/>' in line


def test_node_lines_name_every_variant_and_arrange():
    lines = T.node_lines()
    for name in T.kpi()["variants"]:
        assert f"{name} (" in lines
    for a in T.kpi()["item_attributes"]["arrange"]["values"]:
        assert a in lines


def _gen_state():
    from src.agents.context_builder import build_contract
    from src.agents.style_resolver import resolve_theme
    from src.state import initial_state
    state = initial_state(run_id="tiles-test", raw_request="QBR", deck_min_threshold=0)
    plan = {"slide_index": 0, "slide_type": "data", "slide_title": "ROAS fell", "components": PLAN["components"]}
    state["slide_plans"] = [plan]
    state["contract"] = build_contract(plan, resolve_theme("corporate-slate"))
    return state


def test_generator_prompt_under_tiles(monkeypatch):
    from src.agents.generator import _render_prompts
    system, user = _render_prompts(_gen_state())
    assert "KPI TILES kpis:" in user and "KPI REFS" not in user and "₹114.9L" not in user
    head = system.split("\n## THIS SLIDE\n")[0]
    assert "## KPI TILES (code draws them from the plan)" in head      # fixed lines: in the cached prefix
    assert "# kpi_row" not in system and "# dark_callout_panel" not in system and "# compact_kpi_strip" not in system
    monkeypatch.setenv("POM_BLOCKS", "kpi")
    system, user = _render_prompts(dict(_gen_state()))
    assert "KPI REFS for kpis" in user and "## KPI TILES" not in system


def test_kpi_recipes_stay_on_the_other_routes(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "kpi")
    assert "# kpi_row" in _gen_state()["contract"]["component_recipes"]


def test_validator_expands_tiles(monkeypatch):
    from src.agents import validator
    state = _gen_state()
    state["current_xml"] = slide('<KpiGrid ref="kpis" variant="dot"/><Kpi ref="kpis.9"/>')
    out = validator.validator_node(state)
    assert not out["compile_result"]["ok"] and out["compile_result"]["diagnostics"][0]["type"] == "NODE_REF_UNKNOWN"
    seen = {}

    def fake_norm(xml):
        seen["xml"] = xml
        raise RuntimeError("stop")
    monkeypatch.setattr(validator, "normalize_xml", fake_norm)
    state["current_xml"] = slide('<KpiGrid ref="kpis" variant="dot"/>')
    with pytest.raises(RuntimeError):
        validator.validator_node(state)
    assert "<KpiGrid" not in seen["xml"] and 'id="kpiv1-kpis-0"' in seen["xml"] and "₹114.9" in seen["xml"]


def test_mode_values(monkeypatch):
    assert E.mode() == "tiles" and E.refs_on() and T.on()
    monkeypatch.setenv("POM_BLOCKS", "kpi")
    assert E.refs_on() and not T.on()
    monkeypatch.setenv("POM_BLOCKS", "off")
    assert not E.refs_on()
