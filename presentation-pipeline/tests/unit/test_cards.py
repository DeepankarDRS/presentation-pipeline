"""Card tile nodes (docs/tile-nodes-spec-2026-10-12.md §3, §11), POM_BLOCKS=tiles: a bare <CardGrid> draws the
plan's meaning (tones, focus card, key phrases), columns by text length, steps / rail, placement, NODE_* codes,
the LLM's wrapper boxes, the deferred matrix, the prompt lines and the generator / context hooks."""

import copy
import re

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
STEPS = _grid("plan", [{"title": t, "tag": g} for t, g in zip(["Audit", "Rebuild", "Automate", "Scale"],
                                                                  ["Kickoff", "Build", "Launch", "Grow"])],
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
    # the default `lifted`: a white card with a shadow, tinted (fill and border) by its tone (blind marks 2026-10-13)
    assert watch.get("backgroundColor") == "$warningSoft" and watch.get("border.color") == "$warning"
    assert good.get("backgroundColor") == "$positiveSoft" and good.get("shadow.type") == "outer"
    assert neutral.get("backgroundColor") == "$surface" and neutral.get("border.color") == "$border"
    assert neutral.find(".//Text").get("fontSize")   # tag line in the tone's ink: see test_tag_lines_take_the_tone
    col = run('<CardGrid ref="bets" variant="column"/>')["xml"]
    assert card_el(col, "bets", 3).get("borderLeft.color") == "$warning" and card_el(col, "bets", 3).get("backgroundColor") is None
    filled = run('<CardGrid ref="bets" variant="filled"/>')["xml"]
    assert card_el(filled, "bets", 3).get("backgroundColor") == "$warningSoft"    # filled: watch tone -> toned
    span = good.find(".//Span")   # good card is tinted $positiveSoft already: the ink alone, no highlighter
    assert span is not None and span.text == "$4M+" and span.get("color") == "$positiveText" and good.find(".//Mark") is None
    plain = card_el(run('<CardGrid ref="bets" variant="filled"/>')["xml"], "bets", 0)   # coloured span, no highlighter
    assert plain.find(".//Mark") is None and plain.find(".//Span").get("color") == "$positiveText"
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
    assert "01 · KICKOFF" in text_of(card_el(xml, "plan", 0))
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
    assert dropped["ok"] and codes(dropped).count("NODE_ATTR_DROPPED") == 2
    assert 'borderRadius="12"' not in dropped["xml"] and 'borderRadius="8"' in dropped["xml"]   # code's 8 px, not the LLM's
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
    dark = run('<VStack backgroundColor="$panelDark" padding="20"><CardGrid ref="bets" variant="column"/></VStack>')["xml"]
    assert all(t.get("color") == "$onPanelDark" for t in card_el(dark, "bets", 2).iter("Text"))   # open card on a dark panel


def test_matrix_is_deferred_and_old_plans_without_fields_still_draw():
    assert "mx" not in C.card_components(PLAN)
    assert "NODE_REF_UNKNOWN" in codes(run('<CardGrid ref="mx"/>'))
    old = copy.deepcopy(GRID)
    for c in old["content_data"]["cards"]:
        c.pop("tone", None), c.pop("key_phrase", None)
    old["content_data"].pop("focus_card")
    xml = run('<CardGrid ref="bets"/>', {"components": [old]})["xml"]
    assert all(card_el(xml, "bets", i).get("backgroundColor") == "$surface" for i in range(4))
    old["design_hint"] = "inverted panel on the Hire leads card"
    assert card_el(run('<CardGrid ref="bets"/>', {"components": [old]})["xml"], "bets", 3).get("backgroundColor") == "$panelDark"


def test_prompt_lines():
    line = C.prompt_line(GRID)
    assert "CARDS bets: 4 cards (0-3), grid" in line and "focus 1 (drawn dark)" in line
    assert "tones 0=good 1=bad 3=watch" in line and "inverted" not in line and "Worth" not in line
    assert "never type a title, tag or body yourself" in line
    fixed = C.node_lines()
    assert "<CardGrid" in fixed and "highlight_text" in fixed and "{role}" not in fixed


def test_generator_and_context_hooks(monkeypatch):
    from src.agents.generation import context_builder as CB
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


def test_tag_lines_take_the_tone():
    plan = {"components": [_grid("t", [{"title": "A", "tag": "Q3", "tone": "bad"}, {"title": "B", "tag": "Q4"}])]}
    xml = run('<CardGrid ref="t"/>', plan)["xml"]
    tags = {text_of(t): t.get("color") for t in etree.fromstring(xml.encode()).iter("Text") if text_of(t) in ("Q3", "Q4")}
    assert tags == {"Q3": "$negativeText", "Q4": "$accentText"}


def test_the_plans_icons_are_drawn_unless_the_llm_names_its_own():
    plan = {"components": [_grid("i", [{"title": "A", "icon": "rocket"}, {"title": "B", "icon": "users"}])]}
    names = lambda xml: [e.get("name") for e in etree.fromstring(xml.encode()).iter("Icon")]
    assert names(run('<CardGrid ref="i"/>', plan)["xml"]) == ["rocket", "users"]
    assert names(run('<CardGrid ref="i" icon="star"/>', plan)["xml"]) == ["star", "star"]


def test_an_icon_leads_the_tag_line_or_sits_above_the_title():
    tagged = {"components": [_grid("t", [{"title": "Close logos", "tag": "Q3", "icon": "rocket"},
                                         {"title": "Hire", "tag": "Q4", "icon": "users"}])]}
    el = card_el(run('<CardGrid ref="t"/>', tagged)["xml"], "t", 0)
    row = el.find("HStack")
    assert row is not None and [c.tag for c in row] == ["Icon", "Text"] and text_of(row) == "Q3"
    plain = {"components": [_grid("p", [{"title": "Subscriptions", "icon": "users"}, {"title": "Bundles", "icon": "package"}])]}
    el = card_el(run('<CardGrid ref="p"/>', plain)["xml"], "p", 0)
    assert el[0].tag == "Icon" and el.find("HStack") is None   # beside a title it held the title to its longest word


def test_steps_whose_tags_order_them_get_no_numbers():
    dated = {"components": [_grid("y", [{"title": t, "tag": str(2021 + k)} for k, t in enumerate("ABCD")], layout="steps")]}
    xml = run('<CardGrid ref="y"/>', dated)["xml"]
    assert "01 · " not in xml and ">2021<" in xml
    assert "01 · KICKOFF" in run('<CardGrid ref="plan"/>')["xml"]   # tags without an order of their own: numbered


def test_a_second_card_group_is_drawn_as_another_type():
    xml = run('<CardGrid ref="bets"/><CardGrid ref="plan"/>')["xml"]
    assert card_el(xml, "bets", 2).get("backgroundColor") == "$surface"        # first group: lifted
    second = card_el(xml, "plan", 0)                                           # second group: open column
    assert second.get("backgroundColor") is None and second.get("borderLeft.width") == "3"
    asked = run('<CardGrid ref="bets"/><CardGrid ref="plan" variant="outline"/>')["xml"]
    assert card_el(asked, "plan", 0).get("border.color") == "$border" and card_el(asked, "plan", 0).get("backgroundColor") is None


def test_dense_cards_put_their_icon_on_the_left():
    long_ = {"components": [_grid("d", [{"title": "Search share is falling", "icon": "search",
                                          "body": "Organic search share dropped on every platform this quarter while paid held"},
                                         {"title": "Retention is the strength", "icon": "users",
                                          "body": "Repeat buyers are 41% of revenue and their basket grew this quarter"}])]}
    el = card_el(run('<CardGrid ref="d"/>', long_)["xml"], "d", 0)
    row = el.find("HStack")
    assert row is not None and row[0].tag == "Icon" and row[1].tag == "VStack"   # icon left of the whole text column


def test_a_steps_row_gives_a_long_step_a_wider_card_and_even_steps_equal_ones():
    # card paid 2026-10-14: one long step beside two short ones held the group's one size, the short cards half empty
    long = _grid("plan", [{"title": "Days 0-7", "body": "Pause zero-sales terms; reduce bids on weak ROAS; protect brand "
                           "and exact winners; cap SD, AMC and weak competitor campaigns; identify low-ROAS cities"},
                          {"title": "Days 8-30", "body": "Restructure by intent"},
                          {"title": "Days 31-90", "body": "Scale proven clusters"}], layout="steps")
    xml = run('<CardGrid ref="plan"/>', {"components": [long]})["xml"]
    grows = [float(g) for g in re.findall(r'<VStack id="card-plan-\d"[^>]*\sgrow="([\d.]+)"', xml)]
    assert len(grows) == 3 and grows[0] > grows[1] and grows[1] == grows[2], grows
    even = run('<CardGrid ref="plan"/>')["xml"]
    assert set(re.findall(r'<VStack id="card-plan-\d"[^>]*\sgrow="([\d.]+)"', even)) == {"1"}


def test_a_step_body_of_several_points_draws_one_point_per_line():
    # user, card paid pair 3.1 (2026-10-14): "I need points or a new line between the points"
    steps = _grid("plan", [{"title": "Days 8-30", "body": "Restructure by intent. Move terms into exact. Add negatives."},
                           {"title": "Days 31-90", "body": "Scale proven clusters at 0.25x. or better"},
                           {"title": "Later", "body": "Audit; benchmark; prioritise"}], layout="steps")
    xml = run('<CardGrid ref="plan"/>', {"components": [steps]})["xml"]
    root = etree.fromstring(f"<r>{xml}</r>")
    lis = [["".join(li.itertext()) for li in c.iter("Li")] for c in root.iter("VStack") if (c.get("id") or "").startswith("card-plan-")]
    assert lis == [["Restructure by intent.", "Move terms into exact.", "Add negatives."], [], ["Audit", "benchmark", "prioritise"]]
    assert "Scale proven clusters at 0.25x. or better" in xml
    grid = _grid("g", [{"title": "A", "body": "One. Two."}, {"title": "B", "body": "Three"}])
    assert "<Li" not in run('<CardGrid ref="g"/>', {"components": [grid]})["xml"]   # grids keep their body line
