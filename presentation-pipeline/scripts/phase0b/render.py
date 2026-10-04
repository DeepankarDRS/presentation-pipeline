"""Phase 0b: draw saved slide plans with code only (docs/derived-nodes-design.md §10b).

Experiment, not pipeline code. A style pack + a frame + a few blocks turn each
SlidePlan into POM XML; a small composer stands in for the generator's layout
choices. Every visible string comes from the plan (or is a frame label).

    python -m scripts.phase0b.render scripts/phase0b/plans/cheffin.json --out output/phase0b/cheffin
    python -m scripts.render_check --in output/phase0b/cheffin --out output/render_check/phase0b-cheffin
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import yaml

HERE = Path(__file__).resolve().parent
W, H = 1280, 720
PAD_X = 56
INNER = W - 2 * PAD_X  # 1168


def x(text: Any) -> str:
    return escape(str(text))


# ── style pack ───────────────────────────────────────────────────────────────

class Pack:
    def __init__(self, name: str, entities: dict[str, str] | None = None) -> None:
        spec = yaml.safe_load((HERE / "style_packs.yaml").read_text(encoding="utf-8"))[name]
        self.c = spec["colors"]
        self.sans, self.mono = spec["fonts"]["sans"], spec["fonts"]["mono"]
        self.t = spec["type"]
        self.badge = spec["badge"]
        self.rule = spec["rule_under_headline"]
        self.top_bar = spec["top_bar"]
        self.entities = {k.upper(): v for k, v in (entities or {}).items()}

    def theme(self) -> str:
        tokens = dict(self.c)
        for i, (_, col) in enumerate(self.entities.items()):
            tokens[f"e{i}"] = col
            tokens[f"e{i}t"] = tint(col)
            tokens[f"e{i}d"] = shade(col)
        return "<Theme " + " ".join(f'{k}="{v}"' for k, v in tokens.items()) + " />"

    def entity(self, text: str) -> tuple[str, str, str] | None:
        """($colour, $tint, $dark text colour) of the first entity named in text."""
        up = text.upper()
        for i, name in enumerate(self.entities):
            if re.search(rf"\b{re.escape(name)}\b", up):
                return f"$e{i}", f"$e{i}t", f"$e{i}d"
        return None

    def label(self, text: str, color: str = "$muted", size: int | None = None, extra: str = "") -> str:
        return (f'<Text fontSize="{size or self.t["label"]}" fontFamily="{self.mono}" color="{color}" '
                f'letterSpacing="1.6"{extra}>{x(text.upper())}</Text>')


def shade(hex_color: str, amount: float = 0.25) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{round(c * (1 - amount)):02X}" for c in (r, g, b))


def tint(hex_color: str, amount: float = 0.9) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{round(c + (255 - c) * amount):02X}" for c in (r, g, b))


# ── measuring (structural, no layout engine) ─────────────────────────────────

def text_px(text: str, fs: float, bold: bool = False) -> float:
    return len(text) * fs * (0.6 if bold else 0.54)


def per_row(n: int, most: int) -> int:
    rows = math.ceil(n / most)
    return math.ceil(n / rows)


def fit_columns(titles: list[str], width: float, fs: float, most: int, pad: int = 36, gap: int = 12) -> int:
    """Most cards per row whose longest word fits and whose titles wrap to <= 3 lines."""
    words = [w for t in titles for w in t.split()] or [""]
    longest = max(text_px(w, fs, True) for w in words)
    for n in range(min(most, len(titles)), 0, -1):
        inner = (width - gap * (n - 1)) / n - pad
        if longest <= inner and all(text_px(t, fs, True) / inner <= 3 for t in titles):
            return per_row(len(titles), n)
    return 1


# ── blocks ───────────────────────────────────────────────────────────────────

_NUM = re.compile(r"^(?P<pre>[₹$€£]?)(?P<num>[\d.,]+)(?P<unit>[A-Za-z%]*)$")


def big_number(value: str, fs: int, color: str, p: Pack) -> str:
    m = _NUM.match(value.strip())
    if not m or not m["unit"]:
        return f'<Text fontSize="{fs}" fontFamily="{p.sans}" bold="true" color="{color}" lineHeight="1">{x(value)}</Text>'
    return (f'<Text fontSize="{fs}" fontFamily="{p.sans}" bold="true" color="{color}" lineHeight="1">'
            f'{x(m["pre"] + m["num"])}<Span fontSize="{round(fs * 0.45)}">{x(m["unit"])}</Span></Text>')


def kpi_row(comp: dict, p: Pack, hero: bool) -> str:
    cd = comp["content_data"]
    labels, values = cd.get("kpi_labels", []), cd.get("kpi_values", [])
    notes = cd.get("kpi_deltas") or [""] * len(values)
    dark = _named_in_hint(comp, labels, "inverted")
    tile_w = (INNER - 12 * (len(values) - 1)) / max(1, len(values)) - 40
    chars = max((len(v) for v in values), default=1)
    fs = min(p.t["big"] if hero else p.t["mid"], int(tile_w / (chars * 0.62)))
    tiles = []
    for label, value, note in zip(labels, values, notes):
        ent = p.entity(label)
        bg, lab_c, num_c, border = "$panel", "$muted", "$ink", ""
        if label == dark:
            bg, lab_c, num_c = "$dark", "$accent2", "$white"
        elif ent:
            bg, lab_c = ent[1], ent[2]
            border = f' borderLeft.color="{ent[0]}" borderLeft.width="3"'
        note_xml = (f'<Text fontSize="11" fontFamily="{p.sans}" color="{"$white" if label == dark else "$muted"}">'
                    f'{x(note)}</Text>' if note else "")
        tiles.append(f'<VStack w="1" grow="1" h="{130 if hero else 100}" padding="20" gap="8" backgroundColor="{bg}"{border} '
                     f'justifyContent="spaceBetween">{p.label(label, lab_c)}'
                     f'<VStack gap="6">{big_number(value, fs, num_c, p)}{note_xml}</VStack></VStack>')
    return f'<HStack gap="12" alignItems="stretch">{"".join(tiles)}</HStack>'


_PHASE = re.compile(r"^((?:Phase|Month|Step|Stage)\s*\d+)\s*[:\-–]\s*(.+)$", re.I)


def _split_list(body: str) -> list[str] | None:
    parts = [s.strip().rstrip(".") for s in body.split(",")]
    return parts if len(parts) >= 3 and all(0 < len(s.split()) <= 5 for s in parts) else None


def _named_in_hint(comp: dict, names: list[str], word: str) -> str | None:
    hint = comp.get("design_hint") or ""
    if word not in hint:
        return None
    after = hint.split(word, 1)[1]
    hits = [n for n in names if n and n in after]
    return max(hits, key=len) if hits else None


def card_grid(comp: dict, p: Pack, width: float, grows: bool) -> str:
    cd = comp["content_data"]
    cards = [c if isinstance(c, dict) else {"title": str(c)} for c in cd.get("cards", [])]
    steps = cd.get("card_layout") == "steps"
    titles = [c.get("title", "") for c in cards]
    hi = _named_in_hint(comp, titles, "inverted") or (titles[-1] if steps and len(titles) > 1 else None)
    rich = any(c.get("body") or c.get("bullets") for c in cards)
    tfs = p.t["title"] + (2 if rich else 0)
    n = len(cards) if steps and len(cards) <= 5 else fit_columns(
        [_PHASE.sub(r"\2", t) for t in titles], width, tfs, 5 if len(cards) == 5 else 4)

    n_rows = 1 if steps and len(cards) <= 5 else math.ceil(len(cards) / n)
    tile_h = {1: 150, 2: 120}.get(n_rows, 96)
    grows = grows and rich

    def one(i: int, c: dict) -> str:
        title = c.get("title", "")
        m = _PHASE.match(title)
        tag = m.group(1) if m else (c.get("tag") or f"{i + 1:02d}")
        if m and c.get("tag"):
            tag = f"{tag} · {c['tag']}"
        title = m.group(2) if m else title
        inv = c.get("title") == hi
        bg, ink, lab = ("$dark", "$white", "$accent2") if inv else ("$panel", "$ink", "$accent")
        top = f' borderTop.color="{lab if inv else "$accent"}" borderTop.width="3"' if steps else ""
        parts = [p.label(tag, lab),
                 f'<Text fontSize="{tfs}" fontFamily="{p.sans}" bold="true" color="{ink}" lineHeight="1.2">{x(title)}</Text>']
        bullets = c.get("bullets") or (_split_list(c["body"]) if c.get("body") else None)
        if c.get("body") and not bullets:
            parts.append(f'<Text fontSize="12" fontFamily="{p.sans}" color="{"$white" if inv else "$muted"}" '
                         f'lineHeight="1.4">{x(c["body"])}</Text>')
        if cd.get("columns"):
            parts.append(f'<Text fontSize="12" fontFamily="{p.sans}" color="$muted" lineHeight="1.4">'
                         f'{x(" · ".join(cd["columns"]))}</Text>')
        if bullets:
            dot = "$accent2" if inv else "$accent"
            parts.append('<VStack margin.top="4" gap="8">' + "".join(
                f'<HStack gap="10" alignItems="center"><Shape shapeType="rect" w="5" h="5" fill.color="{dot}" />'
                f'<Text fontSize="{p.t["body"]}" fontFamily="{p.sans}" color="{ink}">{x(b)}</Text></HStack>'
                for b in bullets) + "</VStack>")
        lone = len(parts) == 2  # label + title only: fixed tile, label top, title bottom
        just = f' h="{tile_h}" justifyContent="spaceBetween"' if lone else ""
        return (f'<VStack w="1" grow="1" padding="18" gap="8" backgroundColor="{bg}"{top}{just}>'
                + "".join(parts) + "</VStack>")

    if steps and len(cards) <= 5:
        arrow = f'<Icon name="arrow-right" size="18" color="$muted" alignSelf="center" />'
        row = arrow.join(one(i, c) for i, c in enumerate(cards))
        return f'<HStack gap="10" alignItems="stretch"{" grow=\"1\"" if grows else ""}>{row}</HStack>'
    rows = []
    for r in range(0, len(cards), n):
        chunk = [one(i, c) for i, c in enumerate(cards[r:r + n], start=r)]
        chunk += ['<VStack w="1" grow="1" />'] * (n - len(chunk))  # keep columns aligned
        g = ' grow="1"' if grows else ""
        rows.append(f'<HStack gap="12" alignItems="stretch"{g}>{"".join(chunk)}</HStack>')
    g = ' grow="1"' if grows else ""
    return f'<VStack gap="12" alignItems="stretch"{g}>{"".join(rows)}</VStack>'


def tile_row(items: list[str], p: Pack) -> str:
    """Short parallel items in ONE compact row (Genspark XTSY slide 6 benefits)."""
    tiles = "".join(
        f'<VStack w="1" grow="1" padding="14" backgroundColor="$panel" borderTop.color="$accent" borderTop.width="2">'
        f'<Text fontSize="13" fontFamily="{p.sans}" bold="true" color="$ink" lineHeight="1.25">{x(i)}</Text></VStack>'
        for i in items)
    return f'<HStack gap="10" alignItems="stretch">{tiles}</HStack>'


def note_columns(items: list[str], p: Pack) -> str:
    """Two or three sentence-length notes as columns in one dark panel."""
    cols = "".join(f'<VStack w="1" grow="1" gap="6"><Text fontSize="13" fontFamily="{p.sans}" color="$white" '
                   f'lineHeight="1.45">{x(i)}</Text></VStack>' for i in items)
    return f'<HStack padding="20" gap="28" backgroundColor="$dark" alignItems="start">{cols}</HStack>'


def bullet_panel(items: list[str], p: Pack) -> str:
    rows = "".join(f'<HStack gap="10" alignItems="center"><Shape shapeType="rect" w="5" h="5" fill.color="$accent" />'
                   f'<Text fontSize="{p.t["body"] + 1}" fontFamily="{p.sans}" color="$ink">{x(i)}</Text></HStack>'
                   for i in items)
    return f'<VStack padding="18" gap="10" backgroundColor="$panel">{rows}</VStack>'


def bullets_block(comp: dict, p: Pack) -> str:
    items = [str(b) for b in comp["content_data"].get("bullets", [])]
    if 2 <= len(items) <= 6 and all(len(i.split()) <= 5 for i in items):
        return tile_row(items, p)
    if 2 <= len(items) <= 3 and all(len(i.split()) >= 8 for i in items):
        return note_columns(items, p)
    return bullet_panel(items, p)


def process_steps(comp: dict, p: Pack) -> str:
    steps = [str(s) for s in comp["content_data"].get("process_steps", [])]
    out = []
    for i, s in enumerate(steps):
        last = i == len(steps) - 1
        bg, ink = ("$accent2", "$ink") if last else ("$panel", "$ink")
        out.append(f'<VStack w="1" grow="1" padding="12" backgroundColor="{bg}" alignItems="center">'
                   f'<Text fontSize="14" fontFamily="{p.sans}" bold="true" color="{ink}" textAlign="center">{x(s)}</Text></VStack>')
    arrow = '<Icon name="arrow-right" size="18" color="$accent" alignSelf="center" />'
    return f'<HStack gap="8" alignItems="stretch">{arrow.join(out)}</HStack>'


def data_table(comp: dict, p: Pack, width: float) -> str:
    cd = comp["content_data"]
    cols, rows = cd.get("table_columns", []), cd.get("table_rows", [])
    hi = _named_in_hint(comp, [str(r[0]) for r in rows], "row") if rows else None
    lens = [max(len(str(c)), *(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
    total = sum(min(l, 40) + 6 for l in lens)
    widths = [round(width * (min(l, 40) + 6) / total) for l in lens]
    fs, rh = (15, 50) if len(rows) <= 4 else (13, 38)
    out = [f'<Table defaultRowHeight="{rh}" cellBorder.color="$line" cellBorder.width="1">']
    out += [f'<Col width="{w}" />' for w in widths]
    out.append("<Tr>" + "".join(f'<Td fontSize="10" fontFamily="{p.mono}" color="$muted" bold="true">{x(str(c).upper())}</Td>'
                                for c in cols) + "</Tr>")
    for r in rows:
        bg = ' backgroundColor="$panel"' if str(r[0]) == hi else ""
        ent = p.entity(str(r[0]))
        cells = []
        for i, v in enumerate(r):
            color = ent[2] if (i == 0 and ent) else ("$accent" if str(r[0]) == hi and i else "$ink")
            bold = ' bold="true"' if i == 0 or str(r[0]) == hi else ""
            cells.append(f'<Td fontSize="{fs}" fontFamily="{p.sans}" color="{color}"{bold}{bg}>{x(v)}</Td>')
        out.append("<Tr>" + "".join(cells) + "</Tr>")
    out.append("</Table>")
    return "".join(out)


def _num(v: Any) -> float | None:
    m = re.search(r"[\d.]+", str(v).replace(",", ""))
    return float(m.group()) if m else None


def bar_list(labels: list[str], series: list[tuple[str, list[str]]], p: Pack, width: float) -> str:
    """Horizontal bars. One series: best = accent, worst = negative. Two: entity colour + grey."""
    track = width - 130 - 100
    vals = [_num(v) or 0 for _, vs in series for v in vs]
    top = max(vals) or 1
    rows = []
    for li, label in enumerate(labels):
        ent = p.entity(label)
        bars = []
        for si, (name, vs) in enumerate(series):
            v = _num(vs[li]) or 0
            if len(series) == 1:
                col = "$accent" if v == max(vals) else ("$negative" if v == min(vals) else "$ink")
            else:
                col = (ent[0] if ent else "$ink") if si == 0 else "$line"
            bars.append(f'<HStack gap="8" alignItems="center"><Shape shapeType="rect" w="{max(4, round(track * v / top))}" '
                        f'h="{(22 if len(labels) <= 3 else 16) if len(series) == 1 else (18 if len(labels) <= 3 else 12)}" fill.color="{col}" />'
                        f'<Text fontSize="12" fontFamily="{p.sans}" bold="true" color="$ink">{x(vs[li])}</Text></HStack>')
        lab_c = ent[2] if ent else "$ink"
        rows.append(f'<HStack gap="10" alignItems="center"><Text w="120" fontSize="14" fontFamily="{p.sans}" bold="true" '
                    f'color="{lab_c}">{x(label)}</Text><VStack gap="4">{"".join(bars)}</VStack></HStack>')
    legend = ""
    if len(series) > 1:
        legend = '<HStack gap="16" margin.top="4">' + "".join(
            f'<HStack gap="6" alignItems="center"><Shape shapeType="rect" w="10" h="10" fill.color="{"$ink" if i == 0 else "$line"}" />'
            f'{p.label(name)}</HStack>' for i, (name, _) in enumerate(series)) + "</HStack>"
    return f'<VStack gap="{24 if len(labels) <= 3 else 14}">{"".join(rows)}{legend}</VStack>'


def chart_block(comp: dict, p: Pack, width: float) -> str:
    cd = comp["content_data"]
    labels = cd.get("chart_labels", [])
    series = [(s["name"], s["values"]) for s in cd.get("chart_series", [])] or [(cd.get("chart_title", ""), cd.get("chart_values", []))]
    return bar_list(labels, series, p, width)


def panel(title: str | None, body: str, p: Pack, grows: bool = False) -> str:
    head = p.label(title) if title else ""
    g = ' grow="1"' if grows else ""
    return f'<VStack gap="12"{g}>{head}{body}</VStack>'


def insight(text: str, p: Pack) -> str:
    return (f'<VStack padding.left="14" borderLeft.color="$ink" borderLeft.width="3">'
            f'<Text fontSize="16" fontFamily="{p.sans}" color="$ink" lineHeight="1.4">{x(text)}</Text></VStack>')


def strip(text: str, label: str, p: Pack) -> str:
    return (f'<HStack padding="18" gap="16" backgroundColor="$dark" alignItems="center" '
            f'borderLeft.color="$accent2" borderLeft.width="4">'
            f'{p.label(label, "$accent2", extra=" w=\"120\"")}'
            f'<Text grow="1" fontSize="15" fontFamily="{p.sans}" color="$white" lineHeight="1.4">{x(text)}</Text></HStack>')


# ── composer (stands in for the generator's layout choices) ──────────────────

def compose_body(plan: dict, p: Pack) -> str:
    comps = [c for c in plan["components"] if c["kind"] not in ("title", "caption")]
    narr = [c for c in comps if c["kind"] == "narrative"]
    main = [c for c in comps if c["kind"] != "narrative"]
    out: list[str] = []
    grew = False

    def draw(c: dict, width: float, grows: bool) -> str:
        k = c["kind"]
        if k == "kpi_row":
            return kpi_row(c, p, hero=c.get("weight") != "supporting")
        if k == "card_grid":
            return card_grid(c, p, width, grows)
        if k == "table":
            rows = c["content_data"].get("table_rows", [])
            if len(c["content_data"].get("table_columns", [])) == 2 and all(_num(r[1]) is not None for r in rows):
                cols = c["content_data"]["table_columns"]
                return (f'<VStack gap="12">{p.label(" · ".join(map(str, cols)))}'
                        + bar_list([str(r[0]) for r in rows], [(cols[1], [r[1] for r in rows])], p, width) + "</VStack>")
            return data_table(c, p, width)
        if k == "chart":
            return chart_block(c, p, width)
        if k == "bullet_list":
            return bullets_block(c, p)
        if k == "process_arrow":
            return process_steps(c, p)
        return ""

    i = 0
    while i < len(main):
        c = main[i]
        nxt = main[i + 1] if i + 1 < len(main) else None
        pair = nxt and {c["kind"], nxt["kind"]} <= {"table", "chart"} or (
            nxt and c.get("weight") == nxt.get("weight") == "peer" and c["kind"] == nxt["kind"] == "card_grid")
        if pair:
            wl = INNER * (0.56 if c["kind"] == "table" else 0.5) - 12
            wr = INNER - wl - 24
            left = panel(c["content_data"].get("chart_title") or None, draw(c, wl, False), p)
            right = panel(nxt["content_data"].get("chart_title") or None, draw(nxt, wr, False), p)
            out.append(f'<HStack gap="24" alignItems="start"><VStack w="{round(wl)}">{left}</VStack>'
                       f'<VStack grow="1">{right}</VStack></HStack>')
            i += 2
            continue
        rich = c["kind"] == "card_grid" and any(
            isinstance(k, dict) and (k.get("body") or k.get("bullets")) for k in c["content_data"].get("cards", []))
        grows = not grew and rich and c.get("weight") in ("hero", "peer", None)
        grew = grew or grows
        out.append(draw(c, INNER, grows))
        i += 1
    if not grew:
        out.append('<VStack grow="1" />')
    for j, n in enumerate(narr):
        last = j == len(narr) - 1
        out.append(strip(n["content_data"]["text"], "Key message", p) if last else insight(n["content_data"]["text"], p))
    return "".join(out)


def frame(plan: dict, deck: dict, p: Pack, n: int, total: int) -> str:
    bar = ('<HStack h="6"><Shape shapeType="rect" w="1" grow="1" h="6" fill.color="$dark" />'
           '<Shape shapeType="rect" w="180" h="6" fill.color="$accent2" /></HStack>') if p.top_bar else ""
    if p.badge == "number":
        badge = (f'<VStack w="26" h="26" backgroundColor="$accent2" justifyContent="center" alignItems="center">'
                 f'<Text fontSize="12" fontFamily="{p.mono}" bold="true" color="$ink">{n}</Text></VStack>')
    else:
        badge = '<Shape shapeType="rect" w="7" h="7" fill.color="$accent" />'
    label = p.label(plan.get("label") or "", "$accent") if plan.get("label") else ""
    sub = (f'<Text margin.top="8" fontSize="14" fontFamily="{p.sans}" color="$muted" lineHeight="1.35">'
           f'{x(plan["subtitle"])}</Text>') if plan.get("subtitle") else ""
    rule = '<Shape margin.top="14" shapeType="rect" w="36" h="2" fill.color="$ink" />' if p.rule else ""
    lines = math.ceil(len(plan["slide_title"]) * p.t["headline"] * 0.56 / INNER)
    head_h = round(lines * p.t["headline"] * 1.15 + 6)
    return f'''<Slide>
  <VStack w="{W}" h="{H}" backgroundColor="$bg" alignItems="stretch">
    {bar}
    <VStack grow="1" padding.top="26" padding.bottom="20" padding.left="{PAD_X}" padding.right="{PAD_X}" alignItems="stretch">
      <HStack alignItems="center" justifyContent="spaceBetween">
        <HStack gap="10" alignItems="center">{badge}{label}</HStack>
        {p.label(deck["running"], "$muted", 9, ' textAlign="right"')}
      </HStack>
      <VStack margin.top="14" h="{head_h}"><Text fontSize="{p.t["headline"]}" fontFamily="{p.sans}" bold="true" color="$ink" lineHeight="1.15">{x(plan["slide_title"])}</Text></VStack>
      {sub}{rule}
      <VStack margin.top="20" grow="1" gap="16" alignItems="stretch">{compose_body(plan, p)}</VStack>
      <HStack margin.top="14" alignItems="center" justifyContent="spaceBetween">
        {p.label(deck["brand"], "$muted", 9)}
        {p.label(f"{n:02d} / {total:02d}", "$muted", 9, ' textAlign="right"')}
      </HStack>
    </VStack>
  </VStack>
</Slide>'''


def cover(plan: dict, deck: dict, p: Pack, total: int) -> str:
    comps = {c["kind"]: c for c in plan["components"]}
    caption = comps.get("caption", {}).get("content_data", {}).get("text", "")
    narr = comps.get("narrative", {}).get("content_data", {}).get("text", "")
    title, brand = plan["slide_title"], deck["brand"]
    sub = plan.get("subtitle") or ""
    if p.badge == "number":  # tech: dark hero
        msg = (f'<VStack padding="18" borderLeft.color="$accent2" borderLeft.width="3" backgroundColor="$dark">'
               f'{p.label("Key message", "$accent2")}<Text margin.top="8" fontSize="15" fontFamily="{p.sans}" color="$white" '
               f'lineHeight="1.45">{x(narr)}</Text></VStack>') if narr else ""
        return f'''<Slide>
  <VStack w="{W}" h="{H}" padding="56" alignItems="stretch" backgroundGradient="radial-gradient(circle at 85% 40%, #16324F 0%, #0B1F33 55%)">
    <HStack gap="10" alignItems="center"><Shape shapeType="rect" w="8" h="8" fill.color="$accent2" />{p.label(brand, "$white", 11)}</HStack>
    <VStack grow="1" />
    <HStack gap="40" alignItems="center">
      <VStack w="64%" gap="18">
        <Text fontSize="{p.t["cover"]}" fontFamily="{p.sans}" bold="true" color="$white" lineHeight="1.1">{x(title)}</Text>
        <Shape shapeType="rect" w="72" h="3" fill.color="$accent2" />
        <Text fontSize="16" fontFamily="{p.sans}" color="$line" lineHeight="1.4">{x(sub)}</Text>
        {msg}
      </VStack>
      <VStack grow="1" alignItems="center">
        <Shape shapeType="ellipse" w="300" h="300" fill.color="$accent" text="{x(brand)}" fontSize="44" fontFamily="{p.sans}" bold="true" color="$white" />
      </VStack>
    </HStack>
    <VStack grow="1" />
    <HStack justifyContent="spaceBetween">{p.label(caption or brand, "$line", 9)}{p.label(f"01 / {total:02d}", "$line", 9, ' textAlign="right"')}</HStack>
  </VStack>
</Slide>'''
    # editorial: brand word huge, rest of the title in accent, entity colour cues
    rest = title[len(brand):].strip() if title.upper().startswith(brand.upper()) else title
    head = brand if rest != title else ""
    cues = "".join(f'<VStack w="200" padding="16" gap="10" backgroundColor="$e{i}t" borderLeft.color="$e{i}" borderLeft.width="3">'
                   f'{p.label(name, f"$e{i}d")}<Shape shapeType="rect" w="120" h="6" fill.color="$e{i}" /></VStack>'
                   for i, name in enumerate(p.entities))
    big = (f'<Text fontSize="{p.t["cover"]}" fontFamily="{p.sans}" bold="true" color="$ink" lineHeight="1">{x(head)}</Text>' if head else "")
    return f'''<Slide>
  <VStack w="{W}" h="{H}" padding="64" alignItems="stretch" backgroundColor="$bg">
    <HStack justifyContent="spaceBetween" alignItems="center">
      <HStack gap="10" alignItems="center"><Shape shapeType="rect" w="7" h="7" fill.color="$accent" />{p.label(plan.get("label") or brand, "$accent")}</HStack>
      {p.label(f"01 / {total:02d}", "$muted", 9, ' textAlign="right"')}
    </HStack>
    <VStack grow="1" />
    <HStack gap="40" alignItems="end">
      <VStack grow="1" gap="14">
        {big}
        <Shape shapeType="rect" w="56" h="3" fill.color="$accent" />
        <Text fontSize="30" fontFamily="{p.sans}" bold="true" color="$accent" lineHeight="1.15">{x(rest)}</Text>
        <Text fontSize="15" fontFamily="{p.sans}" color="$muted" lineHeight="1.4">{x(sub)}</Text>
      </VStack>
      <VStack gap="12">{cues}</VStack>
    </HStack>
    <VStack grow="1" />
    {p.label(caption, "$ink", 10) if caption else ""}
  </VStack>
</Slide>'''


def render(plans_file: Path, out: Path) -> list[Path]:
    data = json.loads(plans_file.read_text(encoding="utf-8"))
    deck, plans = data["deck"], data["slides"]
    p = Pack(deck["pack"], deck.get("entities"))
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for i, plan in enumerate(plans):
        body = cover(plan, deck, p, len(plans)) if plan.get("slide_type") == "cover" else frame(plan, deck, p, i + 1, len(plans))
        f = out / f"slide-{i + 1:02d}.xml"
        f.write_text(p.theme() + "\n\n" + body + "\n", encoding="utf-8")
        written.append(f)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plans", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    for f in render(a.plans, a.out):
        print(f)


if __name__ == "__main__":
    main()
