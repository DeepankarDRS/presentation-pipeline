"""Outline items, gates 1-2 report (docs/outline-items-design-2026-10-27.md §7), free: reads saved plan-only runs.

    python -m scripts.outline_items_report outline-items --base typed-schema
        # output/card-plans/<label>/runs.json (scripts.card_plan_only --outline-items) against a saved run without items

Gate 1 (outline): items by kind, POINT_NOT_IN_BRIEF review points, item-form issues, speaker notes left in items,
brief numbers dropped from / added to the outline, the same kinds on a slide across repeats.
Gate 2 (planner): narrative share, components per slide, distinct kinds per deck, KIND_OUTSIDE_FIT notes (listed for
reading by hand), outline numbers missing from the plan. Both runs get the outline / plan numbers; the item measures
only the run with items. Writes output/card-plans/<label>/outline-items.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.agents.outline_items import ITEM_KINDS, item_issues  # noqa: E402
from src.agents.written_lines import NOTES_LABEL  # noqa: E402
from src.utils.case_loader import load_case  # noqa: E402

OUT = _ROOT / "output" / "card-plans"
# a figure: 2+ digits or a decimal; thousands separators and trailing decimal zeros ignored ("4.40" = "4.4")
_FIGURE = re.compile(r"\d[\d,]*\.\d+|\d[\d,]*\d")


def figures(text: str) -> set[str]:
    out = set()
    for f in _FIGURE.findall(text or ""):
        f = f.replace(",", "")
        out.add(f.rstrip("0").rstrip(".") if "." in f else f)
    return out


def brief_figures(case: dict[str, Any]) -> set[str]:
    return figures(" ".join([case.get("request") or "", json.dumps(case.get("supplied_content") or {}, ensure_ascii=False),
                             json.dumps(case.get("clarification_answers") or {}, ensure_ascii=False)]))


def _leaves(v: Any) -> list[str]:
    if isinstance(v, dict):
        return [x for val in v.values() for x in _leaves(val)]
    if isinstance(v, list):
        return [x for val in v for x in _leaves(val)]
    return [] if v is None or isinstance(v, bool) else [str(v)]


def body(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in plan.get("components") or [] if c.get("kind") != "title"]


def outline_text(slide: dict[str, Any]) -> str:
    return " ".join([slide.get("slide_title", ""), slide.get("subtitle", ""), *(slide.get("key_messages") or [])])


def plan_text(plan: dict[str, Any]) -> str:
    return " ".join([plan.get("slide_title", ""), plan.get("subtitle", ""),
                     *[x for c in plan.get("components") or [] for x in _leaves(c.get("content_data") or {})]])


def measure(runs: list[dict[str, Any]], cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    m: dict[str, Any] = defaultdict(int)
    kinds_by_slide: dict[tuple[str, int], list[tuple[str, ...]]] = defaultdict(list)
    lists: dict[str, list[str]] = defaultdict(list)
    deck_kinds = []
    for r in runs:
        case = cases[r["case"]]
        bf = brief_figures(case)
        slides = (r.get("outline") or {}).get("slides") or []
        m["runs"] += 1
        m["cost"] += r.get("cost_usd") or 0.0
        if r.get("error") or not slides:
            m["runs_failed"] += 1
            lists["runs_failed"].append(f"{r['case']} r{r.get('repeat')}: {r.get('error') or 'no outline'}")
            continue
        out_figs = set().union(*(figures(outline_text(s)) for s in slides)) if slides else set()
        m["brief_figures"] += len(bf)
        m["brief_figures_not_in_outline"] += len(bf - out_figs)
        m["outline_figures_not_in_brief"] += len(out_figs - bf)
        for s in slides:
            m["slides"] += 1
            items = s.get("items")
            if items is None:
                continue
            m["items"] += len(items)
            for i in items:
                m[f"kind:{i.get('kind')}"] += 1
                if NOTES_LABEL.match(i.get("text", "")):
                    m["speaker_notes"] += 1
            m["review_points"] += len(s.get("review_points") or [])
            lists["review_points"] += [f"{r['case']} s{s.get('slide_index', 0) + 1}: {t}" for t in s.get("review_points") or []]
            for code, text in item_issues(items):
                m[f"issue:{code}"] += 1
                lists["item_issues"].append(f"{r['case']} s{s.get('slide_index', 0) + 1} {code}: {text}")
            kinds_by_slide[(r["case"], s.get("slide_index", 0))].append(tuple(sorted(i.get("kind", "") for i in items)))
        plans = r.get("slide_plans") or []
        kinds = Counter(c.get("kind") for p in plans for c in body(p))
        deck_kinds.append(len(kinds))
        m["components"] += sum(kinds.values())
        m["narrative"] += kinds["narrative"]
        m["plans"] += len(plans)
        by_index = {s.get("slide_index"): s for s in slides}
        for p in plans:
            s = by_index.get(p.get("slide_index")) or {}
            lost = figures(" ".join(s.get("key_messages") or [])) - figures(plan_text(p))
            m["outline_figures_not_in_plan"] += len(lost)
            for note in p.get("kind_fit_notes") or []:
                m["kind_outside_fit"] += 1
                lists["kind_outside_fit"].append(f"{r['case']} s{p.get('slide_index', 0) + 1}: {note}")
    repeated = [v for v in kinds_by_slide.values() if len(v) > 1]
    m["slides_repeated"] = len(repeated)
    m["slides_same_kinds"] = sum(len(set(v)) == 1 for v in repeated)
    m["kinds_per_deck"] = sum(deck_kinds) / len(deck_kinds) if deck_kinds else 0.0
    m["lists"] = lists
    return m


def _pct(a: float, b: float) -> str:
    return f"{a / b:.0%}" if b else "-"


def report(label: str, m: dict[str, Any], base_label: str | None, b: dict[str, Any] | None) -> str:
    cols = [label] + ([base_label] if b else [])
    ms = [m] + ([b] if b else [])

    def row(name: str, fn) -> str:
        return f"| {name} | " + " | ".join(fn(x) for x in ms) + " |"

    head = ["| | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    lines = [f"# Outline items, gates 1-2: {label}" + (f" vs {base_label}" if b else ""), "", *head,
             row("runs / cost", lambda x: f"{x['runs']} / ${x['cost']:.3f}"),
             row("runs with no outline or an error", lambda x: str(x["runs_failed"])),
             row("slides (outline / plans)", lambda x: f"{x['slides']} / {x['plans']}"),
             "", "**Gate 1, outline**", "", *head,
             row("brief figures not in the outline", lambda x: f"{x['brief_figures_not_in_outline']} of {x['brief_figures']}"),
             row("outline figures not in the brief", lambda x: str(x["outline_figures_not_in_brief"])),
             row("items", lambda x: str(x["items"]) if x["items"] else "-"),
             *[row(f"kind {k}", lambda x, k=k: f"{x[f'kind:{k}']} ({_pct(x[f'kind:{k}'], x['items'])})" if x["items"] else "-")
               for k in ITEM_KINDS],
             row("POINT_NOT_IN_BRIEF review points", lambda x: str(x["review_points"]) if x["items"] else "-"),
             row("VISUAL_WITH_NUMBERS", lambda x: str(x["issue:VISUAL_WITH_NUMBERS"]) if x["items"] else "-"),
             row("RECORDS_WITHOUT_MEASURES", lambda x: str(x["issue:RECORDS_WITHOUT_MEASURES"]) if x["items"] else "-"),
             row("speaker notes in items", lambda x: str(x["speaker_notes"]) if x["items"] else "-"),
             row("slides with the same kinds across repeats",
                 lambda x: f"{x['slides_same_kinds']} of {x['slides_repeated']}" if x["items"] else "-"),
             "", "**Gate 2, planner**", "", *head,
             row("components / per slide", lambda x: f"{x['components']} / {x['components'] / max(1, x['plans']):.2f}"),
             row("narrative share", lambda x: f"{x['narrative']} ({_pct(x['narrative'], x['components'])})"),
             row("distinct kinds per deck", lambda x: f"{x['kinds_per_deck']:.2f}"),
             row("outline figures not in the plan", lambda x: str(x["outline_figures_not_in_plan"])),
             row("KIND_OUTSIDE_FIT", lambda x: str(x["kind_outside_fit"]) if x["items"] else "-"),
             ""]
    for name, title in (("runs_failed", "Runs with no outline or an error (left out of every count above)"),
                        ("review_points", "POINT_NOT_IN_BRIEF (read: outline commentary or brief?)"),
                        ("kind_outside_fit", "KIND_OUTSIDE_FIT (read: mistake or a legitimate pick?)"),
                        ("item_issues", "Item-form issues")):
        lines += [f"## {title}", ""] + [f"- {t}" for t in m["lists"].get(name) or ["(none)"]] + [""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("label")
    ap.add_argument("--base", default=None, help="a saved run without items to compare with, e.g. typed-schema")
    a = ap.parse_args()
    runs = json.loads((OUT / a.label / "runs.json").read_text(encoding="utf-8"))
    base = json.loads((OUT / a.base / "runs.json").read_text(encoding="utf-8")) if a.base else None
    cases = {n: load_case(n) for n in {r["case"] for r in runs + (base or [])}}
    text = report(a.label, measure(runs, cases), a.base, measure(base, cases) if base else None)
    (OUT / a.label / "outline-items.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
