"""Two-pass sizing for Phase 0b slides (derived-nodes-design §13 R3).

The composer allots height from estimates. On a dense slide the real blocks come out
taller, the slide is over-full, and Yoga shrinks boxes below their text (R2: text drawn
over text on 14 of 88 slides). Here POM's own layout (measure.mjs) checks every pass:

  1. compose; measure each block; recompose with fixed blocks at their natural height and
     each grower given at least what its content needs (the rest shared by weight);
  2. if any text / list / stack is still squashed, step the body type down (x0.92 per
     step, to 0.68; labels keep their size, text >= 11 px, table rows >= 24 px) and
     go back to 1;
  3. if nothing fits at the smallest step, keep it and report SLIDE_OVERFULL with the
     remaining deficit (the pipeline would split the slide or move content).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.phase0b import render as R

HERE = Path(__file__).resolve().parent
SCALES = (1.0, 0.92, 0.85, 0.78, 0.72, 0.68)
TOLERANCE = 8  # px a box may run short before it counts as squashed (a headline 5 px short
               # tightens its line spacing; nothing is drawn over anything)


class Measurer:
    """A long-running node process around measure.mjs."""

    def __init__(self) -> None:
        self.p = subprocess.Popen(["node", str(HERE / "measure.mjs")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, encoding="utf-8")

    def __call__(self, xml: str) -> dict:
        self.p.stdin.write(json.dumps({"xml": xml}) + "\n")
        self.p.stdin.flush()
        reply = json.loads(self.p.stdout.readline())
        if "error" in reply:
            raise RuntimeError(reply["error"])
        return reply["slides"][0]

    def close(self) -> None:
        self.p.stdin.close()
        self.p.wait()


def squash(m: dict) -> int:
    """Largest box deficit on the slide (0 = nothing drawn over anything)."""
    return max([d["deficit"] for d in m["squashed"]] + [m["overfull"]], default=0)


def fit_frame(plan: dict, deck: dict, p: R.Pack, n: int, total: int, measure: Measurer) -> tuple[str, dict]:
    """The slide XML (with theme) and a report: scale used, passes, deficit, SLIDE_OVERFULL."""
    best = None
    passes = 0
    for scale in SCALES:
        p.scale, p.measured, p.min_h = scale, {}, {}
        for _ in range(4):  # recompose until the measured block heights are stable
            xml = p.theme() + "\n<!-- fit-grow: off -->\n" + R.frame(plan, deck, p, n, total) + "\n"
            m = measure(xml)
            passes += 1
            learned, grown = {}, {}
            for i, kind in enumerate(p.block_kinds):
                b = m["blocks"].get(f"blk-{i}")
                if not b:
                    continue
                if kind == "fixed" and abs(b["natural"] - p.measured.get(i, -1)) > 2:
                    learned[i] = b["natural"]          # fixed block: its real height
                elif kind == "grow" and b["natural"] > max(b["h"], p.min_h.get(i, 0)) + 2:
                    grown[i] = b["natural"]            # grower: at least what its content needs
            if not learned and not grown:
                break
            p.measured.update(learned)
            p.min_h.update(grown)
        deficit = squash(m)
        if best is None or deficit < best[1]:
            best = (xml, deficit, scale)
        if deficit <= TOLERANCE:
            return xml, {"scale": scale, "passes": passes, "deficit": deficit, "code": None}
    xml, deficit, scale = best
    return xml, {"scale": scale, "passes": passes, "deficit": deficit, "code": "SLIDE_OVERFULL"}
