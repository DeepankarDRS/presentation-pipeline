"""The attribute layer of the composition nodes (docs/syntax-audit-2026-11-04.md §4, F1-F5): an allowed attribute never
blanks a slide, never vanishes without a report, and never reaches a tag POM rejects."""

import pytest
from lxml import etree

from src.compiler.nodes import composed, element_refs, spec, tiles, validate

KPIS = {"component_id": "kpis", "kind": "kpi_row", "content_data": {
    "kpi_labels": ["ARR", "Churn", "NPS", "CAC"], "kpi_values": ["₹31.2L", "2.8%", "41", "₹900"],
    "kpi_deltas": ["up 12%", "down 1pt", "up 3", "flat"]}}
CARDS = {"component_id": "levers", "kind": "card_grid", "content_data": {"cards": [
    {"title": f"Lever {i}", "tag": f"TAG{i}", "body": f"Body {i}", "bullets": [f"Point {i}"]} for i in "ABCD"]}}
CHART = {"component_id": "roas", "kind": "chart", "content_data": {
    "chart_type": "bar", "chart_title": "ROAS", "chart_labels": ["A", "B", "C"], "chart_values": [1, 2, 3]}}
TIMELINE = {"component_id": "road", "kind": "timeline", "content_data": {"timeline_items": [
    {"date": "Q1", "label": "Plan"}, {"date": "Q2", "label": "Build"}, {"date": "Q3", "label": "Ship"}]}}
TABLE = {"component_id": "gaps", "kind": "table", "content_data": {
    "table_columns": ["Area", "Now", "Target"], "table_rows": [["Reach", "10", "20"], ["Spend", "30", "40"]]}}


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "kpi_row,card_grid,chart,timeline,table")
    monkeypatch.setenv("POM_BLOCKS", "tiles")


def run(xml, *comps):
    plan = {"components": list(comps), "slide_title": "H"}
    drawn = composed.expand(xml, plan)
    filled = tiles.fill(drawn["xml"], plan)
    return {"xml": filled["xml"], "issues": drawn["issues"] + filled["issues"], "ok": drawn["ok"] and filled["ok"],
            "components": drawn["components"]}


def codes(r):
    return {i["code"] for i in r["issues"]}


# ── F1: one value per attribute ───────────────────────────────────────────────

def test_one_value_keeps_the_last():
    assert validate.one_value('<VStack gap="8" w="1" gap="40"/>') == '<VStack gap="40" w="1"/>'


def test_one_value_leaves_clean_tags_and_comments_alone():
    xml = '<!-- chart-post {"ink": "$a"} --><VStack gap="8"><Text a="1 &gt; 2">x</Text></VStack>'
    assert validate.one_value(xml) == xml


def test_the_blank_kpi_strip_is_filled():
    r = run('<KpiRow ref="kpis" variant="strip" alignItems="center"/>', KPIS)
    assert r["ok"] and "₹900" in r["xml"] and "Churn" in r["xml"]
    etree.fromstring(f"<r>{r['xml']}</r>".encode())


def test_a_gap_on_a_table_does_not_blank_the_kpi_row_beside_it():
    r = run('<KpiRow ref="kpis"/><Table ref="gaps" variant="rows" gap="20"/>', KPIS, TABLE)
    assert r["ok"] and "₹900" in r["xml"] and "Churn" in r["xml"]
    assert 'gap="20"' in r["xml"]   # the LLM's value, not the expander's literal


def test_the_llms_own_repeated_attribute_does_not_blank_its_tiles():
    r = run('<HStack gap="8" gap="4"><KpiRow ref="kpis"/></HStack>', KPIS)
    assert r["ok"] and "₹900" in r["xml"] and 'gap="4"' in r["xml"]


@pytest.mark.parametrize("kind,comp", [("kpi_row", KPIS), ("card_grid", CARDS), ("chart", CHART), ("timeline", TIMELINE),
                                       ("table", TABLE)])
def test_every_attribute_on_every_composition_stays_well_formed(kind, comp):
    nd = spec.nodes()[kind]
    box = [a for a in tiles.data()["box_attributes"] if a not in ("border", "grow")]
    for variant in nd["compositions"]:
        tag = f'<{nd["tag"]} ref="{comp["component_id"]}" variant="{variant}"' + "".join(f' {a}="1"' for a in box) + " />"
        etree.fromstring(f"<r>{composed.expand(tag, {'components': [comp]})['xml']}</r>".encode())


# ── F2: nothing vanishes silently, nothing reaches a tag POM rejects ──────────

def no_effect(r):
    return [i["message"] for i in r["issues"] if i["code"] == "NODE_ATTR_NO_EFFECT"]


def test_a_part_the_composition_does_not_draw_is_reported():
    r = run('<CardGrid ref="levers" variant="grid" bullets.backgroundColor="$surfaceAlt"/>', CARDS)
    assert r["ok"] and "bullets.backgroundColor" in no_effect(r)[0]
    assert "$surfaceAlt" not in r["xml"].split("bullets")[0] or no_effect(r)


def test_a_part_the_composition_draws_is_kept():
    r = run('<CardGrid ref="levers" variant="columns" bullets.backgroundColor="$negativeSoft"/>', CARDS)
    assert not no_effect(r) and "$negativeSoft" in r["xml"]


@pytest.mark.parametrize("tag,comp,gone", [
    ('<Chart ref="roas" variant="rows" showLegend="true"/>', CHART, "showLegend"),
    ('<Table ref="gaps" variant="rows" cellBorder.color="$border"/>', TABLE, "cellBorder"),
    ('<Table ref="gaps" variant="ledger" stripe.color="$accent"/>', TABLE, 'color="$accent"'),
    ('<Table ref="gaps" variant="native" gap="20"/>', TABLE, 'gap="20"'),
    ('<Timeline ref="road" variant="native" gap="20"/>', TIMELINE, 'gap="20"'),
])
def test_what_pom_rejects_on_that_tag_never_reaches_it(tag, comp, gone):
    r = run(tag, comp)
    assert no_effect(r) and gone not in r["xml"]


def test_a_chart_bar_colour_is_not_called_a_no_op():
    """bar.fill.color reaches chartColors as JSON: the audit's first measure missed it."""
    r = run('<Chart ref="roas" variant="native" bar.fill.color="$negative"/>', CHART)
    assert not no_effect(r) and "$negative" in r["xml"]


def test_a_marker_with_its_shape_is_not_called_a_no_op():
    r = run('<KpiRow ref="kpis" variant="grid" marker.shapeType="rect" marker.fill.color="$negative"/>', KPIS)
    assert not no_effect(r) and "$negative" in r["xml"]


def test_an_item_tag_is_filtered_too():
    r = run('<CardGrid ref="levers" variant="grid"><Card ref="levers.1" band.backgroundColor="$accent"/></CardGrid>', CARDS)
    assert any("band.backgroundColor" in m and "<Card" in m for m in no_effect(r))


def test_an_item_placed_apart_keeps_its_own_size():
    r = run('<KpiRow ref="kpis" variant="grid"/><Kpi ref="kpis.0" grow="1" w="30%"/>', KPIS)
    assert not no_effect(r) and 'w="30%"' in r["xml"]


def test_no_effect_is_a_report_not_a_repair():
    assert run('<KpiRow ref="kpis" variant="grid" band.padding="4"/>', KPIS)["ok"]


def test_every_ignore_names_a_real_attribute():
    d = tiles.data()
    box = set(d["box_attributes"]) | {"borderRadius"}
    for kind, nd in spec.nodes().items():
        for name, c in nd["compositions"].items():
            for k in c.get("ignores") or []:
                head, _, _ = k.partition(".")
                assert head in nd["parts"] or k in box or k in (nd.get("native_attributes") or []), (kind, name, k)
            for p in c.get("draws_only") or {}:
                assert p in nd["parts"], (kind, name, p)


# ── F3: XML that cannot be parsed is an error, not a blank slide ──────────────

def test_broken_xml_with_kpis_on_the_slide_is_an_error():
    r = element_refs.fill_refs('<VStack><Text ref="kpis.0.value"/></HStack>', {"components": [KPIS]})
    assert not r["ok"] and [i["code"] for i in r["issues"]] == ["NODE_XML_INVALID"]


def test_broken_xml_with_nothing_to_fill_stays_the_normalizers():
    r = element_refs.fill_refs('<VStack ref="x"><Text>a</HStack>', {"components": []})
    assert r["ok"] and not r["issues"]


# ── F4: $tone on a node with no item tones ────────────────────────────────────

def test_tone_on_a_chart_is_the_accent():
    r = run('<Chart ref="roas" variant="rows" bar.fill.color="$toneSoft" title.color="$toneText"/>', CHART)
    assert "$tone" not in r["xml"] and "$accentSoft" in r["xml"] and "$accentText" in r["xml"]
    assert "NODE_ATTR_ALIAS" in codes(r)


def test_tone_on_a_timeline_is_the_accent():
    r = run('<Timeline ref="road" variant="rail" marker.fill.color="$tone"/>', TIMELINE)
    assert "$tone" not in r["xml"] and "$accent" in r["xml"] and r["ok"]


def test_tone_on_kpis_still_follows_the_item():
    comp = dict(KPIS, content_data=dict(KPIS["content_data"], kpi_tones=["good", "bad", "", ""]))
    r = run('<KpiRow ref="kpis" variant="rows" value.color="$toneText"/>', comp)
    assert "$positiveText" in r["xml"] and "$negativeText" in r["xml"]


# ── F5: highlight ─────────────────────────────────────────────────────────────

def test_highlight_is_no_longer_offered_and_dropped_with_a_report():
    assert "highlight" not in tiles.data()["part_nodes"]["Text"]
    r = run('<KpiRow ref="kpis" variant="grid" delta.highlight="$accentSoft"/>', KPIS)
    assert r["ok"] and "NODE_ATTR_DROPPED" in codes(r) and "highlight" not in r["xml"]
