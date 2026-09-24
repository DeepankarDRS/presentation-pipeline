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

**Status: built 2026-09-23 (branch `phase-0-eval`); baseline recorded 2026-09-24 (tag `eval-baseline`).**
Decisions (2026-09-23, user):
- Gate = the user's 3 deck prompts `gate-deck-cheffin-audit` (6 slides), `gate-deck-xtsy-qcomm` (8), `gate-deck-agency-takeover` (6) + `eval-*` (3), `maximal-density`, `single-table`, `kpi-row`, `chart-and-table`, `mixed-executive-slide`, `gj-h1-regen` (`GATE_CASES` in `scripts/eval_run.py`); all cases at milestones. **2 runs per case** (`--repeat` default). CHEFFIN prompt: pasted text stopped after slide 1 of an "18-slide structure" → target changed to 6, chat timestamp removed, agency name anonymised (user, 2026-09-23); the other two verbatim.
- gj-h1 case derived from the golden XML (`scripts/make_gj_h1_case.py` → `tests/cases/gj-h1-regen.yaml`, content only, no layout); user confirmed its data may travel in eval bundles.
- Renders: test PC exports PowerPoint COM PNGs into the bundle; build PC renders every slide with LibreOffice on import (same renderer for every label). Committed summaries live in `docs/eval/<label>/` (supersedes `baseline-<date>.md` above).

Built: `scripts/eval_run.py` (streams the unchanged graph — deck state resets per slide, so per-slide numbers come from each validator step), `eval_metrics.py`, `eval_compare.py`, `eval_import.py`, `tests/unit/test_eval.py` (mocked stream, real graph with mocked LLM, real compiles).
Fill ratio = card content span ÷ (card height − 2·padding), padding ≤ 24 px; table rows count only their text height (≥ the 32 px default row), so centred content in a bloated card (F1) and stretched rows (F5) both read as dead space — checked against LibreOffice renders.
LLM-free numbers (`--fixtures`, fit-grow off → on): gj-h1 golden mean fill 0.761 → 0.866, low-fill cards 35.1% → 14.9%; editorial golden 0.826 → 0.875; fit_grow fixtures 0.715 → 0.801. Target for the regenerated deck: `docs/eval/golden-gj-h1/` (74 cards: KPI tile 36, table 13, text 13, dark panel 6, chart 6).
First real run (2026-09-24, `gate-deck-agency-takeover` × 2, commit `380682e`, $1.08, not kept as baseline): harness works end to end (stream, per-slide tagging, PowerPoint renders, bundle). Findings: (1) both runs made **8 slides for a 6-slide brief** — `DeckSettings` defaults `deck_min_threshold` to 8 and `outline_planner` reads it before the state value, so the planner padded with "[Reserved for Additional Insights]" / "Appendix" filler; (2) **cramming** — 5 `kpi_row` components → 23 tiles, words split mid-word, invented "Budget lever" values, yet fill read 0.97; (3) dead space in table cards (fill 0.45–0.58) and a lone bullet list in a full-height card (0.31); (4) invented source/date lines ("Q2 2024", "Q2 FY25"); (5) first-pass 62.5%, mostly `PARSE_ERROR` (messages were not recorded); (6) bare `&` → `layout_audit` cannot parse → 3/16 slides never audited; (7) chart squashed to ~60 px with truncated labels. Harness fixes (2026-09-24): exact slide target via `test_case["slide_count"]` (1 for single-slide cases), `word_breaks` per slide (crushed text), first 3 blocking messages per slide, slide count vs target in the summary, `eval_import` merges bundles per label and re-measures pptx metrics. Re-run this case before it counts.
**Baseline recorded 2026-09-24 → `docs/eval/baseline/`** (commit `ea80267`, models.yaml `919e01fa` = outline_planner max_tokens 12000; the 14-slide outline truncated at 4000). DECIDE (user, 2026-09-24, cost): baseline = **`gj-h1-regen` × 1 run** only; other gate cases run when a phase needs them (routing `eval-*` for Phase 2). Run-to-run noise from the smoke run: fill ±0.04, so later phases need Δfill > 0.05 or first-pass Δ > 2 slides to count.
Baseline numbers (vs golden target): 14/14 slides; compiled 85.7% (slides 4 + 5, the two densest deep-dives, became "could not be generated" placeholders, yet the run reports `passed`); first-pass **50%** (golden 100%); mean fill 0.884 over the 12 compiled slides (golden 0.896); low-fill cards 13%; text overflows 3 (timeline labels off the slide); **invented numbers 15** (a whole chart series + one table); golden card-pattern match **0.38**; 46 cards vs 74 (KPI tiles 12 vs 36). $1.16, 6.6 min, 345k tokens in.
Visual review (build device, PowerPoint + LibreOffice renders) — top 3 failure types:
1. **Slides lost or retried on mechanical errors** (first-pass 50%): `shadow` + `shadow.*` on one node (7/14 slides; knowledge lists `shadow` as a bare attribute name while teaching only the dotted form), `<Table>` missing rows (non-text child in `<Td>`), `border.width="0 0 0 5"` (CSS shorthand), `<Text>` without text, table rows with the wrong cell count. All deterministic → normalizer fixes, no LLM (Phase 1 prep / "no regenerate for deterministic fixes").
2. **Space allocation**: timeline labels overflow the card and the slide while the top half is empty (slide 8); dead space under tables (0.49–0.69) and in chart cards; thin one-row tables (Phases 1, 5).
3. **Content fidelity and density**: invented chart data despite verbatim supplied numbers (numbers pass through outline → slide plan summaries), invented source/date lines; far fewer KPI tiles/cards than the golden deck → planner/routing (Phase 2) and derived nodes (Phase 4).
Also seen: KPI icons render as broken images in the PowerPoint export on the test PC but fine in LibreOffice (to verify by opening the .pptx in PowerPoint); highlight markup on title words; table text in a different font from the rest (F8, Phase 3).
Harness additions from this run: `text_overflows`, `invented_numbers` (numbers on a slide absent from the brief), both re-measured on import.
**Follow-up: deterministic normalizer fixes** — branch `fix/normalizer-deterministic`, built 2026-09-24. **Verified LLM-free by replay** (2026-09-24): all 23 saved attempts of the baseline run (`output/runs/gj-h1-regen-69af33`, emailed) re-normalized and compiled — every attempt compiles; first-pass would be **14/14 (was 7/14)**, retries 8 → 0, and slides 4 + 5 (placeholders in the baseline) compile on their first attempt: both render as dense, data-accurate deep-dives (0 invented numbers; remaining flaws are sizing — a table past its card edge, a squashed chart → Phase 1). No paid re-run: the next paid run (Phase 1) includes this fix, whose compile effect is already isolated here. Each baseline blocker was reproduced against POM 10.3.0 and is now fixed in `normalize_xml` without an LLM call: bare `shadow` next to `shadow.*` dropped (`ATTR_CONFLICT_FIXED`, 7/14 baseline slides), CSS `border.width="t r b l"` → per-side borders (`BORDER_SHORTHAND_EXPANDED`), empty `<Td>` → blank text — also produced by the existing flattener for icon-only cells, the real cause of `<Table>: Missing required attribute "rows"` (`EMPTY_CELL_FILLED`), empty `<Text>` / `<Li>` removed (`EMPTY_TEXT_REMOVED`, `EMPTY_ITEM_REMOVED`; empty `<Li>` fails as `<Ul>: Missing required attribute "items"`), rows with more cells than `<Col>`s padded with `<Col />` (`TABLE_COLS_PADDED`), bare `&` escaped (`AMPERSAND_ESCAPED`, restores `layout_audit` on those slides and lets the Td flattener parse them). Idempotent (deck assembler re-normalizes); all golden/fit-grow fixtures and the baseline's final slides still compile and trigger no new fix except `&`. Not changed: the knowledge that lists `shadow` as a bare attribute name (prompt change; the normalizer makes it harmless). `Thead`/`Tbody`/`Th` already block precisely as `INVALID_CHILD` and were not seen in the baseline.
gj-h1 golden reviewed against its renders (2026-09-23, user request): 10 of 11 tables had fixed `<Col width>` summing 90–346 px short of the card and 6–8 pt text. Now the label/number columns keep a width and the text columns have none (POM shares the rest equally), row heights fill the card, cell text 13–18 px; slide 08 lost three `w="max"` in its VStack (F1 height growth), slide 14's number column got `w="44"` (text was pushed to the right half), text cards on 02/09/12/14 got larger body text. Result (fit-grow on): mean fill 0.866 → 0.896, low-fill cards 14.9% → 8.1%, `COL_WIDTH_SUM` 11 → 0, `FONT_TOO_SMALL` 534 → 387; fit-grow off → on is now 0.824 → 0.896. Limits kept: `<Td>` has no padding/valign (text sits top-left, so single-line rows show space below); slide 09 card 1 title wraps in LibreOffice and touches the next label (F8 font metrics, Phase 3).

---

## Phase 1 — Sizing grammar: let POM allocate (sizing plan Step 1)

**Goal:** remove pixel arithmetic from the generator; express weights and minimums with POM's `grow` / `h="max"` / `minH` (facts F1–F4, detail in `docs/layout-sizing-plan.md` §4 Step 1).

Rules to teach: width in a VStack comes from stretch (no `w="max"` on VStack children; `w="max"` only in HStack) · planner weight → `grow` (hero 3, peer 2, supporting 1, minor none) · Chart `h="max" minH="…"`, no pixel h · Table no `h`/`w`, its card no `grow` · Flow/Tree/ProcessArrow `h="max" minH` · Timeline/Pyramid sized to the diagram, no `grow` · Matrix may fill.

Files: `house-style.yaml` (remove `height_budget`, `worked_example`, rigid-node pixel rules, `'w="max"'` default; add weight → grow table), `recipes.yaml`, `system.j2`/`user.j2` sizing lines, `layout_audit.py` `_check_missing_dims` (Table needs no dims; `h="max"` needs `minH`), `test_layout_audit.py`, new fixtures `tests/fixtures/layout_sizing/`.
Also: `hint-capabilities.yaml` techniques and the Phase 2 derived-node templates must use this grammar.

**DECIDE:** `blueprints.yaml` (57 `w="max"`) and `golden-examples.yaml` (33) — rewrite to the new grammar, or keep as old-style compatibility references and stop injecting them? (Mixed signals in one prompt would undo the phase.)
**Acceptance:** fill ratio and dead-space findings improve vs baseline; first-pass compile not worse; generator prompt shrinks (pixel arithmetic removed).

**Status: built 2026-09-24 (branch `phase-1-sizing`), awaiting eval** (`eval_run gj-h1-regen --repeat 1 --label phase-1`).
Decisions (user, 2026-09-24): (1) **rewrite** blueprints + golden examples to the new grammar — they matter most: a blueprint matched ~10 of the 14 baseline slides and the prompt says "keep the SAME flex properties"; (2) weight → grow **hero 3 / peer 2 / supporting 1 / minor none**, minH Chart 180, Matrix 260, Flow/Tree 200, ProcessArrow 90; (3) `w="max"` on a VStack child: **audit only** (`VSTACK_W_MAX`, low) — decide an auto-fix later from eval data; (4) eval = **`gj-h1-regen` × 1** (same as baseline).
Built:
- Grammar: `house-style.yaml` — `height_budget`, `worked_example`, `weight_allocation`, `rigid_nodes` replaced by `sizing` (SIZING BY WEIGHT) + `data_nodes` (DATA NODE SIZING); vocabulary, composition, header band, checklist, gotchas rewritten. `system.j2` / `user.j2` sizing lines, blueprint band rendering (`[grow=N]` instead of `h=<formula>`), recipe preamble, `recipes.yaml` (all 20 recipes), `pyramid.yaml`, `nodes.yaml` Chart.
- `minH` was a **blocking `UNKNOWN_ATTR`** (not in the generator's attribute list nor the normalizer's `_UNIVERSAL_ATTRS`) — the new grammar would have cost a retry per chart. `minW/maxW/minH/maxH` now allowed (POM `BASE_RULES` accept them on every node).
- `layout_audit`: `MISSING_DIMS` = Chart/Matrix/Flow/Tree/ProcessArrow need an h (`h="max"` needs `minH`), Timeline/Pyramid a pixel h, Table nothing; new `VSTACK_W_MAX` (low).
- Blueprints + golden examples rewritten by a parent-aware transform (VStack child `w="max"` dropped, HStack child `h="max"` dropped, pixel band/card h → content or `grow`, data nodes per DATA NODE SIZING), then by hand: text panels that take the spare height (`pillar_cards`, `kpi_only`, `table_with_action_cards`), `dashboard_3band` 300:200 px → grow 3:2, fixed `<Col>` widths → label column only. Structure bands: `rigid`/`height_formula`/`min_h`/`max_h` → `auto` | `grow` (+ `grow: N`).
- Fixtures `tests/fixtures/layout_sizing/` (dashboard from gj-h1 02, table from gj-h1 10, flow from fit_grow s3); `tests/unit/test_layout_sizing.py`: fixtures, all recipes, all blueprint/golden references compile + are audit-clean, blueprint structure ↔ reference grow agree. Unit tests 413 pass (+17), same 4 pre-existing failures.
LLM-free results:
- Blueprint + golden references (17 slides, 60 cards), fit-grow off → mean fill **0.764 → 0.852**, low-fill cards **19 → 11**; fit-grow on **0.804 → 0.874**, **15 → 10**; `VSTACK_W_MAX` 34 → 0, `COL_WIDTH_SUM` 4 → 0.
- Dashboard fixture with fit-grow off: KPI tiles 83 px, fill 0.97 (the old-style fit_grow s1 tiles: 246 px, 0.32); chart card 0.998; mean 0.906 (on 0.949).
- Generator system prompt **−3.0%** (−117 … −330 tokens per slide over 7 representative plans; e.g. standard 8785 → 8533).
- Baseline deck against the new rules (for the eval comparison): `VSTACK_W_MAX` on 10/14 slides (24×), 30 stacks with a pixel h, 0 `minH`, 0 `grow`.
Findings (render-verified, not fixed here):
- **Wrapped table cells need row height.** A Table with no h at the default 40 px row and 2–3-line cells: POM lays out 312 px, PowerPoint/LibreOffice grow the rows → the table spills out of its card over the next band, and the bottom 40% of the slide stays empty. fit-grow's table pass grows rows only to ~47 px. The grammar therefore sets `defaultRowHeight = 16 + 24 × lines` (+ header 40); computing it is Phase 5 (sizing plan Step 3). The fill metric cannot see this (it reads declared frames) — nor empty slide space below content-sized bands.
- **fit-grow scales peer cards as one group**: a text card beside a card whose chart/diagram now fills stays unenlarged (fixture s3, first layout). The grammar avoids it (hero diagram full width, text band content-sized); worth a look by the fit-grow owner.
- A horizontal Flow of 5 nodes is width-limited: a tall `h="max"` box leaves space above/below the node row (F6) — the grammar gives such flows full width.
- Thin table-only slides now end early instead of stretching the table card (by design, F5); more rows / Phase 5 row sizing fill them.

**Eval `phase-1` (2026-09-24, commit `4ab1fc2`, `gj-h1-regen` × 1, $1.05) → `docs/eval/phase-1/`.** Note: this run also carries the normalizer fixes (merged after the baseline), so first-pass is judged against the replay (14/14), fill and layout against the baseline.

| metric | baseline | phase-1 |
|---|---|---|
| compiled / first-pass | 85.7% / 50% | 100% / 92.9% (13/14; retries: `<Td borderLeft>`, zero-height text box) |
| mean fill (eval, fit-grow on) / low-fill cards | 0.884 / 13.0% | 0.891 / 10.9% |
| 12 common slides, re-compiled with today's normalizer: fill fit-grow off → on | 0.850 → 0.884 (low 22% → 13%) | 0.875 → 0.889 (low 16% → 12%) |
| text overflows / layout issues per slide | 0.21 / 0.79 | 0 / 0 |
| fit-grow changes per slide | 0.86 | 0.29 (the grammar now does that work) |
| golden card-pattern match | 0.38 | 0.475 |
| grammar: VStack-child `w="max"` / Chart pixel h / `grow` / `minH` | 30 / 5 / 0 / 0 | **0 / 0 / 10 / 3** |
| tokens in / cost | 345k / $1.16 | 325k / $1.05 |

Acceptance: first-pass not worse ✔, prompt smaller ✔, generator follows the grammar ✔; **fill Δ +0.007 (+0.025 without fit-grow) is below the 0.05 noise bar** — the fill metric does not see slide-level empty space or table rows spilling out. Visual review (baseline vs phase-1, all 14): better — slide 8 timeline (baseline labels ran off the card, top half empty; now compact with the detail below), slide 2 chart fills its card, slides 4–5 generated (placeholders in the baseline; fixed by the normalizer, sized well here), slide 12 roadmap fits. Weak — **tables**: the planner marks tables `hero` and the generator turns that weight into `grow` on the table card (slides 10, 11) against the rule → stretched card (11); slide 10 spills its table over the chart card below — corrected diagnosis (frame measurement, fixture `tests/fixtures/fit_grow/s6-wrapped-table-phase1.xml`): the cells do not wrap; the slide is over-full (header + 7×40 px table + chart band with minH 180 + note + source > 720), POM flex-shrinks the table box to 175 px while the pptx still writes 280 px of rows; slides 3 and 6 (table-only content) end ~⅓ early. Not sizing: slide 1 planned as 3 `bullet_list`s (no chart/KPIs — planner variance, Phase 2); invented numbers 15 → 0 and first-pass mostly from the normalizer.
**DECIDE (user, 2026-09-24): merged into `feat/golden-reference-grounding`** (not worse than the baseline on any gate metric). Next for tables: pull Phase 5 Step 3 (row heights + column widths from the cell text, in `fit-grow.js`) forward, coordinated with the fit-grow session — brief in Phase 5 below. Done 2026-09-24 (no paid run; measured with the next change): "a `hero` table never grows its card — its weight is rows" in `house-style.yaml`, the `table_card` recipe and the component's `height-weight` line in `generator/user.j2`.

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

### Step 3 pulled forward (user, 2026-09-24) — brief for the `fit-grow.js` session
Tables are the weak spot after Phase 1 (eval `docs/eval/phase-1/`, Phase 1 section above). What the grammar now produces: `<Table>` with **no h/w** (sizes to its rows), its card with **no h, no grow** (also for a `hero` table — "its weight is rows"), `defaultRowHeight` chosen by the generator from wrapped lines (16 + 24 × lines), header `<Tr height="40">`, often one label `<Col width>`.
Why today's `fitTables` never helps: it returns early when any `<Tr height>` exists (the grammar's header row), and it only acts when the table box is taller than its rows (`boxH > rows × rowH0 + 8`), i.e. old-style `Table h`. With the new grammar box == rows, so the pass is a no-op.
Failures to fix, with evidence:
1. **Over-full slide squeezes the table** — `tests/fixtures/fit_grow/s6-wrapped-table-phase1.xml` (real phase-1 slide 10): content-sized bands + chart `minH` exceed 720; POM flex-shrinks the table box to 175 px but writes 7 × 40 = 280 px of rows → the table spills over the chart card (frames measured from the pptx). A Table cannot shrink, so something else must give (or the overflow must be reported).
2. **Wrapped cells at too-short rows** — POM never grows rows with their text (F5); PowerPoint/LibreOffice do, so the table grows past its box. Reproduced with gj-h1 slide 10 content at 40 px rows (Phase 1 findings); `tests/fixtures/fit_grow/s5-review-edge-cases.xml` has long cells. The generator's lines estimate is a guess — measure instead (sizing plan §4 Step 3: widths HTML-auto-layout min/pref; row height = wrapped lines × fontSize × 1.3 + 8 at the resolved column width, `measureText` + `resolveColumnWidths` as `tableTextFits` already does).
3. **Table-only slides end early** (phase-1 slides 3, 6) and **stretched table cards** where a generator still grows them (slide 11): spare height could become taller rows of the slide's main table instead of empty slide / dead card space.
DECIDE (ask the user before coding): (a) overwrite the generator's `<Col width>`s or size only unset columns; (b) over-full slide: protect the table (e.g. `minH` = Σ rows) and let which band give — or only report it; (c) should spare slide height grow the rows of the main table (cap?); (d) fate of the existing grow-a-little / box-clamp logic.
Verify LLM-free: the three fixtures above + `tests/fixtures/layout_sizing/s2-table-text.xml`; gj-h1 golden tables must not regress (fill 0.896 with fit-grow on; `python -m scripts.eval_run --fixtures tests/fixtures/golden/gj-h1-deck --label golden`); `pytest tests/unit` (414 pass, 4 known failures); LibreOffice renders. Replay the phase-1 run for free: `llm_test/gj-h1-regen-7293ef.zip` (local only, untracked) `deck/input.xml` → recompile all 14 slides and compare slides 3, 6, 10, 11 with `docs/eval/phase-1/renders/`. Consider a metric for failure 1/2: rows exceeding their table frame (Σ `<a:tr h>` > the graphicFrame `cy` in the pptx) — the fill metric reads declared frames and cannot see it.

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
- `outline_planner`: `DeckSettings` default (`slide_count="6-10"` → 8) wins over `state["deck_min_threshold"]`, so `python -m src.graph` / `src.runner` / any call without `deck_settings` plans 8 slides (found 2026-09-24; the eval sidesteps it via `test_case["slide_count"]`).
- Bare `&` in generated text compiles in POM but `layout_audit` (ElementTree) fails the whole slide with `XML_PARSE_ERROR`; the normalizer does not escape it (found 2026-09-24).
- `house-style.yaml` `layout_archetypes` (A–E) is never rendered into the prompt (`_HOUSE_STYLE_SECTIONS` omits it), yet `system.j2` makes "pick one of the LAYOUT ARCHETYPES" mandatory (found 2026-09-24).
- `repair_guidance.LAYOUT_SHRINK_GUIDANCE` step 1 tells the repairer "reduce body fontSize by 2 (14->12)", against the 14 pt floor (found 2026-09-24).

## Done before this roadmap (2026-09-23)

- Design-hint scoping, content-model nesting, exact icon names — `docs/design-hint-architecture.md`.
- `llm.md` review: audit source, not a prompt (full-reference prompting lost to selective context on 2026-09-02). Fixed: `shape.yaml` taught `line.width="0"` (POM rejects all zero strokes; normalizer strips them, `ZERO_STROKE_REMOVED`); accent-stripe rule narrowed to `borderTop` (render-verified). `tests/unit/test_upstream_reference.py` compiles every `llm.md` example.
- Sizing facts F1 and F4 of `docs/layout-sizing-plan.md` re-verified by frame measurement (KPI row h=150 + w=max in VStack → 495 px; Table with no h → 84 px = 32 + 52).
