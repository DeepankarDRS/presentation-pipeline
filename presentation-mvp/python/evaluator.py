"""Score one generation run into an EvaluationResult (-> evaluation.json).

Deliberately mechanical: every field is derived from artifacts already on disk
(cleaned XML, compile-result.json) so runs can be re-scored later without the LLM.
"""

from __future__ import annotations

import re
import uuid

from models import (
    ComponentKind,
    ComponentScore,
    CompileResult,
    EvaluationResult,
    PreValidationResult,
    RetryOutcome,
    TokenUsage,
)


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Component detection (heuristic, Phase A + light B/C) ─────────────────────
_TEXT_RE = re.compile(r"<Text\b[^>]*>(.*?)</Text>", re.IGNORECASE | re.DOTALL)


def detect_components(xml: str) -> list[ComponentKind]:
    found: list[ComponentKind] = []
    texts = _TEXT_RE.findall(xml)

    # title: first Text with a large fontSize or bold
    for m in re.finditer(r"<Text\b([^>]*)>", xml, re.IGNORECASE):
        attrs = m.group(1)
        size = re.search(r'fontSize\s*=\s*"(\d+)"', attrs)
        if (size and int(size.group(1)) >= 28) or 'bold="true"' in attrs:
            found.append(ComponentKind.title)
            break

    # narrative: a Text with a long body (>80 chars of content)
    if any(len(re.sub(r"<[^>]+>", "", t).strip()) > 80 for t in texts):
        found.append(ComponentKind.narrative)

    # caption: a short italic Text
    if re.search(r'<Text\b[^>]*italic="true"[^>]*>', xml, re.IGNORECASE):
        found.append(ComponentKind.caption)

    # kpi_row: an HStack containing >=2 nested stacks, or Shape dots + big numbers
    hstacks = re.findall(r"<HStack\b.*?</HStack>", xml, re.IGNORECASE | re.DOTALL)
    for h in hstacks:
        inner_stacks = len(re.findall(r"<VStack\b", h, re.IGNORECASE))
        if inner_stacks >= 2:
            found.append(ComponentKind.kpi_row)
            break

    if re.search(r"<Chart\b", xml, re.IGNORECASE):
        found.append(ComponentKind.chart)
    if re.search(r"<Table\b", xml, re.IGNORECASE):
        found.append(ComponentKind.table)
    if re.search(r"<(Ul|Ol)\b", xml, re.IGNORECASE):
        found.append(ComponentKind.bullet_list)

    # de-dup, preserve order
    seen: set[ComponentKind] = set()
    out: list[ComponentKind] = []
    for c in found:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def score_components(required: list[str], xml: str) -> ComponentScore:
    detected = {c.value for c in detect_components(xml)}
    req = list(dict.fromkeys(required))
    present = [r for r in req if r in detected]
    missing = [r for r in req if r not in detected]
    return ComponentScore(required=req, present=present, missing=missing)


# ── Top-level scoring ──────────────────────────────────────────────────────
def evaluate(
    *,
    run_id: str,
    request: str,
    pre: PreValidationResult,
    compiled: CompileResult,
    required_components: list[str] | None = None,
    tokens: TokenUsage | None = None,
    retry: RetryOutcome | None = None,
    test_case: str | None = None,
) -> EvaluationResult:
    required_components = required_components or []
    tokens = tokens or TokenUsage()
    retry = retry or RetryOutcome()

    components = score_components(required_components, pre.cleaned_xml)

    ev = EvaluationResult(
        run_id=run_id,
        test_case=test_case,
        request=request,
        tokens=tokens,
        retry=retry,
        components=components,
    )

    ev.generation = {
        "xml_returned": bool(pre.raw_xml.strip()),
        "markdown_fences_found": pre.markdown_fences_found,
        "html_tags_found": pre.html_tags_found,
        "html_attributes_found": pre.html_attributes_found,
        "hash_colors_found": pre.hash_colors_found,
        "zero_values_found": pre.zero_values_found,
    }
    ev.pre_validation = {
        "issues_found": pre.issues_found,
        "auto_fixed": pre.auto_fixed,
        "blocking": pre.blocking,
        "issues": [i.model_dump() for i in pre.issues],
    }
    ev.compilation = {
        "status": compiled.status,
        "error_type": compiled.primary_error_type,
        "diagnostics": [d.model_dump() for d in compiled.diagnostics],
        "warnings": [w.model_dump() for w in compiled.warnings],
        "retryable": compiled.retryable,
    }
    ev.artifacts = {
        "pptx_created": bool(compiled.pptx_path) and compiled.ok,
        "pptx_path": compiled.pptx_path,
    }

    # Pass = compiled to PPTX, no compiler warnings (NODE_OUT_OF_BOUNDS etc.),
    # no HTML contamination that survived sanitizing, all required components present.
    no_html_leak = not pre.html_tags_found and not pre.html_attributes_found
    ev.passed = bool(
        compiled.ok
        and not compiled.warnings
        and no_html_leak
        and not components.missing
    )
    return ev
