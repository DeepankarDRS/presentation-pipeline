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

Lightness is changed in HLS (hue kept), never by mixing toward the ink colour:
mixing turns saturated orange into brown.
"""

from __future__ import annotations

import colorsys
from typing import Any

STATUS_ROLES = ("accent", "positive", "negative", "warning")
DERIVED_KEYS = tuple(f"{r}Soft" for r in STATUS_ROLES) + tuple(
    f"{r}Text" for r in STATUS_ROLES) + ("onAccent", "neutral", "border")

TEXT_MIN = 4.5
BORDER_MIN = 1.4
SOFT_MIX_LIGHT = 0.13
SOFT_MIX_DARK = 0.22
NEUTRAL_MIX_LIGHT = 0.22
NEUTRAL_MIX_DARK = 0.32


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
    return out
