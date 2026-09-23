"""POM content model — which children each node may contain.

Single source of truth: the `children` field of every node in
knowledge/core/nodes.yaml. Used by the validator (blocking check that runs
BEFORE parseXml) and by the normalizer (safe flattening of text-only
containers). Never hardcode parent/child rules anywhere else.
"""

from __future__ import annotations

import functools
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

_NODES_YAML = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "nodes.yaml"
_SECTIONS = ("structural", "layout", "content", "phase_b", "phase_c", "phase_d", "post_mvp")

INLINE_TAGS: frozenset[str] = frozenset({"B", "I", "A", "U", "S", "Sub", "Sup", "Span", "Mark"})
# Containers whose body is text + inline tags only. POM either fails (Td) or
# silently strips (Li) any layout/leaf node placed inside them.
TEXT_ONLY: frozenset[str] = frozenset({"Text", "Li", "Td"})
# Nodes that may be dropped/unwrapped when flattening a text-only container.
# Anything else (Chart, Table, ...) is left for the blocking check + repair.
_FLATTEN_SAFE: frozenset[str] = frozenset({"HStack", "VStack", "Text", "Icon", "Shape"}) | INLINE_TAGS

_ANY = None  # sentinel: parent accepts any node


@functools.lru_cache(maxsize=1)
def content_model() -> dict[str, frozenset[str] | None]:
    """node -> allowed child tags (None = any node allowed)."""
    data = yaml.safe_load(_NODES_YAML.read_text(encoding="utf-8")) or {}
    model: dict[str, frozenset[str] | None] = {}
    for section in _SECTIONS:
        for name, meta in (data.get(section) or {}).items():
            if not isinstance(meta, dict):
                continue
            raw = meta.get("children")
            if raw is None or raw == "none":
                model[name] = frozenset()
            elif isinstance(raw, list):
                model[name] = frozenset(raw)
            elif isinstance(raw, str) and "any" in raw.lower():
                model[name] = _ANY
            elif isinstance(raw, str) and "svg" in raw.lower():
                model[name] = frozenset({"svg"})
    # Inline tags may nest other inline tags (e.g. <B><Span>..</Span></B>).
    for name in data.get("inline") or {}:
        model[name] = INLINE_TAGS
    return model


def _message(parent: str, child: str, allowed: frozenset[str]) -> str:
    if parent in TEXT_ONLY:
        alt = {"Td": "build the rows as <HStack> (Icon + Text + value) inside a VStack instead of a <Table>",
               "Li": "use <HStack> rows (Icon + Text) inside a VStack instead of <Ul>/<Ol>",
               "Text": "split into sibling nodes inside an <HStack>/<VStack>"}[parent]
        return (f"<{child}> is not allowed inside <{parent}>. <{parent}> holds text + inline tags only "
                f"({', '.join(sorted(INLINE_TAGS))}). Put plain text there; to show icons/layout, {alt}.")
    kids = ", ".join(sorted(allowed)) if allowed else "none (leaf node)"
    return f"<{child}> is not allowed inside <{parent}>. Allowed children of <{parent}>: {kids}."


def find_violations(xml: str) -> list[dict[str, Any]]:
    """Every parent/child pair that breaks nodes.yaml. One issue per distinct pair.

    Returns normalizer-style issues: {code, message, auto_fixed, parent, child}.
    XML that does not parse returns [] — parse errors are reported elsewhere.
    """
    try:
        root = ET.fromstring(f"<_root_>{xml}</_root_>")
    except ET.ParseError:
        return []
    model = content_model()
    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _walk(elem: ET.Element) -> None:
        if elem.tag == "Svg":  # raw <svg> subtree is not POM
            return
        allowed = model.get(elem.tag, _ANY)  # unknown tags: UNKNOWN_TAG check owns them
        for child in elem:
            if allowed is not _ANY and child.tag not in allowed and (elem.tag, child.tag) not in seen:
                seen.add((elem.tag, child.tag))
                issues.append({
                    "code": "INVALID_CHILD",
                    "message": _message(elem.tag, child.tag, allowed),
                    "auto_fixed": False,
                    "parent": elem.tag,
                    "child": child.tag,
                })
            _walk(child)

    for top in root:
        _walk(top)
    return issues


_TEXT_CONTAINER_RE = re.compile(r"(<(Td|Li)\b[^>]*>)(.*?)(</\2>)", re.DOTALL)
_INNER_TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9]*)\b")


def flatten_text_containers(xml: str) -> tuple[str, int]:
    """Collapse <Td>/<Li> bodies that contain layout/leaf nodes into plain text.

    Only rewrites when every nested tag is in _FLATTEN_SAFE (e.g. HStack of
    Icon + Text — the icon is dropped, the label kept). Returns (xml, count).
    """
    count = 0

    def _fix(m: re.Match) -> str:
        nonlocal count
        open_tag, _, inner, close_tag = m.groups()
        tags = set(_INNER_TAG_RE.findall(inner))
        if tags <= INLINE_TAGS or not tags <= _FLATTEN_SAFE:
            return m.group(0)
        try:
            frag = ET.fromstring(f"<_f_>{inner}</_f_>")
        except ET.ParseError:
            return m.group(0)
        text = " ".join(" ".join(frag.itertext()).split())
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        count += 1
        return f"{open_tag}{text}{close_tag}"

    return _TEXT_CONTAINER_RE.sub(_fix, xml), count


def nesting_compile_failure(issues: list[dict[str, Any]]) -> dict[str, Any] | None:
    """compile_result-shaped failure for INVALID_CHILD issues, or None if there are none.

    Callers use it to skip parseXml/buildPptx: for bad nesting the compiler's
    own error is misleading (Td) or absent (Li silently stripped).
    """
    nesting = [i for i in issues if i.get("code") == "INVALID_CHILD"]
    if not nesting:
        return None
    return {
        "ok": False, "pptx_path": None,
        "diagnostics": [{"type": i["code"], "message": i["message"]} for i in nesting],
        "warnings": [], "retryable": True,
    }
