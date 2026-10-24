"""Tile nodes, same-plan check: both KPI routes draw the SAME slide plans (generator only, paid).

    python -m scripts.experiments.tiles.tile_same_plan --label same-plan --bundle          # paid, test PC (OPENAI_API_KEY)
    python -m scripts.experiments.tiles.tile_same_plan --label same-plan --rescore         # free: score + blind sheet again
    python -m scripts.experiments.tiles.tile_same_plan --label dry --dry                   # free: fake generator (path check)
    python -m scripts.experiments.tiles.tile_same_plan --make-inputs <wide-tiles dir> <wide-kpi dir>   # build PC, once

Why: in the wider paid run each route planned its own decks, so the blind marks judged the text around the KPIs
as much as the tiles (docs/eval/tile-nodes/wide-paid/README.md). Here every KPI slide plan of those two runs
(docs/eval/tile-nodes/same-plan/inputs.json, committed: plan, theme name, case request) goes through the real
graph from the plan twice, POM_BLOCKS=kpi (arm A, element refs) and POM_BLOCKS=tiles (arm B, tile tags);
critic off, as the eval runs. Each run: first try (NODE_* codes), repairs, final slide scored like the replays
(scripts/experiments/kpi/kpi_replay.score: number sizes, card fill, broken words, off-plan values), cost. Writes
output/tile-same-plan/<label>/: runs.json, results.json, summary.md, sheets/ (blind A / B pairs: fill
marks.csv; key.json says which side is tiles) and, with --bundle, <label>.zip to email back.
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.experiments.kpi import kpi_paid as KP  # noqa: E402
from scripts.experiments.kpi.kpi_replay import compile_slide, score  # noqa: E402
from src.agents.planning.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes.element_refs import kpi_components  # noqa: E402

INPUTS = ROOT / "docs" / "eval" / "tile-nodes" / "same-plan" / "inputs.json"
OUT = ROOT / "output" / "tile-same-plan"
ARMS = (("A", "kpi"), ("B", "tiles"))


# ── inputs (build PC) ─────────────────────────────────────────────────────────

def make_inputs(tiles_dir: Path, kpi_dir: Path) -> list[dict]:
    """Every slide with a kpi_row in the two wide-paid bundles: its plan, theme name, the case request and the
    source run's generator XML (for --dry only)."""
    from src.utils.case_loader import load_case
    items = []
    for src, d in (("tiles", tiles_dir), ("kpi", kpi_dir)):
        for sj in sorted(d.glob("decks/*__r1/slides.json")):
            case = sj.parent.name.rsplit("__", 1)[0]
            theme = json.loads((sj.parent / "run-manifest.json").read_text(encoding="utf-8"))["theme"]
            c = load_case(case)
            for s in json.loads(sj.read_text(encoding="utf-8")):
                plan = s.get("slide_plan") or {}
                if not kpi_components(plan):
                    continue
                n = s["slide_index"]
                gen = d / "slides" / f"{case}__r1" / f"slide-{n}" / "generated.xml"
                items.append({"name": f"{src}-plan-{case}-s{n}", "case": case, "slide": n, "plan_from": src,
                              "plan": plan, "theme": theme, "request": c.get("request", c.get("objective", "")),
                              "generated": gen.read_text(encoding="utf-8") if gen.exists() else ""})
    INPUTS.parent.mkdir(parents=True, exist_ok=True)
    INPUTS.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(items)} KPI slide plans -> {INPUTS}")
    return items


def _dry_xml(it: dict, blocks: str) -> str:
    """--dry: the source run's own generator XML, carried over to the other route."""
    from src.compiler.nodes import tiles
    xml = it["generated"]
    if not xml:   # no saved generator XML (a repaired slide): a bare slide of tile tags
        tags = "".join(f'<KpiGrid ref="{cid}"/>' for cid in kpi_components(it["plan"]))
        xml, it = (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
                   f'<Text fontSize="36" bold="true" color="$textMain">{it["plan"].get("slide_title", "")}</Text>{tags}'
                   f'</VStack></Slide>'), {**it, "plan_from": "tiles"}
    if blocks == it["plan_from"]:
        return xml
    if blocks == "kpi":   # tile tags -> the ref tiles they expand to
        return tiles.expand(xml, it["plan"])["xml"]
    from scripts.experiments.tiles.tile_replay import rewrite   # hand ref tiles -> tile tags
    return rewrite(xml, it["plan"])["xml"]


# ── the paid run ──────────────────────────────────────────────────────────────

def run(label: str, repeat: int, dry: bool = False) -> list[dict]:
    out = OUT / label
    items = json.loads(INPUTS.read_text(encoding="utf-8"))
    runs = []
    for r in range(1, repeat + 1):
        for it in items:
            for arm, blocks in ARMS:
                os.environ["POM_BLOCKS"] = blocks
                case = f"{it['name']}-r{r}"
                rid = f"same-{blocks}-{it['case']}-s{it['slide']}-r{r}-{int(time.time())}"
                print(f"run {case} {blocks} ...", flush=True)
                try:
                    if dry:
                        from src.agents.generation import generator
                        generator.get_llm = lambda step, _x=_dry_xml(it, blocks): KP._FakeLLM(_x)
                    res = KP.run_one(it, rid)
                except Exception as e:   # one failure must not cost the other runs
                    res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                           "final_xml": "", "first_xml": "", "cost_usd": 0.0, "validator_passes": 0, "generator_calls": 0}
                d = out / arm / case
                d.mkdir(parents=True, exist_ok=True)
                (d / "final.xml").write_text(res["final_xml"], encoding="utf-8")
                if res.get("first_xml"):
                    (d / "first.xml").write_text(res["first_xml"], encoding="utf-8")
                placed, planned = KP.refs_first_try(it, res["first_issues"])
                runs.append({"case": case, "arm": arm, "blocks": blocks, "item": it["name"], "repeat": r, "run_id": rid,
                             **{k: v for k, v in res.items() if k not in ("final_xml", "first_xml")},
                             "refs_first_try": [placed, planned]})
                print(f"  first try ok={res['first_ok']} refs {placed}/{planned} passes={res['validator_passes']} "
                      f"final ok={res['final_ok']} ${res['cost_usd']:.3f}", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    return runs


# ── scoring (free) ────────────────────────────────────────────────────────────

def rescore(label: str, render: bool = True) -> list[dict]:
    out = OUT / label
    items = {it["name"]: it for it in json.loads(INPUTS.read_text(encoding="utf-8"))}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        it = items[row["item"]]
        d = out / row["arm"] / row["case"]
        xml = (d / "final.xml").read_text(encoding="utf-8") if (d / "final.xml").exists() else ""
        if not xml:
            row["score"] = None
            continue
        dest = d / "slide-0"
        row["score"] = score(row["arm"], dest, compile_slide(deck_font(xml), resolve_theme(it["theme"])["element"], dest),
                             it["plan"], row["case"], render)
    (out / "results.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts.experiments.node_test import node_test_sheet as S
        S.build(out / "B", out / "A", out / "sheets")   # B (tiles) plays the "nodes" role in key.json
    write_summary(out, runs)
    return runs


def _min_size(s: dict | None) -> float | None:
    v = [x for c in ((s or {}).get("sizes") or {}).values() for x in c["sizes"] + c["hero"]]
    return min(v) if v else None


def write_summary(out: Path, runs: list[dict]) -> None:
    by = {(r["case"], r["arm"]): r for r in runs}
    lines = ["# Tile nodes, same-plan check (generator only; A = POM_BLOCKS=kpi, B = POM_BLOCKS=tiles)", ""]
    for arm, blocks in ARMS:
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        first_err = sum(1 for r in rs if any(i["severity"] == "error" for i in r["first_issues"]))
        lines.append(f"- **{arm} ({blocks})**: {len(rs)} runs, ${sum(r['cost_usd'] for r in rs):.3f}; first try compiled "
                     f"{sum(r['first_ok'] for r in rs)}/{len(rs)}, NODE_* error on the first try {first_err}, final "
                     f"compiled {sum(r['final_ok'] for r in rs)}/{len(rs)}, repair passes "
                     f"{sum(max(0, r['validator_passes'] - 1) for r in rs)}, errors {sum(1 for r in rs if r.get('error'))}")
    lines += ["", "| slide plan | smallest number A / B (px) | card empty A / B | broken A / B | off-plan A / B | first try A / B | $ A / B |",
              "|---|---|---|---|---|---|---|"]
    larger = smaller = same = 0
    for case in dict.fromkeys(r["case"] for r in runs):
        a, b = by.get((case, "A"), {}), by.get((case, "B"), {})
        sa, sb = a.get("score") or {}, b.get("score") or {}
        pa, pb = _min_size(sa), _min_size(sb)
        if pa is not None and pb is not None:
            larger, smaller, same = larger + (pb > pa), smaller + (pb < pa), same + (pb == pa)
        f = lambda s: sum((s.get("fill") or {}).values()) if s else "-"
        lines.append(f"| {case} | {pa} / {pb} | {f(sa)} / {f(sb)} | {sa.get('broken')} / {sb.get('broken')} | "
                     f"{len(sa.get('off_plan') or [])} / {len(sb.get('off_plan') or [])} | "
                     f"{'ok' if a.get('first_ok') else 'fail'} / {'ok' if b.get('first_ok') else 'fail'} | "
                     f"{a.get('cost_usd', 0):.3f} / {b.get('cost_usd', 0):.3f} |")
    lines += ["", f"Tiles' smallest number vs element refs on the same plan: larger {larger}, smaller {smaller}, same {same}.",
              "", "Blind sheet: sheets/ (fill marks.csv; key.json: the 'nodes' side is tiles)."]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def bundle(label: str) -> Path:
    out = OUT / label
    z = OUT / f"{label}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in out.rglob("*"):
            if p.is_file():
                f.write(p, p.relative_to(OUT))
        for r in json.loads((out / "runs.json").read_text(encoding="utf-8")):
            run_dir = ROOT / "output" / "runs" / r["run_id"]
            for p in run_dir.rglob("*") if run_dir.exists() else []:
                if p.is_file() and p.suffix in (".xml", ".json", ".log", ".txt"):
                    f.write(p, Path(label) / "runs" / p.relative_to(ROOT / "output" / "runs"))
    return z


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", default="same-plan")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--rescore", action="store_true", help="free: score saved runs again")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: fake generator, checks the path end to end")
    ap.add_argument("--make-inputs", nargs=2, type=Path, metavar=("TILES_DIR", "KPI_DIR"),
                    help="build PC: write the inputs file from the two wide-paid run folders")
    a = ap.parse_args()
    if a.make_inputs:
        make_inputs(*a.make_inputs)
        return 0
    if a.dry:
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        run(a.label, a.repeat, dry=True)
    elif not a.rescore:
        if not os.environ.get("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set (.env): the paid check runs on the test PC")
            return 2
        from src.utils.logging_config import add_file_log, setup_logging
        setup_logging()
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        (OUT / a.label).mkdir(parents=True, exist_ok=True)
        add_file_log(OUT / a.label / "run.log")
        run(a.label, a.repeat)
    rescore(a.label, render=not a.no_render)
    if a.bundle:
        print(f"EMAIL THIS FILE: {bundle(a.label)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
