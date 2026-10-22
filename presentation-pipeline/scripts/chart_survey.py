"""Every saved chart slide, before / after today's chart rules. LLM-free, no compile.

    python -m scripts.chart_survey --roots ../output            # any folders of saved runs
    python -m scripts.chart_survey --roots output/step0 --list   # also print each chart that changes

Finds every input.xml / generated.xml holding a <Chart> (duplicates by content counted once), and
reports per chart: type, series, points, legend, how it is coloured, and what the normalizer's chart
focus rule (src/compiler/normalizer._chart_focus) changes. Numbers for docs/chart-pass-2026-10-22.md.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.compiler.normalizer import (  # noqa: E402
    _CHART_COLORS_RE, _CHART_RE, _COLOR_ITEM_RE, _chart_focus, _is_rest_colour,
)


def _colouring(attrs: str, body: str) -> str:
    cm = _CHART_COLORS_RE.search(attrs)
    if not cm:
        return "none"
    colors = _COLOR_ITEM_RE.findall(cm.group("sq") or cm.group("dq"))
    distinct = set(colors)
    single = body.count("<ChartSeries") == 1
    points = len(re.findall(r"<ChartDataPoint\b", body))
    if len(distinct) == 1:
        return "one colour"
    if len(distinct) == 2 and sum(map(_is_rest_colour, distinct)) == 1:
        return "focus + rest"
    if single and len(colors) >= points and len(distinct) >= 3:
        return "colour per bar (rainbow)"
    return "colour per series"


def survey(roots: list[Path], list_changes: bool) -> None:
    seen: set[str] = set()
    charts: list[dict] = []
    changed = Counter()
    for root in roots:
        for path in sorted(list(root.rglob("input.xml")) + list(root.rglob("generated.xml"))):
            xml = path.read_text(encoding="utf-8", errors="replace")
            if "<Chart" not in xml:
                continue
            key = hashlib.sha1(xml.encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            out, counts = _chart_focus(xml)
            changed.update({k: v for k, v in counts.items() if v})
            if list_changes and out != xml:
                print(f"{path}: {dict((k, v) for k, v in counts.items() if v)}")
            for m in _CHART_RE.finditer(xml):
                attrs, body = m.group("attrs"), m.group("body")
                km = re.search(r'chartType="(\w+)"', attrs)
                charts.append({
                    "kind": km.group(1) if km else "?",
                    "series": body.count("<ChartSeries"),
                    "legend": 'showLegend="true"' in attrs,
                    "sparkline": 'sparkline="true"' in attrs,
                    "hex": bool(re.search(r"(?:\"|&quot;)#?[0-9A-Fa-f]{6}(?:\"|&quot;)", attrs)),
                    "colouring": _colouring(attrs, body),
                })
    n = len(charts)
    print(f"slides with a chart (unique): {len(seen)}; charts: {n}")
    print("types:", dict(Counter(c["kind"] for c in charts).most_common()))
    print("series per chart:", dict(sorted(Counter(min(c["series"], 4) for c in charts).items())), "(4 = 4+)")
    print(f"legend on: {sum(c['legend'] for c in charts)}  ·  sparkline: {sum(c['sparkline'] for c in charts)}"
          f"  ·  literal hex in chartColors: {sum(c['hex'] for c in charts)}")
    print("colouring:", dict(Counter(c["colouring"] for c in charts).most_common()))
    multi = [c for c in charts if c["series"] > 1]
    print(f"multi-series: {len(multi)}, of them with a legend: {sum(c['legend'] for c in multi)}")
    print("chart focus rule changes:", dict(changed) or "none")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--roots", nargs="+", type=Path, default=[ROOT / "output"])
    ap.add_argument("--list", action="store_true", help="print every slide the focus rule changes")
    a = ap.parse_args()
    survey(a.roots, a.list)


if __name__ == "__main__":
    main()
