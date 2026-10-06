"""Tokens and cost per case, pipeline step and slide, from run manifests (§14.6 step 0).

    python -m scripts.usage_report output/runs/<run_id> [more folders / manifests ...] [--per-slide]
    python -m scripts.usage_report docs/eval/step0 --per-slide

Every folder is searched for run-manifest.json (the eval bundle keeps one per case in
decks/<case>__rN/). Old manifests have no step names: their calls are listed as "unknown"
and told apart only by model. tokens_out includes tokens_reasoning and tokens_in includes
tokens_cached; the cost column is the manifest's list-price cost (no cache discount).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

FIELDS = ("calls", "tokens_in", "tokens_cached", "tokens_out", "tokens_reasoning", "cost")


def find_manifests(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for p in paths:
        found += [p] if p.is_file() else sorted(p.rglob("run-manifest.json"))
    return found


def case_name(manifest: Path) -> str:
    return manifest.parent.name


def _add(row: dict[str, Any], step: dict[str, Any]) -> None:
    row["calls"] += 1
    for key in FIELDS[1:]:
        row[key] += step.get(key, 0) or 0


def collect(manifests: list[Path], per_slide: bool = False) -> dict[tuple, dict[str, Any]]:
    """{(case, step, slide_index or None): totals}"""
    rows: dict[tuple, dict[str, Any]] = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    for m in manifests:
        data = json.loads(m.read_text(encoding="utf-8"))
        for step in data.get("steps", []):
            slide = step.get("slide_index") if per_slide else None
            _add(rows[(case_name(m), step.get("step", "unknown"), slide)], step)
    return rows


def render(rows: dict[tuple, dict[str, Any]]) -> str:
    lines = ["| case | step | slide | calls | in | cached | out | reasoning | cost $ |",
             "|---|---|---|---|---|---|---|---|---|"]
    total = dict.fromkeys(FIELDS, 0)
    for (case, step, slide), r in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[0][1], -1 if kv[0][2] is None else kv[0][2])):
        lines.append(f"| {case} | {step} | {'' if slide is None else slide + 1} | {r['calls']} | {r['tokens_in']} | "
                     f"{r['tokens_cached']} | {r['tokens_out']} | {r['tokens_reasoning']} | {r['cost']:.4f} |")
        for key in FIELDS:
            total[key] += r[key]
    lines.append(f"| **total** | | | {total['calls']} | {total['tokens_in']} | {total['tokens_cached']} | "
                 f"{total['tokens_out']} | {total['tokens_reasoning']} | {total['cost']:.4f} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=Path, help="run folders, eval folders or run-manifest.json files")
    ap.add_argument("--per-slide", action="store_true", help="one row per slide instead of per step")
    a = ap.parse_args(argv)
    manifests = find_manifests(a.paths)
    if not manifests:
        print("no run-manifest.json found", file=sys.stderr)
        return 1
    print(render(collect(manifests, a.per_slide)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
