"""Table composition node (composition spec §8, C1 / C2), POM_NODES=table: every composition word, aliases,
requires / fallback, the emphasis row / column from the hint and its tone, look parts written onto the <Td>s,
`item.` on native, peer ids, and the composed hooks (LLM-free)."""

import re

import pytest

from src.compiler.nodes import composed, spec
from src.compiler.nodes import tables as TB

GAPS = {"component_id": "gaps", "kind": "table",
        "design_hint": "side-by-side comparison; accent the Fix column in a positive colour as the recommended fixes",
        "content_data": {"table_columns": ["Gap", "Marketplace A", "Marketplace B", "Fix"], "table_rows": [
            ["CPC above allowable", "CPC 31.1 vs 10.7", "CPC 46.2 vs 14.8", "Break-even CPC bidding"],
            ["Discovery leakage", "Auto and broad weak", "Phrase weak", "Weekly negative-keyword loop"],
            ["Budget not following winners", "Exact under-scaled", "Category under-funded", "Budget tiers"],
            ["Visibility spend mixed in", "Display weak", "Banner weak", "Separate visibility budget"]]}}
MATCH = {"component_id": "match", "kind": "table",
         "design_hint": "shade the Exact Match row and emphasize the ROAS column; mute the Broad Match row",
         "content_data": {"table_columns": ["Match Type", "Spend", "ROAS"], "table_rows": [
             ["Exact Match", "₹1.2L", "0.41x"], ["Phrase Match", "₹2.0L", "0.22x"], ["Broad Match", "₹3.1L", "0.15x"]]}}
TALL = {"component_id": "tall", "kind": "table", "content_data": {
    "table_columns": ["Month", "Target"], "table_rows": [[f"M{i}", str(i)] for i in range(7)]}}
OWN = {"component_id": "own", "kind": "table", "content_data": {
    "table_columns": ["Move", "Owner"], "table_rows": [["01. Format rebalance", "A"], ["02. City shift", "B"]]}}


def plan(*comps):
    return {"slide_title": "Gaps", "components": [{"component_id": "title", "kind": "title", "count": 1},
                                                  *(dict(c, count=1) for c in comps)]}


def run(tag, *comps):
    return TB.expand(f'<Slide><VStack w="1280" h="720">{tag}</VStack></Slide>', plan(*comps))


def codes(res):
    return [i["code"] for i in res["issues"]]


def used(res, cid):
    return res["components"][cid]["composition"]


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "table")


# ── emphasis from the hint ────────────────────────────────────────────────────

@pytest.mark.parametrize("hint,want", [
    ("shade the Exact Match row and emphasize the ROAS column", ("row", 0)),
    ("emphasise Phrase Match ROAS 0.22x", ("row", 1)),
    ("shade the 'ROAS' column", ("col", 2)),
    ("shade the Exact Match and Broad Match rows", None),          # two rows: none
    ("bold the Spend and ROAS columns", None),                     # two columns: none
    ("accent border on the card", None),
    ("", None),
])
def test_emphasis(hint, want):
    assert TB.emphasis(dict(MATCH, design_hint=hint)) == want


def test_emphasis_on_the_sample():
    assert TB.emphasis(GAPS) == ("col", 3)
    assert TB.emphasis(MATCH) == ("col", 2)        # two rows named (Exact, Broad): the one column instead


def test_tone_from_hint():
    assert TB.role(GAPS, TB.emphasis(GAPS)) == "positive"
    assert TB.role(MATCH, TB.emphasis(MATCH)) == "accent"
    neg = dict(MATCH, design_hint="color the Broad Match row negative (red)")
    assert TB.role(neg, TB.emphasis(neg)) == "negative"
    assert TB.role(MATCH, None) == "accent"


def test_tone_tokens():
    out = TB._toned({"p": {"a": "$tone", "b": "$toneSoft", "c": "$toneText", "d": "$textMain"}}, "positive")
    assert out["p"] == {"a": "$positive", "b": "$positiveSoft", "c": "$positiveText", "d": "$textMain"}
    assert TB._toned({"p": {"b": "$toneSoft", "c": "$toneText"}}, "neutral")["p"] == {"b": "$surfaceAlt", "c": "$textMain"}


# ── compositions ──────────────────────────────────────────────────────────────

def test_bare_tag_is_native_with_parts_on_cells():
    r = run('<Table ref="gaps"/>', GAPS)
    assert used(r, "gaps") == "native" and r["ok"]
    x = r["xml"]
    assert 'id="tbl-gaps"' in x and 'cellBorder.color="$border"' in x and "<Tr " not in x.replace("<Tr>", "")
    assert '<Td backgroundColor="$positive" color="$onAccent" bold="true">Fix</Td>' in x
    assert "fontSize" not in x and 'grow="1"' not in x          # fit-grow sizes a native table from its text
    assert x.count('backgroundColor="$positiveSoft"') == 4                     # the Fix column's body cells
    assert x.count('backgroundColor="$surfaceAlt"') == 3                       # the other header cells
    assert "$tone" not in x


def test_row_emphasis_on_native():
    x = run('<Table ref="match"/>', dict(MATCH, design_hint="shade the Exact Match row"))["xml"]
    row0 = re.search(r"<Tr>(<Td[^>]*>Exact Match.*?)</Tr>", x).group(1)
    assert row0.count('backgroundColor="$accentSoft"') == 3 and "$accentText" in row0


def test_stripe_and_item_on_native():
    r = run('<Table ref="match" stripe.backgroundColor="$surfaceAlt" item.backgroundColor="$surface" item.padding="4"/>',
            dict(MATCH, design_hint=""))
    rows = re.findall(r"<Tr>(.*?)</Tr>", r["xml"])
    assert rows[1].count('backgroundColor="$surface"') == 3                  # body row 0: item. on every cell
    assert rows[2].count('backgroundColor="$surfaceAlt"') == 3               # body row 1: the stripe over it
    assert "NODE_ATTR_DROPPED" in codes(r)                                    # item.padding on native (C1)


@pytest.mark.parametrize("alias,word,needle", [
    ("plain", "native", None), ("highlight_row", "native", None),
    ("zebra", "native", 'backgroundColor="$surfaceAlt"'), ("dark_header", "native", 'backgroundColor="$panelDark"'),
])
def test_aliases(alias, word, needle):
    r = run(f'<Table ref="match" variant="{alias}"/>', dict(MATCH, design_hint=""))
    assert used(r, "match") == word and "NODE_ATTR_ALIAS" in codes(r)
    if needle:
        assert needle in r["xml"]


def test_alias_parts_under_the_llms():
    x = run('<Table ref="match" variant="dark_header" header.backgroundColor="$accent"/>', dict(MATCH, design_hint=""))["xml"]
    assert "$panelDark" not in x and 'backgroundColor="$accent"' in x


def test_unknown_variant_is_native():
    r = run('<Table ref="match" variant="minimal"/>', MATCH)
    assert used(r, "match") == "native" and "NODE_VARIANT_UNKNOWN" in codes(r)


def test_rows_and_numbered():
    r = run('<Table ref="gaps" variant="rows numbered"/>', GAPS)
    x = r["xml"]
    assert used(r, "gaps") == "rows numbered"
    assert all(f">0{i}</Text>" in x for i in range(1, 5)) and 'id="card-gaps-3"' in x
    assert "MARKETPLACE A" in x and x.count('color="$positiveText"') >= 5     # Fix label + its 4 cells
    assert 'id="card-gapsx-' in x                                             # inner peer ids (C11)
    assert "borderTop" not in re.search(r'id="card-gaps-0"[^>]*>', x).group(0)
    assert ">01</Text>" not in run('<Table ref="gaps" variant="rows"/>', GAPS)["xml"]


def test_numbered_needs_no_own_numbers():
    r = run('<Table ref="own" variant="rows numbered"/>', OWN)
    assert used(r, "own") == "rows" and "NODE_VARIANT_UNMET" in codes(r)


@pytest.mark.parametrize("word", ["columns", "banded"])
def test_box_words(word):
    r = run(f'<Table ref="gaps" variant="{word}"/>', GAPS)
    assert used(r, "gaps") == word and all(f'id="card-gaps-{i}"' in r["xml"] for i in range(4))
    assert all(c in r["xml"] for row in GAPS["content_data"]["table_rows"] for c in row)


@pytest.mark.parametrize("word", ["columns", "banded"])
def test_box_words_fall_back_on_tall_tables(word):
    r = run(f'<Table ref="tall" variant="{word}"/>', TALL)
    assert used(r, "tall") == "native" and "NODE_VARIANT_UNMET" in codes(r)


def test_columns_needs_six_columns_or_fewer():
    wide = {"component_id": "wide", "kind": "table", "content_data": {
        "table_columns": list("ABCDEFG"), "table_rows": [list("1234567")]}}
    assert not spec.check("columns_le_6", wide) and spec.check("count_le_5", wide)
    assert used(run('<Table ref="wide" variant="columns"/>', wide), "wide") == "native"


@pytest.mark.parametrize("n,k", [(1, 1), (2, 2), (3, 3), (4, 2), (5, 3), (6, 3)])
def test_banded_per_line(n, k):
    assert TB.per_line(n) == k


def test_errors_and_literal_colours():
    r = run('<Table ref="nope"/>', GAPS)
    assert "NODE_REF_UNKNOWN" in codes(r) and not r["ok"]
    empty = {"component_id": "e", "kind": "table", "content_data": {"table_columns": ["A"], "table_rows": []}}
    assert "NODE_ITEM_MISSING" in codes(run('<Table ref="e"/>', empty))
    r = run('<Table ref="gaps" header.color="#FF0000"/>', GAPS)
    assert "LITERAL_COLOR" in codes(r) and "#FF0000" not in r["xml"]
    assert "NODE_ATTR_UNKNOWN" in codes(run('<Table ref="gaps" header.fontSize2="9"/>', GAPS))


def test_a_table_without_ref_is_the_llms():
    xml = '<Slide><Table><Tr><Td>x</Td></Tr></Table></Slide>'
    assert TB.expand(xml, plan(GAPS))["xml"] == xml


# ── hooks ─────────────────────────────────────────────────────────────────────

def test_composed_registry():
    p = plan(GAPS)
    assert "table" in composed.kinds_on() and composed.tag("table") == "Table"
    assert composed.all_drawn(p, "table") and composed.expand('<Table ref="gaps"/>', p)["components"]["gaps"]
    line = composed.prompt_line(dict(GAPS, count=1))
    assert "4 rows x 4 columns" in line and "code colours column 'Fix'" in line and "columns | banded" in line
    assert "TABLES" in composed.node_lines() and "zebra" in composed.node_lines()
    assert "stripe.*" in composed.tag_attributes("table")


def test_off_without_pom_nodes(monkeypatch):
    monkeypatch.setenv("POM_NODES", "chart")
    assert "table" not in composed.kinds_on() and composed.drawn(plan(GAPS), "table") == {}


# ── table as cards: grid / grid numbered / ledger (user, 2026-11-01) ─────────

def test_grid_keeps_rows_columns_and_every_heading():
    r = run('<Table ref="gaps" variant="grid"/>', GAPS)
    x = r["xml"]
    assert used(r, "gaps") == "grid" and r["ok"]
    assert all(f">{h}</Text>" in x for h in GAPS["content_data"]["table_columns"])          # Gap included
    assert all(c in x for row in GAPS["content_data"]["table_rows"] for c in row)
    assert all(f'id="card-gaps.tl-{i}"' in x for i in range(4)) and x.count('id="card-gaps.tc-') == 12
    assert x.count('id="card-gaps.th-') == 4                                                 # three peer groups
    assert x.count('border.color="$positive"') == 4                                          # the Fix column's cards
    assert 'backgroundColor="$positive"' in x and "$tone" not in x                           # its header pill


def test_grid_labels_inside():
    x = run('<Table ref="gaps" variant="grid" labels="inside"/>', GAPS)["xml"]
    assert x.count(">GAP</Text>") == 4 and x.count(">MARKETPLACE A</Text>") == 4             # a name in every card
    assert x.count(">FIX</Text>") == 4 and 'color="$positiveText"' in x
    assert '<HStack padding="10" borderRadius="6"' not in x                                  # no header pills


def test_grid_numbered_and_its_fallbacks():
    r = run('<Table ref="gaps" variant="grid numbered"/>', GAPS)
    assert used(r, "gaps") == "grid numbered" and all(f">0{i}</Text>" in r["xml"] for i in range(1, 5))
    r = run('<Table ref="own" variant="grid numbered"/>', OWN)
    assert used(r, "own") == "grid" and "NODE_VARIANT_UNMET" in codes(r)
    r = run('<Table ref="tall" variant="grid"/>', TALL)
    assert used(r, "tall") == "native" and "NODE_VARIANT_UNMET" in codes(r)


def test_ledger_icons_and_stripes():
    r = run('<Table ref="gaps" variant="ledger" icons="alert-triangle,store,shopping-cart,wrench"/>', GAPS)
    x = r["xml"]
    assert used(r, "gaps") == "ledger" and x.count("<Icon ") == 4 and 'name="wrench"' in x
    rows = re.findall(r'<HStack grow="1" gap="0" alignItems="stretch">(.*?)</HStack>', x)
    assert "$surfaceAlt" not in rows[0] and "$surfaceAlt" in rows[1]                          # alternate rows tinted
    assert "<Icon " not in run('<Table ref="gaps" variant="ledger"/>', GAPS)["xml"]           # no icons asked: names only


@pytest.mark.parametrize("style", ["label_cards", "accent_edge", "lifted"])
def test_grid_recipes_are_valid_attributes(style):
    r = run(f'<Table ref="gaps" variant="grid" {TB.node()["styles"][style]}/>', GAPS)
    assert used(r, "gaps") == "grid" and not [c for c in codes(r) if c in ("NODE_ATTR_UNKNOWN", "LITERAL_COLOR")]


# ── highlights (user, 2026-11-02: fill = the cell's background, color = its text, phrases in <Span color>) ─────────

ROAS = {"component_id": "roas", "kind": "table", "design_hint": "flag the Flipkart row as the worst performer",
        "content_data": {"table_columns": ["Platform", "Spend", "ROAS", "Target", "Note"], "table_rows": [
            ["Amazon", "₹31.2L", "2.8x", "2.0x", "Above target; scale exact match"],
            ["Flipkart", "₹42.0L", "0.34x", "2.0x", "Below target, spend still rising"],
            ["Myntra", "₹12.6L", "1.9x", "2.0x", "Near target; watch CPC creep"],
            ["Nykaa", "₹9.8L", "3.4x", "2.0x", "Best return at the lowest spend"]]}}


def hl(*marks, variant="native"):
    v = f' variant="{variant}"' if variant else ""
    return run(f'<Table ref="roas"{v}>{"".join(marks)}</Table>', ROAS)


def tds(x):
    """native body cells as (attributes, inner XML), row by row."""
    rows = re.findall(r"<Tr>(.*?)</Tr>", x)[1:]
    return [re.findall(r"<Td([^>]*)>(.*?)</Td>", r) for r in rows]


def test_highlight_row_fill_only_tints_the_row():
    res = hl('<Highlight row="Flipkart" fill="bad"/>')
    assert not codes(res)
    cells = tds(res["xml"])
    assert all('backgroundColor="$negativeSoft"' in a for a, _ in cells[1])
    assert not any("negative" in a for r in (0, 2, 3) for a, _ in cells[r])
    assert not any('color="$negativeText"' in a for a, _ in cells[1])     # fill and text colour are separate


def test_highlight_replaces_the_hint_emphasis():
    res = hl('<Highlight cell="Nykaa / ROAS" color="good"/>')
    assert res["components"]["roas"]["focus"] is None and res["components"]["roas"]["highlights"]
    a, inner = tds(res["xml"])[3][2]
    assert 'color="$positiveText"' in a and "backgroundColor" not in a and inner == "3.4x"


def test_bare_tag_keeps_the_hint_emphasis():
    assert run('<Table ref="roas" />', ROAS)["components"]["roas"]["focus"] == ("row", 1)


def test_highlight_rule_against_another_column():
    cells = tds(hl('<Highlight column="ROAS" below="Target" color="bad" else="good"/>')["xml"])
    got = ["negative" if "negativeText" in r[2][0] else "positive" if "positiveText" in r[2][0] else "" for r in cells]
    assert got == ["positive", "negative", "negative", "positive"]


def test_highlight_rule_against_a_number():
    cells = tds(hl('<Highlight column="ROAS" above="3" color="good"/>')["xml"])
    assert ["positiveText" in r[2][0] for r in cells] == [False, False, False, True]


def test_highlight_max_min():
    cells = tds(hl('<Highlight column="Spend" max="bad" min="good"/>')["xml"])
    assert 'negativeText' in cells[1][1][0] and 'positiveText' in cells[3][1][0]
    assert not any("Text" in cells[r][1][0] for r in (0, 2))


def test_highlight_phrase_is_a_span_color_never_a_mark():
    x = hl('<Highlight phrase="spend still rising" color="bad"/>')["xml"]
    _, inner = tds(x)[1][4]
    assert inner == 'Below target, <Span color="$negativeText">spend still rising</Span>'
    assert "<Mark" not in x


def test_highlight_fill_and_phrase_in_one_cell():
    x = hl('<Highlight row="Flipkart" fill="bad"/>', '<Highlight phrase="Below target" color="watch"/>')["xml"]
    a, inner = tds(x)[1][4]
    assert 'backgroundColor="$negativeSoft"' in a and '<Span color="$warningText">Below target</Span>' in inner


@pytest.mark.parametrize("mark", [
    '<Highlight row="Zomato" fill="bad"/>',                        # no such row
    '<Highlight column="CPC" color="bad"/>',                       # no such column
    '<Highlight cell="Nykaa - ROAS" color="good"/>',               # not "<row> / <column>"
    '<Highlight phrase="not in the table" color="bad"/>',
    '<Highlight row="Flipkart" fill="red"/>',                      # not a tone
    '<Highlight row="Flipkart"/>',                                 # no fill / color
    '<Highlight row="Flipkart" fill="bad" tone="bad"/>',           # unknown attribute
    '<Highlight column="ROAS" below="Budget" color="bad"/>',       # neither a number nor a column
])
def test_highlight_errors_go_back_to_the_llm(mark):
    res = hl(mark)
    assert "NODE_HIGHLIGHT_UNKNOWN" in codes(res) and not res["ok"]


def test_highlight_names_ignore_case_and_spaces():
    assert not codes(hl('<Highlight row="  flipkart " fill="bad"/>', '<Highlight cell="nykaa / roas" color="good"/>'))


def test_highlight_limit_keeps_the_first_four():
    marks = [f'<Highlight row="{r}" fill="good"/>' for r in ("Amazon", "Flipkart", "Myntra", "Nykaa")]
    res = hl(*marks, '<Highlight column="ROAS" color="bad"/>')
    assert "NODE_HIGHLIGHT_LIMIT" in codes(res) and res["ok"]
    assert not any("negativeText" in a for r in tds(res["xml"]) for a, _ in r)


def test_highlight_rule_skips_mixed_units():
    t = dict(ROAS, content_data=dict(ROAS["content_data"], table_rows=[
        ["A", "₹6.2 Cr", "2x", "2x", ""], ["B", "₹42L", "1x", "2x", ""]]))
    res = run('<Table ref="roas"><Highlight column="Spend" max="bad"/></Table>', t)
    assert "NODE_HIGHLIGHT_RULE" in codes(res) and res["ok"]
    assert "negativeText" not in res["xml"]


def test_highlight_other_children_dropped():
    res = hl('<Td>x</Td><Highlight row="Amazon" fill="good"/>')
    assert "NODE_ATTR_DROPPED" in codes(res) and "<Td>x</Td>" not in res["xml"]


@pytest.mark.parametrize("variant", ["rows", "columns", "banded", "grid", "grid numbered", "ledger"])
def test_highlight_on_every_composition(variant):
    res = hl('<Highlight row="Flipkart" fill="bad"/>', '<Highlight column="ROAS" max="good"/>',
             '<Highlight phrase="spend still rising" color="bad"/>', variant=variant)
    x = res["xml"]
    assert res["ok"], codes(res)
    assert "$negativeSoft" in x and 'color="$positiveText"' in x
    assert '<Span color="$negativeText">spend still rising</Span>' in x


def test_prompt_line_shows_cells_to_read():
    line = TB.prompt_line(ROAS)
    assert "columns: Platform | Spend | ROAS | Target | Note" in line
    assert "Flipkart | ₹42.0L | 0.34x | 2.0x | Below target, spend still rising" in line
    assert "hint: flag the Flipkart row" in line and "never type one yourself" in line


def test_node_lines_teach_highlight_not_mark():
    lines = TB.node_lines()
    assert "<Highlight" in lines and "<Mark" not in lines and "max=" in lines and "below=" in lines
