"""Bullet-list variant gallery, LLM-free: the proposal for the user's approval (no node yet, no API).

    python -m scripts.bullet_gallery                     # every variant, corporate-slate + graphite-dark
    python -m scripts.bullet_gallery --only native rows

Each variant is the hand-written XML its node would expand to, drawn on four cases (3 short points, 5 lead-ins with a
coloured phrase, 8 mixed points, a 360 px side panel beside a chart). One deck per variant and palette, through the
real steps: deck font, normalizer, theme, compile-pom.js (fit-grow), LibreOffice + Inter. Writes
docs/eval/bullet-node/gallery-<palette>.png and native-evidence.json (what each native variant really wrote in the .pptx).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.card_replay import render  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import compose, native, tables  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

OUT = ROOT / "output" / "bullet-gallery"
DOCS = ROOT / "docs" / "eval" / "bullet-node"
PALETTES = ("corporate-slate", "graphite-dark")
X = native.x

SHORT = ["Scale exact match", "Cut broad leakage", "Review bids weekly"]
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
PHRASE = ("Product C drags", "$negativeText")
CHART = {"component_id": "roas", "kind": "chart", "content_data": {
    "chart_title": "ROAS by campaign class", "chart_labels": ["Generic", "Category", "Brand", "Competitor"],
    "chart_values": ["0.29x", "0.80x", "0.99x", "0.15x"]}}
CASES = [("3 short points · full width", "Three moves decide the H2 return", SHORT, False),
         ("5 lead-ins, one phrase coloured · full width", "Recommendation ads win, Product C drags", LEADS, False),
         ("8 mixed points · full width", "Eight levers for the festive quarter", MIXED, False),
         ("5 lead-ins · 360 px side panel", "Generic search takes the most and returns little", LEADS, True)]


def runs(s: str) -> str:
    """The item's text, escaped, the highlight phrase in <Span color>."""
    p, c = PHRASE
    return f'<Span color="{c}">{X(p)}</Span>{X(s[len(p):])}' if s.startswith(p) else X(s)


def li(s: str) -> str:
    """One <Li>: every word kept; a split point's head bold (and coloured when it is the phrase)."""
    h, d = compose.split(s)
    if not d:
        return f"<Li>{runs(s)}</Li>"
    sep = s[len(h):len(s) - len(d)]
    return f"<Li><B>{runs(h)}</B>{X(sep)}{X(d)}</Li>"


def draw_native(items: list[str], side: bool, tag: str = "Ul", cols: int = 1) -> str:
    def one(part: list[str]) -> str:   # grow: the list's text box takes the whole box (native+ shares out its spare height)
        return f'<{tag} grow="1" fontSize="20" lineHeight="1.3" color="$textMain">{"".join(li(s) for s in part)}</{tag}>'
    if cols == 2 and not side:
        half = (len(items) + 1) // 2
        return (f'<HStack grow="1" gap="40" alignItems="stretch"><VStack w="1" grow="1" alignItems="stretch">{one(items[:half])}</VStack>'
                f'<VStack w="1" grow="1" alignItems="stretch">{one(items[half:])}</VStack></HStack>')
    return f'<VStack grow="1" alignItems="stretch">{one(items)}</VStack>'


def head_detail(s: str, hpx: int, dpx: int) -> str:
    h, d = compose.split(s)
    if not d:   # a point with no head: the head's size, regular, so a mixed list keeps one rhythm
        return f'<Text fontSize="{hpx}" color="$textMain">{X(h)}</Text>'
    c = PHRASE[1] if h == PHRASE[0] else "$textMain"
    return (f'<Text fontSize="{hpx}" bold="true" color="{c}">{X(h)}</Text>'
            f'<Text fontSize="{dpx}" color="$textMuted">{X(d)}</Text>')


def draw_rows(items: list[str], side: bool, lead: str = "dot") -> str:
    out = []
    for i, s in enumerate(items):
        rule = ' borderTop.color="$border" borderTop.width="1"' if i else ""
        if lead == "num":
            m = f'<VStack w="60"><Text id="cardn-pts-{i}" fontSize="22" bold="true" color="$accentText">{i + 1:02d}</Text></VStack>'
        elif lead == "icon":
            m = f'<Icon name="{ICONS[i]}" size="22" variant="square-filled" bgColor="$accentSoft" color="$accentText" />'
        else:
            m = '<VStack w="22" alignItems="center"><Shape shapeType="ellipse" w="10" h="10" fill.color="$accent" /></VStack>'
        out.append(f'<HStack id="card-pts-{i}" grow="1" gap="14" alignItems="center" padding.top="6" padding.bottom="6"{rule}>'
                   f'{m}<VStack w="1" grow="1" gap="2">{head_detail(s, 17, 16)}</VStack></HStack>')
    return f'<VStack gap="0" grow="1">{"".join(out)}</VStack>'


def draw_grid(items: list[str], side: bool) -> str:
    if len(items) > 6:   # requires count <= 6 -> native
        return draw_native(items, side)
    boxes = [f'<VStack id="card-pts-{i}" w="1" grow="1" gap="6" padding="18" justifyContent="center" backgroundColor="$surfaceAlt" '
             f'border.color="$border" border.width="1" borderRadius="8">{head_detail(s, 17, 16)}</VStack>' for i, s in enumerate(items)]
    k = 1 if side else tables.per_line(len(boxes))
    return ('<VStack gap="12" grow="1">' + "".join(f'<HStack gap="12" grow="1" alignItems="stretch">{"".join(boxes[j:j + k])}</HStack>'
                                                  for j in range(0, len(boxes), k)) + "</VStack>")


def draw_banded(items: list[str], side: bool) -> str:
    split = sum(bool(compose.split(s)[1]) for s in items)
    if len(items) > 6 or split < 0.75 * len(items):   # requires count <= 6, >= 75% split -> native
        return draw_native(items, side)
    boxes = []
    for i, s in enumerate(items):
        h, d = compose.split(s)
        boxes.append(f'<VStack id="card-pts-{i}" w="1" grow="1" gap="0" border.color="$border" border.width="1">'
                     f'<HStack padding="10" backgroundColor="$accent"><Text fontSize="16" bold="true" color="$onAccent">{X(h)}</Text></HStack>'
                     f'<VStack grow="1" padding="12" justifyContent="center" backgroundColor="$surfaceAlt">'
                     + (f'<Text fontSize="15" color="$textMain">{X(d)}</Text>' if d else "") + "</VStack></VStack>")
    k = 1 if side else tables.per_line(len(boxes))
    return ('<VStack gap="12" grow="1">' + "".join(f'<HStack gap="12" grow="1" alignItems="stretch">{"".join(boxes[j:j + k])}</HStack>'
                                                  for j in range(0, len(boxes), k)) + "</VStack>")


# name: (tag syntax, what it is, draw)
VARIANTS = {
    "native": ('<Ul ref="pts"/>', "POM's list, no post-edit",
               lambda it, s: draw_native(it, s)),
    "native+": ('<Ul ref="pts"/> (if you want it as the default)', "the same list; pptx-post adds marker colour + item spacing",
                lambda it, s: draw_native(it, s)),
    "native numbered": ('<Ul ref="pts" variant="native numbered"/>', "a real auto-numbered <Ol>",
                        lambda it, s: draw_native(it, s, "Ol")),
    "native cols": ('<Ul ref="pts" cols="2"/>', "two real lists side by side; a side panel stays one column",
                    lambda it, s: draw_native(it, s, cols=2)),
    "rows": ('<Ul ref="pts" variant="rows"/>', "ruled rows: dot, bold head over detail",
             lambda it, s: draw_rows(it, s)),
    "rows numbered": ('<Ul ref="pts" variant="rows numbered"/>', "ruled rows led by 01 02 03",
                      lambda it, s: draw_rows(it, s, "num")),
    "rows icons": ('<Ul ref="pts" variant="rows" icons="target,scissors,..."/>', "ruled rows led by an icon per point",
                   lambda it, s: draw_rows(it, s, "icon")),
    "grid": ('<Ul ref="pts" variant="grid"/>', "each point its own box; > 6 points falls back to native",
             draw_grid),
    "banded": ('<Ul ref="pts" variant="banded"/>', "head in a solid band; needs >= 75% split, <= 6 points, else native",
               draw_banded),
}


def slide(title: str, body: str, side: bool) -> str:
    if side:
        chart = native.chart(CHART, {"h": "max"}, {"chart_tokens": ["$accent"]})
        body = (f'<HStack grow="1" gap="28" alignItems="stretch"><VStack w="1" grow="1" alignItems="stretch">{chart}</VStack>'
                f'<VStack w="360" alignItems="stretch">{body}</VStack></HStack>')
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
            f'<Text fontSize="32" bold="true" color="$textMain" lineHeight="1.15">{X(title)}</Text>'
            f'<VStack grow="1" gap="16" alignItems="stretch">{body}</VStack></VStack></Slide>')


def plus(pptx: Path, accent: str) -> None:
    """native+ (what pptx-post.js would do): each list keeps its paragraphs; the marker takes the accent and the spare
    height of the text box goes between the items. Height estimated with Inter; the node would use fit-grow's layout."""
    from PIL import ImageFont
    font = ROOT / "src" / "node" / "fonts"
    regular = next(font.glob("Inter*.ttf"))

    def edit(xml: str) -> str:
        def shape(m: re.Match) -> str:
            sp = m.group(0)
            paras = re.findall(r"<a:p>.*?</a:p>", sp, re.S)
            if not any("<a:buChar" in p or "<a:buAutoNum" in p for p in paras):
                return sp
            ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', sp)
            w, h = int(ext.group(1)) / 9525 - 36, int(ext.group(2)) / 9525
            used = 0.0
            for p in paras:
                px = int(re.search(r'sz="(\d+)"', p).group(1)) / 75
                pct = int(re.search(r'spcPct val="(\d+)"', p).group(1)) / 100000
                f = ImageFont.truetype(str(regular), max(1, round(px)))
                line, lines = "", 1
                for word in " ".join(re.findall(r"<a:t[^>]*>([^<]*)</a:t>", p)).split():
                    if f.getlength(f"{line} {word}".strip()) * 1.03 > w:
                        line, lines = word, lines + 1
                    else:
                        line = f"{line} {word}".strip()
                used += lines * px * 1.21 * pct
            gap = min(max(h - used, 0) / max(len(paras) - 1, 1), 1.5 * px) * 75   # px -> 1/100 pt
            sp = sp.replace('anchor="t"', 'anchor="ctr"', 1)   # what spacing cannot fill stays even above and below
            for i, p in enumerate(paras):
                q = p
                if i and gap >= 100:
                    q = q.replace("</a:lnSpc>", f'</a:lnSpc><a:spcBef><a:spcPts val="{round(gap)}"/></a:spcBef>', 1)
                q = q.replace("<a:buSzPct", f'<a:buClr><a:srgbClr val="{accent}"/></a:buClr><a:buSzPct', 1)
                sp = sp.replace(p, q, 1)
            return sp
        return re.sub(r"<p:sp>.*?</p:sp>", shape, xml, flags=re.S)

    rewrite(pptx, edit)


def rewrite(pptx: Path, edit) -> None:
    tmp = pptx.with_suffix(".tmp")
    with zipfile.ZipFile(pptx) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", it.filename):
                data = edit(data.decode("utf-8")).encode("utf-8")
            zo.writestr(it, data)
    tmp.replace(pptx)


def evidence(pptx: Path) -> list[dict]:
    """Per slide, what the .pptx holds: the shapes that are real lists, their markers, one bold + one coloured run."""
    out = []
    z = zipfile.ZipFile(pptx)
    names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.findall(r"\d+", n)[0]))
    for n in names:
        x = z.read(n).decode("utf-8")
        lists = [s for s in re.findall(r"<p:sp>.*?</p:sp>", x, re.S) if "<a:buChar" in s or "<a:buAutoNum" in s]
        out.append({"list_shapes": len(lists), "buChar": x.count("<a:buChar"), "buAutoNum": x.count("<a:buAutoNum"),
                    "buClr": x.count("<a:buClr"), "spcBef": x.count("<a:spcBef"), "bold_runs": sum(s.count('b="1"') for s in lists),
                    "sizes_pt": sorted({int(v) / 100 for s in lists for v in re.findall(r'\bsz="(\d+)"', s)})})
    return out


def build(name: str, pal: str, out: Path) -> tuple[Path | None, dict]:
    _, _, draw = VARIANTS[name]
    theme = resolve_theme(pal)["element"]
    d = out / f"{re.sub(r'[^a-z0-9]+', '_', name)}-{pal}"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    xml = "".join(compose.inner_ids(slide(t, draw(items, side), side)) for _, t, items, side in CASES)
    norm = normalize_xml(deck_font(xml))
    (d / "in.xml").write_text(ensure_single_theme(norm["cleaned_xml"], theme), encoding="utf-8")
    p = subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    (d / "compile.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    pptx = d / "presentation.pptx"
    if not pptx.exists():
        print(f"{name} {pal}: NO PPTX\n{p.stdout[-400:]}", flush=True)
        return None, {}
    if name == "native+":
        plus(pptx, re.search(r'\baccent="(\w+)"', theme).group(1))
    if name == "native numbered":   # POM writes startAt="1" on every paragraph: LibreOffice draws 1. 1. 1.; 1 is the default
        rewrite(pptx, lambda x: x.replace(' startAt="1"', ""))
    res = json.loads((d / "compile-result.json").read_text(encoding="utf-8"))
    info = {"slides": evidence(pptx), "warnings": [w.get("code") for w in res.get("warnings") or []], "fitGrow": res.get("fitGrow") or []}
    pdf = render(d)
    print(f"{name} {pal}: {'ok' if pdf else 'NO RENDER'} {sorted(set(info['warnings']))}", flush=True)
    return pdf, info


def sheet(pal: str, done: dict[str, Path | None], path: Path) -> None:
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    font = next((ROOT / "src" / "node" / "fonts").glob("Inter*.ttf"))
    big, small = ImageFont.truetype(str(font), 20), ImageFont.truetype(str(font), 15)
    w, h, gap, head = 560, 315, 12, 34
    img = Image.new("RGB", (4 * (w + gap) + gap, 34 + len(done) * (h + head + gap) + gap), "white")
    dr = ImageDraw.Draw(img)
    for k, (label, *_) in enumerate(CASES):
        dr.text((gap + k * (w + gap), 8), label, fill="#333333", font=small)
    for r, (name, pdf) in enumerate(done.items()):
        y = 34 + r * (h + head + gap)
        tag, what, _ = VARIANTS[name]
        dr.text((gap, y + 6), f"{r + 1}. {name}", fill="black", font=big)
        dr.text((gap + 210, y + 9), f"{tag}   {what}", fill="#555555", font=small)
        for k in range(4):
            x = gap + k * (w + gap)
            if pdf:
                doc = pymupdf.open(pdf)
                if k < doc.page_count:
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
        sheet(pal, done, DOCS / f"gallery-{pal}.png")
        print(DOCS / f"gallery-{pal}.png", flush=True)
    (DOCS / "native-evidence.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
