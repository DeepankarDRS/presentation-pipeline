"""Theme swap — re-skin finished slide XML for a different palette, no LLM.

Slides are stored theme-less and reference colors as $tokens, so most of a
theme switch is just compiling under a new <Theme>. This module handles the
three things a bare <Theme> swap misses:

1. Literal hex -> a $token. Exact matches to an OLD theme token value win
   (attribute-aware when several tokens share a value); anything else maps
   to the nearest token in the attribute's role and is reported in
   ``approximated`` — a leftover light tint would be unreadable on dark.
   Text is matched to the fill it sits on: neutral ink on a $panelDark /
   $accent fill becomes $onPanelDark / $onAccent, so it flips with the fill.
2. chartColors -> tokens: the old accent / neutral hex become $accent /
   $neutral (keeps a one-series-in-focus chart), the rest $chart1..$chartN
   by series position, so later switches recolor charts with no rewrite.
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

# Exact-match tie-breaks, including the derived roles (src/compiler/palette_tokens.py).
_TEXT_PREF = ["textMain", "textMuted", "accentText", "positiveText", "negativeText", "warningText",
              "accent", "accentAlt", "positive", "negative", "warning", "neutral",
              "surfaceAlt", "surface", "onAccent", "onPanelDark", "border", "chartInk", "chartSurface"]
_FILL_PREF = ["surface", "surfaceAlt", "accentSoft", "positiveSoft", "negativeSoft", "warningSoft",
              "panelDark", "accent", "accentAlt", "positive", "negative", "warning", "neutral",
              "border", "textMain", "textMuted", "chartSurface", "chartInk"]
_LINE_PREF = ["border", "neutral", "accent", "accentAlt", "positive", "negative", "warning",
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
    neutral token with the nearest lightness; dark tinted fills invert ($panelDark). Saturated colors go to a semantic token
    (positive/negative/warning) only when the hue is close, otherwise to the
    accent — an off-palette brand color becomes the new theme's accent.
    """
    L, a, b = _lab(hex_)
    chroma = math.hypot(a, b)
    labs = {t: _lab(v) for t, v in old_tokens.items()}

    role = _role(attr)
    if role == "fill" and L < _DARK_TINT_L:
        # A dark tinted panel (navy, brown) is an inverted panel; _remap_hex
        # matches the ink inside it to $onPanelDark.
        return "panelDark" if "panelDark" in labs else ("textMain" if "textMain" in labs else None)
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


_TAG_RE = re.compile(r"<(?P<close>/)?(?P<name>[A-Za-z]\w*)(?P<attrs>[^<>]*?)(?P<self>/)?>")
_FILL_HEX_RE = re.compile(r'(?<![\w.])(?:backgroundColor|fill\.color)\s*=\s*"#?[0-9A-Fa-f]{6}"')
_FILL_TOKEN_RE = re.compile(r'(?<![\w.])(?:backgroundColor|fill\.color)\s*=\s*"\$(?P<tok>\w+)"')
# Ink on these fills must flip with the fill, not with the slide.
_ON_FILL = {"panelDark": "onPanelDark", "textMain": "onPanelDark", "accent": "onAccent"}


def _remap_hex(xml: str, old_tokens: dict[str, str], result: SwapResult) -> str:
    by_value: dict[str, set[str]] = {}
    for name, value in old_tokens.items():
        by_value.setdefault(value, set()).add(name)
    approximated: set[str] = set()

    def token_for(attr: str, hex_: str, fill: str | None) -> str | None:
        on_fill = _ON_FILL.get(fill or "")
        # an old <Theme> without derived tokens: ink on a dark panel was white
        ref = old_tokens.get(on_fill or "") or ("FFFFFF" if on_fill == "onPanelDark" else None)
        if _role(attr) == "text" and ref:
            L, a, b = _lab(hex_)
            if math.hypot(a, b) < _NEUTRAL_CHROMA and abs(L - _lab(ref)[0]) < 30:
                return on_fill
        names = by_value.get(hex_)
        if names:
            return next((t for t in _preference(attr) if t in names), sorted(names)[0])
        token = _nearest_token(hex_, attr, old_tokens)
        if token:
            approximated.add(f"{hex_}->{token}")
        return token

    def remap_attrs(attrs: str, fill: str | None) -> str:
        def repl(m: re.Match[str]) -> str:
            token = token_for(m.group("attr"), m.group("hex").upper(), fill)
            if token is None:
                return m.group(0)
            result.remapped += 1
            return f'{m.group("attr")}="${token}"'
        return _COLOR_ATTR_RE.sub(repl, attrs)

    # On a light source theme a $textMain fill is an inverted panel (an old <Theme> has no
    # $panelDark, so dark hex fills land on $textMain too). Say $panelDark: it equals textMain
    # on light targets and stays dark on dark ones, where $textMain is the light ink.
    old_main = old_tokens.get("textMain")
    panel_from_main = old_main is not None and _lab(old_main)[0] < _DARK_TINT_L

    def as_panel(attrs: str) -> str:
        if not panel_from_main:
            return attrs
        return _FILL_TOKEN_RE.sub(
            lambda f: f.group(0).replace("$textMain", "$panelDark") if f.group("tok") == "textMain"
            else f.group(0), attrs)

    out: list[str] = []
    stack: list[str | None] = []        # the fill token each open element sits on
    pos = 0
    for m in _TAG_RE.finditer(xml):
        out.append(xml[pos:m.start()])
        pos = m.end()
        if m.group("close"):
            if stack:
                stack.pop()
            out.append(m.group(0))
            continue
        parent_fill = stack[-1] if stack else None
        # The element's own fill first (it is the context), then its ink against it.
        attrs = as_panel(_FILL_HEX_RE.sub(lambda f: remap_attrs(f.group(0), parent_fill), m.group("attrs")))
        fm = _FILL_TOKEN_RE.search(attrs)
        fill = fm.group("tok") if fm else parent_fill
        attrs = remap_attrs(attrs, fill)
        out.append(f"<{m.group('name')}{attrs}{m.group('self') or ''}>")
        if not m.group("self"):
            stack.append(fill)
    out.append(xml[pos:])
    result.approximated = sorted(approximated)
    return "".join(out)


_CHART_TOKEN_RE = re.compile(r"chart\d+")


def _swap_chart_colors(xml: str, old_tokens: dict[str, str], n_tokens: int) -> str:
    if not n_tokens:
        return xml
    by_value = {v: k for k, v in old_tokens.items() if _CHART_TOKEN_RE.fullmatch(k)}
    for role in ("neutral", "accent"):      # a focus pair beats a chartN of the same value
        if role in old_tokens:
            by_value[old_tokens[role]] = role

    def repl(m: re.Match[str]) -> str:
        try:
            entries = [str(e) for e in json.loads(m.group("val"))]
        except (ValueError, TypeError):
            entries = []
        new = []
        for i, e in enumerate(entries or [""]):
            hex_ = e.lstrip("#").upper()
            if e.startswith("$"):
                new.append(e)
            elif hex_ in by_value:
                new.append(f"${by_value[hex_]}")
            else:
                new.append(f"$chart{i % n_tokens + 1}")
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


def swap_theme(
    slide_xml: str,
    old_theme_element: str,
    new_theme_element: str,
    new_is_dark: bool,
) -> SwapResult:
    """Rewrite one theme-less slide so it renders correctly under a new theme."""
    result = SwapResult(xml="")
    xml = strip_theme(slide_xml)
    xml = _remap_hex(xml, theme_tokens(old_theme_element), result)
    n_chart = sum(1 for t in theme_tokens(new_theme_element) if _CHART_TOKEN_RE.fullmatch(t))
    xml = _swap_chart_colors(xml, theme_tokens(old_theme_element), n_chart)
    if new_is_dark:
        xml = _wrap_charts(xml, result)
    result.xml = xml
    return result
