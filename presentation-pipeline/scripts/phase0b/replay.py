"""R2 (derived-nodes-design §13): replay saved pipeline plans through the Phase 0b renderer.

    python -m scripts.phase0b.replay <slides.json>... --out output/r2 [--pack studio_inter]

Each input is a run's slides.json (a list of {slide_plan: SlidePlan, ...}). Per deck it
writes <out>/src-<deck>/slide-NN.xml (code-drawn slides), <out>/plans-<deck>.json (the
components the blocks drew, for scripts.phase0b.check) and <out>/coverage.json.

Coverage, per component:
  block        drawn by a Phase 0b block
  fallback     no block: the real design would leave it to the LLM (timeline, flow,
               matrix, layer, group, a caption on a content slide, ...). It is removed
               before rendering, so the slide shows a gap there.
A slide whose renderer call raises counts its components as failed.
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import re
from pathlib import Path

from scripts.phase0b import render as R
from scripts.phase0b.fit import Measurer, fit_frame

BLOCKS = {"title", "narrative", "kpi_row", "table", "chart", "bullet_list", "process_arrow", "card_grid",
          "timeline"}


def classify(comp: dict, slide_type: str | None) -> str:
    k = comp.get("kind")
    if k == "caption":  # cover: in the cover; content slide: the note line above the footer
        return "block"
    if k == "flow":  # a plain sequence of steps is drawn as process steps; branching flows are not
        return "block" if R.linear_flow(comp) else "fallback"
    if k not in BLOCKS:
        return "fallback"
    return "block"  # charts: ranked bars, or POM's native chart for line / doughnut / area / many series


def deck_name(path: Path) -> str:
    return path.parent.name if path.name == "slides.json" else re.sub(r"\W+", "-", path.stem).strip("-")


def replay(path: Path, out: Path, pack: str, measure=None, p: R.Pack | None = None) -> dict:
    """p: a ready pack (e.g. R.deck_pack: the run's own palette); default the named style pack."""
    name = deck_name(path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    plans = [s["slide_plan"] for s in saved if s.get("slide_plan")]
    first = plans[0]
    brand = (first.get("slide_title") or "Deck").split()[0].strip(" ·:|").upper()
    deck = {"pack": pack, "brand": brand, "running": first.get("slide_title") or "", "entities": {}}
    p = p or R.Pack(pack, {})
    src = out / f"src-{name}"
    src.mkdir(parents=True, exist_ok=True)
    drawn_plans, rows = [], []
    counts = collections.Counter()
    for i, plan in enumerate(plans, start=1):
        plan = copy.deepcopy(plan)
        # plans before batch A keep the headline and subtitle in the title component
        tc = next((c for c in plan["components"] if c["kind"] == "title"), {}).get("content_data", {})
        plan["slide_title"] = tc.get("title") or plan.get("slide_title") or ""
        plan.setdefault("label", None)
        plan["subtitle"] = plan.get("subtitle") or tc.get("subtitle")
        kinds = [(c["kind"], classify(c, plan.get("slide_type"))) for c in plan["components"]]
        plan["components"] = [c for c, (_, cls) in zip(plan["components"], kinds) if cls != "fallback"]
        try:
            p.is_dark = R._dark_slide(plan, p)
            fit = None
            if plan.get("slide_type") == "cover":
                xml = p.theme() + "\n<!-- fit-grow: off -->\n" + R.cover(plan, deck, p, len(plans)) + "\n"
            elif measure:  # two-pass sizing against POM's layout (fit.py)
                xml, fit = fit_frame(plan, deck, p, i, len(plans), measure)
            else:
                xml = p.theme() + "\n<!-- fit-grow: off -->\n" + R.frame(plan, deck, p, i, len(plans)) + "\n"
            (src / f"slide-{i:02d}.xml").write_text(xml, encoding="utf-8")
            status = "ok"
        except Exception as error:  # a renderer gap is a finding, not a stop
            status = f"error: {type(error).__name__}: {error}"
            kinds = [(k, "failed") for k, _ in kinds]
            plan["components"] = []
            (src / f"slide-{i:02d}.xml").write_text(p.theme() + "\n<Slide><VStack w=\"1280\" h=\"720\" /></Slide>\n",
                                                   encoding="utf-8")
        counts.update(cls for _, cls in kinds)
        drawn_plans.append(plan)
        rows.append({"slide": i, "status": status, "components": [f"{k}:{cls}" for k, cls in kinds],
                     "fit": fit if status == "ok" else None})
    (out / f"plans-{name}.json").write_text(json.dumps({"deck": deck, "slides": drawn_plans}, ensure_ascii=False,
                                                       indent=1), encoding="utf-8")
    full = sum(1 for r in rows if r["status"] == "ok" and all(c.endswith(":block") for c in r["components"]))
    return {"deck": name, "source": str(path), "slides": len(plans), "slides_all_blocks": full,
            "components": dict(counts), "per_slide": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pack", default="studio_inter")
    ap.add_argument("--fit", action="store_true", help="two-pass sizing against POM's layout (R3)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    measure = Measurer() if a.fit else None
    try:
        decks = [replay(f, a.out, a.pack, measure) for f in a.inputs]
    finally:
        if measure:
            measure.close()
    (a.out / "coverage.json").write_text(json.dumps(decks, ensure_ascii=False, indent=1), encoding="utf-8")
    total = collections.Counter()
    for d in decks:
        total.update(d["components"])
        c = d["components"]
        n = sum(c.values())
        print(f"{d['deck']:28} {d['slides']:3} slides, all-block {d['slides_all_blocks']:2} | "
              f"block {c.get('block', 0)}/{n}, fallback {c.get('fallback', 0)}, failed {c.get('failed', 0)}")
    n = sum(total.values())
    print(f"TOTAL components {n}: block {total['block']} ({total['block'] / n:.0%}), "
          f"fallback {total['fallback']} ({total['fallback'] / n:.0%}), failed {total['failed']}")
    fits = [r["fit"] for d in decks for r in d["per_slide"] if r.get("fit")]
    if fits:
        scales = collections.Counter(f["scale"] for f in fits)
        over = [f"{d['deck']} {r['slide']} ({r['fit']['deficit']} px)" for d in decks for r in d["per_slide"]
                if r.get("fit") and r["fit"]["code"]]
        print(f"FIT {len(fits)} slides: type scale {dict(sorted(scales.items(), reverse=True))}; "
              f"SLIDE_OVERFULL {len(over)}: {', '.join(over)}")


if __name__ == "__main__":
    main()
