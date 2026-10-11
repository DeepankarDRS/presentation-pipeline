"""KPI element refs (D13, docs/kpi-node-pilot-2026-10-11.md §1): the LLM composes the KPI tiles
with ordinary POM nodes and places each item's text by reference,

    <Text ref="kpi_metrics.2.value"/>       ref = <component_id>.<item index>.<label|value|note>

and code writes the text. Runs in the validator before normalize_xml, only under
`POM_BLOCKS=kpi` and only for `kpi_row` components.

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
_STACKS = {"VStack", "HStack"}
_REF = re.compile(r"^(?P<cid>[\w-]+)\.(?P<i>\d+)\.(?P<field>[a-z]+)$")
PEER_ID = re.compile(r"^kpi[vh]\d?-")
# plan weight -> rank in the value id: fit-grow never grows a component's numbers past those of a
# component the plan weights higher on the slide (paid check 2026-10-11: a "peer" row of 2 tiles grew to
# 92 px under the "hero" row at 72)
WEIGHT_RANK = {"hero": 0, "peer": 1, "supporting": 2, "minor": 3}


def mode() -> str:
    """`POM_BLOCKS`: off (today's route) | kpi (kpi_row components become element refs)."""
    v = os.environ.get("POM_BLOCKS", "off").strip().lower()
    return v if v in ("off", "kpi") else "off"


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

    placed: dict[str, dict[int, set[str]]] = {cid: {} for cid in comps}
    value_els: dict[tuple[str, int], etree._Element] = {}
    seen: set[str] = set()
    changed = False

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
        if "color" not in a:
            tones = _list(comp, "kpi_tones")
            role = TONE_ROLE.get(tones[i].lower()) if i < len(tones) else None
            dark = ON_FILL.get(_fill_of(el) or "")
            a["color"] = dark or (f"${role}Text" if role else ROLE_COLOR[field])
        _set_text(el, field, text, size, unit_share(_list(comp, "kpi_values")))
        placed[cid].setdefault(i, set()).add(field)

    # values filled on an earlier pass (a repaired slide comes back already filled) count as placed
    for t in root.iter("Text"):
        pm = re.match(r"^kpi[vh]\d?-(?P<cid>[\w-]+)-(?P<i>\d+)$", t.get("id", ""))
        if pm and pm["cid"] in comps and (pm["cid"], int(pm["i"])) not in value_els:
            placed[pm["cid"]].setdefault(int(pm["i"]), set()).add("value")
            value_els[(pm["cid"], int(pm["i"]))] = t
    # plain Texts that carry a plan value (typed instead of placed by ref)
    plain = {norm("".join(t.itertext())) for t in root.iter("Text")}

    for cid, comp in comps.items():
        values, labels, notes = (_list(comp, PLAN_KEY[f]) for f in FIELDS)
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
            for field, planned in (("label", labels), ("note", notes)):
                if field not in got and i < len(planned) and planned[i]:
                    flag("NODE_FIELD_MISSING", f"{cid}.{i}.{field}", f'{cid} item {i}: no <Text ref="{cid}.{i}.{field}"/>.')
        result["components"][cid] = stats
        _focus_check(comp, cid, value_els, flag)

    if changed:
        result["xml"] = (root.text or "") + "".join(etree.tostring(c, encoding="unicode") for c in root)
    result["ok"] = not any(i["severity"] == ERROR for i in issues)
    return result


def _focus_check(comp: dict, cid: str, value_els: dict, flag) -> None:
    """One item's card drawn apart from its peers (a different fill) that the plan does not single out."""
    cards = {i: _container(el) for (c, i), el in value_els.items() if c == cid}
    fills = {i: (card.get("backgroundColor") if card is not None else None) for i, card in cards.items()}
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
        "Every value exactly once; label and note at most once" + (f" (no note for item {', '.join(no_note)})" if no_note else "") + ".",
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
    return "\n  ".join(parts)
