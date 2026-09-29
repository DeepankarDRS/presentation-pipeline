"""card_grid — parallel items, phases and word grids as cards (2026-09-29 XTSY / CHEFFIN reviews).

The planner had no card kind for words: parallel items went to bullet_list with an
icon per point (batch A routing), and every bullet_list slide also got the icon-row
recipe, so moments / pillars / phases / impact areas rendered as half-empty icon lists.
"""

import json

from src.agents.context_builder import _recipe_kind, _render_component_recipes
from src.agents.hint_capabilities import hint_scopes, planner_capabilities_section
from src.agents.planner_schema import PlannerComponent
from src.agents.slide_component_planner import _jinja_env


def _prompt() -> str:
    return _jinja_env.get_template("system.j2").render(hint_capabilities=planner_capabilities_section())


def test_schema_accepts_card_grid():
    c = PlannerComponent(component_id="moments", kind="card_grid", items=5, content_data_json=json.dumps(
        {"card_layout": "grid", "cards": [{"title": "Stand-up", "tag": "09:00"}]}))
    assert c.kind == "card_grid"


def test_each_card_layout_gets_its_recipe():
    for layout, key in (("grid", "card_grid"), ("steps", "card_steps"), ("matrix", "card_matrix")):
        comp = {"kind": "card_grid", "content_data": {"card_layout": layout}}
        assert _recipe_kind(comp) == key
        assert f"# {key}\n" in _render_component_recipes([key])
    assert _recipe_kind({"kind": "card_grid"}) == "card_grid"


def test_bullet_list_gets_icon_rows_only_when_asked():
    plain = _render_component_recipes([_recipe_kind({"kind": "bullet_list", "design_hint": "bold the action"})])
    icons = _render_component_recipes([_recipe_kind({"kind": "bullet_list", "design_hint": "icon beside each point"})])
    assert "# bullet_list" in plain and "icon_bullet_list" not in plain
    assert "# icon_bullet_list" in icons


def test_card_grid_has_hint_scope():
    scope = hint_scopes(["card_grid"])["card_grid"]
    assert "inverted" in scope and "never:" in scope


def test_planner_routes_parallel_items_phases_and_word_grids_to_cards():
    p = _prompt()
    assert "| card_grid (card_layout \"grid\") |" in p
    assert "| card_grid (card_layout \"steps\") |" in p
    assert "| card_grid (card_layout \"matrix\") |" in p
    assert "bullet_list (an icon per point)" not in p          # batch A routing replaced
    assert "Example 5 — Parallel named items" in p
    assert "use card_grid, steps layout" in p                   # pyramid / chevron detail


def test_highlight_default_follows_the_layout():
    """User decision 2026-09-29 (from the Genspark traces): one highlight for steps (the
    destination) and hubs (the centre); grids equal unless singled out; matrices may mark several."""
    p = _prompt()
    assert "steps → ONE card, the destination" in p
    assert "a hub or engine with inputs and outputs → ONE card, the centre" in p
    assert "grid of parallel items → all cards equal" in p
    assert "matrix → every cell the brief marks" in p


def test_single_kpi_gets_the_hero_stat_recipe_and_planner_explains_it():
    """A: the one number the headline rests on is a kpi_row of 1, drawn as a hero stat."""
    one = {"kind": "kpi_row", "content_data": {"kpi_values": ["0.33x"]}}
    many = {"kind": "kpi_row", "content_data": {"kpi_values": ["₹114.9L", "₹37.4L"]}}
    assert _recipe_kind(one) == "hero_stat" and _recipe_kind(many) == "kpi_row"
    assert "# hero_stat\n" in _render_component_recipes(["hero_stat"])
    p = _prompt()
    assert "ONE number the headline rests on" in p and "kpi_row count=1 (hero: drawn very large)" in p
