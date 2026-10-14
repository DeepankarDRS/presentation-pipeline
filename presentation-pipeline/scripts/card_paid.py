"""Card tile nodes, paid check part 2 (docs/tile-nodes-spec-2026-10-12.md §11): the generator on fresh planner plans.

    python -m scripts.card_plan_only --repeat 3 --label card-plans                         # part 1 (planners, ~$1.30)
    python -m scripts.card_paid --plans card-plans --repeat 3 --label card-paid --bundle   # part 2 (generator, ~$0.60)
    python -m scripts.card_paid --label card-paid --rescore                                # free: scores + sheet again
    python -m scripts.card_paid --label card-dry --dry                                     # free: path check, fake LLM

Inputs: docs/eval/card-nodes/paid-inputs.json (12 saved card slides from six decks: plan, the LLM's hand-drawn XML,
theme; committed so the test PC needs no output/). Arm B: POM_BLOCKS=tiles, the real graph from a slide plan (style
resolver -> context builder -> generator -> validator with the tile expansion -> repairers; critic off), on the plan the
planning-only run made for that slide (matched by card titles; a repeat uses its own run's plan). Arm A: the saved
hand-drawn slide (already paid for), recompiled on this commit. Both compile with the deck font and render in Inter
(scripts.card_replay), and are scored like the replay: card title / body sizes, GEOM_CARD_EMPTY, broken words, rendered
overlaps, LOW_CONTRAST, plan text missing; plus the first try's NODE_* codes, hand-written cards and the card XML's
tokens. Writes output/card-paid/<label>/: runs.json, results.json, summary.md, sheets/ (blind A / B); --bundle zips it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from scripts import card_replay as R  # noqa: E402
from scripts.kpi_paid import REF_CODES, _FakeLLM, run_one  # noqa: E402
from scripts.kpi_replay import score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import cards as C  # noqa: E402

INPUTS = ROOT / "docs" / "eval" / "card-nodes" / "paid-inputs.json"
OUT = ROOT / "output" / "card-paid"


def _titles(plan: dict) -> set[str]:
    return {R.norm(c.get("title")) for comp in C.card_components(plan).values() for c in C.cards_of(comp) if c.get("title")}


def fresh_plan(plans: list[dict], it: dict, r: int) -> dict | None:
    """The planner run's plan of the saved slide (repeat r, else r1): a slide with a card_grid whose titles overlap the
    saved plan's most (a tie: the same slide_index), else the same slide_index if it has a card_grid; None otherwise."""
    runs = [x for x in plans if x.get("case") == it["case"]]
    run_ = next((x for x in runs if x.get("repeat") == r), runs[0] if runs else None)
    cand = [p for p in (run_ or {}).get("slide_plans") or [] if C.card_components(p)]
    want, idx = _titles(it["plan"]), it["plan"].get("slide_index", it["slide"])
    best = max(((len(want & _titles(p)), p.get("slide_index") == idx, p) for p in cand), key=lambda t: t[:2], default=None)
    if best and (best[0] or best[1]):
        return best[2]
    return None


def card_tokens(xml: str, plan: dict) -> tuple[int, int]:
    """(tokens of the card tags in the LLM's first XML, cards it drew by hand instead of with tags)."""
    tags = re.findall(r"<CardGrid\b.*?(?:/>|</CardGrid>)|<Card\b[^>]*/>", xml, re.S)
    drawn = C.expand(xml, plan)["card_items"] if tags else {}
    planned = sum(len(C.cards_of(c)) for c in C.card_components(plan).values())
    return R.tokens("".join(tags)) if tags else 0, max(0, planned - sum(drawn.values()))


def run(label: str, repeat: int, plans: str | None, dry: bool = False) -> None:
    out = OUT / label
    items = json.loads(INPUTS.read_text(encoding="utf-8"))
    fresh = json.loads((ROOT / "output" / "card-plans" / plans / "runs.json").read_text(encoding="utf-8")) if plans else None
    results = []
    for r in range(1, repeat + 1):
        for it in items:
            name = f"{it['case']}-s{it['slide']}"
            rid = f"card-{name}-r{r}-{int(time.time())}"
            row: dict[str, Any] = {"case": f"{name}-r{r}", "item": it["case"], "slide": it["slide"], "repeat": r, "run_id": rid}
            plan = it["plan"]
            if fresh is not None:
                plan = fresh_plan(fresh, it, r)
                if plan is None:
                    print(f"{name} r{r}: skipped, the planner made no card_grid for this slide", flush=True)
                    results.append({**row, "skipped": "no card_grid in the fresh plan"})
                    continue
            (out / "B" / row["case"]).mkdir(parents=True, exist_ok=True)
            (out / "B" / row["case"] / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"run {name} r{r} ...", flush=True)
            try:
                if dry:   # the LLM's saved slide with its cards as bare tags (card_replay), answered by a fake generator
                    from src.agents import generator
                    root = R._parse(it["xml_today"])
                    for comp in C.card_components(plan).values():
                        R.rewrite_component(root, comp)
                    generator.get_llm = lambda step, _x=R._serial(root): _FakeLLM(_x)
                from src.utils.case_loader import load_case
                case = load_case(it["case"])
                res = run_one({**it, "plan": plan, "request": case.get("request", case.get("objective", ""))}, rid)
            except Exception as e:   # one failure must not cost the other runs
                res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                       "final_xml": "", "cost_usd": 0.0, "validator_passes": 0, "generator_calls": 0}
            first = res.get("first_xml") or ""
            row.update({k: v for k, v in res.items() if k not in ("final_xml", "first_xml", "kpi_tokens", "hand_items")})
            row["card_tokens"], row["hand_cards"] = card_tokens(first, plan) if first else (None, None)
            (out / "B" / row["case"] / "final.xml").write_text(res["final_xml"], encoding="utf-8")
            if first:
                (out / "B" / row["case"] / "first.xml").write_text(first, encoding="utf-8")
            results.append(row)
            print(f"  first ok={res['first_ok']} card tokens={row['card_tokens']} hand cards={row['hand_cards']} "
                  f"passes={res['validator_passes']} final ok={res['final_ok']} ${res['cost_usd']:.3f}", flush=True)
            (out / "runs.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "runs.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


def _score(arm: str, d: Path, xml: str, theme: str, plan: dict, case: str, render: bool) -> dict:
    shutil.rmtree(d, ignore_errors=True)
    comp = R.compile_slide(R.deck_font(xml), theme, d)
    if render:
        R.render(d)
    sc = score(arm, d, comp, plan, case, render)
    final = (d / "fitted.xml").read_text(encoding="utf-8") if (d / "fitted.xml").exists() else comp["cleaned"]
    sc.pop("sizes", None), sc.pop("off_plan", None)
    sc["cards"] = R.card_sizes(final, plan, "B" if arm == "B" else "A")
    sc["missing"] = R.missing_text(final, plan)
    sc["overlaps"] = R.overlaps(d / "presentation.pdf" if (d / "presentation.pdf").exists() else None)
    return sc


def rescore(label: str, render: bool = True, refill: bool = False) -> list[dict]:
    out = OUT / label
    items = {f"{i['case']}-s{i['slide']}": i for i in json.loads(INPUTS.read_text(encoding="utf-8"))}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        if row.get("skipped"):
            continue
        it = items[f"{row['item']}-s{row['slide']}"]
        theme = resolve_theme(it["theme"])["element"]
        plan = json.loads((out / "B" / row["case"] / "plan.json").read_text(encoding="utf-8"))
        row["A"] = _score("A", out / "A" / row["case"] / "slide-1", R.BARE_AMP.sub("&amp;", it["xml_today"]), theme,
                          it["plan"], row["case"], render)
        xml = (out / "B" / row["case"] / "final.xml").read_text(encoding="utf-8")
        first = out / "B" / row["case"] / "first.xml"
        if refill and first.exists() and row.get("validator_passes") == 1:   # this commit's card / tile expansion
            from src.compiler.nodes import tiles                              # of the LLM's own XML (no repair ran)
            xml = tiles.fill(R.BARE_AMP.sub("&amp;", first.read_text(encoding="utf-8")), plan)["xml"]
        row["B"] = _score("B", out / "B" / row["case"] / "slide-1", xml, theme, plan, row["case"], render) if xml else None
    (out / "results.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts import node_test_sheet as S
        S.build(out / "B", out / "A", out / "sheets")
    write_summary(out, runs)
    return runs


def write_summary(out: Path, runs: list[dict]) -> None:
    done = [r for r in runs if not r.get("skipped")]
    scored = [r for r in done if r.get("A") and r.get("B")]

    def tot(arm, f):
        return sum(f(r[arm]) or 0 for r in scored if r[arm]["compiled"])

    def med(arm, key):
        vals = sorted(c[key] for r in scored for c in r[arm]["cards"].values() if c[key])
        return vals[len(vals) // 2] if vals else 0
    first_err = sum(1 for r in done if any(i["severity"] == "error" for i in r.get("first_issues") or []))
    toks = [r["card_tokens"] for r in done if r.get("card_tokens") is not None]
    lines = [f"# Card paid check (generator on fresh plans, POM_BLOCKS=tiles; arm A = the saved hand-drawn slides)", "",
             f"{len(done)} runs ({len(runs) - len(done)} skipped: the planner made no card_grid), "
             f"${sum(r.get('cost_usd') or 0 for r in done):.3f}. First try compiled: {sum(r['first_ok'] for r in done)}/{len(done)}; "
             f"NODE_* error on the first try: {first_err}; final compiled: {sum(r['final_ok'] for r in done)}/{len(done)}; "
             f"repair passes: {sum(max(0, r['validator_passes'] - 1) for r in done)}; cards drawn by hand instead of tags: "
             f"{sum(r.get('hand_cards') or 0 for r in done)}; card tag tokens, mean: "
             f"{round(sum(toks) / len(toks)) if toks else '-'}.", "",
             "| | A (saved, hand-drawn) | B (tiles, fresh plan) |", "|---|---|---|",
             f"| compiled | {sum(r['A']['compiled'] for r in scored)} | {sum(r['B']['compiled'] for r in scored)} |",
             f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill']['GEOM_CARD_EMPTY'])} | {tot('B', lambda s: s['fill']['GEOM_CARD_EMPTY'])} |",
             f"| broken words / overlaps (render) | {tot('A', lambda s: s['broken'])} / {tot('A', lambda s: len(s['overlaps']))} | "
             f"{tot('B', lambda s: s['broken'])} / {tot('B', lambda s: len(s['overlaps']))} |",
             f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])} | {tot('B', lambda s: s['low_contrast'])} |",
             f"| plan text missing | {sum(len(r['A']['missing']) for r in scored)} | {sum(len(r['B']['missing']) for r in scored)} |",
             f"| smallest card title / body (median px) | {med('A', 'title_min')} / {med('A', 'body_min')} | "
             f"{med('B', 'title_min')} / {med('B', 'body_min')} |",
             "", "Blind sheet: sheets/ (fill marks.csv; key.json after marking). Plans: B/<run>/plan.json."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
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
    ap.add_argument("--label", default="card-paid")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--plans", help="paid run: the planning-only label (output/card-plans/<label>/runs.json)")
    ap.add_argument("--rescore", action="store_true", help="free: score saved runs again")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--refill", action="store_true", help="with --rescore: re-expand first-try slides with this commit's code")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: fake generator (the saved slide with bare tags)")
    a = ap.parse_args()
    if a.dry:
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        run(a.label, 1, a.plans, dry=True)
    elif not a.rescore:
        if not a.plans:
            print("--plans <label> is required for the paid run (python -m scripts.card_plan_only first)")
            return 2
        if not os.environ.get("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set (.env): the paid check runs on the test PC")
            return 2
        run(a.label, a.repeat, a.plans)
    rescore(a.label, render=not a.no_render, refill=a.refill)
    if a.bundle:
        print(bundle(a.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
