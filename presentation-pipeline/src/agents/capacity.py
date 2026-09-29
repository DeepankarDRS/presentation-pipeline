"""Component capacity — the single source for how much each component kind can draw.

Loaded from knowledge/core/capacity.yaml. The slide component planner prompt renders
these numbers, and the plan checks enforce them, so a limit is never restated in prose.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

_CAPACITY_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "capacity.yaml"


@functools.lru_cache(maxsize=1)
def capacity() -> dict[str, dict[str, Any]]:
    """{kind: {limit: value}}; ranges are [min, max] lists."""
    return yaml.safe_load(_CAPACITY_FILE.read_text(encoding="utf-8")) or {}


def span(kind: str, key: str = "items") -> str:
    """A range as prompt text: [3, 5] -> "3-5"."""
    lo, hi = capacity()[kind][key]
    return f"{lo}-{hi}"


def max_of(kind: str, key: str = "items") -> int:
    value = capacity()[kind][key]
    return value[1] if isinstance(value, list) else value


# ── Plan check: components past their capacity become cards ────────────────
# Chevrons with 7 items or sentence labels break words into letters ("Consume r",
# XTSY slide 7); a horizontal timeline past 5 items collides. A card_grid holds the
# same items legibly, so the plan is fixed in code — no re-plan call.

def _label(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("label") or item.get("title") or item.get("name") or "")
    return str(item)


def _detail(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("description") or item.get("detail") or "")
    return ""


def _as_cards(items: list[Any], tag_key: str | None = None) -> list[dict[str, str]]:
    cards = []
    for item in items:
        card = {"title": _label(item)}
        if tag_key and isinstance(item, dict) and item.get(tag_key):
            card["tag"] = str(item[tag_key])
        if _detail(item):
            card["body"] = _detail(item)
        cards.append(card)
    return cards


def _to_cards(comp: dict[str, Any], cards: list[dict[str, str]]) -> None:
    steps_max = max_of("process_arrow")
    comp["kind"] = "card_grid"
    comp["items"] = len(cards)
    comp.pop("orientation", None)
    comp["content_data"] = {"card_layout": "steps" if len(cards) <= steps_max else "grid", "cards": cards}


def enforce_capacity(components: list[dict[str, Any]]) -> list[str]:
    """Convert process_arrow / timeline components past capacity.yaml into a card_grid,
    in place. Returns one plain-words note per change."""
    notes: list[str] = []
    for comp in components:
        kind, data = comp.get("kind"), comp.get("content_data") or {}
        cid = comp.get("component_id") or kind
        if kind == "process_arrow":
            steps = data.get("process_steps") or []
            too_many = len(steps) > max_of("process_arrow")
            max_words = capacity()["process_arrow"]["max_label_words"]
            long = [s for s in map(_label, steps) if len(s.split()) > max_words]
            if steps and (too_many or long):
                why = f"{len(steps)} steps" if too_many else f"label '{long[0]}' over {max_words} words"
                _to_cards(comp, _as_cards(steps))
                notes.append(f"{cid}: process_arrow with {why} -> card_grid ({comp['content_data']['card_layout']})")
        elif kind == "timeline":
            items = data.get("timeline_items") or []
            if len(items) > max_of("timeline"):
                _to_cards(comp, _as_cards(items, tag_key="date"))
                notes.append(f"{cid}: timeline with {len(items)} items -> card_grid ({comp['content_data']['card_layout']})")
    return notes
