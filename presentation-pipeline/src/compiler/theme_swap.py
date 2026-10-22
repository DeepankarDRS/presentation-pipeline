"""Theme swap — re-skin finished slide XML for a different palette, no LLM.

Slides are stored theme-less and reference colors as $tokens, so most of a
theme switch is just compiling under a new <Theme>. This module handles the
three things a bare <Theme> swap misses:

1. Literal hex -> a $token. Exact matches to an OLD theme token value win
   (attribute-aware when several tokens share a value); anything else maps
   to the nearest token in the attribute's role and is reported in
   ``approximated`` — a leftover light tint would be unreadable on dark.
2. chartColors (literal JSON — tokens don't resolve there) -> the new
   palette's chart colors, by series position.
3. Dark target: wrap any <Chart> not already sitting on $chartSurface,
   because POM hard-codes axis text to black. Existing wrappers are kept on
   light targets ($chartSurface resolves to a light card there).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

from src.compiler.normalizer import strip_theme

_THEME_ATTR_RE = re.compile(r'([A-Za-z][A-Za-z0-9_-]*)\s*=\s*"#?([0-9A-Fa-f]{6})"')
_COLOR_ATTR_RE = re.compile(
    r'(?<![\w.])(?P<attr>(?:[A-Za-z]+\.)?[A-Za-z]*[Cc]olor)\s*=\s*"#?(?P<hex>[0-9A-Fa-f]{6})"'
)
_CHART_COLORS_RE = re.compile(r"chartColors\s*=\s*(?P<q>['\"])(?P<val>.*?)(?P=q)", re.DOTALL)
_CHART_RE = re.compile(r"<Chart\b[^>]*?/>|<Chart\b[^>]*?>.*?</Chart>", re.DOTALL)
_OPEN_TAG_TAIL_RE = re.compile(r"<(?:VStack|HStack)\b[^>]*>\s*$")
_CHART_OPEN_RE = re.compile(r"<Chart\b[^>]*?/?>", re.DOTALL)

_WRAP_PAD = 12
# Attributes that place the chart in its parent: they move to the wrapper.
_PLACEMENT_ATTRS = ("x", "y", "grow", "margin", "alignSelf")

_TEXT_PREF = ["textMain", "textMuted", "accent", "accentAlt", "positive", "negative",
              "warning", "surfaceAlt", "surface", "border", "chartInk", "chartSurface"]
_FILL_PREF = ["surface", "surfaceAlt", "accent", "accentAlt", "positive", "negative",
              "warning", "border", "textMain", "textMuted", "chartSurface", "chartInk"]
_LINE_PREF = ["border", "accent", "accentAlt", "positive", "negative", "warning",
              "textMuted", "textMain", "surfaceAlt", "surface", "chartInk", "chartSurface"]


@dataclass
class SwapResult:
    xml: str
    remapped: int = 0
    approximated: list[str] = field(default_factory=list)
    charts_wrapped: int = 0


def theme_tokens(theme_element: str) -> dict[str, str]:
    """Parse a <Theme .../> element into {token: HEX}."""
    return {k: v.upper() for k, v in _THEME_ATTR_RE.findall(theme_element or "")}


def _preference(attr: str) -> list[str]:
    a = attr.lower()
    if "border" in a or "line" in a:
        return _LINE_PREF
    if "background" in a or "fill" in a:
        return _FILL_PREF
    return _TEXT_PREF


def _lab(hex_: str) -> tuple[float, float, float]:
    """sRGB hex -> CIE Lab (D65)."""
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(hex_[i:i + 2], 16) / 255) for i in (0, 2, 4))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


_NEUTRAL_CHROMA = 15.0
_SEMANTIC_HUE_TOL = 25.0
_DARK_TINT_L = 35.0
_LIGHT_TINT_L = 85.0
_NEUTRAL_ROLES = {
    "text": ["textMain", "textMuted", "surfaceAlt"],
    "fill": ["surface", "surfaceAlt", "border", "textMuted", "textMain"],
    "line": ["border", "textMuted", "textMain", "surfaceAlt"],
}


def _role(attr: str) -> str:
    pref = _preference(attr)
    return "line" if pref is _LINE_PREF else "fill" if pref is _FILL_PREF else "text"


def _nearest_token(hex_: str, attr: str, old_tokens: dict[str, str]) -> str | None:
    """Closest old token in the attribute's role, for hex matching no token exactly.

    Neutrals (greys, near-white text, pale tinted fills) go to the role's
    neutral token with the nearest lightness; dark tinted fills invert ($textMain). Saturated colors go to a semantic token
    (positive/negative/warning) only when the hue is close, otherwise to the
    accent — an off-palette brand color becomes the new theme's accent.
    """
    L, a, b = _lab(hex_)
    chroma = math.hypot(a, b)
    labs = {t: _lab(v) for t, v in old_tokens.items()}

    role = _role(attr)
    if role == "fill" and L < _DARK_TINT_L and "textMain" in labs:
        # A dark tinted panel (navy, brown) is an inverted panel: its white
        # text maps to $surfaceAlt, so the panel must be $textMain to keep the
        # contrast flipping together (accent/warning would hide colored text).
        return "textMain"
    if chroma < _NEUTRAL_CHROMA or (role == "fill" and L > _LIGHT_TINT_L):
        cands = [t for t in _NEUTRAL_ROLES[role] if t in labs]
        return min(cands, key=lambda t: abs(labs[t][0] - L), default=None)

    hue = math.degrees(math.atan2(b, a))

    def hue_diff(t: str) -> float:
        d = abs(math.degrees(math.atan2(labs[t][2], labs[t][1])) - hue) % 360
        return min(d, 360 - d)

    semantic = [t for t in ("positive", "negative", "warning")
                if t in labs and hue_diff(t) <= _SEMANTIC_HUE_TOL]
    if semantic:
        return min(semantic, key=hue_diff)
    accents = [t for t in ("accent", "accentAlt") if t in labs]
    return min(accents, key=hue_diff, default=None)


def _remap_hex(xml: str, old_tokens: dict[str, str], result: SwapResult) -> str:
    by_value: dict[str, set[str]] = {}
    for name, value in old_tokens.items():
        by_value.setdefault(value, set()).add(name)
    approximated: set[str] = set()

    def repl(m: re.Match[str]) -> str:
        attr, hex_ = m.group("attr"), m.group("hex").upper()
        names = by_value.get(hex_)
        if names:
            token = next((t for t in _preference(attr) if t in names), sorted(names)[0])
        else:
            token = _nearest_token(hex_, attr, old_tokens)
            if token is None:
                return m.group(0)
            approximated.add(f"{hex_}->{token}")
        result.remapped += 1
        return f'{attr}="${token}"'

    out = _COLOR_ATTR_RE.sub(repl, xml)
    result.approximated = sorted(approximated)
    return out


def _swap_chart_colors(xml: str, chart_colors: list[str]) -> str:
    if not chart_colors:
        return xml

    def repl(m: re.Match[str]) -> str:
        try:
            n = len(json.loads(m.group("val")))
        except (ValueError, TypeError):
            n = len(chart_colors)
        new = [chart_colors[i % len(chart_colors)] for i in range(max(n, 1))]
        return f"chartColors='{json.dumps(new, separators=(',', ':'))}'"

    return _CHART_COLORS_RE.sub(repl, xml)


def _get_attr(tag: str, name: str) -> str | None:
    m = re.search(rf'(?<![\w.]){re.escape(name)}\s*=\s*"([^"]*)"', tag)
    return m.group(1) if m else None


def _set_attr(tag: str, name: str, value: str | None) -> str:
    pattern = re.compile(rf'\s+{re.escape(name)}\s*=\s*"[^"]*"')
    tag = pattern.sub("", tag)
    if value is None:
        return tag
    return re.sub(r"^<Chart\b", f'<Chart {name}="{value}"', tag)


def _shrink(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(max(int(float(value)) - 2 * _WRAP_PAD, 40))
    except ValueError:
        return "max"  # "max" / "NN%" -> fill the wrapper, which takes the original


def _wrap_charts(xml: str, result: SwapResult) -> str:
    out: list[str] = []
    pos = 0
    for m in _CHART_RE.finditer(xml):
        out.append(xml[pos:m.start()])
        pos = m.end()
        chart = m.group(0)
        parent = _OPEN_TAG_TAIL_RE.search(xml[:m.start()])
        if parent and "$chartSurface" in parent.group(0):
            out.append(chart)
            continue

        open_tag = _CHART_OPEN_RE.match(chart).group(0)
        wrapper_attrs: list[str] = []
        new_tag = open_tag
        for name in ("w", "h"):
            v = _get_attr(open_tag, name)
            if v is not None:
                wrapper_attrs.append(f'{name}="{v}"')
                new_tag = _set_attr(new_tag, name, _shrink(v))
        if _get_attr(open_tag, "w") is None:
            wrapper_attrs.append('w="max"')
            new_tag = _set_attr(new_tag, "w", "max")
        for name in _PLACEMENT_ATTRS:
            v = _get_attr(open_tag, name)
            if v is not None:
                wrapper_attrs.append(f'{name}="{v}"')
                new_tag = _set_attr(new_tag, name, None)

        wrapper = (
            f'<VStack {" ".join(wrapper_attrs)} padding="{_WRAP_PAD}" '
            f'backgroundColor="$chartSurface" borderRadius="10">'
        )
        out.append(f"{wrapper}{new_tag}{chart[len(open_tag):]}</VStack>")
        result.charts_wrapped += 1
    out.append(xml[pos:])
    return "".join(out)


def with_chart_tokens(theme_element: str) -> str:
    """Add chartSurface/chartInk to a <Theme> that lacks them (light palettes).

    A slide switched away from a dark theme keeps its $chartSurface wrapper;
    on a light theme it should resolve to a plain card, not fail to compile.
    """
    tokens = theme_tokens(theme_element)
    extra = []
    if "chartSurface" not in tokens:
        extra.append(f'chartSurface="{tokens.get("surfaceAlt", "FFFFFF")}"')
    if "chartInk" not in tokens:
        extra.append(f'chartInk="{tokens.get("textMain", "16202E")}"')
    if not extra:
        return theme_element
    return re.sub(r"\s*/>\s*$", " " + " ".join(extra) + " />", theme_element.strip(), count=1)


def swap_theme(
    slide_xml: str,
    old_theme_element: str,
    new_chart_colors: list[str],
    new_is_dark: bool,
) -> SwapResult:
    """Rewrite one theme-less slide so it renders correctly under a new theme."""
    result = SwapResult(xml="")
    xml = strip_theme(slide_xml)
    xml = _remap_hex(xml, theme_tokens(old_theme_element), result)
    xml = _swap_chart_colors(xml, new_chart_colors)
    if new_is_dark:
        xml = _wrap_charts(xml, result)
    result.xml = xml
    return result
