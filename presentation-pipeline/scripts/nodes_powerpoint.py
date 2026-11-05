"""The look of the composition-node slides in PowerPoint, free: no LLM calls (docs/eval/nodes-paid/README.md).

    python -m scripts.nodes_powerpoint

LibreOffice drew neither the black table lines nor the stripes PowerPoint showed, so this runs on the test PC. It
recompiles slides it already saved with today's code and exports them through PowerPoint, one at a time:
- the same-plan check's slides with a table, both routes, as a blind sheet (B from the rerun nodes-b6 where it exists);
- every slide of each saved full-deck run (output/eval/nodes-deck-*), route B only, under deck/.
Writes output/composition-paid/nodes-ppt/ and nodes-ppt.zip to email back: sheets/ (fill marks.csv; key.json: the
'nodes' side is B), deck/, slides/ with each slide's pptx, checks.json (what is left in each slide's table XML).
"""

from __future__ import annotations

import csv
import json
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import composition_paid as CP  # noqa: E402
from scripts.kpi_replay import compile_slide  # noqa: E402
from scripts.node_test_sheet import GAP, H, LABEL, PER_SHEET, W  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.screenshot import render_screenshots  # noqa: E402

LABEL_NAME = "nodes-ppt"
SEED = "nodes-ppt"
THEME = re.compile(r"<Theme\b[^>]*/>")


def table_checks(pptx: Path) -> dict:
    """What PowerPoint would draw on its own in a slide's tables: 0 everywhere after the fixes of b2ed3c5."""
    with zipfile.ZipFile(pptx) as z:
        x = "".join(z.read(n).decode("utf-8") for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
    return {"tables": x.count("<a:tbl>"), "zero_lines_solid": len(re.findall(r'<a:ln[LRTB]? w="0"><a:solidFill', x)),
            "default_style": x.count("5C22544A"), "band_rows": x.count('bandRow="1"')}


def draw(arm: str, xml: str, theme: str, dest: Path, checks: dict) -> Path | None:
    """One slide: compile it, export it through PowerPoint. The PNG, or None with the reason printed."""
    CP.set_arm(arm)
    done = compile_slide(deck_font(xml), theme, dest)
    pptx = dest / "presentation.pptx"
    if not done["res"].get("success", pptx.exists()) or not pptx.exists():
        print(f"  NOT COMPILED {dest}: {str(done['res'].get('diagnostics'))[:200]}", flush=True)
        return None
    checks[str(dest.relative_to(dest.parents[2]))] = table_checks(pptx)
    res = render_screenshots(str(pptx), str(dest))
    if not res.ok or not res.slides:
        print(f"  NOT RENDERED {dest}: {res.error}", flush=True)
        return None
    return Path(res.slides[0].png_path)


def same_plan(out: Path, checks: dict) -> list[tuple[str, Path, Path]]:
    """The same-plan check's table slides on both routes."""
    base, rerun = CP.OUT / "nodes-paid", CP.OUT / "nodes-b6"
    pairs = []
    for it in CP.items():
        case = it["name"] + "-r1"
        a = base / "A" / case / "final.xml"
        b = rerun / "B" / case / "final.xml"
        b = b if b.exists() else base / "B" / case / "final.xml"
        if not a.exists() or not b.exists():
            print(f"  no saved slide for {case}: skipped", flush=True)
            continue
        xa, xb = a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")
        if "<Table" not in xa + xb:
            continue
        print(f"same plan {case}", flush=True)
        theme = CP.resolve_theme(it["theme"])["element"]
        pa = draw("A", xa, theme, out / "slides" / "A" / case, checks)
        pb = draw("B", xb, theme, out / "slides" / "B" / case, checks)
        if pa and pb:
            pairs.append((case, pb, pa))
    return pairs


def decks(out: Path, checks: dict) -> int:
    """Every slide of the saved full-deck runs, route B, one PNG each under deck/."""
    n = 0
    for run in sorted((ROOT / "output" / "eval").glob("nodes-deck-*")):
        for f in sorted((run / "slides").glob("*/slide-*/input.xml")):
            xml = f.read_text(encoding="utf-8")
            m = THEME.search(xml)
            if not m:
                print(f"  no theme in {f}: skipped", flush=True)
                continue
            name = f"{f.parent.parent.name}-{f.parent.name}"
            print(f"deck {name}", flush=True)
            png = draw("B", THEME.sub("", xml), m.group(0), out / "slides" / "deck" / name, checks)
            if png:
                (out / "deck").mkdir(exist_ok=True)
                shutil.copy2(png, out / "deck" / f"{name}.png")
                n += 1
    return n


def sheets(pairs: list[tuple[str, Path, Path]], out: Path) -> None:
    """Blind side-by-side sheets, the files scripts.node_test_sheet --score reads."""
    from PIL import Image, ImageDraw
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    key, rows = [], []
    for i in range(0, len(pairs), PER_SHEET):
        chunk = pairs[i:i + PER_SHEET]
        sheet = Image.new("RGB", (2 * W + 3 * GAP, len(chunk) * (H + LABEL + GAP) + GAP), "white")
        ink = ImageDraw.Draw(sheet)
        for j, (case, nodes, off) in enumerate(chunk):
            nodes_left = rng.random() < 0.5
            y = GAP + j * (H + LABEL + GAP)
            pair = f"{i // PER_SHEET + 1}.{j + 1}"
            ink.text((GAP, y + 8), f"pair {pair}:   1 (left)   |   2 (right)", fill="black")
            for k, png in enumerate((nodes, off) if nodes_left else (off, nodes)):
                with Image.open(png) as img:
                    sheet.paste(img.convert("RGB").resize((W, H)), (GAP + k * (W + GAP), y + LABEL))
                ink.rectangle([GAP + k * (W + GAP) - 1, y + LABEL - 1, GAP + k * (W + GAP) + W, y + LABEL + H], outline="#999999")
            key.append({"pair": pair, "case": case, "slide": 0, "nodes_side": 1 if nodes_left else 2})
            rows.append({"pair": pair, "choice": "", "reason": ""})
        sheet.save(out / f"sheet-{i // PER_SHEET + 1:02d}.png")
    (out / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    with (out / "marks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["pair", "choice", "reason"])
        w.writeheader()
        w.writerows(rows)


def bundle(out: Path) -> Path:
    """Sheets, deck images, checks and each slide's pptx; not the working files."""
    z = out.parent / f"{out.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in out.rglob("*"):
            if p.is_file() and (p.suffix == ".pptx" or "slides" not in p.relative_to(out).parts):
                f.write(p, p.relative_to(out.parent))
    return z


def main() -> int:
    out = CP.OUT / LABEL_NAME
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    checks: dict = {}
    pairs = same_plan(out, checks)
    sheets(pairs, out / "sheets")
    n = decks(out, checks)
    (out / "checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    left = {k: sum(c[k] for c in checks.values()) for k in ("tables", "zero_lines_solid", "default_style", "band_rows")}
    print(f"pairs on the blind sheet: {len(pairs)}; deck slides: {n}; in the tables: {left}")
    if not pairs and not n:
        print("Nothing was drawn: see the lines above (no saved slides, or PowerPoint did not export).")
        return 1
    print(f"EMAIL THIS FILE: {bundle(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
