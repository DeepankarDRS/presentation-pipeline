"""Timeline composition node (composition spec §8, approved 2026-10-27), `POM_NODES=timeline`. process_arrow and flow
have no node (user, 2026-11-02): POM's chevrons and flow boxes hold about two words at a fixed size, so the LLM draws
them as before.

The LLM writes one self-closing tag per component; code draws it from the plan:

    <Timeline ref="roadmap" variant="banded" grow="1"/>

Compositions (block-variants.yaml `nodes.timeline`; docs/eval/sequence-nodes/native-vs-derived-timeline.png):
`native` (POM's Timeline; only when every label is short and has no detail, else `rail`), `rail` (dots on a line,
date / head / detail alternating above and below it; at most 7 points, else `columns`), `columns` (a line with a dot
per point, a box per point under it), `rows` (date · head · detail per ruled row), `banded` (the date in a solid band:
done / now / ahead). A bare tag takes the first composition whose `requires` hold (the default chosen from the
content, F13).

Code owns every word (a label shows as head + detail, split at " — " then ": ", every word kept), the order, the dots
and lines, and the emphasis: the point the design hint names ("now"). The LLM owns the box (layout and box attributes
on the tag) and part styles (`date.` `label.` `description.` `marker.` `connector.` `band.` `item.`), $tokens only.
"""

from __future__ import annotations

from typing import Any

from src.compiler import normalizer
from src.compiler.nodes import compose, native, spec

KINDS = ("timeline",)
TAGS = {"timeline": "Timeline"}
SEVERITY = compose.SEVERITY


def on(kind: str) -> bool:
    return kind in KINDS and spec.nodes_on(kind)


def kinds_on() -> list[str]:
    return [k for k in KINDS if on(k)]


def node(kind: str) -> dict[str, Any]:
    return spec.nodes()[kind]


def components(plan: dict | None, kind: str) -> dict[str, dict]:
    return {c["component_id"]: c for c in (plan or {}).get("components") or []
            if c.get("kind") == kind and c.get("component_id")}


def items(comp: dict) -> list[tuple[str, str, str]]:
    """(date, head, detail) per point; the detail split off the label (compose.split) unless the plan gives one."""
    out = []
    for i in (comp.get("content_data") or {}).get("timeline_items") or []:
        label, desc = str(i.get("label") or i.get("title") or ""), str(i.get("description") or "").strip()
        out.append((str(i.get("date") or ""), *((label, desc) if desc else compose.split(label))))
    return out


def emphasis_index(comp: dict) -> int | None:
    """The one point the design hint names by its date or head."""
    its = items(comp)
    hint = str(comp.get("design_hint") or "")
    named = [k for k, (d, h, _) in enumerate(its) if (d and normalizer._names(d, hint)) or (h and normalizer._names(h, hint))]
    return named[0] if len(named) == 1 else None


def _direction(comp: dict, meta: dict) -> str:
    d = meta.get("direction")
    return d if d in ("horizontal", "vertical") else native._direction(comp, comp.get("content_data") or {})


# ── compositions ──────────────────────────────────────────────────────────────

T = compose.text
A = compose.a


def _style(k: int, focus: int | None, rest: dict, hi: dict, done: dict) -> dict:
    return hi if k == focus else (done if focus is not None and k < focus else rest)


def timeline_native(comp, its, box, styles, focus, meta) -> str:
    rest, hi = styles[0], styles[1]
    tl = "".join(f'<TimelineItem date="{native.x(d)}" title="{native.x(h)}"'
                 + (f' description="{native.x(x)}"' if x else "")
                 + f' color="{native.x(_style(k, focus, rest, hi, rest)["marker"].get("fill.color", "$accent"))}" />'
                 for k, (d, h, x) in enumerate(its))
    own = {"direction": _direction(comp, meta), "dateColor": rest["date"].get("color", "$accentText"),
           "titleColor": rest["label"].get("color", "$textMain"),
           "descriptionColor": rest["description"].get("color", "$textMuted"),
           "connectorColor": rest["connector"].get("fill.color", "$border"), "w": "max"}
    return f"<Timeline{A({**own, **box})}>{tl}</Timeline>"


def timeline_rail(comp, its, box, styles, focus, meta) -> str:
    """Dots on a line; each point's date, head and detail above it (even points) or below it (odd ones), so
    neighbours on one side stand a column apart. Three rows of equal columns keep every dot under its text."""
    cid, last = comp["component_id"], len(its) - 1
    top, dots, bottom = [], [], []
    gap = '<VStack w="max" grow="1" />'
    for k, (d, h, x) in enumerate(its):
        p = _style(k, focus, *styles)
        txt = (f'<VStack id="card-{cid}-{k}" w="1" grow="1" gap="4" padding="6">'
               + (T(d.upper(), 14, p["date"], bold="true", letterSpacing="1", textAlign="center") if d else "")
               + T(h, 21, p["label"], bold="true", textAlign="center")
               + (T(x, 16, p["description"], textAlign="center") if x else "") + "</VStack>")
        line = f'<Shape{A({"shapeType": "rect", "w": "max", "grow": "1", "h": "3", **p["connector"]})} />'
        dot = f'<Shape{A({"shapeType": "ellipse", "w": "22", "h": "22", **p["marker"]})} />'
        (top if k % 2 == 0 else bottom).append(txt)
        (bottom if k % 2 == 0 else top).append('<VStack w="1" grow="1" />')
        dots.append(f'<HStack w="1" grow="1" alignItems="center" gap="0">{line if k else gap}{dot}{line if k < last else gap}</HStack>')
    return (f'<VStack gap="14" justifyContent="center"{A(box)}>'
            f'<HStack gap="0" alignItems="end">{"".join(top)}</HStack>'
            f'<HStack gap="0" alignItems="center">{"".join(dots)}</HStack>'
            f'<HStack gap="0" alignItems="start">{"".join(bottom)}</HStack></VStack>')


def timeline_columns(comp, its, box, styles, focus, meta) -> str:
    cid, cols = comp["component_id"], []
    for k, (d, h, x) in enumerate(its):
        p = _style(k, focus, *styles)
        cols.append(f'<VStack w="1" grow="1" gap="14" alignItems="stretch">'
                    f'<HStack alignItems="center" gap="0"><Shape{A({"shapeType": "ellipse", "w": "18", "h": "18", **p["marker"]})} />'
                    f'<Shape{A({"shapeType": "rect", "w": "max", "grow": "1", "h": "2", **p["connector"]})} /></HStack>'
                    f'<VStack id="card-{cid}-{k}" grow="1" gap="6"{A(p["item"])}>'
                    f'{T(d.upper(), 14, p["date"], bold="true", letterSpacing="1")}{T(h, 22, p["label"], bold="true")}'
                    + (T(x, 17, p["description"]) if x else "") + "</VStack></VStack>")
    return f'<HStack gap="16" alignItems="stretch"{A(box)}>{"".join(cols)}</HStack>'


def timeline_banded(comp, its, box, styles, focus, meta) -> str:
    cid, cols = comp["component_id"], []
    for k, (d, h, x) in enumerate(its):
        p = _style(k, focus, *styles)
        cols.append(f'<VStack id="card-{cid}-{k}" w="1" grow="1" gap="0"{A({k2: v for k2, v in p["item"].items() if k2 != "backgroundColor"})}>'
                    f'<HStack padding="12"{A(p["band"])}>{T(d.upper(), 16, p["date"], bold="true", letterSpacing="1")}</HStack>'
                    f'<VStack grow="1" gap="8" padding="18"{A({"backgroundColor": p["item"].get("backgroundColor", "$surfaceAlt")})}>'
                    f'{T(h, 21, p["label"], bold="true")}' + (T(x, 17, p["description"]) if x else "") + "</VStack></VStack>")
    return f'<HStack gap="12" alignItems="stretch"{A(box)}>{"".join(cols)}</HStack>'


def timeline_rows(comp, its, box, styles, focus, meta) -> str:
    cid, out = comp["component_id"], []
    for k, (d, h, x) in enumerate(its):
        p = _style(k, focus, *styles)
        item = {kk: v for kk, v in p["item"].items() if k or not kk.startswith("borderTop")}   # no rule above the first
        out.append(f'<HStack id="card-{cid}-{k}" grow="1" gap="24" alignItems="center" padding="12"{A(item)}>'
                   f'<VStack w="150">{T(d.upper(), 18, p["date"], bold="true", letterSpacing="1")}</VStack>'
                   f'<VStack w="34%">{T(h, 22, p["label"], bold="true")}</VStack>'
                   f'<VStack w="1" grow="1">{T(x, 18, p["description"]) if x else ""}</VStack></HStack>')
    return f'<VStack gap="0"{A(box)}>{"".join(out)}</VStack>'


DRAW = {"native": timeline_native, "rail": timeline_rail, "columns": timeline_columns, "rows": timeline_rows,
        "banded": timeline_banded}


def draw(comp: dict, attrs: dict[str, str], flag) -> tuple[str, dict]:
    """One tag -> its XML, and what was drawn."""
    kind, ref = comp["kind"], comp["component_id"]
    nd = node(kind)
    meta, box, parts = compose.read(attrs, ref, flag, nd)
    name, extra = compose.composition(nd, comp, meta.get("variant"), ref, flag)
    meta = {**extra, **meta}
    its, focus = items(comp), emphasis_index(comp)
    box, rest, hi = compose.layers(nd, name, box, parts, focus is not None)
    done = compose.before_layer(nd, name, rest)
    asked = (nd.get("aliases") or {}).get(meta.get("variant"), meta.get("variant")) or next(iter(nd["compositions"]))
    asked = asked["variant"] if isinstance(asked, dict) else " ".join(str(asked).split())
    if name != asked and "h" in box:   # an h sized for the drawing the LLM expected (a dot row of 92 px) is a floor
        box.setdefault("minH", box.pop("h"))   # for the one drawn instead (replay 2026-10-28: step boxes spilled)
    if not ({"h", "grow"} & set(box)):
        box["grow"] = "1"
    split = [k for k, i in enumerate((comp.get("content_data") or {}).get("timeline_items") or [])
             if not str(i.get("description") or "").strip() and compose.split(str(i.get("label") or ""))[1]]
    if split:
        flag("NODE_TEXT_SPLIT", ref, f'ref="{ref}": items {", ".join(map(str, split))} drawn as head + detail '
             '(split at " — " or ": "; every word kept).')
    xml = DRAW[name](comp, its, box, (rest, hi, done), focus, meta)
    return xml, {"composition": name, "focus": focus}


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <Timeline ref>, drawn from the plan (when POM_NODES has timeline)."""
    out = {"xml": xml, "issues": [], "ok": True, "components": {}}
    for kind in kinds_on():
        def check(comp: dict, flag) -> bool:
            if items(comp):
                return True
            flag("NODE_ITEM_MISSING", comp["component_id"], f'{kind} "{comp["component_id"]}" has no items in the plan.')
            return False
        r = compose.expand(out["xml"], components(plan, kind), TAGS[kind], draw, check)
        out = {"xml": r["xml"], "issues": out["issues"] + r["issues"], "ok": out["ok"] and r["ok"],
               "components": {**out["components"], **r["components"]}}
    return out


# ── prompt ─────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines for the kinds switched on (the cached part of the system prompt)."""
    lines = ["## TIMELINES (code draws them from the plan)"]
    for kind in kinds_on():
        vs = spec.blocks()[kind]["variants"]
        lines.append(f'<{TAGS[kind]} ref="<{kind} id>" variant="..."/>: ' + "; ".join(f"{n} ({v['prompt']})" for n, v in vs.items())
                     + ". A bare tag takes the first that fits the content.")
    parts = sorted({p for k in kinds_on() for p in node(k)["parts"]})
    lines.append("Self-closing: code writes every date and label, the dots and lines, and the emphasis "
                 "(the 'now' point from the plan). Layout (w, h, grow) and box attributes "
                 f"style the block's own box; parts {' '.join(p + '.' for p in parts)} take their node's attributes in "
                 '$tokens (item.backgroundColor="$accentSoft" marker.fill.color="$accent"). No fontSize.')
    return "\n".join(lines)


def tag_attributes(kind: str) -> list[str]:
    nd = node(kind)
    from src.compiler.nodes import tiles
    box = [a.split(".")[0] + ".*" if "." in a else a for a in tiles.data()["box_attributes"]]
    return list(dict.fromkeys(nd["meta"] + [f"{p}.*" for p in nd["parts"]] + ["borderRadius"] + box))


def prompt_line(comp: dict, headline: str = "") -> str:
    kind, cid = comp["kind"], comp["component_id"]
    its, f = items(comp), emphasis_index(comp)
    ok = [n for n, v in node(kind)["compositions"].items() if not spec.failed_requires(v, comp)]
    parts = [f"TIMELINE {cid}: {len(its)} points",
             f"longest head {max((len(h) for _, h, _ in its), default=0)} chars"
             + (", details after the head" if any(x for _, _, x in its) else ""),
             (f"emphasis {f}" if f is not None else "no emphasis point"), "variants " + " | ".join(ok)]
    return "; ".join(parts) + f'. <{TAGS[kind]} ref="{cid}"/>; never type a date or label yourself: code writes them'
