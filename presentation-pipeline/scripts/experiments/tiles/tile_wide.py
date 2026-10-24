"""KPI tile nodes, wide free evaluation (docs/eval/tile-nodes/wide/README.md). LLM-free.

    python -m scripts.experiments.tiles.tile_wide                    # every saved KPI slide: rewrite, compile, render, score -> output/tile-wide/
    python -m scripts.experiments.tiles.tile_wide --no-render        # skip LibreOffice (no broken-word count, no sheets)
    python -m scripts.experiments.tiles.tile_wide --squeeze          # recompile every saved LLM slide for the w="max" squeeze only

The paid checks judged tiles on 3 slides. This replay takes every saved slide with a kpi_row plan and XML that is
not one of those checks' own outputs: scripts.experiments.tiles.tile_replay's 17 slides plus every other output/**/slides.json
(old gj-h1 / xtsy runs, step 0, 1a, colour roles, critic on, q1008, ...), one per distinct XML. Each goes through
tile_replay's path: typed values mapped to refs (A = today's element-ref route, POM_BLOCKS=kpi), the hand-written
tiles rewritten as tile tags from what the LLM drew (B = POM_BLOCKS=tiles), both filled, normalized, compiled
(fit-grow) and scored with scripts.experiments.kpi.kpi_replay.score. Counted on top, per kpi_row and arm:
  - plan tones, a design hint that asks for colour, and what the tiles draw: semantic colour ($positive /
    $negative / $warning), accent, dark panel, a saturated literal colour, or none;
  - label colour per item, A vs B;
  - the w="max" squeeze (POM `addTextBox: width must be a finite positive EMU value`).
`--squeeze` recompiles every distinct input.xml the pipeline ever compiled (output/ and llm_test/*.zip) on today's
compiler and lists the slides that hit the squeeze, with the w="max" boxes beside each other on them.
Writes output/tile-wide/: results.json, summary.md, pairs/, sheets; squeeze.json / squeeze.md.
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from lxml import etree  # noqa: E402

from scripts.experiments.tiles import tile_replay as TR  # noqa: E402
from scripts.experiments.kpi.kpi_replay import _key, compile_slide, score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import element_refs as E  # noqa: E402
from src.compiler.nodes import tiles as T  # noqa: E402
from src.compiler.palette_tokens import derive_tokens, luminance  # noqa: E402

OUT = ROOT / "output" / "tile-wide"
# the paid checks' own outputs (the same 3 slides, judged there) and runs with no KPI values
SKIP = ("output/kpi-decks/", "output/kpi-decks-2/", "output/kpi-paid", "output/runs/kpi-", "output/runs/dry-prompts",
        "output/runs/hierarchical-e2e", "output/tile-", "output/kpi-replay")
# folders that only recompile saved XML (replays, galleries, experiments): not new LLM slides
REPLAYS = ("replay", "render_check", "gallery", "label-test", "fontexp", "scratch", "tile-check", "tile-prompts",
           "phase0b", "handwritten", "blueprint", "tile-wide", "cardgap", "fit_grow", "embedtest", "guardcheck",
           "rc_repro", "palette_preview", "comparison_check", "cmp", "trace", "variant", "p1exp", "reg0", "reg1")
SQUEEZE = "finite positive EMU"
THEME_RE = re.compile(r"<Theme\b[^>]*/>|<Theme\b.*?</Theme>", re.S)
BARE_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")
HINT_COLOUR = re.compile(r"colou?r|\bred\b|green|amber|negative|positive|warning|sentiment|tone", re.I)
SEMANTIC = re.compile(r"^\$(positive|negative|warning)(Soft|Text)?$")
COLOUR_KEYS = ("color", "backgroundColor", "border.color", "borderLeft.color", "borderTop.color", "fill.color",
               "bgColor", "line.color")


# ── collect ──────────────────────────────────────────────────────────────────

def _theme_element(sj: Path) -> str:
    """The run's theme: its manifest, a saved theme.xml (r2), the case file's theme, else corporate-slate."""
    for m in (sj.parent / "run-manifest.json", sj.parent.parent / "run-manifest.json"):
        if m.exists():
            name = json.loads(m.read_text(encoding="utf-8")).get("theme")
            if name:
                return resolve_theme(name)["element"]
    if (sj.parent / "theme.xml").exists():
        return upgrade_theme((sj.parent / "theme.xml").read_text(encoding="utf-8").strip())
    case_name = re.sub(r"(__r\d+|-[0-9a-f]{6})$", "", sj.parent.name)
    case = ROOT / "tests" / "cases" / f"{case_name}.yaml"
    m = re.search(r"^theme:\s*(\S+)", case.read_text(encoding="utf-8"), re.M) if case.exists() else None
    return resolve_theme(m[1] if m else "corporate-slate")["element"]


def upgrade_theme(element: str) -> str:
    """A saved <Theme> from before the derived tokens (2026-10-06) plus today's derived tokens ($accentText, ...),
    as style_resolver.resolve_theme adds them; tiles use them, so without this an old slide fails on tiles only."""
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', element))
    if "surface" not in attrs or "accentText" in attrs:
        return element
    palette = {**attrs, "mode": "dark" if luminance(attrs["surface"]) < 0.2 else "light"}
    attrs.update(derive_tokens(palette))
    return "<Theme " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + " />"


def _has_values(plan: dict) -> bool:
    return any(E._list(c, "kpi_values") for c in E.kpi_components(plan).values())


def collect() -> list[dict]:
    rows = []
    for r in TR.collect():
        rows.append({**r, "group": "tile-replay", "theme_el": resolve_theme(r["theme"])["element"]})
    seen: set[str] = set()
    for sj in sorted((ROOT / "output").rglob("slides.json")):
        rel = sj.relative_to(ROOT).as_posix()
        if any(rel.startswith(s) for s in SKIP):
            continue
        try:
            slides = json.loads(sj.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(slides, list):
            continue
        theme_el = _theme_element(sj)
        for s in slides:
            plan, xml = s.get("slide_plan") or {}, s.get("xml") or ""
            if not E.kpi_components(plan) or not xml or not _has_values(plan) or "<KpiGrid" in xml or "<Kpi " in xml:
                continue
            h = hashlib.sha1(xml.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            group = rel.split("/")[1]
            run = sj.parent.name.split("__")[0]
            row = {"case": f"{group}-{run}-s{s.get('slide_index', 0)}", "source": group, "group": group,
                   "plan": plan, "theme_el": theme_el}
            try:   # old runs typed a bare & (the normalizer escapes it at compile time)
                row["xml"] = TR._unfill(BARE_AMP.sub("&amp;", xml), plan)
            except etree.XMLSyntaxError as exc:
                row.update(xml="", error=f"unparsable: {exc}")
            rows.append(row)
    names = Counter(r["case"] for r in rows)
    for r in rows:   # the same run name in two folders
        if names[r["case"]] > 1:
            r["case"] += "-" + hashlib.sha1(r["xml"].encode()).hexdigest()[:4]
    return rows


# ── looks: colour and label colour per tile ──────────────────────────────────

def _literal_colour(v: str) -> bool:
    m = re.match(r"^#?([0-9a-fA-F]{6})", v or "")
    if not m:
        return False
    r, g, b = (int(m[1][i:i + 2], 16) / 255 for i in (0, 2, 4))
    _, light, sat = colorsys.rgb_to_hls(r, g, b)
    return sat > 0.3 and 0.15 < light < 0.9


def _kind(v: str) -> str | None:
    if SEMANTIC.match(v or ""):
        return "semantic"
    if (v or "").startswith("$accent"):
        return "accent"
    if v in ("$panelDark",):
        return "dark"
    if _literal_colour(v):
        return "literal"
    return None


def _tile(value: etree._Element) -> etree._Element:
    c = E._container(value)
    return c if c is not None else value.getparent()


def _label_colour(el: etree._Element | None) -> str:
    if el is None:
        return "none"
    v = el.get("color") or ""
    k = _kind(v)
    if k:
        return k
    return {"": "default", "$textMuted": "muted", "$textMain": "ink", "$onPanelDark": "on-dark"}.get(v, "other")


def looks(final_xml: str, plan: dict) -> dict[str, dict]:
    """Per kpi_row: plan tones, hint asks colour, what the tiles draw (colour kinds) and each item's label colour."""
    try:
        root = TR._parse(final_xml)
    except etree.XMLSyntaxError:
        return {}
    texts = list(root.iter("Text"))
    out = {}
    for cid, comp in E.kpi_components(plan).items():
        labels = E._list(comp, "kpi_labels")
        kinds, label_cols = Counter(), []
        for i in range(len(E._list(comp, "kpi_values"))):
            value = next((t for t in texts if re.match(rf"^kpi[vh]\d?-{re.escape(cid)}-{i}$", t.get("id", ""))), None)
            if value is None:
                label_cols.append("missing")
                continue
            tile = _tile(value)
            drawn = {_kind(el.get(k) or "") for el in tile.iter() for k in COLOUR_KEYS} - {None}
            kinds.update(drawn or {"none"})
            lab = None
            if i < len(labels) and labels[i]:
                lab = next((t for t in tile.iter("Text") if t is not value and _key("".join(t.itertext())) == _key(labels[i])),
                           None)
            label_cols.append(_label_colour(lab))
        cd = comp.get("content_data") or {}
        out[cid] = {"items": len(label_cols), "tones": any(str(t or "").strip() for t in cd.get("kpi_tones") or []),
                    "hint_colour": bool(HINT_COLOUR.search(comp.get("design_hint") or "")),
                    "kinds": dict(kinds), "labels": label_cols,
                    "coloured": any(k in kinds for k in ("semantic", "accent", "literal"))}
    return out


# ── run ──────────────────────────────────────────────────────────────────────

CASES: list[str] = []


def run(out: Path, render: bool) -> list[dict]:
    results = []
    for r in collect():
        if CASES and not any(c in r["case"] for c in CASES):
            continue
        d = out / "pairs" / r["case"]
        d.mkdir(parents=True, exist_ok=True)
        row = {"case": r["case"], "group": r["group"], "source": r["source"]}
        if r.get("error"):
            results.append({**row, "error": r["error"]})
            continue
        try:
            rw = TR.rewrite(r["xml"], r["plan"])
            a_fill, b_fill = E.fill_refs(r["xml"], r["plan"]), T.fill(rw["xml"], r["plan"])
        except Exception as exc:   # a slide the rewrite cannot read is listed, not dropped silently
            row["error"] = f"{type(exc).__name__}: {exc}"[:300]
            results.append(row)
            print(f"{r['case']}: rewrite failed: {row['error']}", flush=True)
            continue
        (d / "hand.xml").write_text(r["xml"], encoding="utf-8")
        (d / "tiles.xml").write_text(rw["xml"], encoding="utf-8")
        mapped = len(re.findall(r'ref="[^"]+\.\d+\.value"', r["xml"]))
        row.update({"values": sum(len(E._list(c, "kpi_values")) for c in E.kpi_components(r["plan"]).values()),
                    "mapped": mapped, "notes": rw["notes"], "tile_tags": rw["tile_kpi_xml"],
                    "tokens_hand": TR.tokens(rw["hand_kpi_xml"]), "tokens_tiles": TR.tokens(rw["tile_kpi_xml"]),
                    "issues_B": sorted({i["code"] for i in b_fill["issues"]})})
        for arm, filled in (("A", a_fill), ("B", b_fill)):
            dest = d / arm
            comp = compile_slide(filled["xml"], r["theme_el"], dest)
            row[arm] = score("B", dest, comp, r["plan"], r["case"], render)
            final = (dest / "fitted.xml").read_text(encoding="utf-8") if (dest / "fitted.xml").exists() else comp["cleaned"]
            row[arm]["looks"] = looks(final, r["plan"])
            row[arm]["squeeze"] = any(SQUEEZE in m for m in row[arm]["diagnostics"])
        results.append(row)
        print(f"{r['case']}: values {mapped}/{row['values']}; compiled {row['A']['compiled']}/{row['B']['compiled']}; "
              f"broken {row['A']['broken']}/{row['B']['broken']}; empty {sum(row['A']['fill'].values())}/"
              f"{sum(row['B']['fill'].values())}", flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return results


# ── summary ──────────────────────────────────────────────────────────────────

def _sizes(s: dict) -> list[float]:
    return [x for v in (s.get("sizes") or {}).values() for x in v["sizes"] + v["hero"]]


def summary(out: Path, results: list[dict]) -> str:
    ok = [r for r in results if "A" in r]
    both = [r for r in ok if r["A"]["compiled"] and r["B"]["compiled"]]
    lines = [f"# Tile nodes, wide replay ({len(ok)} KPI slides; {len(results) - len(ok)} the rewrite could not read)", ""]

    def tot(arm, key, rows=both):
        vals = [r[arm][key] for r in rows if r[arm].get(key) is not None]
        return sum(vals) if vals else 0

    mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else 0
    a_sz = [x for r in both for x in _sizes(r["A"])]
    b_sz = [x for r in both for x in _sizes(r["B"])]
    lines += ["| | A element refs | B tiles |", "|---|---|---|",
              f"| compiled | {sum(r['A']['compiled'] for r in ok)} | {sum(r['B']['compiled'] for r in ok)} |",
              f"| squeeze (EMU error) | {sum(r['A']['squeeze'] for r in ok)} | {sum(r['B']['squeeze'] for r in ok)} |",
              f"| broken words (both compiled) | {tot('A', 'broken')} | {tot('B', 'broken')} |",
              f"| WORD_TOO_WIDE | {tot('A', 'word_too_wide')} | {tot('B', 'word_too_wide')} |",
              f"| GEOM_CARD_EMPTY | {sum(r['A']['fill'].get('GEOM_CARD_EMPTY', 0) for r in both)} | "
              f"{sum(r['B']['fill'].get('GEOM_CARD_EMPTY', 0) for r in both)} |",
              f"| GEOM_SLIDE_SPARSE | {sum(r['A']['fill'].get('GEOM_SLIDE_SPARSE', 0) for r in both)} | "
              f"{sum(r['B']['fill'].get('GEOM_SLIDE_SPARSE', 0) for r in both)} |",
              f"| LOW_CONTRAST | {tot('A', 'low_contrast')} | {tot('B', 'low_contrast')} |",
              f"| values off plan | {sum(len(r['A']['off_plan']) for r in both)} | {sum(len(r['B']['off_plan']) for r in both)} |",
              f"| number size mean / min (px) | {mean(a_sz)} / {min(a_sz, default=0):g} | {mean(b_sz)} / {min(b_sz, default=0):g} |",
              f"| sizes per slide: B larger / equal / smaller | "
              f"{sum(mean(_sizes(r['B'])) > mean(_sizes(r['A'])) + 0.5 for r in both)} / "
              f"{sum(abs(mean(_sizes(r['B'])) - mean(_sizes(r['A']))) <= 0.5 for r in both)} / "
              f"{sum(mean(_sizes(r['B'])) < mean(_sizes(r['A'])) - 0.5 for r in both)} | |",
              f"| values mapped to refs | {sum(r['mapped'] for r in ok)} / {sum(r['values'] for r in ok)} | |",
              f"| KPI output tokens (replaced XML vs tags) | {sum(r['tokens_hand'] for r in ok)} | {sum(r['tokens_tiles'] for r in ok)} |",
              ""]
    # colour per kpi_row
    comps = [(r, cid, r["A"]["looks"].get(cid), r["B"]["looks"].get(cid)) for r in both for cid in r["A"]["looks"]]
    comps = [c for c in comps if c[2] and c[3]]
    no_tone = [c for c in comps if not c[2]["tones"]]
    lines += [f"## Colour ({len(comps)} kpi_rows on slides both arms compiled)", "",
              f"- plan has tones: {len(comps) - len(no_tone)}; no tones: {len(no_tone)}",
              f"- no tones and the design hint asks colour: {sum(c[2]['hint_colour'] for c in no_tone)}",
              f"- no tones, A draws colour (semantic / accent / literal): {sum(c[2]['coloured'] for c in no_tone)}; "
              f"semantic: {sum('semantic' in c[2]['kinds'] for c in no_tone)}",
              f"- no tones, B draws colour: {sum(c[3]['coloured'] for c in no_tone)}; semantic: "
              f"{sum('semantic' in c[3]['kinds'] for c in no_tone)}",
              f"- no tones, neither draws any colour: {sum(not c[2]['coloured'] and not c[3]['coloured'] for c in no_tone)} "
              f"(of them hint asks colour: {sum(not c[2]['coloured'] and not c[3]['coloured'] and c[2]['hint_colour'] for c in no_tone)})",
              f"- A coloured, B not: {sum(c[2]['coloured'] and not c[3]['coloured'] for c in comps)}; "
              f"B coloured, A not: {sum(c[3]['coloured'] and not c[2]['coloured'] for c in comps)}", ""]
    la = Counter(x for c in comps for x in c[2]["labels"])
    lb = Counter(x for c in comps for x in c[3]["labels"])
    pairs = Counter((x, y) for c in comps for x, y in zip(c[2]["labels"], c[3]["labels"]))
    lines += ["## Label colour per item", "", "| label colour | A | B |", "|---|---|---|"]
    lines += [f"| {k} | {la.get(k, 0)} | {lb.get(k, 0)} |" for k in sorted(set(la) | set(lb))]
    lines += ["", "A → B (items): " + ", ".join(f"{a} → {b}: {n}" for (a, b), n in pairs.most_common()), ""]
    # per slide
    lines += ["## Per slide", "",
              "| slide | group | mapped | compiled A / B | broken A / B | card empty A / B | contrast A / B | "
              "mean size A / B | tones | colour A / B | labels A / B |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ok:
        la_, lb_ = r["A"]["looks"], r["B"]["looks"]
        col = lambda lk: ",".join("+".join(sorted(v["kinds"])) for v in lk.values()) or "-"
        lab = lambda lk: ",".join("/".join(sorted(set(v["labels"]))) for v in lk.values()) or "-"
        lines.append(f"| {r['case']} | {r['group']} | {r['mapped']}/{r['values']} | "
                     f"{'ok' if r['A']['compiled'] else 'FAIL'} / {'ok' if r['B']['compiled'] else 'FAIL'} | "
                     f"{r['A']['broken']} / {r['B']['broken']} | {r['A']['fill'].get('GEOM_CARD_EMPTY', 0)} / "
                     f"{r['B']['fill'].get('GEOM_CARD_EMPTY', 0)} | {r['A']['low_contrast']} / {r['B']['low_contrast']} | "
                     f"{mean(_sizes(r['A']))} / {mean(_sizes(r['B']))} | "
                     f"{'yes' if any(v['tones'] for v in la_.values()) else '-'} | {col(la_)} / {col(lb_)} | {lab(la_)} / {lab(lb_)} |")
    for r in results:
        if "error" in r:
            lines.append(f"| {r['case']} | {r['group']} | rewrite failed: {r['error'][:80]} |")
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


# ── squeeze scan ─────────────────────────────────────────────────────────────

def _inputs():
    """(name, xml) for every distinct input.xml the pipeline compiled, output/ and llm_test zips."""
    seen = set()
    for p in sorted((ROOT / "output").rglob("input.xml")):
        rel = p.relative_to(ROOT).as_posix()
        if any(k in rel for k in REPLAYS):
            continue
        b = p.read_bytes()
        h = hashlib.sha1(b).hexdigest()
        if h not in seen:
            seen.add(h)
            yield rel, b.decode("utf-8", "replace")
    for z in sorted((ROOT / "llm_test").glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if n.endswith("/input.xml"):
                    b = zf.read(n)
                    h = hashlib.sha1(b).hexdigest()
                    if h not in seen:
                        seen.add(h)
                        yield f"{z.name}:{n}", b.decode("utf-8", "replace")


def max_neighbours(xml: str) -> list[str]:
    """HStacks with a w="max" child beside another child: the boxes and their text lengths."""
    try:
        root = TR._parse(re.sub(r"<Theme\b.*?</Theme>|<Theme\b[^>]*/>", "", xml, flags=re.S))
    except etree.XMLSyntaxError:
        return ["(unparsable)"]
    out = []
    for h in root.iter("HStack"):
        kids = [k for k in h if isinstance(k.tag, str)]
        if len(kids) > 1 and any(k.get("w") == "max" for k in kids):
            out.append(" | ".join(f"{k.tag}{' w=max' if k.get('w') == 'max' else ' w=' + (k.get('w') or '-')}"
                                  f"{' grow' if k.get('grow') else ''} ({len(''.join(k.itertext()).strip())} ch)"
                                  for k in kids))
    return out


def squeeze_scan(out: Path) -> str:
    import tempfile
    rows, n = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, xml in _inputs():
            n += 1
            boxes = max_neighbours(xml)
            if not boxes:   # no w="max" box beside another: this squeeze cannot happen, no compile needed
                rows.append({"name": name, "compiled": None, "squeeze": False, "max_neighbours": 0, "boxes": []})
                continue
            theme = THEME_RE.search(xml)   # the normalizer strips the slide's own <Theme>: pass it back in
            theme_el = upgrade_theme(theme[0]) if theme else resolve_theme("corporate-slate")["element"]
            comp = compile_slide(xml, theme_el, Path(tmp) / str(n))
            diags = [d.get("message", "") for d in comp["res"].get("diagnostics") or []]
            hit = any(SQUEEZE in m for m in diags)
            kpi = "kpiv" in xml or "<KpiGrid" in xml
            rows.append({"name": name, "compiled": comp["res"].get("status") == "success", "squeeze": hit, "kpi_ids": kpi,
                         "diagnostics": [m[:160] for m in diags[:2]],
                         "max_neighbours": len(boxes), "boxes": boxes if hit else []})
            if n % 25 == 0:
                print(f"{n} compiled, squeeze {sum(r['squeeze'] for r in rows)}", flush=True)
    (out / "squeeze.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    hits = [r for r in rows if r["squeeze"]]
    lines = [f"# w=\"max\" squeeze on today's compiler", "",
             f"{len(rows)} distinct compiled slides (input.xml in output/ and llm_test zips, replays skipped); "
             f"{sum(r['max_neighbours'] > 0 for r in rows)} have a w=\"max\" box beside another box and were compiled "
             f"(the others cannot hit it); of those compiled {sum(bool(r['compiled']) for r in rows)}, "
             f"squeeze {len(hits)}.", "",
             "| slide | the HStacks with w=max (children: tag, width, text length) |", "|---|---|"]
    lines += [f"| {r['name']} | {'<br>'.join(r['boxes'])} |" for r in hits]
    text = "\n".join(lines) + "\n"
    (out / "squeeze.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--squeeze", action="store_true", help="only the squeeze scan over every saved compiled slide")
    ap.add_argument("--look", nargs="*", default=[], metavar="KEY=VALUE",
                    help="free experiment: override the KPI tiles' house look (block-variants.yaml), e.g. padding=16 gap=6")
    ap.add_argument("--cases", nargs="*", default=[], help="only slides whose name contains one of these")
    a = ap.parse_args()
    T.kpi()["house_look"].update(dict(kv.split("=", 1) for kv in a.look))
    global CASES
    CASES = a.cases
    a.out.mkdir(parents=True, exist_ok=True)
    if a.squeeze:
        print(squeeze_scan(a.out))
        return 0
    shutil.rmtree(a.out / "pairs", ignore_errors=True)
    results = run(a.out, not a.no_render)
    print(summary(a.out, results))
    if not a.no_render:
        for p in TR.sheets(a.out, [r for r in results if "A" in r]):
            print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
