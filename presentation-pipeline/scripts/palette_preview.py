"""Palette preview: today's recipe colours vs the tokens proposed in docs/palette-quality-research-2026-10-06.md.

Research tool, no LLM and no API key. For each palette it draws the SAME specimen slide twice:

  before  what the recipes do today: literal pale tints (DCFCE7, EEF2FD ...), the accent used as text,
          white text on accent fills, every chart series in chartColors.
  after   the proposed tokens: derived *Soft tints, *Text variants, onAccent, neutral, ramp, borderStrong.

Then compiles both (POM), renders them (LibreOffice -> PDF -> PNG) and writes a side-by-side sheet plus a
contrast table of the specimen's text pairs.

    python -m scripts.palette_preview navy-orange saascolor gj-h1 claude-cream graphite-dark corporate-slate
    python -m scripts.palette_preview --all

Output: output/palette_preview/<palette>/{before,after}.png, <palette>/sheet.png, summary.md.
The derivation rules here are PROTOTYPES of docs/palette-quality-research-2026-10-06.md §5.2 / §5.3.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

_PALETTES = _ROOT / "src" / "knowledge" / "theme" / "palettes.yaml"
_COMPILE = _ROOT / "src" / "node" / "compile-pom.js"
_SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.exe")

# §5.1 palette fixes now live in palettes.yaml (2026-10-07, P3); kept as a hook for trying more.
PALETTE_FIXES: dict[str, dict[str, str]] = {}


# --- colour maths -----------------------------------------------------------
def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def lum(h: str) -> float:
    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def mix(a: str, b: str, t: float) -> str:
    return _hex(tuple(x * (1 - t) + y * t for x, y in zip(_rgb(a), _rgb(b))))


def shift_lightness(h: str, direction: int, steps: int = 60) -> list[str]:
    """Same hue and saturation, lightness stepped darker (-1) or lighter (+1)."""
    r, g, b = (v / 255 for v in _rgb(h))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    out = []
    for i in range(steps + 1):
        l2 = ll + direction * i * (1 - ll if direction > 0 else ll) / steps
        out.append(_hex(tuple(v * 255 for v in colorsys.hls_to_rgb(hh, max(0, min(1, l2)), ss))))
    return out


def text_variant(colour: str, backgrounds: list[str], dark_mode: bool, floor: float = 4.5) -> str:
    """Smallest lightness change (hue kept) that reaches `floor` on every background."""
    if all(ratio(colour, bg) >= floor for bg in backgrounds):
        return colour
    for cand in shift_lightness(colour, +1 if dark_mode else -1):
        if all(ratio(cand, bg) >= floor for bg in backgrounds):
            return cand
    return colour


def on_colour(bg: str, p: dict) -> str:
    for c in (p["textMain"], p["surface"], "FFFFFF", "000000"):
        if ratio(c, bg) >= 4.5:
            return c
    return max(("FFFFFF", "000000"), key=lambda c: ratio(c, bg))


# --- derived tokens (prototype of §5.2 / §5.3) -------------------------------
def derive(p: dict) -> dict[str, str]:
    dark = p["mode"] == "dark"
    t = 0.22 if dark else 0.16
    # tint into the lightest of the two surfaces (a palette whose cards are off-white would dull it)
    base = p["surfaceAlt"] if dark or lum(p["surfaceAlt"]) >= lum(p["surface"]) else p["surface"]
    d: dict[str, str] = {}
    for k in ("accent", "positive", "negative", "warning"):
        soft = mix(base, p[k], t)
        d[f"{k}Soft"] = soft
        d[f"{k}Text"] = text_variant(p[k], [p["surface"], p["surfaceAlt"], soft], dark)
    d["onAccent"] = on_colour(p["accent"], p)
    d["onPositive"] = on_colour(p["positive"], p)
    d["neutral"] = mix(p["surface"], p["textMain"], 0.20)
    d["neutralDark"] = mix(p["surface"], p["textMain"], 0.42)
    d["borderStrong"] = mix(p["border"], p["textMuted"], 0.35)
    for i, frac in enumerate((0.10, 0.25, 0.50, 0.75, 1.0), 1):
        d[f"ramp{i}"] = mix(p["surfaceAlt"], p["accent"], frac)
    # the tokens the pipeline ships (2026-10-07) replace the prototype values
    from src.compiler.palette_tokens import derive_tokens
    d.update(derive_tokens(p))
    return d


# --- specimen slide ----------------------------------------------------------
def theme_element(tokens: dict[str, str]) -> str:
    return "<Theme " + " ".join(f'{k}="{v}"' for k, v in tokens.items()) + " />"


def _slide(p: dict, after: bool, d: dict[str, str]) -> tuple[str, list[tuple[str, str, str]]]:
    """Return (xml, text pairs [(label, fg hex, bg hex)]) for the specimen."""
    dark = p["mode"] == "dark"
    pairs: list[tuple[str, str, str]] = []

    def pair(label: str, fg: str, bg: str) -> None:
        pairs.append((label, fg, bg))

    if after:
        eyebrow, phrase = "$accentText", "$accentText"
        pos_t, neg_t, warn_t = "$positiveText", "$negativeText", "$warningText"
        pos_bg, neg_bg, warn_bg = "$positiveSoft", "$negativeSoft", "$warningSoft"
        hl_bg, hl_text = "$accentSoft", "$accentText"
        callout_bg, callout_lab = "$accentSoft", "$accentText"
        step_fg = "$onAccent"
        rule = "$borderStrong"
        c_pos_t, c_neg_t, c_warn_t = d["positiveText"], d["negativeText"], d["warningText"]
        c_pos_bg, c_neg_bg, c_warn_bg = d["positiveSoft"], d["negativeSoft"], d["warningSoft"]
        c_accent_t = d["accentText"]
        c_hl_bg = c_callout_bg = d["accentSoft"]
        c_on_accent = d["onAccent"]
    else:  # today's recipes: literal tints, accent as text, white on accent
        eyebrow = phrase = "$accent"
        pos_t, neg_t, warn_t = "15803D", "B91C1C", "92400E"
        pos_bg, neg_bg, warn_bg = "DCFCE7", "FEE2E2", "FEF3C7"
        hl_bg, hl_text = "EEF2FD", "$accent"
        callout_bg, callout_lab = "EEF2FD", "$accent"
        step_fg = "FFFFFF"
        rule = "$border"
        c_pos_t, c_neg_t, c_warn_t = "15803D", "B91C1C", "92400E"
        c_pos_bg, c_neg_bg, c_warn_bg = "DCFCE7", "FEE2E2", "FEF3C7"
        c_accent_t = p["accent"]
        c_hl_bg = c_callout_bg = "EEF2FD"
        c_on_accent = "FFFFFF"

    s, sa = p["surface"], p["surfaceAlt"]
    pair("Eyebrow / headline phrase (accent as text) on surface", c_accent_t, s)
    pair("Delta chip positive", c_pos_t, c_pos_bg)
    pair("Delta chip negative", c_neg_t, c_neg_bg)
    pair("Delta chip warning", c_warn_t, c_warn_bg)
    pair("Highlighted table row, key cell", c_accent_t, c_hl_bg)
    pair("Callout label", c_accent_t, c_callout_bg)
    pair("Step chip (text on accent fill)", c_on_accent, p["accent"])
    pair("Delta text positive on card", d["positiveText"] if after else p["positive"], sa)
    pair("Delta text negative on card", d["negativeText"] if after else p["negative"], sa)

    if after:
        series = [p["accent"], d["neutral"], d["neutralDark"]]
        ramp_fill = [d[f"ramp{i}"] for i in range(1, 6)]
        ramp_text = [on_colour(c, p) for c in ramp_fill]
    else:
        series = list(p["chartColors"][:3])
        ramp_fill = None
        ramp_text = None
    chart_colors = json.dumps(series).replace(" ", "")

    ramp_cells = ""
    if after:
        for i, (fill, tc) in enumerate(zip(ramp_fill, ramp_text), 1):
            ramp_cells += (f'<Shape shapeType="rect" w="84" h="52" fill.color="{fill}" color="{tc}" fontSize="14" '
                           f'bold="true" textAlign="center">{["Low", "", "Mid", "", "High"][i - 1] or i}</Shape>')
    else:
        for i, op in enumerate((0.2, 0.4, 0.6, 0.8, 1.0), 1):
            ramp_cells += (f'<Shape shapeType="rect" w="84" h="52" fill.color="$accent" opacity="{op}" '
                           f'color="$textMain" fontSize="14" bold="true" textAlign="center">'
                           f'{["Low", "", "Mid", "", "High"][i - 1] or i}</Shape>')

    def chip(text: str, fg: str, bg: str) -> str:
        return (f'<Shape shapeType="roundRect" w="88" h="28" fill.color="{bg}" color="{fg}" fontSize="14" '
                f'bold="true" borderRadius="999" textAlign="center">{text}</Shape>')

    def kpi(label: str, value: str, unit: str, chip_xml: str) -> str:
        return f"""<VStack grow="1" h="104" padding="14" gap="4" backgroundColor="$surfaceAlt" borderRadius="12" border.width="1" border.color="$border" justifyContent="center">
        <Text fontSize="14" color="$textMuted">{label}</Text>
        <HStack gap="12" alignItems="center">
          <Text fontSize="34" bold="true" color="$textMain">{value}<Span fontSize="18">{unit}</Span></Text>
          {chip_xml}
        </HStack>
      </VStack>"""

    def td(text: str, *, bg: str, color: str, right: bool = False, bold: bool = False) -> str:
        align = ' textAlign="right"' if right else ""
        weight = ' bold="true"' if bold else ""
        return f'<Td backgroundColor="{bg}" color="{color}"{align}{weight}>{text}</Td>'

    hdr_bg = "$surfaceAlt"
    rows = [
        ("Platform", "Ad sales", "ROAS"),
        ("Zepto", "9.55 Cr", "4.78x"),
        ("Blinkit", "2.80 Cr", "6.69x"),
        ("Swiggy", "1.42 Cr", "4.92x"),
    ]
    trs = "<Tr>" + "".join(td(t, bg=hdr_bg, color="$textMain", bold=True, right=i > 0)
                           for i, t in enumerate(rows[0])) + "</Tr>"
    for r in rows[1:]:
        hl = r[0] == "Blinkit"
        bg = hl_bg if hl else "$surface"
        trs += "<Tr>" + td(r[0], bg=bg, color="$textMain" if hl else "$textMuted") \
            + td(r[1], bg=bg, color="$textMain", right=True) \
            + td(r[2], bg=bg, color=hl_text if hl else "$textMain", right=True, bold=hl) + "</Tr>"

    chart_xml = f"""<Chart chartType="bar" w="528" h="196" showLegend="true" chartColors='{chart_colors}'>
            <ChartSeries name="Blinkit"><ChartDataPoint label="Jan" value="1.2"/><ChartDataPoint label="Mar" value="1.5"/><ChartDataPoint label="May" value="1.6"/><ChartDataPoint label="Jun" value="1.3"/></ChartSeries>
            <ChartSeries name="Swiggy"><ChartDataPoint label="Jan" value="1.2"/><ChartDataPoint label="Mar" value="1.2"/><ChartDataPoint label="May" value="1.5"/><ChartDataPoint label="Jun" value="1.8"/></ChartSeries>
            <ChartSeries name="Zepto"><ChartDataPoint label="Jan" value="4.6"/><ChartDataPoint label="Mar" value="4.6"/><ChartDataPoint label="May" value="5.4"/><ChartDataPoint label="Jun" value="5.2"/></ChartSeries>
          </Chart>"""
    if dark:
        chart_xml = f'<VStack w="528" backgroundColor="$chartSurface" padding="8" borderRadius="12">{chart_xml}</VStack>'

    xml = f"""<Slide>
  <VStack w="1280" h="720" padding="36" gap="14" backgroundColor="$surface" alignItems="start">
    <Text w="1208" fontSize="14" bold="true" color="{eyebrow}" letterSpacing="2">H1 2026 REVIEW</Text>
    <Text w="1208" fontSize="28" bold="true" color="$textMain">Zepto wins volume, <Span color="{phrase}">Blinkit wins efficiency</Span></Text>
    <Shape shapeType="rect" w="120" h="5" fill.color="$accent" />
    <HStack w="1208" gap="16">
      {kpi("H1 GMV", "44.08", " Cr", chip("+22.2%", pos_t, pos_bg))}
      {kpi("Blended ROAS", "5.09", "x", chip("watch", warn_t, warn_bg))}
      {kpi("Blinkit MoM (Jun)", "-18.4", "%", chip("-18.4%", neg_t, neg_bg))}
    </HStack>
    <HStack w="1208" gap="24" alignItems="start">
      <VStack w="560" gap="6">
        <Text fontSize="14" color="$textMuted">Platform snapshot, highlighted row = the one the headline rests on</Text>
        <Table defaultRowHeight="44" cellBorder.color="{rule}" cellBorder.width="1">
          <Col width="220" /><Col /><Col />
          {trs}
        </Table>
      </VStack>
      <VStack w="528" gap="6">
        <Text fontSize="14" color="$textMuted">Monthly sales (Rs Cr), focus series vs the rest</Text>
        {chart_xml}
      </VStack>
    </HStack>
    <HStack w="1208" gap="20" alignItems="center">
      <VStack grow="1" padding="14" gap="4" backgroundColor="{callout_bg}" borderLeft.color="$accent" borderLeft.width="5" justifyContent="center">
        <HStack gap="10" alignItems="center">
          <Shape shapeType="ellipse" w="30" h="30" fill.color="$accent" color="{step_fg}" fontSize="14" bold="true" textAlign="center">1</Shape>
          <Text fontSize="14" bold="true" color="{callout_lab}" letterSpacing="1">WHY IT MATTERS</Text>
        </HStack>
        <Text fontSize="14" color="$textMain" lineHeight="1.4">Rs 2.71 Cr of ads returned Rs 13.78 Cr of sales; Blinkit's 6.69x is the ceiling to scale towards.</Text>
      </VStack>
      <HStack gap="2">{ramp_cells}</HStack>
    </HStack>
  </VStack>
</Slide>"""
    return xml, pairs


# --- build / render -----------------------------------------------------------
def _compile_and_render(xml: str, theme: str, out_dir: Path, name: str) -> Path:
    import fitz  # pymupdf

    out_dir.mkdir(parents=True, exist_ok=True)
    src = out_dir / f"{name}.xml"
    src.write_text(theme + "\n" + xml, encoding="utf-8")
    comp_dir = out_dir / f"{name}_pptx"
    r = subprocess.run(["node", str(_COMPILE), str(src), str(comp_dir)], capture_output=True, text=True, timeout=180)
    res = json.loads((comp_dir / "compile-result.json").read_text(encoding="utf-8")) \
        if (comp_dir / "compile-result.json").exists() else {"status": "no result", "stderr": r.stderr[:400]}
    pptx = comp_dir / "presentation.pptx"
    if not pptx.exists():
        raise RuntimeError(f"{name}: compile failed: {json.dumps(res)[:600]}")
    subprocess.run([str(_SOFFICE), "--headless", "--convert-to", "pdf", "--outdir", str(comp_dir), str(pptx)],
                   capture_output=True, text=True, timeout=240)
    pdf = comp_dir / "presentation.pdf"
    page = fitz.open(pdf)[0]
    png = out_dir / f"{name}.png"
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(png)
    shutil.rmtree(comp_dir, ignore_errors=True)
    return png


def _sheet(before: Path, after: Path, label: str, out: Path) -> None:
    from PIL import Image, ImageDraw
    a, b = Image.open(before).convert("RGB"), Image.open(after).convert("RGB")
    pad, bar = 16, 40
    sheet = Image.new("RGB", (a.width + b.width + pad * 3, max(a.height, b.height) + bar + pad), "white")
    d = ImageDraw.Draw(sheet)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = None
    d.text((pad, 8), f"{label}  -  BEFORE (today's recipes)", fill="black", font=font)
    d.text((a.width + pad * 2, 8), f"{label}  -  AFTER (proposed tokens)", fill="black", font=font)
    sheet.paste(a, (pad, bar))
    sheet.paste(b, (a.width + pad * 2, bar))
    sheet.save(out)


def run(names: list[str], out_root: Path) -> list[dict]:
    lib = yaml.safe_load(_PALETTES.read_text(encoding="utf-8"))["palettes"]
    summary = []
    for name in names:
        p = dict(lib[name])
        base_tokens = {k: p[k] for k in ("surface", "surfaceAlt", "accent", "accentAlt", "positive", "negative",
                                          "warning", "textMain", "textMuted", "border") if k in p}
        if p["mode"] == "dark":
            base_tokens["chartSurface"], base_tokens["chartInk"] = p["chartSurface"], p["chartInk"]
        fixed = {**p, **PALETTE_FIXES.get(name, {})}
        d = derive(fixed)
        after_tokens = {**base_tokens, **{k: fixed[k] for k in PALETTE_FIXES.get(name, {})}, **d}
        out_dir = out_root / name
        xml_b, pairs_b = _slide(p, False, derive(p))
        xml_a, pairs_a = _slide(fixed, True, d)
        png_b = _compile_and_render(xml_b, theme_element(base_tokens), out_dir, "before")
        png_a = _compile_and_render(xml_a, theme_element(after_tokens), out_dir, "after")
        _sheet(png_b, png_a, name, out_dir / "sheet.png")
        rows = []
        for (label, fb, bb), (_, fa, ba) in zip(pairs_b, pairs_a):
            rows.append((label, ratio(fb, bb), ratio(fa, ba)))
        summary.append({"palette": name, "mode": p["mode"], "rows": rows, "derived": d,
                        "fixes": PALETTE_FIXES.get(name, {})})
        print(f"{name}: rendered -> {out_dir / 'sheet.png'}")
    return summary


def write_summary(summary: list[dict], out_root: Path) -> None:
    lines = ["# Palette preview: contrast of the specimen's text pairs, before vs after", "",
             "Ratios are WCAG; 4.5 is the floor for small text. `before` = today's recipe colours, "
             "`after` = proposed derived tokens (prototype rules, docs/palette-quality-research-2026-10-06.md §5).", ""]
    for s in summary:
        lines += [f"## {s['palette']} ({s['mode']})", ""]
        if s["fixes"]:
            lines += [f"Palette fix applied in `after` (§5.1): {s['fixes']}", ""]
        lines += ["| Pair | Before | After |", "|---|---|---|"]
        for label, b, a in s["rows"]:
            mark = lambda v: f"{v:.2f}" + (" FAIL" if v < 4.5 else "")
            lines.append(f"| {label} | {mark(b)} | {mark(a)} |")
        nb = sum(1 for _, b, _ in s["rows"] if b < 4.5)
        na = sum(1 for _, _, a in s["rows"] if a < 4.5)
        lines += ["", f"Pairs under 4.5:1: before {nb}, after {na}.", ""]
        lines += ["Derived tokens: " + ", ".join(f"`{k}`={v}" for k, v in s["derived"].items()), ""]
    (out_root / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("palettes", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="output/palette_preview")
    args = ap.parse_args()
    lib = yaml.safe_load(_PALETTES.read_text(encoding="utf-8"))["palettes"]
    names = list(lib) if args.all else (args.palettes or ["navy-orange", "gj-h1", "claude-cream", "graphite-dark"])
    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = _ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)
    summary = run(names, out_root)
    write_summary(summary, out_root)
    print(f"summary: {out_root / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
