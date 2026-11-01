"""Composition convention: the proposed KPI and card compositions beside today's style variants, LLM-free
(docs/composition-convention-spec.md §6).

    python -m scripts.composition_convention                  # kpi + card, corporate-slate + graphite-dark
    python -m scripts.composition_convention --only kpi

One sample plan per block (typed schema, content_from_data validates it). Each composition is the bare tag the
generator writes (<KpiRow ref="kpis" variant="rows"/>), drawn by its node (tile_groups.py, POM_NODES) with the
composition's default look ($tokens and $tone only, no LLM attributes), on two palettes. Since 2026-11-01 the
composition gallery (spec §10 step 3): the rows must match the 2026-10-27 proof drawn from hand-written XML.
Today's rows are the real <KpiGrid> / <CardGrid> code (POM_BLOCKS=tiles). Writes <out>/<block>.png and every slide's
folder.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import card_gallery as CG  # noqa: E402
from scripts import composition_test as CT  # noqa: E402
from scripts import left_blocks_gallery as LB  # noqa: E402
from scripts import tile_gallery as TG  # noqa: E402  (sets POM_BLOCKS=tiles)
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import tile_groups  # noqa: E402

os.environ["POM_NODES"] = "kpi_row,card_grid"   # the composition nodes the bare tags need

OUT = ROOT / "output" / "composition-convention"
PALETTES = ("corporate-slate", "graphite-dark")
comp = LB.comp

# ── sample plans ──────────────────────────────────────────────────────────────

KPIS = comp("kpis", "kpi_row", {
    "kpi_labels": ["ARR", "Net revenue retention", "Gross margin", "CAC payback"],
    "kpi_values": ["$48.2M", "114%", "72.1%", "14 months"],
    "kpi_deltas": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"],
    "kpi_tones": ["good", "good", "bad", "watch"],
    "kpi_icons": ["trending-up", "users", "percent", "clock"]}, hint="highlight ARR as the hero")
CARDS = comp("levers", "card_grid", {"card_layout": "grid", "focus_card": 0, "cards": [
    {"title": "Search", "tag": "LEVER 1", "icon": "search", "tone": "bad", "key_phrase": "fell on every platform",
     "body": "Organic share fell on every platform", "bullets": ["Scale exact match", "Cut broad leakage", "Weekly bid review"]},
    {"title": "Placement", "tag": "LEVER 2", "icon": "store", "tone": "watch", "key_phrase": "return 0.4x",
     "body": "Home banners cost 2x and return 0.4x", "bullets": ["Cap home banners", "Test category tiles", "Shift to Hyderabad"]},
    {"title": "Pricing", "tag": "LEVER 3", "icon": "badge-percent",
     "body": "Regular price sits above two rivals", "bullets": ["Price-pack fit", "Bundle the hero SKU", "Match two rivals"]},
    {"title": "Retention", "tag": "LEVER 4", "icon": "repeat", "tone": "good", "key_phrase": "41% of revenue",
     "body": "Repeat buyers are 41% of revenue", "bullets": ["Retarget new buyers", "Monthly refill offer", "Win back lapsed"]}]})

KPI_HEAD = "ARR grew to $48.2M while margin softened"
CARD_HEAD = "Four levers decide whether H2 keeps the 4.1x return"


def tag(group: str, cid: str, variant: str) -> str:
    """The bare tag the generator writes; tile_groups.expand draws it (POM_NODES), as the hand-written XML of the
    2026-10-27 proof did (git history of this file; the sheets in docs/eval/composition-convention/)."""
    plan = {"components": [KPIS, CARDS]}
    return tile_groups.expand(f'<{group} ref="{cid}" variant="{variant}" grow="1" />', plan)["xml"]


# ── sheets ────────────────────────────────────────────────────────────────────

BLOCKS = {
    "kpi": (KPIS, KPI_HEAD,
            [(f"today · {v} (style)", f'<KpiGrid ref="kpis" variant="{v}" grow="1" />') for v in ("plain", "filled", "bar")],
            [(v, lambda v=v: tag("KpiRow", "kpis", v)) for v in ("strip", "rows", "banded", "bento")]),
    "card": (CARDS, CARD_HEAD,
             [(f"today · {v} (style)", f'<CardGrid ref="levers" variant="{v}" />') for v in ("lifted", "filled", "accent_top")],
             [(v, lambda v=v: tag("CardGrid", "levers", v)) for v in ("rows numbered", "columns", "banded", "bento")]),
}


def build(block: str, out: Path) -> None:
    plan, head, today, comps = BLOCKS[block]
    themes = {p: resolve_theme(p)["element"] for p in PALETTES}
    rows = []

    def draw(name: str, pal: str, body_xml: str) -> tuple[str, Path | None]:
        d = out / block / f"{name.split(' (')[0].replace(' · ', '-').replace(' ', '_')}-{pal}"
        pdf, issues = CG.compile_one(d, TG.slide(f"{name.upper()} · {pal.upper()}", head, body_xml), {"components": [plan]},
                                     themes[pal])
        errs = [i["code"] for i in issues if i["severity"] == "error"]
        print(f"{block} {name} {pal}: {'ok' if pdf else 'NO RENDER'}{' errors ' + str(errs) if errs else ''}", flush=True)
        return f"{name} · {pal}", pdf

    for pal in PALETTES:
        rows.append((f"today {pal}", [draw(n, pal, x) for n, x in today]))
    for name, fn in comps:
        xml = fn()   # one XML, both palettes: the theme supplies the colours
        rows.append((name, [draw(f"variant={name}", pal, xml) for pal in PALETTES]))
    CT.sheet_rows(rows, out / f"{block}.png")
    print(out / f"{block}.png", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", default=list(BLOCKS), choices=list(BLOCKS))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    for b in args.only:
        shutil.rmtree(args.out / b, ignore_errors=True)
        build(b, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
