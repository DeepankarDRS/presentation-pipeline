"""A gallery deck of the candidate components in docs/component-variant-research-2026-10-24.md.

    python -m scripts.experiments.component_candidates_gallery [--palette corporate-slate] [--out output/component-candidates]

Nine slides of hand-written POM, one per candidate (A-M), 2-4 variants each, drawn with the palette and
derived tokens of scripts/tools/variant_gallery.py. Content is copied from our briefs (CHEFFIN, agency
takeover, XTSY, sales, product launch); derived numbers (gap multiples, conversion %) are computed here.
It is a picture of the proposals for review: sizes are fixed by hand, the real components would measure.
Writes slide-N.xml (the POM), the merged .pptx and, with --png, one PNG per slide via PowerPoint.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.tools.variant_gallery import (  # noqa: E402
    MONO, SANS, esc, header, label, mix, number, slide, text, tokens, variant_caption,
)
from src.compiler.font_embed import embed_deck_fonts  # noqa: E402
from src.compiler.pptx_merge import merge_pptx_files  # noqa: E402


def panel(name: str, slot: str, note: str, inner: str, size: str = 'w="1" grow="1"', pad: int = 16) -> str:
    return (f'<VStack {size} gap="6" alignItems="stretch">{variant_caption(name, slot, note)}'
            f'<VStack grow="1" padding="{pad}" gap="10" backgroundColor="$surface" border.color="$border" '
            f'border.width="1" alignItems="stretch" justifyContent="center">{inner}</VStack></VStack>')


def row(*panels: str, grow: str = 'grow="1"', gap: int = 20) -> str:
    return f'<HStack {grow} gap="{gap}" alignItems="stretch">{"".join(panels)}</HStack>'


def col(*parts: str, grow: str = 'grow="1"', gap: int = 14) -> str:
    return f'<VStack {grow} gap="{gap}" alignItems="stretch">{"".join(parts)}</VStack>'


def box(x: float, y: float, w: float, h: float, fill: str, txt: str = "", color: str = "$textMain",
        size: int = 13, bold: bool = False, shape: str = "rect", line: str = "") -> str:
    b = ' bold="true"' if bold else ""
    tx = f' text="{esc(txt)}" fontFamily="{SANS}" fontSize="{size}" color="{color}"{b} textAlign="center"' if txt else ""
    ln = f' line.color="{line}" line.width="1"' if line else ""
    return (f'<Shape shapeType="{shape}" x="{round(x)}" y="{round(y)}" w="{round(w)}" h="{round(h)}" '
            f'fill.color="{fill}"{ln}{tx} />')


def ltext(x: float, y: float, w: float, s: str, size: int = 13, color: str = "$textMain", bold: bool = False,
          align: str = "left", font: str = SANS) -> str:
    b = ' bold="true"' if bold else ""
    return (f'<Text x="{round(x)}" y="{round(y)}" w="{round(w)}" fontFamily="{font}" fontSize="{size}" '
            f'color="{color}"{b} textAlign="{align}">{esc(s)}</Text>')


def line(t: dict, x1, y1, x2, y2, color: str = "border", width: float = 1.5, arrow: bool = False, dash: str = "") -> str:
    a = ' endArrow="true"' if arrow else ""
    d = f' dashType="{dash}"' if dash else ""
    return (f'<Line x1="{round(x1)}" y1="{round(y1)}" x2="{round(x2)}" y2="{round(y2)}" color="{t[color]}" '
            f'lineWidth="{width}"{a}{d} />')


def layer(w: int, h: int, inner: str) -> str:
    return f'<HStack justifyContent="center"><Layer w="{w}" h="{h}">{inner}</Layer></HStack>'


def pill(s: str, fill: str, color: str, w: int = 64) -> str:
    return (f'<Shape shapeType="roundRect" w="{w}" h="24" fill.color="{fill}" text="{esc(s)}" '
            f'fontFamily="{SANS}" fontSize="13" bold="true" color="{color}" />')


# ── A. chart options ─────────────────────────────────────────────────────────

REV = [("Q2 FY25", 28.4), ("Q3 FY25", 31.2), ("Q4 FY25", 36.1), ("Q1 FY26", 39.1), ("Q2 FY26", 42.3), ("Q3 FY26", 48.2)]
MATCH = [("Exact", 0.44), ("Auto", 0.30), ("Phrase", 0.26), ("Category", 0.25), ("Broad", 0.22), ("Audience", 0.15)]


def chart_xml(colors: list[str]) -> str:
    pts = "".join(f'<ChartDataPoint label="{k}" value="{v}" />' for k, v in REV)
    cc = json.dumps(colors)
    return (f'<Chart chartType="bar" w="max" h="176" showLegend="false" chartColors=\'{cc}\'>'
            f'<ChartSeries name="Revenue ($M)">{pts}</ChartSeries></Chart>')


def hbars(t: dict) -> str:
    rows = []
    for k, v in MATCH:
        focus = k == "Exact"
        rows.append(f'<HStack gap="10" alignItems="center"><Text w="82" fontFamily="{SANS}" fontSize="13" '
                    f'color="$textMain" textAlign="right">{k}</Text>'
                    f'<Shape shapeType="rect" w="{round(v / 0.44 * 330)}" h="18" '
                    f'backgroundColor="{"$accent" if focus else "$border"}" />'
                    f'<Text fontFamily="{SANS}" fontSize="13" bold="{"true" if focus else "false"}" '
                    f'color="$textMain">{v:.2f}x</Text></HStack>')
    return f'<VStack gap="7">{"".join(rows)}</VStack>'


def target_columns(t: dict) -> str:
    W, H, base, scale = 520, 186, 160, 3.4          # 1 pt of win rate = 3.4 px
    out = [line(t, 20, base, W - 10, base, "border", 1)]
    ty = base - 40 * scale
    out.append(line(t, 20, ty, W - 10, ty, "warning", 1.5, dash="dash"))
    out.append(ltext(W - 150, ty - 20, 140, "Q4 target 40%", 12, "$warningInk", True, "right"))
    for i, (q, v) in enumerate([("Q1 FY26", 28), ("Q2 FY26", 31), ("Q3 FY26", 34)]):
        x, h = 60 + i * 120, v * scale
        out.append(box(x, base - h, 70, h, "$accent" if i == 2 else "$border"))
        out.append(ltext(x - 15, base - h - 20, 100, f"{v}%", 13, "$textMain", True, "center"))
        out.append(ltext(x - 15, base + 6, 100, q, 12, "$textMuted", False, "center"))
    return layer(W, H, "".join(out))


def slide_a(t: dict) -> str:
    muted = [t["border"]] * 5 + [t["accent"]]
    return slide(t, header("A · Chart options", "Bars that answer the question: labels, one highlight, a target",
                           "Native charts stay editable; labels, horizontal bars and target lines are added to the chart XML after compile (pptx-post).")
                 + col(row(panel("native", "(today, not a variant)", "POM bar, no labels (QBR revenue)", chart_xml([t["accent"]])),
                           panel("highlight", "(colour coding, not a variant)", "chartColors per bar, works in POM today", chart_xml(muted))),
                       row(panel("horizontal", 'variant="horizontal"', "ranked, value on every bar (CHEFFIN match-type ROAS)", hbars(t)),
                           panel("target", 'target="40%"', "reference line from the brief (sales win rate)", target_columns(t)))))


# ── B. target vs actual ──────────────────────────────────────────────────────

GAPS = [("FLIPCART CPC", 31.1, 10.7, "₹", "allowable"), ("ZAROMA CPC", 46.2, 14.8, "₹", "allowable"),
        ("Win rate", 34, 40, "%", "target")]


def fmt(v: float, unit: str) -> str:
    return f"₹{v:.1f}" if unit == "₹" else f"{v:g}%"


def gap_text(a: float, tg: float, unit: str) -> str:
    return f"{a / tg:.1f}× allowable" if unit == "₹" else f"{a - tg:+g} pts to target"


def bullet_rows(t: dict) -> str:
    W, x0, track = 540, 120, 300
    s = track / 50
    out = []
    for i, (lab, a, tg, unit, word) in enumerate(GAPS):
        y = 20 + i * 70
        bad = unit == "₹"
        out.append(ltext(0, y + 4, 110, lab, 13, "$textMain", True, "right"))
        out.append(box(x0, y, track, 28, "$panelFill"))
        out.append(box(x0, y + 8, a * s, 12, "$negative" if bad else "$warning"))
        out.append(box(x0 + tg * s - 2, y - 4, 4, 36, "$textMain"))
        out.append(ltext(x0 + track + 12, y - 2, 120, fmt(a, unit), 15, "$textMain", True))
        out.append(ltext(x0 + track + 12, y + 16, 120, gap_text(a, tg, unit), 12,
                         "$negativeInk" if bad else "$warningInk", True))
        out.append(ltext(x0 + tg * s - 50, y + 32, 100, f"{word} {fmt(tg, unit)}", 11, "$textMuted", False, "center"))
    return layer(W, 230, "".join(out))


def dumbbell(t: dict) -> str:
    W, x0, track = 520, 120, 330
    s = track / 50
    out = []
    for i, (lab, a, tg, unit, word) in enumerate(GAPS[:2]):
        y = 34 + i * 62
        out.append(ltext(0, y - 9, 110, lab, 13, "$textMain", True, "right"))
        out.append(line(t, x0 + tg * s, y, x0 + a * s, y, "border", 3))
        out.append(box(x0 + tg * s - 8, y - 8, 16, 16, "$surface", shape="ellipse", line=t["textMuted"]))
        out.append(box(x0 + a * s - 8, y - 8, 16, 16, "$negative", shape="ellipse"))
        out.append(ltext(x0 + tg * s - 40, y + 10, 80, fmt(tg, unit), 12, "$textMuted", False, "center"))
        out.append(ltext(x0 + a * s - 40, y + 10, 80, fmt(a, unit), 13, "$negativeInk", True, "center"))
        out.append(ltext(x0 + (tg + a) / 2 * s - 50, y - 26, 100, f"{a / tg:.1f}×", 13, "$textMain", True, "center"))
    return layer(W, 150, "".join(out))


def paired(t: dict) -> str:
    rows = []
    for lab, a, tg, unit, word in GAPS[:2]:
        rows.append(f'<VStack gap="4"><Text fontFamily="{SANS}" fontSize="13" bold="true" color="$textMain">{lab}</Text>'
                    f'<HStack gap="8" alignItems="center"><Shape shapeType="rect" w="{round(a * 7)}" h="16" fill.color="$negative" />'
                    f'<Text fontFamily="{SANS}" fontSize="13" bold="true" color="$negativeInk">{fmt(a, unit)} actual</Text></HStack>'
                    f'<HStack gap="8" alignItems="center"><Shape shapeType="rect" w="{round(tg * 7)}" h="16" fill.color="$border" />'
                    f'<Text fontFamily="{SANS}" fontSize="13" color="$textMuted">{fmt(tg, unit)} {word}</Text></HStack></VStack>')
    return f'<VStack gap="14">{"".join(rows)}</VStack>'


def slide_b(t: dict) -> str:
    return slide(t, header("B · Target vs actual", "CPC is nearly 3x what conversion economics can support",
                           "One row per item: actual, the brief's target or allowable, and a gap computed by code (never typed by the LLM).")
                 + row(panel("bullet", 'variant="bullet"', "bar + target tick, mixed units per row (Few)", bullet_rows(t), 'w="11" grow="11"'),
                       col(panel("dumbbell", 'variant="dumbbell"', "allowable ↔ actual, gap on the line", dumbbell(t), 'grow="1"'),
                           panel("paired", 'variant="paired"', "two bars per item, labels in words", paired(t), 'grow="1"'),
                           grow='w="9" grow="9"')))


# ── C. before -> after ───────────────────────────────────────────────────────

BETA = [("Config time", "2.3 hrs/wk", "15 min/wk", "−89%"), ("Config outages", "12/qtr", "1/qtr", "−92%"),
        ("API latency", "142ms", "38ms", "−73%"), ("Developer NPS", "22", "71", "+49 pts")]


def ba_tiles(t: dict) -> str:
    tiles = []
    for lab, b, a, ch in BETA:
        tiles.append(f'<VStack w="1" grow="1" padding="16" gap="6" backgroundColor="$panelFill">{label(lab)}'
                     f'<Text fontFamily="{SANS}" fontSize="16" color="$textMuted" strike="true">{esc(b)}</Text>'
                     f'{number(a, 40, "$textMain")}<VStack h="6" /><HStack>{pill(ch, "$positiveTint", "$positiveInk", 76)}</HStack></VStack>')
    return f'<HStack gap="12" alignItems="stretch">{"".join(tiles)}</HStack>'


def ba_rows(t: dict) -> str:
    rows = []
    for lab, b, a, ch in BETA:
        rows.append(f'<HStack gap="10" alignItems="center"><Text w="120" fontFamily="{SANS}" fontSize="13" color="$textMain">{lab}</Text>'
                    f'<Text w="82" fontFamily="{SANS}" fontSize="14" color="$textMuted" textAlign="right">{esc(b)}</Text>'
                    f'<Shape shapeType="rightArrow" w="40" h="14" fill.color="$border" />'
                    f'<Text w="90" fontFamily="{SANS}" fontSize="16" bold="true" color="$textMain">{esc(a)}</Text>'
                    f'{pill(ch, "$positiveTint", "$positiveInk", 76)}</HStack>')
    return f'<VStack gap="12">{"".join(rows)}</VStack>'


def ba_split(t: dict) -> str:
    def side(title: str, fill: str, idx: int, bold: bool) -> str:
        items = "".join(f'<HStack justifyContent="spaceBetween"><Text fontFamily="{SANS}" fontSize="13" color="$textMuted">{lab}</Text>'
                        f'<Text fontFamily="{SANS}" fontSize="15" bold="{"true" if bold else "false"}" color="$textMain">{esc(v[idx])}</Text></HStack>'
                        for lab, *v in [(r[0], r[1], r[2]) for r in BETA])
        return f'<VStack w="1" grow="1" padding="14" gap="9" backgroundColor="{fill}">{label(title)}{items}</VStack>'
    return (f'<HStack gap="12" alignItems="stretch">{side("Before Nexus", "$panelFill", 0, False)}'
            f'{side("Private beta", "$accentTint", 1, True)}</HStack>')


def slide_c(t: dict) -> str:
    return slide(t, header("C · Before → after", "Beta cut config time from 2.3 hours to 15 minutes a week",
                           "Both values copied from the brief; the change pill is computed. A new `kpi_before` field keeps the before value in the plan.")
                 + col(panel("tiles", 'kpi_before + variant="tiles"', "old value struck, new value large, change pill", ba_tiles(t), 'h="190"'),
                       row(panel("rows", 'variant="rows"', "from → to list, 3-8 metrics", ba_rows(t)),
                           panel("split", 'variant="split"', "two columns: before | after", ba_split(t)))))


# ── D. funnel ────────────────────────────────────────────────────────────────

PIPE = [("Prospecting", "$12.4M", 12.4, 38), ("Discovery", "$9.8M", 9.8, 24), ("Proposal", "$11.2M", 11.2, 18),
        ("Negotiation", "$6.1M", 6.1, 9), ("Closed Won", "$3.1M", 3.1, 6)]


def conv(i: int) -> str:
    return f"{PIPE[i][3] / PIPE[i - 1][3]:.0%}"


def funnel_centred(t: dict) -> str:
    rows = []
    for i, (st, v, _, n) in enumerate(PIPE):
        if i:
            rows.append(f'<Text fontFamily="{SANS}" fontSize="11" color="$textMuted" textAlign="center">▼ {conv(i)} of deals</Text>')
        rows.append(f'<HStack justifyContent="center"><Shape shapeType="rect" w="{round(n / 38 * 300)}" h="30" '
                    f'backgroundColor="{"$accent" if i == 4 else mix(t["accent"], t["surface"], 0.15 + i * 0.13)}" /></HStack>'
                    f'<Text fontFamily="{SANS}" fontSize="12" color="$textMain" textAlign="center"><B>{st}</B>  {v} · {n} deals</Text>')
    return f'<VStack gap="2">{"".join(rows)}</VStack>'


def funnel_bars(t: dict) -> str:
    rows = []
    for i, (st, v, m, n) in enumerate(PIPE):
        c = f"  ·  {conv(i)}" if i else ""
        rows.append(f'<VStack gap="3"><Text fontFamily="{SANS}" fontSize="12" color="$textMuted"><B>{st}</B>  {n} deals{c}</Text>'
                    f'<HStack gap="8" alignItems="center"><Shape shapeType="rect" w="{round(m / 12.4 * 230)}" h="20" '
                    f'backgroundColor="{"$accent" if i == 4 else "$border"}" />'
                    f'<Text fontFamily="{SANS}" fontSize="14" bold="true" color="$textMain">{v}</Text></HStack></VStack>')
    return f'<VStack gap="9">{"".join(rows)}</VStack>'


def funnel_steps(t: dict) -> str:
    rows = []
    for i, (st, v, _, n) in enumerate(PIPE):
        if i:
            rows.append(f'<Text fontFamily="{SANS}" fontSize="11" color="$textMuted" textAlign="center">▼ {conv(i)} of deals</Text>')
        dark = i == 4
        rows.append(f'<HStack padding="10" justifyContent="spaceBetween" alignItems="center" '
                    f'backgroundColor="{"$darkFill" if dark else "$panelFill"}">'
                    f'<Text fontFamily="{SANS}" fontSize="13" bold="true" color="{"$onDark" if dark else "$textMain"}">{st}</Text>'
                    f'<Text fontFamily="{SANS}" fontSize="13" color="{"$onDark" if dark else "$textMain"}">{v} · {n}</Text></HStack>')
    return f'<VStack gap="3">{"".join(rows)}</VStack>'


def slide_d(t: dict) -> str:
    return slide(t, header("D · Funnel", "Only 6 of 38 prospected deals reach Closed Won",
                           "Stages and values copied (sales brief); stage conversion computed from deal counts. Value is not monotonic here (Proposal > Discovery), so widths follow deals.")
                 + row(panel("centred", 'variant="centred"', "classic narrowing bars", funnel_centred(t)),
                       panel("bars", 'variant="bars"', "left-aligned, easiest to label", funnel_bars(t)),
                       panel("steps", 'variant="steps"', "stage cards, rate between", funnel_steps(t))))


# ── E. side-by-side compare ──────────────────────────────────────────────────

CMP = [("CPC above allowable", "₹31.1 vs ₹10.7", "₹46.2 vs ₹14.8", "Break-even CPC bidding model"),
       ("Discovery leakage", "Auto, phrase, category, broad weak", "Phrase, broad, generic weak", "Weekly harvesting and negative loop"),
       ("Budget not following winners", "SBT and exact under-scaled", "Brand and category/PLA under-allocated", "Budget tiering by ROAS, CVR, intent"),
       ("Visibility spend not separated", "SD/AMC weak", "CPD/BOTD weak", "Separate awareness and performance budgets"),
       ("Reporting and governance", "Broken pivot ratios", "Sheet reconciliation differences", "Raw-data dashboard and source of truth")]


def compare_table(t: dict) -> str:
    tb, ta = mix(t["accent"], t["surface"], 0.86), mix(t["accentAlt"], t["surface"], 0.86)
    def td(s: str, fill: str = "", bold: bool = False, color: str = "$textMain", size: int = 13) -> str:
        f = f' backgroundColor="{fill}"' if fill else ""
        return f'<Td fontFamily="{SANS}" fontSize="{size}" color="{color}" bold="{"true" if bold else "false"}"{f}>{esc(s)}</Td>'
    head = ("<Tr>" + td("GAP", "", True, "$textMuted", 12) + td("PLATFORM B", tb, True, "$textMain", 12)
            + td("PLATFORM A", ta, True, "$textMain", 12) + td("FIX", "$darkFill", True, "$onDark", 12) + "</Tr>")
    body = "".join("<Tr>" + td(f"{i}  {g}", "", True) + td(b, tb) + td(a, ta) + td(f, "$positiveTint", True, "$positiveInk") + "</Tr>"
                   for i, (g, b, a, f) in enumerate(CMP, 1))
    return (f'<Table defaultRowHeight="52" cellBorder.color="{t["surface"]}" cellBorder.width="2">'
            f'<Col width="170" /><Col width="170" /><Col width="170" /><Col width="180" />{head}{body}</Table>')


def butterfly(t: dict) -> str:
    tb, ta = mix(t["accent"], t["surface"], 0.86), mix(t["accentAlt"], t["surface"], 0.86)
    def cell(s: str, fill: str, align: str) -> str:
        return (f'<VStack w="1" grow="1" padding="8" backgroundColor="{fill}" justifyContent="center">'
                f'<Text fontFamily="{SANS}" fontSize="12" color="$textMain" textAlign="{align}">{esc(s)}</Text></VStack>')
    rows = [f'<HStack gap="4"><Text w="1" grow="1" fontFamily="{MONO}" fontSize="11" color="$textMuted" textAlign="right">PLATFORM B</Text>'
            f'<Text w="104" fontFamily="{MONO}" fontSize="11" color="$textMuted" textAlign="center">GAP</Text>'
            f'<Text w="1" grow="1" fontFamily="{MONO}" fontSize="11" color="$textMuted">PLATFORM A</Text></HStack>']
    for g, b, a, _ in CMP[:4]:
        rows.append(f'<HStack gap="4" alignItems="stretch">{cell(b, tb, "right")}'
                    f'<VStack w="104" justifyContent="center"><Text fontFamily="{SANS}" fontSize="12" bold="true" color="$textMain" '
                    f'textAlign="center">{esc(g)}</Text></VStack>{cell(a, ta, "left")}</HStack>')
    return f'<VStack gap="6">{"".join(rows)}</VStack>'


def slide_e(t: dict) -> str:
    return slide(t, header("E · Side-by-side compare", "Both platforms show the same gap: spend is not governed by economics",
                           "A table variant: compared columns tinted per platform (brand colours when the brief gives them), a fix column, glyph cells when the data is a rating.")
                 + row(panel("compare", 'variant="compare" fix_col="Fix"', "agency slide 3: 5 gaps × 2 platforms + fix", compare_table(t), 'w="13" grow="13"'),
                       panel("butterfly", 'variant="butterfly"', "row label in the middle, A and B either side", butterfly(t), 'w="7" grow="7"')))


# ── F. hub / engine ──────────────────────────────────────────────────────────

def hub_radial(t: dict) -> str:
    cx, cy = 170, 200
    sats = [("Zepto", 170, 40), ("Blinkit", 40, 330), ("Instamart", 300, 330)]
    out = [line(t, cx, cy, x, y, "accent", 2) for _, x, y in sats]
    out.append(box(cx - 75, cy - 75, 150, 150, "$darkFill", "XTSY growth engine", "$onDark", 15, True, "ellipse"))
    out += [box(x - 55, y - 22, 110, 44, "$panelFill", s, "$textMain", 14, True, "roundRect", t["border"]) for s, x, y in sats]
    return layer(340, 380, "".join(out))


def hub_engine(t: dict) -> str:
    out = [line(t, 170, 54, 170, 88, "textMuted", 1.5, True)]
    levers = [("Bid Optimization", 20, 190), ("Budget Reallocation", 180, 190), ("Keyword Expansion", 20, 246), ("Placement Optimization", 180, 246)]
    out.append(line(t, 170, 148, 170, 180, "textMuted", 1.5, True))
    out.append(line(t, 170, 296, 170, 324, "textMuted", 1.5, True))
    out.append(box(90, 10, 160, 44, "$panelFill", "Platform Data", "$textMain", 13, True, line=t["border"]))
    out.append(box(70, 88, 200, 60, "$darkFill", "Decision Engine", "$onDark", 16, True))
    out.append(box(10, 180, 320, 116, "$accentTint"))
    out += [box(x, y, 140, 44, "$surface", s, "$textMain", 12, True, line=t["border"]) for s, x, y in levers]
    out.append(box(90, 324, 160, 44, "$positiveTint", "Business Outcome", "$positiveInk", 13, True))
    return layer(340, 380, "".join(out))


def hub_grouped(t: dict) -> str:
    def plate(x, title, items):
        rows = "".join(f'<Text fontFamily="{SANS}" fontSize="12" color="$textMain">{esc(i)}</Text>' for i in items)
        return (f'<VStack x="{x}" y="120" w="160" h="250" padding="12" gap="7" backgroundColor="$panelFill" '
                f'borderTop.color="$accent" borderTop.width="3">{label(title, "$accentInk", 11)}{rows}</VStack>')
    out = [line(t, 170, 76, 85, 120, "accent", 2), line(t, 170, 76, 255, 120, "accent", 2),
           box(70, 16, 200, 60, "$darkFill", "Commerce Intelligence", "$onDark", 14, True),
           plate(5, "Tracking", ["Share of Search", "Share of Shelf", "Availability Monitoring", "Pricing Intelligence", "Competitor Monitoring"]),
           plate(175, "Insights", ["SKU-level performance", "City-level opportunity mapping", "Platform-wise growth pockets", "Category trends"])]
    return layer(340, 380, "".join(out))


def slide_f(t: dict) -> str:
    return slide(t, header("F · Hub / engine", "One engine connects every platform, signal and lever",
                           "Code places the nodes from the plan (centre, satellites, inputs, outputs) and draws the connectors: replaces free <Layer> drawing (XTSY 1, 5, 6).")
                 + row(panel("radial", 'variant="radial"', "XTSY 1: ecosystem", hub_radial(t)),
                       panel("engine", 'variant="engine"', "XTSY 6: input → engine → levers → outcome", hub_engine(t)),
                       panel("grouped", 'variant="grouped"', "XTSY 5: centre + two capability panels", hub_grouped(t))))


# ── G. swimlane roadmap ──────────────────────────────────────────────────────

PHASES = [("Days 0–7", "Stabilize", 0, 7), ("Days 8–30", "Rebuild", 8, 30), ("Days 31–90", "Scale", 31, 90)]
LANES = [("Platform B", [["Pause or negative 10+ click zero-sales terms", "Reduce bids on ROAS <0.25x", "Cap SD, AMC, weak category/competitor"], [], []]),
         ("Platform A", [["Cap CPD/BOTD unless awareness is objective", "Reduce weak phrase/broad bids", "Identify low-ROAS city/SKU combinations"], [], []]),
         ("Both", [["Protect brand and exact winners"],
                   ["Restructure by intent, SKU, city, objective", "Move converting terms into exact", "Add negatives; budget tiers; CPC ceilings"],
                   ["Increase budgets on high-CVR/ROAS clusters", "Test bundles for AOV", "SBT/SBV/video tests on proven demand"]])]


def lane_grid(t: dict) -> str:
    head = (f'<HStack gap="6"><VStack w="96" />'
            + "".join(f'<VStack w="1" grow="1" padding="8" backgroundColor="{"$darkFill" if i == 0 else "$panelFill"}">'
                      f'<Text fontFamily="{SANS}" fontSize="13" bold="true" color="{"$onDark" if i == 0 else "$textMain"}">{d}  ·  {p}</Text></VStack>'
                      for i, (d, p, _, _) in enumerate(PHASES)) + "</HStack>")
    rows = []
    for lane, cells in LANES:
        cs = "".join(f'<VStack w="1" grow="1" padding="8" gap="3" border.color="$border" border.width="1">'
                     + ("".join(f'<Text fontFamily="{SANS}" fontSize="12" color="$textMain">• {esc(c)}</Text>' for c in cell)
                        or f'<Text fontFamily="{SANS}" fontSize="12" color="$border">—</Text>') + "</VStack>"
                     for cell in cells)
        rows.append(f'<HStack gap="6" alignItems="stretch"><VStack w="96" justifyContent="center">{label(lane, "$accentInk", 11)}</VStack>{cs}</HStack>')
    return f'<VStack gap="6">{head}{"".join(rows)}</VStack>'


def gantt(t: dict) -> str:
    W, x0, span = 1100, 110, 960
    s = span / 90
    out = [line(t, x0, 20, x0 + span, 20, "border", 1)]
    for d in (0, 7, 30, 90):
        out.append(line(t, x0 + d * s, 14, x0 + d * s, 26, "textMuted", 1))
        out.append(ltext(x0 + d * s - 30, 0, 60, f"Day {d}", 11, "$textMuted", False, "center"))
    for i, (d, p, a, b) in enumerate(PHASES):
        y = 36 + i * 32
        out.append(ltext(0, y + 4, 100, p, 13, "$textMain", True, "right"))
        out.append(box(x0 + a * s, y, max((b - a) * s, 4), 24, "$accent" if i == 0 else mix(t["accent"], t["surface"], 0.55)))
        out.append(ltext(x0 + b * s + 8, y + 4, 200, f"{d}", 12, "$textMuted"))
    return layer(W, 136, "".join(out))


def slide_g(t: dict) -> str:
    return slide(t, header("G · Swimlane roadmap", "First stop leakage, then rebuild, then scale where economics prove out",
                           "Phases × lanes from the plan (agency 30/60/90): today the platform lanes are flattened into step cards.")
                 + col(panel("lanes", 'variant="lanes"', "phases as columns, platforms as rows", lane_grid(t), 'grow="1"'),
                       panel("gantt", 'variant="gantt"', "bars to time scale: Stabilize is one week of ninety days", gantt(t), 'h="190"')))


# ── H + I. glyphs, scorecard, heat grid ──────────────────────────────────────

def harvey(t: dict, k: int) -> str:
    """Harvey ball as a glyph (<Svg> did not render in this deck): 0-4 quarters."""
    return f'<Text fontSize="24" color="$textMain" textAlign="center">{"○◔◑◕●"[k]}</Text>'


def indicators(t: dict) -> str:
    items = ["Category Visibility", "Search Share", "Sponsored Placement Share", "New Consumer Acquisition",
             "Repeat Purchase Rate", "Market Share", "Sales Velocity"]
    rows = "".join(f'<HStack gap="10" alignItems="center"><Shape shapeType="upArrow" w="16" h="18" fill.color="$positive" />'
                   f'<Text fontFamily="{SANS}" fontSize="14" color="$textMain">{i}</Text></HStack>' for i in items)
    return f'<VStack gap="10">{rows}</VStack>'


def scorecard(t: dict) -> str:
    deals = [("Globex Corp", "$1.2M", "Negotiation", "Champion left"), ("Initech", "$890K", "Proposal", "Budget freeze"),
             ("Umbrella Inc", "$740K", "Discovery", "Competitor POC"), ("Wayne Enterprises", "$680K", "Negotiation", "Legal review stalled"),
             ("Stark Industries", "$520K", "Proposal", "Timeline slip to Q1")]
    def td(s, color="$textMain", bold=False, size=13):
        return f'<Td fontFamily="{SANS}" fontSize="{size}" color="{color}" bold="{"true" if bold else "false"}">{esc(s)}</Td>'
    head = "<Tr>" + "".join(td(h, "$textMuted", True, 11) for h in ("DEAL", "VALUE", "STAGE", "RISK")) + "</Tr>"
    body = "".join("<Tr>" + td(n, bold=True) + td(v) + td(s) + f'<Td fontFamily="{SANS}" fontSize="13" color="$textMain">'
                   f'<Span color="$negative">●</Span>  {esc(r)}</Td></Tr>' for n, v, s, r in deals)
    return (f'<Table defaultRowHeight="40" cellBorder.color="{t["border"]}" cellBorder.width="1">'
            f'<Col width="124" /><Col width="62" /><Col width="90" /><Col width="140" />{head}{body}</Table>')


def heat(t: dict) -> str:
    rows_ = ["Visibility", "Conversion", "Repeat Purchase", "Market Expansion"]
    levels = [[4, 3, 2], [2, 3, 3], [1, 2, 3], [3, 1, 2]]          # illustrative: the brief gives no levels
    head = (f'<HStack gap="4"><VStack w="104" />' + "".join(
        f'<Text w="1" grow="1" fontFamily="{MONO}" fontSize="11" color="$textMuted" textAlign="center">{p}</Text>'
        for p in ("ZEPTO", "BLINKIT", "INSTAMART")) + "</HStack>")
    rows = []
    for r, lv in zip(rows_, levels):
        cells = "".join(f'<HStack w="1" grow="1" h="44" justifyContent="center" alignItems="center" '
                        f'backgroundColor="{mix(t["accent"], t["surface"], 0.92 - k * 0.14)}">{harvey(t, k)}</HStack>' for k in lv)
        rows.append(f'<HStack gap="4" alignItems="center"><Text w="104" fontFamily="{SANS}" fontSize="12" bold="true" '
                    f'color="$textMain">{r}</Text>{cells}</HStack>')
    return f'<VStack gap="4">{head}{"".join(rows)}</VStack>'


def slide_h(t: dict) -> str:
    return slide(t, header("H + I · Status glyphs and heat grid", "Direction, status and level as marks, not paragraphs",
                           "One glyph set (arrow, RAG dot, Harvey ball) for tables and lists. Levels come from the brief, or are proposed by the planner and flagged.")
                 + row(panel("indicators", 'variant="indicators"', "XTSY 7: arrows, no numbers", indicators(t), 'w="6" grow="6"'),
                       panel("scorecard", 'variant="scorecard"', "sales: deals at risk, status dot", scorecard(t), 'w="8" grow="8"'),
                       panel("heat", 'variant="heat"', "XTSY 3 · LEVELS ILLUSTRATIVE (not in brief)", heat(t), 'w="7" grow="7"')))


# ── J + K + M. equation, chips, statement ────────────────────────────────────

def equation(t: dict) -> str:
    def term(lab, val, fill="$panelFill", c="$textMain"):
        return (f'<VStack w="1" grow="1" padding="12" gap="2" backgroundColor="{fill}" alignItems="center">'
                f'{label(lab, "$textMuted" if fill == "$panelFill" else c, 11)}{number(val, 30, c)}</VStack>')
    def op(s):
        return f'<Text fontFamily="{SANS}" fontSize="26" color="$textMuted">{s}</Text>'
    allow = 195 * 0.055
    return (f'<HStack gap="10" alignItems="center">{term("AOV", "₹195")}{op("×")}{term("CVR", "5.5%")}{op("=")}'
            f'{term("Allowable CPC", f"₹{allow:.1f}", "$accentTint", "$textMain")}{op("vs")}'
            f'{term("Actual CPC", "₹31.1", "$negativeTint", "$negativeInk")}</HStack>'
            f'<Text fontFamily="{SANS}" fontSize="13" color="$textMuted">FLIPCART · actual is {31.1 / allow:.1f}× what AOV and CVR support (result computed by code)</Text>')


def chips(t: dict) -> str:
    groups = [("Winners", "$positiveTint", "$positiveInk", ["[Brand] phrase", "[Brand] exact", "paneer makhani", "curry", "shahi paneer gravy"]),
              ("Weak terms", "$negativeTint", "$negativeInk", ["butter chicken phrase", "instant food phrase", "ready to cook paneer phrase",
                                                                 "mix phrase", "instant gravy broad", "ready masala", "instant dal makhani",
                                                                 "meat masala", "kilrr chicken masala"]),
              ("Cities to review", "$panelFill", "$textMain", ["Hyderabad", "Chennai", "Jaipur", "Sas Nagar", "Surat", "Nashik", "Mumbai", "Delhi"])]
    out = []
    for g, fill, ink, terms in groups:
        lines, cur, used = [], [], 0
        for c in terms:                      # wrap by estimated width: POM's flexWrap shrinks instead of wrapping
            w = len(c) * 7 + 22
            if cur and used + w > 800:
                lines.append(cur); cur, used = [], 0
            cur.append(c); used += w + 6
        lines.append(cur)
        rows_ = "".join('<HStack gap="6">' + "".join(
            f'<VStack padding="5" backgroundColor="{fill}"><Text fontFamily="{SANS}" fontSize="12" color="{ink}">{esc(c)}</Text></VStack>'
            for c in ln) + "</HStack>" for ln in lines)
        out.append(f'<VStack gap="5">{label(g, "$textMuted", 11)}{rows_}</VStack>')
    return f'<VStack gap="10">{"".join(out)}</VStack>'


def statement(t: dict) -> str:
    return (f'<VStack grow="1" padding="26" gap="12" backgroundColor="$darkFill" justifyContent="center">'
            f'<Text fontFamily="{SANS}" fontSize="54" bold="true" color="$accentOnDark" lineHeight="0.8">“</Text>'
            f'<Text fontFamily="{SANS}" fontSize="24" bold="true" color="$onDark" lineHeight="1.25">The current account needs a sharper operator, not just more spend.</Text>'
            f'{label("Next step · 30-day transition audit", "$accentOnDark", 11)}</VStack>')


def slide_j(t: dict) -> str:
    return slide(t, header("J + K + M · Equation, chips, statement", "Small components that carry an argument",
                           "Formula from the brief with the result computed; short-term lists as toned chips (wrapChipRows exists); the closing line at slide scale.")
                 + row(col(panel("equation", 'variant="strip"', "CHEFFIN: allowable CPC = AOV × CVR", equation(t), 'h="170"'),
                           panel("chips", 'variant="chips"', "agency slide 2: term lists", chips(t), 'grow="1"'), grow='w="13" grow="13"'),
                       panel("statement", 'variant="statement"', "agency 6: closing line", statement(t), 'w="7" grow="7"', pad=0)))


# ── build ────────────────────────────────────────────────────────────────────

SLIDES = [slide_a, slide_b, slide_c, slide_d, slide_e, slide_f, slide_g, slide_h, slide_j]


def build(out: Path, palette: str, png: bool) -> Path:
    t = tokens(palette)
    out.mkdir(parents=True, exist_ok=True)
    parts, failed = [], []
    for i, make in enumerate(SLIDES, 1):
        xml = out / f"slide-{i}.xml"
        xml.write_text(make(t), encoding="utf-8")
        build_dir = out / f"build-{i}"
        subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(xml), str(build_dir)],
                       check=False, capture_output=True, env={**os.environ, "POM_FIT_GROW": "0"})
        result = json.loads((build_dir / "compile-result.json").read_text(encoding="utf-8"))
        if result["status"] != "success":
            failed.append((i, result.get("diagnostics") or result.get("error")))
            continue
        parts.append(build_dir / "presentation.pptx")
    if failed:
        raise RuntimeError("\n".join(f"slide {i}: {d}" for i, d in failed))
    deck = merge_pptx_files(parts, out / f"component-candidates-{palette}.pptx")
    embed_deck_fonts(deck)
    if png:
        from src.compiler.screenshot import render_screenshots
        res = render_screenshots(str(deck), str(out / "png"))
        if not res.ok:
            raise RuntimeError(f"screenshots failed: {res.error}")
    return deck


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--palette", default="corporate-slate")
    ap.add_argument("--out", default="output/component-candidates")
    ap.add_argument("--png", action="store_true")
    args = ap.parse_args()
    print(build(ROOT / args.out, args.palette, args.png))


if __name__ == "__main__":
    main()
