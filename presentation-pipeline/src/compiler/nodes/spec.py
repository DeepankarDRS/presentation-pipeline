"""The ref-node tags and variants, read from src/knowledge/core/block-variants.yaml (§3.1, §3.3)."""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml

_FILE = Path(__file__).resolve().parents[2] / "knowledge" / "core" / "block-variants.yaml"

DERIVED_TAGS = {"KpiRow", "CardGrid", "Callout", "SlideHeader"}

# plan kinds the LLM may not place by ref: the header is still written by the LLM in 1a,
# a layer has no content shape (§3.1)
NO_REF_KINDS = {"title", "layer"}

# §3.2: layout attributes every ref tag may carry (POM's common sizing attributes)
LAYOUT_ATTRS = {"ref", "variant", "w", "h", "grow", "alignSelf", "minW", "maxW", "minH", "maxH"}

# §3.2: a native tag's own presentation attributes (nodes.yaml), content attributes left out:
# code writes those (Chart chartType / title, every per-item attribute)
NATIVE_ATTRS: dict[str, set[str]] = {
    "Text": {"fontSize", "color", "textAlign", "bold", "italic", "underline", "fontFamily",
             "lineHeight", "letterSpacing"},
    "Ul": {"fontSize", "color", "textAlign", "bold", "italic", "fontFamily", "lineHeight"},
    "Table": {"defaultRowHeight", "cellBorder.color", "cellBorder.width", "cellBorder.dashType"},
    "Chart": {"showLegend", "chartColors"},
    "Timeline": {"direction", "dateColor", "titleColor", "connectorColor", "useColorForDate", "fontFamily"},
    "ProcessArrow": {"direction", "itemWidth", "itemHeight", "gap", "fontSize", "bold", "fontFamily"},
    "Flow": {"direction", "nodeWidth", "nodeHeight", "nodeGap", "connectorStyle.color", "connectorStyle.width"},
    "Pyramid": {"direction", "fontSize", "bold", "fontFamily"},
    "Tree": {"layout", "nodeShape", "textColor", "nodeWidth", "nodeHeight", "levelGap", "siblingGap",
             "connectorStyle.color", "connectorStyle.width"},
    "Matrix": {"axisLabelColor", "quadrantLabelColor", "itemLabelColor"},
}
CONTENT_ATTRS = {"Chart": {"chartType", "title", "showTitle"}}


@functools.lru_cache(maxsize=1)
def blocks() -> dict[str, Any]:
    return yaml.safe_load(_FILE.read_text(encoding="utf-8"))["blocks"]


def _plan_kinds(b: dict) -> list[str]:
    k = b["plan_kind"]
    return k if isinstance(k, list) else [k]


def block_for(kind: str, tag: str, card_layout: str | None = None) -> tuple[str, dict] | None:
    """(block name, block) the tag draws for this plan kind; None when the tag does not take it."""
    for name, b in blocks().items():
        if b["tag"] != tag or kind not in _plan_kinds(b):
            continue
        if "layouts" in b and (card_layout or "grid") not in b["layouts"]:
            continue
        return name, b
    return None


def tags_for(kind: str) -> list[str]:
    """Every tag that takes the plan kind; the first is the default (narrative: Callout, then Text)."""
    out = [b["tag"] for b in blocks().values() if kind in _plan_kinds(b)]
    return list(dict.fromkeys(out))


def variants(kind: str, tag: str, card_layout: str | None = None) -> dict[str, dict]:
    hit = block_for(kind, tag, card_layout)
    return dict(hit[1].get("variants") or {}) if hit else {}


def family(tag: str) -> str:
    return "derived" if tag in DERIVED_TAGS else "native"


# ── `requires` checks (block-variants.yaml header) ───────────────────────────

_NUMBERED = re.compile(r"^\s*(?:\d+[.)]|phase\s+\d+|step\s+\d+|0\d)\b", re.I)
_EMPHASIS_WORDS = ("inverted", "featured", "highlight", "dark", "emphasis", "singled", "hero")


def items(comp: dict) -> list[str]:
    """The item labels of a component, in plan order (used for counts, emphasis, bypass)."""
    cd = comp.get("content_data") or {}
    k = comp.get("kind")
    if k == "kpi_row":
        return [str(v) for v in cd.get("kpi_labels") or []]
    if k == "card_grid":
        return [str(c.get("title") or "") for c in cd.get("cards") or []]
    if k == "table":
        return [str(r[0]) for r in cd.get("table_rows") or [] if r]
    if k == "chart":
        return [str(v) for v in cd.get("chart_labels") or []]
    if k == "bullet_list":
        return [str(v) for v in cd.get("bullets") or []]
    if k == "timeline":
        return [str(i.get("label") or i.get("title") or "") for i in cd.get("timeline_items") or []]
    if k == "process_arrow":
        return [str(v) for v in cd.get("process_steps") or []]
    if k == "flow":
        return [str(v) for v in cd.get("flow_steps") or []]
    if k == "pyramid":
        return [str(v) for v in cd.get("pyramid_levels") or []]
    if k == "tree":
        out: list[str] = []

        def walk(nodes):
            for n in nodes or []:
                out.append(str(n.get("label") or ""))
                walk(n.get("children"))
        walk(cd.get("tree_nodes"))
        return out
    if k == "matrix":
        return [str(i.get("label") or "") for i in cd.get("matrix_items") or []]
    if k in ("narrative", "caption"):
        t = str(cd.get("text") or "").strip()
        return [t] if t else []
    return []


def singled_out(comp: dict) -> str | None:
    """The one item the design hint names next to an emphasis word, else None."""
    hint = str(comp.get("design_hint") or "").lower()
    if not any(w in hint for w in _EMPHASIS_WORDS):
        return None
    named = [i for i in items(comp) if i and i.lower() in hint]
    return named[0] if len(named) == 1 else None


def check(name: str, comp: dict) -> bool:
    cd = comp.get("content_data") or {}
    n = len(items(comp))
    if name == "count_eq_1":
        return n == 1
    if name == "count_ge_3":
        return n >= 3
    if name == "one_singled_out":
        return singled_out(comp) is not None
    if name == "not_matrix":
        return cd.get("card_layout") != "matrix"
    if name == "all_titles_numbered_ok":
        return not any(_NUMBERED.match(t) for t in items(comp))
    if name == "chart_is_bar":
        return str(cd.get("chart_type") or comp.get("chart_type") or "bar").lower() == "bar"
    if name == "has_tones":
        tones = list(cd.get("kpi_tones") or []) + [c.get("tone") for c in cd.get("cards") or []]
        return any(t for t in tones)
    raise KeyError(f"unknown requires check {name}")


def failed_requires(variant: dict, comp: dict) -> list[str]:
    return [r for r in variant.get("requires") or [] if not check(r, comp)]


def available(kind: str, tag: str, comp: dict) -> dict[str, dict]:
    """The variants whose `requires` hold for this component (the ones the prompt lists)."""
    layout = (comp.get("content_data") or {}).get("card_layout")
    return {k: v for k, v in variants(kind, tag, layout).items() if not failed_requires(v, comp)}


def resolve_variant(kind: str, tag: str, comp: dict, asked: str | None) -> tuple[str | None, str | None, str]:
    """(variant used, code or None, note). Unknown -> default; unmet -> the fallback chain."""
    layout = (comp.get("content_data") or {}).get("card_layout")
    vs = variants(kind, tag, layout)
    if not vs:
        return None, None, ""
    default = next(iter(vs))
    if not asked:
        return default, None, ""
    if asked not in vs:
        return default, "NODE_VARIANT_UNKNOWN", f'variant "{asked}" is not a {tag} variant; "{default}" used'
    seen, name = set(), asked
    while name in vs and name not in seen:
        seen.add(name)
        fails = failed_requires(vs[name], comp)
        if not fails:
            if name == asked:
                return name, None, ""
            return name, "NODE_VARIANT_UNMET", f'variant "{asked}" needs {", ".join(failed_requires(vs[asked], comp))}; "{name}" used'
        name = vs[name].get("fallback") or default
    return default, "NODE_VARIANT_UNMET", f'variant "{asked}" needs {", ".join(failed_requires(vs[asked], comp))}; "{default}" used'
