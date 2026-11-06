"""Would the lab's code score have predicted the user's past blind marks? Free; reads saved compile folders.

    python -m scripts.smart_layout_scorecheck <eval dir> <folder with A/ B/> [...]   (pairs of arguments)

For every decided pair ("same" left out) whose two compile folders exist: did the arm with the higher code score win?
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.smart_layout_lab import measured  # noqa: E402


def check(ev: Path, base: Path) -> dict:
    key = {str(k["pair"]): k for k in json.loads((ev / "key.json").read_text(encoding="utf-8"))}
    rows = list(csv.DictReader((ev / "marks.csv").open(encoding="utf-8")))
    hit = miss = tie = absent = same = gap_when_same = 0
    gaps_same = []
    for r in rows:
        k = key.get(str(r["pair"]))
        if not k or not r.get("choice"):
            continue
        s = k.get("slide", 1)
        a = base / "A" / k["case"] / f"slide-{s}"
        b = base / "B" / k["case"] / f"slide-{s}"
        if not (a / "compile-result.json").exists() or not (b / "compile-result.json").exists():
            absent += 1
            continue
        sa, sb = measured(a)["score"], measured(b)["score"]
        if r["choice"].strip() == "same":
            same += 1
            gaps_same.append(abs(sa - sb))
            continue
        nodes_won = str(r["choice"]).strip() == str(k.get("nodes_side"))
        if sa == sb:
            tie += 1
        elif (sb > sa) == nodes_won:
            hit += 1
        else:
            miss += 1
    return {"set": ev.as_posix().split("docs/eval/")[-1], "decided_scored": hit + miss, "agree": hit, "disagree": miss, "score_tie": tie,
            "marked_same": same, "median_gap_when_same": sorted(gaps_same)[len(gaps_same) // 2] if gaps_same else None, "no_folder": absent}


if __name__ == "__main__":
    args = sys.argv[1:]
    out = [check(Path(args[i]), Path(args[i + 1])) for i in range(0, len(args), 2)]
    print(json.dumps(out, indent=1))
