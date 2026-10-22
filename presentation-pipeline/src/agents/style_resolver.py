"""Style resolver — loosely-coupled theme resolution.

Public API:
  resolve_theme(theme_name) → dict   # callable from any node
  derive_tokens(seed) → (tokens, chart_colors)
  DEFAULT_THEME                       # fallback constant

Graph node:
  style_resolver_node(state) → {theme_element, resolved_theme}

Reads:  theme_name
Writes: theme_element, resolved_theme

Palettes come in two forms (src/knowledge/theme/palettes.yaml):
  - full:  every token written out by hand — used verbatim.
  - seed:  a handful of brand colors (mode, background, ink, accent, ...);
           the rest is derived and every text/accent token is contrast-repaired
           against the surfaces it sits on. Seed colors may be CSS-style
           (#RRGGBB, #RRGGBBAA, rgba(r,g,b,a)) — alpha is flattened over the
           background, since POM tokens are 6-digit hex only.
Every resolved theme also carries chartSurface/chartInk and chart1..chartN
tokens, so chartColors can reference $chart1... (POM resolves tokens there).
"""

from __future__ import annotations

import colorsys
import functools
import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from src.state import PresentationState

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@functools.lru_cache(maxsize=8)
def _load_yaml(relpath: str) -> dict[str, Any]:
    path = _KNOWLEDGE_DIR / relpath
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


_TOKEN_KEYS = [
    "surface", "surfaceAlt", "accent", "accentAlt",
    "positive", "negative", "warning",
    "textMain", "textMuted", "border",
    "chartSurface", "chartInk",
]
MAX_CHART_TOKENS = 5

# --- color math ---------------------------------------------------------------

_RGBA_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", re.I)


def _rgb(hex_: str) -> tuple[float, float, float]:
    return tuple(int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(rgb: tuple[float, float, float]) -> str:
    return "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    """Blend hex a toward hex b by t (0 = a, 1 = b)."""
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))))  # type: ignore[arg-type]


def parse_color(value: Any, background: str = "FFFFFF") -> str:
    """Normalize a seed color to 6-digit hex, flattening any alpha over background."""
    s = str(value).strip()
    m = _RGBA_RE.fullmatch(s)
    if m:
        rgb = _hex(tuple(int(m.group(i)) / 255 for i in (1, 2, 3)))  # type: ignore[arg-type]
        alpha = float(m.group(4)) if m.group(4) is not None else 1.0
        return mix(background, rgb, alpha)
    s = s.lstrip("#").upper()
    if len(s) == 8:
        return mix(background, s[:6], int(s[6:], 16) / 255)
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if not re.fullmatch(r"[0-9A-F]{6}", s):
        raise ValueError(f"not a color: {value!r}")
    return s


def luminance(hex_: str) -> float:
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in _rgb(hex_)]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def ensure_contrast(color: str, backgrounds: list[str], minimum: float, dark: bool) -> str:
    """Shift color's lightness (keeping hue) until it reaches minimum on every background.

    Light themes darken, dark themes lighten. Returns color unchanged if it passes.
    """
    h, l, s = colorsys.rgb_to_hls(*_rgb(color))
    step = 0.02 if dark else -0.02
    out = color
    while min(contrast(out, bg) for bg in backgrounds) < minimum and 0.0 < l < 1.0:
        l = max(0.0, min(1.0, l + step))
        out = _hex(colorsys.hls_to_rgb(h, l, s))
    return out


# --- seeds -------------------------------------------------------------------

_SEMANTIC_DEFAULTS = {
    "light": {"positive": "15803D", "negative": "DC2626", "warning": "B45309"},
    "dark": {"positive": "4ADE80", "negative": "F87171", "warning": "FBBF24"},
}
TEXT_MIN = 4.5      # textMain / textMuted on surface + surfaceAlt
ACCENT_MIN = 3.0    # accent / semantic tokens on surface + surfaceAlt
CHART_MIN = 2.0     # each chart series on the surface the chart is drawn on


def derive_tokens(seed: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Expand a seed palette into the full token set + chart colors.

    Required: mode, background, ink, accent. Optional: card, muted, border,
    accentAlt, positive, negative, warning, chart (list).
    """
    mode = seed.get("mode", "light")
    dark = mode == "dark"
    bg = parse_color(seed["background"])
    color = functools.partial(parse_color, background=bg)
    ink = color(seed["ink"])

    t: dict[str, str] = {"surface": bg, "textMain": ink}
    t["surfaceAlt"] = color(seed["card"]) if seed.get("card") else (
        mix(bg, ink, 0.08) if dark else ("FFFFFF" if bg != "FFFFFF" else mix(bg, ink, 0.03))
    )
    t["textMuted"] = color(seed["muted"]) if seed.get("muted") else mix(ink, bg, 0.38)
    t["border"] = color(seed["border"]) if seed.get("border") else mix(bg, ink, 0.2 if dark else 0.12)

    accent = color(seed["accent"])
    chart_seed = [color(c) for c in seed.get("chart") or []]
    t["accent"] = accent
    t["accentAlt"] = color(seed["accentAlt"]) if seed.get("accentAlt") else (
        chart_seed[1] if len(chart_seed) > 1 else mix(accent, ink, 0.3)
    )
    for k, v in _SEMANTIC_DEFAULTS[mode].items():
        t[k] = color(seed[k]) if seed.get(k) else v

    surfaces = [t["surface"], t["surfaceAlt"]]
    for k in ("textMain", "textMuted"):
        t[k] = ensure_contrast(t[k], surfaces, TEXT_MIN, dark)
    for k in ("accent", "accentAlt", "positive", "negative", "warning"):
        t[k] = ensure_contrast(t[k], surfaces, ACCENT_MIN, dark)

    # Dark: charts sit on a light card (POM draws axis text black).
    t["chartSurface"] = mix(ink, "FFFFFF", 0.5) if dark else t["surfaceAlt"]
    t["chartInk"] = t["surfaceAlt"] if dark else t["textMain"]

    fallback = [t[k] for k in ("accent", "accentAlt", "positive", "warning", "negative", "textMuted")]
    return t, guard_chart_colors(chart_seed + fallback, t["chartSurface"])


CHART_MIN_DELTA_E = 15.0  # series closer than this read as the same color


def guard_chart_colors(colors: list[str], chart_bg: str) -> list[str]:
    """Pick up to MAX_CHART_TOKENS legible, distinguishable series colors, in order.

    Each color is repaired in place to CHART_MIN on the chart surface (lime on
    cream would vanish); repaired colors that land too close to an earlier
    pick are skipped, so trailing fallbacks fill the gap.
    """
    from src.compiler.theme_swap import _lab

    dark_bg = luminance(chart_bg) < 0.5
    picked: list[str] = []
    for c in colors:
        c = ensure_contrast(c, [chart_bg], CHART_MIN, dark_bg)
        lab = _lab(c)
        if all(sum((x - y) ** 2 for x, y in zip(lab, _lab(p))) ** 0.5 >= CHART_MIN_DELTA_E for p in picked):
            picked.append(c)
        if len(picked) == MAX_CHART_TOKENS:
            break
    return picked


# --- resolution ----------------------------------------------------------------

def _build_theme(name: str, tokens: dict[str, str], mode: str, chart_colors: list[str]) -> dict[str, Any]:
    tokens = dict(tokens)
    # Light palettes omit chart tokens; define them so a $chartSurface wrapper
    # (e.g. left over after switching from a dark theme) still resolves.
    tokens.setdefault("chartSurface", tokens.get("surfaceAlt", "FFFFFF"))
    tokens.setdefault("chartInk", tokens.get("textMain", "16202E"))
    chart_colors = [str(c).lstrip("#").upper() for c in chart_colors][:MAX_CHART_TOKENS]

    attrs = [f'{k}="{tokens[k]}"' for k in _TOKEN_KEYS if k in tokens]
    attrs += [f'chart{i}="{c}"' for i, c in enumerate(chart_colors, 1)]
    chart_refs = [f"$chart{i}" for i in range(1, len(chart_colors) + 1)]
    return {
        "name": name,
        "mode": mode,
        "is_dark": mode == "dark",
        "chart_colors": chart_colors,
        "chart_tokens": chart_refs,
        "chart_colors_json": json.dumps(chart_refs, separators=(",", ":")),
        "element": f"<Theme {' '.join(attrs)} />",
    }


DEFAULT_THEME: dict[str, Any] = _build_theme(
    "corporate-slate",
    {
        "surface": "F7F9FC", "surfaceAlt": "FFFFFF", "accent": "2563EB", "accentAlt": "0EA5E9",
        "positive": "15803D", "negative": "DC2626", "warning": "B45309",
        "textMain": "16202E", "textMuted": "55627A", "border": "E2E8F0",
        "chartSurface": "FFFFFF", "chartInk": "334155",
    },
    "light",
    ["2563EB", "0EA5E9", "14B8A6", "6366F1", "F59E0B"],
)


def palette_names() -> list[str]:
    return list((_load_yaml("theme/palettes.yaml").get("palettes") or {}).keys())


@functools.lru_cache(maxsize=64)
def _resolve_cached(theme_name: str) -> str:
    palette = (_load_yaml("theme/palettes.yaml").get("palettes") or {}).get(theme_name)
    if not palette:
        logger.warning(f"theme '{theme_name}' not found, using default")
        return json.dumps(DEFAULT_THEME)
    try:
        if "seed" in palette:
            seed = palette["seed"]
            tokens, chart = derive_tokens(seed)
            mode = seed.get("mode", "light")
        else:
            tokens = {k: str(palette[k]) for k in _TOKEN_KEYS if k in palette}
            mode = palette.get("mode", "light")
            chart = palette.get("chartColors") or DEFAULT_THEME["chart_colors"]
    except (KeyError, ValueError) as e:
        logger.warning(f"theme '{theme_name}' is invalid ({e}), using default")
        return json.dumps(DEFAULT_THEME)
    return json.dumps(_build_theme(theme_name, tokens, mode, chart))


def resolve_theme(theme_name: str) -> dict[str, Any]:
    """Resolve a theme name to a full theme dict.

    Returns: {name, mode, is_dark, chart_colors, chart_tokens, chart_colors_json, element}
    Callable from any node — not coupled to the graph. Always a fresh copy.
    """
    if not theme_name or theme_name == "corporate-slate":
        return json.loads(json.dumps(DEFAULT_THEME))
    return json.loads(_resolve_cached(theme_name))


def style_resolver_node(state: PresentationState) -> dict[str, Any]:
    """LangGraph node: resolve theme and write to state."""
    theme_name = state.get("theme_name", "")
    theme = resolve_theme(theme_name)
    logger.info(f"style_resolver: {theme['name']} ({theme['mode']})")
    return {
        "theme_element": theme["element"],
        "resolved_theme": theme,
    }
