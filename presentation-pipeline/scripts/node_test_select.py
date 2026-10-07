"""1a slide selection (docs/derived-blocks-planning-2026-10-06.md §4.1, D11): every step 0 slide that has a
component to place, except the slides the node prompt's examples were drawn from.

    python -m scripts.node_test_select [--bundles output/step0/b1 output/step0/b2x ...] [--out docs/eval/step0/1a-slides.json]

Rule: pool = every deck in the bundles; out = (1) a slide whose title is the title of a prompt-example source
slide (src/prompts/generator/nodes_rules.j2), (2) a slide whose components are all `title` / `layer`.
Every other slide is in; no sampling.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.from_plans import find_runs, load_run
from src.compiler.nodes.spec import NO_REF_KINDS

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "src" / "prompts" / "generator" / "nodes_rules.j2"


def example_titles(text: str | None = None) -> set[str]:
    """The headlines of the example skeletons: the slides they were drawn from share them."""
    text = text if text is not None else EXAMPLES.read_text(encoding="utf-8")
    heads = re.findall(r'<Text fontSize="(\d+)" bold="true"[^>]*>([^<]+)</Text>', text)
    return {_norm(t) for fs, t in heads if int(fs) >= 28}


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def select(runs: dict[str, Path], examples: set[str]) -> dict:
    chosen, left_out = [], []
    for case, folder in sorted(runs.items()):
        for s in load_run(folder)["slides"]:
            plan = s["plan"]
            comps = [c for c in plan.get("components") or [] if c["kind"] not in NO_REF_KINDS]
            row = {"case": case, "slide": s["number"], "title": plan.get("slide_title", ""),
                   "components": [{"id": c["component_id"], "kind": c["kind"]} for c in plan.get("components") or []]}
            if _norm(plan.get("slide_title", "")) in examples:
                left_out.append({**row, "reason": "prompt example source"})
            elif not comps:
                left_out.append({**row, "reason": "nothing to place (title / layer only)"})
            else:
                chosen.append(row)
    n_comp = sum(sum(c["kind"] not in NO_REF_KINDS for c in r["components"]) for r in chosen)
    return {"rule": "docs/derived-blocks-planning-2026-10-06.md §4.1 (D11)", "slides": chosen, "left_out": left_out,
            "counts": {"slides": len(chosen), "components": n_comp, "decks": len({r["case"] for r in chosen})}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bundles", type=Path, nargs="*", default=sorted((ROOT / "output" / "step0").glob("b*")))
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "eval" / "step0" / "1a-slides.json")
    a = ap.parse_args()
    runs: dict[str, Path] = {}
    for b in a.bundles:
        for case, folder in find_runs(b).items():
            runs.setdefault(case, folder)
    result = select(runs, example_titles())
    for r in result["slides"]:   # repo-relative paths only: the test PC has the same layout
        r["run"] = runs[r["case"]].resolve().relative_to(ROOT).as_posix()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    c = result["counts"]
    print(f"{c['slides']} slides, {c['components']} components, {c['decks']} decks -> {a.out}")
    for r in result["left_out"]:
        print(f"  out: {r['case']} {r['slide']} ({r['reason']}) {r['title'][:60]}")


if __name__ == "__main__":
    main()
