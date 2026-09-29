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
