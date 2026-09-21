"""Tests for the critic agent with mocked visual critic."""

from unittest.mock import patch

from src.agents.critic import critic_node
from src.agents.visual_critic import _filter_visual_notes
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
    </HStack>
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
        "layout_hint": "Title at top, KPI tiles in a row below",
    }]
    state["contract"] = {
        "allowed_nodes": ["Slide", "Theme", "VStack", "HStack", "Text", "Shape", "Span"],
        "theme_element": '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />',
        "house_style": "height budget 720px, 48px padding",
        "notes": ["Use $token colors only", "forbidden tag: div"],
    }
    state["theme_element"] = state["contract"]["theme_element"]
    state["current_xml"] = GOOD_XML
    state["compile_result"] = {
        "ok": True, "pptx_path": "/tmp/test.pptx",
        "diagnostics": [], "warnings": [], "retryable": False,
    }
    state.update(overrides)
    return state


def _mock_visual_result(issues=None, assessment="good", strategy="none"):
    """Return the 3-tuple that run_visual_critic returns."""
    usage = {"tokens_in": 100, "tokens_out": 50, "model": "gpt-4.1"}
    repair_hints = {
        "strategy": strategy,
        "assessment": assessment,
        "affected_nodes": [],
    }
    return (issues or [], usage, repair_hints)


# ── Visual critic — clean pass ──────────────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_clean_pass(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result()

    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert result["critic_result"]["issues"] == []
    assert result["visual_critic_result"]["repair_hints"]["strategy"] == "none"


# ── Visual critic — high severity fails ─────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_high_severity_fails(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result(
        issues=[{
            "severity": "high",
            "type": "completeness",
            "description": "[Visual] Missing KPI tiles",
            "fix": "Add KPI tiles",
            "affected_nodes": ["HStack"],
            "source": "visual",
        }],
        assessment="needs_tuning",
        strategy="patch",
    )

    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is False
    assert len(result["critic_result"]["issues"]) == 1
    assert result["visual_critic_result"]["repair_hints"]["strategy"] == "patch"


# ── Visual critic — medium only passes ──────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_medium_only_passes(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result(
        issues=[{
            "severity": "medium",
            "type": "theme",
            "description": "[Visual] Theme mismatch",
            "fix": "Use $accent",
            "affected_nodes": [],
            "source": "visual",
        }],
        assessment="needs_tuning",
        strategy="patch",
    )

    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True


# ── Screenshot failure — fail-open ──────────────────────────────────────

@patch("src.agents.critic.render_screenshots")
def test_critic_screenshot_failure_passes(mock_screenshots):
    mock_screenshots.return_value = _mock_batch(None, ok=False, error="LibreOffice timeout")

    state = _make_state()
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True
    assert result["critic_result"]["issues"] == []


# ── No PPTX — skip visual review ───────────────────────────────────────

def test_critic_no_pptx_skips_visual():
    state = _make_state()
    state["compile_result"] = {"ok": False, "pptx_path": None, "diagnostics": [], "warnings": []}
    result = critic_node(state)
    assert result["critic_result"]["passed"] is True


# ── Compile warnings passed through ────────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_passes_compile_warnings(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result()

    state = _make_state()
    state["compile_result"]["warnings"] = [
        {"type": "NODE_OUT_OF_BOUNDS", "message": "Text at (100,750) outside slide"},
    ]
    critic_node(state)

    call_kwargs = mock_vc.call_args
    assert call_kwargs.kwargs.get("compile_warnings") or call_kwargs[1].get("compile_warnings")


# ── Layout issues passed through ────────────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_passes_layout_issues(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result()

    state = _make_state()
    state["layout_issues"] = [
        {"severity": "high", "code": "ROOT_SIZE", "message": "Root VStack wrong dims"},
    ]
    critic_node(state)

    call_kwargs = mock_vc.call_args
    assert call_kwargs.kwargs.get("layout_issues") or call_kwargs[1].get("layout_issues")


# ── Repair hints propagation ───────────────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_repair_hints_in_visual_result(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result(
        issues=[{
            "severity": "high",
            "type": "visual",
            "description": "[Visual] Layout broken",
            "fix": "Rebuild",
            "affected_nodes": ["VStack", "Chart"],
            "source": "visual",
        }],
        assessment="layout_broken",
        strategy="regenerate",
    )

    state = _make_state()
    result = critic_node(state)
    hints = result["visual_critic_result"]["repair_hints"]
    assert hints["strategy"] == "regenerate"
    assert hints["assessment"] == "layout_broken"


# ── Screenshot tracking ────────────────────────────────────────────────

@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_tracks_screenshot(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result()

    state = _make_state()
    result = critic_node(state)
    assert result["slide_screenshots"][0] == "/tmp/slide-0.png"
    assert result["visual_critic_result"]["screenshot_path"] == "/tmp/slide-0.png"


# ── _filter_visual_notes ───────────────────────────────────────────────

def test_filter_visual_notes_removes_structural():
    notes = [
        "Use $token colors only",
        "forbidden tag: div",
        "Must not use <br>",
        "Keep 48px padding on all sides",
        "allowed_nodes are strict",
        "Use attribute fontSize not font-size",
    ]
    result = _filter_visual_notes(notes)
    assert "Keep 48px padding on all sides" in result
    assert "Use $token colors only" in result
    assert len(result) == 2


# ── Repairer reads critic issues ───────────────────────────────────────

def test_repairer_collect_problems_reads_visual_issues():
    from src.agents.repairer import _collect_problems

    state = _make_state()
    state["critic_result"] = {
        "passed": False,
        "issues": [
            {
                "severity": "high",
                "type": "completeness",
                "description": "Missing KPI tiles",
                "fix": "Add KPIs",
                "affected_nodes": ["HStack"],
                "source": "visual",
            },
        ],
    }
    problems = _collect_problems(state)
    assert any("VISUAL_HIGH" in p for p in problems)
    assert any("Fix: Add KPIs" in p for p in problems)
    assert any("Fix: Add KPIs" in p for p in problems)


# ── Helpers ─────────────────────────────────────────────────────────────

class _MockSlide:
    def __init__(self, png_path):
        self.png_path = png_path


class _MockBatch:
    def __init__(self, png_path, ok=True, error=None):
        self.ok = ok
        self.error = error
        self.slides = [_MockSlide(png_path)] if ok and png_path else []


def _mock_batch(png_path, ok=True, error=None):
    return _MockBatch(png_path, ok, error)


# ── Re-screenshot loop: previous_issues forwarded ─────────────────────


@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_passes_previous_issues_on_re_review(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result()

    prev_issues = [{
        "severity": "high", "type": "completeness",
        "description": "[Visual] Missing KPI tiles", "fix": "Add KPIs",
        "affected_nodes": ["HStack"], "source": "visual",
    }]

    state = _make_state()
    state["visual_repair_count"] = 1  # re-review round
    state["visual_critic_result"] = {"issues": prev_issues}
    state["pre_critic_xml"] = GOOD_XML
    state["pre_critic_slide_plans"] = list(state["slide_plans"])
    state["pre_critic_contract"] = state["contract"]
    state["pre_critic_score"] = -15

    critic_node(state)

    call_kwargs = mock_vc.call_args
    passed_prev = call_kwargs.kwargs.get("previous_issues") or call_kwargs[1].get("previous_issues")
    assert passed_prev is not None
    assert len(passed_prev) == 1
    assert passed_prev[0]["description"] == "[Visual] Missing KPI tiles"


# ── Re-screenshot loop: first run has no previous_issues ──────────────


@patch("src.agents.critic.render_screenshots")
@patch("src.agents.critic.run_visual_critic")
def test_critic_no_previous_issues_on_first_run(mock_vc, mock_screenshots):
    mock_screenshots.return_value = _mock_batch("/tmp/slide-0.png")
    mock_vc.return_value = _mock_visual_result()

    state = _make_state()
    critic_node(state)

    call_kwargs = mock_vc.call_args
    passed_prev = call_kwargs.kwargs.get("previous_issues") or call_kwargs[1].get("previous_issues")
    assert passed_prev is None
