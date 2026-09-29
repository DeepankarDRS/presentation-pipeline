"""Borders on table cells / list items / diagram nodes (layout-batch run, 2026-09-29).

Design hints like "accent border on the ROAS and CPC rows" made the generator put
borderLeft on <Td> and <FlowNode>; POM rejects it (UNKNOWN_ATTRIBUTE) and 6 of 28 slides
went to the LLM repairer. The normalizer now removes them; the card keeps its border.
"""

from pathlib import Path

import yaml

from src.compiler.normalizer import normalize_xml

CELL = '<Td backgroundColor="FDECEA" color="$negative" borderLeft.color="$accent" borderLeft.width="4">CPC</Td>'


def _slide(body: str) -> str:
    return f'<Slide><VStack w="1280" h="720" padding="36"><VStack padding="18" borderLeft.color="$accent" borderLeft.width="4">{body}</VStack></VStack></Slide>'


def test_td_border_from_the_cheffin_run_is_removed_card_border_kept():
    out = normalize_xml(_slide(f'<Table><Col /><Col /><Tr>{CELL}<Td>₹31.1</Td></Tr></Table>'))
    xml = out["cleaned_xml"]
    assert "<Td backgroundColor=\"FDECEA\" color=\"$negative\">CPC</Td>" in xml
    assert '<VStack padding="18" borderLeft.color="$accent" borderLeft.width="4">' in xml
    assert any(i["code"] == "ITEM_BORDER_REMOVED" and "2 border" in i["message"] for i in out["issues"])
    assert not out["blocking"]


def test_flow_node_and_other_items_lose_borders():
    body = ('<Flow direction="horizontal"><FlowNode id="a" shape="process" text="Decision Engine" borderLeft.color="$accent" />'
            '<FlowNode id="b" shape="process" text="Outcome" /><FlowConnection from="a" to="b" /></Flow>'
            '<Ul><Li border.color="$accent">point</Li></Ul>')
    xml = normalize_xml(_slide(body))["cleaned_xml"]
    assert 'text="Decision Engine" />' in xml and "<Li>point</Li>" in xml


def test_text_and_shape_borders_are_left_alone():
    body = '<Text borderLeft.color="$accent" borderLeft.width="4">Read-out</Text>'
    out = normalize_xml(_slide(body))
    assert 'borderLeft.width="4">Read-out' in out["cleaned_xml"]
    assert not any(i["code"] == "ITEM_BORDER_REMOVED" for i in out["issues"])


class _NoDuplicates(yaml.SafeLoader):
    pass


def _no_dup_mapping(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
    dup = {k for k in keys if keys.count(k) > 1}
    assert not dup, f"duplicate YAML key(s) {dup} at line {node.start_mark.line + 1}"
    return loader.construct_mapping(node, deep=deep)


_NoDuplicates.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup_mapping)


def test_knowledge_yaml_has_no_duplicate_keys():
    """card_grid's entry once held two `never:` keys: YAML kept the last (pyramid's) silently."""
    root = Path(__file__).resolve().parents[2] / "src" / "knowledge"
    for path in sorted(root.rglob("*.yaml")):
        yaml.load(path.read_text(encoding="utf-8"), Loader=_NoDuplicates)
