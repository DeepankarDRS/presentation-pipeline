"""Node break map for Table, KpiGrid / Kpi and CardGrid / Card (2026-10-21), LLM-free.

    python -m scripts.node_break_map --kinds table kpi cards

The diagram map (scripts/node_break_map.py) extended to the nodes a slide is mostly made of. Each case is
written the way the pipeline writes it, then goes the pipeline's own way:

  table   the <Table> the generator writes (knowledge/components/table.yaml `structure`: header row on
          $surfaceAlt, body cells on $surface, numeric columns right-aligned, defaultRowHeight 56, no cell
          fontSize) -> normalize_xml -> theme -> deck font
  kpi     a <KpiGrid ref> tag + a kpi_row plan -> tiles.fill (expand + element_refs.fill_refs: unit spans,
          kpiv- / kpig- ids) -> normalize_xml -> theme -> deck font       (POM_BLOCKS=tiles route)
  cards   a <CardGrid ref> tag + a card_grid plan -> tiles.fill (cards.expand writes the text) -> the same

then compiles raw and with fit-grow (src/node/break-map.js). The placements are the diagram map's where they
make sense (a KPI row is not drawn under a KPI row: `band-over-chart` puts the tiles above a chart instead).

Scored on what is drawn, with the diagram map's codes, but every text is measured **run by run**
(break-map.js `runs`): a KPI value "₹114.9" + a smaller "L" span is one word of two sizes, measured each at
its own size, and lines wrap greedily at the box width less the insets the pptx writes (0 in POM's text boxes
and table cells). Tables are read from the graphicFrame: a row is drawn at least as tall as its tallest cell's
lines, so rows the cell text needs grow the table — past its box that is SPILL, past the slide OFF_SLIDE.

The series axes are stored in the diagram map's Case fields (the column axis of a map is always `labels`):
  table   direction = columns ("c4"), style = header length, labels = cell text, count = body rows
  kpi     direction = arrangement (auto: a bare tag; pinned: layout="grid" cols=n, one row as written),
          style = label length, labels = value length, count = tiles
  cards   direction = card_layout (grid | steps), style = title length, labels = body length, count = cards
"""

from __future__ import annotations

import itertools
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from scripts import node_break_map as bm
from src.compiler.node_facts import Box, drawn_shapes

BLOCK_KINDS = ("table", "kpi", "cards")
PLACEMENTS = {"table": ("band", "band-under-kpi", "split-60", "split-40", "card"),
              "kpi": ("band", "band-over-chart", "split-60", "split-40", "card"),
              "cards": ("band", "band-under-kpi", "split-60", "split-40")}
PLACE_ORDER = ("band", "band-under-kpi", "band-over-chart", "split-60", "split-40", "card")
PALETTE = "corporate-slate"
_EMU = 9525
_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
       "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
_A = "{%s}" % _NS["a"]

# ── content sets (distinct strings: a case never draws the same text twice) ─────

TABLE_LABELS = ["North region", "South region", "East region", "West region", "Online store", "Retail partners",
                "Key accounts", "New markets", "Field sales", "Inside sales", "Channel deals", "Direct web",
                "Mobile app", "Call centre"]
TABLE_NUMBERS = ["$24.9M", "58%", "+4.2 pts", "1,284", "0.34x", "₹114.9L", "-1.4 pts", "$980K", "12.5%", "3.1x"]
TABLE_WORDS = ["High", "Low", "Done", "Open", "Late", "Green", "Amber", "Red", "Owned", "Shared", "Paused", "Live",
               "Ready", "Held"]
TABLE_SENTENCES = ["Renew the contract early", "Price above two rivals", "Owner leaves in March",
                   "Data lands ten days late", "Pilot in three stores first", "Needs a second supplier now",
                   "Volume falls after each promotion", "Fill rate held above target", "Margin slipped on freight costs",
                   "Hire two regional leads", "Launch before the board review", "Audit every vendor invoice"]
TABLE_HEADERS = {"short": ["Segment", "Revenue", "Share", "Growth", "Margin", "Orders", "Returns", "Rating", "Stock",
                           "Owner"],
                 "long": ["Business segment", "Quarterly revenue", "Market share change", "Profitability",
                          "Gross margin trend", "Orders per week", "Return rate", "Customer rating", "Inventory days",
                          "Accountable owner"]}
TABLE_CELLS = {"num": "label + numbers", "w1": "1 short word", "long1": "1 long word", "w36": "3–6 words"}

KPI_VALUES = {"short": ["$4.2M", "18%", "212", "3.1x", "$980K", "42%", "7.5", "$12M"],
              "mid": ["₹114.9L", "₹37.4L", "₹38.6", "0.34x", "₹85.5L", "6.0%", "₹29.4L", "0.32x"],
              "long": ["₹114.9 Cr", "₹37.4 Cr", "₹85.5 Cr", "₹29.4 Cr", "₹10.1 Cr", "₹27.3 Cr", "₹46.2 Cr", "₹31.1 Cr"],
              "word": ["14 months", "3 weeks", "19 months", "2.4 days", "6 weeks", "11 months", "9 days", "4 quarters"]}
KPI_VALUE_NAMES = {"short": "$4.2M (short)", "mid": "₹114.9L (unit span)", "long": "₹114.9 Cr (spaced unit)",
                   "word": "14 months (word unit)"}
KPI_LABELS = {"w1": ["Revenue", "Margin", "Stores", "Payback", "Spend", "Share", "Orders", "Churn"],
              "w3": ["Combined quarterly revenue", "Gross margin after freight", "Stores open this year",
                     "Customer acquisition payback", "Total media spend", "Share of category search",
                     "Orders per active user", "Monthly subscriber churn"],
              "long1": ["Profitability", "Reconciliation", "Implementation", "Infrastructure", "Accountability",
                        "Optimization", "Procurement", "Transformation"]}
KPI_NOTES = ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months", "+6% YoY", "flat", "+12 stores", "-0.3 pts"]

CARD_TITLES = {"w1": ["Visibility", "Pricing", "Assortment", "Supply", "Retention", "Search", "Promotions", "Data",
                      "Service", "Delivery", "Loyalty", "Partners"],
               "w3": ["Close enterprise logos", "Fix self-serve onboarding", "Ship analytics v2", "Reset paid search",
                      "Protect repeat buyers", "Close the price gap", "Speed up reporting", "Open pilot stores",
                      "Renew key contracts", "Hire regional leads", "Cut freight costs", "Launch loyalty tiers"],
               "long1": ["Profitability", "Reconciliation", "Implementation", "Infrastructure", "Accountability",
                         "Optimization", "Procurement", "Transformation", "Benchmarking", "Consolidation",
                         "Sustainability", "Digitalization"]}
CARD_BODIES = {"none": None,
               "short": ["Worth $4M+ combined ARR", "Payback slipped to 19 months", "Before the January board",
                         "Organic share fell this quarter", "Repeat buyers drive 41% of revenue",
                         "Regular price sits above rivals", "Reports land ten days late", "Three cities in the pilot",
                         "Two suppliers renew in March", "North and South first", "Freight is 9% of sales",
                         "Gold tier for top buyers"],
               "long": ["Organic search share dropped on every platform this quarter while paid share held, so the "
                        "brand pays more for the same traffic.",
                        "Repeat buyers are 41% of revenue and their basket grew; this is the base to protect while "
                        "acquisition is reset.",
                        "Discount weeks lift volume but the regular price sits above two rivals, and volume falls back "
                        "as soon as a promotion ends.",
                        "Platform reports land ten days after month end, so every decision uses old numbers and the "
                        "team cannot react within a month.",
                        "Three enterprise logos are in late stage and worth more than four million in combined annual "
                        "recurring revenue.",
                        "Self-serve sign-ups stall at the second step, and the payback on paid acquisition has slipped "
                        "to nineteen months.",
                        "The analytics release has to ship before the January board meeting, with the new cohort views "
                        "the sales team asked for.",
                        "Freight rose to nine percent of sales after the carrier change, and the margin gain from price "
                        "moves went with it.",
                        "Two of the three main suppliers renew in March; both asked for longer terms and higher minimum "
                        "order volumes.",
                        "The pilot runs in three cities for twelve weeks, with a control store in each to read the lift "
                        "cleanly.",
                        "Regional leads in the North and South start first; the East and West follow once the playbook "
                        "is written down.",
                        "Gold tier members get free delivery and early access, paid for by the cut in discount weeks "
                        "across the year."]}
CARD_BODY_NAMES = {"none": "title only", "short": "short body (~5 words)", "long": "long body (~22 words)"}

COUNTS = {"table": range(2, 15), "kpi": range(2, 9), "cards": range(2, 13)}
TABLE_COLS = (2, 3, 4, 5, 6, 8, 10)


def grid(kind: str, quick: bool = False) -> list[bm.Case]:
    out = []
    places = PLACEMENTS[kind] if not quick else ("band", "split-40")
    ns = list(COUNTS[kind])[::2] if quick else list(COUNTS[kind])
    if kind == "table":
        axes = itertools.product(places, [f"c{n}" for n in (TABLE_COLS[::3] if quick else TABLE_COLS)],
                                 ("short", "long"), TABLE_CELLS, [""])
    elif kind == "kpi":
        axes = itertools.product(places, ("auto", "pinned"), KPI_LABELS, KPI_VALUES, [""])
    else:
        axes = itertools.product(places, ("grid", "steps"), CARD_TITLES, CARD_BODIES, [""])
    for (p, d, st, lab, v), n in itertools.product(axes, ns):
        out.append(bm.Case(kind, p, d, lab, n, st, v))
    return out


# ── the slide, written as the pipeline writes it ───────────────────────────────

_x = bm._esc
_HEAD = ('<Text id="bm-head" fontSize="36" bold="true" fontFamily="Inter" color="$textMain">'
         'A headline that states the point</Text>')
SIDE_TEXTS = ("What the slide shows, in one or two plain sentences for the reader.",
              "A second point the slide makes beside it.")
_SIDE = ('<VStack id="bm-side" w="max" gap="12" alignItems="stretch">'
         + "".join(f'<Text fontSize="18" color="$textMuted">{t}</Text>' for t in SIDE_TEXTS) + "</VStack>")
_KPI_ROW = ('<HStack id="bm-kpi" gap="24" h="150" alignItems="stretch">' + "".join(
    '<VStack w="max" padding="16" gap="4" backgroundColor="$surfaceAlt" alignItems="stretch">'
    f'<Text fontSize="40" bold="true">{v}</Text><Text fontSize="14" color="$textMuted">{k}</Text></VStack>'
    for v, k in (("$7.9M", "Bookings"), ("31%", "Win rate"), ("118", "Deals"))) + "</HStack>")
_CHART = ('<Chart id="bm-fill" chartType="bar" h="max" chartColors=\'["2563EB"]\'><ChartSeries name="Revenue">'
          + "".join(f'<ChartDataPoint label="{q}" value="{v}"/>' for q, v in (("Q1", 3), ("Q2", 4), ("Q3", 5), ("Q4", 6)))
          + "</ChartSeries></Chart>")
FIXED_TEXTS = {"A headline that states the point", *SIDE_TEXTS, "$7.9M", "Bookings", "31%", "Win rate", "118", "Deals",
               "The numbers", "Context", "Risks", "Next step", "Notes."}


def _card(title: str, inner: str, cid: str = "") -> str:
    ident = f' id="{cid}"' if cid else ""
    return (f'<VStack{ident} w="max" padding="24" gap="12" '
            f'backgroundColor="$surfaceAlt" alignItems="stretch"><Text fontSize="20" bold="true">{title}</Text>'
            f"{inner}</VStack>")


def table_xml(c: bm.Case) -> str:
    cols, rows = int(c.direction[1:]), c.count
    heads = TABLE_HEADERS[c.style][:cols]
    if c.labels == "num":
        body = [[TABLE_LABELS[r]] + [TABLE_NUMBERS[(r * 3 + k) % len(TABLE_NUMBERS)] for k in range(1, cols)]
                for r in range(rows)]
    else:
        pool = {"w1": TABLE_WORDS, "long1": bm.LABELS["long1"], "w36": TABLE_SENTENCES}[c.labels]
        body = [[TABLE_LABELS[r]] + [pool[(r * 5 + k) % len(pool)] for k in range(1, cols)] for r in range(rows)]
    right = [c.labels == "num" and k > 0 for k in range(cols)]

    def td(v: str, k: int, head: bool) -> str:
        style = ' bold="true" backgroundColor="$surfaceAlt" color="$textMain"' if head else \
            f' backgroundColor="$surface" color="{"$textMuted" if k == 0 else "$textMain"}"'
        align = ' textAlign="right"' if right[k] else ""
        return f"<Td{style}{align}>{_x(v)}</Td>"

    for r in body:
        for v in r:
            c.roles[v] = "cell"
    for h in heads:
        c.roles[h] = "header"
    c.defaults = {"cell": 14, "header": 14}
    return ('<Table defaultRowHeight="56" cellBorder.color="$border" cellBorder.width="1">' + "<Col />" * cols
            + "<Tr>" + "".join(td(h, k, True) for k, h in enumerate(heads)) + "</Tr>"
            + "".join("<Tr>" + "".join(td(v, k, False) for k, v in enumerate(r)) + "</Tr>" for r in body) + "</Table>")


def kpi_plan(c: bm.Case) -> dict:
    n = c.count
    labels, values, notes = KPI_LABELS[c.style][:n], KPI_VALUES[c.labels][:n], KPI_NOTES[:n]
    for t in labels:
        c.roles[t] = "label"
    for t in values:
        c.roles[t] = "value"
    for t in notes:
        c.roles[t] = "note"
    c.defaults = {"label": 16, "value": 28, "note": 16}
    return {"component_id": "kpis", "kind": "kpi_row", "weight": "hero",
            "content_data": {"kpi_labels": labels, "kpi_values": values, "kpi_deltas": notes, "kpi_tones": [""] * n}}


def cards_plan(c: bm.Case) -> dict:
    n = c.count
    bodies = CARD_BODIES[c.labels]
    cs = []
    for i in range(n):
        card = {"title": CARD_TITLES[c.style][i]}
        c.roles[card["title"]] = "title"
        if bodies:
            card["body"] = bodies[i]
            c.roles[bodies[i]] = "body"
        cs.append(card)
    c.defaults = {"title": 20, "body": 16, "other": 13}
    return {"component_id": "cards", "kind": "card_grid", "weight": "hero",
            "content_data": {"card_layout": c.direction, "cards": cs}}


def node_tag(c: bm.Case) -> tuple[str, list[dict]]:
    """The node as the generator writes it, and the plan components it refers to."""
    if c.kind == "table":
        return table_xml(c), []
    if c.kind == "kpi":
        pin = f' layout="grid" cols="{c.count}"' if c.direction == "pinned" else ""
        return f'<KpiGrid ref="kpis"{pin}/>', [kpi_plan(c)]
    return '<CardGrid ref="cards"/>', [cards_plan(c)]


def slide_tags(c: bm.Case) -> tuple[str, list[dict]]:
    node, comps = node_tag(c)
    p = c.placement
    col = '<VStack id="bm-node" w="{}" gap="12" alignItems="stretch">' + node + "</VStack>"
    if p == "band":
        body = node
    elif p == "band-under-kpi":
        body = _KPI_ROW + node
    elif p == "band-over-chart":
        body = node + _CHART
    elif p == "split-60":
        body = f'<HStack gap="24" h="max" alignItems="stretch">{col.format("62%")}{_SIDE}</HStack>'
    elif p == "split-40":
        body = f'<HStack gap="24" h="max" alignItems="stretch">{_SIDE}{col.format("38%")}</HStack>'
    elif p == "card":
        row = '<HStack gap="24" h="max" alignItems="stretch">{}</HStack>'
        note = '<Text fontSize="18">Notes.</Text>'
        body = (row.format(_card("The numbers", node, "bm-node") + _card("Context", note))
                + row.format(_card("Risks", note) + _card("Next step", note)))
    else:
        raise ValueError(p)
    xml = ('<Slide><VStack w="1280" h="720" padding="56" gap="24" alignItems="stretch" backgroundColor="$surface">'
           f"{_HEAD}{body}</VStack></Slide>")
    return xml, comps


def slide_xml(c: bm.Case) -> str:
    """The slide after the validator's steps: tiles.fill (cards + KPI tiles + element refs) -> normalize_xml ->
    the palette's <Theme> -> the deck font (compile_xml)."""
    from src.compiler.compiler_client import deck_font
    from src.compiler.nodes import tiles
    from src.compiler.normalizer import ensure_single_theme, normalize_xml
    xml, comps = slide_tags(c)
    if comps:
        res = tiles.fill(xml, {"components": comps})
        errs = [i for i in res["issues"] if i["severity"] == "error"]
        if errs:
            raise ValueError(f"{c.id}: {errs}")
        xml = res["xml"]
    xml = ensure_single_theme(normalize_xml(xml)["cleaned_xml"], _theme())
    return deck_font(xml)


_THEME: list[str] = []


def _theme() -> str:
    if not _THEME:
        from src.agents.style_resolver import resolve_theme
        _THEME.append(resolve_theme(PALETTE)["element"])
    return _THEME[0]


# ── what is drawn: text boxes as runs, tables as cells ─────────────────────────

def _paras(tx: ET.Element | None) -> list[dict]:
    out = []
    for p in (tx.findall("a:p", _NS) if tx is not None else []):
        ppr = p.find("a:pPr", _NS)

        def pts(tag: str) -> float:
            el = ppr.find(f"a:{tag}/a:spcPts", _NS) if ppr is not None else None
            return int(el.get("val")) / 100 / 0.75 if el is not None else 0.0

        runs = []
        for r in p.findall("a:r", _NS):
            rpr = r.find("a:rPr", _NS)
            latin = rpr.find("a:latin", _NS) if rpr is not None else None
            sz = rpr.get("sz") if rpr is not None else None
            runs.append({"text": r.findtext("a:t", "", _NS), "px": round(int(sz) / 100 / 0.75, 2) if sz else 18,
                         "bold": rpr is not None and rpr.get("b") in ("1", "true"),
                         "family": latin.get("typeface", "") if latin is not None else "",
                         "spc": int(rpr.get("spc")) / 100 / 0.75 if rpr is not None and rpr.get("spc") else 0})
        if runs and "".join(r["text"] for r in runs).strip():
            out.append({"runs": runs, "lnSpc": pts("lnSpc"), "before": pts("spcBef"), "after": pts("spcAft")})
    return out


def drawn_texts(pptx: str | Path) -> list[tuple[Box, list[dict]]]:
    """drawn_shapes with every shape's paragraphs of runs (same order: the shapes with an offset and extent)."""
    with zipfile.ZipFile(pptx) as z:
        root = ET.fromstring(z.read("ppt/slides/slide1.xml"))
    paras = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] not in ("sp", "cxnSp"):
            continue
        if el.find(".//a:off", _NS) is None or el.find(".//a:ext", _NS) is None:
            continue
        paras.append(_paras(next((c for c in el if c.tag.endswith("}txBody")), None)))
    return list(zip(drawn_shapes(pptx), paras))


def drawn_tables(pptx: str | Path) -> list[dict]:
    """Every table: its frame box, column widths, declared row heights and cells (insets, anchor, paragraphs)."""
    with zipfile.ZipFile(pptx) as z:
        root = ET.fromstring(z.read("ppt/slides/slide1.xml"))
    out = []
    for gf in root.iter("{%s}graphicFrame" % _NS["p"]):
        tbl = gf.find(".//a:tbl", _NS)
        if tbl is None:
            continue
        off, ext = gf.find(".//a:off", _NS), gf.find(".//a:ext", _NS)
        cols = [int(g.get("w")) / _EMU for g in tbl.findall("a:tblGrid/a:gridCol", _NS)]
        rows = []
        for tr in tbl.findall("a:tr", _NS):
            cells, k = [], 0
            for tc in tr.findall("a:tc", _NS):
                span = int(tc.get("gridSpan", "1"))
                if tc.get("hMerge") or tc.get("vMerge"):
                    k += 1
                    continue
                pr = tc.find("a:tcPr", _NS)
                mar = {m: int(pr.get(m, d)) / _EMU if pr is not None else d / _EMU
                       for m, d in (("marL", 91440), ("marR", 91440), ("marT", 45720), ("marB", 45720))}
                cells.append({"col": k, "w": sum(cols[k:k + span]), **mar,
                              "paras": _paras(tc.find("a:txBody", _NS))})
                k += span
            rows.append({"h": int(tr.get("h")) / _EMU, "cells": cells})
        out.append({"box": Box(int(off.get("x")) / _EMU, int(off.get("y")) / _EMU,
                               int(ext.get("cx")) / _EMU, int(ext.get("cy")) / _EMU), "cols": cols, "rows": rows})
    return out


def measure_runs(reqs: list[dict], workdir: Path) -> list[dict]:
    src, dst = workdir / "runs.json", workdir / "runs-measured.json"
    src.write_text(json.dumps(reqs), encoding="utf-8")
    bm._node(["runs", str(src), str(dst)])
    return json.loads(dst.read_text(encoding="utf-8"))


# ── scoring ───────────────────────────────────────────────────────────────────

def _geo_id(geo: dict | None, ident: str) -> dict | None:
    stack = [geo] if geo else []
    while stack:
        n = stack.pop()
        if n.get("id") == ident:
            return n
        stack.extend(n.get("children", []))
    return None


def _gbox(n: dict) -> Box:
    return Box(n["x"], n["y"], n["w"], n["h"])


def region(c: bm.Case, geo: dict) -> Box:
    """The box the node was given: its column / card, or the band between the fixed parts above and below it."""
    head = _geo_id(geo, "bm-head")
    band_top, bottom = head["y"] + head["h"] + 24, bm.SLIDE_H - 56
    if c.placement in ("split-60", "split-40", "card"):
        # the column / card, within the band (a column grown past the slide does not give its node more room)
        n = _geo_id(geo, "bm-node")
        b = _gbox(n)
        top = max(b.y, band_top)
        if c.placement == "card":   # under the card's title, inside its padding
            title = next(k for k in n["children"] if k["type"] == "text")
            top = title["y"] + title["h"] + 12
            return Box(b.x + 24, top, b.w - 48, min(b.b - 24, bottom) - top)
        return Box(b.x, top, b.w, min(b.b, bottom) - top)
    y = band_top
    if c.placement == "band-under-kpi":
        kpi = _geo_id(geo, "bm-kpi")
        y = kpi["y"] + kpi["h"] + 24
    if c.placement == "band-over-chart":
        bottom = _geo_id(geo, "bm-fill")["y"] - 24
    return Box(56, y, bm.SLIDE_W - 112, bottom - y)


def _text_of(paras: list[dict]) -> str:
    return re.sub(r"\s+", " ", " ".join("".join(r["text"] for r in p["runs"]) for p in paras)).strip()


def evaluate(cases: list[bm.Case], built: dict[str, dict], workdir: Path) -> list[dict]:
    rows, pending = [], []   # pending: (row, what, request, context)
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
            reg = region(c, r["geometry"])
            row["box"] = [round(reg.w), round(reg.h)]
            texts = drawn_texts(r["pptx"])
            shapes = [s for s, _ in texts]
            if any(s.x < -1 or s.y < -1 or s.r > bm.SLIDE_W + 1 or s.b > bm.SLIDE_H + 1 for s in shapes):
                row["codes"].append("OFF_SLIDE")
            others = [s for s, _ in texts if s.text and s.text in FIXED_TEXTS]
            fixed_geo = [_gbox(n) for n in (_geo_id(r["geometry"], i) for i in ("bm-head", "bm-kpi", "bm-fill", "bm-side"))
                         if n]
            ctx = {"c": c, "reg": reg, "others": others, "fixed": fixed_geo, "extents": [], "px": [], "need": defaultdict(float)}
            row["_ctx"] = ctx
            if c.kind == "table":
                for t in drawn_tables(r["pptx"]):
                    ctx["table"] = t
                    for ri, tr in enumerate(t["rows"]):
                        for cell in tr["cells"]:
                            if not cell["paras"]:
                                continue
                            w = cell["w"] - cell["marL"] - cell["marR"]
                            pending.append((row, ("cell", ri, cell, w), {"paras": cell["paras"], "width": max(w, 1)}))
                continue
            fills = [s for s in shapes if not s.text and s.w > 1 and s.h > 1 and s.geom != "line"]
            # the node's own fills (tiles, cards): not the card / column it sits in
            ctx["fills"] = [f for f in fills if bm._inside(Box(f.cx, f.cy, 0, 0), reg, 2) and not bm._inside(reg, f, 2)]
            for s, paras in texts:
                if not s.text or s.text in FIXED_TEXTS or not paras or not bm._inside(Box(s.cx, s.cy, 0, 0), reg, 4):
                    continue
                area = Box(s.x + s.pad / 2, s.y + s.vpad / 2, s.w - s.pad, s.h - s.vpad)
                pending.append((row, ("text", s, area, paras), {"paras": paras, "width": max(area.w, 1)}))
    measured = measure_runs([q for _, _, q in pending], workdir) if pending else []
    for (row, what, _), m in zip(pending, measured):
        ctx = row["_ctx"]
        c = ctx["c"]
        if what[0] == "cell":
            _, ri, cell, w = what
            px = cell["paras"][0]["runs"][0]["px"]
            role = "header" if ri == 0 else "cell"
            if ri > 0:
                ctx["px"].append(px)
            need = m["height"] + cell["marT"] + cell["marB"]
            ctx["need"][ri] = max(ctx["need"][ri], need)
            _word(row, m, w)
            _small(row, c, role, px, _text_of(cell["paras"]))
            continue
        _, s, area, paras = what
        text = _text_of(paras)
        role = c.roles.get(text, "other")
        px = paras[0]["runs"][0]["px"]
        if role in ("value", "body") or (c.kind == "cards" and role == "title" and c.labels == "none"):
            ctx["px"].append(px)
        _word(row, m, area.w)
        _small(row, c, role, px, text)
        ext = bm._extent(s, area, m["lineW"], m["height"])
        ctx["extents"].append(ext)
        holder = bm._container(s, ctx["fills"])
        room = holder if holder is not None and holder is not s else area
        if not bm._inside(ext, room, 1.0) and "TEXT_OVERFLOW" not in row["codes"]:
            row["codes"].append("TEXT_OVERFLOW")
            row["detail"].append(f"{text[:40]!r} {m['lines']} lines, {ext.w:.0f} x {ext.h:.0f} px out of its "
                                 f"{room.w:.0f} x {room.h:.0f} box")
    for row in rows:
        ctx = row.pop("_ctx", None)
        if not ctx:
            continue
        row["min_px"] = min(ctx["px"], default=None)
        reg = ctx["reg"]
        if "table" in ctx:
            t = ctx["table"]
            drawn = [max(tr["h"], ctx.get("need", {}).get(i, 0)) for i, tr in enumerate(t["rows"])]
            grown = sum(drawn) - sum(tr["h"] for tr in t["rows"])
            row["table"] = {"declared": round(sum(tr["h"] for tr in t["rows"])), "drawn": round(sum(drawn)),
                            "width": round(sum(t["cols"]))}
            ext = Box(t["box"].x, t["box"].y, sum(t["cols"]), sum(drawn), "table")
            if ext.b > bm.SLIDE_H + 1 and "OFF_SLIDE" not in row["codes"]:
                row["codes"].append("OFF_SLIDE")
            if not bm._inside(ext, reg, bm.SPILL_TOL):
                row["codes"].append("SPILL")
                row["detail"].append(f"table drawn {ext.w:.0f} x {ext.h:.0f} px (rows +{grown:.0f} px for their text) "
                                     f"in a {reg.w:.0f} x {reg.h:.0f} box")
            continue
        group = ctx["extents"]
        pair = next(((a, b) for a, b in itertools.combinations(group, 2) if bm._overlap(a, b)), None)
        if pair:
            row["codes"].append("OVERLAP")
            row["detail"].append(f"{pair[0].text[:30]!r} / {pair[1].text[:30]!r}")
        spill = [e for e in group + ctx["fills"] if not bm._inside(e, reg, bm.SPILL_TOL)]
        hit = next(((e, o) for e in group for o in ctx["others"] + ctx["fixed"] if bm._overlap(e, o)), None)
        if spill or hit:
            row["codes"].append("SPILL")
            row["detail"].append(f"{hit[0].text[:30]!r} covers {(hit[1].text or 'a fixed part')[:30]!r}" if hit else
                                 f"{(spill[0].text or 'a tile')[:30]!r} past the {reg.w:.0f}x{reg.h:.0f} box")
    return rows


def _word(row: dict, m: dict, room: float) -> None:
    # any deficit breaks: a word 0.3 px wider than its box broke in a LibreOffice render (2026-10-21)
    if m["wordW"] > room and "WORD_BROKEN" not in row["codes"]:
        row["codes"].append("WORD_BROKEN")
        row["detail"].append(f"{m['word']!r} {m['wordW']:.0f} px in {room:.0f}")


def _small(row: dict, c: bm.Case, role: str, px: float, text: str) -> None:
    floor = min(bm.FLOOR_PX, c.defaults.get(role, bm.FLOOR_PX))
    if px < floor - 0.1 and "SHRUNK" not in row["codes"]:
        row["codes"].append("SHRUNK")
        row["detail"].append(f"{text[:30]!r} {px:g} px")


# ── the map ───────────────────────────────────────────────────────────────────

AXES = {  # (series column titles, column axis names)
    "table": (("placement", "columns", "header"), TABLE_CELLS, "body rows"),
    "kpi": (("placement", "arrangement", "label"), KPI_VALUE_NAMES, "tiles"),
    "cards": (("placement", "layout", "title"), CARD_BODY_NAMES, "cards"),
}
SIZE_OF = {"table": "body cell px", "kpi": "smallest value px", "cards": "smallest body px (title px when title only)"}


def _cell(fit: list[dict], raw: list[dict]) -> str:
    n_fit, br_fit = bm.holds_up_to(fit)
    n_raw, _ = bm.holds_up_to(raw)
    top = max(r["count"] for r in fit)
    if br_fit is None:
        s = f"**≥{top}**"
    else:
        s = f"{n_fit if n_fit is not None else '–'} ({''.join(bm.SHORT[k] for k in bm.CODE_ORDER if k in br_fit['codes'])})"
    at = next((r for r in fit if r["count"] == n_fit), None) if n_fit is not None else None
    if at and at.get("min_px"):
        s += f" {at['min_px']:.0f}px"
    if n_raw != n_fit:
        s += f" · raw {n_raw if n_raw is not None else '–'}"
    return s


def write_doc(kind: str, rows: list[dict]) -> str:
    heads, cols, unit = AXES[kind]
    fit = [r for r in rows if r["mode"] == "fit"]
    raw = [r for r in rows if r["mode"] == "raw"]
    labs = [x for x in cols if any(r["labels"] == x for r in fit)]
    lines = [f"# Break map: {kind}", "",
             f"Generated by `python -m scripts.node_break_map --kinds {kind}` (POM 10.3.0, fit-grow on, palette "
             f"{PALETTE}, deck font Inter from src/node/fonts; the pipeline's own expansion, see "
             "scripts/node_break_map_blocks.py). LLM-free. Each cell: the most "
             f"{unit} that hold with fit-grow, the codes of the first break (in brackets), then the {SIZE_OF[kind]} "
             f"at the count that holds. `· raw N` when POM alone (no fit-grow) holds a different count. **≥N** = holds "
             "over the whole sweep. – = the smallest count already breaks. Words are measured run by run.", "",
             "Codes: W word broken · T text overflows its box · O texts overlap · S shrunk below min(14 px, the "
             "node's default) · F scale floor · P spills out of its box (a table: rows grown for their text past "
             "it) · X off the slide · G fit-grow WORD_TOO_WIDE · C compile error.", ""]
    table = bm.series_table(fit)
    raw_table = bm.series_table(raw)
    lines += [f"| {' | '.join(heads)} | box (fit, smallest count) | " + " | ".join(cols[x] for x in labs) + " |",
              "|---|---|---|---|" + "---|" * len(labs)]

    def order(k):
        d = int(k[1][1:]) if kind == "table" else k[1]
        return (PLACE_ORDER.index(k[0]), d, k[2])

    for key in sorted(table, key=order):
        by_lab = table[key]
        first = min((r for rs in by_lab.values() for r in rs), key=lambda r: r["count"])
        box = "×".join(map(str, first["box"])) if first.get("box") else "?"
        cells = [_cell(by_lab[x], raw_table[key][x]) if x in by_lab else "" for x in labs]
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {box} | " + " | ".join(cells) + " |")
    pairs = {r["id"]: r for r in raw}
    rescued = [r for r in fit if not bm.breaks(r) and r["id"] in pairs and bm.breaks(pairs[r["id"]])]
    regressed = [r for r in fit if bm.breaks(r) and r["id"] in pairs and not bm.breaks(pairs[r["id"]])]
    both = [r for r in fit if bm.breaks(r) and r["id"] in pairs and bm.breaks(pairs[r["id"]])]
    code_counts = defaultdict(int)
    for r in fit:
        for k in r["codes"]:
            code_counts[k] += 1
    lines += ["", "## fit-grow", "",
              f"{len(fit)} cases. Holds with fit-grow: {sum(not bm.breaks(r) for r in fit)}; raw: "
              f"{sum(not bm.breaks(r) for r in raw)}. **Rescued** (raw breaks, fit holds): {len(rescued)}. "
              f"**Made worse** (raw holds, fit breaks): {len(regressed)}. Breaks either way: {len(both)}.", "",
              "Failure codes with fit-grow (a case can have several): "
              + ", ".join(f"{k} {code_counts[k]}" for k in bm.CODE_ORDER if code_counts[k]) + "."]
    if regressed:
        lines += ["", "Made worse by fit-grow (first 12):", ""]
        for r in regressed[:12]:
            lines.append(f"- `{r['id']}`: {', '.join(r['codes'])} — {'; '.join(r['detail'])}; fit-grow: "
                         f"{'; '.join(r.get('fit_grow') or [])}")
    lines += ["", "## What breaks first (one example per code)", ""]
    seen = set()
    for r in sorted(fit, key=lambda r: (r["count"], r["id"])):
        for k in r["codes"]:
            if k not in seen:
                seen.add(k)
                lines.append(f"- **{k}** `{r['id']}` box {r.get('box')}: {'; '.join(r['detail']) or '-'}")
    return "\n".join(lines) + "\n"
