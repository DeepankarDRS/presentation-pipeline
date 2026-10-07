"""The node prompt (§3.5): one line per component with lengths, never the content; the off prompt is unchanged."""

import json
from pathlib import Path

from src.agents import generator as G
from src.agents.context_builder import build_contract
from src.agents.style_resolver import resolve_theme
from src.compiler.nodes import prompt_lines
from src.compiler.nodes.spec import items

_RUNS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nodes" / "runs" / "decks"


def _plans():
    for case in ("deck-qbr-data", "gate-deck-all-nodes-dense"):
        for s in json.loads((_RUNS / f"{case}__r1" / "slides.json").read_text(encoding="utf-8")):
            yield s["slide_plan"]


def test_lines_name_the_tag_and_never_the_items():
    for plan in _plans():
        for c in plan["components"]:
            if c["kind"] in ("title", "layer"):
                continue
            line = prompt_lines.line(c).split("\n")[0]   # the content_summary line under it is the planner's
            assert f'ref="{c["component_id"]}"' in line
            for item in items(c):
                if len(item) > 12:   # a long item text never appears in the line itself
                    assert item not in line, (c["component_id"], item)


def test_shape_hints():
    plan = next(p for p in _plans() if p["slide_title"] == "Headline KPIs")
    assert prompt_lines.shape(plan["components"][2]).startswith("3 tiles, longest value 9 chars")


def test_off_prompt_unchanged_and_nodes_prompt_swaps_recipes():
    theme = resolve_theme("corporate-slate")
    for plan in _plans():
        contract = build_contract(plan, theme)
        off, _ = G._render_prompts({"contract": contract, "slide_plans": [plan], "current_slide_index": 0})
        assert "REF NODES" not in off
        system, user = prompt_lines.render_prompts(plan, contract)
        assert "REF NODES" in system and "## COMPONENT RECIPES" not in system and "VISUAL-INTENT TRANSLATION" not in system
        assert "Data for" not in user or "draw it yourself" in user    # data only for a layer
        if contract["component_recipes"]:
            assert "## COMPONENT RECIPES" in off


def test_layer_is_drawn_by_hand_with_its_data():
    plan = next(p for p in _plans() if any(c["kind"] == "layer" for c in p["components"]))
    _, user = prompt_lines.render_prompts(plan, build_contract(plan, resolve_theme("corporate-slate")))
    assert "architecture_layers · layer · draw it yourself" in user and "Channels" in user
    assert 'ref="architecture_layers"' not in user
