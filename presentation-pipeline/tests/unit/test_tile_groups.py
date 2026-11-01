"""KPI tiles and cards as composition nodes (composition spec §5, §10 steps 1-2), POM_NODES=kpi_row,card_grid: every
composition word, every alias (tags, parts, variants, layout / arrange), requires / fallback, $tone per tone, item.,
recipes, emphasis, peer ids and the generator / context hooks. LLM-free."""

import re

import pytest

from src.compiler.nodes import cards, compose, composed, element_refs, spec
from src.compiler.nodes import tile_groups as G

KPIS = {"component_id": "kpis", "kind": "kpi_row", "design_hint": "highlight ARR as the hero", "content_data": {
    "kpi_labels": ["ARR", "Net revenue retention", "Gross margin", "CAC payback"],
    "kpi_values": ["$48.2M", "114%", "72.1%", "14 months"],
    "kpi_deltas": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"],
    "kpi_tones": ["good", "good", "bad", "watch"],
    "kpi_icons": ["trending-up", "users", "percent", "clock"]}}
SIX = {"component_id": "six", "kind": "kpi_row", "content_data": {
    "kpi_labels": [f"L{i}" for i in range(6)], "kpi_values": [f"{i}%" for i in range(6)]}}
LEVERS = {"component_id": "levers", "kind": "card_grid", "content_data": {"card_layout": "grid", "focus_card": 0, "cards": [
    {"title": "Search", "tag": "Brand", "icon": "search", "tone": "bad", "key_phrase": "fell",
     "body": "Organic share fell", "bullets": ["Scale exact match", "Cut broad leakage"]},
    {"title": "Placement", "tag": "Media", "icon": "store", "tone": "watch", "body": "Banners cost 2x",
     "bullets": ["Cap home banners"]},
    {"title": "Pricing", "tag": "Price", "body": "Above two rivals", "bullets": ["Price-pack fit"]},
    {"title": "Retention", "tag": "CRM", "tone": "good", "body": "Repeat is 41%", "bullets": ["Win back lapsed"]}]}}
NO_BULLETS = {"component_id": "nb", "kind": "card_grid", "content_data": {"cards": [
    {"title": "A", "body": "x"}, {"title": "B", "body": "y"}, {"title": "C", "body": "z"}]}}
STEPS = {"component_id": "plan30", "kind": "card_grid", "content_data": {"card_layout": "steps", "cards": [
    {"title": "Audit", "body": "Find leaks"}, {"title": "Fix", "body": "Cut waste"}, {"title": "Scale", "body": "Grow"}]}}
LEVER_TAGS = {"component_id": "lv", "kind": "card_grid", "content_data": {"cards": [
    {"title": "A", "tag": "Lever 1"}, {"title": "B", "tag": "Lever 2"}, {"title": "C", "tag": "Lever 3"}]}}


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "kpi_row,card_grid")
    monkeypatch.setenv("POM_BLOCKS", "kpi")


def plan(*comps):
    return {"slide_title": "ARR grew", "components": [dict(c) for c in comps]}


def run(tag, *comps):
    return G.expand(f'<Slide><VStack w="1280" h="720">{tag}</VStack></Slide>', plan(*comps))


def codes(res):
    return [i["code"] for i in res["issues"]]


def used(res, cid):
    return res["components"][cid]["composition"]


def item_tag(xml, cid, i):
    m = re.search(rf'<(?:VStack|HStack)[^<>]*id="card-{cid}-{i}"[^<>]*>', xml)
    return m.group(0) if m else ""


# ── switch and registry ───────────────────────────────────────────────────────

def test_switch(monkeypatch):
    assert G.kinds_on() == ["kpi_row", "card_grid"]
    assert {"kpi_row", "card_grid"} <= set(composed.kinds_on())
    monkeypatch.setenv("POM_BLOCKS", "off")   # KPI text is element refs: no fill pass, no kpi node
    assert G.kinds_on() == ["card_grid"]
    monkeypatch.setenv("POM_NODES", "chart")
    assert G.kinds_on() == []
    assert composed.tag("kpi_row") == "KpiRow" and composed.tag("card_grid") == "CardGrid"


def test_untouched_without_tags():
    xml = '<Slide><Text ref="kpis.0.value"/></Slide>'
    assert G.expand(xml, plan(KPIS))["xml"] == xml


# ── KPI: every word ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("word", ["grid", "strip", "rows", "banded", "bento"])
def test_kpi_words(word):
    r = run(f'<KpiRow ref="kpis" variant="{word}"/>', KPIS)
    assert r["ok"] and used(r, "kpis") == word and not codes(r)
    for i in range(4):   # code writes every part as an element ref
        for f in ("label", "value", "note"):
            assert f'ref="kpis.{i}.{f}"' in r["xml"]
    filled = element_refs.fill_refs(r["xml"], plan(KPIS))
    assert filled["ok"] and "$48.2M" in filled["xml"].replace("<Span", "").replace("</Span>", "") or "48.2" in filled["xml"]


def test_kpi_grid_is_todays_tile():
    xml = run('<KpiRow ref="six" variant="grid"/>', SIX)["xml"]
    assert 'backgroundColor="$surfaceAlt"' in xml and 'border.color="$border"' in xml and 'padding="16"' in xml
    assert "card-six-" not in xml   # today's tiles carry no item id (fit-grow as today)


def test_kpi_strip_one_box_and_dividers():
    xml = run('<KpiRow ref="kpis" variant="strip"/>', KPIS)["xml"]
    assert xml.count('borderLeft.color="$border"') == 3   # a hairline before every item after the first
    assert re.search(r'<HStack[^>]*backgroundColor="\$surfaceAlt"[^>]*border\.color="\$border"', xml)


def test_kpi_rows_badge_and_right_value():
    xml = run('<KpiRow ref="kpis" variant="rows"/>', KPIS)["xml"]
    assert 'variant="square-filled" bgColor="$negativeSoft"' in xml
    assert re.search(r'ref="kpis\.2\.value"[^>]*textAlign="right"', xml)
    assert xml.count('borderTop.color="$border"') == 3


def test_kpi_banded_band_takes_tone():
    xml = run('<KpiRow ref="kpis" variant="banded"/>', KPIS)["xml"]
    assert 'backgroundColor="$negative"' in xml and 'backgroundColor="$warning"' in xml
    assert 'backgroundColor="$panelDark"' in xml   # the emphasis (ARR) band


def test_kpi_bento_big_block_is_emphasis():
    xml = run('<KpiRow ref="kpis" variant="bento"/>', KPIS)["xml"]
    big = re.search(r'<VStack id="cardf-kpis-0"[^>]*>', xml).group(0)
    assert 'backgroundColor="$panelDark"' in big and 'w="42%"' in big
    assert re.search(r'ref="kpis\.0\.value"[^>]*size="hero"', xml)


# ── KPI: requires / fallback / default ───────────────────────────────────────

def test_kpi_strip_needs_five_or_fewer():
    r = run('<KpiRow ref="six" variant="strip"/>', SIX)
    assert used(r, "six") == "grid" and "NODE_VARIANT_UNMET" in codes(r)


def test_kpi_bento_needs_emphasis():
    r = run('<KpiRow ref="six" variant="bento"/>', SIX)
    assert used(r, "six") == "grid" and "NODE_VARIANT_UNMET" in codes(r)


def test_unknown_word_default():
    r = run('<KpiRow ref="six" variant="mosaic"/>', SIX)
    assert used(r, "six") == "grid" and "NODE_VARIANT_UNKNOWN" in codes(r)


def test_bare_tag_hint_composition():
    r = run('<KpiRow ref="kpis"/>', KPIS)   # "highlight ARR as the hero"
    assert used(r, "kpis") == "bento" and "NODE_LOOK_FROM_HINT" in codes(r)
    r = run('<KpiRow ref="six"/>', SIX)
    assert used(r, "six") == "grid" and not codes(r)


def test_hint_style_recipe():
    bar = dict(SIX, design_hint="accent bar on every tile")
    r = run('<KpiRow ref="six"/>', bar)
    assert used(r, "six") == "grid" and 'borderLeft.width="6"' in r["xml"] and "NODE_LOOK_FROM_HINT" in codes(r)


# ── aliases (spec §7) ─────────────────────────────────────────────────────────

def test_tag_alias():
    r = run('<KpiGrid ref="kpis" variant="rows"/>', KPIS)
    assert used(r, "kpis") == "rows" and "NODE_TAG_ALIAS" in codes(r)


def test_part_alias_note_is_delta():
    r = run('<KpiRow ref="kpis" variant="grid" note.color="$textMain"/>', KPIS)
    assert "NODE_ATTR_ALIAS" in codes(r)
    assert re.search(r'ref="kpis\.1\.note"[^>]*color="\$textMain"', r["xml"])


@pytest.mark.parametrize("old,word,style", [("plain", "grid", None), ("filled", "grid", "filled"),
                                            ("toned", "grid", "toned"), ("bar", "grid", "bar"), ("dot", "grid", "dot"),
                                            ("bare", "grid", "bare"), ("inverted", "grid", None),
                                            ("divided", "strip", None)])
def test_kpi_variant_aliases(old, word, style):
    r = run(f'<KpiRow ref="kpis" variant="{old}"/>', KPIS)
    assert used(r, "kpis") == word and "NODE_ATTR_ALIAS" in codes(r)
    if style == "bar":
        assert 'borderLeft.color="$negative"' in r["xml"] and 'borderLeft.color="$warning"' in r["xml"]
    if style == "dot":
        assert 'shapeType="ellipse"' in r["xml"]


@pytest.mark.parametrize("attr,word", [('layout="column"', "rows"), ('layout="row"', "grid"), ('arrange="inline"', "rows"),
                                       ('arrange="side"', "rows"), ('arrange="value-first"', "bento"),
                                       ('arrange="icon-top"', "grid")])
def test_kpi_structure_aliases(attr, word):
    r = run(f'<KpiRow ref="kpis" {attr}/>', KPIS)
    assert used(r, "kpis") == word and "NODE_ATTR_ALIAS" in codes(r)


def test_structure_dropped_beside_variant():
    r = run('<KpiRow ref="kpis" variant="strip" layout="column"/>', KPIS)
    assert used(r, "kpis") == "strip" and "NODE_ATTR_DROPPED" in codes(r)


@pytest.mark.parametrize("old,word", [("lifted", "grid"), ("column", "grid"), ("filled", "grid"), ("outline", "grid"),
                                      ("toned", "grid"), ("accent_top", "grid"), ("inverted", "grid")])
def test_card_variant_aliases(old, word):
    r = run(f'<CardGrid ref="levers" variant="{old}"/>', LEVERS)
    assert used(r, "levers") == word and "NODE_ATTR_ALIAS" in codes(r)


def test_card_numerals_alias_and_own_ordinal_fallback():
    r = run('<CardGrid ref="nb" variant="numerals"/>', NO_BULLETS)
    assert used(r, "nb") == "grid numbered" and 'cardn-nb-0' in r["xml"]
    r = run('<CardGrid ref="lv" variant="numerals"/>', LEVER_TAGS)   # "Lever 1": the tags carry their own number
    assert used(r, "lv") == "grid" and "NODE_VARIANT_UNMET" in codes(r)


@pytest.mark.parametrize("attr,word", [('layout="steps"', "steps"), ('layout="rail"', "rail"), ('arrange="side"', "rows")])
def test_card_structure_aliases(attr, word):
    r = run(f'<CardGrid ref="plan30" {attr}/>', STEPS)
    assert used(r, "plan30") == word


def test_item_variant_style_alias_and_drop():
    r = run('<KpiRow ref="kpis"><Kpi ref="kpis.1" variant="bar"/><Kpi ref="kpis.3" variant="inverted"/></KpiRow>', KPIS)
    assert "NODE_ATTR_ALIAS" in codes(r) and "NODE_ATTR_DROPPED" in codes(r)


# ── cards: every word, requires / fallback ────────────────────────────────────

@pytest.mark.parametrize("word", ["grid", "rows", "columns", "banded", "bento"])
def test_card_words(word):
    r = run(f'<CardGrid ref="levers" variant="{word}"/>', LEVERS)
    assert r["ok"] and used(r, "levers") == word and not codes(r)
    for c in LEVERS["content_data"]["cards"]:
        assert c["title"] in r["xml"] and c["bullets"][0] in r["xml"]


def test_card_grid_is_todays_default():
    """grid with no attributes draws what today's bare <CardGrid> draws (the passed card gate's look)."""
    old = cards.expand('<Slide><VStack w="1280" h="720"><CardGrid ref="levers"/></VStack></Slide>', plan(LEVERS))["xml"]
    new = run('<CardGrid ref="levers" variant="grid"/>', LEVERS)["xml"]

    def norm(x):   # attribute order may differ
        return sorted(tuple(sorted(re.findall(r'(\S+?)="([^"]*)"', t))) for t in re.findall(r"<[A-Z][^<>]*>", x))
    assert norm(old) == norm(new)


def test_card_steps_default_and_rail():
    r = run('<CardGrid ref="plan30"/>', STEPS)
    assert used(r, "plan30") == "steps" and "NODE_DEFAULT_FROM_CONTENT" in codes(r) and 'name="arrow-right"' in r["xml"]
    r = run('<CardGrid ref="levers" variant="rail"/>', LEVERS)
    assert used(r, "levers") == "grid" and "NODE_VARIANT_UNMET" in codes(r)


def test_card_columns_need_bullets():
    r = run('<CardGrid ref="nb" variant="columns"/>', NO_BULLETS)
    assert used(r, "nb") == "grid" and "NODE_VARIANT_UNMET" in codes(r)


def test_card_rows_numbered():
    r = run('<CardGrid ref="nb" variant="rows numbered"/>', NO_BULLETS)
    assert used(r, "nb") == "rows numbered" and ">01<" in r["xml"] and ">03<" in r["xml"]
    r = run('<CardGrid ref="lv" variant="rows numbered"/>', LEVER_TAGS)
    assert used(r, "lv") == "rows"


def test_card_bento_needs_focus():
    r = run('<CardGrid ref="nb" variant="bento"/>', NO_BULLETS)
    assert used(r, "nb") == "grid" and "NODE_VARIANT_UNMET" in codes(r)
    xml = run('<CardGrid ref="levers" variant="bento"/>', LEVERS)["xml"]
    assert re.search(r'<VStack id="cardf-levers-0"[^>]*backgroundColor="\$panelDark"', xml)


def test_card_key_phrase_span():
    xml = run('<CardGrid ref="levers" variant="rows"/>', LEVERS)["xml"]
    assert '<Span color="$negativeText">fell</Span>' in xml


# ── $tone, item., recipes, layers ─────────────────────────────────────────────

@pytest.mark.parametrize("role,soft,text", [("negative", "$negativeSoft", "$negativeText"),
                                            ("positive", "$positiveSoft", "$positiveText"),
                                            ("warning", "$warningSoft", "$warningText"),
                                            ("accent", "$accentSoft", "$accentText"),
                                            ("neutral", "$surfaceAlt", "$textMain")])
def test_tone_value(role, soft, text):
    assert compose.tone_value("$toneSoft", role) == soft
    assert compose.tone_value("$toneText", role) == text
    assert compose.tone_value("$tone", role) == ("$neutral" if role == "neutral" else f"${role}")
    assert compose.tone_value("$textMuted", role) == "$textMuted"


def test_tone_per_item():
    xml = run('<KpiRow ref="kpis" variant="grid" item.borderLeft.color="$tone" item.borderLeft.width="6"/>', KPIS)["xml"]
    for c in ("$negative", "$warning", "$positive"):
        assert f'borderLeft.color="{c}"' in xml
    assert "$tone" not in xml


def test_item_color_sets_tone():
    xml = run('<KpiRow ref="six" variant="rows"><Kpi ref="six.2" color="$negative"/></KpiRow>', SIX)["xml"]
    assert re.search(r'ref="six\.2\.value"[^>]*color="\$negativeText"', xml)
    assert re.search(r'ref="six\.1\.value"[^>]*color="\$accentText"', xml)


def test_item_prefix_reaches_every_item_box():
    xml = run('<CardGrid ref="levers" variant="banded" item.backgroundColor="$surface"/>', LEVERS)["xml"]
    assert all('backgroundColor="$surface"' in item_tag(xml, "levers", i) for i in range(4))


def test_item_tag_wins_over_group():
    xml = run('<CardGrid ref="levers" variant="rows" title.color="$textMuted">'
              '<Card ref="levers.2" title.color="$accent"/></CardGrid>', LEVERS)["xml"]
    assert '<Text fontSize="26" color="$accent" bold="true">Pricing</Text>' in xml.replace(' bold="true" color', ' color') \
        or re.search(r'color="\$accent"[^>]*>Pricing<', xml)


def test_emphasis_not_undone_by_group():
    xml = run('<KpiRow ref="kpis" variant="bento" item.backgroundColor="$surface"/>', KPIS)["xml"]
    big = re.search(r'<VStack id="cardf-kpis-0"[^>]*>', xml).group(0)
    assert 'backgroundColor="$panelDark"' in big
    assert 'backgroundColor="$surface"' in item_tag(xml, "kpis", 1)


def test_literal_colour_dropped():
    r = run('<KpiRow ref="kpis" item.backgroundColor="#FF0000"/>', KPIS)
    assert "LITERAL_COLOR" in codes(r) and "#FF0000" not in r["xml"]


def test_hero_only_on_emphasis():
    r = run('<KpiRow ref="kpis" variant="grid"><Kpi ref="kpis.2" size="hero"/></KpiRow>', KPIS)
    assert "NODE_VARIANT_UNMET" in codes(r)
    assert not re.search(r'ref="kpis\.2\.value"[^>]*size="hero"', r["xml"])


# ── items placed apart, refs ──────────────────────────────────────────────────

def test_item_placed_apart_in_group_form():
    r = run('<HStack><KpiRow ref="kpis" variant="rows"/><Kpi ref="kpis.0" w="30%"/></HStack>', KPIS)
    assert r["ok"] and r["xml"].count('ref="kpis.0.value"') == 1 and 'w="30%"' in item_tag(r["xml"], "kpis", 0)
    assert r["xml"].count('ref="kpis.1.value"') == 1


def test_card_apart_only_flags_missing():
    r = run('<Card ref="levers.1"/>', LEVERS)
    assert not r["ok"] and "NODE_ITEM_MISSING" in codes(r)


def test_ref_errors():
    assert "NODE_REF_UNKNOWN" in codes(run('<KpiRow ref="nope"/>', KPIS))
    assert "NODE_REF_DUPLICATE" in codes(run('<KpiRow ref="kpis"/><KpiRow ref="kpis"/>', KPIS))
    assert "NODE_REF_UNKNOWN" in codes(run('<KpiRow ref="kpis"><Kpi ref="kpis.9"/></KpiRow>', KPIS))


def test_inner_peer_ids():
    xml = run('<CardGrid ref="levers" variant="columns"/>', LEVERS)["xml"]
    assert 'id="card-levers-0"' in xml and re.search(r'id="card-leversx-\d+"', xml)


# ── prompt hooks ──────────────────────────────────────────────────────────────

def test_prompt_lines():
    assert "<KpiRow" in G.node_lines() and "<CardGrid" in G.node_lines() and "$tone" in G.node_lines()
    line = composed.prompt_line(KPIS)
    assert "variants grid | strip | rows | banded | bento" in line and "emphasis 0" in line
    assert "columns" not in composed.prompt_line(NO_BULLETS)
    tags, _, attrs = composed.tags_contract("card_grid")
    assert tags == ["CardGrid", "Card"] and "item.*" in attrs["CardGrid"] and "variant" in attrs["Card"]
