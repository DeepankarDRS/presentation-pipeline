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


# a direction for building the slide, not slide text: "Visual: ...", "Visual Suggestion: ..." (agency format), and a
# bare "Show: a, b, c" (XTSY slide 2: topics to cover, drawn as a 3-item list in every XTSY run)
_DIRECTION = re.compile(r"^\s*(visual(?:\s+(?:suggestions?|directions?|ideas?))?|design|style|look|layout|show)\s*:\s*",
                        re.I)
# presenter notes: never on the slide ("Speaker Notes: ...": 18 outline messages in the 29 plan-only runs, written by
# the outline for the agency brief's requested format, drawn as a 6-item list on the pillars slide)
NOTES_LABEL = re.compile(r"^\W*((speaker|presenter|slide)\s+notes?|talking points?|presenter script)\s*[:\-–—]", re.I)
# "Show benefits: a; b" - a direction verb in front of a content label; the label and its items are content
_SHOW_LABEL = re.compile(r"^(\W*)show\s+(?!how\b|that\b|the\b|where\b|why\b)([A-Za-z][^:]{0,40}):", re.I)


def settle_direction_lines(slide: dict[str, Any], instructions: dict[str, list[str]] | None = None,
                           content: str = "") -> list[str]:
    """Clean one outline slide's key_messages in place: presenter notes dropped, "Show <label>:" made "<Label>:".
    "Visual:" / "Show:" directions stay in key_messages (the planner reads them as design input; code keeps them out
    of the slide's content, see `visual_directions`). With the brief's `instructions` (`brief_instructions`), a
    message that rewords one loses its label too: the brief's speaker notes are dropped ("Note: End with
    confidence ..." for "Speaker Notes: End with confidence ..."), an unlabelled design sentence becomes a "Visual:"
    line ("Use arrow visuals rather than hard numbers."). A message whose words are also in the brief's `content`
    (`brief_content`) stays as it is. Returns plain-words notes."""
    notes: list[str] = []
    keep = []
    for msg in slide.get("key_messages") or []:
        text = str(msg or "")
        if NOTES_LABEL.match(text):
            notes.append(f"dropped presenter notes from key_messages: {text[:80]}")
            continue
        if instructions and not _DIRECTION.match(text) and copies_visual(text, instructions.get("visuals") or []):
            text = "Visual: " + _LEAD_LABEL.sub("", text, count=1)
            notes.append(f"gave the brief's Visual: line its label back: {text[8:88]}")
        if instructions and not _DIRECTION.match(text) and not (content and from_brief(_LEAD_LABEL.sub("", text, count=1),
                                                                                      content)):
            if matches_instruction(text, instructions.get("notes") or []):
                notes.append(f"dropped the brief's presenter notes from key_messages: {text[:80]}")
                continue
            if matches_instruction(text, instructions.get("directions") or []):
                text = "Visual: " + _LEAD_LABEL.sub("", text, count=1)
                notes.append(f"marked the brief's design direction as a Visual: line: {text[8:88]}")
        m = _SHOW_LABEL.match(text)
        if m:
            label = m.group(2).strip()
            text = f"{m.group(1)}{label[:1].upper()}{label[1:]}:{text[m.end():]}"
        keep.append(text)
    slide["key_messages"] = keep
    return notes
_TEXT_KINDS = {"narrative", "caption", "bullet_list"}
_DESIGN_WORDS = re.compile(r"visual|theme|cues?\b|colou?r|icons?\b|imagery|illustrat|gradient|layout|style|mood|look and feel",
                           re.I)

# ── the brief's own instruction lines (eval 2026-10-15: the outline rewords their labels) ──
# A brief line for the presenter or the slide builder, not the audience, reaches the slide when the outline drops or
# changes its label: agency "Speaker Notes: End with confidence ..." came back as "Note: End with confidence ...",
# XTSY "Use arrow visuals rather than hard numbers." has no label at all. Both were printed as captions.

# a short label in front of a line ("Note:", "Closing note:"); the outline may write its own in place of the brief's
_LEAD_LABEL = re.compile(r"^\W*[A-Za-z][A-Za-z ]{0,24}:\s+")
# a brief sentence that tells the slide builder how to draw: a build verb first, a design word in it
_BUILD_VERB = re.compile(r"^\W*(use|avoid|show|display|depict|draw|keep|make|add|place|put|render|design)\b", re.I)
_BUILD_WORDS = re.compile(_DESIGN_WORDS.pattern + r"|charts?\b|graphs?\b|diagrams?\b|graphics?\b", re.I)
# brief pieces: lines, runs of 2+ spaces (folded YAML briefs), bullets; then sentences
_BRIEF_PIECE = re.compile(r"\n|\s{2,}|(?:^|\s)[*•]\s")
_SENTENCE_END = re.compile(r"(?<=[a-z0-9)])[.!?]\s+(?=[A-Z])")
MIN_INSTRUCTION_WORDS = 3   # a shorter line matches an instruction by chance
# a figure, not a count in a name ("4-stage"): a decimal, 2+ digits, a currency or a unit after the number
_FIGURE = re.compile(r"\d+[.,]\d|\d{2,}|[₹$€£]\s*\d|\d\s*(?:%|x\b|[kmbl]\b|cr\b|mn\b)", re.I)


def brief_instructions(request: str) -> dict[str, list[str]]:
    """The brief's lines that are not slide content: "notes" (the text after a speaker-notes label), "directions"
    (unlabelled sentences that start with a build verb and name a design element: "Use arrow visuals rather than hard
    numbers.") and "visuals" (the text after a direction label: "Visual: 4-stage growth roadmap" → "4-stage growth
    roadmap"), which the outline may copy without its label."""
    notes: list[str] = []
    directions: list[str] = []
    visuals: list[str] = []
    for piece in _BRIEF_PIECE.split(request or ""):
        piece = " ".join((piece or "").split())
        if not piece:
            continue
        m = NOTES_LABEL.match(piece)
        if m:
            if piece[m.end():].strip():
                notes.append(piece[m.end():].strip())
            continue
        m = _DIRECTION.match(piece)
        if m:
            if piece[m.end():].strip():
                visuals.append(piece[m.end():].strip())
            continue
        if _LEAD_LABEL.match(piece):
            continue
        directions += [s for s in _SENTENCE_END.split(piece) if _BUILD_VERB.match(s) and _BUILD_WORDS.search(s)]
    return {"notes": notes, "directions": directions, "visuals": visuals}


def brief_content(request: str, instructions: dict[str, list[str]]) -> str:
    """The brief without its instruction lines: what a slide line may be copied from."""
    out = request or ""
    for line in [*(instructions.get("notes") or []), *(instructions.get("directions") or []),
                 *(instructions.get("visuals") or [])]:
        out = out.replace(line, " ")
    return " ".join(out.split())


def copies_visual(text: str, visuals: list[str]) -> bool:
    """`text` (a short label in front taken off) is one of the brief's labelled directions without its label: the same
    words ("Opportunity Matrix"), or 70% of each one's words in the other ("Quick Commerce ecosystem — Zepto, Blinkit and
    Instamart connected to XTSY growth engine." for the brief's "Visual: Quick Commerce ecosystem showing ..."). Both
    ways, so a longer content line that only mentions the direction's words stays content. A line with a figure
    ("ROAS by city: Bengaluru 0.45x" from "Visual: bar chart of ROAS by city: ...") stays content: its numbers go on
    the slide."""
    body = _LEAD_LABEL.sub("", str(text or ""), count=1)
    plain = _plain(body)
    if not plain or _FIGURE.search(body):
        return False
    return any(plain == _plain(v) or (len(_words(body)) >= MIN_INSTRUCTION_WORDS and from_brief(body, v)
                                       and from_brief(v, body)) for v in visuals)


def matches_instruction(text: str, instructions: list[str]) -> bool:
    """`text` (any short label in front taken off) words a brief instruction line: 70% of its words are in one."""
    body = _LEAD_LABEL.sub("", str(text or ""), count=1)
    if len(_words(body)) < MIN_INSTRUCTION_WORDS:
        return False
    return any(from_brief(body, line) for line in instructions)


def instruction_lines(outline_plan: dict[str, Any] | None) -> list[str]:
    """Every brief instruction line the outline planner found (`outline_plan["brief_instructions"]`)."""
    found = (outline_plan or {}).get("brief_instructions") or {}
    return [*(found.get("notes") or []), *(found.get("directions") or []), *(found.get("visuals") or [])]


def visual_directions(slide: dict[str, Any]) -> list[str]:
    """The brief's design directions for this slide: its "Visual:" / "Show:" lines, label taken off."""
    out = [_DIRECTION.sub("", m) for m in slide.get("key_messages") or [] if _DIRECTION.match(m or "")]
    return [d for d in out if d.strip()]


def _component_text(comp: dict[str, Any]) -> str:
    data = comp.get("content_data") or {}
    return " ".join(str(x) for x in [data.get("text", ""), *(data.get("bullets") or [])])


def content_line_list(slide: dict[str, Any], directions: list[str]) -> list[str]:
    """The slide's brief lines that are content: not labelled as, or copied from, a design direction."""
    return [m for m in slide.get("key_messages") or []
            if m and not _DIRECTION.match(m) and not NOTES_LABEL.match(m) and not any(from_brief(m, d) for d in directions)]


def content_lines(slide: dict[str, Any], directions: list[str]) -> str:
    return " ".join(content_line_list(slide, directions))


def drop_visual_directions(plan: dict[str, Any], directions: list[str], content: str = "") -> list[str]:
    """Remove text components that only repeat a design direction ("Marketplace growth theme
    with FLIPCART and ZAROMA visual cues." printed as a card on the CHEFFIN cover). The
    direction still reaches the planner as its own block (layout only) and the generator through the design hints."""
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
            # title + tag together (2026-10-08: QBR priority cards split one brief line into title /
            # tag and kept the whole line again as the body - the same words three times)
            head = f'{card.get("title", "")} {card.get("tag", "")}'
            title, body = set(re.findall(r"[a-z0-9₹%]+", head.lower())),                 set(re.findall(r"[a-z0-9₹%]+", str(card["body"]).lower()))
            if title and body and (body <= title or len(body & title) / len(body | title) >= 0.8):
                notes.append(f"removed card body that repeats its title: {card['body']}")
                card.pop("body", None)
                card.pop("body_source", None)
    return notes


SHARED_LINE_CARDS = 3   # a line on every card of a grid this large says nothing about any one card


def _plain(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9₹%]+", (text or "").lower()))


def drop_shared_card_lines(plan: dict[str, Any], brief_text: str) -> list[str]:
    """Remove a body or bullet that is the same on every card of a grid of 3+ when the brief does not write it
    itself: "Applies to: Zepto · Blinkit · Instamart" on all four lever cards (XTSY slide 3, 2026-10-15), composed
    by the planner from the matrix columns. A line the brief writes word for word stays (its own status line)."""
    notes: list[str] = []
    brief = _plain(brief_text)
    for comp in plan.get("components", []):
        cards = [c for c in (comp.get("content_data") or {}).get("cards") or [] if isinstance(c, dict)]
        if comp.get("kind") != "card_grid" or len(cards) < SHARED_LINE_CARDS:
            continue
        bodies = {_plain(str(c.get("body") or "")) for c in cards}
        if len(bodies) == 1 and (line := bodies.pop()) and line not in brief:
            notes.append(f"removed the line on every card of '{comp.get('component_id', '')}': {cards[0]['body']}")
            for c in cards:
                c.pop("body", None)
                c.pop("body_source", None)
        lists = [{_plain(str(b)) for b in c.get("bullets") or [] if str(b).strip()} for c in cards]
        for line in sorted(set.intersection(*lists) if all(lists) else set()):
            if not line or line in brief:
                continue
            notes.append(f"removed the bullet on every card of '{comp.get('component_id', '')}': {line}")
            for c in cards:
                c["bullets"] = [b for b in c.get("bullets") or [] if _plain(str(b)) != line]
    return notes
