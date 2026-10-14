"""Card tile nodes, paid check part 1 (docs/tile-nodes-spec-2026-10-12.md §11): planning-only runs of the main graph.

    python -m scripts.card_plan_only --repeat 3 --label card-plans --bundle      # test PC (OPENAI_API_KEY), ~$1.30
    python -m scripts.card_plan_only --label card-plans --rescore                # free: summary.md again

Runs the real graph up to the style resolver (scripts.kpi_plan_only.plan_case) for the six decks of the card paid
check, so no slide is generated. Per card_grid it records what the planner gave the cards: layout, tones, focus_card,
key phrases, icons, cards without a line, and the plan flags (CARD_LINES_DROPPED re-asks). scripts.card_paid then
draws the slides of docs/eval/card-nodes/paid-inputs.json on these plans (--plans <label>).

Writes output/card-plans/<label>/: runs.json (every run's slide plans), summary.md; --bundle zips the folder.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

from scripts.kpi_plan_only import plan_case  # noqa: E402
from src.utils.case_loader import load_case  # noqa: E402

load_dotenv(_ROOT / ".env")
CASES = ["deck-qbr-data", "deck-product-launch-data", "gate-deck-agency-takeover", "gate-deck-all-nodes-dense",
         "gate-deck-cheffin-full", "gate-deck-xtsy-qcomm"]
OUT = _ROOT / "output" / "card-plans"


def card_slides(run: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for plan in run["slide_plans"]:
        grids = [c for c in plan.get("components") or [] if c.get("kind") == "card_grid"]
        if not grids:
            continue
        flags = [f.get("code") for f in plan.get("plan_flags") or [] if isinstance(f, dict)]
        for c in grids:
            cd = c.get("content_data") or {}
            cards = [x for x in cd.get("cards") or [] if isinstance(x, dict)]
            rows.append({
                "slide": plan.get("slide_index"), "title": plan.get("slide_title", ""), "id": c.get("component_id"),
                "layout": cd.get("card_layout"), "n": len(cards), "focus_card": cd.get("focus_card"),
                "tones": [x.get("tone", "") for x in cards], "phrases": sum(1 for x in cards if x.get("key_phrase")),
                "icons": [x.get("icon", "") for x in cards],
                "title_only": sum(1 for x in cards if not x.get("body") and not x.get("bullets")),
                "titles": [str(x.get("title", "")) for x in cards], "hint": (c.get("design_hint") or "")[:140],
                "flags": flags,
            })
    return rows


def summary(runs: list[dict[str, Any]]) -> str:
    rows = [(r, s) for r in runs for s in r["cards"]]
    n_cards = sum(s["n"] for _, s in rows)
    lines = [f"# Card planning-only runs ({len(runs)} runs, ${sum(r['cost_usd'] for r in runs):.3f})", "",
             f"card_grids: {len(rows)} ({n_cards} cards); with tones: {sum(1 for _, s in rows if any(s['tones']))}; "
             f"focus_card set: {sum(1 for _, s in rows if s['focus_card'] is not None)}; key phrases: "
             f"{sum(s['phrases'] for _, s in rows)}; groups with icons: {sum(1 for _, s in rows if all(s['icons']))}; "
             f"title-only cards: {sum(s['title_only'] for _, s in rows)}; runs that failed: "
             f"{sum(1 for r in runs if r.get('error'))}.", "",
             "| case | run | slide | id | layout | cards | tones | focus | phrases | icons | title-only | flags |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r, s in rows:
        tones = " ".join(t[0] if t else "-" for t in s["tones"])
        lines.append(f"| {r['case']} | {r['repeat']} | {s['slide']} | {s['id']} | {s['layout']} | {s['n']} | {tones} | "
                     f"{s['focus_card'] if s['focus_card'] is not None else '-'} | {s['phrases']} | "
                     f"{'all' if all(s['icons']) else 'none' if not any(s['icons']) else 'some'} | {s['title_only']} | "
                     f"{', '.join(sorted(set(s['flags']))) or '-'} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases", nargs="*", default=CASES)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--label", default="card-plans")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--rescore", action="store_true", help="free: rebuild summary.md from runs.json")
    a = ap.parse_args()
    out = OUT / a.label
    out.mkdir(parents=True, exist_ok=True)
    if a.rescore:
        runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
        for r in runs:
            r["cards"] = card_slides(r)
    else:
        runs = []
        for name in a.cases:
            case = load_case(name)
            for rep in range(1, a.repeat + 1):
                rid = f"cardplan-{name}-r{rep}-{int(time.time())}"
                print(f"plan {name} r{rep} ...", flush=True)
                try:
                    res = plan_case(case, rid)
                except Exception as e:   # one failure must not cost the other runs
                    print(f"  failed: {e}", flush=True)
                    res = {"outline": {}, "slide_plans": [], "cost_usd": 0.0, "error": str(e)[:300]}
                run = {"case": name, "repeat": rep, "run_id": rid, **res}
                run["cards"] = card_slides(run)
                runs.append(run)
                print(f"  ${res['cost_usd']:.3f}; card slides " + ", ".join(
                    f"s{s['slide']} {s['layout']} x{s['n']}" for s in run["cards"]), flush=True)
                (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "summary.md").write_text(summary(runs), encoding="utf-8")
    print(out / "summary.md")
    if a.bundle:
        print(shutil.make_archive(str(out.parent / f"{a.label}-{time.strftime('%Y%m%d-%H%M%S')}"), "zip", out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
