"""Error-specific repair guidance for the retry loop.

Produces targeted fix instructions AND knowledge-base slices from
pre-validation issues and compile diagnostics.

The key idea: errors tell us which nodes/attributes went wrong, so we
load ONLY the relevant component YAML (attributes, pitfalls, examples)
instead of re-sending the full generation prompt.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml

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
    "spacing": "gap (POM uses 'gap' for spacing between children in VStack/HStack)",
    "fontWeight": "bold='true' (POM uses bold attribute, not fontWeight)",
    "src": "Delete — not available on this node type",
    "id": "Delete — only needed for Arrow connectors",
    "onclick": "Delete — no event handlers in POM",
    "onchange": "Delete — no event handlers in POM",
}

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

LAYOUT_SHRINK_GUIDANCE = """LAYOUT OVERFLOW FIX CHECKLIST (apply in order until it fits):
1. Reduce body fontSize by 2 (e.g. 16->14, 14->12)
2. Reduce padding on the root VStack (e.g. 64->48 or 48->32)
3. Reduce gap values (e.g. 24->16 or 16->8)
4. Shorten text content (fewer words, abbreviate labels)
5. If a KPI row has >4 tiles, reduce to 4 or split into two rows
6. Remove the least important component (caption first, then bullet_list)
7. Use a 2-column HStack to place components side by side instead of stacked
All dimensions must stay positive (never 0). Slide bounds: 1280x720."""


def _extract_tag_from_error(msg: str) -> str | None:
    m = re.search(r"<(\w+)>", msg)
    return m.group(1) if m else None


def _extract_attr_from_error(msg: str) -> tuple[str | None, str | None]:
    attr_m = re.search(r'"(\w[\w.\-]*)"', msg)
    node_m = re.search(r"<(\w+)>", msg)
    return (attr_m.group(1) if attr_m else None, node_m.group(1) if node_m else None)


def build_error_guidance(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> str:
    """Build targeted repair guidance from errors. Returns formatted string."""
    sections: list[str] = []
    seen: set[str] = set()

    for issue in pre_issues:
        code = issue.get("code", "")
        message = issue.get("message", "")
        if issue.get("auto_fixed", False):
            continue

        if code in ("HTML_TAG", "UNKNOWN_TAG"):
            tag = _extract_tag_from_error(message)
            if tag and tag.lower() in TAG_TRANSLATIONS:
                key = f"tag_{tag.lower()}"
                if key not in seen:
                    seen.add(key)
                    sections.append(
                        f"TAG FIX: <{tag}> is not POM. Replace with: {TAG_TRANSLATIONS[tag.lower()]}"
                    )

        elif code == "MISCASED_TAG":
            tag = _extract_tag_from_error(message)
            if tag:
                key = f"miscased_{tag}"
                if key not in seen:
                    seen.add(key)
                    sections.append(
                        f"CASE FIX: <{tag}> has wrong case. POM is case-sensitive."
                    )

        elif code == "HTML_ATTR":
            attr, _ = _extract_attr_from_error(message)
            if attr:
                key = f"attr_{attr.lower()}"
                if key not in seen:
                    seen.add(key)
                    low = attr.lower()
                    if low in ATTR_TRANSLATIONS:
                        sections.append(
                            f'ATTR FIX: "{attr}" is forbidden. Replace with: {ATTR_TRANSLATIONS[low]}'
                        )
                    else:
                        sections.append(f'ATTR FIX: "{attr}" is forbidden in POM. Remove it.')

        elif code == "UNKNOWN_ATTR":
            attr, node = _extract_attr_from_error(message)
            if attr and node:
                key = f"unknown_attr_{node}_{attr}"
                if key not in seen:
                    seen.add(key)
                    valid = NODE_VALID_ATTRS.get(node, [])
                    valid_str = ", ".join(valid) if valid else "(check ALLOWED ATTRIBUTES)"
                    sections.append(
                        f'ATTR FIX: "{attr}" is not valid on <{node}>. '
                        f"Valid: {valid_str}"
                    )

        elif code == "ZERO_DIM":
            key = "zero_dim"
            if key not in seen:
                seen.add(key)
                sections.append(
                    "VALUE FIX: w, h, fontSize must be > 0. Never use 0 or negative values."
                )

    for diag in compile_diagnostics:
        dtype = diag.get("type", "")
        dmsg = diag.get("message", "")

        if "child elements" in dmsg.lower() or "unexpected child" in dmsg.lower():
            tag = _extract_tag_from_error(dmsg)
            key = f"no_children_{(tag or 'unknown').lower()}"
            if key not in seen:
                seen.add(key)
                if tag and tag.lower() == "shape":
                    sections.append(
                        f"STRUCTURE FIX: <{tag}> is a LEAF node — it does NOT accept child elements. "
                        "For text inside a shape, use the text attribute: "
                        '<Shape shapeType="rect" text="Hello" />. '
                        "For complex content (multiple Text nodes), replace <Shape> with "
                        "<VStack> containing <Text> children."
                    )
                else:
                    sections.append(
                        f"STRUCTURE FIX: <{tag or '?'}> does not accept child elements. "
                        "Remove nested elements or use a container like VStack/HStack instead."
                    )

        if dtype == "UNKNOWN_TAG":
            tag = _extract_tag_from_error(dmsg)
            if tag:
                key = f"compile_tag_{tag.lower()}"
                if key not in seen:
                    seen.add(key)
                    low = tag.lower()
                    replacement = TAG_TRANSLATIONS.get(low, "a valid POM node")
                    sections.append(f"COMPILER TAG FIX: <{tag}> rejected. Replace with: {replacement}")

        elif dtype == "UNKNOWN_ATTRIBUTE":
            attr, node = _extract_attr_from_error(dmsg)
            if attr:
                key = f"compile_attr_{attr}"
                if key not in seen:
                    seen.add(key)
                    valid = NODE_VALID_ATTRS.get(node, []) if node else []
                    if valid:
                        sections.append(
                            f'COMPILER ATTR FIX: "{attr}" rejected on <{node}>. Valid: {", ".join(valid)}'
                        )
                    else:
                        sections.append(f'COMPILER ATTR FIX: "{attr}" rejected. Remove it.')

        elif dtype == "PARSE_ERROR":
            key = "parse_error"
            if key not in seen:
                seen.add(key)
                sections.append(
                    f"SYNTAX FIX: XML parse error — {dmsg}. "
                    "Check for unclosed tags, mismatched quotes, or invalid XML."
                )

        elif dtype == "INVALID_VALUE":
            key = "invalid_value"
            if key not in seen:
                seen.add(key)
                sections.append(
                    f"VALUE FIX: {dmsg}. "
                    "All dimensions must be positive numbers. Colors: 6-digit hex."
                )

        elif dtype == "DIAGNOSTIC":
            if "OUT_OF_BOUNDS" in dmsg.upper() or "OVERFLOW" in dmsg.upper():
                key = "layout_overflow"
                if key not in seen:
                    seen.add(key)
                    sections.append(LAYOUT_SHRINK_GUIDANCE)
            elif "OVERLAP" in dmsg.upper():
                key = "layout_overlap"
                if key not in seen:
                    seen.add(key)
                    sections.append(
                        "OVERLAP FIX: Sibling nodes overlap. Remove stray offsets or negative margins."
                    )

    return "\n\n".join(sections)


def error_signatures(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> set[str]:
    """Extract error signatures for stall detection."""
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
        sigs.add(f"COMPILE:{diag.get('type', '')}:{diag.get('message', '')[:40]}")

    return sigs


def is_stalled(prev_sigs: set[str], curr_sigs: set[str], threshold: float = 0.65) -> bool:
    """True if >=threshold of current errors were also in the previous attempt."""
    if not curr_sigs or not prev_sigs:
        return False
    overlap = len(curr_sigs & prev_sigs)
    return overlap / len(curr_sigs) >= threshold


_STRUCTURAL_DIAG_TYPES = {"INVALID_CHILD"}


def needs_regeneration(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> bool:
    """True when the errors are structural — an in-place PATCH is unlikely to fix
    them and a full rebuild is the better move.

    Covers invalid child nesting (``INVALID_CHILD`` / "unexpected child elements"
    parse errors). The substrings mirror ``build_error_guidance`` so the two stay
    consistent.
    """
    for diag in compile_diagnostics:
        dtype = diag.get("type", "")
        dmsg = diag.get("message", "").lower()
        if dtype in _STRUCTURAL_DIAG_TYPES:
            return True
        if "unexpected child" in dmsg or "child elements" in dmsg:
            return True
    return False


# ── Error-driven knowledge selection ─────────────────────────────────────────
# Maps errors → targeted knowledge YAML slices so the repairer gets
# node-specific attribute docs + examples instead of the full system prompt.

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"

_NODE_TO_KNOWLEDGE_FILE: dict[str, str] = {
    "Text": "components/text.yaml",
    "Shape": "components/shape.yaml",
    "Chart": "components/chart.yaml",
    "ChartSeries": "components/chart.yaml",
    "ChartDataPoint": "components/chart.yaml",
    "Ul": "components/list.yaml",
    "Ol": "components/list.yaml",
    "Li": "components/list.yaml",
    "Table": "components/table.yaml",
    "Col": "components/table.yaml",
    "Tr": "components/table.yaml",
    "Td": "components/table.yaml",
    "Timeline": "components/timeline.yaml",
    "TimelineItem": "components/timeline.yaml",
    "Flow": "components/flow.yaml",
    "FlowNode": "components/flow.yaml",
    "FlowConnection": "components/flow.yaml",
    "Layer": "components/drawing.yaml",
    "Line": "components/drawing.yaml",
    "Arrow": "components/drawing.yaml",
    "Svg": "components/drawing.yaml",
    "Matrix": "components/matrix.yaml",
    "MatrixAxes": "components/matrix.yaml",
    "MatrixQuadrants": "components/matrix.yaml",
    "MatrixItem": "components/matrix.yaml",
    "Tree": "components/tree.yaml",
    "TreeItem": "components/tree.yaml",
    "ProcessArrow": "components/process-arrow.yaml",
    "ProcessArrowStep": "components/process-arrow.yaml",
    "Pyramid": "components/pyramid.yaml",
    "PyramidLevel": "components/pyramid.yaml",
}


@functools.lru_cache(maxsize=32)
def _load_knowledge_yaml(relpath: str) -> dict[str, Any]:
    path = _KNOWLEDGE_DIR / relpath
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _find_node_attrs(data: dict[str, Any], node: str) -> Any | None:
    """Find the attribute section for a node in a component YAML."""
    key = f"{node}_attributes"
    if key in data:
        return data[key]
    if "attributes" in data and data.get("meta", {}).get("node") == node:
        return data["attributes"]
    return None


def _format_attrs(node: str, attrs_data: Any) -> str:
    """Format attribute data from YAML into readable repair reference text."""
    if isinstance(attrs_data, list):
        return f"<{node}> valid attributes: {', '.join(str(a) for a in attrs_data)}"
    if isinstance(attrs_data, dict):
        lines: list[str] = [f"<{node}> attributes:"]
        for attr, info in attrs_data.items():
            if isinstance(info, dict):
                parts: list[str] = []
                if "type" in info:
                    parts.append(str(info["type"]))
                if "values" in info:
                    parts.append(f"values: {info['values']}")
                if info.get("required"):
                    parts.append("REQUIRED")
                if "default" in info:
                    parts.append(f"default: {info['default']}")
                if "note" in info:
                    parts.append(str(info["note"]))
                lines.append(f"  {attr}: {' | '.join(parts)}")
            else:
                lines.append(f"  {attr}: {info}")
        return "\n".join(lines)
    return f"<{node}> attributes: {attrs_data}"


def _extract_nodes_from_errors(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> set[str]:
    """Extract POM node names mentioned in error messages."""
    nodes: set[str] = set()
    for issue in pre_issues:
        if issue.get("auto_fixed"):
            continue
        msg = issue.get("message", "")
        tag = _extract_tag_from_error(msg)
        if tag and tag[0].isupper():
            nodes.add(tag)
        _, node = _extract_attr_from_error(msg)
        if node and node[0].isupper():
            nodes.add(node)
    for diag in compile_diagnostics:
        msg = diag.get("message", "")
        tag = _extract_tag_from_error(msg)
        if tag and tag[0].isupper():
            nodes.add(tag)
        _, node = _extract_attr_from_error(msg)
        if node and node[0].isupper():
            nodes.add(node)
    return nodes


def select_repair_knowledge(
    pre_issues: list[dict[str, Any]],
    compile_diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select targeted knowledge slices based on error analysis.

    Instead of re-sending the full system prompt, this function loads ONLY
    the attribute docs, pitfalls, and examples for the nodes that actually
    had errors.

    Returns:
        knowledge_text: formatted attribute reference for error-relevant nodes
        example: verified structure example from the relevant component YAML
        nodes_involved: set of POM node names found in the errors
    """
    nodes = _extract_nodes_from_errors(pre_issues, compile_diagnostics)

    sections: list[str] = []
    loaded_files: set[str] = set()
    example_xml = ""

    for node in sorted(nodes):
        file_path = _NODE_TO_KNOWLEDGE_FILE.get(node)
        if not file_path:
            continue

        data = _load_knowledge_yaml(file_path)
        if not data:
            continue

        # Format this node's attributes
        attrs = _find_node_attrs(data, node)
        if attrs is not None:
            sections.append(_format_attrs(node, attrs))

        # Load component-level context once per file
        if file_path not in loaded_files:
            loaded_files.add(file_path)

            # Structure example — the verified correct syntax
            if data.get("structure") and not example_xml:
                example_xml = str(data["structure"]).strip()

            # Pitfalls — the most common mistakes for this component
            pitfalls = data.get("pitfalls", [])
            if pitfalls:
                comp_name = Path(file_path).stem
                sections.append(
                    f"{comp_name} pitfalls:\n"
                    + "\n".join(f"  - {p}" for p in pitfalls)
                )

            # Key notes
            notes = data.get("notes", [])
            if notes:
                sections.append(
                    "Notes:\n" + "\n".join(f"  - {n}" for n in notes)
                )

    # For layout/overflow errors, add common box-model reference
    has_layout_error = any(
        "OUT_OF_BOUNDS" in d.get("message", "").upper()
        or "OVERFLOW" in d.get("message", "").upper()
        for d in compile_diagnostics
    )
    if has_layout_error:
        common = _load_knowledge_yaml("core/attributes.yaml")
        ca = common.get("common_attributes", {})
        relevant = {k: ca[k] for k in ("w", "h", "grow", "padding", "margin", "gap")
                    if k in ca}
        if relevant:
            sections.append(_format_attrs("common box-model", relevant))

    return {
        "knowledge_text": "\n\n".join(sections),
        "example": example_xml,
        "nodes_involved": nodes,
    }
