"""KPI node pilot, paid check (docs/kpi-node-pilot-2026-10-11.md §4): generator only, on saved plans.

    python -m scripts.kpi_paid --repeat 1 --label kpi-paid --bundle      # needs OPENAI_API_KEY (test PC)
    python -m scripts.kpi_paid --label kpi-paid --rescore                  # free: scores + sheet again
    python -m scripts.kpi_paid --label dry --dry                           # free: a fake generator answers with
                                                                           # today's XML mapped to refs (path check)

Inputs: docs/eval/kpi-node/paid-inputs.json (the 3 KPI slides of q1008's deck-qbr-data and
gate-deck-cheffin-full: plan, today's XML, theme, brief; committed so the test PC needs no output/).
Arm B: POM_BLOCKS=kpi, the real graph from the plan (style resolver -> context builder -> generator ->
validator with the ref fill -> repairer / visual repairer as in a normal run; critic off, as q1008's
deck-qbr-data). Arm A: today's XML from q1008 recompiled on this commit (free, already paid for).
Per run the first try is recorded (refs placed, NODE_* errors) and the final slide is scored like the
replay (scripts/kpi_replay.score). Writes output/kpi-paid/<label>/: results.json, summary.md, sheets/
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
os.environ["POM_BLOCKS"] = "kpi"   # before any pipeline import reads it (it is read per call, this is belt and braces)

from scripts.kpi_replay import compile_slide, score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes.element_refs import kpi_components  # noqa: E402

INPUTS = ROOT / "docs" / "eval" / "kpi-node" / "paid-inputs.json"
OUT = ROOT / "output" / "kpi-paid"
REF_CODES = ("NODE_REF_UNKNOWN", "NODE_REF_DUPLICATE", "NODE_ITEM_MISSING", "NODE_FIELD_MISSING",
             "NODE_BYPASSED", "NODE_ATTR_IGNORED", "NODE_FOCUS_UNNAMED", "NODE_VALUE_TEXT")


def run_one(item: dict, run_id: str) -> dict[str, Any]:
    """The graph from one saved slide plan; returns the final state's slide + the first validator pass."""
    from src.graph import compile_graph
    from src.state import initial_state
    from src.utils.logging_config import set_context

    set_context(run_id=run_id)
    state = initial_state(run_id=run_id, raw_request=item["request"], theme_name=item["theme"],
                          deck_min_threshold=1, critic_mode="off")
    state["slide_plans"] = [dict(item["plan"], slide_index=0)]
    attempts, final = [], {}
    cfg = {"run_name": f"kpi-paid-{run_id}", "tags": ["kpi-pilot"], "recursion_limit": 80}
    for mode, chunk in compile_graph().stream(state, config=cfg, stream_mode=["updates", "values"]):
        if mode == "values":
            final = chunk
            continue
        for node, update in chunk.items():
            if node == "validator" and isinstance(update, dict):
                attempts.append(update)
    first = attempts[0] if attempts else {}
    issues = [i for i in (first.get("normalize_result") or {}).get("issues") or [] if i.get("code") in REF_CODES]
    gen = [g for g in final.get("generation_history") or [] if getattr(g, "step", None) == "generator"
           or (isinstance(g, dict) and g.get("step") == "generator")]
    last = attempts[-1] if attempts else {}
    return {
        "first_ok": bool((first.get("compile_result") or {}).get("ok")),
        "first_issues": [{k: i.get(k) for k in ("code", "severity", "message")} for i in issues],
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


def run(label: str, repeat: int, dry: bool = False) -> None:
    out = OUT / label
    items = json.loads(INPUTS.read_text(encoding="utf-8"))
    results = []
    for r in range(1, repeat + 1):
        for it in items:
            name = f"{it['case']}-s{it['slide']}"
            rid = f"kpi-{name}-r{r}-{int(time.time())}"
            print(f"run {name} r{r} ...", flush=True)
            try:
                if dry:
                    from scripts.kpi_replay import map_refs
                    from src.agents import generator
                    skel = map_refs(it["xml_today"], it["plan"])[0]
                    generator.get_llm = lambda step, _x=skel: _FakeLLM(_x)
                res = run_one(it, rid)
            except Exception as e:   # one failure must not cost the other runs
                res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                       "final_xml": "", "cost_usd": 0.0, "validator_passes": 0, "generator_calls": 0}
            placed, planned = refs_first_try(it, res["first_issues"])
            row = {"case": f"{name}-r{r}", "item": it["case"], "slide": it["slide"], "repeat": r, "run_id": rid,
                   **{k: v for k, v in res.items() if k != "final_xml"}, "refs_first_try": [placed, planned]}
            (out / "B" / row["case"] / "slide-0").mkdir(parents=True, exist_ok=True)
            (out / "B" / row["case"] / "final.xml").write_text(res["final_xml"], encoding="utf-8")
            results.append(row)
            print(f"  first try ok={res['first_ok']} refs {placed}/{planned} passes={res['validator_passes']} "
                  f"final ok={res['final_ok']} ${res['cost_usd']:.3f}", flush=True)
    (out / "runs.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")


def rescore(label: str, render: bool = True) -> list[dict]:
    out = OUT / label
    items = {f"{i['case']}-s{i['slide']}": i for i in json.loads(INPUTS.read_text(encoding="utf-8"))}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        it = items[f"{row['item']}-s{row['slide']}"]
        theme = resolve_theme(it["theme"])["element"]
        a_dir, b_dir = out / "A" / row["case"] / "slide-0", out / "B" / row["case"] / "slide-0"
        if True:   # free: always recompile both arms on this commit
            row["A"] = score("A", a_dir, compile_slide(it["xml_today"], theme, a_dir), it["plan"], row["case"], render)
        xml = (out / "B" / row["case"] / "final.xml").read_text(encoding="utf-8")
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
    write_summary(out, runs)
    return runs


def write_summary(out: Path, runs: list[dict]) -> None:
    placed = sum(r["refs_first_try"][0] for r in runs)
    planned = sum(r["refs_first_try"][1] for r in runs)
    first_err = sum(1 for r in runs if any(i["severity"] == "error" for i in r["first_issues"]))
    lines = ["# KPI node pilot: paid check (generator only, POM_BLOCKS=kpi)", "",
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
    a = ap.parse_args()
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
        run(a.label, a.repeat)
    rescore(a.label, render=not a.no_render)
    if a.bundle:
        print(bundle(a.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
