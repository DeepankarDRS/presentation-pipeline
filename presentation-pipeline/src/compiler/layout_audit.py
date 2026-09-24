"""Layout audit — mechanical spatial checks on POM XML.

Pure function, no LLM, no state dependency. Parses cleaned XML and
checks spatial constraints. Returns warnings that feed the critic.

Issues are informational — they never block compilation.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger(__name__)

SLIDE_W = 1280
SLIDE_H = 720
MIN_FONT_SIZE = 14
MAX_NESTING = 6
# TABLE_TOO_WIDE_FOR_CARD: a table in a card narrower than this share of the
# slide whose longest cell would wrap to this many lines (at an equal column
# split, ~7.7 px per char at the 14 px body size). Many short numeric columns in
# a half-width card are fine (the gj-h1 golden deep-dives); long text is not.
TABLE_NARROW_SHARE = 0.6
TABLE_WRAP_LINES = 4
_CHAR_PX = 7.7
_CONTENT_W = SLIDE_W - 2 * 48

_STACK_TAGS = {"VStack", "HStack"}
# Sizing grammar (docs/layout-sizing-plan.md Step 1). Table needs no dims: it
# sizes to its rows at full width. These fill their box, so they need an h —
# pixel, or h="max" with a minH readability floor:
_FILL_NODES = {"Chart", "Matrix", "ProcessArrow", "Flow", "Tree"}
# These never scale up (F6), so the box is sized to the diagram — a pixel h:
_FIXED_NODES = {"Timeline", "Pyramid"}


def _parse_num(value: str | None) -> float | None:
    """Parse a numeric attribute, returning None for non-numeric values."""
    if value is None:
        return None
    if value in ("max", "auto"):
        return None
    try:
        v = value.rstrip("%")
        return float(v)
    except (ValueError, TypeError):
        return None


def _check_root_size(root: ET.Element, issues: list[dict[str, str]]) -> float:
    """Check that the first VStack/HStack under <Slide> has 1280x720 dims.

    Returns root padding for downstream checks.
    """
    slide = root if root.tag == "Slide" else root.find(".//Slide")
    if slide is None:
        return 48.0

    for child in slide:
        if child.tag in _STACK_TAGS:
            w = child.get("w")
            h = child.get("h")
            w_ok = w in ("1280", "max", "100%")
            h_ok = h in ("720", "max", "100%")
            if not w_ok or not h_ok:
                issues.append({
                    "severity": "high",
                    "code": "ROOT_SIZE",
                    "message": f"Root {child.tag} has w=\"{w}\" h=\"{h}\", "
                               f"expected w=\"1280\" h=\"720\" (or \"max\")",
                })
            align = child.get("alignItems")
            if align and align not in ("stretch", "start"):
                issues.append({
                    "severity": "high",
                    "code": "ROOT_ALIGN",
                    "message": f"Root {child.tag} has alignItems=\"{align}\". "
                               f"Use alignItems=\"stretch\" (or omit) so child "
                               f"rows expand to full width.",
                })
            padding = _parse_num(child.get("padding"))
            return padding if padding is not None else 48.0

    return 48.0


def _check_font_sizes(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag any fontSize below MIN_FONT_SIZE."""
    for elem in root.iter():
        fs_str = elem.get("fontSize")
        if fs_str is None:
            continue
        fs = _parse_num(fs_str)
        if fs is not None and fs < MIN_FONT_SIZE:
            tag = elem.tag
            text = (elem.text or "")[:30]
            issues.append({
                "severity": "high",
                "code": "FONT_TOO_SMALL",
                "message": f"<{tag}> has fontSize=\"{fs_str}\" "
                           f"(min {MIN_FONT_SIZE}): \"{text}...\". "
                           f"Fix: raise to {MIN_FONT_SIZE} or cut content.",
            })


def _check_zero_dims(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag zero or negative w, h, fontSize."""
    for elem in root.iter():
        for attr in ("w", "h", "fontSize"):
            val_str = elem.get(attr)
            if val_str is None:
                continue
            val = _parse_num(val_str)
            if val is not None and val <= 0:
                issues.append({
                    "severity": "high",
                    "code": "ZERO_DIM",
                    "message": f"<{elem.tag}> has {attr}=\"{val_str}\" (must be > 0)",
                })


def _check_missing_dims(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag data nodes whose height the sizing grammar cannot resolve."""
    for elem in root.iter():
        h = elem.get("h")
        if elem.tag in _FILL_NODES:
            if h is None:
                message = f'<{elem.tag}> missing h: use h="max" minH="..." to fill its card'
            elif (h == "max" or elem.get("grow")) and elem.get("minH") is None:
                message = f'<{elem.tag}> h="max" without minH: add a readability floor (e.g. minH="180")'
            else:
                continue
        elif elem.tag in _FIXED_NODES and _parse_num(h) is None:
            message = f"<{elem.tag}> needs a pixel h (it never scales up; size the box to the diagram)"
        else:
            continue
        issues.append({"severity": "medium", "code": "MISSING_DIMS", "message": message})


def _check_vstack_w_max(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag w="max" on a VStack child: it grows the HEIGHT (flexGrow on the main
    axis) and overrides a numeric h (F1) — the bloated-KPI-row failure."""
    for stack in root.iter("VStack"):
        count = sum(1 for c in stack if c.get("w") == "max")
        if count:
            issues.append({
                "severity": "low",
                "code": "VSTACK_W_MAX",
                "message": (
                    f'{count} child(ren) of a VStack with w="max": that grows the height, '
                    'not the width (width already stretches). Drop it; use grow="N" '
                    'only if the box should take spare height.'
                ),
            })


def _check_nesting(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag excessive stack nesting depth."""
    def _walk(elem: ET.Element, depth: int) -> None:
        if elem.tag in _STACK_TAGS:
            depth += 1
            if depth > MAX_NESTING:
                issues.append({
                    "severity": "low",
                    "code": "DEEP_NESTING",
                    "message": f"Stack nesting depth {depth} exceeds max {MAX_NESTING}",
                })
                return
        for child in elem:
            _walk(child, depth)

    _walk(root, 0)


def _check_col_widths(root: ET.Element, root_padding: float,
                      issues: list[dict[str, str]]) -> None:
    """Flag Col widths that exceed usable slide width.

    Handles three patterns:
      - All cols have width: sum must be close to usable width.
      - Mixed (some with, some without): specified total must not exceed usable.
      - No cols have width: auto-fill, nothing to check.
    """
    for table in root.iter("Table"):
        cols = table.findall("Col")
        if not cols:
            continue
        specified: list[float] = []
        for col in cols:
            w = _parse_num(col.get("width"))
            if w is not None:
                specified.append(w)
        if not specified:
            continue
        total_specified = sum(specified)
        usable = SLIDE_W - 2 * root_padding
        all_specified = len(specified) == len(cols)
        if all_specified:
            if abs(total_specified - usable) > 100:
                issues.append({
                    "severity": "low",
                    "code": "COL_WIDTH_SUM",
                    "message": f"Col widths sum to {total_specified:.0f}, "
                               f"expected ~{usable:.0f} (1280 - 2×{root_padding:.0f})",
                })
        else:
            if total_specified > usable:
                issues.append({
                    "severity": "high",
                    "code": "COL_WIDTH_SUM",
                    "message": f"Specified Col widths sum to {total_specified:.0f}, "
                               f"exceeding usable {usable:.0f} (1280 - 2×{root_padding:.0f}) "
                               f"— auto-fill columns get zero width",
                })


def _check_band_height_sum(root: ET.Element, root_padding: float,
                           issues: list[dict[str, str]]) -> None:
    """Flag a root VStack whose children's explicit heights + gaps overflow 720.

    POM children default flexShrink=1, so an over-budget stack does NOT raise
    NODE_OUT_OF_BOUNDS — it silently squashes and overlaps. Catch it statically.
    Only fires when the root is a VStack and enough children carry an explicit
    numeric h that a real estimate is possible.
    """
    slide = root if root.tag == "Slide" else root.find(".//Slide")
    if slide is None:
        return
    rootv = next((c for c in slide if c.tag == "VStack"), None)
    if rootv is None:
        return
    children = [c for c in rootv if c.tag in _STACK_TAGS or c.tag == "Chart"]
    if len(children) < 2:
        return
    gap = _parse_num(rootv.get("gap")) or 0.0
    explicit = [_parse_num(c.get("h")) for c in children]
    known = [h for h in explicit if h is not None]
    # need most bands sized to make a meaningful claim
    if len(known) < len(children) - 1 or not known:
        return
    # unknown bands: first child (header) ~100px, other auto bands ~130px
    est_unknown = 0.0
    for i, h in enumerate(explicit):
        if h is None:
            est_unknown += 100.0 if i == 0 else 130.0
    est_total = sum(known) + est_unknown
    est_total += gap * (len(children) - 1) + 2 * root_padding
    if est_total > 720:
        issues.append({
            "severity": "high",
            "code": "BAND_HEIGHT_SUM",
            "message": (
                f"Root VStack children's heights + gaps + padding ~= {est_total:.0f} "
                f"> 720. POM will shrink and overlap the bands (no compile error). "
                f"Reduce a band height, shrink the chart, or drop content."
            ),
        })


def _check_hstack_column_heights(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag columns in an HStack-root layout whose children overflow 720.

    When the slide root is an HStack (full-bleed column split), each VStack
    column is its own vertical layout that must fit within 720px.
    """
    slide = root if root.tag == "Slide" else root.find(".//Slide")
    if slide is None:
        return
    rooth = next((c for c in slide if c.tag == "HStack"), None)
    if rooth is None:
        return
    # Only applies when the root is an HStack (not when a VStack root exists)
    if any(c.tag == "VStack" for c in slide):
        return
    col_padding = _parse_num(rooth.get("padding")) or 0.0
    for col_idx, col in enumerate(rooth):
        if col.tag != "VStack":
            continue
        padding = _parse_num(col.get("padding")) or 0.0
        gap = _parse_num(col.get("gap")) or 0.0
        children = [c for c in col if c.tag in _STACK_TAGS or c.tag == "Chart"]
        if len(children) < 2:
            continue
        explicit = [_parse_num(c.get("h")) for c in children]
        known = [h for h in explicit if h is not None]
        if len(known) < len(children) - 1 or not known:
            continue
        est_unknown = 0.0
        for i, h in enumerate(explicit):
            if h is None:
                est_unknown += 100.0 if i == 0 else 130.0
        est_total = sum(known) + est_unknown
        est_total += gap * (len(children) - 1) + 2 * padding + 2 * col_padding
        if est_total > 720:
            issues.append({
                "severity": "high",
                "code": "BAND_HEIGHT_SUM",
                "message": (
                    f"HStack column {col_idx} children's heights + gaps + padding "
                    f"~= {est_total:.0f} > 720. POM will shrink and overlap. "
                    f"Reduce a band height or drop content."
                ),
            })


def _width_share(child: ET.Element, hstack: ET.Element) -> float:
    """Approximate share of an HStack's width one child gets: its own w (% or
    px of the slide), else an equal split of what the sized children leave."""
    kids = list(hstack)
    sized: dict[int, float] = {}
    for i, c in enumerate(kids):
        w = c.get("w") or ""
        num = _parse_num(w)
        if num is not None:
            sized[i] = num / 100 if w.endswith("%") else num / SLIDE_W
    idx = kids.index(child)
    if idx in sized:
        return min(1.0, sized[idx])
    rest = max(0.0, 1.0 - sum(sized.values()))
    return rest / max(1, len(kids) - len(sized))


def _check_table_width(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag a wide table placed in a narrow card (option B, roadmap Phase 2.4).

    A table with many columns or long cell text in a card that shares its row
    with other cards wraps into tall rows; on a full slide those rows run under
    the next band. Warn-only until Phase 2 settles the threshold.
    """
    parents = {c: p for p in root.iter() for c in p}
    for table in root.iter("Table"):
        share, node = 1.0, table
        while node in parents:
            parent = parents[node]
            if parent.tag == "HStack" and len(parent) > 1:
                share *= _width_share(node, parent)
            node = parent
        if share >= TABLE_NARROW_SHARE:
            continue
        cols = max(len(table.findall("Col")), max(
            (len(tr.findall("Td")) for tr in table.iter("Tr")), default=0), 1)
        longest = max((len("".join(td.itertext()).strip()) for td in table.iter("Td")), default=0)
        lines = longest * _CHAR_PX / (share * _CONTENT_W / cols)
        if lines >= TABLE_WRAP_LINES:
            issues.append({
                "severity": "low",
                "code": "TABLE_TOO_WIDE_FOR_CARD",
                "message": (
                    f"Table with {cols} columns in a card ~{share:.0%} of the slide wide: its "
                    f"longest cell ({longest} chars) wraps to ~{lines:.0f} lines, so rows grow tall "
                    "and can run under the next band. Give it a full-width band, or move the "
                    "long-text column into a list beside the table."
                ),
            })


def audit_layout(xml: str) -> list[dict[str, str]]:
    """Parse POM XML and check spatial/layout constraints.

    Returns a list of issue dicts: {severity, code, message}.
    Issues are warnings — they never block compilation.
    """
    issues: list[dict[str, str]] = []

    try:
        root = ET.fromstring(f"<_root_>{xml}</_root_>")
    except ET.ParseError as e:
        return [{"severity": "high", "code": "XML_PARSE_ERROR",
                 "message": f"Failed to parse XML for layout audit: {e}"}]

    root_padding = _check_root_size(root, issues)
    _check_font_sizes(root, issues)
    _check_zero_dims(root, issues)
    _check_missing_dims(root, issues)
    _check_vstack_w_max(root, issues)
    _check_nesting(root, issues)
    _check_col_widths(root, root_padding, issues)
    _check_band_height_sum(root, root_padding, issues)
    _check_hstack_column_heights(root, issues)
    _check_table_width(root, issues)

    return issues
