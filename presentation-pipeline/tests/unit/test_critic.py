"""Tests for the critic agent with mocked LLM responses."""

from unittest.mock import MagicMock, patch

from src.agents.critic import critic_node, _render_prompts
from src.agents.critic_schema import CriticIssue, CriticOutput
from src.state import initial_state


GOOD_XML = """\
<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" textMuted="55627A" border="E2E8F0" />
<Slide>
  <VStack w="1280" h="720" padding="48" gap="24" backgroundColor="$surface">
    <Text fontSize="32" bold="true" color="$textMain">Q3 Results</Text>
    <HStack gap="16">
      <VStack padding="16" backgroundColor="$accent" gap="4">
        <Text fontSize="28" color="$surface">$1.2M</Text>
        <Text fontSize="14" color="$surface">Revenue</Text>
      </VStack>
      <VStack padding="16" backgroundColor="$accent" gap="4">
        <Text fontSize="28" color="$surface">85%</Text>
        <Text fontSize="14" color="$surface">Growth</Text>
      </VStack>
      <VStack padding="16" backgroundColor="$accent" gap="4">
        <Text fontSize="28" color="$surface">$340K</Text>
        <Text fontSize="14" color="$surface">Profit</Text>
      </VStack>
      <VStack padding="16" backgroundColor="$accent" gap="4">
        <Text fontSize="28" color="$surface">12</Text>
        <Text fontSize="14" color="$surface">Clients</Text>
      </VStack>
    </HStack>
  </VStack>
</Slide>"""

BAD_XML_HARDCODED_COLORS = """\
<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />
<Slide>
  <VStack w="1280" h="720" padding="48" backgroundColor="F7F9FC">
    <Text fontSize="32" color="16202E">Title</Text>
  </VStack>
</Slide>"""


def _make_state(**overrides):
    state = initial_state(
        run_id="critic-test",
        raw_request="Create a KPI dashboard showing Q3 results",
        deck_min_threshold=0,
    )
    state["slide_plans"] = [{
        "slide_index": 0,
        "components": [
            {"kind": "title", "count": 1, "content_summary": "Q3 Results"},
            {"kind": "kpi_row", "count": 4, "content_summary": "Revenue, Growth, Profit, Clients"},
        ],
        "density": "normal",
        "font_tier": "standard",
        "layout_hint": "Title at top, KPI tiles in a row below",
    }]
    state["contract"] = {
        "allowed_nodes": ["Slide", "Theme", "VStack", "HStack", "Text", "Shape", "Span"],
        "allowed_attributes": {"VStack": ["gap"], "Text": ["fontSize", "color", "bold"]},
        "theme_element": '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />',
    }
    state["theme_element"] = state["contract"]["theme_element"]
    state["current_xml"] = GOOD_XML
    state["compile_result"] = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    state.update(overrides)
    return state


def _mock_critic_output(issues=None):
    """Create a mock structured LLM that returns a CriticOutput."""
    output = CriticOutput(issues=issues or [])
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = output
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


# ── Prompt rendering ─────────────────────────────────────────────────────

def test_render_prompts_system_has_checklist():
    state = _make_state()
    system, user = _render_prompts(state)
    assert "Component Completeness" in system
    assert "Content Fidelity" in system
    assert "Structural Sanity" in system
    assert "Theme Adherence" in system


def test_render_prompts_user_has_xml():
    state = _make_state()
    _, user = _render_prompts(state)
    assert "<Slide>" in user
    assert "Q3 Results" in user


def test_render_prompts_user_has_components():
    state = _make_state()
    _, user = _render_prompts(state)
    assert "title" in user
    assert "kpi_row" in user


def test_render_prompts_user_has_theme():
    state = _make_state()
    _, user = _render_prompts(state)
    assert "Theme" in user
    assert "F7F9FC" in user


def test_render_prompts_includes_supplied_content():
    state = _make_state(supplied_content={"title": "Q3 Metrics", "revenue": "$1.2M"})
    _, user = _render_prompts(state)
    assert "SUPPLIED CONTENT" in user
    assert "Q3 Metrics" in user
    assert "$1.2M" in user


def test_render_prompts_no_supplied_content():
    state = _make_state()
    _, user = _render_prompts(state)
    assert "SUPPLIED CONTENT" not in user


def test_render_prompts_empty_plan():
    state = _make_state()
    state["slide_plans"] = []
    system, user = _render_prompts(state)
    assert "Component Completeness" in system


# ── Manual mode ──────────────────────────────────────────────────────────

def test_critic_manual_mode_passes():
    state = _make_state(critic_mode="manual")
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert result["critic_result"]["issues"] == []


# ── Auto mode — clean pass ───────────────────────────────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_clean_pass(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[])
    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert result["critic_result"]["issues"] == []


# ── Auto mode — missing component (high severity) ───────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_catches_missing_component(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="high",
            type="completeness",
            description="Plan specifies kpi_row with 4 tiles but XML has no KPI elements.",
            fix="Add 4 KPI tile VStacks inside an HStack with value + label Text nodes.",
        ),
    ])
    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is False
    assert len(result["critic_result"]["issues"]) == 1
    assert result["critic_result"]["issues"][0]["type"] == "completeness"
    assert result["critic_result"]["issues"][0]["severity"] == "high"


# ── Auto mode — hardcoded color (medium severity) ───────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_catches_hardcoded_color(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="medium",
            type="theme",
            description='<Text> uses hardcoded color="16202E" instead of $textMain.',
            fix='Change color="16202E" to color="$textMain".',
        ),
    ])
    state = _make_state(current_xml=BAD_XML_HARDCODED_COLORS)
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert len(result["critic_result"]["issues"]) == 1
    assert result["critic_result"]["issues"][0]["type"] == "theme"
    assert result["critic_result"]["issues"][0]["severity"] == "medium"


# ── Auto mode — missing supplied value (medium severity) ─────────────────

@patch("src.agents.critic.get_llm")
def test_critic_catches_missing_supplied_value(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="medium",
            type="fidelity",
            description='Supplied value "Q3 Metrics" does not appear in the XML.',
            fix='Replace the title Text content with "Q3 Metrics".',
        ),
    ])
    state = _make_state(supplied_content={"title": "Q3 Metrics"})
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert result["critic_result"]["issues"][0]["type"] == "fidelity"


# ── Auto mode — structural issue (high severity) ────────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_catches_structural_issue(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="high",
            type="structure",
            description="Root element inside <Slide> is not a VStack/HStack with dimensions.",
            fix="Wrap content in <VStack w='1280' h='720'>.",
        ),
    ])
    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is False
    assert result["critic_result"]["issues"][0]["type"] == "structure"


# ── Auto mode — mixed severities ────────────────────────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_mixed_severities_fails_on_high(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="high",
            type="completeness",
            description="Missing chart component.",
            fix="Add a Chart element.",
        ),
        CriticIssue(
            severity="medium",
            type="theme",
            description="Hardcoded color in backgroundColor.",
            fix="Use $surface token.",
        ),
        CriticIssue(
            severity="low",
            type="structure",
            description="Deep nesting (6 levels).",
            fix="Flatten stack hierarchy.",
        ),
    ])
    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is False
    assert len(result["critic_result"]["issues"]) == 3


@patch("src.agents.critic.get_llm")
def test_critic_medium_and_low_only_passes(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="medium",
            type="theme",
            description="Hardcoded color.",
            fix="Use $token.",
        ),
        CriticIssue(
            severity="low",
            type="structure",
            description="Minor nesting.",
            fix="Flatten.",
        ),
    ])
    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert len(result["critic_result"]["issues"]) == 2


# ── Auto mode — LLM error fallback ──────────────────────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_llm_error_falls_back_to_pass(mock_get_llm):
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = RuntimeError("API timeout")
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert result["critic_result"]["issues"] == []


# ── Issue format matches repairer expectations ───────────────────────────

@patch("src.agents.critic.get_llm")
def test_critic_issues_have_expected_keys(mock_get_llm):
    mock_get_llm.return_value = _mock_critic_output(issues=[
        CriticIssue(
            severity="high",
            type="completeness",
            description="Missing title.",
            fix="Add a title Text.",
        ),
    ])
    state = _make_state()
    result = critic_node(state)
    issue = result["critic_result"]["issues"][0]
    assert "severity" in issue
    assert "type" in issue
    assert "description" in issue
    assert "fix" in issue


# ── Verify repairer reads critic issues ──────────────────────────────────

def test_repairer_collect_problems_reads_critic():
    """Verify that the repairer's _collect_problems picks up critic issues."""
    from src.agents.repairer import _collect_problems

    state = _make_state()
    state["critic_result"] = {
        "passed": False,
        "issues": [
            {"severity": "high", "type": "completeness", "description": "Missing KPI tiles", "fix": "Add KPIs"},
        ],
    }
    problems = _collect_problems(state)
    assert any("CRITIC" in p for p in problems)
    assert any("Missing KPI" in p for p in problems)
