"""KPI tile and card composition nodes, free replay on the saved slides (composition spec §10 step 4, §9 Q5 / R6).

    python -m scripts.composition_replay --src C:/dev/presentation-pipeline/presentation-pipeline/output
    python -m scripts.composition_replay --only card --limit 5 --no-render

Takes the saved slides the free replays of the tile nodes take (KPI: scripts.kpi_replay.collect, the LLM's hand-drawn
ref tiles rewritten as one tile tag by scripts.tile_replay.rewrite; cards: scripts.card_replay.collect /
rewrite_component), the LLM's own layout kept around the tag. Both arms get the BARE tag (ref and layout attributes):
- A: today's tile node, <KpiGrid ref> / <CardGrid ref> under POM_BLOCKS=tiles (tiles.fill: the hint's style looks);
- B: the composition node, <KpiRow ref> / <CardGrid ref> under POM_NODES=kpi_row,card_grid (tile_groups.expand: the
  composition the design hint asks for, else the default chosen from the content, then fill_refs).
Same compile path (deck font -> normalize -> compile-pom.js -> LibreOffice with Inter), scored with
scripts.kpi_replay.score (broken words, GEOM_*, LOW_CONTRAST) plus plan text missing. Writes output/composition-replay/:
results.json, summary.md (the scorecard), A/ B/, and blind sheets (sheets/, marks.csv; key.json) of the pairs whose
drawing differs.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from scripts import card_replay as CR  # noqa: E402
from scripts import kpi_replay as KR  # noqa: E402
from scripts import tile_replay as TR  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import cards, tile_groups, tiles  # noqa: E402

OUT = ROOT / "output" / "composition-replay"
LAYOUT = set(CR.LAYOUT_KEYS)
_TAG = re.compile(r"<(KpiGrid|Kpi|CardGrid|Card)\b([^<>]*?)(/?)>")


def bare(xml: str) -> str:
    """Every tile tag with only its ref and layout attributes; a group's item tags dropped (bare = the group draws all)."""
    xml = re.sub(r"<(KpiGrid|CardGrid)\b([^<>]*?)>(.*?)</\1>", r"<\1\2/>", xml, flags=re.S)

    def keep(m: re.Match) -> str:
        attrs = {k: v for k, v in re.findall(r'([\w.]+)="([^"]*)"', m.group(2)) if k == "ref" or k in LAYOUT}
        return f"<{m.group(1)}" + "".join(f' {k}="{v}"' for k, v in attrs.items()) + "/>"
    return _TAG.sub(keep, xml)


def as_composition(xml: str) -> str:
    return re.sub(r"<KpiGrid\b", "<KpiRow", xml)


def collect(src: Path, only: list[str], limit: int | None) -> list[dict]:
    rows = []
    if "kpi" in only:
        KR.ROOT = src.parent   # its SOURCES are globs under <ROOT>/output
        for r in KR.collect():
            xml = TR._unfill(r["xml"], r["plan"])
            rw = TR.rewrite(xml, r["plan"])
            if not rw["tile_kpi_xml"]:
                continue
            rows.append({"kind": "kpi", "case": f"kpi-{r['case']}-s{r['slide']}", "plan": r["plan"],
                         "theme": r["theme"], "tags": bare(rw["xml"])})
        KR.ROOT = ROOT
    if "card" in only:
        CR.ROOT = src.parent
        for r in CR.collect():
            root, plan = CR._parse(r["xml"]), copy.deepcopy(r["plan"])
            done = []
            for cid, comp in cards.card_components(r["plan"]).items():
                res = CR.rewrite_component(root, comp)
                if "plan_comp" in res:   # stand-ins read from the LLM's drawing (old plans: no focus / tone / phrase)
                    plan["components"] = [res["plan_comp"] if c.get("component_id") == cid else c for c in plan["components"]]
                    done.append(cid)
            if done:
                rows.append({"kind": "card", "case": f"card-{r['case']}", "plan": plan, "theme": r["theme"],
                             "tags": bare(CR._serial(root))})
        CR.ROOT = ROOT
    seen, out = set(), []
    for r in rows:   # one per distinct tag XML + plan
        key = r["tags"] + json.dumps(r["plan"].get("components"), sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out[:limit] if limit else out


def arm_b(xml: str, plan: dict) -> dict:
    os.environ["POM_NODES"] = "kpi_row,card_grid"
    try:
        drawn = tile_groups.expand(as_composition(xml), plan)
        filled = tiles.fill(drawn["xml"], plan)
    finally:
        os.environ.pop("POM_NODES", None)
    return {"xml": filled["xml"], "issues": drawn["issues"] + filled["issues"], "components": drawn["components"]}


def run(out: Path, src: Path, only: list[str], do_render: bool, limit: int | None) -> list[dict]:
    results = []
    for r in collect(src, only, limit):
        a = tiles.fill(r["tags"], r["plan"])
        b = arm_b(r["tags"], r["plan"])
        row = {"case": r["case"], "kind": r["kind"], "tags": r["tags"],
               "compositions": {cid: v["composition"] for cid, v in b["components"].items()},
               "a_issues": sorted({i["code"] for i in a["issues"]}), "b_issues": sorted({i["code"] for i in b["issues"]}),
               "b_errors": [i["message"] for i in b["issues"] if i["severity"] == "error"]}
        for arm, xml in (("A", a["xml"]), ("B", b["xml"])):
            dest = out / arm / r["case"] / "slide-1"
            shutil.rmtree(dest, ignore_errors=True)
            comp = KR.compile_slide(deck_font(CR.BARE_AMP.sub("&amp;", xml)), r["theme"], dest)
            if do_render:
                CR.render(dest)
            sc = KR.score(arm, dest, comp, r["plan"], r["case"], do_render)
            final = (dest / "fitted.xml").read_text(encoding="utf-8") if (dest / "fitted.xml").exists() else comp["cleaned"]
            sc.pop("sizes", None)
            sc["missing"] = CR.missing_text(final, r["plan"]) if r["kind"] == "card" else sc.pop("off_plan", [])
            sc["final"] = final
            row[arm] = sc
        row["same"] = row["A"].pop("final") == row["B"].pop("final")
        print(f"{r['case']}: {row['compositions']} A {row['A']['compiled']} B {row['B']['compiled']} "
              f"broken {row['A']['broken']}/{row['B']['broken']} empty {sum(row['A']['fill'].values())}/"
              f"{sum(row['B']['fill'].values())}{' same' if row['same'] else ''}", flush=True)
        results.append(row)
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return results


def sheets(out: Path, results: list[dict]) -> int:
    """Blind pairs of the slides whose drawing differs (node_test_sheet: B = composition, A = today, sides shuffled)."""
    from scripts import node_test_sheet as S
    pick = out / "sheet-in"
    shutil.rmtree(pick, ignore_errors=True)
    n = 0
    for r in results:
        if r["same"]:
            continue
        for arm in ("A", "B"):
            s, d = out / arm / r["case"] / "slide-1", pick / arm / r["case"] / "slide-1"
            d.mkdir(parents=True, exist_ok=True)
            for f in ("presentation.pptx", "presentation.pdf"):
                if (s / f).exists():
                    shutil.copy2(s / f, d / f)
        n += 1
    if n:
        S.build(pick / "B", pick / "A", out / "sheets")
    return n


def summary(out: Path, results: list[dict], n_sheet: int) -> str:
    lines = ["# KPI / card compositions: free replay (bare tags, LLM layout kept)", "",
             "A = today's tile node (<KpiGrid> / <CardGrid>, POM_BLOCKS=tiles); B = the composition node (<KpiRow> / "
             "<CardGrid>, POM_NODES): the composition the design hint asks for, else the default from the content.", ""]
    for kind in ("kpi", "card"):
        rs = [r for r in results if r["kind"] == kind]
        if not rs:
            continue

        def tot(arm, f):
            return sum(v for v in (f(r[arm]) for r in rs if r[arm]["compiled"]) if v is not None)
        comps = Counter(c for r in rs for c in r["compositions"].values())
        lines += [f"## {kind.upper()}: {len(rs)} slides ({sum(r['same'] for r in rs)} drawn the same)", "",
                  "Compositions in B: " + ", ".join(f"{k} {v}" for k, v in comps.most_common()), "",
                  "| | A today | B composition |", "|---|---|---|",
                  f"| compiled | {sum(r['A']['compiled'] for r in rs)} | {sum(r['B']['compiled'] for r in rs)} |",
                  f"| GEOM_CARD_EMPTY | {tot('A', lambda s: s['fill']['GEOM_CARD_EMPTY'])} | {tot('B', lambda s: s['fill']['GEOM_CARD_EMPTY'])} |",
                  f"| GEOM_SLIDE_SPARSE | {tot('A', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} | {tot('B', lambda s: s['fill']['GEOM_SLIDE_SPARSE'])} |",
                  f"| broken words (render) | {tot('A', lambda s: s['broken'])} | {tot('B', lambda s: s['broken'])} |",
                  f"| WORD_TOO_WIDE | {tot('A', lambda s: s['word_too_wide'])} | {tot('B', lambda s: s['word_too_wide'])} |",
                  f"| LOW_CONTRAST | {tot('A', lambda s: s['low_contrast'])} | {tot('B', lambda s: s['low_contrast'])} |",
                  f"| plan text missing / off plan | {sum(len(r['A']['missing']) for r in rs)} | {sum(len(r['B']['missing']) for r in rs)} |",
                  f"| B errors | | {sum(len(r['b_errors']) for r in rs)} |", "",
                  "B issues: " + ", ".join(f"{k} {v}" for k, v in Counter(c for r in rs for c in r["b_issues"]).most_common()), ""]
    lines += [f"Blind sheet: {n_sheet} pairs whose drawing differs, in sheets/ (marks.csv; key.json says which side is "
              "which)."]
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, default=ROOT / "output", help="the output/ folder holding the saved runs")
    ap.add_argument("--only", nargs="*", default=["kpi", "card"], choices=["kpi", "card"])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = run(args.out, args.src, args.only, not args.no_render, args.limit)
    n = sheets(args.out, results) if not args.no_render else 0
    print(summary(args.out, results, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
