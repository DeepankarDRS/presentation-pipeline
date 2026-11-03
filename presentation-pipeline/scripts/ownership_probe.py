"""Who owns what, free probe (docs/composition-convention-spec.md §12): hand-written slides that mix the three layers.

    python -m scripts.ownership_probe            # every case, corporate-slate
    python -m scripts.ownership_probe --only c d

Layer 1 = native POM nodes the LLM writes itself, layer 2 = composition nodes (<Tag ref variant>) code draws from
the plan, layer 3 = the LLM's free XML around them (layout, header, decor / arrow layers). Each slide goes the
validator's way (src/agents/validator.py): composed.expand -> tiles.fill -> deck font -> normalize -> compile-pom.js
(fit-grow, pptx-post) -> LibreOffice with Inter. Cases:
  a  KpiRow + Chart refs inside LLM stacks, with styling attributes
  b  a Table ref beside an LLM-drawn native ProcessArrow
  c  an LLM arrow layer over ref-drawn blocks: Lines at the pixels of the un-grown layout (fit-grow off), then the
     same slide with fit-grow on; and POM's own <Arrow from to> anchored to code-written ids. Measured in the pptx.
  d  a ref inside an LLM card; refs written inside another ref
  e  content attributes the LLM must not set
Writes output/ownership-probe/<case>/ (tiles.xml = what the LLM wrote, in.xml, compile-result.json, issues.json) and
docs/eval/ownership-probe/{sheet.png, results.json}.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import composition_convention as CC  # noqa: E402
from scripts import composition_gallery_left as CL  # noqa: E402
from scripts import composition_test as CT  # noqa: E402
from scripts import tile_gallery as TG  # noqa: E402
from scripts.card_replay import render  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import composed, tiles  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

os.environ["POM_BLOCKS"] = "tiles"
os.environ["POM_NODES"] = "kpi_row,card_grid,chart,table,timeline,process_arrow,flow"   # set after the imports

OUT = ROOT / "output" / "ownership-probe"
DOCS = ROOT / "docs" / "eval" / "ownership-probe"
KPIS, CARDS, CHART, TABLE = CC.KPIS, CC.CARDS, CL.CHART, CL.TABLE
EMU = 9525   # per px


def compile_slide(d: Path, xml: str, comps: list[dict], theme: str) -> dict:
    """The validator's order on one slide; every issue kept (all severities) and the compile result."""
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tiles.xml").write_text(xml, encoding="utf-8")
    plan = {"components": comps}
    drawn = composed.expand(xml, plan)
    filled = tiles.fill(drawn["xml"], plan)
    node_issues = drawn["issues"] + filled["issues"]
    norm = normalize_xml(deck_font(filled["xml"]))
    (d / "in.xml").write_text(ensure_single_theme(norm["cleaned_xml"], theme), encoding="utf-8")
    p = subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    (d / "compile.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    res = json.loads((d / "compile-result.json").read_text(encoding="utf-8")) if (d / "compile-result.json").exists() else {}
    out = {"node_ok": drawn["ok"] and filled["ok"],
           "node_issues": [{k: i.get(k) for k in ("code", "severity", "ref", "message")} for i in node_issues],
           "normalize": sorted({i["code"] for i in norm["issues"]}),
           "compiled": res.get("status") == "success" and (d / "presentation.pptx").exists(),
           "compile_errors": [x.get("type") or x.get("code") for x in res.get("diagnostics") or []],
           "warnings": sorted({w.get("code") for w in res.get("warnings") or []}),
           "fitGrow": res.get("fitGrow") or []}
    (d / "issues.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    out["pdf"] = render(d)
    return out


# ── pptx geometry: where things landed (EMU -> px) ───────────────────────────────────────────────────────────────

_SP = re.compile(r"<p:(sp|cxnSp)\b.*?</p:\1>", re.S)
_OFF = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>')


def shapes(pptx: Path) -> list[dict]:
    with zipfile.ZipFile(pptx) as z:
        x = z.read("ppt/slides/slide1.xml").decode("utf-8")
    out = []
    for m in _SP.finditer(x):
        g = _OFF.search(m.group(0))
        if not g:
            continue
        a, b, w, h = (int(v) / EMU for v in g.groups())
        flip = m.group(0)
        kind = "line" if m.group(1) == "cxnSp" or 'prst="line"' in flip else "sp"
        out.append({"kind": kind, "x": a, "y": b, "w": w, "h": h,
                    "flipH": 'flipH="1"' in flip, "flipV": 'flipV="1"' in flip,
                    "text": "".join(re.findall(r"<a:t>([^<]*)</a:t>", m.group(0)))})
    return out


def box_of(sh: list[dict], text: str) -> dict:
    return next(s for s in sh if s["kind"] == "sp" and s["text"].strip() == text)


def centre(s: dict) -> tuple[float, float]:
    return s["x"] + s["w"] / 2, s["y"] + s["h"] / 2


def ends(line: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    x1, x2 = (line["x"] + line["w"], line["x"]) if line["flipH"] else (line["x"], line["x"] + line["w"])
    y1, y2 = (line["y"] + line["h"], line["y"]) if line["flipV"] else (line["y"], line["y"] + line["h"])
    return (x1, y1), (x2, y2)


def dist(p: tuple[float, float], q: tuple[float, float]) -> float:
    return ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5


def miss(pt: tuple[float, float], s: dict) -> float:
    """px from a point to a box (0 = on or inside it)."""
    dx = max(s["x"] - pt[0], 0, pt[0] - s["x"] - s["w"])
    dy = max(s["y"] - pt[1], 0, pt[1] - s["y"] - s["h"])
    return round((dx * dx + dy * dy) ** 0.5, 1)


# ── the slides ───────────────────────────────────────────────────────────────────────────────────────────────────

def slide(head: str, body: str, extra: str = "", fit_off: bool = False) -> str:
    """tile_gallery.slide plus an optional overlay (extra) on the slide root, absolutely positioned."""
    x = TG.slide("OWNERSHIP PROBE", head, body)
    if extra:
        x = x.replace("</VStack></VStack></Slide>", f"</VStack>{extra}</VStack></Slide>")
    return ("<!-- fit-grow: off -->" if fit_off else "") + x


def case_a() -> list[tuple]:
    body = ('<HStack grow="1" gap="20" alignItems="stretch">'
            '<VStack w="1" grow="1" gap="12" padding="20" backgroundColor="$surfaceAlt" borderRadius="12">'
            '<Text fontSize="15" bold="true" color="$accentText" letterSpacing="1">WHERE WE STAND</Text>'
            '<KpiRow ref="kpis" variant="rows" grow="1" item.borderLeft.color="$tone" item.borderLeft.width="4" '
            'value.color="$toneText" label.color="$textMuted" /></VStack>'
            '<VStack w="1" grow="1" gap="10">'
            '<Chart ref="roas" variant="native labelled" grow="1" backgroundColor="$surface" border.color="$border" '
            'border.width="1" borderRadius="12" padding="16" label.color="$accentText" />'
            '<Text fontSize="16" color="$textMuted">Generic search: the largest pool, the lowest return.</Text>'
            '</VStack></HStack>')
    return [("a KpiRow rows + Chart native labelled in LLM stacks", "a", [KPIS, CHART], slide(CC.KPI_HEAD, body))]


def case_b() -> list[tuple]:
    body = ('<Table ref="gaps" variant="ledger" grow="1" header.backgroundColor="$panelDark" />'
            '<VStack gap="8"><Text fontSize="14" bold="true" color="$textMuted" letterSpacing="1">HOW WE CLOSE THEM</Text>'
            '<ProcessArrow direction="horizontal" h="64" fontSize="16" bold="true">'
            + "".join(f'<ProcessArrowStep label="{s}" color="{c}" textColor="$onAccent" />' for s, c in
                      (("Audit", "$accent"), ("Re-bid", "$accent"), ("Re-budget", "$accent"), ("Measure", "$positive")))
            + "</ProcessArrow></VStack>")
    return [("b Table ref (ledger) + LLM native ProcessArrow", "b", [TABLE], slide(CL.HEADS["table"], body))]


C_BODY = ('<KpiRow ref="kpis" variant="grid" />'
          '<CardGrid ref="levers" variant="grid" grow="1" />')
TWO = CC.comp("two", "card_grid", {"card_layout": "grid", "cards": [
    {k: c[k] for k in ("title", "tag", "icon", "tone", "body")} for c in CARDS["content_data"]["cards"][:2]]})
S_BODY = ('<KpiRow ref="kpis" variant="grid" grow="1" />'
          '<CardGrid ref="two" variant="grid" grow="1" />')


def layer(lines: list[tuple[float, float, float, float]]) -> str:
    return ('<Layer position="absolute" top="0" left="0" w="1280" h="720">'
            + "".join(f'<Line x1="{a:.0f}" y1="{b:.0f}" x2="{c:.0f}" y2="{e:.0f}" color="$negative" lineWidth="3" '
                      f'endArrow="true" />' for a, b, c, e in lines) + "</Layer>")


def arrow_layer(pairs: list[tuple[str, str]]) -> str:
    return ('<Layer position="absolute" top="0" left="0" w="1280" h="720">'
            + "".join(f'<Arrow x="0" y="0" from="{a}" to="{b}" color="$negative" lineWidth="3" endArrow="true" />'
                      for a, b in pairs) + "</Layer>")


def pixel_layer(slug: str, head: str, body: str, comps: list[dict], pairs: list[tuple[str, str]], theme: str) -> str:
    """Compile the slide with no layer and fit-grow off (the layout an LLM that knew POM's natural layout would
    target), then draw a Line from under each value to the left of each title at those pixels."""
    d0 = OUT / f"{slug}-probe"
    compile_slide(d0, slide(head, body, fit_off=True), comps, theme)
    sh = shapes(d0 / "presentation.pptx")
    lines = []
    for v, t in pairs:
        a, b = box_of(sh, v), box_of(sh, t)
        lines.append((a["x"] + a["w"] / 2, a["y"] + a["h"], b["x"] + 10, b["y"] + b["h"] / 2))
    return layer(lines)


def ids_of(head: str, body: str, comps: list[dict], texts: list[str]) -> list[str]:
    """The ids code writes on the Texts that hold these words (a dry expand, as the validator runs it)."""
    plan = {"components": comps}
    xml = tiles.fill(composed.expand(slide(head, body), plan)["xml"], plan)["xml"]
    out = []
    for t in texts:
        m = re.search(rf'<Text[^>]*\sid="([^"]+)"[^>]*>(?:<Span[^>]*>)?{re.escape(t[:3])}', xml)
        out.append(m.group(1) if m else "missing")
    return out


def case_c(theme: str) -> list[tuple]:
    """Dense (KPI row + 4 cards, fit-grow has little room) and sparse (KPI row + 2 short cards, fit-grow grows both):
    a Line layer at the un-grown pixels, compiled with fit-grow off and on; and POM's <Arrow from to> on ids, once
    with the ids the prompt would teach (kpiv-<cid>-<i>, card-<cid>-<i>) and once with the ids code actually wrote."""
    head = "Margin and retention decide whether the levers pay"
    pairs = [("$48.2M", "Search"), ("72.1%", "Pricing")]
    lay = pixel_layer("c", head, C_BODY, [KPIS, CARDS], pairs, theme)
    real = ids_of(head, C_BODY, [KPIS, CARDS], ["$48.2M", "Search", "72.1%", "Pricing"])
    guessed = [("kpiv-kpis-0", "card-levers-0"), ("kpiv-kpis-2", "card-levers-2")]
    s_pairs = [("$48.2M", "Search"), ("72.1%", "Placement")]
    s_lay = pixel_layer("s", head, S_BODY, [KPIS, TWO], s_pairs, theme)
    return [("c1 dense: Line layer at un-grown pixels, fit-grow off", "c1", [KPIS, CARDS], slide(head, C_BODY, lay, fit_off=True), pairs),
            ("c2 dense: same Line layer, fit-grow on (pipeline)", "c2", [KPIS, CARDS], slide(head, C_BODY, lay), pairs),
            ("c3 dense: <Arrow from to>, ids as documented", "c3", [KPIS, CARDS], slide(head, C_BODY, arrow_layer(guessed)), pairs),
            ("c4 dense: <Arrow from to>, ids code wrote", "c4", [KPIS, CARDS],
             slide(head, C_BODY, arrow_layer([(real[0], real[1]), (real[2], real[3])])), pairs),
            ("c5 sparse: Line layer, fit-grow off", "c5", [KPIS, TWO], slide(head, S_BODY, s_lay, fit_off=True), s_pairs),
            ("c6 sparse: same Line layer, fit-grow on (pipeline)", "c6", [KPIS, TWO], slide(head, S_BODY, s_lay), s_pairs)]


def case_d() -> list[tuple]:
    card = ('<HStack grow="1" gap="20" alignItems="stretch">'
            '<VStack w="1" grow="1" gap="10" padding="20" backgroundColor="$surfaceAlt" borderRadius="12">'
            '<Text fontSize="15" bold="true" color="$accentText" letterSpacing="1">THE RETURN BY CLASS</Text>'
            '<Chart ref="roas" grow="1" /></VStack>'
            '<VStack w="1" grow="1" gap="10" padding="20" backgroundColor="$surfaceAlt" borderRadius="12">'
            '<Text fontSize="15" bold="true" color="$accentText" letterSpacing="1">WHAT WE TRACK</Text>'
            '<KpiRow ref="kpis" variant="rows" grow="1" /></VStack></HStack>')
    nested = ('<CardGrid ref="levers" variant="grid" grow="1"><KpiRow ref="kpis" variant="strip" /></CardGrid>'
              '<Table ref="gaps" h="200"><Chart ref="roas" /></Table>')
    return [("d1 Chart + KpiRow refs inside LLM cards", "d1", [KPIS, CHART], slide("Generic search returns the least", card)),
            ("d2 ref-in-ref: KpiRow in CardGrid, Chart in Table", "d2", [KPIS, CARDS, CHART, TABLE],
             slide("Nested refs", nested))]


def case_e() -> list[tuple]:
    body = ('<HStack grow="1" gap="20" alignItems="stretch">'
            '<KpiRow ref="kpis" variant="grid" w="1" grow="1" fontSize="40" value.fontSize="72" value.text="$99M" '
            'kpi_values="$99M,1%,2%,3%" label.fontFamily="Georgia" id="mine" item.backgroundColor="#FF0000" />'
            '<Chart ref="roas" w="1" grow="1" chartType="line" title="ROAS (made up)" showTitle="true" '
            'chartColors="$accent,$negative" x="40" y="40" /></HStack>'
            '<Table ref="gaps" h="190" table_rows="[[1,2]]" defaultRowHeight="30" label.fontSize="30" />')
    return [("e content attributes the LLM must not set", "e", [KPIS, CHART, TABLE],
             slide("Content attributes are code's", body))]


CASES = {"a": lambda th: case_a(), "b": lambda th: case_b(), "c": case_c, "d": lambda th: case_d(),
         "e": lambda th: case_e()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", default=list(CASES), choices=list(CASES))
    ap.add_argument("--palette", default="corporate-slate")
    args = ap.parse_args()
    theme = resolve_theme(args.palette)["element"]
    results, rows = {}, []
    for c in args.only:
        shots = []
        for label, slug, comps, xml, *extra in CASES[c](theme):
            r = compile_slide(OUT / slug, xml, comps, theme)
            if extra and r["compiled"]:
                sh = shapes(OUT / slug / "presentation.pptx")
                lines = [s for s in sh if s["kind"] == "line"]
                r["landing"] = []
                for (v, t), ln in zip(extra[0], lines):
                    p0, p1 = ends(ln)
                    a, b = box_of(sh, v), box_of(sh, t)
                    want0, want1 = (a["x"] + a["w"] / 2, a["y"] + a["h"]), (b["x"] + 10, b["y"] + b["h"] / 2)
                    r["landing"].append({"from": v, "to": t, "start_miss_px": miss(p0, a), "end_miss_px": miss(p1, b),
                                         "start_off_px": round(dist(p0, want0), 1), "end_off_px": round(dist(p1, want1), 1)})
                r["lines_drawn"] = len(lines)
            shots.append((label, r.pop("pdf")))
            results[slug] = {"label": label, **r}
            errs = [i["code"] for i in r["node_issues"]]
            print(f"{slug}: compiled={r['compiled']} node={errs} compile={r['compile_errors']} "
                  f"landing={r.get('landing', '')}", flush=True)
        rows += [(c, shots[k:k + 4]) for k in range(0, len(shots), 4)]
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    CT.sheet_rows(rows, DOCS / "sheet.png", cols=max(len(s) for _, s in rows))
    print(DOCS / "sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
