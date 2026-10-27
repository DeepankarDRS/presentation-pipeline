"""Derived colour roles for a palette (2026-10-07, docs/palette-quality-research-2026-10-06.md §5.2).

A palette in palettes.yaml authors 10-12 colours. Code derives the rest by a
rule that guarantees contrast, so no recipe or prompt needs a literal hex:

  <role>Soft   pale fill of accent / positive / negative / warning
               (highlighted row, badge, delta chip, callout)
  <role>Text   the same hue, lightness stepped until it reads as small text
               (>= 4.5:1) on surface, surfaceAlt and its own Soft fill
  onAccent     text on an accent fill (white when it passes, else the best ink)
  neutral      grey for "everything else" (non-focus series, bars, dots);
               a palette may author its own
  panelDark    a fill that is dark on EVERY palette (an inverted / focus panel; on a
               dark palette $textMain is light): light palettes -> textMain, dark
               palettes -> the accent hue at PANEL_DARK_L lightness (a deep tint
               that reads apart from the neutral slide by hue, not lightness)
  onPanelDark  text on panelDark (>= 4.5:1). Both may be authored (authored wins;
               KPI pilot V7, docs/kpi-node-pilot-2026-10-11.md §5)

Lightness is changed in HLS (hue kept), never by mixing toward the ink colour:
mixing turns saturated orange into brown.
"""

from __future__ import annotations

import colorsys
import functools
import re
from typing import Any

STATUS_ROLES = ("accent", "positive", "negative", "warning")
DERIVED_KEYS = tuple(f"{r}Soft" for r in STATUS_ROLES) + tuple(
    f"{r}Text" for r in STATUS_ROLES) + ("onAccent", "neutral", "border", "panelDark", "onPanelDark")

TEXT_MIN = 4.5
BORDER_MIN = 1.4
SOFT_MIX_LIGHT = 0.13
SOFT_MIX_DARK = 0.22
NEUTRAL_MIX_LIGHT = 0.22
NEUTRAL_MIX_DARK = 0.32
PANEL_DARK_L = 0.2


def _rgb(hex_: str) -> tuple[float, float, float]:
    h = hex_.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(rgb: tuple[float, float, float]) -> str:
    return "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def luminance(hex_: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)))
    return (lb + 0.05) / (la + 0.05)


def mix(color: str, base: str, amount: float) -> str:
    """`amount` of `color` laid over `base` (0 = base, 1 = color)."""
    c, b = _rgb(color), _rgb(base)
    return _hex(tuple(bb + (cc - bb) * amount for cc, bb in zip(c, b)))  # type: ignore[arg-type]


def _step_lightness(color: str, backgrounds: list[str], darken: bool, target: float = TEXT_MIN) -> str:
    """Move `color`'s HLS lightness (hue and saturation kept) until it reaches
    `target` on every background. Unchanged if it already passes."""
    if all(contrast(color, bg) >= target for bg in backgrounds):
        return color.upper()
    h, l, s = colorsys.rgb_to_hls(*_rgb(color))
    step = -0.01 if darken else 0.01
    while 0.0 < l < 1.0:
        l = max(0.0, min(1.0, l + step))
        cand = _hex(colorsys.hls_to_rgb(h, l, s))
        if all(contrast(cand, bg) >= target for bg in backgrounds):
            return cand
    return _hex(colorsys.hls_to_rgb(h, l, s))


def _with_lightness(color: str, lightness: float) -> str:
    h, l, s = colorsys.rgb_to_hls(*_rgb(color))
    return _hex(colorsys.hls_to_rgb(h, min(l, lightness), s))


def derive_tokens(palette: dict[str, Any]) -> dict[str, str]:
    """Return the derived tokens for one palette entry (authored `neutral` wins)."""
    dark = palette.get("mode") == "dark"
    surface, surface_alt = palette["surface"], palette["surfaceAlt"]
    text_main = palette["textMain"]
    out: dict[str, str] = {}

    for role in STATUS_ROLES:
        soft = mix(palette[role], surface_alt, SOFT_MIX_DARK if dark else SOFT_MIX_LIGHT)
        out[f"{role}Soft"] = soft
        out[f"{role}Text"] = _step_lightness(
            palette[role], [surface, surface_alt, soft], darken=not dark)

    accent = palette["accent"]
    # white first, then the palette's own ink, then whatever reads best
    ink = surface if dark else text_main
    for cand in ("FFFFFF", ink):
        if contrast(cand, accent) >= TEXT_MIN:
            out["onAccent"] = cand.upper()
            break
    else:
        out["onAccent"] = max((text_main, surface, "FFFFFF", "111111"),
                              key=lambda c: contrast(c, accent)).upper()

    # a card must read as a card: its hairline >= BORDER_MIN on the slide AND on the card
    # (corporate-slate's E2E8F0 was 1.17:1 on F7F9FC; the critic called white cards "flat",
    # run 5fb8a2, 2026-10-07). Same hue, only the lightness moves.
    out["border"] = _step_lightness(palette["border"], [surface, surface_alt], darken=not dark,
                                    target=BORDER_MIN)

    out["neutral"] = (palette.get("neutral") or mix(
        text_main, surface, NEUTRAL_MIX_DARK if dark else NEUTRAL_MIX_LIGHT)).upper()

    panel = palette.get("panelDark") or (
        _with_lightness(accent, PANEL_DARK_L) if dark else text_main)
    out["panelDark"] = panel.upper()
    out["onPanelDark"] = (palette.get("onPanelDark") or max(
        (surface, text_main, "FFFFFF"), key=lambda c: contrast(c, panel))).upper()
    return out


# --- seed palettes (2026-10-22) ------------------------------------------------
# A palette may be written as a `seed:` of brand colours instead of every token
# (palettes.yaml). expand_seed() turns it into an ordinary authored entry, which
# then goes through derive_tokens() like any other palette.

SEED_TEXT_MIN = 4.5     # textMain / textMuted on surface + surfaceAlt
SEED_ACCENT_MIN = 3.0   # accent / accentAlt / positive / negative / warning (the *Text tokens cover small text)
CHART_MIN = 2.0         # a chart series on the surface the chart is drawn on
CHART_MIN_DELTA_E = 15.0
MAX_CHART_COLORS = 6
_SEMANTIC_DEFAULTS = {
    "light": {"positive": "15803D", "negative": "DC2626", "warning": "B45309"},
    "dark": {"positive": "4ADE80", "negative": "F87171", "warning": "FBBF24"},
}
_RGBA_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", re.I)


def parse_color(value: Any, background: str = "FFFFFF") -> str:
    """CSS-style colour -> 6-digit hex. Alpha (#RRGGBBAA, rgba()) is laid over `background`:
    POM tokens are 6-digit hex only."""
    s = str(value).strip()
    m = _RGBA_RE.fullmatch(s)
    if m:
        rgb = _hex(tuple(int(m.group(i)) / 255 for i in (1, 2, 3)))  # type: ignore[arg-type]
        return mix(rgb, background, float(m.group(4)) if m.group(4) is not None else 1.0)
    s = s.lstrip("#").upper()
    if len(s) == 8:
        return mix(s[:6], background, int(s[6:], 16) / 255)
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if not re.fullmatch(r"[0-9A-F]{6}", s):
        raise ValueError(f"not a colour: {value!r}")
    return s


def guard_chart_colors(colors: list[str], chart_bg: str) -> list[str]:
    """Up to MAX_CHART_COLORS legible, distinguishable series colours, in the given order.
    Each is stepped (hue kept) to CHART_MIN on the chart surface — lime on cream would
    vanish; one that lands too close to an earlier pick is skipped."""
    from src.compiler.theme_swap import _lab     # lazy: theme_swap imports the normalizer

    darken = luminance(chart_bg) >= 0.5
    picked: list[str] = []
    for c in colors:
        c = _step_lightness(c, [chart_bg], darken=darken, target=CHART_MIN)
        lab = _lab(c)
        if all(sum((x - y) ** 2 for x, y in zip(lab, _lab(p))) ** 0.5 >= CHART_MIN_DELTA_E for p in picked):
            picked.append(c)
        if len(picked) == MAX_CHART_COLORS:
            break
    return picked


def expand_seed(seed: dict[str, Any]) -> dict[str, Any]:
    """A seed (mode, background, ink, accent + optional card, muted, border, accentAlt,
    positive, negative, warning, neutral, chart) -> a full authored palette entry.

    Missing colours are mixed from background and ink; text and accent colours are stepped
    in lightness until they meet SEED_TEXT_MIN / SEED_ACCENT_MIN on surface and surfaceAlt."""
    mode = seed.get("mode", "light")
    dark = mode == "dark"
    bg = parse_color(seed["background"])

    def color(key: str) -> str | None:
        return parse_color(seed[key], bg) if seed.get(key) else None

    ink = parse_color(seed["ink"], bg)
    card = color("card") or (mix(ink, bg, 0.08) if dark else ("FFFFFF" if bg != "FFFFFF" else mix(ink, bg, 0.03)))
    out: dict[str, Any] = {
        "mode": mode, "surface": bg, "surfaceAlt": card, "textMain": ink,
        "textMuted": color("muted") or mix(bg, ink, 0.38),
        "border": color("border") or mix(ink, bg, 0.2 if dark else 0.12),
        "accent": color("accent"),
    }
    chart_seed = [parse_color(c, bg) for c in seed.get("chart") or []]
    out["accentAlt"] = color("accentAlt") or (chart_seed[1] if len(chart_seed) > 1 else mix(ink, out["accent"], 0.3))
    taken = {out["accent"]}
    for role, default in _SEMANTIC_DEFAULTS[mode].items():
        c = color(role)
        # house-style color_roles (A4): never two meanings in one colour
        out[role] = c if c and c not in taken else default
        taken.add(out[role])
    if color("neutral"):
        out["neutral"] = color("neutral")

    surfaces = [bg, card]
    for k in ("textMain", "textMuted"):
        out[k] = _step_lightness(out[k], surfaces, darken=not dark, target=SEED_TEXT_MIN)
    for k in ("accent", "accentAlt", "positive", "negative", "warning"):
        out[k] = _step_lightness(out[k], surfaces, darken=not dark, target=SEED_ACCENT_MIN)

    if dark:   # charts sit on a light card there (POM draws axis text black)
        out["chartSurface"] = mix("FFFFFF", out["textMain"], 0.5)
        out["chartInk"] = card
    chart_bg = out.get("chartSurface", card)
    fallback = [out[k] for k in ("accent", "accentAlt", "positive", "warning", "negative", "textMuted")]
    out["chartColors"] = guard_chart_colors(chart_seed + fallback, chart_bg)
    return out


# --- chart series and polarity checks (2026-10-22 chart pass, docs/chart-pass-2026-10-22.md) ----
# Measured with the dataviz skill's validator (src/compiler/dataviz_palette.py): OKLCH lightness band and
# chroma floor per series, adjacent series apart for colour-blind (Machado 2009 protan / deutan) and
# normal vision, and apart in lightness (palette research §5.4, A7). Code repairs a palette's
# chartColors instead of hand-editing hexes: hue kept, lightness moved into the band and away from
# its neighbour, chroma raised to the floor, order chosen to keep every neighbour apart. Every chart
# here sits on a light surface ($chartSurface on dark palettes), so the light band applies.

SERIES_BAND = (0.45, 0.75)       # OKLCH L, inside the validator's light band (0.43-0.77)
SERIES_CHROMA_MIN = 0.10         # validator CHROMA_FLOOR
SERIES_GREY_C = 0.03             # below this a colour has no hue to keep: $neutral's job, dropped
SERIES_CVD_MIN = 8.0             # validator CVD_TARGET (min of protan / deutan, OKLab x100)
SERIES_NORMAL_MIN = 15.0         # validator NORMAL_FLOOR
SERIES_LIGHTNESS_MIN = 1.4       # adjacent series, contrast ratio of their lightness (§5.4 rule 2)
POLARITY_LIGHTNESS_MIN = 1.3     # positive vs negative (§5.5, A6)
POLARITY_CVD_MIN = 8.0


def _okl():
    from src.compiler import dataviz_palette     # lazy, like guard_chart_colors' theme_swap import
    return dataviz_palette


def _oklch_hex(L: float, C: float, h: float) -> str | None:
    """OKLCH -> hex, or None when it falls outside sRGB."""
    import math
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    if any(c < -1e-4 or c > 1 + 1e-4 for c in rgb):
        return None
    v = _okl()
    return _hex(tuple(v.lin2s(c) for c in rgb))  # type: ignore[arg-type]


def _lch(hex_: str) -> tuple[float, float, float]:
    import math
    L, a, b = _okl().lin2oklab(*_okl().lin(hex_))
    return L, math.hypot(a, b), math.atan2(b, a)


def _with_ok_lightness(hex_: str, L: float, c_min: float = 0.0) -> str | None:
    """`hex_` at OKLCH lightness L, hue kept; chroma raised to c_min, lowered only to fit sRGB."""
    _, C, h = _lch(hex_)
    C = max(C, c_min)
    while C >= c_min:
        out = _oklch_hex(L, C, h)
        if out:
            return out
        C -= 0.005
    return None


def _apart(a: str, b: str, cvd: float, normal: float, lightness: float) -> bool:
    v = _okl()
    return (contrast(a, b) >= lightness and v.deltaE(a, b) >= normal
            and min(v.deltaE(a, b, k) for k in ("protan", "deutan")) >= cvd)


def series_report(colors: list[str], chart_bg: str) -> dict[str, Any]:
    """The checks chart series must pass, for the unit tests and the chart-pass doc."""
    v = _okl()
    pairs = list(zip(colors, colors[1:]))
    every = [(a, b) for i, a in enumerate(colors) for b in colors[i + 1:]]
    return {
        "band": all(SERIES_BAND[0] - 0.02 <= _lch(c)[0] <= SERIES_BAND[1] + 0.02 for c in colors),
        "chroma": min(_lch(c)[1] for c in colors) if colors else 0.0,
        "cvd": min((min(v.deltaE(a, b, k) for k in ("protan", "deutan")) for a, b in pairs), default=99.0),
        "normal": min((v.deltaE(a, b) for a, b in pairs), default=99.0),
        "normal_any": min((v.deltaE(a, b) for a, b in every), default=99.0),
        "lightness": min((contrast(a, b) for a, b in pairs), default=99.0),
        "on_surface": min((contrast(c, chart_bg) for c in colors), default=99.0),
    }


def separate_chart_colors(colors: list[str], chart_bg: str) -> list[str]:
    """A palette's chartColors made separable: the first (the accent's hue) stays first, the rest
    are re-ordered and lightness-stepped so every neighbour passes the series checks; a colour no
    step can fit is dropped. Unchanged colours stay exactly as authored."""
    return list(_separate(tuple(c.upper() for c in colors), chart_bg.upper()))


@functools.lru_cache(maxsize=64)
def _separate(colors: tuple[str, ...], chart_bg: str) -> tuple[str, ...]:
    import itertools
    v = _okl()
    lo, hi = SERIES_BAND
    steps = [round(lo + i * 0.02, 2) for i in range(int(round((hi - lo) / 0.02)) + 1)]

    def options(c: str) -> list[str]:
        """Candidates for one series, nearest its own lightness first (as authored when it passes)."""
        L, C, _ = _lch(c)
        if C < SERIES_GREY_C:
            return []
        own = [c] if lo <= L <= hi and C >= SERIES_CHROMA_MIN else []
        cands = [x for s in sorted(steps, key=lambda s: abs(s - L))
                 if (x := _with_ok_lightness(c, s, SERIES_CHROMA_MIN + 0.005))]   # margin for hex rounding
        return [x for x in own + cands if contrast(x, chart_bg) >= CHART_MIN]

    opts = {c: options(c) for c in dict.fromkeys(colors)}
    first, rest = colors[0], [c for c in dict.fromkeys(colors[1:]) if c != colors[0]]
    best: tuple[tuple[float, ...], tuple[str, ...]] | None = None
    for order in itertools.permutations(rest):
        picked: list[str] = []
        moved = 0.0
        for c in (first, *order):
            fit = next((x for x in opts[c] if not picked or (_apart(
                picked[-1], x, SERIES_CVD_MIN, SERIES_NORMAL_MIN, SERIES_LIGHTNESS_MIN) and all(
                    v.deltaE(p, x) >= SERIES_NORMAL_MIN for p in picked))), None)
            if fit:
                moved += abs(_lch(fit)[0] - _lch(c)[0])
                picked.append(fit)
        score = (len(picked), picked[:1] == opts[first][:1], -moved)
        if best is None or score > best[0]:
            best = (score, tuple(picked))
    return best[1] if best and best[1] else colors[:1]


def separate_polarity(palette: dict[str, Any]) -> dict[str, str]:
    """positive / negative apart in lightness and for colour-blind readers (A6). The smallest
    lightness step (hue kept) of either colour that passes, keeping it >= SEED_ACCENT_MIN on surface
    and surfaceAlt; as authored when they already pass."""
    pos, neg = str(palette["positive"]).upper(), str(palette["negative"]).upper()
    surfaces = [palette["surface"], palette["surfaceAlt"]]

    def ok(p: str, n: str) -> bool:
        return _apart(p, n, POLARITY_CVD_MIN, 0.0, POLARITY_LIGHTNESS_MIN)

    if ok(pos, neg):
        return {"positive": pos, "negative": neg}
    for i in range(1, 41):
        for which in ("positive", "negative"):
            for sign in (-1, 1):
                c = pos if which == "positive" else neg
                cand = _with_ok_lightness(c, _lch(c)[0] + sign * i * 0.01)
                if not cand or min(contrast(cand, bg) for bg in surfaces) < SEED_ACCENT_MIN:
                    continue
                pair = (cand, neg) if which == "positive" else (pos, cand)
                if ok(*pair):
                    return {"positive": pair[0], "negative": pair[1]}
    return {"positive": pos, "negative": neg}
