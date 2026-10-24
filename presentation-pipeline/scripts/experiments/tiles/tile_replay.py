"""KPI tile nodes, free replay (docs/tile-nodes-spec-2026-10-12.md §8 step 4).

    python -m scripts.experiments.tiles.tile_replay                  # rewrite, compile, render, score -> output/tile-replay/
    python -m scripts.experiments.tiles.tile_replay --no-render      # skip LibreOffice (no broken-word count, no sheets)

Takes the KPI slides the generator wrote on today's route (POM_BLOCKS=kpi, hand-written tiles with
<Text ref>): the first tries saved by the 2026-10-12 decks run (`generated.xml` / `first-generated.xml`),
and, recovered from their final XML (filled text mapped back to refs, code's ids dropped), the paid check's
9 runs and the 2026-10-11 decks run. Each slide's hand-written KPI block is rewritten as tile tags by
`rewrite` (the tiles' looks read from what the LLM drew: fill, edge bar, dot, dark panel, icon, order,
grouping), then both versions go through the same path: fill (element_refs.fill_refs / tiles.fill) ->
normalize -> compile-pom.js (fit-grow) -> LibreOffice, and are scored with scripts.experiments.kpi.kpi_replay.score
(broken words, number sizes, GEOM_CARD_EMPTY, LOW_CONTRAST, off-plan values). KPI output tokens are the
replaced XML vs its tile tags (o200k, inter-tag whitespace removed on both).
Writes output/tile-replay/: results.json, summary.md, pairs/ (A = hand-written, B = tile tags) and sheets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from lxml import etree  # noqa: E402

from scripts.experiments.kpi.kpi_replay import compile_slide, map_refs, score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import element_refs as E  # noqa: E402
from src.compiler.nodes import tiles as T  # noqa: E402

OUT = ROOT / "output" / "tile-replay"
DECKS2 = ROOT / "output" / "kpi-decks-2" / "kpi-decks-2-20261012-090227"
DECKS1 = ROOT / "output" / "kpi-decks" / "kpi-decks-20261011-210625"
PAID = ROOT / "output" / "kpi-paid" / "kpi-paid"
INPUTS = ROOT / "docs" / "eval" / "kpi-node" / "paid-inputs.json"
STACKS = ("VStack", "HStack")
DARK = ("$panelDark", "$textMain", "$accent")
ROLE_OF_TOKEN = {"accent": "$accent", "positive": "$positive", "negative": "$negative", "warning": "$warning"}


# ── sources ──────────────────────────────────────────────────────────────────

def _theme_name(manifest: Path) -> str:
    return json.loads(manifest.read_text(encoding="utf-8")).get("theme") or "corporate-slate"


def _unfill(xml: str, plan: dict) -> str:
    """The slide in the ref form: refs wrapped in a styled Text unwrapped (as fill_refs does), plan texts typed
    or filled -> refs, code's ids gone. A first try only changes where the LLM typed a label itself."""
    root = _parse(xml)
    E._unwrap_refs(root, lambda *a: None)
    mapped = map_refs(_serial(root), plan)[0]
    return re.sub(r'\sid="kpi[vh]\d?-[^"]*"', "", mapped)


def collect() -> list[dict]:
    rows = []
    for case_dir in sorted((DECKS2 / "slides").iterdir()):
        case = case_dir.name
        slides = json.loads((DECKS2 / "decks" / case / "slides.json").read_text(encoding="utf-8"))
        theme = _theme_name(DECKS2 / "decks" / case / "run-manifest.json")
        for sd in sorted(case_dir.iterdir()):
            first = next((sd / f for f in ("first-generated.xml", "generated.xml") if (sd / f).exists()), None)
            idx = int(sd.name.split("-")[1])
            plan = slides[idx]["slide_plan"]
            if first is None or not E.kpi_components(plan) or 'ref="' not in first.read_text(encoding="utf-8"):
                continue
            rows.append({"case": f"decks2-{case.split('__')[0]}-s{idx}", "source": "first try (decks run 2)",
                         "xml": _unfill(first.read_text(encoding="utf-8"), plan), "plan": plan, "theme": theme})
    items = {f"{i['case']}-s{i['slide']}": i for i in json.loads(INPUTS.read_text(encoding="utf-8"))}
    for d in sorted((PAID / "B").iterdir()):
        it = items[re.sub(r"-r\d+$", "", d.name)]
        xml = (d / "final.xml").read_text(encoding="utf-8")
        if xml:
            rows.append({"case": f"paid-{d.name}", "source": "recovered (paid check)", "xml": _unfill(xml, it["plan"]),
                         "plan": it["plan"], "theme": it["theme"]})
    for deck in sorted((DECKS1 / "decks").iterdir()):
        theme = _theme_name(deck / "run-manifest.json")
        for s in json.loads((deck / "slides.json").read_text(encoding="utf-8")):
            plan = s.get("slide_plan") or {}
            if E.kpi_components(plan) and s.get("xml"):
                rows.append({"case": f"decks1-{deck.name.split('__')[0]}-s{s['slide_index']}",
                             "source": "recovered (decks run 1)", "xml": _unfill(s["xml"], plan), "plan": plan, "theme": theme})
    return rows


# ── the rewrite ──────────────────────────────────────────────────────────────

def _parse(xml: str) -> etree._Element:
    xml = re.sub(r"<\?xml[^>]*\?>", "", xml)
    # the LLM's first XML may hold a bare & ("Travel & commuting"): the normalizer escapes it later, this parse comes
    # first (combined check 2026-10-15: 6 route-A runs lost their whole result to it)
    xml = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", xml)
    return etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"), etree.XMLParser(remove_blank_text=True))


def _serial(root: etree._Element) -> str:
    return (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root)


def _ref_texts(root, cid: str, i: int) -> dict[str, etree._Element]:
    out = {}
    for t in root.iter("Text"):
        m = re.match(rf"^{re.escape(cid)}\.{i}\.(label|value|note)$", t.get("ref", ""))
        if m:
            out[m[1]] = t
    return out


def _tile(value: etree._Element) -> etree._Element:
    c = E._container(value)
    return c if c is not None else value.getparent()


def _role(token: str | None) -> str | None:
    m = re.match(r"^\$(accent|positive|negative|warning)(Soft|Text)?$", token or "")
    return m[1] if m else None


def _look(tile: etree._Element, comp: dict, i: int) -> tuple[str, dict[str, str]]:
    """(variant, attributes) that redraw what the LLM drew for this tile."""
    bg, attrs = tile.get("backgroundColor"), {}
    tone = T.tone_role(comp, i)
    edge = next((tile.get(k) for k in ("borderLeft.width",) if tile.get(k)), None)
    dot = any(s.get("shapeType") in ("ellipse", "oval") and float(s.get("w") or 99) <= 16 for s in tile.iter("Shape"))
    if bg in DARK:
        variant = "inverted" if T.emphasis_index(comp) == i else "plain"
        if variant == "plain":
            attrs["backgroundColor"] = bg
        role = None
    elif edge and float(edge) >= 4:
        variant, role = "bar", _role(tile.get("borderLeft.color"))
        if bg and bg not in ("$surfaceAlt",):
            attrs["backgroundColor"] = bg
    elif dot:
        variant, role = "dot", next((_role(s.get("fill.color")) for s in tile.iter("Shape") if _role(s.get("fill.color"))), None)
    elif bg and bg.endswith("Soft"):
        role = _role(bg)
        variant = "toned" if _role(tile.get("border.color")) else "filled"
        if variant == "toned" and not T.spec.check("has_tones", comp):   # toned needs plan tones: filled + the edge
            variant = "filled"
            attrs.update({k: tile.get(k) for k in ("border.color", "border.width") if tile.get(k)})
    elif not bg and not any(k.startswith("border") for k in tile.attrib):
        variant, role = "bare", None
    else:
        variant, role = "plain", None
        if bg and bg != "$surfaceAlt":
            attrs["backgroundColor"] = bg
    if role and role != tone:
        attrs["color"] = ROLE_OF_TOKEN[role]
    return variant, attrs


def _arrange(tile: etree._Element, refs: dict) -> tuple[str, str | None]:
    icon = next(iter(tile.iter("Icon")), None)
    order = [el for el in tile.iter() if el in refs.values()]
    value_first = refs.get("value") is not None and order and order[0] is refs["value"]
    if icon is None:
        return ("value-first" if value_first else "label-first"), None
    name = icon.get("name")
    if tile.tag == "HStack" and len(tile) and tile[0] is icon:
        return "side", name
    if icon.getparent() is tile and refs.get("label") is not None and refs["label"].getparent() is tile:
        return "icon-top", name
    return ("value-first" if value_first else "label-first"), name


STYLE_ATTRS = ("color", "bold", "italic", "underline", "letterSpacing", "highlight")


def _styles(refs: dict, look: tuple[str, dict], comp: dict, i: int) -> dict[str, str]:
    """part.attr -> value the LLM set on its ref Texts that the tile's look would not give (code's own value attributes
    and literal colours left out)."""
    variant, attrs = look
    role = _role(attrs.get("color")) or T.tone_role(comp, i)
    base = {**T.kpi()["house_look"], **T.kpi()["variants"][variant]["look"]}
    out = {}
    for part, el in refs.items():
        for k, v in el.attrib.items():
            if k not in STYLE_ATTRS or (part == "value" and k == "bold") or (k == "color" and not v.startswith("$")):
                continue
            if T.role_value(base.get(f"{part}.{k}", ""), role) == v or (k == "bold" and v != "true"):
                continue
            out[f"{part}.{k}"] = v
    return out


def _box(el: etree._Element, keep: tuple[str, ...] | None = None) -> dict[str, str]:
    """The box attributes a tile tag may carry, literal colours left out (tile tags take palette tokens only). Sizes,
    grow and gaps are kept: until 2026-10-13 only $-values were, so a rewritten <KpiGrid> lost the LLM's grow / w / h
    (docs/eval/tile-nodes/wide/README.md)."""
    ok = set(T.data()["box_attributes"])
    literal_colour = lambda k, v: ("olor" in k or "Gradient" in k) and not str(v).startswith("$")
    return {k: v for k, v in el.attrib.items() if k in ok and (keep is None or k in keep) and not literal_colour(k, v)}


def _attrs(d: dict[str, str]) -> str:
    return "".join(f' {k}="{v}"' for k, v in d.items())


def rewrite_component(root: etree._Element, comp: dict) -> tuple[str, str, list[str]]:
    """Replace one component's hand-written tiles with tile tags: (the hand-written XML replaced, the tags, notes)."""
    cid = comp["component_id"]
    n = len(E._list(comp, "kpi_values"))
    tiles, looks, arranges, icons, notes, refsd = {}, {}, {}, {}, [], {}
    for i in range(n):
        refs = _ref_texts(root, cid, i)
        if "value" not in refs:
            notes.append(f"item {i}: no value ref in the hand-written XML")
            continue
        refsd[i] = refs
        tile = _tile(refs["value"])
        if any(r is not refs["value"] and tile not in r.iterancestors() for r in refs.values()):
            notes.append(f"item {i}: label / note outside the value's tile")
        tiles[i] = tile
        looks[i] = _look(tile, comp, i)
        arranges[i], icons[i] = _arrange(tile, refs)
    if not tiles:
        return "", "", notes
    # the group: the tiles that share a row (or rows of one grid); the rest are placed outside it
    parents = Counter(t.getparent() for t in tiles.values())
    row = parents.most_common(1)[0][0]
    grid_rows = [p for p in parents if p.tag == "HStack" and p.getparent() is row.getparent()]
    container, layout, cols = row, ("row" if row.tag == "HStack" else "column"), None
    if len(grid_rows) > 1 and row.tag == "HStack":
        g = row.getparent()
        kids = [k for k in g if isinstance(k.tag, str)]
        if all(k in grid_rows for k in kids):
            container, layout, cols = g, "grid", max(parents[r] for r in grid_rows)
    members = [i for i, t in tiles.items() if t.getparent() is container or t.getparent() in (grid_rows if layout == "grid" else [])]
    others = [k for k in container.iter() if k is not container and isinstance(k.tag, str)
              and not any(k is t or t in k.iterancestors() or k in t.iterancestors() for t in tiles.values())
              and k.getparent() is container]
    spacers = [k for k in others if k.tag in STACKS and not len(k) and not k.get("backgroundColor")]
    if [k for k in others if k not in spacers]:   # the row holds other content: each tile becomes a <Kpi> in place
        container, members = None, []
        notes.append("tiles share their row with other content: placed one by one")
    outside = [i for i in tiles if i not in members]
    variant = Counter(looks[i][0] for i in members).most_common(1)[0][0] if members else None
    if variant == "inverted":
        variant = "plain"
    arrange = Counter(arranges[i] for i in members).most_common(1)[0][0] if members else None

    # the LLM's own styling of each part (bold / coloured labels, toned notes) where it differs from the tile's look;
    # shared by every member -> on the group
    styles = {i: _styles(refsd[i], looks[i], comp, i) for i in tiles}
    shared = {k: v for k, v in (styles[members[0]].items() if members else [])
              if all(styles[i].get(k) == v for i in members)} if len(members) > 1 else {}
    for i in members:
        for k in shared:
            styles[i].pop(k, None)

    def item_tag(i: int, inside: bool) -> str:
        v, a = looks[i]
        a = {**dict(a), **styles[i]}
        if not inside or v != variant:
            a = {"variant": v, **a}
        if not inside or arranges[i] != arrange:
            a["arrange"] = arranges[i]
        if icons[i]:
            a["icon"] = icons[i]
        if v == "inverted":
            a["size"] = "hero"
        if not inside:
            a.update(_box(tiles[i], ("w", "h", "grow", "minW", "maxW", "minH", "maxH", "alignSelf", "margin")))
        return f'<Kpi ref="{cid}.{i}"{_attrs(a)}/>' if a or not inside else ""

    written, replaced = [], []
    if members:
        ga = {"variant": variant}
        if arrange != "label-first":
            ga["arrange"] = arrange
        if layout == "grid":
            ga.update(layout="grid", cols=str(cols))
        elif layout == "column":
            ga["layout"] = "column"
        elif len(members) > 4:   # the LLM's own row (the default for 5+ items is a grid)
            ga["layout"] = "row"
        ga.update(shared)
        ga.update(_box(container, ("w", "h", "grow", "gap", "minH", "maxH", "minW", "maxW", "alignSelf", "margin")))
        inner = "".join(item_tag(i, True) for i in members)
        tag = f'<KpiGrid ref="{cid}"{_attrs(ga)}' + (f">{inner}</KpiGrid>" if inner else "/>")
        new = etree.fromstring(tag.encode("utf-8"))
        new.tail = container.tail
        replaced.append(etree.tostring(container, encoding="unicode", with_tail=False))
        container.getparent().replace(container, new)
        written.append(tag)
    for i in outside:
        tag = item_tag(i, False)
        new = etree.fromstring(tag.encode("utf-8"))
        new.tail = tiles[i].tail
        replaced.append(etree.tostring(tiles[i], encoding="unicode", with_tail=False))
        tiles[i].getparent().replace(tiles[i], new)
        written.append(tag)
    return "".join(replaced), "".join(written), notes


def rewrite(xml: str, plan: dict) -> dict[str, Any]:
    root = _parse(xml)
    out = {"hand_kpi_xml": "", "tile_kpi_xml": "", "notes": []}
    for comp in E.kpi_components(plan).values():
        hand, tags, notes = rewrite_component(root, comp)
        out["notes"] += [f"{comp['component_id']}: {x}" for x in notes]
        out["hand_kpi_xml"] += hand
        out["tile_kpi_xml"] += tags
    out["xml"] = _serial(root)
    return out


def kpi_xml(xml: str, plan: dict) -> str:
    """The KPI XML the LLM wrote on a slide: its tile tags, plus any hand-written ref tiles (as `rewrite` finds them)."""
    root = _parse(xml)
    tags = [etree.tostring(el, encoding="unicode", with_tail=False) for el in root.iter(T.GROUP, T.ITEM)
            if not any(a.tag == T.GROUP for a in el.iterancestors())]
    E._unwrap_refs(root, lambda *a: None)
    return "".join(tags) + rewrite(_serial(root), plan)["hand_kpi_xml"]


# ── run ──────────────────────────────────────────────────────────────────────

def tokens(s: str) -> int:
    import tiktoken
    return len(tiktoken.get_encoding("o200k_base").encode(re.sub(r">\s+<", "><", s.strip())))


def run(out: Path, render: bool) -> list[dict]:
    results = []
    for r in collect():
        theme = resolve_theme(r["theme"])["element"]
        d = out / "pairs" / r["case"]
        d.mkdir(parents=True, exist_ok=True)
        rw = rewrite(r["xml"], r["plan"])
        hand = rw["hand_kpi_xml"]
        (d / "hand.xml").write_text(r["xml"], encoding="utf-8")
        (d / "tiles.xml").write_text(rw["xml"], encoding="utf-8")
        (d / "kpi-hand.xml").write_text(hand, encoding="utf-8")
        (d / "kpi-tiles.xml").write_text(rw["tile_kpi_xml"], encoding="utf-8")
        a_fill = E.fill_refs(r["xml"], r["plan"])
        b_fill = T.fill(rw["xml"], r["plan"])
        row = {"case": r["case"], "source": r["source"], "notes": rw["notes"],
               "tokens_hand": tokens(hand), "tokens_tiles": tokens(rw["tile_kpi_xml"]), "tile_tags": rw["tile_kpi_xml"],
               "issues_A": sorted({i["code"] for i in a_fill["issues"]}), "issues_B": sorted({i["code"] for i in b_fill["issues"]}),
               "errors_B": [i["message"] for i in b_fill["issues"] if i["severity"] == "error"],
               "hand_items_B": sum(s.get("hand_items", 0) for s in b_fill["components"].values())}
        for arm, filled in (("A", a_fill), ("B", b_fill)):
            dest = d / arm
            row[arm] = score("B", dest, compile_slide(filled["xml"], theme, dest), r["plan"], r["case"], render)
        results.append(row)
        print(f"{r['case']}: tokens {row['tokens_hand']} -> {row['tokens_tiles']}; A {row['A']['compiled']} "
              f"B {row['B']['compiled']}; broken {row['A']['broken']}/{row['B']['broken']}; "
              f"card empty {sum(row['A']['fill'].values())}/{sum(row['B']['fill'].values())}", flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return results


def sheets(out: Path, results: list[dict]) -> list[Path]:
    """Pairs, hand-written (left) vs tile tags (right), 4 pairs a sheet."""
    import pymupdf
    from PIL import Image, ImageDraw
    w, h, gap, lab = 560, 315, 14, 24
    paths = []
    for k in range(0, len(results), 4):
        chunk = results[k:k + 4]
        img = Image.new("RGB", (2 * w + 3 * gap, len(chunk) * (h + lab + gap) + gap), "white")
        dr = ImageDraw.Draw(img)
        for j, r in enumerate(chunk):
            y = gap + j * (h + lab + gap)
            for c, arm in enumerate(("A", "B")):
                x = gap + c * (w + gap)
                pdf = out / "pairs" / r["case"] / arm / "presentation.pdf"
                tag = "hand-written" if arm == "A" else "tile tags"
                dr.text((x, y + 5), f"{r['case']} · {tag}", fill="black")
                if pdf.exists():
                    page = pymupdf.open(pdf)[0]
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(w / page.rect.width, h / page.rect.height))
                    img.paste(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), (x, y + lab))
                dr.rectangle([x - 1, y + lab - 1, x + w, y + lab + h], outline="#999999")
        p = out / f"pairs-{k // 4 + 1:02d}.png"
        img.save(p)
        paths.append(p)
    return paths


def summary(out: Path, results: list[dict]) -> str:
    th, tt = sum(r["tokens_hand"] for r in results), sum(r["tokens_tiles"] for r in results)
    gen = [r for r in results if r["source"].startswith("first try")]
    gh, gt = sum(r["tokens_hand"] for r in gen), sum(r["tokens_tiles"] for r in gen)

    def tot(arm, key):
        vals = [r[arm][key] for r in results if r[arm].get(key) is not None]
        return sum(vals) if vals else None

    lines = ["| slide | source | KPI tokens hand → tiles | compiled A / B | broken words A / B | card empty A / B | "
             "low contrast A / B | number sizes A / B | off-plan B | tile issues |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        sz = lambda s: "; ".join("/".join(str(round(x)) for x in sorted(set(v["sizes"] + v["hero"]))) or "-"
                                 for v in (s.get("sizes") or {}).values())
        lines.append(f"| {r['case']} | {r['source']} | {r['tokens_hand']} → {r['tokens_tiles']} | "
                     f"{'ok' if r['A']['compiled'] else 'fail'} / {'ok' if r['B']['compiled'] else 'fail'} | "
                     f"{r['A']['broken']} / {r['B']['broken']} | {sum(r['A']['fill'].values())} / {sum(r['B']['fill'].values())} | "
                     f"{r['A']['low_contrast']} / {r['B']['low_contrast']} | {sz(r['A'])} / {sz(r['B'])} | "
                     f"{len(r['B']['off_plan'])} | {', '.join(c for c in r['issues_B'] if c.startswith('NODE_')) or '-'} |")
    head = [f"{len(results)} KPI slides. KPI output tokens: all **{th} → {tt}** "
            f"({round(100 * (1 - tt / th)) if th else 0}% fewer); genuine first tries {gh} → {gt} "
            f"({round(100 * (1 - gt / gh)) if gh else 0}% fewer). Compiled A / B: "
            f"{sum(r['A']['compiled'] for r in results)} / {sum(r['B']['compiled'] for r in results)}. "
            f"Broken words A / B: {tot('A', 'broken')} / {tot('B', 'broken')}. "
            f"GEOM_CARD_EMPTY A / B: {sum(sum(r['A']['fill'].values()) for r in results)} / "
            f"{sum(sum(r['B']['fill'].values()) for r in results)}. LOW_CONTRAST A / B: {tot('A', 'low_contrast')} / "
            f"{tot('B', 'low_contrast')}.", ""]
    text = "\n".join(head + lines)
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    a.out.mkdir(parents=True)
    results = run(a.out, not a.no_render)
    print(summary(a.out, results))
    if not a.no_render:
        for p in sheets(a.out, results):
            print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
