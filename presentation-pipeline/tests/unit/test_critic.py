"""The critic node (2026-11-20 redesign): code-measured defects first (straight to the fixer), then the vision critic
per component; code defects logged for a code fix. LLM and screenshots faked."""

import json
from types import SimpleNamespace

import pytest

from src.agents import critic, visual_critic
from src.agents.critic_schema import ComponentVerdict, VisualCriticOutput
from src.state import initial_state

XML = ('<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />'
       '<Slide><VStack w="1280" h="720" padding="48" gap="24">'
       '<Text id="slide_title" fontSize="32">Q3 Results</Text><VStack id="cmp-kpis"><Text>$1.2M</Text></VStack>'
       '</VStack></Slide>')


@pytest.fixture
def state(tmp_path, monkeypatch):
    folder = tmp_path / "compile"
    folder.mkdir()
    (folder / "drawn.xml").write_text(XML, encoding="utf-8")
    (folder / "geometry.json").write_text(json.dumps({"slideSize": {"w": 1280, "h": 720}, "slides": [
        {"type": "vstack", "x": 0, "y": 0, "w": 1280, "h": 720, "children": [
            {"type": "text", "id": "slide_title", "x": 48, "y": 48, "w": 1184, "h": 40},
            {"type": "vstack", "id": "cmp-kpis", "x": 48, "y": 112, "w": 1184, "h": 300, "children": []}]}]}),
        encoding="utf-8")
    png = tmp_path / "s.png"
    from PIL import Image
    Image.new("RGB", (1280, 720), "white").save(png)
    monkeypatch.setattr(critic, "_ROOT", tmp_path)
    monkeypatch.setattr(critic, "render_screenshots", lambda *a, **k: SimpleNamespace(
        ok=True, error=None, slides=[SimpleNamespace(png_path=str(png))]))
    s = initial_state(run_id="critic-test", raw_request="Q3 results")
    s["slide_plans"] = [{"slide_index": 0, "slide_title": "Q3 Results", "components": [
        {"component_id": "slide_title", "kind": "title"}, {"component_id": "kpis", "kind": "kpi_row"}]}]
    s["current_xml"] = XML
    s["theme_element"] = '<Theme surface="F7F9FC" accent="2563EB" textMain="16202E" />'
    s["normalize_result"] = {"cleaned_xml": XML, "tags_xml": '<Slide><KpiRow ref="kpis"/></Slide>',
                             "component_boxes": {"kpis": ["cmp-kpis"]}}
    s["compile_result"] = {"ok": True, "pptx_path": str(folder / "presentation.pptx"), "diagnostics": [],
                           "warnings": [], "retryable": False}
    s["layout_issues"] = []
    return s


class _FakeLLM:
    def __init__(self, output):
        self.output, self.messages = output, None

    def with_structured_output(self, schema, **_):
        schema.model_json_schema()
        return SimpleNamespace(invoke=self._invoke)

    def _invoke(self, messages):
        self.messages = messages
        return {"parsed": self.output, "raw": SimpleNamespace(response_metadata={}, usage_metadata={})}


def _verdicts(*vs, regenerate=False):
    return VisualCriticOutput(observations="A title over one KPI card.", regenerate=regenerate,
                              regenerate_reason="too much" if regenerate else "",
                              verdicts=[ComponentVerdict(**v) for v in vs])


OK = {"id": "slide", "verdict": "ok", "severity": "none", "check": "none", "what_i_see": "reads well", "owner": "slide"}


def test_clean_slide_passes_with_two_images_and_the_fixed_system_prompt(state, monkeypatch):
    llm = _FakeLLM(_verdicts(OK, dict(OK, id="kpis"), dict(OK, id="slide_title")))
    monkeypatch.setattr(visual_critic, "get_llm", lambda _n: llm)
    out = critic.critic_node(state)
    assert out["critic_result"]["passed"] is True
    system, user = llm.messages
    assert system["content"] == visual_critic.system_prompt()   # one prompt for every slide: cacheable
    images = [c for c in user["content"] if c["type"] == "image_url"]
    assert len(images) == 2   # clean + marked
    text = user["content"][-1]["text"]
    assert "[2] kpis · kpi_row" in text and '<!-- [2] kpis' in text and '<KpiRow ref="kpis"/>' in text


def test_a_medium_issue_fails_the_slide_for_a_fix(state, monkeypatch):
    bad = {"id": "kpis", "verdict": "issue", "severity": "medium", "check": "colour",
           "what_i_see": "every tile is green", "owner": "slide"}
    monkeypatch.setattr(visual_critic, "get_llm", lambda _n: _FakeLLM(_verdicts(OK, bad)))
    out = critic.critic_node(state)
    assert out["critic_result"]["passed"] is False
    assert out["visual_critic_result"]["repair_hints"]["strategy"] == "fix"
    issue = out["critic_result"]["issues"][0]
    assert issue["component"] == "kpis" and "[2] kpis" in issue["description"] and issue["type"] == "theme"


def test_low_only_passes(state, monkeypatch):
    low = {"id": "kpis", "verdict": "issue", "severity": "low", "check": "balance", "what_i_see": "a bit low",
           "owner": "slide"}
    monkeypatch.setattr(visual_critic, "get_llm", lambda _n: _FakeLLM(_verdicts(OK, low)))
    assert critic.critic_node(state)["critic_result"]["passed"] is True


def test_regenerate_when_the_plan_is_wrong(state, monkeypatch):
    monkeypatch.setattr(visual_critic, "get_llm", lambda _n: _FakeLLM(_verdicts(OK, regenerate=True)))
    out = critic.critic_node(state)
    assert out["visual_critic_result"]["repair_hints"]["strategy"] == "regenerate"
    assert out["critic_result"]["passed"] is False


def test_a_measured_defect_goes_straight_to_the_fixer_without_a_vision_call(state, monkeypatch):
    monkeypatch.setattr(visual_critic, "get_llm", lambda _n: pytest.fail("no vision call for a measured defect"))
    state["compile_result"]["warnings"] = [{"code": "SLIDE_DENSE", "message": "...", "spills": [
        {"type": "ul", "kind": "h", "need": 519, "have": 394, "ids": ["lst-kpis", "cmp-kpis"]}]}]
    out = critic.critic_node(state)
    assert out["critic_result"]["passed"] is False
    assert out["visual_critic_result"]["repair_hints"]["strategy"] == "relayout"
    assert "[2] kpis" in out["critic_result"]["issues"][0]["description"]
    assert "519" in out["critic_result"]["issues"][0]["description"]


def test_code_defects_are_logged_for_a_code_fix(state, monkeypatch, tmp_path):
    bad = {"id": "kpis", "verdict": "issue", "severity": "high", "check": "visible_defect",
           "what_i_see": "the last tile draws past the card", "owner": "code_defect"}
    monkeypatch.setattr(visual_critic, "get_llm", lambda _n: _FakeLLM(_verdicts(OK, bad)))
    critic.critic_node(state)
    log = (tmp_path / "output" / "runs" / "critic-test" / "code-defects.jsonl").read_text(encoding="utf-8")
    assert json.loads(log)["component"] == "kpis"


def test_screenshot_failure_passes(state, monkeypatch):
    monkeypatch.setattr(critic, "render_screenshots", lambda *a, **k: SimpleNamespace(ok=False, error="x", slides=[]))
    assert critic.critic_node(state)["critic_result"]["passed"] is True


def test_no_pptx_skips_review():
    s = initial_state(run_id="x", raw_request="x")
    s["compile_result"] = {"ok": False, "pptx_path": None}
    assert critic.critic_node(s)["critic_result"]["passed"] is True
