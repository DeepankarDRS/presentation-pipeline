"""Icon names — keep every <Icon name> inside POM's real icon set.

Source of truth: knowledge/core/icon-names.txt, exported from the installed
compiler by scripts/export_icon_names.py. An unknown name fails parseXml and
would cost a full LLM retry, so the normalizer fixes it deterministically:

  1. exact match                      -> keep
  2. same name in another spelling    -> rewrite ("ShoppingBag", "shopping_bag" -> "shopping-bag")
  3. anything else (incl. no name)    -> remove the <Icon> element

No fuzzy matching: a near-miss guess can render the wrong symbol, which is
worse than no icon.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

_ICON_NAMES_TXT = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "icon-names.txt"

_ICON_RE = re.compile(r"<Icon\b[^>]*?(?:/>|>\s*</Icon>)", re.DOTALL)
_NAME_RE = re.compile(r'(\bname\s*=\s*")([^"]*)(")')
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEP_RE = re.compile(r"[\s_]+")


@functools.lru_cache(maxsize=1)
def valid_icon_names() -> frozenset[str]:
    lines = _ICON_NAMES_TXT.read_text(encoding="utf-8").splitlines()
    return frozenset(n.strip() for n in lines if n.strip() and not n.startswith("#"))


def canonical_icon_name(name: str) -> str:
    """Lucide slug spelling: kebab-case, lowercase."""
    return _SEP_RE.sub("-", _CAMEL_RE.sub("-", name.strip())).lower()


def fix_icon_names(xml: str) -> tuple[str, list[tuple[str, str]], list[str]]:
    """Returns (xml, renamed [(old, new)], removed [name]). Other markup is untouched."""
    valid = valid_icon_names()
    renamed: list[tuple[str, str]] = []
    removed: list[str] = []

    def _fix(m: re.Match) -> str:
        tag = m.group(0)
        nm = _NAME_RE.search(tag)
        name = nm.group(2) if nm else ""
        if name in valid:
            return tag
        slug = canonical_icon_name(name)
        if slug in valid:
            renamed.append((name, slug))
            return tag[:nm.start(2)] + slug + tag[nm.end(2):]
        removed.append(name or "(no name)")
        return ""

    return _ICON_RE.sub(_fix, xml), renamed, removed
