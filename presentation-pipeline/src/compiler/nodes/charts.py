"""Chart composition node (docs/composition-convention-spec.md §8, approved 2026-10-27), `POM_NODES=chart`.

The LLM writes one self-closing tag per chart component; code draws it from the plan:

    <Chart ref="roas" variant="rows" grow="1" bar.fill.color="$accentSoft"/>

`variant` names a composition (block-variants.yaml `nodes.chart.compositions`; the first is the default):
- `native`: POM's Chart on its card ($chartSurface, so POM's black axis text reads on dark palettes). One hue: the
  emphasis point $accent, the rest $neutral; with no emphasis point every bar $accent. Several series, pie and
  doughnut take $chart1..N.
- `native labelled`: `native` + each bar's value as a native data label in the plan's unit (number format from the
  value strings, ink from `label.color`, default $chartInk) and no value axis. pptx-post.js writes the labels from
  the `<!-- chart-post {...} -->` comment placed before the Chart.
- `rows`: one row per point: label · a Shape bar of code-measured length · the plan's value verbatim (unit kept).
  Values carry kpiv- ids so fit-grow grows them as one group of values (C12); rows carry card-<cid>-<i>, inner
  boxes card-<cid>x-<n> (C11).

Code owns every label and value, the chart type, the series colours and the emphasis point: the bar / series the
slide headline names, else the latest period (the chart pass rule, normalizer._chart_focus, which runs after this),
else the one point the design hint names. The LLM owns the box (layout and box attributes on the tag: the card's
own box) and part styles (`title.` `label.` `value.` `bar.`), in $tokens only.

    result = expand(xml, plan)    # {xml, issues, ok, components: {cid: {composition, focus}}}
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.compiler import normalizer
from src.compiler.palette_tokens import MAX_CHART_COLORS
from src.compiler.nodes import native, spec, tiles, validate

ERROR, WARNING, REPORT = "error", "warning", "report"
SEVERITY = {
    "NODE_REF_UNKNOWN": ERROR, "NODE_REF_DUPLICATE": ERROR, "NODE_ITEM_MISSING": ERROR, "NODE_ATTR_UNKNOWN": ERROR,
    "NODE_VARIANT_UNKNOWN": WARNING, "NODE_VARIANT_UNMET": WARNING, "LITERAL_COLOR": WARNING,
    "NODE_ATTR_DROPPED": REPORT, "NODE_ATTR_ALIAS": REPORT,
}
TAG = "Chart"
LAYOUT = set(native.LAYOUT)
TITLE_PX, LABEL_PX, VALUE_PX = 14, 20, 24
BAR_PX = 36
_NUM = re.compile(r"^(?P<pre>[^\d+\-−]*)(?P<sign>[+\-−]?)(?P<num>\d[\d,]*(?:\.(?P<dec>\d+))?)(?P<suf>.*)$")


def on() -> bool:
    return spec.nodes_on("chart")


def node() -> dict[str, Any]:
    return spec.nodes()["chart"]


def chart_components(plan: dict | None) -> dict[str, dict]:
    return {c["component_id"]: c for c in (plan or {}).get("components") or []
            if c.get("kind") == "chart" and c.get("component_id")}


def _cd(comp: dict) -> dict:
    return comp.get("content_data") or {}


def _series(comp: dict) -> list[dict]:
    cd = _cd(comp)
    return cd.get("chart_series") or [{"name": cd.get("chart_title") or "Series 1", "values": cd.get("chart_values") or []}]


def kind_of(comp: dict) -> str:
    k = str(_cd(comp).get("chart_type") or comp.get("chart_type") or "bar").lower()
    return {"donut": "doughnut"}.get(k, k)


def focus_index(comp: dict, headline: str) -> int | None:
    """The point (one series) or series (several) the slide singles out: named in the headline, else the latest
    period (normalizer._chart_focus, the same order, so it never moves this one), else the one the hint names."""
    series = _series(comp)
    names = [str(s.get("name") or "") for s in series] if len(series) > 1 else [str(v) for v in _cd(comp).get("chart_labels") or []]
    if len(names) < 2:
        return None
    named = [i for i, n in enumerate(names) if normalizer._names(n, headline)]
    if named:
        return min(named, key=lambda i: normalizer._name_at(names[i], headline))
    if kind_of(comp) in normalizer._TIME_KINDS and all(normalizer._PERIOD_RE.match(n.strip()) for n in names) \
            and (len(series) > 1 or len(names) >= 3):
        return len(names) - 1
    hint = str(comp.get("design_hint") or "")
    named = [i for i, n in enumerate(names) if normalizer._names(n, hint)]
    return named[0] if len(named) == 1 else None


def number_format(values: list) -> str:
    """An Excel number format that writes the plan's value strings as typed: "0.29x" -> 0.00"x", "₹1,234 Cr" ->
    "₹"#,##0" Cr". "General" when the values are not strings sharing one prefix, suffix and decimals (C6)."""
    if not values or not all(isinstance(v, str) for v in values):
        return "General"
    ms = [_NUM.match(v.strip()) for v in values]
    if not all(ms):
        return "General"
    pre, suf = {m.group("pre") for m in ms}, {m.group("suf") for m in ms}
    if len(pre) != 1 or len(suf) != 1:
        return "General"
    dec = max(len(m.group("dec") or "") for m in ms)
    body = ("#,##0" if any("," in m.group("num") for m in ms) else "0") + ("." + "0" * dec if dec else "")
    q = lambda s: f'"{s}"' if s else ""   # noqa: E731
    return q(pre.pop()) + body + q(suf.pop())


# ── attributes ─────────────────────────────────────────────────────────────────

def _read(attrs: dict[str, str], ref: str, flag) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]]]:
    """(meta, box, parts) of a <Chart ref> tag; the rest flagged (tiles._read's rules)."""
    d, nd = tiles.data(), node()
    parts_of = nd["parts"]
    dropped = set(d["dropped"]["parts"]) | set(d["dropped"]["box"]) - {"borderRadius"}   # a chart card may round
    box_ok = set(d["box_attributes"]) | {"borderRadius"} | set(nd["native_attributes"])
    meta, box, parts = {}, {}, {p: {} for p in parts_of}
    for k, v in attrs.items():
        if k in nd["meta"]:
            meta[k] = v
            continue
        if tiles._is_colour_attr(k) and not str(v).startswith("$"):
            flag("LITERAL_COLOR" if tiles._HEX.match(str(v)) else "NODE_ATTR_DROPPED", ref,
                 f'{k}="{v}" on <{TAG} ref="{ref}">: colours are $tokens; removed.')
            continue
        head, _, rest = k.partition(".")
        if head in parts_of and rest:
            allowed = d["part_nodes"][parts_of[head]]
            if rest in dropped:
                flag("NODE_ATTR_DROPPED", ref, f'{k} on <{TAG} ref="{ref}">: code owns the {rest}; removed.')
            elif rest not in allowed:
                flag("NODE_ATTR_UNKNOWN", ref, f'{k} on <{TAG} ref="{ref}">: {head} is a <{parts_of[head]}>; its '
                     f'attributes are {", ".join(allowed)}.')
            else:
                parts[head][rest] = v
        elif k in box_ok:
            box[k] = v
        elif k in ("chartColors", "chartType", "title", "showTitle") or k in dropped:
            flag("NODE_ATTR_DROPPED", ref, f'{k} on <{TAG} ref="{ref}">: code owns it; removed.')
        else:
            flag("NODE_ATTR_UNKNOWN", ref, f'{k} on <{TAG} ref="{ref}">: not a {TAG} node attribute (meta: '
                 f'{", ".join(nd["meta"])}; parts {" ".join(p + "." for p in parts_of)}; box attributes as a VStack).')
    return meta, box, parts


def composition(comp: dict, asked: str | None, ref: str, flag) -> tuple[str, dict[str, str]]:
    """(composition, extra meta from an alias). Unknown -> default, unmet -> fallback (spec.resolve_variant)."""
    cs, extra = node()["compositions"], {}
    asked = " ".join(asked.split()) if asked else None
    alias = node()["aliases"].get(asked) if asked else None
    if alias is not None:
        extra = {k: v for k, v in alias.items() if k != "variant"} if isinstance(alias, dict) else {}
        new = alias["variant"] if isinstance(alias, dict) else alias
        flag("NODE_ATTR_ALIAS", ref, f'variant="{asked}" on <{TAG} ref="{ref}"> is now variant="{new}"'
             + "".join(f' {k}="{v}"' for k, v in extra.items()) + ".")
        asked = new
    name, code, note = spec.resolve_variant("chart", TAG, comp, asked, vs=cs)
    if code:
        flag(code, ref, f'ref="{ref}": {note}.')
    return name or next(iter(cs)), extra


def _layers(comp_name: str, box: dict, parts: dict, focus: bool) -> tuple[dict, dict, dict]:
    """(box, parts of the rest, parts of the emphasis point): look -> the LLM's group attributes, and on the emphasis
    point look -> emphasis -> the group attributes the emphasis look does not set (no item tag yet)."""
    c = node()["compositions"][comp_name]
    rbox, rest, emph = {}, {p: {} for p in node()["parts"]}, {}
    for k, v in (c.get("look") or {}).items():
        head, _, sub = k.partition(".")
        if head in rest and sub:
            rest[head][sub] = str(v)
        else:
            rbox[k] = str(v)
    hi = {p: dict(a) for p, a in rest.items()}
    for k, v in (c.get("emphasis") or {}).items():
        head, _, sub = k.partition(".")
        hi[head][sub] = str(v)
    if not focus:   # one hue: every item's mark takes its emphasis colour, nothing else of the emphasis look
        mark = node()["one_hue"]
        rest[mark].update({sub: v for sub, v in hi[mark].items() if tiles._is_colour_attr(sub)})
        hi = rest
    rbox.update(box)
    for p, a in parts.items():
        rest[p].update(a)
        if focus:   # the emphasis point keeps its emphasis keys: the LLM restyles it but cannot remove it
            hi[p].update({k: v for k, v in a.items() if f"{p}.{k}" not in (c.get("emphasis") or {})})
    return rbox, rest, hi


def _a(attrs: dict[str, str]) -> str:
    return "".join(f' {k}="{native.x(v)}"' for k, v in attrs.items())


def _text(s: str, px: int, part: dict[str, str], **kw: str) -> str:
    return f'<Text fontSize="{px}"{_a({**kw, **part})}>{native.x(s)}</Text>'


# ── compositions ──────────────────────────────────────────────────────────────

def _title(comp: dict, part: dict) -> str:
    t = str(_cd(comp).get("chart_title") or "").strip()
    return _text(t, TITLE_PX, part, bold="true") if t else ""


def draw_native(comp: dict, name: str, box: dict, rest: dict, hi: dict, focus: int | None, meta: dict,
                theme: dict) -> str:
    series, kind = _series(comp), kind_of(comp)
    n_pts = max((len(s.get("values") or []) for s in series), default=0)
    if len(series) > 1 or kind in ("pie", "doughnut"):
        n = len(series) if len(series) > 1 else n_pts
        colors = [f"$chart{i % MAX_CHART_COLORS + 1}" for i in range(n)]
    else:
        colors = [hi["bar"].get("fill.color", "$accent") if i == focus else rest["bar"].get("fill.color", "$neutral")
                  for i in range(n_pts)] if focus is not None else [rest["bar"].get("fill.color", "$accent")] * n_pts
    own = {k: box.pop(k) for k in list(box) if k in node()["native_attributes"]}
    # a card the LLM sized (h / minH) holds the chart: the chart's own minimum on top of the card's padding and title
    # made the card taller than asked, and fit-grow starved a dense slide's text to 0 px (replay 2026-10-28, 3 slides)
    chart = native.chart(dict(comp, content_data={k: v for k, v in _cd(comp).items() if k != "chart_title"}),
                         {"w": "max", "chartColors": json.dumps(colors), **own}, theme)
    if {"h", "minH"} & set(box):
        chart = chart.replace(' minH="160"', "", 1)
    post: dict[str, Any] = {}
    if name == "native labelled":
        post.update(labels=True, fmt=number_format(series[0].get("values") or []),
                    ink=rest["label"].get("color", "$chartInk"), bold=rest["label"].get("bold", "true"))
    if meta.get("direction") == "horizontal" and kind in ("bar", "column"):
        post["barDir"] = "bar"
    mark = f"<!-- chart-post {json.dumps(post, ensure_ascii=False)} -->" if post else ""
    box.setdefault("gap", "8")
    return f'<VStack{_a(box)} alignItems="stretch">{_title(comp, rest["title"])}{mark}{chart}</VStack>'


def draw_rows(comp: dict, box: dict, rest: dict, hi: dict, focus: int | None) -> str:
    cid = comp["component_id"]
    labels = [str(v) for v in _cd(comp).get("chart_labels") or []]
    vals = list(_series(comp)[0].get("values") or [])
    top = max((abs(native.number(v)) for v in vals), default=0) or 1
    out = []
    for i, v in enumerate(vals):
        p = hi if i == focus else rest
        pct = max(2, round(100 * abs(native.number(v)) / top))
        bar = {"shapeType": "rect", "w": f"{pct}%", "h": str(BAR_PX), **p["bar"]}
        lb = labels[i] if i < len(labels) else str(i + 1)
        out.append(f'<HStack id="card-{cid}-{i}" grow="1" gap="20" alignItems="center">'
                   f'<VStack w="24%">{_text(lb, LABEL_PX, p["label"])}</VStack>'
                   f'<HStack w="1" grow="1" alignItems="center"><Shape{_a(bar)} /></HStack>'
                   f'<VStack w="16%">{_text(str(v), VALUE_PX, p["value"], id=f"kpiv-{cid}-{i}", bold="true", textAlign="right")}'
                   f'</VStack></HStack>')
    box.setdefault("gap", "10")
    return f'<VStack{_a(box)}>{_title(comp, rest["title"])}<VStack gap="12" grow="1">{"".join(out)}</VStack></VStack>'


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


def draw(comp: dict, attrs: dict[str, str], headline: str, flag, theme: dict | None = None) -> tuple[str, dict]:
    """One <Chart ref> tag -> its XML, and what was drawn."""
    ref = comp["component_id"]
    meta, box, parts = _read(attrs, ref, flag)
    name, extra = composition(comp, meta.get("variant"), ref, flag)
    meta = {**extra, **meta}
    focus = focus_index(comp, headline)
    if name != "native" and len(_series(comp)) > 1:
        focus = None
    box, rest, hi = _layers(name, box, parts, focus is not None)
    if not ({"h", "grow", "minH"} & set(box)):
        box["grow"] = "1"
    xml = draw_rows(comp, box, rest, hi, focus) if name == "rows" else \
        draw_native(comp, name, box, rest, hi, focus, meta, theme or {})
    return inner_ids(xml), {"composition": name, "focus": focus}


def expand(xml: str, plan: dict | None, theme: dict | None = None) -> dict[str, Any]:
    """Every <Chart ref="<chart component id>"/> in the slide drawn from the plan. A <Chart> without ref is the
    LLM's own (checked as today); a ref that names no chart component is NODE_REF_UNKNOWN."""
    comps = chart_components(plan)
    issues: list[dict[str, Any]] = []
    done: dict[str, dict] = {}

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY.get(code, WARNING), "ref": ref, "message": message})

    headline = str((plan or {}).get("slide_title") or "")
    out, pos = [], 0
    for t in validate.ref_tags(xml):
        if t["tag"] != TAG:
            continue
        ref = t["attrs"]["ref"]
        out.append(xml[pos:t["start"]])
        pos = t["end"]
        comp = comps.get(ref)
        if comp is None:
            flag("NODE_REF_UNKNOWN", ref, f'<{TAG} ref="{ref}">: no chart component "{ref}" on this slide '
                 f'(charts: {", ".join(comps) or "none"}).')
            continue
        if ref in done:
            flag("NODE_REF_DUPLICATE", ref, f'<{TAG} ref="{ref}"> twice: each chart once.')
            continue
        labels, series = _cd(comp).get("chart_labels") or [], _series(comp)
        if not labels or any(len(s.get("values") or []) != len(labels) for s in series):
            flag("NODE_ITEM_MISSING", ref, f'chart "{ref}": {len(labels)} labels but values of length '
                 f'{[len(s.get("values") or []) for s in series]}; the plan must give one value per label.')
            continue
        if t["body"].strip():
            flag("NODE_ATTR_DROPPED", ref, f'children inside <{TAG} ref="{ref}">: code writes the chart from the plan; '
                 "removed.")
        drawn, done[ref] = draw(comp, t["attrs"], headline, flag, theme)
        out.append(drawn)
    out.append(xml[pos:])
    return {"xml": "".join(out), "issues": issues, "ok": not any(i["severity"] == ERROR for i in issues),
            "components": done}


# ── prompt ─────────────────────────────────────────────────────────────────────

def node_lines() -> str:
    """The fixed lines (same on every slide: the cached part of the system prompt)."""
    cs = spec.blocks()["chart"]["variants"]
    parts = " ".join(f"{p}. = <{n}>" for p, n in node()["parts"].items())
    return "\n".join([
        "## CHARTS (code draws them from the plan)",
        f'<{TAG} ref="<chart id>" variant="..."/> draws the chart: labels, values, chart type, colours and the focus '
        "bar are code's. Self-closing: no ChartSeries / ChartDataPoint, chartType or chartColors.",
        "variant: " + "; ".join(f"{n} ({v['prompt']})" for n, v in cs.items()) + ". direction=\"horizontal\" turns "
        "native bars.",
        f"Layout (w, h, grow) and box attributes style the chart's own card; parts {parts} take that node's "
        'attributes in $tokens (bar.fill.color="$accentSoft" value.color="$accentText"). No fontSize.',
    ])


def tag_attributes() -> list[str]:
    """What a <Chart ref> takes, for the generator's ALLOWED ATTRIBUTES (dotted names by prefix, as tiles)."""
    nd = node()
    box = [a.split(".")[0] + ".*" if "." in a else a for a in tiles.data()["box_attributes"]]
    return list(dict.fromkeys(nd["meta"] + [f"{p}.*" for p in nd["parts"]] + nd["native_attributes"]
                              + ["borderRadius"] + box))


def prompt_line(comp: dict, headline: str = "") -> str:
    """The per-component line: the shape in lengths, the focus point, the compositions it can use; no values."""
    cid, cd = comp["component_id"], _cd(comp)
    labels = [str(v) for v in cd.get("chart_labels") or []]
    series = _series(comp)
    f = focus_index(comp, headline)
    names = [str(s.get("name") or "") for s in series] if len(series) > 1 else labels
    ok = [n for n, v in node()["compositions"].items() if not spec.failed_requires(v, comp)]
    parts = [f"CHART {cid}: {kind_of(comp)}, {len(labels)} points" + (f", {len(series)} series" if len(series) > 1 else ""),
             f"longest label {max((len(x) for x in labels), default=0)} chars",
             f"focus {names[f]}" if f is not None else "no focus point (one hue)",
             "variants " + " | ".join(ok)]
    return "; ".join(parts) + f'. <{TAG} ref="{cid}"/>; never type a label or value yourself: code writes them from the plan'
