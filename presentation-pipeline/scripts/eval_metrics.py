"""LLM-free slide metrics read from a compiled single-slide .pptx.

POM writes every text box at its measured content height, while a card
(a VStack/HStack with a background or border) keeps its full layout box.
So dead space is visible directly in the shape frames:

- card        = rect/roundRect with a fill or line, no text, smaller than 90% of the slide
- content     = every other shape (text, table/chart frame, picture) and nested cards
- fill ratio  = content span / (card height - 2 * padding), padding = the smaller of
                the gaps above and below the content, capped at 24 px (the largest card
                padding in the golden decks) so centred content in a bloated card still
                shows its dead space. 1.0 = no dead space.

A table frame is as tall as its rows, and POM stretches rows (text stays at the top,
no vertical-align — sizing plan F5), so a table counts only the text height of each
row: lines (estimated from characters x column width) x font size x 1.2 + cell margins,
at least POM's default 32 px row.

Card patterns (for the gj-h1 comparison): chart_card, table_card, dark_panel,
kpi_tile, text_card.
"""

from __future__ import annotations

import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
_EMU_PER_PX = 9525
_SLIDE_AREA = 1280 * 720
_MAX_PAD = 24
_DEFAULT_ROW = 32  # POM's default row height (sizing plan F4): rows up to this are not dead space
LOW_FILL = 0.7  # same threshold as fit-grow.js


def _table_text_height(tbl: ET.Element) -> float:
    cols = [int(g.get("w")) / _EMU_PER_PX for g in tbl.iter(f"{{{_NS['a']}}}gridCol")]
    total = 0.0
    for tr in tbl.findall("a:tr", _NS):
        need, col = 0.0, 0
        for tc in tr.findall("a:tc", _NS):
            span = int(tc.get("gridSpan", 1))
            width = sum(cols[col:col + span])
            col += span
            pr = tc.find("a:tcPr", _NS)
            mar = lambda k: int(pr.get(k, 45720)) / _EMU_PER_PX if pr is not None else 4.8  # noqa: E731
            lines, line_px = 0, 0.0
            for p in tc.iter(f"{{{_NS['a']}}}p"):
                text = "".join(t.text or "" for t in p.iter(f"{{{_NS['a']}}}t"))
                sizes = [int(r.get("sz")) for r in p.iter(f"{{{_NS['a']}}}rPr") if r.get("sz")]
                px = max(sizes, default=1800) / 100 * 4 / 3
                per_line = max(1.0, (width - mar("marL") - mar("marR")) / (0.55 * px))
                lines += max(1, -(-len(text) // int(per_line)))
                line_px = max(line_px, 1.2 * px)
            need = max(need, lines * line_px + mar("marT") + mar("marB"))
        total += min(int(tr.get("h")) / _EMU_PER_PX, max(need, _DEFAULT_ROW))
    return total


def _shapes(slide_xml: bytes) -> list[dict]:
    root = ET.fromstring(slide_xml)
    out = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("sp", "graphicFrame", "pic", "cxnSp"):
            continue
        off, ext = el.find(".//a:off", _NS), el.find(".//a:ext", _NS)
        if off is None or ext is None:
            continue
        x, y = int(off.get("x")) / _EMU_PER_PX, int(off.get("y")) / _EMU_PER_PX
        w, h = int(ext.get("cx")) / _EMU_PER_PX, int(ext.get("cy")) / _EMU_PER_PX
        text = "".join(t.text or "" for t in el.iter(f"{{{_NS['a']}}}t")).strip()
        sizes = [int(r.get("sz")) / 100 for r in el.iter() if r.tag.endswith("}rPr") and r.get("sz")]
        geom = el.find(".//a:prstGeom", _NS)
        fill = el.find("./p:spPr/a:solidFill/a:srgbClr", _NS)
        line = el.find("./p:spPr/a:ln/a:solidFill", _NS)
        data = el.find(".//a:graphicData", _NS)
        uri = data.get("uri", "") if data is not None else ""
        tbl = el.find(".//a:tbl", _NS)
        out.append({
            "x": x, "y": y, "w": w, "h": h,
            "content_h": _table_text_height(tbl) if tbl is not None else h,
            "text": text,
            "max_font": max(sizes, default=0),
            "fill": fill.get("val") if fill is not None else "",
            "is_card": (
                tag == "sp" and not text and geom is not None
                and geom.get("prst") in ("rect", "roundRect")
                and (fill is not None or line is not None)
                and w * h < 0.9 * _SLIDE_AREA
            ),
            "kind": "chart" if uri.endswith("/chart") else "table" if uri.endswith("/table") else tag,
        })
    return out


def _inside(s: dict, card: dict) -> bool:
    cx, cy = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2
    return (s is not card and s["w"] * s["h"] < card["w"] * card["h"]
            and card["x"] <= cx <= card["x"] + card["w"]
            and card["y"] <= cy <= card["y"] + card["h"])


def _is_dark(hex_color: str) -> bool:
    if len(hex_color) != 6:
        return False
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.35


def _pattern(card: dict, children: list[dict]) -> str:
    kinds = {c["kind"] for c in children}
    if "chart" in kinds:
        return "chart_card"
    if "table" in kinds:
        return "table_card"
    if _is_dark(card["fill"]):
        return "dark_panel"
    texts = [c for c in children if c["text"] and c["max_font"]]
    if 2 <= len(texts) <= 4:
        value = max(texts, key=lambda c: c["max_font"])
        # one short value clearly larger than its label / note
        if len(value["text"]) <= 14 and value["max_font"] >= 1.4 * min(c["max_font"] for c in texts):
            return "kpi_tile"
    return "text_card"


def card_metrics(pptx_path: str | Path, slide: int = 1) -> list[dict]:
    """One entry per card that has content: pattern, fill ratio, frame (px)."""
    with zipfile.ZipFile(pptx_path) as z:
        shapes = _shapes(z.read(f"ppt/slides/slide{slide}.xml"))
    cards = []
    for card in (s for s in shapes if s["is_card"]):
        children = [s for s in shapes if _inside(s, card)]
        if not children:
            continue  # accent stripe / divider
        top = min(c["y"] for c in children)
        bottom = max(c["y"] + c["content_h"] for c in children)
        pad = max(0.0, min(top - card["y"], card["y"] + card["h"] - bottom, _MAX_PAD))
        inner = card["h"] - 2 * pad
        cards.append({
            "pattern": _pattern(card, children),
            "fill": round(min(1.0, (bottom - top) / inner), 3) if inner > 0 else 1.0,
            "frame": [round(card[k]) for k in ("x", "y", "w", "h")],
        })
    return cards


def pattern_match(generated: list[str], golden: list[str]) -> float:
    """Multiset overlap of card patterns: sum(min) / sum(max). 1.0 = same mix."""
    a, b = Counter(generated), Counter(golden)
    union = sum((a | b).values())
    return round(sum((a & b).values()) / union, 3) if union else 1.0
