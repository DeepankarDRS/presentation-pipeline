"""KPI grid — a slide whose only body band is a row of 4-6 stat tiles gets them as rows.

Four or more tiles in one row of a 1280 px slide are ~230-290 px wide: the numbers are
width-bound (fit-grow stopped "$48.2M" at 50 px) and the grown row leaves the tiles
mostly empty. The same tiles as rows of 2 or 3 at equal widths let the numbers grow to
~96 px and the tiles fill the slide (docs/eval/kpi-tiles/kpi-tile-options.png, user
2026-10-07: "let it be for the KPI case"; other layouts are the LLM's, via the layout
rules in capacity.yaml). No tile is dropped, resized by hand or reworded.

Only when the root's body (below header texts, above a trailing caption) is that one
row; a KPI row beside a chart, table or text band is left alone.
"""

from __future__ import annotations

import math
import re

from lxml import etree

_STACKS = {"VStack", "HStack"}
_HEADER_TAGS = {"Text", "Icon", "Shape"}
_NUMBER = re.compile(r"\d")
TILES = (4, 6)
_WIDTH = {2: "49%", 3: "32%"}


def _text(el: etree._Element) -> str:
    return "".join(el.itertext()).strip()


def _header_like(el: etree._Element) -> bool:
    if el.tag in _HEADER_TAGS:
        return True
    return el.tag in _STACKS and el.get("backgroundColor") is None and all(_header_like(c) for c in el)


def _stat_tile(el: etree._Element) -> bool:
    """A card holding one short number set large (the tile's anchor)."""
    if el.tag not in _STACKS or el.get("backgroundColor") is None:
        return False
    for t in el.iter("Text"):
        size = float(t.get("fontSize", "0") or 0)
        txt = _text(t)
        if size >= 24 and _NUMBER.search(txt) and len(txt) <= 14:
            return True
    return False


def kpi_rows(xml: str) -> tuple[str, str]:
    """Returns (xml, note); note is '' when nothing changed."""
    try:
        wrapper = etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"))
    except etree.XMLSyntaxError:
        return xml, ""
    slide = wrapper.find("Slide")
    root = slide[0] if slide is not None and len(slide) else None
    if root is None or root.tag != "VStack":
        return xml, ""
    kids = [c for c in root if isinstance(c.tag, str)]
    body = [c for c in kids if not _header_like(c)]
    if len(body) != 1 or body[0].tag != "HStack":
        return xml, ""
    row = body[0]
    tiles = [c for c in row if isinstance(c.tag, str)]
    if not (TILES[0] <= len(tiles) <= TILES[1]) or not all(_stat_tile(t) for t in tiles):
        return xml, ""

    per_row = math.ceil(len(tiles) / 2)
    gap = row.get("gap", "18")
    grid = etree.Element("VStack", gap=gap, grow=row.get("grow", "1"))
    for start in range(0, len(tiles), per_row):
        line = etree.SubElement(grid, "HStack", gap=gap, alignItems="stretch", grow="1")
        for tile in tiles[start:start + per_row]:
            for attr in ("w", "grow"):
                tile.attrib.pop(attr, None)
            tile.set("w", _WIDTH[per_row])
            line.append(tile)
    grid.tail = row.tail
    root.replace(row, grid)
    out = "".join(etree.tostring(c, encoding="unicode") for c in wrapper)
    rows = "+".join(str(len(tiles[s:s + per_row])) for s in range(0, len(tiles), per_row))
    return (wrapper.text or "") + out, f"{len(tiles)} KPI tiles alone on the slide -> rows of {rows} at equal widths"
