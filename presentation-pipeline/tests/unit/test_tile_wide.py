"""scripts.experiments.tiles.tile_wide / tile_replay helpers (docs/eval/tile-nodes/wide/README.md)."""

from lxml import etree

from scripts.experiments.tiles import tile_replay as TR
from scripts.experiments.tiles import tile_wide as W


def test_rewrite_keeps_the_rows_size_attributes_and_drops_literal_colours():
    row = etree.fromstring('<HStack grow="3" gap="14" w="max" backgroundColor="FDEAEA" border.color="$border"/>')
    assert TR._box(row) == {"grow": "3", "gap": "14", "w": "max", "border.color": "$border"}


def test_an_old_saved_theme_gets_todays_derived_tokens():
    old = ('<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" accentAlt="0EA5E9" positive="15803D" '
           'negative="DC2626" warning="B45309" textMain="16202E" textMuted="55627A" border="E2E8F0" />')
    new = W.upgrade_theme(old)
    for token in ("accentText", "negativeSoft", "positiveText", "onAccent"):
        assert f'{token}="' in new
    assert W.upgrade_theme(new) == new   # already current: unchanged


PLAN = {"components": [{"component_id": "k", "kind": "kpi_row", "design_hint": "colour-code losses red",
                        "content_data": {"kpi_labels": ["ARR", "Churn"], "kpi_values": ["$48M", "4%"]}}]}


def test_looks_counts_colour_kinds_and_label_colours_per_tile():
    xml = ('<HStack>'
           '<VStack backgroundColor="$surfaceAlt" border.color="$border"><Text color="$textMuted">ARR</Text>'
           '<Text id="kpiv-k-0" color="$textMain">$48M</Text></VStack>'
           '<VStack backgroundColor="$negativeSoft"><Text color="$negativeText">Churn</Text>'
           '<Text id="kpiv-k-1" color="$negativeText">4%</Text></VStack></HStack>')
    lk = W.looks(xml, PLAN)["k"]
    assert lk["tones"] is False and lk["hint_colour"] is True
    assert lk["kinds"] == {"none": 1, "semantic": 1} and lk["coloured"] is True
    assert lk["labels"] == ["muted", "semantic"]


def test_max_neighbours_lists_a_w_max_box_beside_another():
    xml = '<HStack><VStack w="max"><Text>a long callout text</Text></VStack><VStack w="max"/></HStack>'
    assert W.max_neighbours(xml) == ["VStack w=max (19 ch) | VStack w=max (0 ch)"]
    assert W.max_neighbours('<HStack><VStack w="max"/></HStack>') == []
