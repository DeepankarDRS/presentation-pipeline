# Design: derived nodes that take their content from the plan

Status: **proposal, 2026-10-04** — nothing built. Decisions for the user in §10.
Reopens Phase 4 of `docs/roadmap-derived-components.md` (halted 2026-09-24) with one
change: a derived node gets its content **from the plan by reference**, not retyped
by the generator.

## 1. Why

Evidence from the 29 Sep `layout-fixes` run (XTSY + CHEFFIN × 2) and the two 1 Oct UI
decks (XTSY, gpt-4.1 and gpt-5-mini planners):

| Failure | Where | Root cause |
|---|---|---|
| Invented content: 6 of 7 impact areas made up | gpt-5-mini slide 7 | the plan's card grid came back empty; the generator wrote cards anyway, nothing checked them |
| Content dropped: each month's first bullet became the card tag | gpt-4.1 slide 8 | the planner moved it into `tag` (in the plan itself); nothing checks plan items against the brief |
| Broken words ("Zept o", "optimizati on"), tiny cards | XTSY slides 2, 3, 6 in every run | narrow cards; the generator picks widths without measuring; second grids from the plan check (removed in `30da01e`) |
| Same items twice (phase cards + chevrons) | slide 4, both decks | nothing compares components on a slide |
| Generic look: rounded white cards, 14px labels, no header chrome | every slide | the generator copies one recipe per kind (`recipes.yaml`) |
| Workflow lost its sequence | slide 6 | a code rule switched type instead of the component adapting |

More planner reasoning (gpt-5-mini) chose better visuals on 3 slides but cannot touch
any row above: they happen after the planner. Phase 0 (`docs/eval/genspark-ref/`)
showed POM 10.3.0 can draw the Genspark-level look when the XML is written carefully.
So the goal is to make that careful XML **code's job**, for the components that fail.

## 2. Idea in one picture

```
brief ─► planner (LLM) ─► plan: components with component_id + content_data   (checked: brief, capacity)
                                   │
generator (LLM) writes the slide:  │  layout, bands, weights, emphasis, free text
   <VStack> … <CardGrid ref="impact_areas" variant="mixed" highlight="4"/> … </VStack>
                                   │
expander (code) ◄──────────────────┘  content copied from plan[impact_areas]; adapts to item count
   → plain POM (VStack/HStack/Text/Icon/Shape)  ─► normalizer ─► fit-grow ─► compile ─► .pptx
```

- The **LLM keeps the decisions**: what goes where, how much space, which variant,
  which item is emphasised, any free text (narrative, headline wording is already planned).
- **Code owns the inside of the node**: the text (verbatim from the plan), the layout
  inside (cards per row, rows, wrapping), sizes, fonts, fills, labels.
- A node never carries text the LLM typed. There is nothing to invent or drop.

## 3. What changes from the roadmap's Phase 4

| | Roadmap Phase 4 (2026-09-23) | This design |
|---|---|---|
| Content | attributes / children typed by the generator (`<KpiTile label=".." value="..">`) | `ref="<component_id>"`; the expander reads the plan |
| Where expansion runs | first step of `normalize_xml` | validator, before `normalize_xml` (the normalizer never sees the plan) |
| First nodes | KpiTile, TableCard, IconList | CardGrid, ProcessSteps, KpiRow, Callout (from the current failures) |
| Adapting to fit | not covered | the expander picks layout from item count and text length (§6) |
| Kept from the roadmap | spec file, expand to plain POM, escape hatch, ≤ 10 nodes, "repeats AND fails in eval" rule, LLM-free tests per node |

## 4. Nodes — first set

Chosen by the failure table in §1. Each replaces one or more recipes in `recipes.yaml`.

| Node | Replaces (recipe / plan kind) | Options the LLM sets | Adapts how |
|---|---|---|---|
| `CardGrid` | `card_grid`, `card_steps`, `card_matrix` | `layout` (grid / steps / matrix — default from the plan), `variant` (outline / filled / mixed / dark), `highlight` (card index or title), `icons` (on/off), `density` | cards per row from count and longest title; steps > 5 → two rows with a turn arrow; matrix columns equal; title-only cards drawn compact, never stretched empty |
| `ProcessSteps` | `process_arrow` (and the capacity switch to cards) | `variant` (chevron / numbered), `highlight` | ≤ 5 steps one row; 6–8 two rows; labels over 2 words → numbered steps, not chevrons |
| `KpiRow` | `kpi_row`, `hero_stat`, KPI tiers | `variant`, `highlight`, `tone` per tile from the plan's directions | 1 value → hero tile; 6+ → hero + supporting tiers (logic already in code) |
| `Callout` | key-message / closing strip, `dark_callout_panel` | `variant` (rule / panel / dark), `label` | one line vs two lines; full width |

Later, only if evals show failures: `Timeline` (two rows), `TableCard`, `SlideHeader`
(kicker + headline + subtitle from the plan, with the Phase 0 mono kicker) and a deck
footer (`XTSY · 07 / 08`, added by code at deck assembly).

Example (CardGrid, plan `impact_areas` with 7 cards):

```xml
<CardGrid ref="impact_areas" variant="mixed" highlight="Market Share" icons="arrow-up" />
```

expands to two rows of 4 + 3 equal columns (`w="1" grow="1"`, the Phase 0 finding),
micro-labels `IMPACT 01…07`, titles verbatim from the plan, the highlighted card
inverted — the Phase 0 impact slide, but drawn by code for any count.

## 5. How a reference resolves

- The generator prompt already lists each component with its id
  (`- card_grid [impact_areas]: …`, `src/prompts/generator/user.j2`). For kinds that have
  a node, the prompt shows the node line to write instead of the recipe and the data.
- Expander checks, each a normalizer-style issue code:
  - `DERIVED_REF_UNKNOWN` (blocking): `ref` is not a component of this slide's plan.
  - `DERIVED_REF_EMPTY` (blocking, **before generation**): the planned component has no
    content — the plan is re-asked instead of generating (fixes the slide 7 case and the
    CHEFFIN empty-plan case at the source: `slide_component_planner.py` must stop
    falling back to `{}` silently).
  - `DERIVED_REF_MISSING` (warning → repair): a planned component with a node never placed.
  - `DERIVED_REF_DUPLICATE` (blocking): the same ref placed twice.
  - `DERIVED_ATTR_UNKNOWN` (auto-fixed, dropped) / bad enum value → default.
- Duplicate content across components (cards + chevrons of the same items) is caught
  earlier, in the plan check: two components on one slide whose item labels overlap
  ≥ 70% → keep the hero, report the other (goes into the plan reviewer loop later).

## 6. Adapting to the slot

The expander runs before layout, so it does not know pixel widths. Two levels:

1. **Structural (first build, Python):** decisions from item count, text length and the
   node's own options — cards per row, rows, chevron vs numbered, compact vs tall cards,
   font tier. Equal columns use `w="1" grow="1"`, so any slot width splits evenly.
2. **Measured (later, fit-grow):** fit-grow already lays the slide out with POM's engine
   (`src/node/fit-grow.js`). It can check each expanded node (marked by a stable id) for
   words wider than their box and ask for one more row / one tier smaller. Only if step 1
   leaves broken words in evals.

Also fix with this work: fit-grow `reserveWrap` measures in Noto Sans JP and adds blank
heading lines (Phase 0 finding); measure in the slide's named font.

## 7. Effects on the rest of the pipeline

| Part | Change |
|---|---|
| `slide_component_planner` | no prompt change for content; stop the silent `{}` fallback (raise → re-ask) |
| `capacity.py` | `per_row` moves into the expander; chevrons / timeline → cards switches removed once `ProcessSteps` / `Timeline` adapt; limit checks only report |
| `context_builder.py` + generator prompt | per kind: a node line instead of recipe + data; recipes for replaced kinds removed (prompt gets shorter) |
| `validator.py` | `expand_derived(xml, plan)` before `normalize_xml`; keep both XMLs in the run folder (`input.xml` = node level, `expanded.xml`) |
| `repairer.py` PATCH, `slide_edit_service.py` | work on the **node-level** XML (smaller, and the node can't be broken from inside); re-expand after every edit. Compile errors inside an expansion are code bugs → caught by tests, not repairs |
| `deck_nodes.py` | assembles expanded slides; deck footer added here (later) |
| Critic / visual critic | unchanged (they judge the render); remove rules the nodes make impossible |
| Review screen (written lines Keep / Remove) | edits the plan → re-expand; no LLM call |
| Cost | generator output shrinks (no card XML); one extra planner call only when a plan comes back empty |

Escape hatch: the generator may still compose raw POM for anything. If it hand-builds a
component that has a node, the validator warns (`DERIVED_NODE_BYPASSED`) — counted in
evals, not blocked.

## 8. Files

New:
- `src/knowledge/core/derived-nodes.yaml` — per node: options (type, enum, default),
  which plan kind / `content_data` keys it reads, accepted treatments
  (from `hint-capabilities.yaml`).
- `src/compiler/derived_nodes.py` — find nodes, validate, resolve refs, build POM.
- `src/compiler/derived/` — one builder per node (`card_grid.py`, …) + shared style
  tokens (label tier, card fills) taken from the Phase 0 slides.
- `tests/unit/test_derived_nodes.py` — every node × layout × variant × item counts
  (2, 5, 7, 12) expands to XML that compiles, is audit-clean, and contains every plan
  string verbatim; golden snapshots.
- `scripts/render_plan.py` — LLM-free harness: takes saved `slides.json` plans, places
  each component's node in a simple stack, compiles and renders. Lets us judge the
  nodes on the real XTSY / CHEFFIN plans without the API.

Changed: `validator.py`, `context_builder.py`, `prompts/generator/*`, `recipes.yaml`,
`capacity.py`, `slide_component_planner.py`, `repairer.py`, `slide_edit_service.py`,
`deck_nodes.py`, `scripts/eval_*.py` (new metrics, §9).

## 9. Build order and acceptance

| Step | What | Accepted when | API |
|---|---|---|---|
| 1 | Spec + expander + `CardGrid` (grid / steps / matrix) + tests + `render_plan.py` | all `card_grid` plans from the 29 Sep and 1 Oct decks render with 0 broken words, every plan string present, side by side with Phase 0 | no |
| 2 | Wire into the pipeline: validator expansion, generator prompt, repair / edit on node XML, empty-plan re-ask, duplicate check | unit tests; replay of saved runs where possible | no |
| 3 | Paid check: `gate-deck-xtsy-qcomm` + `gate-deck-cheffin-full` × 2 (≈ $2) | vs `layout-fixes` (06c9c46): word breaks ↓, low-fill ↓, invented card text 0, first-pass ≥ 96% | yes |
| 4 | `ProcessSteps`, `KpiRow`, `Callout`; drop the remaining type switches in `capacity.py` | same metrics + `gate-deck-all-nodes*` | step-end paid run |
| 5 | Measured adapting in fit-grow; `SlideHeader` + deck footer if wanted | Genspark side-by-side review | yes |

New eval metrics: `card_text_not_in_plan` (target 0), `duplicate_items_per_slide`,
`node_bypassed`, plus the existing `word_breaks_per_slide`, `low_fill_pct`.

## 10. Decisions for the user

1. **Order vs the plan reviewer loop (D14, `docs/plan-reviewer-loop.md`).** Recommended:
   nodes steps 1–3 first (they fix what the renders show), reviewer loop next; the
   capacity reports and duplicate check feed the loop later.
2. **Builders: Python functions vs Jinja XML templates.** The roadmap leaned Jinja.
   Recommended now: Python builders (the adapting logic — rows, tiers, compact cards —
   is code) with style values in YAML.
3. **Source of truth for repair / edit: node-level XML** (recommended) vs expanded XML.
4. **Label tier below 14px** (Phase 0: 10–12px mono labels read well). Needs the
   house-style minimum and `FONT_TOO_SMALL` to allow a label role.
5. **How much look the LLM controls:** variants per node (recommended: 3–4 each) vs one
   look per node. More variants = more variety, more templates to test.
6. **`SlideHeader` + deck footer in scope** for step 5, or keep headers LLM-written.

## 10b. Phase 0b — proof before wiring (added 2026-10-04)

**Question:** is the gap to Genspark in *drawing* (code could close it) or in
*planning* (it couldn't)?

**Evidence so far**
- Our CHEFFIN plan (29 Sep `layout-fixes`, run 2) matches Genspark's CHEFFIN deck slide
  for slide: exec summary = KPI tiles + dark diagnosis strip; CPC gap = table + bars +
  note; methodology = 5 source cards + 2 notes; FLIPCART = 3 + 4 KPI tiles + strip;
  ad-type / match-type = table + ranked values + action. Headlines identical.
  The differences are drawing: entity colours (FLIPCART orange, ZAROMA purple), big
  numbers with small units, 9–11px mono labels, numbered cards, ranked bars, a frame.
- Phase 0: POM draws the Genspark look when the XML is careful.
- 1 Oct: gpt-5-mini planners changed visual choices on 3 slides, none of the drawing.
- Both Genspark decks use one design system each and ~6 recurring blocks — not a
  library of templates.
- Correction: the XTSY roadmap's missing first bullet is in the **plan**
  (`"tag": "Category assessment"`), a planner error, not the generator's.

**Experiment** (no API): a standalone renderer, `scripts/phase0b/`, that turns saved
plans into POM XML with code only:
- a **style pack** (palette roles, entity colours, type scale with a 9–11px label tier,
  frame) — `editorial` from Genspark CHEFFIN, `tech` from Genspark XTSY;
- a **frame** (label + running title, headline, subtitle, footer with source + n / N);
- blocks: `KpiRow`, `CardGrid`, `MessageStrip`, `DataTable` (+ `BarList`, `ProcessSteps`,
  `BulletPanel` where the decks need them);
- a small **composer** that stands in for the generator's layout choices (order, side
  by side, which variant) with fixed rules — the real pipeline leaves those to the LLM.

Inputs: XTSY = the gpt-4.1 UI deck's `slides.json` (1 Oct; plans complete; components
the removed icon-list rule had converted are drawn as lists, as current code would plan
them). CHEFFIN = plans rebuilt by hand from `tests/cases/gate-deck-cheffin-full.yaml`
with the component kinds our planner chose on 29 Sep, content verbatim from the brief.

**Pass criteria (fixed before building)**
1. 0 broken words (eval `word_breaks`) on every slide.
2. Every plan string is on its slide and no other text is (frame labels excepted).
3. The same frame on every slide.
4. Side by side (ours now / plan + code renderer / Genspark), the user judges the code
   renderer clearly closer to Genspark than ours.

Pass → wire in (§9 steps 1–3). Fail → we learn where the gap really is, for no API cost.
What it cannot show: content Genspark adds (source lines, card descriptions, time
ranges) — that is the content-density decision, measured separately.

## 11. Risks

- **Templated sameness** (why archetypes were removed 2026-09-10): nodes cover card
  internals only; layout, weights, variants and emphasis stay with the LLM. Measure
  variety on the renders.
- **Owning a small DSL:** cap ≈ 10 nodes, versioned spec, every node render-tested.
- **The LLM ignores nodes:** raw POM still compiles; `node_bypassed` shows it in evals;
  replaced recipes are removed so the node is the easy path.
- **Two-level debugging:** keep node-level and expanded XML side by side in every run.
