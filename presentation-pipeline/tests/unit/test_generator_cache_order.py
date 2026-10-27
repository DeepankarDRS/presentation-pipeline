"""Cache order of the generator system prompt (docs/tile-nodes-spec-2026-10-12.md §5): every part that varies
per slide comes after "## THIS SLIDE", so two slides of one deck share everything before it (the cached prefix)."""

from src.agents.context_builder import build_contract
from src.agents.generator import _render_prompts
from src.agents.style_resolver import resolve_theme

MARK = "\n## THIS SLIDE\n"

COVER = {"slide_index": 0, "slide_type": "cover", "slide_title": "Q2 review", "components": [
    {"kind": "title", "component_id": "header", "count": 1}]}
DATA = {"slide_index": 1, "slide_type": "data", "slide_title": "Revenue grew 12%", "components": [
    {"kind": "title", "component_id": "header", "count": 1},
    {"kind": "kpi_row", "component_id": "kpis", "count": 1, "design_hint": "highlight Revenue",
     "content_data": {"kpi_labels": ["Revenue", "Margin", "Churn"], "kpi_values": ["$4.2M", "31%", "2.1%"]}},
    {"kind": "chart", "component_id": "trend", "count": 1, "chart_type": "line",
     "content_data": {"chart_labels": ["Q1", "Q2"], "chart_series": [{"name": "Revenue", "values": [3.7, 4.2]}]}},
    {"kind": "table", "component_id": "regions", "count": 1,
     "content_data": {"table_headers": ["Region", "Revenue"], "table_rows": [["EU", "$1.1M"]]}},
]}


def _system(plan: dict, theme: str = "corporate-slate", hook: str = "Growth is back.") -> str:
    th = resolve_theme(theme)
    state = {"slide_plans": [plan], "current_slide_index": 0, "contract": build_contract(plan, th),
             "theme_element": th["element"], "raw_request": "Q2 deck", "core_hook": hook}
    return _render_prompts(state)[0]


def test_two_slides_of_one_deck_share_everything_before_this_slide():
    a, b = _system(COVER), _system(DATA)
    assert a.count(MARK) == 1 and b.count(MARK) == 1
    head_a, head_b = a.split(MARK)[0], b.split(MARK)[0]
    assert head_a == head_b
    assert a != b   # the slides do differ, after the mark
    # the shared prefix is most of the prompt (OpenAI caches prefixes of 1024+ tokens)
    assert len(head_a) > 0.5 * len(b)


def test_per_slide_parts_come_after_the_mark():
    head, tail = _system(DATA).split(MARK)
    for per_slide in ("## SLIDE TYPE", "## ALLOWED NODES", "## ALLOWED ATTRIBUTES PER NODE", "## NODE HIERARCHY",
                      "## COMPONENT RECIPES", "## VISUAL-INTENT TRANSLATION", "## NOTES FOR THIS SLIDE"):
        assert per_slide not in head
        assert per_slide in tail
    # chart / table notes are per slide; the deck's own notes (theme, content rules) are in the prefix
    assert "Chart chartColors uses theme tokens" in tail and "Chart chartColors uses theme tokens" not in head
    assert "Theme palette:" in head and "Theme palette:" not in tail


def test_deck_parts_sit_after_the_static_rules():
    """Theme and narrative change per deck: they come after the static rules, so decks share those too."""
    a, b = _system(DATA), _system(DATA, theme="graphite-dark", hook="Costs are the story.")
    static = a.split("## THEME (reference only")[0]
    assert b.startswith(static) and "## LAYOUT GRAMMAR" in static and "## DESIGN ELEMENTS" in static


def test_every_note_is_drawn_once():
    th = resolve_theme("corporate-slate")
    c = build_contract(DATA, th)
    assert set(c["deck_notes"]) <= set(c["notes"]) and build_contract(COVER, th)["deck_notes"] == c["deck_notes"]
    system = _system(DATA)
    for note in c["notes"]:
        assert system.count(f"- {note}\n") == 1, note
