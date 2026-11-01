"""Theme gallery: one slide re-skinned into every palette, the way the review screen's theme switch does it.

Free (no LLM). Takes a slide with its own <Theme> line (default: the gj-h1 golden H1 snapshot), runs
src.compiler.theme_swap.swap_theme for each palette in palettes.yaml, compiles (POM), renders
(LibreOffice -> PDF -> PNG) and writes a labelled contact sheet.

    python -m scripts.theme_gallery
    python -m scripts.theme_gallery --slide tests/fixtures/golden/gj-h1-deck/03-performance-trend.xml --only mbb-blue mbb-red

Output: <out>/<palette>.png, <out>/sheet.png (all themes), <out>/sheet-new.png (--highlight palettes only).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.agents.style_resolver import resolve_theme, theme_names  # noqa: E402
from src.compiler.theme_swap import swap_theme  # noqa: E402

_COMPILE = _ROOT / "src" / "node" / "compile-pom.js"
_SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.exe")
_DEFAULT_SLIDE = _ROOT / "tests" / "fixtures" / "golden" / "gj-h1-deck" / "02-h1-snapshot.xml"
_THEME_RE = re.compile(r"<Theme\b[^>]*/>")
_NEW = ["mbb-blue", "mbb-blue-dark", "perceptis", "perceptis-dark",
        "mbb-green", "mbb-green-dark", "mbb-red", "mbb-red-dark"]


def _render(xml: str, work: Path, name: str) -> Path:
    """Compile one slide's XML and render it to a PNG; returns the PNG path."""
    import fitz  # pymupdf

    src = work / f"{name}.xml"
    src.write_text(xml, encoding="utf-8")
    out = work / name
    subprocess.run(["node", str(_COMPILE), str(src), str(out)], check=True, capture_output=True, timeout=120)
    pptx = out / "presentation.pptx"
    subprocess.run([str(_SOFFICE), "--headless", "--convert-to", "pdf", "--outdir", str(out), str(pptx)],
                   check=True, capture_output=True, timeout=180)
    png = work / f"{name}.png"
    fitz.open(out / "presentation.pdf")[0].get_pixmap(matrix=fitz.Matrix(0.75, 0.75)).save(png)
    return png


def _sheet(pngs: dict[str, Path], dest: Path, cols: int) -> None:
    from PIL import Image, ImageDraw, ImageFont

    first = Image.open(next(iter(pngs.values())))
    w, h = first.size
    label_h = 34
    rows = -(-len(pngs) // cols)
    sheet = Image.new("RGB", (cols * (w + 16) + 16, rows * (h + label_h + 16) + 16), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arialbd.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, png) in enumerate(pngs.items()):
        x = 16 + (i % cols) * (w + 16)
        y = 16 + (i // cols) * (h + label_h + 16)
        draw.text((x, y), name, fill="black", font=font)
        sheet.paste(Image.open(png), (x, y + label_h))
    sheet.save(dest)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slide", type=Path, default=_DEFAULT_SLIDE)
    ap.add_argument("--only", nargs="*", help="palettes to draw (default: all)")
    ap.add_argument("--highlight", nargs="*", default=_NEW, help="palettes for sheet-new.png")
    ap.add_argument("--out", type=Path, default=_ROOT / "output" / "theme_gallery")
    args = ap.parse_args()

    raw = args.slide.read_text(encoding="utf-8")
    old_theme = _THEME_RE.search(raw).group(0)
    names = args.only or theme_names()
    args.out.mkdir(parents=True, exist_ok=True)

    pngs: dict[str, Path] = {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for name in names:
            theme = resolve_theme(name)
            swapped = swap_theme(raw, old_theme, theme["element"], theme["is_dark"]).xml
            try:
                png = _render(theme["element"] + "\n" + swapped, work, name)
            except subprocess.CalledProcessError as e:
                print(f"{name}: FAILED {e.stderr[-300:] if e.stderr else e}")
                continue
            dest = args.out / f"{name}.png"
            dest.write_bytes(png.read_bytes())
            pngs[name] = dest
            print(f"{name}: ok")

    _sheet(pngs, args.out / "sheet.png", cols=4)
    new = {n: p for n, p in pngs.items() if n in (args.highlight or [])}
    if new:
        _sheet(new, args.out / "sheet-new.png", cols=2)
    print(f"{len(pngs)}/{len(names)} rendered -> {args.out}")


if __name__ == "__main__":
    main()
