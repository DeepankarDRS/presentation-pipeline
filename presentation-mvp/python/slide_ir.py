"""Build a SlideIR (semantic, no POM XML) from a request string or a test case.

Deterministic and rule-based on purpose: the step that decides *what* the slide
contains must not itself depend on an LLM call.
"""

from __future__ import annotations

import re
from typing import Any

from models import ComponentKind, SlideComponent, SlideIR

# request keyword -> component. Order matters only for readability.
_KEYWORD_MAP: list[tuple[re.Pattern[str], ComponentKind]] = [
    (re.compile(r"\bkpi(s)?\b|\bmetric(s)?\b|key (figure|number|stat)", re.I), ComponentKind.kpi_row),
    (re.compile(r"\bchart\b|\bgraph\b|\btrend\b|bar chart|line chart|pie chart", re.I), ComponentKind.chart),
    (re.compile(r"\btable\b|\bgrid\b|\bcomparison table\b", re.I), ComponentKind.table),
    (re.compile(r"\bbullet(s| points| list)?\b|\bchecklist\b|\bagenda\b", re.I), ComponentKind.bullet_list),
    (re.compile(r"\bnarrative\b|\bparagraph\b|\bsummary\b|\bcommentary\b|\boverview\b", re.I), ComponentKind.narrative),
    # Phase D
    (re.compile(r"\btimeline\b|\broadmap\b|\bmilestone(s)?\b|\bchronolog", re.I), ComponentKind.timeline),
    (re.compile(r"\bflow\s?chart\b|\bprocess\s?flow\b|\bdecision\s?(tree|diagram)\b|\bworkflow\b", re.I), ComponentKind.flow),
    (re.compile(r"\barchitecture\b|\bdiagram\b|\blayer\b|\bconnector(s)?\b|\bannotated\b", re.I), ComponentKind.layer),
    # Post-MVP
    (re.compile(r"\borg\s?chart\b|\bhierarch(y|ical)\b|\btree\b|\borganiz(ation|ational)\b", re.I), ComponentKind.tree),
    (re.compile(r"\bmatrix\b|\b2\s?x\s?2\b|\bquadrant\b|\beffort.impact\b|\brisk.likelihood\b", re.I), ComponentKind.matrix),
    (re.compile(r"\bprocess\s?arrow\b|\bchevron\b|\bstep(s| by step)\b|\bphase(s)?\b(?!.*\bD\b)", re.I), ComponentKind.process_arrow),
    (re.compile(r"\bpyramid\b|\bhierarch(y|ical)\s*(pyramid|tier|level)", re.I), ComponentKind.pyramid),
]

_NO_TITLE_RE = re.compile(r"\bno title\b|\bwithout (a )?title\b|\buntitled\b", re.I)
_CAPTION_RE = re.compile(r"\bcaption\b|\bfootnote\b|\bsource:\b|\bprepared (for|by)\b", re.I)


def detect_components(request: str) -> list[ComponentKind]:
    found: list[ComponentKind] = []

    if not _NO_TITLE_RE.search(request):
        found.append(ComponentKind.title)

    for pattern, kind in _KEYWORD_MAP:
        if pattern.search(request) and kind not in found:
            found.append(kind)

    if _CAPTION_RE.search(request) and ComponentKind.caption not in found:
        found.append(ComponentKind.caption)

    # If nothing but a title was detected, assume a short narrative body.
    if all(c in (ComponentKind.title,) for c in found):
        found.append(ComponentKind.narrative)

    return found


def _coerce_kinds(values: list[str]) -> list[ComponentKind]:
    out: list[ComponentKind] = []
    for v in values:
        key = str(v).strip().lower().replace("-", "_").replace(" ", "_")
        try:
            kind = ComponentKind(key)
        except ValueError as exc:
            valid = ", ".join(k.value for k in ComponentKind)
            raise ValueError(f"Unknown component '{v}'. Valid: {valid}") from exc
        if kind not in out:
            out.append(kind)
    return out


def _first_sentence(text: str) -> str:
    m = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)
    return m[0].strip() if m else text.strip()


def from_request(
    request: str,
    *,
    objective: str | None = None,
    components: list[str] | None = None,
    theme: str = "",
    supplied_content: dict[str, Any] | None = None,
) -> SlideIR:
    request = request.strip()
    if not request:
        raise ValueError("request is empty")

    kinds = _coerce_kinds(components) if components else detect_components(request)
    if not kinds:
        kinds = [ComponentKind.title, ComponentKind.narrative]

    return SlideIR(
        objective=(objective or _first_sentence(request)),
        request=request,
        components=[SlideComponent(kind=k) for k in kinds],
        supplied_content=supplied_content or {},
        theme=str(theme or "").strip(),
    )


def from_test_case(case: dict[str, Any]) -> SlideIR:
    """Build a SlideIR from a Phase 5 test-case dict.

    Expected keys: request (str, required), objective (str), components (list),
    supplied_content / supplied (dict), theme (str).
    """
    if "request" not in case:
        raise ValueError("test case is missing 'request'")

    raw_components = case.get("components")
    components: list[SlideComponent] = []
    if isinstance(raw_components, list):
        for entry in raw_components:
            if isinstance(entry, dict):
                kind = _coerce_kinds([entry.get("kind", "")])[0]
                components.append(SlideComponent(kind=kind, spec=entry.get("spec", {})))
            else:
                components.append(SlideComponent(kind=_coerce_kinds([entry])[0]))

    if not components:
        components = [
            SlideComponent(kind=k) for k in detect_components(case["request"])
        ]

    return SlideIR(
        objective=case.get("objective") or _first_sentence(case["request"]),
        request=case["request"].strip(),
        components=components,
        supplied_content=case.get("supplied_content") or case.get("supplied") or {},
        theme=str(case.get("theme", "") or "").strip(),
    )
