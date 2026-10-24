"""KPI node pilot: what B's KPI cards look like, LLM-free (docs/kpi-node-pilot-2026-10-11.md §8).

    python -m scripts.experiments.kpi.kpi_gallery                          # 6 looks x 2 plans x 3 palettes
    python -m scripts.experiments.kpi.kpi_gallery --palettes gj-h1         # one palette

The skeletons are hand-written in the form the generator LLM writes under POM_BLOCKS=kpi (containers,
fills, icons, refs); everything after that is the real pipeline: element_refs.fill_refs (text,
unit share, colour defaults, peer ids) -> normalize_xml -> fit-grow -> POM. Each slide is compiled and
rendered on its own (merged decks reuse media names, wrong icons). Writes <out>/<palette>.png
(a contact sheet) and every slide's folder. The paid check shows which of these the LLM picks.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.agents.planning.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes.element_refs import fill_refs  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

OUT = ROOT / "output" / "kpi-gallery"
PALETTES = ("corporate-slate", "gj-h1", "graphite-dark")

PLANS = {
    "qbr": {"headline": "ARR grew to $48.2M while margin softened", "kicker": "EXECUTIVE SUMMARY",
            "hint": "highlight ARR as the hero",
            "labels": ["ARR", "NRR", "Gross Margin", "CAC Payback"],
            "values": ["$48.2M", "114%", "72.1%", "14 months"],
            "notes": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"],
            "tones": ["good", "good", "bad", "good"],
            "icons": ["trending-up", "users", "percent", "clock"]},
    "roas": {"headline": "Spend is at scale, but every platform returns a third of it", "kicker": "EXECUTIVE SUMMARY",
             "hint": "highlight Blended ROAS as the hero",
             "labels": ["Combined spend", "Combined revenue", "Blended ROAS", "Amazon ROAS", "Zepto ROAS"],
             "values": ["₹114.9L", "₹37.4L", "0.33x", "0.34x", "0.32x"],
             "notes": ["Amazon ₹29.4L · Zepto ₹85.5L", "Amazon ₹10.1L · Zepto ₹27.3L", "Blended ACOS ~307%",
                       "CPC ₹31.1 · CVR 5.5%", "CPC ₹46.2 · CVR 6.4%"],
             "tones": ["", "", "bad", "bad", "bad"],
             "icons": ["wallet", "indian-rupee", "gauge", "shopping-cart", "shopping-cart"]},
}
SOFT = {"good": "$positiveSoft", "bad": "$negativeSoft", "watch": "$warningSoft"}
EDGE = {"good": "$positive", "bad": "$negative", "watch": "$warning"}
INK = {"good": "$positiveText", "bad": "$negativeText", "watch": "$warningText"}


def plan_of(p: dict) -> dict:
    return {"components": [{"component_id": "kpis", "kind": "kpi_row", "count": len(p["values"]), "design_hint": p["hint"],
                            "content_data": {"kpi_labels": p["labels"], "kpi_values": p["values"],
                                             "kpi_deltas": p["notes"], "kpi_tones": p["tones"]}}]}


def focus(p: dict) -> int:
    return next(i for i, lab in enumerate(p["labels"]) if lab.lower() in p["hint"].lower())


def icon(p, i, size=22, color=None):
    c = color or INK.get(p["tones"][i], "$accent")
    return f'<Icon name="{p["icons"][i]}" size="{size}" color="{c}"/>'


def refs(i, label_color="", value_attrs=""):
    lc = f' color="{label_color}"' if label_color else ""
    return f'<Text ref="kpis.{i}.label"{lc}/><Text ref="kpis.{i}.value"{value_attrs}/>'


def note(i, color=""):
    return f'<Text ref="kpis.{i}.note"{f" color={chr(34)}{color}{chr(34)}" if color else ""}/>'


# ── the looks (what the LLM composes) ────────────────────────────────────────

def tiles(p):
    """Tiles, icon in the label row, toned tiles tinted."""
    out = []
    for i in range(len(p["values"])):
        t = p["tones"][i]
        out.append(f'<VStack w="1" grow="1" padding="22" gap="10" justifyContent="center" backgroundColor="{SOFT.get(t, "$surfaceAlt")}" '
                   f'border.color="{EDGE.get(t, "$border")}" border.width="1" borderRadius="10">'
                   f'<HStack gap="10" alignItems="center">{icon(p, i)}<Text ref="kpis.{i}.label"/></HStack>'
                   f'<Text ref="kpis.{i}.value"/>{note(i)}</VStack>')
    per = 3 if len(out) == 5 else len(out)
    rows = [out[k:k + per] for k in range(0, len(out), per)]
    return "".join(f'<HStack grow="1" gap="14" alignItems="stretch">{"".join(r)}</HStack>' for r in rows)


def strip(p):
    """One card, items split by hairlines; the toned items in a second, tinted strip."""
    plain = [i for i, t in enumerate(p["tones"]) if not t] or list(range(len(p["values"])))
    toned = [i for i in range(len(p["values"])) if i not in plain]

    def band(ids, fill, line):
        cells = "".join(f'<VStack w="1" grow="1" gap="8" padding.left="{0 if k == 0 else 22}" justifyContent="center"'
                        + (f' borderLeft.color="{line}" borderLeft.width="1"' if k else "")
                        + f'>{refs(i)}{note(i)}</VStack>' for k, i in enumerate(ids))
        return (f'<HStack grow="1" padding="26" backgroundColor="{fill}" border.color="{line}" border.width="1" '
                f'borderRadius="10" alignItems="stretch">{cells}</HStack>')
    out = band(plain, "$surfaceAlt", "$border")
    if toned:
        out += band(toned, SOFT[p["tones"][toned[0]]], EDGE[p["tones"][toned[0]]])
    return out


def bars(p):
    """Side bars: the tone's colour on the left edge, neutral tiles."""
    out = "".join(f'<VStack w="1" grow="1" padding="22" gap="10" justifyContent="center" backgroundColor="$surfaceAlt" '
                  f'borderLeft.color="{EDGE.get(p["tones"][i], "$accent")}" borderLeft.width="6">'
                  f'{refs(i)}{note(i)}</VStack>' for i in range(len(p["values"])))
    return f'<HStack grow="1" gap="14" alignItems="stretch">{out}</HStack>'


def focus_panel(p):
    """The focus item in a dark panel (hero size), the rest in a 2 x 2 grid."""
    f = focus(p)
    rest = [i for i in range(len(p["values"])) if i != f][:4]
    hero = (f'<VStack w="42%" padding="34" gap="14" backgroundColor="$panelDark" borderRadius="12" justifyContent="center">'
            f'<HStack gap="10" alignItems="center">{icon(p, f, 24, "$onPanelDark")}<Text ref="kpis.{f}.label" color="$onPanelDark"/></HStack>'
            f'<Text ref="kpis.{f}.value" size="hero"/>{note(f, "$onPanelDark")}</VStack>')

    def small(i):
        t = p["tones"][i]
        return (f'<VStack w="1" grow="1" padding="20" gap="8" justifyContent="center" backgroundColor="{SOFT.get(t, "$surfaceAlt")}" '
                f'borderRadius="10">{refs(i)}{note(i)}</VStack>')
    grid = "".join(f'<HStack grow="1" gap="14" alignItems="stretch">{"".join(small(i) for i in rest[k:k + 2])}</HStack>'
                   for k in range(0, len(rest), 2))
    return f'<HStack grow="1" gap="14" alignItems="stretch">{hero}<VStack grow="1" gap="14">{grid}</VStack></HStack>'


def rows_beside(p):
    """Stacked rows with icons in a narrow box, a takeaway beside it (where a chart would go)."""
    rows = "".join(
        f'<HStack padding.top="14" padding.bottom="14" gap="14" alignItems="center"'
        + (' borderTop.color="$border" borderTop.width="1"' if i else "")
        + f'>{icon(p, i)}<VStack grow="1" gap="4"><Text ref="kpis.{i}.label"/>{note(i)}</VStack>'
        f'<VStack w="170" alignItems="end"><Text ref="kpis.{i}.value"/></VStack></HStack>' for i in range(len(p["values"])))
    lst = (f'<VStack w="52%" padding.left="26" padding.right="26" padding.top="10" padding.bottom="10" justifyContent="center" '
           f'backgroundColor="$surfaceAlt" border.color="$border" border.width="1" borderRadius="10">{rows}</VStack>')
    side = ('<VStack grow="1" padding="30" gap="12" backgroundColor="$accentSoft" borderRadius="10" justifyContent="center">'
            '<Text fontSize="16" bold="true" color="$accentText" letterSpacing="2">WHERE A CHART GOES</Text>'
            '<Text fontSize="20" color="$textMain" lineHeight="1.4">(the slide\'s other component: chart, table or a takeaway)</Text></VStack>')
    return f'<HStack grow="1" gap="16" alignItems="stretch">{lst}{side}</HStack>'


def hero_tier(p):
    """Hero tile on top (full width), the rest as a supporting row under it."""
    f = focus(p)
    rest = [i for i in range(len(p["values"])) if i != f]
    t = p["tones"][f]
    hero = (f'<HStack grow="3" padding="30" gap="28" alignItems="center" backgroundColor="{SOFT.get(t, "$accentSoft")}" borderRadius="12">'
            f'<VStack gap="10"><HStack gap="10" alignItems="center">{icon(p, f, 26)}<Text ref="kpis.{f}.label"/></HStack>'
            f'<Text ref="kpis.{f}.value" size="hero"/></VStack><VStack grow="1" justifyContent="center">{note(f)}</VStack></HStack>')
    sup = "".join(f'<VStack w="1" grow="1" padding="18" gap="6" justifyContent="center" backgroundColor="$surfaceAlt" '
                  f'border.color="$border" border.width="1" borderRadius="10">{refs(i)}{note(i)}</VStack>' for i in rest)
    return f'{hero}<HStack grow="2" gap="14" alignItems="stretch">{sup}</HStack>'


LOOKS = [("tiles", tiles), ("strip", strip), ("side-bars", bars), ("focus-panel", focus_panel),
         ("rows-beside", rows_beside), ("hero-tier", hero_tier)]


def slide(p: dict, body: str, look: str) -> str:
    head = (f'<VStack gap="8"><Text fontSize="14" bold="true" letterSpacing="2" color="$accentText">{p["kicker"]} · {look.upper()}</Text>'
            f'<Text fontSize="34" bold="true" color="$textMain" lineHeight="1.15">{p["headline"]}</Text></VStack>')
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="26" alignItems="stretch" backgroundColor="$surface">'
            f'{head}<VStack grow="1" gap="14" alignItems="stretch">{body}</VStack></VStack></Slide>')


def build(palette: str, out: Path) -> list[tuple[str, Path | None]]:
    from scripts.experiments.node_test.node_test_score import render_pdf
    theme = resolve_theme(palette)["element"]
    shots = []
    for pname, p in PLANS.items():
        for look, fn in LOOKS:
            d = out / palette / f"{pname}-{look}"
            d.mkdir(parents=True, exist_ok=True)
            res = fill_refs(slide(p, fn(p), look), plan_of(p))
            bad = [i["message"] for i in res["issues"] if i["severity"] == "error"]
            if bad:
                print(f"{palette} {pname}-{look}: fill errors {bad}")
            xml = ensure_single_theme(normalize_xml(res["xml"])["cleaned_xml"], theme)
            (d / "in.xml").write_text(xml, encoding="utf-8")
            subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(d / "in.xml"), str(d)],
                           capture_output=True, timeout=300)
            pdf = render_pdf(d)
            shots.append((f"{pname} · {look}", pdf))
            print(f"{palette} {pname}-{look}: {'ok' if pdf else 'NO RENDER'}")
    return shots


def sheet(shots: list[tuple[str, Path | None]], path: Path, cols: int = 3) -> None:
    import pymupdf
    from PIL import Image, ImageDraw
    w, h, gap, lab = 640, 360, 16, 26
    rows = (len(shots) + cols - 1) // cols
    img = Image.new("RGB", (cols * (w + gap) + gap, rows * (h + lab + gap) + gap), "white")
    draw = ImageDraw.Draw(img)
    for k, (name, pdf) in enumerate(shots):
        x, y = gap + (k % cols) * (w + gap), gap + (k // cols) * (h + lab + gap)
        draw.text((x, y + 6), name, fill="black")
        if pdf:
            page = pymupdf.open(pdf)[0]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(w / page.rect.width, h / page.rect.height))
            img.paste(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), (x, y + lab))
        draw.rectangle([x - 1, y + lab - 1, x + w, y + lab + h], outline="#999999")
    img.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--palettes", nargs="*", default=list(PALETTES))
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    for pal in a.palettes:
        sheet(build(pal, a.out), a.out / f"{pal}.png")
        print(a.out / f"{pal}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
