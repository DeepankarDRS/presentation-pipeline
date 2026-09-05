"""PresentationState — single source of truth for the LangGraph pipeline.

Every agent reads/writes only its slice of state. The full TypedDict flows
through the graph; each node function receives and returns a partial dict
of the keys it owns.

Sub-structures use TypedDict so the whole state is JSON-serializable
(required for langgraph-checkpoint).
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


# ── Sub-structures ──────────────────────────────────────────────────────────

class ComponentPlan(TypedDict, total=False):
    kind: str
    count: int
    chart_type: str
    series_count: int
    columns: int
    rows: int
    items: int
    content_summary: str


class SlidePlan(TypedDict, total=False):
    slide_index: int
    components: list[ComponentPlan]
    density: str       # sparse | normal | dense | tight_fit
    font_tier: str     # display | standard | compact | micro
    layout_hint: str   # freeform NL: "KPIs across top, chart+table side by side"
    content_data: dict[str, Any]


class DeckPlan(TypedDict, total=False):
    slide_count: int
    theme: str
    slides: list[SlidePlan]


class AttemptRecord(TypedDict, total=False):
    attempt: int
    tier: int          # 0=initial, 1=patch, 2=simplify, 3=template
    errors_in: list[str]
    errors_out: list[str]
    stalled: bool
    tokens_in: int
    tokens_out: int
    model: str


class ValidateResult(TypedDict, total=False):
    ok: bool
    diagnostics: list[dict[str, str]]
    warnings: list[dict[str, str]]


class CompileResult(TypedDict, total=False):
    ok: bool
    pptx_path: str | None
    diagnostics: list[dict[str, str]]
    warnings: list[dict[str, str]]
    retryable: bool


class CriticResult(TypedDict, total=False):
    passed: bool
    issues: list[dict[str, Any]]


# ── Main state ──────────────────────────────────────────────────────────────

class PresentationState(TypedDict, total=False):
    # ── Identity ──
    run_id: str
    mode: Literal["single", "deck"]
    deck_min_threshold: int

    # ── Input (written once at start) ──
    interactive: bool
    raw_request: str
    test_case: dict[str, Any] | None
    supplied_content: dict[str, Any] | None
    theme_name: str

    # ── Planning (planner writes, generator reads) ──
    deck_plan: DeckPlan | None
    slide_plans: list[SlidePlan]

    # ── Context (context_builder writes, generator reads) ──
    contract: dict[str, Any] | None
    theme_element: str
    resolved_theme: dict[str, Any] | None

    # ── Multi-slide iteration ──
    current_slide_index: int
    completed_slides: Annotated[list[dict[str, Any]], operator.add]

    # ── Generation (generator writes, validator/critic/repairer read) ──
    current_xml: str
    generation_history: Annotated[list[AttemptRecord], operator.add]

    # ── Validation (validator writes) ──
    normalize_result: dict[str, Any] | None
    validate_result: ValidateResult | None
    compile_result: CompileResult | None

    # ── Critique (critic writes) ──
    critic_result: CriticResult | None
    critic_mode: Literal["auto", "manual", "off"]

    # ── Retry (repairer writes) ──
    retry_tier: int
    retry_count: int
    retry_budget: int
    stall_detected: bool

    # ── Output ──
    evaluation: dict[str, Any] | None
    pptx_path: str | None
    passed: bool


def initial_state(
    *,
    run_id: str,
    raw_request: str,
    theme_name: str = "",
    supplied_content: dict[str, Any] | None = None,
    test_case: dict[str, Any] | None = None,
    deck_min_threshold: int = 3,
    critic_mode: Literal["auto", "manual", "off"] = "auto",
    retry_budget: int = 3,
    interactive: bool = False,
) -> PresentationState:
    """Create a fully-initialized starting state for the graph."""
    return PresentationState(
        run_id=run_id,
        mode="single",
        deck_min_threshold=deck_min_threshold,
        interactive=interactive,
        raw_request=raw_request,
        test_case=test_case,
        supplied_content=supplied_content,
        theme_name=theme_name,
        deck_plan=None,
        slide_plans=[],
        current_slide_index=0,
        completed_slides=[],
        contract=None,
        theme_element="",
        resolved_theme=None,
        current_xml="",
        generation_history=[],
        normalize_result=None,
        validate_result=None,
        compile_result=None,
        critic_result=None,
        critic_mode=critic_mode,
        retry_tier=0,
        retry_count=0,
        retry_budget=retry_budget,
        stall_detected=False,
        evaluation=None,
        pptx_path=None,
        passed=False,
    )
