"""Composition gallery for the blocks left after KPI tiles and cards, LLM-free (composition spec §11.3 R1).

    python -m scripts.composition_gallery_left                    # every block, corporate-slate + graphite-dark
    python -m scripts.composition_gallery_left --only table chart

One sample component per block, in today's typed planner schema (content_from_data validates it). The samples copy
the shape of saved slide_component_planner output (item counts, text lengths, "Head: detail" strings, hints that
name one item), with synthetic or anonymised words. Each composition is hand-written as the XML its node would expand
to, using only the shared words of the spec (§2.3), in its theme-default look ($tokens and the plan's tone / emphasis
roles, no LLM attributes). The same XML is drawn on both palettes. Repeated items carry the card ids
card-<cid>-<i>, so fit-grow grows peers to one size across rows. The first row of each sheet is today's style names
for that block (scripts/left_blocks_gallery.py), on corporate-slate. Writes <out>/<block>.png and every slide's folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_NODES"] = "chart,timeline,process_arrow,flow,table"   # the composition nodes the bare tags need

from scripts import composition_test as CT  # noqa: E402
from scripts import left_blocks_gallery as LB  # noqa: E402
from scripts import tile_gallery as TG  # noqa: E402  (sets POM_BLOCKS=tiles: CardGrid expands)
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import native  # noqa: E402

OUT = ROOT / "output" / "composition-left"
DOCS = ROOT / "docs" / "eval" / "composition-left"
PALETTES = ("corporate-slate", "graphite-dark")
X, comp, t, split = LB.X, LB.comp, CT.t, LB.split

# ── sample components (shapes of saved planner output; words synthetic / anonymised) ─────────────────────────────

# a 4 x 4 comparison table; first column "Gap N - name"; the hint singles out the Fix column (saved: 18 tables 4 x 3-5)
TABLE = comp("gaps", "table", {"table_columns": ["Gap", "Marketplace A", "Marketplace B", "Fix"], "table_rows": [
    ["CPC above allowable", "CPC ₹31.1 vs ₹10.7 allowable", "CPC ₹46.2 vs ₹14.8 allowable", "Break-even CPC bidding"],
    ["Discovery leakage", "Auto, phrase and broad weak", "Phrase and generic weak", "Weekly negative-keyword loop"],
    ["Budget not following winners", "Exact match under-scaled", "Category ads under-funded", "Budget tiers by ROAS and intent"],
    ["Visibility spend mixed in", "Display ads weak", "Banner slots weak", "Separate visibility budget"]]},
    "side-by-side comparison; accent the Fix column in a positive colour as the recommended fixes", columns=4, rows=4)
# a numbers table for <Highlight> (user, 2026-11-02): a row fill, a rule against another column, max / min, a phrase
ROAS_T = comp("roas", "table", {"table_columns": ["Platform", "Spend", "ROAS", "Target", "Note"], "table_rows": [
    ["Amazon", "₹31.2L", "2.8x", "2.0x", "Above target; scale exact match"],
    ["Flipkart", "₹42.0L", "0.34x", "2.0x", "Below target, spend still rising"],
    ["Myntra", "₹12.6L", "1.9x", "2.0x", "Near target; watch CPC creep"],
    ["Nykaa", "₹9.8L", "3.4x", "2.0x", "Best return at the lowest spend"]]},
    "flag Flipkart as the worst performer; show which platforms beat the ROAS target", columns=5, rows=4)
HIGHLIGHTS = ('<Highlight row="Flipkart" fill="bad"/><Highlight column="ROAS" below="Target" color="bad" else="good"/>'
              '<Highlight column="Spend" max="bad"/><Highlight phrase="Best return" color="good"/>')
# changes, a status and a size column for show= arrows / pills / bars (user, 2026-11-02)
SEG_T = comp("segs", "table", {"table_columns": ["Segment", "ARR", "QoQ", "Status"], "table_rows": [
    ["Enterprise", "₹28.1 Cr", "+22%", "On track"], ["Mid-Market", "₹14.4 Cr", "-3%", "At risk"],
    ["SMB", "₹5.7 Cr", "+8%", "On track"], ["Startups", "₹2.1 Cr", "-11%", "Watch"]]},
    "flag Mid-Market as at risk; show the quarter's change", columns=4, rows=4)
SHOWS = ('<Highlight column="QoQ" show="arrows"/><Highlight column="Status" show="pills"/>'
         '<Highlight column="ARR" show="bars"/><Highlight phrase="At risk" color="bad"/>')
# one-series bar with unit strings (saved: "Campaign-class ROAS", 19 one-series bars of 4-6 points)
CHART = comp("roas", "chart", {"chart_title": "ROAS by campaign class",
                               "chart_labels": ["Generic search", "Category / PLA", "Brand", "Competitor"],
                               "chart_values": ["0.29x", "0.80x", "0.99x", "0.15x"]},
             "accent the Generic search bar as the largest budget pool; mute the other bars", chart_type="bar", series_count=1)
# four insight points, three "Head: detail" / "Head — detail" (saved: 66 of 142 lists mostly split)
BULLETS = comp("insights", "bullet_list", {"bullets": [
    "Recommendation ads return 11.3x ROAS at a third of Search spend, but bring few new buyers",
    "Product A is the star: 8.0x ROAS at 12.5% ACOS, Product B close behind at 6.9x",
    "Product C drags: 4.3x ROAS and 23% ACOS, CPM ₹470 against ₹332",
    "Generic keywords win new buyers — 19.3% new-to-brand, keep them despite lower ROAS"]}, items=4)
# dates + labels that carry their detail after " — " (saved: 19 timelines, 0 with description; 38% of labels re-cut)
TIMELINE = comp("roadmap", "timeline", {"direction": "horizontal", "timeline_items": [
    {"date": "Jul–Aug", "label": "Growth activation — search scaling, placement expansion"},
    {"date": "Sep–Oct", "label": "Festive push — bundles, competitor conquesting"},
    {"date": "Nov", "label": "Post-festive retention — retarget new-to-brand buyers"},
    {"date": "Dec", "label": "Year-end consolidation — set next year's plan"}]},
    "highlight Nov, where we are now", items=4, orientation="horizontal")
# short steps (saved: 7 of 10 process_arrows) and long "Phase N: head—detail" steps (3 of 10)
STEPS_SHORT = comp("pillars", "process_arrow", {"direction": "horizontal", "process_steps": [
    "Format rebalance", "City re-allocation", "Day-part rollout", "SKU discipline", "Measurement uplift"]}, items=5)
STEPS_LONG = comp("phases", "process_arrow", {"direction": "horizontal", "process_steps": [
    "Phase 1: Foundation and hygiene — track availability, cut out-of-stocks, audit search",
    "Phase 2: Share capture — win search, widen sponsored placements, conquest rivals",
    "Phase 3: Consumer expansion — new-to-brand buyers, new platforms and cities",
    "Phase 4: Scale and profit — automate bidding, measure incrementality, grow repeat"]}, items=4)
# a linear flow, destination last (saved: 9 of 10 flows linear, 4-5 steps)
FLOW = comp("value_chain", "flow", {"direction": "horizontal", "flow_steps": ["Visibility", "Offtake", "Market share",
                                                                             "Profitability"]},
            "emphasize compounding impact: each step more prominent", items=4)
TAKEAWAY = comp("takeaway", "narrative", {"text": "Momentum comes from ARR growth and rising NRR; gross margin and CAC "
                                                  "payback remain the areas to fix in Q4."})
QUOTE = LB.QUOTE
TITLE = LB.TITLE
MATRIX = comp("bets", "matrix", {"x_axis": "Effort", "y_axis": "Impact", "quadrants": {
    "top_left": "Quick wins", "top_right": "Strategic bets", "bottom_left": "Fill-ins", "bottom_right": "Avoid"},
    "matrix_items": [{"label": "Bundle offers", "x": "low", "y": "high"}, {"label": "Referral program", "x": "low", "y": "high"},
                     {"label": "Own delivery fleet", "x": "high", "y": "high"}, {"label": "Loyalty app", "x": "high", "y": "low"},
                     {"label": "Price-pack audit", "x": "low", "y": "low"}]}, "lead with the quick wins")

HEADS = {"table": "Four gaps cost us the return, and each has one fix",
         "chart": "Generic search takes the most budget and returns the least",
         "bullets": "Recommendation ads and Product A carry the return",
         "timeline": "Four phases take the plan to year end",
         "process": "Four phases move us from hygiene to profitable scale",
         "flow": "Visibility compounds into profit",
         "callout": "Revenue keeps compounding while margin slips",
         "header": "Quick commerce carried H1 growth",
         "matrix": "Two quick wins come before the big bets"}


def a(**kw: str) -> str:
    return "".join(f' {k.replace("__", ".")}="{X(v)}"' for k, v in kw.items())


def cd(c: dict) -> dict:
    return c["content_data"]


def rule(i: int, side: str = "borderTop") -> str:
    """The divider. look part between items (rows / strip): none before the first."""
    return a(**{f"{side}__color": "$border", f"{side}__width": "1"}) if i else ""


def num(i: int, px: int = 34, color: str = "$accentText") -> str:
    return f'<VStack w="72">{t(f"{i + 1:02d}", px, color, bold="true")}</VStack>'


def hint_index(c: dict, names: list[str]) -> int | None:
    """The item the plan's hint names (code's emphasis, as tiles.emphasis_index); first word match."""
    h = c.get("design_hint", "").lower()
    return next((i for i, n in enumerate(names) if n.lower().split()[0] in h), None)


# ── table: bare tags drawn by tables.py (POM_NODES); the hand-written XML of 2026-10-27 that they replace drew the
# reference sheet ─────────────────────────────────────────────────────────────────────────────────────────────────


# ── chart: item = point (ChartPoint) ───────────────────────────────────────────────────────────────────────────

def chart_tag(variant: str = "", extra: str = "") -> str:
    """The bare tag the generator writes (POM_NODES=chart); charts.expand draws it (was hand-written XML here, the
    sheet of 2026-10-27 is the reference it must match)."""
    v = f' variant="{variant}"' if variant else ""
    return f'<Chart ref="roas"{v}{extra} />'


# ── bullet list: item = point (Bullet); code splits "Head: detail" into label. + description. ─────────────────────

def bullet_parts(b: str) -> tuple[str, str]:
    return split(b)


def bullets_native() -> str:
    """native: POM Ul, every point verbatim; a split point's head in bold (the left-blocks `lead`, now code's default)."""
    lis = []
    for b in cd(BULLETS)["bullets"]:
        h, d = bullet_parts(b)
        sep = b[len(h):len(b) - len(d)] if d else ""
        lis.append(f"<Li><B>{X(h)}</B>{X(sep)}{X(d)}</Li>" if d else f"<Li>{X(b)}</Li>")
    return f'<Ul fontSize="22" lineHeight="1.5" color="$textMain">{"".join(lis)}</Ul>'


def bullets_rows(numbered: bool) -> str:
    """rows (numbered): one point per full-width row, ruled: marker (or number) · head over detail."""
    out = []
    for i, b in enumerate(cd(BULLETS)["bullets"]):
        h, d = bullet_parts(b)
        lead = num(i, 30) if numbered else ('<VStack w="40" padding.top="8"><Shape shapeType="ellipse" w="14" h="14" '
                                            'fill.color="$accent" /></VStack>')
        txt = t(h, 22, bold="true") + (t(d, 18, "$textMuted") if d else "")
        out.append(f'<HStack id="card-insights-{i}" grow="1" gap="16" alignItems="center" padding.top="10" padding.bottom="10"{rule(i)}>'
                   f'{lead}<VStack w="1" grow="1" gap="4">{txt}</VStack></HStack>')
    return f'<VStack gap="0" grow="1">{"".join(out)}</VStack>'


def bullets_grid() -> str:
    """grid: each point in its own box, 2 x 2; head over detail."""
    boxes = []
    for i, b in enumerate(cd(BULLETS)["bullets"]):
        h, d = bullet_parts(b)
        boxes.append(f'<VStack id="card-insights-{i}" w="1" grow="1" gap="8" padding="22" backgroundColor="$surfaceAlt" '
                     f'border.color="$border" border.width="1" borderRadius="8">{t(h, 21, bold="true")}'
                     + (t(d, 17, "$textMuted") if d else "") + "</VStack>")
    return ('<VStack gap="16" grow="1">' + "".join(f'<HStack gap="16" grow="1" alignItems="stretch">{"".join(boxes[k:k + 2])}</HStack>'
                                                   for k in (0, 2)) + "</VStack>")


def bullets_banded() -> str:
    """banded: equal boxes, 2 x 2, the head in a solid band. over the detail (an unsplit point: the band holds it all)."""
    boxes = []
    for i, b in enumerate(cd(BULLETS)["bullets"]):
        h, d = bullet_parts(b)
        boxes.append(f'<VStack id="card-insights-{i}" w="1" grow="1" gap="0" border.color="$border" border.width="1">'
                     f'<HStack padding="14" backgroundColor="$accent">{t(h, 19, "$onAccent", bold="true")}</HStack>'
                     f'<VStack grow="1" padding="18" backgroundColor="$surfaceAlt">{t(d, 18) if d else ""}</VStack></VStack>')
    return ('<VStack gap="16" grow="1">' + "".join(f'<HStack gap="16" grow="1" alignItems="stretch">{"".join(boxes[k:k + 2])}</HStack>'
                                                   for k in (0, 2)) + "</VStack>")


# ── timeline / process_arrow / flow: bare tags drawn by sequences.py (POM_NODES); the hand-written XML of
# 2026-10-27 that they replace drew the reference sheets ───────────────────────────────────────────────────────

TIMELINE_SHORT = comp("roadmap_short", "timeline", {"direction": "horizontal", "timeline_items": [
    {"date": "Jul–Aug", "label": "Growth activation"}, {"date": "Sep–Oct", "label": "Festive push"},
    {"date": "Nov", "label": "Retention"}, {"date": "Dec", "label": "Year-end plan"}]},
    "highlight Nov, where we are now", items=4, orientation="horizontal")


def table_recipe(variant: str, style: str) -> str:
    """A <Table ref> with one of block-variants.yaml's table recipes written on it, as the LLM would."""
    from src.compiler.nodes import tables
    return f'<Table ref="gaps" variant="{variant}" {tables.node()["styles"][style]} />'


def tag(name: str, c: dict, variant: str = "") -> str:
    v = f' variant="{variant}"' if variant else ""
    return f'<{name} ref="{c["component_id"]}"{v} />'


# ── callout (narrative): one item, no list ───────────────────────────────────────────────────────────────────────

def callout_native(c: dict) -> str:
    """native: the text in its box, default look `tinted` ($toneSoft panel, 4 px $tone edge; tone none = accent).
    A quotation (opens with a quote mark, ends "— Name") draws the mark. glyph and the attribution: a content rule."""
    text = cd(c)["text"]
    if text.lstrip()[:1] in "“\"":
        q, who = (text.rsplit(" — ", 1) + [""])[:2]
        return (f'<VStack backgroundColor="$accentSoft" borderLeft.color="$accent" borderLeft.width="4" padding="28" gap="4">'
                f'{t("“", 64, "$accent", bold="true", lineHeight="1")}{t(q.strip("“”"), 24, italic="true")}'
                + (t(f"— {who}", 16, "$textMuted") if who else "") + "</VStack>")
    return (f'<VStack backgroundColor="$accentSoft" borderLeft.color="$accent" borderLeft.width="4" padding="28">'
            f'{t(text, 24)}</VStack>')


# ── matrix: item = MatrixItem (label, x, y) ───────────────────────────────────────────────────────────────────────

def matrix_grid() -> str:
    """grid: the four quadrants as equal boxes (2 x 2), the quadrant name as title, its items listed (no overlap);
    axis names on the edges. The cell the hint names is the emphasis ($positiveSoft); no hint, no emphasis."""
    m = cd(MATRIX)
    q = m["quadrants"]
    cells = {("low", "high"): q["top_left"], ("high", "high"): q["top_right"], ("low", "low"): q["bottom_left"],
             ("high", "low"): q["bottom_right"]}
    lv = lambda v: "low" if v in ("low", "mid") else "high"  # noqa: E731
    inside = {k: [i["label"] for i in m["matrix_items"] if (lv(i["x"]), lv(i["y"])) == k] for k in cells}

    focus = hint_index(MATRIX, list(cells.values()))
    order = list(cells)

    def box(k: tuple[str, str], i: int) -> str:
        em = focus is not None and order[focus] == k
        items = "".join(f'<HStack gap="10" alignItems="center"><Shape shapeType="ellipse" w="10" h="10" fill.color="{"$positive" if em else "$accent"}" />'
                        f'{t(x, 19)}</HStack>' for x in inside[k])
        fill = a(backgroundColor="$positiveSoft", border__color="$positive") if em else a(backgroundColor="$surfaceAlt", border__color="$border")
        return (f'<VStack id="card-bets-{i}" w="1" grow="1" gap="10" padding="20" border.width="1"{fill}>'
                f'{t(cells[k].upper(), 14, "$positiveText" if em else "$textMuted", bold="true", letterSpacing="1")}{items}</VStack>')

    top = f'<HStack gap="12" grow="1" alignItems="stretch">{box(("low", "high"), 0)}{box(("high", "high"), 1)}</HStack>'
    bot = f'<HStack gap="12" grow="1" alignItems="stretch">{box(("low", "low"), 2)}{box(("high", "low"), 3)}</HStack>'
    # axis names as plain labels: a rotated Text is measured unrotated by POM and wraps in a narrow column
    return (f'<VStack grow="1" gap="10">{t("↑ " + m["y_axis"].upper(), 14, "$textMuted", bold="true")}{top}{bot}'
            f'{t(m["x_axis"].upper() + " →", 14, "$textMuted", bold="true", textAlign="right")}</VStack>')


# ── sheets: block -> (today row [(label, comps, body)], compositions [(label, comps, body)]) ─────────────────────

def blocks() -> dict[str, tuple[list, list]]:
    return {
        "table": ([(f"today · {v}", [LB.TABLE], LB.table(v)) for v in ("plain", "zebra", "dark_header")],
                  [("native (default)", [TABLE], tag("Table", TABLE)), ("rows", [TABLE], tag("Table", TABLE, "rows")),
                   ("native · borderless", [ROAS_T], table_recipe("native", "borderless").replace('"gaps"', '"roas"')),
                   ("native · bordered", [TABLE], table_recipe("native", "bordered")),
                   ("ledger · icons", [TABLE], '<Table ref="gaps" variant="ledger" icons="alert-triangle,store,shopping-cart,wrench" />'),
                   ("native · highlights", [ROAS_T], f'<Table ref="roas">{HIGHLIGHTS}</Table>'),
                   ("ledger · highlights", [ROAS_T], f'<Table ref="roas" variant="ledger">{HIGHLIGHTS}</Table>'),
                   ("native · arrows", [SEG_T], f'<Table ref="segs">{SHOWS}</Table>'),
                   ("ledger · arrows pills bars", [SEG_T], f'<Table ref="segs" variant="ledger">{SHOWS}</Table>'),
                   ("grid · arrows pills bars", [SEG_T], f'<Table ref="segs" variant="grid">{SHOWS}</Table>')]),
        "chart": ([(f"today · {v}", [LB.CHART], LB.chart(v)) for v in ("plain", "labelled", "focus_label")],
                  [("native (default)", [CHART], chart_tag()), ("native labelled", [CHART], chart_tag("native labelled")),
                   ("rows", [CHART], chart_tag("rows")),
                   ("native · horizontal", [CHART], chart_tag("", ' direction="horizontal"')),
                   ("native labelled · horizontal", [CHART], chart_tag("native labelled", ' direction="horizontal"'))]),
        "bullets": ([(f"today · {v}", [LB.BULLETS], LB.bullets(v)) for v in ("plain", "icon", "tiles")],
                    [("native (default)", [BULLETS], bullets_native()), ("rows", [BULLETS], bullets_rows(False)),
                     ("rows numbered", [BULLETS], bullets_rows(True)), ("grid", [BULLETS], bullets_grid()),
                     ("banded", [BULLETS], bullets_banded())]),
        "timeline": ([(f"today · {v}", [LB.TIMELINE], LB.timeline(v)) for v in ("rail", "cards", "columns")],
                     [("native · short labels (default)", [TIMELINE_SHORT], tag("Timeline", TIMELINE_SHORT)),
                      ("bare tag · labels with detail -> rail", [TIMELINE], tag("Timeline", TIMELINE)),
                      ("banded", [TIMELINE], tag("Timeline", TIMELINE, "banded")),
                      ("rows", [TIMELINE], tag("Timeline", TIMELINE, "rows"))]),
        "process": ([(f"today · {v}",) + LB.process(v) for v in ("chevrons", "numbered", "alternating")],
                    [("bare tag · short steps -> native", [STEPS_SHORT], tag("ProcessArrow", STEPS_SHORT)),
                     ("bare tag · long steps -> steps", [STEPS_LONG], tag("ProcessArrow", STEPS_LONG)),
                     ("steps numbered · short steps", [STEPS_SHORT], tag("ProcessArrow", STEPS_SHORT, "steps numbered")),
                     ("rail · short steps", [STEPS_SHORT], tag("ProcessArrow", STEPS_SHORT, "rail")),
                     ("rail · long steps", [STEPS_LONG], tag("ProcessArrow", STEPS_LONG, "rail"))]),
        "flow": ([(f"today · {v}",) + LB.flow(v) for v in ("boxes", "numbered", "step_cards")],
                 [("native (default)", [FLOW], tag("Flow", FLOW)), ("steps", [FLOW], tag("Flow", FLOW, "steps")),
                  ("steps numbered", [FLOW], tag("Flow", FLOW, "steps numbered"))]),
        "callout": ([(f"today · {v}", [LB.TAKEAWAY], LB.beside_chart(LB.callout(v))) for v in ("tinted", "rule", "dark")],
                    [("native (default) · takeaway", [TAKEAWAY], LB.beside_chart(callout_native(TAKEAWAY))),
                     ("native · a quotation (content rule)", [QUOTE], LB.beside_chart(callout_native(QUOTE)))]),
        "header": ([(f"today · {v}", [TITLE, LB.TABLE], LB.header(v)) for v in ("standard", "inverted", "ruled")],
                   [("native (default) = standard", [TITLE, LB.TABLE], LB.header("standard"))]),
        "matrix": ([("today · native POM", [MATRIX], native.matrix(MATRIX, {"w": "max", "h": "max"}, {}))],
                   [("native (default)", [MATRIX], native.matrix(MATRIX, {"w": "max", "h": "max"}, {})),
                    ("grid (proposed)", [MATRIX], matrix_grid())]),
    }


_STACK = re.compile(r"<(/?)(VStack|HStack)\b([^<>]*?)(/?)>")


def inner_ids(xml: str) -> str:
    """Give every box inside an item (id card-<cid>-<i>) the id card-<cid>x-<n>: one fit-grow peer group per block.
    An item whose children stretch is never sparse, so fit-grow grows its inner boxes instead, each alone when they
    carry no group id: one item's parts ended larger than its peers' (first render, 2026-10-27: table `columns`
    column 4, `banded` top row)."""
    out, stack, k = [], [], 0

    def sub(m: re.Match) -> str:
        nonlocal k
        close, tag, attrs, selfclose = m.groups()
        if close:
            stack.pop()
            return m.group(0)
        own = re.search(r'\sid="(card-[^"]+)"', attrs)
        owner = own.group(1) if own else (stack[-1] if stack else None)
        if owner and not own and 'id="' not in attrs:
            k += 1
            attrs += f' id="{owner.rsplit("-", 1)[0]}x-{k}"'
        if not selfclose:
            stack.append(owner)
        return f"<{tag}{attrs}{selfclose}>"

    return _STACK.sub(sub, xml)


def build(block: str, out: Path) -> None:
    today, comps = blocks()[block]
    themes = {p: resolve_theme(p)["element"] for p in PALETTES}
    head = HEADS[block]
    rows, log = [], []

    def draw(label: str, pal: str, cs: list[dict], body: str) -> tuple[str, Path | None]:
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        d = out / block / f"{slug}-{pal}"
        xml = inner_ids(body if body.startswith("<Slide") else TG.slide(label.upper(), head, body))
        # today's chart names get the old post-edit; a <Chart ref> tag draws its labels itself (charts.py, pptx-post.js)
        today = label.startswith("today")
        variant = ("labelled" if "labelled" in label else label.split(" · ")[-1].split()[0]) if today else ""
        pdf, issues = LB.compile_one(d, xml, {"components": cs, "slide_title": head}, themes[pal], variant)
        res = json.loads((d / "compile-result.json").read_text(encoding="utf-8")) if (d / "compile-result.json").exists() else {}
        log.append({"block": block, "shot": label, "palette": pal, "rendered": bool(pdf), "fill_errors": issues,
                    "fitGrow": res.get("fitGrow", []), "warnings": [w.get("code") for w in res.get("warnings") or []]})
        print(f"{block} {label} {pal}: {'ok' if pdf else 'NO RENDER'} {issues or ''}", flush=True)
        return f"{label} · {pal}", pdf

    rows.append(("today", [draw(lb, PALETTES[0], cs, b) for lb, cs, b in today]))
    for label, cs, body in comps:
        rows.append((label, [draw(label, pal, cs, body) for pal in PALETTES]))
    DOCS.mkdir(parents=True, exist_ok=True)
    CT.sheet_rows(rows, DOCS / f"{block}.png")
    (out / block / "log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    print(DOCS / f"{block}.png", flush=True)


def main() -> int:
    names = list(blocks())
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", default=names, choices=names)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    for b in args.only:
        shutil.rmtree(args.out / b, ignore_errors=True)
        build(b, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
