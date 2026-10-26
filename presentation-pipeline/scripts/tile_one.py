"""One slide, tiles route, paid: check the hint looks (tile-variant-choice spec 2026-10-26) on a real generator run.

    python -m scripts.tile_one --list                         # free: the saved plans' KPI / card slides and their hint looks
    python -m scripts.tile_one                                # paid, test PC: the first slide whose hint gives a look
    python -m scripts.tile_one --item gate-deck-cheffin-full-s1

Reuses the slide plans of a combined check (output/tile-combined/<--plans>/plans.json, scripts.tile_combined), so
no planning is paid: one slide, POM_BLOCKS=tiles, the real graph from the plan (scripts.kpi_paid.run_one:
generator, validator, repairers; critic off), once. Writes output/tile-one/<item>/: first.xml (the LLM's own XML),
final.xml, result.json (cost, compile, the tags the LLM wrote, the looks code drew from the hint) and run.log, and
zips them as output/tile-one/<item>.zip to email back.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"   # read per call; this script is the tiles route only

from scripts import kpi_paid as KP  # noqa: E402

OUT = ROOT / "output" / "tile-one"


def looks(plan: dict) -> dict[str, dict]:
    """component_id -> the look its design hint asks for (empty picks left out)."""
    from src.agents.plan_checks import look_from_hint
    out = {}
    for c in plan.get("components") or []:
        lk = look_from_hint(c)
        if lk.get("group") or lk.get("items") or lk.get("emphasis"):
            out[c.get("component_id")] = {k: lk[k] for k in ("group", "items", "emphasis")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plans", default="combined", help="label of a combined check: output/tile-combined/<label>/plans.json")
    ap.add_argument("--item", help="item name (e.g. gate-deck-cheffin-full-s1); default: the first with a hint look")
    ap.add_argument("--list", action="store_true", help="free: list the items and their hint looks, run nothing")
    a = ap.parse_args()
    src = ROOT / "output" / "tile-combined" / a.plans / "plans.json"
    if not src.exists():
        print(f"no {src}: run scripts.tile_combined first, or pass --plans <label> (ls output\\tile-combined)")
        return 2
    items = json.loads(src.read_text(encoding="utf-8"))["items"]
    if a.list:
        for it in items:
            print(f"{it['name']}: {looks(it['plan']) or 'no hint look'}")
        return 0
    pick = [it for it in items if it["name"] == a.item] if a.item else [it for it in items if looks(it["plan"])][:1]
    if not pick:
        print(f"no item {a.item!r}" if a.item else "no item with a hint look; pick one with --item (see --list)")
        return 2
    it = pick[0]
    if not os.environ.get("OPENAI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set (.env): the paid run is for the test PC")
        return 2
    out = OUT / it["name"]
    out.mkdir(parents=True, exist_ok=True)
    from src.utils.logging_config import add_file_log, setup_logging
    setup_logging()
    add_file_log(out / "run.log")
    print(f"run {it['name']} (tiles); hint looks: {looks(it['plan'])}", flush=True)
    res = KP.run_one(it, f"tile-one-{it['name']}-{int(time.time())}")
    first = res.get("first_xml") or ""
    (out / "first.xml").write_text(first, encoding="utf-8")
    (out / "final.xml").write_text(res.get("final_xml") or "", encoding="utf-8")
    from src.compiler.nodes import tiles
    # the generator's XML, then each repair's: a repair may be the step that writes the tile tags
    stages = [("generator", first)] + [(f"repair-{n}", x) for n, x in enumerate(res.get("repaired_xml") or [], 1)]
    for name, x in stages[1:]:
        (out / f"{name}.xml").write_text(x, encoding="utf-8")
    steps = [{"step": name, "tags": re.findall(r"<(?:KpiGrid|Kpi|CardGrid|Card)\b[^>]*>", x),
              "drawn": [i["message"] for i in tiles.fill(x, it["plan"])["issues"] if i["code"] == "NODE_LOOK_FROM_HINT"]}
             for name, x in stages if x]
    row = {"item": it["name"], "hints": {c.get("component_id"): c.get("design_hint") for c in it["plan"].get("components") or []
                                         if c.get("kind") in ("kpi_row", "card_grid")},
           "asked": looks(it["plan"]), "steps": steps,
           **{k: v for k, v in res.items() if k not in ("first_xml", "final_xml", "repaired_xml")}}
    (out / "result.json").write_text(json.dumps(row, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"  first ok={res['first_ok']} final ok={res['final_ok']} cost ${res.get('cost_usd') or 0:.3f}", flush=True)
    for s in steps:
        print(f"  {s['step']}: tags {' '.join(s['tags']) or 'none'}; drawn from the hint: {'; '.join(s['drawn']) or 'nothing'}",
              flush=True)
    z = OUT / f"{it['name']}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in out.rglob("*"):
            if p.is_file():
                f.write(p, p.relative_to(OUT))
    print(f"EMAIL THIS FILE: {z}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
