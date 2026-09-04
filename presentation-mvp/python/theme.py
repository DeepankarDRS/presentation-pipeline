"""Theme resolution: palette library -> a concrete <Theme> element.

The library lives in pom-knowledge/theme/palettes.yaml. A deck / slide picks a
palette by name (project-root theme.yaml, a test-case `theme:` field, or the
--theme CLI flag) and may override individual tokens.

Public surface:
    resolve(name=None, overrides=None)      -> ResolvedTheme
    theme_element(theme)                     -> "<Theme .../>" string
    contrast(hex_a, hex_b)                   -> float (WCAG ratio)
    verify(theme)                            -> list[str] of warnings
    available()                              -> [palette names]

Contrast failures are advisory: verify() returns warnings, and resolve() falls
back to the default palette only when a palette is so broken that its body text
would be unreadable (textMain vs surface below the 4.5:1 AA floor).
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any

import yaml

import config

_PALETTES_FILE = config.KNOWLEDGE_DIR / "theme" / "palettes.yaml"

# Order tokens are emitted in the <Theme> element. chartSurface / chartInk are
# only emitted when the palette defines them (dark palettes). chartColors is NOT
# a Theme attribute — it feeds <Chart chartColors='[...]'> — so it is carried on
# ResolvedTheme but never written into the element.
_COLOR_TOKENS = (
    "surface", "surfaceAlt", "accent", "accentAlt",
    "positive", "negative", "warning",
    "textMain", "textMuted", "border",
    "chartSurface", "chartInk",
)
_REQUIRED_TOKENS = (
    "surface", "surfaceAlt", "accent", "accentAlt",
    "positive", "negative", "warning",
    "textMain", "textMuted", "border",
)

# AA floor for body text; below this resolve() falls back to the default palette.
_READABILITY_FLOOR = 4.5


class ThemeError(ValueError):
    """Raised only for problems the caller must fix (e.g. no palettes file)."""


@dataclass
class ResolvedTheme:
    name: str
    mode: str                      # "light" | "dark"
    tokens: dict[str, str]         # token -> bare 6-digit hex
    chart_colors: list[str]        # literal hex for <Chart chartColors>
    warnings: list[str] = field(default_factory=list)
    fell_back: bool = False        # True if the requested palette was replaced

    @property
    def is_dark(self) -> bool:
        return self.mode == "dark"

    @property
    def chart_colors_json(self) -> str:
        """The value for chartColors='...' — a JSON array string of literal hex."""
        inner = ", ".join(f'"{c}"' for c in self.chart_colors)
        return f"[{inner}]"


# ── library loading ────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=1)
def _library() -> dict[str, Any]:
    if not _PALETTES_FILE.exists():
        raise ThemeError(
            f"palette library not found: {_PALETTES_FILE}. Expected it under "
            "pom-knowledge/theme/ (see palettes.yaml)."
        )
    data = yaml.safe_load(_PALETTES_FILE.read_text(encoding="utf-8")) or {}
    if not data.get("palettes"):
        raise ThemeError(f"{_PALETTES_FILE} has no `palettes:` map.")
    return data


def available() -> list[str]:
    return sorted(_library()["palettes"].keys())


def default_name() -> str:
    return str((_library().get("meta") or {}).get("default") or "corporate-slate")


# Back-compat: the old test cases / deck specs say `theme: dark` / `light`.
_LEGACY_ALIASES = {
    "dark": "graphite-dark",
    "light": "corporate-slate",
}


def canonical_name(name: str | None) -> str:
    """Map a user-supplied theme name to a real palette name (with aliases)."""
    if not name:
        return default_name()
    key = str(name).strip()
    return _LEGACY_ALIASES.get(key.lower(), key)


# ── colour maths (WCAG relative luminance) ─────────────────────────────────
def _luminance(hex6: str) -> float:
    h = hex6.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(hex_a: str, hex_b: str) -> float:
    la, lb = _luminance(hex_a), _luminance(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


_CONTRAST_CHECKS = (
    # (label, fg token, bg token, minimum)
    ("textMain / surface",    "textMain", "surface",    _READABILITY_FLOOR),
    ("textMain / surfaceAlt", "textMain", "surfaceAlt",  _READABILITY_FLOOR),
    ("textMuted / surface",   "textMuted", "surface",    3.0),
    ("accent / surface",      "accent",   "surface",     3.0),
)


def verify(theme: ResolvedTheme | dict[str, str], *, name: str = "") -> list[str]:
    """Return human-readable contrast warnings (empty list == all good)."""
    tokens = theme.tokens if isinstance(theme, ResolvedTheme) else dict(theme)
    label = name or getattr(theme, "name", "") or "palette"
    out: list[str] = []
    for desc, fg, bg, minimum in _CONTRAST_CHECKS:
        if fg not in tokens or bg not in tokens:
            continue
        ratio = contrast(tokens[fg], tokens[bg])
        if ratio < minimum:
            out.append(
                f"{label}: {desc} contrast {ratio}:1 is below {minimum}:1 "
                f"({tokens[fg]} on {tokens[bg]})"
            )
    return out


# ── resolution ─────────────────────────────────────────────────────────────
def _palette_tokens(raw: dict[str, Any]) -> tuple[dict[str, str], list[str], str]:
    mode = str(raw.get("mode", "light")).lower()
    tokens: dict[str, str] = {}
    for tok in _COLOR_TOKENS:
        val = raw.get(tok)
        if val:
            tokens[tok] = str(val).strip().lstrip("#").upper()
    charts = [str(c).strip().lstrip("#").upper() for c in (raw.get("chartColors") or [])]
    return tokens, charts, mode


def resolve(
    name: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> ResolvedTheme:
    """Look up a palette, apply token overrides, check readability.

    `name` accepts a library palette name, a legacy alias (dark/light), or None
    (=> the library default). An unknown name warns and falls back to default.
    `overrides` may set any color token or `chartColors`.
    """
    lib = _library()
    palettes: dict[str, Any] = lib["palettes"]
    default = default_name()

    requested = canonical_name(name)
    warnings: list[str] = []
    fell_back = False

    if requested not in palettes:
        warnings.append(
            f"unknown theme {requested!r}; using default palette {default!r}. "
            f"Available: {', '.join(sorted(palettes))}."
        )
        requested = default
        fell_back = True

    tokens, charts, mode = _palette_tokens(palettes[requested])

    # apply overrides
    ov = overrides or {}
    for key, val in ov.items():
        if key == "chartColors" and isinstance(val, (list, tuple)):
            charts = [str(c).strip().lstrip("#").upper() for c in val]
        elif key in _COLOR_TOKENS and val:
            tokens[key] = str(val).strip().lstrip("#").upper()
        elif key == "mode" and val:
            mode = str(val).lower()

    missing = [t for t in _REQUIRED_TOKENS if t not in tokens]
    if missing:
        warnings.append(
            f"theme {requested!r} is missing token(s) {', '.join(missing)}; "
            f"filling them from default palette {default!r}."
        )
        base_tokens, base_charts, _ = _palette_tokens(palettes[default])
        for t in missing:
            tokens[t] = base_tokens[t]
        if not charts:
            charts = base_charts

    # readability gate — a palette whose body text is unreadable falls back.
    # First drop the overrides (the usual culprit); then the whole palette.
    body = contrast(tokens["textMain"], tokens["surface"])
    if body < _READABILITY_FLOOR:
        if ov:
            warnings.append(
                f"theme {requested!r}: token overrides drop body-text contrast to "
                f"{body}:1 (below {_READABILITY_FLOOR}:1); ignoring the overrides."
            )
            fallback = resolve(requested, None)
        elif requested != default:
            warnings.append(
                f"theme {requested!r}: body text contrast {body}:1 is below the "
                f"{_READABILITY_FLOOR}:1 readability floor; falling back to {default!r}."
            )
            fallback = resolve(default, None)
        else:
            warnings.append(
                f"theme {requested!r}: body text contrast {body}:1 is below the "
                f"{_READABILITY_FLOOR}:1 floor and no safe fallback is available."
            )
            fallback = None
        if fallback is not None:
            return ResolvedTheme(
                name=fallback.name, mode=fallback.mode, tokens=fallback.tokens,
                chart_colors=fallback.chart_colors,
                warnings=warnings + fallback.warnings, fell_back=True,
            )

    warnings.extend(verify(tokens, name=requested))
    if not charts:
        charts = [tokens["accent"], tokens["accentAlt"]]

    return ResolvedTheme(
        name=requested, mode=mode, tokens=tokens, chart_colors=charts,
        warnings=warnings, fell_back=fell_back,
    )


# ── emit ───────────────────────────────────────────────────────────────────
def theme_element(theme: ResolvedTheme | dict[str, str]) -> str:
    """Render the single-line <Theme .../> element (color tokens only)."""
    tokens = theme.tokens if isinstance(theme, ResolvedTheme) else dict(theme)
    parts = [
        f'{tok}="{tokens[tok]}"'
        for tok in _COLOR_TOKENS
        if tok in tokens
    ]
    return f"<Theme {' '.join(parts)} />"
