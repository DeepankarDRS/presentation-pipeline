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

class OutlineSlide(TypedDict, total=False):
    slide_index: int
    slide_title: str
    slide_type: str
    section: str
    narrative_role: str
    key_messages: list[str]
    data_anchors: list[str]
    layout_intent: str
    suggested_components: list[str]


class OutlinePlan(TypedDict, total=False):
    deck_title: str
    core_hook: str
    slides: list[OutlineSlide]


class PlanReview(TypedDict, total=False):
    confidence_score: float
    approved: bool
    summary: str
    issues: list[dict[str, Any]]


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
    slide_type: str    # cover | content | data | section_break | closing
    components: list[ComponentPlan]
    density: str       # sparse | normal | dense | tight_fit
    font_tier: str     # display | standard | compact | micro
    layout_pattern: str  # canonical layout category for variety enforcement
    layout_hint: str   # freeform NL: "KPIs across top, chart+table side by side"
    content_data: dict[str, Any]
    data_provenance: dict[str, str]  # key → "user" | "sample"


class DeckPlan(TypedDict, total=False):
    core_hook: str     # narrative anchor tying the deck together
    slide_count: int
    theme: str
    slides: list[SlidePlan]


class AttemptRecord(TypedDict, total=False):
    attempt: int
    tier: int          # 0=initial, 1=patch, 2=regenerate
    errors_in: list[str]
    errors_out: list[str]
    error_sigs: list[str]   # canonical error_signatures() output for this attempt
    stalled: bool
    truncated: bool         # LLM response hit max_tokens (finish_reason == "length")
    noop: bool              # PATCH returned XML identical to its input
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


class VisualCriticResult(TypedDict, total=False):
    passed: bool
    issues: list[dict[str, Any]]
    screenshot_path: str | None


# ── Main state ──────────────────────────────────────────────────────────────

class PresentationState(TypedDict, total=False):
    # ── Identity ──
    run_id: str
    mode: Literal["single", "deck"]
    deck_min_threshold: int  # planner target slide count (1 = single slide)

    # ── Input (written once at start) ──
    interactive: bool
    raw_request: str
    test_case: dict[str, Any] | None
    supplied_content: dict[str, Any] | None
    theme_name: str

    # ── Questionnaire (questionnaire writes, planner reads) ──
    audience_context: dict[str, str] | None

    # ── Deck settings (Gamma-style form, written by API layer) ──
    deck_settings: dict[str, Any] | None

    # ── Elicitation (elicitor writes; API writes answers before resume) ──
    elicitation_needed: bool
    elicitation_questions: list[dict[str, Any]]
    elicitation_answers: dict[str, str] | None

    # ── Outline plan (outline_planner writes, user may edit via API) ──
    outline_plan: OutlinePlan | None
    current_outline_slide: OutlineSlide | None  # injected per-slide via Send()

    # ── Per-slide assembly (fan-in accumulator, slide_plan_sorter reads) ──
    assembled_slide_plans: Annotated[list[SlidePlan], operator.add]

    # ── Plan review (plan_reviewer writes) ──
    plan_review: PlanReview | None

    # ── Planning (outline/slide planner writes, generator reads) ──
    core_hook: str
    deck_plan: DeckPlan | None
    slide_plans: list[SlidePlan]

    # ── Plan refinement (set by the /plan/refine endpoint, planner reads) ──
    prior_plan: dict[str, Any] | None
    refine_feedback: str

    # ── Context (context_builder writes, generator reads) ──
    contract: dict[str, Any] | None
    theme_element: str
    resolved_theme: dict[str, Any] | None

    # ── Multi-slide iteration ──
    current_slide_index: int
    completed_slides: Annotated[list[dict[str, Any]], operator.add]

    # ── Generation (generator writes, validator/critic/repairer read) ──
    current_xml: str
    speaker_notes: str
    generation_history: Annotated[list[AttemptRecord], operator.add]

    # ── Validation (validator writes) ──
    normalize_result: dict[str, Any] | None
    validate_result: ValidateResult | None
    compile_result: CompileResult | None
    layout_issues: list[dict[str, str]]

    # ── Critique (critic writes) ──
    critic_result: CriticResult | None
    critic_mode: Literal["auto", "manual", "off"]
    visual_critic_result: VisualCriticResult | None
    slide_screenshots: dict[int, str]
    # Per-slide critic verdicts captured by slide_router for the deck path
    slide_critic_results: Annotated[list[dict[str, Any]], operator.add]

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
    deck_min_threshold: int = 1,
    audience_context: dict[str, str] | None = None,
    deck_settings: dict[str, Any] | None = None,
    critic_mode: Literal["auto", "manual", "off"] = "off",
    retry_budget: int = 2,  # PATCH once, then REGENERATE once
    interactive: bool = False,
    outline_plan: OutlinePlan | None = None,
    elicitation_answers: dict[str, str] | None = None,
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
        audience_context=audience_context,
        deck_settings=deck_settings,
        elicitation_needed=False,
        elicitation_questions=[],
        elicitation_answers=elicitation_answers,
        outline_plan=outline_plan,
        current_outline_slide=None,
        assembled_slide_plans=[],
        plan_review=None,
        core_hook="",
        deck_plan=None,
        slide_plans=[],
        prior_plan=None,
        refine_feedback="",
        current_slide_index=0,
        completed_slides=[],
        contract=None,
        theme_element="",
        resolved_theme=None,
        current_xml="",
        speaker_notes="",
        generation_history=[],
        normalize_result=None,
        validate_result=None,
        compile_result=None,
        layout_issues=[],
        critic_result=None,
        critic_mode=critic_mode,
        visual_critic_result=None,
        slide_screenshots={},
        slide_critic_results=[],
        retry_tier=0,
        retry_count=0,
        retry_budget=retry_budget,
        stall_detected=False,
        evaluation=None,
        pptx_path=None,
        passed=False,
    )
