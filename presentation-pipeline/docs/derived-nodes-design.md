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

**Update (2026-10-04, user decision): fill the card, don't shrink it.** Shrinking caps to
natural height × 1.25 removed the gap but left small type and floating white space; the
user rejected it ("the content should increase font size to fit the area"). Built instead
(`render.py`): text is measured with the real Inter / JetBrains Mono widths (PIL on
`src/node/fonts/`, estimate for other fonts); **title-only cards** get the largest title
size (≤ 48px) at which every title fits the card width and free height, breaking after
hyphens like the renderers; the card label scales to 13px. **KPI numbers** take the
largest size the tile width allows (no 72px cap; e.g. 72 → 96–104px hero, 64 → 85px
supporting); the label scales to 14px. A KPI number is width-bound, so the KPI tile is
capped at the height that number needs × 1.15 (never above the old 240 / 150px).
Card sizes elsewhere unchanged. XTSY + CHEFFIN (studio_inter): 14/14 compile, 0 broken
words and 0 KPI wraps in the LibreOffice render, text check 0 / 0.

**Description cards (title + body, XTSY 5):** title and description grow together, the
largest description first (≤ 18px), the title ≥ 1.3× it. Peer grids side by side get the
same rows, a width split by column count, and one shared size (the smaller fit); their
height cap is lifted so they use the slide's spare height. XTSY 5: 19/12 → 25/16px.
Line breaks must agree between POM and the renderer, or the card shows a blank line
(POM reserves more) or overflows (fewer). They differ because POM's wrap keeps each
word's trailing space, never breaks at a hyphen, and measures italic runs upright. So
the fit counts lines as the renderer draws them (italic last word in the italic face),
accepts only sizes where that count is stable within ±3% of the width, and pins a Text's
`h` to the drawn lines when POM's count differs (`pin_h`).

**Width-bound title cards (CHEFFIN 4: five tall, narrow cards):** when the widest word caps
the title size and the card keeps > 40px of height the title can't use, the card's own
number (its "01" label) is drawn as a big faint numeral sized to that space (≤ 96px;
`$line` on white cards, the label colour on dark / lime) — the numbered source cards of
Genspark's CHEFFIN deck, no new content. Not used with ghost numerals, icons or tags.

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

**Correction (font experiment, same day):** POM's `"auto"` mode measures with Noto only
when the text names "Noto Sans JP" or no font. Any other unregistered `fontFamily`
(Segoe UI, Inter, Consolas …) gets a **0.5 em-per-character estimate**
(`measureText.js` → `measureTextFallback`). Phase 0b names Segoe UI / Consolas, so its
"baseline" was the estimate, not Noto. Even with registered fonts, POM uses only the
font's **widths**. Line height and vertical metrics stay on Noto
(`measureFontLineHeightRatio`), and faces are keyed by family + normal/bold, so italic
measures as upright.

#### 10g-1. Font experiment result (2026-10-04, build PC, no API)

Built: `src/node/fonts.js` loads every `.ttf/.otf` in `src/node/fonts/` (Inter 4.1
Regular/Bold/Italic/BoldItalic, JetBrains Mono 2.304 Regular/Bold, OFL files beside
them). `compile-pom.js` passes them to `buildPptx(…, { fonts })` and `fit-grow.js` to
`createBuildContext("auto", fonts)`. `POM_FONTS=0` or an empty folder gives the old
behaviour. Two details were needed:
- **Italic files are not passed:** they would replace the upright face in POM's registry.
- **GSUB is hidden in memory:** POM's opentype.js 2.0.0 throws on a GSUB lookup that
  both fonts use (lookupType 6 format 2) during width measurement. Renaming the table
  tag before parsing avoids it, and the files on disk stay upstream. Substitutions don't
  change advance widths or kerning. A font that still fails a sample measurement is
  skipped with a warning instead of failing every compile.

Measured width of a 46-char sentence at 20px: estimate 470px; Inter Regular 474,
Inter Bold 488, JetBrains Mono 562 (mono labels are about 20% wider than POM assumed).

Run: pack `studio_inter` (copy of studio in Inter + JetBrains Mono, both installed
per-user so LibreOffice draws them), both Phase 0b decks with the `fit-grow: off` marker
removed. (a) is `POM_FONTS=0` (the estimate) and (b) is the real fonts. Both were
scored on the LibreOffice PDF with `scripts/phase0b/fontcheck.py`, plus `eval_run
--fixtures` and `phase0b.check`.

| 14 slides (XTSY 8 + CHEFFIN 6) | (a) estimate | (b) real fonts |
|---|---|---|
| Compile | 14/14 | 14/14 |
| Broken words in the LibreOffice render | 0 | 0 |
| Eval `word_breaks` (0.55 em estimate) | 0 | 2 (false: "Visibility", "Profitability" boxes now sized to the real word; drawn intact) |
| Text spilling out of a card (seen in render) | 1 (CHEFFIN 4: "report" below the dark card) | **0** |
| Table text wrapping in a too-narrow column | CHEFFIN 3: "Actual CPC is ~2.9x allowable" on 2 lines | **1 line** (fit-grow column choice now sees real widths); CHEFFIN 6: one cell wraps to 2 lines |
| `reserveWrap` headings → blank line drawn | 3 → **3 blank** | 6 → **6 blank** (both covers shift up, peer card titles misaligned on XTSY 2 and 6) |
| KPI numbers: wrapped / past box | 0 / 0 of 19 | 0 / 0 of 19 (XTSY 3 platform names 46 → 60px, fit) |
| Mean fill · text overflows (eval) | 0.92 / 0.96 · 0 | same |
| Text check (missing · extra plan words) | 0 · 0 | 0 · 0 |

Side by side: `output/fontexp/cmp_xtsy_1-4.png`, `cmp_xtsy_5-8.png`,
`cmp_cheffin_1-3.png`, `cmp_cheffin_4-6.png` (gitignored).

**Reading:** real-font measurement fixes what it should. Overflow and wrap decisions now
match the renderer: the CHEFFIN 4 spill and the 2-line table cell are gone, and nothing
broke. But **every `reserveWrap` line is wrong in both runs**, and real fonts make it
worse (3 → 6). It measures headings at 85% of their width, a margin that existed to
cover the measurement gap, so with the true width it reserves a line the renderer
never draws. The 85% margins in fit-grow (`reserveWrap`, table columns) are now the
error source.

**Fixed (2026-10-04):** fit-grow's `lineCount` measures a text whose font is loaded
(`fontRegistry.hasFont`) at full width, not 85%, so `reserveWrap` and the heading guard in
`search` no longer see phantom wraps; other fonts keep the 85% margin. Re-run (c), same
14 slides: headings reserved 6 → **0**, blank lines drawn 6 → **0**, broken words 0, KPI
numbers 0 wrapped / 0 past their box; covers and peer card titles (XTSY 2, 6) line up.
Test: `test_headline_in_a_loaded_font_is_measured_at_full_width`. The other 85% margins
(table column sizing) are untouched. After
that, step 2 (one sizing authority). Fonts also need to reach the people who open the
decks: embed them or require installation, since PowerPoint without Inter substitutes
another font and the measurement no longer matches.

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

## 13. Research gate before building (decided 2026-10-05)

The design is **not** built from this doc yet. Moving to it brings new risks; most can
be found cheaply first, so the build waits on a go / no-go gate.

**New risks of the design** (and whether research can find them first):

| Risk | Likelihood | Found before building? |
|---|---|---|
| Mixed styles in one deck — polished code-drawn slides next to LLM-drawn kinds without a block (timeline, flow, pyramid, tree, 2×2 matrix, line / pie charts, layer) | high until coverage is broad | yes — R2 replay measures coverage |
| A block does not know its slot width (needs two-pass expansion: lay out the skeleton, measure each tag's slot, then expand) | medium | yes — R3 |
| Dense slides squashed (POM autoFit shrinks the whole slide) or over-full | medium–high on dense briefs | yes — R3 |
| **PowerPoint draws differently from LibreOffice** (every check so far is LibreOffice; clients open PowerPoint) | unknown, possibly significant | yes — R4 |
| Fonts: licence, embedding, missing on the viewer's machine | medium | partly — R1 + an embedding test |
| The LLM does not follow tags (wrong `ref`, odd variant, hand-builds the block anyway) | medium | **no** — only a paid run after wiring one block (≈ $2) |
| Repair / editor / critic must learn the tags | certain work, low risk | design question |
| Upkeep: ~10 blocks × variants × packs; POM internals pinned to 10.3.0 | certain, ongoing | known cost |
| A wrong plan drawn faithfully (swapped matrix, empty plan) | happens today | reviewer loop + §12, not blocks |

The current path is not risk-free either: its problems recur (layout batch, capacity
rules, borders, fit-grow, grow fallbacks since 2026-09-24; the 1 Oct decks still had
broken words and invented cards).

**Research (free or cheap), then decide:**

| # | Research | Answers | Cost |
|---|---|---|---|
| R1 | Font experiment (§10g step 1; **done 2026-10-05**, result below: `94367ac`, `c4b9c13`) | does POM measuring the real fonts remove broken words / blank heading lines / KPI overflow? | no API |
| R2 | Replay saved decks (`llm_test/` zips: gj-h1, tables-check, baseline, layout-batch, layout-fixes — those with full plans) through the Phase 0b renderer (**done 2026-10-05**, result below) | share of components with a block vs LLM fallback; broken words; text check | no API |
| R3 | (**done 2026-10-05**, result below) Phase 0c: hand-written mixed slides (LLM-style skeleton + tags, half-width slots, free text beside blocks, 3–4 components per slide) + `gate-deck-all-nodes-dense`; two-pass slot measurement; per-block minimum readable size → `SLIDE_OVERFULL` instead of squashing; per-block fit-grow opt-out | overlap, squashing, broken words, text check on mixed and dense slides | no API |
| R4 | PowerPoint check: the user opens 3–4 rendered `.pptx` (Phase 0b studio / editorial) in PowerPoint and compares with the LibreOffice PNGs (**done 2026-10-05, passed**, result below) | does PowerPoint match? | ~15 min of the user's time |

#### R1 result (2026-10-05): done — fonts measure true; embedding works in LibreOffice

1. **Phase 0b decks** (14 code-drawn slides, §10g-1): headings reserved / blank lines
   6 → 0 after the full-width fix (`c4b9c13`); a text spill and a wrapped table cell fixed.
2. **LLM decks** (28 slides from saved runs: CHEFFIN `1b306e1de67f`, gj-h1
   `gj-h1-regen-5a9e2d`, tables-check CHEFFIN audit; final `input.xml` per slide;
   `fontFamily="Inter"` added to every Text / Ul / Ol / Shape / Timeline / ProcessArrow /
   Pyramid / Td; fit-grow on; LibreOffice render; `scripts/phase0b/fontcheck.py`):

   | | o: as generated (Noto default) | a: Inter, no font files | c: Inter + font files |
   |---|---|---|---|
   | Broken words | 13 | 11 | **7** |
   | Blank heading lines | 0 (3 reserved, all drawn) | 1 | **0** |
   | KPI numbers wrapped / past box | 0 / 0 | 0 / 0 | 0 / 0 |

   The 7 left in (c) are not measuring errors: one word wider than its box at the chosen
   size ("Recommendation" in a narrow table column, "Projected" / "₹1.80" in narrow KPI
   tiles, labels in narrow ProcessArrow chevrons). POM now knows they don't fit, but
   fit-grow only grows: fixing them is §10g step 4 (shrink one step / report), not fonts.
   Side effect seen: wider Inter text in a narrow card makes its row taller, the
   ProcessArrow beside it loses height, and fit-grow's arrow widening (gated on height)
   no longer runs, so the chevrons stay narrow (CHEFFIN 4, audit 6).
3. **Embedding** (`scripts/embed_fonts.py`, uncompressed EOT parts as PowerPoint stores
   them, ~840 KB for 4 Inter faces before subsetting): with Inter **uninstalled**,
   LibreOffice drew the plain pptx in DejaVu Sans / Arial Black / Liberation Serif and
   "₹114.9L" broke over two lines; the embedded pptx drew Inter, identical to the
   installed render. PowerPoint is not on the build PC → part of R4
   (`output/embedtest/embedded.pptx`). OFL allows embedding.

Follow-ups (not R1): shrink guard for words wider than their box; ProcessArrow width
growth without height growth; subset embedded fonts; embed in `pptx-post.js` if R4 passes.

#### R4 result (2026-10-05): passed — PowerPoint matches LibreOffice

Four decks (34 slides), built by merging the compiled slides (`src/compiler/pptx_merge.py`)
and embedding fonts (`scripts/embed_fonts.py --font …`): Phase 0b XTSY and CHEFFIN in
studio_inter (Inter + JetBrains Mono embedded), CHEFFIN in editorial (Segoe UI + Consolas,
system fonts), and the gj-h1 LLM deck in Inter (fit-grow on; charts and diagrams keep the
default font). The user opened them on the company test PC: Microsoft 365 for enterprise,
**neither Inter nor JetBrains Mono installed** (checked in the Windows font folders).
Result: **all slides match** the LibreOffice renders (line breaks, words, boxes, sizes),
and PowerPoint draws the embedded Inter / JetBrains Mono. An earlier one-slide check on the
build PC showed the plain (not embedded) file drawn ~6% narrower, i.e. substituted, so
**embedding is required** for decks measured in Inter.

Consequence: LibreOffice renders remain a valid stand-in for PowerPoint in the checks,
provided the fonts are embedded. Follow-up: embed (subset) fonts in `pptx-post.js`.

#### R2 result (2026-10-05): coverage high, density is the open problem

Input: every saved run with full production-planner plans on the build PC. Those are 8
decks, 88 slides, 319 components: CHEFFIN `1b306e1de67f` (29 Sep), gj-h1 `5a9e2d` /
`69af33` / `7293ef` / `bf396b` (23–24 Sep), and three XTSY UI exports (23 Sep,
`llm_test/slides*.txt`). The layout-batch / layout-fixes runs are not on this PC; the
Test 1 plans (new path) were left out. Tool: `scripts/phase0b/replay.py` (pack
studio_inter, fonts loaded), then render_check, LibreOffice and
`scripts/phase0b/fontcheck.py` + `check.py`. "LLM" = the same slides as the pipeline drew
them (the `xml` saved in each slides.json, run's theme, fit-grow on).

**Coverage** (plans from before `card_grid` existed):

| Component | Count | Phase 0b |
|---|---|---|
| narrative, title, table, bullet_list, kpi_row, process_arrow | 272 | block |
| chart, bar | 13 | block |
| chart, line / doughnut / area | 9 | block, but drawn as ranked bars (form changed) |
| timeline 12, flow 4, matrix 3, layer 2, group 1, caption on a content slide 3 | 25 | **no block** (LLM fallback) |

→ 89% of components drawn by a block (92% counting changed forms); 56 / 88 slides
entirely code-drawn; 24 slides have at least one fallback component. Blocks still needed
for most coverage: **timeline** (12), then line / doughnut charts, flow, matrix.

**Quality, same plans:**

| 88 slides | LLM-drawn (as generated) | Code-drawn (Phase 0b) |
|---|---|---|
| Compile | 86 / 88 | **88 / 88** |
| Broken words (LibreOffice render) | 32 | **2** ("Recommendation" in a narrow table column, twice) |
| Blank heading lines | 2 | **0** |
| KPI numbers wrapped | 3 | **0** |
| Plan words missing / words not in plan | not comparable* | **3 / 0** (the 3 = the series name of a chart the planner left without data) |
| Slides with overlapping text | 19 | **14** |

\* the LLM decks' chart values live in chart data (invisible to the text check) and they
add their own source / kicker lines.

**Overlap is the real gap.** Code-drawn overlaps sit on dense gj-h1 slides (4–5 components:
KPI row + table + chart + bullets + notes) and two XTSY KPI slides. Root cause, seen in the
pptx geometry: the composer's height *estimates* for fixed blocks are below what POM lays
out, so the slide is over-full and Yoga shrinks boxes below their text (a 120 px KPI
number got a 120 px box instead of 144, and its note was drawn across the digits; table
rows and bullet panels ran into the block below). This is exactly R3's two-pass slot
measurement and minimum-size / `SLIDE_OVERFULL` work. A slide whose only big component
has no block (gj-h1 "What Worked", a timeline) shows a near-empty body.

**Renderer fixes made during R2** (all plan shapes the hand-written Phase 0b plans never
had): cover with no subtitle (POM rejects an empty `<Text>`); empty table cells → "–";
chart series shorter than its labels or with null values (crash, "None" printed);
null KPI notes; chart titles on single charts; covers whose subtitle lives in the
title component or in a second narrative; KPI numbers sized and boxed by glyph height
(`GLYPH_H` 1.2, cap 120 px).

#### R3 result (2026-10-05): two-pass sizing removes the overlap; mixed slides work

Built (all in `scripts/phase0b/`, nothing wired into the pipeline):
- `measure.mjs`: a long-running Node helper on POM's own layout (fit-grow's `layout` /
  `natural` / `squeezes`, now exported): per slide the natural height, squashed boxes
  (content taller than its box, i.e. Yoga shrank it), and the boxes of `slot-…` ids.
- `fit.py`: **two-pass sizing** for the composer. It composes, measures every block
  (`blk-N` ids) and recomposes with fixed blocks at their real height and each grower given
  at least its content's height. If anything is still squashed it steps the body type down
  (×0.92 … 0.68; labels keep their size, text ≥ 11 px, table rows ≥ 24 px). At the
  smallest step it reports **`SLIDE_OVERFULL`** (with the deficit) instead of drawing
  squashed. `replay.py --fit` uses it.
- `expand.py`: **slots in an LLM-style skeleton** (Phase 0c). Free text plus
  `<VStack id="slot-<component_id>" w="50%" grow="1" />` placeholders. Pass 1 lays out
  the skeleton and reads each slot's box; pass 2 draws the block for that box, re-measures,
  and steps type down or reports over-full. The skeleton's own text is never changed.
- Blocks made slot-aware: KPI rows take the slot width (`kpi_block`: tiers in a slot,
  tiles < 170 px wrap to two rows); bullet tiles / note columns only when every tile fits
  its longest word; native POM `<Chart>` for line / doughnut / area / multi-series /
  > 8 points (scales to any slot, where 18 shape bars could not; R2's "form changed" gone).
- Composer bug fixed: the centring spacers are children of the gapped body stack, so
  each cost one more gap; on paper every slide was ~70 px over-full (Yoga hid it by
  shrinking the spacers).

**Dense slides** (R2's 88 slides, `replay.py --fit`):

| | R2 (estimates) | R3 (two-pass) |
|---|---|---|
| Slides with overlapping text | 14 | **3** (one is a false positive: digit and note boxes touch, ink does not; two small touches: a table cell, two chart labels) |
| Type scale used | — | 1.0 on 74 slides, 0.92 / 0.85 on 5, 0.68 on 2 |
| `SLIDE_OVERFULL` reported | — | **1** (gj-h1 `69af33` slide 6, 51 px: too much content at the minimum sizes) |
| Broken words · KPI wraps · blank headings | 2 · 0 · 0 | 1 · 0 · 0 |
| Compile · plan words missing | 88 / 88 · 3 | 88 / 88 · 5 (the 3 of R2 + 2 numbers on the over-full slide) |

**Mixed slides** (`scripts/phase0b/phase0c/`: CHEFFIN exec summary with the KPI row in a 62 %
slot beside free text; CHEFFIN CPC with table and chart in two half slots; XTSY automation
with cards in a 58 % slot and a bullet slot inside a free-text column; gj-h1 snapshot with
5 slots, dense): **4 / 4 compile, 0 broken words, 0 overlapping text, 0 block words
missing**; the dense one at type 0.92. First attempt showed the slot-width risk exactly as
predicted (bullet tiles in a 469 px slot broke 6 words; 5 KPI tiles in one row of a 734 px
slot); fixed in the blocks.

Not covered: `gate-deck-all-nodes-dense` has only a brief, no saved plans, so it would need
a paid planner run; gj-h1's dense plans stood in. Still open: a grower's type does not grow
to fill a tall slot in every block (bullet panel); LLM compliance with slot tags is unknown
until a paid run.

#### Gate reading (2026-10-05, for the user's decision)

| Criterion | Result |
|---|---|
| Fonts measure true (R1) | yes; embedding required and works |
| Blocks cover most components of real decks (R2) | yes, 92%; timeline is the main gap (POM has a native `<Timeline>`) |
| Mixed and dense slides neither overlap nor squash (R3) | yes for mixed (0 / 4); dense 14 → 2 real touches + 1 reported over-full |
| PowerPoint matches (R4) | yes, with embedded fonts |

Author's reading: **go**, built as §13 says (one block at a time behind a setting, with
fallback, a paid run after `CardGrid` to learn tag compliance). Prerequisites carried
from the research: the measuring helper + two-pass sizing in the validator, font
embedding in `pptx-post.js`, a timeline block, a shrink guard for words wider than
their box. The decision is the user's.

**Go** if: fonts measure true (R1), blocks cover most components of real decks (R2),
mixed and dense slides neither overlap nor squash (R3), PowerPoint matches (R4).
**No-go / rethink** if any fails — we learn which part before touching the pipeline.

**If go — build to contain risk:** one block at a time (`CardGrid` first) behind a
setting; automatic fallback to today's LLM path for a slide whose expansion fails;
blocks expand to plain POM so the layer can be removed; one paid run (≈ $2) after the
first block, against the 1 Oct UI decks — the only way to learn LLM tag compliance.
The 6 decisions in §10 are answered before the build starts (1, 2, 6 have evidence;
4, 5 provisional; 3 is a design call).

## 11. Risks

- **Templated sameness** (why archetypes were removed 2026-09-10): nodes cover card
  internals only; layout, weights, variants and emphasis stay with the LLM. Measure
  variety on the renders.
- **Owning a small DSL:** cap ≈ 10 nodes, versioned spec, every node render-tested.
- **The LLM ignores nodes:** raw POM still compiles; `node_bypassed` shows it in evals;
  replaced recipes are removed so the node is the easy path.
- **Two-level debugging:** keep node-level and expanded XML side by side in every run.
