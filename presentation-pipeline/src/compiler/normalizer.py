"""XML normalizer — strip fences, fix colors, remove br/hr, zero spacing.

Returns plain dicts instead of Pydantic models so the pipeline stays
JSON-serializable.
"""

from __future__ import annotations

import re
from typing import Any


FORBIDDEN_TAGS: set[str] = {
    "br", "div", "p", "span", "hr", "section", "header", "footer", "article",
    "main", "ul", "ol", "li", "table", "tr", "td", "th", "h1", "h2", "h3",
    "h4", "h5", "h6", "img", "a", "strong", "em", "blockquote", "small",
    "figure", "figcaption", "nav", "aside",
}
AUTO_REMOVABLE_TAGS: set[str] = {"br", "hr"}

FORBIDDEN_ATTRS: set[str] = {
    "style", "class", "classname", "onclick", "onchange",
    "width", "height", "font-size", "text-align", "background-color",
    "border-radius", "flex-direction", "flex", "justify", "align",
    "display", "float",
}

POM_TAGS: set[str] = {
    "Slide", "Theme", "Notes", "VStack", "HStack", "Layer", "Text", "Shape",
    "B", "I", "A", "U", "S", "Sub", "Sup", "Mark", "Span",
    "Ul", "Ol", "Li", "Table", "Col", "Tr", "Td",
    "Chart", "ChartSeries", "ChartDataPoint",
    "Image", "Icon", "Svg", "Line", "Arrow",
    "Timeline", "TimelineItem", "Matrix", "MatrixAxes", "MatrixQuadrants",
    "MatrixItem", "Tree", "TreeItem", "Flow", "FlowNode", "FlowConnection",
    "ProcessArrow", "ProcessArrowStep", "Pyramid", "PyramidLevel",
}
_POM_TAGS_LOWER: dict[str, str] = {t.lower(): t for t in POM_TAGS}

_FENCE_RE = re.compile(r"^\s*```(?:xml|XML)?\s*\n?|\n?```\s*$")
_TAG_RE = re.compile(r"</?\s*([A-Za-z][A-Za-z0-9]*)\b")
_ATTR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\"[^\"]*\"")
_HASH_COLOR_RE = re.compile(
    r"(?P<attr>[A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\"#(?P<hex>[0-9A-Fa-f]{3,8})\""
)
_ZERO_DIM_RE = re.compile(
    r"\b(?P<attr>w|h|minW|maxW|minH|maxH|fontSize)\s*=\s*\"(?P<val>0|-\d+(?:\.\d+)?|0*\.0+)\""
)
_ZERO_SPACING_RE = re.compile(r"\s+(?P<attr>gap|padding|margin)\s*=\s*\"0+\"")
_BR_RE = re.compile(r"<\s*/?\s*br\s*/?\s*>", re.IGNORECASE)
_HR_RE = re.compile(r"<\s*/?\s*hr\s*/?\s*>", re.IGNORECASE)
_SPACING_RE = re.compile(r'\bspacing\s*=\s*"([^"]*)"')
_FONTWEIGHT_RE = re.compile(r'\bfontWeight\s*=\s*"([^"]*)"')
_GRADIENT_RE = re.compile(r"[A-Za-z]*[Gg]radient\s*=\s*\"[^\"]*\"")
_COL_RE = re.compile(r"<Col\b[^>]*/?>", re.IGNORECASE)
_BORDER_ACCENT_RE = re.compile(
    r'(?<!\w)(border\.color)\s*=\s*"\$accent(?:Alt)?"'
)
_FONT_FLOOR = 14
_FONTSIZE_RE = re.compile(r'\bfontSize\s*=\s*"(\d+(?:\.\d+)?)"')

_PYRAMID_BLOCK_RE = re.compile(
    r"(<Pyramid\b[^>]*>)(.*?)(</Pyramid>)", re.DOTALL
)
_PYRAMID_LEVEL_RE = re.compile(r"<PyramidLevel\b[^>]*/>")
_PYRAMID_FONTSIZE_RE = re.compile(r'\bfontSize\s*=\s*"(\d+)"')
_PYRAMID_TEXTCOLOR_RE = re.compile(r'\btextColor\s*=\s*"([^"]*)"')
_PYRAMID_COLOR_RE = re.compile(r'\bcolor\s*=\s*"([^"]*)"')
_NOTES_RE = re.compile(r"<Notes\b[^>]*>(.*?)</Notes>", re.DOTALL)
_THEME_RE = re.compile(r"<Theme\b[^>]*?/>|<Theme\b[^>]*?>.*?</Theme>", re.DOTALL)

_OBJECT_ATTR_BASES: set[str] = {
    "border", "borderTop", "borderRight", "borderBottom", "borderLeft",
    "cellBorder", "glow", "shadow", "textShadow",
    "textGradient", "backgroundGradient", "borderGradient",
    "rotate", "rotation",
}
_UNIVERSAL_ATTRS: set[str] = {
    "w", "h", "grow", "padding", "margin", "gap",
    "alignItems", "justifyContent", "alignSelf", "flexWrap",
}
_OPEN_TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9]*)\b([^>]*?)/?>")
_ATTR_NAME_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\"")


def _perceived_brightness(hex_color: str) -> float:
    """Compute perceived brightness (0-1) using W3C formula."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) < 6:
        return 0.5
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return 0.5
    return (r * 299 + g * 587 + b * 114) / 255000


_PYRAMID_FONTSIZE_BY_LEVELS = {3: 16, 4: 15, 5: 14, 6: 14, 7: 14}


def _fix_pyramid_block(match: re.Match) -> tuple[str, list[dict[str, Any]]]:
    """Fix fontSize and textColor inside a single <Pyramid>...</Pyramid> block."""
    opening, body, closing = match.group(1), match.group(2), match.group(3)
    issues: list[dict[str, Any]] = []

    levels = list(_PYRAMID_LEVEL_RE.finditer(body))
    n_levels = len(levels)

    # --- Fix fontSize on the Pyramid element ---
    fs_match = _PYRAMID_FONTSIZE_RE.search(opening)
    current_fs = int(fs_match.group(1)) if fs_match else 14
    max_fs = _PYRAMID_FONTSIZE_BY_LEVELS.get(n_levels, 14)
    if current_fs > max_fs:
        if fs_match:
            opening = opening[:fs_match.start()] + f'fontSize="{max_fs}"' + opening[fs_match.end():]
        else:
            opening = opening.replace("<Pyramid", f'<Pyramid fontSize="{max_fs}"', 1)
        issues.append({
            "code": "PYRAMID_FONTSIZE_FIX",
            "message": f"Pyramid has {n_levels} levels: clamped fontSize from {current_fs} to {max_fs}.",
            "auto_fixed": True,
        })

    # --- Fix textColor on each PyramidLevel ---
    def _fix_level(level_match: re.Match) -> str:
        tag = level_match.group(0)
        color_m = _PYRAMID_COLOR_RE.search(tag)
        if not color_m:
            return tag
        fill = color_m.group(1)
        if fill.startswith("$"):
            return tag
        brightness = _perceived_brightness(fill)
        ideal = "FFFFFF" if brightness < 0.55 else "1E293B"
        tc_m = _PYRAMID_TEXTCOLOR_RE.search(tag)
        if tc_m:
            current_tc = tc_m.group(1)
            if current_tc.startswith("$"):
                return tag
            tc_brightness = _perceived_brightness(current_tc)
            contrast_ok = abs(brightness - tc_brightness) > 0.3
            if not contrast_ok:
                tag = tag[:tc_m.start()] + f'textColor="{ideal}"' + tag[tc_m.end():]
                issues.append({
                    "code": "PYRAMID_TEXTCOLOR_FIX",
                    "message": f"PyramidLevel color=\"{fill}\": textColor \"{current_tc}\" low contrast, fixed to \"{ideal}\".",
                    "auto_fixed": True,
                })
        else:
            if brightness >= 0.55:
                tag = tag.replace("/>", f' textColor="{ideal}" />')
                issues.append({
                    "code": "PYRAMID_TEXTCOLOR_FIX",
                    "message": f"PyramidLevel color=\"{fill}\": added textColor=\"{ideal}\" (light fill, default white invisible).",
                    "auto_fixed": True,
                })
        return tag

    body = _PYRAMID_LEVEL_RE.sub(_fix_level, body)
    return opening + body + closing, issues


def _fix_pyramids(xml: str, issues: list[dict[str, Any]]) -> str:
    """Find all Pyramid blocks and fix fontSize + textColor."""
    def _replacer(m: re.Match) -> str:
        fixed, new_issues = _fix_pyramid_block(m)
        issues.extend(new_issues)
        return fixed
    return _PYRAMID_BLOCK_RE.sub(_replacer, xml)


def _strip_fences(xml: str) -> tuple[str, bool]:
    stripped = xml.strip()
    if "```" not in stripped:
        return xml, False
    out = _FENCE_RE.sub("", stripped)
    out = out.replace("```xml", "").replace("```XML", "").replace("```", "")
    return out.strip(), True


def strip_theme(xml: str) -> str:
    """Remove every <Theme> element (self-closing, multiline, or paired) from xml."""
    return _THEME_RE.sub("", xml).strip()


def ensure_single_theme(xml: str, theme_element: str) -> str:
    """Guarantee exactly one top-level <Theme>.

    Strips any <Theme> the LLM emitted (anywhere in the doc) and prepends the
    canonical ``theme_element``. If ``theme_element`` is empty, a single
    previously-present <Theme> is restored at the top as a fallback.
    """
    existing = _THEME_RE.search(xml)
    body = strip_theme(xml)
    theme = (theme_element or (existing.group(0) if existing else "")).strip()
    if not theme:
        return body if body.endswith("\n") else body + "\n"
    return f"{theme}\n{body}".strip() + "\n"


def normalize_xml(raw_xml: str) -> dict[str, Any]:
    """Normalize raw LLM XML output: strip fences, fix colors, remove br/hr.

    Returns dict with keys: cleaned_xml, issues (list of {code, message, auto_fixed}),
    blocking (bool — True if any non-auto-fixed issue found).
    """
    issues: list[dict[str, Any]] = []
    xml = raw_xml

    xml, had_fence = _strip_fences(xml)
    if had_fence:
        issues.append({
            "code": "MARKDOWN_FENCE",
            "message": "Stripped ``` code fence around the XML.",
            "auto_fixed": True,
        })

    xml = _BR_RE.sub("", xml)
    xml = _HR_RE.sub("", xml)

    hash_hits = list(_HASH_COLOR_RE.finditer(xml))
    if hash_hits:
        xml = _HASH_COLOR_RE.sub(lambda m: f'{m.group("attr")}="{m.group("hex")}"', xml)
        issues.append({
            "code": "HASH_COLOR",
            "message": f"Stripped leading '#' from {len(hash_hits)} color value(s).",
            "auto_fixed": True,
        })

    spacing_hits = list(_SPACING_RE.finditer(xml))
    if spacing_hits:
        xml = _SPACING_RE.sub(r'gap="\1"', xml)
        issues.append({
            "code": "SPACING_TO_GAP",
            "message": f"Replaced {len(spacing_hits)} 'spacing' attribute(s) with 'gap'.",
            "auto_fixed": True,
        })

    fontweight_hits = list(_FONTWEIGHT_RE.finditer(xml))
    if fontweight_hits:
        xml = _FONTWEIGHT_RE.sub(r'bold="true"', xml)
        issues.append({
            "code": "FONTWEIGHT_TO_BOLD",
            "message": f"Replaced {len(fontweight_hits)} 'fontWeight' attribute(s) with 'bold=\"true\"'.",
            "auto_fixed": True,
        })

    border_accent_hits = list(_BORDER_ACCENT_RE.finditer(xml))
    if border_accent_hits:
        xml = _BORDER_ACCENT_RE.sub(r'border.color="$border"', xml)
        issues.append({
            "code": "BORDER_ACCENT_FIX",
            "message": f"Fixed {len(border_accent_hits)} border.color using accent token — replaced with $border.",
            "auto_fixed": True,
        })

    zero_spacing = list(_ZERO_SPACING_RE.finditer(xml))
    if zero_spacing:
        xml = _ZERO_SPACING_RE.sub("", xml)
        attrs = sorted({m.group("attr") for m in zero_spacing})
        issues.append({
            "code": "ZERO_SPACING",
            "message": "Removed {} (omit rather than 0).".format(
                ", ".join(f'{a}="0"' for a in attrs)
            ),
            "auto_fixed": True,
        })

    for m in _ZERO_DIM_RE.finditer(xml):
        issues.append({
            "code": "ZERO_DIM",
            "message": (
                f'{m.group("attr")}="{m.group("val")}" is not > 0. '
                "POM throws 'must be a finite positive EMU value'. Needs regeneration."
            ),
            "auto_fixed": False,
        })

    # ---- font-floor: raise any fontSize < 14 to 14 ----
    def _raise_font(m: re.Match) -> str:
        val = float(m.group(1))
        if val < _FONT_FLOOR:
            return f'fontSize="{_FONT_FLOOR}"'
        return m.group(0)

    font_before = xml
    xml = _FONTSIZE_RE.sub(_raise_font, xml)
    if xml != font_before:
        count = sum(
            1
            for a, b in zip(font_before.split("fontSize="), xml.split("fontSize="))
            if a != b
        )
        issues.append({
            "code": "FONT_FLOOR",
            "message": f"Raised {count} fontSize value(s) below {_FONT_FLOOR} to {_FONT_FLOOR}.",
            "auto_fixed": True,
        })

    if "<Pyramid" in xml:
        xml = _fix_pyramids(xml, issues)

    notes_match = _NOTES_RE.search(xml)
    speaker_notes = notes_match.group(1).strip() if notes_match else ""
    if notes_match:
        xml = _NOTES_RE.sub("", xml)

    had_theme = bool(_THEME_RE.search(xml))
    if had_theme:
        xml = strip_theme(xml)

    cleaned = xml.strip() + "\n"
    auto_fixed = sum(1 for i in issues if i["auto_fixed"])
    blocking = any(not i["auto_fixed"] for i in issues)

    return {
        "cleaned_xml": cleaned,
        "speaker_notes": speaker_notes,
        "had_theme": had_theme,
        "issues": issues,
        "auto_fixed": auto_fixed,
        "blocking": blocking,
    }


def pre_validate(raw_xml: str, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Full normalize + regex-based detection fallback for when parseXml is unavailable."""
    result = normalize_xml(raw_xml)
    xml = result["cleaned_xml"]
    issues = list(result["issues"])

    seen_html: set[str] = set()
    seen_miscased: set[tuple[str, str]] = set()
    seen_unknown: set[str] = set()
    for m in _TAG_RE.finditer(xml):
        name = m.group(1)
        low = name.lower()
        if name in POM_TAGS:
            continue
        if low in FORBIDDEN_TAGS:
            seen_html.add(low)
        elif low in _POM_TAGS_LOWER:
            seen_miscased.add((name, _POM_TAGS_LOWER[low]))
        else:
            seen_unknown.add(name)

    for tag in sorted(seen_html):
        issues.append({
            "code": "HTML_TAG",
            "message": (
                f"Found HTML tag <{tag}>. "
                + ("Removed." if tag in AUTO_REMOVABLE_TAGS
                   else "POM has no equivalent - needs regeneration.")
            ),
            "auto_fixed": tag in AUTO_REMOVABLE_TAGS,
        })
    for bad, good in sorted(seen_miscased):
        issues.append({
            "code": "MISCASED_TAG",
            "message": f"Tag <{bad}> is miscased - POM is case-sensitive. Use <{good}>.",
            "auto_fixed": False,
        })
    for tag in sorted(seen_unknown):
        issues.append({
            "code": "UNKNOWN_TAG",
            "message": f"Tag <{tag}> is not a POM node. POM will raise 'Unknown tag'.",
            "auto_fixed": False,
        })

    scrub = _GRADIENT_RE.sub("", xml)
    scrub = _COL_RE.sub("", scrub)
    seen_attrs: set[str] = set()
    for m in _ATTR_RE.finditer(scrub):
        attr = m.group(1)
        if attr.lower() in FORBIDDEN_ATTRS:
            seen_attrs.add(attr)
    for attr in sorted(seen_attrs):
        issues.append({
            "code": "HTML_ATTR",
            "message": (
                f'Found forbidden attribute "{attr}". '
                "Use POM attributes (w/h not width/height, fontSize not font-size)."
            ),
            "auto_fixed": False,
        })

    if contract is not None:
        allowed_nodes = set(contract.get("allowed_nodes", []))
        allowed_attrs = {
            node: set(attrs) for node, attrs in contract.get("allowed_attributes", {}).items()
        }
        for m in _OPEN_TAG_RE.finditer(_GRADIENT_RE.sub("", xml)):
            tag, blob = m.group(1), m.group(2)
            if tag in ("Theme", "Col"):
                continue
            if tag not in allowed_nodes:
                continue
            node_attrs = allowed_attrs.get(tag, set())
            for am in _ATTR_NAME_RE.finditer(blob):
                a = am.group(1)
                if a.lower() in FORBIDDEN_ATTRS:
                    continue
                base = a.split(".", 1)[0]
                if (a in node_attrs or base in node_attrs
                        or a in _UNIVERSAL_ATTRS or base in _UNIVERSAL_ATTRS
                        or base in _OBJECT_ATTR_BASES
                        or any(x.startswith(base + ".") for x in node_attrs)):
                    continue
                issues.append({
                    "code": "UNKNOWN_ATTR",
                    "message": f'<{tag}>: attribute "{a}" is not allowed on this node.',
                    "auto_fixed": False,
                })

    result["issues"] = issues
    result["auto_fixed"] = sum(1 for i in issues if i["auto_fixed"])
    result["blocking"] = any(not i["auto_fixed"] for i in issues)
    return result
