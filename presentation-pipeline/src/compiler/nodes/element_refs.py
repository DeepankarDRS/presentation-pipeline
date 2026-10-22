"""KPI element refs (D13, docs/kpi-node-pilot-2026-10-11.md §1): the LLM composes the KPI tiles
with ordinary POM nodes and places each item's text by reference,

    <Text ref="kpi_metrics.2.value"/>       ref = <component_id>.<item index>.<label|value|note>

and code writes the text. Runs in the validator before normalize_xml, under `POM_BLOCKS=kpi` (the
default; `off` = the old route) and only for `kpi_row` components. KPI tiles get square corners.

    result = fill_refs(xml, plan)
    result["xml"]         the slide with every ref Text filled (refs gone)
    result["issues"]      [{code, severity, ref, message}]
    result["ok"]          no error-severity issue (errors go to the compile repairer)
    result["components"]  {component_id: {items, values_placed, labels_placed, notes_placed, bypassed}}

Code owns, over anything the LLM wrote on a ref Text: the text (verbatim from kpi_labels /
kpi_values / kpi_deltas), the value's size (one size for every value of a component, the
unit as a span, fit-grow grows the group together: ids `kpiv<rank>-<cid>-<i>`, a focus value with
size="hero" `kpih<rank>-<cid>-<i>`; rank = the plan weight, 0 hero .. 3 minor), label / note sizes from the type ramp, and the colour of a
ref Text with no `$token` colour (tone ink, else the role default, else light ink on a dark
fill the LLM drew). Everything else (containers, fills, bars, icons) is the LLM's.
"""

from __future__ import annotations

import os
import re
from typing import Any

from lxml import etree

from src.compiler.nodes import spec
from src.compiler.value_parts import is_sentence, split_value, unit_px, unit_share

ERROR, WARNING, REPORT = "error", "warning", "report"
SEVERITY = {
    "NODE_REF_UNKNOWN": ERROR, "NODE_REF_DUPLICATE": ERROR, "NODE_ITEM_MISSING": ERROR,
    # a label the LLM typed itself can sit beside the wrong value: CHEFFIN 4 (2026-10-20) typed 7 labels in
    # another order (two not in the brief) while code placed the values in plan order - every tile mislabelled
    "NODE_LABEL_MISSING": ERROR, "NODE_LABEL_PLACED": WARNING,
    "NODE_FIELD_MISSING": WARNING, "NODE_BYPASSED": WARNING, "NODE_ATTR_IGNORED": WARNING,
    "NODE_FOCUS_UNNAMED": REPORT, "NODE_VALUE_TEXT": WARNING,
}

FIELDS = ("label", "value", "note")
PLAN_KEY = {"label": "kpi_labels", "value": "kpi_values", "note": "kpi_deltas"}
# type ramp (house-style.yaml): tile label 16; a note reads as a caption / label. Values start
# small and fit-grow grows each component's values together to its fullest box (<= 96 px; a
# hero <= 120): 28 = the shrink guard's floor for a big number. The replay first started values
# at the ramp's 44: too wide for a dense slide's tiles (the spill fixer shrank the whole slide) and
# too full to count as sparse elsewhere (nothing grew). A hero starts at the ramp's single stat
# (72): in a content-height card nothing grows it, and 48 stayed 48 where the LLM had drawn 72.
LABEL_PX, NOTE_PX, VALUE_PX, HERO_PX = 16, 16, 28, 72
# a "value" that is a sentence (planner put prose in kpi_values; plan check KPI_VALUE_TEXT) is drawn
# as body text, not as a bold number grown to fill (2026-10-11 blind pair 1.3: "not all things bold")
BODY_PX = 18
ROLE_COLOR = {"label": "$accentText", "value": "$textMain", "note": "$textMuted"}
TONE_ROLE = {"good": "positive", "positive": "positive", "bad": "negative", "negative": "negative",
             "watch": "warning", "warning": "warning"}
# text on a dark fill the LLM drew, when it gave the ref no colour
ON_FILL = {"$panelDark": "$onPanelDark", "$textMain": "$surface", "$accent": "$onAccent"}
# the colours that read on each dark fill; any other colour on a KPI text there becomes ON_FILL's
# (QBR 2026-10-11: the LLM wrote $accentText for ARR and a green delta on a $textMain tile, LOW_CONTRAST 2)
READS_ON = {"$panelDark": {"$onPanelDark", "$surface", "$surfaceAlt"},
            "$textMain": {"$surface", "$surfaceAlt", "$onPanelDark"},
            "$accent": {"$onAccent", "$surface", "$surfaceAlt"}}
_STACKS = {"VStack", "HStack"}
_REF = re.compile(r"^(?P<cid>[\w-]+)\.(?P<i>\d+)\.(?P<field>[a-z]+)$")
PEER_ID = re.compile(r"^kpi[vh]\d?-")
# plan weight -> rank in the value id: fit-grow never grows a component's numbers past those of a
# component the plan weights higher on the slide (paid check 2026-10-11: a "peer" row of 2 tiles grew to
# 92 px under the "hero" row at 72)
WEIGHT_RANK = {"hero": 0, "peer": 1, "supporting": 2, "minor": 3}


def mode() -> str:
    """`POM_BLOCKS`: kpi (default since 2026-10-11: kpi_row components become element refs) | tiles (the LLM writes
    <KpiGrid> / <Kpi> tile nodes, src/compiler/nodes/tiles.py; opt-in) | off (the old route)."""
    v = os.environ.get("POM_BLOCKS", "kpi").strip().lower()
    return v if v in ("off", "kpi", "tiles") else "kpi"


def refs_on() -> bool:
    """kpi_row text is placed by ref (kpi and tiles both end in fill_refs)."""
    return mode() in ("kpi", "tiles")


def kpi_components(plan: dict | None) -> dict[str, dict]:
    return {c["component_id"]: c for c in (plan or {}).get("components") or []
            if c.get("kind") == "kpi_row" and c.get("component_id")}


def _list(comp: dict, key: str) -> list[str]:
    return [str(v).strip() if v is not None else "" for v in (comp.get("content_data") or {}).get(key) or []]


def focus_index(comp: dict) -> int | None:
    """The item the plan singles out (its design hint names it beside an emphasis word)."""
    named = spec.singled_out(comp)
    labels = _list(comp, "kpi_labels")
    return labels.index(named) if named in labels else None


def norm(s: str) -> str:
    """Compare form: no spaces, one minus sign, no thousands commas, lower case."""
    s = re.sub(r"\s+", "", str(s)).replace("−", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"(?<=\d),(?=\d{3})", "", s).lower()


def _fill_of(el: etree._Element) -> str | None:
    """The nearest backgroundColor the LLM drew around this element."""
    p = el.getparent()
    while p is not None and p.tag != "_r_":
        bg = p.get("backgroundColor")
        if bg:
            return bg
        p = p.getparent()
    return None


def _container(el: etree._Element) -> etree._Element | None:
    """The nearest stack with a fill or border around this element (the item's card)."""
    p = el.getparent()
    while p is not None and p.tag in _STACKS:
        if p.get("backgroundColor") or any(k.startswith("border") for k in p.attrib):
            return p
        p = p.getparent()
    return None


def _set_text(el: etree._Element, field: str, text: str, size: int, share: float) -> None:
    for c in list(el):
        el.remove(c)
    if field != "value":
        el.text = text
        return
    head, unit = split_value(text)
    el.text = head
    if unit:
        span = etree.SubElement(el, "Span", fontSize=str(unit_px(size, share)))
        span.text = unit


def fill_refs(xml: str, plan: dict | None) -> dict[str, Any]:
    comps = kpi_components(plan)
    issues: list[dict[str, Any]] = []
    result: dict[str, Any] = {"xml": xml, "issues": issues, "ok": True, "components": {}}

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY[code], "ref": ref, "message": message})

    if "ref=" not in xml and not comps:
        return result
    try:
        root = etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"))
    except etree.XMLSyntaxError:
        return result   # the normalizer / parseXml report the XML itself

    changed = _unwrap_refs(root, flag)
    placed: dict[str, dict[int, set[str]]] = {cid: {} for cid in comps}
    value_els: dict[tuple[str, int], etree._Element] = {}
    filled: set[etree._Element] = set()
    seen: set[str] = set()

    for el in list(root.iter()):
        if not isinstance(el.tag, str) or "ref" not in el.attrib:
            continue
        ref = el.get("ref", "")
        m = _REF.match(ref)
        comp = comps.get(m["cid"]) if m else None
        if el.tag != "Text" or not m or comp is None or m["field"] not in FIELDS:
            flag("NODE_REF_UNKNOWN", ref, f'ref="{ref}" on <{el.tag}>: a KPI ref is <Text ref="<component_id>.'
                 f'<item>.<label|value|note>"/> with a kpi_row id from the plan ({", ".join(comps) or "none"}).')
            continue
        cid, i, field = m["cid"], int(m["i"]), m["field"]
        texts = _list(comp, PLAN_KEY[field])
        n = len(_list(comp, "kpi_values"))
        if i >= n:
            flag("NODE_REF_UNKNOWN", ref, f'ref="{ref}": {cid} has {n} items (0-{n - 1}).')
            continue
        if ref in seen:
            flag("NODE_REF_DUPLICATE", ref, f'ref="{ref}" is placed twice; place each item\'s text once.')
            continue
        seen.add(ref)
        changed = True
        text = texts[i] if i < len(texts) else ""
        if field != "value" and not text:
            # a note the plan does not have (or an empty label): nothing to draw
            flag("NODE_ATTR_IGNORED", ref, f'ref="{ref}": the plan has no {field} for item {i}; the Text was removed.')
            el.getparent().remove(el)
            continue

        a = el.attrib
        del a["ref"]
        hero = a.pop("size", None)
        if hero is not None and not (hero == "hero" and field == "value" and focus_index(comp) == i):
            flag("NODE_ATTR_IGNORED", ref, f'size="{hero}" on ref="{ref}": only the focus item\'s value may be size="hero".')
            hero = None
        if n == 1 and field == "value":
            hero = "hero"   # a one-item kpi_row is the plan's hero stat (the number the headline rests on)
        if (el.text or "").strip() or len(el):
            flag("NODE_ATTR_IGNORED", ref, f'text inside ref="{ref}" was replaced by the plan\'s {field}.')
        color = a.get("color")
        if color is not None and not color.startswith("$"):
            flag("NODE_ATTR_IGNORED", ref, f'color="{color}" on ref="{ref}": colours are $tokens; removed.')
            del a["color"]
        fill = _fill_of(el) or ""
        if fill in READS_ON and a.get("color") is not None and a["color"] not in READS_ON[fill]:
            flag("NODE_ATTR_IGNORED", ref, f'color="{a["color"]}" on ref="{ref}" does not read on {fill}; '
                 f'{ON_FILL[fill]} instead.')
            a["color"] = ON_FILL[fill]
        if field == "value" and "fontSize" in a:
            flag("NODE_ATTR_IGNORED", ref, f'fontSize on ref="{ref}": code sizes every value of {cid} together; removed.')

        prose = field == "value" and is_sentence(text)
        if prose:
            flag("NODE_VALUE_TEXT", ref, f'{cid} item {i}: the value is a sentence, drawn as body text: "{text[:60]}"')
        size = BODY_PX if prose else (HERO_PX if hero else VALUE_PX) if field == "value" else (
            LABEL_PX if field == "label" else NOTE_PX)
        a["fontSize"] = str(size)
        if prose:
            a.pop("bold", None)
            value_els[(cid, i)] = el
        elif field == "value":
            a["bold"] = "true"
            a["id"] = f"kpi{'h' if hero else 'v'}{WEIGHT_RANK.get(comp.get('weight') or 'peer', 1)}-{cid}-{i}"
            value_els[(cid, i)] = el
        elif field == "label":
            a["id"] = f"kpil-{cid}-{i}"   # a repaired slide comes back filled: the id says code placed it
        if "color" not in a:
            a["color"] = _default_color(el, comp, i, field)
        _set_text(el, field, text, size, unit_share(_list(comp, "kpi_values")))
        placed[cid].setdefault(i, set()).add(field)
        filled.add(el)

    # values and labels filled on an earlier pass (a repaired slide comes back already filled) count as placed
    for t in root.iter("Text"):
        pm = re.match(r"^kpi[vh]\d?-(?P<cid>[\w-]+)-(?P<i>\d+)$", t.get("id", ""))
        if pm and pm["cid"] in comps and (pm["cid"], int(pm["i"])) not in value_els:
            placed[pm["cid"]].setdefault(int(pm["i"]), set()).add("value")
            value_els[(pm["cid"], int(pm["i"]))] = t
        lm = re.match(r"^kpil-(?P<cid>[\w-]+)-(?P<i>\d+)$", t.get("id", ""))
        if lm and lm["cid"] in comps:
            placed[lm["cid"]].setdefault(int(lm["i"]), set()).add("label")
    changed |= _place_labels(comps, placed, value_els, filled, flag)
    # plain Texts that carry a plan value (typed instead of placed by ref)
    plain = {norm("".join(t.itertext())) for t in root.iter("Text")}

    for cid, comp in comps.items():
        labels, values, notes = (_list(comp, PLAN_KEY[f]) for f in FIELDS)   # FIELDS order: label, value, note
        stats = {"items": len(values), "values_placed": 0, "labels_placed": 0, "notes_placed": 0,
                 "notes_planned": sum(1 for d in notes if d), "bypassed": 0}
        for i, v in enumerate(values):
            got = placed[cid].get(i, set())
            stats["values_placed"] += "value" in got
            stats["labels_placed"] += "label" in got
            stats["notes_placed"] += "note" in got
            if "value" not in got:
                if norm(v) in plain:
                    stats["bypassed"] += 1
                    flag("NODE_BYPASSED", f"{cid}.{i}.value", f'"{v}" is typed as plain text; place it with '
                         f'<Text ref="{cid}.{i}.value"/>.')
                else:
                    flag("NODE_ITEM_MISSING", f"{cid}.{i}.value", f'{cid} item {i} ("{labels[i] if i < len(labels) else ""}"): '
                         f'its value is not on the slide; add <Text ref="{cid}.{i}.value"/>.')
            if "label" not in got and i < len(labels) and labels[i]:
                flag("NODE_LABEL_MISSING", f"{cid}.{i}.label", f'{cid} item {i}: its label is not placed; put '
                     f'<Text ref="{cid}.{i}.label"/> in the tile of its value ("{v}", <Text ref="{cid}.{i}.value"/>) and '
                     "delete any label typed there - code writes every label so it matches its value.")
            if "note" not in got and i < len(notes) and notes[i]:
                flag("NODE_FIELD_MISSING", f"{cid}.{i}.note", f'{cid} item {i}: no <Text ref="{cid}.{i}.note"/>.')
        result["components"][cid] = stats
        _focus_check(comp, cid, value_els, flag)

    # KPI tiles have square corners (user, 2026-10-11): they read apart from the slide's other cards
    cards = []
    for el in value_els.values():
        card = _container(el)
        if card is not None and card not in cards:
            cards.append(card)
            if card.attrib.pop("borderRadius", None) is not None:
                changed = True
    changed |= _fill_rows(cards)

    if changed:
        result["xml"] = (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root)
    result["ok"] = not any(i["severity"] == ERROR for i in issues)
    return result


def _unwrap_refs(root: etree._Element, flag) -> bool:
    """<Text fontSize=".." color=".."><Text ref="k.0.label"/></Text>: the LLM styles a ref by wrapping it
    (full decks 2026-10-12: 2 of 4 KPI slides). POM rejects a Text in a Text, and the repairer then
    flattened the filled slide (labels drawn twice, dark-tile colours past the fill). The ref Text takes
    the wrapper's place and the attributes it lacks."""
    changed = False
    for el in list(root.iter("Text")):
        outer = el.getparent()
        if "ref" not in el.attrib or outer is None or outer.tag != "Text":
            continue
        if len(outer) != 1 or (outer.text or "").strip() or (el.tail or "").strip():
            continue
        for k, v in outer.attrib.items():
            if k not in el.attrib:
                el.set(k, v)
        el.tail = outer.tail
        outer.getparent().replace(outer, el)
        flag("NODE_ATTR_IGNORED", el.get("ref"), f'ref="{el.get("ref")}" was wrapped in a <Text>; the ref Text '
             "took its place (a ref Text carries its own attributes).")
        changed = True
    return changed


def _default_color(el: etree._Element, comp: dict, i: int, field: str) -> str:
    """A KPI text with no colour of its own: light ink on a dark fill, else the item's tone ink, else the role default."""
    tones = _list(comp, "kpi_tones")
    role = TONE_ROLE.get(tones[i].lower()) if i < len(tones) else None
    return ON_FILL.get(_fill_of(el) or "") or (f"${role}Text" if role else ROLE_COLOR[field])


TILE_TEXTS = 3   # a tile holds its value and at most a label, a note and one more line; a wider stack is the slide


def _own_tile(value: etree._Element, values: set) -> etree._Element | None:
    """The widest stack around `value` that holds no other KPI value and at most TILE_TEXTS other texts: the item's
    tile, fill or not (16 Oct CHEFFIN 4 drew some tiles with no fill or border). Never the slide around a lone value."""
    tile, p = None, value.getparent()
    while p is not None and p.tag in _STACKS:
        others = [t for t in p.iter("Text") if t is not value]
        if any(t in values for t in others) or len(others) > TILE_TEXTS:
            break
        tile, p = p, p.getparent()
    return tile


TONE_FILLS = {"$positiveSoft", "$negativeSoft", "$warningSoft"}
MAX_LABEL_WORDS = 8  # a typed text longer than this is a sentence the LLM wrote, not a tile label


def _place_labels(comps: dict, placed: dict, value_els: dict, filled: set, flag) -> bool:
    """A value placed by ref whose label was not: code writes the plan's label in the value's own tile, over the
    label the LLM typed there (the text before the value), or as a new Text just above the value. CHEFFIN 4
    (2026-10-16 and 2026-10-20): the labels were typed in another order than the values, every tile mislabelled.
    A tile code cannot tell apart (no own tile, or several typed texts and none before the value) stays
    NODE_LABEL_MISSING, for the repairer."""
    values = set(value_els.values())
    changed = False
    for (cid, i), value in value_els.items():
        comp = comps[cid]
        labels = _list(comp, "kpi_labels")
        if "label" in placed[cid].get(i, set()) or i >= len(labels) or not labels[i]:
            continue
        tile = _own_tile(value, values)
        if tile is None:
            continue
        order = list(tile.iter("Text"))
        typed = [t for t in order if t is not value and t not in filled and value not in t.iterancestors()
                 and not t.get("id", "").startswith("kpi")
                 and 0 < len("".join(t.itertext()).split()) <= MAX_LABEL_WORDS]
        before = [t for t in typed if order.index(t) < order.index(value)]
        if before:
            el = before[-1]
        elif len(typed) == 1:
            el = typed[0]
        elif not typed:
            el = etree.Element("Text")
            value.addprevious(el)
        else:
            continue
        old = " ".join("".join(el.itertext()).split())
        for c in list(el):
            el.remove(c)
        el.text = labels[i]
        for k in ("ref", "fontSize"):
            el.attrib.pop(k, None)
        if not el.get("color", "$").startswith("$") or (_fill_of(el) in READS_ON and el.get("color") not in READS_ON[_fill_of(el)]):
            el.attrib.pop("color", None)
        el.set("fontSize", str(LABEL_PX))
        el.set("id", f"kpil-{cid}-{i}")
        if "color" not in el.attrib:
            el.set("color", _default_color(el, comp, i, "label"))
        if old and norm(old) != norm(labels[i]):
            # the LLM styled this tile for the metric it typed: its colours and icon follow that metric, not this one
            # (20 Oct: Spend drawn red, styled as ROAS); the plan's tone and icon replace them
            for t in (el, value):
                t.set("color", _default_color(t, comp, i, "value" if t is value else "label"))
                for span in t.iter("Span"):
                    span.attrib.pop("color", None)
            for k in [k for k in tile.attrib if k.startswith("borderLeft")]:
                del tile.attrib[k]   # an accent bar marked the typed metric
            if tile.get("backgroundColor") in TONE_FILLS:
                tones = _list(comp, "kpi_tones")
                role = TONE_ROLE.get(tones[i].lower()) if i < len(tones) else None
                tile.set("backgroundColor", f"${role}Soft" if role else "$surfaceAlt")
            icons = _list(comp, "kpi_icons")
            for icon in tile.iter("Icon"):
                if i < len(icons) and icons[i]:
                    icon.set("name", icons[i])
                icon.set("color", _default_color(value, comp, i, "label"))
        placed[cid].setdefault(i, set()).add("label")
        filled.add(el)
        flag("NODE_LABEL_PLACED", f"{cid}.{i}.label", f'{cid} item {i}: code wrote the plan\'s label "{labels[i]}" in the '
             f"tile of its value" + (f' over the typed "{old}"' if old else "") + ".")
        changed = True
    return changed


def _fill_rows(cards: list) -> bool:
    """A row of content-sized KPI tiles (w="max") spans its width: each tile takes an even share of the
    spare width and an empty stack kept as a grid spacer goes (CHEFFIN 4 + 3, 2026-10-11: the row of 3 stopped short).
    Widths the LLM set (px, %) stay."""
    changed = False
    rows = []
    for c in cards:
        p = c.getparent()
        if p is not None and p.tag == "HStack" and p not in rows:
            rows.append(p)
    for row in rows:
        kids = [k for k in row if isinstance(k.tag, str)]
        tiles = [k for k in kids if k in cards]
        spacers = [k for k in kids if k.tag in _STACKS and len(k) == 0 and not (k.text or "").strip()
                   and not k.get("backgroundColor") and not any(a.startswith("border") for a in k.attrib)]
        if len(tiles) < 2 or len(tiles) + len(spacers) != len(kids) or any(t.get("w", "max") != "max" for t in tiles):
            continue
        for k in spacers:
            row.remove(k)
        for t in tiles:   # content width + an even share of the spare (equal widths squeezed the widest number)
            t.set("grow", "1")
        changed = True
    return changed


def _shown_fill(card: etree._Element | None) -> str | None:
    """The fill behind a card: its own, else its nearest filled stack's (a divided strip's tiles have none of their
    own; the first, with no hairline, found the strip itself as its card and read as drawn apart)."""
    p = card
    while p is not None and p.tag in _STACKS:
        if p.get("backgroundColor"):
            return p.get("backgroundColor")
        p = p.getparent()
    return None


def _focus_check(comp: dict, cid: str, value_els: dict, flag) -> None:
    """One item's card drawn apart from its peers (a different fill) that the plan does not single out."""
    cards = {i: _container(el) for (c, i), el in value_els.items() if c == cid}
    fills = {i: _shown_fill(card) for i, card in cards.items()}
    if len(fills) < 3:
        return
    counts: dict[Any, int] = {}
    for f in fills.values():
        counts[f] = counts.get(f, 0) + 1
    odd = [i for i, f in fills.items() if counts[f] == 1]
    if len(odd) != 1 or len(counts) != 2:
        return
    focus = focus_index(comp)
    if odd[0] != focus:
        label = _list(comp, "kpi_labels")[odd[0]] if odd[0] < len(_list(comp, "kpi_labels")) else odd[0]
        flag("NODE_FOCUS_UNNAMED", f"{cid}.{odd[0]}", f'{cid}: item {odd[0]} ("{label}") is drawn apart from its peers '
             f"but the plan {'singles out item ' + str(focus) if focus is not None else 'names no focus'}.")


def repair_note(issues: list[dict]) -> str:
    """Error-severity issues as one repair instruction block."""
    errs = [i for i in issues if i["severity"] == ERROR]
    if not errs:
        return ""
    return "KPI REFS: " + " ".join(i["message"] for i in errs)


# ── generator prompt line (§3: ids and field names, lengths, focus, tones, tokens; no values) ──

def prompt_line(comp: dict) -> str:
    cid = comp["component_id"]
    labels, values, notes = (_list(comp, PLAN_KEY[f]) for f in FIELDS)
    n = len(values)
    fields = "label, value" + (", note" if any(notes) else "")
    no_note = [str(i) for i, d in enumerate(notes + [""] * (n - len(notes))) if not d] if any(notes) else []
    parts = [
        f"KPI REFS for {cid}: {n} items (index 0-{n - 1}); fields {fields}.",
        f'Place each item\'s text with self-closing <Text ref="{cid}.<index>.<field>"/> - never type a label, '
        "value or note yourself; code writes the text, the number sizes (one size for all values) and default colours.",
        "Every value and every label exactly once, the label in its value's tile; a note at most once"
        + (f" (no note for item {', '.join(no_note)})" if no_note else "") + ".",
        f"Longest value {max((len(v) for v in values), default=0)} chars, longest label "
        f"{max((len(str(x).split()) for x in labels), default=0)} words"
        + (f", longest note {max((len(str(x).split()) for x in notes), default=0)} words" if any(notes) else "") + ".",
        "You compose the containers around them: arrangement, fills, borders, bars, dividers, icons - colours as $tokens only "
        "($surfaceAlt, $accentSoft, $accent, $accentText, $positiveSoft / $positiveText, $negativeSoft / $negativeText, "
        "$warningSoft / $warningText, $border; a dark panel is $panelDark with text color=\"$onPanelDark\"). "
        "A color=\"$token\" on a ref Text is kept; no fontSize on a value.",
        "An icon, if any, goes in the label row (an HStack: icon left of the label, or the label left and the icon "
        "right with justifyContent=\"spaceBetween\") - not alone and centred above the label.",
    ]
    f = focus_index(comp)
    if f is not None:
        parts.append(f'Focus item: {f} ("{labels[f]}"); it may stand apart (its own fill or panel) and its value may take size="hero".')
    tones = _list(comp, "kpi_tones")
    if any(tones):
        parts.append("Tones: " + ", ".join(f"{i}={t}" for i, t in enumerate(tones) if t) + " (good=positive, bad=negative, watch=warning).")
    icons = _list(comp, "kpi_icons")
    if any(icons):
        parts.append("Icons from the plan: " + ", ".join(f"{i}={x}" for i, x in enumerate(icons) if x) + " (one <Icon> per tile).")
    return "\n  ".join(parts)
