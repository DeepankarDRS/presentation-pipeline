"""KPI / card composition nodes, paid same-plan check (docs/composition-convention-spec.md §10 step 5): generator only.

    python -m scripts.composition_paid --label composition-paid --bundle      # paid, test PC (OPENAI_API_KEY)
    python -m scripts.composition_paid --label composition-paid --rescore     # free: score + blind sheet again
    python -m scripts.composition_paid --label dry --dry --limit 2            # free: fake generator (path check)
    python -m scripts.composition_paid --estimate                             # free: cases + cost estimate only

The same saved slide plans go through the real graph from the plan (scripts.kpi_paid.run_one: style resolver ->
context builder -> generator -> validator -> repairers; critic off), twice:
- A = today's tile nodes: POM_BLOCKS=tiles, POM_NODES empty (bare <KpiGrid> / <CardGrid> tags, tiles.py / cards.py);
- B = composition nodes: POM_BLOCKS=tiles (KPI text is element refs), POM_NODES=kpi_row,card_grid
  (<KpiRow ref variant> / <CardGrid ref variant>, src/compiler/nodes/tile_groups.py).
The script sets both switches per arm before each run (they are read at call time; .env values are loaded first and
never override them). Cases: the 12 KPI plans of docs/eval/tile-nodes/same-plan/inputs.json (one also holds a
card_grid) and CARD_PICKS from docs/eval/card-nodes/paid-inputs.json (card plans on the same decks).
Per run: the first try's NODE_* codes (NODE_ATTR_ALIAS / NODE_TAG_ALIAS / NODE_VARIANT_* / NODE_LOOK_FROM_HINT),
the composition the generator wrote vs the default code would pick (B), repairs, cost, and the final slide scored like
the replays (scripts.kpi_replay.score; cards also scripts.card_replay.missing_text). Writes
output/composition-paid/<label>/: runs.json, results.json, summary.md, sheets/ (blind A / B: fill marks.csv; key.json
says which side is the composition nodes) and, with --bundle, <label>.zip to email back.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import kpi_paid as KP  # noqa: E402
from scripts import tile_same_plan as TS  # noqa: E402
from scripts.kpi_replay import compile_slide, score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import cards, element_refs, tile_groups, tiles  # noqa: E402

KPI_INPUTS = TS.INPUTS
CARD_INPUTS = ROOT / "docs" / "eval" / "card-nodes" / "paid-inputs.json"
CARD_PICKS = (("deck-qbr-data", 4), ("deck-product-launch-data", 1), ("gate-deck-cheffin-full", 3))
OUT = ROOT / "output" / "composition-paid"
ARMS = {"A": {"POM_BLOCKS": "tiles", "POM_NODES": ""},
        "B": {"POM_BLOCKS": "tiles", "POM_NODES": "kpi_row,card_grid"}}
# per run on gpt-6.1-sol (docs/eval/tile-nodes/tiles-2/README.md): first try passes $0.029, a long repair $0.052
EST_RUN, EST_RUN_MAX = 0.029, 0.052
WATCH = ("NODE_ATTR_ALIAS", "NODE_TAG_ALIAS", "NODE_VARIANT_UNMET", "NODE_VARIANT_UNKNOWN", "NODE_LOOK_FROM_HINT")
_GROUP = re.compile(r"<(KpiRow|KpiGrid|CardGrid)\b([^>]*)>")
_ATTR = re.compile(r'\s(variant|layout|arrange)="[^"]*"')


def set_arm(arm: str) -> None:
    """The arm's switches (an empty POM_NODES also keeps a .env value out: load_dotenv never overrides a set key)."""
    os.environ.update(ARMS[arm])
    want = ["kpi_row", "card_grid"] if arm == "B" else []
    assert tiles.on() and tile_groups.kinds_on() == want, (arm, os.environ.get("POM_NODES"), tile_groups.kinds_on())


def items() -> list[dict]:
    from src.utils.case_loader import load_case
    out = [dict(it, kind="kpi") for it in json.loads(KPI_INPUTS.read_text(encoding="utf-8"))]
    for it in json.loads(CARD_INPUTS.read_text(encoding="utf-8")):
        if (it["case"], it["slide"]) in CARD_PICKS:
            c = load_case(it["case"])
            out.append({"name": f"card-plan-{it['case']}-s{it['slide']}", "case": it["case"], "slide": it["slide"],
                        "kind": "card", "plan": it["plan"], "theme": it["theme"],
                        "request": c.get("request", c.get("objective", ""))})
    return out


def estimate(n_items: int, repeat: int) -> tuple[int, float, float]:
    n = n_items * repeat * len(ARMS)
    return n, n * EST_RUN, n * EST_RUN_MAX


def _dry_xml(it: dict, arm: str) -> str:
    """--dry: a bare slide of the arm's tags (B writes variant="strip" on KPI groups: the written-variant path)."""
    plan = it["plan"]
    kpi = '<KpiGrid ref="{}"/>' if arm == "A" else '<KpiRow ref="{}" variant="strip"/>'
    tags = "".join(kpi.format(cid) for cid in element_refs.kpi_components(plan))
    tags += "".join(f'<CardGrid ref="{cid}"/>' for cid in cards.card_components(plan))
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
            f'<Text fontSize="36" bold="true" color="$textMain">{plan.get("slide_title", "")}</Text>{tags}</VStack></Slide>')


# ── the paid run ──────────────────────────────────────────────────────────────

def run(label: str, repeat: int, cases: list[dict], max_cost: float, dry: bool = False) -> list[dict]:
    out = OUT / label
    runs, spent = [], 0.0
    for r in range(1, repeat + 1):
        for it in cases:
            if not dry and spent + len(ARMS) * EST_RUN_MAX > max_cost:
                print(f"STOP: ${spent:.3f} spent; the next pair could pass --max-cost ${max_cost:.2f}", flush=True)
                break
            for arm in ARMS:
                set_arm(arm)
                case = f"{it['name']}-r{r}"
                rid = f"comp-{arm}-{it['case']}-s{it['slide']}-r{r}-{int(time.time())}"
                print(f"run {case} {arm} (POM_NODES={os.environ['POM_NODES'] or '-'}) ...", flush=True)
                try:
                    if dry:
                        from src.agents import generator
                        generator.get_llm = lambda step, _x=_dry_xml(it, arm): KP._FakeLLM(_x)
                    res = KP.run_one(it, rid)
                except Exception as e:   # one failure must not cost the other runs
                    res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                           "first_codes": [], "final_xml": "", "first_xml": "", "cost_usd": 0.0,
                           "validator_passes": 0, "generator_calls": 0}
                spent += res["cost_usd"]
                d = out / arm / case
                d.mkdir(parents=True, exist_ok=True)
                (d / "final.xml").write_text(res["final_xml"], encoding="utf-8")
                if res.get("first_xml"):
                    (d / "first.xml").write_text(res["first_xml"], encoding="utf-8")
                runs.append({"case": case, "arm": arm, "kind": it["kind"], "item": it["name"], "repeat": r,
                             "run_id": rid, "env": dict(ARMS[arm]),
                             **{k: v for k, v in res.items() if k not in ("final_xml", "first_xml", "repaired_xml")}})
                print(f"  first try ok={res['first_ok']} codes={sorted({c['code'] for c in res['first_codes']})} "
                      f"passes={res['validator_passes']} final ok={res['final_ok']} ${res['cost_usd']:.3f} "
                      f"(total ${spent:.3f})", flush=True)
                out.mkdir(parents=True, exist_ok=True)   # saved after every run: a stop keeps what was paid for
                (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    return runs


# ── scoring (free) ────────────────────────────────────────────────────────────

def compositions(first_xml: str, plan: dict) -> dict[str, dict]:
    """Arm B's first try, per group: the variant the generator wrote, the default code picks for the bare tag (the
    design hint's composition, else the first one) and the composition drawn."""
    set_arm("B")
    written = {}
    for m in _GROUP.finditer(first_xml):
        ref = re.search(r'\sref="([^"]*)"', m.group(2))
        if ref:
            v = re.search(r'\svariant="([^"]*)"', m.group(2))
            written[ref.group(1)] = {"tag": m.group(1), "written": v.group(1) if v else None}
    bare = _GROUP.sub(lambda m: f"<{m.group(1)}{_ATTR.sub('', m.group(2))}>", first_xml)
    try:
        drawn = tile_groups.expand(first_xml, plan)["components"]
        default = tile_groups.expand(bare, plan)["components"]
    except Exception as e:   # an unparsable first try: the written variants only
        return {cid: dict(w, error=str(e)[:120]) for cid, w in written.items()}
    return {cid: {**written.get(cid, {"tag": None, "written": None}),
                  "default": (default.get(cid) or {}).get("composition"), "drawn": (drawn.get(cid) or {}).get("composition")}
            for cid in {*written, *drawn}}


def rescore(label: str, render: bool = True) -> list[dict]:
    from scripts.card_replay import missing_text
    out = OUT / label
    by_name = {it["name"]: it for it in items()}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        it = by_name[row["item"]]
        d = out / row["arm"] / row["case"]
        first = (d / "first.xml").read_text(encoding="utf-8") if (d / "first.xml").exists() else ""
        row["compositions"] = compositions(first, it["plan"]) if row["arm"] == "B" and first else {}
        xml = (d / "final.xml").read_text(encoding="utf-8") if (d / "final.xml").exists() else ""
        if not xml:
            row["score"] = None
            continue
        set_arm(row["arm"])
        dest = d / "slide-0"
        row["score"] = score(row["arm"], dest, compile_slide(deck_font(xml), resolve_theme(it["theme"])["element"], dest),
                             it["plan"], row["case"], render)
        row["score"]["missing"] = missing_text(xml, it["plan"]) if cards.card_components(it["plan"]) else []
    (out / "results.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts import node_test_sheet as S
        S.build(out / "B", out / "A", out / "sheets")   # B (composition nodes) plays the "nodes" role in key.json
    write_summary(out, runs)
    return runs


def write_summary(out: Path, runs: list[dict]) -> None:
    by = {(r["case"], r["arm"]): r for r in runs}
    lines = ["# KPI / card composition nodes, same-plan check (generator only; A = tile nodes, "
             "B = POM_NODES=kpi_row,card_grid; both POM_BLOCKS=tiles)", ""]
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        codes = [c["code"] for r in rs for c in r.get("first_codes") or []]
        first_err = sum(1 for r in rs if any(c["severity"] == "error" for c in r.get("first_codes") or []))
        lines.append(f"- **{arm}**: {len(rs)} runs, ${sum(r['cost_usd'] for r in rs):.3f}; first try compiled "
                     f"{sum(r['first_ok'] for r in rs)}/{len(rs)}, NODE_* error on the first try {first_err}, final "
                     f"compiled {sum(r['final_ok'] for r in rs)}/{len(rs)}, repair passes "
                     f"{sum(max(0, r['validator_passes'] - 1) for r in rs)}, errors {sum(1 for r in rs if r.get('error'))}; "
                     + ", ".join(f"{c} {codes.count(c)}" for c in WATCH))
    lines += ["", "## Compositions (B, first try): written by the generator / default for the bare tag / drawn", "",
              "| run | group | tag | written | default | drawn |", "|---|---|---|---|---|---|"]
    for r in runs:
        for cid, c in sorted((r.get("compositions") or {}).items()):
            lines.append(f"| {r['case']} | {cid} | {c.get('tag')} | {c.get('written') or '-'} | {c.get('default')} | "
                         f"{c.get('drawn')} |")
    lines += ["", "## Pairs (final slide)", "",
              "| slide plan | smallest number A / B (px) | card empty A / B | broken A / B | off-plan / missing A / B "
              "| first try A / B | codes B | $ A / B |", "|---|---|---|---|---|---|---|---|"]
    for case in dict.fromkeys(r["case"] for r in runs):
        a, b = by.get((case, "A"), {}), by.get((case, "B"), {})
        sa, sb = a.get("score") or {}, b.get("score") or {}
        f = lambda s: sum((s.get("fill") or {}).values()) if s else "-"
        m = lambda s: len(s.get("off_plan") or []) + len(s.get("missing") or [])
        lines.append(f"| {case} | {TS._min_size(sa)} / {TS._min_size(sb)} | {f(sa)} / {f(sb)} | {sa.get('broken')} / "
                     f"{sb.get('broken')} | {m(sa)} / {m(sb)} | {'ok' if a.get('first_ok') else 'fail'} / "
                     f"{'ok' if b.get('first_ok') else 'fail'} | "
                     f"{' '.join(sorted({c['code'][5:] for c in b.get('first_codes') or []})) or '-'} | "
                     f"{a.get('cost_usd', 0):.3f} / {b.get('cost_usd', 0):.3f} |")
    lines += ["", "Blind sheet: sheets/ (fill marks.csv; key.json: the 'nodes' side is B, the composition nodes)."]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", default="composition-paid")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", choices=("kpi", "card"), help="only the KPI plans or only the card plans")
    ap.add_argument("--limit", type=int, help="the first N plans (a dry path check)")
    ap.add_argument("--max-cost", type=float, default=1.0, help="stop before a pair could pass this total (USD)")
    ap.add_argument("--estimate", action="store_true", help="free: print the cases and the cost estimate, then stop")
    ap.add_argument("--rescore", action="store_true", help="free: score saved runs again")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: fake generator, checks the path end to end")
    a = ap.parse_args()
    cases = [it for it in items() if not a.only or it["kind"] == a.only][:a.limit]
    if not a.rescore:
        n, est, worst = estimate(len(cases), a.repeat)
        print(f"{len(cases)} plans x {a.repeat} repeat x {len(ARMS)} arms = {n} runs; estimate ${est:.2f} "
              f"(all long repairs ${worst:.2f}); stop at --max-cost ${a.max_cost:.2f}")
        for it in cases:
            print(f"  {it['kind']:4} {it['name']}")
        if a.estimate:
            return 0
    if a.dry:
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        run(a.label, a.repeat, cases, a.max_cost, dry=True)
    elif not a.rescore:
        if not os.environ.get("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")   # before set_arm: the arm's switches override any POM_* in .env
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set (.env): the paid check runs on the test PC")
            return 2
        from src.utils.logging_config import add_file_log, setup_logging
        setup_logging()
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        (OUT / a.label).mkdir(parents=True, exist_ok=True)
        add_file_log(OUT / a.label / "run.log")
        run(a.label, a.repeat, cases, a.max_cost)
    rescore(a.label, render=not a.no_render)
    if a.bundle:
        print(f"EMAIL THIS FILE: {TS.bundle(a.label, OUT)}")   # zip layout as the tile same-plan check
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
