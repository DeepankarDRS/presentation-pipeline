"""Timeline description check (2026-11-02): planning-only runs of the main graph with POM_NODES=timeline.

    python -m scripts.timeline_plan_only --repeat 2 --label timeline-plans --bundle      (paid: planners only)
    python -m scripts.timeline_plan_only --label timeline-plans --rescore               (free)

With the timeline node on, the slide component planner is asked for each milestone's date, label (its name, a few
words) and description (its detail) as POM's <TimelineItem date title description> has them, instead of the detail
packed into the label. Runs the graph up to the plan reviewer (scripts.kpi_plan_only.plan_case: no slide is
generated) and records per timeline: items, how many carry a description, labels still packed with a detail
(" — " / ": " / an unspaced dash), label and description word counts, what a bare <Timeline> would draw, and
timelines the capacity / label-room checks turned into something else. Baseline (the 23 saved timeline slides of
the replay, docs/eval/sequence-nodes/replay.md): 0 of 102 items had a description.

Writes output/timeline-plans/<label>/: runs.json, summary.md. --bundle zips the folder for email.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ["POM_NODES"] = "timeline"   # before the planner renders its prompt

from scripts.kpi_plan_only import load_case, plan_case  # noqa: E402
from src.agents.capacity import capacity  # noqa: E402
from src.compiler.nodes import compose, sequences  # noqa: E402

CASES = ["gj-h1-regen", "gate-deck-xtsy-qcomm", "deck-product-launch-data", "gate-deck-all-nodes-dense"]
OUT = _ROOT / "output" / "timeline-plans"


def _components(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return plan.get("components") or []


def timelines(run: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per timeline component of the run, plus timelines the plan checks turned into another kind."""
    rows = []
    for k, plan in enumerate(run.get("slide_plans") or []):
        for note in plan.get("capacity_fixes") or []:
            if "timeline" in note:
                rows.append({"slide": k + 1, "moved": note})
        for c in _components(plan):
            if c.get("kind") != "timeline":
                continue
            its = (c.get("content_data") or {}).get("timeline_items") or []
            labels = [str(i.get("label") or "") for i in its]
            descs = [str(i.get("description") or "").strip() for i in its]
            def noop(*_a):
                return None
            name, _ = compose.composition(sequences.node("timeline"), c, None, c.get("component_id") or "", noop)
            rows.append({"slide": k + 1, "id": c.get("component_id"), "items": len(its),
                         "described": sum(bool(d) for d in descs),
                         "packed": sum(bool(compose.split(lb)[1]) for lb, d in zip(labels, descs) if not d),
                         "label_words": [len(lb.split()) for lb in labels],
                         "desc_words": [len(d.split()) for d in descs if d],
                         "direction": (c.get("content_data") or {}).get("direction"), "draws": name,
                         "items_text": [(i.get("date"), i.get("label"), i.get("description")) for i in its]})
    return rows


def summary(runs: list[dict[str, Any]]) -> str:
    cap = capacity()["timeline"]
    rows = [dict(r, case=run["case"], repeat=run["repeat"]) for run in runs for r in run["timelines"]]
    tl = [r for r in rows if "id" in r]
    n = sum(r["items"] for r in tl)
    lw = [w for r in tl for w in r["label_words"]]
    dw = [w for r in tl for w in r["desc_words"]]
    lines = [f"# Timeline planning-only runs ({len(runs)} runs, ${sum(r['cost_usd'] for r in runs):.3f}), POM_NODES=timeline", "",
             f"Timelines: {len(tl)} in {len({(r['case'], r['repeat']) for r in tl})} runs; moved to another kind by the "
             f"plan checks: {sum('moved' in r for r in rows)}. Failed runs: {sum(bool(r.get('error')) for r in runs)}.", "",
             "| | items | share |", "|---|---|---|",
             f"| with a description | {sum(r['described'] for r in tl)} / {n} | {sum(r['described'] for r in tl) / max(n, 1):.0%} |",
             f"| label still packed with a detail (no description) | {sum(r['packed'] for r in tl)} / {n} | "
             f"{sum(r['packed'] for r in tl) / max(n, 1):.0%} |",
             f"| label ≤ {cap['max_label_words']} words | {sum(w <= cap['max_label_words'] for w in lw)} / {len(lw)} | "
             f"{sum(w <= cap['max_label_words'] for w in lw) / max(len(lw), 1):.0%} |",
             f"| description ≤ {cap['max_description_words']} words | {sum(w <= cap['max_description_words'] for w in dw)} / {len(dw)} | "
             f"{sum(w <= cap['max_description_words'] for w in dw) / max(len(dw), 1):.0%} |", "",
             f"Baseline (23 saved timeline slides): 0 / 102 items with a description. Bare tag draws: "
             f"{dict(Counter(r['draws'] for r in tl))}. Label words: {dict(sorted(Counter(lw).items()))}; description "
             f"words: median {sorted(dw)[len(dw) // 2] if dw else '-'}, max {max(dw) if dw else '-'}.", "",
             "## Per timeline", ""]
    for r in rows:
        if "moved" in r:
            lines.append(f"- {r['case']} r{r['repeat']} s{r['slide']}: **moved** — {r['moved']}")
            continue
        lines.append(f"- {r['case']} r{r['repeat']} s{r['slide']} `{r['id']}` ({r['direction']}, draws {r['draws']}): "
                     f"{r['described']}/{r['items']} described, {r['packed']} packed")
        lines += [f"  - {d} · **{lb}**" + (f" · {x}" if x else "") for d, lb, x in r["items_text"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases", nargs="*", default=CASES)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--label", default="timeline-plans")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--rescore", action="store_true", help="free: rebuild summary.md from runs.json")
    a = ap.parse_args()
    out = OUT / a.label
    out.mkdir(parents=True, exist_ok=True)
    if a.rescore:
        runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
        for r in runs:
            r["timelines"] = timelines(r)
    else:
        runs = []
        for name in a.cases:
            case = load_case(name)
            for rep in range(1, a.repeat + 1):
                rid = f"tlplan-{name}-r{rep}-{int(time.time())}"
                print(f"plan {name} r{rep} ...", flush=True)
                try:
                    res = plan_case(case, rid)
                except Exception as e:   # one failure must not cost the other runs
                    print(f"  failed: {e}", flush=True)
                    res = {"outline": {}, "slide_plans": [], "cost_usd": 0.0, "error": str(e)[:300]}
                run = {"case": name, "repeat": rep, "run_id": rid, **res}
                run["timelines"] = timelines(run)
                runs.append(run)
                print(f"  ${res['cost_usd']:.3f}; timelines " + "; ".join(
                    f"s{t['slide']}: {t['described']}/{t['items']} described" if "id" in t else f"s{t['slide']}: moved"
                    for t in run["timelines"]), flush=True)
                (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "summary.md").write_text(summary(runs), encoding="utf-8")
    print(out / "summary.md")
    if a.bundle:
        print(shutil.make_archive(str(out.parent / f"{a.label}-{time.strftime('%Y%m%d-%H%M%S')}"), "zip", out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
