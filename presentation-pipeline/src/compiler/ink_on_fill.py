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
