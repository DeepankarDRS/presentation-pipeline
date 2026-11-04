"""Syntax audit, free (docs/syntax-audit-2026-11-04.md): the composition tags judged side by side. No API calls.

    python -m scripts.syntax_audit catalogue [--only kpi_row card_grid ...]    # every node x variant: tags, XML, counts, render
    python -m scripts.syntax_audit consistency                                 # plan keys / parts / attributes; attribute reach
    python -m scripts.syntax_audit stress [--only kpi_row ...] [--cases one many ...]
    python -m scripts.syntax_audit atomic                                      # 3 nodes as atomic parts vs today's tags
    python -m scripts.syntax_audit flex                                        # what POM's flexbox does, measured
    python -m scripts.syntax_audit census                                      # layout features in expanders and saved LLM slides

Everything goes the validator's way (scripts/ownership_probe.py): composed.expand -> tiles.fill -> deck font -> normalize
-> compile-pom.js (fit-grow, pptx-post) -> LibreOffice with Inter, one process at a time.
The timeline node and the process_arrow / flow removal are on claude/left-blocks-build-0fe007 (it conflicts with this
branch): its sequences.py and its nodes.timeline are loaded from git at run time, nothing is merged.
Writes output/syntax-audit/ (slides) and docs/eval/syntax-audit/ (sheets, results, catalogue.md).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from scripts import composition_convention as CC  # noqa: E402
from scripts import composition_gallery_left as CL  # noqa: E402
from scripts import composition_test as CT  # noqa: E402
from scripts import left_blocks_gallery as LB  # noqa: E402
from scripts import ownership_probe as OP  # noqa: E402  (sets POM_BLOCKS / POM_NODES: overruled below)
from scripts import tile_gallery as TG  # noqa: E402
from scripts.card_replay import LO_PROFILE, render as lo_render, tokens  # noqa: E402
from scripts.phase0b import fontcheck as F  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.geometry_audit import audit_geometry  # noqa: E402
from src.compiler.nodes import compose, composed, spec, tiles  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

os.environ["POM_BLOCKS"] = "tiles"
os.environ["POM_NODES"] = "kpi_row,card_grid,chart,table,timeline"

OUT = ROOT / "output" / "syntax-audit"
DOCS = ROOT / "docs" / "eval" / "syntax-audit"
BRANCH = "claude/left-blocks-build-0fe007"
LIGHT, DARK = "corporate-slate", "graphite-dark"
NODE_KINDS = ("kpi_row", "card_grid", "chart", "timeline", "table")


def _git_show(path: str) -> str:
    cache = OUT / "_branch" / path.replace("/", "_")
    p = subprocess.run(["git", "show", f"{BRANCH}:presentation-pipeline/{path}"], cwd=ROOT, capture_output=True)
    if p.returncode == 0:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(p.stdout)
    return cache.read_text(encoding="utf-8")


def install_timeline() -> None:
    """The finished timeline node from the other branch, in this process only; process_arrow and flow gone."""
    src = OUT / "_branch" / "sequences_audit.py"
    code = _git_show("src/compiler/nodes/sequences.py")
    src.write_text(code, encoding="utf-8")
    sp = importlib.util.spec_from_file_location("sequences_audit", src)
    mod = importlib.util.module_from_spec(sp)
    sys.modules["sequences_audit"] = mod
    sp.loader.exec_module(mod)
    composed.sequences = mod
    other = yaml.safe_load(_git_show("src/knowledge/core/block-variants.yaml"))["nodes"]
    nodes = spec.nodes()
    nodes["timeline"] = other["timeline"]
    nodes.pop("process_arrow", None)
    nodes.pop("flow", None)
    compose.SEVERITY.setdefault("NODE_VERTICAL_ROWS", compose.REPORT)


# ── sample plans (composition_convention / composition_gallery_left: saved shapes, words anonymised) ─────────────────

KPIS, CARDS, CHART, TIMELINE, TABLE = CC.KPIS, CC.CARDS, CL.CHART, CL.TIMELINE, CL.TABLE
TIMELINE_SHORT = CL.TIMELINE_SHORT
STEPS = CC.comp("levers", "card_grid", dict(CARDS["content_data"], card_layout="steps", focus_card=3))
UNNUMBERED = CC.comp("levers", "card_grid", dict(CARDS["content_data"], cards=[   # "LEVER 1" is its own ordinal: `numbered` falls back
    dict(c, tag=t) for c, t in zip(CARDS["content_data"]["cards"], ("DEMAND", "SHELF", "PRICE", "LOYALTY"))]))
HEADS = {"kpi_row": CC.KPI_HEAD, "card_grid": CC.CARD_HEAD, "chart": CL.HEADS["chart"], "timeline": CL.HEADS["timeline"],
         "table": CL.HEADS["table"], "bullets": CL.HEADS["bullets"], "callout": CL.HEADS["callout"],
         "header": CL.HEADS["header"]}


def plan_for(kind: str, variant: str) -> dict:
    if kind == "kpi_row":
        return KPIS
    if kind == "card_grid":
        return STEPS if variant in ("steps", "rail") else UNNUMBERED if variant.endswith("numbered") else CARDS
    if kind == "chart":
        return CHART
    if kind == "timeline":
        return TIMELINE_SHORT if variant == "native" else TIMELINE
    return TABLE


EXTRA_ATTR = {("table", "ledger"): ' icons="alert-triangle,store,store,wrench"'}


def bare_tag(kind: str, cid: str, variant: str, attrs: str = "") -> str:
    v = f' variant="{variant}"' if variant else ""
    return f'<{spec.nodes()[kind]["tag"]} ref="{cid}"{v}{EXTRA_ATTR.get((kind, variant), "")}{attrs} grow="1" />'


# ── every allowed attribute ───────────────────────────────────────────────────────────────────────────────────────

SAMPLE = {
    "color": "$accentText", "bgColor": "$accentSoft", "backgroundColor": "$surfaceAlt", "highlight": "$accentSoft",
    "bold": "true", "italic": "false", "underline": "false", "letterSpacing": "0.5", "textAlign": "left",
    "textGradient": "linear-gradient(90deg, $accent, $accentText)", "glow.size": "1", "glow.opacity": "0.2",
    "glow.color": "$accent", "outline.size": "0.25", "outline.color": "$border", "name": "star", "variant": "circle-filled",
    "shapeType": "rect", "w": "max", "h": "max", "fill.color": "$accent", "fill.transparency": "0.1", "line.color": "$border",
    "line.width": "1", "line.dashType": "solid", "width": "1",
    "backgroundGradient": "linear-gradient(90deg, $surface, $surfaceAlt)", "border": "", "border.color": "$border",
    "border.width": "1", "border.dashType": "solid", "borderTop.color": "$border", "borderTop.width": "1",
    "borderRight.color": "$border", "borderRight.width": "1", "borderBottom.color": "$border", "borderBottom.width": "1",
    "borderLeft.color": "$accent", "borderLeft.width": "3", "padding": "12", "padding.top": "12", "padding.right": "12",
    "padding.bottom": "12", "padding.left": "12", "gap": "8", "alignItems": "stretch", "justifyContent": "start",
    "shadow.type": "outer", "shadow.blur": "4", "shadow.offset": "2", "shadow.color": "$textMain", "shadow.opacity": "0.1",
    "opacity": "1", "grow": "1", "minW": "10", "maxW": "2000", "minH": "10", "maxH": "2000", "alignSelf": "stretch",
    "margin": "1", "borderRadius": "6", "showLegend": "true", "cellBorder.color": "$border", "cellBorder.width": "1", "cellBorder.dashType": "solid",
}


def allowed_attributes(kind: str) -> list[tuple[str, str]]:
    """(attribute on the group tag, the node type it reaches): group box, then every part's attributes."""
    nd, d = spec.nodes()[kind], tiles.data()
    out = [(a, "box") for a in list(d["box_attributes"]) + ["borderRadius"] if a not in ("border",)]
    out += [(a, "own") for a in nd.get("native_attributes") or []]
    for p, typ in nd["parts"].items():
        out += [(f"{p}.{a}", typ) for a in compose.part_attrs(typ) if a != "border"]
    return out


def max_tag(kind: str, cid: str, variant: str) -> str:
    attrs = "".join(f' {k}="{SAMPLE.get(k.split(".", 1)[-1] if "." in k and k.split(".")[0] in spec.nodes()[kind]["parts"] else k, "1")}"'
                    for k, _ in allowed_attributes(kind) if k != "grow")
    return bare_tag(kind, cid, variant, attrs)


STYLED = {
    "kpi_row": ' backgroundColor="$surfaceAlt" padding="14" borderRadius="10" item.backgroundColor="$surface" '
               'item.border.color="$border" item.borderLeft.color="$tone" item.borderLeft.width="4" label.color="$textMuted" '
               'value.color="$toneText" delta.color="$toneText" icon.color="$toneText"',
    "card_grid": ' item.backgroundColor="$surfaceAlt" item.borderTop.color="$tone" item.borderTop.width="4" '
                 'title.color="$toneText" body.color="$textMain" tag.color="$textMuted" icon.color="$toneText"',
    "chart": ' backgroundColor="$surfaceAlt" padding="20" borderRadius="12" border.color="$border" border.width="1" '
             'title.color="$accentText" label.color="$textMain" value.color="$accentText" bar.fill.color="$accentSoft"',
    "timeline": ' backgroundColor="$surfaceAlt" padding="16" borderRadius="12" date.color="$accentText" title.color="$textMain" '
                'description.color="$textMuted" marker.fill.color="$accent" connector.fill.color="$accentSoft"',
    "table": ' header.backgroundColor="$panelDark" header.color="$onPanelDark" label.color="$accentText" '
             'cell.color="$textMain" stripe.backgroundColor="$surfaceAlt"',
}


# ── one slide ─────────────────────────────────────────────────────────────────────────────────────────────────────

def expand_only(xml: str, comps: list[dict], head: str = "") -> dict:
    plan = {"components": comps, "slide_title": head}
    drawn = composed.expand(xml, plan)
    filled = tiles.fill(drawn["xml"], plan)
    return {"xml": filled["xml"], "issues": drawn["issues"] + filled["issues"], "ok": drawn["ok"] and filled["ok"],
            "components": drawn["components"]}


def body_of(slide_xml: str) -> str:
    """The expansion of the audit frame's body (the frame's own stack removed)."""
    start = '<VStack grow="1" gap="18" alignItems="stretch">'
    i = slide_xml.find(start)
    return slide_xml[i + len(start):slide_xml.rfind("</VStack></VStack></Slide>")] if i >= 0 else slide_xml


def compile_slide(d: Path, xml: str, comps: list[dict], theme: str, head: str = "") -> dict:
    """The validator's order, compile only (rendered later in a batch); every issue kept."""
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tag.xml").write_text(xml, encoding="utf-8")
    drawn = expand_only(xml, comps, head)
    (d / "expanded.xml").write_text(drawn["xml"], encoding="utf-8")
    norm = normalize_xml(deck_font(drawn["xml"]))
    (d / "in.xml").write_text(ensure_single_theme(norm["cleaned_xml"], theme), encoding="utf-8")
    p = subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    (d / "compile.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    res = json.loads((d / "compile-result.json").read_text(encoding="utf-8")) if (d / "compile-result.json").exists() else {}
    out = {"node_ok": drawn["ok"], "components": drawn["components"],
           "node_issues": [{k: i.get(k) for k in ("code", "severity", "ref", "message")} for i in drawn["issues"]],
           "normalize": sorted({i["code"] for i in norm["issues"]}),
           "compiled": res.get("status") == "success" and (d / "presentation.pptx").exists(),
           "compile_errors": [str(x.get("message") or x.get("type") or x.get("code"))[:1500] for x in res.get("diagnostics") or []],
           "warnings": sorted({w.get("code") for w in res.get("warnings") or []}), "fitGrow": res.get("fitGrow") or []}
    return out


def render_batch(dirs: list[Path], size: int = 8) -> None:
    """One soffice per `size` slides (no parallel renders): each dir's presentation.pptx -> presentation.pdf."""
    from scripts.node_test_score import SOFFICE
    todo = [d for d in dirs if (d / "presentation.pptx").exists() and not (d / "presentation.pdf").exists()]
    if not todo:
        return
    lo_fonts = LO_PROFILE / "user" / "fonts"
    if not lo_fonts.exists():
        lo_render(todo[0])
    soffice = shutil.which("soffice") or str(SOFFICE)
    tmp = OUT / "_lo"
    for k in range(0, len(todo), size):
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        batch = todo[k:k + size]
        names = []
        for n, d in enumerate(batch):
            names.append(tmp / f"s{n}.pptx")
            shutil.copy2(d / "presentation.pptx", names[-1])
        subprocess.run([soffice, f"-env:UserInstallation={LO_PROFILE.as_uri()}", "--headless", "--convert-to", "pdf",
                        "--outdir", str(tmp), *map(str, names)], capture_output=True, check=False, timeout=600)
        for n, d in enumerate(batch):
            pdf = tmp / f"s{n}.pdf"
            if pdf.exists():
                shutil.move(str(pdf), d / "presentation.pdf")
    shutil.rmtree(tmp, ignore_errors=True)


# ── what a slide shows: measured from the pptx, the fitted XML and the render ─────────────────────────────────────────

def pptx_text(pptx: Path) -> str:
    out = []
    with zipfile.ZipFile(pptx) as z:
        for n in z.namelist():
            if re.match(r"ppt/slides/slide\d+\.xml$", n) or re.match(r"ppt/charts/chart\d+\.xml$", n):
                x = z.read(n).decode("utf-8", "replace")
                out += re.findall(r"<a:t\b[^>]*>([^<]*)</a:t>", x) + re.findall(r"<c:v>([^<]*)</c:v>", x)
    return " ".join(out)


def plan_strings(comp: dict) -> list[str]:
    cd, out = comp.get("content_data") or {}, []

    def walk(v: Any, key: str = "") -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                if k not in ("card_layout", "tone", "icon", "focus_card", "direction", "per_row"):
                    walk(x, k)
        elif isinstance(v, list):
            if key not in ("kpi_tones", "kpi_icons"):
                for x in v:
                    walk(x, key)
        elif isinstance(v, str) and v.strip() and key not in ("key_phrase", "chart_type"):
            out.append(v)
    walk(cd)
    return out


_WORD = re.compile(r"[\w₹$%.,+\-−]+")


def _norm_words(s: str) -> set[str]:
    import html
    return {w.strip(".,").lower() for w in _WORD.findall(html.unescape(s)) if w.strip(".,")}


def _num(w: str) -> float | None:
    try:
        return float(re.sub(r"[^\d.]", "", w))
    except ValueError:
        return None


def missing_words(comps: list[dict], pptx: Path) -> list[str]:
    seen = _norm_words(pptx_text(pptx))
    nums = {_num(w) for w in seen} - {None}
    # a chart stores numbers without their unit: "0.80x" is present as 0.8 with a number format
    miss = []
    for c in comps:
        for s in plan_strings(c):
            ws = _norm_words(s)
            lost = [w for w in ws if w not in seen and _num(w) not in nums]
            if lost:
                miss.append(s[:50])
    return miss


def font_stats(d: Path) -> dict:
    f = d / "fitted.xml"
    x = f.read_text(encoding="utf-8") if f.exists() else (d / "in.xml").read_text(encoding="utf-8")
    sizes = [float(s) for s in re.findall(r'<(?:Text|Ul|Li|Td)\b[^>]*?\sfontSize="([\d.]+)"', x)]
    return {"min": min(sizes) if sizes else None, "max": max(sizes) if sizes else None}


def geometry_codes(d: Path) -> list[str]:
    g = d / "geometry.json"
    if not g.exists():
        return []
    try:
        data = json.loads(g.read_text(encoding="utf-8"))
        issues = audit_geometry(data[0] if isinstance(data, list) else data, d / "presentation.pptx")
    except Exception as e:  # a report only
        return [f"GEOM_AUDIT_FAILED:{type(e).__name__}"]
    return sorted(str(i.get("code") if isinstance(i, dict) else i) for i in issues)


def measure(d: Path, comps: list[dict], r: dict) -> dict:
    if not r.get("compiled"):
        return r
    r["missing"] = missing_words(comps, d / "presentation.pptx")
    r["fonts"] = font_stats(d)
    r["geom"] = geometry_codes(d)
    pdf = d / "presentation.pdf"
    if pdf.exists():
        ws = F.pdf_words(pdf)
        fitted = d / "fitted.xml"
        vocab = F.slide_words((fitted if fitted.exists() else d / "in.xml").read_text(encoding="utf-8"))
        r["broken"] = [str(b)[:60] for b in F.broken(ws, vocab)]
        r["overlap"] = [str(o)[:80] for o in F.overlaps(ws)]
    return r


def verdict(r: dict) -> tuple[str, str]:
    """(PASS | WARN | BREAK, cause), from the measures; the sheet check by eye comes on top (report)."""
    if not r.get("compiled"):
        return "BREAK", "no compile: " + "; ".join(r.get("compile_errors") or [])[:120]
    errs = [i["code"] for i in r["node_issues"] if i["severity"] == "error"]
    if errs:
        return "BREAK", "node error " + ",".join(sorted(set(errs)))
    if r.get("missing"):
        return "BREAK", f"words lost: {r['missing'][0]}"
    if r.get("overlap"):
        return "BREAK", f"text overlap ({len(r['overlap'])})"
    if r.get("broken"):
        return "BREAK", f"broken words ({len(r['broken'])}): {r['broken'][0]}"
    hard = [g for g in r.get("geom") or [] if g in ("GEOM_OFF_SLIDE", "GEOM_TEXT_SPILL", "GEOM_SPILL", "GEOM_CONTENT_SPILL", "GEOM_OVERLAP")]
    if hard:
        return "BREAK", ",".join(sorted(set(hard)))
    if "WORD_TOO_WIDE" in (r.get("warnings") or []):
        return "BREAK", "WORD_TOO_WIDE"
    soft = sorted({i["code"] for i in r["node_issues"] if i["code"] in ("NODE_VARIANT_UNMET", "NODE_ITEM_MISSING")})
    f = r.get("fonts") or {}
    if f.get("min") is not None and f["min"] < 11:
        soft.append(f"text {f['min']:.0f}px")
    if "SLIDE_DENSE" in (r.get("warnings") or []):
        soft.append("SLIDE_DENSE")
    soft += sorted({g for g in r.get("geom") or [] if g == "GEOM_CARD_EMPTY"})
    return ("WARN", ",".join(soft)) if soft else ("PASS", "")


# ── catalogue ─────────────────────────────────────────────────────────────────────────────────────────────────────

_XML_NOISE = re.compile(r'\s(id)="[^"]*"')
_STRETCH = re.compile(r'\salignItems="stretch"')


def hand_form(expanded: str) -> str:
    """The same drawing as an LLM would type it atomically: code's bookkeeping removed (peer ids, the alignItems default).
    It keeps every typed word, size and style; a chart-post comment (data labels) stays, since only code can write it."""
    return _STRETCH.sub("", _XML_NOISE.sub("", expanded))


def pretty_lines(x: str) -> int:
    return len(re.findall(r"<(?!/)", x))   # one element per line, as a person would format it


def undecided() -> list[dict]:
    """bullets, callout, header have no expander: the tag is hypothetical and the XML is the 2026-10-27 proof's."""
    b, t, q, h = CL.BULLETS, CL.TAKEAWAY, CL.QUOTE, CL.TITLE
    hx = ('<VStack gap="6"><Text fontSize="14" bold="true" letterSpacing="2" color="$accentText">PERFORMANCE</Text>'
          f'<Text fontSize="34" bold="true" color="$textMain">{h["content_data"]["title"]}</Text>'
          f'<Text fontSize="18" color="$textMuted">{h["content_data"]["subtitle"]}</Text></VStack>')
    hi = ('<VStack gap="6" padding="28" backgroundColor="$panelDark"><Text fontSize="14" bold="true" letterSpacing="2" color="$onPanelDark">PERFORMANCE</Text>'
          f'<Text fontSize="34" bold="true" color="$onPanelDark">{h["content_data"]["title"]}</Text>'
          f'<Text fontSize="18" color="$onPanelDark">{h["content_data"]["subtitle"]}</Text></VStack>')
    return [
        {"kind": "bullets", "variant": "native", "tag": '<BulletList ref="insights" />', "comp": b, "xml": CL.bullets_native()},
        {"kind": "bullets", "variant": "rows", "tag": '<BulletList ref="insights" variant="rows" />', "comp": b, "xml": CL.bullets_rows(False)},
        {"kind": "bullets", "variant": "rows numbered", "tag": '<BulletList ref="insights" variant="rows numbered" />', "comp": b, "xml": CL.bullets_rows(True)},
        {"kind": "bullets", "variant": "grid", "tag": '<BulletList ref="insights" variant="grid" />', "comp": b, "xml": CL.bullets_grid()},
        {"kind": "bullets", "variant": "banded", "tag": '<BulletList ref="insights" variant="banded" />', "comp": b, "xml": CL.bullets_banded()},
        {"kind": "callout", "variant": "native", "tag": '<Callout ref="takeaway" />', "comp": t, "xml": CL.callout_native(t)},
        {"kind": "callout", "variant": "native (quote)", "tag": '<Callout ref="voice" />', "comp": q, "xml": CL.callout_native(q)},
        {"kind": "header", "variant": "standard", "tag": '<SlideHeader ref="title" />', "comp": h, "xml": hx},
        {"kind": "header", "variant": "inverted", "tag": '<SlideHeader ref="title" variant="inverted" />', "comp": h, "xml": hi},
    ]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def catalogue(only: list[str]) -> None:
    theme = resolve_theme(LIGHT)["element"]
    rows, entries = {}, []
    for kind in only:
        if kind not in NODE_KINDS:
            continue
        for variant in spec.nodes()[kind]["compositions"]:
            comp = plan_for(kind, variant)
            cid, head = comp["component_id"], HEADS[kind]
            d0 = OUT / "catalogue" / kind / slug(variant)
            minimal, styled, full = bare_tag(kind, cid, variant), bare_tag(kind, cid, variant, STYLED[kind]), max_tag(kind, cid, variant)
            shots = {}
            e = {"kind": kind, "variant": variant, "plan": comp, "tag": minimal, "styled": styled, "full": full, "built": True}
            for arm, tag in (("tag", minimal), ("styled", styled), ("full", full)):
                r = compile_slide(d0 / arm, TG.slide("AUDIT", head, tag), [comp], theme, head)
                shots[arm] = d0 / arm
                e[arm + "_result"] = r
            drawn = expand_only(TG.slide("AUDIT", head, minimal), [comp], head)
            expanded = body_of(drawn["xml"])
            hand = hand_form(expanded)
            e.update(expanded=expanded, hand=hand)
            r = compile_slide(d0 / "hand", TG.slide("AUDIT", head, hand), [], theme, head)
            shots["hand"] = d0 / "hand"
            e["hand_result"] = r
            render_batch(list(shots.values()))
            for arm, d in shots.items():
                e[arm + "_result"] = measure(d, [comp], e[arm + "_result"])
                e[arm + "_verdict"] = verdict(e[arm + "_result"])
            e["hand_diff"] = CT.pixel_diff(shots["tag"] / "presentation.pdf", shots["hand"] / "presentation.pdf")
            e["counts"] = {"tag": tokens(minimal), "styled": tokens(styled), "full": tokens(full), "expanded": tokens(expanded),
                           "hand": tokens(hand), "lines_expanded": pretty_lines(expanded), "lines_hand": pretty_lines(hand),
                           "plan": tokens(json.dumps(comp["content_data"], ensure_ascii=False))}
            entries.append(e)
            rows.setdefault(kind, []).append((variant, [(f"{variant}: {a}", shots[a] / "presentation.pdf" if (shots[a] / "presentation.pdf").exists() else None)
                                                        for a in ("tag", "styled", "full", "hand")]))
            print(kind, variant, e["counts"], e["tag_verdict"], "hand diff", e["hand_diff"], flush=True)
    for u in undecided():
        if u["kind"] not in only:
            continue
        comp, head = u["comp"], HEADS[u["kind"]]
        d = OUT / "catalogue" / u["kind"] / slug(u["variant"])
        r = compile_slide(d, TG.slide("AUDIT", head, u["xml"]), [], theme, head)
        render_batch([d])
        r = measure(d, [comp], r)
        hand = hand_form(u["xml"])
        e = {"kind": u["kind"], "variant": u["variant"], "plan": comp, "tag": u["tag"], "styled": u["tag"], "full": u["tag"], "built": False,
             "expanded": u["xml"], "hand": hand, "tag_result": r, "tag_verdict": verdict(r), "hand_diff": None,
             "counts": {"tag": tokens(u["tag"]), "styled": tokens(u["tag"]), "full": tokens(u["tag"]), "expanded": tokens(u["xml"]),
                        "hand": tokens(hand), "lines_expanded": pretty_lines(u["xml"]), "lines_hand": pretty_lines(hand),
                        "plan": tokens(json.dumps(comp["content_data"], ensure_ascii=False))}}
        entries.append(e)
        pdf = d / "presentation.pdf"
        rows.setdefault(u["kind"], []).append((u["variant"], [(f'{u["variant"]} (proof XML, no expander)', pdf if pdf.exists() else None)]))
        print(u["kind"], u["variant"], e["counts"], e["tag_verdict"], flush=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    for kind, rs in rows.items():
        CT.sheet_rows(rs, DOCS / f"catalogue-{kind}.png", cols=max(len(s) for _, s in rs))
    store = DOCS / "catalogue.json"
    old = json.loads(store.read_text(encoding="utf-8")) if store.exists() else []
    keep = [e for e in old if e["kind"] not in {x["kind"] for x in entries}]
    store.write_text(json.dumps(keep + entries, indent=1, ensure_ascii=False), encoding="utf-8")
    write_catalogue_md(keep + entries)


def write_catalogue_md(entries: list[dict]) -> None:
    order = list(NODE_KINDS) + ["bullets", "callout", "header"]
    L = ["# Syntax catalogue (generated by `python -m scripts.syntax_audit catalogue`; do not edit)", "",
         "Per node and variant: the plan JSON, the minimal tag, a styled tag, the tag with every allowed attribute, the XML "
         "the real expander writes (after `tiles.fill`), and the same look typed atomically (the expansion without code's "
         "peer ids and the `alignItems=\"stretch\"` default). Tokens are o200k_base. bullets, callout and header have **no "
         "expander**: their tag is hypothetical and their XML is the 2026-10-27 proof's. Report: "
         "[../../syntax-audit-2026-11-04.md](../../syntax-audit-2026-11-04.md).", ""]
    for kind in order:
        es = [e for e in entries if e["kind"] == kind]
        if not es:
            continue
        L += [f"## {kind}", "", f"![sheet](catalogue-{kind}.png)", ""]
        L += ["```json", json.dumps(es[0]["plan"]["content_data"], ensure_ascii=False, indent=1),
              "```", "", f'Design hint: `{es[0]["plan"].get("design_hint") or ""}`', ""]
        for e in es:
            c = e["counts"]
            L += [f'### {kind} `{e["variant"]}`', "",
                  f'Tokens: tag {c["tag"]} · styled {c["styled"]} · every attribute {c["full"]} · expanded {c["expanded"]} '
                  f'({c["lines_expanded"]} elements) · atomic by hand {c["hand"]} ({c["lines_hand"]} elements). '
                  f'Checks: {e["tag_verdict"][0]} {e["tag_verdict"][1]}'
                  + (f'; hand form differs from the tag by {e["hand_diff"]:.1%} of pixels' if e.get("hand_diff") is not None else ""), "",
                  "Minimal tag:", "```xml", e["tag"], "```", "Styled tag:", "```xml", e["styled"], "```"]
            if e["built"]:
                L += ["<details><summary>Every allowed attribute</summary>", "", "```xml", e["full"], "```", "</details>", ""]
            L += ["<details><summary>Expanded POM XML</summary>", "", "```xml", e["expanded"], "```", "</details>", "",
                  "<details><summary>Atomic by hand</summary>", "", "```xml", e["hand"], "```", "</details>", ""]
    (DOCS / "catalogue.md").write_text("\n".join(L), encoding="utf-8")


def cmd_catalogue(args: argparse.Namespace) -> int:
    catalogue(args.only or list(NODE_KINDS) + ["bullets", "callout", "header"])
    return 0


# ── consistency: does the syntax mean one thing everywhere? ───────────────────────────────────────────────────────────

# plan key -> (part or attribute that styles it, on the tag; a ref field where one exists). "" = no part.
PLAN_MAP: dict[str, list[tuple[str, str, str]]] = {
    "kpi_row": [("kpi_labels", "label", "kpis.N.label"), ("kpi_values", "value", "kpis.N.value"),
                ("kpi_deltas", "delta", "kpis.N.note"), ("kpi_icons", "icon", ""), ("kpi_tones", "$tone* / color", "")],
    "card_grid": [("cards[].title", "title", ""), ("cards[].tag", "tag", ""), ("cards[].body", "body", ""),
                  ("cards[].bullets", "body (text); bullets (box, columns only)", ""), ("cards[].icon", "icon", ""),
                  ("cards[].tone", "$tone* / color", ""), ("cards[].key_phrase", "", ""), ("focus_card", "(emphasis)", ""),
                  ("card_layout", "variant steps / rail", "")],
    "chart": [("chart_title", "title", ""), ("chart_labels", "label", ""), ("chart_values / chart_series", "value; bar", ""),
              ("chart_type", "", "")],
    "timeline": [("timeline_items[].date", "date", ""), ("timeline_items[].label", "title (label. an alias)", ""),
                 ("timeline_items[].description", "description", ""), ("direction", "direction", "")],
    "table": [("table_columns", "header", ""), ("table_rows[][0]", "label", ""), ("table_rows[][1..]", "cell", "")],
}


def _sentinel(attr: str, n: int) -> str:
    return f"$probe{n}" if tiles._is_colour_attr(attr) else str(90000 + n)


def reach_matrix() -> dict:
    """Each allowed attribute alone on the group tag, for every composition: does it reach the expanded XML?
    reach | noop (accepted, no effect, no report) | dropped (reported) | error | crash."""
    out: dict[str, dict] = {}
    for kind in NODE_KINDS:
        nd = spec.nodes()[kind]
        out[kind] = {}
        attrs = allowed_attributes(kind)
        for variant in nd["compositions"]:
            comp, row = plan_for(kind, variant), {}
            for n, (k, typ) in enumerate(attrs):
                v = _sentinel(k, n)
                tag = f'<{nd["tag"]} ref="{comp["component_id"]}" variant="{variant}" {k}="{v}"{" grow=" + chr(34) + "1" + chr(34) if k != "grow" else ""} />'
                try:
                    r = expand_only(TG.slide("A", "H", tag), [comp], "H")
                except Exception as e:
                    row[k] = f"crash:{type(e).__name__}"
                    continue
                codes = {i["code"] for i in r["issues"]}
                row[k] = ("reach" if f'"{v}"' in r["xml"] else "error" if "NODE_ATTR_UNKNOWN" in codes else
                          "dropped" if "NODE_ATTR_DROPPED" in codes or "LITERAL_COLOR" in codes else "noop")
            out[kind][variant] = row
    return out


def tone_matrix() -> dict:
    """$toneSoft on each node's item / main part: resolved per item, or left as a literal token for the compiler?"""
    probes = {"kpi_row": "item.backgroundColor", "card_grid": "item.backgroundColor", "chart": "bar.fill.color",
              "timeline": "item.backgroundColor", "table": "item.backgroundColor"}
    out = {}
    for kind, a in probes.items():
        nd = spec.nodes()[kind]
        out[kind] = {}
        for variant in nd["compositions"]:
            comp = plan_for(kind, variant)
            r = expand_only(TG.slide("A", "H", f'<{nd["tag"]} ref="{comp["component_id"]}" variant="{variant}" {a}="$toneSoft" grow="1" />'), [comp], "H")
            out[kind][variant] = "left literal" if "$toneSoft" in r["xml"] else "resolved"
    return out


def duplicate_matrix() -> dict:
    """Each allowed attribute alone on the group tag: is the expansion still well-formed XML? An expander that writes an
    attribute literally and also passes the LLM's writes it twice. {kind: {variant: [attributes that break the XML]}}."""
    from lxml import etree
    out: dict[str, dict] = {}
    for kind in NODE_KINDS:
        nd = spec.nodes()[kind]
        out[kind] = {}
        for variant in nd["compositions"]:
            comp, bad = plan_for(kind, variant), []
            for k, _ in allowed_attributes(kind):
                if k == "grow":
                    continue
                v = SAMPLE.get(k.split(".", 1)[-1] if "." in k and k.split(".")[0] in nd["parts"] else k, "1")
                tag = f'<{nd["tag"]} ref="{comp["component_id"]}" variant="{variant}" {k}="{v}" grow="1" />'
                drawn = composed.expand(TG.slide("A", "H", tag), {"components": [comp], "slide_title": "H"})
                try:
                    etree.fromstring(f"<r>{drawn['xml']}</r>".encode("utf-8"))
                except etree.XMLSyntaxError:
                    bad.append(k)
            out[kind][variant] = bad
    return out


def cmd_consistency(args: argparse.Namespace) -> int:
    nodes = spec.nodes()
    reach = reach_matrix()
    summary = {}
    for kind, vs in reach.items():
        for v, row in vs.items():
            by: dict[str, dict[str, int]] = {}
            for k, res in row.items():
                head = k.split(".")[0] if "." in k and k.split(".")[0] in nodes[kind]["parts"] else "(group box)"
                b = by.setdefault(head, {})
                key = res.split(":")[0]
                b[key] = b.get(key, 0) + 1
            summary[f"{kind}/{v}"] = by
    parts_matrix = {}
    for kind in NODE_KINDS:
        for p, t in nodes[kind]["parts"].items():
            parts_matrix.setdefault(p, {})[kind] = t
    meta_matrix = {}
    for kind in NODE_KINDS:
        for m in nodes[kind]["meta"]:
            meta_matrix.setdefault(m, []).append(kind)
    words = {}
    for kind in NODE_KINDS:
        for w in nodes[kind]["compositions"]:
            words.setdefault(w, []).append(kind)
    aliases = {k: {"tag_aliases": nodes[k].get("tag_aliases") or {}, "part_aliases": nodes[k].get("part_aliases") or {},
                   "aliases": nodes[k].get("aliases") or {}, "meta_aliases": nodes[k].get("meta_aliases") or {}} for k in NODE_KINDS}
    sources = {k: {"prompts_in_node": "prompts" in nodes[k], "item_tag": nodes[k].get("item_tag"), "styles": len(nodes[k].get("styles") or {}),
                   "blocks_tag": next((b["tag"] for b in spec.blocks().values() if k in (b["plan_kind"] if isinstance(b["plan_kind"], list) else [b["plan_kind"]])), None)}
               for k in NODE_KINDS}
    prompt = {}
    for kind in NODE_KINDS:
        comp = plan_for(kind, "")
        prompt[kind] = {"prompt_line": tokens(composed.prompt_line(comp, HEADS[kind]))}
    prompt["node_lines_all"] = tokens(composed.node_lines())
    res = {"plan_map": PLAN_MAP, "parts": parts_matrix, "meta": meta_matrix, "words": words, "aliases": aliases, "sources": sources,
           "tone": tone_matrix(), "reach_summary": summary, "prompt_tokens": prompt, "duplicates": duplicate_matrix()}
    (DOCS / "consistency.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (DOCS / "reach.json").write_text(json.dumps(reach, indent=0, ensure_ascii=False), encoding="utf-8")
    for k, v in summary.items():
        noop = {h: b.get("noop", 0) for h, b in v.items() if b.get("noop")}
        other = {h: {x: n for x, n in b.items() if x not in ("noop", "reach")} for h, b in v.items() if set(b) - {"noop", "reach"}}
        print(k, "noop", noop, "other", other)
    print(json.dumps(res["tone"]))
    print("DUPLICATES", json.dumps(res["duplicates"]))
    print(prompt)
    return 0


# ── stress ────────────────────────────────────────────────────────────────────────────────────────────────────────

LONG_LABEL = "Net revenue retention across enterprise subscription customers"
LONG_WORD = "Internationalisation-readiness"
LABELS = ["ARR", "Net revenue retention", "Gross margin", "CAC payback", "Logo churn", "Pipeline cover", "NPS", "Win rate", "ACV", "Runway"]
VALUES = ["$48.2M", "114%", "72.1%", "14 months", "3.1%", "3.4x", "62", "27%", "$41K", "19 months"]
DELTAS = ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months", "-0.4 pts", "+0.3x", "+5", "+3 pts", "+6%", "-1 month"]
TONES = ["good", "good", "bad", "watch", "good", "good", "good", "", "", "watch"]
ICONS = ["trending-up", "users", "percent", "clock", "user-minus", "layers", "smile", "trophy", "tag", "hourglass"]


def C(cid: str, kind: str, cd: dict, hint: str = "") -> dict:
    return {"component_id": cid, "kind": kind, "content_data": cd, "design_hint": hint, "weight": "hero"}


def kpi(n: int = 4, labels=None, values=None, deltas=True, tones=True, icons=True, hint: str = "") -> dict:
    cd: dict[str, Any] = {"kpi_labels": (labels or LABELS)[:n], "kpi_values": (values or VALUES)[:n]}
    if deltas:
        cd["kpi_deltas"] = DELTAS[:n]
    if tones:
        cd["kpi_tones"] = TONES[:n]
    if icons:
        cd["kpi_icons"] = ICONS[:n]
    return C("kpis", "kpi_row", cd, hint or f"highlight {cd['kpi_labels'][0]} as the hero")


CARD_BASE = CC.CARDS["content_data"]["cards"]


def cards_many(n: int, layout: str = "grid", focus: int | None = 0) -> dict:
    cs = [dict(CARD_BASE[i % 4], title=f"{CARD_BASE[i % 4]['title']} {i // 4 + 1}" if n > 4 else CARD_BASE[i % 4]["title"],
               tag=f"LEVER {i + 1}") for i in range(n)]
    return C("levers", "card_grid", {"card_layout": layout, "focus_card": focus, "cards": cs})


def cards_sparse(layout: str) -> dict:
    return C("levers", "card_grid", {"card_layout": layout, "cards": [{"title": t} for t in ("Search", "Placement", "Pricing", "Retention")]})


def cards_long(layout: str) -> dict:
    cs = [{"title": f"{LONG_WORD} of the {t} programme", "tag": "A LONG TAG THAT RUNS ON", "icon": "search",
           "body": "A body long enough to fill several lines at any reasonable size, so that the group's one size binds on this "
                   "card and not on its peers, which is where shrink-to-fit decisions hurt most.",
           "bullets": ["A first bullet long enough to wrap twice in a narrow card column", "A second one", "A third bullet that also goes on for quite a while before it stops"]}
          for t in ("search", "placement", "pricing", "retention")]
    return C("levers", "card_grid", {"card_layout": layout, "focus_card": 0, "cards": cs})


def chart_of(labels: list[str], values: list, title: str = "ROAS by campaign class", hint: str = "", **cd: Any) -> dict:
    return C("roas", "chart", {"chart_title": title, "chart_labels": labels, "chart_values": values, "chart_type": "bar", **cd}, hint)


def tl(items: list[dict], hint: str = "") -> dict:
    return C("roadmap", "timeline", {"direction": "horizontal", "timeline_items": items}, hint)


def tb(cols: list[str], rows: list[list[str]], hint: str = "") -> dict:
    return C("gaps", "table", {"table_columns": cols, "table_rows": rows}, hint)


LONG_TL = [{"date": "Q1 FY2026-27 onward", "label": f"{LONG_WORD} workstream {i} — with a detail line long enough to wrap at least twice in any column it is given"} for i in range(1, 5)]


def stress_plan(kind: str, case: str, variant: str) -> dict:
    steps = kind == "card_grid" and variant in ("steps", "rail")
    lay = "steps" if steps else "grid"
    if kind == "kpi_row":
        return {"one": kpi(1), "sparse": kpi(4, deltas=False, tones=False, icons=False), "many": kpi(9), "odd": kpi(5),
                "long": kpi(4, labels=[LONG_LABEL] * 4, values=["₹1,24,56,789 Cr", "1,142.75%", "US$ 2,348,112", "114 months and 3 days"])}.get(case, KPIS)
    if kind == "card_grid":
        base = STEPS if steps else CARDS
        return {"one": cards_many(1, lay, None), "sparse": cards_sparse(lay), "many": cards_many(9, lay, 3 if steps else 0),
                "odd": cards_many(5, lay, 4 if steps else 0), "long": cards_long(lay)}.get(case, base)
    if kind == "chart":
        lab = [f"Class {chr(65 + i)}" for i in range(14)]
        return {"one": chart_of(["Generic search"], ["0.29x"]), "sparse": chart_of(["A", "B", "C", "D"], [1, 2, 3, 4], title=""),
                "many": chart_of(lab, [f"{0.2 + i * 0.1:.2f}x" for i in range(14)]), "odd": chart_of(lab[:5], ["1.1x", "0.8x", "1.9x", "0.5x", "1.4x"]),
                "long": chart_of([LONG_LABEL, "Category listing ads on the marketplace home page", "Brand defence search", "Competitor conquesting"], ["₹1,24,56,789", "₹2,48,112", "₹91,12,000", "₹3,00,000"])}.get(case, CHART)
    if kind == "timeline":
        base = TIMELINE_SHORT if variant == "native" else TIMELINE
        m = [{"date": f"M{i + 1}", "label": f"Step {i + 1}"} for i in range(9)]
        return {"one": tl([{"date": "Nov", "label": "Launch"}]), "sparse": tl([{"date": "", "label": "Plan"}, {"date": "", "label": "Build"}, {"date": "", "label": "Ship"}]),
                "many": tl(m, "highlight M3"), "odd": tl(m[:3]), "long": tl(LONG_TL)}.get(case, base)
    cols = ["Platform", "Spend", "ROAS", "Target", "Share", "Note", "Owner", "Status"]
    rows = [[f"Platform {i}", f"₹{i}.2L", f"{i}.8x", "2.0x", f"{i * 3}%", "Scale", "Team", "On track"] for i in range(1, 13)]
    return {"one": tb(["Gap", "Fix"], [["CPC above allowable", "Break-even bidding"]]), "sparse": tb(["A", "B", "C"], [["x", "", ""], ["", "y", ""], ["", "", "z"]]),
            "many": tb(cols, rows), "odd": tb(cols[:3], [r[:3] for r in rows[:3]]),
            "long": tb(["Gap and its consequences for the plan", LONG_WORD, "Fix"], [[LONG_LABEL, "A cell long enough to wrap several lines at any reasonable size in this column", "Break-even CPC bidding"]] * 3)}.get(case, TABLE)


NOTE = '<VStack grow="1" padding="20" backgroundColor="$surfaceAlt"><Text fontSize="18" color="$textMain">Commentary the LLM placed beside the block: what it means and what we do next.</Text></VStack>'
LAYOUT_CASES = ("one", "sparse", "many", "long", "odd", "narrow", "short")
NODE_CASES = ("side", "nested", "mixed", "missing", "invented", "refinref", "item", "tone", "dark")
SECOND = {"kpi_row": CHART, "card_grid": TABLE, "chart": TABLE, "timeline": KPIS, "table": CHART}
ALT = {"kpi_row": "rows", "card_grid": "banded", "chart": "rows", "timeline": "rail", "table": "ledger"}
DEFAULT = {"kpi_row": "grid", "card_grid": "grid", "chart": "native", "timeline": "columns", "table": "native"}


def layout_case(kind: str, case: str, variant: str) -> tuple[str, list[dict]]:
    comp = stress_plan(kind, case, variant)
    tag = bare_tag(kind, comp["component_id"], variant)
    if case == "narrow":
        return f'<HStack grow="1" gap="20"><VStack w="280">{tag}</VStack>{NOTE}</HStack>', [comp]
    if case == "short":
        return f'<VStack h="130">{tag}</VStack>{NOTE}', [comp]
    return tag, [comp]


def node_case(kind: str, case: str, variant: str) -> tuple[str, list[dict], str]:
    """(body, components, theme palette)."""
    nd = spec.nodes()[kind]
    comp, cid = plan_for(kind, variant), plan_for(kind, variant)["component_id"]
    tag = bare_tag(kind, cid, variant)
    gt = nd["tag"]
    if case == "side":
        o = SECOND[kind]
        return (f'<HStack grow="1" gap="20"><VStack w="1" grow="1">{tag}</VStack><VStack w="1" grow="1">'
                f'{bare_tag(o["kind"], o["component_id"], "")}</VStack></HStack>'), [comp, o], LIGHT
    if case == "nested":
        return ('<VStack grow="1" padding="20" gap="10" backgroundColor="$surfaceAlt" borderRadius="12">'
                '<Text fontSize="15" bold="true" color="$accentText" letterSpacing="1">THE PICTURE</Text>'
                f'<HStack grow="1" gap="14"><VStack w="1" grow="2" padding="14" backgroundColor="$surface" borderRadius="8">{tag}</VStack>'
                '<VStack w="1" grow="1" padding="14" backgroundColor="$surface" borderRadius="8"><Text fontSize="16" color="$textMain">So what: the note the LLM wrote.</Text></VStack>'
                '</HStack></VStack>'), [comp], LIGHT
    if case == "mixed":
        m = {"kpi_row": kpi(4, values=["$48.2M", "114%", "14 months", "0.33x"]),
             "card_grid": comp,
             "chart": chart_of(["Spend", "ROAS", "Share", "Orders"], ["₹31.2L", "2.8x", "41%", "1.9 L"]),
             "timeline": tl([{"date": "2026", "label": "FY plan"}, {"date": "Q3 FY26", "label": "Launch"}, {"date": "Nov 4", "label": "Now"}, {"date": "Week 52", "label": "Close"}]),
             "table": tb(["Metric", "H1", "H2"], [["Spend", "₹31.2L", "$48K"], ["ROAS", "2.8x", "3.1"], ["Share", "41%", "0.44"], ["Orders", "1.9 L", "190,000"]])}[kind]
        return bare_tag(kind, m["component_id"], variant), [m], LIGHT
    if case == "missing":
        m = {"kpi_row": C("kpis", "kpi_row", {"kpi_labels": LABELS[:4], "kpi_values": VALUES[:3], "kpi_deltas": DELTAS[:2], "kpi_tones": ["bogus"]}),
             "card_grid": C("levers", "card_grid", {"cards": [{"title": "Search"}, {"body": "A card with a body and no title"}, {"title": "", "bullets": ["only bullets"]}, {}]}),
             "chart": C("roas", "chart", {"chart_labels": ["A", "B", "C"], "chart_values": ["1x", "2x"]}),
             "timeline": tl([{"label": "No date"}, {"date": "Nov"}, {}]),
             "table": C("gaps", "table", {"table_rows": [["a", "b"], ["c"], ["d", "e", "f"]]})}[kind]
        return bare_tag(kind, m["component_id"], variant), [m], LIGHT
    if case == "invented":
        return bare_tag(kind, cid, variant, ' foo="1" x="40" items="3" label.fontSize="40" value.size="big" title.text="typed" nosuchpart.color="$accent"'), [comp], LIGHT
    if case == "refinref":
        o = SECOND[kind]
        return (f'<{gt} ref="{cid}" variant="{variant}" grow="1">{bare_tag(o["kind"], o["component_id"], "")}</{gt}>'), [comp, o], LIGHT
    if case == "item":
        inner = {"kpi_row": f'<Kpi ref="{cid}.2" value.color="$negativeText" item.backgroundColor="$warningSoft" />',
                 "card_grid": f'<Card ref="{cid}.1" title.color="$negativeText" item.backgroundColor="$warningSoft" />',
                 "chart": f'<ChartDataPoint ref="{cid}.1" bar.fill.color="$negative" />',
                 "timeline": f'<TimelineItem ref="{cid}.1" item.backgroundColor="$warningSoft" />',
                 "table": '<Highlight row="Discovery leakage" fill="bad" />'}[kind]
        return f'<{gt} ref="{cid}" variant="{variant}" grow="1">{inner}</{gt}>', [comp], LIGHT
    if case == "tone":
        a = {"kpi_row": ' item.borderLeft.color="$tone" item.borderLeft.width="5"', "card_grid": ' item.borderTop.color="$tone" item.borderTop.width="5"',
             "chart": ' bar.fill.color="$tone" title.color="$toneText"', "timeline": ' marker.fill.color="$tone" title.color="$toneText"',
             "table": ' label.color="$toneText" stripe.backgroundColor="$toneSoft"'}[kind]
        return bare_tag(kind, cid, variant, a), [comp], LIGHT
    return tag, [comp], DARK   # dark


def small_sheet(rows: list[tuple[str, list[tuple[str, str, Path | None]]]], path: Path, cols: int, w: int = 330) -> None:
    """Rows of shots, a verdict colour on each frame: green PASS, amber WARN, red BREAK."""
    import pymupdf
    from PIL import Image, ImageDraw
    h, gap, lab = w * 9 // 16, 8, 16
    img = Image.new("RGB", (cols * (w + gap) + gap, len(rows) * (h + lab + gap) + gap), "white")
    draw = ImageDraw.Draw(img)
    ink = {"PASS": "#2E7D32", "WARN": "#E08600", "BREAK": "#C62828"}
    for r, (_, shots) in enumerate(rows):
        for k, (name, v, pdf) in enumerate(shots):
            x, y = gap + k * (w + gap), gap + r * (h + lab + gap)
            draw.text((x, y + 2), f"{name} {v}", fill=ink.get(v, "black"))
            if pdf and Path(pdf).exists():
                page = pymupdf.open(pdf)[0]
                pix = page.get_pixmap(matrix=pymupdf.Matrix(w / page.rect.width, h / page.rect.height))
                img.paste(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), (x, y + lab))
            for t in range(2):
                draw.rectangle([x - 1 - t, y + lab - 1 - t, x + w + t, y + lab + h + t], outline=ink.get(v, "#999999"))
    img.save(path)


def cmd_stress(args: argparse.Namespace) -> int:
    kinds = [k for k in (args.only or NODE_KINDS) if k in NODE_KINDS]
    themes = {LIGHT: resolve_theme(LIGHT)["element"], DARK: resolve_theme(DARK)["element"]}
    store = DOCS / "stress.json"
    results = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
    for kind in kinds:
        results.setdefault(kind, {})
        jobs = []
        for variant in spec.nodes()[kind]["compositions"]:
            for case in LAYOUT_CASES:
                if not args.cases or case in args.cases:
                    body, comps = layout_case(kind, case, variant)
                    jobs.append((variant, case, body, comps, LIGHT))
        for variant in dict.fromkeys((DEFAULT[kind], ALT[kind])):
            for case in NODE_CASES:
                if not args.cases or case in args.cases:
                    body, comps, pal = node_case(kind, case, variant)
                    jobs.append((variant, case, body, comps, pal))
        for k in range(0, len(jobs), 8):   # small batches: compile, then one LibreOffice
            chunk, done = jobs[k:k + 8], []
            for variant, case, body, comps, pal in chunk:
                d = OUT / "stress" / kind / slug(variant) / case
                try:
                    r = compile_slide(d, TG.slide("STRESS", f"{kind} {variant}: {case}", body), comps, themes[pal], "")
                except Exception as e:
                    d.mkdir(parents=True, exist_ok=True)
                    r = {"compiled": False, "compile_errors": [f"expander crash {type(e).__name__}: {e}"[:160]], "node_issues": [], "node_ok": False}
                done.append((variant, case, comps, d, r))
            render_batch([x[3] for x in done])
            for variant, case, comps, d, r in done:
                r = measure(d, comps, r)
                v, why = verdict(r)
                results[kind].setdefault(variant, {})[case] = {
                    "verdict": v, "cause": why, "fonts": r.get("fonts"), "composition": {c: i.get("composition") for c, i in (r.get("components") or {}).items()},
                    "codes": sorted({i["code"] for i in r["node_issues"]}), "warnings": r.get("warnings"), "geom": sorted(set(r.get("geom") or [])),
                    "missing": (r.get("missing") or [])[:3], "broken": (r.get("broken") or [])[:3], "overlap": (r.get("overlap") or [])[:3],
                    "normalize": r.get("normalize"), "compile_errors": r.get("compile_errors")}
                print(kind, variant, case, v, why, flush=True)
            store.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        stress_sheets(kind, results)
    return 0


def stress_sheets(kind: str, results: dict) -> None:
    """Two sheets: layout cases per variant, node-level cases of the two variants that ran them."""
    for cases, name in ((LAYOUT_CASES, f"stress-{kind}.png"), (NODE_CASES, f"stress-{kind}-node.png")):
        rows = []
        for variant, cs in results[kind].items():
            shots = [(f"{variant} {c}", cs[c]["verdict"], OUT / "stress" / kind / slug(variant) / c / "presentation.pdf") for c in cases if c in cs]
            if shots:
                rows.append((variant, shots))
        if rows:
            small_sheet(rows, DOCS / name, cols=max(len(s) for _, s in rows))


# ── atomic construction: small parts the LLM assembles, each drawn from the plan by ref ───────────────────────────────
#
# PROTOTYPE, in this script only. KPI parts use the real element_refs.fill_refs (via tiles.fill). Card and timeline parts
# (<Text ref="levers.0.title"/>, <Ul ref="levers.0.bullets"/>, <Icon ref="levers.0.icon"/>, <Text ref="roadmap.0.date"/>)
# do not exist: atomic_fill stands in for what a real fill would do. The "LLM output" is hand-written: no LLM was called.

ATOM_PX = {"title": 20, "tag": 12, "body": 17, "date": 14, "label": 21, "description": 16}


def atomic_fill(xml: str, comps: list[dict]) -> dict:
    """Card / timeline part refs -> text from the plan; missing / duplicate / unknown refs reported. Ids as the real
    expanders write them (cardt-, cardb-, card-<cid>-<i> on the nearest boxed stack), so that fit-grow treats peers alike."""
    from lxml import etree
    by = {c["component_id"]: c for c in comps if c["kind"] in ("card_grid", "timeline")}
    root = etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"))
    issues, seen = [], set()

    def flag(code: str, ref: str, msg: str) -> None:
        issues.append({"code": code, "severity": "error", "ref": ref, "message": msg})

    for el in list(root.iter()):
        if not isinstance(el.tag, str) or "ref" not in el.attrib:
            continue
        ref = el.get("ref")
        m = re.match(r"^(?P<cid>[\w-]+)\.(?P<i>\d+)\.(?P<f>\w+)$", ref)
        if not m or m["cid"] not in by:
            continue
        comp, i, f = by[m["cid"]], int(m["i"]), m["f"]
        items = (comp["content_data"].get("cards") if comp["kind"] == "card_grid" else comp["content_data"].get("timeline_items")) or []
        if i >= len(items):
            flag("NODE_REF_UNKNOWN", ref, f"{m['cid']} has {len(items)} items")
            el.getparent().remove(el)
            continue
        if ref in seen:
            flag("NODE_REF_DUPLICATE", ref, "placed twice")
            el.getparent().remove(el)
            continue
        seen.add(ref)
        item = items[i]
        del el.attrib["ref"]
        cid = m["cid"]
        if comp["kind"] == "timeline":
            d, h, x = str(item.get("date") or ""), *compose.split(str(item.get("label") or ""))
            val = {"date": d.upper(), "title": h, "description": str(item.get("description") or x)}.get(f)
            px = {"date": 14, "title": 21, "description": 16}.get(f)
        else:
            val = {"title": item.get("title"), "tag": str(item.get("tag") or "").upper(), "body": item.get("body")}.get(f)
            px = ATOM_PX.get(f, 17)
        if f == "icon":
            if item.get("icon"):
                el.set("name", item["icon"])
            else:
                el.getparent().remove(el)
            continue
        if f == "bullets":
            for b in item.get("bullets") or []:
                etree.SubElement(el, "Li").text = b
            if "fontSize" not in el.attrib:
                el.set("fontSize", "16")
            continue
        if val is None:
            flag("NODE_REF_UNKNOWN", ref, f"no field {f}")
            continue
        el.text = str(val)
        el.set("fontSize", str(px))
        if f == "title":
            el.set("id", f"cardt-{cid}-{i}")
        if f == "body":
            el.set("id", f"cardb-{cid}-{i}")
        p = el.getparent()
        while p is not None and p.tag in ("VStack", "HStack"):
            if p.get("backgroundColor") or p.get("border.color"):
                p.set("id", p.get("id") or f"card-{cid}-{i}")
                break
            p = p.getparent()
    for cid, comp in by.items():
        n = len((comp["content_data"].get("cards") if comp["kind"] == "card_grid" else comp["content_data"].get("timeline_items")) or [])
        for i in range(n):
            if not any(s.startswith(f"{cid}.{i}.") for s in seen):
                flag("NODE_ITEM_MISSING", f"{cid}.{i}", "item not on the slide")
    return {"xml": (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root), "issues": issues}


def compile_atomic(d: Path, xml: str, comps: list[dict], theme: str, head: str) -> dict:
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tag.xml").write_text(xml, encoding="utf-8")
    a = atomic_fill(xml, comps)
    r = compile_slide(d, a["xml"], comps, theme, head)
    (d / "tag.xml").write_text(xml, encoding="utf-8")
    r["node_issues"] += [{k: i.get(k) for k in ("code", "severity", "ref", "message")} for i in a["issues"]]
    return r


# hand-written, what the LLM would have to type (loops only save this script's lines: each item is spelled out in the XML)

def atom_kpi_rows() -> str:
    tones = KPIS["content_data"]["kpi_tones"]
    icons = KPIS["content_data"]["kpi_icons"]
    role = {"good": "positive", "bad": "negative", "watch": "warning"}
    rows = []
    for i in range(4):
        r = role[tones[i]]
        rule = f' borderTop.color="$border" borderTop.width="1"' if i else ""
        rows.append(f'<HStack grow="1" gap="18" alignItems="center" padding.top="10" padding.bottom="10"{rule}>'
                    f'<Icon name="{icons[i]}" variant="square-filled" bgColor="${r}Soft" color="${r}Text" />'
                    f'<VStack gap="4" grow="1"><Text ref="kpis.{i}.label" color="${r}Text" /><Text ref="kpis.{i}.note" color="${r}Text" /></VStack>'
                    f'<Text ref="kpis.{i}.value" color="${r}Text" textAlign="right" /></HStack>')
    return f'<VStack gap="0" grow="1" padding.left="8" padding.right="8">{"".join(rows)}</VStack>'


def atom_kpi_free() -> str:
    """A look no composition draws: the delta as a pill beside the value, the label under them (Genspark KPI-E)."""
    tones = KPIS["content_data"]["kpi_tones"]
    role = {"good": "positive", "bad": "negative", "watch": "warning"}
    cells = []
    for i in range(4):
        r = role[tones[i]]
        cells.append(f'<VStack w="1" grow="1" gap="10" padding="20" backgroundColor="$surfaceAlt" justifyContent="center">'
                     f'<HStack gap="12" alignItems="center"><Text ref="kpis.{i}.value" w="max" color="$textMain" />'
                     f'<HStack w="max" grow="0" padding="6" backgroundColor="${r}Soft" borderRadius="12"><Text ref="kpis.{i}.note" w="max" color="${r}Text" /></HStack></HStack>'
                     f'<Text ref="kpis.{i}.label" color="$textMuted" /></VStack>')
    return ('<VStack gap="14" grow="1">' + "".join(f'<HStack gap="14" grow="1">{"".join(cells[k:k + 2])}</HStack>' for k in (0, 2)) + "</VStack>")


def atom_card_banded() -> str:
    role = ["negative", "warning", "accent", "positive"]
    boxes = []
    for i in range(4):
        r = role[i] if i else "panelDark"
        band = "$panelDark" if i == 0 else f"${r}"
        ink = "$onPanelDark" if i == 0 else "$onAccent"
        boxes.append(f'<VStack w="1" grow="1" gap="0" backgroundColor="$surfaceAlt" border.color="$border" border.width="1">'
                     f'<HStack alignItems="center" backgroundColor="{band}" padding="14" gap="10">'
                     f'<Icon ref="levers.{i}.icon" size="22" color="{ink}" />'
                     f'<VStack grow="1"><Text ref="levers.{i}.title" bold="true" color="{ink}" /></VStack>'
                     f'<Text ref="levers.{i}.tag" w="max" bold="true" letterSpacing="1" color="{ink}" /></HStack>'
                     f'<VStack grow="1" gap="10" padding="18"><Text ref="levers.{i}.body" color="$textMuted" />'
                     f'<Ul ref="levers.{i}.bullets" fontSize="17" color="$textMuted" /></VStack></VStack>')
    return ('<VStack gap="18" grow="1">' + "".join(f'<HStack gap="18" grow="1">{"".join(boxes[k:k + 2])}</HStack>' for k in (0, 2)) + "</VStack>")


def atom_card_free() -> str:
    """A look no composition draws: title left, a 2-column card with body beside bullets, a tag pill at the top right."""
    rows = []
    for i in range(4):
        rows.append(f'<HStack grow="1" gap="24" padding="16" backgroundColor="$surfaceAlt" borderLeft.color="$accent" borderLeft.width="4" alignItems="center">'
                    f'<VStack w="22%" gap="6"><Icon ref="levers.{i}.icon" size="26" color="$accentText" /><Text ref="levers.{i}.title" bold="true" color="$textMain" /></VStack>'
                    f'<VStack w="1" grow="1"><Text ref="levers.{i}.body" color="$textMain" /></VStack>'
                    f'<VStack w="1" grow="1"><Ul ref="levers.{i}.bullets" color="$textMuted" /></VStack>'
                    f'<HStack w="max" grow="0" padding="6" backgroundColor="$accentSoft" borderRadius="10"><Text ref="levers.{i}.tag" w="max" bold="true" color="$accentText" /></HStack></HStack>')
    return f'<VStack gap="10" grow="1">{"".join(rows)}</VStack>'


def atom_timeline_rail() -> str:
    """The rail by hand: the half-unit grid of sequences.timeline_rail is the LLM's to get right."""
    n, top, bottom, dots = 4, [], [], ['<VStack w="1" grow="1" />']
    for k in range(n):
        txt = (f'<VStack w="1" grow="4" gap="4" padding="6"><Text ref="roadmap.{k}.date" bold="true" letterSpacing="1" textAlign="center" color="$accentText" />'
               f'<Text ref="roadmap.{k}.title" bold="true" textAlign="center" color="{"$accentText" if k == 2 else "$textMain"}" />'
               f'<Text ref="roadmap.{k}.description" textAlign="center" color="$textMuted" /></VStack>')
        (top if k % 2 == 0 else bottom).append(txt)
        line = '<Shape shapeType="rect" w="max" grow="1" h="3" fill.color="$border" />'
        gap = '<VStack w="max" grow="1" />'
        dots.append(f'<HStack w="1" grow="2" alignItems="center" gap="0">{line if k else gap}'
                    f'<Shape shapeType="ellipse" w="22" h="22" fill.color="{"$accent" if k == 2 else "$neutral"}" />{line if k < n - 1 else gap}</HStack>')
    dots.append('<VStack w="1" grow="1" />')
    bottom.insert(0, '<VStack w="1" grow="2" />')
    return ('<VStack grow="1" gap="14" justifyContent="center">'
            f'<HStack gap="0" alignItems="end">{"".join(top)}<VStack w="1" grow="2" /></HStack>'
            f'<HStack gap="0" alignItems="center">{"".join(dots)}</HStack>'
            f'<HStack gap="0" alignItems="start">{"".join(bottom)}</HStack></VStack>')


def atom_timeline_free() -> str:
    """A look no composition draws: the date inside a large marker, the head and detail under it, chevrons between."""
    cols = []
    for k in range(4):
        fill = "$accent" if k == 2 else "$surfaceAlt"
        ink = "$onAccent" if k == 2 else "$accentText"
        arrow = '<Icon name="arrow-right" size="22" color="$textMuted" alignSelf="center" />' if k < 3 else ""
        cols.append(f'<VStack w="1" grow="1" gap="10" alignItems="center"><VStack w="110" h="110" justifyContent="center" backgroundColor="{fill}" borderRadius="55">'
                    f'<Text ref="roadmap.{k}.date" bold="true" textAlign="center" color="{ink}" /></VStack>'
                    f'<Text ref="roadmap.{k}.title" bold="true" textAlign="center" color="$textMain" />'
                    f'<Text ref="roadmap.{k}.description" textAlign="center" color="$textMuted" /></VStack>{arrow}')
    return f'<HStack grow="1" gap="10" alignItems="center">{"".join(cols)}</HStack>'


ATOMIC_PROMPT = """## PARTS (code fills them from the plan; never type a word)
<Text ref="<id>.<i>.<field>"/> writes one field; <Ul ref="<id>.<i>.bullets"/> a card's bullets; <Icon ref="<id>.<i>.icon"/> its icon.
Fields: kpi_row label value note; card_grid title tag body; timeline date title description. No fontSize on a ref.
Every item needs every field the plan gives, in plan order. Build peers alike: same box, same parts, same order.
Boxes are yours: VStack / HStack with w, h, grow, gap, padding, backgroundColor, border, borderRadius, in $tokens.
Equal columns: w="1" grow="1". Equal rows: grow="1". Value at the right: textAlign="right" in a w="max" Text. Dots and lines: Shape.
Tones: good -> $positive*, bad -> $negative*, watch -> $warning*, none -> $accent*; write the token per item from the plan's line.
Dark fill: text $onPanelDark. Icon names exactly from the list. A rail with text above and below: n + 1 units, dot k at unit k + 1,
each text two units wide; odd items below. Dividers: borderTop on every row after the first."""


def peer_sizes(d: Path, prefix: str) -> list[float]:
    f = d / "fitted.xml"
    x = f.read_text(encoding="utf-8") if f.exists() else (d / "in.xml").read_text(encoding="utf-8")
    return [float(m) for m in re.findall(rf'<Text\b[^>]*?id="{prefix}[^"]*"[^>]*?fontSize="([\d.]+)"', x)] + \
           [float(m) for m in re.findall(rf'<Text\b[^>]*?fontSize="([\d.]+)"[^>]*?id="{prefix}[^"]*"', x)]


def cmd_atomic(args: argparse.Namespace) -> int:
    theme = resolve_theme(LIGHT)["element"]
    samples = [
        ("kpi_row", "rows", KPIS, atom_kpi_rows(), atom_kpi_free(), "kpiv", HEADS["kpi_row"]),
        ("card_grid", "banded", CARDS, atom_card_banded(), atom_card_free(), "cardt", HEADS["card_grid"]),
        ("timeline", "rail", TIMELINE, atom_timeline_rail(), atom_timeline_free(), "card-roadmap", HEADS["timeline"]),
    ]
    out, rows = {}, []
    for kind, variant, comp, atom, free, peer, head in samples:
        tag = bare_tag(kind, comp["component_id"], variant)
        arms = {"composition": (tag, False), "atomic": (atom, True), "atomic free": (free, True)}
        dirs, res = {}, {}
        for arm, (xml, is_atom) in arms.items():
            d = OUT / "atomic" / kind / slug(arm)
            dirs[arm] = d
            s = TG.slide("AUDIT", head, xml)
            res[arm] = compile_atomic(d, s, [comp], theme, head) if is_atom else compile_slide(d, s, [comp], theme, head)
        render_batch(list(dirs.values()))
        out[kind] = {}
        for arm, d in dirs.items():
            r = measure(d, [comp], res[arm])
            sizes = peer_sizes(d, peer)
            out[kind][arm] = {"tokens": tokens(arms[arm][0]), "chars": len(arms[arm][0]), "verdict": verdict(r), "fonts": r.get("fonts"),
                              "peers": sizes, "fitGrow": r.get("fitGrow"), "codes": sorted({i["code"] for i in r["node_issues"]})}
            print(kind, arm, out[kind][arm]["tokens"], out[kind][arm]["verdict"], sizes, flush=True)
        out[kind]["pixel_diff_composition_atomic"] = CT.pixel_diff(dirs["composition"] / "presentation.pdf", dirs["atomic"] / "presentation.pdf")
        rows.append((kind, [(f"{kind} {a}", dirs[a] / "presentation.pdf" if (dirs[a] / "presentation.pdf").exists() else None) for a in arms]))
    CT.sheet_rows(rows, DOCS / "atomic.png", cols=3)
    # the mistakes an LLM can make: what does the validator see?  KPI: the real fill_refs. Cards: the prototype.
    k = atom_kpi_rows()
    c = atom_card_banded()
    faults = {
        "kpi item left out": (re.sub(r'<Text ref="kpis\.3\.\w+"[^>]*/>', "", k), KPIS),
        "kpi fields swapped (value <-> note, one item)": (k.replace('kpis.1.value', '__T').replace('kpis.1.note', 'kpis.1.value').replace('__T', 'kpis.1.note'), KPIS),
        "kpi items swapped (value 0 <-> value 1)": (k.replace('kpis.0.value', '__T').replace('kpis.1.value', 'kpis.0.value').replace('__T', 'kpis.1.value'), KPIS),
        "kpi same ref twice": (k.replace('kpis.1.value', 'kpis.0.value'), KPIS),
        "kpi index past the plan": (k.replace('kpis.3.value', 'kpis.7.value'), KPIS),
        "kpi word typed instead of a ref": (k.replace('<Text ref="kpis.2.value" color="$negativeText" textAlign="right" />', '<Text fontSize="40" color="$negativeText">99%</Text>'), KPIS),
        "kpi peer styled apart (one padding)": (k.replace('padding.top="10"', 'padding.top="40"', 1), KPIS),
        "card item left out": (re.sub(r'<(?:Text|Icon|Ul) ref="levers\.3\.\w+"[^>]*/>', "", c), CARDS),
        "card fields swapped (title <-> tag)": (c.replace('levers.1.title', '__T').replace('levers.1.tag', 'levers.1.title').replace('__T', 'levers.1.tag'), CARDS),
        "card field forgotten (no body on one card)": (re.sub(r'<Text ref="levers\.2\.body"[^>]*/>', "", c), CARDS),
        "card bullets forgotten on one card": (re.sub(r'<Ul ref="levers\.2\.bullets"[^>]*/>', "", c), CARDS),
        "card order changed": (c.replace('levers.0.', '__T').replace('levers.1.', 'levers.0.').replace('__T', 'levers.1.'), CARDS),
    }
    fault_rows = {}
    for name, (xml, comp) in faults.items():
        s = TG.slide("AUDIT", "H", xml)
        issues = []
        if comp["kind"] == "card_grid":
            issues += atomic_fill(s, [comp])["issues"]
            sx = atomic_fill(s, [comp])["xml"]
        else:
            sx = s
        issues += expand_only(sx, [comp], "H")["issues"]
        sev = sorted({f"{i['severity']}:{i['code']}" for i in issues})
        fault_rows[name] = {"caught": any(i["severity"] == "error" for i in issues), "codes": sev}
        print(name, fault_rows[name], flush=True)
    prompt = {"composition_node_lines": tokens(composed.node_lines()), "atomic_prompt": tokens(ATOMIC_PROMPT),
              "per_component_line": {kd: tokens(composed.prompt_line(plan_for(kd, ""), HEADS[kd])) for kd in NODE_KINDS}}
    (DOCS / "atomic.json").write_text(json.dumps({"samples": out, "faults": fault_rows, "prompt": prompt,
                                                  "atomic_xml": {s[0]: s[3] for s in samples}, "free_xml": {s[0]: s[4] for s in samples}},
                                                 indent=1, ensure_ascii=False), encoding="utf-8")
    print(prompt)
    return 0


# ── flexbox: what POM's Yoga does, measured ───────────────────────────────────────────────────────────────────────────

MEASURE_JS = """
import { pathToFileURL } from "node:url";
import { readFileSync } from "node:fs";
const fg = await import(pathToFileURL(process.argv[2]).href);
const jobs = JSON.parse(readFileSync(process.argv[3], "utf8"));
const out = {};
for (const [name, xml] of Object.entries(jobs)) {
  try {
    const L = await fg.layout(xml);
    const boxes = {};
    for (const root of L.slides) fg.walk(root, (n) => { if (n.id) { const b = L.box(n); boxes[n.id] = {w: +b.w.toFixed(1), h: +b.h.toFixed(1), x: +b.left.toFixed(1), y: +b.top.toFixed(1)}; } });
    out[name] = boxes;
    L.free();
  } catch (e) { out[name] = {error: String(e && e.message || e).slice(0, 300)}; }
}
process.stdout.write(JSON.stringify(out));
"""


def yoga_boxes(jobs: dict[str, str]) -> dict:
    """POM's own layout (fit-grow's `layout`, no fit-grow): {name: {id: {w, h, x, y}}}. x, y are relative to the parent."""
    d = OUT / "flex"
    d.mkdir(parents=True, exist_ok=True)
    js = d / "measure.mjs"
    js.write_text(MEASURE_JS, encoding="utf-8")
    (d / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
    p = subprocess.run(["node", str(js), str(ROOT / "src" / "node" / "fit-grow.js"), str(d / "jobs.json")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    if not p.stdout.strip():
        raise RuntimeError(p.stderr[-800:])
    return json.loads(p.stdout)


def S(body: str) -> str:
    return (f'<Theme surface="FFFFFF" surfaceAlt="EEF2F7" accent="2563EB" textMain="16202E" border="CBD5E1" /><Slide>'
            f'<VStack id="root" w="1280" h="720" padding="40" gap="16" backgroundColor="$surface">{body}</VStack></Slide>')


def B(i: str, attrs: str = "", text: str = "x", px: int = 18) -> str:
    return f'<VStack id="{i}" backgroundColor="$surfaceAlt" border.color="$border" border.width="1" {attrs}><Text fontSize="{px}" color="$textMain">{text}</Text></VStack>'


LOREM = "Organic share fell on every platform and the home banners cost twice as much for less than half the return"
def a_(attrs: str) -> str:
    """'w=300 grow=1' -> 'w="300" grow="1"' (Python 3.11 takes no backslash inside an f-string expression)."""
    return " ".join('{}="{}"'.format(*x.split("=")) for x in attrs.split())


FLEX_TESTS: dict[str, dict] = {
    "equal_no_w": {"q": "HStack children with no w: equal columns? (POM: basis 0, grow 1)", "xml": f'<HStack id="r" h="120" gap="10">{B("a", text="short")}{B("b", text=LOREM)}{B("c", text="mid length text")}</HStack>'},
    "equal_w1": {"q": 'the expanders\' w="1" grow="1": any different?', "xml": f'<HStack id="r" h="120" gap="10">{B("a", a_("w=1 grow=1"), "short")}{B("b", a_("w=1 grow=1"), LOREM)}{B("c", a_("w=1 grow=1"), "mid length text")}</HStack>'},
    "w_max_row": {"q": 'w="max" in an HStack: sized to content plus a share of the spare', "xml": f'<HStack id="r" h="120" gap="10">{B("a", a_("w=max"), "short")}{B("b", a_("w=max"), "much longer text in here")}</HStack>'},
    "w_max_col": {"q": 'w="max" in a VStack: grows the HEIGHT (flexGrow on the main axis)', "xml": f'<VStack id="r" h="400" gap="10">{B("a", a_("w=max"), "w max")}{B("b", "", "plain")}</VStack>'},
    "h_max_row": {"q": 'h="max" in an HStack: grows the WIDTH', "xml": f'<HStack id="r" h="200" gap="10">{B("a", a_("w=200 h=max"), "h max w200")}{B("b", a_("w=200"), "w200")}</HStack>'},
    "content_w": {"q": 'content-sized, no growth: w="max" grow="0"', "xml": f'<HStack id="r" h="100" gap="10">{B("a", a_("w=max grow=0"), "01")}{B("b", a_("w=max grow=0"), "a longer label")}{B("c", "", "the rest")}</HStack>'},
    "grow0_no_w": {"q": 'grow="0" with no w: the column collapses? (basis 0)', "xml": f'<HStack id="r" h="100" gap="10">{B("a", a_("grow=0"), "collapses?")}{B("b", "", "the rest")}</HStack>'},
    "rows_grow": {"q": 'VStack rows with grow="1", uneven content: equal heights?', "xml": f'<VStack id="r" h="500" gap="10">{B("a", a_("grow=1"), "one")}{B("b", a_("grow=1"), LOREM + " " + LOREM + " " + LOREM + " " + LOREM, 26)}{B("c", a_("grow=1"), "three")}</VStack>'},
    "rows_h1": {"q": 'the same with h="1" grow="1": equal heights?', "xml": f'<VStack id="r" h="500" gap="10">{B("a", a_("h=1 grow=1"), "one")}{B("b", a_("h=1 grow=1"), LOREM + " " + LOREM + " " + LOREM + " " + LOREM, 26)}{B("c", a_("h=1 grow=1"), "three")}</VStack>'},
    "rows_h1_over": {"q": 'h="1" grow="1" when one row needs more than its share: does it overflow?', "xml": f'<VStack id="r" h="300" gap="10">{B("a", a_("h=1 grow=1"), "one")}{B("b", a_("h=1 grow=1"), " ".join([LOREM] * 4), 26)}{B("c", a_("h=1 grow=1"), "three")}</VStack>'},
    "wrap_grid": {"q": 'flexWrap="wrap" + minW: a grid from flexbox alone?', "xml": '<HStack id="r" flexWrap="wrap" gap="10" w="1200" h="400">' + "".join(B(f"c{i}", 'minW="360"', f"tile {i}") for i in range(5)) + "</HStack>"},
    "wrap_w33": {"q": 'flexWrap with w="32%" children: lines and last row', "xml": '<HStack id="r" flexWrap="wrap" gap="10" w="1200" h="400">' + "".join(B(f"c{i}", 'w="32%"', f"tile {i}") for i in range(5)) + "</HStack>"},
    "wrap_stretch": {"q": "do wrapped lines take the box's height? (POM sets no alignContent)", "xml": '<HStack id="r" flexWrap="wrap" gap="10" w="1200" h="500">' + "".join(B(f"c{i}", 'w="48%" grow="1"', f"tile {i}") for i in range(4)) + "</HStack>"},
    "stretch_default": {"q": 'alignItems default: stretch? (peers in a row, no alignItems)', "xml": f'<HStack id="r" gap="10">{B("a", a_("w=300"), "short")}{B("b", a_("w=300"), LOREM + LOREM)}</HStack>'},
    "squeeze": {"q": "narrow column: a word wider than its box (Yoga has no min-content)", "xml": f'<HStack id="r" h="120" gap="10">{B("a", a_("w=60"), "Internationalisation")}{B("b", "", "the rest")}</HStack>'},
    "shrink": {"q": "children too wide for the row: all shrink evenly, min width ignored?", "xml": f'<HStack id="r" w="600" h="100" gap="10">{B("a", a_("w=400"), "a")}{B("b", a_("w=400"), "b")}{B("c", a_("w=400 minW=300"), "c")}</HStack>'},
    "over_height": {"q": "content taller than the slide: Yoga shrinks children below their text", "xml": "".join(B(f"c{i}", "", " ".join([LOREM] * 3), 28) for i in range(5))},
    "absolute_child": {"q": 'position="absolute" inside a box: a badge anchored to its parent, no slide pixels', "xml": f'<VStack id="p" w="400" h="200" backgroundColor="$surfaceAlt"><Text fontSize="18" color="$textMain">card</Text><VStack id="badge" position="absolute" top="8" right="8" w="40" h="40" backgroundColor="$accent" /></VStack>'},
    "negative_margin": {"q": "negative margin: can a block overlap its neighbour?", "xml": f'<HStack id="r" h="100" gap="0">{B("a", a_("w=300"), "a")}{B("b", a_("w=300 margin.left=-40"), "b")}</HStack>'},
    "justify_between": {"q": 'justifyContent="spaceBetween": value at the far right without widths', "xml": '<HStack id="r" h="60" justifyContent="spaceBetween" alignItems="center"><VStack id="a" w="max" grow="0"><Text fontSize="18" color="$textMain">Label</Text></VStack><VStack id="b" w="max" grow="0"><Text fontSize="24" color="$textMain">$48.2M</Text></VStack></HStack>'},
    "text_grow0": {"q": 'grow="0" on a Text: POM rejects it (stacks take it)', "xml": '<HStack id="r" h="60"><Text id="a" w="max" grow="0" fontSize="18" color="$textMain">Label</Text></HStack>'},
    "rows_cols_align": {"q": "columns across sibling rows: content-sized leads do not line up", "xml": "".join(f'<HStack id="r{i}" h="50" gap="10">{B(f"a{i}", a_("w=max grow=0"), t)}{B(f"b{i}", "", "bar")}</HStack>' for i, t in enumerate(("Search", "Category listing ads", "Brand")))},
    "pct_vs_px": {"q": 'w="%" resolves against the parent content box', "xml": f'<HStack id="r" w="1000" padding="50" gap="10" h="80">{B("a", a_("w=50%"), "a")}{B("b", "", "b")}</HStack>'},
    "text_box_fills": {"q": "a box grows, its type does not: flexbox sizes boxes, never fonts", "xml": f'<VStack id="r" h="500">{B("a", a_("grow=1"), "$48.2M", 28)}</VStack>'},
}


def flex_real() -> dict:
    """Before / after on real expansions, by string edits to what the expander wrote (src/ untouched). Each `after` is what
    the proposed expander change would write. Rendered through the full pipeline."""
    uneven = C("levers", "card_grid", {"card_layout": "grid", "cards": [
        {"title": "Search", "icon": "search", "body": "Organic share fell on every platform"},
        {"title": "Placement", "icon": "store", "body": "Home banners cost 2x and return 0.4x",
         "bullets": ["Cap home banners", "Test category tiles", "Shift to Hyderabad", "Review weekly", "Cut the worst slots"]},
        {"title": "Pricing", "icon": "badge-percent", "body": "Regular price sits above two rivals"},
        {"title": "Retention", "icon": "repeat", "body": "Repeat buyers are 41% of revenue"}]})
    long_t = C("gaps", "table", {"table_columns": ["Metric", "H1", "H2"], "table_rows": [
        ["Spend", "₹31.2L", "₹48L"], ["A long row whose first cell runs on to fill two or three lines", "2.8x", "A longer second cell that wraps to several lines in its column as well"],
        ["Share", "41%", "44%"]]})
    def exp(tag: str, comp: dict, head: str) -> str:
        return expand_only(TG.slide("FLEX", head, tag), [comp], head)["xml"]
    out = {}
    head = "Peers in a grid share a height"
    x = exp(bare_tag("card_grid", "levers", "banded"), uneven, head)
    out["equal_rows_cards"] = {"note": 'card_grid banded, rows of a grid: grow="1" -> h="1" grow="1" (equal row heights)', "comp": uneven, "head": head,
                               "before": x, "after": x.replace('<HStack gap="18" grow="1" alignItems="stretch"', '<HStack gap="18" h="1" grow="1"')}
    head = "Peers in a table's rows share a height"
    x = exp(bare_tag("table", "gaps", "grid"), long_t, head)
    out["equal_rows_table"] = {"note": 'table grid: row HStacks grow="1" -> h="1" grow="1"', "comp": long_t, "head": head, "before": x,
                               "after": x.replace('<HStack grow="1" gap="10" alignItems="stretch"', '<HStack h="1" grow="1" gap="10"')}
    head = "Search takes the budget and returns the least"
    lc = C("roas", "chart", {"chart_title": "ROAS", "chart_labels": ["Generic search", "PLA", "Brand", "Competitor conquesting ads"], "chart_values": ["0.29x", "0.80x", "0.99x", "0.15x"], "chart_type": "bar"}, "accent Generic search")
    x = exp(bare_tag("chart", "roas", "rows"), lc, head)
    out["chart_rows_widths"] = {"note": 'chart rows: lead w="24%" and value w="16%" -> value column content-sized (w="max" grow="0"): the bars keep the width the 16% wasted, but values no longer line up', "comp": lc, "head": head,
                                "before": x, "after": re.sub(r'<VStack w="16%"', '<VStack w="max" grow="0"', x)}
    x = exp(bare_tag("kpi_row", "kpis", "grid"), KPIS, CC.KPI_HEAD)
    out["drop_w1"] = {"note": 'all: w="1" grow="1" on an HStack child -> nothing (POM already gives basis 0, grow 1); alignItems="stretch" -> nothing', "comp": KPIS, "head": CC.KPI_HEAD, "before": x,
                      "after": x.replace(' alignItems="stretch"', '').replace(' w="1" grow="1"', '')}
    head = "A sparse slide centres its body by flexbox"
    lines = "".join(f'<Text id="l{i}" fontSize="22" color="$textMain">{t}</Text>' for i, t in enumerate(("One short line", "A second line", "A third line")))
    frame = ('<Slide><VStack w="1280" h="720" padding="48" gap="26" backgroundColor="$surface"><Text fontSize="34" bold="true" color="$textMain">' + head + '</Text>{}</VStack></Slide>')
    out["centre_body"] = {"note": 'fit-grow centreBody writes margin.top = free / 2 -> the body band as grow="1" justifyContent="center"', "comp": None, "head": head,
                          "before": frame.format(f'<VStack id="body" gap="10">{lines}</VStack>'),
                          "after": "<!-- fit-grow: off -->" + frame.format(f'<VStack id="body" gap="10" grow="1" justifyContent="center">{lines}</VStack>')}
    x = exp(bare_tag("kpi_row", "kpis", "banded"), KPIS, CC.KPI_HEAD)
    out["delta_pill"] = {"note": 'spec F (hero note pill): Text has no box, but delta.highlight="$toneSoft" (allowed today) draws a tinted run', "comp": KPIS, "head": CC.KPI_HEAD,
                         "before": exp(bare_tag("kpi_row", "kpis", "grid"), KPIS, CC.KPI_HEAD),
                         "after": exp(bare_tag("kpi_row", "kpis", "grid", ' delta.highlight="$toneSoft"'), KPIS, CC.KPI_HEAD)}
    out["band_height"] = {"note": 'KPI banded: bands of 1 and 2 lines put the values out of line; band.minH (allowed today, the LLM can write it) -> one band height', "comp": KPIS, "head": CC.KPI_HEAD, "before": x,
                          "after": exp(bare_tag("kpi_row", "kpis", "banded", ' band.minH="70"'), KPIS, CC.KPI_HEAD)}
    return out


def cmd_flex(args: argparse.Namespace) -> int:
    boxes = yoga_boxes({k: S(v["xml"]) for k, v in FLEX_TESTS.items()})
    results = {k: {"q": v["q"], "boxes": boxes[k]} for k, v in FLEX_TESTS.items()}
    for k, v in results.items():
        print(k, v["q"], json.dumps({i: (b if isinstance(b, str) else [b["x"], b["y"], b["w"], b["h"]]) for i, b in v["boxes"].items() if i != "root"}), flush=True)
    theme = resolve_theme(LIGHT)["element"]
    dirs = []
    for k, v in FLEX_TESTS.items():
        d = OUT / "flex" / k
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        x = "<!-- fit-grow: off -->" + S(v["xml"])
        (d / "in.xml").write_text(x, encoding="utf-8")
        subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)], capture_output=True, timeout=300)
        dirs.append(d)
    render_batch(dirs)
    rows = [(k, [(k, (OUT / "flex" / k / "presentation.pdf") if (OUT / "flex" / k / "presentation.pdf").exists() else None)]) for k in FLEX_TESTS]
    tiled = [("", [s for _, g in rows[i:i + 5] for s in g]) for i in range(0, len(rows), 5)]
    CT.sheet_rows(tiled, DOCS / "flex-probes.png", cols=5)
    # before / after through the whole pipeline (fit-grow on)
    real, sheet = {}, []
    for k, v in flex_real().items():
        pair = {}
        ds = []
        for arm in ("before", "after"):
            d = OUT / "flex" / "real" / k / arm
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
            norm = normalize_xml(deck_font(v[arm]))
            (d / "in.xml").write_text(ensure_single_theme(norm["cleaned_xml"], theme), encoding="utf-8")
            p = subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            res = json.loads((d / "compile-result.json").read_text(encoding="utf-8")) if (d / "compile-result.json").exists() else {}
            pair[arm] = {"compiled": (d / "presentation.pptx").exists(), "fitGrow": res.get("fitGrow") or [], "warnings": sorted({w.get("code") for w in res.get("warnings") or []}),
                         "tokens": tokens(v[arm]), "fonts": None}
            ds.append(d)
        render_batch(ds)
        for arm, d in zip(("before", "after"), ds):
            if pair[arm]["compiled"]:
                pair[arm]["fonts"] = font_stats(d)
                pair[arm]["geom"] = sorted(set(geometry_codes(d)))
                fx = (d / "fitted.xml") if (d / "fitted.xml").exists() else (d / "in.xml")
                pair[arm]["sizes"] = sorted({float(s) for s in re.findall(r'fontSize="([\d.]+)"', fx.read_text(encoding="utf-8"))})
        pair["diff"] = CT.pixel_diff(ds[0] / "presentation.pdf", ds[1] / "presentation.pdf")
        pair["note"] = v["note"]
        real[k] = pair
        sheet.append((k, [(f"{k} before", ds[0] / "presentation.pdf"), (f"{k} after", ds[1] / "presentation.pdf")]))
        print(k, json.dumps({a: {x: pair[a].get(x) for x in ("tokens", "warnings", "fonts", "geom")} for a in ("before", "after")}), "diff", pair["diff"], flush=True)
    CT.sheet_rows(sheet, DOCS / "flex-before-after.png", cols=2)
    (DOCS / "flex.json").write_text(json.dumps({"probes": results, "real": real}, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


# ── census: which layout features are used ────────────────────────────────────────────────────────────────────────────

CENSUS_ATTRS = ("grow", "gap", "alignItems", "justifyContent", "flexWrap", "alignSelf", "minW", "maxW", "minH", "maxH", "margin", "padding", "position")
MAIN = Path(r"C:\dev\presentation-pipeline\presentation-pipeline\output")
LLM_SOURCES = {   # first LLM output of paid runs only: galleries, replays and mocked unit-test runs left out
    "free XML (no refs)": [("old_zips", "input.xml"), ("step0", "input.xml"), ("colour-roles", "input.xml"), ("critic-on", "input.xml"), ("critic-on2", "input.xml")],
    "KPI element refs": [("tile-combined/combined/A", "first.xml"), ("kpi-decks-2", "first-generated.xml")],
    "tile / card tags": [("tile-combined/combined/B", "first.xml")],
}
_TAG = re.compile(r"<(VStack|HStack|Layer|Text|Shape|Line|Arrow|Icon|Ul|Table|Chart|Timeline|ProcessArrow|Flow|Pyramid|Tree|Matrix|KpiGrid|KpiRow|Kpi|CardGrid|Card)\b([^<>]*)")
_A = re.compile(r'([\w.:-]+)="([^"]*)"')


def size_class(v: str | None) -> str:
    if v is None:
        return "none"
    if v == "max":
        return "max"
    if v.endswith("%"):
        return "percent"
    if v == "1":
        return "1 (flex share)"
    return "px"


def census_xml(texts: list[str]) -> dict:
    c: dict[str, Any] = {"slides": len(texts), "elements": {}, "stacks": 0, "attrs": {}, "values": {}, "w": {}, "h": {}, "text_w": {}, "aliases": {}}
    for x in texts:
        for m in _TAG.finditer(x):
            tag, a = m.group(1), dict(_A.findall(m.group(2)))
            c["elements"][tag] = c["elements"].get(tag, 0) + 1
            stack = tag in ("VStack", "HStack")
            if stack:
                c["stacks"] += 1
                c["w"][size_class(a.get("w"))] = c["w"].get(size_class(a.get("w")), 0) + 1
                c["h"][size_class(a.get("h"))] = c["h"].get(size_class(a.get("h")), 0) + 1
            for k in CENSUS_ATTRS:
                hit = [p for p in a if p == k or p.startswith(k + ".")]
                if hit:
                    c["attrs"][k] = c["attrs"].get(k, 0) + 1
                    if k in ("alignItems", "justifyContent", "alignSelf", "flexWrap", "position"):
                        vs = c["values"].setdefault(k, {})
                        vs[a[hit[0]]] = vs.get(a[hit[0]], 0) + 1
            for name in ("variant", "layout", "arrange", "cols"):
                if tag in ("KpiGrid", "KpiRow", "CardGrid", "Kpi", "Card") and name in a:
                    key = f"{tag} {name}={a[name]}"
                    c["aliases"][key] = c["aliases"].get(key, 0) + 1
    return c


def collect(top: str, name: str) -> list[str]:
    seen, out = set(), []
    for dp, _, fn in os.walk(MAIN / top):
        if name in fn:
            x = Path(dp, name).read_text(encoding="utf-8", errors="replace")
            h = hashlib.sha1(x.encode("utf-8", "replace")).hexdigest()
            if h not in seen:
                seen.add(h)
                out.append(x)
    return out


def expander_source_census() -> dict:
    """Literal layout sizes in the expander source, one row per file."""
    out = {}
    for f in ("tiles", "cards", "tile_groups", "charts", "tables"):
        s = (ROOT / "src" / "compiler" / "nodes" / f"{f}.py").read_text(encoding="utf-8")
        out[f] = {"w_px": len(re.findall(r'\bw="?\\?"?\d{2,}', s)) + len(re.findall(r'"w":\s*"\d{2,}"', s)),
                  "w_pct": len(re.findall(r'w="?\d+%', s)) + len(re.findall(r'"w":\s*"\d+%"', s)),
                  "w1_grow": len(re.findall(r'w="1" grow=', s)) + len(re.findall(r'"w":\s*"1"', s)) + len(re.findall(r'set\("w", "1"\)', s)),
                  "stretch": s.count('alignItems="stretch"') + s.count('"alignItems": "stretch"'), "grow": len(re.findall(r'grow=|"grow"', s))}
    seq = _git_show("src/compiler/nodes/sequences.py")
    out["sequences (timeline branch)"] = {"w_px": len(re.findall(r'\bw="\d{2,}', seq)) + len(re.findall(r'"w":\s*"\d{2,}"', seq)), "w_pct": len(re.findall(r'w="\d+%', seq)),
                                          "w1_grow": len(re.findall(r'w="1" grow=', seq)), "stretch": seq.count('alignItems="stretch"'), "grow": len(re.findall(r'grow=|"grow"', seq))}
    return out


def fit_grow_phases() -> dict:
    s = (ROOT / "src" / "node" / "fit-grow.js").read_text(encoding="utf-8")
    return {"lines": s.count("\n"), "functions": len(re.findall(r"^(?:async )?function ", s, re.M)), "fitSlide_phases": len(re.findall(r"await (\w+)\(xml, report", s))}


def cmd_census(args: argparse.Namespace) -> int:
    out: dict[str, Any] = {"llm": {}, "expanders_source": expander_source_census(), "fit_grow": fit_grow_phases()}
    for name, srcs in LLM_SOURCES.items():
        texts = [x for top, f in srcs for x in collect(top, f)]
        out["llm"][name] = census_xml(texts)
        print(name, out["llm"][name]["slides"], flush=True)
    store = DOCS / "catalogue.json"
    if store.exists():
        es = [e for e in json.loads(store.read_text(encoding="utf-8")) if e.get("built")]
        out["code"] = census_xml([e["expanded"] for e in es])
    (DOCS / "census.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in ("slides", "stacks", "attrs", "values", "w", "h")} for k, v in {**out["llm"], "code": out.get("code", {"slides": 0, "stacks": 0, "attrs": {}, "values": {}, "w": {}, "h": {}})}.items()}, indent=0))
    print(out["expanders_source"], out["fit_grow"])
    return 0


def cmd_remeasure(args: argparse.Namespace) -> int:
    """The measures and verdicts of saved slides again, after a checker fix (no compile, no render)."""
    store = DOCS / "catalogue.json"
    entries = json.loads(store.read_text(encoding="utf-8"))
    for e in entries:
        base = OUT / "catalogue" / e["kind"] / slug(e["variant"])
        for arm in ("tag", "styled", "full", "hand"):
            if arm + "_result" not in e:
                continue
            d = base / arm if e["built"] else base
            comps = [e["plan"]]
            e[arm + "_result"] = measure(d, comps, e[arm + "_result"])
            e[arm + "_verdict"] = verdict(e[arm + "_result"])
        print(e["kind"], e["variant"], {a: e[a + "_verdict"] for a in ("tag", "styled", "full", "hand") if a + "_verdict" in e}, flush=True)
    store.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    write_catalogue_md(entries)
    return 0


def cmd_duplicates(args: argparse.Namespace) -> int:
    """What a duplicated attribute costs, through the whole pipeline (consistency.json `duplicates` lists them all)."""
    theme = resolve_theme(LIGHT)["element"]
    cases = [("kpi_row", "strip", ' alignItems="center"'), ("kpi_row", "banded", ' alignItems="center"'), ("kpi_row", "bento", ' alignItems="center"'),
             ("chart", "native", ' alignItems="center"'), ("timeline", "rail", ' gap="20"'), ("timeline", "columns", ' gap="20"'),
             ("table", "rows", ' gap="20"'), ("table", "grid", ' gap="20"'), ("table", "ledger", ' item.padding="10"'), ("kpi_row", "grid", ' alignItems="center"')]
    out, dirs = {}, []
    for kind, variant, attr in cases:
        comp = plan_for(kind, variant)
        d = OUT / "duplicates" / slug(f"{kind} {variant}")
        r = compile_slide(d, TG.slide("AUDIT", HEADS[kind], bare_tag(kind, comp["component_id"], variant, attr)), [comp], theme, HEADS[kind])
        out[f"{kind} {variant}{attr}"] = {"compiled": r["compiled"], "node_ok": r["node_ok"], "errors": (r.get("compile_errors") or [""])[0][:160],
                                          "lost": len(missing_words([comp], d / "presentation.pptx")) if r["compiled"] else None, "of": len(plan_strings(comp)),
                                          "codes": sorted({i["code"] for i in r["node_issues"]})}
        print(f"{kind} {variant}{attr}", out[f"{kind} {variant}{attr}"], flush=True)
        dirs.append(d)
    # one duplicate anywhere on the slide: tiles.fill cannot parse it, so the KPI refs of another block stay empty
    d = OUT / "duplicates" / "table-gap-blanks-kpi"
    body = bare_tag("kpi_row", "kpis", "grid") + bare_tag("table", "gaps", "rows", ' gap="20"')
    r = compile_slide(d, TG.slide("AUDIT", "A gap on the table blanks the KPI row beside it", body), [KPIS, TABLE], theme, "H")
    out["kpi_row grid beside table rows gap"] = {"compiled": r["compiled"], "node_ok": r["node_ok"], "codes": sorted({i["code"] for i in r["node_issues"]}),
                                                 "lost": len(missing_words([KPIS], d / "presentation.pptx")), "of": len(plan_strings(KPIS))}
    print(out["kpi_row grid beside table rows gap"], flush=True)
    dirs.append(d)
    render_batch(dirs)
    CT.sheet_rows([("x", [('KpiRow strip alignItems="center"', dirs[0] / "presentation.pdf"), ('Table rows gap="20" beside a KpiRow', d / "presentation.pdf")])], DOCS / "duplicates.png", cols=2)
    (DOCS / "duplicates.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


def cmd_tables(args: argparse.Namespace) -> int:
    """stress.json as the markdown tables of the report (docs/eval/syntax-audit/stress-table.md)."""
    res = json.loads((DOCS / "stress.json").read_text(encoding="utf-8"))
    mark = {"PASS": "✓", "WARN": "~", "BREAK": "✗"}
    L = ["# Stress table (generated: `python -m scripts.syntax_audit tables`)", "",
         "✓ pass, ~ warn, ✗ break, by the automatic checks (words lost, overlap, broken words, spill, compile, node errors); blank = not run. "
         "The report's reading by eye comes on top.", ""]
    cases = list(LAYOUT_CASES) + list(NODE_CASES)
    for kind in NODE_KINDS:
        if kind not in res:
            continue
        L += [f"## {kind}", "", "| variant | " + " | ".join(cases) + " |", "|---|" + "---|" * len(cases)]
        for v, cs in res[kind].items():
            L.append(f"| {v} | " + " | ".join(mark[cs[c]["verdict"]] if c in cs else "" for c in cases) + " |")
        L += ["", "| variant | case | verdict | cause | drawn as | codes |", "|---|---|---|---|---|---|"]
        for v, cs in res[kind].items():
            for c, r in cs.items():
                if r["verdict"] != "PASS":
                    drawn = ",".join(sorted(set(str(x) for x in (r.get("composition") or {}).values())))
                    cause = str(r["cause"]).replace("|", "/")[:110]
                    L.append(f'| {v} | {c} | {r["verdict"]} | {cause} | {drawn} | {" ".join(r["codes"])[:90]} |')
        L.append("")
    (DOCS / "stress-table.md").write_text("\n".join(L), encoding="utf-8")
    for kind in res:
        stress_sheets(kind, res)
    tot = {m: sum(1 for k in res.values() for cs in k.values() for r in cs.values() if r["verdict"] == m) for m in mark}
    print(tot)
    return 0


def cmd_bisect(args: argparse.Namespace) -> int:
    """Which attributes of the every-attribute tag make the text vanish (KPI strip)?"""
    theme = resolve_theme(LIGHT)["element"]
    base = allowed_attributes("kpi_row")
    groups = {"none": lambda k: False, "marker.*": lambda k: k.startswith("marker."), "item sizing": lambda k: k.split(".")[-1] in ("w", "h", "grow", "minW", "maxW", "minH", "maxH", "alignSelf", "margin") and k.startswith("item."),
              "group sizing": lambda k: k in ("w", "h", "minW", "maxW", "minH", "maxH", "alignSelf", "margin"), "item.padding*": lambda k: k.startswith("item.padding"), "band.*": lambda k: k.startswith("band."), "alignItems+justify": lambda k: k.split(".")[-1] in ("alignItems", "justifyContent"),
              "textGradient": lambda k: k.endswith("textGradient"), "outline+glow": lambda k: "outline" in k or "glow" in k}
    out = {}
    for name, drop in groups.items():
        attrs = "".join(f' {k}="{SAMPLE.get(k.split(".", 1)[-1] if "." in k and k.split(".")[0] in spec.nodes()["kpi_row"]["parts"] else k, "1")}"' for k, _ in base if k != "grow" and not drop(k))
        d = OUT / "bisect" / slug(name)
        r = compile_slide(d, TG.slide("AUDIT", "H", bare_tag("kpi_row", "kpis", "strip", attrs)), [KPIS], theme, "H")
        out[name] = {"compiled": r["compiled"], "missing": missing_words([KPIS], d / "presentation.pptx") if r["compiled"] else None}
        print(name, out[name], flush=True)
    (DOCS / "bisect.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


COMMANDS = {"duplicates": cmd_duplicates, "tables": cmd_tables, "bisect": cmd_bisect, "catalogue": cmd_catalogue, "consistency": cmd_consistency, "stress": cmd_stress, "atomic": cmd_atomic,
            "flex": cmd_flex, "census": cmd_census, "remeasure": cmd_remeasure}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=list(COMMANDS))
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--cases", nargs="*", default=[])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    install_timeline()
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
