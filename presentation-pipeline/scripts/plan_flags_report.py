"""Plan-check flags per case, from saved slides.json files (§14.6 step 0 acceptance).

    python -m scripts.plan_flags_report docs/eval/step0            # a folder with decks/<case>__rN/slides.json
    python -m scripts.plan_flags_report output/runs/<run_id> --recheck

Counts the `plan_flags` the planner wrote (PLAN_EMPTY, PLAN_INSTRUCTION_TEXT, PLAN_DUPLICATE_ITEMS,
SLIDE_SPARSE), the plans that came from the fallback, and the re-asks (from `capacity_fixes`).
With --recheck every saved plan is also run through `find_problems` again: after step 0 no plan
should come back with an empty block component or instruction text (a fallback plan with no
content lines is the one allowed exception, flagged PLAN_EMPTY).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.agents.plan_checks import find_problems  # noqa: E402


def case_of(path: Path) -> str:
    return path.parent.name


def report(paths: list[Path], recheck: bool = False) -> str:
    files: list[Path] = []
    for p in paths:
        files += [p] if p.is_file() else sorted(p.rglob("slides.json"))
    lines = ["| case | slides | re-asked | fallback | PLAN_EMPTY | INSTRUCTION | DUPLICATE | SPARSE |"
             + (" still has problems |" if recheck else ""),
             "|---|---|---|---|---|---|---|---|" + ("---|" if recheck else "")]
    for f in files:
        slides = json.loads(f.read_text(encoding="utf-8"))
        plans = [(s or {}).get("slide_plan") or {} for s in slides]
        flags = Counter(fl["code"] for p in plans for fl in p.get("plan_flags", []))
        reasked = sum("planner re-asked" in p.get("capacity_fixes", []) for p in plans)
        fallback = sum(p.get("plan_source") == "fallback" for p in plans)
        row = (f"| {case_of(f)} | {len(plans)} | {reasked} | {fallback} | {flags['PLAN_EMPTY']} | "
               f"{flags['PLAN_INSTRUCTION_TEXT']} | {flags['PLAN_DUPLICATE_ITEMS']} | {flags['SLIDE_SPARSE']} |")
        if recheck:
            left = sum(bool(find_problems(p, "")) for p in plans)
            row += f" {left} |"
        lines.append(row)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--recheck", action="store_true")
    a = ap.parse_args(argv)
    print(report(a.paths, a.recheck))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
