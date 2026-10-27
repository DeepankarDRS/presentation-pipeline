# Components and variants to add: research (2026-10-24)

Research only. No code changed, no paid run. The question: which components (content shapes) and
variants should we add so the pipeline makes better decks **for our use case**? Our use case means
agency performance-marketing audits and pitches (CHEFFIN, agency takeover, XTSY), QBRs, launch decks
and sales reviews, in Indian and US formats.

How this fits the 21 Oct review (`docs/look-and-feel-review-2026-10-21.md`, "More variants?"): that review
found that **more looks for KPI tiles and cards** do not win blind marks, and that **charts and
diagrams** are where the real gaps are. This doc follows that split. It is mostly about missing
*content shapes* (a target beside an actual, a funnel with conversion rates, a hub, a before → after
pair), plus chart options. It proposes no new KPI-tile or card looks.

Evidence used (all local and free):
- The six real deck briefs: `gate-deck-cheffin-full`, `gate-deck-agency-takeover`, `gate-deck-xtsy-qcomm`,
  `deck-qbr-data`, `deck-product-launch-data`, `deck-sales-data`, plus `deck-board-update`.
- The saved corpus: **496 unique slide plans** from every `output/**/slides.json`. For each one I counted
  component kinds, chart types and the planner's `design_hint` wording.
- The component knowledge: `block-variants.yaml`, `capacity.yaml`, `nodes.yaml`, `recipes.yaml`, and POM 10.3.0's
  chart renderer (`node_modules/@hirokisakabe/pom/dist/renderPptx/nodes/chart.js`).
- External references, listed in §3 and under Sources.

---

## 1. What we have today

| Plan kind | Draws as | Variants today |
|---|---|---|
| `kpi_row` | element refs (default), KpiGrid tiles (opt-in) | plain · filled · toned · bar · dot · inverted · hero · bare · divided |
| `card_grid` (grid / matrix / steps) | CardGrid (opt-in), else the LLM | outline · filled · featured · numerals · toned · accent_top; steps: cards · rail · columns |
| `table` | native Table | plain · zebra · highlight_row · dark_header |
| `chart` | native Chart (bar, line, pie, doughnut, area, radar) | native · labelled* · horizontal* (*designed, not built) |
| `bullet_list` | Ul | plain · icon · tiles · columns |
| `narrative` / callout | Text / Callout | rule · tinted · dark · quote |
| `timeline` | native Timeline | rail · vertical · cards · columns |
| `process_arrow`, `flow` | native | chevrons / boxes · numbered · alternating · step_cards |
| `matrix`, `pyramid`, `tree` | native | one look each (a pyramid pointing down is our only funnel) |
| `layer` | the LLM draws freely with `<Layer>` + Shape / Line / Arrow | — (hub-and-spoke exists only as a recipe) |

**What POM can't do (this sets the build cost):**
- `<Chart>` takes 6 types. The renderer passes no data labels, no bar direction, no stacking, no
  overlap/gap, no reference line, no combo chart, no scatter, no funnel and no waterfall. It colours
  individual points only for pie / doughnut and single-series bars. Every one of these options exists
  in the PPTX chart XML, so `pptx-post.js` could add them after compile. The chart then stays native
  and editable. Today `pptx-post.js` doesn't touch chart XML.
- `<Svg>` is rasterised to PNG. That's fine for small glyphs (Harvey balls, status icons) but
  not for anything with text.
- `<Layer>` + Shape / Line / Arrow can draw anything with absolute coordinates. That's how a code-drawn
  diagram would work.

---

## 2. What our decks actually ask for

### 2.1 Slide by slide: the six real briefs

The content shape each slide needs → what we use today → fit (✅ good, 🟡 approximated, ❌ missing).

| Brief · slide | Content shape it needs | Today | Fit |
|---|---|---|---|
| CHEFFIN 2 · Exec summary | 5 headline numbers + one callout | kpi_row + callout | ✅ |
| CHEFFIN 3 · Core economics | **actual CPC vs allowable CPC per platform, gap ×2.9 / ×3.1**; formula *Allowable CPC = AOV × CVR* | table + clustered bar, both coloured by hint | 🟡 (no target marker, no gap label, formula not shown) |
| CHEFFIN 5 · Platform snapshot | 7 metric / value pairs | Metric\|Value table → KPI tiers | ✅ |
| CHEFFIN 6 · Ad type & match type | **spend share vs sales share** per ad type + ROAS; 6 match-type ROAS values ranked | table + bar | 🟡 (paired share bars and a ranked labelled bar would read faster) |
| Agency 1 · Campaign diagnosis | ROAS per campaign class, budget vs return | table / bar | 🟡 (ranked horizontal bars with value labels, one highlighted) |
| Agency 2 · Keyword & city leakage | match-type table; **lists of short terms** (winners / weak terms / cities to review) | table + bullets | 🟡 (term lists → chips) |
| Agency 3 · Cross-platform gaps | **5 gaps × 2 platforms + a fix column** | table, columns shaded by hint | 🟡 (a real side-by-side compare component) |
| Agency 4 · Growth system | 6 pillars | card_grid | ✅ |
| Agency 5 · 30/60/90 roadmap | 3 phases × **2 platform lanes** of actions | card_grid steps | 🟡 (lanes lost: needs a swimlane roadmap) |
| Agency 6 · Close + data needed | closing statement; data-needed checklist | callout + bullets | ✅ / 🟡 |
| XTSY 1 · Ecosystem | **hub: XTSY engine centre, 3 platforms around it** | `layer` (LLM free-draw) | ❌ |
| XTSY 2 · Occasions across the day | 6 occasions on a day strip | card_grid | 🟡 |
| XTSY 3 · Opportunity matrix | **4 rows × 3 platforms grid** of opportunity areas | card_grid matrix / table | 🟡 (heat / Harvey grid) |
| XTSY 4 · 4-phase framework | 4 phases with bullets + progression line | card_grid steps | ✅ |
| XTSY 5 · Control tower | 2 grouped capability panels (TRACKING / INSIGHTS) around a centre | `layer` | ❌ (grouped panels / hub) |
| XTSY 6 · Automation engine | **inputs → engine → 4 levers → outcome** (fan-out / fan-in) | flow (linear only) | 🟡 (the flow can't branch) |
| XTSY 7 · Expected impact | 7 metrics with **↑ arrows, no numbers** | `layer` / card_grid | ❌ (directional indicator list) |
| XTSY 8 · 90-day plan | 3 months × 4 actions | card_grid steps / timeline | ✅ |
| QBR · KPIs, revenue trend, segments | 4 KPIs with deltas; 6-quarter bar; segment table | kpi_row, chart, table | ✅ (chart labels missing) |
| QBR · Q4 priorities | 3 priorities, each **against a target** ($4M+, 10 months) | card_grid | 🟡 |
| Launch · Beta results | **4 metrics as before → after** (2.3 h → 15 min, −89%) | kpi_row with the "after" value; the "before" goes in a note or is dropped | 🟡 (one run dropped the before values) |
| Launch · Pipeline / timeline | 5 steps; 4 dated milestones | flow / process, timeline | ✅ |
| Sales · Pipeline by stage | **funnel: 5 stages, $ and deal count, conversion between stages** | pyramid down / bar | 🟡 (no values or conversion rates on the pyramid) |
| Sales · Win-rate trend | 3 actual quarters + **Q4 target 40%** | line / bar | 🟡 (no target line or marker) |
| Sales · Deals at risk | 5 rows: name, $, stage, **risk status** | table | 🟡 (status chips / RAG) |
| Board · P&L | P&L rows × 2 quarters + **QoQ variance** | table | 🟡 (variance colouring; a bridge is the consulting norm) |
| Board · Dividers, asks | section dividers; 3 asks | blueprint, card_grid | ✅ |

Of these 27 rows (slides grouped where a brief repeats a shape), 9 are ✅, 15 🟡 and 3 ❌. **The 🟡 and ❌
rows group into a small number of missing shapes**, and the same ones repeat across briefs: target vs actual, before → after, funnel, side-by-side
compare, hub / engine, lanes on a roadmap, status / direction glyphs, labelled ranked bars.

### 2.2 The saved corpus: what the planner keeps asking for

496 unique slide plans:

| Kind | Count | | Chart type | Count |
|---|---|---|---|---|
| narrative | 287 | | bar | 59 |
| bullet_list | 191 | | line | 9 |
| table | 172 | | doughnut | 8 |
| kpi_row | 138 | | area | 5 |
| card_grid | 131 | | | |
| chart | 83 | | | |
| process_arrow / timeline | 28 / 28 | | | |
| **layer** (free-draw) | **20** | | | |
| flow / matrix / tree / pyramid | 16 / 9 / 7 / 6 | | | |

Words in the planner's `design_hint`s that describe visuals we don't have, worked around with colour on
a table, tile or card instead:

| Signal in the hint | Hints | What the planner was trying to draw |
|---|---|---|
| target / allowable | 54 | "colour CPC above allowable in negative", "Actual CPC series negative, Allowable muted" → **a target-vs-actual visual** |
| progress / gradient left → right | 39 | "gradient from Visibility to Profitability", "muted Phase 1 → strong Phase 4" → **progression** (mostly covered by steps) |
| before → after | 30 | "before → after callout under each KPI tile (2.3 hrs/wk → 15 min/wk)" → **a before → after pair** |
| engine | 28 | "emphasize the Decision Engine node; colour the optimization nodes" → **a hub / engine with branches** |
| `layer` uses | 20 | ecosystem hub (×8), control-tower panel, upward-arrow impact, stacked bands → **hub, grouped panels, indicator list** |
| heat / status | 17 | "heatmap colour scale across the city cards", "status dot beside each label" → **heat grid, status glyphs** |
| horizontal | 19 | horizontal bars for long category names → **horizontal labelled bars** |

**Reading:** the planner already knows the right visual (it writes "actual vs allowable", "heatmap",
"engine node", "before → after"). The generator has no component for it, so the hint turns into
colouring. That is cheaper evidence than any external catalogue: these are the shapes our own planner
reaches for on our own briefs.

---

## 3. External reference sets (what "good" includes)

| Source | What it adds to our picture |
|---|---|
| **FT Visual Vocabulary** (9 families: deviation, correlation, ranking, distribution, change over time, magnitude, part-to-whole, flow, spatial; 70+ charts) | Our coverage: magnitude / change over time ✅ (bar, line, area); part-to-whole 🟡 (pie / doughnut only, no stacked or 100% bars); ranking 🟡 (no horizontal or labelled bars); **deviation ❌** (target vs actual, variance); **flow ❌** (proper funnel, waterfall); correlation / distribution / spatial ❌ (rare in our briefs, see §5). |
| **think-cell** (the chart add-in used at MBB firms and banks; 40+ chart types) | The consulting chart set is: **waterfall**, Mekko, **Gantt**, stacked / clustered / **100%** bars, **combo bar + line**, butterfly / tornado (a stacked-bar variant), scatter / bubble. Most of these are bar-chart options plus waterfall and Gantt. |
| **Consulting slide structures** (Deckary, SlideScience, SlideUpLift) | SCR executive summary (Resolution about 60–70% of the content; bold claims you can skim, evidence under them); **status slide** (on track? what changed? what's next?); **Harvey balls** + RAG for ratings; comparison tables. |
| **Bullet chart** (Stephen Few, 2005; IBCS variant) | The standard compact **target-vs-actual** visual: actual bar + target tick (+ optional bands). Rows stack on one slide. The IBCS form normalises each target to 100% so mixed units sit on one scale. Without meaningful bands, use a bar with a reference line. |
| **Beautiful.ai** (60+ smart slides) | Categories: lists · data & charts · visual impact · diagrams & timelines. Named: timeline, Gantt, SWOT, quadrant, process, comparison table, photo grid (its top-ranked one; we have no images). |
| **Gamma** | Fluid cards that grow instead of shrinking text (the same as our "fill, don't shrink" rule); a third-party guide counts 12 "smart diagram" types in Gamma 3.0 (names not confirmed). |
| **Genspark** (our own variant runs, `docs/eval/genspark-variants/summary.md`) | Hub with a dark centre, engine card grouping the middle steps, quadrant cards, stacked bars instead of a pyramid, labelled bars with one dark bar, progress bar over columns. |
| **Marketing / QBR report templates** (Whatagraph, Quadratic, ClickUp, SlideTeam) | Typical set: **funnel (impressions → clicks → conversions)**, channel comparison, ROI-vs-spend bubble, KPI trend vs target, campaign table, action items. |
| **Papers**: PPTAgent (EMNLP 2025), AutoPresent / SlidesBench (CVPR 2025), SlideGen (Dec 2025), PresentBench (Mar 2026) | No usable component taxonomy. PPTAgent splits slides into *structural* vs *content* and finds layouts by clustering reference decks. PPTEval's design score = colour, visual elements, no overlap. SlideGen argues that earlier systems give **uniform, repetitive layouts**. PresentBench compares Gamma, NotebookLM, Manus and others with 50+ checklist items per deck. The lesson for us: the research field measures overlap, fidelity and variety, which we already measure. The component set has to come from practitioner catalogues (think-cell, SmartArt-style families, consulting slide types). |

---

## 4. Candidates, ranked for our use case

Ranking = (how often our briefs and plans need it) × (how much it changes the slide) ÷ (build cost and
risk). Every candidate is a **component inside an LLM-laid slide**: content comes from the plan by `ref`,
code writes the inside, and the text is never reworded. Whole-slide code layouts lost the 1a test and made
decks look alike (§14.9), so none are proposed.

### Tier 1: strong evidence, data-shaped, build first

**A. Chart options via `pptx-post.js` (native, editable charts)**
- What: **value labels** on bars / points; **horizontal bars**; **target / reference line** (a line series
  over bars = combo); **stacked and 100% stacked** bars; paired bars with gap / overlap set.
- Not variants (user, 2026-10-26): the plain native chart is today's default, and **one highlighted bar is
  colour coding**. `chartColors` with one colour per bar already does it in POM (gallery slide 1), so it
  belongs to colour roles (focus = the item the headline names, else the latest), not to the variant list.
  The real new variants are the ones POM can't draw today: **horizontal**, **labelled**, **target line**
  and **stacked**.
- Evidence: 59 of 83 charts are bars and none has labels; 19 "horizontal" hints; review step 4; hand-qbr
  #8; CHEFFIN 3 and 6, sales win-rate target, QBR revenue trend.
- External: think-cell's core set; FT ranking and part-to-whole; Genspark CHART-D.
- Build: edit chart XML after compile (`c:dLbls`, `c:barDir="bar"`, `c:grouping="stacked|percentStacked"`,
  `c:overlap`, a `c:dPt` per highlighted point, a line chart in the same plotArea for the target). New plan
  fields: `highlight` (item), `target` (value + label), `stack` (bool). It stays a PowerPoint chart the
  client can edit, which matters for agency decks.
- Risk: LibreOffice and M365 render chart XML differently (check both, as with fonts); combo charts need a
  shared axis.

**B. Target vs actual / gap rows (bullet-chart family)**
- What: one row per item: label · actual bar · target tick · value labels · a code-computed gap ("2.9× allowable",
  "−6 pts to target"). Variants: `bullet` (bar + tick), `dumbbell` (two dots joined, for "from → to" or
  "actual ↔ target"), `paired` (two bars). An IBCS-style option normalises to % of target when units differ.
- Evidence: **54 target / allowable hints**, the most frequent missing shape; CHEFFIN 3 (the deck's core
  argument); QBR priorities; sales Q4 target; board asks.
- External: Few's bullet graph and IBCS; FT "deviation"; consulting gap charts.
- Build: a derived component (code-measured Shapes in a box, like KPI element refs) or chart option A
  (bar + target line). Rows of Shapes give exact control of labels and the gap text. Gap numbers are
  **derived values** computed by code (content policy D13), never typed by the LLM.
- Plan: a new kind `comparison_bars` or a `target` field per item on `chart`.

**C. Before → after pair**
- What: per metric, the old value (muted, optionally struck through) → the new value (ink) with a change pill
  (−89%). Variants: `tiles` (inside the KPI row: a schema field, not a new look), `rows` (a slope /
  dumbbell list for 3–8 metrics), `split` (two columns: Before | After).
- Evidence: 30 before → after hints; product-launch beta results (4 pairs); typed schema run dropped the
  before values (review §3); agency / XTSY "current vs proposed" operating model.
- Build: add `kpi_before: [..]` to the typed kpi_row schema (today only `kpi_deltas` / `kpi_directions`);
  element refs already write each value by ref, so the "before" becomes one more ref part. The change % is
  derived by code when both values parse. The rows variant = B's dumbbell.

**D. Funnel with conversion rates**
- What: 3–6 stages; each shows label, value (and count); between stages, the **conversion %** (derived).
  Variants: `centred` (classic narrowing bars), `bars` (left-aligned horizontal bars, easier to read and
  label), `steps` (stage cards with the conversion arrows between them).
- Evidence: sales pipeline by stage; XTSY "use funnels"; impressions → clicks → orders is the spine
  of every ad audit (CHEFFIN's CTR → CVR → AOV); marketing report templates.
- Today: a pyramid pointing down, with no values, no rates, and labels inside narrowing shapes (word-fit risk).
- Build: derived component from Shapes (bar widths ∝ value or fixed steps when values are missing); the
  rates are derived values. PowerPoint's native funnel chart (chartex) is M365-only and LibreOffice drops
  it, so don't use it.

### Tier 2: consulting staples, medium evidence

**E. Side-by-side compare (A vs B)**
- What: a row-header column + 2–3 compared columns (platform vs platform, current vs proposed, us vs
  them) + an optional **fix / so-what** column. Status glyphs in cells (✓ ✕ ◐, Harvey balls, ↑ ↓).
- Evidence: agency 3 (5 gaps × 2 platforms + fix); 13 briefs mention competitor / versus; table hints
  that "shade the two platform columns differently, Fix column as accent".
- Build: **a table variant** (`compare`): code tints each compared column with its brand / role colour
  (CHEFFIN's orange / purple), sets the row-header column, puts the fix column in the accent. Glyph cells
  from a small fixed set (text glyphs or a rasterised `<Svg>` Harvey ball). No new node type.

**F. Hub / engine diagram**
- What: a centre node + 3–8 satellites. Variants: `radial` (ecosystem: platforms around a brand),
  `engine` (inputs on the left → dark centre → outputs on the right → outcome; this is XTSY 6, which today's
  linear `flow` can't draw), `grouped` (centre + two labelled panels, XTSY 5 control tower).
- Evidence: 8 of 20 `layer` uses are this hub; 28 "engine" hints; XTSY 1, 5, 6; Genspark HUB-A / B and
  FLOW-B engine card.
- Build: a code-placed `<Layer>` (coordinates computed from the box and item count, Arrow connectors,
  word fit on node text), with the same measured checks as other diagrams. Replaces free LLM drawing,
  which is where most overlaps come from (review §4.4).

**G. Swimlane roadmap / Gantt-lite**
- What: phases or time as columns × lanes (platforms, workstreams) as rows; each cell holds short actions
  or a bar spanning phases. Optional "now" marker.
- Evidence: agency 30/60/90 with per-platform actions (lanes lost today); XTSY 90-day plan; board roadmap;
  "stage / roadmap visual" was the one card loss in the review (XTSY 3.4).
- External: Gantt is a think-cell and Beautiful.ai staple.
- Build: table-like grid in a Layer or a native Table with merged phase headers; the plan needs `lanes` ×
  `phases` (the planner already writes per-platform lines; today they're flattened).

**H. Status and direction glyphs (scorecard)**
- What: RAG dot, Harvey ball (0–4), trend arrow ↑ ↓ →, as a **cell type** for tables and a **marker** for
  lists. One composed use: the *indicator list* (label + arrow, no numbers), which is XTSY 7, "use arrow
  visuals rather than hard numbers".
- Evidence: 17 heat / status hints; sales deals-at-risk table; XTSY 7 drawn as a free `layer`; project-status
  test cases.
- Build: small; one glyph renderer shared by the table and list variants. Status levels must come from the
  brief, or be **inferred and flagged** (content policy): the planner must not invent a RAG colour.

**I. Heat grid / opportunity matrix**
- What: rows × columns, each cell tinted by a level (low / mid / high) and holding a short label or a
  Harvey ball.
- Evidence: XTSY 3 (4 × 3 opportunity matrix); city "heatmap" hints (CHEFFIN, agency); matrix cells
  repeating one line per row (review §4.4).
- Build: a table variant (`heat`), with cell fills from a level field mapped to palette role steps. **Caveat:**
  most briefs list opportunity areas but don't give levels. Without levels the grid falls back to labels
  only (no fake intensity).

### Tier 3: cheap, structural or occasional

**J. Equation / driver strip.** Value boxes joined by operators: *Allowable CPC = AOV × CVR → ₹195 × 5.5% =
₹10.7*. A short HStack; numbers derived by code from the brief's formulas. CHEFFIN 3 and every ROAS / CAC
argument. A multi-level driver tree can reuse `<Tree>`.

**K. Chips for short-term lists.** Wrapped pill rows for keywords, cities, SKUs (agency 2, CHEFFIN).
`wrapChipRows` already exists in fit-grow; expose it as a `bullet_list` variant `chips`, toned per list
(winners positive, weak negative).

**L. Section divider and agenda tracker.** A blueprint exists for the divider; an agenda strip that marks the
current section is a standard deck frame (board deck has two dividers).

**M. Statement slide.** The closing quote (agency 6, XTSY 8) as a full-slide statement. It's the `quote`
callout at slide scale and needs nothing new beyond a size rule.

### Considered and not recommended now

| Idea | Why not (now) |
|---|---|
| Mekko / Marimekko | Needs two-dimensional market data that none of our briefs supply |
| Sankey | Needs flow volumes between stages; no brief has them; hard to draw legibly in POM |
| Maps (city / region) | 14 briefs name cities but none gives geo data; maps need images or many shapes; a ranked bar of cities says more |
| Scatter / bubble (spend vs ROAS) | A good fit for channel analysis, but POM has no scatter; a later chart option once A exists (check how often plans have two measures per item) |
| Gauges / dials | Few's bullet chart replaces them (B) |
| Word clouds, photo grids, 3D | No images in the pipeline; low information |
| More KPI / card looks | Already tested: no blind-mark wins (review "More variants?") |

---

## 5. What each candidate needs in the pipeline

| Candidate | Planner (schema) | Drawing route | Derived by code | Content-policy note |
|---|---|---|---|---|
| A chart options | `highlight`, `target`, `stack` on `chart` | pptx-post chart XML | highlight from headline / latest | target must be in the brief |
| B target vs actual | new kind or `target` per item | Shapes in a box (element refs) | gap ×, gap pts | target copied; gap derived |
| C before → after | `kpi_before` (typed kpi_row) | element-ref part / rows | change % | both values copied |
| D funnel | new kind `funnel` (stage, value, count) | Shapes | stage conversion % | rates derived, never typed |
| E compare | `table` variant + `compare_cols`, `fix_col` | native Table, code fills | — | glyph levels copied or flagged |
| F hub / engine | new kind `hub` (centre, inputs, outputs, outcome) | code-placed Layer + Arrow | positions | — |
| G swimlane | `lanes` × `phases` | Table or Layer grid | — | — |
| H glyphs | `status` / `trend` per row or item | text glyph / Svg | — | inferred → flagged |
| I heat grid | `level` per cell | Table cell fills | role steps | no level → no tint |
| J equation | `terms` + `operators` | HStack | the result | formula from the brief |
| K chips | `bullet_list` variant | existing `wrapChipRows` | — | — |

Shared rules, from what the project has already learned:
- **The LLM keeps the layout; code owns content and sizing** (element refs won 0.75; code-drawn whole slides
  lost 7–18).
- Each new component gets a `capacity.yaml` entry (items per direction) and goes through word fit and
  geometry checks before it ships.
- Variants stay few (2–3 per component). The 1a run showed the LLM leaves the default on 73% of nodes, so the
  **default look must be the best one**.
- Highlight / emphasis comes from the plan's named sources (design hint, destination, priority), never from
  position (user rule 2026-10-07).

---

## 6. Suggested order and how to check each step

1. **Free count first.** On the 496 saved plans, mark each slide where a candidate would apply (target in the
   data, two values per metric, stage values, a hub-shaped `layer`, lanes in a roadmap) to confirm the
   ranking with numbers, not keywords.
2. **Batch 1, data shapes:** A (chart options) + B (target vs actual) + C (before → after field) + D (funnel).
   All four are numeric, share the derived-value code, and hit CHEFFIN / QBR / sales / launch. Free
   replay on saved chart and KPI slides, then one paid run on those four decks with a blind sheet
   against the last baseline (cost estimate before running, as usual).
3. **Batch 2, table family:** E (compare) + H (glyphs) + I (heat grid) + K (chips). All are table or list
   variants, cheap, and mostly agency / XTSY.
4. **Batch 3, diagrams:** F (hub / engine) + G (swimlane), the two that replace free `layer` drawing.
   Measure overlaps against today's `layer` slides.
5. Tier 3 (J, L, M) fits into any batch.

## 6b. Gallery and the test each candidate must pass (added 2026-10-26)

**Gallery:** `python -m scripts.experiments.component_candidates_gallery [--palette <name>]` (use
`.venv/Scripts/python.exe` so fonts embed) writes `output/component-candidates/slide-1..9.xml`, the merged
`.pptx`, and (with PowerPoint) PNGs. On the build PC, render with LibreOffice → PDF → pymupdf. It draws
candidates A–M with 2–4 variants each, from our briefs' content. **It is a picture of the proposals, not a
result:** sizes are fixed by hand, and the chart variants other than native / highlight are drawn with
shapes.

**Every candidate must pass the same test as tile nodes, KPI and cards before it is adopted.** Looking
right in a hand-made gallery proves nothing about how a candidate holds up when the planner and the LLM
vary it freely. Earlier gallery evidence held up in different ways:
- KPI tile nodes were accurate (48 / 48, 0 off-plan values) and looked good in their gallery, but **failed the
  blind gate** on fresh and same-plan decks (0.33, 0.4, 0.375). The losses were layout defects when the LLM
  placed them freely, plus the LLM decorating its own tiles more.
- Card nodes passed (replay 0.533, paid **0.692**) only after the default look changed (open columns lost at
  0.313).
- In 1a the LLM left the default variant on 73% of nodes, so a variant only matters if it is picked.

The questions per candidate, in this order:
1. **Does real content fit it?** Free replay on every saved slide where it applies (target values, before /
   after pairs, funnel stages, hub-shaped `layer`s, lanes), with long labels, many items, missing values,
   mixed units and every palette. Report broken words, `GEOM_*`, `LOW_CONTRAST` and empty cards against the
   route it replaces.
2. **Does freedom break it?** The LLM places it in its own layouts (beside a chart, in a half-width card, two
   on a slide). Same-plan, generator-only check: both routes on the same plans, as in
   `tile_same_plan`.
3. **Is it picked, and is the pick right?** How often the planner / generator choose it and each variant, and
   whether the chosen variant suits the data (horizontal for long category names, funnel only for stages).
4. **Does it win?** Blind marks vs today's route, gate ≥ 0.5, on whole decks, not on one slide type.

A candidate that fails 2 or 4 stays opt-in, as KPI tile nodes do. Run one batch per paid run (§6), with a
cost estimate first.

## 7. Open questions for you

1. **Native chart vs drawn rows for B (target vs actual):** native (editable in PowerPoint, fewer label
   controls) or Shapes (exact labels and gap text, not editable as a chart)? Agency clients editing the deck
   argues for native.
2. **Funnel when values are missing** (a qualitative "awareness → consideration → purchase"): equal step
   widths with labels only, or route to `process_arrow`?
3. **Heat / status levels the brief doesn't give:** leave the grid untinted (strict), or let the planner
   propose levels flagged for Keep / Remove (as with card description lines)?
4. **Brand colours as series colours** (CHEFFIN orange / purple per platform in compare and charts): allowed
   as data colours, or palette roles only?
5. Is the batch order right for your next client decks, or do the agency decks (E, F, G) matter more right
   now than the numeric ones?

---

## Sources

- FT Visual Vocabulary: [chart-doctor README](https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md), [data.europa.eu guide](https://data.europa.eu/apps/data-visualisation-guide/visual-vocabulary)
- think-cell chart types: [think-cell Charts](https://www.think-cell.com/en/product/think-cell-charts), [Mekko](https://www.think-cell.com/lp/mekko-charts), [Gantt](https://www.think-cell.com/lp/gantt-charts); consulting chart set: [Ampler](https://ampler.io/articles/create-waterfall-mekko-and-gantt-charts-in-powerpoint-with-ampler-charts/), [Deckary on Mekko Graphics](https://deckary.com/blog/mekko-graphics-review)
- Consulting slide structures: [Deckary: executive summary](https://deckary.com/blog/executive-summary-slides), [Deckary: project status slide](https://deckary.com/blog/project-status-slide), [SlideUpLift: McKinsey style](https://slideuplift.com/blog/mckinsey-style-presentation/), [infoDiagram: Harvey balls](https://infodiagram.com/slides/status-harvey-balls)
- Bullet charts / IBCS: [Domo](https://domo-webflow.domo.com/learn/charts/bullet-graphs), [Luzmo](https://www.luzmo.com/blog/bullet-chart), [Inforiver](https://inforiver.com/?p=8262), [bino docs](https://cli.bino.bi/reference/chart-bullet/)
- AI slide tools: [Beautiful.ai top smart slides](https://beautiful.ai/blog/customer-favorites-beautiful-ais-top-10-smart-slide-templates-ranked), [Beautiful.ai diagrams & timelines](https://www.beautiful.ai/slide-categories/diagrams-timeline-slides), [Gamma card layouts](https://gamma.app/uk/explore/content/guides/ai-presentation-tool-card-based-layouts), [TIMEWELL on Gamma 3.0](https://timewell.jp/en/columns/gamma)
- Marketing reporting: [Whatagraph KPI template](https://whatagraph.com/templates/marketing-kpi-report-template), [Quadratic funnel template](https://www.quadratichq.com/templates/marketing-funnel-template-analytics-roi-dashboard), [ClickUp performance marketing QBR](https://clickup.com/p/templates/qbr-planning/performance-marketing-qbr-template)
- Papers: [PPTAgent (arXiv 2501.03936)](https://arxiv.org/abs/2501.03936v3), [AutoPresent (CVPR 2025)](https://mlanthology.org/cvpr/2025/ge2025cvpr-autopresent), [SlideGen (arXiv 2512.04529)](https://arxiv.org/abs/2512.04529v1), [PresentBench (arXiv 2603.07244)](https://arxiv.org/pdf/2603.07244)
