"""Import an emailed eval bundle on the build device.

    python -m scripts.eval_import path/to/<label>-<ts>.zip

1. extracts it to output/eval/<label>-<ts>/ (gitignored)
2. renders every slide .pptx with LibreOffice → renders_lo/ (same renderer for every
   label, so renders are comparable; skipped if soffice is not found)
3. writes docs/eval/<label>/: summary.md, results.json and ≤15 review PNGs
   (failed slides first, then lowest card fill; PowerPoint render preferred)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PIPELINE_ROOT))

from scripts.eval_run import _slide_fill  # noqa: E402

_SOFFICE_DEFAULT = Path("C:/Program Files/LibreOffice/program/soffice.exe")


def _soffice() -> str | None:
    found = os.environ.get("SOFFICE") or shutil.which("soffice")
    if found:
        return found
    return str(_SOFFICE_DEFAULT) if _SOFFICE_DEFAULT.exists() else None


def render_libreoffice(eval_dir: Path) -> int:
    soffice = _soffice()
    if not soffice:
        print("LibreOffice not found (set SOFFICE) — skipping renders")
        return 0
    count = 0
    for pptx in sorted(eval_dir.glob("slides/*/slide-*/presentation.pptx")):
        out = eval_dir / "renders_lo" / pptx.parent.parent.name
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run([soffice, "--headless", "--convert-to", "png", "--outdir", str(pptx.parent), str(pptx)],
                       capture_output=True, timeout=180)
        png = pptx.with_suffix(".png")
        if png.exists():
            png.replace(out / f"{pptx.parent.name}.png")
            count += 1
    return count


def pick_reviews(results: dict, limit: int = 15) -> list[tuple[str, int]]:
    """(case folder, slide index): failed slides first, then lowest card fill."""
    slides = [(f"{c['name']}__r{c['repeat']}", s) for c in results["cases"] for s in c["slides"]]
    slides.sort(key=lambda cs: (cs[1]["compiled"], _slide_fill(cs[1])))
    return [(case, s["index"]) for case, s in slides[:limit]]


def import_bundle(zip_path: Path, docs_root: Path, out_root: Path) -> Path:
    with zipfile.ZipFile(zip_path) as z:
        top = z.namelist()[0].split("/")[0]
        z.extractall(out_root)
    eval_dir = out_root / top
    results = json.loads((eval_dir / "results.json").read_text(encoding="utf-8"))
    print(f"rendered {render_libreoffice(eval_dir)} slide(s) with LibreOffice")

    dest = docs_root / results["label"]
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "renders").mkdir(parents=True)
    shutil.copy2(eval_dir / "results.json", dest / "results.json")
    review = ["", "## Review renders", ""]
    for case, idx in pick_reviews(results):
        for png in (eval_dir / "renders" / case / f"slide-{idx}.png", eval_dir / "renders_lo" / case / f"slide-{idx}.png"):
            if png.exists():
                name = f"{case}__slide-{idx}.png"
                shutil.copy2(png, dest / "renders" / name)
                review.append(f"![{case} slide {idx}](renders/{name})")
                break
    summary = (eval_dir / "summary.md").read_text(encoding="utf-8")
    (dest / "summary.md").write_text(summary + "\n".join(review) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an eval bundle into docs/eval/<label>/")
    parser.add_argument("zip", type=Path)
    args = parser.parse_args(argv)
    dest = import_bundle(args.zip, _PIPELINE_ROOT / "docs" / "eval", _PIPELINE_ROOT / "output" / "eval")
    print(f"wrote {dest / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
