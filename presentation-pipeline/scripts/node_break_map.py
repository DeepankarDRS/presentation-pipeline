"""Node break map (2026-10-21): where each diagram node breaks and where it holds, measured, LLM-free.

    python -m scripts.node_break_map                      # all six diagrams -> docs/eval/node-break-map/
    python -m scripts.node_break_map --kinds flow process_arrow --jobs 4
    python -m scripts.node_break_map --kinds timeline --quick   # a slice, to try a change

Each case is one slide written the way the generator writes it (Slide > VStack padding 56 > a 36 px
headline > the body), with the diagram in one of five placements — so the box it gets comes from its
parent's direction and POM's own stretch rules, not from a size given here:

  band            the diagram straight in the root VStack under the headline (h="max": the full band)
  band-under-kpi  a 150 px row of KPI cards, then the diagram in the rest of the band
  split-60        an HStack: the diagram w="62%" beside a text column (60/40, the evidence side wider)
  split-40        an HStack: a text column beside the diagram w="38%" (the narrow column)
  card            one card of a 2 x 2 card grid, under the card's title

Axes: item count, label length (one short word / one long word / 2 / 3 / 4 words), direction (tree:
layout), the label style where the node takes one (POM's default vs fontFamily="Inter" bold 16 px, as
the generator writes them), flow node shapes, matrix spacing.

Every case compiles twice (src/node/break-map.js): raw (what POM does) and with fit-grow (what the
pipeline ships), in the deck font (src/node/fonts). The drawn shapes are read from the .pptx
(node_facts.drawn_shapes) and each text is measured by POM's own text measurement in the typeface and
size it was drawn in. Failure codes, per case:

  WORD_BROKEN    a text's longest word is wider than its drawn box less its insets (the renderer breaks it)
  TEXT_OVERFLOW  a text's lines are taller than its drawn box less its insets (they run out of it)
  SHRUNK         a label drawn below min(14 px, the node's own default size): POM's scale-to-fit or
                 fit-grow's word guard made the text smaller than the node draws it at full size
  SCALE_FLOOR    POM's SCALE_BELOW_THRESHOLD: the diagram needed < 50 % and is drawn past its box
  OVERLAP        two texts of the same role overlap (labels, nodes, dates)
  SPILL          a drawn shape leaves the diagram's box (into the headline / its neighbour)
  OFF_SLIDE      a drawn shape leaves the slide
  GUARD          fit-grow left a WORD_TOO_WIDE warning
  COMPILE        the slide does not compile

Writes output/node-break-map/<kind>.json (every case) and docs/eval/node-break-map/<kind>.md (the map).
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.compiler.node_facts import Box, drawn_shapes  # noqa: E402

RUNNER = ROOT / "src" / "node" / "break-map.js"
OUT = ROOT / "output" / "node-break-map"
DOCS = ROOT / "docs" / "eval" / "node-break-map"
SLIDE_W, SLIDE_H = 1280, 720
FLOOR_PX = 14
SPILL_TOL = 8   # px past its box a diagram may draw into the 24 px gap around it before it counts (a vertical
                # timeline's first date sits 3 px above its box; POM's < 50 % overflow is tens of px)

KINDS = ("flow", "process_arrow", "timeline", "tree", "matrix", "pyramid")
TAG = {"flow": "flow", "process_arrow": "processArrow", "timeline": "timeline", "tree": "tree",
       "matrix": "matrix", "pyramid": "pyramid"}
PLACEMENTS = ("band", "band-under-kpi", "split-60", "split-40", "card")

# label sets: twelve distinct labels each (a case never draws the same text twice)
LABELS = {
    "w1": ["Plan", "Build", "Test", "Launch", "Scale", "Audit", "Hire", "Train", "Ship", "Review", "Price", "Grow"],
    "long1": ["Profitability", "Reconciliation", "Implementation", "Infrastructure", "Accountability",
              "Optimization", "Procurement", "Transformation", "Benchmarking", "Consolidation",
              "Sustainability", "Digitalization"],
    "w2": ["Market research", "Price testing", "Pilot launch", "Team hiring", "Vendor review", "Cost audit",
           "Data cleanup", "Brand refresh", "Sales training", "Risk review", "Store rollout", "Board approval"],
    "w3": ["Define pricing strategy", "Run pilot stores", "Hire regional leads", "Audit vendor costs",
           "Launch loyalty program", "Clean customer data", "Train sales teams", "Review risk register",
           "Expand delivery zones", "Measure brand lift", "Close the books", "Renew key contracts"],
    "w4": ["Review all supplier contracts", "Open three pilot stores", "Hire two regional leads",
           "Audit every vendor cost", "Launch the loyalty program", "Clean up customer data",
           "Train all sales teams", "Review the risk register", "Expand into new zones",
           "Measure brand lift monthly", "Close the quarterly books", "Renew the key contracts"],
}
LABEL_NAMES = {"w1": "1 short word", "long1": "1 long word", "w2": "2 words", "w3": "3 words", "w4": "4 words"}
DATES = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026",
         "Q1 2027", "Q2 2027", "Q3 2027", "Q4 2027"]

# the share of a flow shape's width / height its text rectangle takes (copied from fit-grow.js FLOW_TEXT_RECT)
FLOW_TEXT_RECT = {
    "flowChartDecision": (0.5, 0.5), "flowChartInputOutput": (0.6, 1), "flowChartTerminator": (0.9, 0.7),
    "flowChartPredefinedProcess": (0.75, 1), "flowChartPreparation": (0.6, 1), "flowChartManualOperation": (0.6, 1),
    "flowChartConnector": (0.7, 0.7), "flowChartDelay": (0.85, 0.7), "flowChartDocument": (1, 0.8),
    "flowChartManualInput": (1, 0.8), "flowChartMagneticDisk": (1, 0.5),
}


# ── the grid ───────────────────────────────────────────────────────────────────

@dataclass
class Case:
    kind: str
    placement: str
    direction: str
    labels: str
    count: int
    style: str = "default"    # default | inter (fontFamily="Inter" bold 16 where the node takes it)
    variant: str = ""         # flow: process | mixed shapes; matrix: spacing; tree: depth
    roles: dict[str, str] = field(default_factory=dict)   # drawn text -> role
    defaults: dict[str, float] = field(default_factory=dict)  # role -> the node's own font px

    @property
    def id(self) -> str:
        return "~".join([self.kind, self.placement, self.direction, self.labels, self.style,
                         self.variant or "-", f"{self.count:02d}"])

    def series(self) -> tuple:
        """Every axis but the count: one row of the map."""
        return (self.placement, self.direction, self.style, self.variant, self.labels)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _style_attrs(c: Case) -> str:
    if c.style != "inter":
        return ""
    return ' fontFamily="Inter" bold="true" fontSize="16"' if c.kind in ("process_arrow", "pyramid") \
        else ' fontFamily="Inter"'


def diagram_xml(c: Case, box: str) -> str:
    """The diagram element; `box` = its size attributes for the placement."""
    labels = LABELS[c.labels]
    st = _style_attrs(c)
    if c.kind == "flow":
        shapes = ["flowChartProcess"] * c.count
        if c.variant == "mixed":
            shapes[0] = shapes[-1] = "flowChartTerminator"
            if c.count >= 4:
                shapes[c.count // 2] = "flowChartDecision"
        nodes = "".join(f'<FlowNode id="n{i}" shape="{s}" text="{_esc(labels[i])}"/>' for i, s in enumerate(shapes))
        links = "".join(f'<FlowConnection from="n{i}" to="n{i + 1}"/>' for i in range(c.count - 1))
        for i in range(c.count):
            c.roles[labels[i]] = "node"
        c.defaults = {"node": 14}
        return f'<Flow direction="{c.direction}"{box}>{nodes}{links}</Flow>'
    if c.kind == "process_arrow":
        steps = "".join(f'<ProcessArrowStep label="{_esc(labels[i])}"/>' for i in range(c.count))
        for i in range(c.count):
            c.roles[labels[i]] = "label"
        c.defaults = {"label": 16 if c.style == "inter" else 14}
        return f'<ProcessArrow direction="{c.direction}"{box}{st}>{steps}</ProcessArrow>'
    if c.kind == "timeline":
        items = "".join(f'<TimelineItem date="{DATES[i]}" title="{_esc(labels[i])}"/>' for i in range(c.count))
        for i in range(c.count):
            c.roles[labels[i]] = "title"
            c.roles[DATES[i]] = "date"
        c.defaults = {"title": 14, "date": 12}
        return f'<Timeline direction="{c.direction}"{box}{st}>{items}</Timeline>'
    if c.kind == "tree":
        root, rest = labels[0], labels[1:]
        if c.variant == "depth3":   # root -> 2 groups -> the leaves split between them
            a, b = rest[0], rest[1]
            leaves = rest[2:2 + c.count]
            half = (len(leaves) + 1) // 2
            kids = (f'<TreeItem label="{_esc(a)}">' + "".join(f'<TreeItem label="{_esc(x)}"/>' for x in leaves[:half])
                    + f'</TreeItem><TreeItem label="{_esc(b)}">'
                    + "".join(f'<TreeItem label="{_esc(x)}"/>' for x in leaves[half:]) + "</TreeItem>")
            used = [root, a, b, *leaves]
        else:
            leaves = rest[:c.count]
            kids = "".join(f'<TreeItem label="{_esc(x)}"/>' for x in leaves)
            used = [root, *leaves]
        for x in used:
            c.roles[x] = "node"
        c.defaults = {"node": 12}
        return f'<Tree layout="{c.direction}"{box}><TreeItem label="{_esc(root)}">{kids}</TreeItem></Tree>'
    if c.kind == "matrix":
        step = float(c.variant.removeprefix("d"))
        # a lattice `step` apart, centred: the quadrant labels sit in the corners, so items placed there
        # collide with them whatever their spacing (a separate fact, not this sweep's axis)
        per_row = int(0.6 / step) + 1
        cols, rows_ = min(c.count, per_row), -(-c.count // per_row)
        x0, y0 = 0.5 - step * (cols - 1) / 2, 0.5 + step * (rows_ - 1) / 2
        items = []
        for i in range(c.count):
            x, y = x0 + step * (i % per_row), y0 - step * (i // per_row)
            items.append(f'<MatrixItem label="{_esc(labels[i])}" x="{min(x, 0.95):.2f}" y="{max(y, 0.05):.2f}"/>')
            c.roles[labels[i]] = "item"
        quads = {"topLeft": "Quick wins", "topRight": "Big bets", "bottomLeft": "Fill-ins", "bottomRight": "Money pits"}
        for q in quads.values():
            c.roles[q] = "quadrant"
        c.roles["Effort"] = c.roles["Impact"] = "axis"
        c.defaults = {"item": 11, "quadrant": 11, "axis": 12}
        q = " ".join(f'{k}="{v}"' for k, v in quads.items())
        return (f'<Matrix{box}><MatrixAxes x="Effort" y="Impact"/><MatrixQuadrants {q}/>'
                + "".join(items) + "</Matrix>")
    if c.kind == "pyramid":
        levels = "".join(f'<PyramidLevel label="{_esc(labels[i])}"/>' for i in range(c.count))
        for i in range(c.count):
            c.roles[labels[i]] = "level"
        c.defaults = {"level": 16 if c.style == "inter" else 14}
        return f'<Pyramid direction="up"{box}{st}>{levels}</Pyramid>'
    raise ValueError(c.kind)


_TEXT = '<Text fontSize="18" fontFamily="Inter" color="334155">{}</Text>'
_SIDE = ('<VStack w="max" gap="12" alignItems="stretch">'
         + _TEXT.format("What the diagram shows, in one or two plain sentences for the reader.")
         + _TEXT.format("A second point the slide makes beside it.") + "</VStack>")


def _card(title: str, inner: str) -> str:
    return (f'<VStack w="max" padding="24" gap="12" backgroundColor="F1F5F9" alignItems="stretch">'
            f'<Text fontSize="20" bold="true" fontFamily="Inter">{title}</Text>{inner}</VStack>')


def slide_xml(c: Case) -> str:
    p = c.placement
    if p in ("band", "band-under-kpi"):
        body = diagram_xml(c, ' h="max"')
        if p == "band-under-kpi":
            tile = ('<VStack w="max" padding="16" gap="4" backgroundColor="F1F5F9" alignItems="stretch">'
                    '<Text fontSize="40" bold="true" fontFamily="Inter">{}</Text>'
                    '<Text fontSize="14" fontFamily="Inter" color="55627A">{}</Text></VStack>')
            kpis = "".join(tile.format(v, k) for v, k in (("$4.2M", "Revenue"), ("18%", "Margin"), ("212", "Stores")))
            body = f'<HStack gap="24" h="150" alignItems="stretch">{kpis}</HStack>' + body
    elif p == "split-60":
        wide = diagram_xml(c, ' w="62%"')
        body = f'<HStack gap="24" h="max" alignItems="stretch">{wide}{_SIDE}</HStack>'
    elif p == "split-40":
        narrow = diagram_xml(c, ' w="38%"')
        body = f'<HStack gap="24" h="max" alignItems="stretch">{_SIDE}{narrow}</HStack>'
    elif p == "card":
        cards = [_card("The process", diagram_xml(c, ' h="max"')), _card("Context", _TEXT.format("Notes."))]
        other = [_card("Risks", _TEXT.format("Notes.")), _card("Next step", _TEXT.format("Notes."))]
        row = '<HStack gap="24" h="max" alignItems="stretch">{}</HStack>'
        body = row.format("".join(cards)) + row.format("".join(other))
    else:
        raise ValueError(p)
    return ('<Slide><VStack w="1280" h="720" padding="56" gap="24" alignItems="stretch" backgroundColor="FFFFFF">'
            '<Text fontSize="36" bold="true" fontFamily="Inter" color="16202E">A headline that states the point</Text>'
            f"{body}</VStack></Slide>")


def grid(kinds: list[str], quick: bool = False) -> list[Case]:
    """Every case of the map (quick: the edges only — fewer counts, placements and label sets)."""
    counts = {"flow": range(3, 11), "process_arrow": range(3, 11), "timeline": range(3, 11),
              "tree": range(2, 9), "matrix": range(2, 9), "pyramid": range(3, 8)}
    dirs = {"flow": ("horizontal", "vertical"), "process_arrow": ("horizontal", "vertical"),
            "timeline": ("horizontal", "vertical"), "tree": ("vertical", "horizontal"),
            "matrix": ("-",), "pyramid": ("up",)}
    styles = {"process_arrow": ("default", "inter"), "timeline": ("default", "inter"), "pyramid": ("default", "inter")}
    variants = {"flow": ("process", "mixed"), "tree": ("depth2", "depth3"), "matrix": ("d0.1", "d0.18", "d0.3")}
    label_sets = {"tree": ("w1", "long1", "w2", "w3"), "matrix": ("w1", "long1", "w2")}
    out = []
    for kind in kinds:
        places = ("band", "split-40") if quick else PLACEMENTS
        labs = label_sets.get(kind, tuple(LABELS))
        if quick:
            labs = tuple(x for x in labs if x in ("long1", "w2"))
        ns = list(counts[kind])
        if quick:
            ns = ns[::2]
        for p, d, st, v, lab, n in itertools.product(places, dirs[kind], styles.get(kind, ("default",)),
                                                     variants.get(kind, ("",)), labs, ns):
            out.append(Case(kind, p, d, lab, n, st, v))
    return out


# ── compiling and measuring ────────────────────────────────────────────────────

def _node(args: list[str]) -> None:
    subprocess.run(["node", str(RUNNER), *args], check=True, capture_output=True,
                   encoding="utf-8", errors="replace", cwd=RUNNER.parent)


def compile_cases(cases: list[Case], workdir: Path, jobs: int = 4, chunk: int = 60,
                  modes: tuple[str, ...] = ("raw", "fit")) -> dict[str, dict]:
    """(case id, raw | fit) -> build result; `jobs` node processes, `chunk` slides each."""
    items = [{"id": f"{c.id}~{mode}", "xml": slide_xml(c), "fit": mode == "fit"} for c in cases for mode in modes]
    batches = [items[i:i + chunk] for i in range(0, len(items), chunk)]

    def run(i_batch):
        i, batch = i_batch
        d = workdir / f"b{i:04d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "cases.json").write_text(json.dumps(batch), encoding="utf-8")
        _node(["build", str(d / "cases.json"), str(d)])
        return json.loads((d / "build-results.json").read_text(encoding="utf-8"))

    out = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for res in ex.map(run, enumerate(batches)):
            for r in res:
                out[r["id"]] = r
    return out


def measure_texts(reqs: list[dict], workdir: Path) -> list[dict]:
    src, dst = workdir / "measure.json", workdir / "measured.json"
    src.write_text(json.dumps(reqs), encoding="utf-8")
    _node(["measure", str(src), str(dst)])
    return json.loads(dst.read_text(encoding="utf-8"))


def _find(geo: dict | None, tag: str) -> dict | None:
    stack = [geo] if geo else []
    while stack:
        n = stack.pop(0)
        if n.get("type") == tag:
            return n
        stack.extend(n.get("children", []))
    return None


def _text_area(c: Case, s: Box) -> Box:
    """The rectangle the renderer sets a drawn text in: its box less insets (flow: the shape's text rect)."""
    fw, fh = FLOW_TEXT_RECT.get(s.geom, (1, 1)) if c.kind == "flow" else (1, 1)
    w, h = s.w * fw, s.h * fh
    x, y = s.x + (s.w - w) / 2, s.y + (s.h - h) / 2
    return Box(x + s.pad / 2, y + s.vpad / 2, w - s.pad, h - s.vpad)


def _extent(s: Box, area: Box, line_w: float, height: float) -> Box:
    """Where the text's lines are drawn: its widest line set by the alignment, its lines by the anchor."""
    tw = min(line_w, area.w) if area.w > 0 else line_w
    x = area.cx - tw / 2 if s.algn == "ctr" else area.r - tw if s.algn == "r" else area.x
    y = area.cy - height / 2 if s.anchor == "ctr" else area.b - height if s.anchor == "b" else area.y
    return Box(x, y, tw, height, s.text)


def _overlap(a: Box, b: Box, tol: float = 1.0) -> bool:
    return min(a.r, b.r) - max(a.x, b.x) > tol and min(a.b, b.b) - max(a.y, b.y) > tol


def _inside(a: Box, b: Box, tol: float = 1.0) -> bool:
    return a.x >= b.x - tol and a.y >= b.y - tol and a.r <= b.r + tol and a.b <= b.b + tol


def _geo_boxes(geo: dict | None, skip: str) -> list[Box]:
    """Boxes of every node in the positioned tree except the diagram's (stack backgrounds, other texts)."""
    out, stack = [], [geo] if geo else []
    while stack:
        n = stack.pop()
        if n.get("type") != skip:
            out.append(Box(n["x"], n["y"], n["w"], n["h"]))
        stack.extend(n.get("children", []))
    return out


def _same_rect(a: Box, b: Box, tol: float = 1.5) -> bool:
    return all(abs(p - q) <= tol for p, q in ((a.x, b.x), (a.y, b.y), (a.w, b.w), (a.h, b.h)))


def _container(s: Box, fills: list[Box]) -> Box | None:
    """The visible shape a text sits on: itself when filled, else the smallest filled shape around its centre."""
    if s.filled:
        return s
    around = [f for f in fills if _inside(s, f, 2)]   # a dot under a label's centre is not what holds it
    return min(around, key=lambda f: f.w * f.h, default=None)


def evaluate(cases: list[Case], built: dict[str, dict], workdir: Path) -> list[dict]:
    """One row per (case, mode) with the failure codes and the measures behind them."""
    rows, pending = [], []
    for c in cases:
        for mode in ("raw", "fit"):
            if f"{c.id}~{mode}" not in built:
                continue
            r = built[f"{c.id}~{mode}"]
            row = {"id": c.id, "mode": mode, "kind": c.kind, "placement": c.placement, "direction": c.direction,
                   "labels": c.labels, "count": c.count, "style": c.style, "variant": c.variant,
                   "codes": [], "detail": [], "ms": r.get("ms")}
            rows.append(row)
            if r["status"] != "success":
                row["codes"].append("COMPILE")
                row["detail"].append(" | ".join(r["errors"])[:200])
                continue
            warn = [w["code"] for w in r["warnings"]]
            if "SCALE_BELOW_THRESHOLD" in warn:
                row["codes"].append("SCALE_FLOOR")
            if "WORD_TOO_WIDE" in warn:
                row["codes"].append("GUARD")
            row["fit_grow"] = [x.removeprefix("slide 1: ") for x in r.get("fitGrow") or []]
            node = _find(r["geometry"], TAG[c.kind])
            row["box"] = [round(node["w"]), round(node["h"])] if node else None
            shapes = drawn_shapes(r["pptx"])
            mine = [s for s in shapes if s.text in c.roles]
            small = [s for s in mine if s.font and s.font < min(FLOOR_PX, c.defaults[c.roles[s.text]]) - 0.1]
            row["min_px"] = min((s.font for s in mine if s.font), default=None)
            if small:
                row["codes"].append("SHRUNK")
                row["detail"].append(f"{small[0].text!r} {small[0].font:g} px")
            others_geo = _geo_boxes(r["geometry"], TAG[c.kind])
            # the diagram's own textless shapes: not the background of a stack / card
            fills = [s for s in shapes if not s.text and s.w > 1 and s.h > 1 and s.geom != "line"]
            own_fills = [f for f in fills if not any(_same_rect(f, g) for g in others_geo)]
            others = [s for s in shapes if s.text and s.text not in c.roles]
            if any(s.x < -1 or s.y < -1 or s.r > SLIDE_W + 1 or s.b > SLIDE_H + 1 for s in shapes):
                row["codes"].append("OFF_SLIDE")
            bx = Box(node["x"], node["y"], node["w"], node["h"]) if node else None
            out_fill = [f for f in own_fills if bx and not _inside(f, bx, SPILL_TOL)]
            row["_ctx"] = (c, bx, fills, others, out_fill)
            for s in mine:
                pending.append((row, s, _text_area(c, s)))
    # one measuring spawn for every drawn text
    def key(s: Box, area: Box):
        return (s.text, s.family or "Noto Sans JP", s.font or 18, s.bold, round(max(area.w, 1), 2))

    keys = {key(s, a): None for _, s, a in pending}
    reqs = [{"text": t, "family": f, "px": px, "bold": b, "width": w} for t, f, px, b, w in keys]
    for k, m in zip(keys, measure_texts(reqs, workdir)):
        keys[k] = m
    extents = defaultdict(list)
    for row, s, area in pending:
        m = keys[key(s, area)]
        c, bx, fills, others, _ = row["_ctx"]
        # any deficit breaks: a word 0.3 px wider than its box broke in a LibreOffice render (2026-10-21)
        if m["wordW"] > area.w and "WORD_BROKEN" not in row["codes"]:
            row["codes"].append("WORD_BROKEN")
            row["detail"].append(f"{m['word']!r} {m['wordW']:.0f} px in {area.w:.0f}")
        ext = _extent(s, area, m["lineW"], m["height"])
        extents[id(row)].append((row, s, ext))
        holder = _container(s, fills)
        room = _text_area(c, holder) if holder is s else holder
        if holder is not None and not _inside(ext, room, 1.0) and "TEXT_OVERFLOW" not in row["codes"]:
            row["codes"].append("TEXT_OVERFLOW")
            row["detail"].append(f"{s.text!r} {m['lines']} lines, {ext.h:.0f} x {ext.w:.0f} px "
                                 f"out of its {room.w:.0f} x {room.h:.0f} shape")
    for group in extents.values():
        row = group[0][0]
        c, bx, fills, others, out_fill = row.pop("_ctx")
        pair = next(((a, b) for (_, _, a), (_, _, b) in itertools.combinations(group, 2) if _overlap(a, b)), None)
        if pair:
            row["codes"].append("OVERLAP")
            row["detail"].append(f"{pair[0].text!r} / {pair[1].text!r}")
        spill = [e for _, _, e in group if bx and not _inside(e, bx, SPILL_TOL)] + out_fill
        hit = next(((e, o) for _, _, e in group for o in others if _overlap(e, o)), None)
        if spill or hit:
            row["codes"].append("SPILL")
            row["detail"].append(f"{hit[0].text!r} covers {hit[1].text!r}" if hit else
                                 f"{spill[0].text or 'a shape'!r} past the {bx.w:.0f}x{bx.h:.0f} box")
    for row in rows:
        row.pop("_ctx", None)
    return rows


# ── the map ───────────────────────────────────────────────────────────────────

CODE_ORDER = ("COMPILE", "WORD_BROKEN", "TEXT_OVERFLOW", "OVERLAP", "SHRUNK", "SCALE_FLOOR", "SPILL",
              "OFF_SLIDE", "GUARD")
SHORT = {"COMPILE": "C", "WORD_BROKEN": "W", "TEXT_OVERFLOW": "T", "OVERLAP": "O", "SHRUNK": "S",
         "SCALE_FLOOR": "F", "SPILL": "P", "OFF_SLIDE": "X", "GUARD": "G"}


SOFT = {"GUARD"}  # shown, not a break: fit-grow's guard keeps 8 % slack for fonts it cannot load


def breaks(r: dict) -> list[str]:
    return [c for c in r["codes"] if c not in SOFT]


def holds_up_to(rows: list[dict]) -> tuple[int | None, dict | None]:
    """The largest count before the first break in a series (rows sorted by count); and the first broken row.
    None = the smallest count already breaks."""
    rows = sorted(rows, key=lambda r: r["count"])
    best = None
    for r in rows:
        if breaks(r):
            return best, r
        best = r["count"]
    return best, None


def series_table(rows: list[dict]) -> dict[tuple, dict[str, list[dict]]]:
    out: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[(r["placement"], r["direction"], r["style"], r["variant"])][r["labels"]].append(r)
    return out


def _cell(fit: list[dict], raw: list[dict]) -> str:
    n_fit, br_fit = holds_up_to(fit)
    n_raw, _ = holds_up_to(raw)
    top = max(r["count"] for r in fit)
    if br_fit is None:
        s = f"**≥{top}**"
    else:
        s = f"{n_fit if n_fit is not None else '–'} ({''.join(SHORT[c] for c in CODE_ORDER if c in br_fit['codes'])})"
    if n_raw != n_fit:
        s += f" · raw {n_raw if n_raw is not None else '–'}"
    return s


def write_doc(kind: str, rows: list[dict], cases_by_id: dict[str, Case]) -> str:
    fit = [r for r in rows if r["mode"] == "fit"]
    raw = [r for r in rows if r["mode"] == "raw"]
    labs = [x for x in LABELS if any(r["labels"] == x for r in fit)]
    lines = [f"# Break map: {kind}", "",
             f"Generated by `python -m scripts.node_break_map --kinds {kind}` (POM 10.3.0, fit-grow on, Inter "
             "loaded from src/node/fonts). LLM-free. Each cell: the most items that hold with fit-grow, then the "
             "codes of the first break (in brackets). `· raw N` when POM alone (no fit-grow) holds a different "
             "count. **≥N** = holds over the whole sweep. – = the smallest count already breaks.", "",
             "Codes: W word broken · T text overflows its box · O labels overlap · S shrunk below "
             "min(14 px, the node's default) · F scale floor (< 50 %, drawn past its box) · P spills out of its "
             "box onto a neighbour · X off the slide · G fit-grow WORD_TOO_WIDE · C compile error.", ""]
    table = series_table(fit)
    raw_table = series_table(raw)
    lines += ["| placement | direction | style | variant | box (fit, at the smallest count) | "
              + " | ".join(LABEL_NAMES[x] for x in labs) + " |",
              "|---|---|---|---|---|" + "---|" * len(labs)]
    for key in sorted(table, key=lambda k: (PLACEMENTS.index(k[0]), k[1], k[2], k[3])):
        by_lab = table[key]
        first = min((r for rs in by_lab.values() for r in rs), key=lambda r: r["count"])
        box = "×".join(map(str, first["box"])) if first.get("box") else "?"
        cells = [_cell(by_lab[x], raw_table[key][x]) if x in by_lab else "" for x in labs]
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3] or '-'} | {box} | " + " | ".join(cells) + " |")
    # fit-grow's effect
    pairs = {(r["id"]): r for r in raw}
    rescued = [r for r in fit if not breaks(r) and breaks(pairs[r["id"]])]
    regressed = [r for r in fit if breaks(r) and not breaks(pairs[r["id"]])]
    both = [r for r in fit if breaks(r) and breaks(pairs[r["id"]])]
    code_counts = defaultdict(int)
    for r in fit:
        for cd in r["codes"]:
            code_counts[cd] += 1
    lines += ["", "## fit-grow", "",
              f"{len(fit)} cases. Holds with fit-grow: {sum(not breaks(r) for r in fit)}; raw: "
              f"{sum(not breaks(r) for r in raw)}. **Rescued** (raw breaks, fit holds): {len(rescued)}. "
              f"**Made worse** (raw holds, fit breaks): {len(regressed)}. Breaks either way: {len(both)}.", "",
              "Failure codes with fit-grow (a case can have several): "
              + ", ".join(f"{k} {code_counts[k]}" for k in CODE_ORDER if code_counts[k]) + "."]
    if regressed:
        lines += ["", "Made worse by fit-grow (first 12):", ""]
        for r in regressed[:12]:
            lines.append(f"- `{r['id']}`: {', '.join(r['codes'])} — {'; '.join(r['detail'])}; fit-grow: "
                         f"{'; '.join(r.get('fit_grow') or [])}")
    # sample of each code's first break, to show what breaks
    lines += ["", "## What breaks first (one example per code)", ""]
    seen = set()
    for r in sorted(fit, key=lambda r: (r["count"], r["id"])):
        for cd in r["codes"]:
            if cd in seen:
                continue
            seen.add(cd)
            lines.append(f"- **{cd}** `{r['id']}` box {r.get('box')}: {'; '.join(r['detail']) or '-'}")
    return "\n".join(lines) + "\n"


# ── the regression slice (tests/unit/test_node_break_map.py) ──────────────────────

POINTS = ROOT / "tests" / "fixtures" / "node_break_map" / "break_points.yaml"

# (kind, placement, direction, labels, style, variant): the series the unit test pins. The band series at the
# capacity's label length are what capacity.yaml states; the others pin facts the prompts teach (a horizontal
# row in the narrow column, a timeline title of one long word, the pyramid's top band, matrix labels).
TEST_SLICE = [
    ("flow", "band", "horizontal", "w2", "default", "process"),
    ("flow", "band", "vertical", "w2", "default", "process"),
    ("process_arrow", "band", "horizontal", "w2", "default", ""),
    ("process_arrow", "band", "horizontal", "w2", "inter", ""),
    ("process_arrow", "band", "vertical", "w2", "default", ""),
    ("process_arrow", "split-40", "horizontal", "w2", "default", ""),
    ("process_arrow", "split-40", "vertical", "w2", "default", ""),
    ("timeline", "band", "horizontal", "w3", "default", ""),
    ("timeline", "band", "vertical", "w3", "default", ""),
    ("timeline", "band", "horizontal", "long1", "default", ""),
    ("tree", "band", "vertical", "w2", "default", "depth2"),
    ("matrix", "band", "-", "w2", "default", "d0.18"),
    ("pyramid", "band", "up", "w2", "default", ""),
]
# capacity.yaml max_items per direction is checked against the band series at this label length
CAPACITY_LABELS = {"flow": "w2", "process_arrow": "w2", "timeline": "w3"}


def series_points(rows: list[dict]) -> list[dict]:
    """The measured break point (fit-grow on) of every TEST_SLICE series, from a full run's rows."""
    out = []
    for kind, place, direction, labels, style, variant in TEST_SLICE:
        rs = [r for r in rows if r["mode"] == "fit" and (r["kind"], r["placement"], r["direction"], r["labels"],
                                                          r["style"], r["variant"]) == (kind, place, direction, labels,
                                                                                       style, variant)]
        if not rs:
            continue
        n, first = holds_up_to(rs)
        out.append({"kind": kind, "placement": place, "direction": direction, "labels": labels, "style": style,
                    "variant": variant, "holds_up_to": n, "swept": [min(r["count"] for r in rs), max(r["count"] for r in rs)],
                    "first_break": breaks(first) if first else None})
    return out


def slice_cases(point: dict) -> list[Case]:
    """The cases that pin one break point: the count it holds at and the one after (when swept)."""
    n, (lo, hi) = point["holds_up_to"], point["swept"]
    counts = [lo] if n is None else [n] + ([n + 1] if n < hi else [])
    return [Case(point["kind"], point["placement"], point["direction"], point["labels"], k, point["style"],
                 point["variant"]) for k in counts]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kinds", nargs="*", default=list(KINDS), choices=KINDS)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--quick", action="store_true", help="a slice of the grid (edges only)")
    ap.add_argument("--no-docs", action="store_true", help="write output/ only")
    ap.add_argument("--write-points", action="store_true",
                    help="write the regression slice's break points (tests/fixtures/node_break_map) from output/")
    a = ap.parse_args()
    if a.write_points:
        import yaml
        rows = [r for k in KINDS if (OUT / f"{k}.json").exists()
                for r in json.loads((OUT / f"{k}.json").read_text(encoding="utf-8"))]
        old = yaml.safe_load(POINTS.read_text(encoding="utf-8")) if POINTS.exists() else {}
        POINTS.parent.mkdir(parents=True, exist_ok=True)
        head = ("# Measured break points of the node break map's regression slice (scripts/node_break_map.py\n"
                "# TEST_SLICE), fit-grow on, POM 10.3.0. Written by `python -m scripts.node_break_map --write-points`\n"
                "# after a full run; tests/unit/test_node_break_map.py compiles each at holds_up_to and the count\n"
                "# after it. capacity_disagreements: capacity.yaml limits above the measured band point, kept\n"
                "# until the user decides (each with the reason); the test fails on any other.\n")
        body = {"series": series_points(rows), "capacity_disagreements": old.get("capacity_disagreements") or {}}
        POINTS.write_text(head + yaml.safe_dump(body, sort_keys=False, width=120), encoding="utf-8")
        print(f"wrote {POINTS}")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    for kind in a.kinds:
        t0 = time.time()
        cases = grid([kind], a.quick)
        work = OUT / "work" / kind
        built = compile_cases(cases, work, jobs=a.jobs)
        rows = evaluate(cases, built, work)
        (OUT / f"{kind}.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
        if not a.no_docs:
            (DOCS / f"{kind}.md").write_text(write_doc(kind, rows, {c.id: c for c in cases}), encoding="utf-8")
        print(f"{kind}: {len(cases)} cases x 2 in {time.time() - t0:.0f}s, "
              f"holding with fit-grow {sum(1 for r in rows if r['mode'] == 'fit' and not breaks(r))}")


if __name__ == "__main__":
    main()
