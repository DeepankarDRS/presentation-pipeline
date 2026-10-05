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

from scripts.embed_fonts import embed
from scripts.phase0b.fit import Measurer
from scripts.phase0b.replay import deck_name, replay
from scripts.render_check import _compile
from src.compiler.pptx_merge import merge_pptx_files

FONTS_DIR = Path(__file__).resolve().parents[2] / "src" / "node" / "fonts"
FONTS = {
    "Inter": {"regular": "Inter-Regular.ttf", "bold": "Inter-Bold.ttf",
              "italic": "Inter-Italic.ttf", "boldItalic": "Inter-BoldItalic.ttf"},
    "JetBrains Mono": {"regular": "JetBrainsMono-Regular.ttf", "bold": "JetBrainsMono-Bold.ttf"},
}


def run_folder(path: Path) -> Path:
    """The run folder: the given folder or the nearest parent holding slides.json."""
    for p in [path, *path.parents]:
        if (p / "slides.json").exists():
            return p
    sys.exit(f"{path}: no slides.json here or above (pass output/runs/<run_id>)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path, help="output/runs/<run_id> (or any path inside it)")
    ap.add_argument("--pack", default="studio_inter", help="style pack (scripts/phase0b/style_packs.yaml)")
    ap.add_argument("--fallback", choices=["llm", "gap"], default="llm")
    a = ap.parse_args()

    run = run_folder(a.run.resolve())
    out = run / "composed"
    saved = json.loads((run / "slides.json").read_text(encoding="utf-8"))
    deck_xml = run / "deck" / "input.xml"
    theme = re.search(r"<Theme[^>]*/>", deck_xml.read_text(encoding="utf-8")).group() if deck_xml.exists() else ""

    measure = Measurer()
    try:
        report = replay(run / "slides.json", out, a.pack, measure)
    finally:
        measure.close()
    code_dir = out / f"src-{deck_name(run / 'slides.json')}"

    pptx, kinds = [], []
    for row, s in zip(report["per_slide"], saved):
        n = row["slide"]
        all_blocks = row["status"] == "ok" and all(c.endswith(":block") for c in row["components"])
        src = code_dir / f"slide-{n:02d}.xml"
        if not all_blocks and a.fallback == "llm" and s.get("xml"):
            src = out / "llm" / f"slide-{n:02d}.xml"
            src.parent.mkdir(parents=True, exist_ok=True)
            xml = s["xml"] if "<Theme" in s["xml"] else theme + "\n" + s["xml"]
            src.write_text(xml, encoding="utf-8")
        kinds.append("code" if src.parent == code_dir else "llm")
        res = _compile(src, out / "build" / f"slide-{n:02d}")
        if res.get("status") != "success":
            print(f"slide {n}: compile {res.get('status')} — left out", file=sys.stderr)
            continue
        pptx.append(out / "build" / f"slide-{n:02d}" / "presentation.pptx")

    merged = merge_pptx_files(pptx, out / "merged.pptx")
    final = out / "composed.pptx"
    embed(merged, final, {f: {k: FONTS_DIR / v for k, v in faces.items()} for f, faces in FONTS.items()})

    fits = [r.get("fit") or {} for r in report["per_slide"]]
    print(f"slides: {kinds.count('code')} code-drawn, {kinds.count('llm')} LLM fallback "
          f"({', '.join(str(i + 1) for i, k in enumerate(kinds) if k == 'llm') or 'none'})")
    print("smaller type on: " + (", ".join(f"{i + 1} (x{f['scale']})" for i, f in enumerate(fits)
                                            if f.get("scale", 1) < 1) or "none"))
    over = [str(i + 1) for i, f in enumerate(fits) if f.get("code")]
    if over:
        print("SLIDE_OVERFULL: " + ", ".join(over))
    print(f"composed deck: {final}")
    if (run / "deck" / "presentation.pptx").exists():
        print(f"LLM deck (same run): {run / 'deck' / 'presentation.pptx'}")


if __name__ == "__main__":
    main()
