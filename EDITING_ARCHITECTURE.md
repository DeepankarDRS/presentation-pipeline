# Editing Architecture: Loosely Coupled Tools & State Re-Entry

## Context

The current pipeline is a one-shot flow: prompt → plan → generate → validate → compile → done. Once a deck is generated, there's no way to go back and change one slide, swap a theme, reorder pages, or regenerate a single component without re-running the entire pipeline.

This document defines the architecture for **loosely coupled, re-entrant editing** — where any tool (planner, generator, critic, compiler) can be triggered independently against stored state, and the user can review, modify, and re-enter the pipeline at any point.

---

## Design Principles

### 1. XML is the Source of Truth

Every slide's generated POM XML is stored persistently. When the user edits a slide, we modify the stored XML and re-compile — we don't re-run the LLM. When the user regenerates a slide, we pass the stored XML as context ("here's the current version, now change X").

### 2. State is Versioned and Resumable

The pipeline state (`PresentationState`) is snapshoted at key checkpoints. Any editing operation creates a new state version by forking from a checkpoint and applying a delta. The user can always go back to a previous version.

### 3. Tools are Independently Triggerable

Each pipeline stage (planner, generator, validator, critic, style resolver) can be invoked as a standalone function with explicit inputs and outputs. The LangGraph topology is the *default* wiring, but editing operations call tools directly without traversing the full graph.

### 4. Granularity Levels

Operations happen at three levels:
- **Deck level**: theme swap, reorder slides, add/remove slides, regenerate entire deck
- **Slide level**: regenerate one slide, change its plan, swap layout
- **Element level**: edit text, change a chart's data, update a KPI value

---

## State Model for Editing

### Current State (One-Shot)

```
PresentationState
├── run_id
├── slide_plans[]           ← planning output
├── completed_slides[]      ← per-slide XML after generation
├── current_xml             ← final combined XML
├── compile_result          ← last compile outcome
└── pptx_path               ← final output file
```

### Extended State (Editable)

```
DeckState
├── deck_id                 ← persistent ID across edits
├── version                 ← incremented on every edit
├── core_hook               ← narrative anchor
├── theme                   ← resolved theme (colors, fonts, spacing)
├── slide_order: int[]      ← ordered list of slide IDs
│
├── slides: dict[slide_id → SlideState]
│   ├── slide_id            ← stable ID (survives reordering)
│   ├── plan: SlidePlan     ← planning output for this slide
│   ├── xml: str            ← current POM XML
│   ├── compiled: bool      ← whether xml has been compiled successfully
│   ├── pptx_fragment: str  ← path to compiled single-slide PPTX (optional)
│   ├── version: int        ← slide-level version counter
│   └── history: list[SlideVersion]
│       ├── xml             ← XML at this version
│       ├── timestamp
│       ├── trigger         ← "generate" | "edit" | "regenerate" | "theme_swap"
│       └── diff_summary    ← what changed
│
├── compile_result          ← last full-deck compile
├── pptx_path               ← current deck PPTX
└── manifests: list[RunManifest]  ← all generation/edit runs
```

### Key Differences from Current State

| Concern | Current | Extended |
|---------|---------|---------|
| Slide identity | Array index (`slide_index: 0, 1, 2`) | Stable UUID (`slide_id`) — survives reorder/insert |
| XML storage | `completed_slides[]` with `slide_index` key | Per-slide `SlideState.xml` keyed by `slide_id` |
| Version history | `generation_history[]` (flat list of attempts) | Per-slide `history[]` + deck-level `version` |
| Deck structure | Implicit from `slide_plans` order | Explicit `slide_order: int[]` — reorderable |
| Theme | `theme_name` string looked up at generation time | `theme` object resolved once, reusable |

---

## Editing Operations

### Deck-Level Operations

#### D1: Reorder Slides

**Input:** New `slide_order` array (e.g., `[slide_3, slide_1, slide_2]`)

**Process:**
1. Update `DeckState.slide_order`
2. Re-run `deck_assembler` to combine XMLs in new order
3. Re-compile
4. No LLM calls needed

**State delta:** Only `slide_order`, `compile_result`, `pptx_path` change. No slide XML changes.

---

#### D2: Add Slide

**Input:** Position index + either a `SlidePlan` or a natural language description

**Process:**
1. If NL description → run `planner` for a single slide (not the whole deck)
2. Create new `SlideState` with generated plan
3. Run `context_builder → generator → validator → critic` for the new slide only
4. Insert `slide_id` into `slide_order` at the requested position
5. Re-run `deck_assembler` + re-compile full deck

**State delta:** New entry in `slides`, updated `slide_order`, re-compiled deck.

---

#### D3: Remove Slide

**Input:** `slide_id` to remove

**Process:**
1. Remove `slide_id` from `slide_order`
2. Keep `SlideState` in `slides` dict (soft delete — history preserved)
3. Re-run `deck_assembler` + re-compile

**State delta:** Updated `slide_order`, re-compiled deck. Slide data retained for undo.

---

#### D4: Swap Theme (Deck-Wide)

**Input:** New theme name or custom color palette

**Process:**
1. Resolve new theme via `style_resolver`
2. For each slide in `slide_order`:
   a. Replace `<Theme .../>` in stored XML with new theme element
   b. Run `normalizer` to fix any theme-variable references (`$accent`, `$surface`, etc.)
3. Re-compile full deck

**State delta:** Every slide's XML gets theme element replaced. All slides re-compiled. No LLM calls needed (theme swap is mechanical).

---

#### D5: Regenerate Entire Deck

**Input:** Modified prompt or parameters

**Process:** Full pipeline re-run (same as current one-shot flow). Creates a new `version` of the deck. Previous version preserved in history.

---

### Slide-Level Operations

#### S1: Regenerate Single Slide

**Input:** `slide_id` + optional modified instructions

**Process:**
1. Load `SlideState.plan` for this slide
2. If instructions provided, merge them into the plan (e.g., "use a bar chart instead of pie")
3. Run the single-slide pipeline: `context_builder → generator → validator → critic → repairer`
4. On success, update `SlideState.xml` and increment `SlideState.version`
5. Store previous XML in `SlideState.history`
6. Re-run `deck_assembler` + re-compile full deck

**State delta:** One slide's XML changes. Full deck re-compiled.

**Key design decision:** The generator receives the *previous* XML as context:
```
You previously generated this slide:
<previous XML>

The user wants the following change:
<instructions>

Generate an updated version of this slide.
```

This gives the LLM continuity — it can preserve what worked and change what was requested.

---

#### S2: Change Slide Plan

**Input:** `slide_id` + modified `SlidePlan` (e.g., change components, density, layout_hint)

**Process:**
1. Update `SlideState.plan`
2. Run `context_builder → generator → validator → critic → repairer`
3. Update `SlideState.xml`
4. Re-compile deck

This is like S1 but the plan itself changes, not just the generation instructions.

---

#### S3: Swap Slide Layout

**Input:** `slide_id` + new `layout_hint`

**Process:**
1. Update `layout_hint` in `SlideState.plan`
2. Regenerate with instruction: "Use this layout: {new_layout_hint}. Keep all content the same."
3. Update XML, re-compile

---

### Element-Level Operations

#### E1: Edit Text Content

**Input:** `slide_id` + element path + new text

**Process:**
1. Parse `SlideState.xml`
2. Find the target `<Text>` element (by content match or structural path)
3. Replace text content
4. Re-compile (no LLM call)

**Example:**
```
Edit slide "intro", change title from "Q3 Results" to "Q3 2025 Results"
```

This is a direct XML manipulation — find `<Text fontSize="32" bold="true">Q3 Results</Text>`, replace inner text.

---

#### E2: Update Chart/KPI Data

**Input:** `slide_id` + data update (new values, labels, series)

**Process:**
1. Parse `SlideState.xml`
2. Find the `<Chart>` or KPI elements
3. Update `<ChartDataPoint>` values, labels, etc.
4. Re-compile (no LLM call)

**Example:**
```
Update chart data: Q4 revenue from $42.8M to $45.1M
```

---

#### E3: AI-Assisted Element Edit

**Input:** `slide_id` + natural language instruction about a specific element

**Process:**
1. Extract the current XML for the slide
2. Run a targeted LLM call: "Here's the slide XML. The user wants to: {instruction}. Modify only the relevant elements."
3. Validate + compile the result
4. Update stored XML

This is for edits too complex for mechanical XML manipulation — e.g., "make the chart show percentages instead of absolute values" or "add a fourth KPI tile for churn rate."

---

## Tool Decoupling Architecture

### Current: Tightly Coupled Graph

```
planner ──→ context_builder ──→ generator ──→ validator ──→ critic
                                                              │
                                                         repairer (loop)
```

Every node reads from and writes to `PresentationState`. You can't call `generator` without first running `context_builder`, because `generator` depends on `contract` which `context_builder` writes.

### Target: Loosely Coupled Tools

Each tool becomes a **standalone callable** with explicit typed inputs and outputs:

```python
# Instead of:
def generator_node(state: PresentationState) -> dict[str, Any]:
    contract = state.get("contract")  # implicit dependency
    ...

# Becomes:
class GeneratorTool:
    def invoke(
        self,
        plan: SlidePlan,
        contract: dict,
        theme_element: str,
        previous_xml: str | None = None,
        instructions: str | None = None,
    ) -> GeneratorResult:
        """Generate POM XML for a single slide."""
        ...

@dataclass
class GeneratorResult:
    xml: str
    tokens_in: int
    tokens_out: int
    model: str
```

The LangGraph node becomes a **thin adapter** that reads state, calls the tool, and writes state back:

```python
def generator_node(state: PresentationState) -> dict[str, Any]:
    """LangGraph adapter — delegates to GeneratorTool."""
    tool = GeneratorTool()
    result = tool.invoke(
        plan=_current_plan(state),
        contract=state["contract"],
        theme_element=state["theme_element"],
    )
    return {
        "current_xml": result.xml,
        "generation_history": [result.to_attempt_record()],
    }
```

Now the same `GeneratorTool` can be called:
- By the LangGraph node (default full-pipeline flow)
- By an API endpoint (single-slide regeneration)
- By an editing operation (S1: regenerate with instructions)
- By a test (with mocked inputs, no state needed)

### Tool Inventory

| Tool | Inputs | Outputs | LLM? |
|------|--------|---------|------|
| `PlannerTool` | raw_request, theme_name, supplied_content, audience_context | PlannerOutput (core_hook + slides) | Yes |
| `StyleResolverTool` | theme_name or custom_colors, prompt_context | ResolvedTheme (colors, fonts, spacing) | Maybe |
| `ContextBuilderTool` | slide_plan, knowledge_dir, resolved_theme | Contract dict + theme_element | No |
| `GeneratorTool` | plan, contract, theme_element, previous_xml?, instructions? | GeneratorResult (xml, tokens) | Yes |
| `NormalizerTool` | xml | NormalizeResult (fixed_xml, issues) | No |
| `ValidatorTool` | xml, output_dir | ValidateResult (ok, diagnostics) | No |
| `CompilerTool` | xml, output_dir | CompileResult (ok, pptx_path, diagnostics) | No |
| `CriticTool` | xml, plan, contract | CriticResult (passed, issues) | Yes |
| `RepairerTool` | xml, errors, contract, plan, tier | RepairResult (xml, tier, stalled) | Yes |
| `DeckAssemblerTool` | slide_xmls[], theme_element, output_dir | CompileResult + combined_xml | No |
| `TextEditorTool` | xml, element_path, new_text | edited_xml | No |
| `DataEditorTool` | xml, data_update | edited_xml | No |
| `ThemeSwapperTool` | xml, new_theme_element | edited_xml | No |

### Tool Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

I = TypeVar("I")  # Input type
O = TypeVar("O")  # Output type

class PipelineTool(ABC, Generic[I, O]):
    """Base for all pipeline tools. Independently callable, testable, composable."""

    @abstractmethod
    def invoke(self, input: I) -> O:
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def requires_llm(self) -> bool:
        return False
```

---

## State Re-Entry Points

The key insight: editing operations re-enter the pipeline at different points depending on what changed.

```
                    ┌──────────────────────────────────────────┐
                    │            User Edit Action               │
                    └────────────┬─────────────────────────────┘
                                 │
                    ┌────────────▼─────────────────────────────┐
                    │        What changed?                      │
                    └────────────┬─────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
    │  Deck-level   │   │  Slide-level  │   │ Element-level │
    └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
            │                    │                    │
    ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
    │ Reorder/Add/  │   │ Regen slide   │   │ XML edit      │
    │ Remove/Theme  │   │ Change plan   │   │ (no LLM)      │
    └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
            │                    │                    │
            │           ┌───────▼───────┐            │
            │           │ context_builder│            │
            │           │ → generator   │            │
            │           │ → validator   │            │
            │           │ → critic      │            │
            │           └───────┬───────┘            │
            │                    │                    │
            ▼                    ▼                    ▼
    ┌────────────────────────────────────────────────────────┐
    │              deck_assembler (combine XMLs)             │
    └────────────────────────┬───────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    compiler     │
                    │  (XML → PPTX)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Updated PPTX   │
                    └─────────────────┘
```

### Re-Entry Decision Matrix

| Operation | Re-entry Point | LLM Calls | Slides Affected |
|-----------|---------------|-----------|-----------------|
| Reorder slides | deck_assembler | 0 | None (order only) |
| Remove slide | deck_assembler | 0 | None (removal only) |
| Add slide | context_builder (new slide only) | 1-2 (gen + critic) | New slide only |
| Swap theme | normalizer (all slides) | 0 | All (mechanical) |
| Regenerate slide | context_builder (one slide) | 1-2 (gen + critic) | One slide |
| Change slide plan | context_builder (one slide) | 1-2 (gen + critic) | One slide |
| Edit text | direct XML edit | 0 | One slide |
| Update chart data | direct XML edit | 0 | One slide |
| AI-assisted edit | generator (targeted) | 1 | One slide |
| Regenerate deck | planner (full) | N+1 (plan + N slides) | All |

---

## API Design for Editing

### Endpoints

```
# ── Generation ──
POST   /api/generate              # Full pipeline: prompt → PPTX
POST   /api/plan                  # Plan only: prompt → DeckPlan (for review)
POST   /api/plan/{deck_id}/approve   # Approve plan, start generation

# ── Deck Operations ──
GET    /api/decks/{deck_id}       # Get deck state
GET    /api/decks/{deck_id}/pptx  # Download current PPTX
PUT    /api/decks/{deck_id}/order # Reorder slides
PUT    /api/decks/{deck_id}/theme # Swap theme
POST   /api/decks/{deck_id}/regenerate  # Full regeneration

# ── Slide Operations ──
GET    /api/decks/{deck_id}/slides/{slide_id}          # Get slide state + XML
POST   /api/decks/{deck_id}/slides                      # Add new slide
DELETE /api/decks/{deck_id}/slides/{slide_id}           # Remove slide
POST   /api/decks/{deck_id}/slides/{slide_id}/regenerate  # Regenerate one slide
PUT    /api/decks/{deck_id}/slides/{slide_id}/plan      # Change slide plan
PUT    /api/decks/{deck_id}/slides/{slide_id}/layout    # Swap layout

# ── Element Operations ──
PUT    /api/decks/{deck_id}/slides/{slide_id}/text      # Edit text
PUT    /api/decks/{deck_id}/slides/{slide_id}/data      # Update chart/KPI data
POST   /api/decks/{deck_id}/slides/{slide_id}/ai-edit   # AI-assisted edit

# ── History ──
GET    /api/decks/{deck_id}/versions                    # List deck versions
GET    /api/decks/{deck_id}/versions/{version}          # Get specific version
POST   /api/decks/{deck_id}/revert/{version}            # Revert to version
```

### WebSocket for Live Updates

```
WS /api/decks/{deck_id}/stream

# Server sends events during generation/editing:
{ "type": "planning", "progress": 0.1 }
{ "type": "generating_slide", "slide_id": "abc", "slide_index": 0, "total": 5 }
{ "type": "validating", "slide_id": "abc" }
{ "type": "slide_complete", "slide_id": "abc", "compiled": true }
{ "type": "assembling" }
{ "type": "done", "pptx_path": "/output/runs/xyz/deck/output.pptx" }
```

---

## XML Storage Strategy

### Where XML Lives

```
output/
└── decks/
    └── {deck_id}/
        ├── deck-state.json          ← serialized DeckState
        ├── deck.pptx                ← current compiled deck
        ├── slides/
        │   ├── {slide_id}/
        │   │   ├── current.xml      ← current POM XML
        │   │   ├── compiled.pptx    ← single-slide PPTX (for preview)
        │   │   └── history/
        │   │       ├── v1.xml
        │   │       ├── v2.xml
        │   │       └── versions.json ← metadata for each version
        │   └── {slide_id}/
        │       └── ...
        └── manifests/
            ├── run-001.json          ← initial generation manifest
            ├── run-002.json          ← edit operation manifest
            └── ...
```

### XML Reuse Patterns

**Pattern 1: Theme Swap (Mechanical)**
```python
def swap_theme(xml: str, new_theme_element: str) -> str:
    """Replace <Theme .../> in XML with new theme element."""
    # 1. Extract existing <Theme .../> via regex
    # 2. Replace with new_theme_element
    # 3. Run normalizer to fix $variable references
    return updated_xml
```

**Pattern 2: Slide Regeneration (LLM with Context)**
```python
def regenerate_slide(
    slide_state: SlideState,
    instructions: str | None = None,
) -> str:
    """Regenerate a slide's XML, using previous version as context."""
    # 1. Load slide's current XML and plan
    # 2. Build generator prompt with:
    #    - The plan (components, density, layout_hint)
    #    - The previous XML ("here's what you generated before")
    #    - The user's instructions ("change the chart type to line")
    # 3. Run generator → validator → critic → repairer
    # 4. Return new XML
    return new_xml
```

**Pattern 3: Deck Assembly (Combine)**
```python
def assemble_deck(deck_state: DeckState) -> str:
    """Combine individual slide XMLs into one POM document."""
    theme = deck_state.theme_element
    slide_xmls = []
    for slide_id in deck_state.slide_order:
        slide = deck_state.slides[slide_id]
        block = extract_slide_block(slide.xml)  # Strip <Theme> from individual
        slide_xmls.append(block)
    return theme + "\n" + "\n".join(slide_xmls)
```

**Pattern 4: Element-Level Edit (Direct XML Manipulation)**
```python
def edit_text_in_xml(xml: str, old_text: str, new_text: str) -> str:
    """Find and replace text content in XML."""
    # Parse XML, find <Text> elements containing old_text
    # Replace inner text
    # Serialize back to string
    return updated_xml

def update_chart_data(xml: str, new_data: dict) -> str:
    """Update ChartDataPoint values in XML."""
    # Parse XML, find <Chart> → <ChartSeries> → <ChartDataPoint>
    # Replace value/label attributes
    # Serialize back
    return updated_xml
```

---

## State Machine for Editing

Each edit operation follows a state machine:

```
                    ┌─────────┐
                    │  IDLE   │ ← deck exists, no active operation
                    └────┬────┘
                         │ user triggers edit
                    ┌────▼────┐
                    │ EDITING │ ← XML modification in progress
                    └────┬────┘
                         │
                ┌────────┼────────┐
                │        │        │
        ┌───────▼──┐ ┌───▼───┐ ┌─▼────────┐
        │ COMPILE  │ │ REGEN │ │ VALIDATE  │
        │ (no LLM) │ │ (LLM) │ │ (compile) │
        └───────┬──┘ └───┬───┘ └─┬────────┘
                │        │        │
                └────────┼────────┘
                         │
                    ┌────▼────┐
                    │ASSEMBLE │ ← combine all slides into deck
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │COMPILED │ ← new PPTX ready
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  IDLE   │ ← ready for next edit
                    └─────────┘
```

### Concurrency

Multiple edit operations on different slides can run in parallel:
- Regenerating slide 2 while the user edits text on slide 4 → no conflict
- Two operations on the same slide → serialize (queue the second)
- Theme swap → must wait for all in-progress operations to complete (affects all slides)

---

## Migration Path from Current Architecture

### Phase 1: Introduce DeckState (Non-Breaking)

Add `DeckState` as a wrapper around `PresentationState` that's created *after* the pipeline completes. The existing pipeline stays unchanged — DeckState is built from the final state as a post-processing step.

```python
def build_deck_state(final_state: PresentationState) -> DeckState:
    """Convert pipeline output to editable DeckState."""
    slides = {}
    for completed in final_state["completed_slides"]:
        slide_id = generate_id()
        slides[slide_id] = SlideState(
            slide_id=slide_id,
            plan=final_state["slide_plans"][completed["slide_index"]],
            xml=completed["xml"],
            compiled=True,
            version=1,
            history=[],
        )
    return DeckState(
        deck_id=generate_id(),
        version=1,
        slides=slides,
        slide_order=list(slides.keys()),
        ...
    )
```

### Phase 2: Extract Tools from Graph Nodes

Refactor each agent from a state-coupled function to a Tool + LangGraph adapter pair. This is mechanical — no behavior changes, just separating the "read state / write state" wrapper from the "do the work" logic.

Before:
```
src/agents/generator.py  ← one function that reads state, calls LLM, writes state
```

After:
```
src/tools/generator.py   ← GeneratorTool.invoke(plan, contract, ...) → GeneratorResult
src/agents/generator.py  ← generator_node(state) calls GeneratorTool, writes state
```

### Phase 3: Add Editing API

Build the `/api/decks/{deck_id}/slides/{slide_id}/regenerate` etc. endpoints. Each endpoint:
1. Loads `DeckState` from disk
2. Calls the appropriate tool(s) directly
3. Updates `DeckState`
4. Re-assembles and re-compiles
5. Saves updated state to disk

### Phase 4: Add WebSocket Streaming

Wire up Server-Sent Events or WebSocket for live progress during generation and editing.

---

## Example: Full User Journey

```
1. User submits: "Create a Q3 board report with revenue KPIs, 
   segment breakdown, and pipeline forecast"

2. Pipeline runs:
   questionnaire (interactive) → answers: {audience: "board", tone: "formal"}
   planner → core_hook: "Revenue grew 40% but CAC is rising"
           → 5 slides: cover, KPI dashboard, segment chart, 
             pipeline forecast, closing

3. User reviews plan in UI:
   "Move the pipeline slide before the segment slide"
   → Reorder: no LLM call, just slide_order change

4. User approves plan → generation runs (5 slides, ~30 seconds)

5. User previews deck:
   "Change the bar chart on slide 3 to a line chart"
   → S2 (change plan): update chart_type in plan, regenerate slide 3 only
   → 1 LLM call, ~5 seconds

6. "Update the ARR KPI from $42.8M to $45.1M"
   → E2 (data edit): direct XML manipulation, no LLM
   → Re-compile, ~2 seconds

7. "Switch to dark theme"
   → D4 (theme swap): mechanical replacement in all slides
   → Re-compile, ~3 seconds

8. "Add a slide about customer satisfaction after the KPI dashboard"
   → D2 (add slide): plan + generate 1 new slide, insert at position 2
   → 2 LLM calls, ~8 seconds

9. User downloads final PPTX
```

Total: 8 LLM calls across the session (5 initial + 1 regen + 2 for new slide), instead of 30+ if the user had to regenerate the full deck each time.

---

## Summary

| Concern | Decision |
|---------|----------|
| Source of truth | Stored POM XML per slide |
| Identity | Stable `slide_id` UUIDs, not array indices |
| Versioning | Per-slide + per-deck version counters |
| Tool coupling | Standalone tools with explicit I/O, LangGraph nodes are thin adapters |
| Re-entry | Decision matrix based on what changed → minimal re-processing |
| Concurrency | Parallel edits on different slides, serialize same-slide edits |
| Storage | File-based (`output/decks/{deck_id}/`) — database optional later |
| API | REST + WebSocket for editing and live progress |
