"""Tests for the hierarchical planning pipeline.

Replaces the old monolithic planner tests. Tests now cover:
- outline_planner_node (mocked LLM)
- _planner_slide_to_state / plan_single_slide helpers
- compute_provenance from settings_mapper
"""

from unittest.mock import MagicMock, patch

from src.agents.outline_planner_schema import OutlinePlannerOutput, OutlineSlide
from src.agents.plan_reviewer_schema import PlanReviewerOutput, PlanReviewIssue
from src.agents.planner_schema import PlannerComponent, PlannerSlide
from src.agents.settings_mapper import compute_provenance, settings_to_constraints, DeckSettings
from src.agents.slide_component_planner import _planner_slide_to_state
from src.state import SlidePlan, initial_state


def _mock_outline_output(
    *slide_overrides: dict,
    deck_title: str = "Test Deck",
    core_hook: str = "Test narrative anchor.",
) -> OutlinePlannerOutput:
    slides = []
    for i, kwargs in enumerate(slide_overrides):
        slides.append(OutlineSlide(
            slide_index=kwargs.get("slide_index", i),
            slide_title=kwargs.get("slide_title", f"Slide {i+1}"),
            slide_type=kwargs.get("slide_type", "content"),
            section=kwargs.get("section", ""),
            narrative_role=kwargs.get("narrative_role", ""),
            key_messages=kwargs.get("key_messages", ["Message 1"]),
            data_anchors=kwargs.get("data_anchors", []),
            layout_intent=kwargs.get("layout_intent", ""),
            suggested_components=kwargs.get("suggested_components", ["title"]),
        ))
    return OutlinePlannerOutput(deck_title=deck_title, core_hook=core_hook, slides=slides)


def _make_structured_llm(output):
    structured = MagicMock()
    structured.invoke.return_value = output
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


# ── _planner_slide_to_state tests ──────────────────────────────────────────

def test_planner_slide_to_state_basic():
    slide = PlannerSlide(
        slide_type="content",
        components=[
            PlannerComponent(kind="title", count=1, content_summary="Main title"),
            PlannerComponent(kind="narrative", count=1, content_summary="Body"),
        ],
        density="normal",
        font_tier="standard",
        layout_hint="Title at top, text below",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["slide_index"] == 0
    assert result["slide_type"] == "content"
    assert result["density"] == "normal"
    assert result["font_tier"] == "standard"
    assert len(result["components"]) == 2
    assert result["components"][0]["kind"] == "title"
    assert result["components"][1]["content_summary"] == "Body"


def test_planner_slide_to_state_chart_fields():
    slide = PlannerSlide(
        slide_type="data",
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
    result = _planner_slide_to_state(0, slide)
    comp = result["components"][0]
    assert comp["kind"] == "chart"
    assert comp["chart_type"] == "bar"
    assert comp["series_count"] == 3
    assert comp["count"] == 6


def test_planner_slide_to_state_table_fields():
    slide = PlannerSlide(
        slide_type="data",
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
    result = _planner_slide_to_state(0, slide)
    comp = result["components"][0]
    assert comp["columns"] == 4
    assert comp["rows"] == 3


def test_planner_slide_to_state_omits_zero_fields():
    slide = PlannerSlide(
        slide_type="cover",
        components=[
            PlannerComponent(kind="title", count=1),
        ],
        density="sparse",
        font_tier="display",
        layout_hint="Centered title",
    )
    result = _planner_slide_to_state(0, slide)
    comp = result["components"][0]
    assert "chart_type" not in comp
    assert "series_count" not in comp
    assert "columns" not in comp


# ── outline_planner_node tests (mocked LLM) ────────────────────────────────

@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_single_slide(mock_get_llm):
    output = _mock_outline_output(
        {"slide_type": "cover", "slide_title": "Company Overview", "key_messages": ["We are great"]},
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    state = initial_state(run_id="op1", raw_request="A company overview slide")
    result = outline_planner_node(state)

    outline = result["outline_plan"]
    assert outline["deck_title"] == "Test Deck"
    assert outline["core_hook"] == "Test narrative anchor."
    assert len(outline["slides"]) == 1
    assert outline["slides"][0]["slide_type"] == "cover"
    assert outline["slides"][0]["key_messages"] == ["We are great"]


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_multi_slide(mock_get_llm):
    output = _mock_outline_output(
        {"slide_type": "cover", "slide_title": "Cover"},
        {"slide_type": "content", "slide_title": "Problem", "key_messages": ["Market is broken"], "data_anchors": ["$50B opportunity"]},
        {"slide_type": "data", "slide_title": "Metrics", "key_messages": ["ARR grew 140% YoY"], "data_anchors": ["ARR: $12M"]},
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    state = initial_state(run_id="op2", raw_request="Investor pitch deck", deck_min_threshold=3)
    result = outline_planner_node(state)

    outline = result["outline_plan"]
    assert len(outline["slides"]) == 3
    assert outline["slides"][1]["data_anchors"] == ["$50B opportunity"]
    assert outline["slides"][2]["key_messages"] == ["ARR grew 140% YoY"]


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_with_deck_settings(mock_get_llm):
    output = _mock_outline_output(
        {"slide_type": "cover", "slide_title": "Cover"},
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    state = initial_state(
        run_id="op3",
        raw_request="Board deck",
        deck_settings={
            "text_mode": "condense",
            "amount_of_text": "minimal",
            "tone": ["Executive"],
            "write_for": ["Board"],
            "slide_count": "6-10",
        },
    )
    result = outline_planner_node(state)
    assert "outline_plan" in result
    assert result["outline_plan"]["slides"][0]["slide_type"] == "cover"


# ── compute_provenance tests ───────────────────────────────────────────────

def test_compute_provenance_all_sample():
    content = {"title": "Q3", "subtitle": "Revenue", "chart_data": [1, 2]}
    prov = compute_provenance(content, {})
    assert prov == {"title": "sample", "subtitle": "sample", "chart_data": "sample"}


def test_compute_provenance_all_user():
    content = {"title": "Q3", "kpi_labels": ["ARR"]}
    supplied = {"title": "Q3", "kpi_labels": ["ARR"]}
    prov = compute_provenance(content, supplied)
    assert prov == {"title": "user", "kpi_labels": "user"}


def test_compute_provenance_mixed():
    content = {"title": "Q3", "subtitle": "Revenue", "kpi_labels": ["ARR"]}
    supplied = {"title": "Q3", "kpi_labels": ["ARR"]}
    prov = compute_provenance(content, supplied)
    assert prov["title"] == "user"
    assert prov["kpi_labels"] == "user"
    assert prov["subtitle"] == "sample"


def test_compute_provenance_empty_content():
    prov = compute_provenance({}, {"title": "Q3"})
    assert prov == {}


def test_planner_slide_to_state_provenance_with_supplied():
    slide = PlannerSlide(
        slide_type="data",
        components=[PlannerComponent(kind="title", count=1)],
        density="normal", font_tier="standard",
        layout_hint="Title at top",
        content_data_json='{"title": "Q3 Metrics", "chart_data": [1, 2, 3]}',
    )
    result = _planner_slide_to_state(0, slide, supplied_content={"title": "Q3 Metrics"})
    assert result["data_provenance"]["title"] == "user"
    assert result["data_provenance"]["chart_data"] == "sample"


def test_planner_slide_to_state_provenance_no_supplied():
    slide = PlannerSlide(
        slide_type="content",
        components=[PlannerComponent(kind="title", count=1)],
        density="normal", font_tier="standard",
        layout_hint="Title at top",
        content_data_json='{"title": "Generated Title"}',
    )
    result = _planner_slide_to_state(0, slide)
    assert result["data_provenance"]["title"] == "sample"


# ── DeckSettings constraint mapping tests ─────────────────────────────────

def test_settings_to_constraints_minimal():
    s = DeckSettings(amount_of_text="minimal", text_mode="generate", slide_count="3-5")
    c = settings_to_constraints(s)
    assert c["density"] == "sparse"
    assert c["key_messages_per_slide"] == "1"
    assert c["deck_min_threshold"] == 4


def test_settings_to_constraints_extensive():
    s = DeckSettings(amount_of_text="extensive", text_mode="preserve", slide_count="10-15")
    c = settings_to_constraints(s)
    assert c["density"] == "tight_fit"
    assert c["key_messages_per_slide"] == "4-6"
    assert c["provenance_rule"] == "llm_preserves_verbatim"
    assert c["deck_min_threshold"] == 12


# Local import needed for the outline node tests
from src.agents.outline_planner import outline_planner_node
