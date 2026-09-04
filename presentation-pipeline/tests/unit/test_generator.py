"""Tests for the generator agent with mocked LLM responses."""

from unittest.mock import MagicMock, patch

from src.agents.generator import generator_node, _render_prompts
from src.state import initial_state


def _make_state(**overrides):
    state = initial_state(
        run_id="gen-test",
        raw_request="Create a title slide about Q3 results",
        deck_min_threshold=0,
    )
    state["slide_plans"] = [{
        "slide_index": 0,
        "components": [
            {"kind": "title", "count": 1, "content_summary": "Q3 Results"},
            {"kind": "narrative", "count": 1, "content_summary": "Revenue summary"},
        ],
        "density": "normal",
        "font_tier": "standard",
        "layout_hint": "Title at top, narrative below",
    }]
    state["contract"] = {
        "allowed_nodes": ["Slide", "Theme", "VStack", "Text", "Shape", "HStack"],
        "allowed_attributes": {
            "VStack": ["gap", "alignItems", "justifyContent"],
            "Text": ["fontSize", "color", "bold", "italic", "textAlign"],
            "Shape": ["shapeType", "fill.color"],
        },
        "forbidden_tags": ["div", "p", "span", "br"],
        "forbidden_attributes": ["style", "class", "width", "height"],
        "theme_element": '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" textMuted="55627A" border="E2E8F0" />',
        "density_tier": "standard",
        "layout_pattern": "Pattern: title-content",
        "example": "<Slide>...</Slide>",
        "notes": ["Use $tokens for colors", "All text in <Text> nodes"],
    }
    state["theme_element"] = state["contract"]["theme_element"]
    state.update(overrides)
    return state


# ── Prompt rendering ──────────────────────────────────────────────────────

def test_render_prompts_system_has_critical_rules():
    state = _make_state()
    system, user = _render_prompts(state)
    assert "CRITICAL RULES" in system
    assert "FORBIDDEN TAGS" in system
    assert "div" in system
    assert "Theme" in system


def test_render_prompts_user_has_objective():
    state = _make_state()
    system, user = _render_prompts(state)
    assert "Q3 results" in user
    assert "COMPONENTS" in user
    assert "title" in user


def test_render_prompts_includes_attributes_for_standard_tier():
    state = _make_state()
    system, _ = _render_prompts(state)
    assert "ALLOWED ATTRIBUTES" in system
    assert "VStack" in system


def test_render_prompts_minimal_tier_omits_attributes():
    state = _make_state()
    state["contract"]["density_tier"] = "minimal"
    system, _ = _render_prompts(state)
    assert "ALLOWED ATTRIBUTES" not in system


def test_render_prompts_dense_tier_includes_shrink_checklist():
    state = _make_state()
    state["contract"]["density_tier"] = "dense"
    system, _ = _render_prompts(state)
    assert "SHRINK CHECKLIST" in system


def test_render_prompts_with_supplied_content():
    state = _make_state(supplied_content={"title": "Q3 Metrics", "subtitle": "FY26"})
    _, user = _render_prompts(state)
    assert "Q3 Metrics" in user
    assert "SUPPLIED CONTENT" in user


def test_render_prompts_empty_contract():
    state = _make_state()
    state["contract"] = {}
    state["slide_plans"] = []
    system, user = _render_prompts(state)
    assert "CRITICAL RULES" in system


# ── LLM call ──────────────────────────────────────────────────────────────

@patch("src.agents.generator.get_llm")
def test_generator_calls_llm_and_returns_xml(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Theme />\n<Slide><VStack><Text>Hello</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 500, "completion_tokens": 200},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state()
    result = generator_node(state)

    assert "<Slide>" in result["current_xml"]
    assert len(result["generation_history"]) == 1

    record = result["generation_history"][0]
    assert record["tokens_in"] == 500
    assert record["tokens_out"] == 200
    assert record["model"] == "gpt-4.1-mini"
    assert record["attempt"] == 0
    assert record["tier"] == 0


@patch("src.agents.generator.get_llm")
def test_generator_records_retry_attempt(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Slide><VStack><Text>Fixed</Text></VStack></Slide>'
    mock_response.response_metadata = {
        "token_usage": {"prompt_tokens": 800, "completion_tokens": 300},
        "model_name": "gpt-4.1-mini",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state(retry_count=2, retry_tier=1)
    result = generator_node(state)

    record = result["generation_history"][0]
    assert record["attempt"] == 2
    assert record["tier"] == 1


@patch("src.agents.generator.get_llm")
def test_generator_handles_missing_token_usage(mock_get_llm):
    mock_response = MagicMock()
    mock_response.content = '<Slide><Text>OK</Text></Slide>'
    mock_response.response_metadata = {}
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm

    state = _make_state()
    result = generator_node(state)

    record = result["generation_history"][0]
    assert record["tokens_in"] == 0
    assert record["tokens_out"] == 0
    assert record["model"] == "unknown"
