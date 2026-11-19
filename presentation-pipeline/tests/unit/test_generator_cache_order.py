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


MIXED = {"slide_index": 2, "slide_type": "content", "slide_title": "How an order flows", "components": [
    {"kind": "title", "component_id": "header", "count": 1},
    {"kind": "chart", "component_id": "trend", "count": 1, "chart_type": "bar",
     "content_data": {"chart_labels": ["Q1", "Q2"], "chart_series": [{"name": "Orders", "values": [3, 4]}]}},
    {"kind": "flow", "component_id": "steps", "count": 1, "design_hint": "accent border on the flow card",
     "content_data": {"flow_steps": ["Order", "Pack", "Ship"]}},
    {"kind": "narrative", "component_id": "why", "count": 1, "content_data": {"text": "Packing is the bottleneck."}},
]}


def test_per_slide_parts_come_after_the_mark():
    head, tail = _system(MIXED).split(MARK)
    for per_slide in ("## SLIDE TYPE", "## ALLOWED NODES", "## ALLOWED ATTRIBUTES PER NODE", "## NODE HIERARCHY",
                      "## CODE-DRAWN NODES", "## CHARTS (code draws them", "## COMPONENT SIZING",
                      "## COMPONENT RECIPES", "## VISUAL-INTENT TRANSLATION", "## NOTES FOR THIS SLIDE"):
        assert per_slide not in head
        assert per_slide in tail
    # a hand-drawn kind's notes are per slide; the deck's own notes (theme, content rules) are in the prefix
    assert "FlowConnection from/to" in tail and "FlowConnection from/to" not in head
    assert "Theme palette:" in head and "Theme palette:" not in tail


def test_only_this_slides_kinds_reach_the_prompt():
    """A code-drawn kind's section, sizing and tags reach a slide's prompt only when its plan has one; a kind code
    draws never gets the rules for drawing it by hand (2026-11-19)."""
    cover, data, mixed = _system(COVER), _system(DATA), _system(MIXED)
    for section in ("## CODE-DRAWN NODES", "## CHARTS", "## TIMELINES", "## KPI TILES", "## TABLES", "## BULLET LISTS",
                    "## COMPONENT SIZING"):
        assert section not in cover, section
    assert "## KPI TILES (code" in data and "## CHARTS" in data and "## TABLES" in data
    assert "## TIMELINES" not in data and "## BULLET LISTS" not in data and "CardGrid" not in data
    assert "## CHARTS" in mixed and "## TABLES" not in mixed and "## KPI TILES" not in mixed
    # chart and table are drawn by code on DATA: no native children or hand-drawing rules for them
    tail = data.split(MARK)[1]
    for prohibition in ("no ChartSeries / ChartDataPoint", "No <Tr>, <Td> or fontSize"):   # the node sections' own
        tail = tail.replace(prohibition, "")
    for hand in ("ChartSeries", "<Col>", "<Td>", "<Tr ", "defaultRowHeight", "TimelineItem",
                 "Chart chartColors uses theme tokens"):
        assert hand not in tail, hand
    # the hand-drawn flow on MIXED gets its sizing and the diagram rule
    assert 'Flow: h="max" minH="200"' in mixed and "Direction and box go together" in mixed


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
