"""Compare two evals: headline metrics and per-case first-pass / fill.

    python -m scripts.eval_compare docs/eval/baseline docs/eval/phase-1

Each argument is a folder holding results.json (docs/eval/<label>/ or output/eval/<label>-<ts>/).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

_HEADLINE = ("runs_passed", "slide_count_off", "compiled_pct", "first_pass_pct", "mean_retries", "mean_fill",
             "low_fill_pct", "word_breaks_per_slide", "text_overflows_per_slide", "table_spill_slides",
             "table_spill_px", "tables_overfull_slides", "empty_cells", "invented_numbers",
             "auto_fixes_per_slide", "layout_issues_per_slide", "fit_grow_changes_per_slide",
             "tokens_in", "tokens_out", "cost_usd")


def _per_case(results: dict) -> dict[str, dict]:
    """Case name → first-pass share, mean fill and golden match, pooled over repeats."""
    pooled: dict[str, list[dict]] = {}
    for c in results["cases"]:
        pooled.setdefault(c["name"], []).append(c)
    out = {}
    for name, runs in pooled.items():
        slides = [s for c in runs for s in c["slides"]]
        fills = [card["fill"] for s in slides for card in s["cards"]]
        golden = [c["golden_match"] for c in runs if "golden_match" in c]
        out[name] = {
            "first_pass": round(sum(s["first_pass_ok"] for s in slides) / len(slides), 2) if slides else None,
            "fill": round(mean(fills), 3) if fills else None,
            "golden": round(mean(golden), 3) if golden else None,
        }
    return out


def _delta(a, b) -> str:
    return f"{b - a:+.3g}" if isinstance(a, (int, float)) and isinstance(b, (int, float)) else ""


def compare(a: dict, b: dict) -> str:
    lines = [f"# `{a['label']}` → `{b['label']}`", "", f"| metric | {a['label']} | {b['label']} | Δ |", "|---|---|---|---|"]
    for key in _HEADLINE:
        va, vb = a["aggregate"].get(key), b["aggregate"].get(key)
        lines.append(f"| {key} | {va} | {vb} | {_delta(va, vb)} |")
    ca, cb = _per_case(a), _per_case(b)
    lines += ["", "| case | first-pass | Δ | fill | Δ | golden | Δ |", "|---|---|---|---|---|---|---|"]
    for name in sorted(set(ca) | set(cb)):
        x, y = ca.get(name, {}), cb.get(name, {})
        cells = []
        for k in ("first_pass", "fill", "golden"):
            cells += [f"{x.get(k)} → {y.get(k)}", _delta(x.get(k), y.get(k))]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two eval results")
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    args = parser.parse_args(argv)
    load = lambda p: json.loads((p / "results.json").read_text(encoding="utf-8"))  # noqa: E731
    sys.stdout.reconfigure(encoding="utf-8")
    print(compare(load(args.a), load(args.b)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
