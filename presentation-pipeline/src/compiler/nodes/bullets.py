"""Bullet list composition node (approved by the user 2026-11-04, docs/eval/bullet-node/), `POM_NODES=bullet_list`.

The LLM writes one tag per bullet_list component; code draws it from the plan:

    <Ul ref="pts" variant="rows" grow="1"><Highlight phrase="Product C drags" color="bad"/></Ul>

Compositions (block-variants.yaml `nodes.bullet_list`):
- `native` (default and the fallback of everything): POM's real list, one text box, hand-editable in PowerPoint.
  A "Head: detail" point's head is bold, every word kept. fit-grow sizes it and splits 4+ short points into two real
  lists; it writes what POM has no attribute for (the marker colour, the spacing between points) as a `list-post`
  comment for pptx-post.js. If that step is skipped the slide keeps POM's plain list.
- `native numbered`: POM's real numbered list; a list carrying its own numbers falls back to `native`.
- `rows` (`icons="target,scissors,..."`: an icon per point) / `rows numbered`: one ruled row per point: a marker, then
  the head over the detail.

Code owns every word, its order and the type sizes. The LLM owns the box and part styles, in $tokens only:
head. detail. (the words), marker. (dot, bullet, number, icon), item. (a row's box, rows only). Colouring by meaning is
<Highlight> inside the tag; with none, code colours the one point the design hint names. Anything that would do
nothing on the chosen composition is removed with a NODE_ATTR_DROPPED report, never silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.compiler.nodes import compose, native, spec
from src.compiler.nodes.tables import MANY_HIGHLIGHTS, TONE_ROLES, TONES, _named

SEVERITY = compose.SEVERITY
TAG = "Ul"
HIGHLIGHT_ATTRS = {"phrase", "item", "color", "fill", "bold"}
TEXT_ATTRS = ("color", "textAlign", "italic")           # on the tag: the whole list's words, on every composition
NATIVE_NO_BOX = ("gap", "alignItems", "justifyContent")  # a native list sits alone in its box, stretched
MAX_ICONS = 6   # past it a full slide's rows are too short for fit-grow to grow their text (gallery, 8 points: 16 px)
_ICON_NAMES = Path(__file__).resolve().parents[2] / "knowledge" / "core" / "icon-names.txt"
X = native.x
A = compose.a


def on() -> bool:
    return spec.nodes_on("bullet_list")


def node() -> dict[str, Any]:
    return spec.nodes()["bullet_list"]


def components(plan: dict | None) -> dict[str, dict]:
    return {c["component_id"]: c for c in (plan or {}).get("components") or []
            if c.get("kind") == "bullet_list" and c.get("component_id")}


def items(comp: dict) -> list[str]:
    return [str(b).strip() for b in (comp.get("content_data") or {}).get("bullets") or [] if str(b).strip()]


def emphasis(comp: dict) -> int | None:
    """The one point the design hint names (by its head); several or none: no emphasis."""
    hint = " ".join(str(comp.get("design_hint") or "").split())
    if not hint:
        return None
    found = _named([compose.split(s)[0] for s in items(comp)], hint, None)
    return found[0] if len(found) == 1 else None


def role(comp: dict, focus: int | None) -> str:
    """The emphasis point's palette role from the hint's tone; accent when it gives none."""
    if focus is None:
        return "accent"
    from src.agents.plan_checks import tones_from_hint   # src.agents imports the validator, which imports this
    heads = [compose.split(s)[0] for s in items(comp)]
    tones = tones_from_hint({"design_hint": comp.get("design_hint"), "content_data": {"kpi_labels": heads, "kpi_values": heads}})
    return compose.TONE_ROLE.get(tones[focus], "accent") if focus < len(tones) and tones[focus] else "accent"


# ── highlights ────────────────────────────────────────────────────────────────

class Paint:
    """What the <Highlight>s give each point: its text role, its row's fill role, its phrases."""

    def __init__(self) -> None:
        self.ink: dict[int, str] = {}
        self.fill: dict[int, str] = {}
        self.phrases: dict[int, list[tuple[str, str | None, bool]]] = {}


def highlights(comp: dict, body: str, flag) -> Paint | None:
    """The tag's <Highlight> children -> Paint; None when it has none. A phrase or point not in the list is
    NODE_HIGHLIGHT_UNKNOWN (an error: the LLM fixes it). Past MANY_HIGHLIGHTS all are kept, with a warning."""
    from lxml import etree
    ref, pts = comp["component_id"], items(comp)
    try:
        kids = [k for k in etree.fromstring(f"<x>{body}</x>") if isinstance(k.tag, str)]
    except etree.XMLSyntaxError:
        flag("NODE_HIGHLIGHT_UNKNOWN", ref, f'the children of <{TAG} ref="{ref}"> are not readable XML: write only '
             '<Highlight .../> elements inside it.')
        return None
    hs = [k for k in kids if k.tag == "Highlight"]
    if len(hs) < len(kids):
        flag("NODE_ATTR_DROPPED", ref, f'only <Highlight> goes inside <{TAG} ref="{ref}">: code writes the points; '
             'other children removed.')
    if not hs:
        return None
    if len(hs) > MANY_HIGHLIGHTS:
        flag("NODE_HIGHLIGHT_LIMIT", ref, f'{len(hs)} <Highlight>s on <{TAG} ref="{ref}">: all drawn, but more than '
             f'{MANY_HIGHLIGHTS} makes a heavily coloured list.')
    norm = lambda s: " ".join(str(s).split()).casefold()  # noqa: E731
    paint = Paint()

    def bad(msg: str) -> None:
        flag("NODE_HIGHLIGHT_UNKNOWN", ref, f'<Highlight> on <{TAG} ref="{ref}">: {msg}')

    for h in hs:
        at = {k: v.strip() for k, v in h.attrib.items()}
        if set(at) - HIGHLIGHT_ATTRS:
            bad(f'unknown attribute {", ".join(sorted(set(at) - HIGHLIGHT_ATTRS))} (use phrase / item, color, fill, bold).')
            continue
        tones = {k: at[k] for k in ("color", "fill") if k in at}
        if any(t not in TONES for t in tones.values()):
            bad(f'tones are {" / ".join(TONES)} ({tones}).')
            continue
        bold = at.get("bold") == "true"
        if not tones and not bold:
            bad('give it color, fill or bold="true".')
            continue
        if "phrase" in at:
            # one piece of a point (its head or its detail): a phrase across the split has no one run to colour
            hits = [i for i, s in enumerate(pts)
                    if any(at["phrase"].lower() in part.lower() for part in compose.split(s) if part)]
            if not hits or "fill" in at:
                bad(f'phrase "{at["phrase"]}" is not in one point\'s head or detail.' if not hits else 'a phrase takes color and bold only.')
                continue
            for i in hits:
                paint.phrases.setdefault(i, []).append((at["phrase"], TONE_ROLES[at["color"]] if "color" in at else None, bold))
            continue
        if "item" not in at:
            bad('name a phrase or an item.')
            continue
        heads = [norm(compose.split(s)[0]) for s in pts]
        whole = [norm(s) for s in pts]
        want = norm(at["item"])
        i = whole.index(want) if want in whole else heads.index(want) if want in heads else None
        if i is None:
            bad(f'item "{at["item"]}" is not a point (name it by its head or its whole text).')
            continue
        if "color" in at:
            paint.ink[i] = TONE_ROLES[at["color"]]
        if "fill" in at:
            paint.fill[i] = TONE_ROLES[at["fill"]]
        if bold:
            paint.phrases.setdefault(i, []).append((pts[i], None, True))
    return paint


# ── drawing ───────────────────────────────────────────────────────────────────

def run(text: str, color: str | None = None, bold: bool = False, italic: bool = False, underline: bool = False) -> str:
    out = X(text)
    if color:
        out = f'<Span color="{X(color)}">{out}</Span>'
    if italic:
        out = f"<I>{out}</I>"
    if underline:
        out = f"<U>{out}</U>"
    return f"<B>{out}</B>" if bold else out


def runs(text: str, part: dict, phrases: list[tuple[str, str | None, bool]], base: str | None = None) -> str:
    """The text in the part's style with each phrase (its first match) in its own colour / bold. `base`: the colour
    the parent already has, so no Span repeats it."""
    low, found = text.lower(), []
    for phrase, r, bold in phrases:
        s = low.find(phrase.lower())
        if s >= 0:
            found.append((s, len(phrase), r, bold))
    color = part.get("color")
    color = None if color == base else color
    bold, ital, und = part.get("bold") == "true", part.get("italic") == "true", part.get("underline") == "true"
    out, pos = [], 0
    for s, n, r, b in sorted(found, key=lambda f: f[0]):
        if s < pos:
            continue
        if s > pos:
            out.append(run(text[pos:s], color, bold, ital, und))
        out.append(run(text[s:s + n], f"${r}Text" if r else color, bold or b, ital, und))
        pos = s + n
    if pos < len(text):
        out.append(run(text[pos:], color, bold, ital, und))
    return "".join(out)


class Pick:
    """The parts of a point: the emphasis look on the hinted point, its highlight colour over them."""

    def __init__(self, rest: dict, hi: dict, focus: int | None, paint: Paint | None):
        self.rest, self.hi, self.focus, self.paint = rest, hi, focus, paint or Paint()

    def parts(self, i: int) -> dict:
        p = self.hi if self.focus == i else self.rest
        r = self.paint.ink.get(i)
        if r is None:
            return p
        ink = f"${r}Text"
        return {**p, "head": {**p["head"], "color": ink}, "detail": {**p["detail"], "color": ink},
                "marker": {**p["marker"], "color": f"${r}"}}

    def phrases(self, i: int) -> list:
        return self.paint.phrases.get(i, [])

    def box(self, i: int) -> dict:
        p = self.parts(i)["item"]
        return {**p, "backgroundColor": f"${self.paint.fill[i]}Soft"} if i in self.paint.fill else p


def list_post(cid: str, marker: str | None) -> str:
    """The marker colour for pptx-post.js (POM's lists have no attribute for it). Hyphens are escaped: a comment may
    not hold "--"."""
    spec_ = json.dumps({"id": f"lst-{cid}", "marker": marker or ""}, ensure_ascii=True).replace("-", "\\u002d")
    return f"<!-- list-post {spec_} -->"


def draw_native(comp: dict, box: dict, pick: Pick, numbered: bool, text: dict) -> str:
    cid, tag = comp["component_id"], "Ol" if numbered else "Ul"
    base = pick.rest["detail"].get("color")
    lis = []
    for i, s in enumerate(items(comp)):
        p = pick.parts(i)
        h, d = compose.split(s)
        ph = pick.phrases(i)
        if d:
            sep = s[len(h):len(s) - len(d)]
            lis.append(f'<Li>{runs(h, p["head"], ph, base)}{X(sep)}{runs(d, p["detail"], ph, base)}</Li>')
        else:   # a point with no head: its words in the detail's style, the emphasis colour on them all
            part = {**p["detail"], "color": p["head"]["color"]} if pick.focus == i else p["detail"]
            lis.append(f"<Li>{runs(s, part, ph, base)}</Li>")
    own = {"grow": "1", "fontSize": "20", "lineHeight": "1.4", **({"color": base} if base else {}), **text}
    marker = pick.rest["marker"].get("color")
    return (f'<VStack{A({"grow": "1", **box, "alignItems": "stretch"})}>{list_post(cid, marker)}'
            f'<{tag} id="lst-{cid}"{A(own)}>{"".join(lis)}</{tag}></VStack>')


def draw_rows(comp: dict, box: dict, pick: Pick, numbered: bool, icons: list[str], who: str, text: dict) -> str:
    cid = comp["component_id"]
    align = {"textAlign": text["textAlign"]} if "textAlign" in text else {}
    out = []
    for i, s in enumerate(items(comp)):
        p = pick.parts(i)
        ink = p["marker"]["color"]
        if numbered:
            m = f'<VStack w="60"><Text id="cardn-{cid}-{i}" fontSize="22" bold="true" color="{X(ink)}">{i + 1:02d}</Text></VStack>'
        elif icons:
            tone = "accent" if pick.paint.ink.get(i) is None and pick.focus != i else pick.paint.ink.get(i) or who
            m = f'<Icon name="{X(icons[i])}" size="22" variant="square-filled" bgColor="${tone}Soft" color="{X(ink)}" />'
        else:
            m = f'<VStack w="22" alignItems="center"><Shape shapeType="ellipse" w="10" h="10" fill.color="{X(ink)}" /></VStack>'
        h, d = compose.split(s)
        head = {k: v for k, v in p["head"].items() if k != "bold"}
        ph = pick.phrases(i)
        if d:
            words = (f'<Text id="lsth-{cid}-{i}" fontSize="17"{A(head)}{A(align)}{A({"bold": p["head"].get("bold", "true")})}>{runs(h, {}, ph)}</Text>'
                     f'<Text fontSize="16"{A(p["detail"])}{A(align)}>{runs(d, {}, ph)}</Text>')
        else:   # no head: the head's size and colour, regular, so a mixed list keeps one rhythm
            words = f'<Text fontSize="17"{A(head)}{A(align)}>{runs(s, {}, ph)}</Text>'
        rule = {} if i == 0 else {k: v for k, v in pick.box(i).items() if k.startswith("borderTop")}
        item = {**{k: v for k, v in pick.box(i).items() if not k.startswith("borderTop")}, **rule}
        attrs = {"id": f"card-{cid}-{i}", "grow": "1", "gap": "14", "alignItems": "center", "padding.top": "6",
                 "padding.bottom": "6", **item}
        out.append(f'<HStack{A(attrs)}>{m}<VStack w="1" grow="1" gap="2">{words}</VStack></HStack>')
    return f'<VStack{A({"gap": "0", "grow": "1", **box})}>{"".join(out)}</VStack>'


def _icons(meta: dict, name: str, n: int, ref: str, flag) -> list[str]:
    """The tag's icons, one exact name per point; otherwise none (dots), with the reason reported."""
    raw = [s.strip() for s in str(meta.get("icons") or "").split(",") if s.strip()]
    if not raw:
        return []
    if name != "rows":
        flag("NODE_ATTR_DROPPED", ref, f'icons on <{TAG} ref="{ref}">: only variant="rows" draws icons, not "{name}"; removed.')
        return []
    known = set(_ICON_NAMES.read_text(encoding="utf-8").split())
    wrong = [s for s in raw if s not in known]
    if wrong or len(raw) != n or n > MAX_ICONS:
        why = (f'unknown names: {", ".join(wrong)}' if wrong else f"{len(raw)} names for {n} points" if len(raw) != n
               else f"{n} points is past {MAX_ICONS}: rows that short have no room for an icon")
        flag("NODE_ATTR_DROPPED", ref, f'icons on <{TAG} ref="{ref}">: {why}; drawn with dots instead.')
        return []
    return raw


def _toned(parts: dict[str, dict], who: str) -> dict[str, dict]:
    return {p: {k: compose.tone_value(v, who) for k, v in at.items()} for p, at in parts.items()}


def draw(comp: dict, attrs: dict[str, str], flag, body: str = "") -> tuple[str, dict]:
    ref, nd, pts = comp["component_id"], node(), items(comp)
    paint = highlights(comp, body, flag) if body.strip() else None
    meta, box, parts = compose.read(attrs, ref, flag, nd)
    name, _ = compose.composition(nd, comp, meta.get("variant"), ref, flag)
    is_native = name.startswith("native")
    text = {k: box.pop(k) for k in TEXT_ATTRS if k in box}
    if is_native:
        for k in [k for k in NATIVE_NO_BOX if k in box]:
            flag("NODE_ATTR_DROPPED", ref, f'{k} on <{TAG} ref="{ref}">: a native list sits alone in its box; removed.')
            del box[k]
        for k in list(parts["item"]):
            flag("NODE_ATTR_DROPPED", ref, f'item.{k} on <{TAG} ref="{ref}">: a native list has no box per point; use '
                 'variant="rows"; removed.')
            del parts["item"][k]
        if paint and paint.fill:
            flag("NODE_ATTR_DROPPED", ref, f'<Highlight fill> on <{TAG} ref="{ref}">: a native list has no box per point; '
                 'use color, or variant="rows"; removed.')
            paint.fill = {}
    focus = None if paint else emphasis(comp)
    box, rest, hi = compose.layers(nd, name, box, parts, focus is not None)
    who = role(comp, focus)
    rest, hi = _toned(rest, "accent"), _toned(hi, who)
    if "color" in text:   # the whole list's words: over the look, under the LLM's own head. / detail.
        for p in (rest, hi):
            for part in ("head", "detail"):
                if "color" not in parts[part] and not (p is hi and focus is not None and part == "head"):
                    p[part]["color"] = text["color"]
    if text.get("italic") == "true":
        for p in (rest, hi):
            p["detail"].setdefault("italic", "true")
    pick = Pick(rest, hi, focus, paint)
    list_text = {k: v for k, v in text.items() if k == "textAlign"}
    icons = _icons(meta, name, len(pts), ref, flag)
    xml = (draw_native(comp, box, pick, name == "native numbered", list_text) if is_native
           else draw_rows(comp, box, pick, name == "rows numbered", icons, who, list_text))
    return xml, {"composition": name, "focus": focus, "icons": bool(icons),
                 "highlights": bool(paint and (paint.ink or paint.fill or paint.phrases))}


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <Ul ref="<bullet_list component id>"> drawn from the plan; a <Ul> with no ref stays the LLM's own."""
    def check(comp: dict, flag) -> bool:
        if items(comp):
            return True
        flag("NODE_ITEM_MISSING", comp["component_id"], f'bullet_list "{comp["component_id"]}" has no points in the plan.')
        return False

    return compose.expand(xml, components(plan), TAG, draw, check, children=True)


# ── prompt ─────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines (the cached part of the system prompt)."""
    vs = spec.blocks()["bullet_list"]["variants"]
    return "\n".join([
        "## BULLET LISTS (code draws them from the plan)",
        f'<{TAG} ref="<bullet_list id>" variant="..."/>: ' + "; ".join(f"{n} ({v['prompt']})" for n, v in vs.items()) + ".",
        'Code writes every point; never type one, no <Li>, no fontSize. variant="rows" takes icons="name,name,..." '
        f"(one exact icon name per point, in order, up to {MAX_ICONS} points; on no other variant). Layout (w, h, grow) and box attributes style "
        "the list's own box; parts head. detail. (the words: color bold italic underline) marker. (color) item. (a "
        "row's box, rows only) in $tokens; color on the tag colours all the words.",
        "Colour by meaning with <Highlight/> inside the tag (without them code colours the point the hint names); "
        "tones good | bad | watch | focus (emphasis, no meaning); name a point by its head or whole text, exactly as "
        "written, and copy a phrase exactly:",
        '  <Highlight phrase="spend still rising" color="bad"/> · <Highlight phrase="11.3x ROAS" bold="true"/> · '
        '<Highlight item="Product C drags" color="bad"/> · <Highlight item="Product C drags" fill="bad"/> (fill: rows only)',
        "Colour only what the headline or the hint is about.",
    ])


def tag_attributes() -> list[str]:
    from src.compiler.nodes import tiles
    nd = node()
    box = [a.split(".")[0] + ".*" if "." in a else a for a in tiles.data()["box_attributes"]]
    return list(dict.fromkeys(nd["meta"] + [f"{p}.*" for p in nd["parts"]] + list(TEXT_ATTRS) + ["borderRadius"] + box))


def prompt_line(comp: dict, headline: str = "") -> str:
    cid, pts = comp["component_id"], items(comp)
    ok = [n for n, v in node()["compositions"].items() if not spec.failed_requires(v, comp)]
    longest = max((len(s) for s in pts), default=0)
    split = sum(bool(compose.split(s)[1]) for s in pts)
    f = emphasis(comp)
    em = repr(compose.split(pts[f])[0]) if f is not None else "nothing"
    hint = " ".join(str(comp.get("design_hint") or "").split())
    head = (f"LIST {cid}: {len(pts)} points, {split} with a head; longest {longest} chars; variants " + " | ".join(ok))
    body = "\n".join(f"  - {s}" for s in pts)
    return (head + (f"\n  hint: {hint}" if hint else "") + f"\n{body}\n"
            f'<{TAG} ref="{cid}"/> (or with <Highlight/> inside; without them code colours {em}); the points are for '
            "reading: never type one yourself, code writes them from the plan")
