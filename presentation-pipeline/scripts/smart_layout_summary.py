"""Tables for docs/eval/smart-layout/README.md from output/smart-layout/results.json. Free."""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")


def arm_row(rows, name):
    got = [r["arms"][name] for r in rows if name in r["arms"]]
    comp = [a for a in got if a.get("compiled")]
    rend = [a.get("rendered") or {} for a in comp]
    return {"arm": name, "offered": len(got), "compiled": len(comp), "hard_faults": sum(a.get("hard", 0) for a in comp),
            "slides_with_hard_fault": sum(a.get("hard", 0) > 0 for a in comp), "too_wide_words": sum(a.get("words", 0) for a in comp),
            "rendered_broken": sum(x.get("broken") or 0 for x in rend), "rendered_overlaps": sum(x.get("overlaps") or 0 for x in rend),
            "empty_flags": sum(a.get("codes", {}).get(c, 0) for a in comp for c in ("GEOM_CARD_EMPTY", "GEOM_BOX_EMPTY", "GEOM_SLIDE_SPARSE")),
            "median_fill": round(statistics.median([a["ink"] for a in comp if a.get("ink") is not None]), 3) if comp else None,
            "median_score": round(statistics.median([a["score"] for a in comp]), 1) if comp else None,
            "median_font": statistics.median([a.get("font_median", 0) for a in comp]) if comp else None}


def side(shape: str) -> bool:
    return shape.startswith("H(") or "H(" in shape


def main() -> int:
    R = json.loads((ROOT / "output/smart-layout/results.json").read_text(encoding="utf-8"))
    rows = [r for r in R if "arms" in r]
    out = {"slides": len(R), "tested": len(rows), "one_component": sum(r.get("skipped") == "one component" for r in R),
           "arms": [arm_row(rows, a) for a in ("today", "static", "solver", "best_k", "library")]}
    t = {r["name"]: r["arms"]["today"] for r in rows}
    for arm in ("static", "solver", "best_k", "library"):
        b = better = worse = same = 0
        for r in rows:
            if arm not in r["arms"] or not r["arms"][arm].get("compiled"):
                continue
            d = r["arms"][arm]["score"] - t[r["name"]]["score"]
            b += 1
            better += d >= 6
            worse += d <= -6
            same += abs(d) < 6
        out[f"{arm}_vs_today"] = {"slides": b, "clearly_higher": better, "clearly_lower": worse, "within_margin": same}
    out["guarded_changed"] = sum(not r["arms"].get("guarded", {}).get("kept_today", True) for r in rows)
    out["static_could_not_place_all"] = [r["arms"]["static"]["skeleton"] for r in rows if "static" in r["arms"] and not r["arms"]["static"]["skeleton"].endswith("+0")]
    out["static_offered"] = sum("static" in r["arms"] for r in rows)
    out["library_coverage"] = {"slides_with_a_donor": sum(r.get("donors", 0) > 0 for r in rows), "of": len(rows)}
    out["seconds_per_slide_median"] = statistics.median([r["seconds"] for r in rows])
    kinds = {r["name"]: tuple(sorted(set(r["leaves"]))) for r in rows}
    pairs = defaultdict(Counter)
    for r in rows:
        for cand in r.get("candidates", []):
            if not cand.get("compiled"):
                continue
    for r in rows:
        if "best_k" not in r["arms"]:
            continue
        key = " + ".join(kinds[r["name"]])
        pairs[key]["side by side" if side(r["arms"]["best_k"].get("shape", "")) else "stacked"] += 1
    out["best_arrangement_by_kinds"] = {k: dict(v) for k, v in sorted(pairs.items())}
    st = ROOT / "output/smart-layout/stress.json"
    if st.exists():
        s = json.loads(st.read_text(encoding="utf-8"))
        out["stress"] = {k: v for k, v in s.items() if k != "rows"}
        pp = defaultdict(Counter)
        for r in s["rows"]:
            b = r["best"]
            if b.get("compiled") and b.get("hard", 1) == 0:
                pp[" + ".join(sorted(set(r["kinds"])))]["side by side" if side(b.get("shape", "")) else "stacked"] += 1
        out["stress"]["best_arrangement_by_kinds"] = {k: dict(v) for k, v in sorted(pp.items())}
    (ROOT / "docs/eval/smart-layout/results-summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
