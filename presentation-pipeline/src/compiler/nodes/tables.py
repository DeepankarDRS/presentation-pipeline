"""Table composition node (composition spec §8, approved 2026-10-27), `POM_NODES=table`.

The LLM writes one self-closing tag per table component; code draws it from the plan:

    <Table ref="gaps" variant="rows numbered" grow="1" stripe.backgroundColor="$surfaceAlt"/>

Compositions (block-variants.yaml `nodes.table`; the sheet docs/eval/composition-left/table.png is what they draw):
- `native` (default): POM's Table. Code writes every part onto the <Td>s, since POM ignores attributes on <Tr> (C1,
  C2): `header.` (the header row), `label.` (the first column), `cell.` (the other cells), `stripe.` (alternate body
  rows: `zebra`), `item.backgroundColor` (every body cell). The table carries an id (tbl-<cid>) and no
  cell fontSize, so fit-grow sizes it from its text (14 px cells, column widths, rows) and, as the slide's main table,
  grows its text and rows into spare height, further than an LLM table (NODE_TABLE_CAPS).
- `rows` / `rows numbered`: one ruled row per table row: [01] · the first cell as its title · the other cells; the
  column names as small labels on top.
- `columns` (≤ 5 rows, ≤ 6 columns): one column per row, its first cell as a `band.` pill, each other cell in its own
  box (`item.`) under its column name.
- `banded` (≤ 6 rows): equal boxes, the first cell in a solid `band.` over "column: value" lines.

Code owns every word (verbatim, plan order), the numbers and the emphasis: the one row or column the design hint
names, in the hint's tone ($tone / $toneSoft / $toneText -> positive, negative, warning; else accent). A row takes
every emphasis part; a column takes `header.` / `cell.` / `item.` on its own cells. The LLM owns the box (layout and
box attributes on the tag: the Table's own box on `native`) and part styles, in $tokens only.
"""

from __future__ import annotations

import re
from typing import Any

from src.compiler.nodes import compose, native, spec

SEVERITY = compose.SEVERITY
TAG = "Table"
ON_NATIVE_ITEM = {"backgroundColor"}   # what a native table takes of `item.` (spec §2.4, C1)
_ROW_WORD = re.compile(r"^\W{0,3}row\b", re.I)
_COL_WORD = re.compile(r"^\W{0,3}col(?:umn)?\b", re.I)
_ROWS_WORD = re.compile(r"^\W{0,3}rows\b", re.I)            # "the A and B rows": a list, no one row
_COLS_WORD = re.compile(r"^\W{0,3}col(?:umn)?s\b", re.I)


def on() -> bool:
    return spec.nodes_on("table")


def node() -> dict[str, Any]:
    return spec.nodes()["table"]


def components(plan: dict | None) -> dict[str, dict]:
    return {c["component_id"]: c for c in (plan or {}).get("components") or []
            if c.get("kind") == "table" and c.get("component_id")}


def grid(comp: dict) -> tuple[list[str], list[list[str]]]:
    """(column names, rows), every row as wide as the widest (missing cells "")."""
    cd = comp.get("content_data") or {}
    cols = [str(c) for c in cd.get("table_columns") or []]
    rows = [[str(c) for c in r] for r in cd.get("table_rows") or [] if r]
    n = max([len(cols)] + [len(r) for r in rows])
    return cols + [""] * (n - len(cols)), [r + [""] * (n - len(r)) for r in rows]


def _named(names: list[str], hint: str, word: re.Pattern | None) -> list[int]:
    """The items the hint names (as plan_checks._hint_names: the label, its part before " (" / " for ", an
    upper-case token only it has), followed by `word` ("row" / "column") when given."""
    from src.agents.plan_checks import _hint_names   # src.agents imports the validator, which imports this
    out = []
    for i, ns in enumerate(_hint_names(names)):
        if any(word is None or word.match(hint[m.end():])
               for nm in ns if nm.strip() for m in re.finditer(rf"(?<!\w){re.escape(nm)}(?!\w)", hint, re.I)):
            out.append(i)
    return out


def emphasis(comp: dict) -> tuple[str, int] | None:
    """("row", r) / ("col", c): the one row (by its first cell) or column (not the first) the design hint names.
    A row wins when it is the only row named and is called a row, or no column is ("emphasise Chennai ROI");
    else the one column called a column ("accent the Fix column"); else, with no row named, the one column named.
    A name before a plural ("the Spend and ROAS columns") makes its axis a list: no emphasis on it."""
    hint = " ".join(str(comp.get("design_hint") or "").split())
    cols, rows = grid(comp)
    if not hint or not rows:
        return None
    labels, heads = [r[0] for r in rows], cols[1:]
    r_any, r_word = _named(labels, hint, None), _named(labels, hint, _ROW_WORD)
    c_any, c_word = _named(heads, hint, None), _named(heads, hint, _COL_WORD)
    if _named(labels, hint, _ROWS_WORD):
        r_any = r_any * 2
    if _named(heads, hint, _COLS_WORD):
        c_any, c_word = c_any * 2, c_word * 2
    if len(r_any) == 1 and (r_word or not c_word):
        return "row", r_any[0]
    if len(c_word) == 1:
        return "col", c_word[0] + 1
    if not r_any and len(c_any) == 1:
        return "col", c_any[0] + 1
    return None


def role(comp: dict, focus: tuple[str, int] | None) -> str:
    """The emphasis item's tone from the hint (plan_checks.tones_from_hint over the rows or columns): its palette
    role, accent when the hint gives none."""
    if focus is None:
        return "accent"
    from src.agents.plan_checks import tones_from_hint
    cols, rows = grid(comp)
    names = [r[0] for r in rows] if focus[0] == "row" else cols
    tones = tones_from_hint({"design_hint": comp.get("design_hint"),
                             "content_data": {"kpi_labels": names, "kpi_values": names}})
    return compose.TONE_ROLE.get(tones[focus[1]], "accent") if focus[1] < len(tones) and tones[focus[1]] else "accent"


# ── compositions ──────────────────────────────────────────────────────────────

T = compose.text
A = compose.a


class Pick:
    """Which parts a cell, a row or a column name takes: the emphasis parts on the emphasis row (all of them) or
    column (its header / cells / cell boxes), else the rest."""

    def __init__(self, rest: dict, hi: dict, focus: tuple[str, int] | None):
        self.rest, self.hi, self.focus = rest, hi, focus

    def row(self, r: int) -> dict:
        return self.hi if self.focus == ("row", r) else self.rest

    def col(self, i: int) -> dict:
        return self.hi if self.focus == ("col", i) else self.rest

    def cell(self, r: int, i: int) -> dict:
        return self.hi if self.focus in (("row", r), ("col", i)) else self.rest


def draw_native(comp: dict, box: dict, pick: Pick) -> str:
    # every cell left-aligned (textAlign is the LLM's, `cell.textAlign`): POM writes 0 cell margins, so a right-aligned
    # number touches the next column's text (replay 2026-10-28: text overlaps 31 -> 56 with numbers right-aligned)
    cols, rows = grid(comp)

    def td(v: str, at: dict, i: int) -> str:
        return f"<Td{A(at)}>{native.x(v)}</Td>"

    out = [f'<Table id="tbl-{comp["component_id"]}"{A({"w": "max", **box})}>' + "<Col />" * len(cols)]
    if any(c.strip() for c in cols):
        out.append("<Tr>" + "".join(td(h, pick.col(i)["header"], i) for i, h in enumerate(cols)) + "</Tr>")
    for r, row in enumerate(rows):
        cells = []
        for i, v in enumerate(row):
            p, rest = pick.cell(r, i), pick.rest
            part = "label" if i == 0 else "cell"
            at = {**rest[part], **{k: v2 for k, v2 in rest["item"].items() if k in ON_NATIVE_ITEM},
                  **(rest["stripe"] if r % 2 else {})}
            if p is not rest:
                at.update(p[part])
            cells.append(td(v, at, i))
        out.append("<Tr>" + "".join(cells) + "</Tr>")
    return "".join(out) + "</Table>"


def draw_rows(comp: dict, box: dict, pick: Pick, numbered: bool) -> str:
    cid, (cols, rows) = comp["component_id"], grid(comp)
    lead = '<VStack w="72" />' if numbered else ""
    lab = lambda i: T(cols[i].upper(), 13, pick.col(i)["header"], bold="true", letterSpacing="1")  # noqa: E731
    head = (f'<HStack gap="20">{lead}<VStack w="24%">{lab(0)}</VStack>'
            + "".join(f'<VStack w="1" grow="1">{lab(i)}</VStack>' for i in range(1, len(cols))) + "</HStack>") \
        if any(c.strip() for c in cols) else ""
    body = []
    for r, row in enumerate(rows):
        p = pick.row(r)
        item = {k: v for k, v in p["item"].items() if r or not k.startswith("borderTop")}   # no rule above the first
        num = f'<VStack w="72">{T(f"{r + 1:02d}", 30, p["number"], bold="true")}</VStack>' if numbered else ""
        cells = "".join(f'<VStack w="1" grow="1">{T(v, 18, pick.cell(r, i)["cell"])}</VStack>'
                        for i, v in enumerate(row) if i)
        body.append(f'<HStack id="card-{cid}-{r}" grow="1" gap="20" alignItems="center" padding="10"{A(item)}>'
                    f'{num}<VStack w="24%">{T(row[0], 22, p["label"], bold="true")}</VStack>{cells}</HStack>')
    return f'<VStack gap="8"{A(box)}>{head}<VStack gap="0" grow="1">{"".join(body)}</VStack></VStack>'


def draw_columns(comp: dict, box: dict, pick: Pick) -> str:
    cid, (cols, rows) = comp["component_id"], grid(comp)
    out = []
    for r, row in enumerate(rows):
        p = pick.row(r)
        pill = (f'<HStack padding="14" justifyContent="center"{A({"borderRadius": "24", **p["band"]})}>'
                f'{T(row[0], 19, p["label"], bold="true", textAlign="center")}</HStack>')
        boxes = "".join(f'<VStack grow="1" gap="4" padding="14" justifyContent="center"{A(pick.cell(r, i)["item"])}>'
                        + (T(cols[i].upper(), 12, pick.cell(r, i)["header"], bold="true", letterSpacing="1") if cols[i].strip() else "")
                        + f'{T(v, 17, pick.cell(r, i)["cell"])}</VStack>' for i, v in enumerate(row) if i)
        out.append(f'<VStack id="card-{cid}-{r}" w="1" grow="1" gap="10" alignItems="stretch">{pill}{boxes}</VStack>')
    return f'<HStack gap="16" alignItems="stretch"{A(box)}>{"".join(out)}</HStack>'


def per_line(n: int) -> int:
    """Boxes per line in `banded`: 2 for 2 and 4, else up to 3 (5 -> 3 + 2, 6 -> 3 + 3)."""
    return 2 if n in (2, 4) else min(n, 3)


def draw_banded(comp: dict, box: dict, pick: Pick) -> str:
    cid, (cols, rows) = comp["component_id"], grid(comp)
    boxes = []
    for r, row in enumerate(rows):
        p = pick.row(r)
        lines = "".join(
            f'<HStack gap="12" alignItems="start"><VStack w="34%">{T(cols[i], 15, pick.cell(r, i)["header"], bold="true")}</VStack>'
            f'<VStack w="1" grow="1">{T(v, 17, pick.cell(r, i)["cell"])}</VStack></HStack>'
            for i, v in enumerate(row) if i)
        item = {k: v for k, v in p["item"].items() if k != "backgroundColor"}
        boxes.append(f'<VStack id="card-{cid}-{r}" w="1" grow="1" gap="0"{A(item)}>'
                     f'<HStack padding="14"{A(p["band"])}>{T(row[0], 20, p["label"], bold="true")}</HStack>'
                     f'<VStack grow="1" gap="10" padding="18"{A({"backgroundColor": p["item"].get("backgroundColor", "$surfaceAlt")})}>'
                     f'{lines}</VStack></VStack>')
    k = per_line(len(boxes))
    return (f'<VStack gap="16"{A(box)}>' + "".join(f'<HStack gap="16" grow="1" alignItems="stretch">{"".join(boxes[j:j + k])}</HStack>'
                                                  for j in range(0, len(boxes), k)) + "</VStack>")


LABEL_W = "22%"   # the first column of a grid / ledger


def _boxed(p: dict) -> tuple[dict, dict]:
    """A Cell part drawn as a box around its Text: (box attributes, text attributes); backgroundColor goes on the box."""
    return {k: v for k, v in p.items() if k == "backgroundColor"}, {k: v for k, v in p.items() if k != "backgroundColor"}


def draw_grid(comp: dict, box: dict, pick: Pick, numbered: bool, inside: bool) -> str:
    """grid (numbered): the table's rows and columns kept, every cell its own card (`item.`). The header row is
    pills (`header.`) over the columns; `labels="inside"` drops it and writes each column name in its cards instead.
    numbered: a solid tile (`band.` box, `number.` text) leads each row. Headings (card-<cid>.th-<i>), first-column
    boxes (card-<cid>.tl-<r>) and cells (card-<cid>.tc-<k>) are three fit-grow peer groups (in one group the bold label
    read as each row's title and held the cells to title / 1.3), each evened to one size after the word guard
    (fit-grow evenTableParts)."""
    cid, (cols, rows) = comp["component_id"], grid(comp)
    lead = '<VStack w="64" />' if numbered else ""

    def heading(i: int, p: dict, px: int = 16) -> str:
        hb, ht = _boxed(p["header"])
        return (f'<HStack id="card-{cid}.th-{i}" padding="10" borderRadius="6"{A(hb)}>{T(cols[i], px, ht, bold="true")}</HStack>'
                if hb else f'<VStack id="card-{cid}.th-{i}">{T(cols[i].upper(), 13, ht, bold="true", letterSpacing="1")}</VStack>')

    def caps(i: int, p: dict) -> str:   # a column name written inside a card (labels="inside")
        ht = {k: v for k, v in p["header"].items() if k != "backgroundColor"}
        return T(cols[i].upper(), 12, ht, bold="true", letterSpacing="1") if inside and cols[i].strip() else ""

    head = "" if inside or not any(c.strip() for c in cols) else (
        f'<HStack gap="10" alignItems="end">{lead}<VStack w="{LABEL_W}">{heading(0, pick.col(0))}</VStack>'
        + "".join(f'<VStack w="1" grow="1">{heading(i, pick.col(i))}</VStack>' for i in range(1, len(cols))) + "</HStack>")
    body = []
    for r, row in enumerate(rows):
        p = pick.row(r)
        lb, lt = _boxed(p["label"])
        tile = ""
        if numbered:
            tile = (f'<VStack w="64" justifyContent="center" alignItems="center" borderRadius="8"{A(p["band"])}>'
                    f'{T(f"{r + 1:02d}", 22, p["number"], bold="true")}</VStack>')
        label = (f'<VStack id="card-{cid}.tl-{r}" w="{LABEL_W}" gap="4" padding="14" justifyContent="center" borderRadius="8"{A(lb)}>'
                 f'{caps(0, p)}{T(row[0], 19, lt, bold="true")}</VStack>')
        cells = "".join(f'<VStack id="card-{cid}.tc-{r * len(cols) + i}" w="1" grow="1" gap="4" padding="14" justifyContent="center"{A(pick.cell(r, i)["item"])}>'
                        f'{caps(i, pick.cell(r, i))}{T(v, 17, pick.cell(r, i)["cell"])}</VStack>'
                        for i, v in enumerate(row) if i)
        body.append(f'<HStack grow="1" gap="10" alignItems="stretch">{tile}{label}{cells}</HStack>')
    return f'<VStack gap="10"{A(box)}>{head}{"".join(body)}</VStack>'


def draw_ledger(comp: dict, box: dict, pick: Pick, icons: list[str]) -> str:
    """ledger: one solid header band (an icon over each column name, from the tag's `icons`) over joined rows;
    alternate rows take `stripe.`, every cell `item.` under it."""
    cid, (cols, rows) = comp["component_id"], grid(comp)

    def heading(i: int) -> str:
        hb, ht = _boxed(pick.col(i)["header"])
        icon = (f'<Icon name="{native.x(icons[i])}" size="26"{A({"color": ht.get("color", "$onAccent")})} />'
                if i < len(icons) and icons[i] else "")
        size = {"w": LABEL_W} if i == 0 else {"w": "1", "grow": "1"}
        return (f'<VStack id="card-{cid}.th-{i}"{A(size)} padding="12" gap="6" '
                f'justifyContent="end" alignItems="{"start" if i == 0 else "center"}"{A(hb)}>{icon}'
                f'{T(cols[i], 15, ht, bold="true", textAlign="left" if i == 0 else "center")}</VStack>')

    head = (f'<HStack gap="0" alignItems="stretch">{"".join(heading(i) for i in range(len(cols)))}</HStack>'
            if any(c.strip() for c in cols) else "")
    body = []
    for r, row in enumerate(rows):
        def cell_box(i: int) -> dict:
            p = pick.cell(r, i)
            base = {**pick.rest["item"], **(pick.rest["stripe"] if r % 2 else {})}
            return {**base, **p["item"]} if p is not pick.rest else base
        lb, lt = _boxed(pick.row(r)["label"])
        cells = "".join(f'<VStack id="card-{cid}.tc-{r * len(cols) + i}" w="1" grow="1" padding="14" justifyContent="center"{A(cell_box(i))}>'
                        f'{T(v, 17, pick.cell(r, i)["cell"])}</VStack>' for i, v in enumerate(row) if i)
        body.append(f'<HStack grow="1" gap="0" alignItems="stretch">'
                    f'<VStack id="card-{cid}.tl-{r}" w="{LABEL_W}" padding="14" justifyContent="center"{A({**cell_box(0), **lb})}>'
                    f'{T(row[0], 18, lt, bold="true")}</VStack>{cells}</HStack>')
    return f'<VStack gap="4"{A(box)}>{head}{"".join(body)}</VStack>'


def _toned(parts: dict[str, dict], role: str) -> dict[str, dict]:
    """$tone / $toneSoft / $toneText in every part -> the role's tokens (compose.tone_value)."""
    return {p: {k: compose.tone_value(v, role) for k, v in at.items()} for p, at in parts.items()}


def draw(comp: dict, attrs: dict[str, str], flag) -> tuple[str, dict]:
    """One <Table ref> tag -> its XML, and what was drawn."""
    ref, nd = comp["component_id"], node()
    meta, box, parts = compose.read(attrs, ref, flag, nd)
    name, extra = compose.composition(nd, comp, meta.get("variant"), ref, flag)
    for k, v in extra.items():   # an alias's part attributes (zebra, dark_header), under the LLM's own
        head, _, sub = k.partition(".")
        if head in parts and sub:
            parts[head].setdefault(sub, str(v))
    if name == "native":
        for k in [k for k in parts["item"] if k not in ON_NATIVE_ITEM]:
            flag("NODE_ATTR_DROPPED", ref, f'item.{k} on <Table ref="{ref}">: a native table cell takes only '
                 'item.backgroundColor; removed (C1).')
            del parts["item"][k]
    focus = emphasis(comp)
    box, rest, hi = compose.layers(nd, name, box, parts, focus is not None)
    rest, hi = _toned(rest, "accent"), _toned(hi, role(comp, focus))
    box = {k: compose.tone_value(v, "accent") for k, v in box.items()}
    if name != "native" and not ({"h", "grow"} & set(box)):
        box["grow"] = "1"   # a native table sizes to its rows: fit-grow sets its columns, then grows it into spare height
    inside = meta.get("labels") == "inside" and name.startswith("grid")
    if inside:   # column names inside the cards: a pill's ink would vanish on a card, so caps text unless the LLM set it
        for p, tone in ((rest, "$textMuted"), (hi, compose.tone_value("$toneText", role(comp, focus)))):
            p["header"] = {k: v for k, v in p["header"].items() if k != "backgroundColor"}
            if "color" not in parts["header"]:
                p["header"]["color"] = tone
    pick = Pick(rest, hi, focus)
    icons = [s.strip() for s in str(meta.get("icons") or "").split(",")]
    xml = (draw_native(comp, box, pick) if name == "native" else
           draw_rows(comp, box, pick, name == "rows numbered") if name.startswith("rows") else
           draw_grid(comp, box, pick, name == "grid numbered", inside) if name.startswith("grid") else
           draw_ledger(comp, box, pick, icons) if name == "ledger" else
           draw_columns(comp, box, pick) if name == "columns" else draw_banded(comp, box, pick))
    return xml, {"composition": name, "focus": focus}


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <Table ref="<table component id>"/> drawn from the plan (compose.expand)."""
    def check(comp: dict, flag) -> bool:
        if grid(comp)[1]:
            return True
        flag("NODE_ITEM_MISSING", comp["component_id"], f'table "{comp["component_id"]}" has no rows in the plan.')
        return False

    return compose.expand(xml, components(plan), TAG, draw, check)


# ── prompt ─────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines (the cached part of the system prompt)."""
    vs = spec.blocks()["table"]["variants"]
    styles = "; ".join(f"{n}: {st}" for n, st in (node().get("styles") or {}).items())
    return "\n".join([
        "## TABLES (code draws them from the plan)",
        f'<{TAG} ref="<table id>" variant="..."/>: ' + "; ".join(f"{n} ({v['prompt']})" for n, v in vs.items()) + ".",
        "Self-closing: code writes every cell, the numbers and the emphasis (the row or column the plan's hint names). "
        "Layout (w, h, grow) and box attributes style the table's own box; parts header. (column names) label. (first "
        "column) cell. (other cells) stripe. (alternate rows) take backgroundColor color bold italic textAlign in "
        "$tokens; item. / band. / number. on the drawn compositions. No <Tr>, <Td> or fontSize. "
        f"Recipes: {styles}.",
    ])


def tag_attributes() -> list[str]:
    from src.compiler.nodes import tiles
    nd = node()
    box = [a.split(".")[0] + ".*" if "." in a else a for a in tiles.data()["box_attributes"]]
    return list(dict.fromkeys(nd["meta"] + [f"{p}.*" for p in nd["parts"]] + ["cellBorder.*", "borderRadius"] + box))


def prompt_line(comp: dict, headline: str = "") -> str:
    cid, (cols, rows) = comp["component_id"], grid(comp)
    f = emphasis(comp)
    ok = [n for n, v in node()["compositions"].items() if not spec.failed_requires(v, comp)]
    longest = max((len(c) for r in rows for c in r), default=0)
    em = (f"emphasis row {rows[f[1]][0]!r}" if f[0] == "row" else f"emphasis column {cols[f[1]]!r}") if f else "no emphasis"
    parts = [f"TABLE {cid}: {len(rows)} rows x {len(cols)} columns", f"longest cell {longest} chars", em,
             "variants " + " | ".join(ok)]
    return "; ".join(parts) + f'. <{TAG} ref="{cid}"/>; never type a cell yourself: code writes them from the plan'
