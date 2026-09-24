"""XML normalizer — strip fences, fix colors, remove br/hr, zero spacing.

Returns plain dicts instead of Pydantic models so the pipeline stays
JSON-serializable.
"""

from __future__ import annotations

import re
from typing import Any

from src.compiler.content_model import find_violations, flatten_text_containers
from src.compiler.icons import fix_icon_names


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
# A zero stroke (line/outline/border width 0) fails buildPptx ("outline.width must
# be a finite positive EMU value"). Omitting the stroke is how POM says "none".
_ZERO_STROKE_RE = re.compile(
    r'\b(?P<prefix>line|outline|border|borderTop|borderRight|borderBottom|borderLeft)'
    r'\.(?:width|size)\s*=\s*"(?:0+(?:\.0+)?|\.0+)"'
)
_ELEMENT_TAG_RE = re.compile(r"<[A-Za-z][^<>]*>")
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
    "w", "h", "grow", "minW", "maxW", "minH", "maxH", "padding", "margin", "gap",
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


def _strip_zero_strokes(xml: str) -> tuple[str, list[str]]:
    """Drop every zero-width stroke group (e.g. border.width="0" + border.color) per element.

    The whole group goes, not just the width: a leftover border.color could get a
    default width and draw the border the zero was meant to hide.
    """
    removed: list[str] = []

    def _fix(m: re.Match) -> str:
        tag = m.group(0)
        for prefix in sorted({z.group("prefix") for z in _ZERO_STROKE_RE.finditer(tag)}):
            tag = re.sub(rf'\s+{prefix}(?:\.[A-Za-z]+)?\s*=\s*"[^"]*"', "", tag)
            removed.append(prefix)
        return tag

    return _ELEMENT_TAG_RE.sub(_fix, xml), removed


# ── Deterministic structure fixes (each reproduced against POM 10.3.0, 2026-09-24) ──────────
# Every one of these cost a repair retry (or a lost slide) in the Phase 0 baseline.

_BARE_AMP_RE = re.compile(r"&(?!(?:[A-Za-z]+|#\d+|#x[0-9A-Fa-f]+);)")
# An opening tag whose attribute values may hold "<" / ">": the generator writes
# title="<B>Doubled down</B> ..." — POM accepts it and PowerPoint shows the tags as text.
_QUOTED_TAG_RE = re.compile(r'<[A-Za-z][\w.]*(?:\s+[\w.:-]+\s*=\s*"[^"]*")*\s*/?>')
_ATTR_VALUE_RE = re.compile(r'(=\s*")([^"]*)(")')
_MARKUP_RE = re.compile(r"</?[A-Za-z][^<>]*>")


def _strip_attr_markup(xml: str) -> tuple[str, int]:
    """Drop markup tags inside attribute values and escape any other bare '<' (strict XML)."""
    count = 0

    def _value(m: re.Match) -> str:
        nonlocal count
        if "<" not in m.group(2):
            return m.group(0)
        count += 1
        return m.group(1) + _MARKUP_RE.sub("", m.group(2)).replace("<", "&lt;") + m.group(3)

    return _QUOTED_TAG_RE.sub(lambda m: _ATTR_VALUE_RE.sub(_value, m.group(0)), xml), count
_BORDER_SHORTHAND_RE = re.compile(r'\sborder\.width\s*=\s*"((?:\s*\d+(?:\.\d+)?(?:px)?){2,4})\s*"')
_BORDER_COLOR_RE = re.compile(r'\sborder\.color\s*=\s*"([^"]*)"')
# Truly empty only: whitespace-only Td/Text/Li compile, and "<Td> </Td>" must stay a fixed point
# (the deck assembler normalizes every slide a second time).
_EMPTY_TD_RE = re.compile(r"<Td\b([^>]*?)(?:/>|></Td>)")
_EMPTY_TEXT_RE = re.compile(r"<Text\b[^>]*?(?:/>|></Text>)")
_EMPTY_LI_RE = re.compile(r"<Li\b[^>]*?(?:/>|></Li>)")
_EMPTY_LIST_RE = re.compile(r"<(Ul|Ol)\b[^>]*>\s*</\1>")
_TABLE_RE = re.compile(r"<Table\b[^>]*>.*?</Table>", re.DOTALL)
_TR_RE = re.compile(r"<Tr\b[^>]*>(.*?)</Tr>", re.DOTALL)
_TD_OPEN_RE = re.compile(r"<Td\b([^>]*)>|<Td\b([^>]*)/>")
_COLSPAN_RE = re.compile(r'\bcolspan\s*=\s*"(\d+)"')
_SIDES = ("Top", "Right", "Bottom", "Left")


def _drop_attr_conflicts(xml: str) -> tuple[str, list[str]]:
    """`shadow="…"` next to `shadow.blur="…"` is a POM PARSE_ERROR ("conflicts with dot-notation").
    The dotted form carries the detail, so the bare attribute is dropped."""
    dropped: list[str] = []

    def _fix(m: re.Match) -> str:
        tag = m.group(0)
        for base in _OBJECT_ATTR_BASES:
            if re.search(rf'\s{base}\s*=\s*"', tag) and re.search(rf'\s{base}\.[A-Za-z]+\s*=', tag):
                tag = re.sub(rf'\s{base}\s*=\s*"[^"]*"', "", tag)
                dropped.append(base)
        return tag

    return _ELEMENT_TAG_RE.sub(_fix, xml), dropped


def _expand_border_shorthand(xml: str) -> tuple[str, int]:
    """CSS-style `border.width="0 0 0 5"` (top right bottom left) is not a number to POM; write
    one `border<Side>.width` (+ the border colour) per non-zero side instead."""
    count = 0

    def _fix(m: re.Match) -> str:
        nonlocal count
        tag = m.group(0)
        short = _BORDER_SHORTHAND_RE.search(tag)
        if not short:
            return tag
        vals = [v.removesuffix("px") for v in short.group(1).split()]
        top, right, bottom, left = {2: vals * 2, 3: vals + vals[1:2], 4: vals}[len(vals)]
        color = _BORDER_COLOR_RE.search(tag)
        sides = ""
        for side, width in zip(_SIDES, (top, right, bottom, left)):
            if float(width) > 0:
                sides += f' border{side}.width="{width}"'
                if color:
                    sides += f' border{side}.color="{color.group(1)}"'
        tag = _BORDER_SHORTHAND_RE.sub("", tag)
        tag = _BORDER_COLOR_RE.sub("", tag)
        count += 1
        end = -2 if tag.endswith("/>") else -1
        return tag[:end].rstrip() + sides + tag[end:]

    return _ELEMENT_TAG_RE.sub(_fix, xml), count


def _pad_table_columns(xml: str) -> tuple[str, int]:
    """A row with more cells (colspan counted) than declared <Col>s fails buildPptx ("each row must
    contain one cell per grid column"). Add width-less <Col />s — POM shares the rest of the width."""
    count = 0

    def _fix(m: re.Match) -> str:
        nonlocal count
        table = m.group(0)
        cols = len(_COL_RE.findall(table))
        if not cols:
            return table
        cells = max((sum(int((_COLSPAN_RE.search(a or b or "") or [0, 1])[1])
                         for a, b in _TD_OPEN_RE.findall(row))
                     for row in _TR_RE.findall(table)), default=0)
        if cells <= cols:
            return table
        count += 1
        last_col = list(_COL_RE.finditer(table))[-1]
        return table[:last_col.end()] + "<Col />" * (cells - cols) + table[last_col.end():]

    return _TABLE_RE.sub(_fix, xml), count


def _fix_structure(xml: str, issues: list[dict[str, Any]], stage: str) -> str:
    """Deterministic fixes for inputs POM rejects. stage="early" runs before the Td/Li
    flattener (which needs parseable text), stage="late" after it (it can leave empty cells)."""

    def note(code: str, message: str) -> None:
        issues.append({"code": code, "message": message, "auto_fixed": True})

    if stage == "early":
        xml, n = _BARE_AMP_RE.subn("&amp;", xml)
        if n:
            note("AMPERSAND_ESCAPED", f"Escaped {n} bare '&' as '&amp;' (strict XML parsers reject it).")
        xml, n = _strip_attr_markup(xml)
        if n:
            note("ATTR_MARKUP_STRIPPED", f"Removed markup such as <B> from {n} attribute value(s) "
                 "(shown as literal text on the slide).")
        xml, dropped = _drop_attr_conflicts(xml)
        if dropped:
            note("ATTR_CONFLICT_FIXED", "Dropped bare attribute(s) that conflict with their dot-notation "
                 f"form: {', '.join(sorted(set(dropped)))}.")
        xml, n = _expand_border_shorthand(xml)
        if n:
            note("BORDER_SHORTHAND_EXPANDED", f'Rewrote {n} CSS-style border.width="t r b l" as per-side borders.')
        return xml

    xml, n = _EMPTY_TD_RE.subn(r"<Td\1> </Td>", xml)
    if n:
        note("EMPTY_CELL_FILLED", f"Gave {n} empty <Td> a blank text (POM rejects empty cells).")
    xml, n = _EMPTY_TEXT_RE.subn("", xml)
    if n:
        note("EMPTY_TEXT_REMOVED", f"Removed {n} empty <Text> (POM requires text).")
    xml, n = _EMPTY_LI_RE.subn("", xml)
    xml, n_lists = _EMPTY_LIST_RE.subn("", xml)
    if n:
        note("EMPTY_ITEM_REMOVED", f"Removed {n} empty <Li>" + (f" and {n_lists} emptied list(s)." if n_lists else "."))
    xml, n = _pad_table_columns(xml)
    if n:
        note("TABLE_COLS_PADDED", f"Added <Col /> to {n} table(s) whose rows had more cells than columns.")
    return xml


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

    Also auto-fixes safe nesting slips (Td/Li bodies) and unknown icon names, and
    reports remaining nodes.yaml content-model violations as INVALID_CHILD.

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
    xml = _fix_structure(xml, issues, "early")

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

    xml, zero_strokes = _strip_zero_strokes(xml)
    if zero_strokes:
        issues.append({
            "code": "ZERO_STROKE_REMOVED",
            "message": "Removed zero-width stroke(s): {} (omit the stroke instead of width 0).".format(
                ", ".join(sorted(set(zero_strokes)))
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

    xml, flattened = flatten_text_containers(xml)
    if flattened:
        issues.append({
            "code": "TEXT_CONTAINER_FLATTENED",
            "message": (
                f"Flattened {flattened} <Td>/<Li> that contained layout nodes (e.g. HStack + Icon) "
                "to plain text — Td/Li hold text + inline tags only."
            ),
            "auto_fixed": True,
        })

    xml = _fix_structure(xml, issues, "late")

    xml, icons_renamed, icons_removed = fix_icon_names(xml)
    if icons_renamed:
        issues.append({
            "code": "ICON_NAME_NORMALIZED",
            "message": "Rewrote icon name(s) to POM spelling: "
                       + ", ".join(f"{a} -> {b}" for a, b in icons_renamed) + ".",
            "auto_fixed": True,
        })
    if icons_removed:
        issues.append({
            "code": "UNKNOWN_ICON_REMOVED",
            "message": "Removed <Icon> with name(s) not in POM's icon set: "
                       + ", ".join(icons_removed) + ".",
            "auto_fixed": True,
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

    # Content model last, on the fully fixed XML: whatever is still mis-nested blocks.
    issues.extend(find_violations(xml))

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
