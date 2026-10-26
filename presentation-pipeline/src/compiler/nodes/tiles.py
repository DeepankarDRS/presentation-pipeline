"""KPI tile nodes (docs/tile-nodes-spec-2026-10-12.md §2, §4), `POM_BLOCKS=tiles`.

The LLM writes KPI tiles like a native POM data node, a group tag and an item tag:

    <KpiGrid ref="kpis" variant="plain" cols="2" icon.color="$accent">     every item, plan order
      <Kpi ref="kpis.2" variant="toned" icon="alert-triangle"/>             restyles one item
    </KpiGrid>
    <Kpi ref="kpis.4" variant="inverted" size="hero" w="36%"/>              places one item anywhere

and code expands each tile into the tile the element-ref route draws by hand (a VStack holding
<Text ref="kpis.2.label|value|note"/>, an Icon, a marker Shape), from the looks in
block-variants.yaml `tile_nodes.kpi`. element_refs.fill_refs then writes the text, so both routes get
the same kpiv- / kpih- ids, unit spans, readable colours on dark fills and fit-grow treatment.
A tile written by hand with <Text ref> stays valid (T2) and is counted (`hand_items`).

    result = fill(xml, plan)      # the shape of element_refs.fill_refs; components[cid] adds
                                  # tile_items (drawn from tile tags) and hand_items (from hand refs)

Attributes resolve in this order, later wins: house look -> group variant -> group attributes ->
item variant -> item attributes. `color` picks the role ({role} in a look); its default is the
plan tone; an item with its own `color` and no variant of its own takes its variant's `with_color` look
(plain -> toned), so the colour always shows; with no colour asked, its plan tone takes `with_tone` (plain: bad /
watch -> toned, good -> the number in that colour). `inverted` and size="hero" only on the item the plan singles
out (is_emphasis_item).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml
from lxml import etree

from src.compiler.nodes import element_refs, spec

ERROR, WARNING, REPORT = element_refs.ERROR, element_refs.WARNING, element_refs.REPORT
SEVERITY = {
    "NODE_REF_UNKNOWN": ERROR, "NODE_REF_DUPLICATE": ERROR, "NODE_ITEM_MISSING": ERROR, "NODE_ATTR_UNKNOWN": ERROR,
    "NODE_VARIANT_UNKNOWN": WARNING, "NODE_VARIANT_UNMET": WARNING, "LITERAL_COLOR": WARNING,
    "NODE_ATTR_DROPPED": REPORT, "NODE_LOOK_FROM_HINT": REPORT,
}

_FILE = Path(__file__).resolve().parents[2] / "knowledge" / "core" / "block-variants.yaml"
GROUP, ITEM = "KpiGrid", "Kpi"
GROUP_META = {"ref", "layout", "cols", "variant", "arrange", "color", "icon"}
ITEM_META = {"ref", "variant", "arrange", "size", "color", "icon"}
ROLE_OF = {"$accent": "accent", "$positive": "positive", "$negative": "negative", "$warning": "warning",
           "$neutral": "neutral"}
ICON_PX = 22      # code-owned (T3): beside a 16 px tile label (element_refs.LABEL_PX)
GROUP_GAP = 14    # between tiles (the pilot gallery)
INLINE_GAP = 14   # between the label column and the value of an inline tile (the house gap 6 lets them touch)
_ITEM_REF = re.compile(r"^(?P<cid>[\w-]+)\.(?P<i>\d+)$")
_HEX = re.compile(r"^#?[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")


@functools.lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    return yaml.safe_load(_FILE.read_text(encoding="utf-8"))["tile_nodes"]


def kpi() -> dict[str, Any]:
    return data()["kpi"]


def on() -> bool:
    return element_refs.mode() == "tiles"


def role_value(value: Any, role: str) -> str:
    """A look value with {role} filled: "${role}Soft" -> "$negativeSoft"; $neutral has no Soft / Text."""
    s = str(value)
    if "${role}" not in s:
        return s
    if role == "neutral":
        return s.replace("${role}Soft", "$surfaceAlt").replace("${role}Text", "$textMain").replace("${role}", "$neutral")
    return s.replace("${role}", f"${role}")


def tone_of(comp: dict, i: int) -> str:
    """The plan's tone of item i: good / bad / watch, or "" (plan_checks.settle_kpi_tones)."""
    tones = element_refs._list(comp, "kpi_tones")
    role = element_refs.TONE_ROLE.get(str(tones[i]).lower(), "") if i < len(tones) and tones[i] else ""
    return {"positive": "good", "negative": "bad", "warning": "watch"}.get(role, "")


def tone_role(comp: dict, i: int) -> str:
    tones = element_refs._list(comp, "kpi_tones")
    return element_refs.TONE_ROLE.get(tones[i].lower(), "accent") if i < len(tones) and tones[i] else "accent"


def emphasis_index(comp: dict) -> int | None:
    """The item the plan singles out (design_hint, emphasis_from); the LLM never picks it."""
    return element_refs.focus_index(comp)


# ── attributes ────────────────────────────────────────────────────────────────

class _Layer:
    """One layer of the resolution order: tile box attributes and part attributes."""

    def __init__(self, parts: dict[str, str] | None = None) -> None:
        self.box: dict[str, str] = {}
        self.parts: dict[str, dict[str, str]] = {p: {} for p in (parts or kpi()["parts"])}

    def put(self, key: str, value: Any) -> None:
        head, _, rest = key.partition(".")
        if head in self.parts and rest:
            self.parts[head][rest] = str(value)
        else:
            self.box[key] = str(value)


def _look(look: dict, role: str, parts: dict[str, str] | None = None) -> _Layer:
    layer = _Layer(parts)
    for k, v in (look or {}).items():
        layer.put(k, role_value(v, role))
    return layer


def _is_colour_attr(key: str) -> bool:
    last = key.rsplit(".", 1)[-1]
    return last in ("color", "bgColor", "backgroundColor") or last.endswith("Color")


def _read(el: etree._Element, meta_names: set[str], flag, block: dict | None = None,
          item_tag: str = ITEM) -> tuple[dict[str, str], _Layer, _Layer]:
    """(meta, box layer, part layer) of a tile tag. Box attributes on a group are the group's own box.
    `block`: the tile_nodes entry (kpi, card); `item_tag`: its item tag."""
    ref = el.get("ref")
    d = data()
    dropped_box, dropped_parts = set(d["dropped"]["box"]), set(d["dropped"]["parts"])
    box_ok, part_nodes, parts = set(d["box_attributes"]), d["part_nodes"], (block or kpi())["parts"]
    meta, box, partl = {}, _Layer(parts), _Layer(parts)
    for k, v in el.attrib.items():
        if k in meta_names:
            meta[k] = v
            continue
        if _is_colour_attr(k) and not str(v).startswith("$"):
            flag("LITERAL_COLOR" if _HEX.match(str(v)) else "NODE_ATTR_DROPPED", ref,
                 f'{k}="{v}" on <{el.tag} ref="{ref}">: colours are $tokens; removed.')
            continue
        head, _, rest = k.partition(".")
        if head in parts and rest:
            node = parts[head]
            if rest in dropped_parts:
                flag("NODE_ATTR_DROPPED", ref, f'{k} on <{el.tag} ref="{ref}">: code owns the {rest}; removed.')
            elif rest not in part_nodes[node]:
                flag("NODE_ATTR_UNKNOWN", ref, f'{k} on <{el.tag} ref="{ref}">: {head} is a <{node}>; its attributes are '
                     f'{", ".join(part_nodes[node])}.')
            elif head == "icon" and rest == "name":
                meta["icon"] = v
            else:
                partl.parts[head][rest] = v
        elif k in dropped_box or k in dropped_parts:
            flag("NODE_ATTR_DROPPED", ref, f'{k} on <{el.tag} ref="{ref}">: code owns it; removed.')
        elif k in box_ok:
            box.box[k] = v
        else:
            flag("NODE_ATTR_UNKNOWN", ref, f'{k} on <{el.tag} ref="{ref}">: not a {el.tag} attribute (meta: '
                 f'{", ".join(sorted(meta_names))}; parts {" ".join(p + "." for p in parts)}; box attributes as a VStack).')
    if (el.text or "").strip() or (len(el) and el.tag == item_tag):
        flag("NODE_ATTR_DROPPED", ref, f'text or children inside <{el.tag} ref="{ref}">: code writes the tile from the plan; removed.')
    return meta, box, partl


def _choice(name: str, value: str | None, values: list[str], ref: str | None, flag) -> str | None:
    if value is None or value in values:
        return value
    flag("NODE_ATTR_DROPPED", ref, f'{name}="{value}" on ref="{ref}": one of {", ".join(values)}; default used.')
    return None


# ── one tile ──────────────────────────────────────────────────────────────────

def _variant(comp: dict, i: int, asked: str | None, ref: str, flag, group: bool = False) -> str:
    """`ref`: the tag that asked (a group's id, so its fallback is reported once); `group`: a group's variant
    (is_group: divided is a group look)."""
    vs = kpi()["variants"]
    extra = {"is_emphasis_item": emphasis_index(comp) == i, "is_group": group}
    name, code, note = spec.resolve_variant("kpi_row", ITEM, comp, asked, vs=vs, extra=extra)
    if code:
        flag(code, ref, f"ref=\"{ref}\": {note}.")
    return name or next(iter(vs))


def hint_looks(comp: dict, gmeta: dict, overrides: dict[int, tuple], flag, block: dict, group_tag: str,
               emphasis: int | None, alone: bool = False, skip: set[int] | frozenset = frozenset()) -> None:
    """A bare group (no variant from the LLM) takes the look its plan's design_hint asks for
    (plan_checks.look_from_hint, docs/tile-variant-choice-spec-2026-10-26.md option A: in combined check arm B the
    LLM named a variant on 0 of 13 KpiGrids and 1 of 32 CardGrids, while saved hints ask for bars, dots, dark tiles).
    The group's look, then an item's own on items with no variant of their own, then the emphasis item's (inverted
    when its `requires` hold: a single tile stays plain, user 2026-10-26). A look whose `requires` fail is not
    applied (the LLM did not ask for it: no NODE_VARIANT_UNMET). In place on gmeta / overrides; info
    NODE_LOOK_FROM_HINT per pick. `block`: the tile_nodes entry (kpi, card); `emphasis`: the plan's emphasis item.
    `alone`: `overrides` are the component's items placed outside any group: the group's look goes on each of them
    with no variant of its own, and only they are touched (replay 2026-10-26: two gj-h1 slides of lone <Kpi> tags).
    `skip`: items the group does not draw (placed outside it)."""
    if gmeta.get("variant"):
        return
    from src.agents.plan_checks import look_from_hint   # src.agents imports the validator, which imports this
    look = look_from_hint(comp)
    cid, cue, vs = comp["component_id"], ", ".join(look["cues"]), block["variants"]

    def unmet(v: str, i: int | None) -> bool:
        return v not in vs or bool(spec.failed_requires(vs[v], comp, {"is_emphasis_item": i is not None and i == emphasis,
                                                                      "is_group": i is None}))
    if look["group"] and not alone and not unmet(look["group"], None):
        gmeta["variant"] = look["group"]
        flag("NODE_LOOK_FROM_HINT", cid, f'<{group_tag} ref="{cid}"> drawn variant="{look["group"]}" from the design '
             f'hint ({cue}).')
    items = {i: look["group"] for i in overrides} if alone and look["group"] else {}
    items.update(look["items"])
    if look["emphasis"] and emphasis is not None:
        items[emphasis] = look["emphasis"]
    for i, v in sorted(items.items()):
        if (alone and i not in overrides) or i in skip:
            continue
        meta = overrides.get(i) or ({}, _Layer(block["parts"]), _Layer(block["parts"]))
        if meta[0].get("variant") or unmet(v, i):
            continue
        meta[0]["variant"] = v
        overrides[i] = meta
        flag("NODE_LOOK_FROM_HINT", f"{cid}.{i}", f'item {i} of <{group_tag} ref="{cid}"> drawn variant="{v}" from '
             f'the design hint ({cue}).')


def _text(ref: str, attrs: dict[str, str], hero: bool = False) -> etree._Element:
    el = etree.Element("Text", ref=ref)
    for k, v in attrs.items():
        el.set(k, v)
    if hero:
        el.set("size", "hero")
    return el


def _icon(name: str, attrs: dict[str, str]) -> etree._Element:
    el = etree.Element("Icon", name=name, size=str(ICON_PX))
    for k, v in attrs.items():
        el.set(k, v)
    return el


def _marker(attrs: dict[str, str]) -> etree._Element | None:
    if not attrs.get("shapeType"):
        return None
    el = etree.Element("Shape")
    for k, v in attrs.items():
        el.set(k, v)
    return el


def _row(lead: etree._Element | None, label: etree._Element | None, gap: int) -> etree._Element | None:
    if lead is None:
        return label
    row = etree.Element("HStack", gap=str(gap), alignItems="center")
    row.append(lead)
    if label is not None:
        row.append(label)
    return row


def build_tile(comp: dict, i: int, group: tuple[dict, _Layer] | None, item: tuple[dict, _Layer, _Layer] | None,
               flag, panel: str | None = None) -> etree._Element:
    """One item's tile, its layers resolved (house -> group variant -> group attrs -> item variant -> item attrs).
    `panel`: the fill of the LLM's own box around the tag (panel_fill)."""
    cid = comp["component_id"]
    ref = f"{cid}.{i}"
    gmeta, gparts = group if group else ({}, _Layer())
    imeta, ibox, iparts = item if item else ({}, _Layer(), _Layer())
    role = ROLE_OF.get(imeta.get("color") or gmeta.get("color") or "", tone_role(comp, i))
    for m in (gmeta, imeta):
        if m.get("color") and m["color"] not in ROLE_OF:
            flag("NODE_ATTR_DROPPED", m.get("ref"), f'color="{m["color"]}" on ref="{m.get("ref")}": one of {", ".join(ROLE_OF)}; '
                 "the plan tone used.")
    vs = kpi()["variants"]
    # an item's own variant replaces the group's (its look does not sit on the group variant's, e.g. a plain
    # hairline under an inverted tile); the group's attributes still apply under it
    layers = [_look(kpi()["house_look"], role)]
    if not imeta.get("variant"):
        name = _variant(comp, i, gmeta.get("variant"), cid, flag, group=group is not None)
        patch: dict = {}
        if imeta.get("color") in ROLE_OF:   # the item's own colour is its tone: a look that shows it
            how = vs[name].get("with_color", name)
            name, patch = (how, {}) if isinstance(how, str) else (name, how)
        elif not gmeta.get("color") and tone_of(comp, i):   # the plan's tone, no colour asked: its look
            how = (vs[name].get("with_tone") or {}).get(tone_of(comp, i))
            name, patch = (how, {}) if isinstance(how, str) else (name, how or {})
        layers += [_look(vs[name]["look"], role), _look(patch, role)]
    layers.append(gparts)
    if imeta.get("variant"):
        layers.append(_look(vs[_variant(comp, i, imeta["variant"], ref, flag)]["look"], role))
    layers += [ibox, iparts]
    box: dict[str, str] = {}
    parts: dict[str, dict[str, str]] = {p: {} for p in kpi()["parts"]}
    for layer in layers:
        box.update(layer.box)
        for p, a in layer.parts.items():
            parts[p].update(a)
    # part colours may name {role} only through the looks; an LLM value is a token already
    if panel and box.get("backgroundColor") == panel:
        # on the LLM's own panel of the same colour the panel is the tile: no fill, border or padding of its own
        # (paid check 2, CHEFFIN 1: filled $negative tiles vanished into a $negativeSoft panel and its padding
        # and theirs kept the row's numbers at 28 px)
        for k in [k for k in box if k == "backgroundColor" or k.startswith("border")]:
            del box[k]
        box["padding"] = "0"
    arranges = kpi()["item_attributes"]["arrange"]["values"]
    arrange = (_choice("arrange", imeta.get("arrange"), arranges, ref, flag)
               or _choice("arrange", gmeta.get("arrange"), arranges, ref, flag) or arranges[0])
    hero = False
    size = imeta.get("size")
    if size is not None:
        if size == "hero" and emphasis_index(comp) == i:
            hero = True
        elif size == "hero":
            flag("NODE_VARIANT_UNMET", ref, f'size="hero" on ref="{ref}" needs is_emphasis_item (the plan singles out '
                 f'{"item " + str(emphasis_index(comp)) if emphasis_index(comp) is not None else "no item"}); normal used.')
        elif size != "normal":
            flag("NODE_ATTR_DROPPED", ref, f'size="{size}" on ref="{ref}": normal or hero; normal used.')

    labels, notes = element_refs._list(comp, "kpi_labels"), element_refs._list(comp, "kpi_deltas")
    label = _text(f"{ref}.label", parts["label"]) if i < len(labels) and labels[i] else None
    value = _text(f"{ref}.value", parts["value"], hero)
    note = _text(f"{ref}.note", parts["note"]) if i < len(notes) and notes[i] else None   # notes always drawn
    icons = element_refs._list(comp, "kpi_icons")
    icon_name = imeta.get("icon") or gmeta.get("icon") or (icons[i] if i < len(icons) else "")   # the LLM's, else the plan's
    fill_ = box.get("backgroundColor", "")
    if fill_ in element_refs.READS_ON and parts["icon"].get("color") not in element_refs.READS_ON[fill_]:
        parts["icon"]["color"] = element_refs.ON_FILL[fill_]   # an icon reads on a dark tile, as its text does
    icon = _icon(icon_name, parts["icon"]) if icon_name else None
    marker = _marker(parts["marker"])

    side = arrange == "side"
    tile = etree.Element("HStack" if arrange in ("side", "inline") else "VStack")
    for k, v in box.items():
        tile.set(k, v)
    if arrange == "inline":
        # one line: [icon] label over note, the value right-aligned at the end (the label column takes the spare)
        tile.set("alignItems", tile.get("alignItems") or "center")
        tile.set("gap", str(max(INLINE_GAP, int(float(tile.get("gap") or 0)))))
        if icon is not None:
            tile.append(icon)
        body = etree.SubElement(tile, "VStack", gap="4", grow="1")
        for el in (_row(marker, label, 8), note):
            if el is not None:
                body.append(el)
        value.set("textAlign", value.get("textAlign") or "right")
        tile.append(value)
        return tile
    if side:
        tile.set("alignItems", tile.get("alignItems") or "center")
        lead = icon if icon is not None else marker
        if lead is not None:
            tile.append(lead)
        body = etree.SubElement(tile, "VStack", gap="6", grow="1")
        if icon is not None and marker is not None:   # the icon leads; the dot stays beside the label
            label = _row(marker, label, 8)
        for el in (label, value, note):
            if el is not None:
                body.append(el)
        return tile
    if arrange == "icon-top":
        first = [icon] if icon is not None else []
        head = _row(marker, label, 8)
    else:
        first = []
        head = _row(icon, label, 10) if icon is not None else _row(marker, label, 8)
        if icon is not None and marker is not None:
            head.insert(0, marker)
    order = [*first, value, head, note] if arrange == "value-first" else [*first, head, value, note]
    for el in order:
        if el is not None:
            tile.append(el)
    return tile


def panel_fill(el: etree._Element) -> str | None:
    """The backgroundColor of the nearest filled box the LLM put around a tile tag (not the slide's root)."""
    for p in el.iterancestors():
        if p.tag == "Slide" or p.getparent() is None or p.getparent().tag == "Slide":
            return None
        if p.get("backgroundColor"):
            return p.get("backgroundColor")
    return None


# ── a group ───────────────────────────────────────────────────────────────────

def _balanced_cols(n: int) -> int:
    """5 -> 3 + 2, 7 -> 4 + 3, 8 -> 4 + 4, 9 -> 3 + 3 + 3."""
    rows = -(-n // 4)
    return -(-n // rows)


def build_group(tiles: list[etree._Element], meta: dict[str, str], box: _Layer, ref: str, flag) -> etree._Element:
    layouts = kpi()["group_attributes"]["layout"]["values"]
    layout = (_choice("layout", meta.get("layout"), layouts, ref, flag)
              or ("column" if meta.get("arrange") == "inline" else "grid" if len(tiles) > 4 else "row"))
    divided = kpi()["variants"]["divided"] if meta.get("variant") == "divided" else None
    gap = box.box.pop("gap", str(divided["divider"]["space"] if divided else GROUP_GAP))
    cols = None
    if meta.get("cols") is not None:
        try:
            cols = max(1, int(meta["cols"]))
        except ValueError:
            flag("NODE_ATTR_DROPPED", ref, f'cols="{meta["cols"]}" on ref="{ref}": a number; balanced columns used.')
        if cols is not None and layout != "grid":
            if cols >= len(tiles):
                cols = None
            else:
                layout = "grid"   # cols="2" asks for a grid
    # tiles share the row: content width + an even share of the spare (element_refs._fill_rows). A row holding a
    # hero tile gets equal columns: the peers' numbers grow first and would take the hero's width (CHEFFIN 1 dry
    # run 2026-10-12: peers 28 -> 79 px, the hero cut from 72 to 35 px by the shrink guard)
    # (side by side only: in a column w="1" is a 1 px wide tile; the gallery's inverted hero in an inline column)
    hero = layout != "column" and any(t.find(".//Text[@size='hero']") is not None for t in tiles)
    for t in tiles:
        if t.get("w") is None and t.get("grow") is None:
            if hero:
                t.set("w", "1")
            t.set("grow", "1")
    if divided:
        for t in tiles:
            _spread_padding(t)
    if layout == "grid":
        cols = cols or _balanced_cols(len(tiles))
        outer = etree.Element("VStack", gap=gap)
        for r, k in enumerate(range(0, len(tiles), cols)):
            row = etree.SubElement(outer, "HStack", gap=gap, grow="1", alignItems="stretch")
            if divided and r:
                _divide(row, "Top", divided["divider"])
            for j, t in enumerate(tiles[k:k + cols]):
                if divided and j:
                    _divide(t, "Left", divided["divider"])
                row.append(t)
    else:
        outer = etree.Element("HStack" if layout == "row" else "VStack", gap=gap, alignItems="stretch")
        for j, t in enumerate(tiles):
            if divided and j:
                _divide(t, "Left" if layout == "row" else "Top", divided["divider"])
            outer.append(t)
        # a row fit-grow may make two rows (regridTiles), also when the LLM wrote layout="row" / cols >= the count:
        # a pinned row of 4-5 stayed width-bound (QBR paid 1: 69 px, 95 as two rows; wide-paid CHEFFIN 1: 51 px in
        # one row under a 130 px empty band, labels grown to 24 / 28 px and wrapped). A grid or column stays as written.
        # A divided row stays one row: a tile moved to the second row would keep its hairline.
        if layout == "row" and cols is None and not divided:
            outer.set("id", f"kpig-{ref}")
    for k, v in (divided or {}).get("group_look", {}).items():   # the strip's box, under the LLM's box attributes
        outer.set(k, str(v))
    for k, v in box.box.items():
        outer.set(k, v)
    return outer


def _spread_padding(el: etree._Element) -> None:
    """`padding` as padding.top / right / bottom / left. Every divided tile gets it: the normalizer drops
    padding="0", and a tile with no box attribute left hands its value to the strip's box in fit-grow's refGroups
    (a full box: the strip's numbers stayed at 28 px, gallery example 6)."""
    pad = el.attrib.pop("padding", None)
    if pad is not None:
        for s in ("top", "right", "bottom", "left"):
            el.set(f"padding.{s}", el.get(f"padding.{s}") or pad)


def _divide(el: etree._Element, side: str, divider: dict) -> None:
    """A hairline on el's `side` (Left / Top) and the divider's space inside it (padding spread first: padding with
    padding.<side> beside it is two values for one side)."""
    _spread_padding(el)
    own = int(float(el.get(f"padding.{side.lower()}") or 0))
    el.set(f"padding.{side.lower()}", str(own or divider["space"]))   # a filled tile keeps its own padding
    el.set(f"border{side}.color", str(divider["color"]))
    el.set(f"border{side}.width", str(divider["width"]))


# ── the slide ─────────────────────────────────────────────────────────────────

def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <KpiGrid> / <Kpi> expanded into tiles of <Text ref> parts; issues as element_refs."""
    issues: list[dict[str, Any]] = []
    result: dict[str, Any] = {"xml": xml, "issues": issues, "ok": True, "tile_items": {}}

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY[code], "ref": ref, "message": message})

    if f"<{ITEM}" not in xml:   # <KpiGrid starts with <Kpi too
        return result
    try:
        root = etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"))
    except etree.XMLSyntaxError:
        return result
    comps = element_refs.kpi_components(plan)
    ids = ", ".join(comps) or "none"
    drawn: dict[str, set[int]] = {cid: set() for cid in comps}

    def item_of(el: etree._Element, group_cid: str | None) -> tuple[str, int] | None:
        ref = el.get("ref", "")
        m = _ITEM_REF.match(ref)
        if not m or m["cid"] not in comps:
            flag("NODE_REF_UNKNOWN", ref or None, f'<Kpi ref="{ref}">: an item is <Kpi ref="<kpi_row id>.<index>"/> '
                 f"with a kpi_row id from the plan ({ids}).")
            return None
        cid, i = m["cid"], int(m["i"])
        n = len(element_refs._list(comps[cid], "kpi_values"))
        if group_cid is not None and cid != group_cid:
            flag("NODE_REF_UNKNOWN", ref, f'<Kpi ref="{ref}"> inside <KpiGrid ref="{group_cid}">: an item in a group '
                 f"names that group's component; place it outside the group.")
            return None
        if i >= n:
            flag("NODE_REF_UNKNOWN", ref, f'<Kpi ref="{ref}">: {cid} has {n} items (0-{n - 1}).')
            return None
        return cid, i

    groups = [el for el in root.iter(GROUP)]
    items_out = [el for el in root.iter(ITEM) if el.getparent() is None or el.getparent().tag != GROUP]
    # items placed outside a group: the group skips them
    outside: dict[tuple[str, int], etree._Element] = {}
    for el in items_out:
        key = item_of(el, None)
        if key is None:
            el.getparent().remove(el)
            continue
        if key in outside:
            flag("NODE_REF_DUPLICATE", el.get("ref"), f'<Kpi ref="{el.get("ref")}"> is placed twice; place each item once.')
            el.getparent().remove(el)
            continue
        outside[key] = el
    seen_groups: set[str] = set()
    for g in groups:
        cid = g.get("ref", "")
        if cid not in comps:
            flag("NODE_REF_UNKNOWN", cid or None, f'<KpiGrid ref="{cid}">: a group is <KpiGrid ref="<kpi_row id>"> '
                 f"with a kpi_row id from the plan ({ids}).")
            g.getparent().remove(g)
            continue
        if cid in seen_groups:
            flag("NODE_REF_DUPLICATE", cid, f'<KpiGrid ref="{cid}"> is placed twice; one group draws every item.')
            g.getparent().remove(g)
            continue
        seen_groups.add(cid)
        comp = comps[cid]
        gmeta, gbox, gparts = _read(g, GROUP_META, flag)
        overrides: dict[int, tuple] = {}
        for child in list(g):
            if not isinstance(child.tag, str):
                continue
            if child.tag != ITEM:
                flag("NODE_ATTR_DROPPED", cid, f"<{child.tag}> inside <KpiGrid ref=\"{cid}\">: a group holds <Kpi> tags only; removed.")
                continue
            key = item_of(child, cid)
            if key is None:
                continue
            if key in outside:
                flag("NODE_REF_DUPLICATE", child.get("ref"), f'<Kpi ref="{child.get("ref")}"> is inside the group and placed '
                     "outside it too; place each item once.")
                continue
            if key[1] in overrides:
                flag("NODE_REF_DUPLICATE", child.get("ref"), f'<Kpi ref="{child.get("ref")}"> appears twice in the group.')
                continue
            overrides[key[1]] = _read(child, ITEM_META, flag)
        hint_looks(comp, gmeta, overrides, flag, kpi(), GROUP, emphasis_index(comp),
                   skip={i for c, i in outside if c == cid})
        n = len(element_refs._list(comp, "kpi_values"))
        mine = [i for i in range(n) if (cid, i) not in outside]
        panel = panel_fill(g)
        tiles = [build_tile(comp, i, (gmeta, gparts), overrides.get(i), flag, panel) for i in mine]
        drawn[cid].update(mine)
        if not tiles:
            g.getparent().remove(g)
            continue
        new = build_group(tiles, gmeta, gbox, cid, flag)
        new.tail = g.tail
        g.getparent().replace(g, new)
    alone: dict[str, dict[int, tuple]] = {}
    for (cid, i), el in outside.items():
        alone.setdefault(cid, {})[i] = _read(el, ITEM_META, flag)
    for cid, items in alone.items():   # bare items placed alone take the hint's look too
        hint_looks(comps[cid], {}, items, flag, kpi(), ITEM, emphasis_index(comps[cid]), alone=True)
    for (cid, i), el in outside.items():
        tile = build_tile(comps[cid], i, None, alone[cid][i], flag, panel_fill(el))
        tile.tail = el.tail
        el.getparent().replace(el, tile)
        drawn[cid].add(i)

    uniq = {(i["code"], i["ref"], i["message"]): i for i in issues}   # a group's issue, once
    issues[:] = list(uniq.values())
    result["tile_items"] = {cid: len(v) for cid, v in drawn.items()}
    result["xml"] = (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root)
    result["ok"] = not any(i["severity"] == ERROR for i in issues)
    return result


def fill(xml: str, plan: dict | None) -> dict[str, Any]:
    """cards.expand (code writes the card text), expand, then element_refs.fill_refs; one result in fill_refs'
    shape, plus card_items {card_grid id: cards drawn from tile tags}."""
    from src.compiler.nodes import cards   # cards builds on this module
    crd = cards.expand(xml, plan)
    exp = expand(crd["xml"], plan)
    exp["issues"] = crd["issues"] + exp["issues"]
    exp["ok"] = exp["ok"] and crd["ok"]
    res = element_refs.fill_refs(exp["xml"], plan)
    res["card_items"] = crd["card_items"]
    missing: dict[str, set[str]] = {}
    for i in res["issues"]:
        if i["code"] == "NODE_ITEM_MISSING":
            cid, k = i["ref"].split(".")[:2]
            missing.setdefault(cid, set()).add(k)
    # an item missing as a whole is drawn by its tag with its label and note: no <Text ref> note for those. CHEFFIN 4
    # (tile_one, 2026-10-26): the LLM drew the 7 tiles by hand with typed labels, the label notes named <Text ref> and
    # the repairer patched refs into the hand tiles, so the slide left the tile route (no variant, no hint look)
    res["issues"] = [i for i in res["issues"] if not (i["code"] in ("NODE_LABEL_MISSING", "NODE_FIELD_MISSING")
                                                      and i["ref"].split(".")[1] in missing.get(i["ref"].split(".")[0], ()))]
    for i in res["issues"]:
        if i["code"] != "NODE_ITEM_MISSING":
            continue
        cid, k = i["ref"].split(".")[:2]   # name the tile tags, not the hand-written ref
        if len(missing[cid]) < res["components"][cid]["items"]:
            i["message"] = (f'{cid} item {k} is not on the slide: draw it in <KpiGrid ref="{cid}"/> or place it with '
                            f'<Kpi ref="{cid}.{k}"/>; delete any tile drawn for it by hand.')
        elif k == min(missing[cid], key=int):   # no item drawn: one instruction for the row, the other items point to it
            i["message"] = (f'{cid}: none of its {len(missing[cid])} tiles is drawn from a tag. Put one '
                            f'<KpiGrid ref="{cid}"/> where its tiles go and delete every tile drawn for it by hand, with '
                            "their typed labels: code draws each tile with its label, value and note.")
        else:
            i["message"] = f'{cid} item {k} is not on the slide: the <KpiGrid ref="{cid}"/> asked for above draws it.'
    res["issues"] = exp["issues"] + res["issues"]
    for cid, stats in res["components"].items():
        tiles = exp["tile_items"].get(cid, 0)
        stats["tile_items"] = tiles
        stats["hand_items"] = max(0, stats["values_placed"] - tiles)
    res["ok"] = res["ok"] and exp["ok"]
    return res


# ── prompt ────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines (same on every slide: the cached part of the system prompt)."""
    k = kpi()
    vs = k["variants"]
    variants = "; ".join(f'{n} ({v["prompt"]})' for n, v in vs.items())
    arranges = " | ".join(k["item_attributes"]["arrange"]["values"])
    return "\n".join([
        "## KPI TILES (code draws them from the plan)",
        f'<{GROUP} ref="<kpi id>" layout="row|grid|column" cols="N"> draws every item in plan order; holds only <{ITEM}>; '
        "its gap / box attributes are the group's box.",
        f'<{ITEM} ref="<kpi id>.<index>"/> inside the group restyles that item; outside, places it anywhere (the group '
        f"skips it). Each item once. Write a <{ITEM}> only for an item that differs: one with no attributes inside "
        "its group changes nothing.",
        "Both take variant, arrange, color, icon and parts: label. value. note. = <Text> attributes, icon. = <Icon>, "
        'marker. = <Shape> (value.glow.size="6" icon.variant="circle-filled"); a Kpi also size="hero" and box attributes.',
        "Code writes the text and sizes: no fontSize, lineHeight, borderRadius or children in a Kpi.",
        f'variant: {variants}. inverted / size="hero": the line\'s emphasis item only.',
        f"arrange: {arranges} (side = icon left; inline = label left, value right on one line, a column by default). color: $accent $positive $negative $warning $neutral (default: the tone).",
        "The component's visual-intent is drawn with these attributes (a bare tag draws none of it):",
        *(f"- {t}: {how}" for t, how in treatments().items()),
    ])


def treatments() -> dict[str, str]:
    """Visual-intent treatment -> the tile attributes that draw it (block-variants.yaml `kpi.treatments`)."""
    return {t: " ".join(str(how).split()) for t, how in kpi()["treatments"].items()}


def scope(planner_treatments: list[str]) -> str:
    """A kpi_row's scope line under tiles: the planner's treatments that tiles can draw."""
    return "treatments: " + ", ".join(t for t in planner_treatments if t in treatments())


def variants_for(comp: dict) -> list[str]:
    """The variants this component can use (requires met; inverted needs the plan's emphasis item)."""
    extra = {"is_emphasis_item": emphasis_index(comp) is not None, "is_group": True}
    return [n for n, v in kpi()["variants"].items() if not spec.failed_requires(v, comp, extra)]


def prompt_line(comp: dict) -> str:
    """The per-component line (spec §5): ids, items, emphasis, tones; no values."""
    cid = comp["component_id"]
    labels, values = element_refs._list(comp, "kpi_labels"), element_refs._list(comp, "kpi_values")
    n = len(values)
    parts = [f"KPI TILES {cid}: {n} item{'s' if n != 1 else ''} (0-{n - 1})"]
    parts.append("items " + ", ".join(f"{i} {labels[i] if i < len(labels) else ''}".strip() for i in range(n)))
    f = emphasis_index(comp)
    parts.append(f"emphasis {f}" if f is not None else "no emphasis item (no hero, inverted or focus)")
    tones = element_refs._list(comp, "kpi_tones")
    if any(tones):
        parts.append("tones " + " ".join(f"{i}={t}" for i, t in enumerate(tones) if t))
    else:
        parts.append("no tones" + (" (colour by the visual-intent)" if comp.get("design_hint") else ""))
    parts.append("variants " + " ".join(variants_for(comp)))
    icons = element_refs._list(comp, "kpi_icons")
    if any(icons):
        parts.append("icons " + " ".join(f"{i}={x}" for i, x in enumerate(icons) if x) + " (drawn; icon= overrides)")
    parts.append(f"longest value {max((len(v) for v in values), default=0)} chars")
    return ("; ".join(parts) + f'. <{GROUP} ref="{cid}"/> or <{ITEM} ref="{cid}.N"/>; never type a label, value or '
            "note yourself: code writes them from the plan")
