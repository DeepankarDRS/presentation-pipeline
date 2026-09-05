# GenOffice Feature Adoption Plan

## Context

This document analyzes [genspark-ai/genoffice](https://github.com/genspark-ai/genoffice) — specifically its `slides-skill.ts` (~80KB) — and maps its capabilities against our LangGraph presentation pipeline. The goal is to identify which GenOffice features we should adopt to produce better deck plans and slide-level output.

Our pipeline currently: prompt → planner → context_builder → generator → validator → critic → repairer → evaluator. For multi-slide decks, a slide_router/deck_assembler loop handles per-slide generation and final assembly.

GenOffice's pipeline: questionnaire → research → style → plan → generate (per-page) → layout audit → done.

---

## GenOffice Architecture Summary

### Pipeline Stages

| Stage | What It Does | LLM Call? |
|-------|-------------|-----------|
| `ask_clarification` | Presents 2-4 trade-off questions about audience/tone/data depth/visual style before planning | No (template) |
| `generateStyleSkill` | Dedicated call producing a visual style guide: color rules, fonts, layout variants per page type | Yes |
| `planDeckOutline` | Produces `core_hook` (narrative anchor with tension/contrast) + per-page outlines with type/brief/layout/image_queries | Yes |
| `generate_deck` / `generatePageCloud` | Per-page generation with auto image search, live progress events | Yes |
| Layout audit | Post-generation check for overlap, out-of-bounds, text overflow | No (mechanical) |
| `verifyResponse` | Claimed-action guard — inspects final text against executed tools | No (mechanical) |

### Key Data Structures

**Deck Plan (`plan_deck` tool output):**
```typescript
{
  core_hook: string,       // "Revenue grew 40% but margins shrinking"
  style: {                 // Unified design system
    color_palette: string[],
    fonts: { heading: string, body: string },
    layout_variants: Record<PageType, string[]>
  },
  pages: [{
    title: string,
    type: "cover" | "content" | "data" | "closing",
    brief: string,         // What this page communicates
    layout: string,        // "three_column_cards" | "hero_big_number" | ...
    image_queries: string[] // Auto-search keywords
  }]
}
```

**Data Provenance:**
Every data value is tagged with `dataSource`:
- `user` — provided by the user directly
- `document` — extracted from an uploaded document
- `search` — retrieved from web search
- `sample` — AI-generated placeholder (clearly labeled, never presented as real)

**Layout Variety Enforcement:**
GenOffice maintains a list of layout patterns and ensures no two adjacent content pages use the same one:
- `three_column_cards`
- `hero_big_number`
- `two_column`
- `timeline`
- `left_text_right_image`
- `full_width_chart`
- `comparison_table`

**Style Templates:**
Save/load/reuse design systems across decks. A style template captures colors, fonts, layout preferences, and spacing rules as a reusable artifact.

**SmartArt Support:**
GenOffice supports SmartArt types: list, process, cycle, hierarchy, pyramid, matrix, venn. These render as structured diagrams rather than manual shape placement.

**Speaker Notes:**
Auto-generated presenter notes per slide with talking points derived from the page brief.

**Progress Events (`DeckProgressEvent`):**
```typescript
type: "style" | "plan" | "images" | "page_start" | "page_done" | "done"
```
Real-time UI feedback during multi-stage generation.

---

## Feature Comparison

### What We Already Have (No Action Needed)

| Feature | Our Implementation |
|---------|-------------------|
| Structured planning | `PlannerOutput` with components, density, font_tier, layout_hint |
| Component vocabulary | 14 component kinds (title, chart, table, kpi_row, timeline, flow, etc.) |
| Content data generation | `content_data_json` in PlannerSlide — LLM generates realistic values |
| Multi-slide generation | slide_router + deck_assembler loop in LangGraph |
| 3-tier repair | Patch → Simplify → Template with stall detection |
| LLM critic | Auto/manual/off modes with structured issue output |
| Robust output parsing | `with_structured_output(method="json_schema")` — no parsing issues |

### What We Should Add

---

### Tier 1: High Impact, Reasonable Effort

#### 1.1 Narrative Anchor (Core Hook)

**What GenOffice does:** Every deck starts with a `core_hook` — a single sentence capturing the narrative arc with tension/contrast. Example: *"Revenue grew 40% YoY but customer acquisition costs are rising faster."* This drives every slide's framing.

**Why it matters:** Without a narrative anchor, each slide is planned in isolation. The deck becomes a bag of data pages rather than a story. The core hook gives the planner a north star for deciding what to emphasize, what to contrast, and what order to present.

**Implementation plan:**

Add to `PlannerOutput`:
```python
class PlannerOutput(BaseModel):
    core_hook: str = Field(
        description="One sentence narrative anchor with tension/contrast "
                    "that ties the whole deck together. Example: "
                    "'Revenue grew 40% but margins are shrinking due to rising CAC.'"
    )
    slides: list[PlannerSlide] = Field(...)
```

Add to `DeckPlan` in state.py:
```python
class DeckPlan(TypedDict, total=False):
    core_hook: str       # NEW
    slide_count: int
    theme: str
    slides: list[SlidePlan]
```

Update planner system prompt to instruct:
- Always produce a core_hook that captures the deck's central tension
- Each slide's `content_summary` should relate back to the core_hook
- The closing slide should resolve or call-to-action on the core_hook's tension

Pass `core_hook` to the generator via the contract so each slide's content is framed consistently.

**Files to modify:** `planner_schema.py`, `state.py`, `planner.py`, `prompts/planner/system.j2`, `context_builder.py`, `prompts/generator/system.j2`

---

#### 1.2 Slide Type Taxonomy

**What GenOffice does:** Every page has a `type` field: `cover | content | data | section_break | closing`. The generator applies different layout rules per type — cover slides get centered large text, data slides get dense layouts, section breaks get minimal text.

**Why it matters:** Our planner currently treats all slides identically. A cover slide and a data-heavy slide get the same density/font_tier selection logic. Explicit types let the generator and critic apply type-specific rules.

**Implementation plan:**

Add to `PlannerSlide`:
```python
SlideTypeLiteral = Literal["cover", "content", "data", "section_break", "closing"]

class PlannerSlide(BaseModel):
    slide_type: SlideTypeLiteral = Field(
        description="Page type. cover=title page, content=narrative/bullets, "
                    "data=charts/tables/KPIs, section_break=divider between sections, "
                    "closing=takeaways/CTA."
    )
    # ... existing fields
```

Add type-specific rules to generator prompt:
- `cover`: centered title, large fonts, minimal elements, optional subtitle
- `content`: title + body text/bullets, standard density
- `data`: title + charts/tables/KPIs, can be dense
- `section_break`: one line of text, accent color block, sparse
- `closing`: key takeaways as bullets, CTA, contact info

Add type-specific critic rules:
- `cover` with density="dense" → issue
- `data` with no data components → issue
- `closing` without a summary/CTA → warning

**Files to modify:** `planner_schema.py`, `state.py`, `prompts/planner/system.j2`, `prompts/generator/system.j2`, `prompts/critic/system.j2`

---

#### 1.3 Layout Variety Enforcement

**What GenOffice does:** After planning, validates that no two adjacent content/data slides use the same layout pattern. If they do, suggests an alternative from a layout vocabulary.

**Why it matters:** Without enforcement, the LLM tends to repeat the same layout pattern (e.g., every slide gets "title at top, chart below"). This makes decks visually monotonous.

**Implementation plan:**

Define layout vocabulary:
```python
LAYOUT_PATTERNS = [
    "hero_big_number",       # Large KPI + supporting text
    "two_column",            # Left/right split
    "three_column_cards",    # Three equal cards in a row
    "full_width_chart",      # Chart spanning full width
    "chart_table_split",     # Chart left, table right
    "timeline_horizontal",   # Timeline spanning width
    "stacked_sections",      # Vertical stack of 2-3 content blocks
    "left_text_right_image", # Text left, visual right
]
```

Add a post-planner validation step (new function in `planner.py`):
```python
def _enforce_layout_variety(slides: list[PlannerSlide]) -> list[PlannerSlide]:
    """Check adjacent slides for duplicate layouts, suggest alternatives."""
    # Compare layout_hint patterns
    # If two adjacent slides have similar layout_hint, nudge the second
```

This runs after the LLM produces the plan but before the plan is written to state.

**Files to modify:** `planner.py`, `prompts/planner/system.j2` (add layout vocabulary)

---

#### 1.4 Speaker Notes

**What GenOffice does:** Auto-generates presenter notes per slide with talking points derived from the page brief.

**Why it matters:** Real presentations need speaker notes. Minimal effort since POM XML already supports `<Notes>` inside `<Slide>`.

**Implementation plan:**

Add to `PlannerSlide`:
```python
speaker_notes: str = Field(
    default="",
    description="2-3 bullet points of talking points for the presenter. "
                "Should expand on the slide's content, not repeat it."
)
```

Pass `speaker_notes` through the contract to the generator. The generator emits:
```xml
<Slide>
  <VStack ...>...</VStack>
  <Notes>
    - Revenue grew 40% driven by enterprise segment
    - CAC increase is a concern but LTV/CAC ratio remains healthy
    - Recommend increasing investment in mid-market
  </Notes>
</Slide>
```

**Files to modify:** `planner_schema.py`, `state.py`, `context_builder.py`, `prompts/generator/system.j2`

---

### Tier 2: Medium Impact, More Effort

#### 2.1 Pre-Generation Questionnaire

**What GenOffice does:** `ask_clarification` tool presents 2-4 trade-off questions before planning:
- Who's the audience? (Board / C-suite / All-hands / External)
- How data-heavy? (High-level story / Balanced / Deep-dive)
- Preferred style? (Clean minimal / Bold colorful / Dark professional)
- What's the focus? (Overview / One metric deep-dive / Comparison)

These answers are injected into the planner prompt as constraints.

**Why it matters:** A "quarterly report" for a board of directors is radically different from one for an engineering all-hands. Without knowing the audience, the planner guesses.

**Implementation plan:**

Create a new `questionnaire` node that runs before the planner when `interactive=True`:

```python
def questionnaire_node(state: PresentationState) -> dict[str, Any]:
    """Generate and present clarifying questions based on the prompt."""
    # LLM generates 2-3 relevant questions based on raw_request
    # In interactive mode: present to user, collect answers
    # In API mode: use defaults or accept answers in request body
    return {"audience_context": answers}
```

Add to state:
```python
audience_context: dict[str, str] | None  # audience, tone, focus, style
```

Graph topology change: `START → questionnaire → planner → ...` (when interactive).

**Files to modify:** New `agents/questionnaire.py`, `state.py`, `graph.py`, new prompt templates

---

#### 2.2 Data Source Provenance

**What GenOffice does:** Tags every data value as `user | document | search | sample`. The UI shows a badge next to sample data ("AI-generated, verify before presenting"). Refuses to present fabricated numbers as real.

**Why it matters:** When the planner generates sample KPI values ("$42.8M ARR"), downstream consumers (the user, the audience) need to know these aren't real. Without provenance, fabricated data can be mistaken for actual metrics.

**Implementation plan:**

Add provenance tracking to `content_data`:
```python
# In content_data, wrap values with source tags:
{
    "kpi_values": [
        {"value": "$42.8M", "source": "user"},
        {"value": "114%", "source": "derived"},
        {"value": "72.1%", "source": "sample"}
    ]
}
```

The generator can optionally add a visual indicator for sample data (e.g., asterisk, lighter color). The evaluator manifest records provenance stats.

**Files to modify:** `planner_schema.py`, `prompts/planner/system.j2`, `context_builder.py`, `evaluator.py`

---

#### 2.3 Dedicated Style Skill

**What GenOffice does:** A separate LLM call (`generateStyleSkill`) produces a complete visual style guide before planning:
- Color palette with semantic roles (primary, accent, success, warning)
- Font pairing (heading + body)
- Layout variants per page type
- Spacing and sizing rules

This makes visual style a first-class deliverable rather than a side-product of theme selection.

**Why it matters:** Our current approach picks a theme name ("corporate-slate") and looks up its palette. This works for predefined themes but can't handle "make it look like Airbnb's brand" or "use our company colors #1E3A5F and #FF6B35."

**Implementation plan:**

Create a `style_resolver` node that runs after the planner:
```python
def style_resolver_node(state: PresentationState) -> dict[str, Any]:
    """Resolve visual style — from theme name, custom colors, or LLM generation."""
    # Path 1: theme_name provided → look up palette (current behavior)
    # Path 2: custom colors provided → build palette from them
    # Path 3: no theme → LLM generates style from prompt context
    return {"resolved_theme": style_dict}
```

This extracts style resolution from `context_builder` into its own node, making it independently triggerable.

**Files to modify:** New `agents/style_resolver.py`, `graph.py`, `state.py`, prompt templates

---

#### 2.4 Layout Audit (Post-Generation)

**What GenOffice does:** After generation, runs a mechanical check:
- Are any elements overlapping?
- Is text likely to overflow its container?
- Are elements outside the 1280×720 bounds?
- Are font sizes below minimum readable threshold?

**Why it matters:** The LLM often generates elements that technically compile but look broken — overlapping text, charts cut off at edges, text overflowing containers.

**Implementation plan:**

Add a `layout_audit` function in the validator or as a separate post-compile check:
```python
def audit_layout(xml: str) -> list[dict]:
    """Parse XML and check spatial constraints."""
    # Extract all elements with x, y, w, h attributes
    # Check: no element exceeds 1280×720 bounds
    # Check: no two sibling elements overlap
    # Check: text content fits in container (heuristic: chars * avg_char_width < container_width)
    return issues
```

This runs after the compiler succeeds but before the critic. Issues feed into the critic's assessment.

**Files to modify:** New function in `compiler/` or `agents/validator.py`, `prompts/critic/system.j2`

---

### Tier 3: Nice-to-Have / Future

#### 3.1 Style Templates (Save/Load Design Systems)
Save a resolved style as a reusable template. Useful for recurring deck types ("monthly board report uses the executive template").

#### 3.2 Image Integration
Auto-search for relevant images per slide using planned keywords. Requires an image search API (Unsplash, Pexels, Bing Images). Images are placed in designated regions of the layout.

#### 3.3 Real-Time Progress Events
For a web UI, emit Server-Sent Events during generation:
```
event: planning
event: generating_slide (slide: 1, total: 5)
event: validating_slide (slide: 1)
event: slide_complete (slide: 1)
event: assembling_deck
event: done (pptx_path: "...")
```

#### 3.4 SmartArt Rendering
Upgrade `flow`, `tree`, `matrix`, `pyramid` components to use SmartArt-style rendering with proper connectors and visual hierarchy, rather than manual shape placement.

#### 3.5 Single-Slide Regeneration
Regenerate one slide in place without regenerating the entire deck. Requires the editing architecture described in `EDITING_ARCHITECTURE.md`.

---

## Implementation Order

```
Phase 7.1: Core Hook + Slide Type          ← schema + prompt changes
Phase 7.2: Speaker Notes                   ← schema + generator prompt
Phase 7.3: Layout Variety Enforcement       ← post-planner validation
Phase 7.4: Questionnaire (interactive)      ← new node + graph wiring
Phase 7.5: Data Provenance                  ← content_data structure change
Phase 7.6: Style Resolver                   ← extract from context_builder
Phase 7.7: Layout Audit                     ← post-compile mechanical check
Phase 7.8: API Layer + Progress Events      ← FastAPI + SSE
```

Each phase is independently shippable. Phases 7.1-7.3 are prompt/schema changes with no new graph nodes. Phases 7.4-7.7 add new nodes but don't break existing flow. Phase 7.8 is the web interface.

---

## What We Intentionally Skip from GenOffice

| GenOffice Feature | Why We Skip It |
|---|---|
| `execute_slide_script` DSL | We use POM XML declaratively — no need for imperative `setBox/moveBy` commands |
| `verifyResponse` guard | Our pipeline is deterministic (graph nodes, not free-form tool calls) — no claimed-action drift |
| Cloud vs local generation paths | We run everything locally via subprocess |
| Batched recursion for large decks | LangGraph's slide_router loop handles this natively |
| Multi-layer JSON fallback parser | `with_structured_output` guarantees valid JSON — no parsing issues |
