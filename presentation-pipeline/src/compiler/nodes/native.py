"""Native fillers (§3.1): a native ref tag -> the POM node with its children written from the plan.

POM's own look, as the off arm draws it; every visible string is copied from the plan's
content_data. In 1a variants are validated and counted, not drawn (§3.3), so each kind has
one look here. `attrs` are the tag's kept attributes (validate.check_skeleton): the layout
attributes plus the node's own presentation attributes; code adds defaults the LLM did not set.
"""

from __future__ import annotations

import json
import re
from typing import Any
from xml.sax.saxutils import escape

LAYOUT = ("w", "h", "grow", "alignSelf", "minW", "maxW", "minH", "maxH")
_NUM = re.compile(r"-?\d+(?:[.,]\d+)*(?:\.\d+)?")
_POS = {"low": 0.2, "mid": 0.5, "medium": 0.5, "high": 0.8}


def x(v: Any) -> str:
    return escape(str(v), {'"': "&quot;"})


def _open(tag: str, attrs: dict[str, str], defaults: dict[str, str]) -> str:
    a = {k: v for k, v in attrs.items() if k not in ("ref", "variant")}
    for k, v in defaults.items():
        a.setdefault(k, v)
    return f"<{tag}" + "".join(f' {k}="{x(v)}"' for k, v in a.items())


def number(v: Any) -> float:
    """A chart value from the plan: 2.6, "0.29x", "₹1,234", "-1.4 pts" -> float (0 when none)."""
    if isinstance(v, (int, float)):
        return float(v)
    m = _NUM.search(str(v))
    return float(m.group(0).replace(",", "")) if m else 0.0


def _fmt(f: float) -> str:
    return str(int(f)) if f == int(f) else repr(f)


def _direction(comp: dict, cd: dict, default: str = "horizontal") -> str:
    d = str(cd.get("direction") or comp.get("orientation") or default)
    return d if d in ("horizontal", "vertical") else default


def text(comp: dict, attrs: dict, theme: dict) -> str:
    body = str((comp.get("content_data") or {}).get("text") or "").strip()
    caption = comp.get("kind") == "caption"
    d = {"fontSize": "14", "color": "$textMuted"} if caption else {"fontSize": "16", "color": "$textMain", "lineHeight": "1.4"}
    return _open("Text", attrs, d) + f">{x(body)}</Text>"


def ul(comp: dict, attrs: dict, theme: dict) -> str:
    items = [str(b).strip() for b in (comp.get("content_data") or {}).get("bullets") or [] if str(b).strip()]
    lis = "".join(f"<Li>{x(b)}</Li>" for b in items)
    return _open("Ul", attrs, {"fontSize": "16", "color": "$textMain", "lineHeight": "1.4"}) + f">{lis}</Ul>"


def _numeric(cell: str) -> bool:
    return bool(re.fullmatch(r"[\s+\-–−₹$€£(]*\d[\d.,]*\s*[%x×a-zA-Z.)]*\s*", cell)) and len(cell) <= 14


def table(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    cols = [str(c) for c in cd.get("table_columns") or []]
    rows = [[str(c) for c in r] for r in cd.get("table_rows") or []]
    n = max([len(cols)] + [len(r) for r in rows])
    right = [i > 0 and bool(rows) and all(_numeric(r[i]) for r in rows if i < len(r) and r[i].strip())
             for i in range(n)]

    def td(v: str, i: int, head: bool) -> str:
        a = ' bold="true" backgroundColor="$surfaceAlt"' if head else (' bold="true"' if i == 0 else "")
        al = ' textAlign="right"' if right[i] else ""
        return f'<Td fontSize="14" color="$textMain"{a}{al}>{x(v)}</Td>'

    out = [_open("Table", attrs, {"cellBorder.color": "$border", "cellBorder.width": "1"}) + ">"]
    out += ["<Col />"] * n
    if cols:
        out.append("<Tr>" + "".join(td(cols[i] if i < len(cols) else "", i, True) for i in range(n)) + "</Tr>")
    for r in rows:
        out.append("<Tr>" + "".join(td(r[i] if i < len(r) else "", i, False) for i in range(n)) + "</Tr>")
    return "".join(out) + "</Table>"


_CHART_TYPES = {"bar", "line", "pie", "area", "doughnut", "radar"}


def chart(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    kind = str(cd.get("chart_type") or comp.get("chart_type") or "bar").lower()
    kind = kind if kind in _CHART_TYPES else "bar"
    labels = [str(v) for v in cd.get("chart_labels") or []]
    series = cd.get("chart_series") or [{"name": cd.get("chart_title") or "Series 1", "values": cd.get("chart_values") or []}]
    colors = theme.get("chart_colors") or ["2563EB"]
    a = {k: v for k, v in attrs.items() if k not in ("ref", "variant")}
    layout = {k: a.pop(k) for k in list(a) if k in LAYOUT}
    d = {"chartType": kind, "showLegend": "true" if len(series) > 1 or kind in ("pie", "doughnut") else "false",
         "chartColors": json.dumps(colors), "h": "max", "minH": "160"}
    for k, v in d.items():
        a.setdefault(k, v)
    body = ""
    for s in series:
        pts = "".join(f'<ChartDataPoint label="{x(labels[i] if i < len(labels) else i + 1)}" value="{_fmt(number(v))}" />'
                      for i, v in enumerate(s.get("values") or []))
        body += f'<ChartSeries name="{x(s.get("name") or "")}">{pts}</ChartSeries>'
    node = "<Chart" + "".join(f' {k}="{x(v)}"' for k, v in a.items()) + f">{body}</Chart>"
    title = str(cd.get("chart_title") or "").strip()
    if not title:
        return node.replace("<Chart", "<Chart" + "".join(f' {k}="{x(v)}"' for k, v in layout.items()), 1)
    box = "".join(f' {k}="{x(v)}"' for k, v in layout.items())
    return (f'<VStack{box} gap="8" alignItems="stretch">'
            f'<Text fontSize="14" bold="true" color="$textMuted">{x(title)}</Text>{node}</VStack>')


def timeline(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    its = "".join(f'<TimelineItem date="{x(i.get("date") or "")}" title="{x(i.get("label") or i.get("title") or "")}" color="$accent" />'
                  for i in cd.get("timeline_items") or [])
    d = {"direction": _direction(comp, cd), "dateColor": "$textMuted", "titleColor": "$textMain", "connectorColor": "$accent"}
    return _open("Timeline", attrs, d) + f">{its}</Timeline>"


def process_arrow(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    steps = "".join(f'<ProcessArrowStep label="{x(s)}" color="$accent" textColor="FFFFFF" />'
                    for s in cd.get("process_steps") or [])
    return _open("ProcessArrow", attrs, {"direction": _direction(comp, cd), "fontSize": "16", "bold": "true"}) + f">{steps}</ProcessArrow>"


def flow(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    steps = [str(s) for s in cd.get("flow_steps") or []]
    last = len(steps) - 1
    nodes = "".join(
        f'<FlowNode id="n{i + 1}" shape="{"flowChartTerminator" if i in (0, last) else "flowChartProcess"}" '
        f'text="{x(s)}" color="$accent" textColor="FFFFFF" />' for i, s in enumerate(steps))
    links = "".join(f'<FlowConnection from="n{i}" to="n{i + 1}" />' for i in range(1, len(steps)))
    return _open("Flow", attrs, {"direction": _direction(comp, cd)}) + f">{nodes}{links}</Flow>"


def pyramid(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    d = str(cd.get("direction") or "up")
    lv = "".join(f'<PyramidLevel label="{x(v)}" color="$accent" textColor="FFFFFF" />' for v in cd.get("pyramid_levels") or [])
    return _open("Pyramid", attrs, {"direction": d if d in ("up", "down") else "up", "fontSize": "15", "bold": "true"}) + f">{lv}</Pyramid>"


def tree(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}

    def item(n: dict, depth: int) -> str:
        kids = "".join(item(c, depth + 1) for c in n.get("children") or [])
        col = "$accent" if depth == 0 else "$accentAlt"
        return f'<TreeItem label="{x(n.get("label") or "")}" color="{col}">{kids}</TreeItem>' if kids else \
            f'<TreeItem label="{x(n.get("label") or "")}" color="{col}" />'

    roots = cd.get("tree_nodes") or []
    if len(roots) > 1:   # POM's Tree takes one root: several roots hang under an empty one (none dropped)
        roots = [{"label": "", "children": roots}]
    layout = str(cd.get("layout") or comp.get("orientation") or "vertical")
    d = {"layout": layout if layout in ("vertical", "horizontal") else "vertical", "nodeShape": "roundRect", "textColor": "FFFFFF"}
    return _open("Tree", attrs, d) + ">" + "".join(item(r, 0) for r in roots) + "</Tree>"


def _pos(v: Any) -> float:
    if isinstance(v, (int, float)):
        return max(0.05, min(0.95, float(v)))
    s = str(v).strip().lower()
    if s in _POS:
        return _POS[s]
    try:
        return max(0.05, min(0.95, float(s)))
    except ValueError:
        return 0.5


def matrix(comp: dict, attrs: dict, theme: dict) -> str:
    cd = comp.get("content_data") or {}
    q = cd.get("quadrants") or {}
    quad = {"topLeft": q.get("top_left"), "topRight": q.get("top_right"),
            "bottomLeft": q.get("bottom_left"), "bottomRight": q.get("bottom_right")}
    qa = "".join(f' {k}="{x(v)}"' for k, v in quad.items() if v)
    # items in the same cell would be drawn on one point: spread them along the cell (positions are code's)
    seen: dict[tuple[float, float], int] = {}
    its = ""
    for i in cd.get("matrix_items") or []:
        px, py = _pos(i.get("x")), _pos(i.get("y"))
        k = seen.get((px, py), 0)
        seen[(px, py)] = k + 1
        px, py = max(0.05, min(0.95, px + (0.12 if k % 2 else 0) * (1 if px < 0.5 else -1))), max(0.05, py - 0.1 * (k // 2 + k % 2))
        its += f'<MatrixItem label="{x(i.get("label") or "")}" x="{round(px, 2)}" y="{round(py, 2)}" color="$accent" />'
    d = {"axisLabelColor": "$textMuted", "quadrantLabelColor": "$textMuted", "itemLabelColor": "$textMain"}
    return (_open("Matrix", attrs, d) + f'><MatrixAxes x="{x(cd.get("x_axis") or "")}" y="{x(cd.get("y_axis") or "")}" />'
            f"<MatrixQuadrants{qa} />{its}</Matrix>")


FILLERS = {"Text": text, "Ul": ul, "Table": table, "Chart": chart, "Timeline": timeline,
           "ProcessArrow": process_arrow, "Flow": flow, "Pyramid": pyramid, "Tree": tree, "Matrix": matrix}


def fill(tag: str, comp: dict, attrs: dict[str, str], theme: dict | None = None) -> str:
    """The native node for a ref tag, children written from the plan."""
    return FILLERS[tag](comp, attrs, theme or {})
