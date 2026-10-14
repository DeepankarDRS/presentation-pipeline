"""Tile nodes, combined paid check: fresh plans (planner gives KPI icons), then both routes draw every KPI / card slide.

    python -m scripts.tile_combined --label combined --bundle                 # paid, test PC: plans + draws (+ scores)
    python -m scripts.tile_combined --label combined --rescore                # free, build PC: scores, renders, blind sheet
    python -m scripts.tile_combined --label combined-dry --dry                # free: fake LLMs, checks the path end to end

What it checks (docs/eval/tile-nodes/combined/README.md): the prompt / planner changes after the same-plan check
(docs/eval/tile-nodes/same-plan/README.md) and the card paid check (docs/eval/card-nodes/paid/README.md):
  1. the tile and card prompt lines say "never type a label, value or note / a title, tag or body yourself"
     (the tile route typed KPI tiles with invented numbers on 2 / 2 runs of one plan; cards drew QBR r2 by hand);
  2. the planner gives each KPI item an icon (kpi_icons), as cards got per-card icons (agency 2: the element-ref side
     won on its decorated tiles).
Part 1 runs the planners only (scripts.kpi_plan_only.plan_case) on CASES, once each. Part 2 draws every planned slide
with a kpi_row or a card_grid twice per repeat: arm A POM_BLOCKS=kpi (element refs; cards drawn by hand), arm B
POM_BLOCKS=tiles (KPI and card tags), the real graph from the slide plan (scripts.kpi_paid.run_one: generator,
validator, repairers; critic off). Same plan, same theme, so only the drawing differs.
Scored per slide (rescore, build PC: Inter render): KPI number sizes, card title / body sizes, GEOM_CARD_EMPTY, broken
words, overlaps, plan text missing, values off the plan; from the first try: NODE_* errors, KPI tiles and cards drawn
by hand (B), icons drawn. Writes output/tile-combined/<label>/: plans.json, runs.json, results.json, summary.md,
sheets/ (blind A / B: fill marks.csv; key.json: the 'nodes' side is tiles); --bundle zips it with run.log.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import kpi_paid as KP  # noqa: E402

CASES = ["deck-qbr-data", "deck-product-launch-data", "gate-deck-agency-takeover", "gate-deck-all-nodes-dense",
         "gate-deck-cheffin-full", "gate-deck-xtsy-qcomm"]
OUT = ROOT / "output" / "tile-combined"
ARMS = (("A", "kpi"), ("B", "tiles"))
DEFAULT_THEME = "corporate-slate"


def _kinds(plan: dict) -> set[str]:
    return {c.get("kind") for c in plan.get("components") or []} & {"kpi_row", "card_grid"}


# ── part 1: plans (paid) ──────────────────────────────────────────────────────

def make_plans(out: Path, cases: list[str], dry: bool = False) -> list[dict]:
    """Every planned slide with a kpi_row or a card_grid: {name, case, slide, plan, theme, request}."""
    from src.utils.case_loader import load_case
    items, runs = [], []
    for name in cases:
        case = load_case(name)
        rid = f"combined-plan-{name}-{int(time.time())}"
        print(f"plan {name} ...", flush=True)
        if dry:   # the same-plan inputs and the card paid inputs of this case stand in for a fresh plan
            plans = [it["plan"] for it in _dry_plans() if it["case"] == name]
            res = {"slide_plans": [dict(p, slide_index=i) for i, p in enumerate(plans)], "cost_usd": 0.0}
        else:
            try:
                from scripts.kpi_plan_only import plan_case
                res = plan_case(case, rid)
            except Exception as e:   # one failure must not cost the other cases
                print(f"  failed: {e}", flush=True)
                res = {"slide_plans": [], "cost_usd": 0.0, "error": str(e)[:300]}
        runs.append({"case": name, "run_id": rid, **{k: v for k, v in res.items() if k != "outline"}})
        for p in res.get("slide_plans") or []:
            if _kinds(p):
                items.append({"name": f"{name}-s{p.get('slide_index')}", "case": name, "slide": p.get("slide_index"),
                              "plan": p, "theme": case.get("theme") or DEFAULT_THEME,
                              "request": case.get("request", case.get("objective", ""))})
        print(f"  ${res.get('cost_usd', 0):.3f}; KPI / card slides: "
              + ", ".join(f"s{p.get('slide_index')} {'+'.join(sorted(_kinds(p)))}" for p in res.get("slide_plans") or [] if _kinds(p)),
              flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / "plans.json").write_text(json.dumps({"runs": runs, "items": items}, indent=1, ensure_ascii=False, default=str),
                                    encoding="utf-8")
    return items


def _dry_plans() -> list[dict]:
    kpi = json.loads((ROOT / "docs/eval/tile-nodes/same-plan/inputs.json").read_text(encoding="utf-8"))
    card = json.loads((ROOT / "docs/eval/card-nodes/paid-inputs.json").read_text(encoding="utf-8"))
    seen, out = set(), []
    for it in [i for i in kpi if i["plan_from"] == "tiles"] + card:
        key = (it["case"], it["slide"])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _dry_xml(plan: dict, blocks: str) -> str:
    """--dry: a slide of bare tags (B), or the plain tiles / cards they expand to (A)."""
    from src.compiler.nodes import cards, tiles
    tags = "".join(f'<KpiGrid ref="{c["component_id"]}"/>' if c.get("kind") == "kpi_row" else f'<CardGrid ref="{c["component_id"]}"/>'
                   for c in plan.get("components") or [] if c.get("kind") in ("kpi_row", "card_grid"))
    xml = (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
           f'<Text fontSize="36" bold="true" color="$textMain">{html.escape(plan.get("slide_title", ""))}</Text>'
           f'<VStack gap="18" grow="1">{tags}</VStack></VStack></Slide>')
    if blocks == "tiles":
        return xml
    return tiles.expand(cards.expand(xml, plan)["xml"], plan)["xml"]


# ── part 2: draws (paid) ──────────────────────────────────────────────────────

def icons_drawn(xml: str, plan: dict) -> tuple[int, int]:
    """(KPI items whose plan icon is on the slide, KPI items with a plan icon)."""
    planned = [x for c in plan.get("components") or [] if c.get("kind") == "kpi_row"
               for x in (c.get("content_data") or {}).get("kpi_icons") or []]
    names = re.findall(r'<Icon\b[^>]*\bname="([^"]+)"', xml)
    return sum(1 for x in planned if x in names), len(planned)


def draw(out: Path, items: list[dict], repeat: int, dry: bool = False) -> list[dict]:
    from scripts.card_paid import card_tokens
    runs = []
    for r in range(1, repeat + 1):
        for it in items:
            for arm, blocks in ARMS:
                os.environ["POM_BLOCKS"] = blocks
                case = f"{it['name']}-r{r}"
                rid = f"combined-{blocks}-{it['case']}-s{it['slide']}-r{r}-{int(time.time())}"
                print(f"run {case} {blocks} ...", flush=True)
                try:
                    if dry:
                        from src.agents import generator
                        generator.get_llm = lambda step, _x=_dry_xml(it["plan"], blocks): KP._FakeLLM(_x)
                    res = KP.run_one(it, rid)
                except Exception as e:   # one failure must not cost the other runs
                    res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                           "final_xml": "", "first_xml": "", "cost_usd": 0.0, "validator_passes": 0, "generator_calls": 0}
                d = out / arm / case
                d.mkdir(parents=True, exist_ok=True)
                (d / "plan.json").write_text(json.dumps(it["plan"], indent=1, ensure_ascii=False), encoding="utf-8")
                (d / "final.xml").write_text(res["final_xml"], encoding="utf-8")
                first = res.get("first_xml") or ""
                if first:
                    (d / "first.xml").write_text(first, encoding="utf-8")
                row = {"case": case, "arm": arm, "blocks": blocks, "item": it["name"], "repeat": r, "run_id": rid,
                       "kinds": sorted(_kinds(it["plan"])),
                       **{k: v for k, v in res.items() if k not in ("final_xml", "first_xml")}}
                if arm == "B" and first and "card_grid" in row["kinds"]:
                    row["card_tokens"], row["hand_cards"] = card_tokens(first, it["plan"])
                row["icons_first"] = list(icons_drawn(first, it["plan"])) if first else None
                runs.append(row)
                print(f"  first ok={res['first_ok']} hand KPI={res.get('hand_items')} hand cards={row.get('hand_cards')} "
                      f"passes={res['validator_passes']} final ok={res['final_ok']} ${res['cost_usd']:.3f}", flush=True)
                (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    return runs


# ── scoring (free) ────────────────────────────────────────────────────────────

def _score(arm: str, d: Path, xml: str, theme: str, plan: dict, case: str, render: bool) -> dict:
    from scripts import card_replay as R
    from scripts.kpi_replay import score
    shutil.rmtree(d, ignore_errors=True)
    comp = R.compile_slide(R.deck_font(xml), theme, d)
    if render:
        R.render(d)
    sc = score(arm, d, comp, plan, case, render)
    final = (d / "fitted.xml").read_text(encoding="utf-8") if (d / "fitted.xml").exists() else comp["cleaned"]
    sc["cards"] = R.card_sizes(final, plan, arm)
    sc["missing"] = R.missing_text(final, plan)
    sc["overlaps"] = R.overlaps(d / "presentation.pdf" if (d / "presentation.pdf").exists() else None)
    sc["icons"] = list(icons_drawn(final, plan))
    return sc


def rescore(out: Path, render: bool = True) -> list[dict]:
    from src.agents.style_resolver import resolve_theme
    items = {it["name"]: it for it in json.loads((out / "plans.json").read_text(encoding="utf-8"))["items"]}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        it = items[row["item"]]
        d = out / row["arm"] / row["case"]
        xml = (d / "final.xml").read_text(encoding="utf-8") if (d / "final.xml").exists() else ""
        row["score"] = _score(row["arm"], d / "slide-0", xml, resolve_theme(it["theme"])["element"], it["plan"],
                              row["case"], render) if xml else None
    (out / "results.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts import node_test_sheet as S
        S.build(out / "B", out / "A", out / "sheets")   # B (tiles) plays the "nodes" role in key.json
    write_summary(out, runs)
    return runs


def _min(vals: list) -> float | None:
    vals = [v for v in vals if v]
    return min(vals) if vals else None


def write_summary(out: Path, runs: list[dict]) -> None:
    plans = json.loads((out / "plans.json").read_text(encoding="utf-8"))
    kpis = [c for it in plans["items"] for c in it["plan"].get("components") or [] if c.get("kind") == "kpi_row"]
    grids = [c for it in plans["items"] for c in it["plan"].get("components") or [] if c.get("kind") == "card_grid"]
    lines = ["# Tile nodes, combined check (A = POM_BLOCKS=kpi, B = POM_BLOCKS=tiles, same fresh plans)", "",
             f"- **Plans**: {len(plans['runs'])} planner runs, ${sum(r.get('cost_usd') or 0 for r in plans['runs']):.3f}; "
             f"{len(plans['items'])} slides with a kpi_row or card_grid; kpi_rows {len(kpis)}, with kpi_icons "
             f"{sum(1 for c in kpis if (c.get('content_data') or {}).get('kpi_icons'))}; card_grids {len(grids)}, with icons "
             f"{sum(1 for c in grids if all((x or {}).get('icon') for x in (c.get('content_data') or {}).get('cards') or [{}]))}."]
    for arm, blocks in ARMS:
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        err = sum(1 for r in rs if any(i.get("severity") == "error" for i in r.get("first_issues") or []))
        lines.append(f"- **{arm} ({blocks})**: {len(rs)} runs, ${sum(r.get('cost_usd') or 0 for r in rs):.3f}; first try "
                     f"compiled {sum(1 for r in rs if r.get('first_ok'))}/{len(rs)}, NODE_* error on the first try {err}, "
                     f"final compiled {sum(1 for r in rs if r.get('final_ok'))}/{len(rs)}, repair passes "
                     f"{sum(max(0, (r.get('validator_passes') or 1) - 1) for r in rs)}"
                     + (f"; KPI tiles typed by hand {sum(r.get('hand_items') or 0 for r in rs)}, cards drawn by hand "
                        f"{sum(r.get('hand_cards') or 0 for r in rs)}" if arm == "B" else ""))
    lines += ["", "| slide | KPI number A / B (px) | card title A / B | empty A / B | broken A / B | missing A / B | "
                  "off-plan A / B | icons A / B | first A / B | $ A / B |", "|---|---|---|---|---|---|---|---|---|---|"]
    by = {(r["case"], r["arm"]): r for r in runs}
    for case in dict.fromkeys(r["case"] for r in runs):
        a, b = by.get((case, "A"), {}), by.get((case, "B"), {})
        sa, sb = a.get("score") or {}, b.get("score") or {}
        num = lambda s: _min([x for c in (s.get("sizes") or {}).values() for x in c["sizes"] + c["hero"]])
        title = lambda s: _min([c.get("title_min") for c in (s.get("cards") or {}).values()])
        fill = lambda s: sum((s.get("fill") or {}).values()) if s else "-"
        ic = lambda s: "/".join(map(str, s.get("icons") or [])) or "-"
        lines.append(f"| {case} | {num(sa)} / {num(sb)} | {title(sa)} / {title(sb)} | {fill(sa)} / {fill(sb)} | "
                     f"{sa.get('broken')} / {sb.get('broken')} | {len(sa.get('missing') or [])} / {len(sb.get('missing') or [])} | "
                     f"{len(sa.get('off_plan') or [])} / {len(sb.get('off_plan') or [])} | {ic(sa)} / {ic(sb)} | "
                     f"{'ok' if a.get('first_ok') else 'fail'} / {'ok' if b.get('first_ok') else 'fail'} | "
                     f"{a.get('cost_usd', 0):.3f} / {b.get('cost_usd', 0):.3f} |")
    lines += ["", "Blind sheet: sheets/ (fill marks.csv; key.json: the 'nodes' side is tiles)."]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def bundle(out: Path) -> Path:
    z = out.parent / f"{out.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in out.rglob("*"):
            if p.is_file() and p.suffix != ".pptx":
                f.write(p, p.relative_to(out.parent))
    return z


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases", nargs="*", default=CASES)
    ap.add_argument("--label", default="combined")
    ap.add_argument("--repeat", type=int, default=2, help="draws per slide plan and arm")
    ap.add_argument("--rescore", action="store_true", help="free: score saved runs again (build PC: renders)")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: fake planner (saved plans) and generator")
    a = ap.parse_args()
    out = OUT / a.label
    if not a.rescore:
        if not a.dry:
            if not os.environ.get("OPENAI_API_KEY"):
                from dotenv import load_dotenv
                load_dotenv(ROOT / ".env")
            if not os.environ.get("OPENAI_API_KEY"):
                print("OPENAI_API_KEY is not set (.env): the paid check runs on the test PC")
                return 2
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True, exist_ok=True)
        from src.utils.logging_config import add_file_log, setup_logging
        setup_logging()
        add_file_log(out / "run.log")
        items = make_plans(out, a.cases, dry=a.dry)
        draw(out, items, a.repeat, dry=a.dry)
    rescore(out, render=not a.no_render)
    if a.bundle:
        print(f"EMAIL THIS FILE: {bundle(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
