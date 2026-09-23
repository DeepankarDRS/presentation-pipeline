# Roadmap: measured quality, correct sizing, deterministic routing, derived components

Written 2026-09-23; merged with `docs/layout-sizing-plan.md` the same day. Execute in NEW sessions, one phase at a time.
Read first: `AGENTS.md`, `docs/design-hint-architecture.md`, `docs/layout-sizing-plan.md` (verified POM sizing facts F1–F10 + step detail), `.cursor/rules/00-working-approach.mdc` (state assumptions, surgical changes, confirm plan before coding).

**Kick-off prompt for a new session:**
> Read AGENTS.md and docs/roadmap-derived-components.md. We are starting Phase <N>. Summarise the phase, list the decisions marked DECIDE for it and ask me before coding. Record a test baseline first.

---

## Why this roadmap exists

The pipeline works, but it is not production-grade yet:

1. **Sizing is LLM pixel arithmetic, and the grammar teaches a POM misconception.** `house-style.yaml` calls `w="max"` the "DEFAULT for anything that should stretch" (136 occurrences across recipes, blueprints, golden examples, house style). In a VStack, `w="max"` grows the **height** and overrides `h` — re-verified 2026-09-23: a KPI row with `h="150" w="max"` rendered **495 px** tall. That is the main source of "half-empty / bloated card" slides that `fit-grow.js` repairs after the fact.
2. **Routing is an LLM reading a prose table.** Data shape (entities × metrics, time series, item count) is computable from `content_data`, yet the planner infers it. Gaps slip through untested — 2 entities × 1 metric has no rule → thin table → the planner invented "platform logos as row icons" (the HStack-in-`<Td>` bug).
3. **The planner's vocabulary is POM node families, but slides are made of cards.** Cards exist only as prose recipes in the generator prompt, invisible to the planner.
4. **The generator hand-writes every low-level node.** Every real failure came from structure code could emit exactly (KPI h=320, band sums of 1000 px, HStack in `<Td>`, Icon in `<Li>`, bad icon names, `line.width="0"`). Each fix added prompt text; the generator system prompt sits at budget (7.7k / 8.8k / 11.8k vs 8k / 9k / 12k).
5. **No quality measurement,** so the design has oscillated (free generation → constraints → archetypes).

## Design principles (read before every phase)

- **Core nodes are fixed.** POM's primitives keep their syntax; we never patch `node_modules` or bend a core node.
- **POM's own rule, adopted:** the POM author ships a node only when flexbox composition cannot express it (Timeline, Flow, Tree, Matrix, ProcessArrow, Pyramid need special geometry; a KPI card does not — so POM has no KpiTile, the README tells users to compose). Our derived nodes follow the same rule one level up: **add a derived node only for a composition that repeats AND fails in eval data.** Target ≤ 10 derived nodes.
- **Let POM allocate, compute only what POM can't** (from the sizing plan): `grow` / `h="max"` / `minH` instead of pixel budgets; code only for table column/row sizing and diagram node sizes.
- **Escape hatches stay open:** the generator may always compose raw core nodes; derived nodes expand to plain POM, so the layer can be removed at any time (expand once, delete the macro).
- **Every phase is accepted on Phase 0 numbers,** not on single slides.

## Target architecture

```
content_data ──(code)──► data shape ──(code, routing.yaml)──► candidate cards
                                                                   │
            narrative + visual_emphasis ──(LLM chooses among candidates only)
                                                                   ▼
   slide = VStack/HStack composition with grow/minH (LLM, free)
         + derived cards (expanded by code into core POM)
                                                                   ▼
          normalizer + content model + fit-grow (code) ──► compiler ──► .pptx
```

| Layer | Owner | Examples |
|---|---|---|
| 1 Core POM nodes | POM (`llm.md`) | Table/Td, Ul/Li, Text, Chart, Icon, Shape, VStack/HStack |
| 2 Derived nodes | us — spec + code expander | `<KpiTile>`, `<TableCard>`, `<IconList>`, `<ChartCard>`, `<CalloutCard>` |
| 3 Slide composition | generator LLM | bands, weights (`grow`), which card where, treatments, copy |

Already in place and reused: `hint-capabilities.yaml`, `content_model.py`, `icons.py`, `blueprint_selector.py` + archetypes, `recipes.yaml` (→ expansion templates), `fit-grow.js`, `render_check.py`, `tests/cases/*.yaml` (48) + `src/runner.py`.

## Phase order at a glance

| # | Phase | Source | Needs API key | Depends on |
|---|---|---|---|---|
| 0 | Quality baseline | roadmap | yes | — |
| 1 | Sizing grammar (grow/minH, no pixel budgets) | sizing plan Step 1 | for acceptance | 0 |
| 2 | Deterministic routing + planner prompt fixes | roadmap | for acceptance | 0 (independent of 1; can swap) |
| 3 | Real font metrics | sizing plan Step 2 | no (visual check) | 1 |
| 4 | Derived nodes: KpiTile, TableCard, IconList | roadmap | for acceptance | 1, 2 |
| 5 | Remaining derived nodes + computed table/diagram sizing | roadmap + sizing plan Steps 3–4 | for acceptance | 4 |
| 6 | Measured critic loop | roadmap + sizing plan Step 5 | yes | 5 |

---

## Phase 0 — Quality baseline (prerequisite)

**Goal:** a repeatable numeric picture of quality so every later phase is accepted or rejected on data.
**Needs:** `OPENAI_API_KEY` (other device), LibreOffice for renders.

**Build** `scripts/eval_run.py` (reuse `src.graph.run` like `src/runner.py`; do not modify runner):
- Input: case names (default all 48 in `tests/cases/`), `--label`.
- Per case/slide from the final state: `first_pass_ok` (compiled with `retry_count == 0`), `retries`, `max_tier`, `passed`; auto-fix counts by code from `normalize_result.issues` (`TEXT_CONTAINER_FLATTENED`, `UNKNOWN_ICON_REMOVED`, `ICON_NAME_NORMALIZED`, `ZERO_STROKE_REMOVED`, `FONT_FLOOR`, …); blocking codes seen during retries (from `generation_history`); `layout_issues` by code; `compile-result.json.fitGrow` changes; tokens/cost/time; planner kinds + design_hints per slide; PNG render per slide.
- **Fill ratio per card** (content height ÷ box height, from the pptx shape frames as in the verification above) — the objective "dead space" metric the sizing work is judged on.
- Output: `output/eval/<label>-<ts>/results.json`, `summary.md`, `renders/`; `scripts/eval_compare.py A B` for diffs.
- Also run the sizing plan's LLM-free regression (§7 of `docs/layout-sizing-plan.md`: fit-grow + golden fixtures with and without `POM_FIT_GROW`).

**Acceptance:** baseline committed as `docs/eval/baseline-<date>.md` (summary only); human review of ~10 renders listing the top 3 visual failure types.

**Quality target = `tests/fixtures/golden/gj-h1-deck/`.** Add an eval case that regenerates those 14 slides from the same source data and scores them against the golden deck: per-slide card-pattern match, fill ratio, audit issues, side-by-side renders. Facts measured 2026-09-23 that make this the right target:
- 63 of its 70 cards are five patterns (KPI tile 31, table card 13, callout 8, dark panel 6, chart card 5); 12 of 14 slides share one header + badge pattern; it uses 1 icon in total — polish comes from density, semantic colour and read-out panels, not decoration.
- It is sized by hand (95 `w="max"`, tuned band heights 78+340, 100+282, …). Compiled by today's pipeline, slide 05 already shows the F1/F5 defects (KPI tiles ≈2× their declared 78 px, tables not filling their cards, stretched rows with top-aligned text) — Phase 1/5 improve even the golden reference.
- A real generated slide (`llm_test/f7cb357c1472.pptx`, 2026-09-22) shows the gap: a 1-row table (1 entity × 2 metrics) in a tall card, a card holding one bullet, a dead band under the header → routing (Phase 2), sizing (Phase 1), thin content (planner/data, not covered by this roadmap).
**DECIDE:** acceptance-gate case subset (suggest: all `eval-*`, `maximal-density`, `single-table`, `kpi-row`, `chart-and-table`, `mixed-executive-slide`, 3 `deck-*`) vs full 48 for milestones.

**Status: built 2026-09-23 (branch `phase-0-eval`), awaiting eval.**
Decisions (2026-09-23, user):
- Gate = the user's 3 deck prompts (6 / 8 / 6 slides; case files pending) + `eval-*` (3), `maximal-density`, `single-table`, `kpi-row`, `chart-and-table`, `mixed-executive-slide`, `gj-h1-regen` (`GATE_CASES` in `scripts/eval_run.py`); full 48 at milestones. Runs per case via `--repeat N`.
- gj-h1 case derived from the golden XML (`scripts/make_gj_h1_case.py` → `tests/cases/gj-h1-regen.yaml`, content only, no layout); user confirmed its data may travel in eval bundles.
- Renders: test PC exports PowerPoint COM PNGs into the bundle; build PC renders every slide with LibreOffice on import (same renderer for every label). Committed summaries live in `docs/eval/<label>/` (supersedes `baseline-<date>.md` above).

Built: `scripts/eval_run.py` (streams the unchanged graph — deck state resets per slide, so per-slide numbers come from each validator step), `eval_metrics.py`, `eval_compare.py`, `eval_import.py`, `tests/unit/test_eval.py` (mocked stream, real graph with mocked LLM, real compiles).
Fill ratio = card content span ÷ (card height − 2·padding), padding ≤ 24 px; table rows count only their text height (≥ the 32 px default row), so centred content in a bloated card (F1) and stretched rows (F5) both read as dead space — checked against LibreOffice renders.
LLM-free numbers (`--fixtures`, fit-grow off → on): gj-h1 golden mean fill 0.761 → 0.866, low-fill cards 35.1% → 14.9%; editorial golden 0.826 → 0.875; fit_grow fixtures 0.715 → 0.801. Target for the regenerated deck: `docs/eval/golden-gj-h1/` (74 cards: KPI tile 36, table 13, text 13, dark panel 6, chart 6).

---

## Phase 1 — Sizing grammar: let POM allocate (sizing plan Step 1)

**Goal:** remove pixel arithmetic from the generator; express weights and minimums with POM's `grow` / `h="max"` / `minH` (facts F1–F4, detail in `docs/layout-sizing-plan.md` §4 Step 1).

Rules to teach: width in a VStack comes from stretch (no `w="max"` on VStack children; `w="max"` only in HStack) · planner weight → `grow` (hero 3, peer 2, supporting 1, minor none) · Chart `h="max" minH="…"`, no pixel h · Table no `h`/`w`, its card no `grow` · Flow/Tree/ProcessArrow `h="max" minH` · Timeline/Pyramid sized to the diagram, no `grow` · Matrix may fill.

Files: `house-style.yaml` (remove `height_budget`, `worked_example`, rigid-node pixel rules, `'w="max"'` default; add weight → grow table), `recipes.yaml`, `system.j2`/`user.j2` sizing lines, `layout_audit.py` `_check_missing_dims` (Table needs no dims; `h="max"` needs `minH`), `test_layout_audit.py`, new fixtures `tests/fixtures/layout_sizing/`.
Also: `hint-capabilities.yaml` techniques and the Phase 2 derived-node templates must use this grammar.

**DECIDE:** `blueprints.yaml` (57 `w="max"`) and `golden-examples.yaml` (33) — rewrite to the new grammar, or keep as old-style compatibility references and stop injecting them? (Mixed signals in one prompt would undo the phase.)
**Acceptance:** fill ratio and dead-space findings improve vs baseline; first-pass compile not worse; generator prompt shrinks (pixel arithmetic removed).

---

## Phase 2 — Deterministic routing + planner prompt fixes

### 2.1 Planner prompt fixes (small, do first)
In `src/prompts/slide_component_planner/system.j2`:
- Worked Example 2 hint asks for "a horizontal reference line at 0.40x" — POM charts cannot draw one; not a chart treatment. Replace with "accent color for the Bengaluru bar, muted for the rest; accent border on the chart card".
- Contradiction: line 1 "optional design_hint", line 148 "mandatory", line 9 "distinctive rendering" without scope; example title/narrative components lack hints. One rule: every component gets a hint from its kind's treatments.
- Worked Example 4: two platforms × one metric (Flipkart ROAS 0.34x, Zomato 0.32x) showing the 2.2 routing outcome and a scoped hint.
- Test: worked-example hints only use their kind's treatments (lexical forbidden-word check per kind).

### 2.2 Shape classifier + routing rules
- `src/agents/data_shape.py`: `shape_of(kind, content_data) -> DataShape(entities, metrics, points, series, items, has_time_axis, max_text_len)` — pure.
- `src/knowledge/core/routing.yaml`: ordered `shape predicate → candidate kinds`, e.g. 2 entities × 1 metric → `[kpi_row, table]`; ≥3 entities × 1 metric → `[chart, table]`; ≥2 entities × ≥2 metrics → `[table]`; time axis ≥3 points → `[chart]`; <3 points → `[kpi_row]`; **guard: brief explicitly asks for a table → table** (user rule).
- Table-driven unit tests, including every `eval-*` case.

### 2.3 Enforce candidates — **DECIDE (recommend 2A first)**
- **2A post-plan check + deterministic remap** (no extra LLM call): non-candidate kind → first candidate, content_data transformed (`table_rows` → `kpi_labels/kpi_values`), logged `ROUTING_REMAP`.
- **2B two-step planning**: extract typed facts → code proposes → LLM chooses (enum per slide). +1 LLM call/slide.

**Acceptance:** `eval-*` routing matches expectations; no gate regression; 2×1 → tiles unless a table was asked for.

---

## Phase 3 — Real font metrics (sizing plan Step 2)

Every pptx declares "Noto Sans JP"; Office machines substitute it, so wrapping differs from POM's measurement (F8). Register metric-identical OFL fonts via `buildPptx(..., { fonts })` (F9: Carlito = Calibri, Liberation Sans = Arial), pass the same list to fit-grow, and have the normalizer set `fontFamily` on Text/Ul/Ol/Shape/Td/Timeline without one.
**DECIDE:** the deck font (Calibri recommended; visible change — confirm with the user). Flow/Pyramid labels stay Noto Sans JP (hard-coded in POM).
**Acceptance:** wrapped lines in PowerPoint match POM's measurement on the fit-grow fixtures; fit-grow's compensation margins re-tuned.

---

## Phase 4 — Derived nodes: `KpiTile`, `TableCard`, `IconList`

Chosen because they caused the real failures. Written in the Phase 1 grammar from day one.

**Spec** `src/knowledge/core/derived-nodes.yaml` — per node: attributes (type, required, enum), allowed children, accepted treatments (map `hint-capabilities` treatments to attributes: `tone`, `accent`, `icon`), expansion template.
```xml
<KpiTile icon="shopping-bag" label="Flipkart" value="0.34" unit="x ROAS" note="Below 0.40x break-even" tone="negative" />
<TableCard title="ROAS by platform" icon="store" accent="left" highlightRow="2" highlightTone="negative">
  <Table>…core table, text-only cells…</Table>
</TableCard>
<IconList items="zap|Instant delivery;clock|24/7 availability" tone="accent" />
```

**Expander** `src/compiler/derived_nodes.py`, called FIRST in `normalize_xml` so everything downstream sees core POM: locate macros by regex (keep the rest byte-identical — `deck_nodes.py` reads the archetype comment), parse each with ElementTree, validate attributes (unknown → dropped + `DERIVED_ATTR_UNKNOWN`; missing required → blocking `DERIVED_ATTR_MISSING`), render template, splice back. **No pixel heights**: sizing comes from the Phase 1 grammar (Table auto-sizes to rows — F4; cards take `grow` from weight). Icons validated by `icons.py`.
**DECIDE:** Jinja templates (`src/knowledge/derived/*.xml.j2`, reviewable data — recommended) vs Python builders.
**DECIDE:** slide editor (`slide_edit_service.py`) works on macro-level XML (store pre-expansion) or expanded core XML.

Prompts: generator `DERIVED NODES` section only for this slide's kinds; remove the replaced recipes (`kpi_row`, `table_card`, `icon_bullet_list`); treatments for those kinds become attributes.
Tests (LLM-free): every derived node × variant expands to XML that compiles, is audit-clean and content-model valid; golden expansion snapshots; normalizer idempotent.
**Acceptance:** gate: first-pass ≥ Phase 2, audit issues on KPI/table/list slides ≈ 0, fill ratio ≥ Phase 1, prompt tokens ↓.

---

## Phase 5 — Remaining derived nodes + computed sizing (sizing plan Steps 3–4)

- Derived: `ChartCard`, `CalloutCard`, `Badge`, `SectionHeader` (from `platform_header`), `DarkPanel`, `StatPair` — only those that pass the "repeats AND fails in eval" rule.
- `fit-grow.js`: table column widths from content (HTML-style auto layout) and row heights from wrapped lines (F5); Flow/Tree/ProcessArrow node sizes on the grown box (F6/F7); add the missing Tree fixture.
- Migrate golden references / blueprints per the Phase 1 decision; repairer and slide-editor prompts learn the derived nodes. Target generator system prompt −20% vs Phase 0.
**Acceptance:** full 48-case milestone run ≥ Phase 4 on every metric.

## Phase 6 — Measured critic loop (sizing plan Step 5)

Add per-card fill ratios to `compile-result.json.fitGrow` and pass them to the visual critic as data; re-enable `critic_mode="auto"` (deferred 2026-09-10) and measure. Optional plan_reviewer check for hints that contradict weight or data.
**DECIDE:** retry/cost cap for the critic loop.

---

## Long-term fit and scalability (why this does not box us in)

| Concern | Current approach | After roadmap |
|---|---|---|
| Adding a new visual pattern | more prompt text (budget already full) | one derived-node spec + template + tests; one prompt line, only on slides that use it |
| A class of error | fixed by prompt wording, recurs | fixed once in code/validator, regression-tested |
| Prompt size vs slide complexity | grows with every rule | grows with the slide's own kinds only |
| Sizing | LLM pixel arithmetic + post-hoc fit-grow | POM flexbox allocates; code computes only tables/diagrams |
| POM upgrade | knowledge drift found by users | `test_upstream_reference.py` + icon-list test + expander tests fail first |
| Visual variety | LLM free at every level | LLM free at composition level; card internals consistent by design |
| Measuring change | anecdotal | Phase 0 metrics on every change |
| Lock-in | — | low: derived nodes expand to plain POM; raw core composition always allowed |

Risks and mitigations:
- **Sameness / templated look** (the reason archetype-style constraints were removed on 2026-09-10): derived nodes cover card internals only; layout, weights, treatments and variants stay with the LLM; measure variety in Phase 0 renders.
- **Owning a small DSL**: cap ≈ 10 nodes, versioned spec, every node render-tested in CI; add nodes only on eval evidence.
- **LLM ignores derived nodes and writes raw POM**: still valid (safety net), just not improved; remove the raw recipes the node replaces.
- **Two-level debugging**: `normalize_result.issues` records every expansion; keep pre- and post-expansion XML in run outputs.
- **Font change is visible** (Phase 3): confirm with the user before shipping.

## Known issues to fold in (not phases)

- Pre-existing failing tests: two `test_graph.py` `*_budget_exhausted*` routing tests (expect `evaluator`/`slide_router`, code routes to `visual_repairer`), `test_critic_medium_only_passes`, `test_font_at_minimum_ok` — decide whether tests or code are wrong.
- `graphify-out/cache/` tracked in git breaks Windows checkouts without `core.longpaths` — consider `.gitignore`.

## Done before this roadmap (2026-09-23)

- Design-hint scoping, content-model nesting, exact icon names — `docs/design-hint-architecture.md`.
- `llm.md` review: audit source, not a prompt (full-reference prompting lost to selective context on 2026-09-02). Fixed: `shape.yaml` taught `line.width="0"` (POM rejects all zero strokes; normalizer strips them, `ZERO_STROKE_REMOVED`); accent-stripe rule narrowed to `borderTop` (render-verified). `tests/unit/test_upstream_reference.py` compiles every `llm.md` example.
- Sizing facts F1 and F4 of `docs/layout-sizing-plan.md` re-verified by frame measurement (KPI row h=150 + w=max in VStack → 495 px; Table with no h → 84 px = 32 + 52).
