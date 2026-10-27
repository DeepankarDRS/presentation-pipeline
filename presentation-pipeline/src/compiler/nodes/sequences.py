"""Timeline, process_arrow and flow composition nodes (composition spec §8, approved 2026-10-27), one expander,
`POM_NODES=timeline,process_arrow,flow` (each kind on its own).

The LLM writes one self-closing tag per component; code draws it from the plan:

    <Timeline ref="roadmap" variant="banded" grow="1"/>     <ProcessArrow ref="phases" variant="steps numbered"/>

Compositions (block-variants.yaml `nodes.<kind>`; the gallery sheets docs/eval/composition-left/ are what they draw):
- timeline: `native` (POM's Timeline; only when every label is short and has no detail, else `rail`), `rail` (a line
  with a dot per point, a box per point under it), `rows` (date · head · detail per ruled row), `banded` (the date in
  a solid band: done / now / ahead).
- process_arrow: `native` (chevrons; short steps only, else `steps`), `steps` (boxes joined by arrows),
  `steps numbered` (+ a numbered circle over each box), `rail` (numbered dots on a line, labels alternating).
- flow: `native` (POM's Flow), `steps`, `steps numbered`.
A bare tag takes the first composition whose `requires` hold (the default chosen from the content, F13).

Code owns every word (a string item shows as head + detail, split at " — " then ": ", every word kept), the order,
the numbers, arrows and lines, and the emphasis item: a timeline's point the design hint names ("now"), a process /
flow's destination (the last step). The LLM owns the box (layout and box attributes on the tag) and part styles
(`date.` `label.` `description.` `marker.` `number.` `connector.` `band.` `item.`), $tokens only.
"""

from __future__ import annotations

from typing import Any

from src.compiler import normalizer
from src.compiler.nodes import compose, native, spec

KINDS = ("timeline", "process_arrow", "flow")
TAGS = {"timeline": "Timeline", "process_arrow": "ProcessArrow", "flow": "Flow"}
LIST_KEY = {"timeline": "timeline_items", "process_arrow": "process_steps", "flow": "flow_steps"}
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
    """(date, head, detail) per item; the detail split off a string item (compose.split) unless the plan gives one."""
    cd = comp.get("content_data") or {}
    if comp["kind"] == "timeline":
        out = []
        for i in cd.get("timeline_items") or []:
            label, desc = str(i.get("label") or i.get("title") or ""), str(i.get("description") or "").strip()
            out.append((str(i.get("date") or ""), *((label, desc) if desc else compose.split(label))))
        return out
    return [("", *compose.split(s)) for s in cd.get(LIST_KEY[comp["kind"]]) or []]


def emphasis_index(comp: dict) -> int | None:
    """Process / flow: the destination. Timeline: the one point the design hint names by its date or head."""
    its = items(comp)
    if comp["kind"] != "timeline":
        return len(its) - 1 if len(its) > 1 else None
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


def _raw(comp: dict) -> list[str]:
    return [str(s) for s in (comp.get("content_data") or {}).get(LIST_KEY[comp["kind"]]) or []]


def process_native(comp, its, box, styles, focus, meta) -> str:
    rest, hi = styles[0], styles[1]
    st = "".join(f'<ProcessArrowStep label="{native.x(s)}"{A(_native_item(_style(k, focus, rest, hi, rest)))} />'
                 for k, s in enumerate(_raw(comp)))
    own = {"direction": _direction(comp, meta), "fontSize": "18", "bold": "true", "w": "max"}
    return f"<ProcessArrow{A({**own, **box})}>{st}</ProcessArrow>"


def _native_item(p: dict) -> dict[str, str]:
    return {"color": p["item"].get("backgroundColor", "$accentSoft"), "textColor": p["label"].get("color", "$textMain")}


def flow_native(comp, its, box, styles, focus, meta) -> str:
    rest, hi = styles[0], styles[1]
    st = _raw(comp)
    last = len(st) - 1
    nodes = "".join(f'<FlowNode id="n{k}" shape="{"flowChartTerminator" if k in (0, last) else "flowChartProcess"}" '
                    f'text="{native.x(s)}"{A(_native_item(_style(k, focus, rest, hi, rest)))} />' for k, s in enumerate(st))
    links = "".join(f'<FlowConnection from="n{k}" to="n{k + 1}" />' for k in range(last))
    own = {"direction": _direction(comp, meta), "w": "max", "h": "max",
           "connectorStyle.color": rest["connector"].get("color", "$neutral")}
    return f"<Flow{A({**own, **box})}>{nodes}{links}</Flow>"


def steps(comp, its, box, styles, focus, meta, numbered: bool = False) -> str:
    cid, out = comp["component_id"], []
    for k, (_, h, x) in enumerate(its):
        p = _style(k, focus, *styles)
        if k:
            out.append(f'<VStack w="32" justifyContent="center"><Icon{A({"name": "arrow-right", "size": "26", **p["connector"]})} /></VStack>')
        num = p["number"]
        circle = (f'<HStack justifyContent="center"><Shape{A({"shapeType": "ellipse", "w": "52", "h": "52", "text": str(k + 1), "fontSize": "22", "bold": "true", **num})} />'
                  "</HStack>") if numbered else ""
        out.append(f'<VStack w="1" grow="1" gap="12" alignItems="stretch">{circle}'
                   f'<VStack id="card-{cid}-{k}" w="100%" grow="1" gap="8" justifyContent="center"{A(p["item"])}>'
                   f'{T(h, 21, p["label"], bold="true", textAlign="center")}'
                   + (T(x, 16, p["description"], textAlign="center") if x else "") + "</VStack></VStack>")
    return f'<HStack gap="8" alignItems="stretch"{A(box)}>{"".join(out)}</HStack>'


def rail(comp, its, box, styles, focus, meta) -> str:
    cid, cols, last = comp["component_id"], [], len(its) - 1
    for k, (_, h, x) in enumerate(its):
        p = _style(k, focus, *styles)
        txt = (f'<VStack id="card-{cid}-{k}" h="130" gap="4" justifyContent="{"end" if k % 2 == 0 else "start"}">'
               f'{T(h, 21, p["label"], bold="true", textAlign="center")}'
               + (T(x, 16, p["description"], textAlign="center") if x else "") + "</VStack>")
        line = lambda on: f'<Shape{A({"shapeType": "rect", "w": "max", "grow": "1", "h": "3", "fill.color": p["connector"].get("color", "$border") if on else "$surface"})} />'  # noqa: E731
        dot = f'<Shape{A({"shapeType": "ellipse", "w": "40", "h": "40", "text": str(k + 1), "fontSize": "18", "bold": "true", **p["marker"], **{"color": p["number"].get("color", "$onAccent")}})} />'
        empty = '<VStack h="130" />'
        cols.append(f'<VStack w="1" grow="1" gap="12" alignItems="stretch">{empty if k % 2 else txt}'
                    f'<HStack alignItems="center">{line(k > 0)}{dot}{line(k < last)}</HStack>{txt if k % 2 else empty}</VStack>')
    return f'<VStack justifyContent="center"{A(box)}><HStack gap="0" alignItems="stretch">{"".join(cols)}</HStack></VStack>'


DRAW = {
    "timeline": {"native": timeline_native, "rail": timeline_rail, "rows": timeline_rows, "banded": timeline_banded},
    "process_arrow": {"native": process_native, "steps": steps,
                      "steps numbered": lambda *a: steps(*a, numbered=True), "rail": rail},
    "flow": {"native": flow_native, "steps": steps, "steps numbered": lambda *a: steps(*a, numbered=True)},
}
SHOWS_DETAIL = {"rail", "rows", "banded", "steps", "steps numbered"}


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
    if not ({"h", "grow"} & set(box)):
        box["grow"] = "1"
    split = [k for k, s in enumerate(_raw(comp)) if compose.split(s)[1]] if kind != "timeline" else \
        [k for k, i in enumerate((comp.get("content_data") or {}).get("timeline_items") or [])
         if not str(i.get("description") or "").strip() and compose.split(str(i.get("label") or ""))[1]]
    if split and name in SHOWS_DETAIL | ({"native"} if kind == "timeline" else set()):
        flag("NODE_TEXT_SPLIT", ref, f'ref="{ref}": items {", ".join(map(str, split))} drawn as head + detail '
             '(split at " — " or ": "; every word kept).')
    xml = DRAW[kind][name](comp, its, box, (rest, hi, done), focus, meta)
    return xml, {"composition": name, "focus": focus}


def expand(xml: str, plan: dict | None) -> dict[str, Any]:
    """Every <Timeline / ProcessArrow / Flow ref> of the kinds switched on, drawn from the plan."""
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
    lines = ["## TIMELINES, PROCESSES, FLOWS (code draws them from the plan)"]
    for kind in kinds_on():
        vs = spec.blocks()[kind]["variants"]
        lines.append(f'<{TAGS[kind]} ref="<{kind} id>" variant="..."/>: ' + "; ".join(f"{n} ({v['prompt']})" for n, v in vs.items())
                     + ". A bare tag takes the first that fits the content.")
    parts = sorted({p for k in kinds_on() for p in node(k)["parts"]})
    lines.append("Self-closing: code writes every date, label and step, the numbers, arrows and lines, and the emphasis "
                 "(a timeline's 'now' from the plan, a process's destination). Layout (w, h, grow) and box attributes "
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
    noun = {"timeline": "points", "process_arrow": "steps", "flow": "steps"}[kind]
    parts = [f"{kind.upper().replace('_', ' ')} {cid}: {len(its)} {noun}",
             f"longest head {max((len(h) for _, h, _ in its), default=0)} chars"
             + (", details after the head" if any(x for _, _, x in its) else ""),
             (f"emphasis {f}" if f is not None else "no emphasis point"), "variants " + " | ".join(ok)]
    return "; ".join(parts) + f'. <{TAGS[kind]} ref="{cid}"/>; never type a date, label or step yourself: code writes them'
