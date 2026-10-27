"""Style or composition? LLM-free test for the variant split (docs/eval/composition-test/README.md).

    python -m scripts.composition_test q1            # every KPI / card style variant: variant= vs attributes only
    python -m scripts.composition_test q2            # 8 Perceptis compositions x 2 stylings beside today's variants
    python -m scripts.composition_test q2 --only table

Q1: each style variant is drawn twice through the card gallery's code path (tiles.fill -> cards / tiles expand,
normalize_xml, compile-pom.js with fit-grow, the Inter render): once as `variant="<name>"`, once with no variant
name, the same look written as group / item / part attributes (the variant's look from block-variants.yaml, its
{role} filled per item from the plan tone, plus the resets that undo the default look under it). The two renders
are compared pixel by pixel.

Q2: each composition is hand-written as the XML a node would expand to, from sample components in today's typed
planner schema (content_from_data validates each), and drawn with two stylings. Writes <out>/q1-*.png,
<out>/q2-*.png and <out>/metrics.json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import card_gallery as CG  # noqa: E402
from scripts import left_blocks_gallery as LB  # noqa: E402
from scripts import tile_gallery as TG  # noqa: E402  (sets POM_BLOCKS=tiles)
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.nodes import cards, tiles  # noqa: E402

OUT = ROOT / "output" / "composition-test"
DOCS = ROOT / "docs" / "eval" / "composition-test"
X = LB.X
comp = LB.comp

# a key the default look sets and the target look does not: the attribute that undoes it (attributes only override)
RESET = {"backgroundColor": "$surface", "border.width": "0", "borderLeft.width": "0", "borderTop.width": "0",
         "shadow.opacity": "0"}
RESET_SKIP = {"border.color", "borderLeft.color", "borderTop.color", "shadow.type", "shadow.blur", "shadow.offset",
              "shadow.color"}   # undone with their width / opacity


# ── Q1: a style variant as attributes ──────────────────────────────────────────

def _resolved(vs: dict, name: str, tone: str, role: str) -> dict[str, str]:
    """A variant's look for one item, its with_tone applied, {role} filled (build_tile / build_card, minus house)."""
    patch: dict = {}
    how = (vs[name].get("with_tone") or {}).get(tone) if tone else None
    if isinstance(how, str) and how in vs:
        name = how
    elif isinstance(how, dict):
        patch = how
    if name == "toned" and not tone and vs is cards.card()["variants"]:
        role = "neutral"   # build_card: toned leaves a card without a tone plain
    return {k: tiles.role_value(v, role) for k, v in {**vs[name]["look"], **patch}.items()}


def as_attributes(vs: dict, default: str, target: str, tone: str, role: str) -> tuple[dict[str, str], list[str]]:
    """The attributes that turn the default look into the target look: (attributes, keys nothing can undo)."""
    base, want = _resolved(vs, default, tone, role), _resolved(vs, target, tone, role)
    house = tiles.data()["kpi" if vs is tiles.kpi()["variants"] else "card"]["house_look"]
    out = {k: v for k, v in want.items() if base.get(k) != v}
    stuck = []
    for k in base:
        if k in want or k in RESET_SKIP:
            continue
        if k in house:   # the house look's value, which the target leaves in place
            out[k] = tiles.role_value(house[k], role)
        elif k in RESET:
            out[k] = RESET[k]
        else:
            stuck.append(k)
    return out, stuck


def attrs(d: dict[str, str]) -> str:
    return "".join(f' {k}="{X(v)}"' for k, v in d.items())


KPI_STYLES = ["filled", "toned", "bar", "dot", "bare", "inverted", "divided"]
CARD_STYLES = ["column", "filled", "outline", "toned", "accent_top"]


def kpi_pair(v: str) -> tuple[str, str, list[str]]:
    """(variant XML, attributes-only XML, what the attributes could not undo)."""
    a = TG.variant_body(v, "label-first")
    vs, c, stuck = tiles.kpi()["variants"], TG.QBR, []
    if v == "divided":   # the group's own box, a hairline before each tile after the first, bare tiles
        dv = vs["divided"]
        g = dict(dv["group_look"], gap=dv["divider"]["space"])
        items = []
        for i, icon in enumerate(TG.ICONS):
            d, s = as_attributes(vs, "plain", "divided", tiles.tone_of(c, i), tiles.tone_role(c, i))
            d["backgroundColor"] = dv["group_look"]["backgroundColor"]   # the strip shows through
            if i:
                d.update({"borderLeft.color": dv["divider"]["color"], "borderLeft.width": dv["divider"]["width"],
                          "padding.left": dv["divider"]["space"]})
            stuck += s
            items.append(f'<Kpi ref="kpis.{i}" icon="{icon}"{attrs({k: str(x) for k, x in d.items()})}/>')
        b = f'<KpiGrid ref="kpis" arrange="label-first" grow="1"{attrs({k: str(x) for k, x in g.items()})}>{"".join(items)}</KpiGrid>'
        return a, b, sorted(set(stuck))
    items = []
    for i, icon in enumerate(TG.ICONS):
        extra = ""
        if v == "inverted":   # the plan's emphasis item only; the others keep the default
            if i == 0:
                d, s = as_attributes(vs, "plain", "inverted", "", tiles.tone_role(c, i))
                # an item's own variant replaces the group's with_tone; as attributes the good tone's number colour
                # is under them and inverted's value.color covers it
                extra = ' size="hero"'
            else:
                d, s = {}, []
        else:
            d, s = as_attributes(vs, "plain", v, tiles.tone_of(c, i), tiles.tone_role(c, i))
        stuck += s
        items.append(f'<Kpi ref="kpis.{i}" icon="{icon}"{extra}{attrs(d)}/>')
    b = f'<KpiGrid ref="kpis" arrange="label-first" grow="1">{"".join(items)}</KpiGrid>'
    return a, b, sorted(set(stuck))


def card_pair(v: str) -> tuple[str, str, list[str]]:
    a = CG.variant_body(v)
    vs, c, stuck, items = cards.card()["variants"], CG.MOMENTS, [], []
    focus = cards.emphasis_index(c)
    for i, icon in enumerate(CG.ICONS):
        d, s = ({}, []) if i == focus else as_attributes(vs, "lifted", v, cards.tone_of(c, i), cards.tone_role(c, i))
        stuck += s
        items.append(f'<Card ref="moments.{i}" icon="{icon}"{attrs(d)}/>')
    return a, f'<CardGrid ref="moments">{"".join(items)}</CardGrid>', sorted(set(stuck))


def pixel_diff(a: Path | None, b: Path | None) -> float | None:
    """Share of pixels that differ visibly (any channel > 24 of 255) at 640 x 360."""
    if not a or not b:
        return None
    import pymupdf
    from PIL import Image, ImageChops

    def img(p: Path) -> Image.Image:
        page = pymupdf.open(p)[0]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(640 / page.rect.width, 360 / page.rect.height))
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    diff = ImageChops.difference(img(a), img(b)).convert("L").point(lambda x: 255 if x > 24 else 0)
    return round(sum(1 for p in diff.getdata() if p) / (diff.width * diff.height), 4)


def q1(theme: str, out: Path, metrics: dict) -> None:
    for block, styles, pair, plan, head in (
            ("kpi", KPI_STYLES, kpi_pair, TG.QBR, "ARR grew to $48.2M while margin softened"),
            ("card", CARD_STYLES, card_pair, CG.MOMENTS, "Teams open the tool at five moments in the working day")):
        shots = []
        for v in styles:
            a, b, stuck = pair(v)
            row = {}
            for side, body in (("variant", a), ("attrs", b)):
                d = out / "q1" / f"{block}-{v}-{side}"
                pdf, issues = CG.compile_one(d, TG.slide(f"{block.upper()} STYLE {v.upper()}", head, body),
                                             {"components": [plan]}, theme)
                row[side] = pdf
                shots.append((f"{v} · {'variant=' if side == 'variant' else 'attributes only'}", pdf))
                print(f"q1 {block} {v} {side}: {'ok' if pdf else 'NO RENDER'} {[i['code'] for i in issues]}")
            metrics.setdefault("q1", {})[f"{block}.{v}"] = {"pixel_diff": pixel_diff(row["variant"], row["attrs"]),
                                                            "not_undoable": stuck, "attrs_xml": b}
            print(f"   diff {metrics['q1'][f'{block}.{v}']['pixel_diff']} stuck {stuck}")
        TG.sheet(shots, out / f"q1-{block}.png", cols=4)


# ── Q2: the 8 compositions ─────────────────────────────────────────────────────

LEVERS = comp("levers", "table", {
    "table_columns": ["Lever", "Problem today", "Action in H2"],
    "table_rows": [["Search", "Organic share fell on every platform", "Scale exact match, the 5.6x winners"],
                   ["Placement", "Home banners cost 2x and return 0.4x", "Cap banners at ₹2 L a month"],
                   ["Pricing", "Regular price sits above two rivals", "Price-pack fit per city"],
                   ["Retention", "Repeat buyers are 41% of revenue", "Retarget new-to-brand buyers weekly"]]},
    columns=3, rows=4)
HEAD_ICONS = ["layers", "alert-triangle", "rocket"]          # no plan field: per column, the LLM's
ROW_ICONS = ["search", "store", "badge-percent", "repeat"]   # no plan field: per row, the LLM's
_STREAMS = [
    {"title": "Search", "icon": "search", "bullets": ["Scale exact match", "Cut broad leakage", "Weekly bid review"]},
    {"title": "Placement", "icon": "store", "bullets": ["Cap home banners", "Test category tiles", "Shift to Hyderabad"]},
    {"title": "Pricing", "icon": "badge-percent", "bullets": ["Price-pack fit", "Bundle the hero SKU", "Match two rivals"]},
    {"title": "Retention", "icon": "repeat", "bullets": ["Retarget new buyers", "Monthly refill offer", "Win back lapsed"]}]
STREAMS = comp("streams", "card_grid", {"card_layout": "grid", "cards": _STREAMS})
STREAMS_F = comp("streams_f", "card_grid", {"card_layout": "grid", "cards": _STREAMS, "focus_card": 0})
INTRO = comp("intro", "narrative", {"text": "Quick commerce carried H1. Four levers decide whether H2 keeps the 4.1x return "
                                            "while the budget grows by a third."})
ACTIONS = comp("actions", "bullet_list", {"bullets": ["Scale exact match: the winners already return 5.6x",
                                                      "Cut phrase and broad leakage: 38% of spend at 0.4x",
                                                      "Shift Bengaluru budget to Hyderabad"]})
TAKEAWAY = LB.TAKEAWAY
SMALL_TABLE = comp("cities", "table", {"table_columns": ["City", "CPC", "ROAS"],
                                       "table_rows": [["Bengaluru", "₹19.3", "2.6x"], ["Hyderabad", "₹12.7", "4.3x"],
                                                      ["Pune", "₹11.9", "4.9x"]]}, columns=3, rows=3)

# two stylings per composition: (fill of the strong part, ink on it, fill of the light part, border)
STYLINGS = {"accent": ("$accent", "$onAccent", "$accentSoft", "$accentSoft"),
            "dark": ("$panelDark", "$onPanelDark", "$surfaceAlt", "$border")}


def t(text: str, px: int = 17, color: str = "$textMain", **kw: str) -> str:
    return f'<Text fontSize="{px}" color="{color}"{attrs(kw)}>{X(text)}</Text>'


def numbered_rows(s: str) -> str:
    strong, ink, light, line = STYLINGS[s]
    cd = LEVERS["content_data"]
    head = (f'<HStack gap="10"><VStack w="64" />'
            + "".join(f'<VStack w="1" grow="{2 if k else 1}" padding.left="16">{t(h, 14, "$textMuted", bold="true", letterSpacing="1")}</VStack>'
                      for k, h in enumerate(c.upper() for c in cd["table_columns"])) + "</HStack>")
    rows = []
    for r, row in enumerate(cd["table_rows"]):
        sq = (f'<VStack w="64" h="64" backgroundColor="{strong}" justifyContent="center" alignItems="center">'
              f'{t(f"{r + 1:02d}", 22, ink, bold="true")}</VStack>')
        title = f'<VStack w="1" grow="1" padding="16" justifyContent="center" border.color="{line}" border.width="1">{t(row[0], 22, bold="true")}</VStack>'
        cells = "".join(f'<VStack w="1" grow="2" padding="16" justifyContent="center" backgroundColor="{light}">{t(x, 20)}</VStack>'
                        for x in row[1:])
        rows.append(f'<HStack gap="10" grow="1" alignItems="stretch">{sq}{title}{cells}</HStack>')
    return f'<VStack gap="10" grow="1" justifyContent="center">{head}{"".join(rows)}</VStack>'


def icon_header(s: str) -> str:
    strong, ink, light, line = STYLINGS[s]
    cd = LEVERS["content_data"]
    head = "".join(f'<VStack w="1" grow="{2 if k else 1}" padding="16" gap="10" backgroundColor="{strong}">'
                   f'<Icon name="{ic}" size="28" color="{ink}" />{t(h, 18, ink, bold="true")}</VStack>'
                   for k, (h, ic) in enumerate(zip(cd["table_columns"], HEAD_ICONS)))
    rows = []
    for r, row in enumerate(cd["table_rows"]):
        fill = light if r % 2 else "$surface"
        rows.append(f'<HStack gap="0" alignItems="stretch" backgroundColor="{fill}">'
                    + "".join(f'<VStack w="1" grow="{2 if k else 1}" padding="14" justifyContent="center">'
                              f'{t(x, 17, bold="true" if k == 0 else "false")}</VStack>' for k, x in enumerate(row))
                    + "</HStack>")
    return (f'<VStack gap="0" grow="1" border.color="{line}" border.width="1"><HStack gap="0" alignItems="stretch">{head}</HStack>'
            f'{"".join(rows)}</VStack>')


def chevron_rows(s: str) -> str:
    strong, ink, light, _ = STYLINGS[s]
    cd = LEVERS["content_data"]
    head = ('<HStack gap="8"><VStack w="250" />' + "".join(
        f'<VStack w="1" grow="1" padding.left="34">{t(h.upper(), 14, "$textMuted", bold="true", letterSpacing="1")}</VStack>'
        for h in cd["table_columns"][1:]) + "</HStack>")
    rows = []
    for row, ic in zip(cd["table_rows"], ROW_ICONS):
        label = (f'<HStack w="250" h="96" gap="0" alignItems="center">'
                 f'<VStack w="64" h="96" backgroundColor="{strong}" justifyContent="center" alignItems="center">'
                 f'<Icon name="{ic}" size="26" color="{ink}" /></VStack>'
                 f'<Shape shapeType="homePlate" w="186" h="96" fill.color="{strong}" text="{X(row[0])}" fontSize="20" bold="true" color="{ink}" /></HStack>')
        cells = "".join(f'<Shape shapeType="chevron" w="1" grow="1" h="96" fill.color="{light}" text="{X(x)}" fontSize="18" '
                        f'color="$textMain" />' for x in row[1:])
        rows.append(f'<HStack gap="8" alignItems="center">{label}{cells}</HStack>')
    return f'<VStack gap="12" grow="1" justifyContent="center">{head}{"".join(rows)}</VStack>'


def titled(s: str) -> str:
    strong, ink, light, _ = STYLINGS[s]
    banner = (f'<HStack padding="16" padding.left="24" gap="12" alignItems="center" backgroundColor="{strong}">'
              f'<Icon name="layers" size="24" color="{ink}" />{t("Four levers for H2", 22, ink, bold="true")}</HStack>')
    tbl = LB.table("zebra" if s == "accent" else "plain", LEVERS).replace('fontSize="18"', 'fontSize="17"')
    if s == "accent":
        tbl = tbl.replace('backgroundColor="$surfaceAlt"', f'backgroundColor="{light}"')
    return f'<VStack gap="0" grow="1">{banner}{tbl}</VStack>'


def columns(s: str) -> str:
    strong, ink, light, line = STYLINGS[s]
    cols = []
    for c in _STREAMS:
        pill = (f'<HStack padding="14" gap="10" alignItems="center" justifyContent="center" backgroundColor="{strong}" borderRadius="24">'
                f'<Icon name="{c["icon"]}" size="22" color="{ink}" />{t(c["title"], 20, ink, bold="true")}</HStack>')
        boxes = "".join(f'<VStack grow="1" padding="16" justifyContent="center" backgroundColor="{light}" border.color="{line}" '
                        f'border.width="1" borderRadius="8">{t(b, 18)}</VStack>' for b in c["bullets"])
        cols.append(f'<VStack w="1" grow="1" gap="12" alignItems="stretch">{pill}{boxes}</VStack>')
    return f'<HStack gap="18" grow="1" alignItems="stretch">{"".join(cols)}</HStack>'


def title_bar(s: str) -> str:
    strong, ink, light, line = STYLINGS[s]
    blocks = []
    for c in _STREAMS:
        bar = (f'<HStack padding="14" gap="10" alignItems="center" backgroundColor="{strong}">'
               f'<Icon name="{c["icon"]}" size="22" color="{ink}" />{t(c["title"], 22, ink, bold="true")}</HStack>')
        body = (f'<VStack grow="1" padding="18" backgroundColor="{light if s == "dark" else "$surface"}">'
                f'<Ul fontSize="22" lineHeight="1.5" color="$textMain">{"".join(f"<Li>{X(b)}</Li>" for b in c["bullets"])}</Ul></VStack>')
        blocks.append(f'<VStack w="1" grow="1" gap="0" border.color="{line}" border.width="1">{bar}{body}</VStack>')
    return ('<VStack gap="18" grow="1">' + "".join(f'<HStack gap="18" grow="1" alignItems="stretch">{"".join(blocks[k:k + 2])}</HStack>'
                                                   for k in (0, 2)) + "</VStack>")


def bento(s: str) -> str:
    """Through the real card code: the focus card placed apart (code draws it dark) beside the group of the rest."""
    v = "filled" if s == "accent" else "outline"
    return (f'<HStack gap="20" grow="1" alignItems="stretch"><Card ref="streams_f.0" w="40%" />'
            f'<CardGrid ref="streams_f" variant="{v}" cols="{3 if s == "accent" else 2}" /></HStack>')


def slide_mix(s: str) -> str:
    """bullets `boxed` + callout `icon_panel`: a text column with boxed points, a table with an icon callout beside it."""
    strong, ink, light, line = STYLINGS[s]
    pts = "".join(f'<HStack padding="14" gap="12" alignItems="center" backgroundColor="{light}" border.color="{line}" border.width="1">'
                  f'<VStack w="10" h="10" backgroundColor="{strong}" />{t(b, 18)}</HStack>' for b in ACTIONS["content_data"]["bullets"])
    left = (f'<VStack w="46%" gap="14">{t(INTRO["content_data"]["text"], 20, lineHeight="1.4")}{pts}</VStack>')
    call = (f'<HStack padding="20" gap="16" alignItems="center" backgroundColor="{strong}">'
            f'<Icon name="lightbulb" size="32" color="{ink}" variant="circle-filled" bgColor="{light}" />'
            f'{t(TAKEAWAY["content_data"]["text"], 18, ink)}</HStack>')
    right = f'<VStack grow="1" gap="16">{LB.table("dark_header" if s == "dark" else "zebra", SMALL_TABLE)}{call}</VStack>'
    return f'<HStack gap="32" grow="1" alignItems="start">{left}{right}</HStack>'


def q2_rows() -> dict[str, list[tuple[str, list[tuple[str, list[dict], str]]]]]:
    """block -> rows of (row label, [(shot label, components, body)])."""
    two = lambda name, fn, cs: (name, [(f"{name} · {s}", cs, fn(s)) for s in STYLINGS])   # noqa: E731
    return {
        "table": [("today's style variants", [(f"table {v} (style)", [LB.TABLE], LB.table(v))
                                              for v in ("plain", "zebra", "dark_header")]),
                  two("numbered_rows", numbered_rows, [LEVERS]), two("icon_header", icon_header, [LEVERS]),
                  two("chevron_rows", chevron_rows, [LEVERS]), two("titled", titled, [LEVERS])],
        "cards": [("today's style variants", [("cards lifted (style)", [STREAMS], '<CardGrid ref="streams" />'),
                                              ("cards filled (style)", [STREAMS], '<CardGrid ref="streams" variant="filled" />'),
                                              ("cards inverted (style, focus card)", [STREAMS_F], '<CardGrid ref="streams_f" />')]),
                  two("columns", columns, [STREAMS]), two("title_bar", title_bar, [STREAMS]),
                  two("bento", bento, [STREAMS_F])],
        "slide": [("today's style variants", [("bullet_list plain (style)", [LB.BULLETS], LB.bullets("plain")),
                                              ("callout tinted (style)", [TAKEAWAY], LB.beside_chart(LB.callout("tinted"))),
                                              ("callout dark (style)", [TAKEAWAY], LB.beside_chart(LB.callout("dark")))]),
                  two("boxed + icon_panel", slide_mix, [INTRO, ACTIONS, TAKEAWAY, SMALL_TABLE])],
    }


def sheet_rows(rows: list[tuple[str, list[tuple[str, Path | None]]]], path: Path, cols: int = 3) -> None:
    """One sheet, one row per group (its label on the left of the row's first shot)."""
    import pymupdf
    from PIL import Image, ImageDraw
    w, h, gap, lab = 560, 315, 14, 24
    img = Image.new("RGB", (cols * (w + gap) + gap, len(rows) * (h + lab + gap) + gap), "white")
    draw = ImageDraw.Draw(img)
    for r, (_, shots) in enumerate(rows):
        for k, (name, pdf) in enumerate(shots):
            x, y = gap + k * (w + gap), gap + r * (h + lab + gap)
            draw.text((x, y + 6), name, fill="black")
            if pdf:
                page = pymupdf.open(pdf)[0]
                pix = page.get_pixmap(matrix=pymupdf.Matrix(w / page.rect.width, h / page.rect.height))
                img.paste(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), (x, y + lab))
            draw.rectangle([x - 1, y + lab - 1, x + w, y + lab + h], outline="#999999")
    img.save(path)


def q2(theme: str, out: Path, metrics: dict, only: list[str]) -> None:
    for block, rows in q2_rows().items():
        if only and block not in only:
            continue
        drawn = []
        for row_label, shots in rows:
            got = []
            for label, comps, body in shots:
                d = out / "q2" / f"{block}-{label.split(' (')[0].replace(' · ', '-').replace(' + ', '-').replace(' ', '_')}"
                pdf, issues = CG.compile_one(d, TG.slide("COMPOSITION TEST", label, body), {"components": comps}, theme)
                got.append((label, pdf))
                print(f"q2 {block} {label}: {'ok' if pdf else 'NO RENDER'} {[i['code'] for i in issues if i['severity'] == 'error']}")
            drawn.append((row_label, got))
        sheet_rows(drawn, out / f"q2-{block}.png")
        # the difference a styling makes (inside a row) against the difference a composition makes (across rows)
        style_rows = [g for lab, g in drawn if lab == "today's style variants"]
        comp_rows = [g for lab, g in drawn if lab != "today's style variants"]
        within = [pixel_diff(g[0][1], g[k][1]) for g in style_rows for k in range(1, len(g))]
        restyle = [pixel_diff(g[0][1], g[1][1]) for g in comp_rows if len(g) > 1]
        across = [pixel_diff(style_rows[0][0][1], g[0][1]) for g in comp_rows] if style_rows else []
        metrics.setdefault("q2", {})[block] = {"today_style_vs_style": within, "composition_restyled": restyle,
                                               "today_plain_vs_composition": across}
        print(block, metrics["q2"][block])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("part", choices=["q1", "q2"])
    ap.add_argument("--palette", default="corporate-slate")
    ap.add_argument("--only", nargs="*", default=[], help="q2 blocks: table cards slide")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    theme = resolve_theme(a.palette)["element"]
    a.out.mkdir(parents=True, exist_ok=True)
    mpath = a.out / "metrics.json"
    metrics = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    if a.part == "q1":
        shutil.rmtree(a.out / "q1", ignore_errors=True)
        q1(theme, a.out, metrics)
    else:
        q2(theme, a.out, metrics, a.only)
    mpath.write_text(json.dumps(metrics, indent=1, ensure_ascii=False), encoding="utf-8")
    print(mpath)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
