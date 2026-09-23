# Roadmap: measured quality, deterministic routing, derived components

Written 2026-09-23 at the end of the design-hint session. Execute in a NEW session, one phase at a time.
Read first: `AGENTS.md`, `docs/design-hint-architecture.md`, `.cursor/rules/00-working-approach.mdc` (state assumptions, surgical changes, confirm plan before coding).

**Kick-off prompt for a new session:**
> Read AGENTS.md and docs/roadmap-derived-components.md. We are starting Phase <N>. Summarise the phase, list the decisions marked "DECIDE" for it and ask me before coding. Record a test baseline first.

---

## Why this roadmap exists

The slide component planner + generator work, but the design is not production-grade yet:

1. **Routing is an LLM reading a prose table.** Data *shape* (entities × metrics, time series, item count) is computable from `content_data`, yet the planner infers it from rules like "Entity + single metric (3+ entities) → chart". Gaps and contradictions slip through untested — e.g. 2 entities × 1 metric has no rule, lands in a thin 2-row table, and the planner then invented "platform logos as row icons" (the HStack-in-`<Td>` bug).
2. **The planner's vocabulary is POM node families** (`table`, `kpi_row`, `chart`), but slides are made of **cards** (KPI tile with icon, table card with header icon, icon+text points). Cards exist only as prose recipes in the generator prompt (`knowledge/core/recipes.yaml`), invisible to the planner.
3. **The generator hand-writes every low-level node.** Every real failure so far came from the LLM writing fiddly structure code could emit exactly: KPI tiles h=320 with clipped deltas, band heights summing to 1000 in a 720 slide, HStack in `<Td>`, Icon in `<Li>`, bad icon names, `line.width="0"`. Each fix added prompt text; the generator system prompt now sits at its budget (7.7k / 8.8k / 11.8k vs 8k / 9k / 12k).
4. **No quality measurement.** Changes are judged slide-by-slide, so the design has oscillated (free generation → constraints → archetypes). Nobody can say whether a change helped overall.

## Target architecture

```
content_data ──(code)──► data shape ──(code, routing.yaml)──► candidate cards
                                                                   │
            narrative + visual_emphasis ──(LLM chooses among candidates only)
                                                                   ▼
   slide = VStack/HStack composition (LLM, free)  +  derived cards (expanded by code)
                                                                   ▼
                                   core POM XML (always valid) ──► compiler
```

Three layers (the user's principle: **core nodes are fixed; derived components are composed around them**):

| Layer | Owner | Examples |
|---|---|---|
| 1 Core POM nodes | POM (`llm.md` is the reference) | Table/Td, Ul/Li, Text, Chart, Icon, Shape, VStack/HStack |
| 2 Derived nodes (macros) | us — data spec + code expander | `<KpiTile>`, `<TableCard>`, `<IconList>`, `<ChartCard>`, `<CalloutCard>` |
| 3 Slide composition | the generator LLM | bands, splits, which card where, proportions, treatments, copy |

The LLM keeps creative control of **composition** (locked decisions 2026-09-03 / 09-10: component-based, free composition, no rigid scaffold) but no longer writes the fiddly inside of cards.

Already in place and reused: `hint-capabilities.yaml` (treatments per kind → per derived node), `content_model.py` + `icons.py` (safety net), `blueprint_selector.py` + archetypes (slide-level layouts), `recipes.yaml` (becomes expansion templates), `render_check.py` + `tests/cases/*.yaml` (48 cases) + `src/runner.py` (harness).

---

## Phase 0 — Quality baseline (prerequisite for everything else)

**Goal:** a repeatable, numeric picture of pipeline quality so every later phase is accepted or rejected on data.
**Needs:** `OPENAI_API_KEY` (other device), LibreOffice for renders. Cost: one pass over the chosen cases (see `models.yaml`; mostly gpt-4.1).

**Build** `scripts/eval_run.py` (reuse `src.graph.run` like `src/runner.py` does; do not modify runner):
- Input: case names (default: all 48 in `tests/cases/`), `--label <name>`.
- Per case/slide collect from the final state:
  - `first_pass_ok` — compiled with `retry_count == 0`
  - `retries`, `max_tier`, `passed`
  - auto-fix counts by code from `normalize_result.issues`: `TEXT_CONTAINER_FLATTENED`, `UNKNOWN_ICON_REMOVED`, `ICON_NAME_NORMALIZED`, `ZERO_STROKE_REMOVED`, `FONT_FLOOR`, …
  - blocking codes seen during retries (`INVALID_CHILD`, `UNKNOWN_ATTR`, compile diagnostic types) — from `generation_history`
  - `layout_issues` counts by severity/code (`BAND_HEIGHT_SUM`, `FONT_TOO_SMALL`, …)
  - tokens in/out, cost, elapsed
  - planner output per slide: component kinds + design_hints (to audit routing and hint quality)
  - PNG render per slide (LibreOffice `--convert-to png`, as in `.cursor/rules/offline-render-loop.mdc`)
- Output: `output/eval/<label>-<timestamp>/results.json`, `summary.md` (per-case table + totals), `renders/`.
- `scripts/eval_compare.py A B` → markdown diff of totals and per-case regressions.

**Acceptance:** baseline run committed as `docs/eval/baseline-<date>.md` (summary only, no binaries). Human review of ~10 renders noting the top 3 visual failure types.
**DECIDE:** which cases are the acceptance gate (suggest: all `eval-*`, `maximal-density`, `single-table`, `kpi-row`, `chart-and-table`, `mixed-executive-slide`, 3 `deck-*`) vs the full 48 for milestone runs.

---

## Phase 1 — Deterministic data-shape routing + planner prompt fixes

**Goal:** component choice follows the data shape by testable rules; the LLM only chooses between valid candidates.

### 1.1 Planner prompt fixes (small, independent — do first)
In `src/prompts/slide_component_planner/system.j2`:
- Worked Example 2 (chart) hint asks for "a horizontal reference line at 0.40x" — POM charts cannot draw one and it is not in the chart treatments. Replace with "accent color for the Bengaluru bar, muted color for the rest; accent border on the chart card".
- Contradiction: line 1 says design_hint is "optional", line 148 "mandatory"; line 9 demands "distinctive rendering" without the treatment scope; worked-example title/narrative components have no hint. Make one rule: every component gets a hint from its kind's treatments (`hint-capabilities.yaml`); add hints to example components.
- Add Worked Example 4: two platforms × one metric (e.g. Flipkart ROAS 0.34x, Zomato 0.32x) showing the Phase 1.2 routing outcome and a scoped hint.
- Test: every design_hint in the worked examples uses only its kind's treatments (lexical check against a per-kind forbidden-word list: `icon|logo|reference line|arrow` for table/chart, etc.).

### 1.2 Shape classifier + routing rules
- `src/agents/data_shape.py`: `shape_of(kind, content_data) -> DataShape(entities, metrics, points, series, items, has_time_axis, max_text_len)` — pure, per content_data schema (table_rows/columns, chart_labels/values/series, kpi_*, bullets, *_steps/items/levels).
- `src/knowledge/core/routing.yaml`: ordered rules `shape predicate → candidate kinds`, e.g.
  - entities == 2 and metrics == 1 → `[kpi_row, table]`
  - entities >= 3 and metrics == 1 → `[chart, table]`
  - entities >= 2 and metrics >= 2 → `[table]`
  - time axis and points >= 3 → `[chart]`; points < 3 → `[kpi_row]`
  - guard: if the brief/visual_emphasis explicitly asks for a table → `table` stays (user rule: "if a table is asked, keep the table").
- Unit tests: table-driven, one row per rule + the guard + every `eval-*` case's expected routing.

### 1.3 Enforce candidates — **DECIDE (recommend 1A first):**
- **1A — post-plan check + deterministic remap (no extra LLM call):** after `plan_single_slide`, classify each component; if its kind is not a candidate, remap to the first candidate and transform content_data (e.g. `table_rows [[Flipkart,0.34x],[Zomato,0.32x]]` → `kpi_labels/kpi_values`). Log `ROUTING_REMAP`. Cheap, testable; limited to remaps we implement.
- **1B — two-step planning:** LLM extracts typed facts → code proposes candidates → LLM chooses (schema enum per slide). Most principled; +1 LLM call per slide (latency/cost).

**Acceptance:** eval gate shows no regression in first-pass/audit; routing of `eval-*` cases matches expectations; 2×1 cases produce tiles unless a table was asked for.

---

## Phase 2 — Derived nodes, first three: `KpiTile`, `TableCard`, `IconList`

Chosen because they caused the real failures (KPI h=320/clipped delta, HStack/Icon in `<Td>`, Icon in `<Li>`).

**Spec** `src/knowledge/core/derived-nodes.yaml` — per node: attributes (type, required, enum), allowed children, treatments it accepts (maps `hint-capabilities` treatments to attributes, e.g. `tone=negative`, `accent=left`, `icon=<name>`), sizing rule, expansion template path.

Sketch (final attribute names decided in-phase):
```xml
<KpiTile icon="shopping-bag" label="Flipkart" value="0.34" unit="x ROAS" delta="-0.06" note="Below 0.40x break-even" tone="negative" />
<TableCard title="ROAS by platform" icon="store" accent="left" highlightRow="2" highlightTone="negative">
  <Table>…core table, text-only cells…</Table>
</TableCard>
<IconList items="zap|Instant delivery;clock|24/7 availability" tone="accent" />
```

**Expander** `src/compiler/derived_nodes.py`, called FIRST in `normalize_xml` (before flatten / icons / content model), so everything downstream sees core POM only:
- locate macro elements by regex (keep the rest of the XML byte-identical — `deck_nodes.py` parses the `<!-- archetype -->` comment), parse each with ElementTree, validate attributes (unknown → `DERIVED_ATTR_UNKNOWN` auto-dropped; missing required → blocking `DERIVED_ATTR_MISSING`), render the template, splice back.
- heights computed in code (e.g. TableCard: title + header + rows × `defaultRowHeight` + padding; KpiTile auto-size per house-style); icons validated via `icons.py`.
- **DECIDE:** templates as Jinja files (`src/knowledge/derived/*.xml.j2`, reviewable data) vs Python builders (easier sizing logic). Recommend Jinja + small Python sizing helpers.

**Prompts:** generator gets a `DERIVED NODES` section listing only the nodes relevant to this slide's kinds (like `visual_intent_techniques`); remove the corresponding recipes (`kpi_row`, `table_card`, `icon_bullet_list`) → measure token delta. `hint-capabilities.yaml` techniques for those kinds become derived-node attributes.

**Tests (LLM-free):** every derived node × variant expands to XML that compiles, is audit-clean and content-model valid (extend `render_check` fixtures); golden snapshot of expansions; normalizer idempotent on expanded output.

**Acceptance:** eval gate: first-pass compile ≥ baseline, audit issues on KPI/table/list slides → ~0, prompt tokens ↓. Visual review of renders equal or better.
**Risk:** LLM writes raw POM instead of macros → still valid (safety net), just not improved; mitigate by removing the raw recipes and using macros in examples.
**DECIDE:** does the slide editor (`slide_edit_service.py`, `prompts/slide_editor`) work at macro level (store pre-expansion XML) or on expanded core XML?

---

## Phase 3 — Remaining derived nodes + prompt reduction

`ChartCard`, `CalloutCard`, `Badge`, `SectionHeader` (from `platform_header`), `DarkPanel` (from `dark_callout_panel`), `StatPair`. Migrate remaining recipes; update golden references and blueprints' `reference_xml` to macros; repairer/slide-editor prompts learn the macros. Target: generator system prompt −20% vs Phase 0.
**Acceptance:** eval gate ≥ Phase 2; full 48-case milestone run.

## Phase 4 — Visual quality loop

Re-enable `critic_mode="auto"` (visual critic → repair; user-deferred on 2026-09-10) and measure against the baseline. Optionally add a plan_reviewer check for hints that contradict weight or reference data not in key_messages (LLM-only judgement).
**Acceptance:** critic loop improves the human-reviewed render score without raising retries/cost beyond an agreed cap (**DECIDE** the cap).

---

## Known issues to fold in (not phases)

- Two stale routing tests in `tests/unit/test_graph.py` (`*_budget_exhausted*`: expect `evaluator`/`slide_router`, code routes to `visual_repairer`) + `test_critic_medium_only_passes` + `test_font_at_minimum_ok` fail before any of this work — decide whether tests or code are wrong.
- `graphify-out/cache/` is tracked in git and breaks Windows checkouts without `core.longpaths` — consider `.gitignore`.
- Generator system prompt is at budget: any new guidance must be per-slide/per-component (see `docs/design-hint-architecture.md` "Prompt budget").

## Done before this roadmap (2026-09-23)

- Design-hint scoping, content-model nesting, exact icon names — `docs/design-hint-architecture.md`.
- `llm.md` review: kept as audit source, not a prompt (full-reference prompting lost to selective context on 2026-09-02; 12.4k tokens; teaches <14pt fonts and a non-house root). Found and fixed: `shape.yaml` taught `line.width="0"` (compile failure — POM rejects every zero stroke; normalizer now strips `line/outline/border*` zero-width groups, `ZERO_STROKE_REMOVED`); house-style/design-language forbade `borderLeft` on rounded cards — render shows only `borderTop` wraps corners. `tests/unit/test_upstream_reference.py` compiles every `llm.md` example after normalize.
