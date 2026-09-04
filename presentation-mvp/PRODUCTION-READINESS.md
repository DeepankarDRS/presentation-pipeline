# Production Readiness Plan — LangGraph Enterprise Pipeline

> v3 — 2026-09-03. All decisions locked. This document is the source of truth
> for building the pipeline across multiple sessions and context windows.
> Every session should read this file first.

---

## 1. Completed Work (Do Not Rebuild)

### Theme System
- Palette library (`palettes.yaml`), WCAG validation, dark chart axis wrapping
- Theme resolution: slide IR → project config → library default
- `$token` enforcement in system prompt + pre_validator

### Knowledge Base
- Curated YAML: `core/nodes.yaml`, `core/attributes.yaml`, `core/validation.yaml`
- Component YAMLs: text, shape, chart, table, list, timeline, flow, drawing, tree, matrix, process-arrow, pyramid
- Layout YAMLs: title-content, kpi-row, two-column, chart-table, timeline-roadmap, diagram-annotated
- Verified XML examples in `pom-knowledge/examples/`
- Selective context assembly (`context_selector.py` → `GenerationContract`)

### Retry Loop (Phase 3)
- 3-tier escalating: Patch → Simplify → Template
- Stall detection (≥80% error overlap → escalate)
- Error-specific repair guidance (tag translations, valid attr lists, shrink checklist)
- Per-attempt tracking (`AttemptRecord`)

### parseXml Validation
- `compile-pom.js --validate-only` — POM's `parseXml()` without `buildPptx()`
- Error types: UNKNOWN_TAG, UNKNOWN_ATTRIBUTE, INVALID_VALUE, INVALID_CHILD, THEME_ERROR
- "Did you mean?" suggestions for typos
- 3-step: normalize → parseXml → buildPptx (parseXml short-circuits before expensive compile)
- Fallback to regex pre_validator when node unavailable

### Bug Fixes
- Retry condition uses compile result only (pre_validator false positives no longer trigger retry)
- `POM_TAGS` expanded to all nodes (was Phase A only → false positives on Arrow/Line)
- `id`/`src` removed from FORBIDDEN_ATTRS (valid POM attributes)

---

## 2. Locked Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | LangGraph with `langgraph-checkpoint` | Typed state, conditional edges, subgraphs, checkpointing |
| Python | 3.11.9, pip (production uses uv) | LangGraph requires 3.11+ |
| LLM Provider | OpenAI only (Azure OpenAI swap-ready) | gpt-4.1 series |
| Models | gpt-4.1-mini for all steps initially | Cheap, fast, upgrade to gpt-4.1 per-step as needed |
| Structured output | OpenAI `response_format: json_schema` for planner | Guaranteed valid JSON, no parse-and-retry |
| Streaming | No | Batch completion, no UI yet |
| Planning | Component-based (NO archetypes) | Free-form layout, LLM has creative freedom |
| Data injection | Single-step (LLM sees data + structure together) | LLM needs data dimensions to size elements correctly |
| Critic | Auto mode (AI) first, manual mode (human) later | Auto is simpler, delivers value immediately |
| Phases | Flattened — no A/B/C/D/post-MVP gating | All POM nodes available, planner selects per slide |
| Dry-run | Removed | Test fixtures replace it |
| deck_min_threshold | Configurable variable, default=3, test with 0 | 0=no deck plan (single slide), 1=2+ slides get deck plan |
| Parallelism | Sequential now, map-reduce ready | Graph structure supports `Send()` for parallel slide gen |
| Tracing | LangSmith + Python logging/contextvars | Production-grade observability |
| Cost | Secondary — optimize for quality | Manage via model selection in models.yaml |

---

## 3. POM Constraints (Critical for Prompts)

These are verified POM v10.3.0 behaviors that the LLM MUST know. Every prompt must encode these.

### Margin & Padding Format
```
VALID:    margin="10"                    (single number, all sides)
VALID:    margin.top="48" margin.left="40"  (dot notation per side)
INVALID:  margin="48 0 0 40"            (CSS shorthand NOT supported)
INVALID:  margin="10px"                 (no units, numbers only)

Same rules for padding: padding="32" or padding.top="16" padding.bottom="8"
```

### Colors
```
VALID:    color="$textMain"    backgroundColor="$surface"   (theme tokens)
VALID:    color="FF0000"       fill.color="2563EB"          (6-digit hex, NO #)
INVALID:  color="#FF0000"      (leading # not allowed)
INVALID:  color="red"          (named colors throw)
```

### Dimensions
```
VALID:    w="1280" h="720"     fontSize="22"    (positive numbers)
INVALID:  w="0"                fontSize="0"     (zero throws render error)
INVALID:  w="-10"              (negative throws render error)
```

### Enums
```
alignItems / justifyContent = start | center | end     (NOT left/right)
textAlign = left | center | right                      (NOT start/end)
```

### Layer Children
```
Children of <Layer> MUST have x="..." y="..." for absolute positioning.
<Layer> is NOT a flex container — it is a canvas.
id="..." is valid on Layer children (used by Arrow from/to).
```

### Chart Colors
```
<Chart chartColors='["3B82F6","10B981","F59E0B"]'>  (literal hex array, NOT $tokens)
Dark themes: wrap Chart in VStack with backgroundColor="$chartSurface"
```

### Table Cells
```
EVERY <Td> needs explicit backgroundColor AND color.
Unstyled cells render with PowerPoint's default white style.
```

---

## 4. Target Folder Structure

```
presentation-pipeline/
├── pyproject.toml
├── models.yaml                       # per-step model config
├── .env.example
│
├── src/
│   ├── __init__.py
│   ├── state.py                      # PresentationState TypedDict
│   ├── graph.py                      # LangGraph graph definition
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py                # component-based planning
│   │   ├── context_builder.py        # knowledge base → contract
│   │   ├── generator.py              # XML generation
│   │   ├── validator.py              # normalize + parseXml + compile
│   │   ├── critic.py                 # auto-mode quality check
│   │   ├── repairer.py               # 3-tier repair
│   │   └── evaluator.py              # scoring
│   │
│   ├── prompts/                      # Jinja2 templates
│   │   ├── planner/
│   │   │   ├── system.j2
│   │   │   └── user.j2
│   │   ├── generator/
│   │   │   ├── system.j2             # tiered: minimal/standard/dense
│   │   │   └── user.j2
│   │   ├── critic/
│   │   │   └── system.j2
│   │   └── repairer/
│   │       ├── patch.j2
│   │       ├── simplify.j2
│   │       └── template.j2
│   │
│   ├── knowledge/                    # from pom-knowledge/ (flattened, no phases)
│   │   ├── core/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── theme/
│   │   └── examples/
│   │
│   ├── compiler/
│   │   ├── compile-pom.js
│   │   ├── package.json
│   │   └── node_modules/
│   │
│   └── utils/
│       ├── llm_client.py             # multi-model, OpenAI/AzureOpenAI
│       ├── theme.py
│       ├── normalizer.py             # XML normalization (from pre_validator)
│       └── token_counter.py
│
├── tests/
│   ├── cases/                        # YAML test cases
│   ├── unit/                         # per-agent mock state tests
│   └── integration/                  # full graph tests
│
└── output/
    └── runs/
```

---

## 5. PresentationState

Single source of truth. Every agent reads/writes only its slice.

```python
from typing import TypedDict, Literal

class ComponentPlan(TypedDict):
    kind: str                          # "title", "kpi_row", "chart", "table", etc.
    count: int                         # number of items (KPI tiles, table rows, etc.)
    chart_type: str                    # "bar", "line", "pie" (when kind=chart)
    series_count: int                  # chart series count
    columns: int                       # table column count
    rows: int                          # table row count
    items: int                         # bullet/timeline item count
    content_summary: str               # compact description for generator context

class SlidePlan(TypedDict):
    slide_index: int
    components: list[ComponentPlan]
    density: str                       # "sparse" | "normal" | "dense" | "tight_fit"
    font_tier: str                     # "display" | "standard" | "compact" | "micro"
    layout_hint: str                   # freeform NL: "KPIs across top, chart+table side by side"
    content_data: dict                 # compact content for this slide (from user or derived)

class DeckPlan(TypedDict):
    slide_count: int
    theme: str
    slides: list[SlidePlan]

class AttemptRecord(TypedDict):
    attempt: int
    tier: int                          # 0=initial, 1=patch, 2=simplify, 3=template
    errors_in: list[str]
    errors_out: list[str]
    stalled: bool
    tokens_in: int
    tokens_out: int
    model: str

class PresentationState(TypedDict):
    # ── Identity ──
    run_id: str
    mode: Literal["single", "deck"]
    deck_min_threshold: int            # 0=no deck plan, N=deck plan for N+ slides

    # ── Input (written once at start) ──
    raw_request: str
    test_case: dict | None
    supplied_content: dict | None      # user business data (source of truth)
    theme_name: str

    # ── Planning (planner writes, generator reads) ──
    deck_plan: DeckPlan | None
    slide_plans: list[SlidePlan]

    # ── Context (context_builder writes, generator reads) ──
    contract: dict | None              # GenerationContract
    theme_element: str
    resolved_theme: dict | None

    # ── Generation (generator writes, validator/critic/repairer read) ──
    current_xml: str
    generation_history: list[AttemptRecord]

    # ── Validation (validator writes) ──
    normalize_result: dict | None
    validate_result: dict | None       # parseXml
    compile_result: dict | None        # buildPptx

    # ── Critique (critic writes) ──
    critic_result: dict | None
    critic_mode: Literal["auto", "manual", "off"]

    # ── Retry (repairer writes) ──
    retry_tier: int                    # 0=initial, 1=patch, 2=simplify, 3=template
    retry_count: int
    retry_budget: int                  # max retries (default 3)
    stall_detected: bool

    # ── Output ──
    evaluation: dict | None
    pptx_path: str | None
    passed: bool
```

### Agent Access Matrix

| Agent | Reads | Writes |
|-------|-------|--------|
| **Planner** | raw_request, theme_name, supplied_content, deck_min_threshold | deck_plan, slide_plans |
| **Context Builder** | slide_plans, theme_name | contract, theme_element, resolved_theme |
| **Generator** | contract, theme_element, slide_plans[i], supplied_content | current_xml, generation_history |
| **Validator** | current_xml | normalize_result, validate_result, compile_result |
| **Critic** | current_xml, compile_result, slide_plans[i], critic_mode | critic_result |
| **Repairer** | current_xml, validate_result, compile_result, critic_result, contract, slide_plans[i] | current_xml, retry_tier, retry_count, stall_detected, generation_history |
| **Evaluator** | all above | evaluation, pptx_path, passed |

---

## 6. Graph Topology

```
                         START
                           │
                   ┌───────▼────────┐
                   │    Planner     │  skip if deck_min_threshold=0
                   └───────┬────────┘    and single slide
                           │
                   ┌───────▼────────┐
                   │ Context Builder│  knowledge → contract
                   └───────┬────────┘
                           │
              ┌────────────▼────────────┐
              │ FOR EACH SLIDE (sequential now,     │
              │ map-reduce parallel later)           │
              │                                      │
              │    ┌────────────────┐                │
              │    │   Generator    │  LLM → XML     │
              │    └───────┬────────┘                │
              │            │                         │
              │    ┌───────▼────────┐                │
              │    │   Validator    │  norm→parse→compile │
              │    └───────┬────────┘                │
              │            │                         │
              │       compile.ok? ── no ──┐          │
              │            │              │          │
              │       ┌────▼───┐    ┌─────▼─────┐   │
              │       │ Critic │    │  Repairer  │   │
              │       │(auto)  │    │ (escalate) │──→│ back to Generator
              │       └────┬───┘    └────────────┘   │
              │            │                         │
              │       critic.pass? ── no ──→ Repairer│
              │            │                         │
              │    ┌───────▼────────┐                │
              │    │   Evaluator    │                │
              │    └───────┬────────┘                │
              │            │                         │
              └────────────▼────────────┘
                           │
                          END
```

### Conditional Edges
- **Planner**: skip if `deck_min_threshold == 0` AND single slide request
- **Critic**: skip if `critic_mode == "off"`, route to human checkpoint if `critic_mode == "manual"`
- **Repairer → Generator**: loop back with escalated tier, up to `retry_budget` times
- **Stall detection**: if ≥80% error overlap between attempts, auto-escalate tier

---

## 7. Agent Specifications

### 7.1 Planner Agent

**Purpose**: Determine what components the slide needs, how dense it is, and provide a freeform layout hint. NO archetypes — the generator has creative freedom.

**Input** (from state): `raw_request`, `theme_name`, `supplied_content`, `deck_min_threshold`

**Output** (to state): `deck_plan`, `slide_plans`

**Prompt strategy**:
- System: component vocabulary (list of component kinds + what each produces)
- System: density/font tier definitions
- User: the raw request + supplied_content summary
- Response format: `json_schema` → `DeckPlan`

**Planner gets component vocabulary ONLY** — not the full knowledge base. The knowledge base is for the generator. The planner just needs to know: "kpi_row produces a row of metric tiles," "chart produces a data visualization," etc.

**Component vocabulary** (hardcoded in planner system prompt):
```
title       → heading text, optional subtitle
narrative   → paragraph body text
caption     → small footnote/source text
kpi_row     → row of metric tiles (label + value + delta)
bullet_list → unordered/ordered list
chart       → bar/line/pie data visualization
table       → data grid with header + rows
timeline    → sequential events/milestones
flow        → step-by-step process
layer       → absolute-positioned shapes with connections
tree        → hierarchical org chart
matrix      → 2x2 or NxN grid categorization
process_arrow → linear process steps with arrows
pyramid     → layered pyramid levels
```

**Content derivation rules**:
- If `supplied_content` has data → use verbatim, derive what's missing
- If `supplied_content` is sparse → derive contextually plausible values from the request
- Never invent data that contradicts supplied data
- When data is insufficient for a component → silently drop it, don't error

### 7.2 Context Builder Agent

**Purpose**: Load knowledge base YAML, build GenerationContract with only the nodes/attributes/examples relevant to THIS slide's component plan.

**Key change from current**: no phase gating. All POM nodes available. Selection is purely component-driven from the `SlidePlan`.

**Prompt optimization**:
- Include attribute lists ONLY for nodes the planner flagged
- Notes: only include notes relevant to the components in this slide
- Examples: max 1, matched by dominant component type
- Compressed examples: skeleton with `<!-- ... -->` for repetitive sections

### 7.3 Generator Agent

**Purpose**: Produce POM XML from the plan + contract + data.

**Prompt strategy (Jinja2 tiered assembly)**:

```
{% if density == "sparse" %}
  {# Minimal: theme + allowed nodes + 1 example = ~2K tokens #}
{% elif density in ["normal", "dense"] %}
  {# Standard: + component rules + layout pattern = ~4K tokens #}
{% else %}  {# tight_fit #}
  {# Dense: + all pitfalls + shrink checklist = ~6K tokens #}
{% endif %}
```

**Critical rules always included** (regardless of tier):
- POM is NOT HTML — forbidden tags/attrs list
- Colors: hex NO #, $tokens in color attrs
- margin/padding: single number OR dot notation (NOT CSS shorthand)
- Dimensions > 0
- Table cells need explicit bg + color

**Token budget**: system prompt ≤ 6K tokens for any slide, including maximal-density.

### 7.4 Validator Agent

**Purpose**: Mechanical (no LLM). Normalize XML, run parseXml, run buildPptx.

**Flow**:
1. `normalizer.normalize_xml()` → strip fences, fix # colors, remove br/hr, remove gap="0"
2. `validate_xml()` → parseXml (fast structural check)
3. If parseXml fails → return errors, skip compile
4. If parseXml passes → `compile_xml()` → buildPptx
5. Write all artifacts to output dir

**Retry decision**: `compile_result.ok == False and compile_result.retryable == True`
(Never retry based on normalize/pre_validate warnings alone.)

### 7.5 Critic Agent (Auto Mode)

**Purpose**: AI quality gate after successful compilation. Checks what the compiler can't.

**Checklist**:
1. Component completeness — does XML include everything the plan specified?
2. Content fidelity — if supplied_content was given, do those values appear in the XML? (WARN if missing, don't fail)
3. Structural sanity — proper nesting? VStack/HStack used correctly?
4. Theme adherence — all colors from Theme? No hardcoded hex in color attrs?

**Does NOT check** (compiler already handles these):
- Tag validity (parseXml)
- Attribute validity (parseXml)
- Dimension errors (buildPptx)
- Layout overlap (buildPptx warnings)

**Output**: `CriticResult { passed: bool, issues: list[{severity, type, description, fix}] }`
- `high` severity → feed to repairer
- `medium`/`low` → log as warnings, don't retry

### 7.6 Repairer Agent

**Purpose**: Fix XML errors using the 3-tier strategy.

Unchanged from current implementation. Uses `repair_guidance.py` for error-specific guidance.

**Tier 1 — Patch**: Feed back failing XML + errors + guidance. "Fix ONLY these errors."
**Tier 2 — Simplify**: Regenerate with simpler constraints.
**Tier 3 — Template**: Verified example as skeleton, fill content only.

### 7.7 Evaluator Agent

**Purpose**: Mechanical scoring. Component completion rate, compile status, token usage.

Unchanged from current `evaluator.py`.

---

## 8. Prompt Optimization Details

### Current Problem
`system-selective.txt` is ~2.3K chars but after placeholder expansion (forbidden lists, allowed nodes, attributes, theme, layout pattern, examples, 40+ notes), maximal-density reaches ~10K tokens.

### Solution: Tiered Jinja2 Assembly

The generator's system prompt has 3 tiers. The `context_builder` sets the tier based on the `SlidePlan.density`.

**Tier 1 — Minimal** (text, narrative, cover slides):
```
- POM critical rules (always)
- Theme element
- Allowed nodes (compact list)
- 1 example (skeleton)
= ~2K tokens
```

**Tier 2 — Standard** (chart, table, KPI slides):
```
- Tier 1 +
- Per-node attribute lists (only for nodes in plan)
- Component-specific pitfalls (only for components in plan)
- Layout pattern
= ~4K tokens
```

**Tier 3 — Dense** (tight_fit, maximal-density):
```
- Tier 2 +
- Shrink checklist (overflow prevention)
- All relevant notes
= ~6K tokens max
```

### Notes Selection
Instead of dumping all 40+ notes, `context_builder` selects only notes relevant to the components in this slide:
- chart → chart color notes, dark theme wrapping
- table → cell styling notes
- kpi_row → numeral formatting, tile gap rules
- All slides → tag translations, color rules

### Example Compression
Current examples are 40-80 lines of full XML. Compressed versions:
```xml
<Theme surface="..." accent="..." textMain="..." textMuted="..." />
<Slide>
  <VStack w="1280" h="720" padding="48" gap="24" backgroundColor="$surface">
    <Text fontSize="32" bold="true" color="$textMain">Title Here</Text>
    <!-- KPI row: HStack with 4 Shape tiles, each ~280w -->
    <!-- Chart: w="600" h="300" with chartColors from theme -->
    <!-- Table: 4 columns, header + 4 rows, all cells styled -->
  </VStack>
</Slide>
```
Shows structure without repeating 4 identical KPI tiles or 16 table cells.

---

## 9. Content Handling

### User-Provided Data (Source of Truth)
When `supplied_content` is present, it is the **source of truth**. The pipeline:
1. **Planner** reads it to determine component count/dimensions
2. **Generator** receives it and must use values verbatim
3. **Critic** warns if supplied values don't appear in final XML
4. **Never invent** data that contradicts supplied data

### Derived Content
When `supplied_content` is sparse or absent:
1. **Planner** derives contextually plausible values from the request
2. Values are realistic and internally consistent
3. KPI values match chart data match table totals
4. Derived content goes into `SlidePlan.content_data`

### Compact Data Format
To reduce prompt tokens, data is passed as compact structures:
```
KPI: ARR=$12.4M(+18%) | NRR=112%(+3pp) | Margin=68.2%(-1.1pp) | CAC=14.2mo(+0.8)
TABLE: [Region,Revenue,Costs,Margin] NA/$8.2M/$5.1M/37.8% | EMEA/$3.1M/$2.0M/35.5%
CHART(bar): Q1=[4.2,3.8,5.1] Q2=[4.8,4.1,5.6] labels=[NA,EMEA,APAC]
```
Not JSON — just pipe-delimited values the LLM can read in fewer tokens.

---

## 10. Implementation Phases

Each phase is a deliverable. Phases can be started in a new session — this doc + the code from previous phases is sufficient context.

### Phase 0 — LangGraph Scaffold + State (Start Here)
**Goal**: Empty graph that runs, state flows through nodes, tests pass.

Deliverables:
- [ ] `pyproject.toml` with dependencies (langgraph, langchain-core, langchain-openai, jinja2, pyyaml, pydantic)
- [ ] `src/state.py` — PresentationState TypedDict
- [ ] `src/graph.py` — graph definition with all nodes (stub implementations)
- [ ] `src/agents/__init__.py` — each agent as a function that takes/returns state
- [ ] `models.yaml` — model config (all gpt-4.1-mini initially)
- [ ] `src/utils/llm_client.py` — OpenAI client, reads models.yaml, supports AzureOpenAI swap
- [ ] `tests/unit/test_state.py` — state schema validation
- [ ] `tests/unit/test_graph.py` — graph runs with mock agents
- [ ] Verify: `python -m src.graph --request "simple title slide"` runs end-to-end with stubs

### Phase 1 — Planner Agent
**Goal**: AI determines components, density, layout hint from request + data.

Deliverables:
- [ ] `src/agents/planner.py` — component-based planning
- [ ] `src/prompts/planner/system.j2` — component vocabulary, density definitions
- [ ] `src/prompts/planner/user.j2` — request + supplied_content
- [ ] Structured output via `response_format: json_schema` → `DeckPlan`
- [ ] `deck_min_threshold` logic: skip planner when threshold=0 and single slide
- [ ] Content derivation: planner invents consistent data when supplied_content is sparse
- [ ] `tests/unit/test_planner.py` — mock LLM, verify SlidePlan structure
- [ ] Verify: planner produces valid SlidePlan for maximal-density test case

### Phase 2 — Context Builder + Prompt Optimization
**Goal**: Knowledge base → contract with tiered prompt assembly. System prompt ≤ 6K tokens.

Deliverables:
- [ ] `src/agents/context_builder.py` — from current `context_selector.py`, flattened (no phases)
- [ ] `src/prompts/generator/system.j2` — Jinja2 tiered template (minimal/standard/dense)
- [ ] `src/prompts/generator/user.j2` — request + plan + compact data
- [ ] Notes selection: only notes relevant to components in this slide
- [ ] Example compression: skeleton examples with `<!-- ... -->` comments
- [ ] Per-node attributes: only for nodes the planner flagged
- [ ] POM constraint rules always included (margin format, colors, dimensions)
- [ ] `tests/unit/test_context_builder.py` — verify token count per tier
- [ ] Verify: maximal-density system prompt ≤ 6K tokens

### Phase 3 — Generator + Validator (Wire Existing)
**Goal**: Port existing generation + validation into LangGraph nodes.

Deliverables:
- [ ] `src/agents/generator.py` — LLM call with tiered prompt
- [ ] `src/agents/validator.py` — normalize → parseXml → buildPptx
- [ ] Port `compiler_client.py` → `src/compiler/` (compile-pom.js already done)
- [ ] Port `normalizer.py` (from pre_validator normalize-only)
- [ ] Port `repair_guidance.py`, `prompt_builder.py` repair methods
- [ ] `src/agents/repairer.py` — 3-tier retry as graph subloop
- [ ] Verify: full pipeline runs for text-slide, kpi-row, maximal-density test cases

### Phase 4 — Critic Agent
**Goal**: AI quality gate catches what the compiler misses.

Deliverables:
- [ ] `src/agents/critic.py` — auto mode
- [ ] `src/prompts/critic/system.j2` — checklist (completeness, fidelity, structure, theme)
- [ ] Conditional edge: skip when `critic_mode == "off"`, manual checkpoint when "manual"
- [ ] Content fidelity: warn if supplied values missing from XML
- [ ] `tests/unit/test_critic.py` — mock state with known issues
- [ ] Verify: critic catches missing component, hardcoded color, missing supplied value

### Phase 5 — Observability + Testing
**Goal**: LangSmith tracing, run manifest, test suite runner.

Deliverables:
- [ ] LangSmith integration (trace each agent call)
- [ ] Python logging with contextvars (run_id, step, model)
- [ ] `run-manifest.json` per run (steps, models, tokens, cost, retries)
- [ ] `tests/integration/test_full_pipeline.py` — run all 17 test cases
- [ ] Summary table output (case, result, cost, tokens, retries, tier)
- [ ] Per-step token tracking in manifest

### Phase 6 (Future) — Enhancements
- [ ] Manual critic mode (human-in-the-loop checkpoint)
- [ ] Map-reduce parallel slide generation with concurrency limit
- [ ] Visual verification (render → screenshot → vision model critique)
- [ ] Web UI for plan review / slide editing
- [ ] Azure OpenAI provider swap
- [ ] Additional test cases (complex enterprise decks)

---

## 11. Models Configuration

```yaml
# models.yaml
steps:
  planner:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.3
    max_tokens: 2000
    response_format: json_schema
  generator:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.2
    max_tokens: 4000
  critic:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.1
    max_tokens: 1000
    enabled: true
  repairer:
    provider: openai
    model: gpt-4.1-mini
    temperature: 0.1
    max_tokens: 4000

defaults:
  provider: openai                    # swap to azure_openai for Azure
  azure_endpoint: ""                  # set when provider=azure_openai
  azure_api_version: "2024-12-01-preview"

pricing:                              # per 1M tokens, for cost tracking
  gpt-4.1:      { input: 2.00, output: 8.00 }
  gpt-4.1-mini: { input: 0.40, output: 1.60 }
  gpt-4.1-nano: { input: 0.10, output: 0.40 }
```

---

## 12. Key Metrics

1. **maximal-density test case must pass** — 4 KPI tiles, 2 charts, bullet list, 4-column table on 1280×720
2. **System prompt ≤ 6K tokens** for any slide (including maximal-density)
3. **Supplied content appears verbatim** in final XML when provided
4. **Retry budget ≤ 3** — if template tier can't fix it, the plan was wrong
5. **Per-run cost < $0.05** for single slide (gpt-4.1-mini)
6. **Presentation quality** comparable to Genspark's output level
