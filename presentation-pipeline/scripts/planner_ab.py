"""Planner A/B on the same saved outlines (2026-11-12): the slide_component_planner at an old commit (arm "old")
against this branch (arm "new"). Each slide is planned once per arm from the SAME outline, so only the planner
differs, and both arms are scored by this branch's code.

    python -m scripts.planner_ab plan --arm new --label ab1                  # paid, ~$1.2 (31 slides)
    python -m scripts.planner_ab plan --arm old --ref 747ce68 --label ab1    # paid, ~$1.5; makes a checkout of the ref
    python -m scripts.planner_ab score --label ab1 --bundle                  # free: summary.md, zip to send back
    python -m scripts.planner_ab plan --arm new --label smoke --cases deck-qbr-data --slides 1   # ~$0.05 path check

Inputs: docs/eval/planner-ab/inputs.json (5 decks, 31 slides: QBR, product launch, quick-commerce strategy, ad audit,
every node kind; outlines of 2026-10-15, committed so the test PC needs no output/). deck_settings are not given
(the same for both arms). --max-cost stops an arm when its spend passes the limit (default $3).

What is tracked, per slide and per arm (summary.md):
  Accuracy   ITEM_MISSING, ITEM_REPEATED, SHAPE_MISFIT (plan_ledger) and the step-0 problems (plan_checks) on the
             final plan; fallback plans; failed calls and output-limit hits.
  Policy     placed_items (inferred placements, flagged) and written_lines (card lines not in the brief).
  Choices    component kinds per slide and per deck (variety), kpi tones and card tones / icons filled.
  Cost       calls, tokens in / cached / out / reasoning, $ per slide, seconds per slide.
  Re-ask     (new arm) how many, edit or replan, codes fixed, codes it brought, which plan was kept.
Not tracked here: how the slides look. Generate from both arms' plans for a blind look only if the plans are close.

Writes output/planner-ab/<label>/: <arm>.json (every slide's plan + history), <arm>.log, summary.md, results.json.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "docs" / "eval" / "planner-ab" / "inputs.json"
OUT = ROOT / "output" / "planner-ab"


def _code_root() -> Path:
    """The planner code to import: this checkout, or `--code <root>` (the old arm's checkout). Read before any
    `src` import, so the old arm runs the old planner, prompts and knowledge files."""
    if "--code" in sys.argv:
        return Path(sys.argv[sys.argv.index("--code") + 1]).resolve()
    return ROOT


CODE = _code_root()
sys.path.insert(0, str(CODE))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")   # the key lives in this checkout only


# ── plan (paid) ─────────────────────────────────────────────────────────────

def _old_checkout(ref: str) -> Path:
    """A detached worktree of `ref` under output/ (ignored by git), made once."""
    top = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    where = OUT / f"_code-{ref}"
    if not where.exists():
        subprocess.check_call(["git", "worktree", "add", "--detach", str(where), ref], cwd=top)
    return where / ROOT.relative_to(top)


def plan_arm(a: argparse.Namespace) -> int:
    if a.arm == "old" and "--code" not in sys.argv:   # run again inside the old code
        code = _old_checkout(a.ref)
        return subprocess.call([sys.executable, "-m", "scripts.planner_ab", *sys.argv[1:], "--code", str(code)],
                               cwd=ROOT)
    from src.agents.evaluator import _compute_cost
    from src.agents.slide_component_planner import plan_with_reask
    from src.utils.logging_config import add_file_log, setup_logging

    out = OUT / a.label
    out.mkdir(parents=True, exist_ok=True)
    setup_logging()
    add_file_log(out / f"{a.arm}.log")
    decks = [d for d in json.loads(INPUTS.read_text(encoding="utf-8"))["decks"] if not a.cases or d["case"] in a.cases]
    jobs = [(d, s) for d in decks for s in d["outline"]["slides"][:a.slides or None]]
    path = out / f"{a.arm}.json"
    results: list[dict[str, Any]] = []
    spent = [0.0]
    lock = threading.Lock()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=CODE, text=True,
                            capture_output=True).stdout.strip()
    print(f"arm {a.arm}: {len(jobs)} slides, planner code at {CODE} ({commit})", flush=True)

    def one(job: tuple[dict[str, Any], dict[str, Any]]) -> None:
        deck, slide = job
        if spent[0] > a.max_cost:
            return
        t0 = time.time()
        try:
            plan, history = plan_with_reask(slide, outline_plan=deck["outline"],
                                            supplied_content=deck.get("supplied_content"))
            err = ""
        except Exception as e:   # plan_with_reask never raises; keep a crash from costing the other slides
            plan, history, err = {}, [], str(e)[:300]
        cost = sum(_compute_cost(r.get("tokens_in", 0), r.get("tokens_out", 0), r.get("model", ""),
                                 r.get("tokens_cached", 0)) for r in history)
        row = {"case": deck["case"], "slide_index": slide.get("slide_index"), "arm": a.arm, "commit": commit,
               "seconds": round(time.time() - t0, 1), "cost_usd": round(cost, 5), "plan": plan,
               "history": history, "error": err}
        with lock:
            spent[0] += cost
            results.append(row)
            results.sort(key=lambda r: (r["case"], r["slide_index"] or 0))
            path.write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
            print(f"  {deck['case']} s{slide.get('slide_index')} ${cost:.3f} {row['seconds']}s "
                  f"calls={len(history)} total=${spent[0]:.3f}", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
        list(pool.map(one, jobs))
    if spent[0] > a.max_cost:
        print(f"stopped at ${spent[0]:.2f} (--max-cost {a.max_cost}); {len(results)} of {len(jobs)} slides planned")
    print(f"arm {a.arm}: ${spent[0]:.3f}, {len(results)} slides -> {path}")
    return 0


# ── score (free, this branch's code) ────────────────────────────────────────

def _slide_of(case: str, index: int) -> dict[str, Any]:
    deck = next(d for d in json.loads(INPUTS.read_text(encoding="utf-8"))["decks"] if d["case"] == case)
    return next(s for s in deck["outline"]["slides"] if s.get("slide_index") == index), deck


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    from src.agents.evaluator import _compute_cost
    from src.agents.plan_checks import find_problems
    from src.agents.plan_ledger import plan_problems
    from src.agents.slide_component_planner import brief_text_for
    from src.agents.written_lines import instruction_lines

    slide, deck = _slide_of(row["case"], row["slide_index"])
    plan, history = row.get("plan") or {}, row.get("history") or []
    instr = instruction_lines(deck["outline"])
    codes = [p["code"] for p in (find_problems(plan, brief_text_for(slide, deck.get("supplied_content")), instr)
                                 + plan_problems(plan, slide, instr))] if plan else ["NO_PLAN"]
    comps = plan.get("components") or []
    cards = [c for comp in comps if comp.get("kind") == "card_grid"
             for c in (comp.get("content_data") or {}).get("cards") or [] if isinstance(c, dict)]
    kpis = [comp.get("content_data") or {} for comp in comps if comp.get("kind") == "kpi_row"]
    outcome = next((r.get("reask_outcome") for r in history if r.get("reask_outcome")), None)
    return {
        "case": row["case"], "slide": row["slide_index"], "arm": row["arm"],
        "kinds": [c.get("kind") for c in comps], "codes": codes,
        "fallback": plan.get("plan_source") == "fallback", "error": bool(row.get("error")),
        "failed_calls": sum(1 for r in history if r.get("failed")),
        "placed_items": len(plan.get("placed_items") or []), "written_lines": len(plan.get("written_lines") or []),
        "kpi_tones": sum(1 for k in kpis if any(k.get("kpi_tones") or [])), "kpi_rows": len(kpis),
        "card_tones": sum(1 for c in cards if c.get("tone")), "card_icons": sum(1 for c in cards if c.get("icon")),
        "cards": len(cards), "calls": len(history), "reask": outcome,
        "tokens_in": sum(r.get("tokens_in", 0) for r in history),
        "tokens_cached": sum(r.get("tokens_cached", 0) for r in history),
        "tokens_out": sum(r.get("tokens_out", 0) for r in history),
        "tokens_reasoning": sum(r.get("tokens_reasoning", 0) for r in history),
        "cost_usd": round(sum(_compute_cost(r.get("tokens_in", 0), r.get("tokens_out", 0), r.get("model", ""),
                                            r.get("tokens_cached", 0)) for r in history), 5),
        "seconds": row.get("seconds", 0),
    }


def _totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows) or 1
    count = lambda code: sum(r["codes"].count(code) for r in rows)   # noqa: E731
    reasks = [r["reask"] for r in rows if r["reask"]]
    return {
        "slides": len(rows), "slides with a problem": sum(1 for r in rows if r["codes"]),
        "ITEM_MISSING": count("ITEM_MISSING"), "ITEM_REPEATED": count("ITEM_REPEATED"),
        "SHAPE_MISFIT": count("SHAPE_MISFIT"),
        "other problems": sum(1 for r in rows for c in r["codes"] if not c.startswith(("ITEM_", "SHAPE_"))),
        "fallback plans": sum(r["fallback"] for r in rows), "failed calls": sum(r["failed_calls"] for r in rows),
        "placed items (flagged)": sum(r["placed_items"] for r in rows),
        "written lines": sum(r["written_lines"] for r in rows),
        "distinct kinds": len({k for r in rows for k in r["kinds"]}),
        "components per slide": round(sum(len(r["kinds"]) for r in rows) / n, 2),
        "kpi rows with tones": f"{sum(r['kpi_tones'] for r in rows)}/{sum(r['kpi_rows'] for r in rows)}",
        "cards with tone / icon": f"{sum(r['card_tones'] for r in rows)} / {sum(r['card_icons'] for r in rows)} "
                                  f"of {sum(r['cards'] for r in rows)}",
        "calls": sum(r["calls"] for r in rows), "re-asks": len(reasks),
        "re-asks edit / replan": f"{sum(1 for x in reasks if x['mode'] == 'edit')} / "
                                 f"{sum(1 for x in reasks if x['mode'] == 'replan')}",
        "re-asks kept": sum(1 for x in reasks if x["kept"] == "reask"),
        "re-asks that brought a new problem": sum(1 for x in reasks if x["new"]),
        "tokens in / slide": round(sum(r["tokens_in"] for r in rows) / n),
        "cached share": f"{sum(r['tokens_cached'] for r in rows) / max(1, sum(r['tokens_in'] for r in rows)):.0%}",
        "tokens out / slide": round(sum(r["tokens_out"] for r in rows) / n),
        "reasoning / slide": round(sum(r["tokens_reasoning"] for r in rows) / n),
        "$ total": round(sum(r["cost_usd"] for r in rows), 3),
        "$ / slide": round(sum(r["cost_usd"] for r in rows) / n, 4),
        "seconds / slide": round(sum(r["seconds"] for r in rows) / n, 1),
    }


def score(a: argparse.Namespace) -> int:
    out = OUT / a.label
    arms = {arm: [score_row(r) for r in json.loads((out / f"{arm}.json").read_text(encoding="utf-8"))]
            for arm in ("old", "new") if (out / f"{arm}.json").exists()}
    totals = {arm: _totals(rows) for arm, rows in arms.items()}
    names = list(arms)
    lines = [f"# Planner A/B · {a.label}", "", "Same outlines for both arms (docs/eval/planner-ab/inputs.json); "
             "scored by this branch's checks. Fewer problems and fewer tokens are better.", "",
             "| measure | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for key in next(iter(totals.values()), {}):
        lines.append(f"| {key} | " + " | ".join(str(totals[n][key]) for n in names) + " |")
    lines += ["", "## Per slide", "", "| deck | slide | " + " | ".join(f"{n} kinds | {n} problems | {n} $"
                                                                        for n in names) + " | new re-ask |",
              "|---|---|" + "---|---|---|" * len(names) + "---|"]
    keyed = {n: {(r["case"], r["slide"]): r for r in rows} for n, rows in arms.items()}
    for key in sorted({k for rows in keyed.values() for k in rows}, key=lambda k: (k[0], k[1] or 0)):
        cells = []
        for n in names:
            r = keyed[n].get(key)
            cells += [", ".join(r["kinds"]) if r else "-", ", ".join(r["codes"]) or "ok" if r else "-",
                      f"{r['cost_usd']:.3f}" if r else "-"]
        ra = (keyed.get("new", {}).get(key) or {}).get("reask")
        ra_text = f"{ra['mode']}: fixed {','.join(ra['fixed']) or '-'}, new {','.join(ra['new']) or '-'}, kept {ra['kept']}" \
            if ra else "-"
        lines.append(f"| {key[0]} | {key[1]} | " + " | ".join(cells) + f" | {ra_text} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps({"totals": totals, "slides": arms}, indent=1, ensure_ascii=False),
                                      encoding="utf-8")
    print(out / "summary.md")
    if a.bundle:
        print(shutil.make_archive(str(out.parent / f"{a.label}-{time.strftime('%Y%m%d-%H%M%S')}"), "zip", out,
                                  ))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="paid: plan every input slide with one arm")
    p.add_argument("--arm", choices=["old", "new"], required=True)
    p.add_argument("--ref", default="747ce68", help="the old arm's commit (default: before the prompt rework)")
    p.add_argument("--code", help=argparse.SUPPRESS)   # set by the old arm's re-run
    p.add_argument("--label", required=True)
    p.add_argument("--cases", nargs="*", default=[])
    p.add_argument("--slides", type=int, default=0, help="first N slides per deck (0 = all)")
    p.add_argument("--workers", type=int, default=4, help="slides planned at once; mind the API rate limit")
    p.add_argument("--max-cost", type=float, default=3.0)
    s = sub.add_parser("score", help="free: compare the arms of a label")
    s.add_argument("--label", required=True)
    s.add_argument("--bundle", action="store_true", help="zip output/planner-ab/<label> to send back")
    a = ap.parse_args()
    return plan_arm(a) if a.cmd == "plan" else score(a)


if __name__ == "__main__":
    raise SystemExit(main())
