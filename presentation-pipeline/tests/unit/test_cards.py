"""Card tile nodes (docs/tile-nodes-spec-2026-10-12.md §3, §11), POM_BLOCKS=tiles: a bare <CardGrid> draws the
plan's meaning (tones, focus card, key phrases), columns by text length, steps / rail, placement, NODE_* codes,
the LLM's wrapper boxes, the deferred matrix, the prompt lines and the generator / context hooks."""

import copy

import pytest
from lxml import etree

from src.compiler.nodes import cards as C
from src.compiler.nodes import tiles as T


def _grid(cid, cards, layout="grid", **cd):
    return {"component_id": cid, "kind": "card_grid", "count": len(cards),
            "content_data": {"card_layout": layout, **cd, "cards": cards}}


GRID = _grid("bets", [
    {"title": "Close logos", "body": "Worth $4M+ combined ARR", "tone": "good", "key_phrase": "$4M+"},
    {"title": "Fix onboarding", "body": "CAC payback slipped to 19 months", "tone": "bad", "key_phrase": "19 months"},
    {"title": "Ship analytics", "body": "Before the board meeting", "tone": ""},
    {"title": "Hire leads", "bullets": ["Two engineering leads", "One designer"], "tone": "watch"},
], focus_card=1)
STEPS = _grid("plan", [{"title": t, "tag": f"Day {k}"} for k, t in enumerate(["Audit", "Rebuild", "Automate", "Scale"])],
              layout="steps")
MATRIX = _grid("mx", [{"title": "Visibility"}, {"title": "Pricing"}], layout="matrix", columns=["Web"], rows=["A", "B"])
PLAN = {"components": [{"component_id": "title", "kind": "title"}, GRID, STEPS, MATRIX]}


@pytest.fixture(autouse=True)
def tiles_on(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")


def run(body, plan=PLAN):
    return T.fill(f'<Slide><VStack w="1280" h="720" padding="40">{body}</VStack></Slide>', plan)


def codes(res):
    return [i["code"] for i in res["issues"]]


def card_el(xml, cid, i):
    root = etree.fromstring(xml.encode())
    return next(e for e in root.iter() if e.get("id") == f"card-{cid}-{i}")


def text_of(el):
    return "".join(el.itertext())


def test_a_bare_group_draws_every_card_with_the_plans_text():
    res = run('<CardGrid ref="bets"/>')
    assert res["ok"] and codes(res) == [] and res["card_items"]["bets"] == 4
    for i, c in enumerate(GRID["content_data"]["cards"]):
        el = card_el(res["xml"], "bets", i)
        assert c["title"] in text_of(el)
        for line in [c.get("body") or ""] + c.get("bullets", []):
            assert line in text_of(el)


def test_the_plans_meaning_shows_on_a_bare_group():
    xml = run('<CardGrid ref="bets"/>')["xml"]
    good, focus, neutral, watch = (card_el(xml, "bets", i) for i in (0, 1, 2, 3))
    assert focus.get("backgroundColor") == "$panelDark"                       # focus_card drawn dark by code
    # the default `column`: an open card (no fill), its left rule in the tone colour, grey without a tone
    assert watch.get("borderLeft.color") == "$warning" and watch.get("backgroundColor") is None
    assert good.get("borderLeft.color") == "$positive" and good.get("backgroundColor") is None
    assert neutral.get("borderLeft.color") == "$border" and neutral.get("backgroundColor") is None
    filled = run('<CardGrid ref="bets" variant="filled"/>')["xml"]
    assert card_el(filled, "bets", 3).get("backgroundColor") == "$warningSoft"    # filled: watch tone -> toned
    span = good.find(".//Span")
    assert span is not None and span.text == "$4M+" and span.get("color") == "$positiveText"
    assert focus.find(".//B").text == "19 months"                             # key phrase bold on the dark card
    assert all(t.get("color") == "$onPanelDark" for t in focus.iter("Text"))


def test_the_llm_can_restyle_the_focus_card_and_colour_shows_on_every_variant():
    xml = run('<CardGrid ref="bets" variant="outline"><Card ref="bets.1" variant="filled"/>'
              '<Card ref="bets.2" color="$negative"/></CardGrid>')["xml"]
    assert card_el(xml, "bets", 1).get("backgroundColor") == "$surfaceAlt"   # its own variant wins
    red = card_el(xml, "bets", 2)
    assert red.get("borderLeft.color") == "$negative"                         # outline with_color: an edge
    for v in ("column", "filled", "accent_top", "numerals", "toned"):
        x = run(f'<CardGrid ref="bets" variant="{v}"><Card ref="bets.2" color="$negative"/></CardGrid>')["xml"]
        el = card_el(x, "bets", 2)
        assert "$negative" in etree.tostring(el, encoding="unicode"), v


def test_toned_leaves_cards_without_a_tone_neutral():
    el = card_el(run('<CardGrid ref="bets" variant="toned"/>')["xml"], "bets", 2)
    assert el.get("backgroundColor") == "$surfaceAlt" and el.get("borderLeft.color") == "$neutral"


def test_columns_follow_the_text_never_more_than_four():
    short = _grid("s", [{"title": t} for t in "ABCDEFG"])
    assert C.columns(short, 7) == 4 and C.columns(short, 5) == 3 and C.columns(short, 4) == 4
    long_ = _grid("l", [{"title": "T", "body": "x" * 150}] * 4)
    assert C.columns(long_, 4) == 2
    xml = run('<CardGrid ref="s"/>', {"components": [short]})["xml"]
    root = etree.fromstring(xml.encode())
    group = next(e for e in root.iter("VStack") if e.get("id") == "cardg-s")
    assert [len(r) for r in group] == [4, 3]
    assert all(c.get("w") == "1" and c.get("grow") == "1" for r in group for c in r)
    fixed = etree.fromstring(run('<CardGrid ref="s" cols="2"/>', {"components": [short]})["xml"].encode())
    assert not any(str(e.get("id", "")).startswith("cardg-") for e in fixed.iter())   # the LLM's cols: not re-gridded


def test_steps_number_the_tag_line_join_with_arrows_and_darken_the_destination():
    xml = run('<CardGrid ref="plan"/>')["xml"]
    root = etree.fromstring(xml.encode())
    assert len([e for e in root.iter("Icon") if e.get("name") == "arrow-right"]) == 3
    assert "01 · DAY 0" in text_of(card_el(xml, "plan", 0))
    assert card_el(xml, "plan", 3).get("backgroundColor") == "$panelDark"
    rail = run('<CardGrid ref="plan" layout="rail"/>')["xml"]
    assert "01 · " not in rail and ">01<" in rail and "arrow-right" not in rail
    bad = run('<CardGrid ref="bets" layout="steps"/>')
    assert "NODE_ATTR_DROPPED" in codes(bad) and "arrow-right" not in bad["xml"]


def test_placement_and_node_codes():
    res = run('<HStack><CardGrid ref="bets" w="max"/><Card ref="bets.1" w="34%"/></HStack>')
    assert res["ok"] and res["xml"].count('id="card-bets-1"') == 1
    assert "NODE_REF_UNKNOWN" in codes(run('<CardGrid ref="nope"/>'))
    assert "NODE_REF_UNKNOWN" in codes(run('<CardGrid ref="bets"><Card ref="plan.0"/></CardGrid>'))
    assert "NODE_REF_UNKNOWN" in codes(run('<Card ref="bets.9"/>'))
    assert "NODE_REF_DUPLICATE" in codes(run('<CardGrid ref="bets"/><CardGrid ref="bets"/>'))
    missing = run('<Card ref="bets.0"/>')
    assert not missing["ok"] and codes(missing).count("NODE_ITEM_MISSING") == 3
    assert "NODE_ATTR_UNKNOWN" in codes(run('<CardGrid ref="bets" title.wobble="1"/>'))
    dropped = run('<CardGrid ref="bets" borderRadius="12" title.fontSize="40"/>')
    assert dropped["ok"] and codes(dropped).count("NODE_ATTR_DROPPED") == 2 and "borderRadius" not in dropped["xml"]
    assert "LITERAL_COLOR" in codes(run('<CardGrid ref="bets" title.color="#FF0000"/>'))


def test_wrappers_the_llm_puts_around_a_group():
    res = run('<Text fontSize="18" bold="true"><CardGrid ref="bets"/></Text>')
    assert res["ok"] and "NODE_ATTR_DROPPED" in codes(res)
    root = etree.fromstring(res["xml"].encode())
    assert not any(t.find(".//VStack") is not None for t in root.iter("Text"))     # no card inside a Text
    panel = run('<VStack backgroundColor="$surfaceAlt" padding="20"><CardGrid ref="bets" variant="filled"/></VStack>')["xml"]
    el = card_el(panel, "bets", 2)
    assert el.get("backgroundColor") is None                                      # same fill: drawn bare
    assert card_el(panel, "bets", 1).get("backgroundColor") == "$panelDark"       # the focus card keeps its fill
    dark = run('<VStack backgroundColor="$panelDark" padding="20"><CardGrid ref="bets"/></VStack>')["xml"]
    assert all(t.get("color") == "$onPanelDark" for t in card_el(dark, "bets", 2).iter("Text"))   # open card on a dark panel


def test_matrix_is_deferred_and_old_plans_without_fields_still_draw():
    assert "mx" not in C.card_components(PLAN)
    assert "NODE_REF_UNKNOWN" in codes(run('<CardGrid ref="mx"/>'))
    old = copy.deepcopy(GRID)
    for c in old["content_data"]["cards"]:
        c.pop("tone", None), c.pop("key_phrase", None)
    old["content_data"].pop("focus_card")
    xml = run('<CardGrid ref="bets"/>', {"components": [old]})["xml"]
    assert all(card_el(xml, "bets", i).get("borderLeft.color") == "$border" for i in range(4))
    old["design_hint"] = "inverted panel on the Hire leads card"
    assert card_el(run('<CardGrid ref="bets"/>', {"components": [old]})["xml"], "bets", 3).get("backgroundColor") == "$panelDark"


def test_prompt_lines():
    line = C.prompt_line(GRID)
    assert "CARDS bets: 4 cards (0-3), grid" in line and "focus 1 (drawn dark)" in line
    assert "tones 0=good 1=bad 3=watch" in line and "inverted" not in line and "Worth" not in line
    fixed = C.node_lines()
    assert "<CardGrid" in fixed and "highlight_text" in fixed and "{role}" not in fixed


def test_generator_and_context_hooks(monkeypatch):
    from src.agents import context_builder as CB
    plan = {"slide_type": "content", "components": [GRID, MATRIX]}
    kinds = [CB._recipe_kind(c) for c in plan["components"]]
    assert kinds == ["card_grid", "card_matrix"]
    drawn = C.card_components(plan)
    assert list(drawn) == ["bets"]


def test_title_only_cards_are_drawn_compact_and_centred():
    thin = _grid("plats", [{"title": "Zepto"}, {"title": "Swiggy Instamart"}, {"title": "Blinkit"}])
    root = etree.fromstring(run('<CardGrid ref="plats"/>', {"components": [thin]})["xml"].encode())
    group = next(e for e in root.iter("VStack") if e.get("id") == "cardg-plats")
    band = group.getparent()
    assert band.get("justifyContent") == "center" and band.get("grow") == "1" and group.get("grow") is None
    assert all(r.get("grow") is None for r in group.iter("HStack"))
    full = etree.fromstring(run('<CardGrid ref="bets"/>')["xml"].encode())
    group = next(e for e in full.iter("VStack") if e.get("id") == "cardg-bets")
    assert group.get("grow") == "1" and all(r.get("grow") == "1" for r in group.iter("HStack"))
