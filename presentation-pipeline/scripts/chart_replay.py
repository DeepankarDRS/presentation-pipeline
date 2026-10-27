"""Chart composition node, free replay with the LLM's own layout kept (left-blocks spec §13 step 5, POM_NODES=chart).

    python -m scripts.chart_replay --src C:/dev/presentation-pipeline/presentation-pipeline/output
    python -m scripts.chart_replay --variant rows          # arm B draws that composition instead of the default
    python -m scripts.chart_replay --no-render --limit 5

Takes every saved slide whose plan has a chart component with an id and whose XML has exactly one hand-drawn <Chart>,
one per distinct XML (output/**/slides.json under --src, replays and galleries skipped). Arm A is the slide as the LLM
wrote it. Arm B is the same XML with the LLM's chart replaced by one <Chart ref> tag at its place: its card too (the
nearest box around it, when that box holds nothing but the chart and Texts naming the chart's title / series), with
that box's or the Chart's layout attributes (w, h, grow...). Everything else stays as the LLM drew it. The tag is bare
unless --variant is given.

Both arms: deck font -> normalize -> compile-pom.js (fit-grow, pptx-post) -> LibreOffice with Inter, scored with
scripts.kpi_replay.score (broken words, GEOM_*, LOW_CONTRAST), plus the chart's own data against the plan (labels and
values the drawn chart misses or changes) and the chart XML's output tokens (o200k: the replaced region vs its tag).
Writes output/chart-replay[-<variant>]/: results.json, summary.md, A/ B/, blind sheets (sheets/, marks.csv; key.json
says which side is which).
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
os.environ["POM_NODES"] = "chart"

from lxml import etree  # noqa: E402

from scripts.card_replay import BARE_AMP, SKIP, _parse, _serial, overlaps, render, tokens  # noqa: E402
from scripts.card_replay import sheets as card_sheets  # noqa: E402
from scripts.kpi_replay import _theme, compile_slide, score  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import charts as C  # noqa: E402
from src.compiler.nodes import native  # noqa: E402

OUT = ROOT / "output" / "chart-replay"
LAYOUT_KEYS = ("w", "h", "grow", "minW", "maxW", "minH", "maxH", "alignSelf")
_WORD = re.compile(r"[a-z0-9₹$%]+")


def words(s: str) -> set[str]:
    return set(_WORD.findall(str(s or "").lower()))


def collect(src: Path, limit: int | None = None) -> list[dict]:
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
            comps = C.chart_components(plan)
            if not xml or len(comps) != 1 or len(re.findall(r"<Chart\b", xml)) != 1 or "<Chart ref" in xml:
                continue
            h = hashlib.sha1(xml.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            run = sj.parent.name.split("__")[0][:40]
            rows.append({"case": f"{rel.split('/')[0]}-{run}-s{s.get('slide_index', 0)}-{h[:4]}", "source": rel,
                         "plan": plan, "xml": xml, "theme": _theme(sj)})
    return rows[:limit] if limit else rows


def chart_card(chart: etree._Element, comp: dict) -> etree._Element:
    """The element the tag replaces: the nearest boxed stack around the chart when it holds only the chart and Texts
    made of the chart's own words (title, series names), else the Chart itself."""
    cd = comp.get("content_data") or {}
    own = words(cd.get("chart_title")) | {w for s in cd.get("chart_series") or [] for w in words(s.get("name"))} \
        | {w for v in cd.get("chart_labels") or [] for w in words(v)}
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


def rewrite(root: etree._Element, comp: dict, variant: str) -> dict:
    chart = next(root.iter("Chart"))
    el = chart_card(chart, comp)
    keep = {k: v for k, v in el.attrib.items() if k in LAYOUT_KEYS}
    if el is not chart:   # a card's height is the chart's when the card sized itself to it
        keep.update({k: v for k, v in chart.attrib.items() if k in ("h", "minH") and k not in keep and v != "max"})
    old = _serial(el)
    attrs = {"ref": comp["component_id"], **({"variant": variant} if variant else {}), **keep}
    tag = "<Chart" + "".join(f' {k}="{native.x(v)}"' for k, v in attrs.items()) + " />"
    new = etree.fromstring(tag)
    new.tail = el.tail
    el.getparent().replace(el, new)
    return {"old": old, "tag": tag, "card": el is not chart}


def drawn_data(final_xml: str, comp: dict) -> dict:
    """The drawn chart against the plan: labels missing, values changed (A: the LLM's <Chart>; B: the node's)."""
    cd = comp.get("content_data") or {}
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


def run(src: Path, out: Path, do_render: bool, limit: int | None, variant: str) -> list[dict]:
    results = []
    for r in collect(src, limit):
        comp = next(iter(C.chart_components(r["plan"]).values()))
        root = _parse(r["xml"])
        done = rewrite(root, comp, variant)
        expanded = C.expand(_serial(root), r["plan"])
        row = {"case": r["case"], "source": r["source"], "card": done["card"], "tag": done["tag"],
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


def summary(out: Path, results: list[dict], variant: str) -> str:
    def tot(arm, f):
        return sum(f(r[arm]) or 0 for r in results if r[arm]["compiled"])

    ta, tb = sum(r["tokens"]["A"] for r in results), sum(r["tokens"]["B"] for r in results)
    used = Counter(c["composition"] for r in results for c in r["drawn"].values())
    lines = [
        f"# Chart node: free replay (LLM layout kept), arm B = <Chart ref{' variant=' + repr(variant) if variant else ''}>", "",
        f"Slides: {len(results)} (one chart component with an id, one hand-drawn <Chart>); the LLM's chart card replaced "
        f"with the chart on {sum(r['card'] for r in results)}. B compositions: {dict(used)}.", "",
        "| | A (LLM's chart) | B (Chart tag) |", "|---|---|---|",
        f"| compiled | {sum(r['A']['compiled'] for r in results)} | {sum(r['B']['compiled'] for r in results)} |",
        f"| chart labels missing vs the plan | {tot('A', lambda s: len(s['data']['labels_missing']))} | {tot('B', lambda s: len(s['data']['labels_missing']))} |",
        f"| chart values changed vs the plan | {tot('A', lambda s: s['data']['values_changed'])} | {tot('B', lambda s: s['data']['values_changed'])} |",
        f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill']['GEOM_CARD_EMPTY'])} | {tot('B', lambda s: s['fill']['GEOM_CARD_EMPTY'])} |",
        f"| GEOM_SLIDE_SPARSE | {tot('A', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} | {tot('B', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} |",
        f"| broken words (render) | {tot('A', lambda s: s['broken'])} | {tot('B', lambda s: s['broken'])} |",
        f"| text overlaps (render) | {sum(len(r['A'].get('overlaps', [])) for r in results)} | {sum(len(r['B'].get('overlaps', [])) for r in results)} |",
        f"| WORD_TOO_WIDE | {tot('A', lambda s: s['word_too_wide'])} | {tot('B', lambda s: s['word_too_wide'])} |",
        f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])} | {tot('B', lambda s: s['low_contrast'])} |",
        f"| chart output tokens | {ta} | {tb} ({(tb - ta) / ta:+.0%}) |" if ta else "| chart output tokens | 0 | 0 |",
        "", f"B issues: {dict(Counter(c for r in results for c in r['b_issues']))}",
    ]
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, default=ROOT / "output", help="the folder holding saved runs' slides.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--variant", default="", help="composition for arm B (default: a bare tag)")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    out = a.out or (OUT.with_name(f"chart-replay-{a.variant.replace(' ', '-')}") if a.variant else OUT)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    results = run(a.src, out, not a.no_render, a.limit, a.variant)
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    if not a.no_render:
        print(f"sheets: {card_sheets(out, results)} pairs")
    print(summary(out, results, a.variant))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
