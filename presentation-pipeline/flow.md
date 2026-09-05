# POM Pipeline Architecture

> LangGraph orchestration for POM XML generation, validation, and PowerPoint compilation
>
> Interactive version: https://claude.ai/code/artifact/fe5e4568-025f-4e26-9962-97e1e345712f

---

## 1. Pipeline Overview

The pipeline takes a natural-language request (e.g. "Create a KPI dashboard slide"), generates POM XML through an LLM, validates and compiles it via the `@hirokisakabe/pom v10.3.0` compiler, and outputs a `.pptx` PowerPoint file. It runs as a **LangGraph StateGraph** with 7 nodes connected by conditional edges.

**Key design decisions (locked):**
- **Component-based planning** — no archetypes. The planner outputs a free-form component list, not a fixed template.
- **Tiered prompt assembly** — minimal / standard / dense tiers keep system prompts under 6K tokens.
- **3-tier escalating retry** — patch → simplify → template, with stall detection.
- **Dual-mode critic** — auto (AI) runs first; manual (human) is a future checkpoint.
- **Single state object** — `PresentationState` TypedDict flows through every node.

---

## 2. Graph Topology

Defined in `src/graph.py`. The graph has 7 nodes and 4 routing functions that create conditional edges.

```
START
  │
  ▼ route_after_start
  ├─ threshold > 0 → PLANNER
  └─ threshold = 0 → CONTEXT_BUILDER (skip planner)
  │
  ▼
PLANNER ──────────────────────────────────────────────────────────────
  │  LLM structured output → PlannerOutput (json_schema)
  │  Writes: mode, deck_plan, slide_plans
  ▼
CONTEXT_BUILDER ──────────────────────────────────────────────────────
  │  Mechanical (no LLM). Reads YAML knowledge base.
  │  Writes: contract, theme_element, resolved_theme
  ▼
GENERATOR ◄──────────────────────────────────── REPAIRER
  │  LLM call with tiered prompts               │ Builds repair
  │  Writes: current_xml, generation_history     │ prompt, calls LLM
  ▼                                              │
VALIDATOR                                        │
  │  normalize → parseXml → buildPptx            │
  │  Writes: normalize_result, validate_result,  │
  │          compile_result                      │
  │                                              │
  ▼ route_after_validator                        │
  ├─ compile failed + retryable + budget ────────┘
  ├─ compile ok + critic_mode=off → EVALUATOR
  │
  ▼ compile ok + critic_mode≠off
CRITIC
  │  LLM structured output → CriticOutput (json_schema)
  │  Writes: critic_result
  │
  ▼ route_after_critic
  ├─ critic failed + budget → REPAIRER ──────────┘
  │
  ▼ critic passed
EVALUATOR ────────────────────────────────────────────────────────────
  │  Mechanical. Scores run, writes manifest.
  │  Writes: evaluation, pptx_path, passed
  ▼
END → .pptx + run-manifest.json
```

### Routing functions

| Function | Logic |
|----------|-------|
| `route_after_start()` | `threshold=0` → skip planner to context_builder |
| `route_after_validator()` | fail+retryable+budget → repairer; ok+critic≠off → critic; ok+critic=off → evaluator |
| `route_after_critic()` | failed+budget → repairer; else → evaluator |
| `route_after_repairer()` | always → generator |

---

## 3. State Schema

Defined in `src/state.py`. Every agent reads and writes only its slice. The full `PresentationState` TypedDict flows through the graph; each node returns a partial dict.

| Slice | Keys | Writer | Reader(s) |
|-------|------|--------|-----------|
| Identity | `run_id`, `mode`, `deck_min_threshold` | initial_state | All nodes |
| Input | `raw_request`, `test_case`, `supplied_content`, `theme_name` | initial_state | planner, context_builder |
| Planning | `deck_plan`, `slide_plans` | planner | context_builder, generator, critic, repairer |
| Context | `contract`, `theme_element`, `resolved_theme` | context_builder | generator, repairer, validator (fallback) |
| Generation | `current_xml`, `generation_history` | generator, repairer | validator, critic, evaluator |
| Validation | `normalize_result`, `validate_result`, `compile_result` | validator | critic, repairer, evaluator |
| Critique | `critic_result`, `critic_mode` | critic | repairer, evaluator |
| Retry | `retry_tier`, `retry_count`, `retry_budget`, `stall_detected` | repairer | validator routing, critic routing |
| Output | `evaluation`, `pptx_path`, `passed` | evaluator | Caller |

### Sub-structures (all TypedDict for JSON serialization)
- `ComponentPlan` — kind, count, chart_type, series_count, columns, rows, items, content_summary
- `SlidePlan` — slide_index, components, density, font_tier, layout_hint, content_data
- `DeckPlan` — slide_count, theme, slides
- `AttemptRecord` — attempt, tier, errors_in/out, stalled, tokens_in/out, model
- `ValidateResult` — ok, diagnostics, warnings
- `CompileResult` — ok, pptx_path, diagnostics, warnings, retryable
- `CriticResult` — passed, issues

**Special:** `generation_history` uses `Annotated[list[AttemptRecord], operator.add]` so LangGraph automatically merges (appends) records from both generator and repairer.

---

## 4. Planner Agent

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/planner.py` |
| **Schema** | `src/agents/planner_schema.py` |
| **LLM** | Yes (structured output, json_schema) |

Determines **what** a slide needs (components, density, font tier, layout hint) without prescribing **how**. Uses OpenAI structured output for guaranteed-valid JSON.

**Reads:** `raw_request`, `theme_name`, `supplied_content`, `deck_min_threshold`, `test_case`
**Writes:** `mode`, `deck_plan`, `slide_plans`

### LLM call chain
```python
llm = get_llm("planner")                                    # ChatOpenAI
structured = llm.with_structured_output(PlannerOutput,       # Pydantic → json_schema
                                        method="json_schema")
result: PlannerOutput = structured.invoke([SystemMessage, HumanMessage])
```

### Component vocabulary (14 kinds)

| Kind | Produces | Key fields |
|------|----------|------------|
| title | Heading + subtitle | count (max 1) |
| narrative | Body paragraph | — |
| caption | Footnote/source | — |
| kpi_row | Metric tiles | count (tiles) |
| bullet_list | Ul/Ol list | items |
| chart | Data viz | chart_type, series_count, count |
| table | Data grid | columns, rows |
| timeline | Events/milestones | items |
| flow | Process steps | items |
| layer | Absolute shapes | — |
| tree | Org chart | items |
| matrix | Categorization grid | items |
| process_arrow | Linear process | items |
| pyramid | Pyramid levels | items |

### Mode determination
If planner returns `≥ deck_min_threshold` slides (default 3) → `mode="deck"` with a `DeckPlan`. Otherwise → `mode="single"`. When `deck_min_threshold=0`, the planner is skipped entirely.

---

## 5. Context Builder

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/context_builder.py` |
| **LLM** | No (mechanical) |

Assembles the **knowledge base contract** — a dict that tells the generator exactly which POM nodes, attributes, notes, examples, and layouts to use. Purely mechanical: reads YAML files from `presentation-mvp/pom-knowledge/`, selects by component kind.

**Reads:** `slide_plans`, `theme_name`
**Writes:** `contract`, `theme_element`, `resolved_theme`

### Contract assembly pipeline
```
build_contract(slide_plan, theme_name) → {
    allowed_nodes:      _select_nodes(kinds)            # component → POM nodes
    allowed_attributes: _select_attributes(nodes, yaml)  # per-node attr lists
    forbidden_tags:     from validation.yaml             # HTML tags → errors
    forbidden_attributes: from validation.yaml           # CSS attrs → errors
    theme_element:      _resolve_theme(name)            # palette → <Theme .../>
    notes:              _select_notes(kinds, ...)        # component-relevant rules
    example:            _select_example(kinds)           # 1 compressed XML example
    layout_pattern:     _select_layout(kinds)            # spatial arrangement YAML
    density_tier:       sparse→minimal, normal/dense→standard, tight_fit→dense
}
```

### Knowledge base sources

| File | Used for |
|------|----------|
| `core/nodes.yaml` | POM node definitions + per-node attributes |
| `core/validation.yaml` | Forbidden tags/attrs, translations, semantic rules |
| `components/*.yaml` | Component-specific structure and pitfalls |
| `theme/palettes.yaml` | Theme palette resolution |
| `layouts/*.yaml` | Layout patterns (kpi-row, chart-table, etc.) |
| `examples/*.xml` | Verified XML examples for reference |

### Node selection mapping

Each component kind maps to additional POM nodes beyond the base set (`Slide`, `Theme`, `VStack`, `Text`, `Shape` + inline nodes):

```
chart       → HStack, Chart, ChartSeries, ChartDataPoint
table       → HStack, Table, Col, Tr, Td
kpi_row     → HStack, Span
bullet_list → Ul, Li
timeline    → Timeline, TimelineItem
flow        → Flow, FlowNode, FlowConnection
layer       → Layer, Line, Arrow, Svg
tree        → Tree, TreeItem
matrix      → Matrix, MatrixAxes, MatrixQuadrants, MatrixItem
process_arrow → ProcessArrow, ProcessArrowStep
pyramid     → Pyramid, PyramidLevel
```

---

## 6. Generator Agent

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/generator.py` |
| **LLM** | Yes |

Produces raw POM XML by rendering Jinja2 templates from the contract and calling the LLM. The system prompt tier is determined by `density_tier` from the contract.

**Reads:** `contract`, `theme_element`, `slide_plans`, `supplied_content`, `raw_request`, `retry_count`, `retry_tier`
**Writes:** `current_xml`, `generation_history` (appends AttemptRecord)

### Prompt tiers

| Tier | Density | Token count | Includes |
|------|---------|-------------|----------|
| Minimal | sparse | ~1.1K | Theme + allowed nodes + critical rules |
| Standard | normal, dense | ~2.5K | + per-node attributes + layout pattern |
| Dense | tight_fit | ~3.2K | + shrink checklist + all pitfalls |

All tiers include the **critical rules** block: forbidden tags/attrs, color format (`6-digit hex NO #`), margin/padding format (single number or dot notation, not CSS shorthand), dimension rules (`>0`), enum rules.

---

## 7. Validator Agent

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/validator.py` |
| **LLM** | No (mechanical) |

Mechanical ground truth — runs the 3-step validation pipeline. No LLM involved.

**Reads:** `current_xml`, `contract` (for pre_validate fallback), `run_id`, `retry_count`
**Writes:** `normalize_result`, `validate_result`, `compile_result`

### Validation pipeline
```
1. normalize_xml(raw)     → strip fences, fix #colors, remove br/hr, flag zero dims
                            src/compiler/normalizer.py

2. validate_xml(cleaned)  → parseXml structural check (fast, no PPTX)
                            src/compiler/compiler_client.py → compile-pom.js --validate-only
                            Falls back to pre_validate() regex if compiler unavailable

3. compile_xml(cleaned)   → buildPptx full compilation
                            src/compiler/compiler_client.py → compile-pom.js
                            Produces .pptx + compile-result.json
```

### Retryable error types
```
UNKNOWN_TAG, UNKNOWN_ATTRIBUTE, PARSE_ERROR,
INVALID_VALUE, INVALID_CHILD, THEME_ERROR, DIAGNOSTIC
```

---

## 8. Critic Agent

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/critic.py` |
| **Schema** | `src/agents/critic_schema.py` |
| **LLM** | Yes (structured output, json_schema) |

AI quality gate — catches what the compiler can't. Runs after successful compilation.

**Reads:** `current_xml`, `compile_result`, `slide_plans`, `critic_mode`, `supplied_content`, `theme_element`
**Writes:** `critic_result`

### Checklist (4 checks)

| Check | What it catches | Severity |
|-------|----------------|----------|
| Component completeness | Plan says 4 KPIs but XML has 2 | HIGH (missing) / MEDIUM (wrong count) |
| Content fidelity | Supplied values not in XML | MEDIUM |
| Structural sanity | Missing root VStack, orphaned text | HIGH (broken) / LOW (deep nesting) |
| Theme adherence | Hardcoded hex instead of $tokens | MEDIUM |

**Pass/fail rule:** any HIGH severity issue → `passed=false` → triggers retry.

### Modes
- **auto** — runs the LLM check (current)
- **manual** — returns `passed=true` (human checkpoint placeholder)
- **off** — skipped entirely via `route_after_validator()`

---

## 9. Repairer Agent

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/repairer.py` |
| **LLM** | Yes |

3-tier escalating repair strategy. Builds a repair prompt and calls the LLM; the graph routes back to generator.

**Reads:** `current_xml`, `normalize_result`, `validate_result`, `compile_result`, `critic_result`, `contract`, `slide_plans`, `generation_history`, `retry_tier`, `retry_count`
**Writes:** `current_xml` (repaired), `retry_tier`, `retry_count`, `stall_detected`, `generation_history`

### The 3 tiers

| Tier | Strategy | Template |
|------|----------|----------|
| 1 — Patch | Feed back failing XML + errors + targeted guidance. Fix in place. | `repairer/patch.j2` |
| 2 — Simplify | Regenerate from scratch with simpler constraints. | `repairer/simplify.j2` |
| 3 — Template | Use a verified example XML as skeleton. Replace only content. | `repairer/template.j2` |

### Stall detection
Compares error signatures between consecutive attempts using `repair_guidance.error_signatures()`. If ≥80% of current errors appeared in the previous attempt → **stall detected** → escalate to next tier.

### Template selection (tier 3)
```
has chart+table → mixed-slide.xml
has chart       → chart-slide.xml
has table       → table-slide.xml
has kpi_row     → kpi-slide.xml
else            → text-slide.xml
```

---

## 10. Evaluator Agent

| | |
|-|-|
| **Status** | ✅ Complete |
| **File** | `src/agents/evaluator.py` |
| **LLM** | No (mechanical) |

Mechanical scoring. Computes pass/fail, token usage, cost estimates, and writes `run-manifest.json`.

**Reads:** All slices
**Writes:** `evaluation`, `pptx_path`, `passed`

**Pass rule:** `passed = compile_result.ok AND critic_result.passed`

---

## 11. Prompt System

All prompts are Jinja2 templates in `src/prompts/`.

| Template | Used by | Purpose |
|----------|---------|---------|
| `planner/system.j2` | planner | Component vocabulary, density/font tier definitions, content rules |
| `planner/user.j2` | planner | Raw request + theme + supplied content + components hint |
| `generator/system.j2` | generator, repairer | Tiered POM rules (critical rules always, attrs/layout/shrink conditional) |
| `generator/user.j2` | generator, repairer | Objective + components + density + layout + data |
| `repairer/patch.j2` | repairer (tier 1) | Previous XML + errors + targeted fix guidance |
| `repairer/simplify.j2` | repairer (tier 2) | Simplification rules + allowed nodes |
| `repairer/template.j2` | repairer (tier 3) | Verified template XML skeleton |
| `critic/system.j2` | critic | 4-point checklist (completeness, fidelity, structure, theme) |
| `critic/user.j2` | critic | Generated XML + plan + supplied content + theme |

### POM-specific rules enforced in prompts

- **Colors:** `6-digit hex NO #` prefix, `$token` references from Theme element
- **Margin/Padding:** single number (`margin="10"`) or dot notation (`margin.top="48"`), never CSS shorthand
- **Dimensions:** `w`, `h`, `fontSize` must be > 0
- **Layout enums:** `alignItems`/`justifyContent` = start|center|end (NOT left/right)
- **Tag names:** PascalCase and case-sensitive
- **Table cells:** every `<Td>` needs explicit `backgroundColor` AND `color`
- **Dark themes:** wrap `<Chart>` in a light-background container (axis text renders black)

---

## 12. Compiler Infrastructure

Three modules in `src/compiler/` bridge the Python pipeline to the Node.js POM compiler.

### normalizer.py
Strips LLM artifacts and auto-fixes common mistakes:

| Fix | Code | Auto-fixed? |
|-----|------|-------------|
| Strip ````xml` fences | MARKDOWN_FENCE | Yes |
| Remove `#` from hex colors | HASH_COLOR | Yes |
| Remove `<br>`, `<hr>` | (silent) | Yes |
| Remove `gap="0"`, `padding="0"` | ZERO_SPACING | Yes |
| Flag `w="0"`, `h="0"`, `fontSize="0"` | ZERO_DIM | No (blocks) |

`pre_validate()` is the regex fallback when the Node compiler isn't available.

### compiler_client.py
Subprocess bridge to `compile-pom.js`:
- `validate_xml(xml, dir)` — runs `--validate-only` (parseXml, no PPTX)
- `compile_xml(xml, dir)` — full `buildPptx`, writes `input.xml` → reads `compile-result.json`
- Raises `CompilerError` for harness issues

### repair_guidance.py
Builds targeted fix instructions from errors:
- **Tag translations:** `<div>` → VStack, `<p>` → Text, `<span>` → Span, etc. (30+ mappings)
- **Attribute translations:** `width` → w, `height` → h, `font-size` → fontSize, etc.
- **Stall detection:** `error_signatures()` + `is_stalled()` (≥80% overlap threshold)

---

## 13. Test Coverage

68+ unit tests across 8 test files in `tests/unit/`. LLM calls are mocked via `@patch`.

| File | Tests | Covers |
|------|-------|--------|
| `test_state.py` | 10 | initial_state keys, custom values, sub-structures, history append |
| `test_graph.py` | 12 | Graph build/compile, 4 routing functions, 2 e2e (skip planner, with planner) |
| `test_planner.py` | 15 | Template rendering, TypedDict conversion, mocked LLM calls |
| `test_context_builder.py` | 32 | Node/attribute/notes/example/layout selection, full contract, prompt token counting |
| `test_generator.py` | — | Generator with mocked LLM |
| `test_validator.py` | — | Normalizer + compiler client with mocked subprocess |
| `test_repairer.py` | — | 3-tier repair with mocked LLM |
| `test_critic.py` | — | Critic with mocked LLM structured output |

---

## 14. Test Cases

21 YAML test cases in `tests/cases/`, loaded by `src/utils/case_loader.py`.

| Case | Components |
|------|-----------|
| `text-only` | title + narrative |
| `title-and-narrative` | title + narrative |
| `kpi-row` | title + kpi_row |
| `single-chart` | title + chart |
| `single-table` | title + table |
| `chart-and-narrative` | title + chart + narrative |
| `chart-and-table` | title + chart + table |
| `table-and-narrative` | title + table + narrative |
| `mixed-executive-slide` | title + kpi + chart + table |
| `minimal-statement` | title only (sparse) |
| `maximal-density` | title + kpi + chart + bullet + table + caption |
| `timeline-roadmap` | title + timeline |
| `flowchart` | title + flow |
| `architecture-diagram` | title + layer |
| `inline-formatting` | title + narrative (B/I/Span) |
| `matrix-prioritization` | title + matrix |
| `tree-org-chart` | title + tree |
| `process-arrow-onboarding` | title + process_arrow |
| `pyramid-strategy` | title + pyramid |
| `mixed-chart-matrix` | title + chart + matrix |
| `mixed-process-timeline-table` | title + process + timeline + table |

---

## 15. File Map

```
presentation-pipeline/
├── pyproject.toml              — project config, dependencies
├── models.yaml                 — per-step LLM model config + pricing
├── .env.example                — OPENAI_API_KEY template
│
├── src/
│   ├── state.py                — PresentationState TypedDict + sub-structures
│   ├── graph.py                — LangGraph StateGraph, routing, CLI entry
│   │
│   ├── agents/
│   │   ├── planner.py          — LLM-powered component planning
│   │   ├── planner_schema.py   — PlannerOutput Pydantic model
│   │   ├── context_builder.py  — knowledge base → contract dict
│   │   ├── generator.py        — LLM XML generation with tiered prompts
│   │   ├── validator.py        — normalize → parseXml → buildPptx
│   │   ├── critic.py           — AI quality gate (4-point checklist)
│   │   ├── critic_schema.py    — CriticOutput Pydantic model
│   │   ├── repairer.py         — 3-tier escalating retry
│   │   └── evaluator.py        — scoring + run-manifest.json
│   │
│   ├── compiler/
│   │   ├── normalizer.py       — XML cleanup + regex pre_validate
│   │   ├── compiler_client.py  — Node subprocess bridge
│   │   └── repair_guidance.py  — error → fix instructions + stall detect
│   │
│   ├── prompts/
│   │   ├── planner/            — system.j2, user.j2
│   │   ├── generator/          — system.j2 (tiered), user.j2
│   │   ├── repairer/           — patch.j2, simplify.j2, template.j2
│   │   └── critic/             — system.j2, user.j2
│   │
│   └── utils/
│       ├── llm_client.py       — get_llm(step), get_pricing(model)
│       ├── logging_config.py   — structured logging with contextvars
│       └── case_loader.py      — YAML test case → PresentationState
│
├── tests/
│   ├── cases/                  — 21 YAML test case definitions
│   └── unit/                   — 68+ unit tests (8 files)
│
└── (sibling) presentation-mvp/
    ├── pom-knowledge/          — YAML knowledge base
    └── node/compile-pom.js     — @hirokisakabe/pom v10.3.0 compiler wrapper
```

---

## 16. Status & What's Left

### Completed

| Phase | Deliverables |
|-------|-------------|
| Phase 0 — Scaffold | state.py, graph.py, llm_client.py, models.yaml, all 7 nodes wired, 22 tests |
| Phase 1 — Planner | planner.py + planner_schema.py + Jinja2 templates, structured output, 15 tests |
| Phase 2 — Context Builder + Prompts | context_builder.py, generator system.j2/user.j2 (tiered), 32 tests, token counts verified |
| Phase 3 — Generator + Validator + Repairer | generator.py (LLM), validator.py (normalize → validate → compile), repairer.py (3-tier), compiler/, repair templates |
| Phase 4 — Critic | critic.py + critic_schema.py + templates, structured output, dual-mode |

### Remaining

| Phase | Status | Deliverables |
|-------|--------|-------------|
| Phase 5 — Observability + Testing | Pending | LangSmith tracing, run manifests with run IDs, integration tests, CI pipeline |
| Phase 6 — Advanced features | Pending | Manual critic, parallel slide gen (deck mode), visual verification, web UI |

### What the pipeline handles today
- Any of the 14 component kinds in single-slide mode
- Maximal density slides (6+ components on 1280x720)
- Theme-aware generation with $token color references
- Dark theme handling (chart axis wrapping)
- Supplied content fidelity (verbatim values)
- 3-tier retry with stall detection and escalation
- AI quality gate (completeness, fidelity, structure, theme)
- Run manifests with per-step cost tracking

### What's not wired yet
- **Deck mode execution** — planner can plan multi-slide decks, but generator/validator process only `slide_plans[0]`
- **Manual critic** — returns `passed=true` as placeholder
- **LangSmith tracing** — config is set up but no tracing callback registered
- **Integration tests** — unit tests mock the LLM and compiler
- **Visual verification** — no screenshot comparison

---

## End-to-End Data Flow

```
User request: "Create a KPI dashboard slide"
     │
     ▼
initial_state(run_id, raw_request, theme_name, ...)
     │
     ▼ route_after_start → planner (if threshold > 0)
┌─────────────────────────────────────────────────┐
│ PLANNER                                         │
│ LLM → PlannerOutput (json_schema)               │
│ → slide_plans: [{                               │
│     components: [{kind:"title"}, {kind:"kpi_row",│
│                   count:4}],                     │
│     density: "normal",                           │
│     font_tier: "standard",                       │
│     layout_hint: "Title top, KPI tiles in row"   │
│   }]                                            │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ CONTEXT BUILDER                                 │
│ kinds → ["title", "kpi_row"]                    │
│ nodes → [Slide, Theme, VStack, HStack, Text,    │
│          Shape, Span, ...]                      │
│ attrs → {VStack: [gap, alignItems, ...], ...}   │
│ notes → [translations, semantic rules, ...]      │
│ theme → <Theme surface="F7F9FC" ... />          │
│ → contract dict                                 │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ GENERATOR                                       │
│ Render system.j2 (standard tier ~2.5K tokens)   │
│ Render user.j2 (objective + components + data)  │
│ LLM → raw POM XML                              │
│ → current_xml, generation_history               │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ VALIDATOR                                       │
│ 1. normalize_xml → strip fences, fix colors     │
│ 2. validate_xml  → parseXml (--validate-only)   │
│ 3. compile_xml   → buildPptx → .pptx           │
│ → compile_result {ok, pptx_path, diagnostics}   │
└─────────────────────────────────────────────────┘
     │
     ▼ route_after_validator
     │
     ├─ compile failed + retryable ──▶ REPAIRER ──▶ GENERATOR (loop)
     │
     ▼ compile ok
┌─────────────────────────────────────────────────┐
│ CRITIC                                          │
│ LLM → CriticOutput (json_schema)                │
│ 4 checks: completeness, fidelity, structure,    │
│           theme adherence                       │
│ → critic_result {passed, issues}                │
└─────────────────────────────────────────────────┘
     │
     ▼ route_after_critic
     │
     ├─ critic failed + budget ──▶ REPAIRER ──▶ GENERATOR (loop)
     │
     ▼ critic passed
┌─────────────────────────────────────────────────┐
│ EVALUATOR                                       │
│ passed = compile_ok AND critic_ok               │
│ Compute tokens, cost, retry summary             │
│ Write run-manifest.json                         │
│ → evaluation, pptx_path, passed                 │
└─────────────────────────────────────────────────┘
     │
     ▼
Output: .pptx file + run-manifest.json
```
