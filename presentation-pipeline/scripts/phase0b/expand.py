"""Phase 0c (derived-nodes-design §13 R3): expand block slots inside an LLM-style skeleton.

    python -m scripts.phase0b.expand scripts/phase0b/phase0c --out output/r3/mixed

A skeleton is ordinary POM XML written the way the generator writes slides (free Text,
VStack / HStack, its own widths), except that a component the code draws is a
placeholder:  <VStack id="slot-<component_id>" w="50%" grow="1" />  (any size attributes).
Each skeleton names its plan: <!-- plan: <plans.json>#<slide number> -->.

Two passes against POM's layout (measure.mjs):
  1. lay out the skeleton with empty slots -> each slot's box (w, h);
  2. draw each block for that box, put it in the slot, lay out again; if any text is
     squashed, step the blocks' type down (fit.SCALES); at the smallest step report
     SLIDE_OVERFULL. Free text in the skeleton is never changed.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.phase0b import render as R
from scripts.phase0b.fit import SCALES, TOLERANCE, Measurer, squash

SLOT = re.compile(r'<VStack\b([^>]*?)\bid="slot-([\w-]+)"([^>]*?)/>')
PLAN = re.compile(r"<!--\s*plan:\s*(\S+?)#(\d+)\s*-->")


def draw(comp: dict, p: R.Pack, w: float, h: float) -> str:
    """One block drawn for a w x h slot; it fills the slot."""
    k, g = comp["kind"], ' grow="1"'
    if k == "kpi_row":
        return R.kpi_block(comp, p, w, h, g)
    if k == "card_grid":
        return R.card_grid(comp, p, w, True, h=h, grow=g)
    if k == "table":
        return f'<VStack{g}>{R.data_table(comp, p, w, h)}</VStack>'
    if k == "chart":
        title = comp["content_data"].get("chart_title")
        head = p.label(title) if title else ""
        return f'<VStack gap="12"{g}>{head}{R.chart_block(comp, p, w, h - (24 if title else 0))}</VStack>'
    if k == "bullet_list":
        return R.bullets_block(comp, p, g, width=w)
    if k == "process_arrow" or (k == "flow" and R.linear_flow(comp)):
        return R.process_steps(comp, p)
    if k == "caption":
        text = str((comp.get("content_data") or {}).get("text") or "").strip()
        if not text:  # POM rejects an empty <Text>
            return "<VStack />"
        return (f'<Text fontSize="{R.NOTE_FS}" fontFamily="{p.sans}" color="$muted" lineHeight="1.35">'
                f'{R.x(text)}</Text>')
    if k == "narrative":
        return R.insight(comp["content_data"]["text"], p)
    raise ValueError(f"no block for {k}")


def expand(skeleton: str, plan: dict, p: R.Pack, measure: Measurer) -> tuple[str, dict]:
    comps = {c["component_id"]: c for c in plan["components"]}
    head = p.theme() + "\n<!-- fit-grow: off -->\n"
    body = PLAN.sub("", skeleton)
    m = measure(head + body)                     # pass 1: the slots' boxes
    boxes = m["slots"]
    best = None
    for scale in SCALES:
        p.scale = scale

        def fill(mt: re.Match) -> str:
            attrs = (mt.group(1) + mt.group(3)).strip()
            cid = mt.group(2)
            box = boxes[f"slot-{cid}"]
            inner = R.scale_type(draw(comps[cid], p, box["w"], box["h"]), scale)
            return f'<VStack id="slot-{cid}" {attrs} alignItems="stretch">{inner}</VStack>'

        xml = head + SLOT.sub(fill, body)
        m2 = measure(xml)                        # pass 2: blocks in their slots
        deficit = squash(m2)
        if best is None or deficit < best[1]:
            best = (xml, deficit, scale)
        if deficit <= TOLERANCE:
            return xml, {"scale": scale, "deficit": deficit, "code": None, "slots": boxes}
    xml, deficit, scale = best
    return xml, {"scale": scale, "deficit": deficit, "code": "SLIDE_OVERFULL", "slots": boxes}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skeletons", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pack", default="studio_inter")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    measure = Measurer()
    plans_out, report = {}, {}
    try:
        for f in sorted(a.skeletons.glob("*.xml")):
            skeleton = f.read_text(encoding="utf-8")
            src, n = PLAN.search(skeleton).groups()
            deck = json.loads(Path(src).read_text(encoding="utf-8"))
            plans = deck["slides"] if isinstance(deck, dict) else [s["slide_plan"] for s in deck]
            plan = plans[int(n) - 1]
            p = R.Pack(a.pack, (deck.get("deck") or {}).get("entities") if isinstance(deck, dict) else {})
            xml, rep = expand(skeleton, plan, p, measure)
            (a.out / f.name).write_text(xml, encoding="utf-8")
            used = set(SLOT.findall(skeleton) and [g[1] for g in SLOT.findall(skeleton)])
            plans_out[f.stem] = {**plan, "components": [c for c in plan["components"] if c["component_id"] in used]}
            report[f.stem] = rep
            print(f"{f.stem}: scale {rep['scale']}, deficit {rep['deficit']} px"
                  + (f", {rep['code']}" if rep["code"] else "") + " | slots "
                  + ", ".join(f"{k[5:]} {v['w']}x{v['h']}" for k, v in rep["slots"].items()))
    finally:
        measure.close()
    (a.out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (a.out / "plans.json").write_text(json.dumps(plans_out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
