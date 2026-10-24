"""KPI tile nodes: every variant x arrange, and the spec's examples, LLM-free (docs/tile-nodes-spec-2026-10-12.md §8 step 3).

    python -m scripts.experiments.tiles.tile_gallery                                    # corporate-slate + graphite-dark
    python -m scripts.experiments.tiles.tile_gallery --palettes gj-h1 --out output/tile-gallery-gj
    python -m scripts.experiments.tiles.tile_gallery --only inverted example-2       # redraw some slides, keep the rest (then the sheets)

The tile tags are hand-written as the generator would write them under POM_BLOCKS=tiles; everything after
that is the real pipeline: tiles.fill (expand + element_refs.fill_refs) -> normalize_xml -> compile-pom.js
(fit-grow, POM) -> LibreOffice. Each slide compiles and renders on its own (merged decks reuse media
names). Writes <out>/<palette>-variants.png (rows: variants, columns: arranges), <out>/<palette>-examples.png
(spec §2.2 examples 1-5; 6-7 divided / inline) and every slide's folder (in.xml, fitted.xml, presentation.pptx / .pdf).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["POM_BLOCKS"] = "tiles"

from scripts.experiments.kpi.kpi_gallery import sheet  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import tiles  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

OUT = ROOT / "output" / "tile-gallery"
PALETTES = ("corporate-slate", "graphite-dark")

QBR = {"component_id": "kpis", "kind": "kpi_row", "weight": "hero", "design_hint": "highlight ARR as the hero",
       "content_data": {"kpi_labels": ["ARR", "NRR", "Gross Margin", "CAC Payback"],
                        "kpi_values": ["$48.2M", "114%", "72.1%", "14 months"],
                        "kpi_deltas": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"],
                        "kpi_tones": ["good", "good", "bad", "good"]}}
ICONS = ["trending-up", "users", "percent", "clock"]
METRICS = {"component_id": "kpi_metrics", "kind": "kpi_row", "weight": "hero",
           "design_hint": "highlight Blended ROAS as the hero",
           "content_data": {"kpi_labels": ["Combined spend", "Combined revenue", "Amazon ROAS", "Zepto ROAS", "Blended ROAS"],
                            "kpi_values": ["₹114.9L", "₹37.4L", "0.34x", "0.32x", "0.33x"],
                            "kpi_deltas": ["Amazon ₹29.4L · Zepto ₹85.5L", "Amazon ₹10.1L · Zepto ₹27.3L",
                                           "CPC ₹31.1 · CVR 5.5%", "CPC ₹46.2 · CVR 6.4%", "Blended ACOS ~307%"],
                            "kpi_tones": ["", "", "bad", "bad", "bad"]}}
HERO = {"component_id": "kpi_hero", "kind": "kpi_row", "weight": "hero",
        "content_data": {"kpi_labels": ["Blended ROAS", "Blended ACOS"], "kpi_values": ["0.33x", "~307%"],
                         "kpi_deltas": ["every platform returns a third of spend", "3x the break-even line"],
                         "kpi_tones": ["bad", "bad"]}}
SUPPORT = {"component_id": "kpi_support", "kind": "kpi_row", "weight": "supporting",
           "content_data": {"kpi_labels": ["Spend", "Revenue", "CPC", "CVR"],
                            "kpi_values": ["₹114.9L", "₹37.4L", "₹38.6", "6.0%"],
                            "kpi_deltas": ["", "", "Amazon ₹31.1 · Zepto ₹46.2", "Amazon 5.5% · Zepto 6.4%"],
                            "kpi_tones": ["", "", "watch", ""]}}

# spec §2.2, verbatim apart from the plan ids
EXAMPLES = [
    ("1 one tag", [METRICS], '<KpiGrid ref="kpi_metrics" variant="filled"/>'),
    ("2 one tile singled out", [METRICS],
     '<KpiGrid ref="kpi_metrics" variant="plain" cols="2" icon.color="$accent">'
     '<Kpi ref="kpi_metrics.2" variant="toned" icon="alert-triangle"/></KpiGrid>'),
    ("3 grid + dark focus panel", [METRICS],
     '<HStack gap="18" grow="1"><KpiGrid ref="kpi_metrics" variant="dot" cols="2" w="max"/>'
     '<Kpi ref="kpi_metrics.4" variant="inverted" size="hero" arrange="value-first" w="36%"/></HStack>'),
    ("4 two groups by role", [HERO, SUPPORT],
     '<KpiGrid ref="kpi_hero" variant="bare" value.glow.size="6" value.glow.color="$accent"/>'
     '<KpiGrid ref="kpi_support" variant="bar"/>'),
    ("5 a native effect on one part", [METRICS],
     '<KpiGrid ref="kpi_metrics" variant="plain" cols="3">'
     '<Kpi ref="kpi_metrics.0" icon="trending-up" icon.variant="circle-filled" icon.bgColor="$accentSoft" '
     'value.textGradient="linear-gradient(90deg, $accent 0%, $accentText 100%)"/></KpiGrid>'),
    # divided / inline (2026-10-22): the strip and ruled-list patterns of the reviewed example decks
    ("6 hero over a divided strip", [HERO, SUPPORT],
     '<KpiGrid ref="kpi_hero" variant="bare"/><KpiGrid ref="kpi_support" variant="divided"/>'),
    ("7 ruled list + dark focus", [METRICS],
     '<HStack gap="18" grow="1"><KpiGrid ref="kpi_metrics" variant="divided" arrange="inline" w="58%"/>'
     '<Kpi ref="kpi_metrics.4" variant="inverted" size="hero" grow="1"/></HStack>'),
]


def variant_body(variant: str, arrange: str) -> str:
    """Every item with its icon; `inverted` goes on the plan's emphasis item (the group stays plain)."""
    items = "".join(f'<Kpi ref="kpis.{i}" icon="{name}"'
                    + (' variant="inverted" size="hero"' if variant == "inverted" and i == 0 else "") + "/>"
                    for i, name in enumerate(ICONS))
    group = "plain" if variant == "inverted" else variant
    return f'<KpiGrid ref="kpis" variant="{group}" arrange="{arrange}" grow="1">{items}</KpiGrid>'


def slide(kicker: str, headline: str, body: str) -> str:
    head = (f'<VStack gap="8"><Text fontSize="14" bold="true" letterSpacing="2" color="$accentText">{kicker}</Text>'
            f'<Text fontSize="34" bold="true" color="$textMain" lineHeight="1.15">{headline}</Text></VStack>')
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="26" alignItems="stretch" backgroundColor="$surface">'
            f'{head}<VStack grow="1" gap="18" alignItems="stretch">{body}</VStack></VStack></Slide>')


ONLY: list[str] = []


def compile_one(d: Path, xml: str, plan: dict, theme: str) -> tuple[Path | None, list[dict]]:
    from scripts.experiments.node_test.node_test_score import render_pdf
    if ONLY and not any(d.name.startswith(o) for o in ONLY) and (d / "presentation.pdf").exists():
        return d / "presentation.pdf", json.loads((d / "issues.json").read_text(encoding="utf-8"))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tiles.xml").write_text(xml, encoding="utf-8")
    res = tiles.fill(xml, plan)
    issues = [{k: i[k] for k in ("code", "severity", "message")} for i in res["issues"]]
    xml = ensure_single_theme(normalize_xml(res["xml"])["cleaned_xml"], theme)
    (d / "in.xml").write_text(xml, encoding="utf-8")
    (d / "issues.json").write_text(json.dumps(issues, indent=1, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                   capture_output=True, timeout=300)
    return render_pdf(d), issues


def build(palette: str, out: Path) -> None:
    theme = resolve_theme(palette)["element"]
    shots = []
    for variant in tiles.kpi()["variants"]:
        for arrange in tiles.kpi()["item_attributes"]["arrange"]["values"]:
            d = out / palette / f"{variant}-{arrange}"
            xml = slide(f"VARIANT {variant.upper()} · ARRANGE {arrange.upper()}", "ARR grew to $48.2M while margin softened",
                        variant_body(variant, arrange))
            pdf, issues = compile_one(d, xml, {"components": [QBR]}, theme)
            shots.append((f"{variant} · {arrange}", pdf))
            errs = [i["code"] for i in issues if i["severity"] == "error"]
            print(f"{palette} {variant}-{arrange}: {'ok' if pdf else 'NO RENDER'}{' errors ' + str(errs) if errs else ''}")
    sheet(shots, out / f"{palette}-variants.png", cols=4)
    shots = []
    for name, comps, body in EXAMPLES:
        d = out / palette / f"example-{name.split()[0]}"
        pdf, issues = compile_one(d, slide(f"EXAMPLE {name.upper()}", "Spend is at scale, but every platform returns a third of it",
                                           body), {"components": comps}, theme)
        shots.append((f"example {name}", pdf))
        print(f"{palette} example {name}: {'ok' if pdf else 'NO RENDER'} {[i['code'] for i in issues]}")
    sheet(shots, out / f"{palette}-examples.png", cols=3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--palettes", nargs="*", default=list(PALETTES))
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--only", nargs="*", default=[], help="slide folder prefixes to redraw; the others are kept")
    a = ap.parse_args()
    ONLY[:] = a.only
    if not a.only:
        shutil.rmtree(a.out, ignore_errors=True)
    for pal in a.palettes:
        build(pal, a.out)
        print(a.out / f"{pal}-variants.png", a.out / f"{pal}-examples.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
