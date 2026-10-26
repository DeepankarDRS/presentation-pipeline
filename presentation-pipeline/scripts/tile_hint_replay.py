"""Tile / card looks from the design hint, free replay (docs/tile-variant-choice-spec-2026-10-26.md §5 step 2).

    python -m scripts.tile_hint_replay                 # rewrite, compile, render, score -> output/tile-hint-replay/
    python -m scripts.tile_hint_replay --no-render     # skip LibreOffice (no broken-word count, no sheets)
    python -m scripts.tile_hint_replay --limit 5       # the first 5 KPI and 5 card slides (a quick look)

Takes the saved slides whose plan's design_hint gives a look (plan_checks.look_from_hint): KPI slides from
scripts.tile_wide.collect (the LLM's hand tiles rewritten by tile_replay.rewrite, then every `variant` removed: the
bare tags the generator writes, combined check arm B 2026-10-26: 0 of 13 KpiGrids named one), card slides from
scripts.card_replay.collect (a bare <CardGrid> at the LLM's cards' place, its layout kept). Both arms draw the same
tags on the same plan (kpi_tones settled as the planner step does): A = tiles.hint_looks off (today), B = on. Each
goes deck font -> normalize -> compile-pom.js (fit-grow) -> LibreOffice with Inter (card_replay.render), scored with
scripts.kpi_replay.score (compiled, GEOM_*, broken words, WORD_TOO_WIDE, LOW_CONTRAST), KPI number sizes and card
title / body sizes. Counts the looks the hints ask for and the ones B drew (NODE_LOOK_FROM_HINT).
Writes output/tile-hint-replay/: results.json, summary.md, A/ B/, blind sheets (sheets/, marks.csv, key.json).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import statistics
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from lxml import etree  # noqa: E402

from scripts import card_replay as CR  # noqa: E402
from scripts import tile_replay as TR  # noqa: E402
from scripts import tile_wide as TW  # noqa: E402
from scripts.kpi_replay import compile_slide, score  # noqa: E402
from src.agents.plan_checks import look_from_hint, settle_kpi_tones  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import cards as C  # noqa: E402
from src.compiler.nodes import element_refs as E  # noqa: E402
from src.compiler.nodes import tiles as T  # noqa: E402

OUT = ROOT / "output" / "tile-hint-replay"


@contextmanager
def hints(on: bool):
    """tiles.hint_looks on or off (cards.expand calls it through the tiles module)."""
    real = T.hint_looks
    if not on:
        T.hint_looks = lambda *a, **k: None
    try:
        yield
    finally:
        T.hint_looks = real


def asked(plan: dict) -> list[str]:
    """The looks the plan's hints ask for, one entry per group / item ("kpis: bar", "kpis.2: inverted")."""
    out = []
    for c in plan.get("components") or []:
        if c.get("kind") not in ("kpi_row", "card_grid"):
            continue
        lk = look_from_hint(c)
        cid = c["component_id"]
        out += [f"{cid}: {lk['group']}"] if lk["group"] else []
        out += [f"{cid}.{i}: {v}" for i, v in lk["items"].items()]
        out += [f"{cid}: {lk['emphasis']} (emphasis)"] if lk["emphasis"] else []
    return out


def _bare(xml: str) -> str:
    root = TR._parse(xml)
    for el in root.iter(T.GROUP, T.ITEM):
        el.attrib.pop("variant", None)
    return TR._serial(root)


def kpi_rows(limit: int | None) -> list[dict]:
    rows = []
    for r in TW.collect():
        if r.get("error") or not r.get("xml"):
            continue
        plan = copy.deepcopy(r["plan"])
        for c in plan.get("components") or []:
            settle_kpi_tones(c)
        want = asked({"components": list(E.kpi_components(plan).values())})
        if not want:
            continue
        try:
            xml = _bare(TR.rewrite(r["xml"], plan)["xml"])
        except Exception as exc:   # a slide the rewrite cannot read is listed, not dropped silently
            rows.append({"case": r["case"], "kind": "kpi", "asked": want, "skipped": f"rewrite: {type(exc).__name__}"})
            continue
        rows.append({"case": r["case"], "kind": "kpi", "asked": want, "xml": xml, "plan": plan, "theme": r["theme_el"]})
        if limit and len(rows) >= limit:
            break
    return rows


def card_rows(limit: int | None) -> list[dict]:
    rows = []
    for r in CR.collect():
        want = asked({"components": list(C.card_components(r["plan"]).values())})
        if not want:
            continue
        root = CR._parse(r["xml"])
        plan = copy.deepcopy(r["plan"])
        done = []
        for cid, comp in C.card_components(r["plan"]).items():
            res = CR.rewrite_component(root, comp)   # bare <CardGrid>
            done.append(res)
            if "plan_comp" in res:
                plan["components"] = [res["plan_comp"] if c.get("component_id") == cid else c for c in plan["components"]]
        row = {"case": r["case"], "kind": "card", "asked": want}
        if not any("tag" in d for d in done):
            rows.append({**row, "skipped": "; ".join(d.get("skipped", "") for d in done)})
            continue
        rows.append({**row, "xml": CR._serial(root), "plan": plan, "theme": r["theme"]})
        if limit and len([x for x in rows if "xml" in x]) >= limit:
            break
    return rows


def run(out: Path, do_render: bool, limit: int | None) -> list[dict]:
    results = []
    for r in kpi_rows(limit) + card_rows(limit):
        row = {k: r[k] for k in ("case", "kind", "asked", "skipped") if k in r}
        if "skipped" in r:
            results.append(row)
            print(f"{r['case']}: skipped ({r['skipped']})", flush=True)
            continue
        for arm, on in (("A", False), ("B", True)):
            with hints(on):
                fill = T.fill(CR.BARE_AMP.sub("&amp;", r["xml"]), r["plan"])
            dest = out / arm / f"{r['kind']}-{r['case']}" / "slide-1"
            shutil.rmtree(dest, ignore_errors=True)
            comp = compile_slide(deck_font(fill["xml"]), r["theme"], dest)
            if do_render:
                CR.render(dest)
            sc = score(arm, dest, comp, r["plan"], r["case"], do_render)
            sc.pop("off_plan", None)
            final = (dest / "fitted.xml").read_text(encoding="utf-8") if (dest / "fitted.xml").exists() else comp["cleaned"]
            sc["cards"] = CR.card_sizes(final, r["plan"], "B")
            sc["drawn"] = [i["message"] for i in fill["issues"] if i["code"] == "NODE_LOOK_FROM_HINT"]
            sc["issues"] = sorted({i["code"] for i in fill["issues"]} - {"NODE_LOOK_FROM_HINT"})
            row[arm] = sc
        results.append(row)
        print(f"{r['kind']}-{r['case']}: asked {len(r['asked'])}, drawn {len(row['B']['drawn'])}; compiled "
              f"{row['A']['compiled']}/{row['B']['compiled']}; empty {sum(row['A']['fill'].values())}/"
              f"{sum(row['B']['fill'].values())}; broken {row['A']['broken']}/{row['B']['broken']}", flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return results


def _nums(s: dict) -> list[float]:
    return [v for c in s["sizes"].values() for v in (c.get("sizes") or [])] if isinstance(s.get("sizes"), dict) else []


def summary(out: Path, results: list[dict], sheets_n: int) -> str:
    done = [r for r in results if "B" in r]
    skipped = Counter(r["skipped"] for r in results if "skipped" in r)

    def tot(arm, f, kind=None):
        return sum(f(r[arm]) or 0 for r in done if r[arm]["compiled"] and (kind is None or r["kind"] == kind))

    def med(vals):
        return statistics.median(vals) if vals else 0

    variants = Counter(a.split(": ", 1)[1] for r in done for a in r["asked"])
    drawn = Counter(m.split('variant="', 1)[1].split('"', 1)[0] for r in done for m in r["B"]["drawn"])
    lines = [
        "# Tile / card looks from the design hint: free replay", "",
        f"Slides whose hint gives a look: {len(results)} ({sum(r['kind'] == 'kpi' for r in results)} KPI, "
        f"{sum(r['kind'] == 'card' for r in results)} card); replayed {len(done)}; skipped {sum(skipped.values())}"
        + (f" ({', '.join(f'{k} {v}' for k, v in skipped.most_common())})" if skipped else "") + ".", "",
        "A = bare tags (today), B = bare tags + the hint's look. Same tags, same plan.", "",
        "| | A | B |", "|---|---|---|",
        f"| compiled | {sum(r['A']['compiled'] for r in done)} | {sum(r['B']['compiled'] for r in done)} |",
        f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill'].get('GEOM_CARD_EMPTY'))} | {tot('B', lambda s: s['fill'].get('GEOM_CARD_EMPTY'))} |",
        f"| GEOM_SLIDE_SPARSE | {tot('A', lambda s: s['fill'].get('GEOM_SLIDE_SPARSE'))} | {tot('B', lambda s: s['fill'].get('GEOM_SLIDE_SPARSE'))} |",
        f"| broken words (render) | {tot('A', lambda s: s['broken'])} | {tot('B', lambda s: s['broken'])} |",
        f"| WORD_TOO_WIDE | {tot('A', lambda s: s['word_too_wide'])} | {tot('B', lambda s: s['word_too_wide'])} |",
        f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])} | {tot('B', lambda s: s['low_contrast'])} |",
        f"| KPI number px, median | {med([v for r in done if r['kind'] == 'kpi' for v in _nums(r['A'])])} | "
        f"{med([v for r in done if r['kind'] == 'kpi' for v in _nums(r['B'])])} |",
        f"| card title px, median of the smallest | {med([c['title_min'] for r in done if r['kind'] == 'card' for c in r['A']['cards'].values() if c['title_min']])} | "
        f"{med([c['title_min'] for r in done if r['kind'] == 'card' for c in r['B']['cards'].values() if c['title_min']])} |",
        "", f"Looks the hints ask for (per group / item): {dict(variants)}",
        f"Looks B drew (NODE_LOOK_FROM_HINT): {dict(drawn)}",
        f"Other issues A: {dict(Counter(c for r in done for c in r['A']['issues']))}",
        f"Other issues B: {dict(Counter(c for r in done for c in r['B']['issues']))}",
        f"Blind sheets: {sheets_n} pairs in sheets/ (marks.csv; key.json says which side is B)." if sheets_n else "No sheets.",
    ]
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def sheets(out: Path, results: list[dict]) -> int:
    """Pairs where B drew a look (the others are the same slide twice)."""
    from scripts import node_test_sheet as S
    pick = out / "sheet-in"
    shutil.rmtree(pick, ignore_errors=True)
    n = 0
    for r in results:
        if "B" not in r or not r["B"]["drawn"]:
            continue
        for arm in ("A", "B"):
            src = out / arm / f"{r['kind']}-{r['case']}" / "slide-1"
            d = pick / arm / f"{r['kind']}-{r['case']}" / "slide-1"
            d.mkdir(parents=True, exist_ok=True)
            for f in ("presentation.pptx", "presentation.pdf"):
                if (src / f).exists():
                    shutil.copy2(src / f, d / f)
        n += 1
    if n:
        S.build(pick / "B", pick / "A", out / "sheets")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = run(args.out, not args.no_render, args.limit)
    n = sheets(args.out, results) if not args.no_render else 0
    print(summary(args.out, results, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
