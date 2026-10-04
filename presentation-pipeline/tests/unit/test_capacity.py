"""Component capacity has ONE source (knowledge/core/capacity.yaml).

The planner prompt renders it, and no prompt or knowledge file may state a different
number — five files disagreeing on KPI tiles (3-5 / 3-4 / 4 / 2-6 / 6) let the planner
ask for more than the generator's recipe could draw (2026-09-29 deck reviews).
"""

import re
from pathlib import Path

from src.agents.capacity import capacity, max_of, span
from src.agents.hint_capabilities import planner_capabilities_section
from src.agents.slide_component_planner import _jinja_env

_K = Path(__file__).resolve().parents[2] / "src" / "knowledge"


def _prompt() -> str:
    return _jinja_env.get_template("system.j2").render(hint_capabilities=planner_capabilities_section())


def test_capacity_file_loads_with_ranges():
    cap = capacity()
    for kind in ("kpi_row", "table", "timeline", "process_arrow", "matrix", "card_grid"):
        assert kind in cap
    assert span("process_arrow") == "3-5" and max_of("table", "max_rows") == 10


def test_planner_prompt_renders_capacity():
    p = _prompt()
    assert "{{" not in p
    assert f"items = steps ({span('process_arrow')}), labels ≤ {capacity()['process_arrow']['max_label_words']} words" in p
    assert f"items = milestones ({span('timeline')})" in p
    assert f"items = positioned items ({span('matrix')})" in p
    assert f"({span('kpi_row', 'per_row')} per row;" in p


def test_no_stale_limits_in_planner_prompt():
    p = _prompt()
    for stale in ("more than 5 tiles", "3-5 typical", "rows exceed 6-7", "max 5 horizontal", "items exceed 3-5"):
        assert stale not in p, stale


def test_knowledge_files_agree_with_capacity():
    cap = capacity()
    recipes = (_K / "core" / "recipes.yaml").read_text(encoding="utf-8")
    house = (_K / "core" / "house-style.yaml").read_text(encoding="utf-8")
    timeline = (_K / "components" / "timeline.yaml").read_text(encoding="utf-8")
    matrix = (_K / "components" / "matrix.yaml").read_text(encoding="utf-8")
    t_max, m_max = cap["timeline"]["items"][1], cap["matrix"]["items"][1]
    assert f"Max {t_max} items" in recipes and f"max {t_max} items" in house
    assert f"{m_max} items max" in recipes
    assert f'"{span("timeline")} items' in timeline and f'"{span("matrix")} items' in matrix
    # no kpi tile cap anywhere in the knowledge: tiers replace it
    assert not re.search(r"Max 3-4 tiles|Max 4 tiles|more than 5 tiles", recipes + house, re.I)


# ── plan check: past capacity -> card_grid (fix 8) ──────────────────────────

from src.agents.capacity import enforce_capacity  # noqa: E402


def test_seven_chevrons_become_a_card_grid():
    """XTSY slide 7: 7 impact areas as chevrons broke words into letters ('Consume r')."""
    steps = ["Category visibility", "Search share", "Sponsored placement share", "New consumer acquisition",
             "Repeat purchase rate", "Market share", "Sales velocity"]
    comps = [{"component_id": "impact", "kind": "process_arrow", "orientation": "horizontal",
              "content_data": {"direction": "horizontal", "process_steps": steps}}]
    notes = enforce_capacity(comps)
    assert comps[0]["kind"] == "card_grid" and "orientation" not in comps[0]
    assert comps[0]["content_data"]["card_layout"] == "grid"
    assert [c["title"] for c in comps[0]["content_data"]["cards"]] == steps
    assert "7 steps" in notes[0]


def test_short_sequence_with_long_labels_becomes_steps():
    comps = [{"kind": "process_arrow", "content_data": {"process_steps": ["Audit the category", "Activate", "Scale"]}}]
    enforce_capacity(comps)
    assert comps[0]["kind"] == "card_grid" and comps[0]["content_data"]["card_layout"] == "steps"


def test_long_timeline_keeps_dates_as_tags():
    items = [{"date": f"Week {i}", "label": f"Step {i}", "description": "detail"} for i in range(1, 8)]
    comps = [{"kind": "timeline", "content_data": {"timeline_items": items}}]
    enforce_capacity(comps)
    card = comps[0]["content_data"]["cards"][0]
    assert card == {"title": "Step 1", "tag": "Week 1", "body": "detail"}


def test_components_within_capacity_are_untouched():
    comps = [{"kind": "process_arrow", "content_data": {"process_steps": ["Plan", "Build", "Test", "Ship"]}},
             {"kind": "timeline", "content_data": {"timeline_items": [{"date": "Q1", "label": "Alpha"}] * 4}},
             {"kind": "table", "content_data": {"table_rows": [[1]] * 30}}]
    before = [dict(c) for c in comps]
    assert enforce_capacity(comps) == [] and comps == before


# ── layout-batch run fixes (2026-09-29, XTSY + CHEFFIN) ─────────────────────

from src.agents.capacity import per_row  # noqa: E402


def test_per_row_balances_rows():
    assert [per_row(n, 4) for n in (3, 4, 5, 6, 7, 8, 9, 12)] == [3, 4, 3, 3, 4, 4, 3, 4]


def test_every_grid_gets_its_cards_per_row():
    """XTSY run 2: 7 impact cards drawn in one row."""
    comps = [{"kind": "card_grid", "content_data": {"card_layout": "grid", "cards": [{"title": f"c{i}"} for i in range(7)]}}]
    enforce_capacity(comps)
    assert comps[0]["content_data"]["per_row"] == 4


def test_seven_steps_become_a_grid_and_a_long_flow_stays_a_flow():
    """XTSY run 2: 7 workflow steps in one row of a 62% panel broke words into letters.
    A long flow is reported, not switched: as cards it lost its arrows (2026-10-04)."""
    steps = [{"kind": "card_grid", "content_data": {"card_layout": "steps", "cards": [{"title": f"s{i}"} for i in range(7)]}}]
    flow = [{"kind": "flow", "content_data": {"flow_steps": [f"Node {i}" for i in range(7)]}}]
    n1, n2 = enforce_capacity(steps), enforce_capacity(flow)
    assert steps[0]["content_data"]["card_layout"] == "grid" and "too many for one row" in n1[0]
    assert flow[0]["kind"] == "flow" and "over its capacity" in n2[0] and "kept as a flow" in n2[0]


def test_metric_value_table_of_one_entity_becomes_kpi_tiers():
    """CHEFFIN slide 5: the brief's 'Show table: Metric | Value' (user decision L5: switch, record why)."""
    rows = [["Spend", "₹29.4L"], ["Ad sales", "₹10.1L"], ["ROAS", "0.34x"], ["CPC", "₹31.1"],
            ["CVR", "5.5%"], ["AOV", "₹195"], ["Allowable CPC for 1.0x ROAS", "₹10.7"]]
    comps = [{"component_id": "flip", "kind": "table", "weight": "hero", "design_hint": "shade the CPC row",
              "content_data": {"table_columns": ["Metric", "Value"], "table_rows": rows}},
             {"kind": "narrative", "content_data": {"text": "x"}}]
    notes = enforce_capacity(comps)
    assert [c["kind"] for c in comps] == ["kpi_row", "kpi_row", "narrative"]
    assert comps[0]["content_data"]["kpi_labels"] == ["Spend", "Ad sales", "ROAS"] and comps[0]["weight"] == "hero"
    assert comps[1]["content_data"]["kpi_values"] == ["₹31.1", "5.5%", "₹195", "₹10.7"] and comps[1]["weight"] == "supporting"
    assert "3 + 4" in notes[0] and "switched" in notes[0]


def test_one_measure_across_entities_stays_a_table():
    rows = [["Bengaluru", "0.45x"], ["Hyderabad", "0.31x"], ["Chennai", "0.28x"]]
    comps = [{"kind": "table", "content_data": {"table_columns": ["City", "ROAS"], "table_rows": rows}}]
    assert enforce_capacity(comps) == [] and comps[0]["kind"] == "table"


def test_icon_list_stays_a_list():
    """CHEFFIN slide 4 used to become a second card grid beside the main one, which
    narrowed the cards and broke words (XTSY slides 2, 3, 6); removed 2026-10-04."""
    sources = ["FLIPCART Targeting last 90 days report", "FLIPCART Search Term report", "ZAROMA campaign-level data",
               "ZAROMA city-level data", "ZAROMA keyword-level data"]
    comps = [{"kind": "bullet_list", "design_hint": "icon beside each point", "content_data": {"bullets": sources}}]
    assert enforce_capacity(comps) == [] and comps[0]["kind"] == "bullet_list"


def test_matrix_of_row_and_column_names_becomes_one_card_per_row():
    """XTSY slide 3: cells read 'Visibility — Zepto'."""
    rows, cols = ["Visibility", "Conversion", "Repeat Purchase", "Market Expansion"], ["Zepto", "Blinkit", "Instamart"]
    cards = [{"title": f"{r} — {c}"} for r in rows for c in cols]
    comps = [{"kind": "card_grid", "content_data": {"card_layout": "matrix", "rows": rows, "columns": cols, "cards": cards}}]
    notes = enforce_capacity(comps)
    cd = comps[0]["content_data"]
    assert cd["card_layout"] == "grid" and [c["title"] for c in cd["cards"]] == rows and "repeated" in notes[0]


def test_real_matrix_is_kept():
    rows, cols = ["Reach"], ["Web", "App"]
    comps = [{"kind": "card_grid", "content_data": {"card_layout": "matrix", "rows": rows, "columns": cols,
                                                    "cards": [{"title": "Search visibility"}, {"title": "Home-screen placement"}]}}]
    enforce_capacity(comps)
    assert comps[0]["content_data"]["card_layout"] == "matrix"
