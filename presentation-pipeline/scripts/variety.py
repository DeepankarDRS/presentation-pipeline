"""Layout variety (docs/derived-blocks-planning-2026-10-06.md §1b), shared by 1a and step 3.

    signature(xml, fine=True)   the slide body's container tree as a string
    report(slides)              slides = [{"deck", "xml", "kinds"}] -> within-deck variety, cross-deck
                                sameness, house-template share (with counts)

Signature: the root's children after dropping the header and decoration (the root's own Text
children, Shapes, Icons); each Stack is its orientation and children, a leaf is a ref node's tag
(<KpiRow ref>, <Table ref> ...) or a native node class (Table -> table, Ul -> bullets, ...) or
`text`. Each child of an HStack carries its width share: narrow <= 33%, wide >= 60%, else mid
(`flex` for grow / max). Single-child containers are flattened. Coarse = the same without shares.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

LEAF = {"Table": "table", "Chart": "chart", "Ul": "bullets", "Ol": "bullets", "Timeline": "timeline",
        "ProcessArrow": "process", "Flow": "flow", "Pyramid": "pyramid", "Tree": "tree", "Matrix": "matrix",
        "KpiRow": "kpi", "CardGrid": "cards", "Callout": "callout", "Text": "text", "Layer": "layer"}
DECOR = {"Shape", "Icon", "Line", "Arrow", "Svg"}
STACKS = {"VStack": "V", "HStack": "H"}
SLIDE_W = 1200.0


def _parse(xml: str) -> ET.Element | None:
    body = re.sub(r"<Theme\b[^>]*/>|<!--.*?-->", "", xml, flags=re.S)
    body = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", "&amp;", body)
    try:
        root = ET.fromstring(body.strip())
    except ET.ParseError:
        return None
    if root.tag == "Slide":
        kids = list(root)
        root = kids[0] if kids else None
    return root


def _share(el: ET.Element, parent_w: float) -> str:
    w = el.get("w") or ""
    if w.endswith("%"):
        s = float(w[:-1]) / 100
    elif re.fullmatch(r"\d+(\.\d+)?", w):
        s = float(w) / max(parent_w, 1)
    else:
        return "flex"
    return "narrow" if s <= 0.33 else "wide" if s >= 0.6 else "mid"


def _node(el: ET.Element, fine: bool, parent: str | None, depth: int) -> str | None:
    tag = el.tag
    if tag in DECOR:
        return None
    if tag in STACKS:
        kids = [k for k in (_node(c, fine, tag, depth + 1) for c in el) if k]
        if not kids:
            return None
        if len(kids) == 1:
            return kids[0]
        if fine and tag == "HStack":
            kids = [f"{k}@{_share(c, SLIDE_W)}" for k, c in zip(kids, [c for c in el if _node(c, fine, tag, depth + 1)])]
        return f"{STACKS[tag]}({','.join(kids)})"
    return LEAF.get(tag, tag.lower())


def signature(xml: str, fine: bool = True) -> str:
    root = _parse(xml)
    if root is None:
        return "unparsed"
    kids = [c for c in root if not (c.tag == "Text" or c.tag in DECOR)]   # header, source line, decoration
    parts = [k for k in (_node(c, fine, root.tag, 1) for c in kids) if k]
    if not parts:
        return "empty"
    return parts[0] if len(parts) == 1 else f"{STACKS.get(root.tag, 'V')}({','.join(parts)})"


def report(slides: list[dict[str, Any]]) -> dict[str, Any]:
    """slides: [{"deck", "xml", "kinds": [plan component kinds]}] -> the three §1b numbers with counts."""
    by_deck: dict[str, list[str]] = defaultdict(list)
    for s in slides:
        by_deck[s["deck"]].append(signature(s["xml"], fine=True))
    within = {d: len(set(sigs)) / len(sigs) for d, sigs in by_deck.items() if sigs}
    coarse = [(s["deck"], tuple(sorted(s.get("kinds") or [])), signature(s["xml"], fine=False)) for s in slides]
    groups: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    for deck, kinds, sig in coarse:
        groups[kinds].append((deck, sig))
    pairs = same = 0
    for members in groups.values():
        if len({d for d, _ in members}) < 2:
            continue
        for (d1, s1), (d2, s2) in combinations(members, 2):
            if d1 != d2:
                pairs += 1
                same += s1 == s2
    common = Counter(sig for _, _, sig in coarse).most_common(1)
    return {
        "within_deck": round(sum(within.values()) / len(within), 3) if within else None,
        "within_by_deck": {d: round(v, 3) for d, v in within.items()},
        "cross_deck_sameness": round(same / pairs, 3) if pairs else None, "cross_deck_pairs": pairs,
        "house_template_share": round(common[0][1] / len(coarse), 3) if common else None,
        "house_template": common[0][0] if common else None, "slides": len(slides),
    }
