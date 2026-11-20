"""The visual fixer (2026-11-20): search/replace edits on the drawn XML, compiled with fit-grow off, kept only when
the code checks pass. LLM and compiler faked."""

import json
from types import SimpleNamespace

import pytest

from src.agents import slide_facts, visual_repairer as vr
from src.agents.visual_repairer import Edit, FixerOutput
from src.state import initial_state

DRAWN = ('<Theme accent="2563EB" />\n<Slide><VStack w="1280" h="720" gap="22">'
         '<Text id="slide_title" fontSize="36">Growth improves</Text>'
         '<HStack gap="18"><VStack id="cmp-kpis" w="49%" padding="24"><Text id="kpiv0-kpis-0" fontSize="82">$48.2M</Text>'
         '</VStack></HStack></VStack></Slide>')
COMPS = [slide_facts.Component(1, "slide_title", "title", "hand", ["slide_title"]),
         slide_facts.Component(2, "kpis", "kpi_row", "code", ["cmp-kpis"], "grid")]


def test_each_old_must_match_exactly_once():
    xml, errors = vr.apply_edits(DRAWN, [Edit(old='gap="18"', new='gap="48"')])
    assert not errors and 'gap="48"' in xml
    same, errors = vr.apply_edits(DRAWN, [Edit(old='gap="18"', new='gap="48"'), Edit(old="fontSize", new="x")])
    assert same == DRAWN and "found 2 times" in errors[0]


def test_check_keeps_a_restyle():
    after = DRAWN.replace('w="49%" padding="24"', 'w="36%" padding="18" backgroundColor="$positiveSoft"')
    assert vr.check(DRAWN, after, COMPS, {"geometry errors": 1}, {"geometry errors": 1}) == []


def test_check_rejects_reworded_code_drawn_content_new_numbers_and_worse_geometry():
    reworded = DRAWN.replace("$48.2M", "$48M")
    assert any("kpis changed" in w for w in vr.check(DRAWN, reworded, COMPS, {}, {}))
    invented = DRAWN.replace("Growth improves", "Growth improves 12%")
    assert any("numbers that were not on the slide" in w for w in vr.check(DRAWN, invented, COMPS, {}, {}))
    assert vr.check(DRAWN, DRAWN, COMPS, {"geometry errors": 0, "slide shrunk by POM": 0},
                    {"geometry errors": 1, "slide shrunk by POM": 1}) == ["geometry errors 0 -> 1", "slide shrunk by POM 0 -> 1"]
    gone = DRAWN.replace(' id="cmp-kpis"', "")
    assert any("box is gone" in w for w in vr.check(DRAWN, gone, COMPS, {}, {}))


@pytest.fixture
def state(tmp_path, monkeypatch):
    folder = tmp_path / "c"
    folder.mkdir()
    (folder / "drawn.xml").write_text(DRAWN, encoding="utf-8")
    monkeypatch.setattr(vr, "_ROOT", tmp_path)
    monkeypatch.setattr(vr, "slide_context", lambda s: ({}, COMPS, []))
    monkeypatch.setattr(vr, "audit_layout", lambda xml: [])
    monkeypatch.setattr(vr, "audit_run_folder", lambda *a, **k: [])
    s = initial_state(run_id="fix", raw_request="x")
    s["slide_plans"] = [{"components": []}]
    s["compile_result"] = {"ok": True, "pptx_path": str(folder / "presentation.pptx"), "warnings": []}
    s["normalize_result"] = {"cleaned_xml": DRAWN, "tags_xml": "<Slide/>"}
    s["layout_issues"] = []
    s["visual_critic_result"] = {"issues": [{"severity": "medium", "description": "[Visual] [2] kpis: cards too wide"}],
                                 "repair_hints": {"strategy": "fix", "observations": "two wide cards"}}
    return s


def _llm(*outputs):
    calls = []

    def invoke(messages):
        calls.append(messages[1]["content"])
        return {"parsed": outputs[len(calls) - 1], "raw": SimpleNamespace(response_metadata={}, usage_metadata={})}
    llm = SimpleNamespace(with_structured_output=lambda *a, **k: SimpleNamespace(invoke=invoke))
    return llm, calls


def test_a_fix_compiles_with_fit_grow_off_and_is_kept(state, monkeypatch):
    llm, calls = _llm(FixerOutput(plan="narrow the cards", edits=[Edit(old='w="49%"', new='w="36%"')]))
    compiled = {}
    monkeypatch.setattr(vr, "get_llm", lambda _n: llm)
    monkeypatch.setattr(vr, "compile_xml", lambda xml, d: compiled.setdefault("xml", xml) and
                        {"ok": True, "pptx_path": str(d / "p.pptx"), "warnings": []})
    out = vr.visual_repairer_node(state)
    assert out["visual_repair_outcome"] == "improved"
    assert compiled["xml"].startswith("<!-- fit-grow: off -->") and 'w="36%"' in compiled["xml"]
    assert out["normalize_result"]["cleaned_xml"] == compiled["xml"]
    assert "[2] kpis · kpi_row" in calls[0] and DRAWN in calls[0]


def test_a_failed_match_goes_back_once_then_the_slide_stays(state, monkeypatch):
    bad = FixerOutput(plan="x", edits=[Edit(old="nowhere", new="y")])
    llm, calls = _llm(bad, bad)
    monkeypatch.setattr(vr, "get_llm", lambda _n: llm)
    monkeypatch.setattr(vr, "compile_xml", lambda *a: pytest.fail("nothing to compile"))
    out = vr.visual_repairer_node(state)
    assert out["visual_repair_outcome"] == "error" and "current_xml" not in out
    assert len(calls) == 2 and "YOUR LAST EDITS FAILED" in calls[1]


def test_a_worse_fix_is_rolled_back(state, monkeypatch):
    llm, _ = _llm(FixerOutput(plan="x", edits=[Edit(old="$48.2M", new="$48M")]))
    monkeypatch.setattr(vr, "get_llm", lambda _n: llm)
    monkeypatch.setattr(vr, "compile_xml", lambda xml, d: {"ok": True, "pptx_path": str(d / "p.pptx"), "warnings": []})
    out = vr.visual_repairer_node(state)
    assert out["visual_repair_outcome"] == "rolled_back" and "current_xml" not in out


def test_one_fix_then_the_slide_is_done():
    from src.graph import route_after_visual_repairer
    s = initial_state(run_id="x", raw_request="x")
    s["slide_plans"] = [{}, {}]
    s["visual_repair_outcome"] = "improved"
    assert route_after_visual_repairer(s) == "slide_router"
