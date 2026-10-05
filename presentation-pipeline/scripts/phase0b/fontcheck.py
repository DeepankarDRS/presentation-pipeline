"""Font experiment (derived-nodes-design §10g): score LibreOffice renders, not estimates.

    python scripts/phase0b/fontcheck.py output/fontexp [a b c]

Expects <root>/src-<deck>/slide-NN.xml, <root>/<variant>-<deck>/slide-NN/ (render_check output)
and <root>/pdf/<variant>-<deck>-slide-NN.pdf (soffice --convert-to pdf of each presentation.pptx).

broken  : a slide word drawn split over two lines (PDF word + next-line word = one slide word)
headings: reserveWrap headings (Text gaining minH in fitted.xml) -> reserved vs drawn lines
kpi     : KPI numbers (pptx text >= 30px, <= 12 chars, a digit) -> drawn lines, px past the box
"""
import html, json, re, sys
from pathlib import Path
import pymupdf, zipfile
sys.path.insert(0, ".")
from scripts.eval_metrics import _shapes

ROOT = Path(sys.argv[1])
VARIANTS = sys.argv[2:] or ["a", "b"]  # run folders <variant>-<deck>
DECKS = sorted(p.name[4:] for p in ROOT.glob("src-*"))  # source XML folders src-<deck>
EDGE = "\"'“”‘’,;:()[]!?"


def norm(w):
    return w.strip(EDGE).lower()


def texts(xml):
    """(attrs, text) for every <Text>, text = concatenated runs, entity-decoded."""
    out = []
    for m in re.finditer(r"<Text\b([^>]*?)(?:/>|>(.*?)</Text>)", xml, re.S):
        attrs, body = m.group(1), m.group(2) or ""
        out.append((attrs, html.unescape(re.sub(r"<[^>]+>", "", body)).strip()))
    return out


def attr(attrs, name):
    m = re.search(rf'\b{re.escape(name)}="([^"]*)"', attrs)
    return m.group(1) if m else None


def slide_words(xml):
    body = re.sub(r"<Theme\b[^>]*/>", "", xml)
    raw = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r'[\w.:-]+="[^"]*"', " ", body)))
    raw += " " + " ".join(html.unescape(v) for v in re.findall(r'\b(?:text|value|label|title)="([^"]*)"', body))
    return {norm(w) for w in raw.split() if norm(w)}


def pdf_words(pdf):
    page = pymupdf.open(pdf)[0]
    return page.get_text("words")  # x0,y0,x1,y1,word,block,line,wno


def overlaps(words):
    """Word pairs from different lines whose boxes overlap by > 30% of the smaller box: text
    drawn over other text (a squashed or over-full block)."""
    hits = []
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            if (a[5], a[6]) == (b[5], b[6]) or not a[4].strip() or not b[4].strip():
                continue
            w = min(a[2], b[2]) - max(a[0], b[0])
            h = min(a[3], b[3]) - max(a[1], b[1])
            if w <= 0 or h <= 0:
                continue
            small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1
            if w * h > 0.3 * small:
                hits.append(f"{a[4]}~{b[4]}")
    return hits


def broken(words, vocab):
    hits = []
    for a, b in zip(words, words[1:]):
        # the next word must start at least half a line lower: a fallback glyph (₹ in a font
        # without it) is split off by the PDF text layer but sits on the same line
        if (a[5], a[6]) == (b[5], b[6]) or b[1] < a[1] + 0.5 * (a[3] - a[1]):
            continue
        ta, tb = norm(a[4]), norm(b[4])
        joined = norm(a[4] + b[4])
        # a break after a hyphen, dash or slash is a normal line break; so is a lone bracket
        if joined in vocab and ta and ta not in vocab and not a[4].endswith(("-", "—", "–", "/")):
            hits.append(f"{a[4]}|{b[4]}")
    return hits


def drawn_lines(words, text):
    """Distinct lines the text's words occupy in the PDF (first sequential match)."""
    target = [norm(w) for w in text.split() if norm(w)]
    toks = [norm(w[4]) for w in words]
    n = len(target)
    for i in range(len(toks) - n + 1):
        if toks[i:i + n] == target:
            ys = sorted({round(w[1]) for w in words[i:i + n]})
            lines = 1
            for p, q in zip(ys, ys[1:]):
                lines += q - p > 4
            return lines
    return None


def kpi_boxes(pptx, pdf):
    """KPI numbers = text shapes >= 30px with a digit and <= 12 chars: drawn lines and drawn width vs box."""
    with zipfile.ZipFile(pptx) as z:
        shapes = _shapes(z.read("ppt/slides/slide1.xml"))
    page = pymupdf.open(pdf)[0]
    k = page.rect.width / 1280
    words = page.get_text("words")
    out = []
    for sh in shapes:
        px = sh["max_font"] * 4 / 3
        if sh["kind"] != "sp" or px < 30 or len(sh["text"]) > 12 or not re.search(r"\d", sh["text"]):
            continue
        x0, y0, x1, y1 = (sh["x"] * k, sh["y"] * k, (sh["x"] + sh["w"]) * k, (sh["y"] + sh["h"]) * k)
        inside = [w for w in words if x0 - 2 <= (w[0] + w[2]) / 2 <= x1 + 2 and y0 - 4 <= (w[1] + w[3]) / 2 <= y1 + 4
                  and (w[3] - w[1]) >= 0.45 * px * k]  # the number's own size, not a note line beside it
        ys = sorted({round(w[3]) for w in inside})  # baselines: a smaller unit span ("Cr") sits higher
        lines = 1 + sum(q - p > 4 for p, q in zip(ys, ys[1:])) if ys else 0
        right = max((w[2] for w in inside), default=x0)
        out.append({"text": sh["text"], "px": round(px), "drawn": lines,
                    "over_px": round((right - x1) / k, 1), "box_w": round(sh["w"])})
    return out


rows = {}
for variant in VARIANTS:
    for deck in DECKS:
        for sdir in sorted((ROOT / f"{variant}-{deck}").glob("slide-*")):
            name = sdir.name
            src = (ROOT / f"src-{deck}" / f"{name}.xml").read_text(encoding="utf-8")
            fitted_p = sdir / "fitted.xml"
            fitted = fitted_p.read_text(encoding="utf-8") if fitted_p.exists() else src
            pdf = ROOT / "pdf" / f"{variant}-{deck}-{name}.pdf"
            if not pdf.exists():  # the slide did not compile
                continue
            words = pdf_words(pdf)
            vocab = slide_words(src)
            res = json.loads((sdir / "compile-result.json").read_text(encoding="utf-8"))
            reserved = [int(m.group(2)) for e in res.get("fitGrow") or []
                        for m in [re.search(r"heading (\d+) -> (\d+) lines", e)] if m]
            src_t, fit_t = texts(src), texts(fitted)
            heads = []
            if len(src_t) == len(fit_t):
                gained = [(a, t) for (sa, _), (a, t) in zip(src_t, fit_t)
                          if attr(a, "minH") and not attr(sa, "minH")]
                for (a, t), r in zip(gained, reserved):
                    heads.append({"text": t[:60], "reserved": r, "drawn": drawn_lines(words, t)})
            kpis = kpi_boxes(sdir / "presentation.pptx", ROOT / "pdf" / f"{variant}-{deck}-{name}.pdf")
            rows[f"{variant}-{deck}-{name}"] = {"broken": broken(words, vocab), "headings": heads, "kpi": kpis,
                                                "overlap": overlaps(words)}

json.dump(rows, open(ROOT / "fontcheck.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for variant in VARIANTS:
    br = sum(len(r["broken"]) for k, r in rows.items() if k.startswith(variant + "-"))
    ov = [k for k, r in rows.items() if k.startswith(variant + "-") and r["overlap"]]
    hs = [h for k, r in rows.items() if k.startswith(variant + "-") for h in r["headings"]]
    blank = sum(1 for h in hs if h["drawn"] is not None and h["reserved"] > h["drawn"])
    ks = [x for k, r in rows.items() if k.startswith(variant + "-") for x in r["kpi"]]
    kwrap = sum(1 for x in ks if x["drawn"] > 1)
    kover = sum(1 for x in ks if x["over_px"] > 1)
    print(f"{variant}: broken words {br}; headings reserved {len(hs)}, blank line drawn {blank}; "
          f"KPI numbers {len(ks)} (mean {sum(x['px'] for x in ks)/max(1,len(ks)):.0f}px), wrapped {kwrap}, past box {kover}; "
          f"slides with overlapping text {len(ov)}: {', '.join(k.split('-slide-')[0][len(variant) + 1:] + ' ' + k.split('-slide-')[1] for k in ov)}")
for k, r in rows.items():
    if r["broken"] or r["headings"] or r["kpi"]:
        print(k, "broken:", r["broken"], "| heads:", [(h["text"][:30], h["reserved"], h["drawn"]) for h in r["headings"]],
              "| kpi:", [(x["text"], x["px"], x["drawn"], x["over_px"]) for x in r["kpi"]])
