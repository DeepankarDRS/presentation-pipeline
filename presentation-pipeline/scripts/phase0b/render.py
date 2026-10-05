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
from functools import lru_cache
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
        self.dark_c = spec.get("colors_dark")
        self.headline = spec.get("headline", "bold")
        self.head_max_w = spec.get("headline_max_w", INNER)
        # two-pass sizing (scripts/phase0b/fit.py): measured heights of fixed blocks by index,
        # a type scale for the body, and the kinds of the last composed blocks
        self.measured: dict[int, float] = {}
        self.min_h: dict[int, float] = {}   # growers: the height their content measured at
        self.scale = 1.0
        self.block_kinds: list[str] = []
        self.card_titles = spec.get("card_titles", "plain")
        self.fills = spec.get("fills", "flat")
        self.card_border = spec.get("card_border", False)
        self.ghost = spec.get("ghost_numerals", False)
        self.dark_slides = spec.get("dark_slides", [])
        self.strip_style = spec.get("strip", "dark")
        self.kicker_number = spec.get("kicker_number", False)
        self.running = spec.get("running", True)
        self.arrows = spec.get("arrows", False)
        self.is_dark = False  # set per slide

    @property
    def border(self) -> str:
        return ' border.color="$line" border.width="1"' if self.card_border else ""

    def theme(self) -> str:
        tokens = dict(self.dark_c if self.is_dark and self.dark_c else self.c)
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


# Real glyph widths for the fonts shipped in src/node/fonts/ (what POM measures and the
# slide renders with); other families fall back to the per-character estimate.
FONT_FILES = {("inter", False, False): "Inter-Regular.ttf", ("inter", True, False): "Inter-Bold.ttf",
              ("inter", False, True): "Inter-Italic.ttf", ("inter", True, True): "Inter-BoldItalic.ttf",
              ("jetbrains mono", False, False): "JetBrainsMono-Regular.ttf",
              ("jetbrains mono", True, False): "JetBrainsMono-Bold.ttf"}


@lru_cache(maxsize=None)
def _font(family: str, bold: bool, italic: bool = False):
    name = FONT_FILES.get((family.lower(), bold, italic)) or FONT_FILES.get((family.lower(), bold, False))
    if not name:
        return None
    try:
        from PIL import ImageFont
        return ImageFont.truetype(str(HERE.parent.parent / "src" / "node" / "fonts" / name), 100)
    except Exception as e:  # no Pillow / no font file: estimate, but say so (sizes will differ)
        import sys
        print(f"phase0b: cannot load {name} ({type(e).__name__}: {e}); text widths are estimated",
              file=sys.stderr)
        return None


def em(text: str, family: str, bold: bool = True, italic: bool = False) -> float:
    """Width of text in em (px at fontSize 1)."""
    f = _font(family, bold, italic)
    return f.getlength(text) / 100 if f else len(text) * (0.62 if bold else 0.54)


def pom_lines(text: str, family: str, fs: float, width: float, bold: bool = True) -> int:
    """Lines POM reserves (measureText.js): tokens "word " keep their trailing space, no break
    inside a word; a word wider than the box takes a line of its own."""
    words = text.split()
    tokens = [w + " " for w in words[:-1]] + words[-1:]
    lines, cur = 1, ""
    for tok in tokens:
        cand = cur + tok
        if not cur or em(cand, family, bold) * fs <= width:
            cur = cand
        else:
            lines, cur = lines + 1, tok
    return lines


def drawn_lines(text: str, family: str, fs: float, width: float, bold: bool = True,
                italic_last: bool = False) -> int | None:
    """Lines the renderer draws (breaks after hyphens too; the last word italic when the pack
    sets it so); None if a piece is wider than the box."""
    lines, cur = 1, 0.0
    space = em(" ", family, bold) * fs
    words = text.split()
    for wi, word in enumerate(words):
        it = italic_last and wi == len(words) - 1 and len(words) > 1
        for k, piece in enumerate(re.findall(r"[^-]+-?|-", word)):
            ww = em(piece, family, bold, it) * fs
            if ww > width:
                return None
            gap = space if k == 0 else 0.0
            if cur and cur + gap + ww > width:
                lines, cur = lines + 1, ww
            else:
                cur = cur + gap + ww if cur else ww
    return lines


def text_lines(text: str, family: str, fs: float, width: float, bold: bool = True,
               italic_last: bool = False) -> int | None:
    """Lines the renderer draws, only when that count is stable within +-3% of the width
    (borders, rounding); None = a break too close to call at this size. Where POM's own
    count differs (it keeps trailing spaces, never breaks at hyphens, measures italics
    upright), the caller pins the Text's height to these lines (pin_h)."""
    a = drawn_lines(text, family, fs, width * 0.97, bold, italic_last)
    b = drawn_lines(text, family, fs, width * 1.03, bold, italic_last)
    return a if a is not None and a == b else None


def pin_h(text: str, family: str, fs: float, width: float, lh: float, bold: bool = True,
            italic_last: bool = False) -> str:
    """h="…" pinning a Text to the lines the renderer draws, when POM would reserve another
    number (a blank line, or text running out of its box); "" when they agree."""
    drawn = text_lines(text, family, fs, width, bold, italic_last)
    if drawn is None or drawn == pom_lines(text, family, fs, width, bold):
        return ""
    return f' h="{math.ceil(drawn * fs * lh)}"'


def fill_card_text(cards: list[tuple[str, str]], family: str, width: float, height: float,
                   lo: tuple[int, int], hi: int = 36, italic_last: bool = False) -> tuple[int, int]:
    """(title, description) sizes that fill every card's width and free height: the largest
    description first (<= 18px), then the largest title, the title at least 1.3x the
    description (lo = the pack's sizes). Only sizes where every line break is unambiguous."""
    def fits(tfs: int, bfs: int) -> bool:
        for title, body in cards:
            tl = text_lines(title, family, tfs, width, italic_last=italic_last)
            bl = text_lines(body, family, bfs, width, bold=False) if body else 0
            if tl is None or bl is None or tl * tfs * 1.2 + (8 + bl * bfs * 1.4 if body else 0) > height:
                return False
        return True

    for bfs in range(18, lo[1] - 1, -1):
        for tfs in range(hi, max(lo[0], math.ceil(bfs * 1.3)) - 1, -1):
            if fits(tfs, bfs):
                return tfs, bfs
    return lo


def fill_title_fs(titles: list[str], family: str, width: float, height: float, lo: int, hi: int = 48,
                  italic_last: bool = False) -> int:
    """Largest title size (lo..hi) at which every title fits its card's width and the free
    height, with unambiguous line breaks (text_lines)."""
    for fs in range(hi, lo, -1):
        lines = [text_lines(t, family, fs, width, italic_last=italic_last) for t in titles]
        if all(n is not None and n * fs * 1.2 <= height for n in lines):
            return fs
    return lo


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
    # line box = the glyphs' height (GLYPH_H): at lineHeight 1 a big number hung below its box
    # onto the note under it (POM writes exact spacing and centres with Noto metrics)
    m = _NUM.match(value.strip())
    if not m or not m["unit"]:
        return f'<Text fontSize="{fs}" fontFamily="{p.sans}" bold="true" color="{color}" lineHeight="{GLYPH_H}">{x(value)}</Text>'
    return (f'<Text fontSize="{fs}" fontFamily="{p.sans}" bold="true" color="{color}" lineHeight="{GLYPH_H}">'
            f'{x(m["pre"] + m["num"])}<Span fontSize="{round(fs * 0.45)}">{x(m["unit"])}</Span></Text>')


def _value_em(value: str, p: Pack) -> float:
    m = _NUM.match(value.strip())
    if not m or not m["unit"]:
        return em(value, p.sans)
    return em(m["pre"] + m["num"], p.sans) + 0.45 * em(m["unit"], p.sans)


def kpi_label_fs(p: Pack, h: float | None) -> int:
    return int(min(14, max(p.t["label"], (h or 0) / 17)))


def kpi_width_fs(comp: dict, p: Pack, width: float = INNER) -> int:
    """Largest number size at which every value fits its tile's width (5% margin)."""
    values = comp["content_data"].get("kpi_values", [])
    tile_w = (width - 12 * (len(values) - 1)) / max(1, len(values)) - 40
    return int(tile_w * 0.95 / max((_value_em(v, p) for v in values), default=1))


GLYPH_H = 1.2   # a number's drawn height per px of font size (Inter ascent + descent ~1.21)
KPI_CAP = 120   # largest KPI number (fit-grow's hero cap)


def kpi_need(comp: dict, p: Pack, h: float) -> float:
    """Tile height when the number fills the width: padding + label + gap + number (+ note)."""
    notes = 22 if any(comp["content_data"].get("kpi_deltas") or []) else 0
    return 40 + kpi_label_fs(p, h) * 1.3 + 12 + min(KPI_CAP, kpi_width_fs(comp, p)) * GLYPH_H + notes


def kpi_row(comp: dict, p: Pack, hero: bool, h: float | None = None, grow: str = "", width: float = INNER) -> str:
    cd = comp["content_data"]
    labels, values = cd.get("kpi_labels", []), cd.get("kpi_values", [])
    notes = [n or "" for n in (cd.get("kpi_deltas") or [])] + [""] * len(values)  # null notes show nothing
    dark = _named_in_hint(comp, labels, "inverted")
    width_fs = kpi_width_fs(comp, p, width)  # the slot's width (a half-width slot on a mixed slide)
    fs = min(p.t["big"] if hero else p.t["mid"], width_fs)
    lfs = kpi_label_fs(p, h)
    if h:  # sized to the slot: the number fills what the tile's width and height allow
        # the glyphs are ~1.2x the size tall: sized by 1.0 a 147px "70%+" ran into its note
        free = h - 40 - lfs * 1.3 - 12 - (22 if any(notes) else 0)
        fs = max(24, min(width_fs, KPI_CAP, int(free / GLYPH_H)))
    tiles = []
    for label, value, note in zip(labels, values, notes):
        ent = p.entity(label)
        bg, lab_c, num_c, border = "$panel", "$muted", "$ink", p.border
        if label == dark:
            bg, lab_c, num_c = "$dark", "$accent2", "$white"
        elif ent:
            bg, lab_c = ent[1], ent[2]
            border = f' borderLeft.color="{ent[0]}" borderLeft.width="3"'
        note_xml = (f'<Text fontSize="11" fontFamily="{p.sans}" color="{"$white" if label == dark else "$muted"}">'
                    f'{x(note)}</Text>' if note else "")
        fixed_h = "" if h else f' h="{130 if hero else 100}"'
        tiles.append(f'<VStack w="1" grow="1"{fixed_h} padding="20" gap="8" backgroundColor="{bg}"{border} '
                     f'justifyContent="spaceBetween">{p.label(label, lab_c, lfs)}'
                     f'<VStack gap="6">{big_number(value, fs, num_c, p)}{note_xml}</VStack></VStack>')
    return f'<HStack gap="12" alignItems="stretch"{grow}>{"".join(tiles)}</HStack>'


_PHASE = re.compile(r"^((?:Phase|Month|Step|Stage)\s*\d+)\s*[:\-–]\s*(.+)$", re.I)


def _split_list(body: str) -> list[str] | None:
    parts = [s.strip().rstrip(".") for s in body.split(",")]
    return parts if len(parts) >= 3 and all(0 < len(s.split()) <= 5 for s in parts) else None


def card_role(p: Pack, role: str) -> tuple[str, str, str, str]:
    """(fill, text, label colour, border) for a card role: normal / highlight / dark."""
    if p.fills == "rhythm":
        if role == "highlight" or (role == "dark" and p.is_dark):
            return "$accent2", "$onAccent", "$onAccent", ""
        if role == "dark":
            return "$dark", "$white", "$accent2", ""
        return "$panel", "$ink", "$muted", p.border
    if role in ("highlight", "dark"):
        return "$dark", "$white", "$accent2", ""
    return "$panel", "$ink", "$accent", p.border


def title_runs(title: str, p: Pack, on_dark: bool) -> str:
    t = title.replace("↑", "").strip() if p.arrows else title
    if p.card_titles != "italic_last" or " " not in t:
        return x(t)
    head, last = t.rsplit(" ", 1)
    inner = f'<Span color="$accent2">{x(last)}</Span>' if on_dark else x(last)
    return f"{x(head)} <I>{inner}</I>"


def _named_in_hint(comp: dict, names: list[str], word: str) -> str | None:
    hint = comp.get("design_hint") or ""
    if word not in hint:
        return None
    after = hint.split(word, 1)[1]
    hits = [n for n in names if n and n in after]
    return max(hits, key=len) if hits else None


def card_text_fit(cards: list[dict], p: Pack, card_w: float, row_h: float) -> tuple[int, int]:
    """(title, description) sizes that fill title + description cards of this size."""
    lab_fs = int(min(13, max(p.t["label"], row_h / 13)))
    pairs = [(_PHASE.sub(r"\2", c.get("title", "")).replace("↑", "").strip(), c.get("body") or "") for c in cards]
    return fill_card_text(pairs, p.sans, card_w, row_h - 36 - lab_fs * 1.3 - 8 - 6, (p.t["title"], 12),
                          italic_last=p.card_titles == "italic_last")


def grid_text_fit(comp: dict, p: Pack, width: float, h: float) -> tuple[int, int] | None:
    """card_text_fit for a whole grid in a slot (uses its _cols); None if not description cards."""
    cd = comp["content_data"]
    cards = [c if isinstance(c, dict) else {"title": str(c)} for c in cd.get("cards", [])]
    if not cards or not cd.get("_cols") or not any(c.get("body") for c in cards) or any(
            c.get("bullets") or _split_list(c.get("body") or "") for c in cards):
        return None
    n = cd["_cols"]
    rows = math.ceil(len(cards) / n)
    return card_text_fit(cards, p, (width - 12 * (n - 1)) / n - 36, (h - 12 * (rows - 1)) / rows)


def card_grid(comp: dict, p: Pack, width: float, grows: bool, h: float | None = None, grow: str = "") -> str:
    cd = comp["content_data"]
    cards = [c if isinstance(c, dict) else {"title": str(c)} for c in cd.get("cards", [])]
    steps = cd.get("card_layout") == "steps"
    titles = [c.get("title", "") for c in cards]
    hi = _named_in_hint(comp, titles, "inverted") or (titles[-1] if steps and len(titles) > 1 else None)
    rich = any(c.get("body") or c.get("bullets") for c in cards)
    tfs = p.t["title"] + (2 if rich else 0)
    n = cd.get("_cols") or (len(cards) if steps and len(cards) <= 5 else fit_columns(
        [_PHASE.sub(r"\2", t) for t in titles], width, tfs, 5 if len(cards) == 5 else 4))

    n_rows = 1 if steps and len(cards) <= 5 else math.ceil(len(cards) / n)
    tile_h = {1: 150, 2: 120}.get(n_rows, 96)
    if h:  # a slot: rows share it, titles grow with the row (never past the longest word's width)
        grows = True
        row_h = (h - 12 * (n_rows - 1)) / n_rows
        card_w = (width - 12 * (n - 1)) / n - 36
        longest = max((len(w) for t in titles for w in _PHASE.sub(r"\2", t).split()), default=1)
        most_items = max((len(c.get("bullets") or _split_list(c.get("body") or "") or []) for c in cards), default=0)
        if rich and not most_items:  # title + description cards: both grow to fill the card
            lab_fs = int(min(13, max(p.t["label"], row_h / 13)))
            tfs, body_fs = card_text_fit(cards, p, card_w, row_h)
            if cd.get("_fit"):  # a peer grid beside it: both use the smaller fit
                tfs, body_fs = min(tfs, cd["_fit"][0]), min(body_fs, cd["_fit"][1])
        elif rich:
            tfs = int(max(p.t["title"], min(tfs, card_w / (longest * 0.62))))
        else:  # title-only cards: the title fills the card's width and free height
            lab_fs = int(min(13, max(p.t["label"], row_h / 13)))
            icon = 50 if p.arrows and any("↑" in t for t in titles) else 0
            ghost_h = 54 if p.ghost and (steps or any(_PHASE.match(t) for t in titles)) else 0
            shown = [_PHASE.sub(r"\2", t).replace("↑", "").strip() for t in titles]
            title_w = card_w - icon
            free_h = row_h - 36 - lab_fs * 1.3 - 8 - ghost_h - 6
            tfs = fill_title_fs(shown, p.sans, title_w, free_h, p.t["title"],
                                italic_last=p.card_titles == "italic_last")
            # titles are width-bound (narrow cards): the space they can't use goes to the card's
            # own number, drawn as a big numeral instead of the small label (numbered cards)
            used = max((text_lines(t, p.sans, tfs, title_w, italic_last=p.card_titles == "italic_last") or 1)
                       for t in shown) * tfs * 1.2
            left = free_h - used
            if left > 40 and not ghost_h and not icon and all(not c.get("tag") for c in cards):
                num_fs = int(min(96, lab_fs * 1.3 + left - 6))
        most = max((len(c.get("bullets") or _split_list(c.get("body") or "") or []) for c in cards), default=0)
        if rich and most:
            free = row_h - 36 - 14 - 8 - (54 if p.ghost and (steps or any(_PHASE.match(t) for t in titles)) else 0) - tfs * 2.6
            per = free / most
            bfs = int(max(p.t["body"], min(17, per * 0.42)))
            bgap = int(max(8, min(22, per - bfs * 1.35)))

    lab_size = locals().get("lab_fs")
    num_fs = locals().get("num_fs")
    # filled cards: pin each Text to the lines the renderer draws (pin_h)
    text_w = (locals().get("title_w") or locals().get("card_w")) if locals().get("lab_fs") else None
    body_fs = locals().get("body_fs", 12)
    bfs = locals().get("bfs", p.t["body"])
    bgap = locals().get("bgap", 8)

    def role_of(i: int, c: dict) -> str:
        if c.get("title") == hi:
            return "dark" if steps and p.fills == "rhythm" and not p.is_dark else "highlight"
        if p.fills == "rhythm" and not steps and len(cards) >= 5:
            if i % 4 == 1:
                return "dark"
            if hi is None and i == 3:
                return "highlight"
        return "normal"

    italic = p.card_titles == "italic_last"

    def pin(text: str, fs: float, lh: float, bold: bool) -> str:
        return pin_h(text.replace("↑", "").strip(), p.sans, fs, text_w, lh, bold, italic and bold) if text_w else ""

    def one(i: int, c: dict) -> str:
        title = c.get("title", "")
        m = _PHASE.match(title)
        tag = m.group(1) if m else (c.get("tag") or f"{i + 1:02d}")
        if m and c.get("tag"):
            tag = f"{tag} · {c['tag']}"
        title = m.group(2) if m else title
        role = role_of(i, c)
        bg, ink, lab, border = card_role(p, role)
        inv = role != "normal"
        on_dark = bg == "$dark" or (p.is_dark and role == "normal")
        top = f' borderTop.color="{lab if inv else "$accent"}" borderTop.width="3"' if steps else ""
        ghost = ""
        num = re.search(r"\d+", tag)
        if p.ghost and (steps or m) and num:
            gcol = "$line" if role == "normal" else lab
            ghost = f'<Text fontSize="46" fontFamily="{p.sans}" bold="true" color="{gcol}" lineHeight="1">{int(num.group()):02d}</Text>'
        num_col = "$line" if role == "normal" else lab  # faint, like the pack's ghost numerals
        tag_xml = (f'<Text fontSize="{num_fs}" fontFamily="{p.sans}" bold="true" color="{num_col}" lineHeight="1">{x(tag)}</Text>'
                   if num_fs and re.fullmatch(r"\d+", tag) else p.label(tag, lab, lab_size))
        parts = [tag_xml, ghost,
                 f'<Text fontSize="{tfs}" fontFamily="{p.sans}" bold="true" color="{ink}" lineHeight="1.2"'
                 f'{pin(title, tfs, 1.2, True)}>{title_runs(title, p, on_dark)}</Text>']
        parts = [q for q in parts if q]
        bullets = c.get("bullets") or (_split_list(c["body"]) if c.get("body") else None)
        if c.get("body") and not bullets:
            parts.append(f'<Text fontSize="{body_fs}" fontFamily="{p.sans}" color="{ink if inv else "$muted"}" '
                         f'lineHeight="1.4"{pin(c["body"], body_fs, 1.4, False)}>{x(c["body"])}</Text>')
        if cd.get("columns"):
            parts.append(f'<Text fontSize="12" fontFamily="{p.sans}" color="$muted" lineHeight="1.4">'
                         f'{x(" · ".join(cd["columns"]))}</Text>')
        if bullets:
            dot = lab if inv else ("$accent2" if p.is_dark else "$accent")
            parts.append(f'<VStack margin.top="4" gap="{bgap}">' + "".join(
                f'<HStack gap="10" alignItems="center"><Shape shapeType="rect" w="5" h="5" fill.color="{dot}" />'
                f'<Text fontSize="{bfs}" fontFamily="{p.sans}" color="{ink}">{x(b)}</Text></HStack>'
                for b in bullets) + "</VStack>")
        lone = len(parts) == 2  # label + title only: fixed tile, label top, title bottom
        just = (' justifyContent="spaceBetween"' if grows else f' h="{tile_h}" justifyContent="spaceBetween"') if lone else ""
        if p.arrows and "↑" in title:
            icol = {"highlight": "$onAccent", "dark": "$accent2"}.get(role, "$accent" if i % 2 == 0 else "$ink")
            if p.is_dark and role == "dark":
                icol = "$onAccent"
            return (f'<HStack w="1" grow="1" padding="18" gap="10" alignItems="center" backgroundColor="{bg}"{border}{top}'
                    f'{" h=" + chr(34) + str(tile_h) + chr(34) if lone and not grows else ""}>'
                    f'<VStack grow="1" gap="8" justifyContent="spaceBetween">{"".join(parts)}</VStack>'
                    f'<Icon name="arrow-up" size="40" color="{icol}" /></HStack>')
        return (f'<VStack w="1" grow="1" padding="18" gap="8" backgroundColor="{bg}"{border}{top}{just}>'
                + "".join(parts) + "</VStack>")

    if steps and len(cards) <= 5:
        arrow = f'<Icon name="arrow-right" size="18" color="$muted" alignSelf="center" />'
        row = arrow.join(one(i, c) for i, c in enumerate(cards))
        return f'<HStack gap="10" alignItems="stretch"{grow or (" grow=" + chr(34) + "1" + chr(34) if grows else "")}>{row}</HStack>'
    rows = []
    for r in range(0, len(cards), n):
        chunk = [one(i, c) for i, c in enumerate(cards[r:r + n], start=r)]
        chunk += ['<VStack w="1" grow="1" />'] * (n - len(chunk))  # keep columns aligned
        g = ' grow="1"' if grows else ""
        rows.append(f'<HStack gap="12" alignItems="stretch"{g}>{"".join(chunk)}</HStack>')
    g = grow or (' grow="1"' if grows else "")
    return f'<VStack gap="12" alignItems="stretch"{g}>{"".join(rows)}</VStack>'


def tile_row(items: list[str], p: Pack) -> str:
    """Short parallel items in ONE compact row (Genspark XTSY slide 6 benefits)."""
    tiles = "".join(
        f'<VStack w="1" grow="1" padding="14" backgroundColor="$panel"{p.border} borderTop.color="{"$accent2" if p.fills == "rhythm" else "$accent"}" borderTop.width="3">'
        f'<Text fontSize="13" fontFamily="{p.sans}" bold="true" color="$ink" lineHeight="1.25">{x(i)}</Text></VStack>'
        for i in items)
    return f'<HStack gap="10" alignItems="stretch">{tiles}</HStack>'


def note_columns(items: list[str], p: Pack) -> str:
    """Two or three sentence-length notes as columns in one dark panel."""
    cols = "".join(f'<VStack w="1" grow="1" gap="6"><Text fontSize="13" fontFamily="{p.sans}" color="$white" '
                   f'lineHeight="1.45">{x(i)}</Text></VStack>' for i in items)
    return f'<HStack padding="20" gap="28" backgroundColor="$dark" alignItems="start">{cols}</HStack>'


def bullet_panel(items: list[str], p: Pack, grow: str = "") -> str:
    rows = "".join(f'<HStack gap="10" alignItems="center"><Shape shapeType="rect" w="5" h="5" fill.color="$accent" />'
                   f'<Text fontSize="{p.t["body"] + 1}" fontFamily="{p.sans}" color="$ink">{x(i)}</Text></HStack>'
                   for i in items)
    spread = ' justifyContent="spaceEvenly"' if grow else ""
    return f'<VStack padding="18" gap="10" backgroundColor="$panel"{p.border}{grow}{spread}>{rows}</VStack>'


def bullets_block(comp: dict, p: Pack, grow: str = "", width: float = INNER) -> str:
    """Short items -> one tile row, long ones -> note columns, else a bullet panel; the row and
    columns only when the slot is wide enough (a 469 px slot broke "optimiza/tion" in tiles)."""
    items = [str(b) for b in comp["content_data"].get("bullets", [])]
    if 2 <= len(items) <= 6 and all(len(i.split()) <= 5 for i in items):
        tile_inner = (width - 10 * (len(items) - 1)) / len(items) - 28
        if all(em(w_, p.sans) * 13 <= tile_inner for i in items for w_ in i.split()):
            return tile_row(items, p)
    if 2 <= len(items) <= 3 and all(len(i.split()) >= 8 for i in items) and width >= 300 * len(items):
        return note_columns(items, p)
    return bullet_panel(items, p, grow)


def linear_flow(comp: dict) -> list[str] | None:
    """A flow that is a plain sequence (only `flow_steps`, 2-8 short steps) is drawn like
    process steps; a flow with nodes / connections / branches is not a sequence (None)."""
    cd = comp.get("content_data") or {}
    steps = cd.get("flow_steps")
    if set(cd) - {"flow_steps", "direction"} or not isinstance(steps, list) or not 2 <= len(steps) <= 8:
        return None
    return [str(s) for s in steps] if all(isinstance(s, (str, int, float)) for s in steps) else None


def process_steps(comp: dict, p: Pack) -> str:
    cd = comp["content_data"]
    steps = [str(s) for s in (cd.get("process_steps") or cd.get("flow_steps") or [])]
    out = []
    for i, s in enumerate(steps):
        last = i == len(steps) - 1
        bg, ink = ("$accent2", "$onAccent") if last else ("$panel", "$ink")
        out.append(f'<VStack w="1" grow="1" padding="12" backgroundColor="{bg}"{"" if last else p.border} alignItems="center">'
                   f'<Text fontSize="14" fontFamily="{p.sans}" bold="true" color="{ink}" textAlign="center">{x(s)}</Text></VStack>')
    arrow = '<Icon name="arrow-right" size="18" color="$accent" alignSelf="center" />'
    return f'<HStack gap="8" alignItems="stretch">{arrow.join(out)}</HStack>'


# "Head — detail", "Head—detail" (em dash, spaces optional), "Head – detail" / "Head: detail" (spaced);
# an unspaced en dash is a range ("6–11 AM"), not a split
_HEAD = re.compile(r"^(.{2,60}?)(?:\s*—\s*|\s+–\s+|:\s+)(.+)$", re.S)
TL_SHORT = 6       # every label <= this many words: rail + dots + labels, no cards
TL_DOT = 12


def timeline_items(comp: dict) -> list[tuple[str, str, str]]:
    """(date, head, body) per item. A label written "Head — detail" / "Head: detail" (head of
    <= 6 words) splits at the planner's own dash; otherwise head is "" and the label is the body.
    Nothing is reworded."""
    out = []
    for it in (comp.get("content_data") or {}).get("timeline_items") or []:
        date, label = (str(it.get("date") or ""), str(it.get("label") or "")) if isinstance(it, dict) else ("", str(it))
        m = _HEAD.match(label.strip())
        if m and len(m.group(1).split()) <= 6 and len(label.split()) > TL_SHORT:
            out.append((date, m.group(1).strip(), m.group(2).strip()))
        else:
            out.append((date, "", label.strip()))
    return out


def timeline_need(comp: dict, p: Pack) -> float:
    """Natural height of a short-label timeline (the long one grows into its slot)."""
    return 16 + 8 + TL_DOT + 12 + 2 * 20 * 1.25


def timeline_block(comp: dict, p: Pack, width: float, h: float | None = None, grow: str = "") -> str:
    """A horizontal timeline: one column per item, a continuous rail (dot + line to the next
    column), the date above the rail. Short labels sit under their dot as a title; long ones
    get a card under the dot (head bold, detail below), type sized to fill the cards. The item
    a design hint calls "inverted" gets a dark card."""
    items = timeline_items(comp)
    n = max(1, len(items))
    col_w = width / n
    short = all(not hd and len(b.split()) <= TL_SHORT for _, hd, b in items)
    hi = _named_in_hint(comp, [b for _, _, b in items] + [hd for _, hd, _ in items if hd], "inverted")
    lab_fs = int(min(13, max(p.t["label"], (h or 0) / 30)))
    head_h = lab_fs * 1.3 + 8 + TL_DOT + 12  # date + gap + rail + gap
    inner_w = col_w - 14 - 32                # card: margin.right 14, padding 16 x 2
    free = (h or 260) - head_h - 32 - 4
    def lines(t: str, fs: float, w: float, bold: bool) -> int:
        """Lines for the height budget: drawn at 97% of the width (a break near the edge counts
        as the extra line), never fewer than POM reserves. Long texts almost always have one
        borderline break, so the strict text_lines() would reject every size."""
        return max(drawn_lines(t, p.sans, fs, w * 0.97, bold) or 99, pom_lines(t, p.sans, fs, w, bold))

    if short:
        avail = max(24.0, (h or 120) - head_h - 12)
        tfs = next((fs for fs in range(32, p.t["title"] - 1, -1)
                    if all(lines(b, fs, col_w - 14, True) * fs * 1.25 <= avail for _, _, b in items)), p.t["title"])
    else:
        heads = any(hd for _, hd, _ in items)
        tfs, bfs = p.t["title"], 11
        for b_fs in range(24, 10, -1):  # the largest detail size first, then the largest head (>= 1.25x)
            t_lo = max(p.t["title"], math.ceil(b_fs * 1.25))
            t_fs = next((t for t in range(max(26, t_lo), t_lo - 1, -1)
                         if all((lines(hd, t, inner_w, True) * t * 1.2 + 6 if hd else 0)
                                + lines(b, b_fs, inner_w, False) * b_fs * 1.4 <= free for _, hd, b in items)), None)
            if t_fs is not None or not heads and all(lines(b, b_fs, inner_w, False) * b_fs * 1.4 <= free for _, _, b in items):
                tfs, bfs = (t_fs or p.t["title"]), b_fs
                break

    cols = []
    for i, (date, hd, body) in enumerate(items):
        last = i == len(items) - 1
        inv = hi is not None and hi in (hd, body)
        dot = f'<Shape shapeType="ellipse" w="{TL_DOT}" h="{TL_DOT}" fill.color="{"$accent2" if inv else "$accent"}" />'
        line = '' if last else '<Shape shapeType="rect" w="1" grow="1" h="2" fill.color="$line" />'
        rail = f'<HStack alignItems="center" margin.top="8">{dot}{line}</HStack>'
        date_xml = p.label(date, "$accent" if p.fills != "rhythm" else "$muted", lab_fs) if date else ""
        if short:
            under = (f'<Text margin.top="12" margin.right="14" fontSize="{tfs}" fontFamily="{p.sans}" bold="true" '
                     f'color="$ink" lineHeight="1.25"{pin_h(body, p.sans, tfs, col_w - 14, 1.25)}>{x(body)}</Text>')
        else:
            bg, ink, _, border = card_role(p, "dark" if inv else "normal")
            parts = []
            if hd:
                parts.append(f'<Text fontSize="{tfs}" fontFamily="{p.sans}" bold="true" color="{ink}" lineHeight="1.2"'
                             f'{pin_h(hd, p.sans, tfs, inner_w, 1.2)}>{x(hd)}</Text>')
            parts.append(f'<Text fontSize="{bfs}" fontFamily="{p.sans}" color="{ink if inv else "$muted"}" lineHeight="1.4"'
                         f'{pin_h(body, p.sans, bfs, inner_w, 1.4, bold=False)}>{x(body)}</Text>')
            under = (f'<VStack margin.top="12" margin.right="14" grow="1" padding="16" gap="6" backgroundColor="{bg}"{border}>'
                     + "".join(parts) + "</VStack>")
        cols.append(f'<VStack w="1" grow="1" alignItems="stretch">{date_xml}{rail}{under}</VStack>')
    return f'<HStack alignItems="stretch"{grow}>{"".join(cols)}</HStack>'


def data_table(comp: dict, p: Pack, width: float, h: float | None = None) -> str:
    cd = comp["content_data"]
    cols, rows = cd.get("table_columns", []), cd.get("table_rows", [])
    hi = _named_in_hint(comp, [str(r[0]) for r in rows], "row") if rows else None
    lens = [max(len(str(c)), *(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
    total = sum(min(l, 40) + 6 for l in lens)
    widths = [round(width * (min(l, 40) + 6) / total) for l in lens]
    fs, rh = (15, 50) if len(rows) <= 4 else (13, 38)
    if h:
        rh = int(max(38, min(76, (h - 40) / max(1, len(rows)))))
        fs = 13 if rh < 46 else (15 if rh < 60 else 17)
    out = [f'<Table defaultRowHeight="{rh}" cellBorder.color="$line" cellBorder.width="1">']
    out += [f'<Col width="{w}" />' for w in widths]
    out.append('<Tr height="40">' + "".join(f'<Td fontSize="10" fontFamily="{p.mono}" color="$muted" bold="true">{x(str(c).upper())}</Td>'
                                for c in cols) + "</Tr>")
    for r in rows:
        bg = ' backgroundColor="$panel"' if str(r[0]) == hi else ""
        ent = p.entity(str(r[0]))
        cells = []
        for i, v in enumerate(r):
            color = ent[2] if (i == 0 and ent) else ("$accent" if str(r[0]) == hi and i else "$ink")
            bold = ' bold="true"' if i == 0 or str(r[0]) == hi else ""
            shown = x(v) if str(v).strip() else "–"  # POM rejects an empty cell; a dash marks the missing value
            cells.append(f'<Td fontSize="{fs}" fontFamily="{p.sans}" color="{color}"{bold}{bg}>{shown}</Td>')
        out.append("<Tr>" + "".join(cells) + "</Tr>")
    out.append("</Table>")
    return "".join(out)


def _signed(v: Any) -> float:
    m = re.search(r"-?[\d.]+", str(v).replace(",", ""))
    try:
        return float(m.group()) if m else 0.0
    except ValueError:
        return 0.0


def _num(v: Any) -> float | None:
    m = re.search(r"[\d.]+", str(v).replace(",", ""))
    return float(m.group()) if m else None


def bar_list(labels: list[str], series: list[tuple[str, list[str]]], p: Pack, width: float, h: float | None = None) -> str:
    """Horizontal bars. One series: best = accent, worst = negative. Two: entity colour + grey."""
    track = width - 130 - 100
    vals = [_num(v) or 0 for _, vs in series for v in vs]
    top = max(vals) or 1
    rows = []
    per = (h - (34 if len(series) > 1 else 0)) / max(1, len(labels)) if h else None

    def thick(per_row: float | None) -> int:
        if per_row is None:
            return (22 if len(labels) <= 3 else 16) if len(series) == 1 else (18 if len(labels) <= 3 else 12)
        return int(max(12, min(30, per_row * (0.32 if len(series) == 1 else 0.22))))
    for li, label in enumerate(labels):
        ent = p.entity(label)
        bars = []
        for si, (name, vs) in enumerate(series):
            if li >= len(vs) or vs[li] is None:  # missing / null value (malformed plan): no bar, no "None"
                continue
            v = _num(vs[li]) or 0
            if len(series) == 1:
                col = "$accent" if v == max(vals) else ("$negative" if v == min(vals) else "$ink")
            else:
                col = (ent[0] if ent else "$ink") if si == 0 else "$line"
            bars.append(f'<HStack gap="8" alignItems="center"><Shape shapeType="rect" w="{max(4, round(track * v / top))}" '
                        f'h="{thick(per)}" fill.color="{col}" />'
                        f'<Text fontSize="{14 if per and per > 70 else 12}" fontFamily="{p.sans}" bold="true" color="$ink">{x(vs[li])}</Text></HStack>')
        lab_c = ent[2] if ent else "$ink"
        rows.append(f'<HStack gap="10" alignItems="center"><Text w="120" fontSize="14" fontFamily="{p.sans}" bold="true" '
                    f'color="{lab_c}">{x(label)}</Text><VStack gap="4">{"".join(bars)}</VStack></HStack>')
    legend = ""
    if len(series) > 1:
        legend = '<HStack gap="16" margin.top="4">' + "".join(
            f'<HStack gap="6" alignItems="center"><Shape shapeType="rect" w="10" h="10" fill.color="{"$ink" if i == 0 else "$line"}" />'
            f'{p.label(name)}</HStack>' for i, (name, _) in enumerate(series)) + "</HStack>"
    if h:
        return (f'<VStack grow="1" gap="10"><VStack grow="1" justifyContent="spaceAround">{"".join(rows)}</VStack>{legend}</VStack>')
    return f'<VStack gap="{24 if len(labels) <= 3 else 14}">{"".join(rows)}{legend}</VStack>'


def chart_block(comp: dict, p: Pack, width: float, h: float | None = None) -> str:
    """Ranked bars (shapes) for a short single-series bar chart; POM's native chart for
    everything else (line / doughnut / area, several series, many points): it scales to any
    slot, where 18 shape bars for 3 series x 6 months cannot (R2/R3)."""
    cd = comp["content_data"]
    labels = cd.get("chart_labels", [])
    series = [(s["name"], s["values"]) for s in cd.get("chart_series", [])] or [(cd.get("chart_title", ""), cd.get("chart_values", []))]
    kind = cd.get("chart_type") or "bar"
    if kind in ("bar", "column", "horizontal_bar") and len(series) <= 2 and len(labels) <= 8:
        return bar_list(labels, series, p, width, h)
    kind = {"column": "bar", "horizontal_bar": "bar"}.get(kind, kind)
    if kind not in ("bar", "line", "pie", "area", "doughnut", "radar"):
        kind = "bar"
    ents = [p.entity(name) for name, _ in series]
    named = [list(p.entities.values())[int(e[0][2:])] if e else None for e in ents]  # "$e0" -> entity colour
    palette = [p.c.get(k) for k in ("ink", "accent", "muted", "accent2", "negative") if p.c.get(k)]
    colors = [n or palette[i % len(palette)] for i, n in enumerate(named)]
    if kind in ("pie", "doughnut"):
        colors = palette
    pts = "".join(
        f'<ChartSeries name="{x(name)}">' + "".join(
            f'<ChartDataPoint label="{x(lab)}" value="{_signed(v):g}" />'
            for lab, v in zip(labels, vs) if v is not None) + "</ChartSeries>"
        for name, vs in series)
    ch = round(h) if h else 260
    return (f'<Chart chartType="{kind}" w="{round(width)}" h="{max(120, ch)}" showLegend="{"true" if len(series) > 1 or kind in ("pie", "doughnut") else "false"}" '
            f"chartColors='{json.dumps(colors)}'>{pts}</Chart>")


def panel(title: str | None, body: str, p: Pack, grows: bool = False) -> str:
    head = p.label(title) if title else ""
    g = ' grow="1"' if grows else ""
    return f'<VStack gap="12"{g}>{head}{body}</VStack>'


def insight(text: str, p: Pack) -> str:
    return (f'<VStack padding.left="14" borderLeft.color="$ink" borderLeft.width="3">'
            f'<Text fontSize="16" fontFamily="{p.sans}" color="$ink" lineHeight="1.4">{x(text)}</Text></VStack>')


def strip(text: str, label: str, p: Pack) -> str:
    if p.strip_style == "statement":
        parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
        body = f"<B>{x(parts[0])}</B> {x(parts[1])}" if len(parts) == 2 else x(text)
        return (f'<HStack gap="16" alignItems="start"><Shape margin.top="13" shapeType="rect" w="36" h="2" fill.color="$ink" />'
                f'<Text grow="1" fontSize="19" fontFamily="{p.sans}" italic="true" color="$ink" lineHeight="1.35">{body}</Text></HStack>')
    tag = p.label(label, "$accent2", extra=' w="120"')
    return (f'<HStack padding="18" gap="16" backgroundColor="$dark" alignItems="center" '
            f'borderLeft.color="$accent2" borderLeft.width="4">{tag}'
            f'<Text grow="1" fontSize="15" fontFamily="{p.sans}" color="$white" lineHeight="1.4">{x(text)}</Text></HStack>')


# ── composer (stands in for the generator's layout choices) ──────────────────

def _lines(text: str, fs: float, width: float) -> int:
    return max(1, math.ceil(text_px(text, fs) / width))


WEIGHT = {"hero": 3, "peer": 3, "supporting": 1, "minor": 1}
GAP = 16


def kpi_block(comp: dict, p: Pack, width: float, h: float, grow: str = "") -> str:
    """A KPI row for a w x h slot: mixed totals / entity values -> two tiers (as the composer
    does), and tiles narrower than ~170 px wrap into two rows; rows share the height."""
    rows = _split_kpi_tiers([comp], p)
    if len(rows) == 1:
        cd = comp["content_data"]
        n = len(cd.get("kpi_values") or [])
        if n >= 4 and (width - 12 * (n - 1)) / n < 170:
            half = math.ceil(n / 2)
            rows = [dict(comp, content_data={k: (v[a:b] if isinstance(v, list) and len(v) == n else v)
                                             for k, v in cd.items()})
                    for a, b in ((0, half), (half, n))]
    if len(rows) == 1:
        return kpi_row(comp, p, hero=comp.get("weight") != "supporting", h=h, grow=grow, width=width)
    share = [0.58, 0.42] if rows[0].get("weight") != rows[-1].get("weight") else [0.5, 0.5]
    inner = h - 12 * (len(rows) - 1)
    body = "".join(kpi_row(r, p, hero=r.get("weight") != "supporting", h=inner * share[i], width=width)
                   for i, r in enumerate(rows))
    return f'<VStack gap="12" alignItems="stretch"{grow}>{body}</VStack>'


def _split_kpi_tiers(comps: list[dict], p: Pack) -> list[dict]:
    """5+ tiles mixing combined and per-entity values -> combined tier + entity tier
    (Genspark CHEFFIN slide 2). Same content, laid out to fit."""
    out = []
    for c in comps:
        cd = c.get("content_data") or {}
        labels = cd.get("kpi_labels") or []
        ents = [i for i, l in enumerate(labels) if p.entity(l)]
        if c["kind"] == "kpi_row" and len(labels) > 4 and 0 < len(ents) < len(labels):
            for keep, weight, suffix in ((lambda i: i not in ents, c.get("weight", "hero"), ""),
                                          (lambda i: i in ents, "supporting", "_entities")):
                idx = [i for i in range(len(labels)) if keep(i)]
                tier = dict(c, weight=weight, component_id=(c.get("component_id") or "kpi") + suffix)
                tier["content_data"] = {k: ([v[i] for i in idx] if isinstance(v, list) and len(v) == len(labels) else v)
                                        for k, v in cd.items()}
                out.append(tier)
        else:
            out.append(c)
    return out


def compose_body(plan: dict, p: Pack, body_h: float) -> str:
    comps = [c for c in plan["components"] if c["kind"] not in ("title", "caption")]
    narr = [c for c in comps if c["kind"] == "narrative"]
    main = _split_kpi_tiers([c for c in comps if c["kind"] != "narrative"], p)

    # 1. blocks: ("fixed", xml, est_h) or ("grow", draw(h, grow_attr), weight)
    blocks: list[tuple] = []

    def fixed(xml: str, h: float) -> None:
        blocks.append(("fixed", xml, p.measured.get(len(blocks), h)))  # POM's height once measured

    def grower(fn, weight: float, cap: float = 1e9) -> None:
        blocks.append(("grow", fn, weight, cap))

    def cap_of(c: dict) -> float:
        k, cd = c["kind"], c.get("content_data") or {}
        if k == "kpi_row":  # the number is width-bound: a taller tile would only add empty space
            cap = 240 if c.get("weight") != "supporting" else 150
            return min(cap, kpi_need(c, p, cap) * 1.15)
        if k == "card_grid":
            cards = cd.get("cards", [])
            n = len(cards) if cd.get("card_layout") == "steps" and len(cards) <= 5 else max(1, min(4, len(cards)))
            rows = math.ceil(len(cards) / n) if cards else 1
            most = max((len(q.get("bullets") or _split_list(q.get("body") or "") or []) if isinstance(q, dict) else 0
                        for q in cards), default=0)
            if not most and not any(isinstance(q, dict) and q.get("body") for q in cards):
                return rows * 170 + 12 * (rows - 1)
            if not most:  # title + description cards: their text grows with the card (fill_card_text)
                return 1e9
            per_card = 36 + 14 + 8 + 54 + 60 + most * 34
            return rows * per_card + 12 * (rows - 1)
        if k == "table":
            rows, cols = cd.get("table_rows", []), cd.get("table_columns", [])
            if len(cols) == 2 and all(_num(r[1]) is not None for r in rows):
                return 24 + len(rows) * 52
            return 40 + len(rows) * 76
        if k == "chart":
            series = cd.get("chart_series") or [1]
            return len(cd.get("chart_labels", [])) * (len(series) * 34 + 40) + 34
        if k == "bullet_list":
            return 36 + len(cd.get("bullets", [])) * 34
        if k == "timeline":  # short labels: rail + one title line or two; long ones grow into cards
            items = timeline_items(c)
            return timeline_need(c, p) * 2.0 if all(not hd and len(b.split()) <= TL_SHORT for _, hd, b in items) else 1e9
        return 1e9

    def draw(c: dict, width: float, h: float, g: str) -> str:
        k = c["kind"]
        if k == "kpi_row":
            return kpi_row(c, p, hero=c.get("weight") != "supporting", h=h, grow=g)
        if k == "card_grid":
            return card_grid(c, p, width, True, h=h, grow=g)
        if k == "table":
            rows = c["content_data"].get("table_rows", [])
            cols = c["content_data"].get("table_columns", [])
            if len(cols) == 2 and all(_num(r[1]) is not None for r in rows):
                return (f'<VStack gap="12"{g}>{p.label(" · ".join(map(str, cols)))}'
                        + bar_list([str(r[0]) for r in rows], [(cols[1], [r[1] for r in rows])], p, width, h - 24) + "</VStack>")
            return f'<VStack{g}>{data_table(c, p, width, h)}</VStack>'
        if k == "chart":  # a chart on its own row keeps its title as a label
            title = c["content_data"].get("chart_title")
            head = p.label(title) if title else ""
            return f'<VStack gap="12"{g}>{head}{chart_block(c, p, width, h - (24 if title else 0))}</VStack>'
        if k == "bullet_list":
            return bullets_block(c, p, g)
        if k == "timeline":
            return timeline_block(c, p, width, h, g)
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
            if c["kind"] == nxt["kind"] == "card_grid":
                # peer grids: same number of rows, width split by columns -> every card the same
                # size, so both grids fill with the same type
                nl, nr = len(c["content_data"].get("cards", [])), len(nxt["content_data"].get("cards", []))
                rows = 2 if max(nl, nr) > 3 else 1
                cl, cr = math.ceil(nl / rows), math.ceil(nr / rows)
                unit = (INNER - 24 - 12 * (cl - 1) - 12 * (cr - 1)) / (cl + cr)
                wl = unit * cl + 12 * (cl - 1)
                wr = INNER - wl - 24
                c = dict(c, content_data=dict(c["content_data"], _cols=cl))
                nxt = dict(nxt, content_data=dict(nxt["content_data"], _cols=cr))

            def side(cc: dict, w: float, h: float, extra: str) -> str:
                title = cc["content_data"].get("chart_title")
                head = p.label(title) if title else ""
                inner_h = h - (24 if title else 0)
                return f'<VStack gap="12"{extra}>{head}{draw(cc, w, inner_h, chr(32) + "grow=" + chr(34) + "1" + chr(34))}</VStack>'

            pair_cap = max(cap_of(c), cap_of(nxt)) + 24

            def pair_xml(h, g, c=c, nxt=nxt, wl=wl, wr=wr):
                fits = [grid_text_fit(c, p, wl, h), grid_text_fit(nxt, p, wr, h)]
                if all(fits):  # peer description grids share the smaller fit
                    shared = (min(f[0] for f in fits), min(f[1] for f in fits))
                    c = dict(c, content_data=dict(c["content_data"], _fit=shared))
                    nxt = dict(nxt, content_data=dict(nxt["content_data"], _fit=shared))
                return (f'<HStack gap="24" alignItems="stretch"{g}>{side(c, wl, h, f" w={chr(34)}{round(wl)}{chr(34)}")}'
                        f'{side(nxt, wr, h, chr(32) + "grow=" + chr(34) + "1" + chr(34))}</HStack>')
            grower(pair_xml, 3, pair_cap)
            i += 2
            continue
        k = c["kind"]
        if k == "process_arrow" or (k == "flow" and linear_flow(c)):
            fixed(process_steps(c, p), 50)
        elif k == "bullet_list":
            items = [str(b) for b in c["content_data"].get("bullets", [])]
            if 2 <= len(items) <= 6 and all(len(t.split()) <= 5 for t in items):
                fixed(tile_row(items, p), 62)
            elif 2 <= len(items) <= 3 and all(len(t.split()) >= 8 for t in items):
                col_w = (INNER - 40 - 28 * (len(items) - 1)) / len(items)
                fixed(note_columns(items, p), 40 + max(_lines(t, 13, col_w) for t in items) * 19)
            else:
                grower(lambda h, g, c=c: draw(c, INNER, h, g), 1, cap_of(c))
        else:
            grower(lambda h, g, c=c: draw(c, INNER, h, g), WEIGHT.get(c.get("weight") or "hero", 3)
                   if not (k == "kpi_row" and c.get("weight") == "supporting") else 1.4, cap_of(c))
        i += 1

    for text in captions(plan, minor=False):  # weighted captions read as insights, not footnotes
        fixed(insight(text, p), _lines(text, 16, INNER - 20) * 23)
    for j, n in enumerate(narr):
        text = n["content_data"]["text"]
        if j == len(narr) - 1:
            if p.strip_style == "statement":
                fixed(strip(text, "Key message", p), _lines(text, 19, INNER - 52) * 26)
            else:
                fixed(strip(text, "Key message", p), 36 + _lines(text, 15, INNER - 170) * 21)
        else:
            fixed(insight(text, p), _lines(text, 16, INNER - 20) * 23)

    # 2. split the height: fixed blocks take what they need; growers share the rest by
    #    weight up to their cap (water-filling); slack left over becomes even spacing.
    fixed_h = sum(b[2] for b in blocks if b[0] == "fixed")
    gaps = GAP * (len(blocks) - 1)
    spare = max(120.0, body_h - fixed_h - gaps)
    growers = [i for i, b in enumerate(blocks) if b[0] == "grow"]
    # a grower first gets what its content measured at (fit.py), then shares the rest by weight
    alloc = {i: p.min_h.get(i, 0.0) for i in growers}
    open_ = {i for i in growers if alloc[i] < blocks[i][3]}
    left = max(0.0, spare - sum(alloc.values()))
    while open_ and left > 1:
        wsum = sum(blocks[i][2] for i in open_)
        step = {i: left * blocks[i][2] / wsum for i in open_}
        left = 0.0
        for i in list(open_):
            room = blocks[i][3] - alloc[i]
            if step[i] >= room:
                alloc[i] += room
                left += step[i] - room
                open_.discard(i)
            else:
                alloc[i] += step[i]
    slack = max(0.0, left)
    out = []
    for i, blk in enumerate(blocks):
        xml = blk[1] if blk[0] == "fixed" else blk[1](alloc[i], f' h="{round(alloc[i])}"')
        out.append(re.sub(r"^\s*<(\w+)", rf'<\1 id="blk-{i}"', xml, count=1))  # measured by fit.py
    p.block_kinds = [b[0] for b in blocks]
    out = [scale_type(o, p.scale) for o in out]
    # slack: widen the gaps (up to +32px) and centre what remains, never one empty band
    extra = min(32.0, slack / max(1, len(blocks) + 1))
    rest = slack - extra * max(0, len(blocks) - 1)
    # each centring spacer is a child of the gapped stack too: it costs one more gap
    pad_h = rest / 2 - (GAP + extra)
    pad = '<VStack h="%d" />' % round(pad_h) if pad_h > 8 else ""
    return pad + "".join(out) + pad, GAP + extra


def scale_type(xml: str, s: float) -> str:
    """Body type at scale s (two-pass fit): labels (<= 11px) keep their size, other text never
    below 11px, table rows never below 24px."""
    if s >= 0.999:
        return xml
    xml = re.sub(r'fontSize="(\d+(?:\.\d+)?)"',
                 lambda m: f'fontSize="{m.group(1) if float(m.group(1)) <= 11 else max(11, round(float(m.group(1)) * s))}"', xml)
    return re.sub(r'(<Tr\b[^>]*\bheight=")(\d+)"', lambda m: f'{m.group(1)}{max(24, round(int(m.group(2)) * s))}"', xml)


_PHRASE = re.compile(r"phrase\s+['\"‘“](.+?)['\"’”]")


def headline_runs(plan: dict, p: Pack) -> str:
    """two_tone: regular weight, the plan's emphasised phrase (title design_hint) in bold."""
    t = plan["slide_title"]
    if p.headline != "two_tone":
        return x(t)
    hint = " ".join(c.get("design_hint") or "" for c in plan["components"] if c["kind"] == "title")
    m = _PHRASE.search(hint)
    if m and m.group(1) in t:
        i = t.index(m.group(1))
        return x(t[:i]) + "<B>" + x(m.group(1)) + "</B>" + x(t[i + len(m.group(1)):])
    for sep in ("; ", " — ", ", "):
        if sep in t:
            a, b = t.rsplit(sep, 1)
            return x(a + sep) + "<B>" + x(b) + "</B>"
    w = t.split()
    return x(" ".join(w[:-3]) + " ") + "<B>" + x(" ".join(w[-3:])) + "</B>" if len(w) > 4 else "<B>" + x(t) + "</B>"


NOTE_FS = 11  # caption / source line above the footer


def captions(plan: dict, minor: bool = True) -> list[str]:
    """Caption texts to draw on a content slide: not empty, and not a repeat of the slide's
    kicker or headline (planners often put the label in a caption: "SEGMENT BREAKDOWN").
    minor=True: the planner's minor captions (source / footnote) -> the note line above the
    footer; minor=False: heavier captions (the planner's own weight; in saved plans these are
    full-sentence insights) -> insight lines in the body."""
    seen = {re.sub(r"\W+", " ", str(plan.get(k) or "")).strip().lower() for k in ("label", "slide_title")}
    out = []
    for c in plan["components"]:
        if c["kind"] != "caption" or ((c.get("weight") or "minor") == "minor") != minor:
            continue
        text = str((c.get("content_data") or {}).get("text") or "").strip()
        if text and re.sub(r"\W+", " ", text).strip().lower() not in seen:
            out.append(text)
    return out


def frame(plan: dict, deck: dict, p: Pack, n: int, total: int) -> str:
    bar = ('<HStack h="6"><Shape shapeType="rect" w="1" grow="1" h="6" fill.color="$dark" />'
           '<Shape shapeType="rect" w="180" h="6" fill.color="$accent2" /></HStack>') if p.top_bar else ""
    if p.badge == "number":
        badge = (f'<VStack w="26" h="26" backgroundColor="$accent2" justifyContent="center" alignItems="center">'
                 f'<Text fontSize="12" fontFamily="{p.mono}" bold="true" color="$ink">{n}</Text></VStack>')
    else:
        badge = f'<Shape shapeType="rect" w="7" h="7" fill.color="{"$accent2" if p.fills == "rhythm" else "$accent"}" />'
    ktext = (plan.get("label") or "") + (f" · {n:02d}" if p.kicker_number and plan.get("label") else "")
    label = p.label(ktext, "$muted" if p.fills == "rhythm" else "$accent") if plan.get("label") else ""
    running = p.label(deck["running"], "$muted", 9, ' textAlign="right"') if p.running else ""
    sub = (f'<Text margin.top="8" fontSize="14" fontFamily="{p.sans}" color="$muted" lineHeight="1.35">'
           f'{x(plan["subtitle"])}</Text>') if plan.get("subtitle") else ""
    rule = '<Shape margin.top="14" shapeType="rect" w="36" h="2" fill.color="$ink" />' if p.rule else ""
    # header heights from the real glyph widths (bold for the headline: two-tone mixes weights)
    lines = drawn_lines(plan["slide_title"], p.sans, p.t["headline"], p.head_max_w) or math.ceil(
        len(plan["slide_title"]) * p.t["headline"] * 0.56 / p.head_max_w)
    head_h = round(lines * p.t["headline"] * 1.15 + 6)
    sub_lines = (drawn_lines(plan["subtitle"], p.sans, 14, INNER, bold=False) or _lines(plan["subtitle"], 14, INNER)
                 ) if plan.get("subtitle") else 0
    sub_h = (8 + sub_lines * 19) if plan.get("subtitle") else 0
    notes = captions(plan)
    note_xml = "".join(f'<Text fontSize="{NOTE_FS}" fontFamily="{p.sans}" color="$muted" lineHeight="1.35">{x(t)}</Text>'
                       for t in notes)
    note_h = sum((drawn_lines(t, p.sans, NOTE_FS, INNER, bold=False) or _lines(t, NOTE_FS, INNER))
                 * NOTE_FS * 1.35 + 4 for t in notes)
    if notes:
        note_xml = f'<VStack margin.top="12" gap="4">{note_xml}</VStack>'
        note_h += 12
    body_h = (H - (6 if p.top_bar else 0) - 26 - 20 - 14 - 14 - head_h - sub_h - (16 if p.rule else 0)
              - 20 - 14 - 12 - note_h)
    body_xml, body_gap = compose_body(plan, p, body_h)
    return f'''<Slide>
  <VStack w="{W}" h="{H}" backgroundColor="$bg" alignItems="stretch">
    {bar}
    <VStack grow="1" padding.top="26" padding.bottom="20" padding.left="{PAD_X}" padding.right="{PAD_X}" alignItems="stretch">
      <HStack alignItems="center" justifyContent="spaceBetween">
        <HStack gap="10" alignItems="center">{badge}{label}</HStack>
        {running}
      </HStack>
      <VStack margin.top="14" h="{head_h}"><Text maxW="{p.head_max_w}" fontSize="{p.t["headline"]}" fontFamily="{p.sans}"{"" if p.headline == "two_tone" else ' bold="true"'} color="$ink" lineHeight="1.15">{headline_runs(plan, p)}</Text></VStack>
      {sub}{rule}
      <VStack margin.top="20" grow="1" gap="{round(body_gap)}" alignItems="stretch">{body_xml}</VStack>
      {note_xml}
      <HStack margin.top="14" alignItems="center" justifyContent="spaceBetween">
        {p.label(deck["brand"], "$ink" if p.fills == "rhythm" else "$muted", 9, ' bold="true"' if p.fills == "rhythm" else "")}
        {p.label(f"{n:02d} / {total:02d}", "$muted", 9, ' textAlign="right"')}
      </HStack>
    </VStack>
  </VStack>
</Slide>'''


def cover(plan: dict, deck: dict, p: Pack, total: int) -> str:
    # POM rejects an empty <Text>: a plan without a subtitle / caption drops that line
    return re.sub(r"\n?[ \t]*<Text[^>]*>\s*</Text>", "", _cover(plan, deck, p, total))


def _cover(plan: dict, deck: dict, p: Pack, total: int) -> str:
    comps = {c["kind"]: c for c in plan["components"]}
    caption = comps.get("caption", {}).get("content_data", {}).get("text", "")
    narrs = [c["content_data"].get("text", "") for c in plan["components"] if c["kind"] == "narrative"]
    # no planned subtitle (plans before batch A): the first narrative is the subtitle, the rest the key message
    if not plan.get("subtitle") and len(narrs) > 1:
        plan = dict(plan, subtitle=narrs[0])
        narrs = narrs[1:]
    narr = " ".join(t for t in narrs if t)
    title, brand = plan["slide_title"], deck["brand"]
    sub = plan.get("subtitle") or ""
    if p.fills == "rhythm":  # studio: dark hero, brand word italic lime in the title
        runs = x(title)
        if brand in title:
            i = title.index(brand)
            runs = x(title[:i]) + f'<I><Span color="$accent2">{x(brand)}</Span></I>' + x(title[i + len(brand):])
        msg = (f'<VStack w="380" gap="10" padding.left="18" borderLeft.color="$accent2" borderLeft.width="3">'
               f'{p.label("Key message", "$accent2")}<Text fontSize="15" fontFamily="{p.sans}" italic="true" color="$muted" '
               f'lineHeight="1.45">{x(narr)}</Text></VStack>') if narr else ""
        return f'''<Slide>
  <VStack w="{W}" h="{H}" padding="56" alignItems="stretch" backgroundGradient="radial-gradient(circle at 12% 8%, #26301A 0%, #0D0F0C 60%)">
    <HStack alignItems="center" justifyContent="spaceBetween">
      <HStack gap="10" alignItems="center"><Shape shapeType="rect" w="8" h="8" fill.color="$accent2" />{p.label(brand, "$ink", 12, ' bold="true"')}</HStack>
      {p.label(f"01 / {total:02d}", "$muted", 9, ' textAlign="right"')}
    </HStack>
    <VStack grow="1" />
    <HStack gap="48" alignItems="end">
      <VStack grow="1" gap="20">
        <Text fontSize="{p.t["cover"]}" fontFamily="{p.sans}" bold="true" color="$ink" lineHeight="1.08">{runs}</Text>
        <Text fontSize="16" fontFamily="{p.sans}" color="$muted" lineHeight="1.4">{x(sub)}</Text>
      </VStack>
      {msg}
    </HStack>
    <VStack grow="1" />
    <HStack gap="10" alignItems="center"><Shape shapeType="rect" w="28" h="2" fill.color="$accent2" />{p.label(caption or brand, "$muted", 9)}</HStack>
  </VStack>
</Slide>'''
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


def _dark_slide(plan: dict, p: Pack) -> bool:
    if plan.get("slide_type") == "cover":
        return p.fills == "rhythm"
    return "steps" in p.dark_slides and any(
        c["kind"] == "card_grid" and c["content_data"].get("card_layout") == "steps"
        and len(c["content_data"].get("cards", [])) >= 4 for c in plan["components"])


def render(plans_file: Path, out: Path, pack: str | None = None) -> list[Path]:
    data = json.loads(plans_file.read_text(encoding="utf-8"))
    deck, plans = data["deck"], data["slides"]
    p = Pack(pack or deck["pack"], deck.get("entities"))
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for i, plan in enumerate(plans):
        p.is_dark = _dark_slide(plan, p)
        body = cover(plan, deck, p, len(plans)) if plan.get("slide_type") == "cover" else frame(plan, deck, p, i + 1, len(plans))
        f = out / f"slide-{i + 1:02d}.xml"
        f.write_text(p.theme() + "\n<!-- fit-grow: off -->\n" + body + "\n", encoding="utf-8")
        written.append(f)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plans", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pack", help="style pack to use instead of the plans file's")
    a = ap.parse_args()
    for f in render(a.plans, a.out, a.pack):
        print(f)


if __name__ == "__main__":
    main()
