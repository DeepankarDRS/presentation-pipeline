"""Score a 1a run (docs/derived-blocks-planning-2026-10-06.md §4.3): measures 1, 2, 3, 5-9, free.

    python -m scripts.node_test_score --nodes output/1a/1a --off output/1a/off [--out docs/eval/1a] [--no-render]

1 compliance (first try, per component; derived / native; slides all ok)   2 words inside nodes not in the plan
3 broken words + overlapping text (LibreOffice render, scripts/phase0b/fontcheck.py), nodes vs off
5 / 6 variety (scripts/variety.py; nodes = the final skeleton, off = step 0's XML)
7 tokens per slide: the nodes arm's first generator call vs step 0's generator call on the same slide
8 fallback (repairs, NODE_* errors, overfull)   9 variants chosen
Writes <out>/summary.md and <out>/results.json.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from scripts import variety
from scripts.from_plans import load_run
from src.compiler.nodes import spec
from src.compiler.nodes.validate import attrs_of, ref_tags, words

ROOT = Path(__file__).resolve().parents[1]
SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.exe")
FRAME = {"key", "message", "phase", "month", "step", "stage"}   # frame words a block may add (check.py)
PASS = {"compliance": 0.90, "invented": 0, "blind": 0.6, "variety_drop": 0.05}


# ── measure 2: words inside nodes ────────────────────────────────────────────

def _strings(v: Any) -> list[str]:
    if isinstance(v, dict):
        return [s for k, x in v.items() if k not in ("card_layout", "chart_type", "direction", "layout", "order")
                for s in _strings(x)]
    if isinstance(v, list):
        return [s for x in v for s in _strings(x)]
    return [str(v)] if v is not None else []


def node_regions(xml: str) -> dict[str, str]:
    """ref -> the XML of its drawn node (derived: id="slot-<ref>", native: id="node-<ref>")."""
    out = {}
    for m in re.finditer(r'<(\w+)\b[^>]*\bid="(?:slot|node)-([\w-]+)"[^>]*?(/?)>', xml):
        tag, ref, selfclose = m.group(1), m.group(2), m.group(3)
        if selfclose:
            out[ref] = m.group(0)
            continue
        depth, k = 1, m.end()
        pat = re.compile(rf"<(/?){tag}\b[^<>]*?(/?)>")
        while depth:
            n = pat.search(xml, k)
            if not n:
                k = len(xml)
                break
            depth += -1 if n.group(1) else (0 if n.group(2) else 1)
            k = n.end()
        out[ref] = xml[m.start():k]
    return out


INLINE = re.compile(r"</?(?:Span|B|I|U|S|Sub|Sup|Mark|A)\b[^>]*>")


def region_words(region: str) -> list[str]:
    # inline tags join their text ("₹114.9<Span>L</Span>" is one word); other tags separate words
    ws = words(re.sub(r"<[^>]+>", " ", INLINE.sub("", region)))
    for m in re.finditer(r"<(\w+)\b([^<>]*)>", region):
        if m.group(1) == "Icon":   # an icon's name is not visible text
            continue
        for k, v in attrs_of(m.group(2)).items():
            if k in ("label", "title", "text", "date", "name"):
                ws += words(v)
    return ws


def invented(xml: str, plan: dict) -> dict[str, list[str]]:
    comps = {c["component_id"]: c for c in plan.get("components") or []}
    out = {}
    for ref, region in node_regions(xml).items():
        comp = comps.get(ref)
        if not comp:
            continue
        allowed = {w for s in _strings(comp.get("content_data")) for w in words(s)}
        extra = [w for w in region_words(region)
                 if w not in allowed and w not in FRAME and not re.fullmatch(r"0?\d{1,2}", w)]
        if extra:
            out[ref] = sorted(set(extra))
    return out


# ── measure 3: render ────────────────────────────────────────────────────────

def render_pdf(slide_dir: Path) -> Path | None:
    pptx = slide_dir / "presentation.pptx"
    pdf = slide_dir / "presentation.pdf"
    if not pptx.exists():
        return None
    if pdf.exists() and pdf.stat().st_mtime >= pptx.stat().st_mtime:
        return pdf
    soffice = shutil.which("soffice") or str(SOFFICE)
    for _ in range(2):   # LibreOffice now and then exits without writing the PDF: one retry
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(slide_dir), str(pptx)],
                       capture_output=True, check=False, timeout=180)
        if pdf.exists():
            return pdf
    return None


def render_scores(slide_dir: Path) -> dict | None:
    from scripts.phase0b import fontcheck as F
    pdf = render_pdf(slide_dir)
    xml_p = slide_dir / "expanded.xml"
    if not pdf or not xml_p.exists():
        return None
    ws = F.pdf_words(pdf)
    return {"broken": F.broken(ws, F.slide_words(xml_p.read_text(encoding="utf-8"))), "overlap": F.overlaps(ws)}


# ── main ─────────────────────────────────────────────────────────────────────

def _manifest(folder: Path) -> dict:
    return json.loads((folder / "node-test-manifest.json").read_text(encoding="utf-8"))


def score(nodes: Path, off: Path | None, slides_file: Path, do_render: bool = True) -> dict:
    sel = json.loads(slides_file.read_text(encoding="utf-8"))["slides"]
    man = _manifest(nodes)
    done = {(r["case"], r["slide"]) for r in man["results"]}
    sel = [r for r in sel if (r["case"], r["slide"]) in done]
    runs: dict[str, dict] = {}
    comp_rows, slide_rows, var_nodes, var_off = [], [], [], []
    calls = {(c["case"], c["slide"], c["attempt"]): c for c in man["calls"]}
    for row in sel:
        case, n = row["case"], row["slide"]
        run = runs.get(case) or runs.setdefault(case, load_run(ROOT / row["run"]))
        slide = next(s for s in run["slides"] if s["number"] == n)
        plan = slide["plan"]
        d = nodes / case / f"slide-{n:02d}"
        chk = json.loads((d / "check.json").read_text(encoding="utf-8"))
        first = chk["first"]["check"] if chk.get("first") else {"components": {}, "unknown_refs": 0}
        res = next(r for r in man["results"] if (r["case"], r["slide"]) == (case, n))
        for cid, c in first.get("components", {}).items():
            comp_rows.append({"case": case, "slide": n, "ref": cid, "kind": c["kind"], "family": c["family"],
                              "status": c["status"], "variant": c.get("variant")})
        sk_first = (d / "skeleton.xml").read_text(encoding="utf-8") if (d / "skeleton.xml").exists() else ""
        asked = {t["attrs"]["ref"]: t["attrs"].get("variant") for t in ref_tags(sk_first)}
        finals = sorted(d.glob("skeleton-repair-*.xml"))
        sk_final = finals[-1].read_text(encoding="utf-8") if finals else sk_first
        expanded = (d / "expanded.xml").read_text(encoding="utf-8") if (d / "expanded.xml").exists() else ""
        kinds = [c["kind"] for c in plan["components"] if c["kind"] != "title"]
        var_nodes.append({"deck": case, "xml": sk_final, "kinds": kinds})
        var_off.append({"deck": case, "xml": slide["xml"], "kinds": kinds})
        step0 = [s for s in run["manifest"].get("steps") or [] if s.get("step") == "generator" and s.get("slide_index") == n - 1]
        a0 = min(step0, key=lambda s: s.get("attempt", 0)) if step0 else {}
        b0 = calls.get((case, n, 0), {})
        r_nodes = render_scores(d) if do_render else None
        r_off = render_scores(off / case / f"slide-{n:02d}") if (do_render and off) else None
        slide_rows.append({
            "case": case, "slide": n, "all_ok": first.get("ok", False) and not first.get("unknown_refs"),
            "unknown_refs": first.get("unknown_refs", 0), "repairs": res.get("repairs", 0), "compiled": res["compiled"],
            "first_issues": res.get("issues_first", []), "final_issues": res.get("issues_final", []),
            "overfull": "NODE_OVERFULL" in res.get("issues_final", []) or "SLIDE_OVERFULL" in (res.get("warnings") or []),
            "invented": invented(expanded, plan),
            "variants_asked": asked,
            "tokens": {"off_in": a0.get("tokens_in"), "off_out": a0.get("tokens_out"), "off_cached": a0.get("tokens_cached"),
                       "nodes_in": b0.get("tokens_in"), "nodes_out": b0.get("tokens_out"), "nodes_cached": b0.get("tokens_cached")},
            "render_nodes": r_nodes, "render_off": r_off,
        })

    def share(rows, pred):
        return round(sum(pred(r) for r in rows) / len(rows), 3) if rows else None

    ok = lambda r: r["status"] == "ok"   # noqa: E731
    der = [r for r in comp_rows if r["family"] == "derived"]
    nat = [r for r in comp_rows if r["family"] == "native"]
    tok = [s["tokens"] for s in slide_rows if s["tokens"]["nodes_in"] and s["tokens"]["off_in"]]
    sumk = lambda k: sum(t[k] or 0 for t in tok)   # noqa: E731
    rn = [s["render_nodes"] for s in slide_rows if s["render_nodes"]]
    ro = [s["render_off"] for s in slide_rows if s["render_off"]]
    v_nodes, v_off = variety.report(var_nodes), variety.report(var_off)
    asked = [v for s in slide_rows for v in s["variants_asked"].values()]
    out = {
        "nodes_run": str(nodes), "off_run": str(off) if off else None, "llm": man.get("llm"), "commit": man.get("git_commit"),
        "slides": len(slide_rows), "components": len(comp_rows),
        "m1_compliance": share(comp_rows, ok), "m1_derived": share(der, ok), "m1_native": share(nat, ok),
        "m1_slides_all_ok": share(slide_rows, lambda s: s["all_ok"]),
        "m1_status": dict(Counter(r["status"] for r in comp_rows)),
        "m1_unknown_refs": sum(s["unknown_refs"] for s in slide_rows),
        "m2_invented_words": sum(len(w) for s in slide_rows for w in s["invented"].values()),
        "m3_broken_nodes": sum(len(r["broken"]) for r in rn) if rn else None,
        "m3_broken_off": sum(len(r["broken"]) for r in ro) if ro else None,
        "m3_overlap_slides_nodes": sum(bool(r["overlap"]) for r in rn) if rn else None,
        "m3_overlap_slides_off": sum(bool(r["overlap"]) for r in ro) if ro else None,
        "m5_within_nodes": v_nodes["within_deck"], "m5_within_off": v_off["within_deck"],
        "m6_nodes": {k: v_nodes[k] for k in ("cross_deck_sameness", "cross_deck_pairs", "house_template_share", "house_template")},
        "m6_off": {k: v_off[k] for k in ("cross_deck_sameness", "cross_deck_pairs", "house_template_share", "house_template")},
        "m7_slides_compared": len(tok),
        "m7_per_slide": {k: round(sumk(k) / len(tok)) if tok else None
                         for k in ("off_in", "off_out", "off_cached", "nodes_in", "nodes_out", "nodes_cached")},
        "m7_cost_usd_nodes": man.get("cost_usd"),
        "m8_repaired_slides": sum(s["repairs"] > 0 for s in slide_rows),
        "m8_error_first_try": sum(not s["all_ok"] for s in slide_rows),
        "m8_overfull": sum(s["overfull"] for s in slide_rows),
        "m8_not_compiled": sum(not s["compiled"] for s in slide_rows),
        "m9_variants": dict(Counter(r["variant"] for r in comp_rows if r["variant"])),
        "m9_default_share": round(sum(v is None for v in asked) / len(asked), 3) if asked else None,
        "slide_rows": slide_rows, "component_rows": comp_rows,
    }
    return out


def verdict(r: dict) -> list[str]:
    lines = []
    c = r["m1_compliance"]
    lines.append(f"1 compliance {c:.0%} ({r['components']} components; margin about ±7 points) -> "
                 + ("pass" if c is not None and c >= PASS["compliance"] else "FAIL") + (", re-run zone" if c is not None and 0.86 <= c < 0.94 else ""))
    lines.append(f"2 invented words in nodes {r['m2_invented_words']} -> " + ("pass" if r["m2_invented_words"] == 0 else "FAIL"))
    if r["m3_broken_nodes"] is not None and r["m3_broken_off"] is not None:
        ok3 = r["m3_broken_nodes"] <= r["m3_broken_off"] and r["m3_overlap_slides_nodes"] <= r["m3_overlap_slides_off"]
        lines.append(f"3 broken words {r['m3_broken_nodes']} vs off {r['m3_broken_off']}; overlap slides "
                     f"{r['m3_overlap_slides_nodes']} vs {r['m3_overlap_slides_off']} -> " + ("pass" if ok3 else "FAIL"))
    lines.append("4 blind side-by-side: scripts/node_test_sheet.py (your marks)")
    if r["m5_within_nodes"] is not None and r["m5_within_off"] is not None:
        ok5 = r["m5_within_nodes"] >= r["m5_within_off"] - PASS["variety_drop"]
        lines.append(f"5 within-deck variety {r['m5_within_nodes']} vs off {r['m5_within_off']} -> " + ("pass" if ok5 else "FAIL"))
    return lines


def write(r: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    t = r["m7_per_slide"]
    md = [f"# 1a node test: {Path(r['nodes_run']).name}", "",
          f"{r['slides']} slides, {r['components']} components · LLM `{r['llm']}` · commit `{r['commit']}`", "",
          "## Kill criteria", ""] + [f"- {l}" for l in verdict(r)] + [
          "", "## Detail", "",
          f"- compliance: derived {r['m1_derived']}, native {r['m1_native']}, slides all ok {r['m1_slides_all_ok']}; "
          f"status {r['m1_status']}; unknown refs {r['m1_unknown_refs']}",
          f"- cross-deck (informational): nodes {r['m6_nodes']}; off {r['m6_off']}",
          f"- tokens per slide ({r['m7_slides_compared']} slides): off in {t['off_in']} / out {t['off_out']} / cached {t['off_cached']}; "
          f"nodes in {t['nodes_in']} / out {t['nodes_out']} / cached {t['nodes_cached']}; nodes arm cost ${r['m7_cost_usd_nodes']}",
          f"- fallback: repaired {r['m8_repaired_slides']}, error on first try {r['m8_error_first_try']}, "
          f"overfull {r['m8_overfull']}, not compiled {r['m8_not_compiled']}",
          f"- variants: {r['m9_variants']}; LLM left the default {r['m9_default_share']}", "",
          "## Slides", "", "| case | slide | all ok | repairs | first-try issues | invented | broken (nodes / off) |", "|---|---|---|---|---|---|---|"]
    for s in r["slide_rows"]:
        bn = len(s["render_nodes"]["broken"]) if s["render_nodes"] else "-"
        bo = len(s["render_off"]["broken"]) if s["render_off"] else "-"
        md.append(f"| {s['case']} | {s['slide']} | {s['all_ok']} | {s['repairs']} | {', '.join(s['first_issues']) or '-'} | "
                  f"{sum(len(v) for v in s['invented'].values())} | {bn} / {bo} |")
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nodes", type=Path, required=True)
    ap.add_argument("--off", type=Path)
    ap.add_argument("--slides", type=Path, default=ROOT / "docs" / "eval" / "step0" / "1a-slides.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    r = score(a.nodes, a.off, a.slides, not a.no_render)
    out = a.out or a.nodes / "score"
    write(r, out)
    print("\n".join(verdict(r)))
    print(f"-> {out / 'summary.md'}")


if __name__ == "__main__":
    main()
