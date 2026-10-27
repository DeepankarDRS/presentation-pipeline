"""Composition convention: the proposed KPI and card compositions beside today's style variants, LLM-free
(docs/composition-convention-spec.md §6).

    python -m scripts.composition_convention                  # kpi + card, corporate-slate + graphite-dark
    python -m scripts.composition_convention --only kpi

One sample plan per block (typed schema, content_from_data validates it). Each composition is hand-written as the
XML its node would expand to, with the composition's theme-default look ($tokens and the plan's tone roles only, no
LLM attributes), and drawn on two palettes. The same XML on both palettes: the theme supplies every colour.
Peer ids as the real nodes write them, so fit-grow grows peers to one size: KPI parts are element refs
(<Text ref="kpis.0.value"/> -> kpiv- ids), card boxes are card-<cid>-<i>. Today's row is the real
<KpiGrid> / <CardGrid> code (POM_BLOCKS=tiles). Writes <out>/<block>.png and every slide's folder.
"""

from __future__ import annotations

import argparse
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
from src.compiler.nodes import tiles  # noqa: E402

OUT = ROOT / "output" / "composition-convention"
PALETTES = ("corporate-slate", "graphite-dark")
X, comp, t = LB.X, LB.comp, CT.t

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


def a(**kw: str) -> str:
    return "".join(f' {k.replace("__", ".")}="{X(v)}"' for k, v in kw.items())


# ── KPI compositions (default look: theme tokens + the plan's tone roles) ────────

def kpi_role(i: int) -> str:
    return tiles.tone_role(KPIS, i)   # good -> positive, bad -> negative, watch -> warning, none -> accent


def kpi_parts(i: int, value_color: bool = True, hero: bool = False, ink: str = "") -> tuple[str, str, str, str]:
    """(icon, label, value, delta) for item i: element refs, so code writes the text and the peer ids."""
    r, cd = kpi_role(i), KPIS["content_data"]
    icon = f'<Icon name="{cd["kpi_icons"][i]}" size="24" color="{ink or f"${r}Text"}" />'
    label = f'<Text ref="kpis.{i}.label"{a(color=ink) if ink else ""} />'
    vc = ink or (f"${r}Text" if value_color and r != "accent" else "")
    value = f'<Text ref="kpis.{i}.value"{a(color=vc) if vc else ""}{a(size="hero") if hero else ""} />'
    note = f'<Text ref="kpis.{i}.note"{a(color=ink) if ink else ""} />'
    return icon, label, value, note


def kpi_strip() -> str:
    """strip: one shared box, the items side by side split by hairlines, one row (today's `divided`)."""
    items = []
    for i in range(4):
        icon, label, value, note = kpi_parts(i)
        rule = a(borderLeft__color="$border", borderLeft__width="1", padding__left="28") if i else ""
        items.append(f'<VStack id="kpis-item-{i}" w="1" grow="1" gap="8" justifyContent="center"{rule}>'
                     f'<HStack gap="10" alignItems="center">{icon}{label}</HStack>{value}{note}</VStack>')
    return (f'<HStack gap="28" grow="1" alignItems="stretch" padding="28" backgroundColor="$surfaceAlt" '
            f'border.color="$border" border.width="1">{"".join(items)}</HStack>')


def kpi_rows() -> str:
    """rows: one item per full-width row, hairlines between: icon, label over delta, the value at the right."""
    rows = []
    for i in range(4):
        icon, label, value, note = kpi_parts(i)
        rule = a(borderTop__color="$border", borderTop__width="1") if i else ""
        badge = (f'<VStack w="48" h="48" backgroundColor="${kpi_role(i)}Soft" justifyContent="center" '
                 f'alignItems="center">{icon}</VStack>')
        rows.append(f'<HStack id="kpis-item-{i}" grow="1" gap="18" alignItems="center" padding.top="10" padding.bottom="10"{rule}>'
                    f'{badge}<VStack grow="1" gap="4">{label}{note}</VStack>'
                    f'{value.replace(" />", " textAlign=\"right\" />")}</HStack>')
    return f'<VStack gap="0" grow="1" padding.left="8" padding.right="8">{"".join(rows)}</VStack>'


def kpi_banded() -> str:
    """banded: equal boxes, each with a solid head band (icon + label) over the value and delta."""
    items = []
    for i in range(4):
        r = kpi_role(i)
        icon, label, value, note = kpi_parts(i, value_color=False)
        icon_b = icon.replace(f'color="${r}Text"', 'color="$onAccent"')
        label_b = label.replace(" />", ' color="$onAccent" />')
        items.append(f'<VStack id="kpis-item-{i}" w="1" grow="1" gap="0" border.color="$border" border.width="1">'
                     f'<HStack gap="10" padding="14" alignItems="center" backgroundColor="${r}">{icon_b}{label_b}</HStack>'
                     f'<VStack grow="1" gap="8" padding="20" justifyContent="center" backgroundColor="$surfaceAlt">{value}{note}</VStack></VStack>')
    return f'<HStack gap="18" grow="1" alignItems="stretch">{"".join(items)}</HStack>'


def kpi_bento() -> str:
    """bento: the plan's emphasis item as one large dark block, value first; the rest stacked beside it."""
    e = tiles.emphasis_index(KPIS)
    icon, label, value, note = kpi_parts(e, hero=True, ink="$onPanelDark")
    hero = (f'<VStack id="kpis-hero" w="42%" gap="12" padding="32" justifyContent="center" backgroundColor="$panelDark">'
            f'{icon}{value}{label}{note}</VStack>')
    rest = []
    for i in (k for k in range(4) if k != e):
        icon, label, value, note = kpi_parts(i)
        rest.append(f'<HStack id="kpis-item-{i}" grow="1" gap="16" padding="18" alignItems="center" backgroundColor="$surfaceAlt" '
                    f'border.color="$border" border.width="1">{icon}<VStack grow="1" gap="4">{label}{note}</VStack>'
                    f'{value.replace(" />", " textAlign=\"right\" />")}</HStack>')
    return f'<HStack gap="18" grow="1" alignItems="stretch">{hero}<VStack grow="1" gap="14">{"".join(rest)}</VStack></HStack>'


# ── card compositions ─────────────────────────────────────────────────────────

def card_role(i: int) -> str:
    return {"good": "positive", "bad": "negative", "watch": "warning"}.get(CARDS["content_data"]["cards"][i].get("tone", ""), "accent")


def body(c: dict, px: int = 18, color: str = "$textMuted", key: str = "") -> str:
    """The body line, its key phrase as a coloured span (as cards.py draws it)."""
    text, kp = c["body"], c.get("key_phrase")
    if kp and kp in text:
        pre, post = text.split(kp, 1)
        inner = f'{X(pre)}<Span color="{key}" bold="true">{X(kp)}</Span>{X(post)}'
    else:
        inner = X(text)
    return f'<Text fontSize="{px}" color="{color}" lineHeight="1.35">{inner}</Text>'


def bullets(c: dict, px: int = 17, color: str = "$textMain") -> str:
    return f'<Ul fontSize="{px}" lineHeight="1.4" color="{color}">{"".join(f"<Li>{X(b)}</Li>" for b in c["bullets"])}</Ul>'


def focus() -> int:
    return CARDS["content_data"]["focus_card"]


def card_rows() -> str:
    """rows numbered: one card per full-width row, hairlines between: code's number, tag + title, body, bullets."""
    rows = []
    for i, c in enumerate(CARDS["content_data"]["cards"]):
        r = card_role(i)
        rule = a(borderTop__color="$border", borderTop__width="1") if i else ""
        rows.append(f'<HStack id="card-levers-{i}" grow="1" gap="24" alignItems="center" padding.top="10" padding.bottom="10"{rule}>'
                    f'{t(f"{i + 1:02d}", 40, f"${r}Text", bold="true")}'
                    f'<VStack w="22%" gap="4">{t(c["tag"], 13, f"${r}Text", bold="true", letterSpacing="1")}'
                    f'{t(c["title"], 26, bold="true")}</VStack>'
                    f'<VStack w="1" grow="1">{body(c, 20, key=f"${r}Text")}</VStack>'
                    f'<VStack w="30%">{bullets(c, 18)}</VStack></HStack>')
    return f'<VStack gap="0" grow="1">{"".join(rows)}</VStack>'


def card_columns() -> str:
    """columns: one column per card: a pill head (icon + title), the body, each bullet in its own box."""
    cols = []
    for i, c in enumerate(CARDS["content_data"]["cards"]):
        r = card_role(i)
        fill, ink = ("$panelDark", "$onPanelDark") if i == focus() else (f"${r}", "$onAccent")
        pill = (f'<HStack padding="14" gap="10" alignItems="center" justifyContent="center" backgroundColor="{fill}" borderRadius="24">'
                f'<Icon name="{c["icon"]}" size="22" color="{ink}" />{t(c["title"], 20, ink, bold="true")}</HStack>')
        boxes = "".join(f'<VStack grow="1" padding="14" justifyContent="center" backgroundColor="$surfaceAlt" border.color="$border" '
                        f'border.width="1" borderRadius="8">{t(b, 17)}</VStack>' for b in c["bullets"])
        cols.append(f'<VStack id="card-levers-{i}" w="1" grow="1" gap="12" alignItems="stretch">{pill}'
                    f'{body(c, 16, key=f"${r}Text")}{boxes}</VStack>')
    return f'<HStack gap="18" grow="1" alignItems="stretch">{"".join(cols)}</HStack>'


def card_banded() -> str:
    """banded: equal boxes in a grid, each with a solid head band (icon + title, tag at the right) over body + bullets."""
    blocks = []
    for i, c in enumerate(CARDS["content_data"]["cards"]):
        r = card_role(i)
        fill, ink = ("$panelDark", "$onPanelDark") if i == focus() else (f"${r}", "$onAccent")
        band = (f'<HStack padding="14" gap="10" alignItems="center" backgroundColor="{fill}">'
                f'<Icon name="{c["icon"]}" size="22" color="{ink}" /><VStack grow="1">{t(c["title"], 20, ink, bold="true")}</VStack>'
                f'{t(c["tag"], 12, ink, bold="true", letterSpacing="1")}</HStack>')
        inner = (f'<VStack grow="1" gap="10" padding="18" backgroundColor="$surfaceAlt">{body(c, 17, key=f"${r}Text")}'
                 f'{bullets(c)}</VStack>')
        blocks.append(f'<VStack id="card-levers-{i}" w="1" grow="1" gap="0" border.color="$border" border.width="1">{band}{inner}</VStack>')
    return ('<VStack gap="18" grow="1">' + "".join(f'<HStack gap="18" grow="1" alignItems="stretch">{"".join(blocks[k:k + 2])}</HStack>'
                                                  for k in (0, 2)) + "</VStack>")


def card_bento() -> str:
    """bento: the plan's focus card as one large dark block; the rest as 2 + 1 beside it."""
    cs, f = CARDS["content_data"]["cards"], focus()
    c = cs[f]
    big = (f'<VStack id="cardf-levers-{f}" w="40%" gap="14" padding="32" justifyContent="center" backgroundColor="$panelDark" borderRadius="8">'
           f'<Icon name="{c["icon"]}" size="36" color="$onPanelDark" />{t(c["tag"], 13, "$onPanelDark", bold="true", letterSpacing="1")}'
           f'{t(c["title"], 30, "$onPanelDark", bold="true")}{body(c, 20, "$onPanelDark", key="$onPanelDark")}'
           f'{bullets(c, 18, "$onPanelDark")}</VStack>')
    small = []
    for i in (k for k in range(len(cs)) if k != f):
        r, c = card_role(i), cs[i]
        tint = a(backgroundColor=f"${r}Soft", border__color=f"${r}") if c.get("tone") else a(backgroundColor="$surfaceAlt", border__color="$border")
        small.append(f'<VStack id="card-levers-{i}" w="1" grow="1" gap="8" padding="20" borderRadius="8" border.width="1"{tint}>'
                     f'<HStack gap="10" alignItems="center"><Icon name="{c["icon"]}" size="22" color="${r}Text" />'
                     f'{t(c["title"], 20, bold="true")}</HStack>{body(c, 16, key=f"${r}Text")}{bullets(c, 15)}</VStack>')
    right = (f'<VStack grow="1" gap="18"><HStack gap="18" grow="1" alignItems="stretch">{"".join(small[:2])}</HStack>'
             f'<HStack gap="18" grow="1" alignItems="stretch">{small[2]}</HStack></VStack>')
    return f'<HStack gap="18" grow="1" alignItems="stretch">{big}{right}</HStack>'


# ── sheets ────────────────────────────────────────────────────────────────────

BLOCKS = {
    "kpi": (KPIS, KPI_HEAD,
            [(f"today · {v} (style)", f'<KpiGrid ref="kpis" variant="{v}" grow="1" />') for v in ("plain", "filled", "bar")],
            [("strip", kpi_strip), ("rows", kpi_rows), ("banded", kpi_banded), ("bento", kpi_bento)]),
    "card": (CARDS, CARD_HEAD,
             [(f"today · {v} (style)", f'<CardGrid ref="levers" variant="{v}" />') for v in ("lifted", "filled", "accent_top")],
             [("rows numbered", card_rows), ("columns", card_columns), ("banded", card_banded), ("bento", card_bento)]),
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
