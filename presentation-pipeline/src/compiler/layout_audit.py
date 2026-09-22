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

_STACK_TAGS = {"VStack", "HStack"}
_NEEDS_DIMS = {"Chart", "Table", "Matrix", "ProcessArrow", "Flow", "Pyramid", "Tree", "Timeline"}
_LI_VALID_CHILDREN = {"B", "I", "A", "U", "S", "Sub", "Sup", "Span", "Mark"}


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
    """Flag Chart/Table without explicit w and h."""
    for elem in root.iter():
        if elem.tag in _NEEDS_DIMS:
            w = elem.get("w")
            h = elem.get("h")
            if w is None or h is None:
                missing = []
                if w is None:
                    missing.append("w")
                if h is None:
                    missing.append("h")
                issues.append({
                    "severity": "medium",
                    "code": "MISSING_DIMS",
                    "message": f"<{elem.tag}> missing explicit {', '.join(missing)}",
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


def _check_li_children(root: ET.Element, issues: list[dict[str, str]]) -> None:
    """Flag block elements inside <Li> — POM silently strips them."""
    for li in root.iter("Li"):
        for child in li:
            if child.tag not in _LI_VALID_CHILDREN:
                issues.append({
                    "severity": "high",
                    "code": "LI_INVALID_CHILD",
                    "message": (
                        f"<{child.tag}> inside <Li> will be silently stripped. "
                        f"Li only supports inline tags: {', '.join(sorted(_LI_VALID_CHILDREN))}. "
                        f"Use HStack rows with Icon + Text instead of Ul/Li."
                    ),
                })


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
    _check_nesting(root, issues)
    _check_li_children(root, issues)
    _check_col_widths(root, root_padding, issues)
    _check_band_height_sum(root, root_padding, issues)
    _check_hstack_column_heights(root, issues)

    return issues
