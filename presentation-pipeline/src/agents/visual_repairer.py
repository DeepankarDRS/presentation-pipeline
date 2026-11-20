"""Visual fixer: one fix per slide after the critic (2026-11-20 redesign).

  fix / relayout -> a reasoning model writes search/replace edits on the XML the slide was DRAWN from (after
                    fit-grow, compile-pom.js drawn.xml). Code applies them (each `old` must match exactly once),
                    compiles with fit-grow off, so every value the fixer wrote is drawn as written; a failed match or
                    compile goes back to the model once.
  regenerate     -> the plan is wrong: re-plan + generate the slide, through the validator as a new slide.

Code then keeps the fix only if nothing measured got worse (compiles; geometry-audit errors and low-contrast texts
no more than before; POM did not shrink the slide; no word or number inside a code-drawn component changed; no
number that was not on the slide). Otherwise the slide stays as it was.

Reads:  visual_critic_result, compile_result, normalize_result, layout_issues, slide_plans, contract, theme
Writes: current_xml, compile_result, normalize_result, validate_result, layout_issues, visual_repair_count,
        visual_repair_outcome, generation_history (slide_plans, contract on a regenerate)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from src.agents import slide_facts
from src.agents.context_builder import build_contract
from src.agents.critic import slide_context
from src.agents.repairer import _build_repair_context, regenerate_prompts, replan
from src.agents.validator import validate_slide
from src.compiler.compiler_client import FIT_GROW_OFF, CompilerError, compile_xml, drawn_xml
from src.compiler.geometry_audit import audit_run_folder
from src.compiler.layout_audit import audit_layout
from src.state import AttemptRecord, PresentationState
from src.utils.llm_client import extract_usage, get_llm, unpack_raw, usage_record

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
# measured defects a fix may not add: spills / collisions / off-slide at tier error, text overflow, placeholders
GEOM_ERRORS = {"GEOM_SPILL", "GEOM_COLLISION", "GEOM_OFF_SLIDE"}
GEOM_ANY = {"GEOM_TEXT_OVERFLOW", "PLACEHOLDER_TEXT"}
_THEME = re.compile(r"<Theme[^>]*/>")


class Edit(BaseModel):
    old: str = Field(description="Exact text from the XML, matching exactly once (include an id to make it unique).")
    new: str = Field(description="What replaces it.")


class FixerOutput(BaseModel):
    plan: str = Field(description="2-4 sentences: what you change and why it fixes the findings.")
    edits: list[Edit] = Field(description="Applied in order, each to the result of the ones before.")


SYSTEM = """You fix one presentation slide written in POM XML (a flexbox layout language that compiles to PowerPoint, 1280x720 px).
A reviewer and code checks found problems on the rendered slide. You get the findings, what code measured, every
component's id and box, and the exact XML the slide was drawn from. Fix the findings with small search/replace edits.

THE XML
- Each plan component carries an id: a code-drawn one on its outer box (cmp-<id>, tbl-<id>, kpig-<id>, cardg-<id>),
  a hand-drawn one as id="<component id>". Inner parts of code-drawn components carry their own ids (kpil-, kpiv-,
  card-, lst-): you may restyle them.
- Values are final: code does NOT re-fit the slide after you. Every size, gap, padding, font size, colour and grow
  you write is drawn exactly as written. Text needs fontSize >= 14.
- Lay out with flex: VStack / HStack, w / h (px, "%", or "max"), grow, gap, padding, alignItems, justifyContent.
  Never absolute positions. Colours as the theme's $tokens only (the token names are listed).
- Keep every <!-- ... --> comment that is in the XML: code reads them when it draws.

RULES
- Never change, add or drop a word or number inside a code-drawn component, never invent text or numbers anywhere,
  and never remove a plan component. You may remove a hand-drawn box only when a finding calls it filler.
- A component that needs more room: give it room (re-balance grow / w between bands, put side-by-side parts in one
  column or the reverse, a tighter gap or padding elsewhere, a smaller font down to 14 inside it). Fix the cause,
  not only the symptom; keep peers looking alike.
- Each `old` must appear exactly once in the XML at the time it is applied: copy it exactly, with an id or a
  distinctive attribute to make it unique. Keep edits small; do not rewrite the whole slide."""


def _texts(xml: str, ids: list[str]) -> str | None:
    """All the text inside the elements with these ids, in order; None when one is gone."""
    try:
        root = ET.fromstring("<r>" + _THEME.sub("", xml) + "</r>")
    except ET.ParseError:
        return None
    found = {el.get("id"): " ".join(" ".join(el.itertext()).split()) for el in root.iter() if el.get("id") in ids}
    return None if set(ids) - set(found) else " | ".join(found[i] for i in ids)


def apply_edits(xml: str, edits: list[Edit]) -> tuple[str, list[str]]:
    """Apply in order; each `old` must match exactly once. Returns (xml, errors); on any error the xml is unchanged."""
    out, errors = xml, []
    for k, e in enumerate(edits, 1):
        n = out.count(e.old) if e.old else 0
        if n != 1:
            errors.append(f"edit {k}: `old` found {n} times (must be exactly once): {e.old[:120]!r}")
            continue
        out = out.replace(e.old, e.new, 1)
    return (xml, errors) if errors else (out, [])


def _measure(compile_result: dict, layout_issues: list[dict]) -> dict[str, int]:
    warns = {w.get("code") for w in compile_result.get("warnings") or []}
    return {"geometry errors": sum((i.get("code") in GEOM_ERRORS and i.get("tier") == "error")
                                   or i.get("code") in GEOM_ANY for i in layout_issues),
            "low contrast": sum(i.get("code") == "LOW_CONTRAST" for i in layout_issues),
            "slide shrunk by POM": int("AUTOFIT_SHRANK" in warns)}


def check(before_xml: str, after_xml: str, comps: list[slide_facts.Component], before: dict[str, int],
          after: dict[str, int]) -> list[str]:
    """Why the fix is worse ([] = keep it)."""
    why = [f"{k} {before.get(k, 0)} -> {v}" for k, v in after.items() if v > before.get(k, 0)]
    for c in comps:
        if c.by == "code" and _texts(before_xml, c.box_ids) != _texts(after_xml, c.box_ids):
            why.append(f"the words or numbers of {c.id} changed (or its box is gone)")
    nums = lambda x: set(re.findall(r"\d+(?:[.,]\d+)?", re.sub(r"<[^>]*>", " ", x)))
    new = nums(after_xml) - nums(before_xml)
    if new:
        why.append(f"numbers that were not on the slide: {sorted(new)[:5]}")
    return why


def _fix_prompt(state: PresentationState, xml: str, comps, facts, issues, hints, errors: list[str]) -> str:
    theme = state.get("theme_element", "")
    tokens = ", ".join(f"${t}" for t in re.findall(r'\b(\w+)="[0-9A-Fa-f]{6}"', theme))
    lines = ["## FINDINGS (fix these)"] + [f"- [{i['severity']}] {i['description']}" for i in issues]
    if hints.get("observations"):
        lines += ["", f"Reviewer's view of the slide: {hints['observations']}"]
    lines += ["", "## COMPONENTS (box x, y, w, h in px)", slide_facts.table(comps),
              "", "## MEASURED FACTS"] + [f"- {f.text}" for f in facts or []] + ([] if facts else ["- none"])
    lines += ["", f"## THEME TOKENS\n{tokens}"]
    if errors:
        lines += ["", "## YOUR LAST EDITS FAILED (fix them; the XML below is unchanged)"] + [f"- {e}" for e in errors]
    lines += ["", "## THE XML THE SLIDE WAS DRAWN FROM (edit this)", xml]
    return "\n".join(lines)


def _fix(state: PresentationState, out_dir: Path, issues: list[dict], hints: dict) -> dict[str, Any]:
    """The search/replace fix on the drawn XML. Returns the kept result's state updates, or why it was not kept."""
    cr = state.get("compile_result") or {}
    before_xml = drawn_xml(cr)
    if not before_xml:
        return {"outcome": "error", "why": ["no drawn.xml for this slide"], "usage": []}
    _plan, comps, facts = slide_context(state)
    before = _measure(cr, state.get("layout_issues") or [])
    llm = get_llm("repairer").with_structured_output(FixerOutput, method="json_schema", include_raw=True)
    usages, errors = [], []
    for attempt in (1, 2):   # one retry, for a failed match or compile
        prompt = _fix_prompt(state, before_xml, comps, facts, issues, hints, errors)
        result, usage = unpack_raw(llm.invoke([{"role": "system", "content": SYSTEM},
                                               {"role": "user", "content": prompt}]))
        usages.append(usage)
        logger.info(f"visual_repairer: fix attempt {attempt}: {result.plan} ({len(result.edits)} edit(s))")
        xml, errors = apply_edits(before_xml, result.edits)
        if errors:
            logger.info("visual_repairer: " + "; ".join(errors))
            continue
        if xml.strip() == before_xml.strip():
            return {"outcome": "noop", "why": ["no change"], "usage": usages}
        if FIT_GROW_OFF not in xml:
            xml = FIT_GROW_OFF + "\n" + xml
        try:
            new_cr = compile_xml(xml, out_dir / f"try-{attempt}")
        except CompilerError as exc:
            errors = [f"compile harness: {exc}"]
            continue
        if not new_cr.get("ok"):
            errors = [f"compile: {d.get('type')}: {d.get('message')}" for d in new_cr.get("diagnostics", [])][:5]
            logger.info("visual_repairer: " + "; ".join(errors))
            continue
        plan = (state.get("slide_plans") or [{}])[state.get("current_slide_index", 0)] or {}
        after_issues = audit_layout(xml) + audit_run_folder(out_dir / f"try-{attempt}", slide_type=plan.get("slide_type", ""),
                                                            brief=state.get("raw_request") or "")
        why = check(before_xml, xml, comps, before, _measure(new_cr, after_issues))
        if why:
            return {"outcome": "rolled_back", "why": why, "usage": usages}
        norm = dict(state.get("normalize_result") or {}, cleaned_xml=xml, tags_xml="")
        return {"outcome": "improved", "usage": usages,
                "updates": {"current_xml": xml, "compile_result": new_cr, "normalize_result": norm,
                            "layout_issues": after_issues}}
    return {"outcome": "error", "why": errors, "usage": usages}


def _regenerate(state: PresentationState, out_dir: Path, issues: list[dict], hints: dict) -> dict[str, Any]:
    """Re-plan + generate the slide; kept when it compiles and nothing measured got worse."""
    idx = state.get("current_slide_index", 0)
    plans = list(state.get("slide_plans") or [])
    problems = [f"VISUAL_{i['severity'].upper()}: {i['description']}" for i in issues]
    if hints.get("regenerate_reason"):
        problems.insert(0, f"PLAN: {hints['regenerate_reason']}")
    ctx = _build_repair_context(plans[idx], problems, visual_failure=True, has_compile_errors=False)
    new_plan, plan_usage = replan(state, plans[idx], idx, ctx)
    contract = build_contract(new_plan, state.get("resolved_theme") or {})
    system_prompt, user_prompt = regenerate_prompts(state, new_plan, contract, idx, problems)
    response = get_llm("generator").invoke([{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_prompt}])
    usages = [extract_usage(response)]
    plans[idx] = new_plan
    checked = validate_slide({**state, "current_xml": response.content, "slide_plans": plans, "contract": contract},
                             out_dir)
    new_cr = checked.get("compile_result") or {}
    if not new_cr.get("ok"):
        return {"outcome": "error", "why": ["the regenerated slide did not compile"], "usage": usages,
                "plan_usage": plan_usage}
    worse = [f"{k} {v0} -> {v1}" for k, v0, v1 in
             ((k, v, _measure(new_cr, checked.get("layout_issues") or [])[k])
              for k, v in _measure(state.get("compile_result") or {}, state.get("layout_issues") or []).items()) if v1 > v0]
    if worse:
        return {"outcome": "rolled_back", "why": worse, "usage": usages, "plan_usage": plan_usage}
    return {"outcome": "improved", "usage": usages, "plan_usage": plan_usage,
            "updates": {"current_xml": response.content, "compile_result": new_cr,
                        "normalize_result": checked.get("normalize_result"),
                        "validate_result": checked.get("validate_result"),
                        "layout_issues": checked.get("layout_issues", []), "slide_plans": plans, "contract": contract}}


def visual_repairer_node(state: PresentationState) -> dict[str, Any]:
    """One fix for what the critic found; kept only when the code checks pass."""
    vcr = state.get("visual_critic_result") or {}
    issues = [i for i in vcr.get("issues") or [] if i.get("severity") in ("high", "medium")] or vcr.get("issues") or []
    hints = vcr.get("repair_hints") or {}
    strategy = hints.get("strategy", "fix")
    idx = state.get("current_slide_index", 0)
    count = state.get("visual_repair_count", 0) + 1
    out_dir = _ROOT / "output" / "runs" / state.get("run_id", "unknown") / f"slide-{idx}" / f"visual-repair-{count}"
    logger.info(f"visual_repairer: {strategy.upper()}, {len(issues)} finding(s)")
    try:
        res = (_regenerate if strategy == "regenerate" else _fix)(state, out_dir, issues, hints)
    except Exception as exc:
        logger.error(f"visual_repairer: {strategy} failed: {exc}")
        res = {"outcome": "error", "why": [str(exc)], "usage": []}

    history = [AttemptRecord(attempt=state.get("retry_count", 0) + 1, tier=2 if strategy == "regenerate" else 1,
                             errors_in=[i["description"] for i in issues], errors_out=list(res.get("why") or []),
                             error_sigs=[], stalled=False, truncated=False, noop=res["outcome"] == "noop",
                             tokens_in=u.get("tokens_in", 0), tokens_out=u.get("tokens_out", 0),
                             tokens_reasoning=u.get("tokens_reasoning", 0), tokens_cached=u.get("tokens_cached", 0),
                             model=u.get("model", "unknown"), step="visual_repairer", slide_index=idx)
               for u in res.get("usage") or []]
    if res.get("plan_usage"):   # the re-plan of a regenerate is the planner's spend
        history.insert(0, usage_record(res["plan_usage"], "slide_component_planner", idx))
    if res["outcome"] == "improved":
        logger.info("visual_repairer: kept (compiles, nothing measured got worse)")
        return {**res["updates"], "visual_repair_count": count, "visual_repair_outcome": "improved",
                "generation_history": history}
    logger.info(f"visual_repairer: {res['outcome']}, slide kept as it was: {'; '.join(res.get('why') or [])}")
    return {"visual_repair_count": count, "visual_repair_outcome": res["outcome"], "generation_history": history}
