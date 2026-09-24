"""Phase 0 eval harness — LLM-free: mocked pipeline stream + one real compile."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import eval_compare, eval_import, eval_run
from scripts.eval_metrics import card_metrics, invented_numbers, pattern_match, text_overflows, word_breaks
from scripts.make_gj_h1_case import CASE, build_case

_ROOT = Path(__file__).resolve().parents[2]
_GOLDEN = _ROOT / "tests" / "fixtures" / "golden" / "gj-h1-deck"
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"


@pytest.fixture(scope="module")
def blinkit_pptx(tmp_path_factory) -> Path:
    """gj-h1 slide 05 compiled for real: 5 KPI tiles, 2 table cards, chart card, dark panel."""
    if not shutil.which("node"):
        pytest.skip("node not installed")
    out = tmp_path_factory.mktemp("blinkit")
    subprocess.run(["node", str(_COMPILER), str(_GOLDEN / "05-blinkit-deepdive.xml"), str(out)],
                   check=True, capture_output=True, timeout=120)
    return out / "presentation.pptx"


def test_card_metrics_on_real_compile(blinkit_pptx):
    cards = card_metrics(blinkit_pptx)
    patterns = sorted(c["pattern"] for c in cards)
    assert patterns == ["chart_card", "dark_panel"] + ["kpi_tile"] * 5 + ["table_card"] * 2
    assert all(0 < c["fill"] <= 1 for c in cards)
    kpi = next(c for c in cards if c["pattern"] == "kpi_tile")
    assert kpi["fill"] > 0.95  # label + value + note fill the tile between equal paddings


def test_fill_sees_centred_and_stretched_row_dead_space(tmp_path):
    """fit_grow s1 without fit-grow: KPI row h=150 renders 246 px with centred text (F1),
    and the table's rows are stretched with top-aligned text (F5) — both must read as low fill."""
    if not shutil.which("node"):
        pytest.skip("node not installed")
    xml = _ROOT / "tests" / "fixtures" / "fit_grow" / "s1-performance-overview.xml"
    subprocess.run(["node", str(_COMPILER), str(xml), str(tmp_path)], check=True, capture_output=True,
                   timeout=120, env={**os.environ, "POM_FIT_GROW": "0"})
    cards = card_metrics(tmp_path / "presentation.pptx")
    assert [c["fill"] < 0.5 for c in cards if c["pattern"] == "kpi_tile"] == [True] * 3
    assert all(c["fill"] < 0.7 for c in cards if c["pattern"] == "table_card")


def test_pattern_match():
    assert pattern_match(["kpi_tile"] * 3, ["kpi_tile"] * 3) == 1.0
    assert pattern_match(["kpi_tile", "table_card"], ["kpi_tile", "chart_card"]) == pytest.approx(1 / 3, abs=1e-3)
    assert pattern_match([], []) == 1.0
    assert pattern_match(["kpi_tile"], []) == 0.0


def _attempt(slide, retry, tier, pptx, *, ok=True, issues=(), diags=(), layout=()):
    return {
        "slide": slide, "retry": retry, "tier": tier,
        "normalize_result": {"issues": [{"code": c, "auto_fixed": True} for c in issues]},
        "compile_result": {"ok": ok, "pptx_path": str(pptx) if ok else None,
                           "diagnostics": [{"type": d, "message": f"{d} at line 3"} for d in diags]},
        "layout_issues": [{"code": c} for c in layout],
    }


@pytest.fixture
def deck_result(monkeypatch, blinkit_pptx):
    """Two-slide deck: slide 0 fails once then passes on PATCH; slide 1 passes first time."""
    attempts = [
        _attempt(0, 0, 0, blinkit_pptx, ok=False, issues=["ICON_NAME_NORMALIZED"], diags=["INVALID_CHILD"]),
        _attempt(0, 1, 1, blinkit_pptx, issues=["ICON_NAME_NORMALIZED"], layout=["FONT_TOO_SMALL"]),
        _attempt(1, 0, 0, blinkit_pptx, issues=["TEXT_CONTAINER_FLATTENED", "FONT_FLOOR"]),
    ]
    final = {
        "passed": True, "pptx_path": None,
        "evaluation": {"tokens": {"total_in": 1000, "total_out": 200}, "cost": {"total_usd": 0.01}},
        "slide_plans": [{"components": [{"kind": "kpi_row", "weight": "hero", "design_hint": "accent"}]},
                        {"components": [{"kind": "table", "weight": "peer"}]}],
    }
    monkeypatch.setattr(eval_run, "_stream_case", lambda case, run_id: (final, attempts))
    return eval_run.evaluate_case({"name": "deck-x"}, 1)


def test_per_slide_metrics_from_stream(deck_result):
    s0, s1 = deck_result["slides"]
    assert (s0["first_pass_ok"], s0["retries"], s0["max_tier"], s0["compiled"]) == (False, 1, 1, True)
    assert s0["blocking"] == {"INVALID_CHILD": 1}
    assert s0["blocking_msgs"] == ["INVALID_CHILD: INVALID_CHILD at line 3"]
    assert (s0["word_breaks"], deck_result["expected_slides"]) == (0, 1)
    assert s0["auto_fixes"] == {"ICON_NAME_NORMALIZED": 1}  # first attempt only
    assert s0["layout_issues"] == {"FONT_TOO_SMALL": 1}  # final attempt
    assert s0["components"] == [{"kind": "kpi_row", "weight": "hero", "design_hint": "accent"}]
    assert (s1["first_pass_ok"], s1["retries"]) == (True, 0)
    assert s1["auto_fixes"] == {"TEXT_CONTAINER_FLATTENED": 1, "FONT_FLOOR": 1}
    assert len(s1["cards"]) == 9
    assert (deck_result["tokens_in"], deck_result["cost"], deck_result["passed"]) == (1000, 0.01, True)


def test_aggregate_summary_bundle_import_compare(deck_result, tmp_path, monkeypatch):
    out_dir = tmp_path / "eval" / "base-20260923-000000"
    eval_run._copy_slides(deck_result, out_dir)
    results = {"label": "base", "created": "2026-09-23T00:00:00", "git_commit": "abc", "models_sha": "123",
               "fit_grow": "1", "aggregate": eval_run.aggregate([deck_result]), "cases": [deck_result]}
    agg = results["aggregate"]
    assert (agg["slides"], agg["first_pass_pct"], agg["mean_retries"], agg["cards"]) == (2, 50.0, 0.5, 18)
    assert agg["blocking_codes"] == {"INVALID_CHILD": 1}
    assert (agg["tables_overfull_slides"], agg["empty_cells"]) == (0, 0)
    (out_dir / "results.json").write_text(json.dumps(results), encoding="utf-8")
    eval_run.write_summary(results, out_dir / "summary.md")
    assert "| first_pass_pct | 50.0 |" in (out_dir / "summary.md").read_text(encoding="utf-8")
    assert (out_dir / "slides" / "deck-x__r1" / "slide-1" / "presentation.pptx").exists()

    zip_path = eval_run.make_bundle(out_dir)
    monkeypatch.setattr(eval_import, "render_libreoffice", lambda eval_dir: 0)
    dest = eval_import.import_bundle(zip_path, tmp_path / "docs", tmp_path / "imported")
    assert dest.name == "base"
    assert json.loads((dest / "results.json").read_text(encoding="utf-8"))["label"] == "base"
    summary = (dest / "summary.md").read_text(encoding="utf-8")
    assert "## Review renders" in summary and "| slide_count_off | 1 |" in summary  # 2 slides, target 1

    # a second bundle with the same label merges; re-running a case replaces its earlier runs
    other = json.loads(json.dumps(results))
    for c in other["cases"]:
        c["name"] = "deck-y"
    out2 = tmp_path / "eval" / "base-20260924-000000"
    shutil.copytree(out_dir / "slides" / "deck-x__r1", out2 / "slides" / "deck-y__r1")
    (out2 / "results.json").write_text(json.dumps(other), encoding="utf-8")
    eval_run.write_summary(other, out2 / "summary.md")
    eval_import.import_bundle(eval_run.make_bundle(out2), tmp_path / "docs", tmp_path / "imported")
    eval_import.import_bundle(zip_path, tmp_path / "docs", tmp_path / "imported")
    merged = json.loads((dest / "results.json").read_text(encoding="utf-8"))
    assert sorted(c["name"] for c in merged["cases"]) == ["deck-x", "deck-y"]
    assert merged["aggregate"]["slides"] == 4

    better = json.loads(json.dumps(results))
    better["label"] = "phase-1"
    better["aggregate"]["first_pass_pct"] = 100.0
    report = eval_compare.compare(results, better)
    assert "| first_pass_pct | 50.0 | 100.0 | +50 |" in report
    assert "| deck-x |" in report


def test_score_against_golden(deck_result):
    golden = {"slides": [{"cards": [{"pattern": "kpi_tile"}]}]}  # 1 golden slide vs 2 generated
    eval_run.score_against_golden(deck_result, golden)
    assert deck_result["slides"][1]["golden_match"] == 0.0
    assert deck_result["golden_match"] == pytest.approx(deck_result["slides"][0]["golden_match"] / 2, abs=1e-3)


def test_stream_case_tags_validator_attempts_on_real_graph():
    """The real LangGraph graph (LLM + compiler mocked): attempts are tagged per slide."""
    from unittest.mock import MagicMock, patch

    import src.state

    icons = ["bar-chart-2", "not-a-real-icon"]

    def gen(messages):
        resp = MagicMock()
        n = gen.calls = getattr(gen, "calls", 0) + 1
        resp.content = (f'<Slide><VStack w="1280" h="720"><Icon name="{icons[n - 1]}" />'
                        f"<Text>Slide {n}</Text></VStack></Slide>")
        resp.response_metadata = {"token_usage": {"prompt_tokens": 1, "completion_tokens": 1}, "model_name": "m"}
        return resp

    def with_plans(**kwargs):
        seen.update(kwargs)
        state = real_initial_state(**kwargs)
        state["slide_plans"] = [
            {"slide_index": i, "slide_type": "data", "layout_hint": "", "content_data": {}, "data_provenance": {},
             "components": [{"kind": "title", "count": 1, "content_summary": f"Slide {i}"}]}
            for i in range(2)
        ]
        return state

    real_initial_state, seen = src.state.initial_state, {}
    ok = {"ok": True, "pptx_path": "/tmp/x.pptx", "diagnostics": [], "warnings": [], "retryable": False}
    with patch("src.agents.generator.get_llm") as get_llm, \
         patch("src.agents.validator.validate_xml", return_value={"ok": True, "diagnostics": [], "warnings": []}), \
         patch("src.agents.validator.compile_xml", return_value=ok), \
         patch("src.agents.deck_nodes.compile_xml", return_value=ok), \
         patch("src.state.initial_state", side_effect=with_plans):
        get_llm.return_value.invoke.side_effect = gen
        final, attempts = eval_run._stream_case({"name": "t", "request": "two slides"}, "eval-test")

    assert final["passed"] is True
    assert seen["test_case"]["slide_count"] == seen["deck_min_threshold"] == 1  # exact target reaches the planner
    assert [(a["slide"], a["retry"]) for a in attempts] == [(0, 0), (1, 0)]
    codes = [{i["code"] for i in a["normalize_result"]["issues"]} for a in attempts]
    assert "UNKNOWN_ICON_REMOVED" not in codes[0] and "UNKNOWN_ICON_REMOVED" in codes[1]


def test_crash_mid_deck_keeps_slides_already_run(monkeypatch, blinkit_pptx):
    import src.graph

    class Graph:
        def stream(self, state, config, stream_mode):
            yield "updates", {"validator": _attempt(0, 0, 0, blinkit_pptx)}
            yield "updates", {"slide_router": {"current_slide_index": 1, "retry_count": 0}}
            raise RuntimeError("API timeout on slide 1")

    monkeypatch.setattr(src.graph, "compile_graph", Graph)
    result = eval_run.evaluate_case({"name": "deck-z", "expect": {"slide_count": 2}}, 1)
    assert result["error"] == "RuntimeError: API timeout on slide 1"
    assert [s["index"] for s in result["slides"]] == [0] and result["slides"][0]["compiled"]


def test_slide_target_beats_deck_settings_default():
    """DeckSettings defaults to 8 slides; the eval must pass each case's own target."""
    assert eval_run._slide_target({"expect": {"slide_count": 6}}) == 6
    assert eval_run._slide_target({"slide_count": 14, "expect": {"slide_count": 6}}) == 14
    assert eval_run._slide_target({"name": "kpi-row"}) == 1


def test_word_breaks_on_a_crushed_tile(tmp_path, blinkit_pptx):
    if not shutil.which("node"):
        pytest.skip("node not installed")
    xml = tmp_path / "crushed.xml"
    xml.write_text('<Slide><HStack w="1280" h="720" gap="8"><VStack w="40" backgroundColor="FFFFFF">'
                   '<Text fontSize="22">Winner</Text></VStack><VStack w="max"><Text>ok</Text></VStack>'
                   '</HStack></Slide>', encoding="utf-8")
    subprocess.run(["node", str(_COMPILER), str(xml), str(tmp_path)], check=True, capture_output=True, timeout=120)
    assert word_breaks(tmp_path / "presentation.pptx") == 1
    assert word_breaks(blinkit_pptx) == 0


def test_text_overflow_needs_two_extra_lines(tmp_path, blinkit_pptx):
    def slide(w_px, h_px, text, pt=12):
        emu = lambda px: str(int(px * 9525))  # noqa: E731
        xml = ('<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
               'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp>'
               f'<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu(w_px)}" cy="{emu(h_px)}"/></a:xfrm></p:spPr>'
               f'<p:txBody><a:p><a:r><a:rPr sz="{pt * 100}"/><a:t>{text}</a:t></a:r></a:p></p:txBody>'
               '</p:sp></p:spTree></p:cSld></p:sld>')
        path = tmp_path / f"s{w_px}x{h_px}.pptx"
        with __import__("zipfile").ZipFile(path, "w") as z:
            z.writestr("ppt/slides/slide1.xml", xml)
        return path

    long_label = "Day-parting 6-11 AM for Milk, Paneer and Curd; +15.5% Zepto GMV May vs Apr (4.69 to 5.41 Cr)"
    assert text_overflows(slide(100, 40, long_label)) == 1   # timeline label in a small fixed box
    assert text_overflows(slide(320, 20, "Restructure by intent, SKU, city, objective", 11)) == 0  # one-line estimate slack
    assert text_overflows(blinkit_pptx) == 0


def test_invented_numbers_ignores_formatting_variants():
    brief = "Blinkit ROAS 6.35x, NTB customers 10,332, ACOS 4.40%"
    xml = ('<Slide><VStack><Text>ROAS 6.35x · 10332 NTB · ACOS 4.4%</Text>'
           '<Chart><ChartSeries name="Zepto"><ChartDataPoint label="Jan" value="3.12" /></ChartSeries></Chart>'
           '<Text>Source: Q2 2024 & internal</Text></VStack></Slide>')
    assert invented_numbers(xml, brief) == ["3.12", "2024"]


def test_invented_numbers_survives_xml_a_strict_parser_rejects():
    """eval 2026-09-24 crashed on a slide POM compiled but ElementTree rejects (a bare '<' in text)."""
    xml = '<Slide><Text fontSize="14">ACOS <20% target, ROAS 4.33x</Text><Chart><ChartDataPoint label="Q1" value="12.5" /></Chart></Slide>'
    assert invented_numbers(xml, "ROAS 4.33x, Q1 12.5") == ["20"]
    # the real case: markup inside an attribute; colour codes after it must not read as numbers
    xml = '<Slide><Timeline><TimelineItem date="Feb" title="<B>Scroll winners</B> +38% GMV" color="2563EB" /></Timeline></Slide>'
    assert invented_numbers(xml, "+38% GMV") == []


def test_pick_reviews_failed_first_then_lowest_fill():
    results = {"cases": [{"name": "a", "repeat": 1, "slides": [
        {"index": 0, "compiled": True, "cards": [{"fill": 0.9}]},
        {"index": 1, "compiled": False, "cards": []},
        {"index": 2, "compiled": True, "cards": [{"fill": 0.4}]},
    ]}]}
    assert eval_import.pick_reviews(results, limit=2) == [("a__r1", 1), ("a__r1", 2)]


def test_every_gate_case_loads_with_a_request():
    from src.utils.case_loader import load_case

    for name in eval_run.GATE_CASES:
        case = load_case(name)
        assert case["name"] == name and case.get("request"), name
    decks = {n: load_case(n)["expect"]["slide_count"] for n in eval_run.GATE_CASES if n.startswith("gate-deck-")}
    assert decks == {"gate-deck-cheffin-audit": 6, "gate-deck-xtsy-qcomm": 8, "gate-deck-agency-takeover": 6}


def test_gj_h1_case_matches_golden_deck():
    assert CASE.read_text(encoding="utf-8") == build_case(), "run: python -m scripts.make_gj_h1_case"
    assert "gj-h1-regen" in eval_run.GATE_CASES
