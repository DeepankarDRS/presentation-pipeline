"""eval_run --compose: each run's plans and LLM deck are copied next to the scores, the composed
deck is added, and a compose failure is recorded without stopping the eval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import eval_run


def _run(tmp: Path) -> Path:
    run = tmp / "runs" / "case-abc123"
    (run / "deck").mkdir(parents=True)
    (run / "slides.json").write_text(json.dumps([{"slide_index": 0, "slide_plan": {}}]), encoding="utf-8")
    (run / "deck" / "presentation.pptx").write_bytes(b"llm")
    return run


def _case() -> dict:
    return {"name": "case", "repeat": 1}


def test_plans_and_llm_deck_are_copied_without_compose(tmp_path: Path) -> None:
    run = _run(tmp_path)
    case = _case()
    eval_run._collect_run(case, str(run / "deck" / "presentation.pptx"), tmp_path / "eval", compose=False)
    dst = tmp_path / "eval" / "decks" / "case__r1"
    assert (dst / "slides.json").exists() and (dst / "llm.pptx").read_bytes() == b"llm"
    assert not (dst / "composed.pptx").exists() and "composed" not in case


def test_compose_adds_the_composed_deck(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _run(tmp_path)
    (run / "composed").mkdir()
    (run / "composed" / "composed.pptx").write_bytes(b"code")

    def fake(r: Path) -> dict:
        return {"pptx": str(run / "composed" / "composed.pptx"), "slides": 1, "code": [1], "llm": [],
                "left_out": [], "smaller_type": {}, "overfull": []}

    monkeypatch.setattr("scripts.phase0b.compose_deck.compose", fake)
    case = _case()
    eval_run._collect_run(case, str(run / "deck" / "presentation.pptx"), tmp_path / "eval", compose=True)
    assert (tmp_path / "eval" / "decks" / "case__r1" / "composed.pptx").read_bytes() == b"code"
    assert case["composed"]["code"] == [1]
    assert "| case r1 | 1 | 1 |" in eval_run._composed_summary([case])


def test_compose_failure_is_recorded_not_raised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _run(tmp_path)

    def boom(r: Path) -> dict:
        raise RuntimeError("no slide compiled")

    monkeypatch.setattr("scripts.phase0b.compose_deck.compose", boom)
    case = _case()
    eval_run._collect_run(case, str(run / "deck" / "presentation.pptx"), tmp_path / "eval", compose=True)
    assert "no slide compiled" in case["composed"]["error"]
    assert (tmp_path / "eval" / "decks" / "case__r1" / "slides.json").exists()


def test_missing_deck_is_skipped(tmp_path: Path) -> None:
    case = _case()
    eval_run._collect_run(case, None, tmp_path / "eval", compose=True)
    assert not (tmp_path / "eval").exists() and "composed" not in case


# ── a paid run must never be lost to a scoring / copying error (step 0: one case crashed the whole eval) ──

def test_a_scoring_error_is_reported_on_the_case_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    final = {"slide_plans": [{}], "passed": True, "evaluation": {"cost": {"total_usd": 0.2}}, "pptx_path": "x.pptx"}
    monkeypatch.setattr(eval_run, "_stream_case", lambda case, run_id: (final, [{"slide": 0, "retry": 0, "tier": 0}]))

    def boom(*a, **k):
        raise ValueError("not well-formed (invalid token)")

    monkeypatch.setattr(eval_run, "_slide_row", boom)
    result = eval_run.evaluate_case({"name": "case", "request": "r", "slide_count": 1}, 1)
    assert result["slides"] == [] and result["cost"] == 0.2 and result["passed"] is True
    assert "scoring failed" in result["error"] and "output/runs/case-" in result["error"]


def test_a_copy_error_in_one_case_does_not_stop_the_bundle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    good = {"name": "good", "repeat": 1, "run_id": "g", "passed": True, "error": None, "tokens_in": 1, "tokens_out": 1,
            "cost": 0.1, "elapsed": 1.0, "expected_slides": 1, "slides": [], "_deck_pptx": None}
    bad = {**good, "name": "bad", "run_id": "b"}
    results = iter([bad, good])
    monkeypatch.setattr(eval_run, "evaluate_case", lambda case, r: next(results))
    monkeypatch.setattr(eval_run, "load_case", lambda name: {"name": name})
    monkeypatch.setattr("src.utils.logging_config.setup_logging", lambda: None, raising=False)
    copied = []

    def copy(case, out_dir):
        if case["name"] == "bad":
            raise OSError("disk full")
        copied.append(case["name"])

    monkeypatch.setattr(eval_run, "_copy_slides", copy)
    assert eval_run.main(["bad", "good", "--label", "t", "--repeat", "1", "--bundle", "--out", str(tmp_path)]) == 0
    assert copied == ["good"]
    assert list(tmp_path.glob("t-*.zip"))                      # the bundle was still written
    summary = next(tmp_path.glob("t-*/results.json")).read_text(encoding="utf-8")
    assert "collecting its files failed" in summary


def test_two_runs_started_in_the_same_second_get_their_own_folders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Fixed:
        @staticmethod
        def now():
            import datetime
            return datetime.datetime(2026, 10, 7, 9, 0, 0)

    monkeypatch.setattr(eval_run, "datetime", Fixed)
    fixtures = tmp_path / "fx"
    fixtures.mkdir()
    for _ in range(2):
        assert eval_run.main(["--fixtures", str(fixtures), "--label", "same", "--out", str(tmp_path / "o")]) == 0
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == ["same-20261007-090000", "same-20261007-090000-2"]
