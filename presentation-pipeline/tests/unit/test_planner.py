"""Tests for the hierarchical planning pipeline.

Replaces the old monolithic planner tests. Tests now cover:
- outline_planner_node (mocked LLM)
- _planner_slide_to_state / plan_single_slide helpers
- compute_provenance from settings_mapper
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.outline_planner_schema import OutlinePlannerOutput, OutlineSlide
from src.agents.plan_reviewer_schema import PlanReviewerOutput, PlanReviewIssue
from src.agents.planner_schema import PlannerComponent, PlannerSlide
from src.agents.outline_planner import stated_slide_count
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
            section=kwargs.get("section", ""),
            narrative_role=kwargs.get("narrative_role", ""),
            key_messages=kwargs.get("key_messages", ["Message 1"]),
            visual_emphasis=kwargs.get("visual_emphasis", ""),
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
            PlannerComponent(component_id="main_title", kind="title", count=1, content_summary="Main title"),
            PlannerComponent(component_id="body_text", kind="narrative", count=1, content_summary="Body"),
        ],
        layout_hint="Title at top, text below",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["slide_index"] == 0
    assert result["slide_type"] == "content"
    assert len(result["components"]) == 2
    assert result["components"][0]["kind"] == "title"
    assert result["components"][0]["component_id"] == "main_title"
    assert result["components"][1]["content_summary"] == "Body"


def test_planner_slide_to_state_chart_fields():
    slide = PlannerSlide(
        slide_type="data",
        components=[
            PlannerComponent(
                component_id="revenue_chart",
                kind="chart", count=6, chart_type="bar",
                series_count=3, content_summary="Revenue by quarter"
            ),
        ],
        layout_hint="Chart centered",
    )
    result = _planner_slide_to_state(0, slide)
    comp = result["components"][0]
    assert comp["kind"] == "chart"
    assert comp["chart_type"] == "bar"
    assert comp["series_count"] == 3
    assert comp["count"] == 6
    assert comp["component_id"] == "revenue_chart"


def test_planner_slide_to_state_table_fields():
    slide = PlannerSlide(
        slide_type="data",
        components=[
            PlannerComponent(
                component_id="segment_table",
                kind="table", count=1, columns=4, rows=3,
                content_summary="Segment breakdown"
            ),
        ],
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
            PlannerComponent(component_id="hero_title", kind="title", count=1),
        ],
        layout_hint="Centered title",
    )
    result = _planner_slide_to_state(0, slide)
    comp = result["components"][0]
    assert "chart_type" not in comp
    assert "series_count" not in comp
    assert "columns" not in comp


def test_planner_slide_to_state_per_component_content_data():
    """Each component's content_data_json is parsed into its own content_data dict."""
    slide = PlannerSlide(
        slide_type="data",
        components=[
            PlannerComponent(
                component_id="kpi_metrics",
                kind="kpi_row", count=3,
                content_data_json='{"kpi_labels": ["ARR", "NRR"], "kpi_values": ["$42.8M", "114%"]}',
            ),
            PlannerComponent(
                component_id="revenue_chart",
                kind="chart", count=1, chart_type="bar",
                content_data_json='{"chart_labels": ["Q1", "Q2"], "chart_values": [28.4, 31.2]}',
            ),
        ],
        layout_hint="KPIs on top, chart below",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["components"][0]["content_data"]["kpi_labels"] == ["ARR", "NRR"]
    assert result["components"][1]["content_data"]["chart_labels"] == ["Q1", "Q2"]
    # Slide-level content_data is merged from all components
    assert "kpi_labels" in result["content_data"]
    assert "chart_labels" in result["content_data"]


def test_planner_slide_to_state_copies_weight():
    slide = PlannerSlide(
        slide_type="data",
        components=[
            PlannerComponent(
                component_id="revenue_chart", kind="chart", count=1,
                chart_type="bar", weight="hero",
                content_summary="Revenue by quarter",
            ),
            PlannerComponent(
                component_id="segment_table", kind="table", count=1,
                columns=3, rows=4, weight="supporting",
                content_summary="Segment breakdown",
            ),
        ],
        layout_hint="Chart is primary, table is supporting",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["components"][0]["weight"] == "hero"
    assert result["components"][1]["weight"] == "supporting"


def test_planner_slide_to_state_default_weight():
    slide = PlannerSlide(
        slide_type="content",
        components=[
            PlannerComponent(component_id="body", kind="narrative", count=1),
        ],
        layout_hint="Body text",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["components"][0].get("weight") == "peer"


def test_planner_slide_to_state_copies_design_hint():
    slide = PlannerSlide(
        slide_type="data",
        components=[
            PlannerComponent(
                component_id="hero_chart", kind="chart", count=1,
                chart_type="bar",
                design_hint="emphasize Q4 value with accent color",
            ),
        ],
        layout_hint="Chart centered",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["components"][0]["design_hint"] == "emphasize Q4 value with accent color"


# ── outline_planner_node tests (mocked LLM) ────────────────────────────────

@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_single_slide(mock_get_llm):
    output = _mock_outline_output(
        {"slide_title": "Company Overview", "key_messages": ["We are great"]},
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    state = initial_state(run_id="op1", raw_request="A company overview slide")
    result = outline_planner_node(state)

    outline = result["outline_plan"]
    assert outline["deck_title"] == "Test Deck"
    assert outline["core_hook"] == "Test narrative anchor."
    assert len(outline["slides"]) == 1
    assert outline["slides"][0]["key_messages"] == ["We are great"]


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_multi_slide(mock_get_llm):
    output = _mock_outline_output(
        {"slide_title": "Cover", "key_messages": ["Welcome"]},
        {"slide_title": "Problem", "key_messages": ["Market is broken — $50B opportunity untapped"]},
        {"slide_title": "Metrics", "key_messages": ["ARR grew 140% YoY to $12M"]},
    )
    mock_get_llm.return_value = _make_structured_llm(output)

    state = initial_state(run_id="op2", raw_request="Investor pitch deck", deck_min_threshold=3)
    result = outline_planner_node(state)

    outline = result["outline_plan"]
    assert len(outline["slides"]) == 3
    assert "50B" in outline["slides"][1]["key_messages"][0]
    assert outline["slides"][2]["key_messages"] == ["ARR grew 140% YoY to $12M"]


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_with_deck_settings(mock_get_llm):
    output = _mock_outline_output(
        {"slide_title": "Cover", "key_messages": ["Board update Q3"]},
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


def _captured_user_prompt(mock_get_llm) -> str:
    structured = mock_get_llm.return_value.with_structured_output.return_value
    return structured.invoke.call_args[0][0][1].content


@pytest.mark.parametrize("request_text, expected", [
    ("Create a 6-SLIDE audit presentation", 6),
    ("Create a 14-slide deck, one slide per section below", 14),
    ("A five-slide pitch deck. Slide 1: cover. Slide 2: problem.", 5),
    ("Deck. Slide 1: cover. Slide 2: KPIs. Slide 3: plan.", 3),     # headings only
    ("One slide with four KPIs on a single 1280x720 slide", 1),
    ("A 1280x720 slide with a chart", None),
    ("Show our revenue trend", None),
    ("Either 6 slides or 8 slides", None),                          # conflicting counts
    ("Slide 1: cover. Slide 3: plan.", None),                        # headings with a gap
])
def test_stated_slide_count(request_text, expected):
    assert stated_slide_count(request_text) == expected


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_slide_count_from_request(mock_get_llm):
    mock_get_llm.return_value = _make_structured_llm(_mock_outline_output({}))
    state = initial_state(run_id="op4", raw_request="Create a 5-slide QBR deck")  # settings default = 8
    outline_planner_node(state)
    prompt = _captured_user_prompt(mock_get_llm)
    assert "TARGET DECK SIZE: 5 slides (the count the request states)." in prompt
    assert "EXACTLY 5 slides" in prompt


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_test_case_count_wins(mock_get_llm):
    mock_get_llm.return_value = _make_structured_llm(_mock_outline_output({}))
    state = initial_state(run_id="op5", raw_request="Create a 5-slide QBR deck")
    state["test_case"] = {"slide_count": 7}
    outline_planner_node(state)
    assert "TARGET DECK SIZE: 7 slides." in _captured_user_prompt(mock_get_llm)


@patch("src.agents.outline_planner.get_llm")
def test_outline_planner_header_reaches_slide_plan(mock_get_llm):
    output = OutlinePlannerOutput(deck_title="D", core_hook="H", slides=[OutlineSlide(
        slide_index=0, label="PLATFORM DEEP-DIVE", slide_title="Search carries sales",
        subtitle="₹1.32 Cr sales · 6.35x ROAS", narrative_role="r", key_messages=["m"],
        visual_emphasis="e",
    )])
    mock_get_llm.return_value = _make_structured_llm(output)
    outline_slide = outline_planner_node(initial_state(run_id="op6", raw_request="x"))["outline_plan"]["slides"][0]
    assert outline_slide["label"] == "PLATFORM DEEP-DIVE"
    assert outline_slide["subtitle"] == "₹1.32 Cr sales · 6.35x ROAS"

    plan = _planner_slide_to_state(
        0, PlannerSlide(slide_type="data", layout_hint="", components=[
            PlannerComponent(component_id="t", kind="title", count=1, content_summary="t")]),
        slide_title=outline_slide["slide_title"], label=outline_slide["label"],
        subtitle=outline_slide["subtitle"],
    )
    assert (plan["label"], plan["slide_title"], plan["subtitle"]) == (
        "PLATFORM DEEP-DIVE", "Search carries sales", "₹1.32 Cr sales · 6.35x ROAS")


def test_outline_prompts_have_no_invention_lines():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "src"
    texts = [
        (root / "prompts/outline_planner/system.j2").read_text(encoding="utf-8"),
        (root / "prompts/outline_planner/user.j2").read_text(encoding="utf-8"),
        (root / "prompts/outline_replanner/system.j2").read_text(encoding="utf-8"),
        str(OutlinePlannerOutput.model_json_schema()),
    ]
    for text in texts:
        assert "plausible" not in text and "$42.8M" not in text


def test_generator_prompts_draw_the_planned_header_and_invent_nothing():
    from src.agents.generator import _render_prompts
    plan = {"slide_title": "Search carries sales", "label": "DEEP-DIVE", "subtitle": "₹1.32 Cr · 6.35x",
            "slide_type": "data", "components": [{"kind": "table", "component_id": "t", "count": 1}]}
    for content_data in ({}, {"x": "1"}):
        plan["content_data"] = content_data
        system, user = _render_prompts({"slide_plans": [plan], "current_slide_index": 0, "contract": {},
                                        "previous_slide_archetype": "B"})
        assert "kicker: DEEP-DIVE\n  headline: Search carries sales\n  subtitle: ₹1.32 Cr · 6.35x" in user
        for text in (system, user):
            low = text.lower()
            assert "invent realistic" not in low and "real-sounding" not in low
            assert "add substance" not in low and "archetype" not in low
            assert "$42.8M" not in text and "do NOT rearrange" not in text
            assert "Derive the kicker" not in text


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
        components=[PlannerComponent(
            component_id="slide_title",
            kind="title", count=1,
            content_data_json='{"title": "Q3 Metrics", "chart_data": [1, 2, 3]}',
        )],
        layout_hint="Title at top",
    )
    result = _planner_slide_to_state(0, slide, supplied_content={"title": "Q3 Metrics"})
    assert result["data_provenance"]["title"] == "user"
    assert result["data_provenance"]["chart_data"] == "sample"


def test_planner_slide_to_state_provenance_no_supplied():
    slide = PlannerSlide(
        slide_type="content",
        components=[PlannerComponent(
            component_id="slide_title",
            kind="title", count=1,
            content_data_json='{"title": "Generated Title"}',
        )],
        layout_hint="Title at top",
    )
    result = _planner_slide_to_state(0, slide)
    assert result["data_provenance"]["title"] == "sample"


# ── DeckSettings constraint mapping tests ─────────────────────────────────

def test_settings_to_constraints_minimal():
    s = DeckSettings(amount_of_text="minimal", text_mode="generate", slide_count="3-5")
    c = settings_to_constraints(s)
    assert c["content_level"] == "sparse"
    assert "data only" in c["narrative_guidance"]
    assert c["deck_min_threshold"] == 4


def test_settings_to_constraints_extensive():
    s = DeckSettings(amount_of_text="extensive", text_mode="preserve", slide_count="10-15")
    c = settings_to_constraints(s)
    assert c["content_level"] == "tight_fit"
    assert "rich narrative" in c["narrative_guidance"]
    assert c["provenance_rule"] == "llm_preserves_verbatim"
    assert c["deck_min_threshold"] == 12


# Local import needed for the outline node tests
from src.agents.outline_planner import outline_planner_node


def test_planner_temperatures_are_low():
    """§9.1 planner 9: both planners at 0.1 for stable plans."""
    from src.utils.llm_client import _load_models_config
    steps = _load_models_config()["steps"]
    assert steps["outline_planner"]["temperature"] == 0.1
    assert steps["slide_component_planner"]["temperature"] == 0.1


def test_slide_planner_prompt_examples_by_shape():
    """§9.1 planners 13, 15, 16 — and the matrix routing fix (f51c3f6) stays."""
    from src.agents.hint_capabilities import planner_capabilities_section
    from src.agents.slide_component_planner import _jinja_env
    prompt = _jinja_env.get_template("system.j2").render(hint_capabilities=planner_capabilities_section())
    assert "Source: Company" not in prompt                       # 13: no dated source example
    assert "Match Type Performance" not in prompt                # 15: examples outside the ad domain
    assert "One entity's metrics → kpi_row" in prompt
    assert "labels ≤ 2 words, full slide width" in prompt        # 16: chevron capacity
    assert "The **matrix** kind is only a 2×2 positioning map" in prompt
