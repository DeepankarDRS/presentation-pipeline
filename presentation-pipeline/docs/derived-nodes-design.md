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

### 10c. Phase 0b results (2026-10-04, build PC, no API)

Built: `scripts/phase0b/` — `style_packs.yaml` (editorial, tech), `render.py` (frame,
cover, KpiRow, CardGrid, tile row, note columns, bullet panel, DataTable, BarList,
ProcessSteps, MessageStrip, insight; a fixed-rule composer), `check.py` (criterion 2),
`plans/xtsy.json`, `plans/cheffin.json`. Run:

```bash
python -m scripts.phase0b.render scripts/phase0b/plans/cheffin.json --out output/phase0b/cheffin
python -m scripts.render_check --in output/phase0b/cheffin --out output/render_check/phase0b-cheffin
python -m scripts.phase0b.check scripts/phase0b/plans/cheffin.json output/phase0b/cheffin
```

| Criterion | Ours (same XTSY plan, gpt-4.1 UI deck) | Code renderer |
|---|---|---|
| Compiles first time | 8/8 (after repairs in the run) | 14/14, no repair loop |
| 1. Broken words / slide (eval) | 1.0 | **0** (XTSY and CHEFFIN) |
| Mean fill · low-fill cards | 0.81 · 23% | **0.91 · 0%** (XTSY), **0.97 · 0%** (CHEFFIN) |
| 2. Plan words missing · words not in plan | 0 · 4 (an invented "Opportunity Matrix: Levers…" heading, "Key takeaway") | **0 · 0** both decks |
| 3. Same frame on every slide | no (each slide's header drawn differently) | **yes** (by construction) |
| 4. Closer to Genspark (user's judgement) | — | side-by-side sheets: `output/phase0b/cmp_cheffin.png`, `cmp_xtsy.png` (gitignored) |

Audit after the run: only the intended 9–10px `FONT_TOO_SMALL` labels, `DEEP_NESTING`
(low), and the known `LOW_CONTRAST` false alarm on the XTSY cover gradient.

What the side by side shows (author's read; the user decides criterion 4):
- **CHEFFIN (data deck): close.** Frame, entity colours, KPI tiers, ranked bars, dark
  strip, numbered source cards match Genspark's design language. Remaining gap: Genspark
  fills the slide (bigger numbers, a note under each KPI, "2.9x" derived column, a
  larger "what this means" panel); ours leaves vertical space where the plan has less
  content.
- **XTSY (narrative deck): look yes, visuals no.** Frame, number badge, phase columns,
  progression row and strip match; Genspark's purpose-built slide visuals (time-of-day
  line, input → engine → outcome with a feedback loop, rising arrows) are slide patterns
  (§ ranked option 3) plus extra content, which blocks alone don't give.
- The renderer needed **no LLM call and no repair**; every number and line is the plan's.

Found on the way (feed into the build):
- fit-grow `growStats` grew a KPI number 42 → 60px that the renderer then wrapped
  ("₹114." / "9L"): code-drawn nodes must be **exempt from fit-grow** (or fit-grow must
  measure in the slide's font) — confirms §6.
- fit-grow `reserveWrap` again added blank heading lines; the renderer holds headlines
  in a fixed-height box, as Phase 0 found.
- Small orange / teal labels need darker shades for 4.5:1 (`C2410C`, `00795A`; entity
  text uses a 25% darker shade of the entity colour).

### 10d. Studio style pack (2026-10-04, no API)

Compared against Genspark **AI Slides**' XTSY deck (cream, lime, display type) — the
tech pack matched its structure but not its style. A third pack, `studio` (from AI
Slides + the Phase 0 hand-built slides), added as style-pack switches only:
two-tone headlines (the bold phrase comes from the plan's own title `design_hint`,
"color the phrase …"), italic last word on card titles, a white / dark / lime fill
rhythm, hairline-bordered white cards on cream, ghost numerals on phase cards, a dark
slide when the hero is 4+ ordered steps, ruled italic closing statements, arrow icons
for "↑" items. `python -m scripts.phase0b.render <plans> --out <dir> --pack studio`.

- XTSY 8/8 and CHEFFIN 6/6 compile; plan words missing 0, words not in plan 0 (both).
- New contrast findings are audit limits (dark slides measured against white, the
  gradient cover) and the intentionally faint ghost numerals.
- One switch restyles a whole deck: CHEFFIN rendered in studio with no other change.
- Side by side (`output/phase0b/cmp_xtsy_studio_*.png`): typography and colour rhythm
  now read like AI Slides. Still missing: purpose-built visuals (engine diagram, mini
  charts, filled matrix), rewritten claim headlines and per-card descriptions — slide
  patterns and content policy, not style.

### 10e. Layout v2: height by weights and caps (2026-10-04, `943dd13`)

The empty bands in 10c/10d came from the composer, not POM: all slack went to one
spacer, KPI tiles and title-only cards had fixed heights, type ignored the slot.
Now the frame passes the body height; fixed blocks (strips, statements, tile rows,
note panels, progression rows) take their estimated height; growers share the rest by
weight (hero 3, peer 3, supporting 1) up to a per-block cap (water-filling); slack
left over widens gaps (≤ +32px) and centres the rest. Blocks size to their slot (KPI
numbers, card titles, rich-card bullets, table rows, bar thickness). 5+ KPI tiles that
mix totals and per-entity values split into two tiers. A slide containing
`<!-- fit-grow: off -->` skips fit-grow (`compile-pom.js`); code-drawn slides carry it.
28/28 compile, text check 0 / 0 on all four deck × pack runs.

Open (see 10f): the caps are fixed numbers, not relative to the content, so sparse
blocks are enlarged rather than left with honest white space.

### 10f. Sparse content is enlarged, not left alone (open, 2026-10-04)

Why KPI tiles and card grids grow when the content is sparse: after the fixed blocks,
the composer gives **all** remaining height to the growers, up to caps that are fixed
numbers (KPI hero 240px, supporting 150px, title-only cards 170px per row). On a
sparse slide the fixed blocks are small, so every grower reaches its cap — about twice
its natural height (a title-only card needs ~80px, a hero KPI tile ~110px) — and the
type then scales to the taller box (KPI numbers up to 72px, card titles up to 30px).
That is "fill the slide" by inflation: the same thing fit-grow did, moved into the
composer.

Proposed rule (not built):
- **Cap = natural content height × a stretch factor** (≈ 1.3, per block kind), not a
  fixed pixel number; type grows at most one step (KPI hero ≤ 56px, card title ≤ 22px).
- **White space is allowed.** Slack beyond the caps goes to spacing rhythm (gaps,
  centring, margins) — never to bigger boxes or bigger type.
- **Thin slides are a content signal, not a layout job.** If the content fills < ~55%
  of the body, report `SLIDE_SPARSE` to the plan reviewer: the fix is §12 content
  (derived values, flagged card lines, a second component), not inflation.

### 10g. Root cause: POM measures every font as Noto Sans JP (found 2026-10-04)

Verified in code: POM can measure real fonts (`buildPptx(xml, size, { fonts })` →
`FontRegistry`), but we never pass any — `compile-pom.js` calls
`buildPptx(xml, SLIDE_SIZE)` and `fit-grow.js` calls `createBuildContext("auto")`. So
POM lays out every `fontFamily` with Noto Sans JP metrics while the slide renders in
Segoe UI / Aptos / a substitute. Every sizing compensation follows from this:
fit-grow's 85% width margin, `reserveWrap`'s blank heading lines, its timid caps
(text ≥ 24px frozen, body ≤ 22, KPI ≤ 60) and its occasional over-growth (₹114.9L
wrapped at 60px), and the composer caps in 10e. Adding rules hides one symptom and
creates another.

Production-grade direction (proposed, in order):
1. **Measure with the real fonts** — ship open fonts (Inter, Space Grotesk,
   JetBrains Mono, Noto Sans; Segoe UI cannot be redistributed), pass them to
   `buildPptx(…, { fonts })` and fit-grow's `createBuildContext`, embed / install them
   where decks are opened. **Next step: the font experiment** — Phase 0b slides in
   Inter + JetBrains Mono, fit-grow back on, measure broken words and blank heading
   lines against the LibreOffice render.
2. **One sizing authority, content first** — each block measures its content, picks a
   size from a fixed type scale by role, emits `minH` (natural) / `maxH` (≈ ×1.3) /
   `grow`; POM's Yoga solves the slide. Replaces the Python water-filling and
   fit-grow's post-hoc filling.
3. **Alignment is a style token** — card content top-aligned by default (`spaceBetween`
   only where a pack asks; the pipeline's `card_grid` recipe centres today).
4. **fit-grow becomes a guard** — shrink one step / report overflow, never fill.
5. Sparse slides → §12 content + `SLIDE_SPARSE`, not inflation (10f).
6. Real-renderer checks in tests (render_check + eval word breaks / overflow).

## 12. Content policy (decided by the user, 2026-10-04)

Replaces the blanket "never invent" for slide text. The test: **can a reviewer check
it from the brief alone?**

| Kind | What it is | Examples (Genspark decks) | Rule |
|---|---|---|---|
| **Copied** | the brief's own words | headlines, numbers, list items | allowed (as today) |
| **Derived** | computed from facts in the brief | "2.9x" (₹31.1 ÷ ₹10.7), "Seven growth levers", "Day 1–30" from "90 days / 3 months", "best ad type" (highest ROAS), "≈ ⅓ of break-even" | **allowed, computed by code**: the planner names the derivation, code computes it, the slide marks it derived (provenance). Settles D13. |
| **Inferred** | a plausible reading, not stated | one-line card descriptions, a claim headline written from the brief's own key message, placing the brief's listed items into matrix cells | **allowed, flagged**: qualitative only — no numbers, no company / person / place names not in the brief, no claims about results or causes; listed on the review screen with Keep / Remove (extends `written_lines`) |
| **Invented** | new facts | market sizes and CAGRs, cited sources, "6–8% incremental demand", new list items ("Tier-2 city entry", "Combo upsell + multi-can"), time windows ("5–7 AM") | **not allowed**; a later opt-in research mode may add figures only with a cited source the user approves |

Consequences for the build:
- Headlines: the planner may write a claim headline from the brief's key message
  (flagged inferred); the brief's own headline stays available as the subtitle.
- Matrix: the brief's listed items may be placed in lever × platform cells (flagged);
  no items beyond the brief's list.
- Derived values need a small, tested set of operations in code (ratio, difference,
  share, rank / best / worst, count, range split) and a provenance tag per value.
- Checks: `scripts/phase0b/check.py`-style text check becomes three-way — copied words,
  derived values (recomputed), inferred lines (on the review list); anything else is
  an error.

## 11. Risks

- **Templated sameness** (why archetypes were removed 2026-09-10): nodes cover card
  internals only; layout, weights, variants and emphasis stay with the LLM. Measure
  variety on the renders.
- **Owning a small DSL:** cap ≈ 10 nodes, versioned spec, every node render-tested.
- **The LLM ignores nodes:** raw POM still compiles; `node_bypassed` shows it in evals;
  replaced recipes are removed so the node is the easy path.
- **Two-level debugging:** keep node-level and expanded XML side by side in every run.
