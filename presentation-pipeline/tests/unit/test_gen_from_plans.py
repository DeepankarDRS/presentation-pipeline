"""scripts.gen_from_plans: the brief's fingerprint matches the evaluator's request_sha256; arguments are checked."""

import hashlib
import json

import pytest

from scripts.gen_from_plans import main, request_fingerprint


def test_fingerprint_is_the_evaluators_request_sha256():
    blob = json.dumps({"request": "Make a deck", "supplied_content": None}, sort_keys=True, ensure_ascii=False)
    assert request_fingerprint("Make a deck") == hashlib.sha256(blob.encode()).hexdigest()[:16]


def test_one_request_file_per_run_is_required(tmp_path):
    with pytest.raises(SystemExit):
        main([str(tmp_path), "--requests", str(tmp_path / "a.txt"), str(tmp_path / "b.txt")])


def test_a_run_folder_without_plans_is_rejected(tmp_path):
    (tmp_path / "brief.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(tmp_path), "--requests", str(tmp_path / "brief.txt")])


def test_gpt6_models_are_reasoning_models():
    from src.utils.llm_client import _is_reasoning_model
    assert _is_reasoning_model("gpt-6.1-sol") and not _is_reasoning_model("gpt-4.1")
