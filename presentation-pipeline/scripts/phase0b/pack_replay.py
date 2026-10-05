"""Replay saved plans with several style packs and with a brief's own theme colours (§14.9).

    python -m scripts.phase0b.pack_replay --out output/packs

Draws the three hold-out decks (output/holdout/inputs/*/slides.json) with editorial, tech,
studio_inter and a studio_inter-structured pack recoloured from each case's palette
(QBR corporate-slate, launch midnight-indigo, agency none -> default corporate-slate), with
two-pass sizing, then compiles every slide (scripts.render_check). The recolouring is a plain
token swap on purpose: §14.9 records where that breaks contrast. Experiment code, no API.
"""

from __future__ import annotations

import argparse
import copy
import subprocess
import sys
import types
from pathlib import Path

import yaml

from scripts.phase0b import render as R
from scripts.phase0b import replay as RP
from scripts.phase0b.fit import Measurer

ROOT = Path(__file__).resolve().parents[2]
DECKS = {
    "qbr": ROOT / "output/holdout/inputs/deck-qbr-data-59ba2c/slides.json",
    "launch": ROOT / "output/holdout/inputs/deck-product-launch-data-6f688c/slides.json",
    "agency": ROOT / "output/holdout/inputs/gate-deck-agency-takeover-d0b906/slides.json",
}
SLATE = dict(surface="F7F9FC", surfaceAlt="FFFFFF", accent="2563EB", accentAlt="0EA5E9",
             negative="DC2626", textMain="16202E", textMuted="55627A", border="E2E8F0", dark=False)
INDIGO = dict(surface="12122A", surfaceAlt="232346", accent="818CF8", accentAlt="A5B4FC",
              negative="F87171", textMain="EEF0FB", textMuted="AAAECF", border="3A3A63", dark=True)
BRIEF = {"qbr": SLATE, "launch": INDIGO, "agency": SLATE}
PACKS = ["editorial", "tech", "studio_inter", "brief"]


def from_palette(base: dict, t: dict) -> dict:
    spec = copy.deepcopy(base)
    spec["colors"] = {
        "bg": t["surface"], "ink": t["textMain"], "muted": t["textMuted"], "line": t["border"],
        "panel": t["surfaceAlt"], "dark": "F5F5FC" if t["dark"] else t["textMain"], "white": "FFFFFF",
        "accent": t["accent"], "accent2": t["accentAlt"], "negative": t["negative"],
        "onAccent": t["surface"] if t["dark"] else t["textMain"],
    }
    spec.pop("colors_dark", None)
    return spec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "packs")
    a = ap.parse_args()
    packs = yaml.safe_load((Path(R.__file__).parent / "style_packs.yaml").read_text(encoding="utf-8"))
    extra = {f"brief_{k}": from_palette(packs["studio_inter"], v) for k, v in BRIEF.items()}
    real = R.yaml.safe_load
    R.yaml = types.SimpleNamespace(safe_load=lambda txt: {**real(txt), **extra})
    m = Measurer()
    try:
        for pack in PACKS:
            for deck, src in DECKS.items():
                out = a.out / pack / deck
                out.mkdir(parents=True, exist_ok=True)
                RP.replay(src, out, f"brief_{deck}" if pack == "brief" else pack, m)
    finally:
        m.close()
    for pack in PACKS:
        for deck in DECKS:
            for srcdir in (a.out / pack / deck).glob("src-*"):
                subprocess.run([sys.executable, "-m", "scripts.render_check", "--in", str(srcdir),
                                "--out", str(a.out / pack / deck / "rc")], cwd=ROOT, check=True,
                               capture_output=True)
                print("compiled", pack, deck)


if __name__ == "__main__":
    main()
