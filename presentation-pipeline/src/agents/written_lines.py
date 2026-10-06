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


_DIRECTION = re.compile(r"^\s*(visual|design|style|look|layout)\s*:\s*", re.I)
_TEXT_KINDS = {"narrative", "caption", "bullet_list"}
_DESIGN_WORDS = re.compile(r"visual|theme|cues?\b|colou?r|icons?\b|imagery|illustrat|gradient|layout|style|mood|look and feel",
                           re.I)


def visual_directions(slide: dict[str, Any]) -> list[str]:
    """The brief's design directions for this slide (a "Visual:" line, visual_emphasis)."""
    out = [_DIRECTION.sub("", m) for m in slide.get("key_messages") or [] if _DIRECTION.match(m or "")]
    emphasis = str(slide.get("visual_emphasis") or "")
    if _DESIGN_WORDS.search(emphasis):  # an emphasis note that restates content is not a direction
        out.append(_DIRECTION.sub("", emphasis))
    return [d for d in out if d.strip()]


def _component_text(comp: dict[str, Any]) -> str:
    data = comp.get("content_data") or {}
    return " ".join(str(x) for x in [data.get("text", ""), *(data.get("bullets") or [])])


def content_line_list(slide: dict[str, Any], directions: list[str]) -> list[str]:
    """The slide's brief lines that are content: not labelled as, or copied from, a design direction."""
    return [m for m in slide.get("key_messages") or []
            if m and not _DIRECTION.match(m) and not any(from_brief(m, d) for d in directions)]


def content_lines(slide: dict[str, Any], directions: list[str]) -> str:
    return " ".join(content_line_list(slide, directions))


def drop_visual_directions(plan: dict[str, Any], directions: list[str], content: str = "") -> list[str]:
    """Remove text components that only repeat a design direction ("Marketplace growth theme
    with FLIPCART and ZAROMA visual cues." printed as a card on the CHEFFIN cover). The
    direction still reaches the generator through visual_emphasis / the design hints."""
    notes: list[str] = []
    keep = []
    for comp in plan.get("components", []):
        text = _component_text(comp)
        if (comp.get("kind") in _TEXT_KINDS and text.strip() and any(from_brief(text, d) for d in directions)
                and not (content and from_brief(text, content))):
            notes.append(f"dropped {comp.get('kind')} '{comp.get('component_id', '')}': it repeats the brief's "
                         f"design direction, not content: {text[:80]}")
            continue
        keep.append(comp)
    plan["components"] = keep
    return notes


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


def drop_repeated_bodies(plan: dict[str, Any]) -> list[str]:
    """Remove a card body that only repeats its title (hold-out agency 4: "Intent-layer campaign
    structure" / "Intent-layer campaign structure."): same words, or every body word is in the title.
    A body that adds words ("Raw-data reporting" / "... and weekly diagnostics") stays."""
    notes: list[str] = []
    for comp in plan.get("components", []):
        if comp.get("kind") != "card_grid":
            continue
        for card in (comp.get("content_data") or {}).get("cards", []):
            if not isinstance(card, dict) or not card.get("body"):
                continue
            title, body = set(re.findall(r"[a-z0-9₹%]+", str(card.get("title", "")).lower())),                 set(re.findall(r"[a-z0-9₹%]+", str(card["body"]).lower()))
            if title and body and (body <= title or len(body & title) / len(body | title) >= 0.8):
                notes.append(f"removed card body that repeats its title: {card['body']}")
                card.pop("body", None)
                card.pop("body_source", None)
    return notes
