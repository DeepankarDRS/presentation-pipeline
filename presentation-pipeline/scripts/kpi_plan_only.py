"""KPI pilot §14: planning-only runs of the main graph — how the slide component planner groups a slide's numbers.

    python -m scripts.kpi_plan_only --repeat 3 --label kpi-plans --bundle

Runs the real graph (outline planner -> slide component planner -> plan reviewer) for each case and stops
before the style resolver, so no slide is generated (paid: the planners only). Per KPI slide it records the
kpi_row components (id, weight, items, design hint), whether the numbers were split into several groups,
numbers placed in two groups, and numbers of the slide's key_messages that no component carries.

Writes output/kpi-plans/<label>/: runs.json (every run's slide plans), summary.md. --bundle zips the folder
for email. --rescore only rebuilds summary.md from runs.json (free).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

from scripts.eval_run import _slide_target  # noqa: E402
from src.utils.case_loader import load_case  # noqa: E402

load_dotenv(_ROOT / ".env")
CASES = ["deck-qbr-data", "gate-deck-cheffin-full", "gate-deck-all-nodes-dense"]
OUT = _ROOT / "output" / "kpi-plans"
_NUM = re.compile(r"[₹$€£]?\d[\d,.]*\s?(?:%|x|×|[KMB]|Cr|L|pts?)?", re.I)


def _num(s: str) -> str:
    return re.sub(r"[\s,]", "", s).lower().rstrip(".")


def plan_case(case: dict[str, Any], run_id: str) -> dict[str, Any]:
    """The graph up to the plan reviewer; returns the outline, the slide plans and the cost."""
    from src.agents.evaluator import _compute_cost
    from src.graph import compile_graph
    from src.state import initial_state
    from src.utils.logging_config import set_context

    set_context(run_id=run_id)
    supplied = case.get("supplied_content")
    state = initial_state(
        run_id=run_id, raw_request=case.get("request", case.get("objective", "")),
        theme_name=case.get("theme", ""), deck_min_threshold=_slide_target(case), critic_mode="off",
        supplied_content=supplied if isinstance(supplied, dict) else None,
        test_case={**case, "slide_count": _slide_target(case)},
    )
    cfg = {"run_name": f"kpi-plans-{run_id}", "tags": ["kpi-pilot", "plan-only"], "recursion_limit": 150}
    final: dict[str, Any] = {}
    for mode, chunk in compile_graph().stream(state, config=cfg, stream_mode=["updates", "values"]):
        if mode == "values":
            final = chunk
            continue
        if "style_resolver" in chunk:   # planning is done: stop before any slide is generated
            break
    history = final.get("generation_history") or []
    cost = sum(_compute_cost(r.get("tokens_in", 0), r.get("tokens_out", 0), r.get("model", "unknown")) for r in history)
    return {"outline": final.get("outline_plan") or {}, "slide_plans": final.get("slide_plans") or [],
            "cost_usd": round(cost, 4)}


def _key_messages(outline: dict[str, Any], index: int) -> list[str]:
    slides = outline.get("slides") or []
    s = next((x for x in slides if x.get("slide_index", x.get("index")) == index), None)
    if s is None and index < len(slides):
        s = slides[index]
    return [str(m) for m in (s or {}).get("key_messages") or []]


def kpi_slides(run: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for plan in run["slide_plans"]:
        comps = plan.get("components") or []
        kpis = [c for c in comps if c.get("kind") == "kpi_row"]
        if not kpis:
            continue
        groups, seen, dup = [], {}, []
        for c in kpis:
            cd = c.get("content_data") or {}
            vals = [str(v) for v in cd.get("kpi_values") or []]
            groups.append({"id": c.get("component_id"), "weight": c.get("weight"), "n": len(vals),
                           "labels": [str(x) for x in cd.get("kpi_labels") or []], "values": vals,
                           "hint": (c.get("design_hint") or "")[:160]})
            for v in vals:
                if _num(v) in seen and seen[_num(v)] != c.get("component_id"):
                    dup.append(v)
                seen.setdefault(_num(v), c.get("component_id"))
        carried = _num(json.dumps([c.get("content_data") for c in comps], ensure_ascii=False))
        msgs = _key_messages(run["outline"], plan.get("slide_index", 0))
        missing = sorted({m.group(0).strip() for t in msgs for m in _NUM.finditer(t)
                          if len(_num(m.group(0))) > 1 and _num(m.group(0)) not in carried})
        rows.append({"slide": plan.get("slide_index"), "title": plan.get("slide_title", ""), "groups": groups,
                     "split": len(kpis) > 1, "numbers": sum(g["n"] for g in groups), "in_two_groups": dup,
                     "not_carried": missing, "other_kinds": [c.get("kind") for c in comps if c.get("kind") != "kpi_row"]})
    return rows


def summary(runs: list[dict[str, Any]]) -> str:
    slides = [(r, s) for r in runs for s in r["kpi"]]
    split = sum(s["split"] for _, s in slides)
    lines = [f"# KPI planning-only runs ({len(runs)} runs, ${sum(r['cost_usd'] for r in runs):.3f})", "",
             f"KPI slides: {len(slides)}; split into several kpi_rows: {split}; numbers in two groups: "
             f"{sum(len(s['in_two_groups']) for _, s in slides)}; key-message numbers no component carries: "
             f"{sum(len(s['not_carried']) for _, s in slides)}.", "",
             "| case | run | slide | numbers | groups (id, weight, items) | other components | in two groups | not carried |",
             "|---|---|---|---|---|---|---|---|"]
    for r, s in slides:
        g = "; ".join(f"{x['id']} ({x['weight']}, {x['n']})" for x in s["groups"])
        lines.append(f"| {r['case']} | {r['repeat']} | {s['slide']} | {s['numbers']} | {g} | {', '.join(s['other_kinds'])} | "
                     f"{', '.join(s['in_two_groups']) or '-'} | {', '.join(s['not_carried']) or '-'} |")
    lines += ["", "## Groups in detail", ""]
    for r, s in slides:
        lines.append(f"**{r['case']} r{r['repeat']} slide {s['slide']}** — {s['title']}")
        for x in s["groups"]:
            lines.append(f"- `{x['id']}` {x['weight']}: " + ", ".join(f"{a} {b}" for a, b in zip(x["labels"], x["values"]))
                         + (f" — _{x['hint']}_" if x["hint"] else ""))
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases", nargs="*", default=CASES)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--label", default="kpi-plans")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--rescore", action="store_true", help="free: rebuild summary.md from runs.json")
    a = ap.parse_args()
    out = OUT / a.label
    out.mkdir(parents=True, exist_ok=True)
    if a.rescore:
        runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
        for r in runs:
            r["kpi"] = kpi_slides(r)
    else:
        runs = []
        for name in a.cases:
            case = load_case(name)
            for rep in range(1, a.repeat + 1):
                rid = f"kpiplan-{name}-r{rep}-{int(time.time())}"
                print(f"plan {name} r{rep} ...", flush=True)
                try:
                    res = plan_case(case, rid)
                except Exception as e:   # one failure must not cost the other runs
                    print(f"  failed: {e}", flush=True)
                    res = {"outline": {}, "slide_plans": [], "cost_usd": 0.0, "error": str(e)[:300]}
                run = {"case": name, "repeat": rep, "run_id": rid, **res}
                run["kpi"] = kpi_slides(run)
                runs.append(run)
                print(f"  ${res['cost_usd']:.3f}; KPI slides " + "; ".join(
                    f"s{s['slide']}: " + " + ".join(str(g["n"]) for g in s["groups"]) for s in run["kpi"]), flush=True)
                (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "summary.md").write_text(summary(runs), encoding="utf-8")
    print(out / "summary.md")
    if a.bundle:
        print(shutil.make_archive(str(out.parent / f"{a.label}-{time.strftime('%Y%m%d-%H%M%S')}"), "zip", out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
