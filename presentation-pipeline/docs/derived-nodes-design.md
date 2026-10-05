# Design: derived nodes that take their content from the plan

Status: **proposal, 2026-10-04** — nothing built. Research gate §13 done; hold-out test §14.3b; current recommendation §14.6 (LLM layout + code blocks in slots + a checking loop, planner fixes first), decisions for the user in §14.4 (2026-10-05). **User chose §14.6 (2026-10-05)**; evidence per part and kill criteria in §14.5; the slot test (step 1a) runs before the build.
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

## 14. Build route and decisions (proposal, 2026-10-05)

Written after the research gate (§13), for the user's go / no-go. Nothing here is
decided. **The recommendation was revised after the hold-out test (14.3b) and the outside
evidence (14.5): see 14.6.** 14.1–14.3 stay as the record of the first proposal. Each item gives the **assumption** it rests on, the **evidence** for and against,
and a **recommendation**. "Free" = no API cost.

### 14.1 Route: code composer first, LLM skeleton + tags later if needed (superseded by 14.6)

**The two routes**

| | A. Code composer (Phase 0b, proven) | B. LLM skeleton + tags (§2, as designed) |
|---|---|---|
| Who lays out the slide | code, from the plan (kinds, weights, item counts) | the generator LLM writes the skeleton and places `<CardGrid ref=…/>` tags |
| Who draws each component | code (blocks) | code (blocks) |
| Free text beside blocks | none; only plan strings and frame labels | the LLM may add text |
| Generator LLM call | **skipped** for a slide whose components all have a block | every slide |
| Slides with a component without a block | today's LLM path, whole slide | the LLM draws that component in its skeleton |
| Tested | R2: 88 slides, R3: dense slides with two-pass sizing | R3 Phase 0c: 4 hand-written skeletons only |
| Unknown before a paid run | how fallback slides sit beside code-drawn ones | whether the LLM writes tags correctly (wrong `ref`, odd variant, hand-builds the block anyway) |

**Assumptions behind recommending A first**
1. *The layout choices that matter are already in the plan.* The planner sets each
   component's kind and weight (hero / peer / supporting) and writes a `layout_hint`. The
   Phase 0b composer turns kinds and weights into a layout with fixed rules: order,
   table + chart side by side, KPI tiers, height by weight. Evidence: CHEFFIN and XTSY
   (§10c–10e) and the 88 R2 slides render without a generator call. Against: the
   composer **ignores the `layout_hint` text**. Saved hints say things like "cpc_table
   sits below *or beside*", and the composer doesn't read them.
2. *Tag compliance is the largest risk we cannot test for free* (§13 risk table, "found
   before building? no"). Route A doesn't have it. Route B needs a paid run before we
   know whether the design works at all.
3. *Fallback per slide is good enough to start.* R2: 56 / 88 slides (64%) have a block for
   every component. CHEFFIN 8 / 8, gj-h1 38 / 56, XTSY 10 / 24. The rest go through
   today's path unchanged. A timeline block alone moves 12 components (§13 R2).
4. *Skipping the generator call is a real gain.* It costs less and runs faster. A code
   slide has no compile errors from LLM XML, so it never enters the repair loop
   (R2: 88 / 88 compiled; the LLM versions of the same plans were 86 / 88).

**The main cost: the LLM loses layout freedom on code-drawn slides.** On 2026-09-10 the
user chose "the LLM free to generate any kind of slide". Archetypes and the enforced
layout patterns were removed then, because constraints added by code had caused overlap
and dead space. Route A goes back on that choice for covered slides, so it needs the
user's explicit agreement. Differences from 10 Sep:
- the 10 Sep regression came from code *contradicting* the LLM's layout (a swapped pattern
  plus a prescriptive example). Route A doesn't mix the two: on a slide, either code
  draws all of it or the LLM does;
- the fixed rules are measured against POM (two-pass sizing, §13 R3), not hand-written
  pixel budgets;
- the risk that remains is **sameness**: decks drawn by one composer may look templated.
  Not measured yet.

**Ways to give layout choice back to the LLM within route A, if sameness shows up**
(in order of cost):
1. More arrangements in the composer, chosen from content (free; code only).
2. A small structured field in the plan, e.g. `arrangement: stacked | side_by_side |
   hero_left | grid`, that the composer obeys. This is a one-enum planner prompt change,
   so it needs a paid check. Compliance risk is much smaller than for XML tags.
3. Route B: skeleton + tags, using the R3 slot code (`scripts/phase0b/expand.py`) as
   built.

**Recommendation (first proposal, superseded by 14.6):** A, behind a setting (`render_mode: llm | code_first`), per-slide
fallback to today's path. Add a free **variety metric** with the first block: distinct
layout signatures per deck (block kinds × arrangement), code-drawn vs the LLM decks of
the same plans. Move to 2 or B only if that metric or the user's review shows sameness.

### 14.2 The six decisions of §10, revisited for route A (rows 3, 5, 6 change under 14.6)

| # | Decision | Assumption | Evidence | Recommendation |
|---|---|---|---|---|
| 1 | Order vs the plan reviewer loop | render failures are the most visible problem; thin plans are a planner problem that blocks expose but don't cause | §1: broken words, invented cards, duplicates all happen after the planner. R2: broken words 32 → 2. **Against:** code draws exactly what the plan holds, so thin plans *look* thinner. gj-h1 "What Worked" rendered a near-empty body. Today the generator pads thin plans, partly with invented content (§1, §12) | **Blocks first**, but bring two small pieces of the loop forward into step 1: stop `slide_component_planner`'s silent `{}` fallback (re-ask instead), and report `SLIDE_SPARSE` (§10f). The full reviewer loop (`docs/plan-reviewer-loop.md`) follows |
| 2 | Builders: Python vs Jinja templates | the hard part is measuring, not markup | everything that fixed Phase 0b is measuring code: `fill_card_text`, `pin_h`, KPI glyph sizing, two-pass `fit.py`. A template can't measure. Style values already live in YAML (`style_packs.yaml`) | **Python builders, style in YAML** |
| 3 | Source of truth for repair / edit | in route A there is no node-level XML from the LLM | a code slide is a function of (plan, style pack); its compile failures are code bugs, caught by tests (R2: none) | **The plan.** Edits change the plan and the slide is re-drawn, with no LLM call: the review screen's Keep / Remove already edits the plan. Fallback slides keep today's XML repair / edit. Route B would reopen this |
| 4 | Label tier below 14 px | small mono labels read well and don't hurt legibility | Phase 0 (4 Oct): 10–12 px mono labels read well. Phase 0b uses 9–11 px. R4: PowerPoint draws them the same. **Against:** `house-style.yaml` `min_font: 14` and `FONT_TOO_SMALL` reject them, and nobody has judged them on a projector or a laptop at normal size | **Allow a `label` role at ≥ 10 px** (mono, uppercase, ≤ 4 words, never body text). Body stays ≥ 14 px, and `FONT_TOO_SMALL` exempts the role. Provisional until the user has looked at a projected slide |
| 5 | How much look the LLM controls | in route A, the LLM controls no look directly | one switch restyles a deck (§10d: CHEFFIN in studio, no other change). Per-component emphasis already comes from the plan's `design_hint` (inverted tile, highlighted row, bold phrase) | **One look per block per style pack**, plus the plan-driven switches above. No per-node variants for the LLM. Revisit with 14.1's variety metric. Provisional |
| 6 | `SlideHeader` + deck footer | a deck needs one frame; slide-to-slide header drift reads as amateur | §10c criterion 3: same frame on every slide, code yes, ours no. In route A the frame comes with the composer (label, headline, subtitle, footer with brand + n / N) | **In scope from step 1.** Open: fallback slides still have LLM-drawn headers, so a mixed deck shows two header styles. First fix (free): code draws the frame on fallback slides too and the LLM draws only the body. That's a generator prompt change, so it goes in the paid check |

### 14.3 Build order for route A (superseded by 14.6)

Each step is free unless marked. Unit-test baseline before each change (557 pass, 4
known failures as of 2026-10-05).

| Step | What | Accepted when |
|---|---|---|
| 0 | Prerequisites: subset font embedding in `pptx-post.js`; pipeline style switched to Inter + JetBrains Mono for code slides; shrink guard for words wider than their box (§13 R1) | embedded deck opens in PowerPoint without the fonts (as R4); pptx size growth small (target: ≤ 300 KB per deck, to be confirmed) |
| 1 | `src/compiler/compose/`: Phase 0b blocks + composer + two-pass sizing (`measure.mjs`, `fit.py`) moved from `scripts/phase0b/` into pipeline code with tests; setting `render_mode`; per-slide fallback; `SLIDE_OVERFULL` / `SLIDE_SPARSE` reported; silent empty-plan fallback removed; variety metric in eval | replay of the 8 R2 decks: same or better than §13 R3 (overlap ≤ 3, broken words ≤ 1, text check 0 extra words); fallback slides identical to today |
| 2 | Timeline block, then native `Chart` for line / doughnut / area (built in R3), flow, matrix | coverage ≥ 85% of slides fully code-drawn on the R2 decks |
| 3 | **Paid check (≈ $2):** `gate-deck-xtsy-qcomm` + `gate-deck-cheffin-full` × 2, `render_mode: code_first` vs `llm` | word breaks ↓, invented text 0, first-pass compile ≥ 96%, generator calls ↓; user's side-by-side review including sameness |
| 4 | Frame on fallback slides (14.2 #6); plan reviewer loop | per `docs/plan-reviewer-loop.md` |

### 14.3b Hold-out test (2026-10-05): new briefs, code frozen at `a866137`

The R2 / R3 numbers are in-sample: every renderer fix was made while looking at CHEFFIN,
XTSY and gj-h1 plans. So three briefs the renderer had never seen were run through the
normal pipeline on the test PC (`eval_run … --label holdout`, 1 repeat, $0.78, 17
slides): `deck-qbr-data` (SaaS QBR), `deck-product-launch-data` (API product launch),
`gate-deck-agency-takeover` (agency pitch, 6.8k-char brief). These plans are newer than
R2's: kickers, planned headlines, `card_grid`. Their plans were replayed through the
renderer **without any change to it** (`replay.py --fit`, studio_inter), and both sides
were scored the same way on the LibreOffice render (`fontcheck.py`, `check.py`).
Files: `output/holdout/` (gitignored), sheets `output/holdout/sheets/holdout-*.png`.

| 17 slides | LLM-drawn (pipeline today) | Code-drawn (same plans) |
|---|---|---|
| Renderer crashes / compile | — / 17 of 17 (94% first pass) | 0 / 17 of 17 |
| Components with a block · slides fully code-drawn | — | 50 / 55 (91%) · 12 / 17 (one of them has an empty plan) |
| Broken words (render) | 0 | 0 |
| Blank heading lines · KPI numbers wrapped | 4 · 1 | 0 · 0 |
| Slides with overlapping text | 1 (agency 2: headline over subtitle) | 2 (QBR 2: KPI note touches; agency 6: last line runs into the footer) |
| Words not in the plan | 15 + labels ("why it matters", "speaker notes"); launch 5 drawn from the brief because its plan was empty | 0 |
| Plan words missing | 15 (launch 6 timeline, text check reads it partly) | 1 (agency 2, "62.0" chart value) |

**New failures the in-sample decks never showed** (renderer, all fixable in code):
1. Ranked-bar colouring on a **time series**: the oldest quarter is drawn red as
   "worst" (QBR 3). Best / worst colour only fits a ranking, not a trend.
2. A card body with commas is **split into bullets** ("SKU / city / and inventory-aware
   …", agency 4; `_split_list`).
3. The replay's fix for pre-batch-A plans (headline taken from the title component) picks
   the **label as the headline** when the title component holds it ("GROWTH SYSTEM",
   agency 4). Replay code, but the same ambiguity exists in the plans.
4. Two-pass sizing left small deficits unreported (agency 2: 8 px at scale 0.72;
   agency 5: 5 px) and missed agency 6's overflow into the footer.
5. Known: duplicate chart title (agency 2); the brand is guessed from the first slide title
   ("CAMPAIGN-PURPOSE"); thin slides drawn as a small strip in empty space (QBR 5,
   launch 2).

**Planner problems both versions share** (blocks can't fix them):
- **Empty plan** (launch 5: `kpi_row` and caption `{}`). Code draws an empty slide. The
  LLM drew the KPIs from the brief, unchecked against any plan. This is the silent `{}`
  fallback (§5, 14.2 #1).
- Planner **instructions printed as content** ("Deepen the growth story by showing…", QBR 3;
  "Break down ARR by segment to show…", QBR 4). Speaker notes planned as a narrative
  (agency 2, 4, 5, 6). A card body that repeats its title (agency 4).
- Timeline (launch 6) has no block: an empty slide in the replay, LLM fallback in a build.

**Reading:** on brand-new plans the renderer held up mechanically: no crash, 0 broken
words, 0 invented words, fewer blank headings and KPI wraps. Overlap was slightly worse
(2 vs 1). It also showed 4 failure types the in-sample decks never had, so in-sample
results overstate readiness. Per slide (author's read; the user judges): code clearly
better on agency 1 (the LLM fills whole table rows red / green), equal on data slides (QBR 2
and 4; launch 3 and 4; agency 3 and 5), worse where the plan is thin or empty (QBR 5;
launch 2, 5 and 6). The biggest visible gaps come from the plan, not the renderer.

### 14.5 Outside evidence: what the POM author and other tools do (2026-10-05)

**POM's own guidance** (pom kit docs, read 2026-10-05):
- POM XML is the single source of truth. Every authoring surface (agent skills, Markdown
  `pom-md`, JSX `pom-jsx`, the visual editor) produces it, and preview, validation and
  rendering all work from it.
- The **recommended** workflow is "AI agent + pom CLI". An agent with the `pom-slide`
  skill writes and edits the XML, validates it, renders it for review, and keeps a live
  preview open while the user asks for changes. That is the LLM writing POM XML
  **in a loop** (write → validate → render → look → fix), not in one call.
- Applications and custom pipelines (ours) call `buildPptx()` with the XML.
- `pom-jsx` (0.8.1, matches POM 10.3.0; README + `src/types.ts` read 2026-10-05) is a typed
  JSX/TSX way for **developers** to write POM XML: every node is a component with
  hand-written prop types ("attribute typos … surface at compile time"), and "custom
  components" are plain functions returning fixed POM nodes (README example:
  `TwoColumnSlide({title, left, right})`, a whole-slide layout template). It has **no
  measuring, fitting or adapting** logic, no mention of LLMs, and is not described as
  something to mix with LLM-written XML: the README calls agent skills, pom-jsx, pom-md and
  the editor "alternative authoring surfaces", each producing XML on its own.
  *Correction (2026-10-05): an earlier version of this section said the author provides
  code components "alongside LLM-written XML". That was overstated.* What pom-jsx does show:
  the author holds that reusable components should expand to **plain POM** (as our blocks
  do). Our blocks differ in the part that did the work in R2 / R3: they measure and adapt
  (`fill_card_text`, `pin_h`, two-pass `fit.py`).
- The `pom-slide` skill (read 2026-10-05) builds to validate, renders to PNG, checks the
  image ("no overflow/overlap, adequate spacing, aligned edges, visual hierarchy…") and
  repeats up to 3 times; it tells the agent to reuse a "common header block" across slides.
- Usable now: pom-jsx's `types.ts` is a readable list of each node's accepted attributes
  (e.g. `Td` has no `borderLeft`, matching our `ITEM_BORDER_REMOVED` finding). Step 1 checks
  every attribute a block writes against it plus `attributes.yaml` (POM's compile stays the
  final word; the types are hand-written and may lag). Writing blocks in TSX: not worth it
  (measuring lives in Python / Node; blocks already compile 88 / 88 + 17 / 17).

So the author's model is: XML as the shared format, components that expand to plain POM,
and an AI that writes XML **checks the render and iterates** (in an interactive agent
session, not a batch pipeline). The author does **not** address measured / adapting
components or mixing LLM layout with code components through slots; those are ours. Our
generator writes XML in one shot; repair only reacts to compile errors and one critic round.

**Research on LLM slide generation:**
- **AutoPresent** (CVPR 2025): the same 8B model writing slides through a high-level
  function library (SlidesLib) instead of raw python-pptx: code that runs 2.1% → 54.4%,
  score 1.3 → 33.5 ("observable gains … by at most 34.0 points"). Self-refinement helps a
  little (58.0 → 59.5 → 60.1); "the first iteration usually gives the biggest performance
  improvement". Human slides still score clearly higher.
- **PPTAgent** (EMNLP 2025): the LLM picks reference slide layouts and edits them with
  actions instead of drawing from scratch; beats end-to-end generation on content, design
  and coherence (PPTEval). Closest analogue to "LLM decides structure, something fixed
  carries the detail", but not our slot contract.

**Other tools** (public material only; internals mostly undisclosed):

| Tool | Approach | Trade-off |
|---|---|---|
| Genspark (its own traces, §10b, Genspark notes 2026-10-05) | the LLM writes HTML/CSS per slide (absolute positions) from a deck-level token theme and reference patterns, then a layout checker (clipping, overflow, contrast) plus screenshots, then edits until 0 errors | varied, polished; many LLM calls per slide; still invented content in our check (§12) |
| Gamma | described as "large language models and layout logic": the LLM produces content as cards, the engine lays them out ("layouts adjust automatically") | consistent, editable; own format, details not public |
| Beautiful.ai | "smart templates": a design-rules engine reflows spacing, alignment and font size as content changes | always tidy; reviewers note decks converge on one house style |
| Canva, SlidesAI | AI text into pre-built templates | fast, on-brand; same sameness |
| Newer HTML-generation tools | the LLM writes each slide's code from a theme spec and a **component kit** (cards, callouts, tables, column splits) | the middle ground |

Sources: [pom kit docs](https://github.com/hirokisakabe/pom),
[Gamma: card-based layouts](https://gamma.app/explore/content/guides/ai-presentation-tool-card-based-layouts),
[Gamma explained (SketchBubble)](https://www.sketchbubble.com/blog/gamma-explained-a-comprehensive-deep-dive-into-the-ai-powered-presentation-platform/),
[HTML vs image slide generation (Tosea)](https://tosea.ai/blog/ai-slides-html-vs-image-generation-guide-2026),
[LLMs vs layout engines (Perceptis)](https://perceptis.ai/blog/llms-vs-layout-engines-how-ai-presentation-tools-work),
[Alai vs Beautiful.ai](https://getalai.com/blog/alai-vs-beautiful-ai),
[pom-jsx](https://github.com/hirokisakabe/pom/tree/main/packages/pom-jsx),
[pom-slide skill](https://github.com/hirokisakabe/pom/tree/main/skills/pom-slide),
[AutoPresent (arXiv 2501.00912)](https://arxiv.org/abs/2501.00912),
[PPTAgent (arXiv 2501.03936)](https://arxiv.org/abs/2501.03936). Gamma / Beautiful.ai
descriptions come from marketing and review pages, not engineering documentation.

**Where we stand against these:**
- The pure composer (route A) is the **Beautiful.ai model**: a rules engine, tidy and
  correct, converging on a house style. The hold-out showed exactly that: correct,
  samey, and empty when the plan is thin.
- Today's generator is a **weak version of the Genspark / POM-author model**: the LLM
  writes the code, but without the render-and-fix loop that makes that model work.
- The middle pattern (LLM layout + component kit + a checking loop) is consistent with
  POM's tooling and what newer tools use; the slot contract between the two is our own.

**Evidence per part of 14.6** (what is proven, what is not):

| Part | Our evidence | Outside evidence | Confidence |
|---|---|---|---|
| Code draws the inside of components | R2: broken words 32 → 2, compile 88 / 88 vs 86 / 88; hold-out (14.3b): 0 broken, 0 invented, 0 crashes on unseen briefs | AutoPresent library vs raw code (2.1% → 54.4% runs); pom-jsx components expand to plain POM; `pom-slide` "common header block" | **strong** |
| LLM writes the layout as POM XML | today's pipeline | POM README: agent skills "recommended", XML "designed for LLM code generation" | **strong** |
| Checking loop after drawing | none (not built) | `pom-slide`: render → check → fix, ≤ 3 rounds; AutoPresent: small gains, most in round 1 | **moderate** — helps, small; ≤ 2 rounds |
| Slots (LLM leaves `slot-<id>`, code fills) | 4 hand-written skeletons (Phase 0c), all clean | none direct; PPTAgent is the nearest analogue | **weak — the main unknown** |
| Planner fixes | hold-out: empty plans, instruction text, thin slides | — | **no-regret** |

**Kill criteria, set before the slot test** (14.6 step 1a; on briefs not used for tuning):
- slot compliance ≥ 90% first try (right `ref`, none missing / duplicated, no hand-built block);
- 0 invented words inside blocks;
- broken words and overlapping text ≤ today's LLM path on the same plans;
- the user prefers the slot version on most slides side by side;
- layout variety (distinct layout signatures per deck) not below LLM-only.
Fail → keep blocks, drop slots: the composer with a planner-chosen `arrangement` field
(14.1 option 2). After launch, track block fixes needed per new brief family (must fall
toward 0, or we are back to rule-chasing), fallback rate, and checking-loop repairs per slide.

### 14.6 Updated recommendation (2026-10-05): LLM layout, code components, a checking loop

Replaces 14.1's "route A first". Reasons:
- **Composer rules don't scale to new briefs** (14.3b). Rules for the *inside* of a
  component scale: one kind's content shape is bounded. Rules for the *slide layout* don't:
  kinds × counts × weights × text lengths combine without limit. Fixed rules give sameness
  plus a stream of uncovered cases (2 of the 4 hold-out failures were layout / sizing).
- **Editing and the visual critic stay simple with LLM-written layout.** On a pure
  composer slide, layout edits and critic fixes would need a pre-built option set, plus a
  "detach" escape to XML for anything else. With LLM layout, layout edits and visual
  repair stay XML edits (today's path). Only edits inside a block go through the plan.
- **It matches the POM author's recommended model and the newer tools** (14.5).

**The design:**
1. **Planner fixes first** (they help every route; the hold-out's biggest visible gaps):
   re-ask instead of the silent `{}` plan; never print planner instructions or speaker
   notes as slide text; `SLIDE_SPARSE` for thin slides; card bodies that repeat titles
   rejected; **duplicate items on one slide** (two components whose item labels overlap
   ≥ 70%, e.g. phase cards + chevrons of the same items, 1 Oct decks slide 4: keep the
   hero, report the other; moved forward from the reviewer loop, 2026-10-05). These are
   the in-branch part of planner item 4 in `docs/planner-redesign-research.md` §9.1 and
   checks C14–C17 of `docs/plan-reviewer-loop.md`; both docs carry the 2026-10-05
   alignment (§9.2 and the status note). Batch B timing (planners 3, 4) is open there as
   Q15.
2. **The generator LLM keeps writing the slide's POM XML** (layout, bands, free text,
   emphasis), with **slots for blocks**: `<VStack id="slot-<component_id>" …/>` or the §2
   tag form.
3. **Code blocks draw inside the slots** (component kit): KPI row (hero, tiers), table,
   card grid (grid / steps), chart (bar; line / doughnut / area as native `<Chart>`),
   bullets, process steps, linear flow, timeline, caption, narrative (timeline, caption
   and linear flow added in 14.7); `SlideHeader` in step 1. **No block yet:** 2×2 matrix,
   pyramid, tree, layer, group, branching flow, so the LLM draws those as today. Coverage
   on saved plans is 98% of components (368 / 374, 105 slides, 14.7), but pyramid and tree
   never occur there; the dense case asks for all six. Content comes from the plan by
   `ref`, sized to the slot by two-pass measurement (`expand.py`, `fit.py`, built in R3),
   the 4 hold-out failures fixed and unit-tested.

   **What "the LLM can't invent or drop block text" covers** (2026-10-05): the text
   *inside* a block. Measured on the 105 slides: 0 words not in the plan; 6 plan words
   missing, all reported (3 = the series name of a chart left without data, 2 numbers on
   an over-full slide, 1 chart value). It does **not** cover (a) an empty plan: the block
   draws nothing, so the step 0 re-ask is needed (the XTSY slide 7 case needs both fixes);
   (b) a plan that itself invents: planner checks (`written_lines.py`, planner 4, §12);
   (c) free text the LLM writes beside a block: the three-way text check of §12, not
   built; (d) an LLM that hand-builds the block instead of leaving a slot: counted
   (`node_bypassed`), measured in 1a.
4. **A checking loop after the slide is drawn**, the part we lack: measured feedback from
   POM's layout and the real fonts (squashed boxes, words wider than their box, overflow
   into the footer, broken words on the render), stated precisely ("the KPI tile is 24 px
   short"). Fixes come from code where the cause is a block (step type down, split rows)
   and from the LLM where it is layout, for ≤ 2 rounds, keeping the best version.
5. **Plan = source of truth for content; XML = source of truth for layout.** Content edits
   change the plan and re-expand the blocks. Layout and look edits edit the XML (today's
   edit service), with blocks re-expanded after each edit.
6. **The composer stays** as the research and test tool (`compose_deck.py`), and as a
   fallback for a slide whose LLM skeleton fails twice.

**Changes to 14.2:**

| # | Under 14.6 |
|---|---|
| 3 Source of truth | plan for block content, node-level XML (skeleton + slots) for layout; repair and edit work on the skeleton, blocks re-expanded after every change |
| 5 Look the LLM controls | the LLM picks the layout and may pick a block variant per slot (3–4 per block, §10 #5 as first proposed); style pack for everything else |
| 6 Header + footer | the frame becomes a block the skeleton places (`SlideHeader`), so every slide shares it, including slides with no other block |
| 1, 2, 4 | unchanged (blocks after planner fixes; Python builders; label role ≥ 10 px, provisional) |

**Build order:**

| Step | What | Accepted when | API |
|---|---|---|---|
| 0 | Planner fixes (item 1); subset font embedding in `pptx-post.js`; shrink guard. **Step-end run** (2026-10-05): full pipeline, × 1, on every step 3 case (`deck-qbr-data`, `deck-product-launch-data`, `gate-deck-agency-takeover`, `gate-deck-xtsy-qcomm`, `gate-deck-cheffin-full`, `gate-deck-all-nodes-dense`) with `--compose`, **run folders kept** (bundles lack `slides.json`). Its plans are reused by 1a and step 3; its `llm.pptx` decks are step 3's `off` arm. **Usage logging** (2026-10-05): every entry in `run-manifest.json` `steps` names its step (elicitor, outline_planner, slide_component_planner, plan_reviewer, generator, repairer, …, and later the checking loop) and slide index, and carries `tokens_reasoning` (already read in `src/utils/llm_client.py` but dropped before the manifest) and `tokens_cached` (from `prompt_tokens_details.cached_tokens`; not read today). Today steps are told apart only by model and order | no `{}` components, no instruction / notes text and no duplicate items on a slide in any plan; every manifest step named, with reasoning and cached tokens | ≈ $1.8 |
| 1a | **Slot test first** (added 2026-10-05): generator-only run with a slot prompt on step 0's saved plans (hold-out + XTSY, ≈ 20 slides), expanded with `scripts/phase0b/expand.py`. Builds the **from-plans runner** (≈ 30 lines: loads a run's `slides.json` into `state["slide_plans"]`; the graph already skips planning then, `route_after_start`, as `/generate-from-plan` does; Python 3.11-safe). Records the real cost per slide with the slot prompt; token method below | the kill criteria in 14.5; tokens per slide reported against step 0's generator calls on the same plans | ≈ $0.5 |
| 1 | Only if 1a passes: blocks moved into `src/compiler/blocks/` with tests; hold-out failures fixed; slot expansion in the validator behind a setting (`blocks: off \| slots`); `SlideHeader` block; every attribute a block writes checked against pom-jsx `types.ts` + `attributes.yaml` | all R2 + hold-out plans expand with 0 broken words, 0 extra words, overlap ≤ R3; unit tests | no |
| 2 | Generator prompt: skeleton + slots for kinds with a block; checking loop (item 4) | replay on saved skeletons; unit tests | no |
| 3 | **Paid check (≈ $1.2–1.5, revised 2026-10-05):** the from-plans runner on step 0's saved plans of all six cases (≈ 40 slides), `blocks: slots` only, × 1. The `off` arm is step 0's `llm.pptx` on the same plans (no extra cost), so the two arms differ only by the slot route. Before paying: a dry run with a scripted LLM replaying 1a's skeletons through the real pipeline, so the paid run is not repeated for a pipeline bug. Exact cost re-estimated from 1a's per-slide figure before asking | slot compliance (wrong / missing / duplicate refs, hand-built blocks), broken words ↓, invented text 0, user's side-by-side incl. variety | yes |
| 4 | Blocks still missing: 2×2 matrix, pyramid, tree, layer, branching flow (timeline and linear flow are done in Phase 0b, 14.7, and move in with step 1); plan reviewer loop | coverage, per `docs/plan-reviewer-loop.md` | step-end |

**LLM calls and tokens: baseline, expected change, method (2026-10-05).**

Baseline, from the hold-out run manifests (`output/holdout/inputs/*/run-manifest.json`, 17
slides, $0.78; product-launch deck, 6 slides, $0.235):

| Call | Model | Calls | In / call | Out / call | Share of cost |
|---|---|---|---|---|---|
| elicitor | gpt-4.1 | 1 | ~1.6k | ~60 | 2% |
| outline planner | gpt-5-mini | 1 | ~3.6k | ~5k (incl. reasoning) | 5% |
| slide component planner | gpt-5-mini | 1 / slide | ~11.4k | 1–6k | 22% |
| plan reviewer | gpt-5-mini | 1 | ~2.3k | ~2.4k | 2% |
| **generator** | gpt-4.1 | 1 / slide | **9–14k** | 0.1–2.4k (the slide XML) | **~69%** |
| repairs | gpt-4.1 | 0–2 / deck | 2–10k | ~1k | varies |

The generator's **input** (~12k ≈ $0.024 per slide) is the largest single cost. Generator
calls were identified by their output matching the saved slide XML token count.

Expected change (estimates until 1a / step 3 measure them):

| Change | Calls | Tokens |
|---|---|---|
| step 0 empty-plan re-ask | +1 planner call only when a plan fails | ≈ $0.009 per re-ask |
| planner 4 checks (batch B) | +≤ 1 re-ask per flagged slide (Test 1: 30–40% of slides) | ≈ +$0.003 / slide on average |
| generator, kinds with a block | unchanged (1 / slide) | **input down**: the kind's recipe (kpi_row 614, card_grid 989, card_steps 649, card_matrix 798, hero_stat 551, table_card 424, timeline 264, chart_card 245 tokens, o200k) and its data become one slot line; **output down**: no card / table / KPI XML; small fixed rise for the slot rules in the system prompt |
| compile repairs | likely down (code-drawn blocks compiled 88 / 88 vs 86 / 88) | fewer 2–10k repair calls |
| checking loop (step 2) | +0–2 per slide with a *layout* issue; block issues fixed by code | ≈ $0.02–0.025 per round |
| content edits in the UI | down: plan edit + re-draw, no LLM call | — |
| reviewer loop (step 4) | +1 checklist per deck + re-plans | `plan-reviewer-loop.md` §8 (to re-estimate for gpt-5-mini) |

Rough net per 6-slide deck (today ≈ $0.24–0.33): generator ≈ −$0.06, re-asks ≈ +$0.02,
checking loop ≈ +$0.05 if one slide in three needs a round, repairs slightly down:
**about flat (± 20%) — more calls, smaller generator calls**, before the step 4 reviewer.

Method:
1. **Baseline:** per-call `tokens_in` / `tokens_out` / `cost` from `run-manifest.json`; from
   step 0 on, with step names, reasoning and cached tokens (step 0 logging item).
2. **Free estimate before paying (step 2):** render the generator prompt for step 0's saved
   plans in both modes (recipes + data vs slot lines) and count with `tiktoken`
   (`o200k_base`): the exact input change, no API call.
3. **1a:** generator tokens per slide with the slot prompt vs step 0's generator calls on the
   same plans (like-for-like); used to re-estimate step 3 before asking.
4. **Step 3:** per deck and per slide, slots vs off on identical plans: calls per slide,
   tokens in / out / reasoning / cached by step, $ per slide; checking-loop rounds,
   re-asks and repairs counted separately so any increase is traceable.

**Paid runs, total (2026-10-05):** step 0 ≈ $1.8 + 1a ≈ $0.5 + step 3 ≈ $1.2–1.5 ≈ **$3.5–3.8**
(was ≈ $3.6–4.6), with like-for-like arms in step 3. A failed 1a stops at ≈ $2.3. Per-slide
estimates come from the 2026-10-05 hold-out run ($0.78 / 17 slides, gpt-5-mini planners).
Precondition for reusing step 0's decks as the `off` arm: step 2's prompt and loop changes
apply only under `blocks: slots`, so `off` stays the step 0 path.

**Main risk now:** whether the LLM writes slots correctly (step 3), the same unknown as
route B had. Fallback if it doesn't: the composer with a planner-chosen `arrangement`
field (14.1 option 2).

### 14.7 Caption, linear-flow and timeline blocks (2026-10-05)

The two easy fallback kinds from 14.3b, built in `scripts/phase0b/` (composer + slot
expander):
- **Linear flow:** a `flow` whose plan holds only `flow_steps` (2–8 steps, every saved
  flow so far) is drawn by the process-steps block (`render.linear_flow`). A flow with
  nodes / connections / branches stays a fallback.
- **Caption on a content slide:** the saved captions were three different things, so the
  rule follows the planner's own weight. A `minor` caption is a source / footnote line
  (11 px, muted) above the footer, with its height taken out of the body budget. A heavier
  caption (`supporting`; in saved plans these were full-sentence insights) becomes an
  insight line in the body. Captions that are empty or that repeat the slide's kicker
  or headline ("SEGMENT BREAKDOWN") are skipped. Before the weight rule, two insights
  came out at 11 px (gj-h1 `5a9e2d` slide 11).

Replay of the 8 R2 decks + 3 hold-out decks (105 slides, `--fit`, scored as before;
`output/blocks3/`, sheets `output/blocks2/sheets/caption-flow-*.png`):

| 105 slides | before | after |
|---|---|---|
| Components with a block | 89% (R2) / 91% (hold-out) | **95%** (355 / 374) |
| Slides fully code-drawn | 76 | **86** (hold-out 12 → 16 of 17) |
| Broken words · KPI wraps · blank headings | 1 · 0 · 0 | 1 · 0 · 0 |
| Slides with overlapping text | 5 | 5 (the same slides; none new) |
| Plan words missing · words not in plan | 6 · 0 | 6 · 0 |

Still a fallback after this step: timeline (13), matrix (3), layer (2) and group (1), the
last two with empty plans.

**Timeline block** (same day, `render.timeline_block`). Every saved timeline is
`timeline_items` of `{date, label}`, 3–6 items, horizontal, in two regimes: short labels
(1–5 words: launch milestones, XTSY time-of-day occasions) and long ones (9–49 words,
mostly "Head — detail"). Drawn as one column per item: the date (mono label) above a
continuous rail (dot + line to the next column), then
- short labels: the label under its dot, sized to the column (≤ 32 px); the block is capped
  at 2× its natural height so a thin slide isn't inflated;
- long labels: a card under the dot; a label written "Head — detail" / "Head—detail" (em
  dash) / "Head – detail" / "Head: detail" (head ≤ 6 words) splits at the planner's own
  dash into a bold head and the detail; nothing is reworded. An unspaced en dash is a range
  ("6–11 AM"), not a split. Detail type fills the card (≤ 24 px), heads ≥ 1.25× the detail.
  Line counts for the height budget are conservative (97% width, never fewer than POM's),
  because the strict "unambiguous breaks" rule rejected every size for 40-word texts
  (first version: 11 px detail in near-empty cards).
- the item a design hint calls "inverted" gets a dark card.

| 105 slides | after captions + flow | after timeline |
|---|---|---|
| Components with a block | 95% | **98%** (368 / 374) |
| Slides with overlapping text | 5 | **4** (XTSY-3 slide 2, which has a timeline, no longer overlaps) |
| Broken words · KPI wraps · blank headings | 1 · 0 · 0 | 1 · 0 · 0 |
| `SLIDE_OVERFULL` | 1 | 2 (+ gj-h1 `bf396b` 13: 6-item timeline + 6-row table + narrative, 15 px, reported not squashed) |
| Plan words missing · not in plan | 6 · 0 | 6 · 0 |

All 13 timeline slides, LLM-drawn vs code-drawn (`output/blocks6/sheets/timeline-*.png`): the
LLM versions show text spilling out of the timeline (`69af33` 9), literal `<B>` tags
(`bf396b` 9) and labels drawn over the detail text (the three XTSY roadmaps); the code
versions are legible and fill their cards. Weak spots: a short-label timeline on a slide
with nothing else (launch 6) sits in empty space (thin plan); dates are small mono labels.
Left as fallbacks: matrix (3) and layer / group (3, empty plans). Launch slide 5 counts as code-drawn but stays empty: its whole plan is `{}`
(planner fix).

### 14.4 What the user decides

1. **The 14.6 design** (LLM layout + code blocks in slots + a checking loop, planner fixes
   first), or the first proposal (14.1, composer first).
2. The 14.2 rows as changed in 14.6. The research supports #2; #1 changed with the hold-out
   (planner fixes first); #3, #5, #6 follow from 14.6; #4 needs the user's judgement.
3. Whether `gate-deck-all-nodes-dense` gets a paid planner run before step 1, or
   the gj-h1 dense plans keep standing in (§13 R3 "not covered"). Cost to be estimated
   before asking.
4. The long-run comparison on the test PC (`compose_deck.py`, LLM vs composer on the same
   runs) continues to feed this. It measures the composer's ceiling, not 14.6's.

## 11. Risks

- **Templated sameness** (why archetypes were removed 2026-09-10): nodes cover card
  internals only; layout, weights, variants and emphasis stay with the LLM. Measure
  variety on the renders.
- **Owning a small DSL:** cap ≈ 10 nodes, versioned spec, every node render-tested.
- **The LLM ignores nodes:** raw POM still compiles; `node_bypassed` shows it in evals;
  replaced recipes are removed so the node is the easy path.
- **Two-level debugging:** keep node-level and expanded XML side by side in every run.
