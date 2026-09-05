"""Tests for the context builder agent."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.agents.context_builder import (
    _select_nodes,
    _select_attributes,
    _select_notes,
    _select_example,
    _select_layout,
    _compress_example,
    _detect_components_from_text,
    build_contract,
    context_builder_node,
    _load_yaml,
)
from src.agents.style_resolver import DEFAULT_THEME, resolve_theme
from src.state import ComponentPlan, SlidePlan, initial_state

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "prompts" / "generator"


def _make_plan(kinds: list[str], density: str = "normal") -> SlidePlan:
    return SlidePlan(
        slide_index=0,
        components=[ComponentPlan(kind=k, count=1) for k in kinds],
        density=density,
        font_tier="standard",
        layout_hint="test layout",
        content_data={},
    )


# ── Node selection ───────────────────────────────────────────────────────────

def test_select_nodes_title_only():
    nodes = _select_nodes(["title"])
    assert "Slide" in nodes
    assert "Theme" in nodes
    assert "VStack" in nodes
    assert "Text" in nodes
    assert "Chart" not in nodes
    assert "Table" not in nodes


def test_select_nodes_chart():
    nodes = _select_nodes(["title", "chart"])
    assert "Chart" in nodes
    assert "ChartSeries" in nodes
    assert "ChartDataPoint" in nodes
    assert "HStack" in nodes
    assert "Table" not in nodes


def test_select_nodes_table():
    nodes = _select_nodes(["title", "table"])
    assert "Table" in nodes
    assert "Col" in nodes
    assert "Tr" in nodes
    assert "Td" in nodes


def test_select_nodes_timeline():
    nodes = _select_nodes(["title", "timeline"])
    assert "Timeline" in nodes
    assert "TimelineItem" in nodes


def test_select_nodes_layer():
    nodes = _select_nodes(["layer"])
    assert "Layer" in nodes
    assert "Line" in nodes
    assert "Arrow" in nodes


def test_select_nodes_maximal():
    kinds = ["title", "kpi_row", "chart", "bullet_list", "table", "caption"]
    nodes = _select_nodes(kinds)
    assert "Chart" in nodes
    assert "Table" in nodes
    assert "Ul" in nodes
    assert "HStack" in nodes
    assert len(nodes) >= 15


def test_select_nodes_always_includes_inlines():
    nodes = _select_nodes(["title"])
    assert "B" in nodes
    assert "I" in nodes
    assert "Span" in nodes


# ── Attribute assembly ───────────────────────────────────────────────────────

def test_attributes_vstack():
    nodes_yaml = _load_yaml("core/nodes.yaml")
    attrs = _select_attributes(["VStack"], nodes_yaml)
    assert "gap" in attrs["VStack"]
    assert "alignItems" in attrs["VStack"]
    assert "w" in attrs["VStack"]


def test_attributes_text():
    nodes_yaml = _load_yaml("core/nodes.yaml")
    attrs = _select_attributes(["Text"], nodes_yaml)
    assert "fontSize" in attrs["Text"]
    assert "color" in attrs["Text"]
    assert "bold" in attrs["Text"]
    assert "w" in attrs["Text"]


def test_attributes_chart():
    nodes_yaml = _load_yaml("core/nodes.yaml")
    attrs = _select_attributes(["Chart"], nodes_yaml)
    assert "chartType" in attrs["Chart"]
    assert "w" in attrs["Chart"]


def test_attributes_skip_structural():
    nodes_yaml = _load_yaml("core/nodes.yaml")
    attrs = _select_attributes(["Slide", "Theme", "Text"], nodes_yaml)
    assert "Slide" not in attrs
    assert "Theme" not in attrs
    assert "Text" in attrs


def test_attributes_no_box_on_inline():
    nodes_yaml = _load_yaml("core/nodes.yaml")
    attrs = _select_attributes(["B", "Span"], nodes_yaml)
    assert "w" not in attrs.get("B", [])
    assert "fontSize" in attrs.get("Span", [])


# ── Notes selection ──────────────────────────────────────────────────────────

def test_notes_always_includes_translations():
    validation = _load_yaml("core/validation.yaml")
    text_yaml = _load_yaml("components/text.yaml")
    notes = _select_notes(["title"], validation, text_yaml, {}, {"name": "test", "mode": "light"})
    translation_notes = [n for n in notes if "NOT " in n and " -> " in n]
    assert len(translation_notes) > 5


def test_notes_includes_chart_guidance():
    validation = _load_yaml("core/validation.yaml")
    text_yaml = _load_yaml("components/text.yaml")
    chart_yaml = _load_yaml("components/chart.yaml")
    notes = _select_notes(
        ["chart"], validation, text_yaml,
        {"chart": chart_yaml},
        {"name": "test", "mode": "light", "chart_colors_json": '["2563EB"]'},
    )
    chart_notes = [n for n in notes if "chartColors" in n]
    assert len(chart_notes) >= 1


def test_notes_includes_table_guidance():
    validation = _load_yaml("core/validation.yaml")
    text_yaml = _load_yaml("components/text.yaml")
    notes = _select_notes(
        ["table"], validation, text_yaml, {},
        {"name": "test", "mode": "light"},
    )
    table_notes = [n for n in notes if "Td" in n]
    assert len(table_notes) >= 1


def test_notes_dark_theme_chart_wrapping():
    validation = _load_yaml("core/validation.yaml")
    text_yaml = _load_yaml("components/text.yaml")
    notes = _select_notes(
        ["chart"], validation, text_yaml, {},
        {"name": "graphite-dark", "mode": "dark", "is_dark": True, "chart_colors_json": "[]"},
    )
    dark_notes = [n for n in notes if "DARK theme" in n]
    assert len(dark_notes) == 1


# ── Example selection ────────────────────────────────────────────────────────

def test_example_chart():
    ex = _select_example(["chart"])
    assert "<Chart" in ex or "Chart" in ex


def test_example_kpi():
    ex = _select_example(["kpi_row"])
    assert "<Theme" in ex or "Theme" in ex


def test_example_fallback():
    ex = _select_example(["title"])
    assert len(ex) > 0


def test_compress_example():
    long_xml = "\n".join([f'<Td>Row {i}</Td>' for i in range(30)])
    compressed = _compress_example(long_xml, max_lines=10)
    assert "..." in compressed
    assert len(compressed.split("\n")) < len(long_xml.split("\n"))


# ── Layout selection ─────────────────────────────────────────────────────────

def test_layout_chart_table():
    layout = _select_layout(["chart", "table"])
    assert len(layout) > 0


def test_layout_kpi():
    layout = _select_layout(["kpi_row"])
    assert len(layout) > 0


def test_layout_timeline():
    layout = _select_layout(["timeline"])
    assert len(layout) > 0


# ── Full contract build ─────────────────────────────────────────────────────

def test_build_contract_text():
    plan = _make_plan(["title", "narrative"])
    contract = build_contract(plan, DEFAULT_THEME)
    assert "VStack" in contract["allowed_nodes"]
    assert "Text" in contract["allowed_nodes"]
    assert contract["density_tier"] == "standard"
    assert len(contract["forbidden_tags"]) > 5


def test_build_contract_maximal():
    plan = _make_plan(
        ["title", "kpi_row", "chart", "bullet_list", "table", "caption"],
        density="tight_fit",
    )
    contract = build_contract(plan, DEFAULT_THEME)
    assert "Chart" in contract["allowed_nodes"]
    assert "Table" in contract["allowed_nodes"]
    assert "Ul" in contract["allowed_nodes"]
    assert contract["density_tier"] == "dense"
    assert len(contract["notes"]) > 10


def test_build_contract_sparse():
    plan = _make_plan(["title"], density="sparse")
    contract = build_contract(plan, DEFAULT_THEME)
    assert contract["density_tier"] == "minimal"


# ── Prompt rendering + token counting ────────────────────────────────────────

def _render_system_prompt(contract: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("system.j2").render(**contract)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def test_prompt_minimal_tier():
    plan = _make_plan(["title", "narrative"], density="sparse")
    contract = build_contract(plan, DEFAULT_THEME)
    prompt = _render_system_prompt(contract)
    tokens = _estimate_tokens(prompt)
    assert tokens < 3000, f"Minimal tier too large: {tokens} tokens"
    assert "ALLOWED ATTRIBUTES PER NODE" not in prompt
    assert "SHRINK CHECKLIST" not in prompt


def test_prompt_standard_tier():
    plan = _make_plan(["title", "chart", "table"], density="normal")
    contract = build_contract(plan, DEFAULT_THEME)
    prompt = _render_system_prompt(contract)
    tokens = _estimate_tokens(prompt)
    assert tokens < 5000, f"Standard tier too large: {tokens} tokens"
    assert "ALLOWED ATTRIBUTES PER NODE" in prompt
    assert "SHRINK CHECKLIST" not in prompt


def test_prompt_dense_tier_under_6k():
    """The key acceptance test: maximal-density must stay under 6K tokens."""
    plan = _make_plan(
        ["title", "kpi_row", "chart", "bullet_list", "table", "caption"],
        density="tight_fit",
    )
    contract = build_contract(plan, DEFAULT_THEME)
    prompt = _render_system_prompt(contract)
    tokens = _estimate_tokens(prompt)
    assert tokens < 6000, f"Dense tier too large: {tokens} tokens (target: <6000)"
    assert "ALLOWED ATTRIBUTES PER NODE" in prompt
    assert "SHRINK CHECKLIST" in prompt
    assert "NOTES" in prompt


def test_prompt_always_has_critical_rules():
    for density in ("sparse", "normal", "tight_fit"):
        plan = _make_plan(["title"], density=density)
        contract = build_contract(plan, DEFAULT_THEME)
        prompt = _render_system_prompt(contract)
        assert "CRITICAL RULES" in prompt
        assert "margin" in prompt.lower()
        assert "FORBIDDEN" in prompt


# ── LangGraph node test ──────────────────────────────────────────────────────

def test_context_builder_node_runs():
    state = initial_state(run_id="cb1", raw_request="test")
    state["slide_plans"] = [_make_plan(["title", "chart"])]
    result = context_builder_node(state)
    assert "contract" in result
    assert result["contract"]["allowed_nodes"]
    assert "Chart" in result["contract"]["allowed_nodes"]
    assert "<Theme" in result["contract"]["theme_element"]


def test_context_builder_node_empty_plans():
    state = initial_state(run_id="cb2", raw_request="test")
    state["slide_plans"] = []
    result = context_builder_node(state)
    assert result["contract"] != {}
    assert "allowed_nodes" in result["contract"]
    assert "Text" in result["contract"]["allowed_nodes"]
    assert "<Theme" in result["contract"]["theme_element"]


# ── Intent detection tests ──────────────────────────────────────────────────

def test_detect_components_chart():
    kinds = _detect_components_from_text("Create a bar chart of revenue")
    assert "chart" in kinds


def test_detect_components_table_and_kpi():
    kinds = _detect_components_from_text("Show a table with KPI metrics")
    assert "table" in kinds
    assert "kpi_row" in kinds


def test_detect_components_timeline():
    kinds = _detect_components_from_text("Create a product roadmap with milestones")
    assert "timeline" in kinds


def test_detect_components_no_match():
    kinds = _detect_components_from_text("Create a simple title slide")
    assert kinds == []


def test_detect_components_multiple():
    kinds = _detect_components_from_text(
        "Create a presentation with chart table and kpi cards"
    )
    assert "chart" in kinds
    assert "table" in kinds
    assert "kpi_row" in kinds


def test_context_builder_uses_test_case_components():
    state = initial_state(run_id="cb3", raw_request="test")
    state["slide_plans"] = []
    state["test_case"] = {"components": ["title", "chart", "table"]}
    result = context_builder_node(state)
    assert "Chart" in result["contract"]["allowed_nodes"]
    assert "Table" in result["contract"]["allowed_nodes"]


def test_context_builder_uses_intent_detection():
    state = initial_state(
        run_id="cb4",
        raw_request="Create a dashboard with kpi cards and a chart",
    )
    state["slide_plans"] = []
    result = context_builder_node(state)
    assert "Chart" in result["contract"]["allowed_nodes"]
    assert "HStack" in result["contract"]["allowed_nodes"]
