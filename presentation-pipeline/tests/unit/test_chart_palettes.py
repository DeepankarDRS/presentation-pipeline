"""Chart series and positive / negative colours on every palette (2026-10-22 chart pass,
docs/chart-pass-2026-10-22.md), measured with the dataviz skill's validator
(src/compiler/dataviz_palette.py, a verbatim copy). Seed palettes are checked as they resolve."""

from __future__ import annotations

import pytest

from src.agents.style_resolver import palette_entry, resolve_theme, theme_names
from src.compiler import dataviz_palette as dv
from src.compiler.palette_tokens import (
    CHART_MIN, POLARITY_CVD_MIN, POLARITY_LIGHTNESS_MIN, SEED_ACCENT_MIN, SERIES_CVD_MIN,
    SERIES_LIGHTNESS_MIN, SERIES_NORMAL_MIN, contrast, separate_chart_colors, separate_polarity,
)
from src.compiler.theme_swap import theme_tokens

NAMES = sorted(theme_names())


def _theme(name: str) -> tuple[dict, dict]:
    t = resolve_theme(name)
    return t, theme_tokens(t["element"])


@pytest.mark.parametrize("name", NAMES)
def test_chart_series_pass_the_dataviz_validator(name):
    """$chart1..$chartN: lightness band, chroma floor, adjacent colour-blind and normal-vision gaps."""
    t, tok = _theme(name)
    colors = ["#" + c for c in t["chart_colors"]]
    report, ok = dv.validate(colors, "light", "#" + tok["chartSurface"])
    assert ok, (name, report)
    cvd = dict((r[0], r[1]) for r in report)["CVD separation"]
    assert cvd == "pass", (name, report)          # the 8.0 target, not only the 6.0 floor


@pytest.mark.parametrize("name", NAMES)
def test_chart_series_separable_by_lightness(name):
    """Neighbouring series differ by >= 1.4:1 in lightness (greyscale print, projectors; §5.4)."""
    cols = resolve_theme(name)["chart_colors"]
    for a, b in zip(cols, cols[1:]):
        assert contrast(a, b) >= SERIES_LIGHTNESS_MIN - 1e-6, (name, a, b, round(contrast(a, b), 2))


@pytest.mark.parametrize("name", NAMES)
def test_no_two_chart_series_look_alike(name):
    """Any two series (a line chart shows them all at once) stay apart for full-colour readers."""
    cols = resolve_theme(name)["chart_colors"]
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            assert dv.deltaE(a, b) >= SERIES_NORMAL_MIN, (name, a, b)


@pytest.mark.parametrize("name", NAMES)
def test_chart_series_count_and_first_hue(name):
    t, tok = _theme(name)
    cols = t["chart_colors"]
    assert 2 <= len(cols) <= 6, (name, cols)
    assert len(t["chart_tokens"]) == len(cols)
    for c in cols:
        assert contrast(c, tok["chartSurface"]) >= CHART_MIN
    # chart1 keeps the hue of the palette's first authored chart colour (the accent's role)
    first = str((palette_entry(name).get("chartColors") or [palette_entry(name)["accent"]])[0]).upper()
    hue = lambda h: dv.lin2oklch(*dv.lin(h))  # noqa: E731
    import math
    a1 = math.atan2(*reversed(dv.lin2oklab(*dv.lin(first))[1:]))
    a2 = math.atan2(*reversed(dv.lin2oklab(*dv.lin(cols[0]))[1:]))
    assert abs(math.degrees(math.remainder(a1 - a2, 2 * math.pi))) < 8, (name, first, cols[0], hue(first))


@pytest.mark.parametrize("name", NAMES)
def test_positive_and_negative_apart(name):
    """A6: good and bad marks differ in lightness (>= 1.3:1) and for colour-blind readers."""
    _, tok = _theme(name)
    pos, neg = tok["positive"], tok["negative"]
    assert contrast(pos, neg) >= POLARITY_LIGHTNESS_MIN - 1e-6, (name, pos, neg)
    assert min(dv.deltaE(pos, neg, k) for k in ("protan", "deutan")) >= POLARITY_CVD_MIN, (name, pos, neg)
    for c in (pos, neg):
        for bg in (tok["surface"], tok["surfaceAlt"]):
            assert contrast(c, bg) >= SEED_ACCENT_MIN - 0.05, (name, c, bg)


@pytest.mark.parametrize("name", NAMES)
def test_focus_pair_reads_apart(name):
    """$accent on the focus bar against $neutral on the rest: plainly different on the chart card."""
    _, tok = _theme(name)
    assert dv.deltaE(tok["accent"], tok["neutral"]) >= SERIES_NORMAL_MIN, name
    assert min(dv.deltaE(tok["accent"], tok["neutral"], k) for k in ("protan", "deutan")) >= SERIES_CVD_MIN, name


def test_passing_series_are_kept_as_authored():
    good = ["2563EB", "ED990F", "199E8F"]
    assert dv.validate(["#" + c for c in good], "light", "#FFFFFF")[1]
    assert separate_chart_colors(good, "FFFFFF") == good


def test_greys_are_dropped_and_dark_inks_stepped_into_the_band():
    out = separate_chart_colors(["0E7C7B", "141413", "B0AEA5", "12302F"], "FFFFFF")
    assert "141413" not in out and "B0AEA5" not in out
    assert all(0.43 <= dv.oklch(c)[0] <= 0.77 for c in out)


def test_polarity_kept_when_already_apart():
    p = {"positive": "4ADE80", "negative": "C7572C", "surface": "0E1116", "surfaceAlt": "1A1F2A"}
    assert separate_polarity(p) == {"positive": "4ADE80", "negative": "C7572C"}
