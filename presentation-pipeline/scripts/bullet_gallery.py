"""Bullet-list node gallery, LLM-free: every approved variant drawn from real tags (bullets.py, POM_NODES=bullet_list).

    python -m scripts.bullet_gallery                     # every variant, corporate-slate + graphite-dark
    python -m scripts.bullet_gallery --only native rows

Five cases: 3 short points, 5 lead-ins with a coloured phrase, 6 short points (the automatic split), 8 mixed points, a
360 px side panel beside a chart. One deck per variant and palette, through the real steps: composed.expand, deck font,
normalizer, theme, compile-pom.js (fit-grow, pptx-post), LibreOffice + Inter. Writes docs/eval/bullet-node/gallery-<palette>.png
and native-evidence.json (what each variant really wrote in the .pptx).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_NODES"] = "bullet_list"

from scripts.card_replay import render  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import composed, native  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

OUT = ROOT / "output" / "bullet-gallery"
DOCS = ROOT / "docs" / "eval" / "bullet-node"
PALETTES = ("corporate-slate", "graphite-dark")
X = native.x

SHORT3 = ["Scale exact match", "Cut broad leakage", "Review bids weekly"]
SHORT6 = ["Scale exact match", "Cut broad leakage", "Review bids weekly", "Test category tiles", "Cap home banners", "Refill offers monthly"]
LEADS = ["Recommendation ads: 11.3x ROAS at a third of Search spend, but few new buyers",
         "Product A is the star: 8.0x ROAS at 12.5% ACOS, Product B close behind at 6.9x",
         "Product C drags: 4.3x ROAS and 23% ACOS, CPM ₹470 against ₹332",
         "Generic keywords — 19.3% new-to-brand, keep them despite lower ROAS",
         "Festive budget: move ₹12L from display to exact match before October"]
MIXED = ["Quick commerce carried H1 growth and now brings 41% of new buyers across the top eight cities",
         "Scale exact match", "Competitor conquesting returned 0.15x: stop it until the new creative is live",
         "Weekly negative-keyword loop", "Home banners cost twice the category tiles and returned 0.4x in the same weeks",
         "Retention: repeat buyers are 41% of revenue, so refill offers go monthly",
         "Test category tiles in Hyderabad", "Separate the visibility budget from performance so ROAS targets stay honest"]
ICONS = ["target", "scissors", "wallet", "truck", "calendar", "users", "trending-up", "search"]
MARK = '<Highlight phrase="Product C drags" color="bad"/>'
CHART = {"component_id": "roas", "kind": "chart", "content_data": {
    "chart_title": "ROAS by campaign class", "chart_labels": ["Generic", "Category", "Brand", "Competitor"],
    "chart_values": ["0.29x", "0.80x", "0.99x", "0.15x"]}}
# (label, slide title, points, side panel, highlights)
CASES = [("3 short points", "Three moves decide the H2 return", SHORT3, False, ""),
         ("5 lead-ins, one phrase coloured", "Recommendation ads win, Product C drags", LEADS, False, MARK),
         ("6 short points (automatic split)", "Six moves for the festive quarter", SHORT6, False, ""),
         ("8 mixed points", "Eight levers for the festive quarter", MIXED, False, ""),
         ("5 lead-ins, 360 px side panel", "Generic search takes the most and returns little", LEADS, True, MARK)]
# name: (the tag's attributes, what it is)
VARIANTS = {"native": ("", "a real editable list; the default and the fallback"),
            "native numbered": (' variant="native numbered"', "a real auto-numbered list"),
            "rows": (' variant="rows"', "ruled rows: dot, bold head over detail"),
            "rows numbered": (' variant="rows numbered"', "ruled rows led by 01 02 03"),
            "rows icons": (' variant="rows" icons="{icons}"', "ruled rows led by an icon per point")}


def slide(title: str, tag: str, side: bool) -> str:
    body = tag
    if side:
        chart = native.chart(CHART, {"h": "max"}, {"chart_tokens": ["$accent"]})
        body = (f'<HStack grow="1" gap="28" alignItems="stretch"><VStack w="1" grow="1" alignItems="stretch">{chart}</VStack>'
                f'<VStack w="360" alignItems="stretch">{tag}</VStack></HStack>')
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
            f'<Text fontSize="32" bold="true" color="$textMain" lineHeight="1.15">{X(title)}</Text>'
            f'<VStack grow="1" gap="16" alignItems="stretch">{body}</VStack></VStack></Slide>')


def evidence(pptx: Path) -> list[dict]:
    """Per slide, what the .pptx holds: the shapes that are real lists, their markers, the sizes."""
    out = []
    z = zipfile.ZipFile(pptx)
    names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.findall(r"\d+", n)[0]))
    for n in names:
        x = z.read(n).decode("utf-8")
        lists = [s for s in re.findall(r"<p:sp>.*?</p:sp>", x, re.S) if "<a:buChar" in s or "<a:buAutoNum" in s]
        out.append({"list_shapes": len(lists), "buChar": x.count("<a:buChar"), "buAutoNum": x.count("<a:buAutoNum"),
                    "buClr": x.count("<a:buClr"), "spcBef": x.count("<a:spcBef"),
                    "sizes_px": sorted({round(int(v) / 75) for v in re.findall(r'\bsz="(\d+)"', x)})})
    return out


def build(name: str, pal: str, out: Path) -> tuple[Path | None, dict]:
    attrs = VARIANTS[name][0]
    theme = resolve_theme(pal)["element"]
    d = out / f"{re.sub(r'[^a-z0-9]+', '_', name)}-{pal}"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    slides, issues = [], []
    for _, title, pts, side, marks in CASES:
        comp = {"component_id": "pts", "kind": "bullet_list", "content_data": {"bullets": pts}}
        a = attrs.replace("{icons}", ",".join(ICONS[:len(pts)]))
        r = composed.expand(slide(title, f'<Ul ref="pts"{a} grow="1">{marks}</Ul>', side), {"components": [comp]})
        issues += [i["code"] for i in r["issues"]]
        slides.append(r["xml"])
    norm = normalize_xml(deck_font("".join(slides)))
    (d / "in.xml").write_text(ensure_single_theme(norm["cleaned_xml"], theme), encoding="utf-8")
    p = subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    (d / "compile.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    pptx = d / "presentation.pptx"
    if not pptx.exists():
        print(f"{name} {pal}: NO PPTX\n{p.stdout[-400:]}", flush=True)
        return None, {}
    res = json.loads((d / "compile-result.json").read_text(encoding="utf-8"))
    info = {"slides": evidence(pptx), "node_issues": issues, "warnings": [w.get("code") for w in res.get("warnings") or []],
            "fitGrow": res.get("fitGrow") or []}
    pdf = render(d)
    print(f"{name} {pal}: {'ok' if pdf else 'NO RENDER'} {issues} {sorted(set(info['warnings']))}", flush=True)
    return pdf, info


def sheet(done: dict[str, Path | None], path: Path) -> None:
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    font = ROOT / "src" / "node" / "fonts" / "Inter-Regular.ttf"
    big, small = ImageFont.truetype(str(font), 20), ImageFont.truetype(str(font), 15)
    w, h, gap, head, cols = 480, 270, 12, 34, len(CASES)
    img = Image.new("RGB", (cols * (w + gap) + gap, 34 + len(done) * (h + head + gap) + gap), "white")
    dr = ImageDraw.Draw(img)
    for k, c in enumerate(CASES):
        dr.text((gap + k * (w + gap), 8), c[0], fill="#333333", font=small)
    for r, (name, pdf) in enumerate(done.items()):
        y = 34 + r * (h + head + gap)
        attrs, what = VARIANTS[name]
        dr.text((gap, y + 6), f"{r + 1}. {name}", fill="black", font=big)
        dr.text((gap + 230, y + 9), f'<Ul ref="pts"{attrs.replace("{icons}", "...")}/>   {what}', fill="#555555", font=small)
        doc = pymupdf.open(pdf) if pdf else None
        for k in range(cols):
            x = gap + k * (w + gap)
            if doc and k < doc.page_count:
                page = doc[k]
                pix = page.get_pixmap(matrix=pymupdf.Matrix(w / page.rect.width, h / page.rect.height))
                img.paste(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), (x, y + head))
            dr.rectangle([x - 1, y + head - 1, x + w, y + head + h], outline="#999999")
    img.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", default=list(VARIANTS), choices=list(VARIANTS))
    ap.add_argument("--palettes", nargs="*", default=list(PALETTES))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    DOCS.mkdir(parents=True, exist_ok=True)
    log = {}
    for pal in args.palettes:
        done = {}
        for name in args.only:
            done[name], log[f"{name}-{pal}"] = build(name, pal, args.out)
        sheet(done, DOCS / f"gallery-{pal}.png")
        print(DOCS / f"gallery-{pal}.png", flush=True)
    (DOCS / "native-evidence.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
