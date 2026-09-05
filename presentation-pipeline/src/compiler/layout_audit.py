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
MIN_FONT_SIZE = 11
MAX_NESTING = 6

_STACK_TAGS = {"VStack", "HStack"}
_NEEDS_DIMS = {"Chart", "Table"}


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
                "severity": "medium",
                "code": "FONT_TOO_SMALL",
                "message": f"<{tag}> has fontSize=\"{fs_str}\" "
                           f"(min {MIN_FONT_SIZE}): \"{text}...\"",
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


def _check_col_widths(root: ET.Element, root_padding: float,
                      issues: list[dict[str, str]]) -> None:
    """Flag Col widths that don't sum to usable slide width."""
    for table in root.iter("Table"):
        cols = table.findall("Col")
        if not cols:
            continue
        widths: list[float] = []
        for col in cols:
            w = _parse_num(col.get("width"))
            if w is not None:
                widths.append(w)
        if not widths or len(widths) != len(cols):
            continue
        total = sum(widths)
        usable = SLIDE_W - 2 * root_padding
        if abs(total - usable) > 100:
            issues.append({
                "severity": "low",
                "code": "COL_WIDTH_SUM",
                "message": f"Col widths sum to {total:.0f}, "
                           f"expected ~{usable:.0f} (1280 - 2×{root_padding:.0f})",
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
    _check_col_widths(root, root_padding, issues)

    return issues
