"""A gallery deck of the KPI row and card block variants (docs/block-variants-look-spec.md).

    python -m scripts.variant_gallery [--palette corporate-slate] [--out output/variant-gallery]

Five slides, hand-written POM that draws each variant as the look spec describes it, from one palette
in palettes.yaml plus the derived role tokens (D1): the node syntax, the KPI row variants, the card
grid variants, the card steps variants, and the context variants (bare, tones, toned, accent_top).
Content is synthetic. It is a picture of the spec for review,
not the step 1 blocks: sizes are fixed here, the blocks will measure them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.compiler.font_embed import embed_deck_fonts  # noqa: E402
from src.compiler.pptx_merge import merge_pptx_files  # noqa: E402

SANS, MONO = "Inter", "JetBrains Mono"


# ── palette + derived role tokens (D1) ───────────────────────────────────────

def _lum(hex_color: str) -> float:
    def ch(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, t: float) -> str:
    """a moved t of the way toward b."""
    pa, pb = ([int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in (a, b))
    return "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


def first_ok(bg: str, candidates: list[str], need: float = 4.5) -> str:
    return next((c for c in candidates if contrast(c, bg) >= need), "FFFFFF" if _lum(bg) < 0.4 else "000000")


def ink(color: str, toward: str, bgs: list[str], need: float = 4.5) -> str:
    """color moved toward `toward` (a palette text colour) in 10% steps until it reads on every bg."""
    for k in range(11):
        c = mix(color, toward, k / 10)
        if all(contrast(c, bg) >= need for bg in bgs):
            return c
    return toward


def fill(color: str, base: str, readers: list[str], start: float = 0.88, need: float = 4.5) -> str:
    """color mixed toward the slide colour `base` (from `start`) until every reader text reads on it."""
    k = start
    while k < 1 and any(contrast(r, mix(color, base, k)) < need for r in readers):
        k = min(1.0, k + 0.02)
    return mix(color, base, k)


def tokens(name: str) -> dict[str, str]:
    """The palette's colours plus the role colours the blocks use, all derived from that palette:
    mixes of its own colours, moved until the text on them reaches 4.5:1 (D1, look spec §2)."""
    pal = yaml.safe_load((ROOT / "src/knowledge/theme/palettes.yaml").read_text(encoding="utf-8"))["palettes"][name]
    t = {k: pal[k] for k in ("surface", "surfaceAlt", "accent", "accentAlt", "positive", "negative",
                             "warning", "textMain", "textMuted", "border")}
    dark = pal.get("mode", "light") == "dark"
    # panelFill (V8): surfaceAlt when it shows against the slide, else surface stepped toward the
    # text colour, as far as muted text on it still reads
    if contrast(t["surfaceAlt"], t["surface"]) >= 1.12:
        t["panelFill"] = t["surfaceAlt"]
    else:
        steps = [mix(t["surface"], t["textMain"], s / 100) for s in (8, 7, 6, 5, 4, 3)]
        t["panelFill"] = next((c for c in steps if contrast(t["textMuted"], c) >= 4.5), t["surfaceAlt"])
    t["panelInk"] = ink(t["textMain"], t["textMain"], [t["panelFill"]])
    t["darkFill"] = mix(t["surface"], t["textMain"], 0.12) if dark else t["textMain"]
    t["onDark"] = first_ok(t["darkFill"], [t["surface"], t["surfaceAlt"], t["textMain"]])
    t["accentOnDark"] = ink(t["accent"], t["onDark"], [t["darkFill"]])
    # accentSolid + onAccent: a solid accent fill with text on it (the hero pill). A mid-tone accent
    # that neither light nor dark text reads on is darkened toward the text colour until light text reads
    t["accentSolid"], t["onAccent"] = t["accent"], first_ok(t["accent"], [t["surface"], t["surfaceAlt"], t["textMain"]])
    if contrast(t["onAccent"], t["accent"]) < 4.5:
        t["onAccent"] = t["surface"] if not dark else t["textMain"]
        t["accentSolid"] = ink(t["accent"], t["darkFill"] if not dark else t["surface"], [t["onAccent"]])
    # accentInk: the accent as small text (tags, kickers) on the slide and on panels
    t["accentInk"] = ink(t["accent"], t["textMain"], [t["surface"], t["panelFill"], t["surfaceAlt"]])
    # accentTint (V1): the accent mixed toward the slide colour until body and muted text read on it
    t["accentTint"] = fill(t["accent"], t["surface"], [t["textMain"], t["textMuted"]], 0.8 if dark else 0.88)
    # tone tints + tone inks (V9): a tinted card per tone; the tone as text on its tint and on panels
    for tone in ("positive", "negative", "warning"):
        t[tone + "Tint"] = fill(t[tone], t["surface"], [t["textMain"], t["textMuted"]], 0.8 if dark else 0.9)
        t[tone + "Ink"] = ink(t[tone], t["textMain"], [t[tone + "Tint"], t["panelFill"], t["surface"]])
    return t


def theme_xml(t: dict[str, str]) -> str:
    return "<Theme " + " ".join(f'{k}="{v}"' for k, v in t.items()) + " />"


# ── text helpers ─────────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def label(text: str, color: str = "$textMuted", size: int = 12) -> str:
    return f'<Text fontFamily="{MONO}" fontSize="{size}" letterSpacing="1.6" color="{color}">{esc(text.upper())}</Text>'


def text(s: str, size: int, color: str, bold: bool = False, extra: str = "") -> str:
    b = ' bold="true"' if bold else ""
    return f'<Text fontFamily="{SANS}" fontSize="{size}"{b} color="{color}" lineHeight="1.25"{extra}>{esc(s)}</Text>'


VALUE = re.compile(r"^(?P<head>[+\-\u2212~<>\u2248]?[\u20b9$\u20ac\u00a3\u00a5]?\d[\d,]*(?:\.\d+)?)\s?(?P<unit>%|x|\u00d7|[A-Za-z]{1,3})?$")


def split_value(value: str) -> tuple[str, str]:
    """(number, unit) for a KPI value (look spec §7c, V15); no full match -> (value, "")."""
    m = VALUE.match(value.strip())
    return (m["head"], m["unit"] or "") if m else (value, "")


def number(value: str, size: int, color: str) -> str:
    """Bold number; its unit (%, x, ×, Cr, B, K …) as a 0.45x span; anything else drawn whole."""
    head, unit = split_value(value)
    span = f'<Span fontSize="{round(size * 0.45)}">{esc(unit)}</Span>' if unit else ""
    return f'<Text fontFamily="{SANS}" fontSize="{size}" bold="true" color="{color}" lineHeight="1.2">{esc(head)}{span}</Text>'


def code(lines: str, size: int = 13) -> str:
    rows = "".join(f'<Text fontFamily="{MONO}" fontSize="{size}" color="$onDark" lineHeight="1.35">{esc(ln) or " "}</Text>'
                   for ln in lines.strip("\n").split("\n"))
    return rows


def header(kicker: str, headline: str, sub: str) -> str:
    return (f'<VStack gap="6">{label(kicker, "$accentInk")}{text(headline, 30, "$textMain", True)}'
            f'{text(sub, 15, "$textMuted")}</VStack>')


def slide(t: dict, body: str) -> str:
    return (f'{theme_xml(t)}\n<Slide><VStack w="1280" h="720" backgroundColor="$surface" padding="40" gap="18" '
            f'alignItems="stretch">{body}</VStack></Slide>\n')


def variant_caption(name: str, slot: str, note: str) -> str:
    return (f'<Text fontFamily="{SANS}" fontSize="16" color="$textMain"><B>{esc(name)}</B>   '
            f'<Span fontFamily="{MONO}" fontSize="12" color="$accentInk">{esc(slot)}</Span>   '
            f'<Span fontSize="12" color="$textMuted">{esc(note)}</Span></Text>')


# ── KPI row ──────────────────────────────────────────────────────────────────

KPIS = [("Revenue", "₹4.2Cr", "+18% vs H2"), ("Blended ROAS", "0.33x", "Target 1.0x"),
        ("Ad spend", "₹12.7Cr", "+42% vs H2"), ("Orders", "18.4K", "")]
FOCUS = "Blended ROAS"   # the design hint names it


def kpi_tile(lab: str, val: str, note: str, fill: str, ink: str, lab_c: str, note_c: str, fs: int = 34,
             border: str = "") -> str:
    note_xml = label(note, note_c) if note else ""
    return (f'<VStack grow="1" w="1" padding="16" gap="4" backgroundColor="{fill}"{border} justifyContent="spaceBetween">'
            f'{label(lab, lab_c)}<VStack gap="6">{number(val, fs, ink)}{note_xml}</VStack></VStack>')


def kpi_row(variant: str) -> str:
    tiles = []
    for lab, val, note in KPIS:
        if variant == "filled":
            tiles.append(kpi_tile(lab, val, note, "$accentTint", "$textMain", "$textMuted", "$textMuted"))
        elif variant == "inverted" and lab == FOCUS:
            tiles.append(kpi_tile(lab, val, note, "$darkFill", "$onDark", "$accentOnDark", "$onDark"))
        else:
            tiles.append(kpi_tile(lab, val, note, "$panelFill", "$panelInk", "$textMuted", "$textMuted"))
    return f'<HStack grow="1" gap="12" alignItems="stretch">{"".join(tiles)}</HStack>'


def kpi_hero() -> str:
    pill = (f'<HStack padding.left="12" padding.right="12" padding.top="4" padding.bottom="4" '
            f'backgroundColor="$accentSolid" borderRadius="12">{label("Target 1.0x", "$onAccent")}</HStack>')
    return (f'<HStack grow="1" padding="18" gap="28" backgroundColor="$darkFill" alignItems="center">'
            f'<VStack gap="10" alignItems="start">{label("Blended ROAS · H1 FY27", "$accentOnDark")}{pill}</VStack>'
            f'{number("0.33x", 72, "$onDark")}'
            f'<VStack grow="1" />'
            f'{text("one value only (count = 1); the pill is kpi_deltas[0], verbatim", 13, "$onDark")}</HStack>')


def kpi_slide(t: dict) -> str:
    def block(name: str, note: str, inner: str) -> str:
        slot = '<KpiRow ref="c2" grow="1" variant="' + name + '" />'
        return f'<VStack grow="1" gap="6" alignItems="stretch">{variant_caption(name, slot, note)}{inner}</VStack>'
    return slide(t, header("Block variants · KPI row", "One KPI row, four variants",
                           "Same plan component every time; only the node's variant attribute changes.")
                 + f'<VStack grow="1" gap="14" alignItems="stretch">'
                 + block("plain", "default · light tiles", kpi_row("plain"))
                 + block("filled", "every tile accent-tinted", kpi_row("filled"))
                 + block("inverted", "3+ tiles · the tile the design hint names", kpi_row("inverted"))
                 + block("hero", "exactly 1 value → else falls back to inverted", kpi_hero())
                 + "</VStack>")


# ── syntax slide ─────────────────────────────────────────────────────────────

SKELETON = """\
<VStack w="1280" h="720" padding="48" gap="20">
  <Text fontSize="30" bold="true">Spend grew
    2.4x faster than revenue</Text>
  <KpiRow ref="c2" grow="1"
          variant="inverted" />
  <HStack grow="2" gap="24">
    <Chart ref="c3" w="2" grow="1"
           showLegend="false" />
    <Timeline ref="c4" w="1"
              direction="vertical" />
  </HStack>
</VStack>"""

PLAN = """\
{ "id": "c2", "kind": "kpi_row",
  "weight": "hero",
  "content_data": {
    "kpi_labels": ["Revenue",
      "Blended ROAS", "Ad spend",
      "Orders"],
    "kpi_values": ["₹4.2Cr",
      "0.33x", "₹12.7Cr", "18.4K"],
    "kpi_deltas": ["+18% vs H2",
      "Target 1.0x", "+42% vs H2",
      null] } }"""

EXPANDED = """\
<HStack grow="1" gap="12">
  <VStack w="1" grow="1" padding="16"
          backgroundColor="$panelFill">
    <Text fontSize="12" color="$textMuted">
      REVENUE</Text>
    <Text fontSize="44" bold="true">4.2
      <Span fontSize="20">Cr</Span></Text>
  </VStack>
  <VStack w="1" grow="1" padding="16"
          backgroundColor="$darkFill">
    <Text color="$accentOnDark">
      BLENDED ROAS</Text>
    <Text color="$onDark">0.33…</Text>
  </VStack>
  … 2 more tiles …
</HStack>"""


def syntax_slide(t: dict) -> str:
    def col(title: str, who: str, body: str, w: int) -> str:
        return (f'<VStack w="{w}" grow="{w}" gap="8" alignItems="stretch">{label(who, "$accentInk")}'
                f'{text(title, 17, "$textMain", True)}'
                f'<VStack grow="1" padding="16" gap="0" backgroundColor="$darkFill">{code(body)}</VStack></VStack>')
    arrow = f'<VStack w="28" alignItems="center" justifyContent="center"><Icon name="arrow-right" size="24" color="$textMuted" /></VStack>'
    return slide(t, header("Block variants · syntax", "The LLM places a node by ref; code writes what is inside",
                           "Derived tags (KpiRow, CardGrid) become blocks; native tags (Chart, Timeline, Table …) get their children from the plan.")
                 + f'<HStack grow="1" gap="14" alignItems="stretch">'
                 + col("1 · Skeleton (generator LLM)", "LLM writes", SKELETON, 10) + arrow
                 + col("2 · Plan component (ref c2)", "plan supplies", PLAN, 8) + arrow
                 + col("3 · Expanded POM (node pass)", "code writes", EXPANDED, 10)
                 + "</HStack>"
                 + text("On every ref tag: ref, w, h, grow, alignSelf, variant; native tags also keep their own presentation "
                        "attributes (direction, legend). Children and content attributes are code's (NODE_ATTR_IGNORED).", 13, "$textMuted"))


# ── card grid ────────────────────────────────────────────────────────────────

CARDS = [("Search share", "Branded search fell 4 pts after the price change."),
         ("Ad efficiency", "ROAS 0.33x against a 1.0x target."),
         ("Retention", "Repeat orders steady at 38% of revenue."),
         ("Pricing", "Two SKUs above the category median.")]
FEATURED = "Ad efficiency"


def card(i: int, title: str, body: str, fill: str, ink: str, body_c: str, tag_c: str, border: bool,
         numeral: bool = False, title_fs: int = 18) -> str:
    b = ' border.color="$border" border.width="1"' if border else ""
    top = (f'<Text fontFamily="{SANS}" fontSize="54" bold="true" color="$border" lineHeight="1">{i + 1:02d}</Text>'
           if numeral else label(f"{i + 1:02d}", tag_c))
    return (f'<VStack w="1" grow="1" padding="16" gap="8" backgroundColor="{fill}"{b}>{top}'
            f'{text(title, title_fs, ink, True)}{text(body, 14, body_c)}</VStack>')


def grid(variant: str) -> str:
    if variant == "featured":
        i = next(k for k, (ti, _) in enumerate(CARDS) if ti == FEATURED)
        big = (f'<VStack w="4" grow="4" padding="18" gap="10" backgroundColor="$darkFill" justifyContent="end">'
               f'{label(f"{i + 1:02d}", "$accentOnDark")}{text(FEATURED, 24, "$onDark", True)}'
               f'{text(CARDS[i][1], 15, "$onDark")}</VStack>')
        rest = "".join(f'<VStack grow="1" padding.left="14" padding.right="14" justifyContent="center" gap="2" '
                       f'backgroundColor="$panelFill">{text(ti, 15, "$panelInk", True)}{text(bo, 13, "$textMuted")}</VStack>'
                       for ti, bo in CARDS if ti != FEATURED)
        return f'<HStack grow="1" gap="10" alignItems="stretch">{big}<VStack w="6" grow="6" gap="8" alignItems="stretch">{rest}</VStack></HStack>'
    cards = []
    for i, (ti, bo) in enumerate(CARDS):
        if variant == "filled":
            cards.append(card(i, ti, bo, "$panelFill", "$panelInk", "$textMuted", "$accentInk", False, title_fs=16))
        else:
            cards.append(card(i, ti, bo, "$surface", "$textMain", "$textMuted", "$accentInk", True,
                              numeral=variant == "numerals", title_fs=16))
    return f'<HStack grow="1" gap="10" alignItems="stretch">{"".join(cards)}</HStack>'


def quad(name: str, note: str, inner: str) -> str:
    attr = 'variant="' + name + '"'
    return f'<VStack w="1" grow="1" gap="8" alignItems="stretch">{variant_caption(name, attr, note)}{inner}</VStack>'


def grid_slide(t: dict) -> str:
    return slide(t, header("Block variants · card grid", "One card grid, four variants",
                           "Four parallel items; the featured card is the one the design hint names.")
                 + '<VStack grow="1" gap="16" alignItems="stretch">'
                 + '<HStack grow="1" gap="24" alignItems="stretch">'
                 + quad("outline", "default · hairline cards", grid("outline"))
                 + quad("filled", "panel fill, no border", grid("filled")) + "</HStack>"
                 + '<HStack grow="1" gap="24" alignItems="stretch">'
                 + quad("featured", "3+ cards, one named · not matrix", grid("featured"))
                 + quad("numerals", "faint 01-04 · not matrix", grid("numerals")) + "</HStack></VStack>")


# ── card steps ───────────────────────────────────────────────────────────────

STEPS = [("Phase 1", "Fix tracking", "One attribution source for all platforms."),
         ("Phase 2", "Cut waste", "Pause campaigns under 0.2x ROAS."),
         ("Phase 3", "Shift budget", "Move spend to the two best platforms."),
         ("Phase 4", "Scale to 1.0x", "Grow spend only above target ROAS.")]


def steps_cards() -> str:
    out = []
    for k, (tag, ti, bo) in enumerate(STEPS):
        dest = k == len(STEPS) - 1
        fill, ink, body_c, tag_c = (("$darkFill", "$onDark", "$onDark", "$accentOnDark") if dest
                                    else ("$panelFill", "$panelInk", "$textMuted", "$accentInk"))
        top = "$accentOnDark" if dest else "$accent"
        out.append(f'<VStack w="1" grow="1" padding="14" gap="6" backgroundColor="{fill}" '
                   f'borderTop.color="{top}" borderTop.width="3">{label(tag, tag_c)}{text(ti, 17, ink, True)}'
                   f'{text(bo, 14, body_c)}</VStack>')
        if not dest:
            out.append('<VStack w="24" alignItems="center" justifyContent="center"><Icon name="arrow-right" size="18" color="$textMuted" /></VStack>')
    return f'<HStack grow="1" gap="8" alignItems="stretch">{"".join(out)}</HStack>'


def steps_rail() -> str:
    rows = []
    for k, (tag, ti, bo) in enumerate(STEPS):
        dest = k == len(STEPS) - 1
        dot = 16 if dest else 10
        line = '' if dest else '<Shape shapeType="rect" w="2" grow="1" fill.color="$border" />'
        rows.append(f'<HStack grow="1" gap="14" alignItems="stretch">'
                    f'<VStack w="16" alignItems="center"><Shape shapeType="ellipse" w="{dot}" h="{dot}" '
                    f'fill.color="$accent" />{line}</VStack>'
                    f'<VStack grow="1" gap="2">{label(tag, "$accentInk")}'
                    f'{text(ti, 15, "$textMain", True)}{text(bo, 13, "$textMuted")}'
                    f'</VStack></HStack>')
    return f'<VStack grow="1" gap="0" alignItems="stretch">{"".join(rows)}</VStack>'


def steps_columns() -> str:
    segs = "".join(f'<Shape shapeType="rect" w="1" grow="1" h="8" fill.color="{"$accent" if k == len(STEPS) - 1 else "$accentTint"}" />'
                   for k in range(len(STEPS)))
    cols = "".join(f'<VStack w="1" grow="1" gap="6">'
                   f'<Text fontFamily="{SANS}" fontSize="30" bold="true" color="{"$accentInk" if k == len(STEPS) - 1 else "$border"}" lineHeight="1">{k + 1:02d}</Text>'
                   f'{text(ti, 15, "$textMain", True)}{text(bo, 13, "$textMuted")}</VStack>'
                   for k, (_, ti, bo) in enumerate(STEPS))
    return (f'<VStack grow="1" gap="12" alignItems="stretch"><HStack gap="4">{segs}</HStack>'
            f'<HStack grow="1" gap="16" alignItems="stretch">{cols}</HStack></VStack>')


def steps_slide(t: dict) -> str:
    return slide(t, header("Block variants · card steps", "Ordered phases, three variants",
                           "The destination (last step) is singled out unless the design hint names another.")
                 + '<VStack grow="1" gap="16" alignItems="stretch">'
                 + quad("cards", "default · arrows, destination dark", steps_cards()).replace('w="1" grow="1"', 'h="190"', 1)
                 + '<HStack grow="1" gap="28" alignItems="stretch">'
                 + quad("rail", "tall or narrow box", steps_rail())
                 + quad("columns", "segmented progress bar", steps_columns())
                 + "</HStack></VStack>")


# ── context variants: bare, tones, toned, accent_top ─────────────────────────

TONE = {"good": "positive", "bad": "negative", "watch": "warning", "": None}
ARROW = {"up": "▲ ", "down": "▼ ", "": ""}   # code adds the arrow from kpi_directions


def kpi_bare() -> str:
    stats = [("47%", "less processing time"), ("3.2×", "faster decisions"), ("99.99%", "uptime SLA")]
    cells = "".join(f'<VStack gap="2">{number(v, 40, "$onDark")}{label(l, "$accentOnDark")}</VStack>' for v, l in stats)
    return (f'<HStack grow="1" padding.left="24" padding.right="24" gap="64" alignItems="center" '
            f'backgroundColor="$darkFill">{cells}</HStack>')


def kpi_toned_plain() -> str:
    # (label, value, delta, direction, tone): churn going down is good news
    rows = [("ARR", "¥1.24B", "28% YoY", "up", "good"), ("Net new ARR", "¥84M", "12% vs plan", "up", "good"),
            ("NRR", "121%", "4pt QoQ", "up", "good"), ("Gross churn", "1.6%", "0.5pt QoQ", "down", "good"),
            ("Burn multiple", "1.2×", "target < 1.0×", "", "watch")]
    tiles = []
    for lab, val, d, direc, tone in rows:
        role = TONE[tone]
        note_c = f"${role}Ink" if role else "$textMuted"
        tiles.append(kpi_tile(lab, val, ARROW[direc] + d, "$panelFill", "$panelInk", "$textMuted", note_c, fs=30))
    return f'<HStack grow="1" gap="12" alignItems="stretch">{"".join(tiles)}</HStack>'


def cards_toned() -> str:
    cards = [("GROWTH", "Enterprise ARR +31%", "Expansion in the top 20 accounts.", "good"),
             ("WATCH", "APAC acquisition cost +8%", "One-off partner launch costs.", "watch"),
             ("OUTLOOK", "Full-year forecast raised", "Operating profit ¥10.2B → ¥10.8B.", "good")]
    out = []
    for tag, ti, bo, tone in cards:
        r = TONE[tone]
        out.append(f'<VStack w="1" grow="1" padding="14" gap="6" backgroundColor="${r}Tint" '
                   f'borderLeft.color="${r}" borderLeft.width="5">{label(tag, f"${r}Ink")}'
                   f'{text(ti, 19, "$textMain", True)}{text(bo, 15, "$textMuted")}</VStack>')
    return f'<HStack grow="1" gap="10" alignItems="stretch">{"".join(out)}</HStack>'


def cards_accent_top() -> str:
    cards = [("01 / Product", "Field data at the core"), ("02 / Market", "Repeatable wins per industry"),
             ("03 / Delivery", "Adoption is the product"), ("Not doing", "No race on feature count")]
    out = []
    for k, (tag, ti) in enumerate(cards):
        contrast_card = k == len(cards) - 1   # singled out by the plan (the brief's "not doing")
        fill, top = ("$panelFill", "$textMain") if contrast_card else ("$surface", "$accent")
        b = "" if contrast_card else ' border.color="$border" border.width="1"'
        out.append(f'<VStack w="1" grow="1" padding="14" gap="6" backgroundColor="{fill}"{b} '
                   f'borderTop.color="{top}" borderTop.width="4">'
                   f'{label(tag, "$textMain" if contrast_card else "$accentInk")}{text(ti, 20, "$textMain", True)}</VStack>')
    return f'<HStack grow="1" gap="10" alignItems="stretch">{"".join(out)}</HStack>'


def context_slide(t: dict) -> str:
    def row(name: str, note: str, inner: str, size: str = 'grow="1"') -> str:
        attr = 'variant="' + name + '"'
        return f'<VStack {size} gap="6" alignItems="stretch">{variant_caption(name, attr, note)}{inner}</VStack>'
    return slide(t, header("Block variants · context", "Three more variants, and tones from the plan",
                           "Tone (good / bad / watch) comes from the planner and colours every variant; the arrow comes from kpi_directions.")
                 + '<VStack grow="1" gap="14" alignItems="stretch">'
                 + row("bare", "kpi_row · numbers only, no tiles · here on a dark band", kpi_bare(), 'h="112"')
                 + row("plain", "kpi_row + kpi_tones · churn ▼ is good, burn multiple is watch", kpi_toned_plain(), 'h="132"')
                 + '<HStack grow="1" gap="24" alignItems="stretch">'
                 + row("toned", "card_grid · needs tones", cards_toned(), 'w="5" grow="5"')
                 + row("accent_top", "card_grid · the singled-out card contrasts", cards_accent_top(), 'w="7" grow="7"')
                 + "</HStack></VStack>")


# ── build ────────────────────────────────────────────────────────────────────

def build(out: Path, palette: str) -> Path:
    t = tokens(palette)
    out.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, make in enumerate((syntax_slide, kpi_slide, grid_slide, steps_slide, context_slide), 1):
        xml = out / f"slide-{i}.xml"
        xml.write_text(make(t), encoding="utf-8")
        build_dir = out / f"build-{i}"
        subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(xml), str(build_dir)],
                       check=False, capture_output=True, env={**os.environ, "POM_FIT_GROW": "0"})
        result = json.loads((build_dir / "compile-result.json").read_text(encoding="utf-8"))
        if result["status"] != "success":
            raise RuntimeError(f"slide {i} did not compile: {result.get('diagnostics')}")
        parts.append(build_dir / "presentation.pptx")
    deck = merge_pptx_files(parts, out / f"variant-gallery-{palette}.pptx")
    embed_deck_fonts(deck)
    return deck


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--palette", default="corporate-slate")
    ap.add_argument("--out", default="output/variant-gallery")
    args = ap.parse_args()
    print(build(ROOT / args.out, args.palette))


if __name__ == "__main__":
    main()
