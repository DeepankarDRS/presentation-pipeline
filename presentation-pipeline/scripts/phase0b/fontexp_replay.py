"""Replay R1's saved LLM slides through the current compiler and score the LibreOffice render (step 0.3).

    python -m scripts.phase0b.fontexp_replay [--src output/fontexp2] [--out output/fontexp3]

Takes <src>/inter-<deck>/slide-NN.xml (the saved LLM slides with fontFamily Inter added, derived-nodes-design
§13 R1 variant c), compiles each deck with fit-grow on (render_check), converts every slide with LibreOffice
and runs scripts/phase0b/fontcheck.py: broken words, blank heading lines, KPI numbers past their box. The R1
numbers for the same slides (variant c, before the shrink guard): broken words 7. Needs LibreOffice and pymupdf
(`uv pip install pymupdf`); the inputs are local (output/ is gitignored).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.exe")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, default=ROOT / "output" / "fontexp2")
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "fontexp3")
    a = ap.parse_args()
    soffice = shutil.which("soffice") or str(SOFFICE)
    shutil.rmtree(a.out, ignore_errors=True)
    (a.out / "pdf").mkdir(parents=True)
    for inter in sorted(a.src.glob("inter-*")):
        deck = inter.name[len("inter-"):]
        shutil.copytree(a.src / f"src-{deck}", a.out / f"src-{deck}")
        subprocess.run([sys.executable, "-m", "scripts.render_check", "--in", str(inter), "--out", str(a.out / f"d-{deck}")],
                       cwd=ROOT, capture_output=True, check=False)
        for slide in sorted((a.out / f"d-{deck}").glob("slide-*")):
            pptx = slide / "presentation.pptx"
            if not pptx.exists():
                continue
            tmp = a.out / "pdf" / f"tmp-d-{deck}-{slide.name}.pptx"
            shutil.copy2(pptx, tmp)
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(a.out / "pdf"), str(tmp)],
                           capture_output=True, check=False)
            tmp.with_suffix(".pdf").replace(a.out / "pdf" / f"d-{deck}-{slide.name}.pdf")
            tmp.unlink()
    result = subprocess.run([sys.executable, "scripts/phase0b/fontcheck.py", str(a.out), "d"], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8")
    (a.out / "fontcheck.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout.splitlines()[0] if result.stdout else result.stderr)


if __name__ == "__main__":
    main()
