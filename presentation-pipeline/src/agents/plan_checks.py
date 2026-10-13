"""Code checks on one slide plan (§14.6 step 0; checks C14-C17 of docs/plan-reviewer-loop.md).

The renderer draws exactly what a plan holds, so a plan that is empty, thin, repeats itself or
carries planner instructions shows up on the slide. Two kinds of check:

* **problems** (`find_problems`) - a re-ask is justified: an empty component (`PLAN_EMPTY`) or
  text that is an instruction to the presenter, not slide content (`PLAN_INSTRUCTION_TEXT`).
* **fixes** (`finalize_plan`) - code repairs what is left: drops an empty caption and any
  instruction text still there, drops a duplicate component (`PLAN_DUPLICATE_ITEMS`) and a card
  body that repeats its title, and flags a thin slide (`SLIDE_SPARSE`, report only).

Every flag lands in `SlidePlan.plan_flags` as {code, component_id?, detail}; each fix also
writes a plain-words note into `capacity_fixes`, like the other plan checks. Thresholds are an
estimate set on the 17 hold-out plans (docs/derived-blocks-planning-2026-10-06.md §2).
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.written_lines import drop_repeated_bodies, from_brief
from src.compiler.value_parts import is_sentence

PLAN_EMPTY = "PLAN_EMPTY"
PLAN_INSTRUCTION_TEXT = "PLAN_INSTRUCTION_TEXT"
PLAN_DUPLICATE_ITEMS = "PLAN_DUPLICATE_ITEMS"
SLIDE_SPARSE = "SLIDE_SPARSE"
KPI_VALUE_TEXT = "KPI_VALUE_TEXT"   # a kpi_row value that is a sentence, not a figure (KPI pilot 2026-10-11)
REASK_CODES = (PLAN_EMPTY, PLAN_INSTRUCTION_TEXT, KPI_VALUE_TEXT)

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

# a label that marks presenter notes ("Speaker Notes: Lead with ...", "Talking points: ..."): always instruction text
_NOTES_LABEL = re.compile(r"^\W*((speaker|presenter|slide)\s+notes?|talking points?)\s*[:\-–—]", re.I)
# a bare "Note: ..." is NOT a label: it is a normal footnote prefix (launch 6: "Note: SOC2 + HIPAA certification ...")
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


def is_instruction_text(text: str, brief_text: str) -> bool:
    """True when `text` is a direction to the presenter or slide builder, not audience content."""
    t = (text or "").strip()
    if not t:
        return False
    if _NOTES_LABEL.match(t) or _PRESENTER_VERB.match(t) or _ADDRESSES_SLIDE.search(t):
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

def find_problems(plan: dict[str, Any], brief_text: str) -> list[dict[str, str]]:
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
            if is_instruction_text(item, brief_text):
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
    return problems


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
                                                                              for p in problems) else "")),
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


def drop_instruction_text(plan: dict[str, Any], brief_text: str) -> list[str]:
    """What a re-ask did not remove: instruction paragraphs and bullets, and empty captions."""
    notes: list[str] = []
    keep = []
    for comp in plan.get("components") or []:
        cid, kind = comp.get("component_id", ""), comp.get("kind")
        if kind == "caption" and is_empty(comp):
            notes.append(f"dropped empty caption '{cid}'")
            continue
        if kind in ("narrative", "caption") and any(is_instruction_text(t, brief_text) for t in _text_items(comp)):
            notes.append(f"dropped {kind} '{cid}': it is an instruction to the presenter, not slide content")
            _flag(plan, PLAN_INSTRUCTION_TEXT, cid, notes[-1])
            continue
        if kind == "bullet_list":
            data = comp.get("content_data") or {}
            bullets = [b for b in data.get("bullets") or [] if not is_instruction_text(str(b), brief_text)]
            if len(bullets) != len(data.get("bullets") or []):
                data["bullets"] = bullets
                comp["items"] = len(bullets) or comp.get("items", 0)
                notes.append(f"dropped instruction bullets from '{cid}'")
                _flag(plan, PLAN_INSTRUCTION_TEXT, cid, notes[-1])
        keep.append(comp)
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


# ── entry point ─────────────────────────────────────────────────────────────

def finalize_plan(plan: dict[str, Any], brief_text: str) -> list[str]:
    """Run every code fix and the thin-slide report on a finished plan, in place.
    Returns the plain-words notes; `plan["plan_flags"]` lists what was found."""
    notes = drop_instruction_text(plan, brief_text)
    notes += drop_repeated_bodies(plan)
    notes += drop_duplicate_items(plan)
    for comp in plan.get("components") or []:
        if is_empty(comp):
            _flag(plan, PLAN_EMPTY, comp.get("component_id", ""), f"{comp.get('kind')} has no content")
    if not plan.get("components"):
        _flag(plan, PLAN_EMPTY, "", "the plan has no components")
    for comp in plan.get("components") or []:
        notes += settle_kpi_tones(comp)
        vals = (comp.get("content_data") or {}).get("kpi_values") or [] if comp.get("kind") == "kpi_row" else []
        if any(is_sentence(str(v)) for v in vals):
            _flag(plan, KPI_VALUE_TEXT, comp.get("component_id", ""), "kpi_values hold sentences, not figures")
    sparse = sparse_flag(plan)
    if sparse:
        plan.setdefault("plan_flags", []).append(sparse)
    return notes
