"""Can today's planner JSON draw every variant of the left blocks? LLM-free check for
docs/derived-nodes-spec-left-blocks.md (callout, header, table, chart, bullet list, timeline, process arrow, flow).

    python -m scripts.left_blocks_gallery                       # corporate-slate
    python -m scripts.left_blocks_gallery --palettes graphite-dark --only chart

Each variant is written here by hand as the XML a node would expand to, built ONLY from a sample component in
today's typed planner schema (`planner_schema_typed.content_from_data` validates every sample first), so a variant
that needs a field the plan lacks shows up as a gap. step_cards draw through the real card code (<CardGrid ref>,
layout steps). Chart `labelled` / `focus_label` / `horizontal` edit the compiled .pptx chart XML (data labels, bar
direction), the chart pass's option B. Then the real pipeline: normalize_xml, compile-pom.js with fit-grow, the
Inter LibreOffice render. Writes <out>/<palette>-<block>.png sheets.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import tile_gallery as TG  # noqa: E402  (sets POM_BLOCKS=tiles: CardGrid expands)
from scripts.kpi_gallery import sheet  # noqa: E402
from src.agents.planner_schema_typed import content_from_data  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import native  # noqa: E402

OUT = ROOT / "output" / "left-blocks-gallery"
X = native.x

# ── sample components (synthetic BREWLY content, typed schema) ─────────────────

def comp(cid: str, kind: str, cd: dict, hint: str = "", **kw) -> dict:
    content_from_data(kind, cd)   # raises when the sample is not today's schema
    return {"component_id": cid, "kind": kind, "content_data": cd, "design_hint": hint, "weight": "hero", **kw}


TAKEAWAY = comp("takeaway", "narrative", {"text": "Quick commerce now brings 41% of new buyers, so the H2 budget follows it."})
QUOTE = comp("voice", "narrative", {"text": "“We reorder every week now that delivery takes ten minutes.” — Store manager, Pune"})
TITLE = comp("title", "title", {"title": "Quick commerce carried H1 growth", "subtitle": "Revenue ₹48.2 Cr (+38%), ROAS 4.1x, 41% of new buyers"})
KICKER = "PERFORMANCE"
TABLE = comp("channels", "table", {"table_columns": ["Channel", "Spend", "ROAS", "Orders", "Share of new buyers"],
                                    "table_rows": [["Blinkit", "₹6.2 Cr", "4.8x", "1.92 L", "22%"],
                                                   ["Zepto", "₹4.1 Cr", "4.1x", "1.10 L", "12%"],
                                                   ["Instamart", "₹3.9 Cr", "2.6x", "0.71 L", "7%"],
                                                   ["Amazon", "₹5.4 Cr", "3.9x", "1.35 L", "9%"],
                                                   ["Website", "₹2.2 Cr", "3.2x", "0.48 L", "4%"]]},
              "highlight Instamart, the weakest ROAS", columns=5, rows=5)
CHART = comp("rev_chart", "chart", {"chart_title": "Revenue by quarter (₹ Cr)",
                                    "chart_labels": ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25", "Q1 FY26", "Q2 FY26"],
                                    "chart_values": [6.1, 6.8, 7.4, 8.2, 9.3, 10.4]}, chart_type="bar", series_count=1)
CHART_LONG = comp("city_chart", "chart", {"chart_title": "ROAS by city",
                                          "chart_labels": ["Bengaluru Urban", "Hyderabad Metro", "Mumbai Suburban",
                                                           "Delhi NCR (East)", "Pune City"],
                                          "chart_values": ["2.6x", "4.3x", "3.8x", "3.1x", "4.9x"]}, chart_type="bar")
BULLETS = comp("actions", "bullet_list", {"bullets": [
    "Scale exact match: the winners already return 5.6x",
    "Cut phrase and broad leakage: 38% of spend, 0.4x return",
    "Cap competitor terms at ₹2 L a month",
    "Shift Bengaluru budget to Hyderabad, where CPC is ₹12.7 not ₹19.3",
    "Review ROAS by city every Monday",
    "Brief the agency on the new budget rules"]}, items=6)
ICONS = ["target", "scissors", "wallet", "truck", "calendar", "users"]   # the LLM's `icon` per point (no plan field)
TIMELINE = comp("roadmap", "timeline", {"direction": "horizontal", "timeline_items": [
    {"date": "Jul–Aug", "label": "Growth activation", "description": "Search scaling, placement expansion"},
    {"date": "Sep–Oct", "label": "Festive push", "description": "Bundles, competitor conquesting"},
    {"date": "Nov", "label": "Post-festive retention", "description": "Retarget new-to-brand buyers"},
    {"date": "Dec", "label": "Year-end consolidation", "description": "Finalise the H1 '27 plan"}]},
               "highlight Nov, where we are now", items=4, orientation="horizontal")
STEPS_SHORT = comp("gtm", "process_arrow", {"direction": "horizontal", "process_steps": [
    "Visibility", "Consideration", "Conversion", "Repeat", "Profitability"]}, items=5)
STEPS_DETAIL = comp("phases", "process_arrow", {"direction": "horizontal", "process_steps": [
    "Audit — map spend, ROAS and gaps by city",
    "Fix — stop phrase and broad leakage",
    "Scale — move budget to exact winners",
    "Expand — new cities and new-to-brand buyers"]}, items=4)
FLOW = comp("checkout", "flow", {"direction": "horizontal", "flow_steps": [
    "Search", "Product page", "Add to cart", "Checkout", "Delivered in 10 min"]}, items=5)

SEP = re.compile(r"\s+—\s+|:\s+")


def split(s: str) -> tuple[str, str]:
    """'Head — detail' / 'Head: detail' -> (head, detail); every word kept (spec §2.1, Q7)."""
    parts = SEP.split(s, maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 else (s, "")


# ── variant builders: (component(s), body XML) ─────────────────────────────────

def callout(v: str, c: dict = TAKEAWAY) -> str:
    t = X(c["content_data"]["text"])
    if v == "tinted":
        return f'<VStack backgroundColor="$accentSoft" borderLeft.color="$accent" borderLeft.width="4" padding="28"><Text fontSize="24" color="$textMain">{t}</Text></VStack>'
    if v == "rule":
        return f'<VStack borderLeft.color="$accent" borderLeft.width="4" padding="8" padding.left="24"><Text fontSize="24" color="$textMain">{t}</Text></VStack>'
    if v == "dark":
        return f'<VStack backgroundColor="$panelDark" padding="32"><Text fontSize="24" bold="true" color="$onPanelDark">{t}</Text></VStack>'
    if v == "quote":
        q, who = (c["content_data"]["text"].rsplit(" — ", 1) + [""])[:2]
        return (f'<VStack backgroundColor="$surfaceAlt" padding="32" gap="4"><Text fontSize="72" bold="true" color="$accent" lineHeight="1">“</Text>'
                f'<Text fontSize="26" italic="true" color="$textMain">{X(q.strip("“”"))}</Text>'
                + (f'<Text fontSize="16" color="$textMuted">— {X(who)}</Text>' if who else "") + "</VStack>")
    return f'<Text fontSize="22" color="$textMain">{t}</Text>'   # plain


def beside_chart(callout_xml: str) -> str:
    """A callout as the LLM places it: a takeaway column beside the slide's chart."""
    return (f'<HStack grow="1" gap="24" alignItems="stretch"><VStack w="62%" alignItems="stretch">{native.chart(CHART, {"grow": "1"}, {})}</VStack>'
            f'<VStack grow="1" justifyContent="center">{callout_xml}</VStack></HStack>')


def header(v: str) -> str:
    cd = TITLE["content_data"]
    k, h, s = X(KICKER), X(cd["title"]), X(cd["subtitle"])
    ink, sub = ("$onPanelDark", "$onPanelDark") if v == "inverted" else ("$textMain", "$textMuted")
    kc = "$onPanelDark" if v == "inverted" else "$accentText"
    inner = (f'<Text fontSize="14" bold="true" letterSpacing="2" color="{kc}">{k}</Text>'
             f'<Text fontSize="36" bold="true" color="{ink}" lineHeight="1.15">{h}</Text>')
    if v == "ruled":
        inner += '<Shape shapeType="rect" w="96" h="4" fill.color="$accent" />'
    inner += f'<Text fontSize="18" color="{sub}">{s}</Text>'
    head = (f'<VStack backgroundColor="$panelDark" padding="48" gap="10">{inner}</VStack>' if v == "inverted"
            else f'<VStack padding="48" padding.bottom="0" gap="10">{inner}</VStack>')
    body = f'<VStack grow="1" padding="48" padding.top="24">{native.table(TABLE, {"w": "max"}, {})}</VStack>'
    return f'<Slide><VStack w="1280" h="720" alignItems="stretch" backgroundColor="$surface">{head}{body}</VStack></Slide>'


def table(v: str, c: dict = TABLE) -> str:
    cd = c["content_data"]
    cols, rows = cd["table_columns"], cd["table_rows"]
    focus = next((i for i, r in enumerate(rows) if r[0].lower() in c["design_hint"].lower()), None)   # one_singled_out
    num = [i > 0 and all(native._numeric(r[i]) for r in rows) for i in range(len(cols))]

    def td(val: str, i: int, head: bool, r: int = -1) -> str:
        a = {"fontSize": "18", "color": "$textMain"}
        if num[i]:
            a["textAlign"] = "right"
        if head:
            a["bold"] = "true"
            if v in ("plain", "zebra", "highlight_row"):
                a["backgroundColor"] = "$surfaceAlt"
            if v == "dark_header":
                a.update(backgroundColor="$panelDark", color="$onPanelDark")
        else:
            if v == "zebra" and r % 2 == 1:
                a["backgroundColor"] = "$surfaceAlt"
            if v == "highlight_row" and r == focus:
                a["backgroundColor"] = "$negativeSoft"
                if i == 0:
                    a.update(color="$negativeText", bold="true")
            if v == "dark_header" and i == 0:
                a.update(color="$accentText", bold="true")
        return "<Td" + "".join(f' {k}="{X(x)}"' for k, x in a.items()) + f">{X(val)}</Td>"

    out = f'<Table cellBorder.color="$border" cellBorder.width="1" w="max">' + "<Col />" * len(cols)
    out += "<Tr>" + "".join(td(h, i, True) for i, h in enumerate(cols)) + "</Tr>"
    out += "".join("<Tr>" + "".join(td(x, i, False, r) for i, x in enumerate(row)) + "</Tr>" for r, row in enumerate(rows))
    return out + "</Table>"


def chart(v: str) -> str:
    c = CHART_LONG if v == "horizontal" else CHART
    n = len(c["content_data"]["chart_labels"])
    xml = native.chart(c, {"w": "max"}, {})
    # the chart pass focus rule: one hue, the latest period in $accent (one series: colours per point)
    xml = re.sub(r'chartColors="[^"]*"', 'chartColors="' + X(json.dumps(["$neutral"] * (n - 1) + ["$accent"])) + '"', xml)
    return xml


def post_chart(pptx: Path, v: str) -> list[str]:
    """Edit the compiled chart XML: data labels on every bar (labelled) or the focus bar (focus_label), bars turned
    (horizontal). Returns what it changed."""
    if v not in ("labelled", "focus_label", "horizontal"):
        return []
    tmp = pptx.with_suffix(".tmp")
    done = []
    with zipfile.ZipFile(pptx) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"ppt/charts/chart\d+\.xml$", item.filename):
                s = data.decode("utf-8")
                s0 = s
                lbl = ('<c:numFmt formatCode="General" sourceLinked="0"/><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>'
                       '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1400" b="1"><a:solidFill>'
                       '<a:srgbClr val="1E293B"/></a:solidFill></a:defRPr></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>'
                       '<c:dLblPos val="outEnd"/><c:showLegendKey val="0"/><c:showVal val="1"/><c:showCatName val="0"/>'
                       '<c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/>')
                if v in ("labelled", "horizontal"):
                    new = f"<c:dLbls>{lbl}</c:dLbls>"
                else:   # one label: the last point
                    n = len(re.findall(r"<c:pt idx=", s.split("<c:val>", 1)[1].split("</c:val>", 1)[0]))
                    new = (f'<c:dLbls><c:dLbl><c:idx val="{n - 1}"/>{lbl}</c:dLbl>'
                           '<c:showLegendKey val="0"/><c:showVal val="0"/><c:showCatName val="0"/><c:showSerName val="0"/>'
                           '<c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbls>')
                s = re.sub(r"<c:dLbls>.*?</c:dLbls>(?=\s*<c:cat>)", "", s, flags=re.S)   # pptxgenjs's own, if any
                s = s.replace("<c:cat>", new + "<c:cat>", 1)
                s = re.sub(r'(<c:valAx>.*?<c:delete val=")0(")', r"\g<1>1\2", s, count=1, flags=re.S)   # labels replace the axis
                if v == "horizontal":
                    s = s.replace('<c:barDir val="col"/>', '<c:barDir val="bar"/>')
                    s = re.sub(r'(<c:catAx>.*?<c:orientation val=")minMax(")', r"\g<1>maxMin\2", s, count=1, flags=re.S)
                if s != s0:
                    done.append(item.filename)
                data = s.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(pptx)
    return done


def bullets(v: str) -> str:
    bl = BULLETS["content_data"]["bullets"]
    if v == "plain":
        return native.ul(BULLETS, {"fontSize": "22", "lineHeight": "1.5"}, {})
    if v == "lead":
        rows = []
        for b in bl:
            h, d = split(b)
            rows.append(f'<Text fontSize="22" color="$textMain"><B>{X(h)}</B>{": " + X(d) if d else ""}</Text>')
        return '<VStack gap="14">' + "".join(rows) + "</VStack>"
    if v == "icon":
        return ('<VStack gap="16">' + "".join(
            f'<HStack gap="14" alignItems="center"><Icon name="{ic}" size="24" color="$accent" variant="circle-filled" bgColor="$accentSoft" />'
            f'<Text fontSize="22" color="$textMain">{X(b)}</Text></HStack>' for ic, b in zip(ICONS, bl)) + "</VStack>")
    if v == "tiles":
        tiles = [f'<VStack w="1" grow="1" backgroundColor="$surfaceAlt" padding="20" gap="8"><Icon name="{ic}" size="24" color="$accentText" />'
                 f'<Text fontSize="20" color="$textMain">{X(b)}</Text></VStack>' for ic, b in zip(ICONS, bl)]
        return ('<VStack grow="1" gap="16">' + "".join(f'<HStack grow="1" gap="16" alignItems="stretch">{"".join(tiles[i:i + 3])}</HStack>'
                                                        for i in range(0, len(tiles), 3)) + "</VStack>")
    half = (len(bl) + 1) // 2   # columns
    col = lambda part: native.ul({"content_data": {"bullets": part}}, {"fontSize": "22", "lineHeight": "1.5", "w": "1", "grow": "1"}, {})
    return f'<HStack gap="40">{col(bl[:half])}{col(bl[half:])}</HStack>'


def _focus(c: dict, labels: list[str]) -> int | None:
    h = c["design_hint"].lower()
    return next((i for i, l in enumerate(labels) if l.lower().split()[0] in h), None)


def timeline(v: str) -> str:
    items = TIMELINE["content_data"]["timeline_items"]
    now = _focus(TIMELINE, [i["date"] for i in items])
    if v in ("rail", "vertical"):
        its = "".join(f'<TimelineItem date="{X(i["date"])}" title="{X(i["label"])}" description="{X(i["description"])}" '
                      f'color="{"$accent" if k == now else "$neutral"}" />' for k, i in enumerate(items))
        d = "vertical" if v == "vertical" else "horizontal"
        return (f'<Timeline direction="{d}" dateColor="$accentText" titleColor="$textMain" descriptionColor="$textMuted" '
                f'connectorColor="$border" w="max" h="max">{its}</Timeline>')
    if v == "cards":
        cols = []
        for k, i in enumerate(items):
            dot = "$accent" if k == now else "$neutral"
            dark = k == now
            cols.append(
                f'<VStack w="1" grow="1" gap="14" alignItems="stretch">'
                f'<HStack alignItems="center" gap="0"><Shape shapeType="ellipse" w="16" h="16" fill.color="{dot}" />'
                f'<Shape shapeType="rect" w="max" grow="1" h="2" fill.color="$border" /></HStack>'
                f'<VStack grow="1" padding="20" gap="6" backgroundColor="{"$panelDark" if dark else "$surface"}" border.color="$border" border.width="1">'
                f'<Text fontSize="14" bold="true" letterSpacing="1" color="{"$onPanelDark" if dark else "$accentText"}">{X(i["date"].upper())}</Text>'
                f'<Text fontSize="22" bold="true" color="{"$onPanelDark" if dark else "$textMain"}">{X(i["label"])}</Text>'
                f'<Text fontSize="17" color="{"$onPanelDark" if dark else "$textMuted"}">{X(i["description"])}</Text></VStack></VStack>')
        return f'<HStack grow="1" gap="16" alignItems="stretch">{"".join(cols)}</HStack>'
    # columns under a segmented progress bar, filled up to "now"
    segs = "".join(f'<Shape shapeType="rect" w="1" grow="1" h="10" fill.color="{"$accent" if now is not None and k <= now else "$border"}" />'
                   for k in range(len(items)))
    cols = "".join(f'<VStack w="1" grow="1" gap="6" padding.top="8"><Text fontSize="14" bold="true" letterSpacing="1" color="$accentText">{X(i["date"].upper())}</Text>'
                   f'<Text fontSize="22" bold="true" color="$textMain">{X(i["label"])}</Text>'
                   f'<Text fontSize="17" color="$textMuted">{X(i["description"])}</Text></VStack>' for i in items)
    return f'<VStack grow="1" gap="18"><HStack gap="6">{segs}</HStack><HStack grow="1" gap="24" alignItems="start">{cols}</HStack></VStack>'


def steps_of(c: dict) -> list[str]:
    cd = c["content_data"]
    return cd.get("process_steps") or cd.get("flow_steps") or []


def numbered(c: dict) -> str:
    st = steps_of(c)
    out = []
    for k, s in enumerate(st):
        h, d = split(s)
        if k:
            out.append('<VStack padding.top="12"><Icon name="arrow-right" size="24" color="$neutral" /></VStack>')
        out.append(f'<VStack w="1" grow="1" gap="10" alignItems="stretch">'
                   f'<HStack justifyContent="center"><Shape shapeType="ellipse" w="48" h="48" fill.color="$accent" text="{k + 1}" fontSize="20" bold="true" color="$onAccent" /></HStack>'
                   f'<VStack grow="1" padding="16" gap="6" border.color="$border" border.width="1" backgroundColor="$surface">'
                   f'<Text fontSize="20" bold="true" color="$textMain" textAlign="center">{X(h)}</Text>'
                   + (f'<Text fontSize="16" color="$textMuted" textAlign="center">{X(d)}</Text>' if d else "") + "</VStack></VStack>")
    return f'<HStack grow="1" gap="8" alignItems="start">{"".join(out)}</HStack>'


def alternating(c: dict) -> str:
    st = steps_of(c)
    cols = []
    for k, s in enumerate(st):
        h, d = split(s)
        txt = (f'<VStack h="120" gap="4" justifyContent="{"end" if k % 2 == 0 else "start"}">'
               f'<Text fontSize="20" bold="true" color="$textMain" textAlign="center">{X(h)}</Text>'
               + (f'<Text fontSize="16" color="$textMuted" textAlign="center">{X(d)}</Text>' if d else "") + "</VStack>")
        empty = '<VStack h="120" />'
        line_l = f'<Shape shapeType="rect" w="max" grow="1" h="3" fill.color="{"$border" if k else "$surface"}" />'
        line_r = f'<Shape shapeType="rect" w="max" grow="1" h="3" fill.color="{"$border" if k < len(st) - 1 else "$surface"}" />'
        dot = f'<Shape shapeType="ellipse" w="40" h="40" fill.color="$accent" text="{k + 1}" fontSize="18" bold="true" color="$onAccent" />'
        cols.append(f'<VStack w="1" grow="1" gap="12" alignItems="stretch">{txt if k % 2 == 0 else empty}'
                    f'<HStack alignItems="center">{line_l}{dot}{line_r}</HStack>{txt if k % 2 else empty}</VStack>')
    return f'<VStack grow="1" justifyContent="center"><HStack gap="0" alignItems="stretch">{"".join(cols)}</HStack></VStack>'


def step_cards(c: dict) -> tuple[dict, str]:
    """Drawn by the real card code: the steps as a card_grid `steps` plan (title, body), destination = last."""
    cards = []
    for s in steps_of(c):
        h, d = split(s)
        cards.append({"title": h, **({"body": d} if d else {})})
    cg = {"component_id": c["component_id"] + "_cards", "kind": "card_grid", "weight": "hero", "design_hint": "",
          "content_data": {"card_layout": "steps", "cards": cards}}
    return cg, f'<CardGrid ref="{cg["component_id"]}" layout="steps" grow="1" />'


def process(v: str) -> tuple[list[dict], str]:
    if v == "chevrons":
        return [STEPS_SHORT], native.process_arrow(STEPS_SHORT, {"w": "max"}, {})
    c = STEPS_SHORT if v == "alternating-short" else STEPS_DETAIL
    if v.startswith("alternating"):
        return [c], alternating(c)
    if v == "numbered":
        return [c], numbered(c)
    cg, xml = step_cards(c)
    return [c, cg], xml


def flow(v: str) -> tuple[list[dict], str]:
    if v == "boxes":
        return [FLOW], native.flow(FLOW, {"w": "max", "h": "max"}, {})
    if v == "numbered":
        return [FLOW], numbered(FLOW)
    cg, xml = step_cards(FLOW)
    return [FLOW, cg], xml


# ── blocks: (variant label, components, body XML or a whole slide) ─────────────

def blocks() -> dict[str, list[tuple[str, list[dict], str]]]:
    return {
        "callout": [(f"callout {v}", [TAKEAWAY], beside_chart(callout(v))) for v in ("tinted", "rule", "dark", "plain")]
        + [("callout quote", [QUOTE], beside_chart(callout("quote", QUOTE)))],
        "header": [(f"header {v}", [TITLE, TABLE], header(v)) for v in ("standard", "inverted", "ruled")],
        "table": [(f"table {v}", [TABLE], table(v)) for v in ("plain", "minimal", "zebra", "highlight_row", "dark_header")],
        "chart": [(f"chart {v}", [CHART_LONG if v == "horizontal" else CHART], chart(v))
                  for v in ("plain", "labelled", "focus_label", "horizontal")],
        "bullets": [(f"bullet_list {v}", [BULLETS], bullets(v)) for v in ("plain", "lead", "icon", "tiles", "columns")],
        "timeline": [(f"timeline {v}", [TIMELINE], timeline(v)) for v in ("rail", "vertical", "cards", "columns")],
        "process": [(f"process_arrow {v}",) + process(v)
                    for v in ("chevrons", "numbered", "alternating", "alternating-short", "step_cards")],
        "flow": [(f"flow {v}",) + flow(v) for v in ("boxes", "numbered", "step_cards")],
    }


def compile_one(d: Path, xml: str, plan: dict, theme: str, variant: str):
    """scripts.card_gallery.compile_one with the chart post-edit between compile and render."""
    from scripts.card_replay import render
    from src.compiler.compiler_client import deck_font
    from src.compiler.nodes import tiles
    from src.compiler.normalizer import ensure_single_theme, normalize_xml
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tiles.xml").write_text(xml, encoding="utf-8")
    from src.compiler.nodes import charts
    drawn = charts.expand(xml, plan)   # <Chart ref> composition tags (POM_NODES=chart); a no-op without them
    res = tiles.fill(drawn["xml"], plan)
    issues = [i["code"] for i in drawn["issues"] + res["issues"] if i["severity"] == "error"]
    norm = normalize_xml(deck_font(res["xml"]))
    xml = ensure_single_theme(norm["cleaned_xml"], theme)
    (d / "in.xml").write_text(xml, encoding="utf-8")
    p = subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    (d / "compile.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    pptx = d / "presentation.pptx"
    if pptx.exists():
        issues += [f"post:{f}" for f in post_chart(pptx, variant)]
    return render(d), issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--palettes", nargs="*", default=["corporate-slate"])
    ap.add_argument("--only", nargs="*", default=[], help="blocks to draw (callout header table chart bullets timeline process flow)")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    for pal in a.palettes:
        theme = resolve_theme(pal)["element"]
        for name, rows in blocks().items():
            if a.only and name not in a.only:
                continue
            shots = []
            for label, comps, body in rows:
                xml = body if body.startswith("<Slide") else TG.slide(KICKER, label, body)
                d = a.out / pal / f"{name}-{len(shots)}"
                pdf, issues = compile_one(d, xml, {"components": comps}, theme, label.split()[-1])
                shots.append((label, pdf))
                print(f"{pal} {label}: {'ok' if pdf else 'NO RENDER'} {issues or ''}")
            sheet(shots, a.out / f"{pal}-{name}.png", cols=3)
            print(a.out / f"{pal}-{name}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
