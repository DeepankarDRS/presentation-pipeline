"""Grow fallback — make sure a slide's main content band takes the spare height.

POM gives spare height only to children with grow (or h). When the generator
leaves every band of a VStack root content-sized (a KPI row + callout slide, a
bullet card), the content stacks at the top and the lower half of the slide is
empty; fit-grow cannot fill it because no box is taller than its content.

This pass adds grow="1" to ONE band of the root VStack when none of its bands
grows: the band with a chart / diagram if any, else the largest card band
(KPI row, card grid, bullet card, callout). Header and caption lines (no card,
no data node) and fixed-height diagrams (Timeline, Pyramid) never get it. A
slide with a table is left alone: fit-grow grows the table's rows and text into
the spare height, and a growing sibling would take that space from the table.

It edits the XML text in place (one attribute inserted), like the normalizer.
"""

from __future__ import annotations

import re

_TAG_RE = re.compile(
    r"<!--.*?-->|<(?P<close>/?)(?P<name>[A-Za-z][\w.]*)(?P<attrs>(?:[^<>\"']|\"[^\"]*\"|'[^']*')*?)(?P<self>/?)>",
    re.S,
)
_FLEX_ATTR_RE = re.compile(r"\s(?:grow|h)\s*=")
_BG_ATTR_RE = re.compile(r"\s(?:backgroundColor|fill\.color)\s*=")

_FILLS = {"Chart", "Matrix", "Flow", "Tree", "ProcessArrow"}  # h="max" fills its card
_NEVER = {"Table", "Timeline", "Pyramid"}                       # size to rows / pixel h


class _Band:
    __slots__ = ("start", "open_end", "name", "attrs", "tags", "has_bg", "nodes")

    def __init__(self, start: int, open_end: int, name: str, attrs: str) -> None:
        self.start, self.open_end, self.name, self.attrs = start, open_end, name, attrs
        self.tags: set[str] = {name}
        self.has_bg = bool(_BG_ATTR_RE.search(attrs))
        self.nodes = 1


def _root_bands(xml: str) -> tuple[str | None, list[_Band]]:
    """Name of the slide's root stack and its direct children (with subtree facts)."""
    depth = 0
    root_name: str | None = None
    root_depth = -1
    bands: list[_Band] = []
    current: _Band | None = None
    for m in _TAG_RE.finditer(xml):
        name = m.group("name")
        if name is None:  # comment
            continue
        closing, selfclosing = bool(m.group("close")), bool(m.group("self"))
        if closing:
            depth -= 1
            if current is not None and depth == root_depth + 1:
                current = None
            continue
        if root_name is None and name in ("VStack", "HStack", "Layer"):
            root_name, root_depth = name, depth
        elif root_name is not None and depth == root_depth + 1:
            current = _Band(m.start(), m.end(), name, m.group("attrs"))
            bands.append(current)
        elif current is not None and depth > root_depth + 1:
            current.tags.add(name)
            current.nodes += 1
            if _BG_ATTR_RE.search(m.group("attrs")):
                current.has_bg = True
        if not selfclosing:
            depth += 1
        if current is not None and selfclosing and depth == root_depth + 1 and current.start == m.start():
            current = None
    return root_name, bands


def ensure_growing_band(xml: str) -> tuple[str, str | None]:
    """Return (xml, message). message is None when nothing changed."""
    root_name, bands = _root_bands(xml)
    if root_name != "VStack" or len(bands) < 2:
        return xml, None
    if any(_FLEX_ATTR_RE.search(b.attrs) for b in bands):
        return xml, None
    if any("Table" in b.tags for b in bands):
        return xml, None
    candidates = [
        b for b in bands
        if not (b.tags & _NEVER) and (b.tags & _FILLS or b.has_bg or "Ul" in b.tags or "Ol" in b.tags)
    ]
    if not candidates:
        return xml, None
    with_fill = [b for b in candidates if b.tags & _FILLS]
    pick = with_fill[0] if with_fill else max(candidates, key=lambda b: b.nodes)
    tag_open = xml[pick.start:pick.open_end]
    insert_at = pick.start + 1 + len(pick.name)
    xml = xml[:insert_at] + ' grow="1"' + xml[insert_at:]
    what = "chart/diagram" if with_fill else f"{pick.nodes}-node {pick.name}"
    return xml, (f'No band of the root VStack grew; gave grow="1" to the main content band '
                 f"({what}) so it takes the spare height. Opening tag was: {tag_open[:80]}")
