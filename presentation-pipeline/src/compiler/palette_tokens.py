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
