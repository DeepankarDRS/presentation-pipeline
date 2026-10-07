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
    if k == "timeline":
        return R.timeline_block(comp, p, w, h, g)
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


# ── ref nodes (node contract §3, 1a §4): <KpiRow ref="summary_kpis" w="60%" /> ──────────────

FONT_TAGS = ("Text", "Ul", "Ol", "Td", "Timeline", "ProcessArrow", "Pyramid")
# D8 (2026-10-05): no block text under the 12 px label floor (Phase 0b blocks draw some notes
# at 11 px and the type steps go lower); step 1 bakes the floors into the blocks themselves
LABEL_FLOOR = 12
BELOW_FLOOR = re.compile(r'fontSize="(?:\d|1[01])(?:\.\d+)?"')


def deck_font(xml: str, family: str | None) -> str:
    """Every text-bearing node without a fontFamily gets the deck font (both 1a arms, font-neutral)."""
    if not family:
        return xml
    pat = re.compile(rf"<({'|'.join(FONT_TAGS)})\b(?![^<>]*\bfontFamily=)")
    return pat.sub(lambda m: f'<{m.group(1)} fontFamily="{family}"', xml)


def _layout_attrs(a: dict) -> str:
    from src.compiler.nodes.native import LAYOUT
    return "".join(f' {k}="{v}"' for k, v in a.items() if k in LAYOUT)


def draw_derived(tag: str, comp: dict, p: R.Pack, w: float, h: float) -> str:
    if tag == "Callout":
        return R.insight(str((comp.get("content_data") or {}).get("text") or ""), p)
    return draw(comp, p, w, h)


def expand_nodes(skeleton: str, plan: dict, theme_element: str, measure: Measurer,
                 theme: dict | None = None, font: str | None = "Inter") -> tuple[str, dict]:
    """A generator skeleton with ref tags -> plain POM (no <Theme>) and a report:
    {check (validate result), scale, deficit, code, boxes, issues (NODE_EXPAND_FAILED, NODE_OVERFULL)}."""
    from src.compiler.nodes import native as N
    from src.compiler.nodes import spec as S
    from src.compiler.nodes import validate as V

    res = V.check_skeleton(PLAN.sub("", skeleton), plan)
    comps = {c["component_id"]: c for c in plan.get("components") or []}
    p = R.deck_pack(theme_element)
    body = res["xml"]
    tags = V.ref_tags(body)
    issues: list[dict] = []

    def failed(t: dict, e: Exception) -> str:
        ref = t["attrs"]["ref"]
        issues.append({"code": "NODE_EXPAND_FAILED", "severity": "error", "ref": ref,
                       "message": f"drawing {t['tag']} ref={ref} raised {type(e).__name__}: {e}"})
        return f"<VStack{_layout_attrs(t['attrs'])} />"

    natives: dict[int, str] = {}
    for i, t in enumerate(tags):
        if S.family(t["tag"]) == "native":
            try:   # id="node-<ref>" marks the node for scoring (1a measure 2: words inside nodes)
                natives[i] = re.sub(r"^<(\w+)", rf'<\1 id="node-{t["attrs"]["ref"]}"',
                                    N.fill(t["tag"], comps[t["attrs"]["ref"]], t["attrs"], theme), count=1)
            except Exception as e:  # a filler bug must not lose the slide
                natives[i] = failed(t, e)

    def build(derived) -> str:
        out = body
        for i, t in sorted(enumerate(tags), key=lambda it: -it[1]["start"]):
            rep = natives[i] if i in natives else derived(t)
            out = out[:t["start"]] + rep + out[t["end"]:]
        return deck_font(out, font)

    def slot(t: dict) -> str:
        return f'<VStack id="slot-{t["attrs"]["ref"]}"{_layout_attrs(t["attrs"])} />'

    boxes = measure(theme_element + "\n" + build(slot))["slots"]   # pass 1: the derived nodes' boxes
    best = None
    for scale in SCALES:
        drawn: dict[str, str] = {}

        def block(t: dict) -> str:
            ref = t["attrs"]["ref"]
            if ref not in drawn:
                box = boxes.get(f"slot-{ref}") or {"w": 400, "h": 200}
                try:
                    inner = R.retoken(R.scale_type(draw_derived(t["tag"], comps[ref], p, box["w"], box["h"]), scale), p)
                    inner = BELOW_FLOOR.sub(f'fontSize="{LABEL_FLOOR}"', inner)
                    drawn[ref] = f'<VStack id="slot-{ref}"{_layout_attrs(t["attrs"])} alignItems="stretch">{inner}</VStack>'
                except Exception as e:
                    drawn[ref] = failed(t, e)
            return drawn[ref]

        p.scale = scale
        xml = build(block)
        deficit = squash(measure(theme_element + "\n" + xml))       # pass 2: blocks in their boxes
        if best is None or deficit < best[1]:
            best = (xml, deficit, scale)
        if deficit <= TOLERANCE:
            break
    xml, deficit, scale = best
    if deficit > TOLERANCE:
        issues.append({"code": "NODE_OVERFULL", "severity": "report", "ref": None,
                       "message": f"blocks at the smallest type step still {deficit}px short"})
    once = {(i["code"], i["ref"]): i for i in issues}   # a failed draw is retried per scale: report it once
    return xml, {"check": res, "scale": scale, "deficit": deficit, "boxes": boxes,
                 "issues": res["issues"] + list(once.values())}


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
