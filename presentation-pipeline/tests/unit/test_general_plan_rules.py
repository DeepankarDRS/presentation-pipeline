"""General plan checks (2026-11-12): the item ledger and the shape check (src/agents/plan_ledger.py), plus the
placement flag. Every case is written in neutral words, not from one brief: the checks look at the brief's items and
the routing table, never at a topic or a single slide. They were replayed on the saved outline + plan pairs before use
(output/**/runs.json): 395 slide plans, missing 6%, repeated 2%, shape 0.5%, the samples read as real faults."""

from __future__ import annotations

from src.agents.capacity import enforce_capacity
from src.agents.plan_ledger import (ITEM_MISSING, ITEM_REPEATED, SHAPE_MISFIT, brief_items, ledger_problems,
                                    routing_rows, shape_problems)
from src.agents.written_lines import flag_placed_items


def _slide(*messages, **extra):
    return {"slide_index": 0, "slide_title": "Headline", "key_messages": list(messages), **extra}


def _plan(*components):
    return {"components": list(components)}


def _comp(cid, kind, data):
    return {"component_id": cid, "kind": kind, "content_data": data}


def _cards(*cards):
    return _comp("g", "card_grid", {"card_layout": "grid", "cards": [{"title": t, "bullets": b} for t, b in cards]})


def _codes(problems):
    return [p["code"] for p in problems]


# ── items ───────────────────────────────────────────────────────────────────

def test_items_are_the_briefs_pieces_without_labels_directions_or_headers():
    slide = _slide("Visual: a three-step diagram", "Show progression from A to B",
                   "Areas: Search ads; Display banners", "Benefits:", "Metric | Value",
                   "Ingest → Clean → Publish", "Levels (top → bottom): Core, Edge")
    items = brief_items(slide)
    assert "Search ads" in items and "Display banners" in items
    assert {"Ingest", "Clean", "Publish"} <= set(items)
    assert not any(i.startswith(("Show", "a three-step")) for i in items)
    assert "Benefits" not in items and "Metric | Value" not in items
    assert "Core, Edge" in items   # the arrow inside brackets did not split the line


def test_an_item_on_no_component_is_missing():
    slide = _slide("Areas: Search ads; Display banners; Loyalty emails")
    plan = _plan(_comp("l", "bullet_list", {"bullets": ["Search ads", "Display banners"]}))
    problems = ledger_problems(plan, slide)
    assert _codes(problems) == [ITEM_MISSING] and "Loyalty emails" in problems[0]["detail"]


def test_a_figure_must_appear_exactly_but_prose_may_be_redrawn():
    slide = _slide("North returned 0.80x on 31.5 spend")
    as_cells = _plan(_comp("t", "table", {"table_columns": ["Region", "Return", "Spend"],
                                          "table_rows": [["North", "0.8x", "31.5"]]}))
    assert ledger_problems(as_cells, slide) == []           # 0.80 = 0.8, the prose became cells
    wrong = _plan(_comp("t", "table", {"table_columns": ["Region", "Return"], "table_rows": [["North", "0.9x"]]}))
    assert _codes(ledger_problems(wrong, slide)) == [ITEM_MISSING]


def test_the_header_covers_a_cover_line():
    slide = _slide("Quarterly review | Key results", subtitle="Quarterly review | Key results")
    assert ledger_problems(_plan(_comp("t", "title", {"title": "Headline"})), slide) == []


def test_the_same_item_in_two_components_is_repeated():
    slide = _slide("Ingest → Clean → Publish")
    plan = _plan(_comp("a", "process_arrow", {"process_steps": ["Ingest", "Clean", "Publish"]}),
                 _comp("c", "card_grid", {"cards": [{"title": "Ingest"}, {"title": "Clean"}, {"title": "Publish"}]}))
    assert ITEM_REPEATED in _codes(ledger_problems(plan, slide))


def test_shared_words_are_not_a_repeat():
    slide = _slide("Stages: Market Share; Growth", "Phase 2: Market Share Capture")
    plan = _plan(_comp("a", "process_arrow", {"process_steps": ["Market Share", "Growth"]}),
                 _comp("c", "card_grid", {"cards": [{"title": "Market Share Capture"}]}))
    assert ITEM_REPEATED not in _codes(ledger_problems(plan, slide))


def test_one_data_set_drawn_twice_is_repeated():
    slide = _slide("North 31.1 vs 10.7", "South 46.2 vs 14.8")
    plan = _plan(_comp("ch", "chart", {"chart_labels": ["North", "South"], "chart_series": [
                    {"name": "Actual", "values": [31.1, 46.2]}, {"name": "Limit", "values": [10.7, 14.8]}]}),
                 _comp("tb", "table", {"table_columns": ["Region", "Actual", "Limit"],
                                       "table_rows": [["North", "31.1", "10.7"], ["South", "46.2", "14.8"]]}))
    assert ITEM_REPEATED in _codes(ledger_problems(plan, slide))


def test_one_figure_in_a_callout_is_not_a_repeated_data_set():
    slide = _slide("Margin 31%", "Growth 18%")
    plan = _plan(_comp("k", "kpi_row", {"kpi_labels": ["Margin", "Growth"], "kpi_values": ["31%", "18%"]}),
                 _comp("n", "narrative", {"text": "31%"}))
    assert ITEM_REPEATED not in _codes(ledger_problems(plan, slide))


# ── shape ───────────────────────────────────────────────────────────────────

def test_shape_check_cites_the_routing_table_the_prompt_shows():
    two = _plan(_comp("t", "table", {"table_columns": ["Group", "Score"], "table_rows": [["A", "0.34x"], ["B", "0.32x"]]}))
    problems = shape_problems(two)
    assert _codes(problems) == [SHAPE_MISFIT]
    row = next(r for r in routing_rows() if r["id"] == "two_subjects")
    assert row["states"] in problems[0]["detail"] and row["kind"] in problems[0]["detail"]


def test_shapes_that_fit_their_kind_pass():
    ok = _plan(_comp("t", "table", {"table_columns": ["Region", "Margin"], "table_rows": [["A", "31%"], ["B", "24%"],
                                                                                         ["C", "22%"]]}),
               _comp("c", "chart", {"chart_labels": ["A", "B"], "chart_series": [{"name": "x", "values": [1, 2]},
                                                                                 {"name": "y", "values": [3, 4]}]}),
               _comp("s", "table", {"table_columns": ["Group", "Note"], "table_rows": [["A", "Cost is 2.9x the limit"]]}))
    assert shape_problems(ok) == []


def test_a_chart_mixing_units_on_one_axis_is_a_misfit():
    plan = _plan(_comp("c", "chart", {"chart_labels": ["A", "B", "C"], "chart_series": [
        {"name": "Spend", "values": ["₹21L", "₹45L", "₹9L"]}, {"name": "Return", "values": ["0.4x", "0.3x", "0.5x"]}]}))
    assert _codes(shape_problems(plan)) == [SHAPE_MISFIT]


def test_the_prompt_renders_every_routing_row():
    from src.agents.slide_component_planner import _jinja_env
    text = _jinja_env.get_template("system.j2").render(hint_capabilities="", content_field="content")
    for row in routing_rows():
        assert f"| {row['states']} | {row['kind']} | {row['not_for']} |" in text, row["id"]


# ── the code fix that stays: sentences are never tile values ───────────────

def test_a_metric_table_of_sentences_is_not_turned_into_tiles():
    comps = [_comp("t", "table", {"table_columns": ["Metric", "Value"], "table_rows": [
        ["Cost", "Cost is 2.9x what it can carry"], ["Share", "Share fell to 12% this quarter"],
        ["Return", "0.4x"]]})]
    enforce_capacity(comps)
    assert comps[0]["kind"] == "table"


# ── placements by meaning (content policy, inferred) ────────────────────────

def test_items_from_one_flat_list_filed_under_groups_are_listed_for_review():
    brief = "Groups: Reach Retention\nAreas: Search ads; Display banners; Loyalty emails; Win-back offers"
    plan = {"components": [_cards(("Reach", ["Search ads", "Display banners"]),
                                  ("Retention", ["Loyalty emails", "Win-back offers"]))]}
    notes = flag_placed_items(plan, brief)
    assert plan["placed_items"] == ["Reach: Search ads", "Reach: Display banners", "Retention: Loyalty emails",
                                    "Retention: Win-back offers"] and notes


def test_items_the_brief_files_itself_are_not_flagged():
    for brief in ("Reach: Search ads, Display banners; Retention: Loyalty emails, Win-back offers",
                  "Phase 1: Reach - Search ads, Display banners\nPhase 2: Retention - Loyalty emails, Win-back offers"):
        plan = {"components": [_cards(("Reach", ["Search ads", "Display banners"]),
                                      ("Retention", ["Loyalty emails", "Win-back offers"]))]}
        assert flag_placed_items(plan, brief) == [] and "placed_items" not in plan, brief


# ── found in the planner A/B (2026-11-12) ───────────────────────────────────

def test_separators_inside_brackets_do_not_split_an_item_and_a_position_is_shown():
    slide = _slide("2x2 (Effort low→high; Impact low→high): Item A: low effort, high impact; Item B: high effort, "
                   "low impact")
    items = brief_items(slide)
    assert not any(i.startswith(("Impact low", "2x2 (Effort low→high")) and ";" not in i for i in items)
    plan = _plan(_comp("m", "matrix", {"x_axis": "Effort", "y_axis": "Impact", "matrix_items": [
        {"label": "Item A", "x": "low", "y": "high"}, {"label": "Item B", "x": "high", "y": "low"}]}))
    assert ledger_problems(plan, slide) == []


def test_a_bullet_the_brief_files_under_its_card_is_not_a_placement():
    brief = ("Sources: North report\nSources: South data\nSources: East data\n"
             "Note: South sheets differ; East data was used for the totals")
    plan = {"components": [_cards(("Sources", ["North report", "South data", "East data"]),
                                  ("Note", ["South sheets differ", "East data was used for the totals"]))]}
    assert flag_placed_items(plan, brief) == []
    steps = "Month 1 Audit: channel review, offer audit → Month 2 Launch: start pilot, open bundles"
    plan = {"components": [_cards(("Audit", ["channel review", "offer audit"]), ("Launch", ["start pilot", "open bundles"]))]}
    assert flag_placed_items(plan, steps) == []


def test_a_component_that_only_repeats_the_header_is_dropped():
    from src.agents.plan_checks import HEADER_REPEATED, finalize_plan
    plan = {"label": "THE PROBLEM", "slide_title": "Costs rise", "subtitle": "Across teams", "components": [
        _comp("k", "narrative", {"text": "THE PROBLEM"}), _comp("s", "caption", {"text": "Across teams."}),
        _comp("n", "narrative", {"text": "Costs rise across teams, slowing delivery."})]}
    finalize_plan(plan, "Costs rise across teams, slowing delivery.")
    assert [c["component_id"] for c in plan["components"]] == ["n"]
    assert HEADER_REPEATED in [f["code"] for f in plan["plan_flags"]]


def test_a_bracketed_kpi_change_loses_its_brackets():
    from src.agents.plan_checks import finalize_plan
    plan = {"components": [_comp("k", "kpi_row", {"kpi_labels": ["A", "B"], "kpi_values": ["$4M", "11%"],
                                                  "kpi_deltas": ["(+18% QoQ)", "(net) of returns"]})]}
    finalize_plan(plan, "A: $4M (+18% QoQ); B: 11% (net) of returns")
    assert plan["components"][0]["content_data"]["kpi_deltas"] == ["+18% QoQ", "(net) of returns"]
