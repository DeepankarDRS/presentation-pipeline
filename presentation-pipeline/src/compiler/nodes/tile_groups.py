"""KPI tiles and cards as composition nodes (docs/composition-convention-spec.md §5, §10 steps 1-2),
`POM_NODES=kpi_row,card_grid` (each kind on its own; kpi_row needs element refs on, POM_BLOCKS kpi or tiles).

The LLM writes a group tag per component, as the tile nodes; `variant` names a composition only:

    <KpiRow ref="kpis" variant="rows" item.borderLeft.color="$tone" item.borderLeft.width="6">
      <Kpi ref="kpis.2" value.color="$negativeText"/>                 restyles one item
    </KpiRow>
    <Card ref="levers.3" w="34%"/>                                     places one card anywhere, in its group's form

Compositions (block-variants.yaml `nodes.kpi_row` / `nodes.card_grid`; the sheets in docs/eval/composition-convention/
are what they draw):
- KPI: `grid` (today's tiles, tiles.assemble + tiles.build_group), `strip` (one shared box, hairlines, one row),
  `rows` (icon badge · label over delta · value at the right; today's inline tile), `banded` (a solid band over value +
  delta), `bento` (the emphasis item large and value first, the rest as rows beside it).
- Cards: `grid` / `grid numbered` / `steps` (today's cards, cards.assemble + cards.build_group), `rows` /
  `rows numbered`, `columns` (a pill head, each bullet in its own box), `banded`, `bento`.
Today's names are aliases (`KpiGrid`, `note.`, style variants -> recipes, `divided`, `numerals`, `layout`, `arrange`).

Style per item, later wins: the composition's `look` -> its `tone` (the item's tone) -> its `emphasis` (the plan's
emphasis item) -> a recipe (an alias's or the design hint's) -> the group's attributes (`item.` reaches every item's box)
-> the item tag's. $tone / $toneSoft / $toneText resolve per item (compose.tone_value). Code owns the words, sizes,
order, numbers, columns and which item is the emphasis. Items carry card-<cid>-<i> (the bento block cardf-), inner
boxes card-<cid>x-<n> (C11); KPI text is element refs (kpiv- value ids, C12) that element_refs.fill_refs writes.
"""

from __future__ import annotations

import re
from typing import Any

from lxml import etree

from src.compiler.nodes import cards, compose, element_refs, spec, tiles, validate

KINDS = ("kpi_row", "card_grid")
SEVERITY = compose.SEVERITY
STRUCTURE = ("layout", "arrange")   # today's structure attributes: meta_aliases
TODAY = {"grid", "grid numbered", "steps"}   # today's tiles / cards: drawn by tiles.py / cards.py, ids as today
_ITEM_REF = tiles._ITEM_REF


def on(kind: str) -> bool:
    if kind == "kpi_row":
        return spec.nodes_on(kind) and element_refs.refs_on()
    return kind in KINDS and spec.nodes_on(kind)


def kinds_on() -> list[str]:
    return [k for k in KINDS if on(k)]


def node(kind: str) -> dict[str, Any]:
    return spec.nodes()[kind]


def components(plan: dict | None, kind: str) -> dict[str, dict]:
    if kind == "card_grid":
        return cards.card_components(plan)   # a matrix card_grid stays hand-drawn (deferred)
    return element_refs.kpi_components(plan)


def count(comp: dict) -> int:
    if comp["kind"] == "card_grid":
        return len(cards.cards_of(comp))
    return len(element_refs._list(comp, "kpi_values"))


def emphasis_index(comp: dict) -> int | None:
    return cards.emphasis_index(comp) if comp["kind"] == "card_grid" else tiles.emphasis_index(comp)


def role_of(comp: dict, i: int, color: str | None) -> str:
    """The item's role: its own (or its group's) color, else the plan tone (none -> accent)."""
    if color in tiles.ROLE_OF:
        return tiles.ROLE_OF[color]
    return cards.tone_role(comp, i) if comp["kind"] == "card_grid" else tiles.tone_role(comp, i)


# ── attributes ────────────────────────────────────────────────────────────────

def _structure(attrs: dict[str, str], nd: dict, ref: str, flag) -> dict[str, str]:
    """Today's `layout` / `arrange` on a group: the composition they name when no `variant` is given (NODE_ATTR_ALIAS),
    else dropped (the variant wins)."""
    attrs = dict(attrs)
    for k in STRUCTURE:
        if k not in attrs:
            continue
        v = attrs.pop(k)
        word = (nd.get("meta_aliases") or {}).get(k, {}).get(v)
        if word and not attrs.get("variant"):
            attrs["variant"] = word
            flag("NODE_ATTR_ALIAS", ref, f'{k}="{v}" on <{nd["tag"]} ref="{ref}"> is now variant="{word}".')
        else:
            flag("NODE_ATTR_DROPPED", ref, f'{k}="{v}" on <{nd["tag"]} ref="{ref}">: the composition (variant) places '
                 "the parts; removed.")
    return attrs


def _item_read(attrs: dict[str, str], nd: dict, ref: str, flag) -> tuple[dict, dict, dict]:
    """An item tag: (meta, box, parts). Its `variant` is a group's word: a style alias becomes its recipe on this item,
    anything else is dropped (spec §2.2); `arrange` is dropped; `item.` on it is its own box."""
    attrs = dict(attrs)
    style = None
    for k in ("variant", "arrange"):
        if k not in attrs:
            continue
        v = " ".join(attrs.pop(k).split())
        alias = (nd.get("aliases") or {}).get(v)
        if k == "variant" and isinstance(alias, dict) and alias.get("style"):
            style = alias["style"]
            flag("NODE_ATTR_ALIAS", ref, f'variant="{v}" on <{nd["item_tag"]} ref="{ref}"> is now its style: '
                 f'{nd["styles"][style]}.')
        else:
            flag("NODE_ATTR_DROPPED", ref, f'{k}="{v}" on <{nd["item_tag"]} ref="{ref}">: an item takes its group\'s '
                 "composition; removed.")
    meta, box, parts = compose.read(attrs, ref, flag, nd, nd["item_meta"], nd["item_tag"])
    box.update(parts.pop("item"))
    if style:
        meta["style"] = style
    return meta, box, parts


def _put(box: dict, parts: dict, attrs: dict, role: str, group: dict | None = None, skip: set[str] = frozenset()) -> None:
    """Lay attributes over an item's (box, parts): `item.x` -> the item box, `<part>.x` -> the part, anything else ->
    `group` (the group's own box; ignored when None). None removes the key; $tone* resolved for the item's role."""
    for k, v in attrs.items():
        if k in skip:
            continue
        head, _, sub = k.partition(".")
        if head == "item" and sub:
            dst, key = box, sub
        elif head in parts and sub:
            dst, key = parts[head], sub
        elif group is not None and k != "size":
            dst, key = group, k
        else:
            continue
        if v is None:
            dst.pop(key, None)
        else:
            dst[key] = compose.tone_value(v, role)


def item_style(nd: dict, name: str, comp: dict, i: int, role: str, focus: bool, recipe: dict, gparts: dict,
               item: tuple[dict, dict, dict] | None) -> tuple[dict, dict, bool]:
    """(box, parts, hero) of item i: look -> tone -> emphasis -> recipe -> group attributes -> item tag. On the emphasis
    item the group's attributes do not undo what the emphasis look sets (compose.layers)."""
    c = nd["compositions"][name]
    box: dict[str, str] = {}
    parts: dict[str, dict[str, str]] = {p: {} for p in nd["parts"] if p != "item"}
    look = c.get("look") or {}
    _put(box, parts, look, role)
    tone = {"positive": "good", "negative": "bad", "warning": "watch"}.get(role, "")
    toned = (c.get("tone") or {}).get(tone) or {}
    _put(box, parts, toned, role)
    emph = (c.get("emphasis") or {}) if focus else {}
    _put(box, parts, emph, role)
    _put(box, parts, recipe, role, skip=set(emph))
    # the LLM restating the composition's default (item.backgroundColor="$surfaceAlt" on a grid, look3 QBR 2) must not
    # wipe the tone look: a group / item attribute equal to the look's own value is skipped where the tone set the key
    restated = {k for k in toned if look.get(k) is not None}

    def _keep(attrs: dict) -> dict:
        return {k: v for k, v in attrs.items() if not (k in restated and v == look[k])}
    flat = {f"item.{k}" if p == "item" else f"{p}.{k}": v for p, a in gparts.items() for k, v in a.items()}
    _put(box, parts, _keep(flat), role, skip=set(emph))
    hero = emph.get("size") == "hero"
    if item:
        meta, ibox, iparts = item
        _put(box, parts, _keep({f"item.{k}": v for k, v in ibox.items()}), role)
        _put(box, parts, _keep({f"{p}.{k}": v for p, a in iparts.items() for k, v in a.items()}), role)
        _put(box, parts, compose.recipe(nd["styles"].get(meta.get("style"), "")), role)
        if meta.get("size") == "hero":
            hero = hero or focus
        elif meta.get("size") not in (None, "normal"):
            hero = False
    return box, parts, hero


def group_look(nd: dict, name: str, box: dict) -> dict:
    """The group's own box: the composition look's keys without a part prefix, then the LLM's group box attributes."""
    out: dict[str, str] = {}
    _put({}, {p: {} for p in nd["parts"] if p != "item"}, nd["compositions"][name].get("look") or {}, "accent", out)
    out.update(box)
    return out


def _hint(nd: dict, comp: dict, flag) -> tuple[str | None, str | None, dict[int, str]]:
    """A bare group (no variant): (composition, group style, {item: style}) its design hint asks for. The composition
    cues (hero / spotlight -> bento, ruled -> rows, strip -> strip, F5) and the style cues (plan_checks.look_from_hint,
    today's names -> their alias); a composition whose `requires` fail is not used (no NODE_VARIANT_UNMET)."""
    from src.agents.plan_checks import composition_from_hint, look_from_hint   # src.agents imports the validator
    cid, cs, al = comp["component_id"], nd["compositions"], nd.get("aliases") or {}
    word = composition_from_hint(comp)
    if word and (word not in cs or spec.failed_requires(cs[word], comp)):
        word = None
    look = look_from_hint(comp)
    style, items = None, {}
    for target, v in [(None, look["group"]), *look["items"].items()]:
        a = al.get(v) if v else None
        if isinstance(a, dict) and a.get("style"):
            if target is None:
                style = a["style"]
            else:
                items[target] = a["style"]
        elif target is None and isinstance(a, str) and a in cs and a != next(iter(cs)) and not word \
                and not spec.failed_requires(cs[a], comp):
            word = a
    if word or style or items:
        flag("NODE_LOOK_FROM_HINT", cid, f'<{nd["tag"]} ref="{cid}"> drawn'
             + (f' variant="{word}"' if word else "") + (f" with the {style} style" if style else "")
             + (f", items {', '.join(f'{i} {s}' for i, s in items.items())}" if items else "")
             + f' from the design hint ({", ".join(look["cues"]) or "composition cue"}).')
    return word, style, items


# ── KPI compositions ──────────────────────────────────────────────────────────

A = compose.a


def _kpi_text(comp: dict, i: int, field: str, part: dict, hero: bool = False, **kw: str) -> str:
    size = ' size="hero"' if hero else ""
    return f'<Text ref="{comp["component_id"]}.{i}.{field}"{A({**part, **kw})}{size} />'


def _icon(name: str, part: dict, px: int) -> str:
    return f'<Icon name="{name}" size="{px}"{A(part)} />' if name else ""


def _xml(el: etree._Element) -> str:
    return etree.tostring(el, encoding="unicode")


def _divide(box: dict, parts: dict, side: str, space: str | None = None) -> None:
    """The `divider.` hairline before an item (side Left / Top), and the space inside it."""
    d = parts.get("divider") or {}
    if d.get("width") in (None, "0"):
        return
    box[f"border{side}.color"] = d.get("color", "$border")
    box[f"border{side}.width"] = d["width"]
    if space:
        box.setdefault(f"padding.{side.lower()}", space)


def kpi_item(comp: dict, i: int, name: str, box: dict, parts: dict, hero: bool, icon: str, focus: bool) -> str:
    """Item i in the composition's item form (also an item placed apart)."""
    cid = comp["component_id"]
    if name in ("grid", "strip"):
        el = tiles.assemble(comp, i, box, parts, icon, "label-first", hero, note_part="delta")
    elif name == "rows" or (name == "bento" and not focus):
        el = tiles.assemble(comp, i, box, parts, icon, "inline", hero, note_part="delta")
    elif name == "bento":   # the big block: icon, the value first, label, delta
        return (f'<VStack id="cardf-{cid}-{i}" w="42%" justifyContent="center"{A(box)}>{_icon(icon, parts["icon"], 28)}'
                f'{_kpi_text(comp, i, "value", parts["value"], hero)}{_kpi_text(comp, i, "label", parts["label"])}'
                f'{_kpi_text(comp, i, "note", parts["delta"])}</VStack>')
    else:   # banded
        band = {"alignItems": "center", **parts["band"]}
        inner = {k: v for k, v in box.items() if k in ("padding", "justifyContent")}
        outer = {k: v for k, v in box.items() if k not in inner}
        return (f'<VStack id="card-{cid}-{i}"{A(outer)}><HStack{A(band)}>{_icon(icon, parts["icon"], 22)}'
                f'{_kpi_text(comp, i, "label", parts["label"])}</HStack>'
                f'<VStack grow="1" gap="8"{A({"padding": "20", "justifyContent": "center", **inner})}>'
                f'{_kpi_text(comp, i, "value", parts["value"], hero)}{_kpi_text(comp, i, "note", parts["delta"])}</VStack></VStack>')
    if name != "grid":   # grid: today's tiles have no item id (pixel for pixel)
        el.set("id", f"card-{cid}-{i}")
    return _xml(el)


def kpi_group(comp: dict, name: str, items: list[tuple[int, str]], gbox: dict, meta: dict, flag) -> str:
    """The drawn items (index, xml) laid out as the composition's group."""
    cid = comp["component_id"]
    if name == "grid":
        els = [etree.fromstring(x) for _, x in items]
        layer = tiles._Layer()
        layer.box = dict(gbox)
        return _xml(tiles.build_group(els, {k: v for k, v in meta.items() if k == "cols"}, layer, cid, flag))
    xs = [x for _, x in items]
    if name in ("strip", "banded"):
        xs = [_first(x, w="1", grow="1") for x in xs]
        return f'<HStack alignItems="stretch"{A({"gap": "18", **gbox})}>{"".join(xs)}</HStack>'
    if name == "rows":
        xs = [_first(x, grow="1") for x in xs]
        return f'<VStack{A({"gap": "0", **gbox})}>{"".join(xs)}</VStack>'
    big = [x for x in xs if x.startswith("<VStack id=\"cardf-")]
    rest = [_first(x, grow="1") for x in xs if x not in big]
    return (f'<HStack alignItems="stretch"{A({"gap": "18", **gbox})}>{"".join(big)}'
            f'<VStack grow="1" gap="14">{"".join(rest)}</VStack></HStack>')


def _first(x: str, **attrs: str) -> str:
    """The item's own tag with these attributes added where it has none of its own (an LLM's w stays)."""
    m = re.match(r"<(\w+)([^<>]*?)(/?)>", x)
    add = {k: v for k, v in attrs.items() if k not in validate.attrs_of(m.group(2))}
    return f"<{m.group(1)}{A(add)}{x[len(m.group(1)) + 1:]}"


# ── card compositions ─────────────────────────────────────────────────────────

def _card_text(text: str, px: int, part: dict, **kw: str) -> etree._Element:
    return cards._text(text, px, part, **kw)


def _body(c: dict, px: int, part: dict, ink: str) -> etree._Element | None:
    body, _ = cards._lines(c)
    if not body:
        return None
    t = _card_text("", px, part, lineHeight="1.35")
    phrase = str(c.get("key_phrase") or "")
    cards._with_phrase(t, body, phrase if phrase and phrase in body else "", ink)
    return t


def _bullets(c: dict, px: int, part: dict) -> etree._Element | None:
    _, bullets = cards._lines(c)
    if not bullets:
        return None
    ul = etree.Element("Ul", fontSize=str(px), lineHeight="1.4")
    for k, v in part.items():
        if k in ("color", "bold", "italic", "underline", "textAlign"):
            ul.set(k, v)
    for b in bullets:
        etree.SubElement(ul, "Li").text = b
    return ul


def _stack(tag: str, attrs: dict, *children: etree._Element | None) -> etree._Element:
    el = etree.Element(tag)
    for k, v in attrs.items():
        el.set(k, str(v))
    for c in children:
        if c is not None:
            el.append(c)
    return el


def _ink(fill: str, parts: dict, names: tuple[str, ...]) -> None:
    """Readable text on a dark fill the LLM's attributes put under these parts (element_refs.READS_ON)."""
    for p in names:
        parts[p]["color"] = cards._readable(fill, parts[p].get("color")) or ""
        if not parts[p]["color"]:
            del parts[p]["color"]


def card_item(comp: dict, i: int, name: str, box: dict, parts: dict, role: str, icon: str | None, focus: bool,
              number: str | None, dense: bool) -> etree._Element:
    """Card i in the composition's item form (also a card placed apart)."""
    cid, c = comp["component_id"], cards.cards_of(comp)[i]
    tint = "$accentText" if role == "neutral" else f"${role}Text"
    title, tag = str(c.get("title") or ""), str(c.get("tag") or "").upper()
    if name in ("grid", "grid numbered", "steps"):
        box = {"borderRadius": "8", **box}   # cards are rounded (user, 2026-10-13); code's, like today
        el = cards.assemble(comp, i, box, parts, role, "side" if dense else "stack", icon,
                            number if name == "steps" else None, name == "grid numbered")
        return el
    if name in ("rows", "rows numbered"):
        lead = (_card_text(f"{i + 1:02d}", 40, parts["number"], bold="true") if name == "rows numbered" else
                _stack("Icon", {"name": icon, "size": "28", **parts["icon"]}) if icon else None)
        head = _stack("VStack", {"w": "22%", "gap": "4"}, _card_text(tag, 13, parts["tag"], bold="true", letterSpacing="1")
                      if tag else None, _card_text(title, 26, parts["title"], bold="true"))
        return _stack("HStack", {"id": f"card-{cid}-{i}", **box},
                      _stack("VStack", {"w": "72"}, lead) if lead is not None else None, head,
                      _stack("VStack", {"w": "1", "grow": "1"}, _body(c, 20, parts["body"], tint)),
                      _stack("VStack", {"w": "30%"}, _bullets(c, 18, parts["body"])) if cards._lines(c)[1] else None)
    if name == "columns":
        _ink(parts["band"].get("backgroundColor", ""), parts, ("icon", "title"))
        pill = _stack("HStack", {"alignItems": "center", "justifyContent": "center", **parts["band"]},
                      _stack("Icon", {"name": icon, "size": "22", **parts["icon"]}) if icon else None,
                      _card_text(title, 20, parts["title"], bold="true"))
        cells = [_stack("VStack", {"grow": "1", "justifyContent": "center", **parts["bullets"]},
                        _card_text(b, 17, {k: v for k, v in parts["body"].items() if k != "color"})) for b in cards._lines(c)[1]]
        return _stack("VStack", {"id": f"card-{cid}-{i}", "alignItems": "stretch", **box},
                      _card_text(tag, 13, parts["tag"], bold="true", letterSpacing="1") if tag else None, pill,
                      _body(c, 16, parts["body"], tint), *cells)
    if name == "banded":
        _ink(parts["band"].get("backgroundColor", ""), parts, ("icon", "title", "tag"))
        band = _stack("HStack", {"alignItems": "center", **parts["band"]},
                      _stack("Icon", {"name": icon, "size": "22", **parts["icon"]}) if icon else None,
                      _stack("VStack", {"grow": "1"}, _card_text(title, 20, parts["title"], bold="true")),
                      _card_text(tag, 12, parts["tag"], bold="true", letterSpacing="1") if tag else None)
        inner = _stack("VStack", {"grow": "1", "gap": "10", "padding": "18"}, _body(c, 17, parts["body"], tint),
                       _bullets(c, 17, {**parts["body"], "color": parts["body"].get("color", "$textMuted")}))
        return _stack("VStack", {"id": f"card-{cid}-{i}", **box}, band, inner)
    # bento: the focus card as the big block, the others small
    _ink(box.get("backgroundColor", ""), parts, ("icon", "tag", "title", "body"))
    big = focus
    px = {"icon": 36, "tag": 13, "title": 30, "body": 20, "bullets": 18} if big else \
        {"icon": 22, "tag": 13, "title": 20, "body": 16, "bullets": 15}
    ink = "" if box.get("backgroundColor") in element_refs.READS_ON else tint
    icon_el = _stack("Icon", {"name": icon, "size": str(px["icon"]), **parts["icon"]}) if icon else None
    title_el = _card_text(title, px["title"], parts["title"], bold="true")
    tag_el = _card_text(tag, px["tag"], parts["tag"], bold="true", letterSpacing="1") if tag else None
    # a small card: the icon leads the tag line, as on a grid card, or the title when there is no tag
    head = ([icon_el, tag_el, title_el] if big else
            [_stack("HStack", {"gap": "10", "alignItems": "center"}, icon_el, tag_el), title_el] if tag else
            [_stack("HStack", {"gap": "10", "alignItems": "center"}, icon_el, title_el)])
    attrs = {"id": f"cardf-{cid}-{i}", "w": "40%", "justifyContent": "center", "borderRadius": "8", **box} if big else \
        {"id": f"card-{cid}-{i}", **box}
    return _stack("VStack", attrs, *head, _body(c, px["body"], parts["body"], ink), _bullets(c, px["bullets"], parts["body"]))


def _rows_of(xs: list[etree._Element], cols: int, gap: str) -> etree._Element:
    outer = _stack("VStack", {"gap": gap})
    for k in range(0, len(xs), cols):
        row = etree.SubElement(outer, "HStack", gap=gap, grow="1", alignItems="stretch")
        for t in xs[k:k + cols]:
            if t.get("w") is None:
                t.set("w", "1")
                t.set("grow", "1")
            row.append(t)
    return outer


def card_group(comp: dict, name: str, items: list[tuple[int, etree._Element]], gbox: dict, meta: dict,
               flag) -> str:
    cid, els = comp["component_id"], [e for _, e in items]
    if name in ("grid", "grid numbered", "steps"):
        layer = tiles._Layer(cards.card()["parts"])
        layer.box = dict(gbox)
        layout = "steps" if name == "steps" else "grid"
        return _xml(cards.build_group(comp, els, {k: v for k, v in meta.items() if k == "cols"}, layer, cid, flag, layout))
    gap = gbox.pop("gap", "18")
    if name in ("rows", "rows numbered"):
        for e in els:
            e.set("grow", "1")
        out = _stack("VStack", {"gap": gap, **gbox}, *els)
    elif name == "columns":
        out = _stack("HStack", {"gap": gap, "alignItems": "stretch", **gbox}, *[_peer(e) for e in els])
    elif name == "banded":
        n = len(els)
        out = _rows_of(els, -(-n // -(-n // 3)), gap)
        for k, v in gbox.items():
            out.set(k, v)
    else:   # bento: the big block, the rest 2 + 1 (2 + 2) beside it
        big = [e for e in els if e.get("id", "").startswith("cardf-")]
        rest = [e for e in els if e not in big]
        side = _rows_of(rest, 2, gap)
        side.set("grow", "1")
        out = _stack("HStack", {"gap": gap, "alignItems": "stretch", **gbox}, *big, side)
    if out.get("grow") is None and out.get("h") is None:
        out.set("grow", "1")
    return _xml(out)


def _peer(e: etree._Element) -> etree._Element:
    if e.get("w") is None:
        e.set("w", "1")
        e.set("grow", "1")
    return e


# ── colour by <Highlight> ─────────────────────────────────────────────────────
# The generator colour-codes items inside the group tag, as on tables and lists (2026-11-13: the gj-h1 and production
# CHEFFIN decks colour item by item: one tinted tile, a coloured edge or head per category or phase, a dark read-out):
#   <KpiRow ref="k"><Highlight item="Gross Margin" fill="bad"/><Highlight item="ARR" color="good"/></KpiRow>
#   <CardGrid ref="c"><Highlight item="*" edge="category"/><Highlight item="Scale" head="phase"/></CardGrid>
# item = an item's label / title (or its index, or * for every item). Carrier = the attribute: fill (the item's box),
# edge (a bar on its top, side="left" for the left), head (its band where the composition draws one, else a thick
# top edge), color (its key text). Meaning = the value: good / bad / watch / focus (status, accent), dark (inverted),
# category (each item its own series colour), phase (the light-to-dark order ramp). Code picks the tokens and inks.

HL_CARRIERS = ("fill", "edge", "head", "color")
HL_MEANINGS = ("good", "bad", "watch", "focus", "dark", "category", "phase")
HL_ATTRS = {"item", "side", *HL_CARRIERS}
_HL_STATUS = {"good": "positive", "bad": "negative", "watch": "warning", "focus": "accent"}
_HL_TEXT = {"kpi_row": ("label", "value", "delta", "icon"), "card_grid": ("tag", "title", "body", "icon", "number")}
_HL_KEY = {"kpi_row": ("value", "delta"), "card_grid": ("title", "tag", "icon")}
_HL_BAND_TEXT = {"kpi_row": ("label", "icon"), "card_grid": ("title", "tag", "icon")}
_HL_CATEGORIES = 6   # $chart1..$chart6: the palette's separable series colours


def _labels(comp: dict) -> list[str]:
    if comp["kind"] == "card_grid":
        return [str(c.get("title") or "") for c in cards.cards_of(comp)]
    return [str(v) for v in element_refs._list(comp, "kpi_labels")]


def highlights(comp: dict, body: str, flag) -> dict[int, list[tuple[str, str, str]]]:
    """The group's <Highlight> children -> {item: [(carrier, meaning, side)]}. An item name not in the plan or an
    unknown attribute / meaning is NODE_HIGHLIGHT_UNKNOWN (an error: the generator fixes it)."""
    cid, tag = comp["component_id"], node(comp["kind"])["tag"]
    try:
        kids = [k for k in etree.fromstring(f"<x>{body}</x>") if isinstance(k.tag, str) and k.tag == "Highlight"]
    except etree.XMLSyntaxError:
        if "<Highlight" in body:
            flag("NODE_HIGHLIGHT_UNKNOWN", cid, f'the children of <{tag} ref="{cid}"> are not readable XML: write only '
                 f'<Highlight .../> and item tags inside it.')
        return {}
    norm = lambda s: " ".join(str(s).split()).casefold()  # noqa: E731
    names = [norm(x) for x in _labels(comp)]
    out: dict[int, list[tuple[str, str, str]]] = {}

    def bad(msg: str) -> None:
        flag("NODE_HIGHLIGHT_UNKNOWN", cid, f'<Highlight> in <{tag} ref="{cid}">: {msg}')

    for h in kids:
        at = {k: " ".join(v.split()) for k, v in h.attrib.items()}
        if set(at) - HL_ATTRS:
            bad(f'unknown attribute {", ".join(sorted(set(at) - HL_ATTRS))} (use item, and one of fill / edge / head / '
                "color, side for an edge).")
            continue
        want = norm(at.get("item", ""))
        if want == "*":
            idx = list(range(len(names)))
        elif want.isdigit() and int(want) < len(names):
            idx = [int(want)]
        else:
            idx = [i for i, n in enumerate(names) if n == want] or [i for i, n in enumerate(names) if want and want in n]
            if len(idx) != 1:
                bad(f'item="{at.get("item", "")}" names no single item; use one of: '
                    + ", ".join(f'"{x}"' for x in _labels(comp)) + ', or "*".')
                continue
        for carrier in HL_CARRIERS:
            meaning = at.get(carrier, "").lower()
            if not meaning:
                continue
            if meaning not in HL_MEANINGS:
                bad(f'{carrier}="{meaning}": use {" / ".join(HL_MEANINGS)}.')
                continue
            for i in idx:
                out.setdefault(i, []).append((carrier, meaning, at.get("side", "top").lower()))
    return out


def _phase_step(i: int, n: int, lightest: int = 1) -> int:
    """Item i of n on the 5-step ramp, light to dark; one item takes the darkest. A thin edge starts at step 2: step 1
    vanished on a light slide (look3 redraw 2026-11-13)."""
    return 5 if n <= 1 else lightest + round(i * (5 - lightest) / (n - 1))


def paint(comp: dict, name: str, i: int, marks: list[tuple[str, str, str]], box: dict, parts: dict, flag) -> None:
    """Lay item i's <Highlight>s over its resolved (box, parts), in place: they come last, so they win."""
    kind, cid = comp["kind"], comp["component_id"]
    n, c = count(comp), node(kind)["compositions"][name]
    band = "band" in parts and "band" not in (c.get("ignores") or [])

    def ink(names: tuple[str, ...], colour: str) -> None:
        for p in names:
            if p in parts:
                parts[p]["color"] = colour

    def edge(token: str, side: str, width: str = "5") -> None:
        # rows draw their divider as a top border: an edge there goes on the left
        s = "Left" if side == "left" or name in ("rows", "rows numbered") else "Top"
        box[f"border{s}.color"], box[f"border{s}.width"] = token, width

    for carrier, meaning, side in marks:
        k = _phase_step(i, n, 2 if carrier == "edge" else 1)
        if meaning in _HL_STATUS:
            r = _HL_STATUS[meaning]
            solid, soft, text, deep, on_deep = f"${r}", f"${r}Soft", f"${r}Text", f"${r}Dark", "$onPanelDark"
            if meaning == "focus":
                deep, on_deep = "$accent", "$onAccent"
        elif meaning == "dark":
            solid = soft = deep = "$panelDark"
            text = on_deep = "$onPanelDark"
        elif meaning == "phase":
            solid = soft = deep = f"$step{k}"
            text = on_deep = f"$onStep{k}"
        else:   # category
            solid = deep = f"$chart{i % _HL_CATEGORIES + 1}"
            soft = text = ""
            on_deep = "$inkLight"   # bold head text on a mid-tone series colour (LOW_CONTRAST reports a weak pair)
        if carrier == "color":
            if meaning not in _HL_STATUS:
                flag("NODE_HIGHLIGHT_RULE", f"{cid}.{i}", f'color="{meaning}": text colours are good / bad / watch / '
                     "focus; drawn as an edge.")
                edge(solid, side)
                continue
            ink(_HL_KEY[kind], text)
        elif carrier == "fill":
            if meaning == "category":
                flag("NODE_HIGHLIGHT_RULE", f"{cid}.{i}", 'fill="category": a category colours an edge or a head, not '
                     "the box; drawn as an edge.")
                edge(solid, side)
                continue
            box["backgroundColor"] = soft
            if "border.color" in box:
                box["border.color"] = solid
            if meaning in _HL_STATUS:
                ink(_HL_KEY[kind], text)
            else:   # a dark or ramp fill: every text reads on it, flat like the code's own dark card
                ink(_HL_TEXT[kind], text)
                for key in [key for key in box if key.startswith("shadow.")]:
                    del box[key]
        elif carrier == "edge":
            edge(solid, side)
        else:   # head
            if band:
                parts["band"]["backgroundColor"] = deep
                ink(_HL_BAND_TEXT[kind], on_deep)
            else:
                edge(solid, "top", "8")
                if meaning in _HL_STATUS:
                    ink(_HL_KEY[kind][:1], text)


# ── one group ─────────────────────────────────────────────────────────────────

def draw(comp: dict, gattrs: dict[str, str] | None, kids: dict[int, dict], apart: set[int], flag,
         second: bool = False, marks: dict[int, list] | None = None) -> tuple[str, dict[int, str], dict]:
    """A component's group tag (attrs; None when only items placed apart) -> (the group's XML, {placed-apart item:
    its XML}, what was drawn). `kids`: item tags inside the group by index; `apart`: items whose tag stands elsewhere
    (their attrs in kids too); `second`: a slide's second card group (today: drawn as open columns)."""
    kind, cid = comp["kind"], comp["component_id"]
    nd = node(kind)
    gattrs = _structure(gattrs or {}, nd, cid, flag)
    meta, gbox, gparts = compose.read(gattrs, cid, flag, nd)
    asked = meta.get("variant")
    hint_word, style, item_styles = (None, None, {}) if asked else _hint(nd, comp, flag)
    name, extra = compose.composition(nd, comp, asked or hint_word, cid, flag)
    compose.undrawn(nd, name, gbox, gparts, cid, flag)
    for i, (_, ibox, iparts) in kids.items():   # an item tag's box is its `item.`; placed apart, it sizes itself (w, grow)
        compose.undrawn(nd, name, {}, iparts if i in apart else {**iparts, "item": ibox}, f"{cid}.{i}", flag, nd["item_tag"])
    style = extra.get("style") or style or ("column" if second and kind == "card_grid" else None)
    focus_i = emphasis_index(comp)
    c = nd["compositions"][name]
    emph_ok = focus_i is not None and not spec.failed_requires({"requires": c.get("emphasis_requires") or []}, comp)
    n = count(comp)
    numbers = [None] * n
    if kind == "card_grid" and name == "steps" and cards.numbered_ok(comp):
        numbers = [f"{k + 1:02d}" for k in range(n)]
    icons = element_refs._list(comp, "kpi_icons") if kind == "kpi_row" else [c_.get("icon") for c_ in cards.cards_of(comp)]
    dense = kind == "card_grid" and cards.dense(comp)
    drawn: dict[int, Any] = {}
    for i in range(n):
        item = kids.get(i)
        color = (item[0].get("color") if item else None) or meta.get("color")
        if color and color not in tiles.ROLE_OF:
            flag("NODE_ATTR_DROPPED", cid, f'color="{color}" on ref="{cid}": one of {", ".join(tiles.ROLE_OF)}; the plan '
                 "tone used.")
        role = role_of(comp, i, color)
        focus = emph_ok and i == focus_i
        rec = compose.recipe(nd["styles"].get(item_styles.get(i) or style or "", ""))
        box, parts, hero = item_style(nd, name, comp, i, role, focus, rec, gparts, item)
        if marks and marks.get(i):
            paint(comp, name, i, marks[i], box, parts, flag)
        if item and item[0].get("size") == "hero" and not hero:
            flag("NODE_VARIANT_UNMET", f"{cid}.{i}", f'size="hero" on ref="{cid}.{i}" needs the plan\'s emphasis item; '
                 "normal used.")
        icon = (item[0].get("icon") if item else None) or meta.get("icon") or (icons[i] if i < len(icons) else "") or ""
        if kind == "kpi_row":
            drawn[i] = kpi_item(comp, i, name, box, parts, hero, icon, focus)
        else:
            drawn[i] = card_item(comp, i, name, box, parts, role, icon or None, focus, numbers[i], dense)
    # dividers: before every item of a strip / rows after the first (in the group's order)
    mine = [i for i in range(n) if i not in apart]
    if name in ("strip", "rows") or (kind == "card_grid" and name in ("rows", "rows numbered")):
        for k, i in enumerate(mine[1:]):
            side = "Left" if name == "strip" else "Top"
            div = {p: {} for p in nd["parts"]}
            _put({}, div, nd["compositions"][name].get("look") or {}, "accent")
            div["divider"].update(gparts.get("divider") or {})
            extra_box: dict[str, str] = {}
            _divide(extra_box, div, side, gbox.get("gap", "28") if side == "Left" else None)
            if isinstance(drawn[i], str):
                drawn[i] = _first(drawn[i], **extra_box)
            else:
                for k2, v in extra_box.items():
                    drawn[i].set(k2, v)
    gb = group_look(nd, name, gbox)
    group = ""
    if gattrs is not None and mine and kind == "kpi_row":
        group = kpi_group(comp, name, [(i, drawn[i]) for i in mine], gb, meta, flag)
    elif gattrs is not None and mine:
        group = card_group(comp, name, [(i, drawn[i]) for i in mine], gb, meta, flag)
    alone = {i: (drawn[i] if isinstance(drawn[i], str) else _xml(drawn[i])) for i in apart}
    return group, alone, {"composition": name, "focus": focus_i if emph_ok else None, "items": len(mine) + len(apart)}


# ── the slide ─────────────────────────────────────────────────────────────────

def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every group / item tag of the kinds switched on, drawn from the plan."""
    out = {"xml": xml, "issues": [], "ok": True, "components": {}}
    for kind in kinds_on():
        r = _expand_kind(out["xml"], plan, kind)
        out = {"xml": r["xml"], "issues": out["issues"] + r["issues"], "ok": out["ok"] and r["ok"],
               "components": {**out["components"], **r["components"]}}
    return out


def _expand_kind(xml: str, plan: dict | None, kind: str) -> dict[str, Any]:
    nd = node(kind)
    issues: list[dict[str, Any]] = []

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY.get(code, compose.WARNING), "ref": ref, "message": message})

    gtag, itag = nd["tag"], nd["item_tag"]
    gtags = {gtag, *(nd.get("tag_aliases") or {})}
    comps = components(plan, kind)
    ids = ", ".join(comps) or "none"
    tags = [t for t in validate.ref_tags(xml) if t["tag"] in gtags | {itag}]
    if not tags:
        return {"xml": xml, "issues": [], "ok": True, "components": {}}

    def item_key(t: dict, group: str | None) -> tuple[str, int] | None:
        ref = t["attrs"]["ref"]
        m = _ITEM_REF.match(ref)
        if not m or m["cid"] not in comps:
            flag("NODE_REF_UNKNOWN", ref, f'<{itag} ref="{ref}">: an item is <{itag} ref="<{kind} id>.<index>"/> with a '
                 f"{kind} id from the plan ({ids}).")
            return None
        if group is not None and m["cid"] != group:
            flag("NODE_REF_UNKNOWN", ref, f'<{itag} ref="{ref}"> inside <{gtag} ref="{group}">: an item in a group names '
                 "that group's component; place it outside the group.")
            return None
        if int(m["i"]) >= count(comps[m["cid"]]):
            flag("NODE_REF_UNKNOWN", ref, f'<{itag} ref="{ref}">: {m["cid"]} has {count(comps[m["cid"]])} items.')
            return None
        return m["cid"], int(m["i"])

    apart: dict[tuple[str, int], dict] = {}
    groups: dict[str, dict] = {}
    for t in tags:
        if t["tag"] == itag:
            key = item_key(t, None)
            if key and key in apart:
                flag("NODE_REF_DUPLICATE", t["attrs"]["ref"], f'<{itag} ref="{t["attrs"]["ref"]}"> is placed twice; '
                     "place each item once.")
                t["drop"] = True
            elif key:
                apart[key] = t
            else:
                t["drop"] = True
            continue
        cid = t["attrs"]["ref"]
        if t["tag"] != gtag:
            flag("NODE_TAG_ALIAS", cid, f'<{t["tag"]} ref="{cid}"> is now <{gtag} ref="{cid}">.')
        if cid not in comps:
            flag("NODE_REF_UNKNOWN", cid, f'<{gtag} ref="{cid}">: no {kind} component with this id ({ids}).')
            t["drop"] = True
        elif cid in groups:
            flag("NODE_REF_DUPLICATE", cid, f'<{gtag} ref="{cid}"> is placed twice; one group draws every item.')
            t["drop"] = True
        else:
            groups[cid] = t
    result: dict[str, dict] = {}
    for cid in list(dict.fromkeys(list(groups) + [c for c, _ in apart])):
        comp, g = comps[cid], groups.get(cid)
        kids: dict[int, tuple] = {}
        marks: dict[int, list] = {}
        if g is not None:
            marks = highlights(comp, g["body"], flag)
            for k in validate.ref_tags(g["body"]):
                key = item_key(k, cid) if k["tag"] == itag else None
                if k["tag"] != itag:
                    continue
                if key and (key in apart or key[1] in kids):
                    flag("NODE_REF_DUPLICATE", k["attrs"]["ref"], f'<{itag} ref="{k["attrs"]["ref"]}"> is placed twice; '
                         "place each item once.")
                elif key:
                    kids[key[1]] = _item_read(k["attrs"], node(kind), k["attrs"]["ref"], flag)
            if re.sub(rf"<(?:{itag}|Highlight)\b[^<>]*?/>", "", g["body"]).strip():
                flag("NODE_ATTR_DROPPED", cid, f'children inside <{gtag} ref="{cid}"> other than <{itag}/> and '
                     "<Highlight/> tags: code writes the group from the plan; removed.")
        mine_apart = {i for c, i in apart if c == cid}
        for i in mine_apart:
            kids[i] = _item_read(apart[(cid, i)]["attrs"], nd, f"{cid}.{i}", flag)
        second = kind == "card_grid" and g is not None and sum(1 for c in groups if c != cid
                                                               and groups[c]["start"] < g["start"]) > 0
        group, alone, info = draw(comp, g["attrs"] if g else None, kids, mine_apart, flag, second, marks)
        ids = (lambda x: x) if info["composition"] in TODAY else compose.inner_ids   # today's forms: as today
        if g is not None:
            g["xml"] = ids(group)
        for i, x in alone.items():
            apart[(cid, i)]["xml"] = ids(x)
        result[cid] = info
        if g is None and kind == "card_grid" and len(mine_apart) < count(comp):
            for k in sorted(set(range(count(comp))) - mine_apart):
                flag("NODE_ITEM_MISSING", f"{cid}.{k}", f'{cid} card {k} is not on the slide: draw it in <{gtag} '
                     f'ref="{cid}"/> or place it with <{itag} ref="{cid}.{k}"/>.')
    out, pos = [], 0
    for t in tags:
        out.append(xml[pos:t["start"]])
        pos = t["end"]
        out.append(t.get("xml", "") if not t.get("drop") else "")
    out.append(xml[pos:])
    uniq = {(i["code"], i["ref"], i["message"]): i for i in issues}
    issues = list(uniq.values())
    return {"xml": "".join(out), "issues": issues, "ok": not any(i["severity"] == compose.ERROR for i in issues),
            "components": result}


# ── prompt ─────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines for the kinds switched on (the cached part of the system prompt)."""
    lines = ["## KPI TILES AND CARDS (code draws them from the plan)"]
    for kind in kinds_on():
        nd = node(kind)
        parts = " ".join(f"{p}." for p in nd["parts"])
        lines.append(f'<{nd["tag"]} ref="<{kind} id>" variant="..."/>: variant = ' + "; ".join(
            f"{n} ({v})" for n, v in nd["prompts"].items())
            + f'. Inside, <{nd["item_tag"]} ref="<id>.<index>"/> restyles one item; outside, places it anywhere in its '
            f"group's form. Parts: {parts}")
        # a recipe that tints every box by its tone ($toneSoft) is not offered: box colour is a <Highlight> per item
        lines.append("Style recipes (attributes, write them on the group or an item): "
                     + "; ".join(f"{k}: {v}" for k, v in nd["styles"].items() if "$toneSoft" not in v) + ".")
    lines.append("Self-closing items: code writes every word, number, size, column and the emphasis item. Style is "
                 "attributes in $tokens: item.<box attribute> styles every item's box, <part>.<attribute> every item's "
                 "part; $tone / $toneSoft / $toneText follow each item's tone (good / bad / watch, else the accent). "
                 "No fontSize.")
    lines += [
        "COLOUR CODE with <Highlight/> inside the group tag: code colours an item's number by its tone, nothing else. "
        "Every box colour is YOUR choice, per item, for what the item means:",
        '  <Highlight item="<label or title, or *>" fill|edge|head|color="<meaning>"/> (edge may add side="left")',
        "  fill = the item's box tinted · edge = a bar on its top · head = its solid band (banded, columns; else a thick "
        "top bar) · color = its number / title only",
        "  good / bad / watch = status (wins, losses, watch) · focus = the one the headline names · dark = an inverted "
        "item · category = each item its own colour (pillars, segments, platforms; an edge or a head) · phase = a "
        "light-to-dark order (stages, months, steps)",
        "  A fill marks a difference: the bad metric among good ones, the item the headline names. Items that all "
        "mean the same take no fill (one colour on all = no meaning); give them an edge or head by category or "
        "phase, or leave them plain.",
        '  <KpiRow ref="snapshot"><Highlight item="Gross Margin" fill="bad"/><Highlight item="CAC Payback" '
        'fill="watch"/></KpiRow>',
        '  <CardGrid ref="pillars" variant="banded"><Highlight item="*" head="category"/></CardGrid>',
        '  <CardGrid ref="roadmap"><Highlight item="*" edge="phase"/><Highlight item="Scale" fill="dark"/></CardGrid>',
        "  Hint words -> Highlight: 'X in negative / positive / warning' -> fill or color bad / good / watch on X; "
        "'focus on X', 'tint X' -> fill=\"focus\"; 'dark / inverted X' -> fill=\"dark\"; 'accent border' -> edge=\"focus\" side=\"left\" (on X, or *); "
        "'by stage / phase' -> phase; 'each pillar / segment / platform its colour' -> category; 'lift / elevate' -> "
        'item.shadow.type="outer" item.shadow.blur="6" item.shadow.offset="2" on the group; \'all positive / equal '
        "toned' -> no fill (code colours the numbers), an edge or head by category or phase if the items are "
        "parallel or ordered. Never item.backgroundColor with a status or Soft token on the group.",
        "  Each group's line under THIS SLIDE lists the Highlights its plan fits; pick by the hint, or none.",
    ]
    return "\n".join(lines)


def tag_attributes(kind: str) -> list[str]:
    nd = node(kind)
    box = [a.split(".")[0] + ".*" if "." in a else a for a in tiles.data()["box_attributes"]]
    return list(dict.fromkeys(nd["meta"] + [f"{p}.*" for p in nd["parts"]] + ["borderRadius"] + box))


def item_attributes(kind: str) -> list[str]:
    nd = node(kind)
    box = [a.split(".")[0] + ".*" if "." in a else a for a in tiles.data()["box_attributes"]]
    return list(dict.fromkeys(nd["item_meta"] + [f"{p}.*" for p in nd["parts"]] + box))


def tags_contract(kind: str) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """(tags, hierarchy lines, {tag: attributes}) for the generator's ALLOWED NODES (as tiles.tags_contract)."""
    nd = node(kind)
    g, it = nd["tag"], nd["item_tag"]
    return [g, it, "Highlight"], [f"  <{g}> -> {it}, Highlight", f"  <{it}> -- LEAF (no children)",
                                  "  <Highlight> -- LEAF (no children)"], {g: tag_attributes(kind),
                                                                            it: item_attributes(kind),
                                                                            "Highlight": sorted(HL_ATTRS)}


def prompt_line(comp: dict, headline: str = "") -> str:
    kind, cid = comp["kind"], comp["component_id"]
    nd, n, f = node(kind), count(comp), emphasis_index(comp)
    ok = [w for w, v in nd["compositions"].items() if not spec.failed_requires(v, comp)]
    if kind == "kpi_row":
        labels = element_refs._list(comp, "kpi_labels")
        head = f"KPI TILES {cid}: {n} items (0-{n - 1}); items " + ", ".join(f"{i} {labels[i] if i < len(labels) else ''}".strip()
                                                                            for i in range(n))
        tones = element_refs._list(comp, "kpi_tones")
    else:
        cs = cards.cards_of(comp)
        head = (f"CARDS {cid}: {n} cards (0-{n - 1}), {cards.layout_of(comp)}; titles "
                + ", ".join(f"{i} {str(c.get('title') or '')}".strip() for i, c in enumerate(cs)))
        tones = [cards.tone_of(comp, i) for i in range(n)]
    parts = [head, f"emphasis {f}" if f is not None else "no emphasis item",
             ("tones " + " ".join(f"{i}={t}" for i, t in enumerate(tones) if t) + " (code colours the numbers; box "
              "colour only by <Highlight>)") if any(tones) else "no tones",
             "variants " + " | ".join(ok)]
    return ("; ".join(parts) + f'. <{nd["tag"]} ref="{cid}"/> (or with <Highlight/> inside) or <{nd["item_tag"]} '
            f'ref="{cid}.N"/>; never type a label, value or title yourself: code writes them from the plan'
            + highlight_options(comp, tones))


def highlight_options(comp: dict, tones: list[str]) -> str:
    """The colour codes this group's plan fits, for the generator to choose from (the hint decides; none is drawn
    unless written): status fills on the items whose tone differs from the rest, phases on ordered cards, categories
    on parallel cards whose tones are alike."""
    labels, n = _labels(comp), count(comp)
    name = lambda i: (labels[i] if i < len(labels) and labels[i] else str(i)).replace('"', "'")
    set_ = [t for t in tones if t]
    common = max(sorted(set(set_)), key=set_.count) if set_ else ""
    odd = [i for i, t in enumerate(tones) if t and (t != common or len(set(set_)) == 1 and len(set_) < n)]
    opts = []
    if odd and len(odd) < n:
        opts.append(" ".join(f'<Highlight item="{name(i)}" fill="{tones[i]}"/>' for i in odd[:3]))
    if comp["kind"] == "card_grid" and n >= 3:
        if cards.layout_of(comp) == "steps":
            opts.append('<Highlight item="*" head="phase"/> (or edge="phase")')
        elif not odd:
            opts.append('<Highlight item="*" edge="category"/> (or head="category")')
    return (". Colour code that fits this plan (by the hint, or none): " + " | ".join(opts)) if opts else ""
