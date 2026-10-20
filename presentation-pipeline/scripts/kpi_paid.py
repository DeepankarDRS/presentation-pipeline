"""KPI node pilot, paid check (docs/kpi-node-pilot-2026-10-11.md §4): generator only, on saved plans.

    python -m scripts.kpi_paid --repeat 1 --label kpi-paid --bundle      # needs OPENAI_API_KEY (test PC)
    python -m scripts.kpi_paid --label kpi-paid --rescore                  # free: scores + sheet again
    python -m scripts.kpi_paid --label dry --dry                           # free: a fake generator answers with
                                                                           # today's XML mapped to refs (path check)
    python -m scripts.kpi_paid --blocks tiles --arm-a kpi --label tiles-paid --bundle   # tile nodes (spec §8 step 5)
    python -m scripts.kpi_plan_only deck-qbr-data gate-deck-cheffin-full --repeat 3 --label p3   # then arm B on
    python -m scripts.kpi_paid --blocks tiles --arm-a kpi --plans p3 --repeat 3 --label tiles-paid-3   # fresh plans
    python -m scripts.kpi_paid --blocks tiles --arm-a kpi --label <copy> --rescore --refill   # free: tile code
                                                    # changes on saved runs (B expanded again from first.xml)

Inputs: docs/eval/kpi-node/paid-inputs.json (the 3 KPI slides of q1008's deck-qbr-data and
gate-deck-cheffin-full: plan, today's XML, theme, brief; committed so the test PC needs no output/).
Arm B: POM_BLOCKS=kpi, the real graph from the plan (style resolver -> context builder -> generator ->
validator with the ref fill -> repairer / visual repairer as in a normal run; critic off, as q1008's
deck-qbr-data). Arm A: today's XML from q1008 recompiled on this commit (free, already paid for).
Per run the first try is recorded (refs placed, NODE_* errors) and the final slide is scored like the
replay (scripts/kpi_replay.score).
--blocks tiles: arm B on POM_BLOCKS=tiles (<KpiGrid> / <Kpi>, docs/tile-nodes-spec-2026-10-12.md); --arm-a kpi:
arm A = the 2026-10-11 paid check's element-ref slides (docs/eval/tile-nodes/paid-kpi-arm.json, recompiled on
this commit) instead of q1008's XML. Both record the first generator call's tokens and the KPI XML's tokens
(tile tags + hand-written ref tiles, scripts/tile_replay.kpi_xml) and the hand-written tiles a tiles run used. Writes output/kpi-paid/<label>/: results.json, summary.md, sheets/
(blind A / B, scripts/node_test_sheet.py) and, with --bundle, <label>.zip to email back.
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
os.environ.setdefault("POM_BLOCKS", "kpi")   # read per call; main() sets it from --blocks

from scripts.kpi_replay import compile_slide, score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes.element_refs import kpi_components  # noqa: E402

INPUTS = ROOT / "docs" / "eval" / "kpi-node" / "paid-inputs.json"
KPI_ARM = ROOT / "docs" / "eval" / "tile-nodes" / "paid-kpi-arm.json"   # {run case: final XML} of the 2026-10-11 paid check
OUT = ROOT / "output" / "kpi-paid"
REF_CODES = ("NODE_REF_UNKNOWN", "NODE_REF_DUPLICATE", "NODE_ITEM_MISSING", "NODE_LABEL_MISSING", "NODE_FIELD_MISSING",
             "NODE_BYPASSED", "NODE_ATTR_IGNORED", "NODE_FOCUS_UNNAMED", "NODE_VALUE_TEXT",
             "NODE_ATTR_UNKNOWN", "NODE_ATTR_DROPPED", "NODE_VARIANT_UNKNOWN", "NODE_VARIANT_UNMET", "LITERAL_COLOR")


def run_one(item: dict, run_id: str) -> dict[str, Any]:
    """The graph from one saved slide plan; returns the final state's slide + the first validator pass."""
    from src.graph import compile_graph
    from src.state import initial_state
    from src.utils.logging_config import set_context

    set_context(run_id=run_id)
    state = initial_state(run_id=run_id, raw_request=item["request"], theme_name=item["theme"],
                          deck_min_threshold=1, critic_mode="off")
    state["slide_plans"] = [dict(item["plan"], slide_index=0)]
    attempts, generated, final = [], [], {}
    cfg = {"run_name": f"kpi-paid-{run_id}", "tags": ["kpi-pilot"], "recursion_limit": 80}
    for mode, chunk in compile_graph().stream(state, config=cfg, stream_mode=["updates", "values"]):
        if mode == "values":
            final = chunk
            continue
        for node, update in chunk.items():
            if node == "validator" and isinstance(update, dict):
                attempts.append(update)
            elif node == "generator" and isinstance(update, dict) and update.get("current_xml"):
                generated.append(update["current_xml"])
    first = attempts[0] if attempts else {}
    issues = [i for i in (first.get("normalize_result") or {}).get("issues") or [] if i.get("code") in REF_CODES]
    gen = [g for g in final.get("generation_history") or [] if getattr(g, "step", None) == "generator"
           or (isinstance(g, dict) and g.get("step") == "generator")]
    last = attempts[-1] if attempts else {}
    g0 = gen[0] if gen else {}
    tok = (lambda k: g0.get(k) if isinstance(g0, dict) else getattr(g0, k, None))
    first_xml = generated[0] if generated else ""
    kpi_tokens, hand_items = None, None
    if first_xml:
        from scripts.tile_replay import kpi_xml, tokens
        from src.compiler.nodes import tiles
        kpi_tokens = tokens(kpi_xml(first_xml, item["plan"]))
        if tiles.on():
            hand_items = sum(c.get("hand_items", 0) for c in tiles.fill(first_xml, item["plan"])["components"].values())
    return {
        "blocks": os.environ.get("POM_BLOCKS", "kpi"),
        "gen_tokens": {"in": tok("tokens_in"), "out": tok("tokens_out"), "cached": tok("tokens_cached")},
        "kpi_tokens": kpi_tokens,
        "hand_items": hand_items,
        "first_ok": bool((first.get("compile_result") or {}).get("ok")),
        "first_issues": [{k: i.get(k) for k in ("code", "severity", "message")} for i in issues],
        "first_diagnostics": [f"{d.get('type', '?')}: {str(d.get('message', ''))[:200]}"
                              for d in (first.get("compile_result") or {}).get("diagnostics") or []][:5],
        "first_xml": generated[0] if generated else "",
        "validator_passes": len(attempts),
        "generator_calls": len(gen),
        "final_xml": (last.get("normalize_result") or {}).get("cleaned_xml") or final.get("current_xml", ""),
        "final_ok": bool((last.get("compile_result") or {}).get("ok")),
        "cost_usd": ((final.get("evaluation") or {}).get("cost") or {}).get("total_usd", 0.0),
    }


def refs_first_try(item: dict, issues: list[dict]) -> tuple[int, int]:
    """(values placed by ref on the first try, values planned)."""
    n = sum(len((c.get("content_data") or {}).get("kpi_values") or []) for c in kpi_components(item["plan"]).values())
    lost = sum(1 for i in issues if i["code"] in ("NODE_ITEM_MISSING", "NODE_BYPASSED"))
    return n - lost, n


class _FakeLLM:
    """--dry: answers every generator call with today's XML for the slide mapped to refs."""
    def __init__(self, xml: str) -> None:
        self.xml = xml

    def invoke(self, messages):
        from types import SimpleNamespace
        return SimpleNamespace(content=self.xml, response_metadata={"finish_reason": "stop", "model_name": "dry"})


def _kpi_labels(plan: dict) -> set[str]:
    return {str(lbl).strip().lower() for c in kpi_components(plan).values()
            for lbl in (c.get("content_data") or {}).get("kpi_labels") or []}


def fresh_plan(plans: list[dict], it: dict, r: int) -> dict | None:
    """--plans: the planner run's plan of the saved item's slide (repeat r, else r1): the slide whose kpi_row labels
    overlap the saved plan's most (a tie: the same slide_index); None when no slide shares a KPI label."""
    runs = [x for x in plans if x.get("case") == it["case"]]
    run_ = next((x for x in runs if x.get("repeat") == r), runs[0] if runs else None)
    want, idx = _kpi_labels(it["plan"]), it["plan"].get("slide_index")
    scored = [(len(want & _kpi_labels(p)), p.get("slide_index") == idx, p) for p in (run_ or {}).get("slide_plans") or []]
    best = max(scored, key=lambda t: (t[0], t[1]), default=None)
    return best[2] if best and best[0] else None


def run(label: str, repeat: int, dry: bool = False, plans: str | None = None) -> None:
    out = OUT / label
    items = json.loads(INPUTS.read_text(encoding="utf-8"))
    fresh = json.loads((ROOT / "output" / "kpi-plans" / plans / "runs.json").read_text(encoding="utf-8")) if plans else None
    results = []
    for r in range(1, repeat + 1):
        for it in items:
            name = f"{it['case']}-s{it['slide']}"
            rid = f"kpi-{name}-r{r}-{int(time.time())}"
            print(f"run {name} r{r} ...", flush=True)
            if fresh is not None:   # this slide planned again (kpi_plan_only); scored against that plan
                plan = fresh_plan(fresh, it, r)
                if plan is None:
                    print("  skipped: the planner run has no slide with these KPI labels", flush=True)
                    continue
                it = {**it, "plan": plan}
                (out / "B" / f"{name}-r{r}").mkdir(parents=True, exist_ok=True)
                (out / "B" / f"{name}-r{r}" / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False),
                                                                     encoding="utf-8")
            try:
                if dry:
                    from scripts.kpi_replay import map_refs
                    from src.agents import generator
                    skel = map_refs(it["xml_today"], it["plan"])[0]
                    if os.environ.get("POM_BLOCKS") == "tiles":   # the same tiles as tile tags
                        from scripts.tile_replay import rewrite
                        skel = rewrite(skel, it["plan"])["xml"]
                    generator.get_llm = lambda step, _x=skel: _FakeLLM(_x)
                res = run_one(it, rid)
            except Exception as e:   # one failure must not cost the other runs
                res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                       "final_xml": "", "cost_usd": 0.0, "validator_passes": 0, "generator_calls": 0}
            placed, planned = refs_first_try(it, res["first_issues"])
            row = {"case": f"{name}-r{r}", "item": it["case"], "slide": it["slide"], "repeat": r, "run_id": rid,
                   **{k: v for k, v in res.items() if k not in ("final_xml", "first_xml")}, "refs_first_try": [placed, planned]}
            (out / "B" / row["case"] / "slide-0").mkdir(parents=True, exist_ok=True)
            (out / "B" / row["case"] / "final.xml").write_text(res["final_xml"], encoding="utf-8")
            if res.get("first_xml"):
                (out / "B" / row["case"] / "first.xml").write_text(res["first_xml"], encoding="utf-8")
            results.append(row)
            print(f"  first try ok={res['first_ok']} refs {placed}/{planned} passes={res['validator_passes']} "
                  f"final ok={res['final_ok']} ${res['cost_usd']:.3f}", flush=True)
    (out / "runs.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


def rescore(label: str, render: bool = True, arm_a: str = "today", refill: bool = False) -> list[dict]:
    out = OUT / label
    kpi_arm = json.loads(KPI_ARM.read_text(encoding="utf-8")) if arm_a == "kpi" else {}
    items = {f"{i['case']}-s{i['slide']}": i for i in json.loads(INPUTS.read_text(encoding="utf-8"))}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        it = items[f"{row['item']}-s{row['slide']}"]
        theme = resolve_theme(it["theme"])["element"]
        a_dir, b_dir = out / "A" / row["case"] / "slide-0", out / "B" / row["case"] / "slide-0"
        if arm_a == "kpi":   # the element-ref route's slide of the same run (repeat r1 when this one has none)
            a_xml = kpi_arm.get(row["case"]) or kpi_arm[f"{row['item']}-s{row['slide']}-r1"]
            row["A"] = score("B", a_dir, compile_slide(a_xml, theme, a_dir), it["plan"], row["case"], render)
        else:   # free: always recompile both arms on this commit
            row["A"] = score("A", a_dir, compile_slide(it["xml_today"], theme, a_dir), it["plan"], row["case"], render)
        xml = (out / "B" / row["case"] / "final.xml").read_text(encoding="utf-8")
        first = out / "B" / row["case"] / "first.xml"
        plan_file = out / "B" / row["case"] / "plan.json"   # --plans: arm B's own plan
        if plan_file.exists():
            it = {**it, "plan": json.loads(plan_file.read_text(encoding="utf-8"))}
        if refill and first.exists() and row.get("validator_passes") == 1:   # this commit's tile expansion of the
            from src.compiler.nodes import tiles                              # LLM's own XML (no repair ran)
            xml = tiles.fill(first.read_text(encoding="utf-8"), it["plan"])["xml"]
        # runs filled before ids carried the plan weight's rank (kpiv-cid-i -> kpiv<rank>-cid-i, as the fill writes now)
        from src.compiler.nodes.element_refs import WEIGHT_RANK
        for cid, c in kpi_components(it["plan"]).items():
            rank = WEIGHT_RANK.get(c.get("weight") or "peer", 1)
            xml = xml.replace(f'id="kpiv-{cid}-', f'id="kpiv{rank}-{cid}-').replace(f'id="kpih-{cid}-', f'id="kpih{rank}-{cid}-')
        row["B"] = score("B", b_dir, compile_slide(xml, theme, b_dir), it["plan"], row["case"], render) if xml else None
    (out / "results.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts import node_test_sheet as S
        S.build(out / "B", out / "A", out / "sheets")
    write_summary(out, runs, arm_a)
    return runs


def write_summary(out: Path, runs: list[dict], arm_a: str = "today") -> None:
    placed = sum(r["refs_first_try"][0] for r in runs)
    planned = sum(r["refs_first_try"][1] for r in runs)
    first_err = sum(1 for r in runs if any(i["severity"] == "error" for i in r["first_issues"]))
    blocks = runs[0].get("blocks", "kpi") if runs else "kpi"
    gen = [r.get("gen_tokens") or {} for r in runs]
    kt = [r["kpi_tokens"] for r in runs if r.get("kpi_tokens") is not None]
    lines = [f"# KPI paid check (generator only, POM_BLOCKS={blocks}; arm A = "
             f"{'the element-ref route, 2026-10-11' if arm_a == 'kpi' else 'q1008 XML'})", "",
             f"Generator first call, mean tokens: in {_mean([g.get('in') for g in gen])}, cached {_mean([g.get('cached') for g in gen])}, "
             f"out {_mean([g.get('out') for g in gen])}; KPI XML tokens (first try) mean {_mean(kt)}; hand-written tiles "
             f"in tiles runs: {sum(r.get('hand_items') or 0 for r in runs)}.", "",
             f"{len(runs)} runs, ${sum(r['cost_usd'] for r in runs):.3f}. Value refs placed on the first try: "
             f"**{placed}/{planned}** ({round(100 * placed / planned) if planned else 0}%); runs with a NODE_* error "
             f"on the first try: {first_err}; final compiled: {sum(r['final_ok'] for r in runs)}/{len(runs)}; "
             f"repair passes (validator passes - 1): {sum(max(0, r['validator_passes'] - 1) for r in runs)}.", "",
             "| run | first try | refs | passes | broken A / B | sizes A / B | card empty A / B | off-plan B | $ |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        a, b = r.get("A") or {}, r.get("B") or {}
        sz = lambda s: "; ".join("/".join(str(round(x)) for x in sorted(set(v["sizes"]))) or "-" for v in (s.get("sizes") or {}).values())
        codes = ", ".join(sorted({i["code"] for i in r["first_issues"]})) or "clean"
        lines.append(f"| {r['case']} | {'ok' if r['first_ok'] else 'fail'} ({codes}) | {r['refs_first_try'][0]}/{r['refs_first_try'][1]} | "
                     f"{r['validator_passes']} | {a.get('broken')} / {b.get('broken')} | {sz(a)} / {sz(b)} | "
                     f"{sum((a.get('fill') or {}).values())} / {sum((b.get('fill') or {}).values())} | "
                     f"{len(b.get('off_plan') or [])} | {r['cost_usd']:.3f} |")
    lines += ["", "Blind sheet: sheets/ (fill marks.csv; B plays the 'nodes' role in key.json)."]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _mean(xs: list) -> str:
    xs = [x for x in xs if x is not None]
    return str(round(sum(xs) / len(xs))) if xs else "-"


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
    ap.add_argument("--label", default="kpi-paid")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--rescore", action="store_true", help="free: score saved runs again")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: fake generator, checks the path end to end")
    ap.add_argument("--blocks", choices=("kpi", "tiles"), default="kpi", help="POM_BLOCKS for arm B")
    ap.add_argument("--arm-a", choices=("today", "kpi"), default="today",
                    help="arm A: q1008's XML (today) or the 2026-10-11 element-ref slides (kpi)")
    ap.add_argument("--plans", help="paid run: arm B on the slide plans of output/kpi-plans/<label>/runs.json "
                    "(python -m scripts.kpi_plan_only), matched to each saved slide by its KPI labels")
    ap.add_argument("--refill", action="store_true",
                    help="--rescore: expand arm B again from the LLM's first.xml on this commit (runs with no repair)")
    a = ap.parse_args()
    os.environ["POM_BLOCKS"] = a.blocks
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
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        run(a.label, a.repeat, plans=a.plans)
    rescore(a.label, render=not a.no_render, arm_a=a.arm_a, refill=a.refill)
    if a.bundle:
        print(bundle(a.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
