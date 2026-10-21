"""Grow fallback — make sure a slide's main content band takes the spare height.

POM gives spare height only to children with grow (or h). When the generator
leaves every band of a VStack root content-sized (a KPI row + callout slide, a
bullet card), the content stacks at the top and the lower half of the slide is
empty; fit-grow cannot fill it because no box is taller than its content.

This pass adds grow="1" to ONE band of the root VStack when none of its bands
grows: the band with a chart / diagram if any, else the largest card band
(KPI row, card grid, bullet card, callout). Header and caption lines (no card,
no data node) and fixed-height diagrams (Timeline, Pyramid) never get it. A
slide with a table is left alone: fit-grow grows the table's rows and text into
the spare height, and a growing sibling would take that space from the table.

It edits the XML text in place (one attribute inserted), like the normalizer.
"""

from __future__ import annotations

import re

_TAG_RE = re.compile(
    r"<!--.*?-->|<(?P<close>/?)(?P<name>[A-Za-z][\w.]*)(?P<attrs>(?:[^<>\"']|\"[^\"]*\"|'[^']*')*?)(?P<self>/?)>",
    re.S,
)
_FLEX_ATTR_RE = re.compile(r"\s(?:grow|h)\s*=")
_BG_ATTR_RE = re.compile(r"\s(?:backgroundColor|fill\.color)\s*=")

_FILLS = {"Chart", "Matrix", "Flow", "Tree", "ProcessArrow"}  # h="max" fills its card
_NEVER = {"Table", "Timeline", "Pyramid"}                       # size to rows / pixel h


class _Band:
    __slots__ = ("start", "open_end", "name", "attrs", "tags", "has_bg", "nodes")

    def __init__(self, start: int, open_end: int, name: str, attrs: str) -> None:
        self.start, self.open_end, self.name, self.attrs = start, open_end, name, attrs
        self.tags: set[str] = {name}
        self.has_bg = bool(_BG_ATTR_RE.search(attrs))
        self.nodes = 1


def _root_bands(xml: str) -> tuple[str | None, list[_Band]]:
    """Name of the slide's root stack and its direct children (with subtree facts)."""
    depth = 0
    root_name: str | None = None
    root_depth = -1
    bands: list[_Band] = []
    current: _Band | None = None
    for m in _TAG_RE.finditer(xml):
        name = m.group("name")
        if name is None:  # comment
            continue
        closing, selfclosing = bool(m.group("close")), bool(m.group("self"))
        if closing:
            depth -= 1
            if current is not None and depth == root_depth + 1:
                current = None
            continue
        if root_name is None and name in ("VStack", "HStack", "Layer"):
            root_name, root_depth = name, depth
        elif root_name is not None and depth == root_depth + 1:
            current = _Band(m.start(), m.end(), name, m.group("attrs"))
            bands.append(current)
        elif current is not None and depth > root_depth + 1:
            current.tags.add(name)
            current.nodes += 1
            if _BG_ATTR_RE.search(m.group("attrs")):
                current.has_bg = True
        if not selfclosing:
            depth += 1
        if current is not None and selfclosing and depth == root_depth + 1 and current.start == m.start():
            current = None
    return root_name, bands


def ensure_growing_band(xml: str) -> tuple[str, str | None]:
    """Return (xml, message). message is None when nothing changed."""
    root_name, bands = _root_bands(xml)
    if root_name != "VStack" or len(bands) < 2:
        return xml, None
    if any(_FLEX_ATTR_RE.search(b.attrs) for b in bands):
        return xml, None
    if any("Table" in b.tags for b in bands):
        return xml, None
    candidates = [
        b for b in bands
        if not (b.tags & _NEVER) and (b.tags & _FILLS or b.has_bg or "Ul" in b.tags or "Ol" in b.tags)
    ]
    if not candidates:
        return xml, None
    with_fill = [b for b in candidates if b.tags & _FILLS]
    pick = with_fill[0] if with_fill else max(candidates, key=lambda b: b.nodes)
    tag_open = xml[pick.start:pick.open_end]
    insert_at = pick.start + 1 + len(pick.name)
    xml = xml[:insert_at] + ' grow="1"' + xml[insert_at:]
    what = "chart/diagram" if with_fill else f"{pick.nodes}-node {pick.name}"
    return xml, (f'No band of the root VStack grew; gave grow="1" to the main content band '
                 f"({what}) so it takes the spare height. Opening tag was: {tag_open[:80]}")


# ── rows of cards share their band's height ─────────────────────────────────
# XTSY layout-batch run: the card grid's band had grow="2" but its two card rows
# had none, so the rows kept their content height and the band's lower half stayed
# empty. A growing VStack whose children are all HStack rows, none flexible, gives
# each row grow="1" (the recipe's own shape).

def _elements(xml: str) -> list[dict]:
    """Every element as {name, attrs, start, open_end, children}, in document order."""
    stack: list[dict] = []
    out: list[dict] = []
    for m in _TAG_RE.finditer(xml):
        name = m.group("name")
        if name is None:
            continue
        if m.group("close"):
            if stack:
                stack.pop()["end"] = m.end()
            continue
        el = {"name": name, "attrs": m.group("attrs"), "start": m.start(), "open_end": m.end(), "children": [],
              "end": m.end()}
        if stack:
            stack[-1]["children"].append(el)
        out.append(el)
        if not m.group("self"):
            stack.append(el)
    return out


def share_row_height(xml: str) -> tuple[str, str | None]:
    """Return (xml, message); message is None when nothing changed."""
    inserts: list[int] = []
    for el in _elements(xml):
        if el["name"] != "VStack" or not _FLEX_ATTR_RE.search(el["attrs"]):
            continue
        rows = el["children"]
        if len(rows) < 2 or any(r["name"] != "HStack" or _FLEX_ATTR_RE.search(r["attrs"]) for r in rows):
            continue
        inserts.extend(r["start"] + 1 + len("HStack") for r in rows)
    if not inserts:
        return xml, None
    for at in sorted(inserts, reverse=True):
        xml = xml[:at] + ' grow="1"' + xml[at:]
    return xml, (f'Gave grow="1" to {len(inserts)} card row(s) of a growing band so the rows '
                 "share its height (none of them grew).")


# A growing band whose ONLY child is a card (no grow / h) leaves the card at content height:
# the QBR revenue chart sat in a <VStack grow="3"> but its card did not grow, so the chart stayed
# at minH 180 with the lower 40% of the slide empty (2026-10-08). The lone card takes the band.

def _subtree_names(el: dict) -> set[str]:
    names = {el["name"]}
    for c in el["children"]:
        names |= _subtree_names(c)
    return names


def fill_lone_child(xml: str) -> tuple[str, str | None]:
    """Return (xml, message); message is None when nothing changed."""
    inserts: list[int] = []
    for el in _elements(xml):
        if el["name"] != "VStack" or not _FLEX_ATTR_RE.search(el["attrs"]) or len(el["children"]) != 1:
            continue
        child = el["children"][0]
        if child["name"] not in ("VStack", "HStack") or _FLEX_ATTR_RE.search(child["attrs"]):
            continue
        if not (_BG_ATTR_RE.search(child["attrs"]) or _subtree_names(child) & _FILLS):
            continue
        inserts.append(child["start"] + 1 + len(child["name"]))
    if not inserts:
        return xml, None
    for at in sorted(inserts, reverse=True):
        xml = xml[:at] + ' grow="1"' + xml[at:]
    return xml, f'Gave grow="1" to {len(inserts)} card(s) that were the only child of a growing band.'


# ── a long text box in w="max" must not squeeze its row ─────────────────────
# POM gives an HStack child w="max" flexGrow 1 with an AUTO basis: its text's one-line width. A sibling with no
# w gets basis 0 (llm.md: w="max" "behaves as grow=1"). So a box of a long sentence in w="max" takes almost the
# whole row and its neighbour keeps a sliver: tile same-plan pair 1.4 (CHEFFIN 1, one 110-character bullet beside
# two KPI tiles: 1015 of 1184 px, the tiles drawn letter by letter), paid check 3 CHEFFIN 1 ×3 (a 170-character
# callout beside the tiles' own w="max" panel: zero width, compile error). Such a box gets grow="1" instead
# (basis 0: it shares the row's spare width with its siblings by grow, as the docs say) when a sibling holds KPI
# tiles or cards: their numbers and words cannot wrap. Beside other text it stays: a w="max" checklist beside a
# grow="2" quote keeps its content width (as grow="1" it took a third of the row: 10 broken words, agency 2).

_LONG_TEXT = 60          # characters: ~500 px at 16 px Inter, past a fair share of a two-box row
_RIGID = {"Table", "Chart", "Image", "Matrix", "Flow", "Tree", "ProcessArrow", "Timeline", "Pyramid"}
_W_MAX_RE = re.compile(r"\sw\s*=\s*\"max\"")
_TILE_ID_RE = re.compile(r"\sid\s*=\s*\"(?:kpi[vhg]\d?-|card-)")
_GROW_RE = re.compile(r"\sgrow\s*=")


def _text_len(xml: str, el: dict) -> int:
    return len(" ".join(re.sub(r"<[^>]*>", " ", xml[el["open_end"]:el["end"]]).split()))


def unsqueeze_text_boxes(xml: str) -> tuple[str, str | None]:
    """Return (xml, message); message is None when nothing changed."""
    edits: list[tuple[int, int]] = []
    for el in _elements(xml):
        if el["name"] != "HStack" or len(el["children"]) < 2:
            continue
        tiles = [c for c in el["children"] if _TILE_ID_RE.search(xml[c["start"]:c["end"]])]
        for c in el["children"]:
            if not [t for t in tiles if t is not c]:
                continue
            m = _W_MAX_RE.search(c["attrs"])
            if c["name"] not in ("VStack", "HStack", "Text", "Ul", "Ol") or not m or _GROW_RE.search(c["attrs"]):
                continue
            if _subtree_names(c) & _RIGID or _text_len(xml, c) < _LONG_TEXT:
                continue
            at = c["start"] + 1 + len(c["name"]) + m.start()
            edits.append((at, at + len(m.group(0))))
    if not edits:
        return xml, None
    for a, b in sorted(edits, reverse=True):
        xml = xml[:a] + ' grow="1"' + xml[b:]
    return xml, (f'Gave grow="1" instead of w="max" to {len(edits)} box(es) of long text in a row, so they share '
                 "the row's width instead of taking their one-line width.")


# ── a short symbol between w="max" boxes must not be squeezed to zero ───────
# XTSY 4 (gpt-6.1-sol, 2026-10-21): four w="max" phase cards with a "→" <Text> between each pair. The cards'
# basis is their text's one-line width, the arrows' basis 0, so the arrows got 0 px and POM threw "addTextBox: width
# must be a finite positive EMU value". The repairer then pinned the cards and set the row to alignItems="start"
# (unequal card heights). A short symbol Text (≤ 3 characters: arrows, "+", "·", "vs") with no w / grow in a row
# that has a w="max" child gets a width from its font size (1.2 em), so it can never be squeezed out. A wrapping row
# (flexWrap="wrap") is left alone: its children wrap instead of shrinking, and wider arrows pushed the last card of
# gpt-5-mini's XTSY 4 onto a second row in the replay.

_SYMBOL_MAX = 3
_W_RE = re.compile(r"\s(?:w|grow)\s*=")
_FONT_RE = re.compile(r"\sfontSize\s*=\s*\"(\d+(?:\.\d+)?)\"")
_WRAP_RE = re.compile(r"\sflexWrap\s*=\s*\"wrap\"")


def size_row_symbols(xml: str) -> tuple[str, str | None]:
    """Return (xml, message); message is None when nothing changed."""
    edits: list[tuple[int, str]] = []
    for el in _elements(xml):
        if el["name"] != "HStack" or _WRAP_RE.search(el["attrs"]):
            continue
        if not any(_W_MAX_RE.search(c["attrs"]) for c in el["children"]):
            continue
        for c in el["children"]:
            if c["name"] != "Text" or c["children"] or _W_RE.search(c["attrs"]):
                continue
            text = _text_len(xml, c)
            if not 0 < text <= _SYMBOL_MAX:
                continue
            m = _FONT_RE.search(c["attrs"])
            w = max(16, round(float(m.group(1)) * 1.2)) if m else 22
            edits.append((c["start"] + 1 + len("Text"), f' w="{w}"'))
    if not edits:
        return xml, None
    for at, ins in sorted(edits, reverse=True):
        xml = xml[:at] + ins + xml[at:]
    return xml, (f"Gave {len(edits)} short symbol text(s) between w=\"max\" boxes a width from their font size, so "
                 "the boxes beside them cannot squeeze them to zero width.")


# ── peer cards in one row share one height ──────────────────────────────────
# Rule K6 (peers look alike, presentation-rules-draft 2026-10-15): cards of the same kind side by side are one
# size. With alignItems="start" / "center" / "end" on the row every card is as tall as its own text, so the card with
# the longest text stands out (XTSY 4 after the repair above, 2026-10-21). A row whose boxed children (VStack /
# HStack with a fill or border) number ≥ 2, share one structure (same attribute names and the same padding /
# borderRadius; fills may differ, e.g. one focus card) and set no h / minH gets alignItems="stretch". Its other
# children (arrows, icons) keep their old position through alignSelf.

_ALIGN_RE = re.compile(r"\salignItems\s*=\s*\"(start|center|end)\"")
_HEIGHT_RE = re.compile(r"\s(?:h|minH|maxH)\s*=")
_BOX_RE = re.compile(r"\s(?:backgroundColor|border\.color|border\.width|borderLeft\.color|borderTop\.color)\s*=")
_ALIGNSELF_RE = re.compile(r"\salignSelf\s*=")
_ATTR_RE = re.compile(r"([\w.]+)\s*=\s*\"([^\"]*)\"")
_SHAPE_KEYS = ("padding", "borderRadius")
_IGNORED = {"w", "h", "grow", "id", "alignSelf", "minW", "maxW", "minH", "maxH", "backgroundColor",
            "border.color", "borderLeft.color", "borderTop.color", "shadow.color"}


def _signature(attrs: str) -> tuple:
    kv = dict(_ATTR_RE.findall(attrs))
    return (frozenset(k for k in kv if k not in _IGNORED), tuple(kv.get(k) for k in _SHAPE_KEYS))


def stretch_peer_cards(xml: str) -> tuple[str, str | None]:
    """Return (xml, message); message is None when nothing changed."""
    edits: list[tuple[int, int, str]] = []
    rows = 0
    for el in _elements(xml):
        if el["name"] != "HStack":
            continue
        m = _ALIGN_RE.search(el["attrs"])
        if not m:
            continue
        boxes = [c for c in el["children"] if c["name"] in ("VStack", "HStack") and _BOX_RE.search(c["attrs"])]
        if len(boxes) < 2 or any(_HEIGHT_RE.search(b["attrs"]) or _ALIGNSELF_RE.search(b["attrs"]) for b in boxes):
            continue
        if len({_signature(b["attrs"]) for b in boxes}) != 1:
            continue
        at = el["start"] + 1 + len("HStack") + m.start()
        edits.append((at, at + len(m.group(0)), ' alignItems="stretch"'))
        for c in el["children"]:
            if c in boxes or _ALIGNSELF_RE.search(c["attrs"]):
                continue
            pos = c["start"] + 1 + len(c["name"])
            edits.append((pos, pos, f' alignSelf="{m.group(1)}"'))
        rows += 1
    if not edits:
        return xml, None
    for a, b, ins in sorted(edits, reverse=True):
        xml = xml[:a] + ins + xml[b:]
    return xml, (f'Set alignItems="stretch" on {rows} row(s) of same-styled cards so the cards share one height '
                 "(peers look alike); their other children keep their place.")
