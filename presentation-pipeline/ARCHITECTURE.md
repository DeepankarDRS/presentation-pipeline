# Architecture: LangGraph Presentation Pipeline

## Overview

This pipeline converts a **natural-language prompt** into a **PowerPoint (.pptx) file** using a LangGraph state machine. An LLM generates POM XML (a declarative slide markup language), which a Node.js compiler transforms into the final presentation.

```
User prompt ──▶ [LangGraph Pipeline] ──▶ .pptx file
                      │
                      ├── LLM generates POM XML
                      └── Node.js compiles XML → PowerPoint
```

---

## System Context

```
┌──────────────────────────────────────────────────────────┐
│                   presentation-pipeline/                  │
│                                                          │
│   Python 3.11+ · LangGraph · LangChain · OpenAI API     │
│                                                          │
│   src/graph.py          ← pipeline orchestrator          │
│   src/state.py          ← shared state (TypedDict)       │
│   src/agents/*.py       ← 7 graph nodes                 │
│   src/compiler/*.py     ← Node.js bridge + normalizer    │
│   src/prompts/**/*.j2   ← Jinja2 prompt templates        │
│   src/utils/*.py        ← LLM client, logging, loaders  │
│   models.yaml           ← per-step model config          │
│                                                          │
└─────────────────────────┬────────────────────────────────┘
                          │ subprocess (stdin/stdout)
                          ▼
┌──────────────────────────────────────────────────────────┐
│                   presentation-mvp/                       │
│                                                          │
│   node/compile-pom.js   ← POM v10.3.0 compiler          │
│   pom-knowledge/        ← YAML knowledge base            │
│     core/nodes.yaml     ← allowed tags + attributes      │
│     core/validation.yaml← forbidden tags, translations   │
│     components/*.yaml   ← chart, table, timeline specs   │
│     layouts/*.yaml      ← layout patterns                │
│     theme/palettes.yaml ← color palettes                 │
│     examples/*.xml      ← verified POM XML examples      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Both directories must be **siblings** — the pipeline locates `presentation-mvp/` via relative path (`../presentation-mvp`).

---

## Pipeline Topology

```
START
  │
  ▼
route_after_start ──┐
  │                 │
  │ (threshold>0)   │ (threshold=0)
  ▼                 │
┌──────────┐        │
│ PLANNER  │        │
└────┬─────┘        │
     │              │
     ▼              ▼
┌──────────────────────┐
│   CONTEXT BUILDER    │
└──────────┬───────────┘
           │
           ▼
     ┌───────────┐◄──────────────────────────────┐
     │ GENERATOR │                                │
     └─────┬─────┘                                │
           │                                      │
           ▼                                      │
     ┌───────────┐                                │
     │ VALIDATOR  │                                │
     └─────┬─────┘                                │
           │                                      │
     route_after_validator                        │
       │         │          │                     │
       │ fail    │ ok       │ ok                  │
       │ retry   │ critic   │ critic=off          │
       ▼         ▼          │                     │
  ┌──────────┐ ┌────────┐   │                     │
  │ REPAIRER │ │ CRITIC │   │                     │
  └────┬─────┘ └───┬────┘   │                     │
       │           │         │                     │
       │     route_after_critic                    │
       │       │         │                         │
       │       │ fail    │ pass                    │
       │       ▼         │                         │
       │  ┌──────────┐   │                         │
       │  │ REPAIRER │   │                         │
       │  └────┬─────┘   │                         │
       │       │         │                         │
       └───────┴─────────┼── (loop back) ──────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  EVALUATOR  │
                  └──────┬──────┘
                         │
                         ▼
                        END
```

**Retry loop**: Generator → Validator → (fail) → Repairer → Generator. Up to `retry_budget` times (default: 3).

---

## State: Single Source of Truth

All 7 nodes read and write slices of a single `PresentationState` TypedDict. The full state flows through the graph; each node receives the complete state and returns only the keys it owns.

```python
PresentationState(TypedDict):
    # Identity
    run_id, mode, deck_min_threshold

    # Input (set once at start)
    raw_request, test_case, supplied_content, theme_name

    # Planning (planner → context_builder/generator)
    deck_plan, slide_plans

    # Context (context_builder → generator)
    contract, theme_element, resolved_theme

    # Generation (generator → validator/critic/repairer)
    current_xml, generation_history (append-only)

    # Validation (validator → routing logic)
    normalize_result, validate_result, compile_result

    # Critique (critic → routing logic)
    critic_result, critic_mode

    # Retry (repairer → generator)
    retry_tier, retry_count, retry_budget, stall_detected

    # Output (evaluator → caller)
    evaluation, pptx_path, passed
```

`generation_history` uses LangGraph's `Annotated[list, operator.add]` — each node appends records, the framework merges them.

---

## The 7 Nodes

### 1. Planner (LLM)

**File**: `src/agents/planner.py`

Determines what components a slide should contain. Uses structured output via Pydantic (`PlannerOutput` → `PlannerSlide` → `PlannerComponent`).

- **Input**: `raw_request`, `theme_name`, `supplied_content`
- **Output**: `slide_plans`, `deck_plan`, `mode`
- **Skipped when**: `deck_min_threshold = 0` (route bypasses to context_builder)

Each `SlidePlan` contains:
- `components[]` — what to generate (title, kpi_row, chart, table, etc.)
- `density` — sparse | normal | dense | tight_fit
- `font_tier` — display | standard | compact | micro
- `layout_hint` — freeform NL description of arrangement

### 2. Context Builder (mechanical, no LLM)

**File**: `src/agents/context_builder.py`

Assembles a **generation contract** by reading the POM knowledge base YAML files. The contract tells the generator exactly what POM nodes, attributes, and patterns are available.

- **Input**: `slide_plans[0]`, `theme_name`
- **Output**: `contract`, `theme_element`, `resolved_theme`

The contract contains:
| Field | Purpose |
|-------|---------|
| `allowed_nodes` | POM tags the LLM may use (e.g., `VStack`, `Chart`, `Table`) |
| `allowed_attributes` | Per-node attribute lists |
| `forbidden_tags` | HTML tags the LLM must NOT emit |
| `forbidden_attributes` | CSS-style attributes to reject |
| `theme_element` | `<Theme surface="..." accent="..." ... />` string |
| `notes` | Component-specific rules, pitfalls, translations |
| `example` | Compressed verified XML example |
| `layout_pattern` | Layout structure from YAML |
| `density_tier` | minimal / standard / dense |

Node selection is component-driven:
```
component kind → _KIND_TO_NODES map → POM tags
  "chart"    → Chart, ChartSeries, ChartDataPoint, HStack
  "table"    → Table, Col, Tr, Td, HStack
  "timeline" → Timeline, TimelineItem
```

### 3. Generator (LLM)

**File**: `src/agents/generator.py`

Calls the LLM to produce POM XML using tiered Jinja2 prompts:

| Density | Prompt tier | Included |
|---------|-------------|----------|
| sparse | minimal | theme + allowed nodes + 1 example (~1K tokens) |
| normal/dense | standard | + component rules + layout (~2.5K tokens) |
| tight_fit | dense | + all pitfalls + shrink checklist (~3.2K tokens) |

- **Input**: `contract`, `theme_element`, `slide_plans`, `supplied_content`, `raw_request`
- **Output**: `current_xml`, `generation_history` (appends 1 record)

Each `AttemptRecord` tracks: attempt number, tier, token counts (in/out), model name, errors, stall flag.

### 4. Validator (mechanical, no LLM)

**File**: `src/agents/validator.py`

Three-stage mechanical check — no LLM involved:

```
current_xml → normalize → parseXml (validate) → buildPptx (compile)
```

1. **Normalize** (`normalizer.py`): Strip markdown fences, fix 3-char hex colors, remove `<br>/<hr>`, flag zero dimensions, auto-fix known issues
2. **Validate** (`compiler_client.validate_xml`): Structural check via Node.js `parseXml` — catches unknown tags, invalid attributes, nesting errors
3. **Compile** (`compiler_client.compile_xml`): Full PPTX generation via Node.js `buildPptx`

- **Input**: `current_xml`, `contract`
- **Output**: `normalize_result`, `validate_result`, `compile_result`

`compile_result.retryable` determines if the error is fixable (unknown tags, parse errors = yes; harness crash = no).

### 5. Critic (LLM)

**File**: `src/agents/critic.py`

AI quality gate that checks what the compiler cannot — semantic correctness:

| Check | What it catches | Severity |
|-------|----------------|----------|
| Component completeness | Plan says "chart" but XML has no `<Chart>` | HIGH |
| Content fidelity | `supplied_content` says "Revenue: $2.4M" but value missing in XML | MEDIUM |
| Structural sanity | Root VStack missing `w`/`h`, broken nesting | HIGH |
| Theme adherence | Hardcoded hex colors instead of `$tokens` | MEDIUM |

- **Dual-mode**: `auto` (LLM check) or `manual` (human checkpoint, Phase 6)
- **Fail-open**: If LLM call errors, returns `passed=True` (doesn't block the pipeline)
- **Pass logic**: `passed = not any(issue.severity == "high")`
- **Output**: Pydantic `CriticOutput` → plain dicts for JSON serializability

### 6. Repairer (LLM)

**File**: `src/agents/repairer.py`

Three-tier escalating repair strategy:

| Tier | Strategy | When |
|------|----------|------|
| 1 — Patch | Feed failing XML + errors + guidance → "fix in place" | First failure |
| 2 — Simplify | Regenerate with simpler constraints (fewer components, smaller dims) | Stall detected |
| 3 — Template | Use verified example XML as skeleton, fill content only | Double stall |

**Stall detection**: If >=80% of error signatures overlap between consecutive attempts, the repairer escalates to the next tier instead of retrying the same fix.

- **Input**: `current_xml`, `compile_result`, `critic_result`, `contract`, `generation_history`
- **Output**: `current_xml` (repaired), `retry_tier`, `retry_count`, `stall_detected`, `generation_history`

After repair, the graph routes back to **Generator** → **Validator** for another attempt.

### 7. Evaluator (mechanical, no LLM)

**File**: `src/agents/evaluator.py`

Scores the run and writes a manifest. No LLM — pure computation.

- **Pass condition**: `compile_ok AND critic_ok`
- **Cost computation**: Per-step token counts × model pricing from `models.yaml`
- **Manifest**: Written to `output/runs/{run_id}/run-manifest.json`

Manifest schema:
```json
{
  "run_id": "abc123",
  "passed": true,
  "compile_ok": true,
  "critic_ok": true,
  "retry_count": 0,
  "max_tier": 0,
  "stall_detected": false,
  "tokens": { "total_in": 1200, "total_out": 800, "total": 2000 },
  "cost": { "total_usd": 0.0016, "models_used": ["gpt-4.1-mini"] },
  "critic": { "issues_total": 0, "high": 0, "medium": 0, "low": 0 },
  "steps": [{ "attempt": 0, "tier": 0, "model": "...", "cost": 0.0016 }],
  "pptx_path": "/tmp/pom-pipeline/abc123/output.pptx"
}
```

---

## LLM Configuration

All LLM calls go through `src/utils/llm_client.py`, which reads `models.yaml`:

```yaml
steps:
  planner:    { model: gpt-4.1-mini, temperature: 0.3, max_tokens: 2000 }
  generator:  { model: gpt-4.1-mini, temperature: 0.2, max_tokens: 4000 }
  critic:     { model: gpt-4.1-mini, temperature: 0.1, max_tokens: 1000 }
  repairer:   { model: gpt-4.1-mini, temperature: 0.1, max_tokens: 4000 }

pricing:
  gpt-4.1-mini: { input: 0.40, output: 1.60 }  # per 1M tokens
```

Supports both OpenAI and Azure OpenAI (set `provider: azure_openai` in models.yaml).

---

## Compiler Bridge

The Node.js compiler (`presentation-mvp/node/compile-pom.js`) is invoked via subprocess. Python writes XML to a temp file, runs Node, and reads the structured JSON result. Python **never parses Node stderr**.

```
Python                              Node.js
  │                                   │
  ├── write input.xml ──────────────▶ │
  ├── subprocess.run(compile-pom.js)  │
  │                                   ├── parseXml(xml)
  │                                   ├── buildPptx(ast)
  │                                   ├── write compile-result.json
  │                                   ├── write output.pptx
  │◀── read compile-result.json ──────┤
  │                                   │
```

---

## XML Normalizer

Before the compiler sees the XML, the normalizer (`src/compiler/normalizer.py`) fixes common LLM mistakes:

- Strips markdown code fences (` ```xml ... ``` `)
- Expands 3-char hex colors to 6-char (`#F00` → `FF0000`)
- Removes HTML tags (`<br>`, `<hr>`, `<div>`, etc.)
- Flags zero/negative dimensions
- Detects forbidden CSS-style attributes (`style`, `class`, `font-size`)

Issues are classified as auto-fixable or blocking. Auto-fixed issues are silently corrected; blocking issues trigger a retry.

---

## Repair Guidance

When the compiler returns errors, `src/compiler/repair_guidance.py` translates them into actionable fix instructions for the LLM:

```
UNKNOWN_TAG "div"  →  "Replace <div> with VStack (vertical stack) or HStack"
UNKNOWN_TAG "h2"   →  "Replace <h2> with Text (with fontSize=32 bold=true)"
INVALID_VALUE      →  "Check attribute values: use numbers without px/em units"
```

This is fed into the repairer's Jinja2 prompt template alongside the failing XML.

---

## Prompt Architecture

All prompts are Jinja2 templates in `src/prompts/`:

```
prompts/
  planner/
    system.j2     ← component vocabulary, output schema
    user.j2       ← request + supplied_content + hints
  generator/
    system.j2     ← POM spec, allowed nodes, theme, examples
    user.j2       ← objective, components, density, layout
  critic/
    system.j2     ← 4-item quality checklist
    user.j2       ← current XML + plan + theme for review
  repairer/
    patch.j2      ← tier 1: failing XML + errors + guidance
    simplify.j2   ← tier 2: simplification instructions
    template.j2   ← tier 3: verified example as skeleton
```

---

## Observability

### Structured Logging
`src/utils/logging_config.py` uses Python `contextvars` to inject `run_id`, `step`, and `model` into every log line:

```
src.agents.generator | [3b5c1e89f110] [generator] [gpt-4.1-mini] tokens_in=1200 tokens_out=800
```

### LangSmith Tracing
When `LANGCHAIN_TRACING_V2=true` is set, every `graph.invoke()` call sends traces to LangSmith with:
- `run_name`: `pom-pipeline-{run_id}`
- `tags`: `["presentation-pipeline"]`
- `metadata`: `{run_id, theme, critic_mode}`

### Run Manifest
Every run writes `output/runs/{run_id}/run-manifest.json` with full token/cost/retry accounting.

---

## Testing

### Test Structure
```
tests/
  unit/
    test_planner.py          ← planner LLM mock + schema
    test_context_builder.py  ← contract assembly
    test_generator.py        ← prompt rendering + LLM mock
    test_validator.py        ← normalizer + compiler mock
    test_repairer.py         ← 3-tier repair + stall detection
    test_critic.py           ← quality gate + severity logic
    test_evaluator.py        ← cost computation + manifest
    test_graph.py            ← end-to-end graph mock tests
    test_logging_config.py   ← contextvars injection
    test_case_loader.py      ← YAML case loading
  integration/
    test_full_pipeline.py    ← 21 parametrized cases through full graph
  cases/
    text-only.yaml           ← 21 YAML test case definitions
    kpi-row.yaml
    chart-bar.yaml
    maximal-density.yaml
    ... (21 total)
```

### Running Tests
```bash
python -m pytest tests/ -v          # all 182 tests, ~4s, no API key needed
python -m pytest tests/unit/ -v     # unit tests only
python -m pytest tests/integration/ # full pipeline integration
```

All tests mock the LLM and compiler — no API key or Node.js required.

---

## CLI Usage

### Single slide
```bash
python -m src.graph "Create a KPI dashboard showing revenue and growth"
```

### Batch runner (all 21 test cases)
```bash
python -m src.runner
python -m src.runner text-only kpi-row chart-bar    # specific cases
python -m src.runner --json                          # JSON output
```

The runner prints an aligned ASCII table:
```
Case              Result  Retries  Tier  Tokens In  Tokens Out  Cost     Time
text-only         PASS    0        0     1,200      800         $0.0016  1.2s
kpi-row           PASS    1        1     3,400      1,600       $0.0039  3.8s
────────────────  ──────  ───────  ────  ─────────  ──────────  ───────  ────
TOTAL (21 cases)  21/21   4        -     28,500     14,200      $0.034   45s
```

---

## Dependencies

### Python (`pyproject.toml`)
| Package | Purpose |
|---------|---------|
| langgraph | State machine orchestration |
| langchain-openai | OpenAI LLM wrapper |
| pydantic | Structured LLM output schemas |
| jinja2 | Prompt template rendering |
| pyyaml | Knowledge base + config loading |
| python-dotenv | `.env` file support |
| pytest | Testing |

### Node.js (`presentation-mvp/node/`)
| Package | Purpose |
|---------|---------|
| @hirokisakabe/pom | POM v10.3.0 XML → PPTX compiler |

---

## Data Flow (one successful run)

```
1. User prompt: "Create a KPI dashboard with revenue $2.4M"
                                    │
2. Planner → SlidePlan:             │
   components: [title, kpi_row]     │
   density: normal                  │
   layout_hint: "KPIs across top"   │
                                    │
3. Context Builder → Contract:      │
   allowed_nodes: [Slide, Theme, VStack, HStack, Text, Shape, Span]
   theme_element: '<Theme surface="F7F9FC" accent="2563EB" .../>'
   notes: ["KPI numeral note", "use $tokens for colors"]
   example: (compressed kpi-slide.xml)
                                    │
4. Generator → POM XML:             │
   <Theme surface="F7F9FC" ... />   │
   <Slide>                          │
     <VStack w="1280" h="720" ...>  │
       <Text>Revenue Dashboard</Text>
       <HStack gap="24">           │
         <VStack ...>$2.4M</VStack> │
         ...                        │
       </HStack>                    │
     </VStack>                      │
   </Slide>                         │
                                    │
5. Validator:                       │
   normalize → clean XML            │
   parseXml  → structural OK        │
   buildPptx → output.pptx created  │
                                    │
6. Critic:                          │
   Component completeness: OK       │
   Content fidelity: "$2.4M" found  │
   Structural sanity: OK            │
   Theme adherence: OK              │
   → passed: true                   │
                                    │
7. Evaluator:                       │
   passed: true                     │
   cost: $0.0016                    │
   manifest → output/runs/{id}/run-manifest.json
   pptx    → /tmp/pom-pipeline/{id}/output.pptx
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes (for real runs) | OpenAI API authentication |
| `OPENAI_MODEL` | No | Override default model (fallback: gpt-4.1-mini) |
| `AZURE_OPENAI_ENDPOINT` | For Azure | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | For Azure | Azure API key |
| `NODE_BIN` | No | Path to Node.js binary (default: `node`) |
| `LANGCHAIN_TRACING_V2` | No | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |

---

## File Map

```
presentation-pipeline/
├── pyproject.toml              ← project config + dependencies
├── models.yaml                 ← per-step LLM model/temperature/pricing
├── ARCHITECTURE.md             ← this file
├── src/
│   ├── graph.py                ← LangGraph pipeline definition + CLI
│   ├── state.py                ← PresentationState TypedDict
│   ├── runner.py               ← batch test runner with summary table
│   ├── agents/
│   │   ├── planner.py          ← [LLM] component planning
│   │   ├── planner_schema.py   ← Pydantic schemas for structured output
│   │   ├── context_builder.py  ← [no LLM] knowledge base → contract
│   │   ├── generator.py        ← [LLM] POM XML generation
│   │   ├── validator.py        ← [no LLM] normalize → validate → compile
│   │   ├── critic.py           ← [LLM] AI quality gate
│   │   ├── critic_schema.py    ← Pydantic schemas for critic output
│   │   ├── repairer.py         ← [LLM] 3-tier escalating repair
│   │   └── evaluator.py        ← [no LLM] scoring + manifest
│   ├── compiler/
│   │   ├── compiler_client.py  ← Node.js subprocess bridge
│   │   ├── normalizer.py       ← XML cleanup + pre-validation
│   │   └── repair_guidance.py  ← error → fix instruction mapping
│   ├── prompts/
│   │   ├── planner/            ← system.j2, user.j2
│   │   ├── generator/          ← system.j2, user.j2
│   │   ├── critic/             ← system.j2, user.j2
│   │   └── repairer/           ← patch.j2, simplify.j2, template.j2
│   └── utils/
│       ├── llm_client.py       ← multi-model LLM factory
│       ├── logging_config.py   ← contextvars structured logging
│       └── case_loader.py      ← YAML test case loader
├── tests/
│   ├── unit/                   ← 160+ unit tests
│   ├── integration/            ← 21+ parametrized pipeline tests
│   └── cases/                  ← 21 YAML test case definitions
└── output/                     ← generated PPTX + run manifests
```
