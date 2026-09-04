"""Tests for the planner agent with mocked LLM responses."""

from unittest.mock import MagicMock, patch

from src.agents.planner import planner_node, _render_system, _render_user, _slide_to_state
from src.agents.planner_schema import PlannerComponent, PlannerOutput, PlannerSlide
from src.state import initial_state


def _mock_planner_output(*slides: PlannerSlide) -> PlannerOutput:
    return PlannerOutput(slides=list(slides))


def _make_structured_llm(output: PlannerOutput):
    """Create a mock that mimics llm.with_structured_output().invoke()."""
    structured = MagicMock()
    structured.invoke.return_value = output
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


# ── Template rendering tests ────────────────────────────────────────────────

def test_render_system_not_empty():
    text = _render_system()
    assert "Component Vocabulary" in text
    assert "Density" in text
    assert len(text) > 200


def test_render_user_basic():
    state = initial_state(run_id="t1", raw_request="A simple title slide")
    text = _render_user(state)
    assert "A simple title slide" in text
    assert "SUPPLIED CONTENT" not in text


def test_render_user_with_supplied_content():
    state = initial_state(
        run_id="t2",
        raw_request="KPI dashboard",
        supplied_content={"title": "Q3 Metrics", "kpi_labels": ["ARR", "NRR"]},
    )
    text = _render_user(state)
    assert "Q3 Metrics" in text
    assert "kpi_labels" in text
    assert "SUPPLIED CONTENT" in text


def test_render_user_with_theme():
    state = initial_state(
        run_id="t3",
        raw_request="A slide",
        theme_name="corporate-slate",
    )
    state["theme_name"] = "corporate-slate"
    text = _render_user(state)
    assert "corporate-slate" in text


def test_render_user_with_components_hint():
    state = initial_state(run_id="t4", raw_request="A slide")
    state["test_case"] = {"components": ["title", "chart", "table"]}
    text = _render_user(state)
    assert "title, chart, table" in text


# ── Conversion tests ────────────────────────────────────────────────────────

def test_slide_to_state_basic():
    slide = PlannerSlide(
        components=[
            PlannerComponent(kind="title", count=1, content_summary="Main title"),
            PlannerComponent(kind="narrative", count=1, content_summary="Body"),
        ],
        density="normal",
        font_tier="standard",
        layout_hint="Title at top, text below",
    )
    result = _slide_to_state(0, slide)
    assert result["slide_index"] == 0
    assert result["density"] == "normal"
    assert result["font_tier"] == "standard"
    assert len(result["components"]) == 2
    assert result["components"][0]["kind"] == "title"
    assert result["components"][1]["content_summary"] == "Body"


def test_slide_to_state_chart_fields():
    slide = PlannerSlide(
        components=[
            PlannerComponent(
                kind="chart", count=6, chart_type="bar",
                series_count=3, content_summary="Revenue by quarter"
            ),
        ],
        density="normal",
        font_tier="standard",
        layout_hint="Chart centered",
    )
    result = _slide_to_state(0, slide)
    comp = result["components"][0]
    assert comp["kind"] == "chart"
    assert comp["chart_type"] == "bar"
    assert comp["series_count"] == 3
    assert comp["count"] == 6


def test_slide_to_state_table_fields():
    slide = PlannerSlide(
        components=[
            PlannerComponent(
                kind="table", count=1, columns=4, rows=3,
                content_summary="Segment breakdown"
            ),
        ],
        density="dense",
        font_tier="compact",
        layout_hint="Table fills width",
    )
    result = _slide_to_state(0, slide)
    comp = result["components"][0]
    assert comp["columns"] == 4
    assert comp["rows"] == 3


def test_slide_to_state_omits_zero_fields():
    slide = PlannerSlide(
        components=[
            PlannerComponent(kind="title", count=1),
        ],
        density="sparse",
        font_tier="display",
        layout_hint="Centered title",
    )
    result = _slide_to_state(0, slide)
    comp = result["components"][0]
    assert "chart_type" not in comp
    assert "series_count" not in comp
    assert "columns" not in comp


# ── Planner node tests (mocked LLM) ────────────────────────────────────────

@patch("src.agents.planner.get_llm")
def test_planner_text_only(mock_get_llm):
    output = _mock_planner_output(
        PlannerSlide(
            components=[
                PlannerComponent(kind="title", count=1, content_summary="Title"),
                PlannerComponent(kind="narrative", count=1, content_summary="Body text"),
            ],
            density="sparse",
            font_tier="display",
            layout_hint="Title centered, text below",
        )
    )
    mock_get_llm.return_value = _make_structured_llm(output).with_structured_output.return_value
    mock_get_llm.return_value = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    state = initial_state(run_id="p1", raw_request="A simple title slide", deck_min_threshold=3)
    result = planner_node(state)

    assert result["mode"] == "single"
    assert result["deck_plan"] is None
    assert len(result["slide_plans"]) == 1
    plan = result["slide_plans"][0]
    assert plan["density"] == "sparse"
    assert plan["font_tier"] == "display"
    assert len(plan["components"]) == 2
    assert plan["components"][0]["kind"] == "title"


@patch("src.agents.planner.get_llm")
def test_planner_kpi_row(mock_get_llm):
    output = _mock_planner_output(
        PlannerSlide(
            components=[
                PlannerComponent(kind="title", count=1, content_summary="Key Metrics"),
                PlannerComponent(
                    kind="kpi_row", count=4,
                    content_summary="ARR, NRR, Gross Margin, Customer Count"
                ),
            ],
            density="normal",
            font_tier="standard",
            layout_hint="Title at top, 4 KPI tiles in horizontal row below",
            content_data={
                "title": "Key Metrics - Q3 FY26",
                "kpi_labels": ["ARR", "NRR", "Gross Margin", "Customer Count"],
            },
        )
    )
    mock_get_llm.return_value = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    state = initial_state(
        run_id="p2",
        raw_request="KPI row slide for Q3 FY26",
        supplied_content={"title": "Key Metrics - Q3 FY26", "kpi_labels": ["ARR", "NRR", "Gross Margin", "Customer Count"]},
    )
    result = planner_node(state)

    plan = result["slide_plans"][0]
    assert plan["density"] == "normal"
    kpi = [c for c in plan["components"] if c["kind"] == "kpi_row"][0]
    assert kpi["count"] == 4
    assert plan["content_data"]["title"] == "Key Metrics - Q3 FY26"


@patch("src.agents.planner.get_llm")
def test_planner_maximal_density(mock_get_llm):
    output = _mock_planner_output(
        PlannerSlide(
            components=[
                PlannerComponent(kind="title", count=1, content_summary="Q3 FY26 Operating Review"),
                PlannerComponent(kind="kpi_row", count=4, content_summary="ARR, NRR, Margin, CAC"),
                PlannerComponent(kind="chart", count=6, chart_type="bar", series_count=1, content_summary="Revenue by quarter"),
                PlannerComponent(kind="chart", count=6, chart_type="line", series_count=1, content_summary="Margin trend"),
                PlannerComponent(kind="bullet_list", items=5, content_summary="Key takeaways"),
                PlannerComponent(kind="table", columns=4, rows=4, content_summary="Segment breakdown"),
                PlannerComponent(kind="caption", count=1, content_summary="Footnote"),
            ],
            density="tight_fit",
            font_tier="micro",
            layout_hint="Title+kicker at top, 4 KPI tiles below, then 3 columns (bar chart | line chart | bullet list), table spanning full width below, footnote at bottom",
            content_data={
                "kicker": "Q3 FY26 OPERATING REVIEW",
                "title": "The Whole Quarter, One View",
            },
        )
    )
    mock_get_llm.return_value = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    state = initial_state(
        run_id="p3",
        raw_request="An extremely dense Q3 FY26 operating-review slide",
        supplied_content={"kicker": "Q3 FY26 OPERATING REVIEW", "title": "The Whole Quarter, One View"},
    )
    result = planner_node(state)

    plan = result["slide_plans"][0]
    assert plan["density"] == "tight_fit"
    assert plan["font_tier"] == "micro"
    kinds = [c["kind"] for c in plan["components"]]
    assert "kpi_row" in kinds
    assert "chart" in kinds
    assert "table" in kinds
    assert "bullet_list" in kinds
    assert "caption" in kinds
    charts = [c for c in plan["components"] if c["kind"] == "chart"]
    assert len(charts) == 2


@patch("src.agents.planner.get_llm")
def test_planner_chart_and_table(mock_get_llm):
    output = _mock_planner_output(
        PlannerSlide(
            components=[
                PlannerComponent(kind="title", count=1, content_summary="Bookings Performance"),
                PlannerComponent(kind="chart", count=4, chart_type="bar", series_count=1, content_summary="Bookings by quarter"),
                PlannerComponent(kind="table", columns=4, rows=4, content_summary="Quarterly metrics"),
            ],
            density="normal",
            font_tier="standard",
            layout_hint="Title at top, chart on left and table on right side by side",
        )
    )
    mock_get_llm.return_value = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    state = initial_state(
        run_id="p4",
        raw_request="Two-column slide with bar chart and table",
        supplied_content={"chart_type": "bar", "quarters": ["Q4", "Q1", "Q2", "Q3"]},
    )
    result = planner_node(state)

    plan = result["slide_plans"][0]
    assert plan["density"] == "normal"
    kinds = [c["kind"] for c in plan["components"]]
    assert "chart" in kinds
    assert "table" in kinds
    assert "side by side" in plan["layout_hint"]


@patch("src.agents.planner.get_llm")
def test_planner_multi_slide_deck_mode(mock_get_llm):
    output = _mock_planner_output(
        PlannerSlide(
            components=[PlannerComponent(kind="title", count=1)],
            density="sparse", font_tier="display",
            layout_hint="Cover slide",
        ),
        PlannerSlide(
            components=[PlannerComponent(kind="kpi_row", count=4)],
            density="normal", font_tier="standard",
            layout_hint="KPI dashboard",
        ),
        PlannerSlide(
            components=[PlannerComponent(kind="chart", chart_type="bar", count=4)],
            density="normal", font_tier="standard",
            layout_hint="Revenue chart",
        ),
    )
    mock_get_llm.return_value = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    state = initial_state(
        run_id="p5",
        raw_request="A 3-slide deck with cover, KPIs, and revenue chart",
        deck_min_threshold=3,
    )
    result = planner_node(state)

    assert result["mode"] == "deck"
    assert result["deck_plan"] is not None
    assert result["deck_plan"]["slide_count"] == 3
    assert len(result["slide_plans"]) == 3
    assert result["slide_plans"][0]["slide_index"] == 0
    assert result["slide_plans"][2]["slide_index"] == 2


@patch("src.agents.planner.get_llm")
def test_planner_single_slide_below_threshold(mock_get_llm):
    output = _mock_planner_output(
        PlannerSlide(
            components=[PlannerComponent(kind="title", count=1)],
            density="sparse", font_tier="display",
            layout_hint="Simple title",
        ),
    )
    mock_get_llm.return_value = MagicMock()
    mock_get_llm.return_value.with_structured_output.return_value.invoke.return_value = output

    state = initial_state(run_id="p6", raw_request="Title slide", deck_min_threshold=3)
    result = planner_node(state)

    assert result["mode"] == "single"
    assert result["deck_plan"] is None
