"""Error-specific repair guidance for the retry loop.

Given a list of errors from pre-validation and compilation, produces targeted
fix instructions for each error type. This is what makes retry attempts
produce *different* (better) output — the AI sees what it got wrong and
exactly how to fix it.
"""

from __future__ import annotations

import re
from typing import Any

# ── Tag translation table (HTML → POM) ────────────────────────────────────────
TAG_TRANSLATIONS: dict[str, str] = {
    "div": "VStack (vertical stack) or HStack (horizontal stack)",
    "p": "Text",
    "span": "Span (capital S, only inside <Text>)",
    "ul": "Ul (capital U)",
    "ol": "Ol (capital O)",
    "li": "Li (capital L)",
    "table": "Table (capital T)",
    "tr": "Tr (capital T)",
    "td": "Td (capital T)",
    "th": "Td (capital T, use bold=true for header styling)",
    "h1": "Text (with fontSize=40 bold=true)",
    "h2": "Text (with fontSize=32 bold=true)",
    "h3": "Text (with fontSize=24 bold=true)",
    "h4": "Text (with fontSize=20 bold=true)",
    "h5": "Text (with fontSize=18 bold=true)",
    "h6": "Text (with fontSize=16 bold=true)",
    "img": "Shape (with shapeType and fill)",
    "strong": "B (bold inline tag inside <Text>)",
    "em": "I (italic inline tag inside <Text>)",
    "br": "Delete — use separate <Text> nodes in a VStack",
    "hr": "Shape (with shapeType='rect' h='2' for a horizontal rule)",
    "a": "A (capital A, inline hyperlink inside <Text>)",
    "section": "VStack",
    "header": "VStack",
    "footer": "VStack",
    "article": "VStack",
    "nav": "VStack",
    "blockquote": "VStack (with borderLeft and padding)",
    "small": "Text (with smaller fontSize)",
    "figure": "VStack",
    "figcaption": "Text (with small fontSize and muted color)",
}

# ── Attribute translation table (CSS/HTML → POM) ─────────────────────────────
ATTR_TRANSLATIONS: dict[str, str] = {
    "style": "Delete — use explicit POM attributes instead",
    "class": "Delete — no classes in POM, use explicit attributes",
    "className": "Delete — no classes in POM",
    "width": "w",
    "height": "h",
    "font-size": "fontSize",
    "text-align": "textAlign",
    "background-color": "backgroundColor",
    "border-radius": "borderRadius",
    "flex-direction": "Use VStack (column) or HStack (row) instead",
    "flex": "grow",
    "justify": "justifyContent",
    "align": "alignItems",
    "display": "Delete — POM layout is implicit from VStack/HStack",
    "float": "Delete — use HStack for side-by-side layout",
    "src": "Delete — not available on this node type",
    "id": "Delete — only needed for Arrow connectors",
    "onclick": "Delete — no event handlers in POM",
    "onchange": "Delete — no event handlers in POM",
}

# ── Valid attributes per node (selective subset for repair hints) ─────────────
NODE_VALID_ATTRS: dict[str, list[str]] = {
    "Text": [
        "fontSize", "color", "textAlign", "bold", "italic", "underline",
        "strike", "fontFamily", "lineHeight", "letterSpacing", "highlight",
        "textGradient", "glow.size", "glow.color", "rotate",
    ],
    "Shape": [
        "shapeType", "text", "fill.color", "fill.transparency",
        "line.color", "line.width", "line.dashType", "borderRadius",
        "rotate",
    ],
    "VStack": ["gap", "alignItems", "justifyContent", "flexWrap"],
    "HStack": ["gap", "alignItems", "justifyContent", "flexWrap"],
    "Chart": [
        "chartType", "chartColors", "w", "h",
        "axis.x.label", "axis.y.label", "axis.x.show", "axis.y.show",
        "legend.show", "legend.position",
    ],
    "Table": ["cellBorder.color", "cellBorder.width"],
    "Td": [
        "backgroundColor", "color", "fontSize", "bold", "textAlign",
        "colSpan", "rowSpan", "padding",
    ],
    "Ul": ["marker"],
    "Li": ["marker"],
}

# Common box-model attrs valid on any node
UNIVERSAL_ATTRS = [
    "w", "h", "grow", "padding", "margin", "gap",
    "alignItems", "justifyContent", "alignSelf", "flexWrap",
    "backgroundColor", "backgroundGradient", "borderRadius",
    "border.color", "border.width", "opacity", "zIndex",
    "shadow.type", "shadow.blur", "shadow.offset", "shadow.color",
]

# ── Layout shrink guidance ───────────────────────────────────────────────────
LAYOUT_SHRINK_GUIDANCE = """LAYOUT OVERFLOW FIX CHECKLIST (apply in order until it fits):
1. Reduce body fontSize by 2 (e.g. 16→14, 14→12)
2. Reduce padding on the root VStack (e.g. 64→48 or 48→32)
3. Reduce gap values (e.g. 24→16 or 16→8)
4. Shorten text content (fewer words, abbreviate labels)
5. If a KPI row has >4 tiles, reduce to 4 or split into two rows
6. Remove the least important component (caption first, then bullet_list)
7. Use a 2-column HStack to place components side by side instead of stacked
All dimensions must stay positive (never 0). Slide bounds: 1280x720."""


def _extract_tag_from_error(msg: str) -> str | None:
    """Extract a tag name from an error message like 'Unknown tag: <div>'."""
    m = re.search(r"<(\w+)>", msg)
    return m.group(1) if m else None


def _extract_attr_from_error(msg: str) -> tuple[str | None, str | None]:
    """Extract (attr, node) from an error message."""
    attr_m = re.search(r'"(\w[\w.\-]*)"', msg)
    node_m = re.search(r"<(\w+)>", msg)
    attr = attr_m.group(1) if attr_m else None
    node = node_m.group(1) if node_m else None
    return attr, node


def build_error_guidance(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> str:
    """Build targeted repair guidance from pre-validation issues + compile diagnostics.

    Returns a formatted string to inject into the repair prompt.
    """
    sections: list[str] = []
    seen_guidance: set[str] = set()

    # Process pre-validation issues
    for issue in pre_issues:
        code = issue.get("code", "")
        message = issue.get("message", "")
        auto_fixed = issue.get("auto_fixed", False)
        if auto_fixed:
            continue

        if code == "HTML_TAG":
            tag = _extract_tag_from_error(message)
            if tag and tag.lower() in TAG_TRANSLATIONS:
                key = f"tag_{tag.lower()}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    replacement = TAG_TRANSLATIONS[tag.lower()]
                    sections.append(
                        f"TAG FIX: <{tag}> is HTML, not POM. "
                        f"Replace with: {replacement}"
                    )

        elif code == "MISCASED_TAG":
            tag = _extract_tag_from_error(message)
            if tag:
                key = f"miscased_{tag}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    sections.append(
                        f"CASE FIX: <{tag}> has wrong case. POM is case-sensitive. "
                        f"Check exact spelling in the ALLOWED NODES list."
                    )

        elif code == "UNKNOWN_TAG":
            tag = _extract_tag_from_error(message)
            if tag:
                low = tag.lower()
                key = f"unknown_{low}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    if low in TAG_TRANSLATIONS:
                        sections.append(
                            f"TAG FIX: <{tag}> is not a POM node. "
                            f"Replace with: {TAG_TRANSLATIONS[low]}"
                        )
                    else:
                        sections.append(
                            f"TAG FIX: <{tag}> is not a POM node. "
                            f"Use only: VStack, HStack, Text, Shape, Span, B, I, "
                            f"Chart, ChartSeries, ChartDataPoint, Ul, Li, Table, Col, Tr, Td"
                        )

        elif code == "HTML_ATTR":
            attr, _ = _extract_attr_from_error(message)
            if attr:
                key = f"attr_{attr.lower()}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    low = attr.lower()
                    if low in ATTR_TRANSLATIONS:
                        sections.append(
                            f"ATTR FIX: \"{attr}\" is forbidden. "
                            f"Replace with: {ATTR_TRANSLATIONS[low]}"
                        )
                    else:
                        sections.append(
                            f"ATTR FIX: \"{attr}\" is forbidden in POM. Remove it."
                        )

        elif code == "UNKNOWN_ATTR":
            attr, node = _extract_attr_from_error(message)
            if attr and node:
                key = f"unknown_attr_{node}_{attr}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    valid = NODE_VALID_ATTRS.get(node, [])
                    valid_str = ", ".join(valid) if valid else "(check ALLOWED ATTRIBUTES)"
                    sections.append(
                        f"ATTR FIX: \"{attr}\" is not valid on <{node}>. "
                        f"Valid attributes for <{node}>: {valid_str} "
                        f"(plus universal: w, h, grow, padding, margin, backgroundColor, ...)"
                    )

        elif code == "ZERO_DIM":
            key = "zero_dim"
            if key not in seen_guidance:
                seen_guidance.add(key)
                sections.append(
                    "VALUE FIX: w, h, fontSize must be > 0. Never use 0 or negative values. "
                    "Use real positive sizes (e.g. w=\"200\", h=\"40\", fontSize=\"14\")."
                )

    # Process compile diagnostics
    for diag in compile_diagnostics:
        dtype = diag.get("type", "")
        dmsg = diag.get("message", "")

        if dtype == "UNKNOWN_TAG":
            tag = _extract_tag_from_error(dmsg)
            if tag:
                low = tag.lower()
                key = f"compile_tag_{low}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    if low in TAG_TRANSLATIONS:
                        sections.append(
                            f"COMPILER TAG FIX: <{tag}> rejected by compiler. "
                            f"Replace with: {TAG_TRANSLATIONS[low]}"
                        )
                    else:
                        sections.append(
                            f"COMPILER TAG FIX: <{tag}> rejected by compiler. "
                            f"Use only valid POM nodes."
                        )

        elif dtype == "UNKNOWN_ATTRIBUTE":
            attr, node = _extract_attr_from_error(dmsg)
            if attr:
                key = f"compile_attr_{attr}"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    valid = NODE_VALID_ATTRS.get(node, []) if node else []
                    if valid:
                        sections.append(
                            f"COMPILER ATTR FIX: \"{attr}\" rejected on <{node}>. "
                            f"Valid: {', '.join(valid)}"
                        )
                    else:
                        sections.append(
                            f"COMPILER ATTR FIX: \"{attr}\" rejected. Remove it or "
                            f"use a real POM attribute."
                        )

        elif dtype == "PARSE_ERROR":
            key = "parse_error"
            if key not in seen_guidance:
                seen_guidance.add(key)
                sections.append(
                    f"SYNTAX FIX: XML parse error — {dmsg}. "
                    f"Check for unclosed tags, mismatched quotes, or invalid XML characters."
                )

        elif dtype == "INVALID_VALUE":
            key = "invalid_value"
            if key not in seen_guidance:
                seen_guidance.add(key)
                sections.append(
                    f"VALUE FIX: {dmsg}. "
                    f"All dimensions (w, h, fontSize) must be positive numbers. "
                    f"Colors must be 6-digit hex (e.g. FF0000), no named colors."
                )

        elif dtype == "DIAGNOSTIC":
            if "OUT_OF_BOUNDS" in dmsg.upper() or "OVERFLOW" in dmsg.upper():
                key = "layout_overflow"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    sections.append(LAYOUT_SHRINK_GUIDANCE)
            elif "OVERLAP" in dmsg.upper():
                key = "layout_overlap"
                if key not in seen_guidance:
                    seen_guidance.add(key)
                    sections.append(
                        "OVERLAP FIX: Sibling nodes overlap. Remove stray top/left "
                        "offsets or negative margins. Check that VStack/HStack children "
                        "don't have position='absolute'."
                    )

    if not sections:
        return ""
    return "\n\n".join(sections)


def error_signatures(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> set[str]:
    """Extract a set of error 'signatures' for stall detection.

    If two consecutive attempts produce ≥80% overlapping signatures,
    the retry loop should escalate to the next tier.
    """
    sigs: set[str] = set()
    for issue in pre_issues:
        if issue.get("auto_fixed"):
            continue
        code = issue.get("code", "")
        tag = _extract_tag_from_error(issue.get("message", ""))
        attr, node = _extract_attr_from_error(issue.get("message", ""))
        if code in ("HTML_TAG", "MISCASED_TAG", "UNKNOWN_TAG") and tag:
            sigs.add(f"{code}:{tag}")
        elif code in ("HTML_ATTR", "UNKNOWN_ATTR") and attr:
            sigs.add(f"{code}:{node or '?'}:{attr}")
        elif code == "ZERO_DIM":
            sigs.add("ZERO_DIM")
        else:
            sigs.add(f"{code}:{issue.get('message', '')[:40]}")

    for diag in compile_diagnostics:
        dtype = diag.get("type", "")
        dmsg = diag.get("message", "")[:40]
        sigs.add(f"COMPILE:{dtype}:{dmsg}")

    return sigs


def is_stalled(prev_sigs: set[str], curr_sigs: set[str], threshold: float = 0.8) -> bool:
    """True if ≥threshold of current errors were also in the previous attempt."""
    if not curr_sigs:
        return False
    if not prev_sigs:
        return False
    overlap = len(curr_sigs & prev_sigs)
    return overlap / len(curr_sigs) >= threshold
