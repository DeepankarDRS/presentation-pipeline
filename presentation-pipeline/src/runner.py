"""CLI runner — execute test cases and print a summary table.

Usage:
    python -m src.runner                          # run all cases
    python -m src.runner text-only kpi-row        # run specific cases
    python -m src.runner --theme corporate-slate  # override theme
    python -m src.runner --critic-mode off        # disable critic
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from typing import Any

from src.graph import run
from src.utils.case_loader import load_all_cases, load_case
from src.utils.logging_config import setup_logging


def _format_table(rows: list[dict[str, Any]]) -> str:
    """Format results as an aligned ASCII table."""
    headers = ["Case", "Result", "Retries", "Tier", "Tokens In", "Tokens Out", "Cost ($)", "Time (s)"]
    col_widths = [len(h) for h in headers]

    formatted: list[list[str]] = []
    for row in rows:
        cells = [
            row["name"],
            "PASS" if row["passed"] else "FAIL",
            str(row["retries"]),
            str(row["max_tier"]),
            str(row["tokens_in"]),
            str(row["tokens_out"]),
            f"{row['cost']:.4f}",
            f"{row['elapsed']:.1f}",
        ]
        formatted.append(cells)
        for i, cell in enumerate(cells):
            col_widths[i] = max(col_widths[i], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"

    lines = [sep, header_line, sep]
    for cells in formatted:
        line = "| " + " | ".join(c.ljust(w) for c, w in zip(cells, col_widths)) + " |"
        lines.append(line)
    lines.append(sep)

    return "\n".join(lines)


def run_cases(
    case_names: list[str] | None = None,
    *,
    theme: str = "",
    critic_mode: str = "auto",
    deck_min_threshold: int = 0,
) -> list[dict[str, Any]]:
    """Run test cases and return summary rows."""
    if case_names:
        cases = [load_case(name) for name in case_names]
    else:
        cases = load_all_cases()

    results: list[dict[str, Any]] = []

    for case in cases:
        name = case.get("name", "unnamed")
        case_theme = theme or case.get("theme", "")
        request = case.get("request", case.get("objective", ""))
        rid = f"{name}-{uuid.uuid4().hex[:6]}"

        print(f"\n>> Running: {name} ...", flush=True)
        t0 = time.time()

        try:
            final = run(
                request,
                theme=case_theme,
                critic_mode=critic_mode,
                deck_min_threshold=deck_min_threshold,
                run_id=rid,
            )
            elapsed = time.time() - t0

            evaluation = final.get("evaluation") or {}
            tokens = evaluation.get("tokens", {})
            cost_data = evaluation.get("cost", {})

            results.append({
                "name": name,
                "run_id": rid,
                "passed": final.get("passed", False),
                "retries": final.get("retry_count", 0),
                "max_tier": final.get("retry_tier", 0),
                "tokens_in": tokens.get("total_in", 0),
                "tokens_out": tokens.get("total_out", 0),
                "cost": cost_data.get("total_usd", 0.0),
                "elapsed": elapsed,
                "pptx_path": final.get("pptx_path"),
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f"   ERROR: {e}")
            results.append({
                "name": name,
                "run_id": rid,
                "passed": False,
                "retries": 0,
                "max_tier": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
                "elapsed": elapsed,
                "pptx_path": None,
                "error": str(e),
            })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run presentation pipeline test cases")
    parser.add_argument("cases", nargs="*", help="Case names to run (default: all)")
    parser.add_argument("--theme", default="", help="Override theme for all cases")
    parser.add_argument("--critic-mode", default="auto", choices=["auto", "manual", "off"])
    parser.add_argument("--deck-min-threshold", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    setup_logging()

    results = run_cases(
        args.cases or None,
        theme=args.theme,
        critic_mode=args.critic_mode,
        deck_min_threshold=args.deck_min_threshold,
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(_format_table(results))

        total_pass = sum(1 for r in results if r["passed"])
        total = len(results)
        total_cost = sum(r["cost"] for r in results)
        total_time = sum(r["elapsed"] for r in results)
        print(f"\n{total_pass}/{total} passed | Total cost: ${total_cost:.4f} | Total time: {total_time:.1f}s")


if __name__ == "__main__":
    main()
