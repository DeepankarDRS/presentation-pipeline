"""Visual critic: judges a rendered slide per component, from two screenshots (clean + numbered marks) and what code
measured (2026-11-20 redesign, decisions in docs/visual-critic-redesign-2026-11-20.md).

The system prompt is the same for every slide (the variant catalogue included), so the provider caches it; everything
about the slide is in the user message. The critic describes problems; the fixer (visual_repairer) writes the edits.

Called from critic_node(), and from slide_edit_service after user edits (no marks there).
"""

from __future__ import annotations

import base64
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.agents import slide_facts
from src.agents.critic_schema import VisualCriticOutput
from src.compiler.nodes import composed
from src.utils.llm_client import get_llm, unpack_raw

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "visual_critic"
_jinja_env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), keep_trailing_newline=True)

# the critic's checklist item -> the issue type the rest of the pipeline reads (CriticTypeLiteral)
_TYPE = {"completeness": "completeness", "message": "fidelity", "hierarchy": "visual", "visible_defect": "structure",
         "colour": "theme", "variant_fit": "visual", "balance": "visual", "none": "visual"}


def _empty_repair_hints() -> dict[str, Any]:
    return {"strategy": "none", "assessment": "good", "affected_nodes": []}


@lru_cache(maxsize=1)
def system_prompt() -> str:
    """The critic's system prompt: fixed for every slide and deck (a cacheable prefix)."""
    lines = []
    for kind in composed.KINDS:
        vs = slide_facts.variants(kind)
        lines.append(f"- {kind} (<{composed.tag(kind)} ref>): " + "; ".join(f"{n}: {p}" if p else n for n, p in vs.items()))
    return _jinja_env.get_template("system.j2").render(variant_catalogue="\n".join(lines))


def _image(path: str) -> dict[str, Any]:
    b64 = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}}


def user_text(slide_plan: dict[str, Any], xml: str, comps: list[slide_facts.Component], facts: list[str],
              theme_element: str) -> str:
    hints = [f"[{c.n}] {c.id}: {h}" for c in comps
             for h in [next((p.get("design_hint") for p in slide_plan.get("components") or []
                             if p.get("component_id") == c.id), None)] if h]
    return _jinja_env.get_template("user.j2").render(
        label=slide_plan.get("label", ""), headline=slide_plan.get("slide_title", ""),
        slide_type=slide_plan.get("slide_type", ""), layout_hint=slide_plan.get("layout_hint", ""),
        hints=hints, colour_roles=slide_facts.colour_roles(theme_element),
        component_table=slide_facts.table(comps) or "(no plan component ids on this slide)",
        facts=facts, xml=slide_facts.annotate(xml, comps) if comps else xml)


def run_visual_critic(
    screenshot_path: str,
    current_xml: str,
    slide_plan: dict[str, Any],
    theme_element: str,
    contract: dict[str, Any] | None = None,
    compile_warnings: list[dict[str, str]] | None = None,
    components: list[slide_facts.Component] | None = None,
    facts: list[str] | None = None,
    marked_path: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Review the slide; return (issues, usage, repair_hints). Fails open: ([], zero usage, no repair).

    current_xml: the generator's XML (ref tags) when there is one, else the drawn XML.
    issues: every verdict "issue" as {severity, type, description, fix, affected_nodes, source, component, owner,
    check}; repair_hints.strategy: "regenerate" (the plan is wrong), "fix" (a medium / high issue), else "none".
    """
    zero_usage = {"tokens_in": 0, "tokens_out": 0, "model": "unknown"}
    if not Path(screenshot_path).exists():
        logger.warning(f"visual_critic: screenshot not found: {screenshot_path}")
        return [], zero_usage, _empty_repair_hints()

    comps = components or []
    if facts is None:   # the slide editor's path: the compiler's warnings as they are
        facts = [f"{w.get('code') or w.get('type')}: {w.get('message', '')}" for w in compile_warnings or []]
    text = user_text(slide_plan, current_xml, comps, facts, theme_element)
    content: list[dict[str, Any]] = [_image(screenshot_path)]
    if marked_path and Path(marked_path).exists():
        content.append(_image(marked_path))
    content.append({"type": "text", "text": text})
    messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": content}]

    structured = get_llm("visual_critic").with_structured_output(VisualCriticOutput, method="json_schema",
                                                                 include_raw=True)
    try:
        result, usage = unpack_raw(structured.invoke(messages))
    except Exception as e:
        logger.error(f"visual_critic: LLM call failed: {e}")
        return [], zero_usage, _empty_repair_hints()

    by_id = {c.id: c for c in comps}
    issues = []
    for v in result.verdicts:
        if v.verdict != "issue" or v.severity == "none":
            continue
        c = by_id.get(v.id)
        where = f"[{c.n}] {c.id} ({c.kind})" if c else v.id
        issues.append({
            "severity": v.severity,
            "type": _TYPE.get(v.check, "visual"),
            "description": f"[Visual] {where}: {v.what_i_see}",
            "fix": f"variant {v.better_variant}" if v.better_variant else "",
            "affected_nodes": [v.id],
            "source": "visual",
            "component": v.id,
            "owner": v.owner,
            "check": v.check,
        })
    if result.regenerate:
        strategy = "regenerate"
    elif any(i["severity"] in ("high", "medium") for i in issues):
        strategy = "fix"
    else:
        strategy = "none"
    worst = max((i["severity"] for i in issues), key=["low", "medium", "high"].index, default=None)
    hints = {"strategy": strategy,
             "assessment": {"high": "layout_broken", "medium": "needs_tuning"}.get(worst, "good"),
             "affected_nodes": sorted({i["component"] for i in issues}),
             "observations": result.observations,
             "regenerate_reason": result.regenerate_reason}

    missing = [c.id for c in comps if c.id not in {v.id for v in result.verdicts}]
    if missing:
        logger.info(f"visual_critic: no verdict for {', '.join(missing)}")
    logger.info(f"visual_critic: observations: {result.observations}")
    for i in issues:
        logger.info(f"visual_critic: {i['severity']} {i['check']} ({i['owner']}): {i['description']}")
    logger.info(f"visual_critic: {len(issues)} issue(s), strategy={strategy}")
    logger.info(f"visual_critic: {usage['model']} tokens_in={usage['tokens_in']} tokens_out={usage['tokens_out']}")
    return issues, usage, hints
