"""Table composition node (composition spec §8, approved 2026-10-27), `POM_NODES=table`.

The LLM writes one self-closing tag per table component; code draws it from the plan:

    <Table ref="gaps" variant="ledger" grow="1" stripe.backgroundColor="$surfaceAlt"/>

Compositions (block-variants.yaml `nodes.table`; the sheet docs/eval/composition-left/table.png is what they draw):
- `native` (default): POM's Table. Code writes every part onto the <Td>s, since POM ignores attributes on <Tr> (C1,
  C2): `header.` (the header row), `label.` (the first column), `cell.` (the other cells), `stripe.` (alternate body
  rows: `zebra`), `item.backgroundColor` (every body cell). The table carries an id (tbl-<cid>) and no
  cell fontSize, so fit-grow sizes it from its text (14 px cells, column widths, rows) and, as the slide's main table,
  grows its text and rows into spare height, further than an LLM table (NODE_TABLE_CAPS).
- `rows`: one ruled row per table row: the first cell as its title · the other cells; the column names as small labels
  on top.
- `ledger` (≤ 6 columns): one solid header band (an icon over each column name, from `icons`) over joined, tinted rows.
Only `native` is a real PowerPoint table, which a person can edit by hand; the others are loose shapes. `rows numbered`,
`columns`, `banded`, `grid` and `grid numbered` were removed (user, 2026-11-04): their names are aliases now.

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


# ── highlights ────────────────────────────────────────────────────────────────
# The LLM marks meaning inside the tag, by name; code finds the cells, compares the numbers and colours them
# (user, 2026-11-02: a cell's background and its text are separate; words inside a cell take <Span color>, never <Mark>):
#   <Highlight row="Flipkart" fill="bad"/>  <Highlight column="ROAS" below="Target" color="bad" else="good"/>
#   <Highlight column="ROAS" max="good" min="bad"/>  <Highlight cell="Nykaa / ROAS" color="good"/>
#   <Highlight phrase="spend still rising" color="bad"/>
# fill = the cell's background ($<role>Soft), color = its text ($<role>Text); tones good / bad / watch / focus.
# show= a column's values drawn as (user, 2026-11-02): arrows (▲ / ▼ before signed numbers, up good unless
# invert="true"), pills (each value in a rounded tag) or bars (a bar under each number, sized to the column's largest).
# Pills and bars need a box per cell: the card compositions draw them, native drops them (NODE_ATTR_DROPPED).

# No cap (user, 2026-11-02): every <Highlight> is drawn; past MANY_HIGHLIGHTS a warning says the table is heavily
# coloured, nothing is dropped (a cut left tables half-coloured: docs/eval/table-node/highlight-limits.png).
MANY_HIGHLIGHTS = 6
HIGHLIGHT_ATTRS = {"row", "column", "cell", "phrase", "fill", "color", "above", "below", "else", "max", "min",
                   "show", "invert"}
SHOWS = ("arrows", "pills", "bars")
_SIGNED = re.compile(r"^\s*[-+−▲▼]")
TONES = ("good", "bad", "watch", "focus")   # focus: emphasis without a meaning, in the accent
TONE_ROLES = {**compose.TONE_ROLE, "focus": "accent"}
_NUM = re.compile(r"[-+−]?\d[\d,]*(?:\.\d+)?")


def _number(s: str) -> tuple[float, str] | None:
    """'₹31.2L' -> (31.2, '₹L'): the first number and what is left around it (the unit)."""
    m = _NUM.search(str(s))
    if not m:
        return None
    return float(m.group().replace(",", "").replace("−", "-")), (s[:m.start()] + s[m.end():]).strip()


class Paint:
    """What the highlights give each body cell (r, c): a fill role, a text role, phrases in a role."""

    def __init__(self) -> None:
        self.fill: dict[tuple[int, int], str] = {}
        self.ink: dict[tuple[int, int], str] = {}
        self.spans: dict[tuple[int, int], list[tuple[str, str]]] = {}
        self.arrows: dict[tuple[int, int], tuple[str, str]] = {}   # (glyph, role)
        self.pills: set[tuple[int, int]] = set()
        self.bars: dict[tuple[int, int], int] = {}                  # % of the column's largest

    def boxed(self) -> bool:
        """Pills or bars asked: only a composition with a box per cell draws them."""
        return bool(self.pills or self.bars)

    def box(self, r: int, c: int, at: dict) -> dict:
        """A cell's box attributes with its fill: the role's Soft fill, its border in the role when it has one."""
        if (r, c) not in self.fill:
            return at
        role = self.fill[(r, c)]
        return {**at, "backgroundColor": f"${role}Soft", **({"border.color": f"${role}"} if "border.color" in at else {})}

    def color(self, r: int, c: int) -> dict:
        return {"color": f"${self.ink[(r, c)]}Text"} if (r, c) in self.ink else {}

    def runs(self, r: int, c: int, v: str) -> str:
        """The cell's text, escaped, each highlighted phrase (its first match) in a <Span color>."""
        low, found = v.lower(), []
        for phrase, role in self.spans.get((r, c), []):
            s = low.find(phrase.lower())
            if s >= 0:
                found.append((s, len(phrase), role))
        out, pos = [], 0
        for s, n, role in sorted(found):
            if s < pos:
                continue
            out += [native.x(v[pos:s]), f'<Span color="${role}Text">{native.x(v[s:s + n])}</Span>']
            pos = s + n
        arrow = self.arrows.get((r, c))
        lead = f'<Span color="${arrow[1]}Text">{arrow[0]} </Span>' if arrow else ""
        return lead + "".join(out) + native.x(v[pos:])

    def wrap(self, r: int, c: int, text: str) -> str:
        """A card cell's Text as a pill (a rounded tag in its tone, accent by default) and / or over a bar."""
        role = self.ink.get((r, c), "accent")
        if (r, c) in self.pills:
            text = (f'<HStack alignSelf="start" alignItems="center" justifyContent="center" padding.top="4" padding.bottom="4" padding.left="12" padding.right="12" '
                    f'borderRadius="14" backgroundColor="${role}Soft">{text}</HStack>')
        if (r, c) in self.bars:
            pct = self.bars[(r, c)]
            fill = f'<VStack w="{pct}%" h="6" borderRadius="3" backgroundColor="${role}" />' if pct else ""
            text += f'<HStack h="6" borderRadius="3" backgroundColor="$surfaceAlt">{fill}</HStack>'
        return text


def highlights(comp: dict, body: str, flag) -> Paint | None:
    """The tag's <Highlight> children -> Paint; None when it has none (code then colours the hint's emphasis).
    A name or phrase not in the table is NODE_HIGHLIGHT_UNKNOWN (an error: the LLM fixes it); past MANY_HIGHLIGHTS all
    are kept with a warning (NODE_HIGHLIGHT_LIMIT); a rule on cells without comparable numbers colours nothing there
    (NODE_HIGHLIGHT_RULE)."""
    from lxml import etree
    ref, (cols, rows) = comp["component_id"], grid(comp)
    try:
        kids = [k for k in etree.fromstring(f"<x>{body}</x>") if isinstance(k.tag, str)]
    except etree.XMLSyntaxError:
        flag("NODE_HIGHLIGHT_UNKNOWN", ref, f'the children of <{TAG} ref="{ref}"> are not readable XML: write only '
             '<Highlight .../> elements inside it.')
        return None
    hs = [k for k in kids if k.tag == "Highlight"]
    if len(hs) < len(kids):
        flag("NODE_ATTR_DROPPED", ref, f'only <Highlight> goes inside <{TAG} ref="{ref}">: code writes the cells; '
             'other children removed.')
    if not hs:
        return None
    if len(hs) > MANY_HIGHLIGHTS:
        flag("NODE_HIGHLIGHT_LIMIT", ref, f'{len(hs)} <Highlight>s on <{TAG} ref="{ref}">: all drawn, but more than '
             f'{MANY_HIGHLIGHTS} makes a heavily coloured table; colour a whole row or column first, then mark only '
             'the exceptions.')
    norm = lambda s: " ".join(str(s).split()).casefold()  # noqa: E731
    labels, heads = [norm(r[0]) for r in rows], [norm(c) for c in cols]
    paint = Paint()

    def bad(msg: str) -> None:
        flag("NODE_HIGHLIGHT_UNKNOWN", ref, f'<Highlight> on <{TAG} ref="{ref}">: {msg}')

    def role(tone: str) -> str:
        return TONE_ROLES[tone]

    def put(cells: list[tuple[int, int]], at: dict, tone_key: str = "") -> None:
        for rc in cells:
            for k, store in (("fill", paint.fill), ("color", paint.ink)):
                t = at.get(tone_key) if tone_key else at.get(k)
                if at.get(k) and t:
                    store[rc] = role(t)

    for h in hs:
        at = {k: v.strip() for k, v in h.attrib.items()}
        if set(at) - HIGHLIGHT_ATTRS:
            bad(f'unknown attribute {", ".join(sorted(set(at) - HIGHLIGHT_ATTRS))} (use row / column / cell / phrase, '
                'fill, color, above / below / else, max / min).')
            continue
        tones = {k: at[k] for k in ("fill", "color", "else", "max", "min") if k in at}
        if any(t not in TONES for t in tones.values()):
            bad(f'tones are {" / ".join(TONES)} ({tones}).')
            continue
        if "show" in at:
            if at["show"] not in SHOWS or "column" not in at or norm(at["column"]) not in heads:
                bad(f'show="{at["show"]}" takes a column ({", ".join(cols)}) and one of {" / ".join(SHOWS)}.')
                continue
            c = heads.index(norm(at["column"]))
            nums = {r: _number(row[c]) for r, row in enumerate(rows)}
            if at["show"] == "pills":
                paint.pills |= {(r, c) for r, row in enumerate(rows) if row[c].strip()}
            elif at["show"] == "arrows":
                up, down = ("bad", "good") if at.get("invert") == "true" else ("good", "bad")
                for r, row in enumerate(rows):
                    if nums[r] and nums[r][0] and _SIGNED.match(row[c]) and not row[c].lstrip().startswith(("▲", "▼")):
                        paint.arrows[(r, c)] = ("▲", role(up)) if nums[r][0] > 0 else ("▼", role(down))
                if not any(k[1] == c for k in paint.arrows):
                    flag("NODE_HIGHLIGHT_RULE", ref, f'show="arrows" on column "{cols[c]}": no signed number (+ / -) in it; '
                         'no arrows drawn.')
            else:
                vals = {r: n for r, n in nums.items() if n and n[0] >= 0}
                if len({u for _, u in vals.values()}) > 1 or not vals or not max(v for v, _ in vals.values()):
                    flag("NODE_HIGHLIGHT_RULE", ref, f'show="bars" on column "{cols[c]}": needs positive numbers in one '
                         'unit; no bars drawn.')
                    continue
                top = max(v for v, _ in vals.values())
                paint.bars |= {(r, c): round(100 * v / top) for r, (v, _) in vals.items()}
            continue
        if not ({"fill", "color"} & set(at)) and not ({"max", "min"} & set(at) and "column" in at):
            bad('give it fill and / or color (max / min colour the text by themselves).')
            continue
        if "phrase" in at:
            hits = [(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if at["phrase"].lower() in v.lower()]
            if not hits or "color" not in at:
                bad(f'phrase "{at["phrase"]}" is not in any cell.' if not hits else 'a phrase takes color only.')
                continue
            for rc in hits:
                paint.spans.setdefault(rc, []).append((at["phrase"], role(at["color"])))
            continue
        if "cell" in at:
            parts = at["cell"].split(" / ")
            hit = next(((labels.index(norm(" / ".join(parts[:k]))), heads.index(norm(" / ".join(parts[k:]))))
                        for k in range(1, len(parts)) if norm(" / ".join(parts[:k])) in labels
                        and norm(" / ".join(parts[k:])) in heads), None)
            if hit is None:
                bad(f'cell "{at["cell"]}" is not "<first cell of a row> / <column name>".')
                continue
            put([hit], at)
            continue
        if "row" in at:
            if norm(at["row"]) not in labels:
                bad(f'row "{at["row"]}" is not a row (rows are named by their first cell: {", ".join(r[0] for r in rows)}).')
                continue
            r = labels.index(norm(at["row"]))
            put([(r, c) for c in range(len(cols))], at)
            continue
        if "column" not in at or norm(at["column"]) not in heads:
            bad(f'column "{at.get("column", "")}" is not a column ({", ".join(cols)}).' if "column" in at
                else 'name a row, column, cell or phrase.')
            continue
        c = heads.index(norm(at["column"]))
        rule = next((k for k in ("above", "below") if k in at), None)
        if rule is None and not ({"max", "min"} & set(at)):
            put([(r, c) for r in range(len(rows))], at)
            continue
        nums = {r: _number(row[c]) for r, row in enumerate(rows)}
        nums = {r: n for r, n in nums.items() if n}
        if rule:
            other = heads.index(norm(at[rule])) if norm(at[rule]) in heads else None
            fixed = None if other is not None else _number(at[rule])
            if other is None and fixed is None:
                bad(f'{rule}="{at[rule]}" is neither a number nor a column.')
                continue
            hit, miss, skipped = [], [], 0
            for r, (v, unit) in nums.items():
                than = fixed if other is None else _number(rows[r][other])
                if not than or (than[1] and than[1] != unit):   # a bare number ("3") compares with any unit
                    skipped += 1
                    continue
                (hit if (v > than[0] if rule == "above" else v < than[0]) else miss).append((r, c))
            if skipped or not nums:
                flag("NODE_HIGHLIGHT_RULE", ref, f'{rule}="{at[rule]}" on column "{cols[c]}": '
                     f'{skipped + len(rows) - len(nums)} cell(s) without a number in the same unit; left uncoloured.')
            put(hit, at)
            if "else" in at:
                put(miss, at, "else")
        units = {u for _, u in nums.values()}
        if {"max", "min"} & set(at) and nums:
            if len(units) > 1:
                flag("NODE_HIGHLIGHT_RULE", ref, f'max / min on column "{cols[c]}": mixed units ({", ".join(sorted(units))}); '
                     'left uncoloured.')
                continue
            for k, pick in (("max", max), ("min", min)):
                if k in at:
                    best = pick(v for v, _ in nums.values())
                    for r, (v, _) in nums.items():
                        if v == best:
                            paint.ink[(r, c)] = role(at[k])
    return paint


# ── compositions ──────────────────────────────────────────────────────────────

T = compose.text
A = compose.a


class Pick:
    """Which parts a cell, a row or a column name takes: the emphasis parts on the emphasis row (all of them) or
    column (its header / cells / cell boxes), else the rest."""

    def __init__(self, rest: dict, hi: dict, focus: tuple[str, int] | None, paint: Paint | None = None):
        self.rest, self.hi, self.focus, self.paint = rest, hi, focus, paint or Paint()

    def text(self, r: int, c: int, v: str, px: int, part: dict, **kw: str) -> str:
        """A body cell's Text: its highlight colour over the part's, its phrases in <Span color>, as a pill / over a
        bar when asked."""
        return self.paint.wrap(r, c, f'<Text fontSize="{px}"{A({**kw, **part, **self.paint.color(r, c)})}>'
                                     f'{self.paint.runs(r, c, v)}</Text>')

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

    paint = pick.paint

    def td(v: str, at: dict, i: int, r: int | None = None) -> str:
        if r is None:
            return f"<Td{A(at)}>{native.x(v)}</Td>"
        return f"<Td{A({**paint.box(r, i, at), **paint.color(r, i)})}>{paint.runs(r, i, v)}</Td>"

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
            cells.append(td(v, at, i, r))
        out.append("<Tr>" + "".join(cells) + "</Tr>")
    return "".join(out) + "</Table>"


def draw_rows(comp: dict, box: dict, pick: Pick) -> str:
    cid, (cols, rows) = comp["component_id"], grid(comp)
    lab = lambda i: T(cols[i].upper(), 13, pick.col(i)["header"], bold="true", letterSpacing="1")  # noqa: E731
    head = (f'<HStack gap="20"><VStack w="24%">{lab(0)}</VStack>'
            + "".join(f'<VStack w="1" grow="1">{lab(i)}</VStack>' for i in range(1, len(cols))) + "</HStack>") \
        if any(c.strip() for c in cols) else ""
    body = []
    for r, row in enumerate(rows):
        p = pick.row(r)
        item = {k: v for k, v in p["item"].items() if r or not k.startswith("borderTop")}   # no rule above the first
        cells = "".join(f'<VStack w="1" grow="1"{A(pick.paint.box(r, i, {}))}>{pick.text(r, i, v, 18, pick.cell(r, i)["cell"])}</VStack>'
                        for i, v in enumerate(row) if i)
        body.append(f'<HStack id="card-{cid}-{r}" grow="1" gap="20" alignItems="center" padding="10"{A(item)}>'
                    f'<VStack w="24%"{A(pick.paint.box(r, 0, {}))}>{pick.text(r, 0, row[0], 22, p["label"], bold="true")}</VStack>{cells}</HStack>')
    return f'<VStack gap="8"{A(box)}>{head}<VStack gap="0" grow="1">{"".join(body)}</VStack></VStack>'


LABEL_W = "22%"   # the first column of a ledger


def _boxed(p: dict) -> tuple[dict, dict]:
    """A Cell part drawn as a box around its Text: (box attributes, text attributes); backgroundColor goes on the box."""
    return {k: v for k, v in p.items() if k == "backgroundColor"}, {k: v for k, v in p.items() if k != "backgroundColor"}


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
        cells = "".join(f'<VStack id="card-{cid}.tc-{r * len(cols) + i}" w="1" grow="1" padding="14" justifyContent="center"{A(pick.paint.box(r, i, cell_box(i)))}>'
                        f'{pick.text(r, i, v, 17, pick.cell(r, i)["cell"])}</VStack>' for i, v in enumerate(row) if i)
        body.append(f'<HStack grow="1" gap="0" alignItems="stretch">'
                    f'<VStack id="card-{cid}.tl-{r}" w="{LABEL_W}" padding="14" justifyContent="center"{A(pick.paint.box(r, 0, {**cell_box(0), **lb}))}>'
                    f'{pick.text(r, 0, row[0], 18, lt, bold="true")}</VStack>{cells}</HStack>')
    return f'<VStack gap="4"{A(box)}>{head}{"".join(body)}</VStack>'


def _toned(parts: dict[str, dict], role: str) -> dict[str, dict]:
    """$tone / $toneSoft / $toneText in every part -> the role's tokens (compose.tone_value)."""
    return {p: {k: compose.tone_value(v, role) for k, v in at.items()} for p, at in parts.items()}


def draw(comp: dict, attrs: dict[str, str], flag, body: str = "") -> tuple[str, dict]:
    """One <Table ref> tag (and its <Highlight> children) -> its XML, and what was drawn. With highlights, the LLM
    has chosen what to colour: no emphasis from the hint on top of them."""
    ref, nd = comp["component_id"], node()
    paint = highlights(comp, body, flag) if body.strip() else None
    meta, box, parts = compose.read(attrs, ref, flag, nd)
    name, extra = compose.composition(nd, comp, meta.get("variant"), ref, flag)
    compose.undrawn(nd, name, box, parts, ref, flag)
    for k, v in extra.items():   # an alias's part attributes (zebra, dark_header), under the LLM's own
        head, _, sub = k.partition(".")
        if head in parts and sub:
            parts[head].setdefault(sub, str(v))
    if name == "native":
        for k in [k for k in parts["item"] if k not in ON_NATIVE_ITEM]:
            flag("NODE_ATTR_DROPPED", ref, f'item.{k} on <Table ref="{ref}">: a native table cell takes only '
                 'item.backgroundColor; removed (C1).')
            del parts["item"][k]
    if paint and paint.boxed() and name == "native":
        flag("NODE_ATTR_DROPPED", ref, f'show="pills" / "bars" on <{TAG} ref="{ref}">: a native table cell holds only '
             'text; use rows or ledger for them. Removed.')
        paint.pills, paint.bars = set(), {}
    focus = None if paint else emphasis(comp)
    box, rest, hi = compose.layers(nd, name, box, parts, focus is not None)
    rest, hi = _toned(rest, "accent"), _toned(hi, role(comp, focus))
    box = {k: compose.tone_value(v, "accent") for k, v in box.items()}
    if name != "native" and not ({"h", "grow"} & set(box)):
        box["grow"] = "1"   # a native table sizes to its rows: fit-grow sets its columns, then grows it into spare height
    pick = Pick(rest, hi, focus, paint)
    icons = [s.strip() for s in str(meta.get("icons") or "").split(",")]
    xml = (draw_native(comp, box, pick) if name == "native" else
           draw_rows(comp, box, pick) if name == "rows" else draw_ledger(comp, box, pick, icons))
    return xml, {"composition": name, "focus": focus,
                 "highlights": bool(paint and (paint.fill or paint.ink or paint.spans))}


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <Table ref="<table component id>"/> drawn from the plan (compose.expand)."""
    def check(comp: dict, flag) -> bool:
        if grid(comp)[1]:
            return True
        flag("NODE_ITEM_MISSING", comp["component_id"], f'table "{comp["component_id"]}" has no rows in the plan.')
        return False

    return compose.expand(xml, components(plan), TAG, draw, check, children=True)


# ── prompt ─────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines (the cached part of the system prompt)."""
    vs = spec.blocks()["table"]["variants"]
    styles = "; ".join(f"{n}: {st}" for n, st in (node().get("styles") or {}).items())
    return "\n".join([
        "## TABLES (code draws them from the plan)",
        f'<{TAG} ref="<table id>" variant="..."/>: ' + "; ".join(f"{n} ({v['prompt']})" for n, v in vs.items()) + ".",
        "Code writes every cell and number; never type one. Layout (w, h, grow) and box attributes style the table's "
        "own box; parts header. (column names) label. (first column) cell. (other cells) stripe. (alternate rows) take "
        "backgroundColor color bold italic textAlign in $tokens; item. on rows and ledger. "
        f"No <Tr>, <Td> or fontSize. Recipes: {styles}.",
        "Colour by meaning with <Highlight/> inside the tag, a whole row or column first, then its exceptions (later "
        "marks win); without them code colours the row or column "
        "the hint names). Name rows by their first cell and columns by their name, exactly as in the table; tones "
        "good | bad | watch | focus (emphasis, no meaning); fill = the cell's background, color = its text:",
        '  <Highlight row="Flipkart" fill="bad"/> · <Highlight column="ROAS" color="good"/> · '
        '<Highlight cell="Nykaa / ROAS" fill="good" color="good"/>',
        '  <Highlight column="ROAS" below="Target" color="bad" else="good"/> (a number or another column; code '
        'compares) · <Highlight column="ROAS" max="good" min="bad"/> (highest / lowest value, its text)',
        '  <Highlight phrase="spend still rising" color="bad"/> (those words of a cell, in colour)',
        '  <Highlight column="QoQ" show="arrows"/> (▲ / ▼ before signed numbers; invert="true" when up is bad) · '
        '<Highlight column="Status" show="pills"/> · <Highlight column="Spend" show="bars"/> (pills and bars: rows, '
        'ledger only)',
        "Colour only what the headline or the hint is about.",
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
    em = (f"row {rows[f[1]][0]!r}" if f[0] == "row" else f"column {cols[f[1]]!r}") if f else "nothing"
    hint = " ".join(str(comp.get("design_hint") or "").split())
    parts = [f"TABLE {cid}: {len(rows)} rows x {len(cols)} columns", f"longest cell {longest} chars",
             "variants " + " | ".join(ok)]
    cells = "\n".join(["  columns: " + " | ".join(cols)] + ["  " + " | ".join(r) for r in rows])
    about = " ".join(str(comp.get("content_summary") or "").split())
    heading = (f'\n  about: {about}. Unless the slide title already says this, write a short heading from it as a <Text> '
               "above the tag; code draws the column names, not a heading." if about else "")
    return ("; ".join(parts) + (f"\n  hint: {hint}" if hint else "") + heading + f"\n{cells}\n"
            f'<{TAG} ref="{cid}"/> (or with <Highlight/> inside; without them code colours {em}); the cells are '
            "for reading: never type one yourself, code writes them from the plan")
