"""Code checks for planning v2. Each returns a list of issues in plain words; the graph sends
them back to the LLM (bounded retries) and records whatever remains."""

from __future__ import annotations

import re
from typing import Any

from src.planning.adapter import LABEL_ONLY_KINDS, fill_component, shown_text
from src.planning.brief_index import by_id, data_numbers, numbers

MAX_EMPHASIS = 2
MAX_KPIS = 6
MAX_TABLE_ROWS = 10
MAX_BULLETS = 6
MAX_STEP_WORDS = 4
# a brief line that asks for content: "Mention that…", "DATA QUALITY NOTE: Mention…", "Also mention…",
# "Include: Prepared by…" (a bare "Include:" label line has nothing after it and does not count)
_REQUIREMENT = re.compile(r"^(?:[A-Z][A-Z ]+:\s*)?(?:also\s+)?(?:mention|include|add)\b[:\s]+\S{2}", re.I)
_STEP_KINDS ={"timeline", "process_arrow", "flow", "pyramid", "tree", "matrix"}
# unit of a chart series or category, from its name (CHEFFIN put CVR % and AOV ₹ on one axis)
_UNITS = {"%": r"%|\bcvr\b|\bctr\b|\bacos\b|\bshare\b",
          "₹": r"₹|\brs\b|\binr\b|\baov\b|\bcpc\b|\bcpm\b|\bspend\b|\bsales\b|\brevenue\b|\bgmv\b",
          "x": r"\broas\b|\broi\b|\(x\)"}


def _unit(name: str) -> str | None:
    """The unit of a series / category name: its FIRST metric word decides
    ("Allowable CPC for 1.0x ROAS" is ₹ — the ROAS is only a qualifier)."""
    hits = [(m.start(), u) for u, pat in _UNITS.items() if (m := re.search(pat, name.lower()))]
    return min(hits)[1] if hits else None


def _canon(s: str) -> str:
    return re.sub(r"[^a-z0-9₹%]+", " ", (s or "").lower()).strip()


def _short(ids: list[str], n: int = 12) -> str:
    return ", ".join(ids[:n]) + (f" (+{len(ids) - n} more)" if len(ids) > n else "")


def apply_headline_blocks(story: dict[str, Any], index: dict[str, Any]) -> None:
    """Copy the brief's headline verbatim where the storyline pointed at one; renumber slides.

    The LLM's headline is kept only when the block is "<label>: <that headline>"
    ("Title Slide Headline: X" → "X"); in every other case the whole block text is used."""
    blocks = by_id(index)
    for i, s in enumerate(story.get("slides", [])):
        s["slide_index"] = i
        b = blocks.get(s.get("headline_block") or "")
        if not b or b["kind"] != "text":
            continue
        own, text = (s.get("headline") or "").strip(), b["text"].strip()
        label_only = bool(own) and text.endswith(own) and text[: len(text) - len(own)].rstrip().endswith(":")
        if not label_only:
            s["headline"] = text


def check_storyline(story: dict[str, Any], index: dict[str, Any], target_slides: int | None) -> list[str]:
    issues: list[str] = []
    blocks = by_id(index)
    slides = story.get("slides", [])
    known = set(index["numbers"])
    if target_slides and len(slides) != target_slides:
        issues.append(f"The deck must have exactly {target_slides} slides; you planned {len(slides)}.")

    used: set[str] = set()
    for s in slides:
        n = s["slide_index"] + 1
        unknown = [b for b in s.get("block_ids", []) if b not in blocks]
        if unknown:
            issues.append(f"Slide {n}: unknown block ids {_short(unknown)}.")
        used.update(s.get("block_ids", []))
        hb = s.get("headline_block") or ""
        if hb and (hb not in blocks or blocks[hb]["kind"] != "text"):
            issues.append(f"Slide {n}: headline_block '{hb}' is not a text block.")
        if not s.get("headline", "").strip():
            issues.append(f"Slide {n}: the headline is empty.")
        elif s["headline"].strip().endswith(":"):
            issues.append(f"Slide {n}: the headline '{s['headline'].strip()}' is a field label; point "
                          "headline_block at the line that follows it.")
        elif s.get("intent") not in ("cover", "section_divider", "closing") and \
                _canon(s["headline"]) == _canon(s.get("label", "")):
            issues.append(f"Slide {n}: the headline repeats the label; state the slide's conclusion.")
        if len(s.get("emphasis", [])) > MAX_EMPHASIS:
            issues.append(f"Slide {n}: {len(s['emphasis'])} emphasis items; at most {MAX_EMPHASIS}.")
        written = " ".join([s.get("label", ""), s.get("headline", ""), s.get("subtitle", ""),
                            s.get("so_what", ""), *s.get("emphasis", [])])
        invented = sorted(set(numbers(written)) - known)
        if invented:
            issues.append(f"Slide {n}: numbers not in the brief: {', '.join(invented)}. Use only the brief's numbers.")

    aside = {a["block_id"] for a in story.get("set_aside", [])}
    missing = [b["id"] for b in index["blocks"] if b["data_numbers"] and b["id"] not in used | aside]
    if missing:
        issues.append(f"Blocks with numbers that no slide shows and set_aside does not list: {_short(missing)}. "
                      "Put each on a slide, or in set_aside with the reason.")
    asked = [b["id"] for b in index["blocks"] if b["kind"] == "text" and _REQUIREMENT.match(b["text"])
             and b["id"] not in used]
    if asked:
        issues.append(f"Blocks {_short(asked)} ask for content to be shown (\"Mention…\", \"Include…\") but are on "
                      "no slide. Put each on the slide where it belongs.")
    return issues


def check_slide(design: dict[str, Any], story: dict[str, Any], index: dict[str, Any]) -> list[str]:
    """Check a slide design; `design` components must already be filled (fill_design)."""
    issues: list[str] = []
    blocks = by_id(index)
    known = set(index["numbers"])
    assigned = set(story.get("block_ids", []))
    comps = design.get("components", [])

    header = " ".join([story.get("label", ""), story.get("headline", ""), story.get("subtitle", "")])
    shown_parts = [header] + [shown_text(c) for c in comps]
    shown = set(numbers(" ".join(shown_parts)))

    invented = sorted(shown - known)
    if invented:
        issues.append(f"Numbers not in the brief: {', '.join(invented)}. Copy values exactly from the blocks.")

    # not_shown is for labels and instructions; it never excuses data (gj-h1 run 7af681 dropped KPI notes
    # and read-out figures that way). Dropping data is a storyline decision (set_aside), visible deck-wide.
    skipped = {a["block_id"] for a in design.get("not_shown", [])}
    for bid in sorted(assigned, key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 0)):
        b = blocks.get(bid)
        if not b:
            continue
        lost = sorted(set(data_numbers(b["text"])) - shown)
        if lost and bid in skipped:
            issues.append(f"Block {bid} holds data ({', '.join(lost)}) but is in not_shown — not_shown is only for "
                          "labels and instructions. Show it: a KPI note, a table cell or the read-out.")
        elif lost:
            issues.append(f"Block {bid} is assigned to this slide but {', '.join(lost)} is not shown. Show it.")

    heroes = [c["id"] for c in comps if c.get("role") == "hero"]
    if len(heroes) > 1:
        issues.append(f"{len(heroes)} hero components ({', '.join(heroes)}); at most one focal point.")
    emph = [c["id"] for c in comps if c.get("emphasis")]
    if len(emph) > MAX_EMPHASIS:
        issues.append(f"{len(emph)} components carry emphasis; at most {MAX_EMPHASIS}.")

    header_lines = [h for h in (story.get("headline", ""), story.get("subtitle", "")) if len(_canon(h)) >= 15]
    for c in comps:
        cid, kind = c["id"], c["kind"]
        body = _canon(" ".join([c.get("text", ""), *c.get("bullets", [])]))
        if any(_canon(h) in body for h in header_lines):
            issues.append(f"{cid}: repeats the slide's headline or subtitle — the header already shows them.")
        stray = [b for b in c.get("block_ids", []) if b not in assigned]
        if stray:
            issues.append(f"{cid}: blocks {_short(stray)} are not assigned to this slide.")
        if not shown_text(c).strip():
            issues.append(f"{cid}: no content (bind a parsed table/chart block or fill its fields).")
        if kind == "kpi_row" and len(c.get("kpis", [])) > MAX_KPIS:
            issues.append(f"{cid}: {len(c['kpis'])} KPI tiles; at most {MAX_KPIS} — use a table for more.")
        if kind == "table" and len(c.get("rows", [])) > MAX_TABLE_ROWS:
            issues.append(f"{cid}: {len(c['rows'])} rows; at most {MAX_TABLE_ROWS} — split the slide or the table.")
        if kind == "bullet_list" and len(c.get("bullets", [])) > MAX_BULLETS:
            issues.append(f"{cid}: {len(c['bullets'])} bullets; at most {MAX_BULLETS}.")
        if kind in LABEL_ONLY_KINDS and any(i.get("detail", "").strip() for i in c.get("items", [])):
            issues.append(f"{cid}: a {kind} shows only its labels, so the item details would be lost — keep the "
                          f"{kind} for the labels and put the details in a table or bullets.")
        if kind in _STEP_KINDS:
            long = [i["label"] for i in c.get("items", []) if len(i["label"].split()) > MAX_STEP_WORDS]
            if long:
                issues.append(f"{cid}: {kind} labels must be ≤ {MAX_STEP_WORDS} words ({long[0]!r}); put the "
                              "detail in a table or bullets instead.")
        if kind == "chart":
            names = [s["name"] for s in c.get("series", [])]
            if len(names) < 2:  # one series: its categories may name the metrics ("CVR", "AOV")
                names += c.get("labels", [])
            units = sorted({u for n in names if (u := _unit(n))})
            if len(units) > 1:
                issues.append(f"{cid}: series mix units ({', '.join(units)}) on one axis — use one chart per "
                              "unit, or a table.")
            if not c.get("series"):
                issues.append(f"{cid}: chart has no series.")
    return issues


def fill_design(design: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    blocks = by_id(index)
    return {**design, "components": [fill_component(c, blocks) for c in design.get("components", [])]}
