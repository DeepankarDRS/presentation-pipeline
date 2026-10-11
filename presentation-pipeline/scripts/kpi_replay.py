"""KPI node pilot, free replay (docs/kpi-node-pilot-2026-10-11.md §2). LLM-free.

    python -m scripts.kpi_replay                       # today's route (q1008 + run-1008) and the older routes
    python -m scripts.kpi_replay --no-render           # skip LibreOffice (no broken-word count, no blind sheet)
    python -m scripts.node_test_sheet --score output/kpi-replay/sheets    # after marking

For every saved slide with a kpi_row component (slides.json: the deck's XML + its slide plan):
  1. map   — each Text whose whole text (Span markup joined, whitespace / minus / thousands
             commas normalised) equals a plan label / value / delta becomes <Text ref="cid.i.field"/>,
             keeping its other attributes (colour, bold, ...) but not its fontSize; misses are listed
             (dropped, merged into a longer Text, retyped differently, in a table);
  2. arm A — the saved XML, compiled unchanged on today's compiler (normalizer, fit-grow, Inter);
     arm B — the mapped XML through the fill step (element_refs.fill_refs), then the same path;
  3. score — broken words (WORD_TOO_WIDE + words split in the LibreOffice render), number sizes per
             component, GEOM_CARD_EMPTY / GEOM_SLIDE_SPARSE, LOW_CONTRAST, plan values not on the slide;
  4. blind sheet of the slides whose renders differ (scripts/node_test_sheet.py, B in the "nodes" role).
Writes <out>/results.json and <out>/summary.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.geometry_audit import audit_run_folder  # noqa: E402
from src.compiler.layout_audit import audit_layout  # noqa: E402
from src.compiler.nodes.element_refs import FIELDS, PLAN_KEY, fill_refs, kpi_components, norm  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

OUT = ROOT / "output" / "kpi-replay"
SOURCES = {   # group -> [(label, glob under output/)]
    "today": [("q1008", "q1008/quality-1008-*/decks/*/slides.json"), ("run1008", "run-1008/*/slides.json")],
    "older": [("step0", "step0/b*/*/decks/*/slides.json"), ("colour", "colour-roles/*/decks/*/slides.json"),
              ("critic-on", "critic-on/*/slides.json"), ("critic-on2", "critic-on2/*/slides.json")],
}
ARROWS = "▲▼↑↓▴▾"
FILL_CODES = ("GEOM_CARD_EMPTY", "GEOM_SLIDE_SPARSE")


# ── map ──────────────────────────────────────────────────────────────────────

def _key(s: str) -> str:
    return norm(s).lstrip(ARROWS)


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"))


def _serial(root: etree._Element) -> str:
    return (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root)


def plan_texts(comps: dict[str, dict]) -> list[tuple[str, int, str, str]]:
    """(cid, i, field, text) for every non-empty plan text, values first (they matter most)."""
    out = []
    for field in ("value", "label", "note"):
        for cid, c in comps.items():
            for i, t in enumerate((c.get("content_data") or {}).get(PLAN_KEY[field]) or []):
                if str(t or "").strip():
                    out.append((cid, i, field, str(t).strip()))
    return out


def map_refs(xml: str, plan: dict) -> tuple[str, dict, list[dict]]:
    """(mapped xml, {(cid, i, field): original Text attrs}, misses)."""
    comps = kpi_components(plan)
    root = _parse(xml)
    texts = [t for t in root.iter("Text")]
    whole = {id(t): _key("".join(t.itertext())) for t in texts}
    taken: set[int] = set()
    found: dict[tuple[str, int, str], dict] = {}
    misses = []
    for cid, i, field, text in plan_texts(comps):
        k = _key(text)
        hit = next((t for t in texts if id(t) not in taken and whole[id(t)] == k), None)
        if hit is None:
            misses.append({"ref": f"{cid}.{i}.{field}", "text": text, "why": _why(root, k, text)})
            continue
        taken.add(id(hit))
        found[(cid, i, field)] = dict(hit.attrib)
        for c in list(hit):
            hit.remove(c)
        hit.text = None
        keep = {a: v for a, v in hit.attrib.items() if a != "fontSize"}
        hit.attrib.clear()
        hit.set("ref", f"{cid}.{i}.{field}")
        for a, v in keep.items():
            hit.set(a, v)
    return _serial(root), found, misses


def _why(root: etree._Element, k: str, text: str) -> str:
    for t in root.iter("Text", "Td", "Li", "Shape"):
        s = _key("".join(t.itertext()) + " ".join(t.attrib.values()))
        if k and k in s:
            inside = t.tag == "Td" or any(a.tag in ("Table", "Td") for a in t.iterancestors())
            return "in a table" if inside else "merged into a longer text"
    digits = re.findall(r"\d[\d.,]*", text)
    flat = _key("".join(root.itertext()))
    if digits and all(d.replace(",", "") in flat for d in digits):
        return "retyped differently"
    return "dropped"


# ── compile + score ──────────────────────────────────────────────────────────

def compile_slide(xml: str, theme: str, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    norm_res = normalize_xml(xml)
    cleaned = ensure_single_theme(norm_res["cleaned_xml"], theme)
    (dest / "in.xml").write_text(cleaned, encoding="utf-8")
    subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(dest / "in.xml"), str(dest)],
                   capture_output=True, timeout=300)
    res = json.loads((dest / "compile-result.json").read_text(encoding="utf-8"))
    return {"res": res, "cleaned": cleaned}


def _size(t: etree._Element) -> float:
    try:
        return float(t.get("fontSize") or 24)
    except ValueError:
        return 24.0


def value_sizes(final_xml: str, plan: dict, arm: str) -> dict[str, dict]:
    """Per component: the drawn number sizes (B: the kpiv ids; A: Texts whose text is a plan value)."""
    comps = kpi_components(plan)
    root = _parse(final_xml)
    out = {}
    for cid, c in comps.items():
        if arm == "B":
            sizes = [_size(t) for t in root.iter("Text") if re.match(rf"^kpiv-{re.escape(cid)}-\d+$", t.get("id", ""))]
            hero = [_size(t) for t in root.iter("Text") if re.match(rf"^kpih-{re.escape(cid)}-\d+$", t.get("id", ""))]
        else:
            keys = [_key(v) for v in (c.get("content_data") or {}).get("kpi_values") or []]
            texts = list(root.iter("Text"))
            sizes, used = [], set()
            for k in keys:
                t = next((t for t in texts if id(t) not in used and _key("".join(t.itertext())) == k), None)
                if t is not None:
                    used.add(id(t))
                    sizes.append(_size(t))
            hero = []
        out[cid] = {"sizes": sizes, "hero": hero, "distinct": len(set(sizes)),
                    "max": max(sizes, default=0), "min": min(sizes, default=0)}
    return out


def values_off_plan(final_xml: str, plan: dict) -> list[str]:
    """Plan values that are not on the slide as written (normalised), in any Text."""
    root = _parse(final_xml)
    slide = [_key("".join(t.itertext())) for t in root.iter("Text", "Td", "Li")]
    out = []
    for c in kpi_components(plan).values():
        for v in (c.get("content_data") or {}).get("kpi_values") or []:
            if str(v).strip() and not any(_key(str(v)) in s for s in slide):
                out.append(str(v))
    return out


def broken_words(dest: Path, final_xml: str) -> int | None:
    from scripts.node_test_score import render_pdf
    from scripts.phase0b import fontcheck as F
    pdf = render_pdf(dest)
    if not pdf:
        return None
    return len(F.broken(F.pdf_words(pdf), F.slide_words(final_xml)))


def score(arm: str, dest: Path, comp: dict, plan: dict, case: str, render: bool) -> dict:
    res, cleaned = comp["res"], comp["cleaned"]
    ok = res.get("status") == "success"
    final = (dest / "fitted.xml").read_text(encoding="utf-8") if (dest / "fitted.xml").exists() else cleaned
    geo = audit_run_folder(dest) if ok else []
    try:
        contrast = [i for i in audit_layout(cleaned) if i.get("code") == "LOW_CONTRAST"]
    except Exception:
        contrast = []
    return {
        "compiled": ok,
        "diagnostics": [d.get("message", "")[:200] for d in res.get("diagnostics") or []],
        "word_too_wide": sum(1 for w in res.get("warnings") or [] if w.get("code") == "WORD_TOO_WIDE"),
        "broken": broken_words(dest, final) if ok and render else None,
        "sizes": value_sizes(final, plan, arm),
        "fill": {c: sum(1 for i in geo if i["code"] == c) for c in FILL_CODES},
        "low_contrast": len(contrast),
        "off_plan": values_off_plan(final, plan),
    }


# ── driver ───────────────────────────────────────────────────────────────────

def _theme(slides_json: Path) -> str:
    for m in (slides_json.parent / "run-manifest.json", slides_json.parent.parent / "run-manifest.json"):
        if m.exists():
            name = json.loads(m.read_text(encoding="utf-8")).get("theme")
            if name:
                return resolve_theme(name)["element"]
    return resolve_theme("corporate-slate")["element"]


def collect() -> list[dict]:
    seen: set[str] = set()
    rows = []
    for group, srcs in SOURCES.items():
        for label, pattern in srcs:
            for sj in sorted((ROOT / "output").glob(pattern)):
                if "/nk/" in sj.as_posix():
                    continue
                case = sj.parent.name
                theme = _theme(sj)
                for s in json.loads(sj.read_text(encoding="utf-8")):
                    plan = s.get("slide_plan") or {}
                    if not kpi_components(plan) or not s.get("xml"):
                        continue
                    h = hashlib.sha1(s["xml"].encode("utf-8")).hexdigest()
                    if h in seen:
                        continue
                    seen.add(h)
                    rows.append({"group": group, "source": label, "case": f"{label}-{case}",
                                 "slide": int(s.get("slide_index", 0)), "xml": s["xml"], "plan": plan, "theme": theme})
    return rows


def run(out: Path, render: bool) -> list[dict]:
    results = []
    for r in collect():
        sub = f"{r['case']}/slide-{r['slide']}"
        mapped, found, misses = map_refs(r["xml"], r["plan"])
        filled = fill_refs(mapped, r["plan"])
        base = out / r["group"]
        (base / "B" / sub).mkdir(parents=True, exist_ok=True)
        (base / "B" / sub / "mapped.xml").write_text(mapped, encoding="utf-8")
        a = compile_slide(r["xml"], r["theme"], base / "A" / sub)
        b = compile_slide(filled["xml"], r["theme"], base / "B" / sub)
        comps = kpi_components(r["plan"])
        counts = {f: {"planned": 0, "found": 0} for f in FIELDS}
        for cid, c in comps.items():
            for f in FIELDS:
                for i, t in enumerate((c.get("content_data") or {}).get(PLAN_KEY[f]) or []):
                    if str(t or "").strip():
                        counts[f]["planned"] += 1
                        counts[f]["found"] += (cid, i, f) in found
        row = {k: r[k] for k in ("group", "source", "case", "slide")}
        row.update({"components": list(comps), "mapping": counts, "misses": misses,
                    "fill_issues": [{k: i[k] for k in ("code", "severity", "message")} for i in filled["issues"]],
                    "A": score("A", base / "A" / sub, a, r["plan"], r["case"], render),
                    "B": score("B", base / "B" / sub, b, r["plan"], r["case"], render)})
        results.append(row)
        print(f"{r['group']:5s} {sub}: values {counts['value']['found']}/{counts['value']['planned']}, "
              f"A {row['A']['compiled']} B {row['B']['compiled']}, sizes A {[v['distinct'] for v in row['A']['sizes'].values()]} "
              f"B {[v['distinct'] for v in row['B']['sizes'].values()]}, broken A {row['A']['broken']} B {row['B']['broken']}")
    return results


def _png(pdf: Path) -> bytes:
    import pymupdf
    return pymupdf.open(pdf)[0].get_pixmap(dpi=50).samples


def sheets(out: Path, results: list[dict]) -> int:
    """Blind sheet of today's-route slides whose renders differ (B plays the 'nodes' role)."""
    from scripts import node_test_sheet as S
    from scripts.node_test_score import render_pdf
    pick = out / "sheet-in"
    shutil.rmtree(pick, ignore_errors=True)
    n = 0
    for r in results:
        if r["group"] != "today":
            continue
        sub = f"{r['case']}/slide-{r['slide']}"
        pa, pb = render_pdf(out / "today" / "A" / sub), render_pdf(out / "today" / "B" / sub)
        r["renders_differ"] = bool(pa and pb and _png(pa) != _png(pb)) or bool(pa) != bool(pb)
        if not r["renders_differ"]:
            continue
        for arm in ("A", "B"):
            d = pick / arm / sub
            d.mkdir(parents=True, exist_ok=True)
            for f in ("presentation.pptx", "presentation.pdf"):
                if (out / "today" / arm / sub / f).exists():
                    shutil.copy2(out / "today" / arm / sub / f, d / f)
        n += 1
    if n:
        S.build(pick / "B", pick / "A", out / "sheets")
    return n


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({round(100 * a / b) if b else 0}%)"


def summary(out: Path, results: list[dict]) -> str:
    lines = ["# KPI node pilot: free replay", "",
             "Arm A = the saved XML on today's compiler; arm B = the same XML with each KPI text mapped to a ref and "
             "filled by `element_refs.fill_refs`. Produced by `python -m scripts.kpi_replay`.", ""]
    for group in ("today", "older"):
        rows = [r for r in results if r["group"] == group]
        if not rows:
            continue
        m = {f: [sum(r["mapping"][f][k] for r in rows) for k in ("found", "planned")] for f in FIELDS}
        def tot(arm, f):
            vals = [f(r[arm]) for r in rows]
            return sum(v for v in vals if v is not None), sum(v is None for v in vals)
        comps = [(r, cid) for r in rows for cid in r["components"]]
        # a component with no figures (sentence values drawn as body text, NODE_VALUE_TEXT) has no size to share
        figs = [(r, c) for r, c in comps if r["B"]["sizes"][c]["sizes"] or r["B"]["sizes"][c]["hero"]]
        one = lambda arm: sum(1 for r, c in figs if r[arm]["sizes"][c]["distinct"] <= 1
                             and (r[arm]["sizes"][c]["sizes"] or r[arm]["sizes"][c]["hero"]))
        lines += [f"## {'Today' if group == 'today' else 'Older routes'} ({len(rows)} slides, {len(comps)} kpi_row components)", "",
                  f"Mapping rate: values {_pct(*m['value'])}, labels {_pct(*m['label'])}, notes {_pct(*m['note'])}.", "",
                  "| | A (today) | B (refs) |", "|---|---|---|",
                  f"| compiled | {sum(r['A']['compiled'] for r in rows)} | {sum(r['B']['compiled'] for r in rows)} |",
                  f"| WORD_TOO_WIDE | {tot('A', lambda s: s['word_too_wide'])[0]} | {tot('B', lambda s: s['word_too_wide'])[0]} |",
                  f"| broken words in the render | {tot('A', lambda s: s['broken'])[0]} | {tot('B', lambda s: s['broken'])[0]} |",
                  f"| components with one number size (with figures) | {one('A')} / {len(figs)} | {one('B')} / {len(figs)} |",
                  f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill']['GEOM_CARD_EMPTY'])[0]} | {tot('B', lambda s: s['fill']['GEOM_CARD_EMPTY'])[0]} |",
                  f"| GEOM_SLIDE_SPARSE | {tot('A', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])[0]} | {tot('B', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])[0]} |",
                  f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])[0]} | {tot('B', lambda s: s['low_contrast'])[0]} |",
                  f"| plan values not on the slide | {tot('A', lambda s: len(s['off_plan']))[0]} | {tot('B', lambda s: len(s['off_plan']))[0]} |",
                  "", "| slide | values mapped | A sizes | B sizes (hero) | broken A / B | fill A / B | contrast A / B |",
                  "|---|---|---|---|---|---|---|"]
        for r in rows:
            sz = lambda arm: "; ".join(f"{'/'.join(str(round(x)) for x in sorted(set(v['sizes'])))}"
                                       + (f" ({'/'.join(str(round(h)) for h in v['hero'])})" if v["hero"] else "")
                                       for v in r[arm]["sizes"].values())
            f = lambda arm: sum(r[arm]["fill"].values())
            lines.append(f"| {r['case']} / {r['slide']} | {r['mapping']['value']['found']}/{r['mapping']['value']['planned']} | "
                         f"{sz('A')} | {sz('B')} | {r['A']['broken']} / {r['B']['broken']} | {f('A')} / {f('B')} | "
                         f"{r['A']['low_contrast']} / {r['B']['low_contrast']} |")
        misses = [(r, x) for r in rows for x in r["misses"]]
        if misses:
            lines += ["", "Misses (plan text with no Text of its own):", ""]
            lines += [f"- {r['case']} / {r['slide']} `{x['ref']}` \"{x['text']}\": {x['why']}" for r, x in misses]
        lines.append("")
    text = "\n".join(lines)
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--summary", action="store_true", help="rewrite summary.md from results.json only")
    a = ap.parse_args()
    if a.summary:
        print(summary(a.out, json.loads((a.out / "results.json").read_text(encoding="utf-8"))))
        return 0
    shutil.rmtree(a.out, ignore_errors=True)
    results = run(a.out, render=not a.no_render)
    if not a.no_render:
        print(f"blind sheet: {sheets(a.out, results)} slides whose renders differ")
    (a.out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    print(summary(a.out, results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
