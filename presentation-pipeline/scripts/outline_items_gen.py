"""Outline items, gate 3 (docs/outline-items-design-2026-10-27.md §7): the generator on the items plans and on the
saved plans of the same slides, scored and drawn as blind A / B sheets.

    python -m scripts.outline_items_gen --make-inputs --items <runs.json> --base <runs.json> --drop <pair>,...   # free
    python -m scripts.outline_items_gen --label gate3 --no-render --bundle --max-usd 1.5         # paid, test PC (~$1)
    python -m scripts.outline_items_gen --label gate3 --rescore                                  # free, build PC
    python -m scripts.outline_items_gen --label gate3-dry --dry                                  # free: fake generator

--make-inputs pairs repeat 1 of a plan-only run with OUTLINE_ITEMS=on (--items, e.g. output/card-plans/outline-items-2/
runs.json) with repeat 1 of a run without (--base, typed-schema): each items slide with the base slide of the same deck
whose words overlap its own most (the two outlines may order slides differently: launch 5 and 6 swap), at least a
third of them; kept only when the two plans draw different component kinds (the same kinds would compare the generator
with itself). --drop leaves out pairs a person judged unfair (different content, near-identical plans, a defect
both plans share; docs/eval/outline-items/gate3-pairs-review.md). The pairs go to
docs/eval/outline-items/gate3-inputs.json, committed, so the test PC needs no output/.

The paid run draws every pair twice with the real graph from a slide plan (scripts.kpi_paid.run_one: style resolver ->
context builder -> generator -> validator -> repairers; critic off; models.yaml as committed), arm "items" and arm
"base", and stops before a pair when the spend reaches --max-usd. --rescore (needs LibreOffice) compiles each arm's
final slide with the deck font, renders it in Inter (scripts.card_replay.render), scores it (compiled, GEOM_* fill,
broken words, LOW_CONTRAST) and builds the blind sheets: sheets/sheet-NN.png, marks.csv to fill, key.json (open after
marking; "nodes_side" = the items slide). Tally: python -m scripts.node_test_sheet --score output/outline-items-gen/<label>/sheets

Writes output/outline-items-gen/<label>/: runs.json, items/<pair>/, base/<pair>/ (plan.json, first.xml, final.xml,
slide-1/), results.json, summary.md, sheets/; --bundle zips it with the run folders.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

INPUTS = ROOT / "docs" / "eval" / "outline-items" / "gate3-inputs.json"
OUT = ROOT / "output" / "outline-items-gen"
ARMS = ("items", "base")


def kinds(plan: dict) -> list[str]:
    return sorted(c.get("kind", "") for c in plan.get("components") or [] if c.get("kind") != "title")


def words(plan: dict) -> set[str]:
    from scripts.outline_items_report import plan_text
    import re
    return set(re.findall(r"[a-z]{4,}|\d[\d.,]*", plan_text(plan).lower()))


def overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def make_inputs(items_path: Path, base_path: Path, repeat: int = 1, drop: set[str] | None = None) -> list[dict]:
    from src.utils.case_loader import load_case
    new = json.loads(items_path.read_text(encoding="utf-8"))
    base = json.loads(base_path.read_text(encoding="utf-8"))
    pairs = []
    for r in new:
        if r.get("repeat") != repeat:
            continue
        b = next((x for x in base if x.get("case") == r["case"] and x.get("repeat") == repeat), None)
        base_plans = (b or {}).get("slide_plans") or []
        for p in r.get("slide_plans") or []:
            w = words(p)
            best = max(base_plans, key=lambda q: (overlap(w, words(q)), q.get("slide_index") == p.get("slide_index")),
                       default=None)
            if best is None or overlap(w, words(best)) < 1 / 3:
                continue
            q = best
            if kinds(p) == kinds(q):
                continue
            n = p.get("slide_index", 0) + 1
            if f"{r['case']}-s{n}" in (drop or set()):
                continue
            pairs.append({"pair": f"{r['case']}-s{n}", "case": r["case"], "slide": n,
                          "base_slide": q.get("slide_index", 0) + 1, "overlap": round(overlap(w, words(q)), 2),
                          "theme": load_case(r["case"]).get("theme", ""), "items": p, "base": q})
    return pairs


def _fake_xml(plan: dict) -> str:
    title = (plan.get("slide_title") or "dry").replace("&", "and").replace("<", "")
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" backgroundColor="$surface">'
            f'<Text fontSize="32" color="$textMain" bold="true">{title}</Text></VStack></Slide>')


def run(label: str, max_usd: float, dry: bool = False) -> list[dict]:
    from scripts.kpi_paid import _FakeLLM, run_one
    from src.utils.case_loader import load_case
    out = OUT / label
    pairs = json.loads(INPUTS.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    spent = 0.0
    for pr in pairs:
        if spent >= max_usd:
            print(f"stopped before {pr['pair']}: ${spent:.3f} spent, ceiling ${max_usd:.2f}", flush=True)
            rows.append({"pair": pr["pair"], "skipped": f"ceiling ${max_usd:.2f} reached"})
            continue
        case = load_case(pr["case"])
        request = case.get("request", case.get("objective", ""))
        for arm in ARMS:
            plan = pr[arm]
            d = out / arm / pr["pair"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
            rid = f"oigen-{arm}-{pr['pair']}-{int(time.time())}"
            row: dict[str, Any] = {"pair": pr["pair"], "arm": arm, "case": pr["case"], "slide": pr["slide"],
                                   "theme": pr["theme"], "run_id": rid, "kinds": kinds(plan)}
            print(f"run {pr['pair']} {arm} ...", flush=True)
            try:
                if dry:
                    from src.agents import generator
                    generator.get_llm = lambda step, _x=_fake_xml(plan): _FakeLLM(_x)
                res = run_one({"plan": plan, "request": request, "theme": pr["theme"]}, rid)
            except Exception as e:   # one failure must not cost the other runs
                res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "final_xml": "", "first_xml": "",
                       "cost_usd": 0.0, "validator_passes": 0, "generator_calls": 0}
            spent += res.get("cost_usd") or 0.0
            (d / "final.xml").write_text(res.get("final_xml") or "", encoding="utf-8")
            if res.get("first_xml"):
                (d / "first.xml").write_text(res["first_xml"], encoding="utf-8")
            row.update({k: res.get(k) for k in ("blocks", "first_ok", "final_ok", "validator_passes", "generator_calls",
                                                  "cost_usd", "gen_tokens", "first_diagnostics", "error") if k in res})
            rows.append(row)
            print(f"  first ok={row.get('first_ok')} passes={row.get('validator_passes')} final ok={row.get('final_ok')} "
                  f"${row.get('cost_usd') or 0:.3f} (total ${spent:.3f})", flush=True)
            (out / "runs.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "runs.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return rows


def rescore(label: str, render: bool = True) -> list[dict]:
    from scripts import card_replay as R
    from scripts.kpi_replay import compile_slide, score
    from src.agents.style_resolver import resolve_theme
    from src.compiler.compiler_client import deck_font
    out = OUT / label
    rows = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in rows:
        if row.get("skipped"):
            continue
        d = out / row["arm"] / row["pair"]
        xml = (d / "final.xml").read_text(encoding="utf-8") if (d / "final.xml").exists() else ""
        if not xml:
            row["score"] = None
            continue
        dest = d / "slide-1"
        shutil.rmtree(dest, ignore_errors=True)
        plan = json.loads((d / "plan.json").read_text(encoding="utf-8"))
        comp = compile_slide(deck_font(R.BARE_AMP.sub("&amp;", xml)), resolve_theme(row.get("theme") or "")["element"], dest)
        if render and comp["res"].get("status") == "success":
            R.render(dest)
        sc = score(row["arm"], dest, comp, plan, row["pair"], render)
        sc.pop("sizes", None), sc.pop("off_plan", None)
        row["score"] = sc
    (out / "results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts import node_test_sheet as S
        S.build(out / "items", out / "base", out / "sheets")
    write_summary(out, rows)
    return rows


def write_summary(out: Path, rows: list[dict]) -> None:
    done = [r for r in rows if not r.get("skipped")]

    def col(arm: str) -> list[str]:
        rs = [r for r in done if r["arm"] == arm]
        sc = [r["score"] for r in rs if r.get("score") and r["score"]["compiled"]]
        fill = {}
        for s in sc:
            for k, v in s["fill"].items():
                fill[k] = fill.get(k, 0) + v
        return [str(len(rs)), f"${sum(r.get('cost_usd') or 0 for r in rs):.3f}",
                f"{sum(bool(r.get('first_ok')) for r in rs)} / {len(rs)}",
                f"{sum(bool(r.get('final_ok')) for r in rs)} / {len(rs)}",
                str(sum(max(0, (r.get('validator_passes') or 0) - 1) for r in rs)),
                str(sum(s["broken"] or 0 for s in sc)), str(sum(s["low_contrast"] for s in sc)),
                ", ".join(f"{k} {v}" for k, v in sorted(fill.items()) if v) or "-",
                f"{sum(len(r['kinds']) for r in rs) / max(1, len(rs)):.2f}"]
    names = ["slides", "cost", "first try compiled", "final compiled", "repair passes", "broken words (render)",
             "LOW_CONTRAST", "GEOM fill codes", "components per slide"]
    a, b = col("items"), col("base")
    skipped = [r["pair"] for r in rows if r.get("skipped")]
    lines = ["# Outline items, gate 3: generator on the items plans vs the saved plans", "",
             f"{len({r['pair'] for r in done})} pairs" + (f"; skipped (ceiling): {', '.join(skipped)}" if skipped else ""),
             "", "| | items | base |", "|---|---|---|", *[f"| {n} | {x} | {y} |" for n, x, y in zip(names, a, b)], "",
             "Blind sheets: sheets/ (fill marks.csv: 1 = left better, 2 = right, 0 = same; key.json after marking, "
             "\"nodes_side\" = the items slide). Tally: python -m scripts.node_test_sheet --score <this folder>/sheets"]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def bundle(label: str) -> Path:
    out = OUT / label
    z = OUT / f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in out.rglob("*"):
            if p.is_file():
                f.write(p, p.relative_to(OUT))
        for r in json.loads((out / "runs.json").read_text(encoding="utf-8")):
            run_dir = ROOT / "output" / "runs" / r.get("run_id", "-")
            for p in run_dir.rglob("*") if run_dir.exists() else []:
                if p.is_file() and p.suffix in (".xml", ".json", ".log", ".txt"):
                    f.write(p, Path(label) / "runs" / p.relative_to(ROOT / "output" / "runs"))
    return z


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--make-inputs", action="store_true", help="free: build gate3-inputs.json from two plan-only runs")
    ap.add_argument("--items", type=Path, help="with --make-inputs: runs.json of the OUTLINE_ITEMS=on run")
    ap.add_argument("--base", type=Path, help="with --make-inputs: runs.json of the run without items")
    ap.add_argument("--drop", default="", help="with --make-inputs: pairs to leave out, comma-separated "
                                                "(e.g. gate-deck-cheffin-full-s4)")
    ap.add_argument("--label", default="gate3")
    ap.add_argument("--max-usd", type=float, default=1.5, help="paid run: stop before a pair once this is spent")
    ap.add_argument("--rescore", action="store_true", help="free: render, score and build the blind sheets again")
    ap.add_argument("--no-render", action="store_true", help="skip LibreOffice (the test PC); rescore on the build PC")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: a fake generator answers every call")
    a = ap.parse_args()
    if a.make_inputs:
        if not (a.items and a.base):
            print("--make-inputs needs --items and --base (runs.json paths)")
            return 2
        drop = {d.strip() for d in a.drop.split(",") if d.strip()}
        pairs = make_inputs(a.items, a.base, drop=drop)
        missing = drop - {p["pair"] for p in make_inputs(a.items, a.base)}
        if missing:
            print(f"--drop names no pair: {', '.join(sorted(missing))}")
            return 2
        INPUTS.parent.mkdir(parents=True, exist_ok=True)
        INPUTS.write_text(json.dumps(pairs, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{len(pairs)} pairs -> {INPUTS}")
        return 0
    if a.dry:
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        run(a.label, max_usd=float("inf"), dry=True)
    elif not a.rescore:
        if not os.environ.get("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set (.env): the paid run is for the test PC")
            return 2
        run(a.label, a.max_usd)
    rescore(a.label, render=not a.no_render)
    if a.bundle:
        print(bundle(a.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
