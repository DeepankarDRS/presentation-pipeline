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
from src.compiler.nodes import compose, native, spec, tiles

SEVERITY = compose.SEVERITY
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


# ── compositions ──────────────────────────────────────────────────────────────

def _title(comp: dict, part: dict) -> str:
    t = str(_cd(comp).get("chart_title") or "").strip()
    return compose.text(t, TITLE_PX, part, bold="true") if t else ""


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
    return f'<VStack{compose.a(box)} alignItems="stretch">{_title(comp, rest["title"])}{mark}{chart}</VStack>'


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
                   f'<VStack w="24%">{compose.text(lb, LABEL_PX, p["label"])}</VStack>'
                   f'<HStack w="1" grow="1" alignItems="center"><Shape{compose.a(bar)} /></HStack>'
                   f'<VStack w="16%">{compose.text(str(v), VALUE_PX, p["value"], id=f"kpiv-{cid}-{i}", bold="true", textAlign="right")}'
                   f'</VStack></HStack>')
    box.setdefault("gap", "10")
    return f'<VStack{compose.a(box)}>{_title(comp, rest["title"])}<VStack gap="12" grow="1">{"".join(out)}</VStack></VStack>'


def draw(comp: dict, attrs: dict[str, str], headline: str, flag, theme: dict | None = None) -> tuple[str, dict]:
    """One <Chart ref> tag -> its XML, and what was drawn."""
    ref = comp["component_id"]
    meta, box, parts = compose.read(attrs, ref, flag, node())
    name, extra = compose.composition(node(), comp, meta.get("variant"), ref, flag)
    compose.undrawn(node(), name, box, parts, ref, flag)
    compose.no_item_tones(box, parts, ref, flag, TAG)
    meta = {**extra, **meta}
    focus = focus_index(comp, headline)
    if name != "native" and len(_series(comp)) > 1:
        focus = None
    box, rest, hi = compose.layers(node(), name, box, parts, focus is not None)
    if not ({"h", "grow"} & set(box)):   # minH is a floor, not a size (replay 2026-10-28: a minH-only card stayed short)
        box["grow"] = "1"
    xml = draw_rows(comp, box, rest, hi, focus) if name == "rows" else \
        draw_native(comp, name, box, rest, hi, focus, meta, theme or {})
    return xml, {"composition": name, "focus": focus}


def expand(xml: str, plan: dict | None, theme: dict | None = None) -> dict[str, Any]:
    """Every <Chart ref="<chart component id>"/> in the slide drawn from the plan (compose.expand)."""
    headline = str((plan or {}).get("slide_title") or "")

    def check(comp: dict, flag) -> bool:
        labels, series = _cd(comp).get("chart_labels") or [], _series(comp)
        if labels and all(len(s.get("values") or []) == len(labels) for s in series):
            return True
        flag("NODE_ITEM_MISSING", comp["component_id"], f'chart "{comp["component_id"]}": {len(labels)} labels but values of '
             f'length {[len(s.get("values") or []) for s in series]}; the plan must give one value per label.')
        return False

    return compose.expand(xml, chart_components(plan), TAG, lambda c, at, fl: draw(c, at, headline, fl, theme), check)


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
