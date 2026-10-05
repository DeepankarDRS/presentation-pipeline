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
