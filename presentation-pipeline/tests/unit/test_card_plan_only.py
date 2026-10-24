"""scripts.experiments.cards.card_plan_only --workers: decks planned at once, runs.json in case order (plan_case mocked, no API)."""

import json
import threading
import time

from scripts.experiments.cards import card_plan_only as cpo


def test_workers_run_decks_at_once_and_keep_case_order(tmp_path, monkeypatch):
    active, peak, lock = [0], [0], threading.Lock()

    def fake_plan_case(case, run_id):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.05)
        with lock:
            active[0] -= 1
        if "r2" in run_id and case["name"] == "deck-qbr-data":
            raise RuntimeError("rate limit")
        return {"outline": {}, "slide_plans": [], "cost_usd": 0.01}

    monkeypatch.setattr(cpo, "plan_case", fake_plan_case)
    monkeypatch.setattr(cpo, "load_case", lambda name: {"name": name})
    monkeypatch.setattr(cpo, "OUT", tmp_path)
    monkeypatch.setattr("sys.argv", ["card_plan_only", "deck-qbr-data", "gate-deck-xtsy-qcomm", "--repeat", "2",
                                     "--label", "t", "--workers", "3"])
    assert cpo.main() == 0
    runs = json.loads((tmp_path / "t" / "runs.json").read_text(encoding="utf-8"))
    assert [(r["case"], r["repeat"]) for r in runs] == [("deck-qbr-data", 1), ("deck-qbr-data", 2),
                                                        ("gate-deck-xtsy-qcomm", 1), ("gate-deck-xtsy-qcomm", 2)]
    assert runs[1]["error"] == "rate limit" and "error" not in runs[0]
    assert peak[0] > 1
    assert (tmp_path / "t" / "summary.md").exists()
