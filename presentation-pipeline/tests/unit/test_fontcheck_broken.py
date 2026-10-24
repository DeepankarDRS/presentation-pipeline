"""scripts/experiments/phase0b/fontcheck.broken: a word drawn over several lines counts (same-plan pair 1.4 scored 0)."""
import pytest

pytest.importorskip("pymupdf")
from scripts.experiments.phase0b.fontcheck import broken  # noqa: E402


def w(x, y0, y1, text, block, line):
    return (x, y0, x + 40, y1, text, block, line, 0)


def test_word_split_over_three_lines_counts():
    words = [w(48, 348, 361, "FLIP", 5, 0), w(48, 362, 374, "CAR", 5, 1), w(48, 375, 388, "T", 5, 2)]
    assert broken(words, {"flipcart", "roas"}) == ["FLIP|CAR|T"]


def test_last_letters_merged_with_the_number_below_count():
    words = [w(48, 389, 402, "ROA", 5, 3), w(48, 381, 415, "S0.", 5, 4)]
    assert broken(words, {"roas", "0.34"}) == ["ROA|S0.…"]


def test_two_piece_break_and_normal_breaks():
    vocab = {"structural", "data-driven", "issue"}
    assert broken([w(0, 0, 10, "struc", 0, 0), w(0, 12, 22, "tural", 0, 1)], vocab) == ["struc|tural"]
    assert broken([w(0, 0, 10, "data-", 0, 0), w(0, 12, 22, "driven", 0, 1)], vocab) == []   # hyphen break
    assert broken([w(0, 0, 10, "issue", 0, 0), w(0, 12, 22, "structural", 0, 1)], vocab) == []   # whole words
    assert broken([w(0, 0, 10, "₹", 0, 0), w(9, 0, 10, "struc", 0, 1)], vocab) == []          # same line
