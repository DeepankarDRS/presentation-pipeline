"""Card tile nodes, free replay with the LLM's own layout kept (docs/tile-nodes-spec-2026-10-12.md §11, step 4).

    python -m scripts.experiments.cards.card_replay                  # rewrite, compile, render, score -> output/card-replay/
    python -m scripts.experiments.cards.card_replay --no-render      # skip LibreOffice (no broken-word count, no sheets)
    python -m scripts.experiments.cards.card_replay --limit 5        # the first 5 slides (a quick look)

Takes every saved slide with a card_grid plan (grid / steps; matrix is deferred) from output/**/slides.json, one per
distinct XML, skipping replays and galleries. Arm A is the slide as the LLM wrote it (today's compiler). Arm B is the
same XML with only the LLM's hand-drawn cards replaced by one <CardGrid ref> tag at their place: the panels, headers,
columns and other components around them stay as the LLM drew them (tile-nodes learning 8: a replay that drops the
LLM's own layout gives misleading numbers). The tag is bare (ref and the LLM's w / grow: the generator wrote bare tags, learning 1); with --styled its
attributes come from what the LLM drew, as a generator under
POM_BLOCKS=tiles would write them (variant from the card fills / edges, icons, side icons). The plan fields old plans
lack are stand-ins read from the same drawing: the LLM's one dark card -> focus_card, its tinted cards -> tones, its
coloured / bold runs inside a card's own line -> key_phrase, its icons (on every card) -> icon. Fresh planner plans may differ; that is the paid check.

Both arms: the deck font (compile_xml's deck_font) -> normalize -> compile-pom.js (fit-grow) -> LibreOffice with Inter
(a private profile, `render`), scored with scripts.experiments.kpi.kpi_replay.score (broken words,
GEOM_CARD_EMPTY, LOW_CONTRAST) plus card title / body sizes, plan text missing from the slide, and the card XML's output
tokens (o200k: the replaced region vs its tag). Writes output/card-replay/: results.json, summary.md, A/ B/, and blind
sheets (sheets/, marks.csv; key.json says which side is which).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from lxml import etree  # noqa: E402

from scripts.experiments.kpi.kpi_replay import _theme, compile_slide, score  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import cards as C  # noqa: E402
from src.compiler.nodes import tiles as T  # noqa: E402

OUT = ROOT / "output" / "card-replay"
SKIP = ("replay", "gallery", "tile-", "card-", "render_check", "phase0b", "variant", "fontexp", "label-test",
        "scratch", "cardgap", "fit_grow", "embedtest", "guardcheck", "rc_repro", "palette_preview", "comparison_check",
        "cmp/", "trace", "p1exp", "reg0", "reg1", "handwritten", "blueprint")
BARE_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")
DARK = {"$panelDark", "$textMain", "$accent", "$accentDark"}
TONE_OF = {"negative": "bad", "positive": "good", "warning": "watch"}
LAYOUT_KEYS = ("w", "h", "grow", "minW", "maxW", "minH", "maxH", "alignSelf", "margin")
BOX_KEYS = ("backgroundColor", "border.color", "border.width", "borderLeft.color", "borderLeft.width",
            "borderTop.color", "borderTop.width", "padding", "shadow.type")


def norm(s: Any) -> str:
    return re.sub(r"\W+", " ", str(s or "")).strip().lower()


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(BARE_AMP.sub("&amp;", xml).encode("utf-8"))


def _parse_doc(xml: str) -> etree._Element:
    """A compiled slide file (<Theme> and <Slide> side by side, maybe a comment) under one root."""
    body = re.sub(r"<\?xml[^>]*\?>", "", BARE_AMP.sub("&amp;", xml))
    return etree.fromstring(f"<_r_>{body}</_r_>".encode("utf-8"))


def _serial(el: etree._Element) -> str:
    return etree.tostring(el, encoding="unicode")


def collect(limit: int | None = None) -> list[dict]:
    rows, seen = [], set()
    for sj in sorted((ROOT / "output").rglob("slides.json")):
        rel = sj.relative_to(ROOT).as_posix()
        if any(k in rel for k in SKIP):
            continue
        try:
            slides = json.loads(sj.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(slides, list):
            continue
        for s in slides:
            plan, xml = s.get("slide_plan") or {}, s.get("xml") or ""
            if not xml or "<CardGrid" in xml or not C.card_components(plan):
                continue
            h = hashlib.sha1(xml.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            run = sj.parent.name.split("__")[0][:40]
            rows.append({"case": f"{rel.split('/')[1]}-{run}-s{s.get('slide_index', 0)}-{h[:4]}", "source": rel,
                         "plan": plan, "xml": xml, "theme": _theme(sj)})
    return rows[:limit] if limit else rows


# ── rewrite: the LLM's cards -> one <CardGrid> at their place ─────────────────

def _boxed(el: etree._Element) -> bool:
    return any(el.get(k) for k in ("backgroundColor", "border.color", "borderLeft.color", "borderTop.color", "padding"))


def _card_box(title: etree._Element) -> etree._Element | None:
    for p in title.iterancestors():
        if p.tag == "Slide":
            return None
        if p.tag in ("VStack", "HStack") and _boxed(p):
            return p
    return None


def find_cards(root: etree._Element, comp: dict) -> tuple[list[etree._Element], list[etree._Element]] | str:
    """(title Texts, card boxes) in plan order, or why they cannot be found."""
    if not C.cards_of(comp):
        return "no cards in the plan"
    texts = [t for t in root.iter("Text") if t.getparent() is not None]
    used: set[int] = set()
    titles, boxes = [], []
    for i, c in enumerate(C.cards_of(comp)):
        key = norm(c.get("title"))
        hit = next((t for t in texts if id(t) not in used and key and
                    (norm("".join(t.itertext())) == key or (len(key) > 8 and norm("".join(t.itertext())).startswith(key)))),
                   None)
        if hit is None:
            return f"card {i} title not on the slide"
        used.add(id(hit))
        box = _card_box(hit)
        if box is None:
            return f"card {i} has no box"
        titles.append(hit)
        boxes.append(box)
    if len({id(b) for b in boxes}) != len(boxes):
        return "two cards share a box"
    return titles, boxes


def _lca(els: list[etree._Element]) -> etree._Element:
    chains = [[e, *e.iterancestors()] for e in els]
    common = set(map(id, chains[0]))
    for ch in chains[1:]:
        common &= set(map(id, ch))
    return next(a for a in chains[0] if id(a) in common)


def _contains(el: etree._Element, targets: set[int]) -> bool:
    return any(id(e) in targets for e in el.iter())


def _filler(el: etree._Element) -> bool:
    """An arrow / connector / spacer the LLM put between its cards (no words)."""
    words = norm("".join(el.itertext()))
    return not re.search(r"[a-z0-9]", words)


def _token(v: str | None) -> str:
    return str(v or "")


def stand_ins(boxes: list[etree._Element], comp: dict) -> tuple[dict, dict]:
    """(plan copy with focus_card / tones / key_phrase read from the drawing, what was read)."""
    comp = copy.deepcopy(comp)
    cs = comp["content_data"]["cards"]
    dark = [i for i, b in enumerate(boxes) if _token(b.get("backgroundColor")) in DARK]
    read = {"dark": dark, "tones": {}, "phrases": {}}
    if len(dark) == 1 and len(boxes) >= 3:
        comp["content_data"]["focus_card"] = dark[0]
    for i, b in enumerate(boxes):
        if not isinstance(cs[i], dict):
            continue
        cols = " ".join(_token(b.get(k)) for k in ("backgroundColor", "borderLeft.color", "border.color", "borderTop.color"))
        role = next((r for r in TONE_OF if f"${r}" in cols), None)
        if role and not cs[i].get("tone"):
            cs[i]["tone"] = read["tones"][i] = TONE_OF[role]
        body = " ".join([str(cs[i].get("body") or "")] + [str(x) for x in cs[i].get("bullets") or []])
        for run in b.iter("Span", "B"):
            t = (run.text or "").strip()
            if t and t in body and norm(t) != norm(cs[i].get("title")) and not cs[i].get("key_phrase"):
                cs[i]["key_phrase"] = read["phrases"][i] = t
    icons = [next(b.iter("Icon"), None) for b in boxes]   # the planner's per-card icon: the LLM's icons
    if all(ic is not None and ic.get("name") for ic in icons):
        for c, ic in zip(cs, icons):
            if isinstance(c, dict):
                c.setdefault("icon", ic.get("name"))
        read["icons"] = len(icons)
    if any(c.get("tone") for c in cs if isinstance(c, dict)):
        for c in cs:
            if isinstance(c, dict):
                c.setdefault("tone", "")
    return comp, read


def _beside_icon(title: etree._Element, box: etree._Element) -> bool:
    """The title sits in an HStack (inside its card) that also holds an Icon: arrange="side"."""
    for p in title.iterancestors():
        if p is box:
            return False
        if p.tag == "HStack" and any(e.tag == "Icon" for e in p.iter()):
            return True
    return False


def tag_attrs(boxes: list[etree._Element], titles: list[etree._Element], comp: dict) -> tuple[str, list[str]]:
    """The <CardGrid> attributes from what the LLM drew, and the per-card <Card> tags."""
    plain = [b for b in boxes if _token(b.get("backgroundColor")) not in DARK]
    fills = Counter(_token(b.get("backgroundColor")) for b in plain)
    tops = sum(1 for b in plain if b.get("borderTop.width") or b.get("borderTop.color"))
    soft = sum(1 for b in plain if _token(b.get("backgroundColor")).endswith("Soft"))
    if tops >= len(plain) / 2:
        variant = "accent_top"
    elif soft >= len(plain) / 2 and any(c.get("tone") for c in C.cards_of(comp)):
        variant = "toned"
    elif fills.most_common(1)[0][0] in ("", "-") and any(b.get("border.color") for b in plain):
        variant = "outline"
    else:
        variant = "filled"
    attrs = {"variant": variant}
    icons = []
    for b in boxes:
        ic = next(b.iter("Icon"), None)
        icons.append(ic.get("name") if ic is not None else None)
    items = []
    if all(icons) and len(set(icons)) == 1:
        attrs["icon"] = icons[0]
    elif any(icons):
        items = [f'<Card ref="{comp["component_id"]}.{i}" icon="{n}"/>' for i, n in enumerate(icons) if n]
    side = sum(1 for b, t in zip(boxes, titles) if _beside_icon(t, b))
    if any(icons) and side >= len(boxes) / 2:
        attrs["arrange"] = "side"
    return " ".join(f'{k}="{v}"' for k, v in attrs.items()), items


def rewrite_component(root: etree._Element, comp: dict, styled: bool = False) -> dict:
    """Replace the LLM's cards of comp in root (in place). Returns what was done or why not."""
    found = find_cards(root, comp)
    if isinstance(found, str):
        return {"skipped": found}
    titles, boxes = found
    cid = comp["component_id"]
    bid = {id(b) for b in boxes}
    anc = _lca(boxes) if len(boxes) > 1 else boxes[0].getparent()
    if anc.tag not in ("VStack", "HStack"):
        return {"skipped": f"cards sit in a <{anc.tag}>"}
    plan_comp, read = stand_ins(boxes, comp)
    # bare by default: the generator wrote a bare <KpiGrid> in all 6 QBR runs (tile-nodes learning 1), so the
    # defaults are what gets judged; --styled writes the variant / icons read from the LLM's drawing
    attrs, items = tag_attrs(boxes, titles, plan_comp) if styled else ("", [])
    kids = [k for k in anc if isinstance(k.tag, str)]
    part = [k for k in kids if _contains(k, bid)]
    lo, hi = kids.index(part[0]), kids.index(part[-1])
    between = kids[lo:hi + 1]
    stray = [k for k in between if not _contains(k, bid) and not _filler(k)]
    # text of the cards' own containers that is not a card (a heading inside the grid) stays outside the tag
    loose = [t for k in part for t in k.iter("Text") if not any(_contains(b, {id(t)}) for b in boxes) and not _filler(t)]
    if stray or loose:
        return {"skipped": "other content between the cards"}
    old = "".join(_serial(k) for k in between)
    whole = len(between) == len(kids) and not _boxed(anc) and anc.getparent() is not None and anc.getparent().tag != "Slide"
    keep = {k: v for k, v in anc.attrib.items() if k in LAYOUT_KEYS} if whole else {}
    if not whole and anc.tag == "HStack":
        keep = {"w": "1", "grow": "1"}
    elif not whole:
        keep = {"grow": "1"}
    lay = " ".join(f'{k}="{v}"' for k, v in keep.items())
    tag_xml = (" ".join(x for x in (f'<CardGrid ref="{cid}"', attrs, lay) if x) + (">" + "".join(items) + "</CardGrid>" if items else "/>"))
    new = etree.fromstring(tag_xml)
    if whole:
        new.tail = anc.tail
        anc.getparent().replace(anc, new)
    else:
        new.tail = between[-1].tail
        anc.insert(anc.index(between[0]), new)
        for k in between:
            anc.remove(k)
    return {"old": old, "tag": tag_xml, "plan_comp": plan_comp, "read": read, "whole": whole}


LO_PROFILE = ROOT / "output" / "lo-inter"


def render(dest: Path) -> Path | None:
    """presentation.pdf by LibreOffice with the deck fonts (src/node/fonts) in a private profile: LibreOffice ignores
    the fonts embedded in the .pptx, and without Inter it drew bold text in Arial Black (2026-10-13: overlaps that the
    real deck does not have). scripts.experiments.node_test.node_test_score.render_pdf then finds this PDF."""
    import subprocess
    from scripts.experiments.node_test.node_test_score import SOFFICE
    fonts = LO_PROFILE / "user" / "fonts"
    if not fonts.exists():
        fonts.mkdir(parents=True)
        for f in (ROOT / "src" / "node" / "fonts").glob("*.ttf"):
            shutil.copy2(f, fonts / f.name)
    pptx, pdf = dest / "presentation.pptx", dest / "presentation.pdf"
    if not pptx.exists():
        return None
    soffice = shutil.which("soffice") or str(SOFFICE)
    if not Path(soffice).exists() and not shutil.which(soffice):
        print(f"render skipped: LibreOffice not found ({soffice})")
        return None
    for _ in range(2):
        subprocess.run([soffice, f"-env:UserInstallation={LO_PROFILE.as_uri()}", "--headless", "--convert-to", "pdf",
                        "--outdir", str(dest), str(pptx)], capture_output=True, check=False, timeout=180)
        if pdf.exists():
            return pdf
    return None


def overlaps(pdf: Path | None) -> list[str]:
    """Rendered text lines that run into each other (ink boxes overlapping); single glyph runs ("₹", "•") ignored."""
    if not pdf:   # --no-render (test PC: no LibreOffice / pymupdf)
        return []
    import pymupdf
    lines = []
    for b in pymupdf.open(pdf)[0].get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(sp["text"] for sp in ln["spans"]).strip()
            if len(re.findall(r"\w", t)) >= 2:
                x0, y0, x1, y1 = ln["bbox"]
                sz = ln["spans"][0]["size"]
                lines.append((pymupdf.Rect(x0, y0 + 0.2 * sz, x1, y1 - 0.2 * sz), t))
    out = []
    for i, (a, ta) in enumerate(lines):
        for b, tb in lines[i + 1:]:
            r = a & b
            if r.is_valid and not r.is_empty and r.get_area() > 0.15 * min(a.get_area(), b.get_area()):
                out.append(f"{ta[:24]} / {tb[:24]}")
    return out


def tokens(s: str) -> int:
    import tiktoken
    return len(tiktoken.get_encoding("o200k_base").encode(re.sub(r">\s+<", "><", s.strip())))


# ── score ─────────────────────────────────────────────────────────────────────

def card_sizes(final_xml: str, plan: dict, arm: str) -> dict:
    """Per card_grid: title and body sizes as drawn (B: code's ids; A: Texts whose text is the plan's)."""
    try:
        root = _parse_doc(final_xml)
    except etree.XMLSyntaxError:
        return {}
    out = {}
    for cid, comp in C.card_components(plan).items():
        def size(t):
            try:
                return float(t.get("fontSize") or 24)
            except ValueError:
                return 24.0
        if arm == "B":
            ti = [size(t) for t in root.iter("Text") if re.match(rf"^cardt-{re.escape(cid)}-\d+$", t.get("id", ""))]
            bo = [size(t) for t in root.iter("Text") if re.match(rf"^cardb-{re.escape(cid)}-\d+$", t.get("id", ""))]
        else:
            keys = [norm(c.get("title")) for c in C.cards_of(comp)]
            bodies = [norm(C._lines(c)[0]) for c in C.cards_of(comp)]
            ti = [size(t) for t in root.iter("Text") if norm("".join(t.itertext())) in keys]
            bo = [size(t) for t in root.iter("Text") if norm("".join(t.itertext())) in bodies and norm("".join(t.itertext()))]
        out[cid] = {"title_min": min(ti, default=0), "title_max": max(ti, default=0), "body_min": min(bo, default=0)}
    return out


def missing_text(final_xml: str, plan: dict) -> list[str]:
    """Plan card titles / lines that are not on the slide (normalised)."""
    try:
        slide = norm(" ".join("".join(t.itertext()) for t in _parse_doc(final_xml).iter("Text", "Li")))
    except etree.XMLSyntaxError:
        return ["<unparsable>"]
    out = []
    for comp in C.card_components(plan).values():
        for c in C.cards_of(comp):
            body, bullets = C._lines(c)
            for line in [c.get("title"), body, *bullets]:
                if norm(line) and norm(line) not in slide:
                    out.append(str(line)[:40])
    return out


def run(out: Path, do_render: bool, limit: int | None, styled: bool = False) -> list[dict]:
    results = []
    for r in collect(limit):
        root = _parse(r["xml"])
        plan_b = copy.deepcopy(r["plan"])
        done = []
        for cid, comp in C.card_components(r["plan"]).items():
            res = rewrite_component(root, comp, styled)
            res["cid"] = cid
            done.append(res)
            if "plan_comp" in res:
                plan_b["components"] = [res["plan_comp"] if c.get("component_id") == cid else c for c in plan_b["components"]]
        row = {"case": r["case"], "source": r["source"],
               "components": [{k: v for k, v in d.items() if k not in ("plan_comp", "old")} for d in done]}
        if not any("tag" in d for d in done):
            row["skipped"] = "; ".join(d.get("skipped", "") for d in done)
            results.append(row)
            print(f"{r['case']}: skipped ({row['skipped']})")
            continue
        row["tokens"] = {"A": sum(tokens(d["old"]) for d in done if "tag" in d),
                         "B": sum(tokens(d["tag"]) for d in done if "tag" in d)}
        xml_b = _serial(root)
        fill = T.fill(xml_b, plan_b)
        row["b_issues"] = [i["code"] for i in fill["issues"]]
        for arm, xml, plan in (("A", BARE_AMP.sub("&amp;", r["xml"]), r["plan"]), ("B", fill["xml"], plan_b)):
            dest = out / arm / r["case"] / "slide-1"
            shutil.rmtree(dest, ignore_errors=True)
            comp = compile_slide(deck_font(xml), r["theme"], dest)   # the deck font, as compile_xml sets it
            if do_render:
                render(dest)
            sc = score(arm, dest, comp, plan, r["case"], do_render)
            final = (dest / "fitted.xml").read_text(encoding="utf-8") if (dest / "fitted.xml").exists() else comp["cleaned"]
            sc.pop("sizes", None), sc.pop("off_plan", None)
            sc["cards"] = card_sizes(final, plan, arm)
            sc["missing"] = missing_text(final, plan)
            sc["overlaps"] = overlaps(dest / "presentation.pdf" if (dest / "presentation.pdf").exists() else None)
            row[arm] = sc
        print(f"{r['case']}: A {row['A']['compiled']} empty {row['A']['fill']['GEOM_CARD_EMPTY']} broken {row['A']['broken']} | "
              f"B {row['B']['compiled']} empty {row['B']['fill']['GEOM_CARD_EMPTY']} broken {row['B']['broken']} "
              f"tokens {row['tokens']['A']} -> {row['tokens']['B']}")
        results.append(row)
    return results


def sheets(out: Path, results: list[dict]) -> int:
    from scripts.experiments.node_test import node_test_sheet as S
    pick = out / "sheet-in"
    shutil.rmtree(pick, ignore_errors=True)
    n = 0
    for r in results:
        if "B" not in r:
            continue
        for arm in ("A", "B"):
            src, d = out / arm / r["case"] / "slide-1", pick / arm / r["case"] / "slide-1"
            d.mkdir(parents=True, exist_ok=True)
            for f in ("presentation.pptx", "presentation.pdf"):
                if (src / f).exists():
                    shutil.copy2(src / f, d / f)
        n += 1
    if n:
        S.build(pick / "B", pick / "A", out / "sheets")
    return n


def summary(out: Path, results: list[dict]) -> str:
    done = [r for r in results if "B" in r]
    skipped = Counter(r["skipped"] for r in results if "skipped" in r)

    def tot(arm, f):
        vals = [f(r[arm]) for r in done if r[arm]["compiled"]]
        return sum(v for v in vals if v is not None)

    def med(arm, key):
        vals = [c[key] for r in done for c in r[arm]["cards"].values() if c[key]]
        return statistics.median(vals) if vals else 0

    ta, tb = sum(r["tokens"]["A"] for r in done), sum(r["tokens"]["B"] for r in done)
    lines = [
        "# Card tile nodes: free replay (LLM layout kept)", "",
        f"Slides: {len(results)} with a card_grid plan; {len(done)} replayed; {sum(skipped.values())} skipped "
        f"({', '.join(f'{k} {v}' for k, v in skipped.most_common())}).", "",
        "| | A (LLM's cards) | B (CardGrid tag) |", "|---|---|---|",
        f"| compiled | {sum(r['A']['compiled'] for r in done)} | {sum(r['B']['compiled'] for r in done)} |",
        f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill']['GEOM_CARD_EMPTY'])} | {tot('B', lambda s: s['fill']['GEOM_CARD_EMPTY'])} |",
        f"| GEOM_SLIDE_SPARSE | {tot('A', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} | {tot('B', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} |",
        f"| broken words (render) | {tot('A', lambda s: s['broken'])} | {tot('B', lambda s: s['broken'])} |",
        f"| text overlaps (render) | {sum(len(r['A'].get('overlaps', [])) for r in done)} | {sum(len(r['B'].get('overlaps', [])) for r in done)} |",
        f"| WORD_TOO_WIDE | {tot('A', lambda s: s['word_too_wide'])} | {tot('B', lambda s: s['word_too_wide'])} |",
        f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])} | {tot('B', lambda s: s['low_contrast'])} |",
        f"| plan text missing (lines) | {sum(len(r['A']['missing']) for r in done)} | {sum(len(r['B']['missing']) for r in done)} |",
        f"| card title px, median of the smallest | {med('A', 'title_min')} | {med('B', 'title_min')} |",
        f"| card body px, median of the smallest | {med('A', 'body_min')} | {med('B', 'body_min')} |",
        f"| card output tokens | {ta} | {tb} ({(tb - ta) / ta:+.0%}) |" if ta else "| card output tokens | 0 | 0 |",
        "", "Stand-ins read from the LLM's drawing (old plans have no focus_card / tone / key_phrase):",
        f"- focus card (one dark card): {sum(1 for r in done for c in r['components'] if c.get('read', {}).get('dark') and len(c['read']['dark']) == 1)}",
        f"- cards with a tone: {sum(len(c.get('read', {}).get('tones', {})) for r in done for c in r['components'])}",
        f"- key phrases: {sum(len(c.get('read', {}).get('phrases', {})) for r in done for c in r['components'])}",
        f"- card groups with icons: {sum(1 for r in done for c in r['components'] if c.get('read', {}).get('icons'))}",
        f"- B issues: {dict(Counter(code for r in done for code in r['b_issues']))}",
    ]
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--styled", action="store_true", help="B writes the variant / icons read from the LLM's drawing")
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    a.out.mkdir(parents=True)
    results = run(a.out, not a.no_render, a.limit, a.styled)
    (a.out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    if not a.no_render:
        print(f"sheets: {sheets(a.out, results)} pairs")
    print(summary(a.out, results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
