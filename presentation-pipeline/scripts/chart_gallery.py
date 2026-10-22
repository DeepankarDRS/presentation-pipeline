"""Chart pass gallery: chart slides in several palettes, before / after the 2026-10-22 chart pass. LLM-free.

    python -m scripts.chart_gallery                                   # 4 default palettes
    python -m scripts.chart_gallery corporate-slate midnight-indigo --slide <saved input.xml>

For each palette it draws a specimen slide (3-series line with a title-row key, 5-series bars, a
one-series focus bar, good / bad marks) and, with --slide, one saved chart slide re-skinned with
theme_swap. BEFORE = the palette as built before the chart pass (authored chartColors and
positive / negative); AFTER = today's build (separate_chart_colors / separate_polarity) plus the
normalizer's chart focus rule. Each sheet has a second row with the deuteranopia simulation
(Machado 2009, the dataviz validator's matrix). Needs LibreOffice + pymupdf + numpy (build PC).

Output: output/chart_gallery/<palette>.png (and the single renders next to it).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents import style_resolver  # noqa: E402
from src.compiler import dataviz_palette as dv  # noqa: E402
from src.compiler.normalizer import _chart_focus, strip_theme  # noqa: E402
from src.compiler.theme_swap import swap_theme  # noqa: E402

_COMPILE = ROOT / "src" / "node" / "compile-pom.js"
_SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.exe")
DEFAULT = ["corporate-slate", "terracotta-light", "navy-orange", "midnight-indigo"]


def build(name: str, after: bool) -> dict:
    """The palette's theme dict, as built today (after) or before the chart pass."""
    entry = style_resolver._palettes()[name]          # not resolve_theme: the default is cached
    if after:
        return style_resolver._build_theme(name, entry)
    with mock.patch.object(style_resolver, "separate_chart_colors", lambda c, bg: list(c)), \
         mock.patch.object(style_resolver, "separate_polarity", lambda p: {}):
        return style_resolver._build_theme(name, entry)


def _card(inner: str, dark: bool, w: str = "50%") -> str:
    bg = "$chartSurface" if dark else "$surfaceAlt"
    return (f'<VStack w="{w}" h="max" padding="16" gap="8" backgroundColor="{bg}" borderRadius="12" '
            f'border.color="$border" border.width="1">{inner}</VStack>')


def _key(names: list[str], tokens: list[str], ink: str) -> str:
    return "".join(f'<HStack gap="6" alignItems="center"><Shape shapeType="rect" w="12" h="12" '
                   f'backgroundColor="{t}" /><Text fontSize="14" color="{ink}">{n}</Text></HStack>'
                   for n, t in zip(names, tokens))


def specimen(dark: bool, n_series: int) -> str:
    ink, muted = ("$chartInk", "$chartInk") if dark else ("$textMain", "$textMuted")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    lines = {"North": [12, 14, 13, 17, 19, 22], "South": [10, 11, 13, 12, 14, 15], "West": [8, 9, 9, 11, 10, 12]}
    line_series = "".join(f'<ChartSeries name="{n}">' + "".join(
        f'<ChartDataPoint label="{m}" value="{v}" />' for m, v in zip(months, vals)) + "</ChartSeries>"
        for n, vals in lines.items())
    t3 = ["$chart1", "$chart2", "$chart3"]
    line = _card(f'<HStack gap="16" alignItems="center"><Text fontSize="16" bold="true" color="{ink}">'
                 f'Bookings by region ($M)</Text>{_key(list(lines), t3, muted)}</HStack>'
                 f'<Chart chartType="line" w="max" h="max" minH="180" showLegend="false" '
                 f'chartColors=\'["$chart1","$chart2","$chart3"]\'>{line_series}</Chart>', dark)
    segs = ["A", "B", "C", "D", "E"][:min(5, n_series)]
    bar_series = "".join(f'<ChartSeries name="{s}">' + "".join(
        f'<ChartDataPoint label="{q}" value="{(i * 7 + j * 5) % 11 + 4}" />' for j, q in enumerate(["Q1", "Q2", "Q3"]))
        + "</ChartSeries>" for i, s in enumerate(segs))
    t5 = [f"$chart{i}" for i in range(1, len(segs) + 1)]
    bars = _card(f'<HStack gap="12" alignItems="center"><Text fontSize="16" bold="true" color="{ink}">'
                 f'Every series ({len(segs)})</Text>{_key(segs, t5, muted)}</HStack>'
                 f'<Chart chartType="bar" w="max" h="max" minH="180" showLegend="false" '
                 f'chartColors=\'{str(t5).replace(chr(39), chr(34))}\'>{bar_series}</Chart>', dark)
    focus = _card(f'<Text fontSize="16" bold="true" color="{ink}">Revenue ($M): Q3 FY26 $48.2M</Text>'
                  '<Chart chartType="bar" w="max" h="max" minH="160" showLegend="false" '
                  'chartColors=\'["$accent","$neutral","$neutral","$neutral"]\'><ChartSeries name="Revenue">'
                  + "".join(f'<ChartDataPoint label="{q}" value="{v}" />' for q, v in
                            [("Q4 FY25", 39.1), ("Q1 FY26", 41.0), ("Q2 FY26", 44.6), ("Q3 FY26", 48.2)])
                  + "</ChartSeries></Chart>", dark)
    good_bad = _card(
        f'<Text fontSize="16" bold="true" color="{ink}">Good / bad marks</Text>'
        '<Chart chartType="bar" w="max" h="max" minH="160" showLegend="false" '
        'chartColors=\'["$positive","$negative","$positive","$negative"]\'><ChartSeries name="Variance">'
        + "".join(f'<ChartDataPoint label="{k}" value="{v}" />' for k, v in
                  [("Online", 12), ("Retail", 7), ("B2B", 9), ("Export", 5)])
        + "</ChartSeries></Chart>", dark)
    return ('<Slide><VStack w="1280" h="720" padding="32" gap="16" backgroundColor="$surface">'
            '<Text fontSize="28" bold="true" color="$textMain">Q3 FY26 revenue ahead of plan</Text>'
            f'<HStack w="max" h="max" gap="16" alignItems="stretch">{line}{bars}</HStack>'
            f'<HStack w="max" h="max" gap="16" alignItems="stretch">{focus}{good_bad}</HStack>'
            '</VStack></Slide>')


def render(xml: str, theme_element: str, out_dir: Path, name: str) -> Path:
    import fitz  # pymupdf

    out_dir.mkdir(parents=True, exist_ok=True)
    src = out_dir / f"{name}.xml"
    src.write_text(theme_element + "\n" + strip_theme(xml), encoding="utf-8")
    comp = out_dir / f"{name}_pptx"
    subprocess.run(["node", str(_COMPILE), str(src), str(comp)], capture_output=True, text=True, timeout=180)
    pptx = comp / "presentation.pptx"
    if not pptx.exists():
        raise RuntimeError(f"{name}: compile failed, see {comp}")
    # a private profile: a LibreOffice another session holds open blocks the shared one
    profile = (out_dir.parent / ".lo-profile").resolve().as_uri()
    subprocess.run([str(_SOFFICE), f"-env:UserInstallation={profile}", "--headless", "--convert-to", "pdf",
                    "--outdir", str(comp), str(pptx)], capture_output=True, text=True, timeout=240)
    png = out_dir / f"{name}.png"
    fitz.open(comp / "presentation.pdf")[0].get_pixmap(matrix=fitz.Matrix(1.0, 1.0)).save(png)
    shutil.rmtree(comp, ignore_errors=True)
    return png


def deutan(png: Path) -> "object":
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    sim = np.clip(lin @ np.array(dv.MACHADO["deutan"]).T, 0, 1)
    s = np.where(sim <= 0.0031308, 12.92 * sim, 1.055 * sim ** (1 / 2.4) - 0.055)
    return Image.fromarray((s * 255).round().astype("uint8"))


def sheet(rows: list[tuple[str, Path, Path]], out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = None
    tiles = []
    for label, before, after in rows:
        b, a = Image.open(before).convert("RGB"), Image.open(after).convert("RGB")
        tiles.append((f"{label} - BEFORE", b, f"{label} - AFTER", a))
        tiles.append((f"{label} - BEFORE, deuteranopia", deutan(before), f"{label} - AFTER, deuteranopia", deutan(after)))
    w, h = tiles[0][1].size
    pad, bar = 12, 30
    img = Image.new("RGB", (2 * w + 3 * pad, len(tiles) * (h + bar) + pad), "white")
    d = ImageDraw.Draw(img)
    for i, (l1, i1, l2, i2) in enumerate(tiles):
        y = i * (h + bar)
        d.text((pad, y + 6), l1, fill="black", font=font)
        d.text((w + 2 * pad, y + 6), l2, fill="black", font=font)
        img.paste(i1, (pad, y + bar))
        img.paste(i2, (w + 2 * pad, y + bar))
    img.save(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("palettes", nargs="*", default=DEFAULT)
    ap.add_argument("--slide", type=Path, action="append", default=[], help="a saved input.xml to re-skin")
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "chart_gallery")
    a = ap.parse_args()
    src_theme = build("corporate-slate", after=False)["element"]     # the saved slides' theme
    for name in a.palettes:
        rows = []
        for label, xml0 in [("specimen", None)] + [(p.parent.name, p.read_text(encoding="utf-8")) for p in a.slide]:
            pngs = []
            for after in (False, True):
                t = build(name, after)
                if xml0 is None:
                    xml = specimen(t["is_dark"], len(t["chart_colors"]))
                else:
                    xml = swap_theme(xml0, src_theme, t["element"], t["is_dark"]).xml
                if after:
                    xml = _chart_focus(xml)[0]
                pngs.append(render(xml, t["element"], a.out / name, f"{label}-{'after' if after else 'before'}"))
            rows.append((f"{name} {label}", *pngs))
        sheet(rows, a.out / f"{name}.png")
        print(a.out / f"{name}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
