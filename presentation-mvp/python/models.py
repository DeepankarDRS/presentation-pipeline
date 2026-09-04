"""Pydantic models for the pipeline's structured data.

Flow:  user request -> SlideIR -> GenerationContract -> (LLM) -> raw XML
       -> PreValidationResult -> CompileResult -> EvaluationResult

SlideIR and GenerationContract are consumed heavily in Phase 4
(context_selector / prompt_builder); they are defined now so the whole
pipeline speaks one vocabulary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field


# ── Enums ────────────────────────────────────────────────────────────────────
class ComponentKind(str, Enum):
    """Semantic slide components. Phase A covers title/narrative/kpi_row."""
    title = "title"
    narrative = "narrative"
    caption = "caption"
    kpi_row = "kpi_row"
    bullet_list = "bullet_list"   # Phase B
    chart = "chart"               # Phase B
    table = "table"               # Phase C
    timeline = "timeline"         # Phase D
    flow = "flow"                 # Phase D
    layer = "layer"               # Phase D (drawing/diagram)
    tree = "tree"                 # Post-MVP
    matrix = "matrix"             # Post-MVP
    process_arrow = "process_arrow"  # Post-MVP
    pyramid = "pyramid"           # Post-MVP


class DiagnosticType(str, Enum):
    UNKNOWN_TAG = "UNKNOWN_TAG"
    UNKNOWN_ATTRIBUTE = "UNKNOWN_ATTRIBUTE"
    PARSE_ERROR = "PARSE_ERROR"
    INVALID_VALUE = "INVALID_VALUE"
    INVALID_CHILD = "INVALID_CHILD"
    THEME_ERROR = "THEME_ERROR"
    RENDER_ERROR = "RENDER_ERROR"
    DIAGNOSTIC = "DIAGNOSTIC"
    IO_ERROR = "IO_ERROR"
    USAGE_ERROR = "USAGE_ERROR"
    HARNESS_ERROR = "HARNESS_ERROR"


# ── Semantic IR (input side) ─────────────────────────────────────────────────
class SlideComponent(BaseModel):
    kind: ComponentKind
    # Free-form spec for this component (labels supplied, values to invent, etc.).
    spec: dict[str, Any] = Field(default_factory=dict)


class SlideIR(BaseModel):
    """A semantic description of the requested slide. Contains NO POM XML."""
    objective: str
    request: str                       # the raw user request, verbatim
    components: list[SlideComponent] = Field(default_factory=list)
    supplied_content: dict[str, Any] = Field(default_factory=dict)
    # Palette name from pom-knowledge/theme/palettes.yaml (or a legacy
    # "dark"/"light" alias). "" means "use the project/library default".
    theme: str = ""

    @property
    def component_kinds(self) -> list[ComponentKind]:
        return [c.kind for c in self.components]


class DeckIR(BaseModel):
    """An ordered set of slides sharing one theme. Deck mode (Phase 9)."""
    title: str
    objective: str = ""
    theme: str = ""              # palette name shared by every slide in the deck
    slides: list[SlideIR] = Field(default_factory=list)

    @property
    def slide_count(self) -> int:
        return len(self.slides)


# ── Generation contract (what the prompt builder assembles) ──────────────────
class GenerationContract(BaseModel):
    """The component-specific context handed to prompt_builder."""
    allowed_nodes: list[str] = Field(default_factory=list)
    allowed_attributes: dict[str, list[str]] = Field(default_factory=dict)
    forbidden_tags: list[str] = Field(default_factory=list)
    forbidden_attributes: list[str] = Field(default_factory=list)
    theme_element: str = ""
    theme_name: str = ""
    theme_mode: str = "light"            # "light" | "dark"
    chart_colors: list[str] = Field(default_factory=list)  # literal hex for <Chart>
    layout_pattern: str = ""
    examples: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ── Pre-validation ──────────────────────────────────────────────────────────
class PreValidationIssue(BaseModel):
    code: str
    message: str
    auto_fixed: bool = False


class PreValidationResult(BaseModel):
    raw_xml: str
    cleaned_xml: str
    issues: list[PreValidationIssue] = Field(default_factory=list)

    markdown_fences_found: bool = False
    html_tags_found: list[str] = Field(default_factory=list)
    html_attributes_found: list[str] = Field(default_factory=list)
    hash_colors_found: list[str] = Field(default_factory=list)
    zero_values_found: list[str] = Field(default_factory=list)

    @property
    def issues_found(self) -> int:
        return len(self.issues)

    @property
    def auto_fixed(self) -> int:
        return sum(1 for i in self.issues if i.auto_fixed)

    @property
    def blocking(self) -> bool:
        """True if an issue remains that the compiler will choke on / that
        corrupts run integrity (structural HTML, zero dims, invented attrs)."""
        return any(not i.auto_fixed for i in self.issues)


# ── Compilation (mirrors node/compile-pom.js compile-result.json) ────────────
class CompileDiagnostic(BaseModel):
    type: str
    message: str


class CompileWarning(BaseModel):
    code: str | None = None
    message: str | None = None


class CompileResult(BaseModel):
    status: Literal["success", "failure"]
    input_path: str | None = Field(default=None, alias="inputPath")
    pptx_path: str | None = Field(default=None, alias="pptxPath")
    diagnostics: list[CompileDiagnostic] = Field(default_factory=list)
    warnings: list[CompileWarning] = Field(default_factory=list)
    pom_version: str | None = Field(default=None, alias="pomVersion")
    error_name: str | None = Field(default=None, alias="errorName")

    model_config = {"populate_by_name": True}

    @property
    def ok(self) -> bool:
        return self.status == "success"

    @property
    def primary_error_type(self) -> str | None:
        return self.diagnostics[0].type if self.diagnostics else None

    @property
    def retryable(self) -> bool:
        retryable_types = {
            "UNKNOWN_TAG", "UNKNOWN_ATTRIBUTE", "PARSE_ERROR",
            "INVALID_VALUE", "INVALID_CHILD", "THEME_ERROR", "DIAGNOSTIC",
        }
        return bool(self.diagnostics) and all(
            d.type in retryable_types for d in self.diagnostics
        )


# ── Evaluation ──────────────────────────────────────────────────────────────
class ComponentScore(BaseModel):
    required: list[str] = Field(default_factory=list)
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completion_rate(self) -> float:
        if not self.required:
            return 1.0
        return round(len(self.present) / len(self.required), 3)


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        return self.input + self.output


class AttemptRecord(BaseModel):
    """One generation or repair attempt in the retry loop."""
    attempt: int                         # 0 = initial, 1+ = retries
    tier: int = 0                        # 0=initial, 1=patch, 2=simplify, 3=template
    errors_in: list[str] = Field(default_factory=list)   # errors fed to this attempt
    errors_out: list[str] = Field(default_factory=list)  # errors found after this attempt
    stalled: bool = False                # same errors as previous attempt
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    model: str = ""


class RetryOutcome(BaseModel):
    attempted: bool = False
    attempts: int = 0                    # number of repair round-trips made
    succeeded: bool | None = None        # did the final repair attempt come out clean
    reason: str | None = None            # what triggered the first retry
    diagnostics_fed_back: list[str] = Field(default_factory=list)
    # ── Enhanced fields for 3-tier retry ──
    max_tier_used: int = 0               # highest tier reached (1=patch, 2=simplify, 3=template)
    attempt_records: list[AttemptRecord] = Field(default_factory=list)
    stall_count: int = 0                 # how many times stall was detected


class EvaluationResult(BaseModel):
    run_id: str
    test_case: str | None = None
    request: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    generation: dict[str, Any] = Field(default_factory=dict)
    pre_validation: dict[str, Any] = Field(default_factory=dict)
    compilation: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    components: ComponentScore = Field(default_factory=ComponentScore)
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    retry: RetryOutcome = Field(default_factory=RetryOutcome)

    passed: bool = False

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


class DeckEvaluationResult(BaseModel):
    """Aggregate result for a deck run (Phase 9)."""
    run_id: str
    title: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    slide_count: int = 0

    # one summary dict per slide (compiled, passed, error_type, tokens, retry)
    slides: list[dict[str, Any]] = Field(default_factory=list)

    deck_compilation: dict[str, Any] = Field(default_factory=dict)
    tokens: TokenUsage = Field(default_factory=TokenUsage)

    theme_consistent: bool = True   # every slide resolved to the one deck theme
    passed: bool = False            # deck compiled + every slide passed

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
