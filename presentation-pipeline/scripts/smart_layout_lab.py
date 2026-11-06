"""Smart-layout research, Part 3 (docs/smart-layout-research-2026-11-06.md): free tests of how to arrange one slide.
No LLM, no pipeline change. Every arm keeps the slide's header, its components and their style attributes as the LLM wrote
them in a saved run, and changes ONLY the arrangement, so the comparison is about layout alone.

    python -m scripts.smart_layout_lab run --np <dir> --b6 <dir> --deck <dir> --corpus <dir> ... --k 6
    python -m scripts.smart_layout_lab render      # renders each slide's arms (one at a time) and builds the blind sheets
    python -m scripts.smart_layout_lab stress --corpus <dir> ...   # any composition: bare tags on every kind set seen

Arms (each a layout tree of the same leaves):
  today    the LLM's own arrangement
  static   the selected blueprint skeleton (14 named layouts), followed strictly
  solver   code only: every order-keeping slicing tree, sized from measured content and weights; estimator's best
  best_k   the estimator's top K different shapes, each compiled; the code score on the compiled result picks one
  library  up to 3 arrangements retrieved from other decks' saved slides with the same kinds; the same code score picks
  guarded  today, unless best_k beats it by MARGIN on the same code score
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.kpi_replay import compile_slide  # noqa: E402
from src.agents.blueprint_selector import select_blueprint  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.geometry_audit import audit_run_folder  # noqa: E402
from src.compiler.nodes import composed, element_refs, spec, tiles  # noqa: E402
from src.compiler.normalizer import _BARE_AMP_RE  # noqa: E402

OUT = ROOT / "output" / "smart-layout"
MARGIN = 6.0
STACKS = ("VStack", "HStack")
VISUAL = {"Chart": "chart", "Table": "table", "Ul": "bullet_list", "Ol": "bullet_list", "Timeline": "timeline",
          "ProcessArrow": "process_arrow", "Flow": "flow", "Pyramid": "pyramid", "Tree": "tree", "Matrix": "matrix",
          "Layer": "layer", "KpiRow": "kpi_row", "KpiGrid": "kpi_row", "CardGrid": "card_grid"}
LAYOUT_ATTRS = ("w", "h", "grow", "minW", "maxW", "minH", "maxH", "alignSelf", "cols")
WEIGHT = {"hero": 3.0, "peer": 2.0, "supporting": 1.0, "minor": 0.5}
DECOR = ("Shape", "Icon", "Line", "Arrow", "Svg")
DIAGRAMS = ("timeline", "process_arrow", "flow")


# ── the layout tree ───────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class Leaf:
    el: Any
    kind: str
    comp: dict = field(default_factory=dict)

    @property
    def weight(self) -> float:
        if self.comp.get("weight") in WEIGHT:
            return WEIGHT[self.comp["weight"]]
        return 1.0 if self.kind == "narrative" else 2.0


@dataclass
class Split:
    orient: str          # "V" or "H"
    kids: list
    shares: list = field(default_factory=list)   # H only: percent per kid


def leaves_of(t) -> list[Leaf]:
    return [t] if isinstance(t, Leaf) else [x for k in t.kids for x in leaves_of(k)]


def shape(t) -> str:
    if isinstance(t, Leaf):
        return t.kind
    return t.orient + "(" + ",".join(shape(k) for k in t.kids) + ")"


def fine_shape(t) -> str:
    if isinstance(t, Leaf):
        return t.kind
    if t.orient == "H":
        return "H(" + ",".join(f"{shape(k)}:{s}" for k, s in zip(t.kids, t.shares)) + ")"
    return "V(" + ",".join(fine_shape(k) for k in t.kids) + ")"


def _parse(xml: str):
    return etree.fromstring(_BARE_AMP_RE.sub("&amp;", xml).encode("utf-8"))


def _refs(e) -> list[str]:
    return [x.get("ref") for x in e.iter() if isinstance(x.tag, str) and x.get("ref") and "." not in x.get("ref")]


def _text(e) -> str:
    return "".join(e.itertext())


def _is_texty(e) -> bool:
    return all(c.tag in ("Text", "Span", "B", "I", "Mark", "VStack", "HStack", "Shape", "Icon")
               for c in e.iter() if c is not e and isinstance(c.tag, str))


def _like_row(e) -> bool:
    """A row of like children: hand-drawn tiles or cards, one component."""
    kids = [c for c in e if isinstance(c.tag, str) and c.tag not in DECOR]
    if len(kids) < 2:
        return False
    sig = {tuple(sorted(Counter(x.tag for x in c.iter() if isinstance(x.tag, str) and x.tag not in ("Span", "B", "I")).items())) for c in kids}
    return len(sig) == 1


def _classify_box(e) -> str:
    for x in e.iter():
        if isinstance(x.tag, str) and x.tag in VISUAL:
            return VISUAL[x.tag]
    txt = _text(e)
    if _like_row(e) or (e.tag in STACKS and any(_like_row(c) for c in e if c.tag in STACKS)):
        nums = len(re.findall(r"\d", txt))
        return "kpi_row" if nums >= 3 and len(txt) / max(1, len(list(e))) < 60 else "card_grid"
    return "narrative"


def split_header(root) -> tuple[list, list]:
    kids = [c for c in root if isinstance(c.tag, str) and c.tag not in DECOR]
    head = []
    for c in kids:
        if c.get("ref") or _refs(c):
            break
        if len(head) < 3 and c.tag == "Text" and len(_text(c)) < 240 and not c.get("grow"):
            head.append(c)
            continue
        if not head and c.tag in STACKS and _is_texty(c) and len(_text(c)) < 320 and not c.get("grow") and not c.get("backgroundColor"):
            head.append(c)
        break
    return head, [c for c in kids if c not in head]


def to_tree(e, comps: dict[str, dict]):
    """The arrangement of one element: a Leaf for a component (with its own title and card) or a Split."""
    refs = _refs(e)
    if e.get("ref") and "." not in e.get("ref"):
        c = comps.get(e.get("ref"), {})
        return Leaf(e, c.get("kind") or VISUAL.get(e.tag, "narrative"), c)
    specials = [x for x in e.iter() if isinstance(x.tag, str) and x.tag in VISUAL and x is not e]
    if e.tag not in STACKS:
        return Leaf(e, VISUAL.get(e.tag, "narrative"))
    n_things = len(refs) if refs else len(specials)
    if n_things <= 1:
        others = [c for c in e if isinstance(c.tag, str) and c.tag in STACKS and not _refs(c) and not any(x.tag in VISUAL for x in c.iter() if isinstance(x.tag, str))]
        has_thing = n_things == 1
        if (has_thing and not others) or not has_thing and (_is_texty(e) or _like_row(e)) and (_like_row(e) or not any(_like_row(c) for c in e if c.tag in STACKS) or True):
            if has_thing and refs:
                c = comps.get(refs[0], {})
                return Leaf(e, c.get("kind") or "narrative", c)
            if not has_thing and e.tag == "HStack" and not _like_row(e) and len([c for c in e if c.tag in STACKS]) >= 2:
                pass   # unlike hand-drawn boxes side by side: a real split, below
            elif not has_thing and e.tag == "VStack" and len([c for c in e if c.tag in STACKS]) >= 2 and not _like_row(e):
                pass
            else:
                return Leaf(e, _classify_box(e))
    kids = []
    for c in e:
        if not isinstance(c.tag, str) or c.tag in DECOR:
            continue
        kids.append(to_tree(c, comps))
    if len(kids) == 1:
        return kids[0]
    orient = "H" if e.tag == "HStack" else "V"
    flat = []
    for k in kids:
        if isinstance(k, Split) and k.orient == orient:
            flat.extend(k.kids)
        else:
            flat.append(k)
    return Split(orient, flat, [])


def from_xml(xml: str, plan: dict) -> dict | None:
    """{root, head, tree}; None when the slide has no top VStack (a full-height split root) or no body."""
    slide = _parse(xml)
    root = slide[0] if slide.tag == "Slide" else slide
    if root.tag != "VStack":
        return None
    head, body = split_header(root)
    if not head or not body:
        return None
    comps = {c.get("component_id"): c for c in plan.get("components", [])}
    kids = [to_tree(c, comps) for c in body]
    tree = kids[0] if len(kids) == 1 else Split("V", [x for k in kids for x in (k.kids if isinstance(k, Split) and k.orient == "V" else [k])], [])
    return {"root": root, "head": head, "tree": tree}


# ── writing a tree back as XML ────────────────────────────────────────────────────────────────────────────────

def _growable(leaf: Leaf) -> bool:
    if leaf.kind == "table":
        return False
    if leaf.kind in ("narrative", "caption"):
        return len(_text(leaf.el)) > 140 or bool(leaf.el.get("backgroundColor"))
    return True


def _subtree_grows(t) -> float:
    if isinstance(t, Leaf):
        return t.weight if _growable(t) else 0.0
    vals = [_subtree_grows(k) for k in t.kids]
    return max(vals) if vals else 0.0


def _serial(e) -> str:
    s = etree.tostring(e, encoding="unicode", with_tail=False)
    return re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", s)


def _emit(t, parent: str, share: float | None, gap: str, box: tuple[float, float]) -> str:
    w, h = box
    if isinstance(t, Leaf):
        el = etree.fromstring(_serial(t.el).encode("utf-8"))
        for a in LAYOUT_ATTRS:
            el.attrib.pop(a, None)
        if parent == "H":
            el.set("w", f"{share:g}%")
        else:
            g = _subtree_grows(t)
            if g:
                el.set("grow", f"{g:g}")
        if el.tag == "Chart":
            el.set("h", "max")
            el.set("minH", "180")
        if el.tag in ("KpiRow", "CardGrid"):
            el.set("cols", str(_best_cols(t, w, h)))
        if el.tag in ("Timeline", "ProcessArrow", "Flow"):
            el.set("direction", "horizontal" if _across_fits(t, w) else "vertical")
        if el.tag == "VStack" and (t.kind == "chart" or t.kind in DIAGRAMS):
            pass
        return _serial(el)
    tag = "VStack" if t.orient == "V" else "HStack"
    attrs = [f'gap="{gap}"', 'alignItems="stretch"']
    if parent == "H":
        attrs.insert(0, f'w="{share:g}%"')
    else:
        g = _subtree_grows(t)
        if g:
            attrs.insert(0, f'grow="{g:g}"')
    alloc = allot(t, w, h)
    inner = "".join(_emit(k, t.orient, (t.shares[i] if t.orient == "H" else None), gap, alloc[i]) for i, k in enumerate(t.kids))
    return f"<{tag} {' '.join(attrs)}>{inner}</{tag}>"


def body_box(root) -> tuple[float, float]:
    pad = _num(root.get("padding"), 48)
    return 1280 - 2 * pad, 720 - 2 * pad - 96 - _num(root.get("gap"), 24)


def _num(s, d: float) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return d


def to_xml(parts: dict, tree) -> str:
    root = parts["root"]
    gap = root.get("gap") or "24"
    attrs = " ".join(f'{k}="{v}"' for k, v in root.attrib.items())
    head = "".join(_serial(h) for h in parts["head"])
    box = body_box(root)
    if isinstance(tree, Split) and tree.orient == "V":
        alloc = allot(tree, *box)
        body = "".join(_emit(k, "V", None, gap, alloc[i]) for i, k in enumerate(tree.kids))
    else:
        body = _emit(tree, "V", None, gap, box)
    return f"<Slide><VStack {attrs}>{head}{body}</VStack></Slide>"


# ── what a component needs from its box: the estimator (no compile) ──────────────────────────────────────────

def _c(leaf: Leaf) -> dict:
    return leaf.comp.get("content_data") or {}


def _kpi_need(leaf: Leaf, w: float, cols: int) -> float:
    cd = _c(leaf)
    vals = [str(v) for v in cd.get("kpi_values") or []] or ["00"]
    n = max(1, len(vals))
    tile = (w - (cols - 1) * 12) / cols
    size = min(56.0, (tile - 32) / (0.6 * max(len(v) for v in vals)))
    labels = cd.get("kpi_labels") or [""]
    lab_lines = max(1, int(max(len(str(x)) for x in labels) * 9 / max(40, tile - 32)) + 1)
    notes = 26 if any(str(d).strip() for d in cd.get("kpi_deltas") or []) else 0
    rows = -(-n // cols)
    return rows * (size * 1.25 + lab_lines * 24 + notes + 36) + (rows - 1) * 12


def _kpi_ok(leaf: Leaf, w: float, cols: int) -> bool:
    vals = [str(v) for v in _c(leaf).get("kpi_values") or []] or ["00"]
    tile = (w - (cols - 1) * 12) / cols
    return (tile - 32) / (0.6 * max(len(v) for v in vals)) >= 28 and tile >= 130


def _card_need(leaf: Leaf, w: float, cols: int) -> float:
    cards = _c(leaf).get("cards") or [{}]
    cw = max(60.0, (w - (cols - 1) * 14) / cols - 36)
    tallest = 0.0
    for card in cards:
        title = str(card.get("title") or "")
        body = str(card.get("body") or "") + " ".join(str(b) for b in card.get("bullets") or [])
        tallest = max(tallest, 36 + (int(len(title) * 12.5 / cw) + 1) * 30 + (int(len(body) * 9.2 / cw) + (1 if body else 0)) * 25)
    rows = -(-len(cards) // cols)
    return rows * tallest + (rows - 1) * 14


def _best_cols(leaf: Leaf, w: float, h: float) -> int:
    if leaf.kind == "kpi_row":
        n = max(1, len(_c(leaf).get("kpi_values") or [1]))
        opts = [c for c in range(1, n + 1) if _kpi_ok(leaf, w, c)] or [1]
        return min(opts, key=lambda c: (max(0.0, _kpi_need(leaf, w, c) - h), abs(((w / c) / max(1.0, h / (-(-n // c)))) - 1.8), -c))
    n = max(1, len(_c(leaf).get("cards") or [1]))
    opts = [c for c in range(1, n + 1) if (w - (c - 1) * 14) / c >= 190] or [1]
    return min(opts, key=lambda c: (max(0.0, _card_need(leaf, w, c) - h), abs(((w / c) / max(1.0, h / (-(-n // c)))) - 1.5), -c))


def _items(leaf: Leaf) -> list:
    try:
        return spec.items(leaf.comp) if leaf.comp else []
    except Exception:
        return []


def _across_fits(leaf: Leaf, w: float) -> bool:
    return w >= max(1, len(_items(leaf))) * 165


def need(t, w: float) -> float:
    """The height this subtree needs at width w, at the slide's normal type sizes."""
    if isinstance(t, Split):
        if t.orient == "V":
            return sum(need(k, w) for k in t.kids) + 18 * (len(t.kids) - 1)
        return max(need(k, w * s / 100 - 12) for k, s in zip(t.kids, t.shares))
    k = t.kind
    if k == "kpi_row":
        n = max(1, len(_c(t).get("kpi_values") or [1]))
        opts = [c for c in range(1, n + 1) if _kpi_ok(t, w, c)] or [1]
        return min(_kpi_need(t, w, c) for c in opts)
    if k == "card_grid":
        n = max(1, len(_c(t).get("cards") or [1]))
        opts = [c for c in range(1, n + 1) if (w - (c - 1) * 14) / c >= 190] or [1]
        return min(_card_need(t, w, c) for c in opts)
    if k == "table":
        cd = _c(t)
        rows = cd.get("table_rows") or []
        cols = cd.get("table_columns") or []
        ncol = max([len(cols)] + [len(r) for r in rows] + [1])
        cw = w / ncol
        total = 44.0
        for r in rows:
            longest = max((len(str(c)) for c in r), default=1)
            total += (int(longest * 9.5 / max(40, cw - 16)) + 1) * 27 + 12
        return total
    if k == "chart":
        return 230.0
    if k in DIAGRAMS:
        n = max(1, len(_items(t)))
        return 170.0 if _across_fits(t, w) else n * 74.0
    if k in ("pyramid", "tree", "matrix", "layer"):
        return 300.0
    words = sum(len(str(i)) for i in _items(t)) or len(_text(t.el))
    n_items = max(1, len(_items(t)))
    return (int(words * 9.4 / max(60, w - 32)) + n_items) * 26 + (24 if t.el.get("backgroundColor") else 0)


def allot(t: Split, w: float, h: float) -> list[tuple[float, float]]:
    if t.orient == "H":
        return [(w * s / 100 - 12, h) for s in t.shares]
    needs = [need(k, w) for k in t.kids]
    avail = h - 18 * (len(t.kids) - 1)
    spare = avail - sum(needs)
    grows = [_subtree_grows(k) for k in t.kids]
    tot = sum(grows)
    if spare >= 0 and tot:
        return [(w, n + spare * g / tot) for n, g in zip(needs, grows)]
    if spare < 0:
        return [(w, n * avail / max(1.0, sum(needs))) for n in needs]
    return [(w, n) for n in needs]


def estimate(t, w: float, h: float, total_w: float, total_h: float) -> float:
    """Higher is better. Penalties: content past its box, boxes too narrow, charts of a poor shape, the slide's
    weights not matching the area each component gets, boxes much larger than what they hold."""
    if isinstance(t, Split):
        alloc = allot(t, w, h)
        return sum(estimate(k, a[0], a[1], total_w, total_h) for k, a in zip(t.kids, alloc)) - (6.0 if len(t.kids) > 3 and t.orient == "H" else 0.0)
    nd = need(t, w)
    s = 0.0
    if nd > h:
        s -= 120 * (nd / max(1.0, h) - 1)
    min_w = {"chart": 340, "table": 360, "bullet_list": 280, "narrative": 240, "kpi_row": 150, "card_grid": 210}.get(t.kind, 280)
    if w < min_w:
        s -= 100 * (min_w / max(1.0, w) - 1)
    if t.kind == "chart":
        a = w / max(1.0, h)
        s -= 18 * max(0.0, 1.15 - a) + 8 * max(0.0, a - 2.8)
        n = max(1, len(_items(t)))
        if w < n * 90:      # category labels wrap and bars shrink below this
            s -= 40 * (n * 90 / max(1.0, w) - 1)
    if t.kind == "kpi_row":   # a box far wider than its numbers need is width taken from its neighbours
        vals = [str(v) for v in _c(t).get("kpi_values") or []] or ["00"]
        cols = _best_cols(t, w, h)
        tile = (w - (cols - 1) * 12) / cols
        s -= 30 * max(0.0, tile / (max(len(v) for v in vals) * 0.6 * 56 + 80) - 1.0)
    if t.kind == "table":
        n = len(_c(t).get("table_columns") or [])
        if w < n * 120:
            s -= 30
    if t.kind in DIAGRAMS and not _across_fits(t, w) and h < need(t, w):
        s -= 30
    if not _growable(t) or t.kind in ("narrative", "bullet_list", "table"):
        s -= 25 * max(0.0, 0.55 - nd / max(1.0, h))
    area = w * h / (total_w * total_h)
    s += 12 * t.weight * min(area, 0.75)
    return s


# ── every arrangement: order-keeping slicing trees ───────────────────────────────────────────────────────────

def _groupings(items: list, max_parts: int):
    n = len(items)
    for k in range(2, min(n, max_parts) + 1):
        for cuts in itertools.combinations(range(1, n), k - 1):
            bounds = (0,) + cuts + (n,)
            yield [items[bounds[i]:bounds[i + 1]] for i in range(k)]


def trees(items: list[Leaf], orient: str | None = None):
    if len(items) == 1:
        yield items[0]
        return
    for o in (("V", "H") if orient is None else (orient,)):
        for parts in _groupings(items, 4 if o == "V" else 3):
            other = "H" if o == "V" else "V"
            for kids in itertools.product(*[list(trees(p, other)) for p in parts]):
                yield Split(o, list(kids), [])


def _copy(t):
    return t if isinstance(t, Leaf) else Split(t.orient, [_copy(k) for k in t.kids], list(t.shares))


def _h_nodes(t) -> list[Split]:
    if isinstance(t, Leaf):
        return []
    return ([t] if t.orient == "H" else []) + [x for k in t.kids for x in _h_nodes(k)]


def _weight_of(t) -> float:
    return sum(l.weight for l in leaves_of(t))


def share_options(t: Split) -> list[list[int]]:
    n = len(t.kids)
    eq = [round(100 / n)] * n
    wts = [_weight_of(k) for k in t.kids]
    tot = sum(wts)
    by_w = [max(25, min(72, round(100 * x / tot))) for x in wts]
    by_w[-1] += 100 - sum(by_w)
    opts = [by_w, eq]
    if n == 2:
        opts += [[60, 40], [40, 60], [66, 34], [34, 66]]
    seen, out = set(), []
    for o in opts:
        if tuple(o) not in seen:
            seen.add(tuple(o))
            out.append(list(o))
    return out


def with_shares(t) -> list:
    """The tree with each H node's share options (capped)."""
    t = _copy(t)
    hs = _h_nodes(t)
    if not hs:
        return [t]
    out = []
    for combo in itertools.islice(itertools.product(*[share_options(h) for h in hs]), 36):
        for h, c in zip(hs, combo):
            h.shares = list(c)
        out.append(_copy(t))
    return out


def ranked(items: list[Leaf], box: tuple[float, float]) -> list[tuple[float, Any]]:
    """Per shape, its best shares by the estimator; shapes best first."""
    best: dict[str, tuple[float, Any]] = {}
    for t in itertools.islice(trees(items), 400):
        for v in with_shares(t):
            s = estimate(v, box[0], box[1], box[0], box[1]) if isinstance(v, Split) else 0.0
            k = shape(v)
            if k not in best or s > best[k][0]:
                best[k] = (s, v)
    return sorted(best.values(), key=lambda x: -x[0])


# ── drawing and the measured score ───────────────────────────────────────────────────────────────────────────

def draw(xml: str, plan: dict, theme: str, dest: Path) -> dict:
    """The validator's path for the LLM's tags, then the compile: expand -> fill -> deck font -> normalize -> compile-pom."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "tags.xml").write_text(xml, encoding="utf-8")
    d = composed.expand(xml, plan)
    issues = list(d["issues"])
    ok = d["ok"]
    x = d["xml"]
    if element_refs.refs_on():
        fill = tiles.fill if tiles.on() else element_refs.fill_refs
        r = fill(x, plan)
        x, issues, ok = r["xml"], issues + r["issues"], ok and r["ok"]
    if not ok:
        return {"status": "node_error", "issues": [i["code"] + ": " + i["message"][:90] for i in issues if i["severity"] == "error"]}
    comp = compile_slide(deck_font(x), theme, dest)
    return {"status": comp["res"].get("status"), "res": comp["res"], "issues": [i["code"] for i in issues]}


def _final(dest: Path) -> Path:
    """fit-grow writes fitted.xml only when it changed something; otherwise the compiled input is the slide."""
    return dest / "fitted.xml" if (dest / "fitted.xml").exists() else dest / "in.xml"


def _font_stats(dest: Path) -> dict:
    p = _final(dest)
    if not p.exists():
        return {"median": 0.0, "low": 0.0}
    root = _parse(re.sub(r"<Theme\b[^>]*/>", "", p.read_text(encoding="utf-8")))
    sizes: list[float] = []
    for e in root.iter():
        if not isinstance(e.tag, str):
            continue
        if e.tag in ("Text", "Li", "Td"):
            n = len(_text(e).strip())
            if n >= 3:
                sizes += [_num(e.get("fontSize"), 16)] * min(n, 200)
    if not sizes:
        return {"median": 0.0, "low": 0.0}
    sizes.sort()
    return {"median": statistics.median(sizes), "low": sizes[len(sizes) // 10]}


def _chart_boxes(geo: dict) -> list[tuple[float, float]]:
    out = []

    def walk(n):
        if n.get("type") == "chart":
            out.append((n.get("w", 0), n.get("h", 0)))
        for c in n.get("children") or []:
            walk(c)
    for s in geo.get("slides") or []:
        walk(s)
    return out


def ink(dest: Path) -> float:
    """Share of the slide's area that type and charts fill: the user's past marks follow this ("better space allocation",
    30 of 42 decided pairs, docs/eval/smart-layout/README.md), a fault count alone did not (21 of 41)."""
    a = 0.0
    root = _parse(re.sub(r"<Theme\b[^>]*/>", "", _final(dest).read_text(encoding="utf-8")))
    for e in root.iter():
        if isinstance(e.tag, str) and e.tag in ("Text", "Li", "Td"):
            fs = _num(e.get("fontSize"), 16)
            a += len(_text(e).strip()) * 0.5 * fs * fs * 1.3
    for w, h in _chart_boxes(json.loads((dest / "geometry.json").read_text(encoding="utf-8"))):
        a += w * h * 0.6
    return a / (1280 * 720)


HARD = ("GEOM_SPILL", "GEOM_COLLISION", "GEOM_OFF_SLIDE", "GEOM_TEXT_OVERFLOW")


def measured(dest: Path, slide_type: str = "", plan: dict | None = None) -> dict:
    """The code score of a compiled slide. Fixed by hand before any marks: hard faults, then empty space, then type size."""
    try:
        res = json.loads((dest / "compile-result.json").read_text(encoding="utf-8"))
    except Exception:
        return {"score": -999.0, "compiled": False}
    if res.get("status") != "success":
        return {"score": -999.0, "compiled": False}
    geo = audit_run_folder(dest, slide_type)
    codes = Counter(i["code"] for i in geo)
    warn = Counter(w.get("code") for w in res.get("warnings") or [])
    diag = Counter(d.get("type") or d.get("code") for d in res.get("diagnostics") or [])
    fonts = _font_stats(dest)
    charts = []
    try:
        charts = _chart_boxes(json.loads((dest / "geometry.json").read_text(encoding="utf-8")))
    except Exception:
        pass
    hard = sum(codes[c] for c in HARD)
    s = 100.0 - 20 * min(hard, 3) - 10 * min(warn["WORD_TOO_WIDE"], 3) - 12 * warn["SLIDE_DENSE"]
    s -= 6 * min(codes["GEOM_BOX_EMPTY"], 2) + 4 * min(codes["GEOM_CARD_EMPTY"], 3) + 8 * codes["GEOM_SLIDE_SPARSE"]
    s -= 10 * (diag["NODE_OVERLAP"] + diag["NODE_OUT_OF_BOUNDS"] > 0)
    fill = ink(dest)
    s += 150 * min(fill, 0.45)
    points = max([len(spec.items(c)) for c in (plan or {}).get("components", []) if c.get("kind") == "chart"] or [0])
    for w, h in charts:
        a = w / max(1.0, h)
        s -= 30 * max(0.0, points * 90 / max(1.0, w) - 1)
        s -= 12 if h < 170 or w < 300 else 0
        s -= 6 * max(0.0, 1.0 - a) + 3 * max(0.0, a - 3.5)
    return {"score": round(s, 1), "compiled": True, "hard": hard, "codes": dict(codes), "words": warn["WORD_TOO_WIDE"],
            "dense": warn["SLIDE_DENSE"], "ink": round(fill, 3), "font_median": fonts["median"], "font_low": fonts["low"], "charts": charts}


# ── the static arm: one of the 14 skeletons, followed strictly ───────────────────────────────────────────────

ROLE_KINDS = [("kpi", "kpi_row"), ("chart", "chart"), ("table", "table"), ("card|insight|action|pillar|numbered|detail", "card_grid"),
              ("bullet|list", "bullet_list"), ("callout|narrative|text|content", "narrative")]


def static_tree(plan: dict, items: list[Leaf]):
    bp = select_blueprint(plan)
    if not bp:
        return None, ""
    left = list(items)

    def take(role: str):
        for pat, kind in ROLE_KINDS:
            if re.search(pat, role):
                for l in left:
                    if l.kind == kind:
                        left.remove(l)
                        return l
        if re.search("main|primary|secondary|sidebar|panel", role) and left:
            return left.pop(0)
        return None
    bands = []
    for b in bp.get("structure", {}).get("bands", []):
        role = b.get("role", "")
        if re.search("header|title|eyebrow|subtitle|source|meta|divider", role):
            continue
        kids = b.get("children") or []
        if len(kids) >= 2:
            got = [x for x in (take(c.get("role", "")) for c in kids) if x]
            if len(got) >= 2:
                sp = [float(v) for v in re.findall(r"\d+", str(b.get("split") or ""))][:len(got)]
                shares = [round(v) for v in sp] if len(sp) == len(got) and abs(sum(sp) - 100) < 2 else [round(100 / len(got))] * len(got)
                bands.append(Split("H", got, shares))
            elif got:
                bands.append(got[0])
        else:
            x = take(role)
            if x:
                bands.append(x)
    extra = len(left)
    bands += left
    if len(bands) == 1:
        return bands[0], f"{bp['blueprint_name']}+{extra}"
    return Split("V", bands, []), f"{bp['blueprint_name']}+{extra}"


# ── the library arm: arrangements from other decks ───────────────────────────────────────────────────────────

def deck_of(path: str) -> str:
    m = re.search(r"(gate-deck-[a-z0-9-]*?|deck-[a-z0-9-]*?|gj-h1[a-z0-9-]*?)(?:-s\d|__r\d|-r\d|-\d{6,}|/)", path.replace("\\", "/") + "/")
    return m.group(1) if m else path


def load_library(srcs: list[Path]) -> dict[tuple, list[dict]]:
    lib: dict[tuple, list[dict]] = defaultdict(list)
    seen = set()
    for src in srcs:
        for sj in src.rglob("slides.json"):
            try:
                data = json.loads(sj.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for s in data:
                if not isinstance(s, dict) or not s.get("xml") or not isinstance(s.get("slide_plan"), dict):
                    continue
                key = hash(s["xml"])
                if key in seen:
                    continue
                seen.add(key)
                try:
                    parts = from_xml(s["xml"], s["slide_plan"])
                except Exception:
                    continue
                if not parts:
                    continue
                tree = parts["tree"]
                ls = leaves_of(tree)
                if len(ls) < 2:
                    continue
                k = tuple(sorted(l.kind for l in ls))
                lib[k].append({"deck": deck_of(str(sj)), "abs": abstract(tree), "shape": shape(tree)})
    return lib


def abstract(t):
    if isinstance(t, Leaf):
        return t.kind
    shares = list(t.shares)
    if t.orient == "H":
        vals = [_num((k.el.get("w") or "").rstrip("%"), 0) if isinstance(k, Leaf) and "%" in (k.el.get("w") or "") else 0 for k in t.kids]
        shares = [round(v) for v in vals] if all(vals) and abs(sum(vals) - 100) < 6 else [round(100 / len(t.kids))] * len(t.kids)
    return {"o": t.orient, "kids": [abstract(k) for k in t.kids], "shares": shares}


def instantiate(a, pool: dict[str, list[Leaf]]):
    if isinstance(a, str):
        return pool[a].pop(0)
    return Split(a["o"], [instantiate(k, pool) for k in a["kids"]], list(a["shares"]))


def library_trees(items: list[Leaf], lib: dict, deck: str, n: int = 3) -> tuple[list, int]:
    key = tuple(sorted(l.kind for l in items))
    donors = [d for d in lib.get(key, []) if d["deck"] != deck]
    by_shape = Counter(d["shape"] for d in donors)
    out = []
    for sh, _ in by_shape.most_common(n):
        d = next(x for x in donors if x["shape"] == sh)
        pool = defaultdict(list)
        for l in items:
            pool[l.kind].append(l)
        out.append(instantiate(d["abs"], pool))
    return out, len(donors)


# ── one slide ────────────────────────────────────────────────────────────────────────────────────────────────

def run_slide(case: dict, lib: dict, k: int, out: Path) -> dict:
    plan, xml, theme = case["plan"], case["xml"], case["theme"]
    row: dict[str, Any] = {"name": case["name"], "deck": case["deck"], "kinds": [c.get("kind") for c in plan.get("components", [])]}
    try:
        parts = from_xml(xml, plan)
    except Exception as e:
        return {**row, "skipped": f"parse: {e}"[:100]}
    if not parts:
        return {**row, "skipped": "split root or no header"}
    items = leaves_of(parts["tree"])
    row["today_shape"] = shape(parts["tree"])
    row["leaves"] = [l.kind for l in items]
    if len(items) < 2:
        return {**row, "skipped": "one component"}
    box = body_box(parts["root"])
    base = out / case["name"]
    st = resolve_theme(theme)["element"]
    t0 = time_now()

    def try_arm(name: str, x: str) -> dict:
        d = draw(x, plan, st, base / name)
        m = measured(base / name, plan.get("slide_type", ""), plan) if d.get("status") == "success" else {"score": -999.0, "compiled": False, "why": d.get("issues")}
        return {"arm": name, **m}
    arms = {"today": try_arm("today", xml)}
    row["today_issues"] = arms["today"].get("why")
    # static
    s, tag = static_tree(plan, list(items))
    if s is not None:
        arms["static"] = {**try_arm("static", to_xml(parts, s)), "skeleton": tag, "shape": shape(s)}
    # solver + best_k
    rk = ranked(items, box)
    row["shapes_considered"] = len(rk)
    cands = []
    for i, (est, t) in enumerate(rk[:k]):
        m = try_arm(f"k{i}", to_xml(parts, t))
        cands.append({**m, "est": round(est, 1), "shape": fine_shape(t)})
    row["candidates"] = cands
    if cands:
        arms["solver"] = {**cands[0], "dir": "k0"}
        bi = max(range(len(cands)), key=lambda i: cands[i]["score"])
        arms["best_k"] = {**cands[bi], "dir": f"k{bi}"}
    # library
    libs, n_d = library_trees(items, lib, case["deck"])
    row["donors"] = n_d
    lc = []
    for i, t in enumerate(libs):
        m = try_arm(f"lib{i}", to_xml(parts, t))
        lc.append({**m, "shape": fine_shape(t)})
    if lc:
        bi = max(range(len(lc)), key=lambda i: lc[i]["score"])
        arms["library"] = {**lc[bi], "dir": f"lib{bi}"}
    # guarded
    if "best_k" in arms and arms["today"]["compiled"]:
        keep = arms["best_k"]["score"] < arms["today"]["score"] + MARGIN
        arms["guarded"] = {"arm": "guarded", "kept_today": keep, "score": arms["today"]["score"] if keep else arms["best_k"]["score"]}
    elif "best_k" in arms:
        arms["guarded"] = {"arm": "guarded", "kept_today": False, "score": arms["best_k"]["score"]}
    row["arms"] = arms
    row["seconds"] = round(time_now() - t0, 1)
    return row


def time_now() -> float:
    import time
    return time.time()


# ── cases ────────────────────────────────────────────────────────────────────────────────────────────────────

def nodes_paid_cases(np_dir: Path, b6_dir: Path | None) -> list[dict]:
    cases = []
    inputs = {i["name"]: i for i in json.loads((ROOT / "docs/eval/nodes-paid/inputs.json").read_text(encoding="utf-8"))}
    for name, it in inputs.items():
        d = np_dir / "B" / f"{name}-r1"
        if b6_dir and (b6_dir / "B" / f"{name}-r1" / "first.xml").exists():
            d = b6_dir / "B" / f"{name}-r1"   # the rerun after the fixes
        if not (d / "first.xml").exists():
            continue
        cases.append({"name": name, "deck": it["case"], "plan": it["plan"], "theme": it["theme"],
                      "xml": (d / "first.xml").read_text(encoding="utf-8")})
    return cases


def deck_cases(deck_dir: Path, label: str) -> list[dict]:
    """A whole eval bundle: generated.xml per slide + slides.json."""
    cases = []
    for sj in deck_dir.rglob("slides.json"):
        run = sj.parent.name
        for s in json.loads(sj.read_text(encoding="utf-8")):
            gen = None
            for root in deck_dir.rglob(f"{run}/slide-{s['slide_index']}/generated.xml"):
                gen = root
            if not gen or s["slide_plan"].get("slide_type") not in ("content", "data"):
                continue
            cases.append({"name": f"{label}-{deck_of(run)}-s{s['slide_index']}", "deck": deck_of(run), "plan": s["slide_plan"],
                          "theme": "corporate-slate", "xml": gen.read_text(encoding="utf-8")})
    return cases


# ── stress: any composition, bare tags, no LLM ───────────────────────────────────────────────────────────────

BARE = {"chart": "Chart", "timeline": "Timeline", "kpi_row": "KpiRow", "card_grid": "CardGrid", "table": "Table", "bullet_list": "Ul"}


def bare_xml(plan: dict) -> str | None:
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")  # noqa: E731
    head = f'<VStack gap="8"><Text fontSize="30" bold="true" color="$textMain" lineHeight="1.15">{esc(plan.get("slide_title", ""))}</Text>'
    if plan.get("subtitle"):
        head += f'<Text fontSize="18" color="$textMuted">{esc(plan["subtitle"])}</Text>'
    head += "</VStack>"
    body = ""
    for c in plan.get("components", []):
        k = c.get("kind")
        if k in ("title", "caption"):
            continue
        if k == "narrative":
            t = " ".join(str(i) for i in spec.items(c)) or c.get("content_summary", "")
            body += f'<VStack padding="16" backgroundColor="$surfaceAlt"><Text fontSize="18" color="$textMain">{esc(t)}</Text></VStack>'
        elif k in BARE and c.get("component_id"):
            body += f'<{BARE[k]} ref="{c["component_id"]}"/>'
        else:
            return None
    return f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">{head}{body}</VStack></Slide>'


def stress(srcs: list[Path], k: int, per_set: int, out: Path) -> dict:
    from scripts.smart_layout_part1 import collect
    rows = collect(srcs)
    by_set: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["n"] >= 2:
            by_set[r["kinds"]].append(r)
    res, unsupported = [], 0
    for kinds, group in sorted(by_set.items(), key=lambda kv: -len(kv[1])):
        for r in group[:per_set]:
            x = bare_xml(r["plan"])
            if not x:
                unsupported += 1
                continue
            parts = from_xml(x, r["plan"])
            if not parts or len(leaves_of(parts["tree"])) < 2:
                continue
            name = f"s{len(res):03d}"
            items = leaves_of(parts["tree"])
            base = out / name
            st = resolve_theme("corporate-slate")["element"]
            cands = []
            for i, (est, t) in enumerate(ranked(items, body_box(parts["root"]))[:k]):
                d = draw(to_xml(parts, t), r["plan"], st, base / f"k{i}")
                m = measured(base / f"k{i}", r["plan"].get("slide_type", ""), r["plan"]) if d.get("status") == "success" else {"score": -999.0, "compiled": False, "why": d.get("issues")}
                cands.append({**m, "shape": fine_shape(t)})
            best = max(cands, key=lambda c: c["score"]) if cands else {"score": -999.0, "compiled": False}
            res.append({"name": name, "kinds": kinds, "best": best, "first_compiled": bool(cands and cands[0]["compiled"]), "n_compiled": sum(c["compiled"] for c in cands)})
            print(name, kinds, best.get("score"), best.get("shape"), flush=True)
            shutil.rmtree(base, ignore_errors=True)   # keep the disk free on this PC
    summary = {"kind_sets_seen": len(by_set), "slides_tried": len(res), "plans_with_a_kind_code_cannot_draw_bare": unsupported,
               "any_candidate_compiled": sum(r["n_compiled"] > 0 for r in res),
               "best_has_no_hard_fault": sum(r["best"].get("hard", 9) == 0 and r["best"].get("compiled", False) for r in res),
               "best_no_broken_word": sum(r["best"].get("words", 9) == 0 for r in res),
               "best_not_sparse": sum(not r["best"].get("codes", {}).get("GEOM_SLIDE_SPARSE") for r in res), "rows": res}
    (out.parent / "stress.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return summary


# ── renders and sheets ───────────────────────────────────────────────────────────────────────────────────────

def _pdf_png(dest: Path, png: Path) -> bool:
    from scripts.card_replay import render
    import pymupdf
    pdf = render(dest)
    if not pdf:
        return False
    pymupdf.open(pdf)[0].get_pixmap(dpi=64).save(png)
    return True


def render_all(out: Path, results: list[dict], names: list[str] | None = None) -> None:
    """One LibreOffice at a time (the build PC has 8 GB). Arms with the same tags share one render. Keeps rendered faults."""
    from scripts.card_replay import overlaps
    from scripts.kpi_replay import broken_words
    results_file = out.parent / "results.json"
    for r in results:
        if "arms" not in r or (names and r["name"] not in names):
            continue
        done: dict[str, dict] = {}
        for arm, a in r["arms"].items():
            if arm == "guarded" or not a.get("compiled"):
                continue
            dest = out / r["name"] / (a.get("dir") or arm)
            png = out / r["name"] / f"{arm}.png"
            tags = (dest / "tags.xml").read_text(encoding="utf-8")
            if tags in done:
                if not png.exists() and done[tags]["png"].exists():
                    shutil.copy2(done[tags]["png"], png)
                a["rendered"] = done[tags]["rendered"]
                continue
            ok = png.exists() or _pdf_png(dest, png)
            rendered = {}
            if ok and (dest / "presentation.pdf").exists():
                rendered = {"broken": broken_words(dest, _final(dest).read_text(encoding="utf-8")),
                            "overlaps": len(overlaps(dest / "presentation.pdf"))}
            a["rendered"] = rendered
            done[tags] = {"png": png, "rendered": rendered}
            print(r["name"], arm, ok, rendered, flush=True)
        results_file.write_text(json.dumps(results, indent=1, default=str, ensure_ascii=False), encoding="utf-8")


def build_sheets(out: Path, results: list[dict], sheet_dir: Path, public_decks: tuple[str, ...] | None, label: str) -> dict:
    """One row per slide: every distinct arm, in a random order per row, numbered. key.json says which is which."""
    from PIL import Image, ImageDraw
    rng = random.Random(20261106)
    sheet_dir.mkdir(parents=True, exist_ok=True)
    W, H, GAP, LABEL = 560, 315, 10, 22
    order = ("today", "static", "solver", "best_k", "library")
    rows = []
    for r in results:
        if "arms" not in r or (public_decks is not None and r["deck"] not in public_decks):
            continue
        groups: dict[str, list[str]] = {}
        for arm in order:
            a = r["arms"].get(arm)
            if not a or not a.get("compiled"):
                continue
            png = out / r["name"] / f"{arm}.png"
            if not png.exists():
                continue
            xml = (out / r["name"] / (a.get("dir") or arm) / "tags.xml").read_text(encoding="utf-8")
            groups.setdefault(xml, []).append(arm)
        if len(groups) >= 2:
            rows.append((r, list(groups.values())))
    key, marks, per = [], ["slide,best,worst,reason"], 4
    n_sheets = 0
    for s in range(0, len(rows), per):
        chunk = rows[s:s + per]
        n_sheets += 1
        cols = max(len(g) for _, g in chunk)
        im = Image.new("RGB", (cols * (W + GAP) + GAP, len(chunk) * (H + LABEL + GAP) + GAP), "white")
        dr = ImageDraw.Draw(im)
        for j, (r, g) in enumerate(chunk):
            g = list(g)
            rng.shuffle(g)
            sid = f"{n_sheets}.{j + 1}"
            y = GAP + j * (H + LABEL + GAP)
            dr.text((GAP, y + 4), f"slide {sid}", fill="black")
            opts = {}
            for i, arms in enumerate(g):
                x = GAP + i * (W + GAP)
                dr.text((x + 70, y + 4), f"option {i + 1}", fill="black")
                im.paste(Image.open(out / r["name"] / f"{arms[0]}.png").convert("RGB").resize((W, H)), (x, y + LABEL))
                dr.rectangle((x, y + LABEL, x + W, y + LABEL + H), outline="#999999")
                opts[str(i + 1)] = arms
            key.append({"slide": sid, "case": r["name"], "options": opts})
            marks.append(f"{sid},,,")
        im.save(sheet_dir / f"{label}-{n_sheets}.png")
    (sheet_dir / f"{label}-key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (sheet_dir / f"{label}-marks.csv").write_text("\n".join(marks) + "\n", encoding="utf-8")
    return {"sheets": n_sheets, "slides": len(rows)}


def rescore(out: Path, results: list[dict]) -> list[dict]:
    """The code score again on the compiled folders, no compile; best_k, library and guarded picked again."""
    for r in results:
        if "arms" not in r:
            continue
        base = out / r["name"]
        p = CASE_PLANS.get(r["name"])
        for i, c in enumerate(r.get("candidates", [])):
            if c.get("compiled"):
                c.update(measured(base / f"k{i}", p.get("slide_type", ""), p))
        lc = [i for i in range(3) if (base / f"lib{i}" / "compile-result.json").exists()]
        libs = [(i, measured(base / f"lib{i}", p.get("slide_type", ""), p)) for i in lc]
        for arm in ("today", "static"):
            if arm in r["arms"] and r["arms"][arm].get("compiled"):
                r["arms"][arm].update(measured(base / arm, p.get("slide_type", ""), p))
        cands = r.get("candidates", [])
        if cands:
            r["arms"]["solver"] = {**cands[0], "dir": "k0"}
            bi = max(range(len(cands)), key=lambda i: cands[i]["score"])
            r["arms"]["best_k"] = {**cands[bi], "dir": f"k{bi}"}
        if libs:
            i, m = max(libs, key=lambda x: x[1]["score"])
            r["arms"]["library"] = {**r["arms"].get("library", {}), **m, "dir": f"lib{i}"}
        t = r["arms"]["today"]
        if "best_k" in r["arms"]:
            keep = t.get("compiled") and r["arms"]["best_k"]["score"] < t["score"] + MARGIN
            r["arms"]["guarded"] = {"arm": "guarded", "kept_today": bool(keep), "score": t["score"] if keep else r["arms"]["best_k"]["score"],
                                    "dir": "today" if keep else r["arms"]["best_k"]["dir"], "compiled": True}
    return results


CASE_PLANS: dict = {}


def pair_sheets(out: Path, results: list[dict], sheet_dir: Path, public_decks: tuple[str, ...] | None) -> None:
    """The earlier gates' sheet (scripts/node_test_sheet.py): today against best_k, blind, per slide. best_k plays "nodes"."""
    from scripts import node_test_sheet as T
    pick = out.parent / ("pair-in-public" if public_decks else "pair-in")
    shutil.rmtree(pick, ignore_errors=True)
    for r in results:
        if "arms" not in r or (public_decks is not None and r["deck"] not in public_decks):
            continue
        a, b = r["arms"]["today"], r["arms"].get("best_k")
        if not b or not b.get("compiled") or not a.get("compiled"):
            continue
        src_a, src_b = out / r["name"] / "today", out / r["name"] / b["dir"]
        if not (src_a / "presentation.pdf").exists() or not (src_b / "presentation.pdf").exists():
            continue
        if (src_a / "tags.xml").read_text(encoding="utf-8") == (src_b / "tags.xml").read_text(encoding="utf-8"):
            continue
        for arm, src in (("A", src_a), ("B", src_b)):
            d = pick / arm / r["name"] / "slide-0"
            d.mkdir(parents=True, exist_ok=True)
            for f in ("presentation.pptx", "presentation.pdf"):
                shutil.copy2(src / f, d / f)
    T.build(pick / "B", pick / "A", sheet_dir)


def summarise(results: list[dict]) -> dict:
    done = [r for r in results if "arms" in r]
    arms = ("today", "static", "solver", "best_k", "library", "guarded")
    table = {}
    for a in arms:
        got = [r["arms"][a] for r in done if a in r["arms"]]
        comp = [x for x in got if x.get("compiled", True)]
        table[a] = {"slides": len(got), "compiled": len(comp),
                    "median_score": round(statistics.median([x["score"] for x in comp]), 1) if comp else None,
                    "no_hard_fault": sum(x.get("hard", 0) == 0 for x in comp), "broken_word_warnings": sum(x.get("words", 0) for x in comp),
                    "empty_codes": sum(x.get("codes", {}).get(c, 0) for x in comp for c in ("GEOM_CARD_EMPTY", "GEOM_BOX_EMPTY", "GEOM_SLIDE_SPARSE")),
                    "median_ink": statistics.median([x["ink"] for x in comp if x.get("ink")]) if [x for x in comp if x.get("ink")] else None,
                    "median_font": statistics.median([x["font_median"] for x in comp if x.get("font_median")]) if [x for x in comp if x.get("font_median")] else None}
    return {"slides": len(results), "tested": len(done), "skipped": Counter(r.get("skipped", "") for r in results if "skipped" in r),
            "kept_today_guarded": sum(r["arms"].get("guarded", {}).get("kept_today", False) for r in done),
            "library_donor_coverage": sum(r.get("donors", 0) > 0 for r in done),
            "static_unplaced": sum(1 for r in done if r["arms"].get("static", {}).get("skeleton", "+0").split("+")[-1] != "0"),
            "shapes_considered_median": statistics.median([r["shapes_considered"] for r in done]) if done else 0,
            "seconds_per_slide_median": statistics.median([r["seconds"] for r in done]) if done else 0, "arms": table}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["run", "render", "stress", "sheets", "rescore"])
    ap.add_argument("--np")
    ap.add_argument("--b6")
    ap.add_argument("--deck", nargs="*", default=[])
    ap.add_argument("--corpus", nargs="*", default=[])
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--only", default="")
    ap.add_argument("--per-set", type=int, default=1)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.what == "run":
        cases = nodes_paid_cases(Path(a.np), Path(a.b6) if a.b6 else None) if a.np else []
        for d in a.deck:
            cases += deck_cases(Path(d), "nov5")
        if a.only:
            cases = [c for c in cases if a.only in c["name"]]
        lib = load_library([Path(p) for p in a.corpus])
        print("library kind sets", len(lib), "slides", sum(len(v) for v in lib.values()), flush=True)
        results = []
        for c in cases:
            r = run_slide(c, lib, a.k, OUT / "slides")
            results.append(r)
            print(r["name"], r.get("skipped") or {k: v.get("score") for k, v in r["arms"].items()}, flush=True)
            (OUT / "results.json").write_text(json.dumps(results, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summarise(results), indent=1, default=str))
    elif a.what == "rescore":
        cases = nodes_paid_cases(Path(a.np), Path(a.b6) if a.b6 else None) if a.np else []
        for d in a.deck:
            cases += deck_cases(Path(d), "nov5")
        CASE_PLANS.update({c["name"]: c["plan"] for c in cases})
        results = rescore(OUT / "slides", json.loads((OUT / "results.json").read_text(encoding="utf-8")))
        (OUT / "results.json").write_text(json.dumps(results, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summarise(results), indent=1, default=str))
    elif a.what == "render":
        results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
        render_all(OUT / "slides", results, [a.only] if a.only else None)
    elif a.what == "sheets":
        results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
        print(build_sheets(OUT / "slides", results, OUT / "sheets", None, "all"))
        public = ("deck-qbr-data", "deck-product-launch-data", "gate-deck-all-nodes-dense")
        print(build_sheets(OUT / "slides", results, OUT / "sheets-public", public, "public"))
        pair_sheets(OUT / "slides", results, OUT / "pairs", None)
        pair_sheets(OUT / "slides", results, OUT / "pairs-public", public)
    else:
        print(json.dumps({k: v for k, v in stress([Path(p) for p in a.corpus], a.k, a.per_set, OUT / "stress").items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
