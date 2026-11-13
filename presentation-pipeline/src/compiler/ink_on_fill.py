"""Text ink that cannot read on the fill it sits on (look2 blind marks, 2026-11-13).

Two slips left text invisible on a light card or panel, in both planner arms:
  - ink meant for a dark fill ($onPanelDark, $onAccent, $surface, $surfaceAlt) on a surface-family fill: a focus
    card whose fill a later layer made light kept its dark look's inks (bullets, "03" numerals), and a dark panel
    softened to a tint (one dark panel per deck) keeps whatever the regex in soften_dark_panels does not map;
  - a tint token ($accentSoft, $positiveSoft, ...) written as a text colour: tints are fills, the same lightness as
    the card under them.
Surface-family fills ($surface, $surfaceAlt, $*Soft, $neutral) are built to carry $textMain and $*Text in light and
dark palettes alike (palette_tokens), so those are the replacements. Text on a dark or saturated fill, on a literal
colour, inside a <Layer>, an Icon, and the <Mark> highlighter's own colour are left alone."""
from __future__ import annotations

import re

_TAG_RE = re.compile(r"<(/?)([A-Za-z]\w*)\b([^>]*?)(/?)>")
_FILL_RE = re.compile(r'(?<![\w.])backgroundColor="([^"]*)"')   # not header. / item. parts
_COLOR_RE = re.compile(r'((?<![\w.])color=")([^"]*)(")')
_SOFT_RE = re.compile(r"^\$(accent|positive|negative|warning)Soft$")
_INK_TAGS = {"Text", "Span", "B", "I", "U", "Ul", "Ol", "Li", "Td", "Th"}
# a <Layer> places text over shapes it draws itself (fill.color), and an Icon often sits on a filled Shape dot:
# neither is judged by its container's fill (scan of 5,459 saved slides, 2026-11-13)
_OVER_SHAPES = "Layer"
_ON_DARK_INKS = {"$onPanelDark", "$onAccent", "$surface", "$surfaceAlt"}
SLIDE_FILL = "$surface"


def light_fill(fill: str) -> bool:
    return fill in ("$surface", "$surfaceAlt", "$neutral") or bool(_SOFT_RE.match(fill))


def readable_ink(color: str, fill: str) -> str:
    """The ink `color` becomes on `fill`: unchanged unless it cannot read there."""
    if not light_fill(fill):
        return color
    if color in _ON_DARK_INKS:
        return "$textMain"
    m = _SOFT_RE.match(color)
    return f"${m.group(1)}Text" if m else color


def fix_ink_on_fill(xml: str) -> tuple[str, int]:
    """Each text tag's `color` judged against the nearest enclosing backgroundColor (the slide's surface when none)."""
    stack: list[tuple[str, str | None]] = []   # open tags with their own fill
    out: list[str] = []
    pos = count = 0
    for m in _TAG_RE.finditer(xml):
        closing, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
        out.append(xml[pos:m.start()])
        pos = m.end()
        if closing:
            if stack:
                stack.pop()
            out.append(m.group(0))
            continue
        own = _FILL_RE.search(attrs)
        if tag in _INK_TAGS and not any(t == _OVER_SHAPES for t, _ in stack):
            fill = own.group(1) if own else next((f for _, f in reversed(stack) if f), SLIDE_FILL)

            def _ink(c: re.Match) -> str:
                nonlocal count
                new = readable_ink(c.group(2), fill)
                count += new != c.group(2)
                return c.group(1) + new + c.group(3)
            attrs = _COLOR_RE.sub(_ink, attrs)
        out.append(f"<{tag}{attrs}{selfclose}>")
        if not selfclose:
            stack.append((tag, own.group(1) if own else None))
    out.append(xml[pos:])
    return "".join(out), count


# --- text on a colour fill: a <Highlight> head or fill, a category / phase band (look5, 2026-11-13) ---
# White ink on every $chartN head read poorly on the light series colours (XTSY "Market Expansion" on light cyan),
# and a focus fill ($accentSoft) on a dark palette is a mid tone under muted body text. The surface family is left
# to fix_ink_on_fill (built to carry $textMain); every other token fill has its text judged by real contrast.
_PLAIN_FILLS = {"$surface", "$surfaceAlt", "$coverDark"}
_INKS = ("$textMain", "$onPanelDark", "$onAccent", "$surface")
_LAST = ("$inkDark", "$inkLight")
_SIZE_RE = re.compile(r'(?<![\w.])fontSize="(\d+(?:\.\d+)?)"')
_BOLD_RE = re.compile(r'(?<![\w.])bold="true"')
_INK_TAGS_FILL = {"Text", "Span", "B", "I", "U", "Icon"}


def readable_on_colour_fills(xml: str, theme_element: str) -> tuple[str, int]:
    """Text, spans and icons whose colour does not reach WCAG on the token fill they sit on (4.5:1, 3:1 for large
    text >= 24 px or bold >= 19 px and for icons) take the theme ink that reads best: $onStepN on $stepN, else the
    theme's own inks, pure black / white last. Only token fills outside the surface family; text over <Layer>
    shapes and literal colours are left alone. Returns (xml, changed)."""
    from src.compiler.palette_tokens import contrast
    tokens = dict(re.findall(r'(\w+)="([0-9A-Fa-f]{6})"', theme_element or ""))
    if not tokens:
        return xml, 0
    hex_of = lambda t: tokens.get(t[1:]) if t and t.startswith("$") else None
    stack: list[tuple[str, str | None, float]] = []   # (tag, own fill, inherited size)
    out: list[str] = []
    pos = count = 0
    for m in _TAG_RE.finditer(xml):
        closing, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
        out.append(xml[pos:m.start()])
        pos = m.end()
        if closing:
            if stack:
                stack.pop()
            out.append(m.group(0))
            continue
        own = _FILL_RE.search(attrs)
        size_m = _SIZE_RE.search(attrs)
        size = float(size_m.group(1)) if size_m else (stack[-1][2] if stack else 16.0)
        fill = own.group(1) if own else next((f for _, f, _ in reversed(stack) if f), None)
        if (tag in _INK_TAGS_FILL and fill and fill not in _PLAIN_FILLS and hex_of(fill)
                and not any(t == _OVER_SHAPES for t, _, _ in stack)):
            bg = hex_of(fill)
            need = 3.0 if tag == "Icon" or size >= 24 or (size >= 19 and _BOLD_RE.search(attrs)) else 4.5

            def _ink(c: re.Match) -> str:
                nonlocal count
                now = hex_of(c.group(2))
                if not now or contrast(now, bg) >= need:
                    return c.group(0)
                step = re.fullmatch(r"\$step(\d)", fill)
                pick = f"$onStep{step.group(1)}" if step and f"onStep{step.group(1)}" in tokens else None
                if not pick:
                    pick = max((t for t in _INKS if t[1:] in tokens), key=lambda t: contrast(tokens[t[1:]], bg),
                               default=None)
                    if not pick or contrast(tokens[pick[1:]], bg) < need:
                        pick = max((t for t in _INKS + _LAST if t[1:] in tokens),
                                   key=lambda t: contrast(tokens[t[1:]], bg), default=pick)
                if not pick or pick == c.group(2):
                    return c.group(0)
                count += 1
                return c.group(1) + pick + c.group(3)
            attrs = _COLOR_RE.sub(_ink, attrs)
        out.append(f"<{tag}{attrs}{selfclose}>")
        if not selfclose:
            stack.append((tag, own.group(1) if own else None, size))
    out.append(xml[pos:])
    return "".join(out), count
