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


# ── Closed value sets ───────────────────────────────────────────────────────
# One source for every field with a fixed set of values. The LLM schemas
# (src/agents/*_schema.py) import these, so the LLM can only answer with them;
# the TypedDicts below use them for the type checker. state.py cannot import
# from src/agents (its __init__ imports every node, and the nodes import state).

ComponentKindLiteral = Literal[
    "title", "narrative", "caption", "kpi_row", "bullet_list",
    "chart", "table", "timeline", "flow", "layer",
    "tree", "matrix", "process_arrow", "pyramid", "card_grid",
]
WeightLiteral = Literal["hero", "peer", "supporting", "minor"]
SlideTypeLiteral = Literal["cover", "content", "data", "section_break", "closing"]
# POM 10.3.0 <Chart chartType> = knowledge/core/nodes.yaml chartType_values (test_state_literals.py)
ChartTypeLiteral = Literal["bar", "line", "pie", "area", "doughnut", "radar"]
OrientationLiteral = Literal["", "horizontal", "vertical"]

SeverityLiteral = Literal["high", "medium", "low"]
PlanReviewIssueTypeLiteral = Literal[
    "narrative_gap", "layout_repeat", "component_mismatch", "content_weak", "missing_data",
]
CriticTypeLiteral = Literal["completeness", "fidelity", "structure", "theme", "visual"]
QuestionTypeLiteral = Literal["single_choice", "multi_choice", "free_text", "numeric"]

ProvenanceLiteral = Literal["user", "sample"]
PlanSourceLiteral = Literal["fallback"]   # absent = the planner's own plan
PlanFlagCodeLiteral = Literal[            # what plan_checks writes to plan_flags (_flag, sparse_flag);
    "PLAN_EMPTY", "PLAN_INSTRUCTION_TEXT", "PLAN_DUPLICATE_ITEMS", "SLIDE_SPARSE", "KPI_VALUE_TEXT",
]                                         # CARD_LINES_DROPPED only drives a re-ask
RetryTierLiteral = Literal[0, 1, 2]       # 0 = initial, 1 = PATCH, 2 = REGENERATE (repairer.py)
StepLiteral = Literal[                    # step names in usage records (llm_client.usage_record, src/planning)
    "elicitor", "outline_planner", "slide_component_planner", "plan_reviewer",
    "generator", "repairer", "critic", "visual_critic", "visual_repairer", "slide_editor",
    "storyline", "slide_designer",        # Test 1 planning path (src/planning/graph.py)
]
VisualRepairOutcomeLiteral = Literal["improved", "noop", "error"]


# ── Sub-structures ──────────────────────────────────────────────────────────

class OutlineSlide(TypedDict, total=False):
    slide_index: int
    label: str         # kicker above the headline
    slide_title: str   # the headline
    subtitle: str      # evidence line under the headline (key figures)
    section: str
    narrative_role: str
    key_messages: list[str]
    visual_emphasis: str


class OutlinePlan(TypedDict, total=False):
    deck_title: str
    core_hook: str
    slides: list[OutlineSlide]


class PlanReviewIssue(TypedDict, total=False):
    severity: SeverityLiteral
    slide_index: int | None   # None = deck-level issue
    type: PlanReviewIssueTypeLiteral
    description: str
    suggestion: str


class PlanReview(TypedDict, total=False):
    confidence_score: float   # 0.0 - 1.0
    approved: bool
    summary: str
    issues: list[PlanReviewIssue]


class ComponentPlan(TypedDict, total=False):
    component_id: str
    kind: ComponentKindLiteral
    count: int
    chart_type: ChartTypeLiteral
    series_count: int
    columns: int
    rows: int
    items: int
    content_summary: str
    content_data: dict[str, Any]
    orientation: OrientationLiteral
    design_hint: str
    weight: WeightLiteral


class PlanFlag(TypedDict):
    code: PlanFlagCodeLiteral
    component_id: str   # "" = the whole slide
    detail: str


class SlidePlan(TypedDict, total=False):
    slide_index: int
    slide_title: str   # the headline from the outline planner
    label: str         # kicker from the outline planner
    subtitle: str      # evidence line from the outline planner
    slide_type: SlideTypeLiteral
    components: list[ComponentPlan]
    layout_hint: str   # freeform layout INTENT (priority/relationships, not pixels)
    content_data: dict[str, Any]
    data_provenance: dict[str, ProvenanceLiteral]  # content_data key → source
    capacity_fixes: list[str]        # components converted past capacity.yaml (plan check)
    written_lines: list[str]         # card lines the planner wrote (not in the brief), for review
    plan_flags: list[PlanFlag]       # plan_checks findings
    plan_source: PlanSourceLiteral   # "fallback" when the planner failed twice (outline lines as a bullet list)


class DeckPlan(TypedDict, total=False):
    core_hook: str     # narrative anchor tying the deck together
    slide_count: int
    theme: str
    slides: list[SlidePlan]


class AttemptRecord(TypedDict, total=False):
    attempt: int
    tier: RetryTierLiteral
    errors_in: list[str]
    errors_out: list[str]
    error_sigs: list[str]   # canonical error_signatures() output for this attempt
    stalled: bool
    truncated: bool         # LLM response hit max_tokens (finish_reason == "length")
    noop: bool              # PATCH returned XML identical to its input
    tokens_in: int
    tokens_out: int
    tokens_reasoning: int   # part of tokens_out (reasoning models)
    tokens_cached: int      # part of tokens_in served from the prompt cache
    model: str
    step: StepLiteral       # pipeline step that made the call (llm_client.usage_record)
    slide_index: int | None  # 0-based; None for a deck-level call
    reask: bool             # a planner re-ask after a failed plan (step 0)


class Diagnostic(TypedDict):
    type: str      # error code, e.g. UNKNOWN_ATTRIBUTE, HARNESS_ERROR
    message: str


class LayoutIssue(TypedDict, total=False):
    severity: str  # layout_audit: high / medium / low; geometry_audit: error / warning / info
    code: str
    message: str
    tier: str


class ValidateResult(TypedDict, total=False):
    ok: bool
    diagnostics: list[Diagnostic]
    warnings: list[Diagnostic]


class CompileResult(TypedDict, total=False):
    ok: bool
    pptx_path: str | None
    diagnostics: list[Diagnostic]
    warnings: list[Diagnostic]
    retryable: bool


class CriticIssue(TypedDict, total=False):
    severity: SeverityLiteral
    type: CriticTypeLiteral
    description: str
    fix: str
    affected_nodes: list[str]   # visual critic only


class CriticResult(TypedDict, total=False):
    passed: bool
    issues: list[CriticIssue]


class VisualCriticResult(TypedDict, total=False):
    passed: bool
    issues: list[CriticIssue]
    screenshot_path: str | None
    repair_hints: dict[str, Any]


class ElicitationQuestion(TypedDict, total=False):
    key: str
    question: str
    type: QuestionTypeLiteral
    options: list[str]
    required: bool
    default: str
    hint: str


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
    elicitation_questions: list[ElicitationQuestion]
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
    layout_issues: list[LayoutIssue]

    # ── Critique (critic writes) ──
    critic_result: CriticResult | None
    critic_mode: Literal["auto", "off"]
    visual_critic_result: VisualCriticResult | None
    slide_screenshots: dict[int, str]
    # Per-slide critic verdicts captured by slide_router for the deck path
    slide_critic_results: Annotated[list[dict[str, Any]], operator.add]
    # Snapshot before first repair — used for score-based rollback
    pre_critic_xml: str | None
    pre_critic_slide_plans: list[dict[str, Any]] | None
    pre_critic_contract: dict[str, Any] | None
    pre_critic_score: int

    # ── Retry (repairer writes) ──
    retry_tier: RetryTierLiteral
    retry_count: int
    retry_budget: int
    visual_repair_budget: int
    visual_repair_count: int
    visual_repair_outcome: VisualRepairOutcomeLiteral | None
    stall_detected: bool

    # ── Output ──
    excluded_slides: list[int]
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
    critic_mode: Literal["auto", "off"] = "off",
    retry_budget: int = 3,  # PATCH, REGENERATE (replan+generate), cleanup PATCH
    visual_repair_budget: int = 2,
    interactive: bool = False,
    outline_plan: OutlinePlan | None = None,
    elicitation_answers: dict[str, str] | None = None,
) -> PresentationState:
    """Create a fully-initialized starting state for the graph.

    An unknown theme_name raises here, at run start; "" = the default theme.
    """
    if theme_name:
        from src.agents.style_resolver import theme_names  # lazy: src.agents imports state
        if theme_name not in theme_names():
            raise ValueError(f"unknown theme '{theme_name}'; palettes.yaml has: {', '.join(theme_names())}")
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
        pre_critic_xml=None,
        pre_critic_slide_plans=None,
        pre_critic_contract=None,
        pre_critic_score=0,
        retry_tier=0,
        retry_count=0,
        retry_budget=retry_budget,
        visual_repair_budget=visual_repair_budget,
        visual_repair_count=0,
        visual_repair_outcome=None,
        stall_detected=False,
        evaluation=None,
        pptx_path=None,
        passed=False,
    )
