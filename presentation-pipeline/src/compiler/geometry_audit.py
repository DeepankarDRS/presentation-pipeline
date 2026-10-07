"""Component-level layout check on what is DRAWN (2026-10-07, slide-quality item 2, step 1).

POM's own diagnostics (NODE_OUT_OF_BOUNDS, NODE_OVERLAP) compare layout boxes only.
A component can draw past its box: a squeezed table still writes every row at full
height, a diagram's labels run wider than its box. So this audit compares two sources:

  boxes   the positioned tree POM draws from (src/node/geometry.js -> geometry.json)
  drawn   every shape in the compiled .pptx; a table's drawn height is the sum of its rows

Each drawn shape is given to the smallest component box (a non-container node) that holds
its top-left corner; a container's own background shape is skipped. Rules, the same for
every component kind:

  GEOM_SPILL         a drawn shape leaves the card (framed stack) its component sits in,
                     or no component holds it at all
  GEOM_COLLISION     a drawn shape covers another component's box
  GEOM_OFF_SLIDE     a drawn shape leaves the slide
  GEOM_TEXT_OVERFLOW a text needs at least two lines more than its frame (estimate)
  GEOM_CARD_EMPTY    a tall card whose content spans < 55% of its height
  GEOM_BOX_EMPTY     a tall component box (table / diagram / chart) whose content uses < 50% of it
  GEOM_SLIDE_SPARSE  the slide's content ends above 75% of the slide height

Report only (layout_audit.REPORT_ONLY_CODES): measured first, no repair.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
_EMU = 9525
TOL = 2.0                 # px: rounding between layout and pptx
OWN_TOL = 4.0             # px: a drawn shape may start this far outside its box (text insets, rounding)
COLLIDE_MIN = 4.0         # px: smaller overlaps are not visible (checked by eye, 2026-10-07)
ERROR_PX = 10.0           # px: above this a spill / collision is a measured defect (tier error);
                          # 4-10 px were borderline by eye -> tier warning, the critic confirms
CARD_FILL_MIN = 0.55
BOX_FILL_MIN = 0.5
SLIDE_BOTTOM_MIN = 0.75
TALL = 120.0              # px: only cards / boxes at least this tall are judged for fill
CONTAINERS = {"vstack", "hstack", "layer"}
SPARSE_BY_DESIGN = {"cover", "section_break", "closing"}  # planner_schema.SlideTypeLiteral

GEOM_CODES = ("GEOM_SPILL", "GEOM_COLLISION", "GEOM_OFF_SLIDE", "GEOM_TEXT_OVERFLOW",
              "GEOM_CARD_EMPTY", "GEOM_BOX_EMPTY", "GEOM_SLIDE_SPARSE")


# --- the two sources ------------------------------------------------------------

def _flatten(node: dict, parent: dict | None, out: list[dict], path: str, card: dict | None,
             layer: dict | None) -> None:
    node = dict(node, parent=parent, path=path, card=card, layer=layer)
    out.append(node)
    if node["type"] in CONTAINERS:
        inner_card = node if node.get("frame") and parent is not None else card
        inner_layer = node if node["type"] == "layer" else layer
        for i, child in enumerate(node.get("children", [])):
            _flatten(child, node, out, f"{path} > {child['type']}[{i}]"
                     + (f"#{child['id']}" if child.get("id") else ""), inner_card, inner_layer)


def _table_rows(tbl: ET.Element) -> float:
    return sum(int(tr.get("h")) for tr in tbl.findall("a:tr", _NS)) / _EMU


def _table_text_height(tbl: ET.Element) -> float:
    """Height the table's text needs (POM stretches rows to fill a tall frame; the text stays
    at the top). Same estimate as scripts/eval_metrics.py: lines from characters x column
    width, 1.2 line height, cell margins, at least POM's default 32px row."""
    cols = [int(g.get("w")) / _EMU for g in tbl.iter(f"{{{_NS['a']}}}gridCol")]
    total = 0.0
    for tr in tbl.findall("a:tr", _NS):
        need, col = 0.0, 0
        for tc in tr.findall("a:tc", _NS):
            span = int(tc.get("gridSpan", 1))
            width = sum(cols[col:col + span])
            col += span
            lines, line_px = 0, 0.0
            for p in tc.iter(f"{{{_NS['a']}}}p"):
                text = "".join(t.text or "" for t in p.iter(f"{{{_NS['a']}}}t"))
                sizes = [int(r.get("sz")) for r in p.iter(f"{{{_NS['a']}}}rPr") if r.get("sz")]
                px = max(sizes, default=1800) / 100 * 4 / 3
                per_line = max(1.0, (width - 9.6) / (0.55 * px))
                lines += max(1, -(-len(text) // int(per_line)))
                line_px = max(line_px, 1.2 * px)
            need = max(need, lines * line_px + 9.6)
        total += min(int(tr.get("h")) / _EMU, max(need, 32.0))
    return total


def _text_need(sp: ET.Element, w: float) -> tuple[float, float]:
    """(estimated text height, one line) — ~0.5 em per character, 1.2 line height."""
    need, line = 0.0, 0.0
    for p in sp.iter(f"{{{_NS['a']}}}p"):
        text = "".join(t.text or "" for t in p.iter(f"{{{_NS['a']}}}t"))
        sizes = [int(r.get("sz")) for r in p.iter(f"{{{_NS['a']}}}rPr") if r.get("sz")]
        if not text.strip() or not sizes or w <= 0:
            continue
        px = max(sizes) / 100 * 4 / 3
        need += -(-len(text) * 0.5 * px // w) * px * 1.2
        line = max(line, px * 1.2)
    return need, line


def _drawn(slide_xml: bytes) -> list[dict]:
    root = ET.fromstring(slide_xml)
    out = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("sp", "graphicFrame", "pic", "cxnSp"):
            continue
        off, ext = el.find(".//a:off", _NS), el.find(".//a:ext", _NS)
        if off is None or ext is None:
            continue
        x, y = int(off.get("x")) / _EMU, int(off.get("y")) / _EMU
        w, h = int(ext.get("cx")) / _EMU, int(ext.get("cy")) / _EMU
        text = "".join(t.text or "" for t in el.iter(f"{{{_NS['a']}}}t")).strip()
        tbl = el.find(".//a:tbl", _NS)
        data = el.find(".//a:graphicData", _NS)
        uri = data.get("uri", "") if data is not None else ""
        xfrm = el.find(".//a:xfrm", _NS)
        if xfrm is not None and int(xfrm.get("rot", "0")) % 21600000:
            continue  # rotated (an axis label): its frame is not where it is drawn
        shape = {"x": x, "y": y, "w": w, "h": h, "text": text,
                 "kind": "table" if tbl is not None else "chart" if uri.endswith("/chart") else tag}
        # what is drawn: a table writes every row, whatever its frame says
        shape["dh"] = max(h, _table_rows(tbl)) if tbl is not None else h
        # ... and every column, whatever its frame width
        shape["dw"] = max(w, sum(int(g.get("w")) for g in tbl.iter(f"{{{_NS['a']}}}gridCol")) / _EMU) \
            if tbl is not None else w
        if tbl is not None:
            shape["text_h"] = _table_text_height(tbl)
        if tag == "sp" and text:
            shape["need"], shape["line"] = _text_need(el, w)
            if shape["need"] > h + 2 * shape["line"]:
                shape["dh"] = shape["need"]  # clearly more text than frame: judge where it is drawn
        out.append(shape)
    return out


# --- geometry helpers -------------------------------------------------------------

def _rect(n: dict, h: float | None = None) -> tuple[float, float, float, float]:
    return n["x"], n["y"], n["x"] + n["w"], n["y"] + (n["h"] if h is None else h)


def _overlap(a, b) -> tuple[float, float]:
    return min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])


def _within(node: dict, ancestor: dict) -> bool:
    p = node["parent"]
    while p is not None:
        if p is ancestor:
            return True
        p = p["parent"]
    return False


def _contains(outer, inner) -> bool:
    return (outer[0] - TOL <= inner[0] and outer[1] - TOL <= inner[1]
            and inner[2] <= outer[2] + TOL and inner[3] <= outer[3] + TOL)


def _past(inner, outer) -> dict[str, float]:
    over = {"left": outer[0] - inner[0], "top": outer[1] - inner[1],
            "right": inner[2] - outer[2], "bottom": inner[3] - outer[3]}
    return {k: round(v) for k, v in over.items() if v > TOL}


def _label(n: dict) -> str:
    return n["path"]


# --- the audit ----------------------------------------------------------------------

_PLACEHOLDER = re.compile(
    r"\[[^\[\]\n]{1,40}\]"                       # [Platform B], [Brand], [Insert chart]
    r"|(?<![\w])X+[.,]X+(?![\w])"                # X.XX, XX,XXX
    r"|(?<![\w])XX+(?![\w])"                     # XX, XXX
    r"|\b(?:TBD|TBC|TODO|lorem ipsum|placeholder)\b"
    r"|\b(?:Insight|Metric|Point|Item) [0-9A-C]\b(?= ?[—:-])"
    r"|\bMETRIC [A-C]\b",
    re.IGNORECASE)


def _placeholders(text: str, brief: str) -> list[str]:
    """Placeholder-looking runs in drawn text; a bracketed name the brief itself uses
    (an anonymised client: "[Platform B]") is content, not a placeholder."""
    out = []
    for m in _PLACEHOLDER.finditer(text or ""):
        hit = m.group(0)
        if hit.startswith("[") and hit.lower() in (brief or "").lower():
            continue
        if not hit.startswith("[") and hit.isupper() and hit.strip("X.,") and len(hit) > 3:
            continue  # an acronym, not X-filler
        out.append(hit)
    return out


def audit_geometry(geometry: dict[str, Any], pptx_path: str | Path, slide: int = 1,
                   slide_type: str = "", brief: str = "") -> list[dict[str, str]]:
    tree = geometry["slides"][slide - 1]
    sw, sh = geometry["slideSize"]["w"], geometry["slideSize"]["h"]
    nodes: list[dict] = []
    _flatten(tree, None, nodes, tree["type"], None, None)
    leaves = [n for n in nodes if n["type"] not in CONTAINERS]
    frames = [n for n in nodes if n["type"] in CONTAINERS]
    with zipfile.ZipFile(pptx_path) as z:
        shapes = _drawn(z.read(f"ppt/slides/slide{slide}.xml"))

    issues: list[dict[str, str]] = []
    seen: set[tuple] = set()

    def add(code: str, severity: str, key: tuple, message: str, px: float | None = None) -> None:
        """tier: error = measured defect (> ERROR_PX, or always for PLACEHOLDER_TEXT): code fix or repair;
        warning = borderline: the visual critic confirms it on the screenshot; info = fill, owned by code."""
        if (code,) + key in seen:
            return
        seen.add((code,) + key)
        if code in ("GEOM_CARD_EMPTY", "GEOM_BOX_EMPTY", "GEOM_SLIDE_SPARSE"):
            tier = "info"
        elif code == "PLACEHOLDER_TEXT" or (px is not None and px > ERROR_PX):
            tier = "error"
        else:
            tier = "warning"
        issues.append({"severity": severity, "code": code, "message": message, "tier": tier})

    owned: dict[int, list[dict]] = {}
    for s in shapes:
        if not s["text"] and s["kind"] == "sp" and any(
                abs(s["x"] - f["x"]) <= TOL and abs(s["y"] - f["y"]) <= TOL
                and abs(s["w"] - f["w"]) <= TOL and abs(s["h"] - f["h"]) <= TOL for f in frames):
            continue  # a stack's own background / border
        holders = [n for n in leaves
                   if n["x"] - OWN_TOL <= s["x"] <= n["x"] + n["w"] + OWN_TOL
                   and n["y"] - OWN_TOL <= s["y"] <= n["y"] + n["h"] + OWN_TOL]
        drawn = (s["x"], s["y"], s["x"] + s["dw"], s["y"] + s["dh"])
        if not holders:
            if s["w"] * s["h"] > 0:
                add("GEOM_SPILL", "high", ("orphan", round(s["x"]), round(s["y"])),
                    f'a {s["kind"]} drawn at ({s["x"]:.0f},{s["y"]:.0f}) {s["w"]:.0f}x{s["dh"]:.0f}px '
                    f'lies in no component box' + (f' ("{s["text"][:30]}")' if s["text"] else ""))
            continue
        # the box the frame overlaps most (a text starting 1px above its box is not its
        # neighbour's); ties -> the smaller box (a diagram node inside a card-sized leaf)
        frame = (s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"])

        def share(n: dict) -> float:
            ow, oh = _overlap(frame, _rect(n))
            return max(ow, 0.0) * max(oh, 0.0)
        owner = max(holders, key=lambda n: (round(share(n)), -n["w"] * n["h"]))
        owned.setdefault(id(owner), []).append(s)

        if s["kind"] == "cxnSp":
            continue  # connectors may run between boxes
        # R1: out of the card the component sits in
        if owner["card"] is not None:
            past = _past(drawn, _rect(owner["card"]))
            if past:
                add("GEOM_SPILL", "high", (owner["path"],),
                    f'{owner["type"]} {_label(owner)} draws past its card '
                    + ", ".join(f"{k} by {v}px" for k, v in past.items())
                    + (f' (rows {s["dh"]:.0f}px in a {s["h"]:.0f}px frame)' if s["kind"] == "table" and s["dh"] > s["h"] + TOL else ""),
                    px=max(past.values()))
        # R2: over another component's box
        for other in leaves:
            if other is owner or (owner["layer"] is not None and other["layer"] is owner["layer"]):
                continue
            ow, oh = _overlap(drawn, _rect(other))
            if ow > COLLIDE_MIN and oh > COLLIDE_MIN:
                add("GEOM_COLLISION", "high", tuple(sorted((owner["path"], other["path"]))),
                    f'{owner["type"]} {_label(owner)} draws over {other["type"]} {_label(other)} '
                    f"by {ow:.0f}x{oh:.0f}px", px=min(ow, oh))
        # R3: off the slide
        past = _past(drawn, (0, 0, sw, sh))
        if past:
            add("GEOM_OFF_SLIDE", "high", (owner["path"],),
                f'{owner["type"]} {_label(owner)} draws off the slide '
                + ", ".join(f"{k} by {v}px" for k, v in past.items()), px=max(past.values()))
        # R4: text needs more lines than its frame holds
        if s.get("need") and s["need"] > s["h"] + 2 * s["line"]:
            add("GEOM_TEXT_OVERFLOW", "medium", (owner["path"], round(s["y"])),
                f'text "{s["text"][:30]}" needs ~{s["need"]:.0f}px in a {s["h"]:.0f}px frame')

    # R2b: text over text, also inside one component (matrix labels, layer captions):
    # never intended. A text inside a filled shape that holds it is a label, not a collision.
    texts = [s for s in shapes if s["text"] and s["kind"] == "sp"]
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            ra = (a["x"], a["y"], a["x"] + a["w"], a["y"] + a["h"])
            rb = (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])
            ow, oh = _overlap(ra, rb)
            if ow > 4 and oh > 4 and not _contains(ra, rb) and not _contains(rb, ra):
                add("GEOM_COLLISION", "high", ("text", round(a["x"]), round(a["y"]), round(b["x"]), round(b["y"])),
                    f'text "{a["text"][:25]}" and text "{b["text"][:25]}" overlap by {ow:.0f}x{oh:.0f}px',
                    px=min(ow, oh))

    # placeholder text left on the slide (a recipe's "X.XX", "[Platform B]" not in the brief, TBD)
    for s in shapes:
        for hit in _placeholders(s["text"], brief):
            add("PLACEHOLDER_TEXT", "high", ("ph", hit), f'placeholder text "{hit}" on the slide')

    # R5: fill — content (what is drawn inside) against the box it was given
    def content_span(members: list[dict]) -> float:
        if not members:
            return 0.0
        return max(m["y"] + m["dh"] for m in members) - min(m["y"] for m in members)

    for card in (f for f in frames if f.get("frame") and f["parent"] is not None and f["h"] >= TALL):
        # everything inside the card, at any depth; a nested card counts as its full box
        inside = [s for n in leaves if _within(n, card) for s in owned.get(id(n), [])]
        inside += [{"y": f["y"], "dh": f["h"]} for f in frames
                   if f is not card and f.get("frame") and _within(f, card)]
        if inside and content_span(inside) / card["h"] < CARD_FILL_MIN:
            add("GEOM_CARD_EMPTY", "low", (card["path"],),
                f'card {_label(card)} is {card["h"]:.0f}px tall, its content spans '
                f'{content_span(inside):.0f}px ({content_span(inside) / card["h"]:.0%})')
    for leaf in leaves:
        if leaf["type"] in ("text", "shape", "icon", "image", "line", "arrow") or leaf["h"] < TALL:
            continue
        members = owned.get(id(leaf), [])
        if leaf["type"] == "table":
            used = sum(_table_text_rows(m) for m in members) or content_span(members)
        else:
            used = content_span(members)
        if members and used / leaf["h"] < BOX_FILL_MIN:
            add("GEOM_BOX_EMPTY", "low", (leaf["path"],),
                f'{leaf["type"]} {_label(leaf)} has a {leaf["h"]:.0f}px box, its content uses '
                f'{used:.0f}px ({used / leaf["h"]:.0%})')
    content = [s for ss in owned.values() for s in ss]
    if content and slide_type not in SPARSE_BY_DESIGN:
        bottom = max(s["y"] + s["dh"] for s in content)
        if bottom < SLIDE_BOTTOM_MIN * sh:
            add("GEOM_SLIDE_SPARSE", "low", ("slide",),
                f"the slide's content ends at {bottom:.0f}px ({bottom / sh:.0%} of the height)")
    return issues


def _table_text_rows(shape: dict) -> float:
    # a table frame that POM stretched: its text, not its rows, is the content (set by _drawn callers)
    return shape.get("text_h", 0.0)


def audit_run_folder(folder: str | Path, slide_type: str = "", brief: str = "") -> list[dict[str, str]]:
    """geometry.json + presentation.pptx in one compile folder -> issues ([] when either is missing)."""
    folder = Path(folder)
    geo, pptx = folder / "geometry.json", folder / "presentation.pptx"
    if not geo.exists() or not pptx.exists():
        return []
    return audit_geometry(json.loads(geo.read_text(encoding="utf-8")), pptx, slide_type=slide_type, brief=brief)
