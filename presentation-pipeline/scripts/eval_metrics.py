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

import re
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


def word_breaks(pptx_path: str | Path, slide: int = 1) -> int:
    """Text boxes whose longest word is wider than the box (~0.55 em per character): the word is
    split mid-word ("Wi / nn / er"). Crushed cards still read as 'full', so fill cannot see this."""
    with zipfile.ZipFile(pptx_path) as z:
        shapes = _shapes(z.read(f"ppt/slides/slide{slide}.xml"))
    return sum(
        max(len(w) for w in s["text"].split()) * 0.55 * s["max_font"] * 4 / 3 > s["w"] + 1
        for s in shapes if s["kind"] == "sp" and s["text"] and s["max_font"]
    )


def text_overflows(pptx_path: str | Path, slide: int = 1) -> int:
    """Text boxes whose wrapped text (~0.5 em per character, 1.2 line height) needs at least two lines
    more than the box holds: the text spills out of its box / card / slide (e.g. long Timeline
    labels). The margin keeps one-line estimate errors from counting."""
    with zipfile.ZipFile(pptx_path) as z:
        root = ET.fromstring(z.read(f"ppt/slides/slide{slide}.xml"))
    count = 0
    for sp in root.iter(f"{{{_NS['p']}}}sp"):
        ext = sp.find(".//a:ext", _NS)
        if ext is None or sp.find(".//p:txBody", _NS) is None:
            continue
        w, h = int(ext.get("cx")) / _EMU_PER_PX, int(ext.get("cy")) / _EMU_PER_PX
        need, line = 0.0, 0.0
        for p in sp.iter(f"{{{_NS['a']}}}p"):
            text = "".join(t.text or "" for t in p.iter(f"{{{_NS['a']}}}t"))
            sizes = [int(r.get("sz")) for r in p.iter(f"{{{_NS['a']}}}rPr") if r.get("sz")]
            if not text.strip() or not sizes or w <= 0:
                continue
            px = max(sizes) / 100 * 4 / 3
            need += -(-len(text) * 0.5 * px // w) * px * 1.2
            line = max(line, px * 1.2)
        count += need > h + 2 * line
    return count


def table_spill(pptx_path: str | Path, slide: int = 1) -> int:
    """Px of table rows past their frame, summed over the slide's tables: POM flex-shrinks a table box on
    an over-full slide but still writes every row, so the rows spill over the next band. The fill metric
    reads declared frames and cannot see it."""
    with zipfile.ZipFile(pptx_path) as z:
        root = ET.fromstring(z.read(f"ppt/slides/slide{slide}.xml"))
    spill = 0.0
    for frame in root.iter(f"{{{_NS['p']}}}graphicFrame"):
        tbl, ext = frame.find(".//a:tbl", _NS), frame.find(".//a:ext", _NS)
        if tbl is None or ext is None:
            continue
        rows = sum(int(tr.get("h")) for tr in tbl.findall("a:tr", _NS))
        spill += max(0, rows - int(ext.get("cy"))) / _EMU_PER_PX
    return round(spill)


_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_CONTENT_ATTRS = ("value", "label", "title", "description", "date", "text", "name")


def _numbers(text: str) -> list[str]:
    """Numbers with ≥2 digits, thousands separators dropped ("10,332" → "10332")."""
    return [n.replace(",", "") for n in _NUMBER.findall(text) if len(re.sub(r"\D", "", n)) >= 2]


def invented_numbers(slide_xml: str, brief: str) -> list[str]:
    """Numbers shown on the slide (text, chart values, diagram labels) that appear nowhere in the
    brief — invented or mangled data. Formatting variants ("4.40" vs "4.4") are not counted."""
    known = {n.rstrip("0").rstrip(".") if "." in n else n for n in _numbers(brief)}
    xml = re.sub(r"&(?![a-zA-Z]+;|#\d+;)", "&amp;", re.sub(r"<Theme\b[^>]*/>", "", slide_xml))
    shown = []
    for el in ET.fromstring(f"<r>{xml}</r>").iter():
        shown += _numbers(el.text or "")
        shown += [n for a in _CONTENT_ATTRS if el.get(a) for n in _numbers(el.get(a))]
    return [n for n in shown if (n.rstrip("0").rstrip(".") if "." in n else n) not in known]


def pattern_match(generated: list[str], golden: list[str]) -> float:
    """Multiset overlap of card patterns: sum(min) / sum(max). 1.0 = same mix."""
    a, b = Counter(generated), Counter(golden)
    union = sum((a | b).values())
    return round(sum((a & b).values()) / union, 3) if union else 1.0
