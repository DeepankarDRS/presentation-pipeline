"""Composition nodes, free replay with the LLM's own layout kept (left-blocks spec §13 step 5, POM_NODES).

    python -m scripts.node_replay --kind chart --src C:/dev/presentation-pipeline/presentation-pipeline/output
    python -m scripts.node_replay --kind timeline --variant rows    # arm B draws that composition instead
    python -m scripts.node_replay --kind flow --no-render --limit 5
    (python -m scripts.chart_replay = --kind chart)

--kind: chart, timeline, process_arrow, flow, table or bullet_list. Takes every saved slide whose plan has one component of that kind with
an id and whose XML has exactly one LLM-drawn node of its tag (<Chart>, <Timeline>, <ProcessArrow>, <Flow>), one per
distinct XML (output/**/slides.json under --src, replays and galleries skipped). Arm A is the slide as the LLM wrote it.
Arm B is the same XML with the LLM's node replaced by one <Tag ref> at its place: its card too (the nearest box around
it, when that box holds nothing but the node and Texts made of the component's own words: a title row, a legend), with
that box's or the node's layout attributes (w, h, grow...). Everything else stays as the LLM drew it. The tag is bare
unless --variant is given.

Both arms: deck font -> normalize -> compile-pom.js (fit-grow, pptx-post) -> LibreOffice with Inter, scored with
scripts.kpi_replay.score (broken words, GEOM_*, LOW_CONTRAST), plus the component's own data against the plan (chart:
labels and values missing or changed; timeline / process / flow: items whose words are not all on the slide) and the
node XML's output tokens (o200k: the replaced region vs its tag). Writes output/<kind>-replay[-<variant>]/:
results.json, summary.md, A/ B/, blind sheets (sheets/, marks.csv; key.json says which side is which).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_NODES"] = "chart,timeline,process_arrow,flow,table,bullet_list"

from lxml import etree  # noqa: E402

from scripts.card_replay import BARE_AMP, SKIP, _parse, _serial, overlaps, render, tokens  # noqa: E402
from scripts.card_replay import sheets as card_sheets  # noqa: E402
from scripts.kpi_replay import _theme, compile_slide, score  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import bullets, compose, composed, native, sequences, tables  # noqa: E402
LAYOUT_KEYS = ("w", "h", "grow", "minW", "maxW", "minH", "maxH", "alignSelf")
SKIPPED: list[str] = []   # saved slides that could not be parsed
_WORD = re.compile(r"[a-z0-9₹$%]+")


def words(s: str) -> set[str]:
    return set(_WORD.findall(str(s or "").lower()))


def collect(src: Path, kind: str, limit: int | None = None) -> list[dict]:
    tag = composed.tag(kind)
    rows, seen = [], set()
    for sj in sorted(src.rglob("slides.json")):
        rel = sj.relative_to(src).as_posix()
        if any(k in rel for k in SKIP + ("composition", "chart-")):
            continue
        try:
            slides = json.loads(sj.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(slides, list):
            continue
        for s in slides:
            plan, xml = s.get("slide_plan") or {}, s.get("xml") or ""
            comps = composed.drawn(plan, kind)
            if not xml or len(comps) != 1 or len(re.findall(rf"<{tag}\b", xml)) != 1 or f"<{tag} ref" in xml:
                continue
            h = hashlib.sha1(xml.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            run = sj.parent.name.split("__")[0][:40]
            rows.append({"case": f"{rel.split('/')[0]}-{run}-s{s.get('slide_index', 0)}-{h[:4]}", "source": rel,
                         "plan": plan, "xml": xml, "theme": _theme(sj)})
    return rows[:limit] if limit else rows


def own_words(comp: dict) -> set[str]:
    """The component's own words: chart title, series and labels; a sequence's dates and items; a table's cells."""
    cd = comp.get("content_data") or {}
    if comp["kind"] == "table":
        return {w for c in plan_items(comp) for w in words(c)}
    if comp["kind"] == "chart":
        return words(cd.get("chart_title")) | {w for s in cd.get("chart_series") or [] for w in words(s.get("name"))} \
            | {w for v in cd.get("chart_labels") or [] for w in words(v)}
    return {w for d, h, x in sequences.items(comp) for w in words(f"{d} {h} {x}")}


def chart_card(chart: etree._Element, comp: dict) -> etree._Element:
    """The element the tag replaces: the nearest boxed stack around the node when it holds only the node and Texts
    made of the component's own words (a title row, a legend), else the node itself."""
    own = own_words(comp)
    def heading(k: etree._Element) -> bool:
        """A Text, Icon or stack of them whose words are mostly the chart's own (its title row, a legend)."""
        if any(d.tag not in ("Text", "Span", "B", "I", "Icon", "Shape", "HStack", "VStack") for d in k.iter() if isinstance(d.tag, str)):
            return False
        ws = words("".join(k.itertext()))
        return len(ws & own) >= 0.6 * len(ws)

    el, p = chart, chart.getparent()
    while p is not None and p.tag in ("VStack", "HStack") and p.getparent() is not None and p.getparent().tag != "Slide":
        others = [k for k in p if isinstance(k.tag, str) and k is not el]
        if not all(heading(k) for k in others):
            break
        el = p
        if p.get("backgroundColor") or p.get("border.color") or p.get("shadow.type"):
            return el
        p = p.getparent()
    return el if el is not chart and (el.get("backgroundColor") or el.get("border.color")) else chart


_TONE_OF = (("negative", "bad"), ("positive", "good"), ("warning", "watch"), ("accent", "focus"))


def _tone(v: str | None, focus: bool = True) -> str:
    """A colour token's tone: $negative* bad, $positive* good, $warning* watch, $accent* focus; else ""."""
    v = str(v or "")
    return next((t for k, t in _TONE_OF if k in v and (focus or t != "focus")), "") if v.startswith("$") else ""


def llm_marks(table: etree._Element, comp: dict) -> list[str]:
    """The LLM's own colour coding of its <Table> as <Highlight> marks on the plan's names (user 2026-11-02: can the
    tag reproduce it?): a body row whose every cell has one fill / text tone -> a row mark; a column likewise (no focus:
    a whole column in the accent is the LLM's look, not an emphasis); other toned cells -> cell marks; toned <Span>s
    -> phrase marks. All of them, in that order (the node draws them all)."""
    cols, rows = tables.grid(comp)
    norm = lambda s: " ".join(str(s).split()).casefold()  # noqa: E731
    trs = [t for t in table if t.tag == "Tr"]
    body = trs[1:] if trs and len(trs) == len(rows) + 1 else trs[-len(rows):] if rows else []
    labels = [norm(r[0]) for r in rows]
    grid_ = []   # (plan row, [(fill, ink, spans) per column])
    for i, tr in enumerate(body):
        tds = [td for td in tr if td.tag == "Td"]
        r = labels.index(norm("".join(tds[0].itertext()))) if tds and norm("".join(tds[0].itertext())) in labels else i
        if r >= len(rows) or len(tds) != len(cols):
            continue
        grid_.append((r, [(_tone(td.get("backgroundColor")), _tone(td.get("color")),
                           [("".join(s.itertext()).strip(), _tone(s.get("color"))) for s in td.iter("Span") if _tone(s.get("color"))])
                          for td in tds]))
    marks, done = [], set()   # done: (r, c, "fill" / "color") covered
    q = lambda s: native.x(s).replace('"', "&quot;")  # noqa: E731
    for r, cells in grid_:
        for k, attr in ((0, "fill"), (1, "color")):
            ts = {c[k] for c in cells}
            if len(ts) == 1 and next(iter(ts)):
                marks.append(f'<Highlight row="{q(rows[r][0])}" {attr}="{next(iter(ts))}"/>')
                done |= {(r, c, attr) for c in range(len(cols))}
    for c in range(len(cols)):
        for k, attr in ((0, "fill"), (1, "color")):
            col =[cells[c][k] for r, cells in grid_ if (r, c, attr) not in done]
            if len(grid_) > 1 and col and len(set(col)) == 1 and col[0] and col[0] != "focus" and len(col) == len(grid_):
                marks.append(f'<Highlight column="{q(cols[c])}" {attr}="{col[0]}"/>')
                done |= {(r, c, attr) for r, _ in grid_}
    for r, cells in grid_:
        for c, (fill, ink, spans) in enumerate(cells):
            at = {a: t for a, t in (("fill", fill), ("color", ink)) if t and (r, c, a) not in done}
            if at:
                marks.append(f'<Highlight cell="{q(rows[r][0])} / {q(cols[c])}"' + "".join(f' {a}="{t}"' for a, t in at.items()) + "/>")
    for r, cells in grid_:
        for c, (_, ink, spans) in enumerate(cells):
            for text, tone in spans:
                if text and (r, c, "color") not in done and text.lower() in rows[r][c].lower():
                    marks.append(f'<Highlight phrase="{q(text)}" color="{tone}"/>')
    return marks


def bullet_marks(ul: etree._Element, comp: dict) -> tuple[dict, list[str], Counter]:
    """The LLM's own styling of its <Ul> as the tag's attributes and <Highlight>s (user 2026-11-04: can the tag replicate
    the native attributes?). Returns (tag attributes, marks, what happened to each native attribute): carried, code (the
    node writes it by itself), code-owned (sizes and fonts), changed (Mark -> colour, the user's rule), lost."""
    pts, how, attrs, marks = bullets.items(comp), Counter(), {}, []
    q = lambda s: native.x(s).replace('"', "&quot;")  # noqa: E731
    norm = lambda s: " ".join(str(s).split()).casefold()  # noqa: E731
    pieces = [p for s in pts for p in compose.split(s) if p]
    for k, v in ul.attrib.items():
        if k == "color":
            if v == "$textMain":
                how["list color: default"] += 1
            elif v.startswith("$"):
                attrs["color"] = v
                how["list color: carried"] += 1
            else:
                how["list color: lost (not a token)"] += 1
        elif k in ("fontSize", "lineHeight", "fontFamily"):
            how[f"list {k}: code-owned"] += 1
        elif k in ("bold", "italic", "textAlign"):
            attrs["detail.bold" if k == "bold" else k] = v
            how[f"list {k}: carried"] += 1
        elif k not in LAYOUT_KEYS:
            how[f"list {k}: lost"] += 1
    for li in ul:
        if li.tag != "Li":
            continue
        text = norm("".join(li.itertext()))
        hit = next((s for s in pts if norm(s) == text), None)
        for k, v in li.attrib.items():
            if k in ("fontSize", "fontFamily"):
                how[f"li {k}: code-owned"] += 1
            elif hit is None:
                how[f"li {k}: lost (point not in the plan as written)"] += 1
            elif k == "color" and _tone(v):
                marks.append(f'<Highlight item="{q(hit)}" color="{_tone(v)}"/>')
                how["li color: carried"] += 1
            elif k == "bold" and v == "true":
                marks.append(f'<Highlight item="{q(hit)}" bold="true"/>')
                how["li bold: carried"] += 1
            else:
                how[f"li {k}: lost ({v})"] += 1
        for e in li.iter():
            if e is li or not isinstance(e.tag, str):
                continue
            words = "".join(e.itertext()).strip()
            bold = e.tag == "B" or e.get("bold") == "true"
            tone = _tone(e.get("color"))
            for k in ("fontSize", "fontFamily"):
                if e.get(k):
                    how[f"inline {k}: code-owned"] += 1
            if e.tag == "Icon":
                how["Icon in Li: POM strips it (rows + icons replaces it)"] += 1
                continue
            in_plan = any(words.lower() in p.lower() for p in pieces) if words else False
            if not tone and not bold and e.tag != "Mark":
                how[f"inline {e.tag}: no effect"] += 1
            elif not in_plan:
                how[f"inline {e.tag}: lost (words not one piece of the plan's point)"] += 1
            elif not tone and bold and any(norm(words).rstrip(":") == norm(compose.split(s)[0]) for s in pts):
                how["bold lead-in: code draws it"] += 1
            elif e.tag == "Mark":
                if tone:
                    marks.append(f'<Highlight phrase="{q(words)}" color="{tone}"/>')
                how["Mark: changed to colour (user rule)" if tone else "Mark: lost (no tone)"] += 1
            elif tone or bold:
                marks.append(f'<Highlight phrase="{q(words)}"' + (f' color="{tone}"' if tone else "")
                             + (' bold="true"' if bold else "") + "/>")
                how[f"inline {e.tag} {'colour' if tone else 'bold'}: carried"] += 1
    return attrs, list(dict.fromkeys(marks)), how


def rewrite(root: etree._Element, comp: dict, variant: str, marks_from_llm: bool = False) -> dict:
    tag = composed.tag(comp["kind"])
    chart = next(root.iter(tag))
    marks = llm_marks(chart, comp) if marks_from_llm and comp["kind"] == "table" else []
    extra, how = {}, Counter()
    if marks_from_llm and comp["kind"] == "bullet_list":
        extra, marks, how = bullet_marks(chart, comp)
    # a table or list node draws no card or title: the LLM keeps its own around the tag (user marks 2026-11-02: on 38
    # slides the replay had dropped the card and its title row)
    el = chart if comp["kind"] in ("table", "bullet_list") else chart_card(chart, comp)
    keep = {k: v for k, v in el.attrib.items() if k in LAYOUT_KEYS}
    if el is not chart:   # a card's height is the chart's plus the card's title row and padding (the LLM sized the chart)
        chrome = sum(float(el.get(k) or el.get("padding") or 0) for k in ("padding.top", "padding.bottom")) \
            + 30 * (len([k for k in el if isinstance(k.tag, str)]) > 1)
        keep.update({k: str(round(float(v) + chrome)) for k, v in chart.attrib.items()
                     if k in ("h", "minH") and k not in keep and re.fullmatch(r"\d+(?:\.\d+)?", v)})
    old = _serial(el)
    attrs = {"ref": comp["component_id"], **({"variant": variant} if variant else {}), **keep, **extra}
    head = f"<{tag}" + "".join(f' {k}="{native.x(v)}"' for k, v in attrs.items())
    tag = f"{head}>{''.join(marks)}</{tag}>" if marks else head + " />"
    new = etree.fromstring(tag)
    new.tail = el.tail
    el.getparent().replace(el, new)
    return {"old": old, "tag": tag, "card": el is not chart, "marks": len(marks), "native": dict(how)}


_SHOWN = ("label", "title", "text", "date", "description")


def plan_items(comp: dict) -> list[str]:
    """What `drawn_data` checks is on the slide: a sequence's items (date head detail), a table's cells."""
    if comp["kind"] == "table":
        cols, rows = tables.grid(comp)
        return [c for c in cols + [v for r in rows for v in r] if c.strip()]
    if comp["kind"] == "bullet_list":
        return bullets.items(comp)
    return [f"{d} {h} {x}".strip() for d, h, x in sequences.items(comp)]


def drawn_data(final_xml: str, comp: dict) -> dict:
    """The drawn component against the plan. Chart: labels missing, values changed (A: the LLM's <Chart>; B: the
    node's). Timeline / process / flow: the plan items whose words are not all on the slide (text and item attributes)."""
    cd = comp.get("content_data") or {}
    if comp["kind"] != "chart":
        root = _parse(re.sub(r"<Theme\b[^>]*/>", "", final_xml))
        seen = words(" ".join(root.itertext()) + " " + " ".join(v for e in root.iter() if isinstance(e.tag, str)
                                                                    for k, v in e.attrib.items() if k in _SHOWN))
        return {"items_missing": [i for i in plan_items(comp) if not words(i) <= seen]}
    labels = [str(v) for v in cd.get("chart_labels") or []]
    series = cd.get("chart_series") or [{"values": cd.get("chart_values") or []}]
    plan_vals = sorted(round(native.number(v), 6) for s in series for v in s.get("values") or [])
    root = _parse(re.sub(r"<Theme\b[^>]*/>", "", final_xml))
    pts = [p for p in root.iter("ChartDataPoint")]
    if not pts:   # rows: the values are Texts
        texts = ["".join(t.itertext()) for t in root.iter("Text")]
        return {"labels_missing": [lb for lb in labels if lb not in texts],
                "values_changed": sum(1 for s in series for v in s.get("values") or [] if str(v) not in texts)}
    got_labels = {p.get("label") for p in pts}
    got_vals = sorted(round(float(p.get("value") or 0), 6) for p in pts)
    return {"labels_missing": [lb for lb in labels if lb not in got_labels],
            "values_changed": sum(1 for a, b in zip(plan_vals, got_vals) if abs(a - b) > 1e-6) + abs(len(plan_vals) - len(got_vals))}


def run(src: Path, out: Path, do_render: bool, limit: int | None, variant: str, only: list[str] | None = None,
        kind: str = "chart", marks_from_llm: bool = False) -> list[dict]:
    results = []
    for r in collect(src, kind, limit):
        if only and not any(o in r["case"] for o in only):
            continue
        comp = next(iter(composed.drawn(r["plan"], kind).values()))
        try:
            root = _parse(r["xml"])
        except etree.XMLSyntaxError as e:   # the saved slide is not well-formed XML (an unescaped "<" in an attribute)
            SKIPPED.append(f"{r['case']}: {e}")
            print(f"{r['case']}: skipped, not well-formed ({e})", flush=True)
            continue
        done = rewrite(root, comp, variant, marks_from_llm)
        expanded = composed.expand(_serial(root), r["plan"])
        row = {"case": r["case"], "source": r["source"], "card": done["card"], "tag": done["tag"], "marks": done["marks"], "native": done["native"],
               "b_issues": [i["code"] for i in expanded["issues"]], "drawn": expanded["components"],
               "tokens": {"A": tokens(done["old"]), "B": tokens(done["tag"])}}
        for arm, xml in (("A", BARE_AMP.sub("&amp;", r["xml"])), ("B", expanded["xml"])):
            dest = out / arm / r["case"] / "slide-1"
            shutil.rmtree(dest, ignore_errors=True)
            res = compile_slide(deck_font(xml), r["theme"], dest)
            if do_render:
                render(dest)
            sc = score(arm, dest, res, copy.deepcopy(r["plan"]), r["case"], do_render)
            sc.pop("sizes", None), sc.pop("off_plan", None)
            sc["data"] = drawn_data(res["cleaned"], comp)
            sc["overlaps"] = overlaps(dest / "presentation.pdf" if (dest / "presentation.pdf").exists() else None)
            row[arm] = sc
        print(f"{r['case']}: A {row['A']['compiled']} broken {row['A']['broken']} data {row['A']['data']} | "
              f"B {row['B']['compiled']} broken {row['B']['broken']} data {row['B']['data']} "
              f"tokens {row['tokens']['A']} -> {row['tokens']['B']}", flush=True)
        results.append(row)
    return results


def summary(out: Path, results: list[dict], variant: str, kind: str = "chart") -> str:
    def tot(arm, f):
        return sum(f(r[arm]) or 0 for r in results if r[arm]["compiled"])

    ta, tb = sum(r["tokens"]["A"] for r in results), sum(r["tokens"]["B"] for r in results)
    used = Counter(c["composition"] for r in results for c in r["drawn"].values())
    tag = composed.tag(kind)
    data = ([f"| chart labels missing vs the plan | {tot('A', lambda s: len(s['data']['labels_missing']))} | {tot('B', lambda s: len(s['data']['labels_missing']))} |",
             f"| chart values changed vs the plan | {tot('A', lambda s: s['data']['values_changed'])} | {tot('B', lambda s: s['data']['values_changed'])} |"]
            if kind == "chart" else
            [f"| plan items not all on the slide | {tot('A', lambda s: len(s['data']['items_missing']))} | {tot('B', lambda s: len(s['data']['items_missing']))} |"])
    lines = [
        f"# {tag} node: free replay (LLM layout kept), arm B = <{tag} ref{' variant=' + repr(variant) if variant else ''}>", "",
        f"Slides: {len(results)} (one {kind} component with an id, one LLM-drawn <{tag}>); the LLM's card around it replaced "
        f"too on {sum(r['card'] for r in results)}. B compositions: {dict(used)}."
        + (f" Skipped (not well-formed XML): {len(SKIPPED)}." if SKIPPED else ""), "",
        f"| | A (LLM's {kind}) | B ({tag} tag) |", "|---|---|---|",
        f"| compiled | {sum(r['A']['compiled'] for r in results)} | {sum(r['B']['compiled'] for r in results)} |",
        *data,
        f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill']['GEOM_CARD_EMPTY'])} | {tot('B', lambda s: s['fill']['GEOM_CARD_EMPTY'])} |",
        f"| GEOM_SLIDE_SPARSE | {tot('A', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} | {tot('B', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} |",
        f"| broken words (render) | {tot('A', lambda s: s['broken'])} | {tot('B', lambda s: s['broken'])} |",
        f"| text overlaps (render) | {sum(len(r['A'].get('overlaps', [])) for r in results)} | {sum(len(r['B'].get('overlaps', [])) for r in results)} |",
        f"| WORD_TOO_WIDE | {tot('A', lambda s: s['word_too_wide'])} | {tot('B', lambda s: s['word_too_wide'])} |",
        f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])} | {tot('B', lambda s: s['low_contrast'])} |",
        f"| {kind} output tokens | {ta} | {tb} ({(tb - ta) / ta:+.0%}) |" if ta else f"| {kind} output tokens | 0 | 0 |",
        "", f"B issues: {dict(Counter(c for r in results for c in r['b_issues']))}",
        *([f"Highlights from the LLM's colours: {sum(1 for r in results if r.get('marks'))} slides with marks; "
           f"marks per table {dict(sorted(Counter(r.get('marks', 0) for r in results).items()))} "
           f"(more than {tables.MANY_HIGHLIGHTS}: {sum(1 for r in results if r.get('marks', 0) > tables.MANY_HIGHLIGHTS)})"]
          if any(r.get("marks") for r in results) else []),
        *(["", "What became of the LLM's native list attributes:", "",
           *(f"- {k}: {v}" for k, v in sorted(sum((Counter(r.get("native") or {}) for r in results), Counter()).items()))]
          if any(r.get("native") for r in results) else []),
    ]
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kind", default="chart", choices=("chart", *sequences.KINDS, "table", "bullet_list"))
    ap.add_argument("--src", type=Path, default=ROOT / "output", help="the folder holding saved runs' slides.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--variant", default="", help="composition for arm B (default: a bare tag)")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="*", help="cases whose name contains one of these")
    ap.add_argument("--marks-from-llm", action="store_true",
                    help="table / bullet_list: arm B gets <Highlight> marks made from the LLM's own colour coding")
    a = ap.parse_args()
    base = ROOT / "output" / f"{a.kind.replace('_', '-')}-replay"
    out = a.out or (base.with_name(f"{base.name}-{a.variant.replace(' ', '-')}") if a.variant else base)
    if a.marks_from_llm and not a.out:
        out = out.with_name(out.name + "-marks")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    results = run(a.src, out, not a.no_render, a.limit, a.variant, a.only, a.kind, a.marks_from_llm)
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    if not a.no_render:
        print(f"sheets: {card_sheets(out, results)} pairs")
    print(summary(out, results, a.variant, a.kind))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
