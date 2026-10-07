"""The node prompt (§3.5): one line per component in place of its data and recipe, and the
generator's system / user prompts rendered with the node rules.

A line names the tag, a shape hint in lengths (never the text, so nothing invites retyping),
the weight and the variants whose `requires` hold:
    summary_kpis · <KpiRow ref="summary_kpis"/> · 4 tiles, longest value 7 chars · weight hero · variants: plain = ...; filled = ...
"""

from __future__ import annotations

from typing import Any

from src.compiler.nodes import spec


def _words(s: Any) -> int:
    return len(str(s).split())


def _longest_words(items: list) -> int:
    return max((_words(i) for i in items), default=0)


def shape(comp: dict) -> str:
    """Lengths only: how many items and how long, so the LLM can size the box."""
    cd = comp.get("content_data") or {}
    k = comp["kind"]
    its = spec.items(comp)
    n = len(its)
    if k == "kpi_row":
        vals = [str(v) for v in cd.get("kpi_values") or []]
        notes = any(str(d).strip() for d in cd.get("kpi_deltas") or [])
        return (f"{n} tile{'s' * (n != 1)}, longest value {max((len(v) for v in vals), default=0)} chars, "
                f"longest label {_longest_words(cd.get('kpi_labels') or [])} words" + (", each with a note" if notes else ""))
    if k == "card_grid":
        cards = cd.get("cards") or []
        bodies = [c.get("body") or " ".join(c.get("bullets") or []) for c in cards]
        body = f", longest body {_longest_words(bodies)} words" if any(bodies) else ", titles only"
        layout = cd.get("card_layout") or "grid"
        return f"{n} cards ({layout}), longest title {_longest_words(its)} words{body}"
    if k == "table":
        cols = cd.get("table_columns") or []
        rows = cd.get("table_rows") or []
        cells = [str(c) for r in rows for c in r] + [str(c) for c in cols]
        return f"{len(rows)} rows x {max([len(cols)] + [len(r) for r in rows])} cols, longest cell {max((len(c) for c in cells), default=0)} chars"
    if k == "chart":
        series = cd.get("chart_series")
        s = f", {len(series)} series" if series and len(series) > 1 else ""
        return f"{cd.get('chart_type') or 'bar'} chart, {n} points{s}, longest label {max((len(i) for i in its), default=0)} chars"
    if k == "tree":
        levels, widths = 0, {}

        def walk(nodes, d):
            nonlocal levels
            for t in nodes or []:
                levels = max(levels, d + 1)
                widths[d] = widths.get(d, 0) + 1
                walk(t.get("children"), d + 1)
        walk(cd.get("tree_nodes"), 0)
        return f"{n} nodes, {levels} levels, widest level {max(widths.values(), default=0)}"
    if k == "matrix":
        return f"2x2 map, {n} items, longest label {_longest_words(its)} words"
    if k in ("narrative", "caption"):
        return f"{_words(its[0]) if its else 0} words"
    noun = {"bullet_list": "bullets", "timeline": "points", "process_arrow": "steps", "flow": "steps",
            "pyramid": "levels"}.get(k, "items")
    return f"{n} {noun}, longest {_longest_words(its)} words"


def line(comp: dict) -> str:
    """The component's prompt line (a `title` / `layer` gets none: see `self_drawn`)."""
    cid, k = comp["component_id"], comp["kind"]
    tags = spec.tags_for(k)
    tag_txt = " or ".join(f'<{t} ref="{cid}"/>' for t in tags)
    parts = [cid, tag_txt, shape(comp)]
    if comp.get("weight"):
        parts.append(f"weight {comp['weight']}")
    vs = spec.available(k, tags[0], comp)
    if len(vs) > 1:
        parts.append("variants: " + "; ".join(f"{name} = {v.get('prompt', '')}" for name, v in vs.items()))
    out = " · ".join(parts)
    if comp.get("content_summary"):
        out += f"\n    ({comp['content_summary']})"
    return out


def self_drawn(comp: dict) -> bool:
    return comp["kind"] == "layer"


def render_prompts(plan: dict, contract: dict, *, raw_request: str = "", core_hook: str = "") -> tuple[str, str]:
    """(system, user) for the node arm: the generator's system prompt with the node rules in place of
    the recipes and visual-intent section, and nodes_user.j2 with one line per component."""
    from src.agents.generator import _jinja_env

    system = _jinja_env.get_template("system.j2").render(
        forbidden_tags=contract.get("forbidden_tags", []),
        forbidden_attributes=contract.get("forbidden_attributes", []),
        theme_element=contract.get("theme_element", ""),
        allowed_nodes=contract.get("allowed_nodes", []),
        allowed_attributes=contract.get("allowed_attributes", {}),
        node_hierarchy=contract.get("node_hierarchy", ""),
        component_count=contract.get("component_count", 0),
        house_style=contract.get("house_style", ""),
        component_recipes=contract.get("component_recipes", ""),
        golden_examples=contract.get("golden_examples", ""),
        blueprint_structure=contract.get("blueprint_structure", ""),
        blueprint_reference_xml=contract.get("blueprint_reference_xml", ""),
        notes=contract.get("notes", []),
        visual_intent_techniques=contract.get("visual_intent_techniques", ""),
        icon_names=contract.get("icon_names", ""),
        core_hook=core_hook,
        slide_type=plan.get("slide_type", ""),
        nodes=True,
    )
    comps = [c for c in plan.get("components") or [] if c["kind"] != "title"]
    user = _jinja_env.get_template("nodes_user.j2").render(
        objective=raw_request,
        slide_title=plan.get("slide_title", ""),
        label=plan.get("label", ""),
        subtitle=plan.get("subtitle", ""),
        core_hook=core_hook,
        slide_type=plan.get("slide_type", ""),
        node_lines=[line(c) for c in comps if not self_drawn(c)],
        self_drawn=[c for c in comps if self_drawn(c)],
        layout_hint=plan.get("layout_hint", ""),
    )
    return system, user
