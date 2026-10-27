"""What every composition node shares (docs/composition-convention-spec.md §2): reading the LLM's attributes on a
group tag, choosing the composition, layering the default look, the emphasis and the LLM's attributes, the
"Head — detail" split, inner peer ids, and the tag loop. A node is one block-variants.yaml `nodes.<kind>` entry
(`nd`): tag, parts ({part: Text | Icon | Shape | Box}), meta, native_attributes, compositions, aliases, one_hue.
Used by charts.py and sequences.py.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from src.compiler.nodes import native, spec, tiles, validate

ERROR, WARNING, REPORT = "error", "warning", "report"
SEVERITY = {
    "NODE_REF_UNKNOWN": ERROR, "NODE_REF_DUPLICATE": ERROR, "NODE_ITEM_MISSING": ERROR, "NODE_ATTR_UNKNOWN": ERROR,
    "NODE_VARIANT_UNKNOWN": WARNING, "NODE_VARIANT_UNMET": WARNING, "LITERAL_COLOR": WARNING,
    "NODE_ATTR_DROPPED": REPORT, "NODE_ATTR_ALIAS": REPORT, "NODE_TEXT_SPLIT": REPORT,
    "NODE_DEFAULT_FROM_CONTENT": REPORT,
}
Flag = Callable[[str, "str | None", str], None]


def part_attrs(node_type: str) -> list[str]:
    """The attributes a part of this node type may carry (`Box`: a stack's box attributes)."""
    return list(tiles.data()["box_attributes"]) + ["borderRadius"] if node_type == "Box" else tiles.data()["part_nodes"][node_type]


def read(attrs: dict[str, str], ref: str, flag: Flag, nd: dict) -> tuple[dict, dict, dict]:
    """(meta, box, parts) of a group tag; the rest flagged as tiles._read does. Box attributes are the group's own box."""
    d, tag, parts_of = tiles.data(), nd["tag"], nd["parts"]
    dropped = set(d["dropped"]["parts"]) | set(d["dropped"]["box"]) - {"borderRadius"}   # a block's box may round
    box_ok = set(d["box_attributes"]) | {"borderRadius"} | set(nd.get("native_attributes") or [])
    owned = set(nd.get("code_owned") or [])
    meta, box, parts = {}, {}, {p: {} for p in parts_of}
    for k, v in attrs.items():
        if k in nd["meta"]:
            meta[k] = v
            continue
        if tiles._is_colour_attr(k) and not str(v).startswith("$"):
            flag("LITERAL_COLOR" if tiles._HEX.match(str(v)) else "NODE_ATTR_DROPPED", ref,
                 f'{k}="{v}" on <{tag} ref="{ref}">: colours are $tokens; removed.')
            continue
        head, _, rest = k.partition(".")
        if head in parts_of and rest:
            allowed = part_attrs(parts_of[head])
            if rest in dropped:
                flag("NODE_ATTR_DROPPED", ref, f'{k} on <{tag} ref="{ref}">: code owns the {rest}; removed.')
            elif rest not in allowed:
                flag("NODE_ATTR_UNKNOWN", ref, f'{k} on <{tag} ref="{ref}">: {head}. is a <{parts_of[head]}>; its '
                     f'attributes are {", ".join(allowed)}.')
            else:
                parts[head][rest] = v
        elif k in box_ok:
            box[k] = v
        elif k in owned or k in dropped:
            flag("NODE_ATTR_DROPPED", ref, f'{k} on <{tag} ref="{ref}">: code owns it; removed.')
        else:
            flag("NODE_ATTR_UNKNOWN", ref, f'{k} on <{tag} ref="{ref}">: not a {tag} node attribute (meta: '
                 f'{", ".join(nd["meta"])}; parts {" ".join(p + "." for p in parts_of)}; box attributes as a VStack).')
    return meta, box, parts


def composition(nd: dict, comp: dict, asked: str | None, ref: str, flag: Flag) -> tuple[str, dict[str, str]]:
    """(composition, extra meta from an alias). Unknown -> the default; unmet -> the fallback chain
    (spec.resolve_variant). A bare tag takes the first composition whose `requires` hold along that chain: the
    default chosen from the content (spec §8, F13), info NODE_DEFAULT_FROM_CONTENT when it is not the first."""
    cs, extra, tag = nd["compositions"], {}, nd["tag"]
    asked = " ".join(asked.split()) if asked else None
    alias = (nd.get("aliases") or {}).get(asked) if asked else None
    if alias is not None:
        extra = {k: v for k, v in alias.items() if k != "variant"} if isinstance(alias, dict) else {}
        new = alias["variant"] if isinstance(alias, dict) else alias
        flag("NODE_ATTR_ALIAS", ref, f'variant="{asked}" on <{tag} ref="{ref}"> is now variant="{new}"'
             + "".join(f' {k}="{v}"' for k, v in extra.items()) + ".")
        asked = new
    if not asked:
        first = next(iter(cs))
        name, code, note = spec.resolve_variant(nd["plan_kind"], tag, comp, first, vs=cs)
        if code:
            flag("NODE_DEFAULT_FROM_CONTENT", ref, f'ref="{ref}": {note.replace("variant ", "composition ")}.')
        return name or first, extra
    name, code, note = spec.resolve_variant(nd["plan_kind"], tag, comp, asked, vs=cs)
    if code:
        flag(code, ref, f'ref="{ref}": {note}.')
    return name or next(iter(cs)), extra


def layers(nd: dict, name: str, box: dict, parts: dict, focus: bool) -> tuple[dict, dict, dict]:
    """(box, parts of the rest, parts of the emphasis item): look -> the LLM's group attributes, and on the emphasis
    item look -> emphasis -> the group attributes the emphasis look does not set (the LLM restyles the emphasis
    item but cannot remove it). With no emphasis item every item's `one_hue` part takes its emphasis colours."""
    c = nd["compositions"][name]
    rbox, rest = {}, {p: {} for p in nd["parts"]}
    for k, v in (c.get("look") or {}).items():
        head, _, sub = k.partition(".")
        if head in rest and sub:
            rest[head][sub] = str(v)
        else:
            rbox[k] = str(v)
    hi = {p: dict(a) for p, a in rest.items()}
    emph = c.get("emphasis") or {}
    for k, v in emph.items():
        head, _, sub = k.partition(".")
        hi[head][sub] = str(v)
    if not focus:
        mark = nd.get("one_hue")
        if mark:
            rest[mark].update({sub: v for sub, v in hi[mark].items() if tiles._is_colour_attr(sub)})
        hi = rest
    rbox.update(box)
    for p, a in parts.items():
        rest[p].update(a)
        if focus:
            hi[p].update({k: v for k, v in a.items() if f"{p}.{k}" not in emph})
    return rbox, rest, hi


def a(attrs: dict[str, str]) -> str:
    return "".join(f' {k}="{native.x(v)}"' for k, v in attrs.items())


def text(s: str, px: int, part: dict[str, str], **kw: str) -> str:
    return f'<Text fontSize="{px}"{a({**kw, **part})}>{native.x(s)}</Text>'


_DASH = re.compile(r"\s+[—–]\s+")
_COLON = re.compile(r":\s+")


def split(s: str) -> tuple[str, str]:
    """'Head — detail' / 'Head: detail' -> (head, detail), every word kept: at the first " — " and only then at ": "
    (C10: "Phase 1: Foundation — detail" keeps the head "Phase 1: Foundation")."""
    s = str(s or "").strip()
    for rx in (_DASH, _COLON):
        parts = rx.split(s, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), parts[1].strip()
    return s, ""


_OWN_ORDINAL = re.compile(r"^\s*(?:\d+[.)]|0\d\b|(?:phase|step|stage|wave)\s+\d+\b)", re.I)


def own_ordinal(s: str) -> bool:
    """The item already carries its own number ("Phase 1: …", "01. …"): `numbered` would repeat it (C10)."""
    return bool(_OWN_ORDINAL.match(str(s or "")))


_DATED = re.compile(r"^\s*(?:Q[1-4]|H[12]|FY\s?\d|CY\s?\d|W\d|(?:19|20)\d\d|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
                    re.I)


def dated(s: str) -> bool:
    """The item opens with a date or period ("Q1: …", "Jul–Aug — …"): dated steps are not numbered."""
    return bool(_DATED.match(str(s or "")))


def before_layer(nd: dict, name: str, rest: dict) -> dict:
    """The parts of an item before the emphasis item: `rest` with the composition's `before` look over it."""
    out = {p: dict(a) for p, a in rest.items()}
    for k, v in (nd["compositions"][name].get("before") or {}).items():
        head, _, sub = k.partition(".")
        out[head][sub] = str(v)
    return out


_STACK = re.compile(r"<(/?)(VStack|HStack)\b([^<>]*?)(/?)>")


def inner_ids(xml: str) -> str:
    """Every box inside an item (id card-<cid>-<i>) without an id gets card-<cid>x-<n>: one fit-grow peer group per
    block, so an item whose children stretch does not grow its inner boxes alone (C11)."""
    stack, k = [], 0

    def sub(m: re.Match) -> str:
        nonlocal k
        close, tag, attrs, selfclose = m.groups()
        if close:
            stack.pop()
            return m.group(0)
        own = re.search(r'\sid="(card-[^"]+)"', attrs)
        owner = own.group(1) if own else (stack[-1] if stack else None)
        if owner and not own and 'id="' not in attrs:
            k += 1
            attrs += f' id="{owner.rsplit("-", 1)[0]}x-{k}"'
        if not selfclose:
            stack.append(owner)
        return f"<{tag}{attrs}{selfclose}>"

    return _STACK.sub(sub, xml)


def expand(xml: str, comps: dict[str, dict], tag: str, draw: Callable[..., tuple[str, dict]],
           check: Callable[[dict, Flag], bool] | None = None) -> dict[str, Any]:
    """Every <tag ref="<component id>"/> drawn by `draw(comp, attrs, flag)`. A tag without ref is the LLM's own;
    a ref naming no component of the node's kind is NODE_REF_UNKNOWN. `check(comp, flag)` False: not drawn."""
    issues: list[dict[str, Any]] = []
    done: dict[str, dict] = {}

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY.get(code, WARNING), "ref": ref, "message": message})

    out, pos = [], 0
    for t in validate.ref_tags(xml):
        if t["tag"] != tag:
            continue
        ref = t["attrs"]["ref"]
        out.append(xml[pos:t["start"]])
        pos = t["end"]
        comp = comps.get(ref)
        if comp is None:
            flag("NODE_REF_UNKNOWN", ref, f'<{tag} ref="{ref}">: no such component on this slide '
                 f'({", ".join(comps) or "none"}).')
            continue
        if ref in done:
            flag("NODE_REF_DUPLICATE", ref, f'<{tag} ref="{ref}"> twice: each component once.')
            continue
        if check and not check(comp, flag):
            continue
        if t["body"].strip():
            flag("NODE_ATTR_DROPPED", ref, f'children inside <{tag} ref="{ref}">: code writes it from the plan; removed.')
        drawn, done[ref] = draw(comp, t["attrs"], flag)
        out.append(inner_ids(drawn))
    out.append(xml[pos:])
    return {"xml": "".join(out), "issues": issues, "ok": not any(i["severity"] == ERROR for i in issues),
            "components": done}
