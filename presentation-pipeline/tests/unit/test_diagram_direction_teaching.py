"""Diagram direction and space are taught as one decision (user, 2026-10-20).

Teaching only, no code rewrites the plan: the slide component planner chooses direction,
weight and band together (a process drawn with arrows is never a layer; every step is its own
node, parallel ones too — user, 2026-10-21), the generator sizes the diagram to that band (facts *.box_for_direction), and the visual
critic only flags a diagram without its space.
"""

from __future__ import annotations

import re

from src.compiler import node_facts as nf


def _flat(text: str) -> str:
    return " ".join(text.split())


def _planner_prompt() -> str:
    from src.agents.slide_component_planner import _jinja_env
    return _flat(_jinja_env.get_template("system.j2").render(content_field="content_data_json"))


def test_planner_chooses_direction_and_space_together():
    text = _planner_prompt()
    assert "Diagram direction and space are one decision." in text
    assert "choose the direction (tree: layout), the diagram's weight and the layout_hint together" in text
    assert "**horizontal** only when the diagram has a band to itself across the slide width" in text
    assert "**vertical** when the diagram shares the width with another component" in text
    assert "Never a horizontal diagram squeezed beside another component." in text
    assert "A diagram's weight follows its direction" in text
    assert "the layout_hint states the band you chose with its direction" in text


def test_planner_never_draws_a_process_as_a_layer():
    text = _planner_prompt()
    assert re.search(r"A process the brief draws with arrows .*? never \*\*layer\*\*", text)
    assert "steps the brief lists side by side between the same two arrows are separate nodes, one each" in text
    assert "More steps than fit across → the same diagram **vertical**" in text
    assert "Never a layer for a process, workflow or anything the brief draws with arrows" in text


def test_planner_rules_stay_general():
    text = _planner_prompt()
    for brief_word in ("XTSY", "Decision Engine", "Bid Optimization", "Bid optimization", "Profitability"):
        assert brief_word not in text, brief_word


def test_every_line_diagram_says_which_box_its_direction_needs():
    for kind, fid in (("flow", "flow.box_for_direction"), ("process_arrow", "process_arrow.box_for_direction"),
                      ("timeline", "timeline.box_for_direction"), ("tree", "tree.box_for_layout")):
        ids = {f["id"]: f for f in nf.facts(kind, "generator")}
        assert fid in ids, fid
        assert ids[fid]["kind"] == "advice" and "full-width band" in ids[fid]["text"]
        direction = next(f for f in nf.facts(kind, "planner") if f["id"].endswith((".direction", ".layout")))
        assert "full-width band" in _flat(direction["text"]), direction["id"]


def test_critic_flags_a_diagram_without_its_space_and_never_lays_it_out():
    from src.agents.visual_critic import _jinja_env
    text = _flat(_jinja_env.get_template("system.j2").render(slide_type="content"))
    rule = re.search(r"\*\*Diagram without its space\*\*:(.*?)- \*\*Parallel items", text).group(1)
    assert "wrong direction or too little space" in rule
    assert "LOW, flag only" in rule and "never a patch and never a new layout" in rule


_MERGE = re.compile(r"parallel steps (as|are) one node|ONE node \(or step\) whose label|parallel steps\)? are therefore one step"
                    r"|a node of parallel steps", re.I)


def test_no_text_merges_parallel_steps_into_one_node():
    """User, 2026-10-21: "Bid Optimization Budget Reallocation Keyword Expansion Placement Optimization" in one
    flow node is a mixture of nodes. Each step gets its own node; one node holds several steps (joined with
    " · ") only past the vertical limit too, as the last resort."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "src"
    hits = [str(p) for p in list((root / "prompts").rglob("*.j2")) + list((root / "knowledge").rglob("*.yaml"))
            if _MERGE.search(_flat(p.read_text(encoding="utf-8")))]
    assert not hits, hits
    text = _planner_prompt()
    last = text.index("Only when the steps exceed the vertical number too")
    assert '" · "' in text[last:last + 300] and text.count('" · "') == 1
