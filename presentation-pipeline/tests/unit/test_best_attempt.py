"""Tests for best-of-N attempt tracking."""

from src.agents.best_attempt import keep_best_attempt, score_attempt


def test_score_non_candidates():
    assert score_attempt(compile_ok=False, critic_passed=True, high_count=0,
                          attempt=0, truncated=False) == [0, 0, 0, 0]
    assert score_attempt(compile_ok=True, critic_passed=True, high_count=0,
                          attempt=0, truncated=True) == [0, 0, 0, 0]


def test_score_ordering():
    passed = score_attempt(compile_ok=True, critic_passed=True, high_count=0, attempt=2, truncated=False)
    two_high = score_attempt(compile_ok=True, critic_passed=False, high_count=2, attempt=1, truncated=False)
    one_high = score_attempt(compile_ok=True, critic_passed=False, high_count=1, attempt=3, truncated=False)
    assert passed > one_high > two_high


def test_score_earliest_wins_ties():
    early = score_attempt(compile_ok=True, critic_passed=False, high_count=1, attempt=1, truncated=False)
    late = score_attempt(compile_ok=True, critic_passed=False, high_count=1, attempt=3, truncated=False)
    assert early > late


def test_keep_best_records_better_attempt():
    state = {"retry_count": 2, "best_score": [1, 0, -3, 0], "generation_history": [{}]}
    updates = {
        "compile_result": {"ok": True},
        "critic_result": {"passed": False, "issues": [{"severity": "high"}]},  # 1 high
    }
    keep_best_attempt(state, updates)
    assert updates["best_attempt"] == 2
    assert updates["best_score"] == [1, 0, -1, -2]


def test_keep_best_ignores_worse_attempt():
    state = {"retry_count": 3, "best_score": [1, 1, 0, -1], "generation_history": [{}]}
    updates = {
        "compile_result": {"ok": True},
        "critic_result": {"passed": False, "issues": [{"severity": "high"}]},
    }
    keep_best_attempt(state, updates)
    assert "best_attempt" not in updates


def test_keep_best_skips_failed_compile():
    state = {"retry_count": 1, "best_score": [0, 0, 0, 0], "generation_history": [{}]}
    updates = {"compile_result": {"ok": False}}
    keep_best_attempt(state, updates)
    assert "best_attempt" not in updates


def test_keep_best_skips_truncated():
    state = {"retry_count": 1, "best_score": [0, 0, 0, 0],
             "generation_history": [{"truncated": True}]}
    updates = {"compile_result": {"ok": True}, "critic_result": {"passed": True, "issues": []}}
    keep_best_attempt(state, updates)
    assert "best_attempt" not in updates
