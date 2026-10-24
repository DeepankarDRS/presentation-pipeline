"""Card tile nodes: every variant, layout and column choice, and the LLM's wrapper boxes, LLM-free
(docs/tile-nodes-spec-2026-10-12.md §11, step 3).

    python -m scripts.experiments.cards.card_gallery                                   # corporate-slate + graphite-dark
    python -m scripts.experiments.cards.card_gallery --palettes gj-h1 --out output/card-gallery-gj
    python -m scripts.experiments.cards.card_gallery --only steps wrap               # redraw some slides, keep the rest

The card tags are hand-written as the generator would write them under POM_BLOCKS=tiles; everything after that
is the real pipeline (scripts.experiments.tiles.tile_gallery.compile_one: tiles.fill -> cards.expand, normalize_xml, compile-pom.js
with fit-grow, LibreOffice). Writes <out>/<palette>-variants.png (each variant on the 5-card grid),
<out>/<palette>-layouts.png (columns by text length, steps, rail) and <out>/<palette>-wrappers.png (the boxes the
LLM puts around a group: a panel of the cards' own fill, a styled Text, a half-width column beside a chart).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.experiments.tiles import tile_gallery as TG  # noqa: E402  (sets POM_BLOCKS=tiles)
from scripts.experiments.kpi.kpi_gallery import sheet  # noqa: E402
from src.agents.planning.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import cards  # noqa: E402

OUT = ROOT / "output" / "card-gallery"


def compile_one(d: Path, xml: str, plan: dict, theme: str):
    """scripts.experiments.tiles.tile_gallery.compile_one with the deck font (compile_xml's deck_font) and the Inter render
    (scripts.experiments.cards.card_replay.render): LibreOffice ignores embedded fonts and drew bold text in Arial Black."""
    import json
    import subprocess
    from scripts.experiments.cards.card_replay import render
    from src.compiler.compiler_client import deck_font
    from src.compiler.nodes import tiles
    from src.compiler.normalizer import ensure_single_theme, normalize_xml
    if TG.ONLY and not any(d.name.startswith(o) for o in TG.ONLY) and (d / "presentation.pdf").exists():
        return d / "presentation.pdf", json.loads((d / "issues.json").read_text(encoding="utf-8"))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tiles.xml").write_text(xml, encoding="utf-8")
    res = tiles.fill(xml, plan)
    issues = [{k: i[k] for k in ("code", "severity", "message")} for i in res["issues"]]
    xml = ensure_single_theme(normalize_xml(deck_font(res["xml"]))["cleaned_xml"], theme)
    (d / "in.xml").write_text(xml, encoding="utf-8")
    (d / "issues.json").write_text(json.dumps(issues, indent=1, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                   capture_output=True, timeout=300)
    return render(d), issues


def grid(cid: str, rows: list[tuple], layout: str = "grid", focus: int | None = None, hint: str = "") -> dict:
    """rows: (title, tag, body, tone, key_phrase[, bullets])."""
    cs = []
    for r in rows:
        c = {"title": r[0]}
        for k, v in zip(("tag", "body", "tone", "key_phrase"), r[1:5]):
            if v:
                c[k] = v
        if len(r) > 5:
            c["bullets"] = r[5]
        cs.append(c)
    cd = {"card_layout": layout, "cards": cs}
    if focus is not None:
        cd["focus_card"] = focus
    return {"component_id": cid, "kind": "card_grid", "weight": "hero", "design_hint": hint, "content_data": cd}


# the planner's Example 5 with tones, key phrases and its focus card
MOMENTS = grid("moments", [
    ("Stand-up", "09:00-09:30", "The board is reviewed live with the whole team", "", ""),
    ("Deep work", "10:00-12:00", "Tasks are updated quietly, one person at a time", "", ""),
    ("Hand-off", "14:00-15:00", "Work passes between time zones and stalls overnight", "bad", "stalls overnight"),
    ("Review", "16:00-17:00", "Managers approve the day's changes", "", ""),
    ("Late fixes", "After 20:00", "Urgent edits from mobile, the fastest-growing moment", "good", "fastest-growing moment"),
], focus=4)
PRIORITIES = grid("priorities", [
    ("Close 3 enterprise logos", "", "Worth $4M+ combined ARR", "good", "$4M+"),
    ("Fix self-serve onboarding", "", "CAC payback slipped to 19 months", "bad", "19 months"),
    ("Ship analytics v2", "", "Before the January board meeting", "", ""),
])
SHORT4 = grid("pillars", [("Visibility", "", "Search and home placement", "", ""), ("Pricing", "", "Price-pack fit", "", ""),
                          ("Assortment", "", "Range per city", "", ""), ("Supply", "", "Fill rate above 95%", "watch", "95%")])
LONG4 = grid("findings", [
    ("Search share is falling", "", "Organic search share dropped on every platform this quarter while paid share held, so "
     "the brand pays more for the same traffic.", "bad", "dropped on every platform"),
    ("Retention is the strength", "", "Repeat buyers are 41% of revenue and their basket grew; this is the base to "
     "protect while acquisition is reset.", "good", "41% of revenue"),
    ("Promotions hide the price gap", "", "Discount weeks lift volume but the regular price sits above two rivals, and "
     "volume falls back as soon as a promotion ends.", "watch", "falls back"),
    ("Data arrives late", "", "Platform reports land ten days after month end, so every decision uses old numbers and "
     "the team cannot react within a month.", "bad", "ten days"),
])
SEVEN = grid("sources", [(t, "", "", "", "") for t in ("Orders", "Returns", "Ads", "Search", "Reviews", "Stock", "Prices")])
PLAN90 = grid("plan90", [
    ("Audit", "Day 0-30", "", "", "", ["Map every open ticket by queue", "Time each hand-off"]),
    ("Rebuild", "Day 31-60", "", "", "", ["Merge duplicate queues", "Route billing to specialists"]),
    ("Automate", "Day 61-75", "First replies drafted by templates", "", ""),
    ("Scale", "Day 76-90", "", "", "", ["Report resolution time weekly", "Hire two leads"]),
], layout="steps")
STEPS_PLAIN = grid("flow", [("Collect", "", "Orders, ads and stock in one table", "", ""),
                            ("Clean", "", "One SKU code across platforms", "", ""),
                            ("Model", "", "Price and promotion effects per city", "", ""),
                            ("Act", "", "Weekly price and budget moves", "", "")], layout="steps")

ICONS = ["sun", "brain", "repeat", "check-circle", "moon"]
VARIANTS = [n for n in cards.card()["variants"] if n != "inverted"]


def variant_body(variant: str) -> str:
    items = "".join(f'<Card ref="moments.{i}" icon="{n}"/>' for i, n in enumerate(ICONS))
    return f'<CardGrid ref="moments" variant="{variant}">{items}</CardGrid>'


LAYOUTS = [
    ("3 cards (bare tag)", [PRIORITIES], '<CardGrid ref="priorities"/>'),
    ("4 short: one row", [SHORT4], '<CardGrid ref="pillars" variant="accent_top"/>'),
    ("4 long: 2 x 2", [LONG4], '<CardGrid ref="findings"/>'),
    ("7: 4 + 3", [SEVEN], '<CardGrid ref="sources" icon="database"/>'),
    ("steps: tags + bullets", [PLAN90], '<CardGrid ref="plan90"/>'),
    ("steps: numbered", [STEPS_PLAIN], '<CardGrid ref="flow"/>'),
    ("rail", [STEPS_PLAIN], '<CardGrid ref="flow" layout="rail" variant="outline"/>'),
    ("side icons", [PRIORITIES], '<CardGrid ref="priorities" arrange="side" icon="target"/>'),
    ("numerals", [SHORT4], '<CardGrid ref="pillars" variant="numerals"/>'),
]

# the boxes the LLM puts around a group (tile-nodes learning 6)
WRAPPERS = [
    ("panel of the cards' fill", [PRIORITIES],
     '<VStack backgroundColor="$surfaceAlt" padding="24" gap="14" grow="1"><Text fontSize="16" bold="true">Q4 bets</Text>'
     '<CardGrid ref="priorities"/></VStack>'),
    ("styled Text around the tag", [PRIORITIES],
     '<Text fontSize="18" bold="true" color="$accent"><CardGrid ref="priorities" variant="outline"/></Text>'),
    ("half column beside a chart", [SHORT4],
     '<HStack gap="20" grow="1"><VStack w="50%" gap="10"><Chart chartType="bar" w="max" h="max">'
     '<ChartSeries name="Share"><ChartDataPoint label="Web" value="42"/><ChartDataPoint label="App" value="35"/>'
     '<ChartDataPoint label="Store" value="23"/></ChartSeries></Chart></VStack>'
     '<VStack w="max" gap="10"><CardGrid ref="pillars"/></VStack></HStack>'),
    ("one card placed apart", [MOMENTS],
     '<HStack gap="18" grow="1"><CardGrid ref="moments" w="max"/><Card ref="moments.4" w="34%" icon="moon"/></HStack>'),
    ("dark panel around tones", [PRIORITIES],
     '<VStack backgroundColor="$panelDark" padding="24" grow="1"><CardGrid ref="priorities" variant="toned"/></VStack>'),
    ("cards in a bordered card", [LONG4],
     '<VStack border.color="$border" border.width="1" padding="20" grow="1"><CardGrid ref="findings" variant="outline"/></VStack>'),
]


def build(palette: str, out: Path) -> None:
    theme = resolve_theme(palette)["element"]
    groups = [("variants", [(f"variant {v}", [MOMENTS], variant_body(v)) for v in VARIANTS], 3),
              ("layouts", LAYOUTS, 3), ("wrappers", WRAPPERS, 3)]
    for name, rows, cols in groups:
        shots = []
        for title, comps, body in rows:
            d = out / palette / f"{name}-{title.split(':')[0].split()[0]}-{len(shots)}"
            xml = TG.slide(title.upper(), "Teams open the tool at five moments in the working day", body)
            pdf, issues = compile_one(d, xml, {"components": comps}, theme)
            shots.append((title, pdf))
            errs = [i["code"] for i in issues if i["severity"] == "error"]
            print(f"{palette} {name} {title}: {'ok' if pdf else 'NO RENDER'}"
                  f"{' errors ' + str(errs) if errs else ''} {[i['code'] for i in issues if i['severity'] != 'error']}")
        sheet(shots, out / f"{palette}-{name}.png", cols=cols)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--palettes", nargs="*", default=list(TG.PALETTES))
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--only", nargs="*", default=[], help="slide folder prefixes to redraw; the others are kept")
    a = ap.parse_args()
    TG.ONLY[:] = a.only
    if not a.only:
        shutil.rmtree(a.out, ignore_errors=True)
    for pal in a.palettes:
        build(pal, a.out)
        print(*(a.out / f"{pal}-{n}.png" for n in ("variants", "layouts", "wrappers")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
