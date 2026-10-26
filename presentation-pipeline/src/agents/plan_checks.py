"""Code checks on one slide plan (§14.6 step 0; checks C14-C17 of docs/plan-reviewer-loop.md).

The renderer draws exactly what a plan holds, so a plan that is empty, thin, repeats itself or
carries planner instructions shows up on the slide. Two kinds of check:

* **problems** (`find_problems`) - a re-ask is justified: an empty component (`PLAN_EMPTY`) or
  text that is an instruction to the presenter, not slide content (`PLAN_INSTRUCTION_TEXT`).
* **fixes** (`finalize_plan`) - code repairs what is left: drops an empty caption and any
  instruction text still there, drops a duplicate component (`PLAN_DUPLICATE_ITEMS`) and a card
  body that repeats its title, turns many short cards on a full slide into a list (`CARDS_TO_LIST`, rule K4),
  and flags a thin slide (`SLIDE_SPARSE`, report only).

Every flag lands in `SlidePlan.plan_flags` as {code, component_id?, detail}; each fix also
writes a plain-words note into `capacity_fixes`, like the other plan checks. Thresholds are an
estimate set on the 17 hold-out plans (docs/derived-blocks-planning-2026-10-06.md §2).
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.written_lines import (NOTES_LABEL, drop_repeated_bodies, drop_shared_card_lines, from_brief,
                                      matches_instruction)
from src.compiler.value_parts import is_sentence

PLAN_EMPTY = "PLAN_EMPTY"
PLAN_INSTRUCTION_TEXT = "PLAN_INSTRUCTION_TEXT"
PLAN_DUPLICATE_ITEMS = "PLAN_DUPLICATE_ITEMS"
SLIDE_SPARSE = "SLIDE_SPARSE"
KPI_VALUE_TEXT = "KPI_VALUE_TEXT"   # a kpi_row value that is a sentence, not a figure (KPI pilot 2026-10-11)
# a title-only card whose title the brief follows with its own line (tile-nodes §11: under card tile nodes code
# writes only plan text, so a line the planner dropped is lost; the LLM used to recover or invent one)
CARD_LINES_DROPPED = "CARD_LINES_DROPPED"
REASK_CODES = (PLAN_EMPTY, PLAN_INSTRUCTION_TEXT, KPI_VALUE_TEXT, CARD_LINES_DROPPED)

# the keys that hold a component's content; a block kind with none of them filled is empty
_CONTENT_KEYS: dict[str, tuple[str, ...]] = {
    "kpi_row": ("kpi_labels", "kpi_values"),
    "chart": ("chart_labels", "chart_series", "chart_values"),
    "table": ("table_rows",),
    "bullet_list": ("bullets",),
    "narrative": ("text",),
    "caption": ("text",),
    "timeline": ("timeline_items",),
    "flow": ("flow_steps", "nodes"),
    "process_arrow": ("process_steps",),
    "pyramid": ("pyramid_levels",),
    "tree": ("tree_nodes",),
    "card_grid": ("cards",),
    "matrix": ("matrix_items", "quadrants"),
}
_TEXT_KINDS = ("narrative", "caption", "bullet_list")
_WEIGHT_RANK = {"hero": 0, "peer": 1, "supporting": 2, "minor": 3}

# ── instruction text ────────────────────────────────────────────────────────

# presenter notes (written_lines.NOTES_LABEL) are always instruction text; a bare "Note: ..." is NOT a label: it is
# a normal footnote prefix (launch 6: "Note: SOC2 + HIPAA certification ...")
# verbs that only address a presenter: always instruction text at the start of slide text
_PRESENTER_VERB = re.compile(
    r"^\W*(walk (?:the audience |them |everyone )?through|talk (?:the audience )?through|lead with|"
    r"frame (?:this|these|the)|start with|begin with|open with|end with|close with|conclude with|"
    r"remind (?:the )?(?:audience|them)|tell (?:the )?(?:audience|them)|pivot to|transition to)\b", re.I)
# verbs that direct how to build the slide: instruction text only when the brief did not say them
_PLANNER_VERB = re.compile(
    r"^\W*(deepen|break down|show(?: how| that| the| where)?|highlight|illustrate|emphasi[sz]e|stress|"
    r"explain|discuss|summari[sz]e|demonstrate|introduce|present|outline|compare|focus on|"
    r"point out|call out|use this slide|make the case)\b", re.I)
# words that address the slide or the audience, anywhere in the text
_ADDRESSES_SLIDE = re.compile(r"\b(this slide|the audience|speaker notes?|presenter|talking points?)\b", re.I)


def is_instruction_text(text: str, brief_text: str, instructions: list[str] | tuple[str, ...] = ()) -> bool:
    """True when `text` is a direction to the presenter or slide builder, not audience content. `instructions` are
    the brief's own instruction lines (`written_lines.brief_instructions`): text that words one counts whatever its
    label, unless the slide's other brief lines say it too."""
    t = (text or "").strip()
    if not t:
        return False
    if NOTES_LABEL.match(t) or _PRESENTER_VERB.match(t) or _ADDRESSES_SLIDE.search(t):
        return True
    if instructions and matches_instruction(t, list(instructions)):
        content = "\n".join(x for x in (brief_text or "").split("\n") if not matches_instruction(x, list(instructions)))
        if not from_brief(t, content):
            return True
    return bool(_PLANNER_VERB.match(t)) and not from_brief(t, brief_text)


def _text_items(comp: dict[str, Any]) -> list[str]:
    data = comp.get("content_data") or {}
    if comp.get("kind") == "bullet_list":
        return [str(b) for b in data.get("bullets") or []]
    return [str(data["text"])] if data.get("text") else []


# ── emptiness ───────────────────────────────────────────────────────────────

def _filled(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return any(_filled(v) for v in (value.values() if isinstance(value, dict) else value))
    return value is not None and value != ""


def is_empty(comp: dict[str, Any]) -> bool:
    keys = _CONTENT_KEYS.get(comp.get("kind", ""))
    if not keys:
        return False  # title (its text is the slide's headline) and kinds we do not check
    data = comp.get("content_data") or {}
    return not any(_filled(data.get(k)) for k in keys)


def holds_no_content(plan: dict[str, Any]) -> bool:
    """No component past the headline and captions carries any content: the generator would
    write the whole slide from the summaries (wide-kpi XTSY slide 5, 2026-10-13: both answers'
    content_data_json unreadable, five invented lists). Unchecked kinds (layer, ...) count too.
    Not one: a plan of only a title, and a cover or closing slide, whose visual may be decoration."""
    if plan.get("slide_type") in ("cover", "closing"):
        return False
    body = [c for c in plan.get("components") or [] if c.get("kind") not in ("title", "caption")]
    return bool(body) and not any(_filled(c.get("content_data")) for c in body)


# ── problems that justify a re-ask ──────────────────────────────────────────

def find_problems(plan: dict[str, Any], brief_text: str,
                  instructions: list[str] | tuple[str, ...] = ()) -> list[dict[str, str]]:
    """PLAN_EMPTY / PLAN_INSTRUCTION_TEXT flags for a plan. An empty caption alone is not one:
    nothing is lost by dropping it, so it is not worth a second call."""
    problems: list[dict[str, str]] = []
    comps = plan.get("components") or []
    if not comps:
        problems.append({"code": PLAN_EMPTY, "component_id": "", "detail": "the plan has no components"})
    elif holds_no_content(plan) and not any(is_empty(c) for c in comps):
        problems.append({"code": PLAN_EMPTY, "component_id": "", "detail": "no component holds any content"})
    for comp in comps:
        cid = comp.get("component_id", "")
        if is_empty(comp) and comp.get("kind") != "caption":
            problems.append({"code": PLAN_EMPTY, "component_id": cid,
                             "detail": f"{comp.get('kind')} '{cid}' has no content"})
        for item in _text_items(comp):
            if is_instruction_text(item, brief_text, instructions):
                problems.append({"code": PLAN_INSTRUCTION_TEXT, "component_id": cid,
                                 "detail": f"{comp.get('kind')} '{cid}' holds an instruction, not slide content: "
                                           f"{item[:90]}"})
                break
        if comp.get("kind") == "kpi_row":
            prose = [str(v) for v in (comp.get("content_data") or {}).get("kpi_values") or [] if is_sentence(str(v))]
            if prose:
                problems.append({"code": KPI_VALUE_TEXT, "component_id": cid,
                                 "detail": f"kpi_row '{cid}' has {len(prose)} sentence(s) as kpi_values, not figures: "
                                           f"{prose[0][:80]}"})
        if comp.get("kind") == "card_grid":
            dropped = dropped_card_lines(comp, brief_text)
            if dropped:
                problems.append({"code": CARD_LINES_DROPPED, "component_id": cid,
                                 "detail": f"card_grid '{cid}' gives {len(dropped)} card(s) only a title though the key "
                                           f"messages give them a line: {dropped[0][:80]}"})
    return problems


# a line, a bullet, a ";" item or a sentence; " - " is kept: it often joins a title to its line
_BRIEF_PIECES = re.compile(r"\n|(?:^|\s)[*•·]\s|;|(?<=[a-z0-9)])\.\s+(?=[A-Z])")


def dropped_card_lines(comp: dict[str, Any], brief_text: str) -> list[str]:
    """The brief's lines for cards that have only a title: a piece of the brief (a line or a bullet) that starts with
    the card's title and goes on for 4+ words ("Late fixes (after 20:00): urgent edits from mobile")."""
    pieces = [re.sub(r"^(?:\d+[.)]|-)\s*", "", " ".join(x.split())) for x in _BRIEF_PIECES.split(brief_text or "")
              if x and x.strip()]   # "1. Stand-up (09:00): ..." -> "Stand-up (09:00): ..."
    out = []
    for card in (comp.get("content_data") or {}).get("cards") or []:
        if not isinstance(card, dict) or _card_lines(card):
            continue
        title = " ".join(str(card.get("title") or "").split())
        if len(title) < 3:
            continue
        for piece in pieces:
            if piece.lower().startswith(title.lower()) and len(piece[len(title):].split()) >= 4:
                out.append(piece)
                break
    return out


def reask_context(problems: list[dict[str, str]]) -> dict[str, Any]:
    """The `repair_context` block of the planner's user prompt, naming what to fix."""
    kinds = sorted({p["detail"].split(" ")[0] for p in problems if p["component_id"]})
    return {
        "failed_kinds": kinds or ["(whole plan)"],
        "errors": [p["detail"] for p in problems],
        "directive": ("Plan this slide again. Fill every component's content_data from the key messages "
                      "(no empty components). Slide text must be what the audience reads: never an "
                      "instruction to the presenter, never speaker notes, never 'show / highlight / break down / "
                      "walk through ...' directions. Keep the other components that were right."
                      + (" A kpi_row's kpi_values hold the figure only (e.g. '0.29x', '₹10.0L'), with the metric "
                         "name in kpi_labels; findings written as sentences belong in a card_grid (one card per "
                         "finding) or a bullet_list, not in a kpi_row." if any(p["code"] == KPI_VALUE_TEXT
                                                                              for p in problems) else "")
                      + (" A card_grid card copies its own line from the key messages into body (or bullets) when the "
                         "key messages give one; code draws only what the plan holds." if any(
                             p["code"] == CARD_LINES_DROPPED for p in problems) else "")),
    }


def problem_count(plan: dict[str, Any], brief_text: str) -> int:
    return len(find_problems(plan, brief_text))


# ── fixes ───────────────────────────────────────────────────────────────────

_TOKEN = re.compile(r"[a-z0-9₹%]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _labels(comp: dict[str, Any]) -> list[str]:
    """The item labels of a list-like component."""
    data = comp.get("content_data") or {}
    kind = comp.get("kind")
    if kind == "card_grid":
        return [str(c.get("title", "")) for c in data.get("cards") or [] if isinstance(c, dict)]
    if kind == "timeline":
        return [str(i.get("label", "")) for i in data.get("timeline_items") or [] if isinstance(i, dict)]
    key = {"process_arrow": "process_steps", "flow": "flow_steps", "bullet_list": "bullets",
           "pyramid": "pyramid_levels"}.get(kind or "")
    if not key:
        return []
    return [str(i.get("label", "") if isinstance(i, dict) else i) for i in data.get(key) or []]


def _same_label(a: set[str], b: set[str]) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= 0.6


def label_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Share of the smaller component's item labels that the other one also has (0 when either
    has fewer than 3 labels: two short lists share words by chance)."""
    la, lb = [_tokens(x) for x in _labels(a)], [_tokens(x) for x in _labels(b)]
    la, lb = [x for x in la if x], [x for x in lb if x]
    if min(len(la), len(lb)) < 3:
        return 0.0
    small, large = (la, lb) if len(la) <= len(lb) else (lb, la)
    return sum(any(_same_label(s, o) for o in large) for s in small) / len(small)


def _text_mass(comp: dict[str, Any]) -> int:
    return len(re.findall(r"\S+", str(comp.get("content_data") or {})))


def drop_duplicate_items(plan: dict[str, Any]) -> list[str]:
    """C17: two list-like components that show the same items (phase cards + chevrons of the same
    phases): keep the one with more text (a tie keeps the heavier weight) and drop the other, so
    nothing the poorer one said is lost; the kept one takes the better of the two weights."""
    notes: list[str] = []
    comps = list(plan.get("components") or [])
    dropped: set[int] = set()  # id() of a dict: plans saved before step 0 may have no component_id
    for i, a in enumerate(comps):
        for b in comps[i + 1:]:
            if id(a) in dropped or id(b) in dropped or label_overlap(a, b) < 0.7:
                continue
            keep, drop = sorted((a, b), key=lambda c: (-_text_mass(c), _WEIGHT_RANK.get(c.get("weight", "peer"), 1)))
            dropped.add(id(drop))
            if _WEIGHT_RANK.get(drop.get("weight", "peer"), 1) < _WEIGHT_RANK.get(keep.get("weight", "peer"), 1):
                keep["weight"] = drop["weight"]
            notes.append(f"dropped {drop.get('kind')} '{drop.get('component_id', '')}': it shows the same items as "
                         f"{keep.get('kind')} '{keep.get('component_id', '')}'")
            _flag(plan, PLAN_DUPLICATE_ITEMS, drop.get("component_id", ""), notes[-1])
    if dropped:
        plan["components"] = [c for c in comps if id(c) not in dropped]
    return notes


def _flag(plan: dict[str, Any], code: str, component_id: str, detail: str) -> None:
    plan.setdefault("plan_flags", []).append({"code": code, "component_id": component_id, "detail": detail})


def drop_instruction_text(plan: dict[str, Any], brief_text: str,
                          instructions: list[str] | tuple[str, ...] = ()) -> list[str]:
    """What a re-ask did not remove: instruction paragraphs and bullets, and empty captions."""
    notes: list[str] = []
    keep = []
    for comp in plan.get("components") or []:
        cid, kind = comp.get("component_id", ""), comp.get("kind")
        if kind == "caption" and is_empty(comp):
            notes.append(f"dropped empty caption '{cid}'")
            continue
        if kind in ("narrative", "caption") and any(is_instruction_text(t, brief_text, instructions)
                                                     for t in _text_items(comp)):
            notes.append(f"dropped {kind} '{cid}': it is an instruction to the presenter, not slide content")
            _flag(plan, PLAN_INSTRUCTION_TEXT, cid, notes[-1])
            continue
        if kind == "bullet_list":
            data = comp.get("content_data") or {}
            bullets = [b for b in data.get("bullets") or [] if not is_instruction_text(str(b), brief_text, instructions)]
            if len(bullets) != len(data.get("bullets") or []):
                data["bullets"] = bullets
                comp["items"] = len(bullets) or comp.get("items", 0)
                notes.append(f"dropped instruction bullets from '{cid}'")
                _flag(plan, PLAN_INSTRUCTION_TEXT, cid, notes[-1])
        keep.append(comp)
    plan["components"] = keep
    return notes


# ── free-drawn layers beside a component that shows the content (eval 2026-10-15) ──

LAYER_REPEATED = "LAYER_REPEATED"
LAYER_REPEAT_SHARE = 0.8   # share of a layer's words another visual component already shows
_NOT_VISUAL = ("title", "caption", "narrative", "layer")
_LAYER_NAME_KEYS = {"description", "visual", "visual_suggestion", "title", "center", "center_label", "annotation"}


def _layer_items(data: dict[str, Any]) -> int:
    """The most items any list field of a layer holds (nodes, layers, platforms ...): 0 = it only names a visual."""
    return max([len(v) for v in data.values() if isinstance(v, list)] or [0])


def _visual_words(comps: list[dict[str, Any]]) -> set[str]:
    return _tokens(" ".join(_strings(c.get("content_data") or {}) for c in comps))


def _strings(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_strings(v) for k, v in value.items() if k not in _NOT_TEXT)
    if isinstance(value, (list, tuple)):
        return " ".join(_strings(v) for v in value)
    return ""


def drop_repeated_layers(plan: dict[str, Any]) -> list[str]:
    """A layer is drawn free-hand by the generator, so it earns its place only with content of its own. Dropped when
    another visual component (cards, list, flow, table ...) holds content and the layer either only names a visual
    (no list of items: "Visual: Growth Impact Framework" drawn as three empty boxes, XTSY 7) or shows words that
    component already shows (TRACKING / INSIGHTS nodes beside TRACKING / INSIGHTS cards, XTSY 5). A layer that is
    the slide's only visual stays: it is the slide's picture (XTSY cover ecosystem)."""
    notes: list[str] = []
    comps = list(plan.get("components") or [])
    visuals = [c for c in comps if c.get("kind") not in _NOT_VISUAL and not is_empty(c)]
    if not visuals:
        return notes
    shown = _visual_words(visuals)
    keep = []
    for comp in comps:
        data = comp.get("content_data") or {}
        if comp.get("kind") != "layer" or not isinstance(data, dict):
            keep.append(comp)
            continue
        own = {w for w in _tokens(_strings({k: v for k, v in data.items() if k not in _LAYER_NAME_KEYS})) if len(w) > 2}
        share = len(own & shown) / len(own) if own else 0.0
        if _layer_items(data) >= 2 and share < LAYER_REPEAT_SHARE:
            keep.append(comp)
            continue
        why = (f"{share:.0%} of its words are in {visuals[0].get('kind')} '{visuals[0].get('component_id', '')}'"
               if _layer_items(data) >= 2 else "it only names a visual, with no items of its own")
        cid = comp.get("component_id", "")
        notes.append(f"dropped layer '{cid}': {why}")
        _flag(plan, LAYER_REPEATED, cid, notes[-1])
        if _WEIGHT_RANK.get(comp.get("weight", "peer"), 1) < min(_WEIGHT_RANK.get(v.get("weight", "peer"), 1)
                                                                  for v in visuals):
            heaviest = max(visuals, key=_text_mass)
            heaviest["weight"] = comp.get("weight")   # the slide's hero moves to the component that shows it
    plan["components"] = keep
    return notes


# ── thin slides ─────────────────────────────────────────────────────────────

SPARSE_UNITS = 9  # a slide worth less than this many "units" is reported thin
_LIST_KEYS = {"bullet_list": "bullets", "timeline": "timeline_items", "process_arrow": "process_steps",
              "flow": "flow_steps", "pyramid": "pyramid_levels"}


def _units(comp: dict[str, Any]) -> float:
    """A rough visual weight: a KPI tile counts 3, a card 2, a chart 10, a table at least the limit,
    list items grow with their length."""
    data = comp.get("content_data") or {}
    kind = comp.get("kind")
    if kind == "kpi_row":
        return 3.0 * len(data.get("kpi_values") or data.get("kpi_labels") or [])
    if kind == "card_grid":
        return 2.0 * len(data.get("cards") or [])
    if kind == "chart":
        return 10.0
    if kind == "table":
        # a table grows to fill the slide, so a table slide is never thin by itself
        return max(float(SPARSE_UNITS), len(data.get("table_rows") or []) * max(1, len(data.get("table_columns") or [])) / 3)
    if kind == "narrative":
        return 2.0
    if kind in ("matrix", "tree", "layer"):
        return 8.0
    key = _LIST_KEYS.get(kind or "")
    if key:
        items = data.get(key) or []
        if not items:
            return 0.0
        words = len(re.findall(r"\S+", str(items))) / len(items)
        return len(items) * (1 + min(words, 24) / 12)
    return 0.0


def sparse_flag(plan: dict[str, Any]) -> dict[str, str] | None:
    """SLIDE_SPARSE for a content / data slide worth fewer than SPARSE_UNITS (an estimate: the
    renderer's own SLIDE_SPARSE, content filling < 55% of the body, arrives with blocks)."""
    if plan.get("slide_type") not in ("content", "data"):
        return None
    comps = plan.get("components") or []
    if not comps or all(is_empty(c) for c in comps if c.get("kind") != "title"):
        return None  # empty, not thin: PLAN_EMPTY already says it
    total = sum(_units(c) for c in comps if c.get("kind") not in ("title", "caption"))
    if total >= SPARSE_UNITS:
        return None
    return {"code": SLIDE_SPARSE, "component_id": "",
            "detail": f"thin slide: about {total:.1f} units of content (limit {SPARSE_UNITS})"}


# ── dense slides (rule K4, docs/presentation-rules-draft-2026-10-15.md) ─────

CARDS_TO_LIST = "CARDS_TO_LIST"
# K4 thresholds, set on the saved plans (docs/eval/structure-loss/README.md, "K4"): the agency Keyword & City slide's
# other components hold 103-132 words in all 5 saved plans; every other slide with a 6+ card grid holds <= 53.
DENSE_REST_WORDS = 80   # words in the slide's other components that make it dense
MANY_CARDS = 6          # a grid of at least this many cards ...
SHORT_CARD_WORDS = 6    # ... most of them (2 in 3) with at most this many words of body and bullets
_NOT_TEXT = {"tone", "icon", "key_phrase", "card_layout", "chart_type", "direction", "layout", "body_source",
             "kpi_directions", "kpi_tones", "kpi_icons", "focus_card", "x", "y"}


def content_words(value: Any) -> int:
    """Words the audience reads in a content_data value (a number counts one; tones, icons and layout keys none)."""
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, dict):
        return sum(content_words(v) for k, v in value.items() if k not in _NOT_TEXT)
    if isinstance(value, (list, tuple)):
        return sum(content_words(v) for v in value)
    return 1 if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def rest_words(plan: dict[str, Any], comp: dict[str, Any]) -> int:
    """How full the slide is without `comp`: the words of its other components (headline and captions aside)."""
    return sum(content_words(c.get("content_data") or {}) for c in plan.get("components") or []
               if c is not comp and c.get("kind") not in ("title", "caption"))


def cards_to_list(plan: dict[str, Any]) -> list[str]:
    """K4: on a slide already full, a grid of many short cards becomes a bullet_list. Nine cards beside a table, two
    lists and three paragraphs made POM squeeze a text box to zero height (agency Keyword & City, 2026-10-13 / 15).
    Each card becomes one item, "title: body; bullets", word for word; cards with the same lines share one item
    ("Hyderabad, Chennai: Needs immediate review"). Grids of steps or a matrix, and grids on a slide with room, stay
    cards: they fill the slide's spare space."""
    notes: list[str] = []
    for comp in plan.get("components") or []:
        data = comp.get("content_data") or {}
        if comp.get("kind") != "card_grid" or (data.get("card_layout") or "grid") != "grid":
            continue
        cards = [c for c in data.get("cards") or [] if isinstance(c, dict) and str(c.get("title") or "").strip()]
        short = sum(len(" ".join(_card_lines(c)).split()) <= SHORT_CARD_WORDS for c in cards)
        rest = rest_words(plan, comp)
        if len(cards) < MANY_CARDS or 3 * short < 2 * len(cards) or rest < DENSE_REST_WORDS:
            continue
        groups: dict[str, list[str]] = {}
        for card in cards:
            groups.setdefault("; ".join(_card_lines(card)), []).append(" ".join(str(card["title"]).split()))
        bullets = [f"{', '.join(titles)}: {lines}" if lines else ", ".join(titles) for lines, titles in groups.items()]
        comp["kind"] = "bullet_list"
        comp["content_data"] = {"bullets": bullets}
        comp["items"] = comp["count"] = len(bullets)
        comp["design_hint"] = "bold each item's lead-in"
        cid = comp.get("component_id", "")
        notes.append(f"{cid}: card_grid of {len(cards)} short cards on a full slide ({rest} words in the other "
                     f"components) -> bullet_list of {len(bullets)} items")
        _flag(plan, CARDS_TO_LIST, cid, notes[-1])
    return notes


_TONES = {"good": "good", "positive": "good", "bad": "bad", "negative": "bad", "watch": "watch", "warning": "watch"}


# Role words a design hint uses for a tone (hint-capabilities sentiment: losses / leaks / risks, wins / fixes, watch).
_HINT_ROLES = (("bad", re.compile(r"\bnegative\b|\bred\b|\bloss(?:es)?\b|\bleaks?\b|\brisks?\b", re.I)),
               ("good", re.compile(r"\bpositive\b|\bgreen\b|\bgains?\b|\bwins?\b", re.I)),
               ("watch", re.compile(r"\bwarning\b|\bamber\b|\bwatch\b|\bcaution\b", re.I)))
_EVERY_ITEM = re.compile(r"\b(?:all|every|each|both)\s+(?:(?:the|these|those|kpi|of\s+the)\s+)*(?:(\w[\w%/-]*)\s+)?"
                         r"(?:tiles?|items?|metrics?|kpis?|values?|cards?)\b", re.I)
_HINT_STOP = re.compile(r",|\b(?:and|while|but|keep|keeping|except|other|others)\b", re.I)
_HINT_FOR = re.compile(r"\bfor\b", re.I)   # "green for high ROAS": the role names the item after it
_HINT_REACH = 80   # a role word after an item, at most this many characters on ("A and B in positive")
_HINT_LEAD = 25    # a role word before an item, this close and with no "and / keep / while" between ("red on CPC")


def _hint_names(labels: list[str]) -> list[list[str]]:
    """The names a hint may use for each item: the label, the label before " for " / " (" ("Allowable CPC"), and
    an upper-case token only this label has ("FLIPCART" in "FLIPCART ROAS")."""
    tokens = [set(re.findall(r"\b[A-Z]{2,8}\b", lab)) for lab in labels]
    count = {t: sum(t in ts for ts in tokens) for ts in tokens for t in ts}
    out = []
    for lab, ts in zip(labels, tokens):
        names = [lab] if lab else []
        short = re.split(r"\s+for\s+|\s*\(", lab, maxsplit=1)[0].strip()
        if short and short != lab:
            names.append(short)
        names += sorted(t for t in ts if count[t] == 1 and t != lab)
        out.append(names)
    return out


def tones_from_hint(comp: dict[str, Any]) -> list[str]:
    """kpi_tones read from a kpi_row's design_hint, for a row the planner gave none (wide eval P2, 2026-10-13).

    Per clause (split at ; and sentence ends) every place an item is named takes the nearest role word after it
    within _HINT_REACH characters ("color the CPC row in negative", "ARR and NRR as positive"), or one just before
    it with no comma or "and / keep / while" between ("negative color on CPC"; "green for ROAS" wins outright); of
    several places the nearest wins. A name inside a longer item's name does not count ("CPC" in "Allowable CPC").
    When no item is named, a clause with "all / each / both [X] tiles" and one role gives that role to every item
    (with X: the items whose label has X). The emphasis item is not touched."""
    data = comp.get("content_data") or {}
    labels = [str(x or "").strip() for x in data.get("kpi_labels") or []]
    n = len(data.get("kpi_values") or [])
    names = _hint_names(labels[:n])
    best: dict[int, tuple[int, str]] = {}
    clauses = re.split(r";|\.\s", comp.get("design_hint") or "")
    for clause in clauses:
        roles = sorted((m.start(), m.end(), tone) for tone, rx in _HINT_ROLES for m in rx.finditer(clause))
        if not roles:
            continue
        spans = [(m.start(), m.end(), i) for i, ns in enumerate(names) for nm in ns
                 for m in re.finditer(r"(?<!\w)" + re.escape(nm) + r"(?!\w)", clause, re.I)]
        spans = [s for s in spans if not any(o[2] != s[2] and o[0] <= s[0] and s[1] <= o[1] and o[1] - o[0] > s[1] - s[0]
                                             for o in spans)]
        for start, end, i in spans:
            found = []
            after = [r for r in roles if r[0] >= end]
            if after and after[0][0] - end <= _HINT_REACH:
                found.append((after[0][0] - end, after[0][2]))
            before = [r for r in roles if r[1] <= start]
            gap = clause[before[-1][1]:start] if before else ""
            if before and len(gap) <= _HINT_LEAD and not _HINT_STOP.search(gap):
                found.append((0 if _HINT_FOR.search(gap) else len(gap), before[-1][2]))
            for cand in found:
                if i not in best or cand[0] < best[i][0]:
                    best[i] = cand
    tones = [best[i][1] if i in best else "" for i in range(n)]
    if not any(tones):
        for clause in clauses:
            kinds = {tone for tone, rx in _HINT_ROLES if rx.search(clause)}
            every = _EVERY_ITEM.search(clause)
            if every and len(kinds) == 1:   # "all ROAS tiles": the items whose label has ROAS; "all tiles": every item
                tone, word = kinds.pop(), (every.group(1) or "").lower()
                return [tone if not word or word in lab.lower() else "" for lab in (labels + [""] * n)[:n]]
    return tones


# Look cues a design hint uses, per tile-node variant (tile-variant-choice spec 2026-10-26 §4, option A). A plain
# "border" is not a cue ("a clear border": the default hairline); a bar needs accent / coloured / left with it.
_LOOK_CUES = {
    "bar": re.compile(r"\b(?:accent|colou?red|left|side)[\s-]+(?:borders?|bars?|edges?|stripes?|lines?|rules?)\b", re.I),
    "dot": re.compile(r"\b(?:status\s+)?dots?\b", re.I),
    "dark": re.compile(r"\bdark\b|\binvert", re.I),
    "tint": re.compile(r"\b(?:tint(?:s|ed)?|fill(?:ed)?|shade[ds]?|shading)\b", re.I),
    "numbered": re.compile(r"\bnumbered\b|\bnumerals?\b|\b0?1\s*[,·/]\s*0?2\b", re.I),
}
_LOOK_NOT = re.compile(r"\b(?:no|without|avoid|not)\b[\w\s/-]{0,14}$", re.I)   # "no status dots", "without an accent bar"
# cue -> variant, in priority order (spec §4: bar > dot > filled; accent_top > numerals). No card tint: the default
# `lifted` card is already tinted by its tone (census 2026-10-26: the one card tint cue was a heatmap inside a card)
_KPI_LOOKS = (("bar", "bar"), ("dot", "dot"), ("tint", "filled"))
_CARD_LOOKS = (("bar", "accent_top"), ("numbered", "numerals"))


def look_from_hint(comp: dict[str, Any]) -> dict[str, Any]:
    """The tile-node look a kpi_row's or card_grid's design_hint asks for, for a bare <KpiGrid> / <CardGrid>
    (tile-variant-choice spec 2026-10-26, option A; read by tiles.expand / cards.expand, the LLM's variant wins).

    Returns {"group": variant or None, "items": {index: variant}, "emphasis": variant or None, "cues": [...]}.
    Per clause (as tones_from_hint) each cue applies to the items the clause names; a clause that names none gives
    it to the whole group. KPI: accent border / bar -> bar, status dot -> dot, tint / shade (only with tones) ->
    filled; an item keeps its own look only when it ranks above the group's ("status dot beside each label" and
    "NRR shaded positive": dots everywhere, the dot takes the tone). Dark / inverted -> `emphasis` inverted, for the
    plan's emphasis item (code checks it is one). Cards: only a group look (a lifted card next to a flat one reads
    as two card types), from a clause naming every card or none ("accent border on the 'Month 3 Scale' card" asks
    for one card: the focus card covers it): accent bar -> accent_top, numbered on a grid -> numerals (steps
    already number their cards)."""
    kind = comp.get("kind")
    data = comp.get("content_data") or {}
    out: dict[str, Any] = {"group": None, "items": {}, "emphasis": None, "cues": []}
    hint = " ".join(str(comp.get("design_hint") or "").split())
    if kind not in ("kpi_row", "card_grid") or not hint:
        return out
    if kind == "kpi_row":
        labels = [str(x or "").strip() for x in data.get("kpi_labels") or []][:len(data.get("kpi_values") or [])]
        toned = any(data.get("kpi_tones") or []) or any(tones_from_hint(comp))
        looks = _KPI_LOOKS
    else:
        cards = [c for c in data.get("cards") or [] if isinstance(c, dict)]
        labels = [str(c.get("title") or "").strip() for c in cards]
        toned = any(c.get("tone") for c in cards)
        looks = _CARD_LOOKS
    names = _hint_names(labels)
    group: set[str] = set()
    items: dict[int, set[str]] = {}
    for clause in re.split(r";|\.\s", hint):
        cues = {cue for cue, rx in _LOOK_CUES.items()
                if any(not _LOOK_NOT.search(clause[:m.start()]) for m in rx.finditer(clause))}
        if not cues:
            continue
        out["cues"] += sorted(cues - set(out["cues"]))
        if "dark" in cues and kind == "kpi_row":
            out["emphasis"] = "inverted"
        spans = [(m.start(), m.end(), i) for i, ns in enumerate(names) for nm in ns
                 for m in re.finditer(r"(?<!\w)" + re.escape(nm) + r"(?!\w)", clause, re.I)]
        named = {s[2] for s in spans if not any(o[2] != s[2] and o[0] <= s[0] and s[1] <= o[1]
                                                 and o[1] - o[0] > s[1] - s[0] for o in spans)}
        if kind == "card_grid" and named and len(named) < len(labels):
            continue
        for i in (named if kind == "kpi_row" and named else [None]):
            (group if i is None else items.setdefault(i, set())).update(cues)

    def pick(cues: set[str]) -> int:
        """Rank of the look the cues ask for (index in `looks`), len(looks) for none."""
        return next((r for r, (cue, _) in enumerate(looks) if cue in cues and (cue != "tint" or toned)
                     and not (cue == "numbered" and (data.get("card_layout") or "grid") != "grid")), len(looks))
    top = pick(group)
    out["group"] = looks[top][1] if top < len(looks) else None
    out["items"] = {i: looks[r][1] for i, cs in sorted(items.items()) if (r := pick(cs)) < top}
    return out


def settle_kpi_tones(comp: dict[str, Any]) -> list[str]:
    """A kpi_row's kpi_tones as code reads them (tile-nodes spec §6): one per value, good / bad / watch / "",
    synonyms mapped, anything else blank. A row with no tone at all takes the tones its design hint names
    (`tones_from_hint`), else keeps no kpi_tones. Returns the notes (a tone taken from the hint)."""
    data = comp.get("content_data") or {}
    if comp.get("kind") != "kpi_row" or not data.get("kpi_values"):
        return []
    raw = data.get("kpi_tones") if isinstance(data.get("kpi_tones"), list) else []
    n = len(data.get("kpi_values") or [])
    tones = [_TONES.get(str(t).strip().lower(), "") for t in raw[:n]] + [""] * max(0, n - len(raw))
    if any(tones):
        data["kpi_tones"] = tones
        return []
    data.pop("kpi_tones", None)
    hinted = tones_from_hint(comp)
    if not any(hinted):
        return []
    data["kpi_tones"] = hinted
    labels = list(data.get("kpi_labels") or [])
    named = ", ".join(f"{labels[i] if i < len(labels) else i} {t}" for i, t in enumerate(hinted) if t)
    return [f"{comp.get('component_id', '')}: kpi_tones taken from the design hint ({named}); the planner wrote none"]


def settle_kpi_icons(comp: dict[str, Any]) -> None:
    """A kpi_row's kpi_icons as code reads them, as card icons (settle_card_fields): a real icon name per value
    (icons.canonical_icon_name) on every item, else none kept. Same-plan check 2026-10-14, pair 3.1: the
    element-ref side drew icons on its KPI tiles, the tile side had none to draw."""
    data = comp.get("content_data") or {}
    if comp.get("kind") != "kpi_row" or "kpi_icons" not in data:
        return
    raw = data.pop("kpi_icons")
    n = len(data.get("kpi_values") or [])
    if not isinstance(raw, list) or not n or len(raw) < n:
        return
    from src.compiler.icons import canonical_icon_name, valid_icon_names
    names = [canonical_icon_name(str(x or "")) for x in raw[:n]]
    if all(nm in valid_icon_names() for nm in names):
        data["kpi_icons"] = names


def _card_lines(card: dict[str, Any]) -> list[str]:
    bullets = card.get("bullets") if isinstance(card.get("bullets"), list) else []
    return [str(x) for x in [card.get("body") or "", *bullets] if str(x).strip()]


def settle_card_fields(comp: dict[str, Any]) -> None:
    """A card_grid's per-card tone / key_phrase and its focus_card as code reads them (tile-nodes spec §11):
    tones as kpi_tones (none kept when all blank); a key_phrase only when its words are in the card's body
    or bullets (case and spacing taken from there), else dropped; focus_card only as an index in range, not on a
    matrix (deferred), and not on the last step (the destination is the default there)."""
    data = comp.get("content_data") or {}
    if comp.get("kind") != "card_grid":
        return
    cards = [c for c in data.get("cards") or [] if isinstance(c, dict)]
    tones = [_TONES.get(str(c.get("tone") or "").strip().lower(), "") for c in cards]
    for c, t in zip(cards, tones):
        if any(tones):
            c["tone"] = t
        else:
            c.pop("tone", None)
    for c in cards:
        phrase = " ".join(str(c.get("key_phrase") or "").split())
        c.pop("key_phrase", None)
        if not phrase:
            continue
        for line in _card_lines(c):
            m = re.search(r"\s+".join(map(re.escape, phrase.split())), line, re.I)
            if m and m.group(0).strip() != line.strip():   # a phrase that is the whole line marks nothing
                c["key_phrase"] = m.group(0)
                break
    # icons: a real icon name (icons.canonical_icon_name), on every card or on none (a grid with some icons reads as
    # missing ones; blind marks 2026-10-13: icons were the second reason the LLM's cards won)
    from src.compiler.icons import canonical_icon_name, valid_icon_names
    names = [canonical_icon_name(str(c.get("icon") or "")) for c in cards]
    ok = bool(cards) and all(n in valid_icon_names() for n in names)
    for c, n in zip(cards, names):
        if ok:
            c["icon"] = n
        else:
            c.pop("icon", None)
    raw = data.pop("focus_card", None)
    try:
        focus = int(raw) if raw is not None and str(raw).strip() != "" and not isinstance(raw, bool) else None
    except (TypeError, ValueError):
        focus = None
    layout = data.get("card_layout") or "grid"
    if focus is not None and 0 <= focus < len(cards) and layout != "matrix" \
            and not (layout == "steps" and focus == len(cards) - 1):
        data["focus_card"] = focus


# ── entry point ─────────────────────────────────────────────────────────────

def finalize_plan(plan: dict[str, Any], brief_text: str, instructions: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Run every code fix and the thin-slide report on a finished plan, in place.
    Returns the plain-words notes; `plan["plan_flags"]` lists what was found."""
    notes = drop_instruction_text(plan, brief_text, instructions)
    notes += drop_repeated_bodies(plan)
    notes += drop_shared_card_lines(plan, brief_text)
    notes += drop_duplicate_items(plan)
    notes += drop_repeated_layers(plan)
    notes += cards_to_list(plan)
    for comp in plan.get("components") or []:
        if is_empty(comp):
            _flag(plan, PLAN_EMPTY, comp.get("component_id", ""), f"{comp.get('kind')} has no content")
    if not plan.get("components"):
        _flag(plan, PLAN_EMPTY, "", "the plan has no components")
    for comp in plan.get("components") or []:
        notes += settle_kpi_tones(comp)
        settle_kpi_icons(comp)
        settle_card_fields(comp)
        vals = (comp.get("content_data") or {}).get("kpi_values") or [] if comp.get("kind") == "kpi_row" else []
        if any(is_sentence(str(v)) for v in vals):
            _flag(plan, KPI_VALUE_TEXT, comp.get("component_id", ""), "kpi_values hold sentences, not figures")
    sparse = sparse_flag(plan)
    if sparse:
        plan.setdefault("plan_flags", []).append(sparse)
    return notes
