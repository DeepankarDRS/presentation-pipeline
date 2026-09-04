"""XML sanitizer — runs on the raw LLM response before it reaches the compiler.

Two jobs:
  1. Normalize trivially (strip markdown fences, strip a leading '#' from plain
     color attrs, drop <br>/</br>, drop gap="0"/padding="0").
  2. Detect contamination the compiler will NOT catch, or would only catch after
     a wasted compile round-trip: stray HTML closing tags like </br> are silently
     dropped by POM's parser; a leading '#' on a color is tolerated; and an
     invented attribute (e.g. uppercase="true" on <Text>) is a retryable compile
     error we would rather catch here so the repair prompt fires immediately.

Rules sourced from pom-knowledge/core/validation.yaml. When a GenerationContract
is passed, `pre_validate` also checks every attribute against that contract's
per-node allow-list.
"""

from __future__ import annotations

import re

from models import GenerationContract, PreValidationIssue, PreValidationResult

# ── Rule tables (keep in sync with core/validation.yaml) ─────────────────────
FORBIDDEN_TAGS: set[str] = {
    "br", "div", "p", "span", "hr", "section", "header", "footer", "article",
    "main", "ul", "ol", "li", "table", "tr", "td", "th", "h1", "h2", "h3",
    "h4", "h5", "h6", "img", "a", "strong", "em", "blockquote", "small",
    "figure", "figcaption", "nav", "aside",
}
# Tags whose removal does not change the tree — safe to auto-fix.
AUTO_REMOVABLE_TAGS: set[str] = {"br", "hr"}

FORBIDDEN_ATTRS: set[str] = {
    "style", "class", "classname", "onclick", "onchange",
    "width", "height", "font-size", "text-align", "background-color",
    "border-radius", "flex-direction", "flex", "justify", "align",
    "display", "float",
}
# `id` and `src` are valid POM attributes (Layer children, Image, etc.).

_FENCE_RE = re.compile(r"^\s*```(?:xml|XML)?\s*\n?|\n?```\s*$")
_TAG_RE = re.compile(r"</?\s*([A-Za-z][A-Za-z0-9]*)\b")
_ATTR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\"[^\"]*\"")
# color-ish attribute carrying a leading '#': color="#FFF" backgroundColor="#0F172A"
# Any attribute whose value is exactly '#' + 3-8 hex digits (covers color,
# backgroundColor, Theme token names like accent="#3B82F6", border.color, ...).
# Gradient strings never match: they contain spaces/commas inside the quotes.
_HASH_COLOR_RE = re.compile(
    r"(?P<attr>[A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\"#(?P<hex>[0-9A-Fa-f]{3,8})\""
)
_ZERO_DIM_RE = re.compile(
    r"\b(?P<attr>w|h|minW|maxW|minH|maxH|fontSize)\s*=\s*\"(?P<val>0|-\d+(?:\.\d+)?|0*\.0+)\""
)
_ZERO_SPACING_RE = re.compile(r"\s+(?P<attr>gap|padding|margin)\s*=\s*\"0+\"")
_BR_RE = re.compile(r"<\s*/?\s*br\s*/?\s*>", re.IGNORECASE)
_HR_RE = re.compile(r"<\s*/?\s*hr\s*/?\s*>", re.IGNORECASE)
_GRADIENT_RE = re.compile(r"[A-Za-z]*[Gg]radient\s*=\s*\"[^\"]*\"")
# <Col width="..."> is the one place `width` is a valid POM attribute.
_COL_RE = re.compile(r"<Col\b[^>]*/?>", re.IGNORECASE)

# Every real POM tag (plan.md s12). Used for case-sensitivity checks and to
# distinguish "real POM tag" from "HTML leak / invented tag".
POM_TAGS: set[str] = {
    "Slide", "Theme", "VStack", "HStack", "Layer", "Text", "Shape",
    "B", "I", "A", "U", "S", "Sub", "Sup", "Mark", "Span",
    "Ul", "Ol", "Li", "Table", "Col", "Tr", "Td",
    "Chart", "ChartSeries", "ChartDataPoint",
    "Image", "Icon", "Svg", "Line", "Arrow",
    "Timeline", "TimelineItem", "Matrix", "MatrixAxes", "MatrixQuadrants",
    "MatrixItem", "Tree", "TreeItem", "Flow", "FlowNode", "FlowConnection",
    "ProcessArrow", "ProcessArrowStep", "Pyramid", "PyramidLevel",
}
_POM_TAGS_LOWER: dict[str, str] = {t.lower(): t for t in POM_TAGS}

# Kept for backward compat — identical to POM_TAGS now.
ALL_POM_TAGS: set[str] = POM_TAGS


# Attributes legal on any layout/content node regardless of the contract
# (the selective system prompt states this explicitly).
_UNIVERSAL_ATTRS: set[str] = {
    "w", "h", "grow", "padding", "margin", "gap",
    "alignItems", "justifyContent", "alignSelf", "flexWrap",
}
# Base names of POM's dotted object-attributes (border.color, glow.size, ...).
# A `foo.bar` attribute is accepted when `foo` is one of these.
_OBJECT_ATTR_BASES: set[str] = {
    "border", "borderTop", "borderRight", "borderBottom", "borderLeft",
    "cellBorder", "glow", "shadow", "textShadow",
    "textGradient", "backgroundGradient", "borderGradient",
    "rotate", "rotation",
}
# Per-tag attribute scan: <Tag ...>. Group 1 = tag, group 2 = the attr blob.
_OPEN_TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9]*)\b([^>]*?)/?>")
_ATTR_NAME_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\"")


def _check_contract_attributes(
    xml: str, contract: GenerationContract
) -> list[PreValidationIssue]:
    """Flag attributes the contract's per-node allow-list does not permit.

    Conservative by design: only nodes that appear in the contract's allow-list
    are checked (unknown nodes are already reported as UNKNOWN_TAG), and dotted
    object-attributes and the universal box attrs are always allowed. The point
    is to catch flat hallucinated attributes like uppercase="true" before they
    reach the compiler as a retryable UNKNOWN_ATTRIBUTE.
    """
    allowed_nodes = set(contract.allowed_nodes)
    allowed_attrs = {
        node: set(attrs) for node, attrs in contract.allowed_attributes.items()
    }
    forbidden = FORBIDDEN_ATTRS  # reported separately as HTML_ATTR

    seen: set[tuple[str, str]] = set()
    issues: list[PreValidationIssue] = []
    for m in _OPEN_TAG_RE.finditer(xml):
        tag, blob = m.group(1), m.group(2)
        if tag in ("Theme", "Col"):        # arbitrary token names / width exception
            continue
        if tag not in allowed_nodes:       # UNKNOWN_TAG covers this node already
            continue
        node_attrs = allowed_attrs.get(tag, set())
        for am in _ATTR_NAME_RE.finditer(blob):
            attr = am.group(1)
            low = attr.lower()
            if low in forbidden:
                continue
            base = attr.split(".", 1)[0]
            if (
                attr in node_attrs
                or base in node_attrs
                or attr in _UNIVERSAL_ATTRS
                or base in _UNIVERSAL_ATTRS
                or base in _OBJECT_ATTR_BASES
                or any(a.startswith(base + ".") for a in node_attrs)
            ):
                continue
            key = (tag, attr)
            if key in seen:
                continue
            seen.add(key)
            issues.append(PreValidationIssue(
                code="UNKNOWN_ATTR",
                message=(
                    f'<{tag}>: attribute "{attr}" is not allowed on this node. '
                    "POM will raise 'Unknown attribute' at compile. Remove it or "
                    "use a real POM attribute. Needs regeneration."
                ),
                auto_fixed=False,
            ))
    return issues


def _strip_fences(xml: str) -> tuple[str, bool]:
    stripped = xml.strip()
    if "```" not in stripped:
        return xml, False
    out = _FENCE_RE.sub("", stripped)
    out = out.replace("```xml", "").replace("```XML", "").replace("```", "")
    return out.strip(), True


def normalize_xml(raw_xml: str) -> PreValidationResult:
    """Normalization-only pass: strip fences, # colors, br/hr, zero spacing.

    Always runs as the first pipeline step. Does NOT detect structural errors
    (unknown tags, forbidden attrs) — those are caught by parseXml when
    available, or by the full pre_validate() fallback.
    """
    result = PreValidationResult(raw_xml=raw_xml, cleaned_xml=raw_xml)
    issues: list[PreValidationIssue] = []
    xml = raw_xml

    # 1. Markdown fences
    xml, had_fence = _strip_fences(xml)
    if had_fence:
        result.markdown_fences_found = True
        issues.append(PreValidationIssue(
            code="MARKDOWN_FENCE", message="Stripped ``` code fence around the XML.",
            auto_fixed=True,
        ))

    # 2. Remove <br>/<hr> (always safe)
    xml = _BR_RE.sub("", xml)
    xml = _HR_RE.sub("", xml)

    # 3. Strip '#' prefix from plain color attributes
    hash_hits = list(_HASH_COLOR_RE.finditer(xml))
    if hash_hits:
        for m in hash_hits:
            result.hash_colors_found.append(f'{m.group("attr")}="#{m.group("hex")}"')
        xml = _HASH_COLOR_RE.sub(lambda m: f'{m.group("attr")}="{m.group("hex")}"', xml)
        issues.append(PreValidationIssue(
            code="HASH_COLOR",
            message=f"Stripped leading '#' from {len(hash_hits)} color value(s).",
            auto_fixed=True,
        ))

    # 4. Remove gap/padding/margin = "0" (valid but noisy)
    zero_spacing = list(_ZERO_SPACING_RE.finditer(xml))
    if zero_spacing:
        attrs = sorted({m.group("attr") for m in zero_spacing})
        xml = _ZERO_SPACING_RE.sub("", xml)
        removed = ", ".join('{}="0"'.format(a) for a in attrs)
        issues.append(PreValidationIssue(
            code="ZERO_SPACING",
            message="Removed {} (omit rather than 0).".format(removed),
            auto_fixed=True,
        ))

    # 5. Detect zero/negative dimensions (render error parseXml won't catch)
    for m in _ZERO_DIM_RE.finditer(xml):
        token = f'{m.group("attr")}="{m.group("val")}"'
        result.zero_values_found.append(token)
        issues.append(PreValidationIssue(
            code="ZERO_DIM",
            message=(
                f"Dimension {token} is not > 0. POM throws "
                '"must be a finite positive EMU value" at render. Needs regeneration.'
            ),
            auto_fixed=False,
        ))

    result.cleaned_xml = xml.strip() + "\n"
    result.issues = issues
    return result


def pre_validate(
    raw_xml: str, contract: GenerationContract | None = None
) -> PreValidationResult:
    """Full sanitize + detect. Used as fallback when parseXml is unavailable.

    Calls normalize_xml() first, then runs regex-based detection for HTML tags,
    forbidden attributes, unknown tags, and contract-aware attribute checks.
    When parseXml is available, use normalize_xml() instead and let parseXml
    handle detection.
    """
    result = normalize_xml(raw_xml)
    xml = result.cleaned_xml
    issues = list(result.issues)

    # ── Detection (fallback for when parseXml is unavailable) ──────────────

    # Bad tags: HTML leaks, miscased POM tags, unknown tags
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
        result.html_tags_found.append(tag)
        auto = tag in AUTO_REMOVABLE_TAGS
        issues.append(PreValidationIssue(
            code="HTML_TAG",
            message=(
                f"Found HTML tag <{tag}>. "
                + ("Removed." if auto else "POM has no equivalent - needs regeneration "
                   "(<div>->VStack/HStack, <p>->Text, <span>-><Span>, <ul>-><Ul>).")
            ),
            auto_fixed=auto,
        ))
    for bad, good in sorted(seen_miscased):
        result.html_tags_found.append(bad)
        issues.append(PreValidationIssue(
            code="MISCASED_TAG",
            message=f"Tag <{bad}> is miscased - POM is case-sensitive. Use <{good}>. Needs regeneration.",
            auto_fixed=False,
        ))
    for tag in sorted(seen_unknown):
        result.html_tags_found.append(tag)
        if tag in ALL_POM_TAGS:
            msg = (f"Tag <{tag}> is a real POM node but outside this slide's "
                   "allowed set. Rebuild with the allowed nodes only.")
        else:
            msg = (f"Tag <{tag}> is not a POM node. POM will raise "
                   "'Unknown tag'. Needs regeneration.")
        issues.append(PreValidationIssue(
            code="UNKNOWN_TAG", message=msg, auto_fixed=False,
        ))

    # Forbidden attributes
    scrub = _GRADIENT_RE.sub("", xml)
    scrub = _COL_RE.sub("", scrub)
    seen_attrs: set[str] = set()
    for m in _ATTR_RE.finditer(scrub):
        attr = m.group(1)
        if attr.lower() in FORBIDDEN_ATTRS:
            seen_attrs.add(attr)
    for attr in sorted(seen_attrs):
        result.html_attributes_found.append(attr)
        issues.append(PreValidationIssue(
            code="HTML_ATTR",
            message=(
                f'Found forbidden attribute "{attr}". '
                "Use POM attributes (w/h not width/height, fontSize not font-size, "
                "explicit attrs not style/class). Needs regeneration."
            ),
            auto_fixed=False,
        ))

    # Contract-aware attribute checking (non-blocking warning)
    if contract is not None:
        for issue in _check_contract_attributes(_GRADIENT_RE.sub("", xml), contract):
            result.html_attributes_found.append(issue.message.split('"')[1])
            issue.auto_fixed = True
            issues.append(issue)

    result.issues = issues
    return result
