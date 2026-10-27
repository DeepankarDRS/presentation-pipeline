"""Outline items (OUTLINE_ITEMS=on, docs/outline-items-design-2026-10-27.md): each outline slide carries items of a
kind + text instead of plain key_messages. key_messages stays, computed from the items, so code that reads it keeps
working; the slide component planner reads the items with their kind while they still match key_messages (the plan
editor and the outline replanner edit key_messages only).

The fit list (knowledge/core/kind-fit.yaml) names the components each kind may become; the planner prompt renders
it and a pick outside it is reported, never blocked. Every check here is report-only.
"""

from __future__ import annotations

import functools
import os
import re
from pathlib import Path
from typing import Any, get_args

import yaml

from src.agents.outline_planner_schema import ItemKind
from src.agents.written_lines import _DIRECTION, from_brief, settle_direction_lines

ITEM_KINDS: tuple[str, ...] = get_args(ItemKind)
_FIT_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "kind-fit.yaml"
# a figure, not a count in a name ("4-stage roadmap", "90-Day Action Plan", "Phase 2"): 2+ digits or a decimal, not
# joined to a word by a hyphen
_FIGURE = re.compile(r"(?:\d[\d,]*\.\d+|\d{2,})(?![\d-])")


def outline_items_on() -> bool:
    """`OUTLINE_ITEMS`: "on" = the outline writes items (kind + text); anything else = key_messages (today's route).
    Read per call."""
    return os.getenv("OUTLINE_ITEMS", "off").strip().lower() == "on"


def _message(item: dict[str, Any]) -> str:
    text = str(item.get("text") or "").strip()
    if item.get("kind") == "visual" and text and not _DIRECTION.match(text):
        return f"Visual: {text}"
    return text


def messages_from_items(items: list[dict[str, Any]]) -> list[str]:
    """key_messages as today: each item's text, a visual item with its "Visual:" label."""
    return [m for m in (_message(i) for i in items or []) if m]


def settle_items(slide: dict[str, Any], instructions: dict[str, list[str]] | None = None,
                 content: str = "") -> list[str]:
    """`settle_direction_lines` per item, in place: presenter notes dropped, a line that turns out to be a direction
    becomes a visual item (label off); then key_messages computed from the items. Returns plain-words notes."""
    notes: list[str] = []
    keep = []
    for item in slide.get("items") or []:
        one = {"key_messages": messages_from_items([item])}
        notes += settle_direction_lines(one, instructions, content)
        for msg in one["key_messages"]:
            if _DIRECTION.match(msg):
                keep.append({"kind": "visual", "text": _DIRECTION.sub("", msg).strip()})
            else:
                keep.append({"kind": item.get("kind", "point"), "text": msg})
    slide["items"] = keep
    slide["key_messages"] = messages_from_items(keep)
    return notes


def items_for_planner(slide: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The slide's items when they still match its key_messages; None when it has none or key_messages was edited
    after the outline (then the planner reads key_messages as today)."""
    items = slide.get("items")
    if not items or messages_from_items(items) != list(slide.get("key_messages") or []):
        return None
    return items


# ── fit list ─────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def kind_fit() -> dict[str, dict[str, Any]]:
    """{item kind: {"options": [component kinds], "note": str}}"""
    return yaml.safe_load(_FIT_FILE.read_text(encoding="utf-8")) or {}


def kind_fit_lines() -> list[str]:
    """The fit list as prompt lines: "series: chart, kpi_row, table — <note>"."""
    out = []
    for kind, entry in kind_fit().items():
        options = ", ".join(entry.get("options") or []) or "never drawn"
        out.append(f"{kind}: {options}" + (f" — {entry['note']}" if entry.get("note") else ""))
    return out


def _leaves(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [x for v in value.values() for x in _leaves(v)]
    if isinstance(value, list):
        return [x for v in value for x in _leaves(v)]
    if value is None or isinstance(value, bool):
        return []
    return [str(value).strip()]


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def kind_fit_notes(plan: dict[str, Any], items: list[dict[str, Any]]) -> list[str]:
    """KIND_OUTSIDE_FIT (report-only): a component drawing an item whose kind does not list that component. An item
    feeds a component when half the component's texts (3+ characters) are in the item's text, or when one of them
    is almost the whole item (a card body that is the item's sentence). One shared number ("42.8" in a chart and in
    a KPI) or a shared name ("Allowable CPC for 1.0x ROAS" in a formula note and as a chart series) is not enough."""
    fit = kind_fit()
    notes = []
    for comp in plan.get("components") or []:
        kind = comp.get("kind")
        if kind == "title":
            continue
        leaves = [_norm(x) for x in _leaves(comp.get("content_data") or {}) if len(x) >= 3]
        for item in items or []:
            options = (fit.get(item.get("kind")) or {}).get("options")
            if not options or kind in options:
                continue
            text = _norm(item.get("text", ""))
            found = [leaf for leaf in leaves if leaf in text]
            if leaves and (len(found) >= len(leaves) / 2 or any(len(leaf) >= max(12, 0.9 * len(text)) for leaf in found)):
                notes.append(f"KIND_OUTSIDE_FIT: {item.get('kind')} item drawn as {kind} "
                             f"({comp.get('component_id', '')}): {item.get('text', '')[:80]}")
    return notes


# ── outline checks ───────────────────────────────────────────────────────────

def review_points(items: list[dict[str, Any]], brief_text: str) -> list[str]:
    """POINT_NOT_IN_BRIEF (report-only): point items whose words are mostly not in the brief, the outline's own
    commentary, listed for the user's review."""
    return [i["text"] for i in items or [] if i.get("kind") == "point" and not from_brief(i.get("text", ""), brief_text)]


def item_issues(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Items in the wrong form (report-only): a visual item with figures in it (content written as a direction), a
    records item with a row that holds no measure."""
    out = []
    for item in items or []:
        text = item.get("text", "")
        if item.get("kind") == "visual" and _FIGURE.search(text):
            out.append(("VISUAL_WITH_NUMBERS", text))
        elif item.get("kind") == "records" and any(not re.search(r"\d", row) for row in text.split("|")):
            out.append(("RECORDS_WITHOUT_MEASURES", text))
    return out
