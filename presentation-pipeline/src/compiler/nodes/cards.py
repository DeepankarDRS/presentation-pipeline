"""Card tile nodes (docs/tile-nodes-spec-2026-10-12.md §3, §11), `POM_BLOCKS=tiles`.

The LLM writes a card_grid like a native POM data node, a group tag and an item tag:

    <CardGrid ref="pillars" variant="accent_top" icon="shield">     every card, plan order
      <Card ref="pillars.1" color="$negative"/>                     restyles one card
    </CardGrid>
    <Card ref="pillars.3" w="36%"/>                                 places one card anywhere

and code expands each card into a VStack holding Icon / tag / number / title / body parts, from the looks in
block-variants.yaml `tile_nodes.card`, and writes the text itself from the plan (title, tag, body line, bullets,
the plan's key_phrase as a coloured Span). The meaning comes from the plan, so a bare <CardGrid ref/> is the
good-looking version (tile-nodes learnings 1-3, 2026-10-13):
  - tones (cards[i].tone): a filled / outline card with a bad / watch tone draws toned, a good one gets a
    coloured left edge; an item's own `color` always shows (`with_color`);
  - the emphasis card (focus_card -> design hint -> the last step) draws `inverted` unless the LLM gives it a
    variant of its own; the LLM never picks it;
  - columns are measured from the text (never one row of more than 4), peers share equal columns.
A matrix card_grid is deferred (user, 2026-10-13): it keeps the hand-written route and has no tile line.

    result = expand(xml, plan)   # {"xml", "issues", "ok", "card_items": {cid: cards drawn}}
"""

from __future__ import annotations

import re
from typing import Any

from lxml import etree

from src.compiler.nodes import element_refs, spec, tiles

ERROR = element_refs.ERROR
SEVERITY = tiles.SEVERITY
GROUP, ITEM = "CardGrid", "Card"
GROUP_META = {"ref", "layout", "cols", "variant", "arrange", "color", "icon"}
ITEM_META = {"ref", "variant", "arrange", "color", "icon"}
GAP = 20                       # between cards (blind marks 2026-10-13: separation between cards)
PX = {"tag": 13, "title": 20, "body": 16, "number": 28, "numerals": 40}   # start sizes; fit-grow grows them
ICON_PX = 26
_TONE_ROLE = {"good": "positive", "bad": "negative", "watch": "warning"}
_INLINE = {"Text", "B", "I", "U", "S", "Span", "Mark", "Li", "Td"}


def card() -> dict[str, Any]:
    return tiles.data()["card"]


def on() -> bool:
    return tiles.on()


def card_components(plan: dict | None) -> dict[str, dict]:
    """card_grid components code draws: a component_id and a layout that is not deferred (matrix)."""
    deferred = set(card().get("deferred_layouts") or [])
    return {c["component_id"]: c for c in (plan or {}).get("components") or []
            if c.get("kind") == "card_grid" and c.get("component_id")
            and (c.get("content_data") or {}).get("card_layout", "grid") not in deferred}


def cards_of(comp: dict) -> list[dict]:
    return [c if isinstance(c, dict) else {"title": str(c)} for c in (comp.get("content_data") or {}).get("cards") or []]


def layout_of(comp: dict) -> str:
    return str((comp.get("content_data") or {}).get("card_layout") or "grid")


def tone_of(comp: dict, i: int) -> str:
    cs = cards_of(comp)
    t = str(cs[i].get("tone") or "").lower() if i < len(cs) else ""
    return t if t in _TONE_ROLE else ""


def tone_role(comp: dict, i: int) -> str:
    return _TONE_ROLE.get(tone_of(comp, i), "accent")


def emphasis_index(comp: dict) -> int | None:
    """focus_card -> the card the design hint names -> the last step of a steps layout (destination)."""
    titles = spec.items(comp)
    named = spec.singled_out(comp)
    if named is not None and named in titles:
        return titles.index(named)
    if layout_of(comp) == "steps" and len(titles) >= 2:
        return len(titles) - 1
    return None


def _lines(c: dict) -> tuple[str, list[str]]:
    """(body line, bullets) of a card; a body given as a list is bullets."""
    body, bullets = c.get("body"), c.get("bullets")
    bullets = [str(b) for b in bullets] if isinstance(bullets, list) else []
    if isinstance(body, list):
        return "", [str(b) for b in body] + bullets
    return str(body or "").strip(), [b for b in bullets if b.strip()]


# a step body of several sentences or "a; b; c" items: one point per line (user, card paid pair 3.1, 2026-10-14:
# "I need points or a new line between the points"). A split needs a capital or "[" after the full stop, so
# "0.25x." inside a sentence or "e.g. bids" stays whole; the words are the plan's, unchanged.
_POINT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])|;\s+")


def points(body: str) -> list[str]:
    """The points of a step body, or [] when it is one point."""
    parts = [p.strip() for p in _POINT_SPLIT.split(body) if p.strip()]
    return parts if len(parts) >= 2 else []


def text_len(c: dict) -> int:
    body, bullets = _lines(c)
    return len(str(c.get("title") or "")) + len(body) + sum(len(b) for b in bullets)


def columns(comp: dict, n: int) -> int:
    """Cards per row, measured from the text: never one row of more than 4 (7 in a row gave 28-37 px numbers and
    empty tiles; 4 + 3 won 6 of 6), long cards at most 3 or 2 per row, a short last row (5 -> 3 + 2, 7 -> 4 + 3)."""
    longest = max((text_len(c) for c in cards_of(comp)), default=0)
    cap = 4 if longest <= 90 else 3 if longest <= 180 else 2
    if n <= cap:
        return n
    rows = -(-n // cap)
    return -(-n // rows)


def numbered_ok(comp: dict) -> bool:
    """No title or tag already carries its own number ("Phase 1", "01"), and the tags do not order the steps themselves
    (years, months, quarters, days: any digit in every tag; blind marks 2026-10-13: "01 · 2021" was not wanted)."""
    tags = [str(c.get("tag") or "") for c in cards_of(comp)]
    return (spec.check("all_titles_numbered_ok", comp) and not any(spec._NUMBERED.match(t) for t in tags)
            and not (tags and all(re.search(r"\d", t) for t in tags)))


DENSE_CHARS = 90   # a group whose cards average more text than this draws its icons on the left


def dense(comp: dict) -> bool:
    """Cards with a lot of text (blind marks 2026-10-13, 10.4: icon left for dense cards, on top for sparse ones)."""
    cs = cards_of(comp)
    return bool(cs) and sum(text_len(c) for c in cs) / len(cs) > DENSE_CHARS


# ── one card ──────────────────────────────────────────────────────────────────

def _variant(comp: dict, i: int, asked: str | None, ref: str, flag) -> str:
    vs = card()["variants"]
    extra = {"is_emphasis_item": emphasis_index(comp) == i}
    name, code, note = spec.resolve_variant("card_grid", ITEM, comp, asked, vs=vs, extra=extra)
    if code:
        flag(code, ref, f'ref="{ref}": {note}.')
    return name or next(iter(vs))


def _patch(how: Any, vs: dict, name: str) -> tuple[str, dict]:
    """A `with_color` / `with_tone` entry: another variant's name, or attributes over this one's look."""
    if isinstance(how, str) and how in vs:
        return how, {}
    return name, how if isinstance(how, dict) else {}


def _readable(fill: str, color: str | None) -> str | None:
    """The ink a part takes on a dark fill (element_refs.READS_ON / ON_FILL), else its own colour."""
    if fill in element_refs.READS_ON and color not in element_refs.READS_ON[fill]:
        return element_refs.ON_FILL[fill]
    return color


def _text(text: str, px: int, attrs: dict[str, str], **extra: str) -> etree._Element:
    el = etree.Element("Text", fontSize=str(px))
    for k, v in {**extra, **attrs}.items():
        el.set(k, v)
    el.text = text
    return el


def _with_phrase(el: etree._Element, text: str, phrase: str, color: str, mark: str = "") -> None:
    """`text` into el, the first `phrase` in it (the plan's key_phrase, exact words) as a highlighter: <Mark mark>
    around a <Span color>; without `mark` a coloured Span; with neither, bold (a dark card)."""
    k = text.find(phrase) if phrase else -1
    if k < 0:
        el.text = text
        return
    el.text = text[:k]
    host = etree.SubElement(el, "Mark", color=mark) if mark else el
    run = etree.SubElement(host, "Span", color=color) if color else etree.SubElement(host, "B")
    run.text = phrase
    (host if mark else run).tail = text[k + len(phrase):]


def build_card(comp: dict, i: int, group: tuple[dict, tiles._Layer] | None,
               item: tuple[dict, tiles._Layer, tiles._Layer] | None, flag, panel: str | None = None,
               number: str | None = None, default_variant: str | None = None,
               default_arrange: str | None = None) -> etree._Element:
    """One card, its layers resolved (house -> group variant -> group attrs -> item variant -> item attrs).
    `panel`: the fill of the LLM's own box around the tag; `number`: "01" on numbered steps, else None."""
    cid = comp["component_id"]
    ref = f"{cid}.{i}"
    parts_def = card()["parts"]
    gmeta, gparts = group if group else ({}, tiles._Layer(parts_def))
    imeta, ibox, iparts = item if item else ({}, tiles._Layer(parts_def), tiles._Layer(parts_def))
    for m in (gmeta, imeta):
        if m.get("color") and m["color"] not in tiles.ROLE_OF:
            flag("NODE_ATTR_DROPPED", m.get("ref"), f'color="{m["color"]}" on ref="{m.get("ref")}": one of '
                 f'{", ".join(tiles.ROLE_OF)}; the plan tone used.')
    own_colour = imeta.get("color") in tiles.ROLE_OF
    asked_colour = imeta.get("color") or gmeta.get("color") or ""
    role = tiles.ROLE_OF.get(asked_colour, tone_role(comp, i))
    vs = card()["variants"]
    emphasis = emphasis_index(comp) == i
    patch: dict = {}
    if imeta.get("variant"):
        used = name = _variant(comp, i, imeta["variant"], ref, flag)
    else:
        # the plan's emphasis card is dark unless the LLM gives it a variant of its own (the meaning is the plan's)
        asked = "inverted" if emphasis and len(cards_of(comp)) >= 3 else (gmeta.get("variant") or default_variant)
        name = used = _variant(comp, i, asked, cid if asked == gmeta.get("variant") else ref, flag)
        if own_colour:
            name, patch = _patch(vs[name].get("with_color"), vs, name)
        elif not gmeta.get("color") and tone_of(comp, i):
            name, patch = _patch((vs[name].get("with_tone") or {}).get(tone_of(comp, i)), vs, name)
    if name == "toned" and asked_colour not in tiles.ROLE_OF and not tone_of(comp, i):
        role = "neutral"   # toned colours the cards that have a tone; the others stay plain (gallery 2026-10-13)

    def look(d: dict) -> tiles._Layer:
        return tiles._look(d, role, parts_def)

    layers = [look(card()["house_look"])]
    if imeta.get("variant"):
        layers += [gparts, look(vs[name]["look"])]
    else:
        layers += [look(vs[name]["look"]), look(patch), gparts]
    layers += [ibox, iparts]
    box: dict[str, str] = {}
    parts: dict[str, dict[str, str]] = {p: {} for p in parts_def}
    for layer in layers:
        box.update(layer.box)
        for p, a in layer.parts.items():
            parts[p].update(a)
    if panel and box.get("backgroundColor") == panel:
        # on the LLM's own panel of the same colour the panel is the card: no fill or border of its own
        for k in [k for k in box if k == "backgroundColor" or k.startswith("border")]:
            del box[k]
    # an open card (no fill of its own) sits on the LLM's panel: its text reads on that panel's fill
    fill = box.get("backgroundColor") or panel or ""
    for p in parts:   # text and icons read on a dark fill
        if fill in element_refs.READS_ON:
            parts[p]["color"] = _readable(fill, parts[p].get("color"))

    arranges = card()["item_attributes"]["arrange"]["values"]
    arrange = (tiles._choice("arrange", imeta.get("arrange"), arranges, ref, flag)
               or tiles._choice("arrange", gmeta.get("arrange"), arranges, ref, flag) or default_arrange or arranges[0])
    c = cards_of(comp)[i]
    body, bullets = _lines(c)
    if layout_of(comp) == "steps" and body and not bullets and points(body):
        body, bullets = "", points(body)
    phrase = str(c.get("key_phrase") or "")
    # the key phrase: in the card's colour; bold on a dark card (a tint does not show there, gallery 2026-10-13);
    # a neutral card's in ink against its muted body
    dark = fill in element_refs.READS_ON
    # the key phrase: coloured text in the card's tone, bold on a dark card (blind marks 2026-10-13: "I like span
    # better than the mark"; the <Mark> highlighter stays possible through _with_phrase's `mark`)
    tint = "accent" if role == "neutral" else role
    phrase_ink = "" if dark else f"${tint}Text"
    phrase_mark = ""
    els: list[etree._Element] = []
    # numerals: the group's numerals stay on its dark emphasis card too
    numerals = used == "numerals" or (not imeta.get("variant") and gmeta.get("variant") == "numerals"
                                      and not spec.failed_requires(vs["numerals"], comp))
    if numerals:
        els.append(_text(f"{i + 1:02d}", PX["numerals"], parts["number"], bold="true", id=f"cardn-{cid}-{i}"))
    tag = " · ".join(t for t in ((number if not numerals else None), str(c.get("tag") or "").upper()) if t)
    if tag:   # a step's number leads its tag line ("01 · DAY 0-30")
        els.append(_text(tag, PX["tag"], parts["tag"], bold="true", letterSpacing="1"))
    els.append(_text(str(c.get("title") or ""), PX["title"], parts["title"], bold="true", id=f"cardt-{cid}-{i}"))
    if body:
        t = _text("", PX["body"], parts["body"], lineHeight="1.4", id=f"cardb-{cid}-{i}")
        _with_phrase(t, body, phrase if phrase in body else "", phrase_ink, phrase_mark)
        els.append(t)
    if bullets:
        ul = etree.Element("Ul", fontSize=str(PX["body"]), lineHeight="1.4")
        if not body:   # the card's body: fit-grow grows text with an id only (points stayed at 16 px beside 22 px titles)
            ul.set("id", f"cardb-{cid}-{i}")
        for k, v in parts["body"].items():
            if k in ("color", "bold", "italic", "underline", "textAlign"):
                ul.set(k, v)
        for b in bullets:
            li = etree.SubElement(ul, "Li")
            _with_phrase(li, b, phrase if phrase in b and phrase not in body else "", phrase_ink, phrase_mark)
        els.append(ul)
    icon_name = imeta.get("icon") or gmeta.get("icon") or c.get("icon")   # the LLM's, else the plan's
    icon = None
    if icon_name:
        icon = etree.Element("Icon", name=icon_name, size=str(ICON_PX))
        for k, v in parts["icon"].items():
            icon.set(k, v)
        if arrange != "side":
            icon.set("alignSelf", "start")

    tile = etree.Element("VStack", id=f"card-{cid}-{i}")
    for k, v in box.items():
        tile.set(k, v)
    if arrange == "side" and icon is not None:
        row = etree.SubElement(tile, "HStack", gap="14", alignItems="start", grow="1")
        row.append(icon)
        col = etree.SubElement(row, "VStack", gap=box.get("gap", "8"), grow="1")
        for el in els:
            col.append(el)
        return tile
    tag_el = next((e for e in els if e.get("letterSpacing") and not e.get("id", "").startswith("cardt-")), None)
    if icon is not None and tag_el is not None:
        # the icon leads the tag line: on a row of its own it cost the title ~20% of its size (replay 2026-10-13:
        # QBR 44 -> 36 px). Not beside a title: the narrower title could not grow past its longest word
        # (BREWLY pillars stayed at 20 px, "Subscriptions"), and the body is held below the title.
        icon.attrib.pop("alignSelf", None)
        row = etree.Element("HStack", gap="10", alignItems="center")
        row.append(icon)
        els[els.index(tag_el)] = row
        tag_el.set("w", "1")       # beside the icon the tag takes the rest of the row and wraps there
        tag_el.set("grow", "1")
        row.append(tag_el)
    elif icon is not None:
        els.insert(0, icon)
    for el in els:
        tile.append(el)
    return tile


# ── a group ───────────────────────────────────────────────────────────────────

def _peer(t: etree._Element) -> etree._Element:
    if t.get("w") is None and t.get("grow") is None:
        t.set("w", "1")
        t.set("grow", "1")
    return t


def _step_shares(cards: list[etree._Element]) -> list[str] | None:
    """Width shares of a steps row by each card's text (sqrt, 0.7-1.6), or None when the texts are about even.
    Equal columns put one long step beside short ones: the group's one size stops at the full card and the rest stay
    half empty (agency takeover 30/60/90, card paid 2026-10-14). A grid's rows keep equal columns, to line up."""
    lens = [max(1, len("".join(t.itertext()))) for t in cards]
    if len(lens) < 2 or max(lens) < 1.5 * min(lens):
        return None
    mean = sum(lens) / len(lens)
    return [f"{min(1.6, max(0.7, (n / mean) ** 0.5)):.2f}" for n in lens]


def group_layout(comp: dict, meta: dict[str, str], ref: str, flag) -> str:
    """The group's layout: the LLM's when the plan's card_layout allows it (match_plan), else the plan's."""
    plan_layout = layout_of(comp)
    allowed = card()["group_attributes"]["layout"]["match_plan"].get(plan_layout, [plan_layout])
    layout = meta.get("layout") or plan_layout
    if layout not in allowed:
        flag("NODE_ATTR_DROPPED", ref, f'layout="{layout}" on <CardGrid ref="{ref}">: the plan\'s cards are '
             f'{plan_layout} ({" / ".join(allowed)}); {plan_layout} used.')
        layout = plan_layout
    return layout


def build_group(comp: dict, cards: list[etree._Element], meta: dict[str, str], box: tiles._Layer, ref: str,
                flag, layout: str, numbers: list[str | None] | None = None) -> etree._Element:
    """`numbers`: the rail's step numbers, one per card (None: no number)."""
    gap = box.box.pop("gap", str(GAP))
    if layout == "steps":
        outer = etree.Element("HStack", gap="10", alignItems="stretch")
        shares = _step_shares(cards)
        for k, t in enumerate(cards):
            if k:
                etree.SubElement(outer, "Icon", name="arrow-right", size="22", color="$textMuted", alignSelf="center")
            outer.append(_peer(t))
            if shares and t.get("grow") == "1":
                t.set("grow", shares[k])
    elif layout == "rail":
        outer = etree.Element("VStack", gap=gap)
        for t, num in zip(cards, numbers or [None] * len(cards)):
            row = etree.SubElement(outer, "HStack", gap="16", alignItems="stretch", grow="1")
            lead = etree.SubElement(row, "VStack", w="64", minW="64", gap="6", alignItems="center")
            if num:   # on the slide's background, not the card: the accent ink ("01" at 28 px is 43 px wide)
                lead.append(_text(num, PX["number"], {"color": "$accentText"}, bold="true", textAlign="center",
                                  w="64"))   # POM sizes a w="max" Text to its own (narrower) measure
            etree.SubElement(lead, "VStack", w="2", grow="1", backgroundColor="$border")
            t.set("w", "1")
            t.set("grow", "1")
            row.append(t)
    else:
        cols = None
        if meta.get("cols") is not None:
            try:
                cols = max(1, int(meta["cols"]))
            except ValueError:
                flag("NODE_ATTR_DROPPED", ref, f'cols="{meta["cols"]}" on ref="{ref}": a number; measured columns used.')
        chosen = cols is None
        cols = cols or columns(comp, len(cards))
        outer = etree.Element("VStack", gap=gap)
        if chosen:
            outer.set("id", f"cardg-{ref}")   # columns code chose (fit-grow may re-grid it)
        for k in range(0, len(cards), cols):
            row = etree.SubElement(outer, "HStack", gap=gap, grow="1", alignItems="stretch")
            for t in cards[k:k + cols]:
                row.append(_peer(t))
    if title_only(comp):
        # cards with a title and nothing else are drawn to their content and centred in the band: stretched, a
        # 48 px title cannot fill a 300 px card (replay 2026-10-13: 21 of 80 saved plans; GEOM_CARD_EMPTY 33 -> 45;
        # user: compact, centred). fit-grow still grows the titles and may re-grid the cardg- group.
        for row in outer.iter("HStack"):
            row.attrib.pop("grow", None)
        band = etree.Element("VStack", justifyContent="center", alignItems="stretch")
        band.append(outer)
        outer = band
    for k, v in box.box.items():
        outer.set(k, v)
    if outer.get("grow") is None and outer.get("h") is None:
        outer.set("grow", "1")   # the cards take the band's spare height (fill the card, don't shrink it)
    return outer


def title_only(comp: dict) -> bool:
    """No card of the component has a line or bullets (only titles, maybe tags)."""
    return not any(any(_lines(c)) for c in cards_of(comp))


# ── the slide ─────────────────────────────────────────────────────────────────

def _unwrap(root: etree._Element, flag) -> None:
    """A CardGrid / Card the LLM wrapped in its own Text (or inline run): the tag replaces the wrapper
    (element_refs._unwrap_refs for tile tags; the repairer otherwise drew the text twice)."""
    for el in [e for e in root.iter(GROUP, ITEM)]:
        top = None
        for p in el.iterancestors():
            if p.tag in _INLINE:
                top = p
        if top is None:
            continue
        el.tail = top.tail
        top.getparent().replace(top, el)
        flag("NODE_ATTR_DROPPED", el.get("ref"), f'<{top.tag}> around <{el.tag} ref="{el.get("ref")}">: '
             "code writes the card text; the wrapper was removed.")


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <CardGrid> / <Card> expanded into cards with the plan's text; issues as element_refs."""
    issues: list[dict[str, Any]] = []
    result: dict[str, Any] = {"xml": xml, "issues": issues, "ok": True, "card_items": {}}

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY[code], "ref": ref, "message": message})

    if f"<{ITEM}" not in xml:   # <CardGrid starts with <Card too
        return result
    try:
        root = etree.fromstring(f"<_r_>{xml}</_r_>".encode("utf-8"))
    except etree.XMLSyntaxError:
        return result
    comps = card_components(plan)
    ids = ", ".join(comps) or "none"
    _unwrap(root, flag)
    drawn: dict[str, set[int]] = {cid: set() for cid in comps}
    block = card()

    def item_of(el: etree._Element, group_cid: str | None) -> tuple[str, int] | None:
        ref = el.get("ref", "")
        m = tiles._ITEM_REF.match(ref)
        if not m or m["cid"] not in comps:
            flag("NODE_REF_UNKNOWN", ref or None, f'<Card ref="{ref}">: a card is <Card ref="<card_grid id>.<index>"/> '
                 f"with a card_grid id from the plan ({ids}).")
            return None
        cid, i = m["cid"], int(m["i"])
        n = len(cards_of(comps[cid]))
        if group_cid is not None and cid != group_cid:
            flag("NODE_REF_UNKNOWN", ref, f'<Card ref="{ref}"> inside <CardGrid ref="{group_cid}">: a card in a group '
                 "names that group's component; place it outside the group.")
            return None
        if i >= n:
            flag("NODE_REF_UNKNOWN", ref, f'<Card ref="{ref}">: {cid} has {n} cards (0-{n - 1}).')
            return None
        return cid, i

    def numbers(comp: dict) -> list[str | None]:
        n = len(cards_of(comp))
        if layout_of(comp) == "steps" and numbered_ok(comp):
            return [f"{k + 1:02d}" for k in range(n)]
        return [None] * n

    outside: dict[tuple[str, int], etree._Element] = {}
    for el in [e for e in root.iter(ITEM) if e.getparent() is None or e.getparent().tag != GROUP]:
        key = item_of(el, None)
        if key is None or key in outside:
            if key is not None:
                flag("NODE_REF_DUPLICATE", el.get("ref"), f'<Card ref="{el.get("ref")}"> is placed twice; place each card once.')
            el.getparent().remove(el)
            continue
        outside[key] = el
    seen: set[str] = set()
    for g in list(root.iter(GROUP)):
        cid = g.get("ref", "")
        if cid not in comps or cid in seen:
            if cid in seen:
                flag("NODE_REF_DUPLICATE", cid, f'<CardGrid ref="{cid}"> is placed twice; one group draws every card.')
            else:
                flag("NODE_REF_UNKNOWN", cid or None, f'<CardGrid ref="{cid}">: a group is <CardGrid ref="<card_grid id>"> '
                     f"with a card_grid id from the plan ({ids}); a matrix card_grid is drawn by hand.")
            g.getparent().remove(g)
            continue
        seen.add(cid)
        comp = comps[cid]
        gmeta, gbox, gparts = tiles._read(g, GROUP_META, flag, block, ITEM)
        overrides: dict[int, tuple] = {}
        for child in list(g):
            if not isinstance(child.tag, str):
                continue
            if child.tag != ITEM:
                flag("NODE_ATTR_DROPPED", cid, f'<{child.tag}> inside <CardGrid ref="{cid}">: a group holds <Card> tags only; removed.')
                continue
            key = item_of(child, cid)
            if key is None:
                continue
            if key in outside or key[1] in overrides:
                flag("NODE_REF_DUPLICATE", child.get("ref"), f'<Card ref="{child.get("ref")}"> is placed twice; place each card once.')
                continue
            overrides[key[1]] = tiles._read(child, ITEM_META, flag, block, ITEM)
        nums = numbers(comp)
        layout = group_layout(comp, gmeta, cid, flag)
        mine = [i for i in range(len(cards_of(comp))) if (cid, i) not in outside]
        panel = tiles.panel_fill(g)
        # steps: the number leads each card's tag line; rail: the rail draws it beside the card
        # a slide's second card group reads as a different type of card (blind marks 2026-10-13: "variants for 2 types
        # of the cards"): open `column` cards unless the LLM names a variant; dense cards put their icons on the left
        second = "column" if len(seen) > 1 else None
        built = [build_card(comp, i, (gmeta, gparts), overrides.get(i), flag, panel,
                            nums[i] if layout == "steps" else None, second, "side" if dense(comp) else None)
                 for i in mine]
        drawn[cid].update(mine)
        if not built:
            g.getparent().remove(g)
            continue
        new = build_group(comp, built, gmeta, gbox, cid, flag, layout, [nums[i] for i in mine])
        new.tail = g.tail
        g.getparent().replace(g, new)
    for (cid, i), el in outside.items():
        meta, box, parts = tiles._read(el, ITEM_META, flag, block, ITEM)
        tile = build_card(comps[cid], i, None, (meta, box, parts), flag, tiles.panel_fill(el), numbers(comps[cid])[i])
        tile.tail = el.tail
        el.getparent().replace(el, tile)
        drawn[cid].add(i)
    for cid, done in drawn.items():   # a component the slide shows with tile tags must show every card
        n = len(cards_of(comps[cid]))
        if done and len(done) < n:
            for k in sorted(set(range(n)) - done):
                flag("NODE_ITEM_MISSING", f"{cid}.{k}", f'{cid} card {k} is not on the slide: draw it in '
                     f'<CardGrid ref="{cid}"/> or place it with <Card ref="{cid}.{k}"/>.')

    uniq = {(i["code"], i["ref"], i["message"]): i for i in issues}
    issues[:] = list(uniq.values())
    result["card_items"] = {cid: len(v) for cid, v in drawn.items()}
    result["xml"] = (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root)
    result["ok"] = not any(i["severity"] == ERROR for i in issues)
    return result


# ── prompt ────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed card lines (same on every slide: the cached part of the system prompt)."""
    k = card()
    variants = "; ".join(f'{n} ({v["prompt"]})' for n, v in k["variants"].items())
    return "\n".join([
        "## CARDS (code draws them from the plan)",
        f'<{GROUP} ref="<card_grid id>" layout="grid|steps|rail" cols="N"> draws every card in plan order with '
        f"the plan's text; holds only <{ITEM}>; its gap / box attributes are the group's box. steps = cards joined by "
        "arrows, rail = one card per row down a line (steps plans only).",
        f'<{ITEM} ref="<card_grid id>.<index>"/> inside the group restyles that card; outside, places it anywhere (the '
        f"group skips it). Each card once; write a <{ITEM}> only for a card that differs.",
        "Both take variant, arrange (stack | side = icon left), color, icon and parts: tag. title. body. number. = <Text> "
        'attributes, icon. = <Icon> (title.letterSpacing="1" icon.variant="circle-filled"); a Card also box attributes.',
        "Code writes the text, sizes, columns, step numbers, arrows and key phrases: no fontSize, borderRadius or "
        "children in a Card. The plan's focus card (or the last step) is drawn dark; tones colour the cards.",
        f"variant: {variants}.",
        "color: $accent $positive $negative $warning $neutral (default: the tone). A bare tag is a finished slide part.",
        "The component's visual-intent is drawn with these attributes:",
        *(f"- {t}: {how}" for t, how in treatments().items()),
    ])


def treatments() -> dict[str, str]:
    return {t: " ".join(str(how).split()) for t, how in card()["treatments"].items()}


def scope(planner_treatments: list[str]) -> str:
    return "treatments: " + ", ".join(t for t in planner_treatments if t in treatments())


def variants_for(comp: dict) -> list[str]:
    """The variants a group can use (requires met; inverted is the emphasis card's, drawn by code)."""
    return [n for n, v in card()["variants"].items()
            if n != "inverted" and not spec.failed_requires(v, comp, {"is_emphasis_item": True})]


def prompt_line(comp: dict) -> str:
    """The per-component line: id, layout, cards, emphasis, tones; no text beyond the titles."""
    cid = comp["component_id"]
    cs = cards_of(comp)
    n = len(cs)
    parts = [f"CARDS {cid}: {n} card{'s' if n != 1 else ''} (0-{n - 1}), {layout_of(comp)}"]
    parts.append("titles " + ", ".join(f"{i} {str(c.get('title') or '')}".strip() for i, c in enumerate(cs)))
    f = emphasis_index(comp)
    parts.append(f"focus {f} (drawn dark)" if f is not None and n >= 3 else "no focus card")
    tones = [tone_of(comp, i) for i in range(n)]
    parts.append("tones " + " ".join(f"{i}={t}" for i, t in enumerate(tones) if t) if any(tones) else "no tones")
    if layout_of(comp) == "grid":
        parts.append(f"{columns(comp, n)} per row")
    parts.append("variants " + " ".join(variants_for(comp)))
    parts.append(f"longest card {max((text_len(c) for c in cs), default=0)} chars")
    return ("; ".join(parts) + f'. <{GROUP} ref="{cid}"/> or <{ITEM} ref="{cid}.N"/>; never type a title, tag or '
            "body yourself: code writes them from the plan")
