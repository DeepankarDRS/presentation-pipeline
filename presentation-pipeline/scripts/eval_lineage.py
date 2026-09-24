"""Content lineage audit: where does a deck lose the brief's headlines and numbers?

    python -m scripts.eval_lineage llm_test/gj-h1-regen-69af33.zip llm_test/gj-h1-regen-bf396b.zip \
        --case tests/cases/gj-h1-regen.yaml --ignore 01,02,03,04,05,26

Each RUN is a run folder or a zip holding one (it must contain the slides.json the evaluator
writes: per slide the plan and the normalized XML). No LLM, no compiler. Per run it reports:

- brief numbers (request + supplied_content) dropped by planning (absent from the slide plan),
  dropped by XML writing (in the plan, absent from the slide XML) and invented at each stage —
  per slide when the brief has "Slide N:" sections, else for the whole deck;
- headlines kept: the golden slide's headline found on the generated slide (non-cover slides;
  needs a golden folder, from --golden or the case's `golden:` field);
- decoration: icons, marker highlights, status dots, shadowed nodes, accent bars, and slides whose
  XML has highlights / icons that no design_hint asked for;
- card consistency: KPI tiles and cards and how many distinct styles they use;
- plan stability: slides planned with the same component kinds in every run given.

The golden deck (XML only) is scored the same way as a reference column.
Method and first results: docs/architecture-north-star.md §3.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

import yaml

from scripts.eval_metrics import _CONTENT_ATTRS, _numbers

_SECTION = re.compile(r"\n\s*Slide (\d+):\s*\n")
_COVERS = {"cover", "section_break"}
_DECORATION = {
    "icons": r"<Icon\b",
    "marker_highlights": r"<Mark\b|\bhighlight=",
    "shadowed_nodes": r"<\w+\b[^>]*\bshadow[.\w]*\s*=",
    "accent_bars": r"border(?:Left|Top)\.width=",
}


# ── Loading ─────────────────────────────────────────────────────────────────

def load_run(path: Path) -> list[dict]:
    """slides.json of a run folder, or of the run folder inside a zip."""
    if path.is_dir():
        return json.loads((path / "slides.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(path) as z:
        names = sorted((n for n in z.namelist() if n.endswith("slides.json")), key=len)
        if not names:
            raise FileNotFoundError(f"{path}: no slides.json")
        return json.loads(z.read(names[0]).decode("utf-8"))


def load_brief(case: dict) -> tuple[str, dict[int, str] | None]:
    """The brief (request + supplied_content) and its "Slide N:" sections, keyed 0-based."""
    request = case.get("request") or ""
    text = request
    if case.get("supplied_content"):
        text += "\n" + json.dumps(case["supplied_content"], ensure_ascii=False)
    parts = _SECTION.split(request)
    sections = {int(parts[i]) - 1: parts[i + 1] for i in range(1, len(parts), 2)}
    return text, sections or None


def golden_headlines(folder: Path, sizes: set[str]) -> list[str]:
    """Per golden slide, the first <Text> whose fontSize is a headline size."""
    heads = []
    for f in sorted(folder.glob("*.xml")):
        head = ""
        for attrs, text in re.findall(r"<Text\b([^>]*)>([^<]*)", f.read_text(encoding="utf-8")):
            m = re.search(r'\bfontSize="([\d.]+)"', attrs)
            if m and m.group(1) in sizes:
                head = text.strip()
                break
        heads.append(head)
    return heads


# ── Text and numbers ────────────────────────────────────────────────────────

def _norm(n: str) -> str:
    return n.rstrip("0").rstrip(".") if "." in n else n


def nums(text: str) -> set[str]:
    """Numbers with ≥ 2 digits (the eval's rule), trailing decimal zeros ignored ("4.40" = "4.4")."""
    return {_norm(n) for n in _numbers(text)}


def _root(xml: str) -> ET.Element | None:
    xml = re.sub(r"<!--.*?-->", "", re.sub(r"<Theme\b[^>]*/>", "", xml), flags=re.S)
    xml = re.sub(r"&(?![a-zA-Z]+;|#\d+;)", "&amp;", xml)
    try:
        return ET.fromstring(f"<r>{xml}</r>")
    except ET.ParseError:
        return None


def slide_text(xml: str) -> str:
    """What a reader can see: element text, text after inline tags (tails), content attributes."""
    root = _root(xml)
    if root is None:  # POM accepts some text a strict parser rejects: read it by regex instead
        bits = [re.sub(r"<[A-Za-z/!?][^>]*>", " ", re.sub(r'[\w.:-]+\s*=\s*"[^"]*"', " ", xml))]
        bits += [v for a in _CONTENT_ATTRS for v in re.findall(rf'\s{a}\s*=\s*"([^"]*)"', xml)]
        return " ".join(bits)
    bits = []
    for el in root.iter():
        bits += [el.text or "", el.tail or ""]
        bits += [el.get(a) for a in _CONTENT_ATTRS if el.get(a)]
    return " ".join(bits)


def _plan(slide: dict) -> dict | None:
    return slide.get("slide_plan")


def _plan_nums(slide: dict) -> set[str]:
    plan = _plan(slide) or {}
    return nums(json.dumps(plan.get("components", []), ensure_ascii=False) + " " + plan.get("slide_title", ""))


def _canon(s: str) -> str:
    return re.sub(r"[^a-z0-9₹%]+", " ", s.replace("&amp;", "&").lower()).strip()


# ── Measures ────────────────────────────────────────────────────────────────

def lineage(slides: list[dict], brief: str, sections: dict[int, str] | None, ignore: set[str]) -> dict:
    """Brief numbers dropped / invented per stage. Slides without a plan (golden) get only `missing_final`."""
    known = nums(brief)
    has_plan = any(_plan(s) for s in slides)
    if sections:
        pairs = [(nums(sections.get(s["slide_index"], "")) - ignore, [s]) for s in slides]
    else:
        pairs = [(known - ignore, slides)]
    t = Counter()
    for brief_nums, group in pairs:
        shown = set().union(*(nums(slide_text(s.get("xml") or "")) for s in group))
        t["brief"] += len(brief_nums)
        t["missing_final"] += len(brief_nums - shown)
        if has_plan:
            planned = set().union(*(_plan_nums(s) for s in group))
            t["dropped_planning"] += len(brief_nums - planned)
            t["dropped_xml"] += len((brief_nums & planned) - shown)
            t["invented_planning"] += len(planned - known)
            t["invented_xml"] += len(shown - planned - known)
    return dict(t)


def headlines(slides: list[dict], heads: list[str]) -> tuple[int, int]:
    """(kept, counted) over slides that are not cover / section_break."""
    kept = counted = 0
    for s in slides:
        i = s["slide_index"]
        if i >= len(heads) or not heads[i] or (_plan(s) or {}).get("slide_type") in _COVERS:
            continue
        counted += 1
        kept += _canon(heads[i]) in _canon(slide_text(s.get("xml") or ""))
    return kept, counted


def _status_dots(xml: str) -> int:
    return sum(1 for tag in re.findall(r"<Shape\b[^>]*>", xml)
               if 'shapeType="ellipse"' in tag and re.search(r'\bw="(?:[4-9]|1[0-4])"', tag))


def decoration(slides: list[dict]) -> dict:
    """Decoration totals, and slides whose hints ask for highlighting / whose XML adds unasked decoration."""
    d = Counter()
    for s in slides:
        xml = s.get("xml") or ""
        for key, pattern in _DECORATION.items():
            d[key] += len(re.findall(pattern, xml))
        d["status_dots"] += _status_dots(xml)
        plan = _plan(s)
        if plan is None:
            continue
        hints = " ".join(c.get("design_hint") or "" for c in plan.get("components", [])).lower()
        asked_highlight = bool(re.search(r"highlight|marker", hints))
        d["slides_hint_highlight"] += asked_highlight
        d["slides_unasked_highlight"] += bool(re.search(_DECORATION["marker_highlights"], xml)) and not asked_highlight
        d["slides_unasked_icons"] += bool(re.search(_DECORATION["icons"], xml)) and "icon" not in hints
    return dict(d)


def _font(el: ET.Element) -> float:
    try:
        return float(el.get("fontSize") or 0)
    except ValueError:
        return 0.0


def styles(slides: list[dict]) -> dict:
    """KPI tiles and cards, and how many distinct styles each uses across the deck."""
    tiles, cards = [], []
    for s in slides:
        root = _root(s.get("xml") or "")
        if root is None:
            continue
        for el in root.iter("VStack"):
            kids = list(el)
            sizes = [_font(t) for t in el.iter("Text")]
            if (2 <= len(kids) <= 5 and all(k.tag in ("Text", "Shape", "Icon", "Chart", "HStack") for k in kids)
                    and sizes and max(sizes) >= 22 and min(sizes) <= 16):
                tiles.append((el.get("padding"), el.get("gap"), el.get("borderRadius"), el.get("backgroundColor"),
                              el.get("justifyContent"),
                              tuple((k.tag, k.get("fontSize"), k.get("bold")) for k in kids)))
            if el.get("backgroundColor") and el.get("padding") and el.get("borderRadius"):
                cards.append((el.get("padding"), el.get("borderRadius"), el.get("border.color") or el.get("border"),
                              any(a.startswith("shadow") for a in el.attrib),
                              any(a.startswith(("borderLeft", "borderTop")) for a in el.attrib)))
    return {"kpi_tiles": len(tiles), "kpi_tile_styles": len(set(tiles)),
            "cards": len(cards), "card_styles": len(set(cards))}


def kinds(slide: dict) -> tuple[str, ...]:
    comps = (_plan(slide) or {}).get("components", [])
    return tuple(sorted(c.get("kind", "") for c in comps if c.get("kind") != "title"))


def stability(runs: dict[str, list[dict]]) -> dict:
    """Slides (present in every run) whose planned component kinds are identical in all runs."""
    per: dict[int, dict[str, tuple[str, ...]]] = {}
    for label, slides in runs.items():
        for s in slides:
            per.setdefault(s["slide_index"], {})[label] = kinds(s)
    common = {i: v for i, v in sorted(per.items()) if len(v) == len(runs)}
    same = sum(1 for v in common.values() if len(set(v.values())) == 1)
    return {"same": same, "slides": len(common),
            "per_slide": {i: {k: list(v) for k, v in row.items()} for i, row in common.items()}}


def score(slides: list[dict], brief: str, sections, ignore: set[str], heads: list[str] | None) -> dict:
    out = {"slides": len(slides), **lineage(slides, brief, sections, ignore), **decoration(slides), **styles(slides)}
    if heads and any(_plan(s) for s in slides):
        out["headlines_kept"], out["headlines_counted"] = headlines(slides, heads)
    return out


# ── Report ──────────────────────────────────────────────────────────────────

def _pct(n: int, total: int) -> str:
    return f"{n} ({round(100 * n / total)}%)" if total else str(n)


_ROWS = [
    ("slides", lambda m: m["slides"]),
    ("headlines kept (non-cover)", lambda m: f"{m['headlines_kept']}/{m['headlines_counted']}"
        if "headlines_kept" in m else "n/a"),
    ("brief numbers", lambda m: m.get("brief", 0)),
    ("dropped by planning", lambda m: _pct(m["dropped_planning"], m["brief"]) if "dropped_planning" in m else "n/a"),
    ("dropped by XML writing", lambda m: _pct(m["dropped_xml"], m["brief"]) if "dropped_xml" in m else "n/a"),
    ("missing on final slides", lambda m: _pct(m.get("missing_final", 0), m.get("brief", 0))),
    ("invented by planning", lambda m: m.get("invented_planning", "n/a")),
    ("invented by XML writing", lambda m: m.get("invented_xml", "n/a")),
    ("slides whose hints ask for highlighting", lambda m: m.get("slides_hint_highlight", "n/a")),
    ("slides with unasked highlights", lambda m: m.get("slides_unasked_highlight", "n/a")),
    ("slides with unasked icons", lambda m: m.get("slides_unasked_icons", "n/a")),
    ("icons", lambda m: m.get("icons", 0)),
    ("marker highlights", lambda m: m.get("marker_highlights", 0)),
    ("status dots", lambda m: m.get("status_dots", 0)),
    ("shadowed nodes", lambda m: m.get("shadowed_nodes", 0)),
    ("accent bars", lambda m: m.get("accent_bars", 0)),
    ("KPI tiles / distinct styles", lambda m: f"{m['kpi_tiles']} / {m['kpi_tile_styles']}"),
    ("cards / distinct styles", lambda m: f"{m['cards']} / {m['card_styles']}"),
]


def report(columns: dict[str, dict]) -> str:
    lines = ["| measure | " + " | ".join(columns) + " |", "|---" * (len(columns) + 1) + "|"]
    for name, cell in _ROWS:
        lines.append(f"| {name} | " + " | ".join(str(cell(m)) for m in columns.values()) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Content lineage audit of saved runs (no LLM, no compiler)")
    parser.add_argument("runs", nargs="+", type=Path, help="run folders or zips holding slides.json")
    parser.add_argument("--case", type=Path, required=True, help="the tests/cases/<case>.yaml the runs were made from")
    parser.add_argument("--golden", type=Path, help="golden XML folder (default: the case's golden: field)")
    parser.add_argument("--ignore", default="", help="comma list of brief numbers to leave out (section numbers, the year)")
    parser.add_argument("--headline-sizes", default="26,27,28,42", help="fontSizes of the golden headline <Text>")
    parser.add_argument("--detail", action="store_true", help="also print the planned component kinds per slide")
    parser.add_argument("--json", type=Path, help="also write all numbers to this JSON file")
    args = parser.parse_args(argv)

    case = yaml.safe_load(args.case.read_text(encoding="utf-8"))
    brief, sections = load_brief(case)
    ignore = {_norm(n.strip()) for n in args.ignore.split(",") if n.strip()}
    golden_dir = args.golden
    if golden_dir is None and case.get("golden"):
        golden_dir = args.case.resolve().parents[2] / case["golden"]
    heads = golden_headlines(golden_dir, set(args.headline_sizes.split(","))) if golden_dir else None

    runs = {(p.stem if p.suffix == ".zip" else p.name): load_run(p) for p in args.runs}
    columns = {label: score(slides, brief, sections, ignore, heads) for label, slides in runs.items()}
    if golden_dir:
        golden = [{"slide_index": i, "xml": f.read_text(encoding="utf-8"), "slide_plan": None}
                  for i, f in enumerate(sorted(golden_dir.glob("*.xml")))]
        columns["golden"] = score(golden, brief, sections, ignore, None)
    stable = stability(runs)

    mode = "per slide ('Slide N:' sections)" if sections else "whole deck (no 'Slide N:' sections in the brief)"
    print(f"Case {case.get('name', args.case.stem)} - numbers counted {mode}\n")
    print(report(columns))
    if len(runs) > 1:
        print(f"\nPlan stability: {stable['same']}/{stable['slides']} slides planned with the same component "
              f"kinds in all {len(runs)} runs")
        if args.detail:
            print("\n| slide | " + " | ".join(runs) + " |\n" + "|---" * (len(runs) + 1) + "|")
            for i, row in stable["per_slide"].items():
                print(f"| {i} | " + " | ".join(", ".join(row[label]) or "-" for label in runs) + " |")
    if args.json:
        args.json.write_text(json.dumps({"case": case.get("name"), "mode": mode, "columns": columns,
                                         "stability": stable}, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
