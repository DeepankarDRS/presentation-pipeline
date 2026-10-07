"""1a measure 4: blind side-by-side sheets (docs/derived-blocks-planning-2026-10-06.md §4.3).

    python -m scripts.node_test_sheet --nodes output/1a/1a --off output/1a/off --out output/1a/sheets
    python -m scripts.node_test_sheet --score output/1a/sheets      # after you fill marks.csv

Per slide the two renders (both arms' presentation.pdf, made by node_test_score) side by side,
left / right by a fixed seed, no labels, 4 slides per sheet (sheet-01.png ...). marks.csv has one
row per pair: write 1, 2 or = in `choice` and a reason (readability, fill, overlap, empty, designed).
key.json says which side is which; open it only after marking. --score: (nodes wins + ½ ties) / N, where a
node slide with no render (did not compile) counts as a loss in N without being shown (D12).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = "1a"
PER_SHEET = 4
W, H = 960, 540        # one slide image
GAP, LABEL = 24, 40


def png(pdf: Path, out: Path) -> Path:
    import pymupdf
    page = pymupdf.open(pdf)[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(W / page.rect.width, H / page.rect.height))
    pix.save(out)
    return out


def build(nodes: Path, off: Path, out: Path) -> int:
    from PIL import Image, ImageDraw
    from scripts.node_test_score import render_pdf

    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    pairs, lost = [], []
    for d in sorted(p for p in nodes.glob("*/slide-*") if p.is_dir()):
        o = off / d.parent.name / d.name
        a, b = render_pdf(d), render_pdf(o)
        if a and b:
            pairs.append((d.parent.name, int(d.name.split("-")[1]), a, b))
        elif b:   # D12: a node slide with no render (did not compile) is a loss for nodes, not left out
            lost.append({"pair": f"auto-{d.parent.name}-{d.name}", "case": d.parent.name,
                         "slide": int(d.name.split("-")[1]), "nodes_side": 0, "auto": "nodes slide did not render"})
    key, rows = [], []
    for i in range(0, len(pairs), PER_SHEET):
        chunk = pairs[i:i + PER_SHEET]
        sheet = Image.new("RGB", (2 * W + 3 * GAP, len(chunk) * (H + LABEL + GAP) + GAP), "white")
        draw = ImageDraw.Draw(sheet)
        for j, (case, n, pdf_nodes, pdf_off) in enumerate(chunk):
            nodes_left = rng.random() < 0.5
            left, right = (pdf_nodes, pdf_off) if nodes_left else (pdf_off, pdf_nodes)
            y = GAP + j * (H + LABEL + GAP)
            pair = f"{i // PER_SHEET + 1}.{j + 1}"
            draw.text((GAP, y + 8), f"pair {pair}:   1 (left)   |   2 (right)", fill="black")
            for k, pdf in enumerate((left, right)):
                img = Image.open(png(pdf, out / f"tmp-{k}.png")).convert("RGB")
                sheet.paste(img, (GAP + k * (W + GAP), y + LABEL))
                draw.rectangle([GAP + k * (W + GAP) - 1, y + LABEL - 1, GAP + k * (W + GAP) + W, y + LABEL + H], outline="#999999")
            key.append({"pair": pair, "case": case, "slide": n, "nodes_side": 1 if nodes_left else 2})
            rows.append({"pair": pair, "choice": "", "reason": ""})
        sheet.save(out / f"sheet-{i // PER_SHEET + 1:02d}.png")
    for t in out.glob("tmp-*.png"):
        t.unlink()
    (out / "key.json").write_text(json.dumps(key + lost, indent=1), encoding="utf-8")
    with (out / "marks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["pair", "choice", "reason"])
        w.writeheader()
        w.writerows(rows)
    return len(pairs) + len(lost)


def tally(folder: Path) -> dict:
    key = {k["pair"]: k for k in json.loads((folder / "key.json").read_text(encoding="utf-8"))}
    with (folder / "marks.csv").open(encoding="utf-8") as f:
        marks = [r for r in csv.DictReader(f) if r["choice"].strip()]
    wins = ties = 0
    for m in marks:
        c = m["choice"].strip()
        if c == "=":
            ties += 1
        elif c.isdigit() and int(c) == key[m["pair"]]["nodes_side"]:
            wins += 1
    auto = [k for k in key.values() if k.get("auto")]   # counted as off wins, never shown
    n = len(marks) + len(auto)
    return {"marked": len(marks), "auto_losses": len(auto), "of": len(key), "nodes_wins": wins, "ties": ties,
            "score": round((wins + ties / 2) / n, 3) if n else None, "pass": n > 0 and (wins + ties / 2) / n >= 0.6}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nodes", type=Path)
    ap.add_argument("--off", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "1a" / "sheets")
    ap.add_argument("--score", type=Path, help="tally marks.csv in this folder")
    a = ap.parse_args()
    if a.score:
        print(json.dumps(tally(a.score), indent=1))
        return
    n = build(a.nodes, a.off, a.out)
    print(f"{n} pairs, {(n + PER_SHEET - 1) // PER_SHEET} sheets -> {a.out} (fill marks.csv; key.json is the answer)")


if __name__ == "__main__":
    main()
