"""Tile / card looks from the plan's design_hint (docs/tile-variant-choice-spec-2026-10-26.md, option A),
POM_BLOCKS=tiles: plan_checks.look_from_hint per mapping row, the expand hooks (a bare group takes the hint's look,
the LLM's variant wins, unmet looks are left out quietly) and the src.api startup line."""

import copy
import logging
import re

import pytest

from src.agents.plan_checks import look_from_hint
from src.compiler.nodes import tiles as T


def kpi_row(hint, n=4, tones=True):
    labels = ["Spend", "Revenue", "Blended ROAS", "Orders"][:n]
    cd = {"kpi_labels": labels, "kpi_values": ["₹114.9L", "₹37.4L", "0.33x", "1,204"][:n]}
    if tones:
        cd["kpi_tones"] = ["", "good", "bad", "watch"][:n]
    return {"component_id": "kpis", "kind": "kpi_row", "count": n, "design_hint": hint, "content_data": cd}


def card_grid(hint, titles=("Close logos", "Fix onboarding", "Ship analytics"), layout="grid", cid="bets"):
    return {"component_id": cid, "kind": "card_grid", "count": len(titles), "design_hint": hint,
            "content_data": {"card_layout": layout, "cards": [{"title": t, "body": f"{t} body"} for t in titles]}}


def pick(comp):
    look = look_from_hint(comp)
    return look["group"], look["items"], look["emphasis"]


@pytest.fixture(autouse=True)
def tiles_mode(monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")


def run(*comps, body):
    plan = {"components": [{"component_id": "title", "kind": "title"}, *comps]}
    return T.fill(f'<Slide><VStack w="1280" h="720" padding="40">{body}</VStack></Slide>', plan)


def hint_codes(res):
    return [(i["ref"], i["severity"]) for i in res["issues"] if i["code"] == "NODE_LOOK_FROM_HINT"]


# ── look_from_hint: one test per mapping row (spec §4) ────────────────────────

def test_kpi_status_dot_is_a_group_dot():
    assert pick(kpi_row("show a small status dot beside each label")) == ("dot", {}, None)
    assert pick(kpi_row("add a status dot on the Orders tile")) == (None, {3: "dot"}, None)


def test_kpi_accent_border_is_a_bar_on_the_group_or_the_named_tile():
    assert pick(kpi_row("accent border on the card; icon in each tile")) == ("bar", {}, None)
    assert pick(kpi_row("accent border on the Blended ROAS tile")) == (None, {2: "bar"}, None)
    # names as tones_from_hint reads them: an upper-case token only one label has
    assert pick(kpi_row("coloured left bar on ROAS")) == (None, {2: "bar"}, None)


def test_kpi_dark_or_inverted_asks_for_the_emphasis_item():
    assert pick(kpi_row("dark / inverted panel on the Blended ROAS tile")) == (None, {}, "inverted")
    # hero / focus alone is not a dark tile (user 2026-10-26, Q1)
    assert pick(kpi_row("emphasize the Blended ROAS tile as the hero and the focus")) == (None, {}, None)


def test_kpi_tint_only_with_tones():
    assert pick(kpi_row("shade the Revenue and Orders tiles")) == (None, {1: "filled", 3: "filled"}, None)
    assert pick(kpi_row("shade the Revenue and Orders tiles", tones=False)) == (None, {}, None)


def test_kpi_lift_draws_nothing():   # KPI tiles stay flat (user 2026-10-13, 2026-10-26 Q2)
    assert pick(kpi_row("lift the tiles with a soft shadow")) == (None, {}, None)


def test_kpi_several_cues_rank_bar_dot_filled():
    assert pick(kpi_row("status dot and accent border on every tile")) == ("bar", {}, None)
    # an item keeps its own look only above the group's: dots everywhere, the shaded tiles take the dot's colour
    assert pick(kpi_row("Revenue shaded positive; show a status dot beside each label")) == ("dot", {}, None)
    assert pick(kpi_row("accent border on the Orders tile; status dot beside each KPI")) == ("dot", {3: "bar"}, None)


def test_plain_border_and_negations_are_not_cues():
    assert pick(kpi_row("a clear border and rounded corners")) == (None, {}, None)
    assert pick(kpi_row("no status dots; without an accent border")) == (None, {}, None)
    assert look_from_hint(kpi_row("")) == {"group": None, "items": {}, "emphasis": None, "cues": []}


def test_card_accent_border_is_a_group_accent_top():
    assert pick(card_grid("icon in each card; accent border on the cards")) == ("accent_top", {}, None)
    # one card named: not a group look (cards never mix lifted and flat); every card named is the group
    assert pick(card_grid("accent border on the 'Fix onboarding' card")) == (None, {}, None)
    assert pick(card_grid("accent border on the Close logos, Fix onboarding and Ship analytics cards"))[0] == "accent_top"


def test_card_numbered_only_on_a_grid():
    assert pick(card_grid("numbered cards, icon in each"))[0] == "numerals"
    assert pick(card_grid("steps layout with numbered tags", layout="steps"))[0] is None   # steps number themselves


def test_card_tint_and_dark_draw_nothing_new():   # lifted is tinted by tone; the focus card is already dark
    assert pick(card_grid("shade each card by its tone; dark panel on Fix onboarding")) == (None, {}, None)


# ── the expand hooks ──────────────────────────────────────────────────────────

def test_a_bare_kpi_grid_draws_the_hints_look_and_logs_it():
    res = run(kpi_row("accent border on the card"), body='<KpiGrid ref="kpis"/>')
    assert res["ok"], res["issues"]
    assert res["xml"].count('borderLeft.width="6"') == 4
    assert hint_codes(res) == [("kpis", "report")]


def test_item_looks_on_a_bare_grid():
    res = run(kpi_row("accent border on the Blended ROAS tile; status dot on the Orders tile"), body='<KpiGrid ref="kpis"/>')
    assert res["xml"].count('borderLeft.width="6"') == 1 and res["xml"].count('shapeType="ellipse"') == 1
    assert sorted(r for r, _ in hint_codes(res)) == ["kpis.2", "kpis.3"]


def test_the_llms_variant_wins():
    comp = kpi_row("accent border on the card")
    res = run(comp, body='<KpiGrid ref="kpis" variant="dot"/>')
    assert hint_codes(res) == [] and 'borderLeft.width="6"' not in res["xml"]
    # an item's own variant wins over the hint's item look
    res = run(kpi_row("status dot on the Orders tile"), body='<KpiGrid ref="kpis"><Kpi ref="kpis.3" variant="bar"/></KpiGrid>')
    assert hint_codes(res) == [] and 'shapeType="ellipse"' not in res["xml"] and 'borderLeft.width="6"' in res["xml"]


def test_dark_draws_the_emphasis_item_inverted():
    res = run(kpi_row("dark / inverted panel on the Blended ROAS tile"), body='<KpiGrid ref="kpis"/>')
    assert res["xml"].count('backgroundColor="$panelDark"') == 1 and hint_codes(res) == [("kpis.2", "report")]
    assert "NODE_VARIANT_UNMET" not in [i["code"] for i in res["issues"]]


def test_unmet_looks_fall_back_quietly():
    # a single tile stays plain (user 2026-10-26, Q3); two tiles are a pair, not a focus
    for n in (1, 2):
        res = run(kpi_row("dark / inverted panel on the Spend tile", n=n), body='<KpiGrid ref="kpis"/>')
        assert "$panelDark" not in res["xml"] and hint_codes(res) == []
        assert "NODE_VARIANT_UNMET" not in [i["code"] for i in res["issues"]]
    # numerals need titles without their own numbers
    comp = card_grid("numbered cards", titles=("Phase 1: Audit", "Phase 2: Build", "Phase 3: Scale"))
    res = run(comp, body='<CardGrid ref="bets"/>')
    assert hint_codes(res) == [] and "NODE_VARIANT_UNMET" not in [i["code"] for i in res["issues"]]


def test_a_bare_card_grid_draws_accent_top_and_keeps_the_focus_card():
    comp = card_grid("accent border on the cards")
    comp["content_data"]["focus_card"] = 1
    res = run(comp, body='<CardGrid ref="bets"/>')
    assert res["ok"], res["issues"]
    assert res["xml"].count('borderTop.width="4"') == 2 and res["xml"].count('backgroundColor="$panelDark"') == 1
    assert hint_codes(res) == [("bets", "report")]
    res = run(comp, body='<CardGrid ref="bets" variant="outline"/>')   # the LLM's variant wins
    assert hint_codes(res) == [] and 'borderTop.width="4"' not in res["xml"]


def test_the_hint_beats_the_second_groups_default():
    first, second = card_grid("icon in each card", cid="a"), card_grid("accent border on the cards", cid="b")
    res = run(first, second, body='<CardGrid ref="a"/><CardGrid ref="b"/>')
    assert res["xml"].count('borderTop.width="4"') == 3 and hint_codes(res) == [("b", "report")]


def test_numerals_from_the_hint():
    res = run(card_grid("numbered cards"), body='<CardGrid ref="bets"/>')
    assert re.findall(r">0([123])<", res["xml"]) == ["1", "2", "3"]


def test_the_plan_is_not_changed():
    comp = kpi_row("accent border on the Blended ROAS tile")
    before = copy.deepcopy(comp)
    run(comp, body='<KpiGrid ref="kpis"/>')
    assert comp == before


# ── src.api startup ───────────────────────────────────────────────────────────

def test_api_logs_the_blocks_mode_at_startup(caplog):
    from fastapi.testclient import TestClient

    import src.api as api
    with caplog.at_level(logging.INFO, logger="src.api"), TestClient(api.app):
        pass
    assert any("POM_BLOCKS=tiles" in r.getMessage() for r in caplog.records)
