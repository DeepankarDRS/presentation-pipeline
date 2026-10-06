"""Draw a pipeline run's slide plans with the code composer, as one .pptx (research tool, §14).

    python -m scripts.phase0b.compose_deck output/runs/<run_id> [--pack studio_inter] [--fallback llm|gap]

Takes the run's slides.json (written by every pipeline run), draws each slide with the
Phase 0b composer + two-pass sizing (replay.py --fit), compiles, merges the slides and
embeds Inter + JetBrains Mono so PowerPoint draws them without the fonts installed.

A slide with a component that has no block (timeline, flow, matrix, a caption on a content
slide, ...) uses the LLM's own slide from the same run (--fallback llm, the default; what a
build would do) or the code slide with that component left out (--fallback gap).

Writes <run>/composed/composed.pptx; the run's LLM deck is <run>/deck/presentation.pptx.
No API calls. Experiment code, not wired into the pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.phase0b.fit import Measurer
from scripts.phase0b.replay import deck_name, replay
from scripts.render_check import _compile
from src.compiler.font_embed import embed_deck_fonts
from src.compiler.pptx_merge import merge_pptx_files


def run_folder(path: Path) -> Path:
    """The run folder: the given folder or the nearest parent holding slides.json."""
    for p in [path, *path.parents]:
        if (p / "slides.json").exists():
            return p
    raise FileNotFoundError(f"{path}: no slides.json here or above (pass output/runs/<run_id>)")


def compose(run: Path, pack: str = "studio_inter", fallback: str = "llm") -> dict:
    """Draw the run's plans; returns {pptx, slides, code, llm, left_out, smaller_type, overfull}.
    Writes <run>/composed/composed.pptx."""
    try:  # the blocks measure text with the real font files; without Pillow they silently estimate
        from PIL import ImageFont  # noqa: F401
    except ImportError as e:
        raise RuntimeError("Pillow is required to draw composed decks (real text widths): "
                           "uv pip install pillow  (or pip install pillow)") from e
    run = run_folder(run.resolve())
    out = run / "composed"
    saved = json.loads((run / "slides.json").read_text(encoding="utf-8"))
    deck_xml = run / "deck" / "input.xml"
    m = re.search(r"<Theme[^>]*/>", deck_xml.read_text(encoding="utf-8")) if deck_xml.exists() else None
    theme = m.group() if m else ""

    measure = Measurer()
    try:
        report = replay(run / "slides.json", out, pack, measure)
    finally:
        measure.close()
    code_dir = out / f"src-{deck_name(run / 'slides.json')}"

    pptx, kinds, left_out = [], [], []
    for row, s in zip(report["per_slide"], saved):
        n = row["slide"]
        all_blocks = row["status"] == "ok" and all(c.endswith(":block") for c in row["components"])
        src = code_dir / f"slide-{n:02d}.xml"
        if not all_blocks and fallback == "llm" and s.get("xml"):
            src = out / "llm" / f"slide-{n:02d}.xml"
            src.parent.mkdir(parents=True, exist_ok=True)
            xml = s["xml"] if "<Theme" in s["xml"] else theme + "\n" + s["xml"]
            src.write_text(xml, encoding="utf-8")
        kinds.append("code" if src.parent == code_dir else "llm")
        res = _compile(src, out / "build" / f"slide-{n:02d}")
        if res.get("status") != "success":
            left_out.append(n)
            continue
        pptx.append(out / "build" / f"slide-{n:02d}" / "presentation.pptx")
    if not pptx:
        raise RuntimeError(f"{run}: no slide compiled")

    merged = merge_pptx_files(pptx, out / "merged.pptx")
    final = out / "composed.pptx"
    embed_deck_fonts(merged, final)  # the open fonts the slides name, subset (src/compiler/font_embed.py)
    merged.unlink()  # same slides without the fonts: only an intermediate step
    fits = [r.get("fit") or {} for r in report["per_slide"]]
    return {
        "pptx": str(final),
        "slides": len(kinds),
        "code": [i + 1 for i, k in enumerate(kinds) if k == "code"],
        "llm": [i + 1 for i, k in enumerate(kinds) if k == "llm"],
        "left_out": left_out,
        "smaller_type": {i + 1: f["scale"] for i, f in enumerate(fits) if f.get("scale", 1) < 1},
        "overfull": [i + 1 for i, f in enumerate(fits) if f.get("code")],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path, help="output/runs/<run_id> (or any path inside it)")
    ap.add_argument("--pack", default="studio_inter", help="style pack (scripts/phase0b/style_packs.yaml)")
    ap.add_argument("--fallback", choices=["llm", "gap"], default="llm")
    a = ap.parse_args()
    try:
        r = compose(a.run, a.pack, a.fallback)
    except FileNotFoundError as e:
        sys.exit(str(e))
    print(f"slides: {len(r['code'])} code-drawn, {len(r['llm'])} LLM fallback "
          f"({', '.join(map(str, r['llm'])) or 'none'})")
    if r["left_out"]:
        print(f"left out (did not compile): {', '.join(map(str, r['left_out']))}")
    print("smaller type on: " + (", ".join(f"{n} (x{s})" for n, s in r["smaller_type"].items()) or "none"))
    if r["overfull"]:
        print("SLIDE_OVERFULL: " + ", ".join(map(str, r["overfull"])))
    print(f"composed deck: {r['pptx']}")
    llm = run_folder(a.run.resolve()) / "deck" / "presentation.pptx"
    if llm.exists():
        print(f"LLM deck (same run): {llm}")


if __name__ == "__main__":
    main()
