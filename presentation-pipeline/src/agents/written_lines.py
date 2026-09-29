"""Card lines the planner wrote itself — flagged for the user, never trusted.

User decision 2026-09-29: when the brief gives a card only its name, the planner may
write one short qualitative line (Genspark does the same), but every such line is
flagged so the user can keep or remove it. The planner's own "body_source" mark is
not trusted: a line counts as the brief's only when its words are in the slide's
key messages. A written line may never carry a number — those are removed here.
"""

from __future__ import annotations

import re
from typing import Any

_WORD = re.compile(r"[a-z0-9₹%]+")
_DIGIT = re.compile(r"\d")
BRIEF_OVERLAP = 0.7  # share of a line's content words that must appear in the brief


def _words(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if len(w) > 3 or _DIGIT.search(w)]


def from_brief(line: str, brief_text: str) -> bool:
    words = _words(line)
    if not words:
        return True
    have = set(_words(brief_text))
    return sum(w in have for w in words) / len(words) >= BRIEF_OVERLAP


def flag_written_lines(plan: dict[str, Any], brief_text: str) -> list[str]:
    """Mark card_grid lines not found in the brief as written, in place; drop written
    lines with numbers. Returns plain-words notes; the kept written lines are listed
    in plan["written_lines"]."""
    notes: list[str] = []
    written: list[str] = []
    for comp in plan.get("components", []):
        if comp.get("kind") != "card_grid":
            continue
        for card in (comp.get("content_data") or {}).get("cards", []):
            if not isinstance(card, dict) or not card.get("body"):
                continue
            body = str(card["body"])
            if from_brief(body, brief_text):
                card.pop("body_source", None)
                continue
            if _DIGIT.search(body):
                card.pop("body", None)
                card.pop("body_source", None)
                notes.append(f"removed written line with a number from card '{card.get('title', '')}': {body}")
                continue
            card["body_source"] = "written"
            written.append(body)
    if written:
        plan["written_lines"] = written
    return notes
