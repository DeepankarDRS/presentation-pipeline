"""R8 (composition spec §11.3): every tag / variant / style name a prompt or knowledge file uses exists in
block-variants.yaml, and the KPI / card composition nodes' aliases, recipes, look keys and requires checks resolve."""

import re
from pathlib import Path

import yaml

from src.compiler.nodes import compose, spec
from tests.unit.test_tile_groups import KPIS, LEVERS

ROOT = Path(__file__).resolve().parents[2]


def _bv():
    return yaml.safe_load((ROOT / "src/knowledge/core/block-variants.yaml").read_text(encoding="utf-8"))


def test_nodes_entries_consistent():
    """Every alias, recipe, look key and requires check in the KPI / card nodes resolves."""
    for kind in ("kpi_row", "card_grid"):
        nd = _bv()["nodes"][kind]
        cs, parts = nd["compositions"], set(nd["parts"])
        assert set(nd["prompts"]) == set(cs)
        for name, a in nd["aliases"].items():
            word = a["variant"] if isinstance(a, dict) else a
            assert word in cs, (kind, name)
            if isinstance(a, dict) and "style" in a:
                assert a["style"] in nd["styles"]
        for k, words in nd["meta_aliases"].items():
            assert set(words.values()) <= set(cs)
        for name, c in cs.items():
            assert c.get("fallback") in (None, *cs)
            for layer in [c.get("look") or {}, c.get("emphasis") or {}, *(c.get("tone") or {}).values()]:
                for k in layer:
                    head, _, sub = k.partition(".")
                    assert k == "size" or not sub or head in parts or head in tiles_box_heads(), (kind, name, k)
            for r in (c.get("requires") or []) + (c.get("emphasis_requires") or []):
                spec.check(r, KPIS if kind == "kpi_row" else LEVERS)   # KeyError on an unknown check
        for s in nd["styles"].values():
            for k in compose.recipe(s):
                assert k.split(".")[0] in parts, (kind, k)


def tiles_box_heads():
    from src.compiler.nodes import tiles
    return {a.split(".")[0] for a in tiles.data()["box_attributes"]}


def _names_for(tag: str) -> set[str]:
    bv = _bv()
    out: set[str] = set()
    for b in bv["blocks"].values():
        if b["tag"] == tag:
            out |= set(b.get("variants") or {})
    for k in ("kpi", "card"):
        t = bv["tile_nodes"][k]
        if tag in (t["group_tag"], t["item_tag"]):
            out |= set(t["variants"])
    for nd in bv["nodes"].values():
        if tag == nd["tag"] or tag in (nd.get("tag_aliases") or {}) or tag == nd.get("item_tag"):
            out |= set(nd["compositions"]) | set(nd.get("aliases") or {})
    return out


def test_r8_every_tag_and_variant_used_exists():
    """Every <Tag ... variant="x"> in prompts, knowledge and node code names a tag and a name block-variants.yaml has
    for that tag (promised in its header; spec §11.3 R8)."""
    bv = _bv()
    known_tags = {b["tag"] for b in bv["blocks"].values()} | {t[k] for t in bv["tile_nodes"].values()
                                                             if isinstance(t, dict) and "group_tag" in t
                                                             for k in ("group_tag", "item_tag")}
    for nd in bv["nodes"].values():
        known_tags |= {nd["tag"], *(nd.get("tag_aliases") or {})} | ({nd["item_tag"]} if nd.get("item_tag") else set())
    files = [*(ROOT / "src/prompts").rglob("*.j2"), *(ROOT / "src/knowledge").rglob("*.yaml"),
             *(ROOT / "src/compiler/nodes").glob("*.py"), *(ROOT / "src/agents").glob("*.py")]
    rx = re.compile(r'<([A-Z]\w*)\b[^<>]*?\bvariant=\\?"([^"\\]+)')
    seen = 0
    for f in files:
        for tag, v in rx.findall(f.read_text(encoding="utf-8")):
            if tag not in known_tags or "{" in v or v in ("...", "x"):
                continue
            seen += 1
            assert v in _names_for(tag), f"{f.name}: <{tag} variant=\"{v}\"> is not in block-variants.yaml"
    assert seen


def test_r8_treatment_and_style_names_exist():
    """variant="x" inside the tile treatments names a tile variant; every style recipe in the nodes is a recipe."""
    bv = _bv()
    for k in ("kpi", "card"):
        t = bv["tile_nodes"][k]
        for how in t["treatments"].values():
            for v in re.findall(r'variant="([^"]+)"', how):
                assert v in t["variants"], (k, v)
    for nd in bv["nodes"].values():
        for v in (nd.get("styles") or {}).values():
            assert compose.recipe(v), v
