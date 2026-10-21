# Look-and-feel review: what worked, what failed, what next (2026-10-21)

One view of every look-and-feel experiment since September 2026, for whole-deck slide quality.
Read-only review of the docs and eval READMEs on `feat/tile-nodes` (`2df8fb7`); no code changed, no
paid run. Every number below comes from the doc named in its row; "blind marks" = the user's blind
side-by-side score for the new side (win 1, tie 0.5), gate usually ≥ 0.5.

Sources: `AGENTS.md` "Where work stands", `docs/eval/**` (hand-qbr, 1a, step0, kpi-node, kpi-tiles,
tile-nodes paid / paid-2 / paid-3 / wide / wide-paid / same-plan / combined, card-nodes, genspark-ref,
genspark-variants, structure-loss, planner-schema, test-1, deck-output-fixes-2026-10-15),
`kpi-node-pilot-2026-10-11.md`, `tile-nodes-spec-2026-10-12.md`, `geometry-check-2026-10-07.md`,
`palette-quality-research-2026-10-06.md`, `derived-nodes-design.md` §10–14, `derived-blocks-planning-2026-10-06.md`,
`presentation-rules-draft-2026-10-15.md`, `planner-output-schema-research-2026-10-15.md`,
`architecture-north-star.md` §14, the worklog, `roadmap-derived-components.md` (halted), the memory notes on
fit-grow, filling cards and quality-first priorities, and the commits of 2026-10-16 → 10-21.

## Summary

- **What moved whole-deck quality most was planning and house-style numbers, not drawing code.** The
  hand-written QBR comparison (`docs/eval/hand-qbr/README.md`) traced 12 gaps: 5 were planning, 4 house-style
  numbers / rules, 2 code bugs, 1 a missing chart block, 0 the model's ability. After fixing them the QBR deck went
  from 8 slides to 5, cost $0.49 → $0.25, 0 retries, claim headlines, no repeated facts.
- **Code that owns content and sizing, with the LLM owning the layout, wins.** Code-drawn blocks lost the 1a
  blind test 7–18 (5 ties). Element refs (the LLM draws the tiles, code writes the text and the one number size)
  won 0.643 → 0.556 → 0.75 and became the default. Card nodes passed at 0.692. KPI tile nodes kept failing the
  gate (0.33, 0.4, 0.375) once compared on whole decks or on the same plan.
- **Colour and contrast are largely solved in code** (derived role tokens, 0 typed hex colours, `LOW_CONTRAST`
  20 → 7 on 75 card slides). **Charts are the area with the least work done:** no direct labels, legends still
  in the knowledge examples, and POM has no data labels.
- **Empty space (`GEOM_CARD_EMPTY`) is the most frequent geometry finding still open**, and the newest fix
  (`fillLoneRows`) swaps empty bands for taller cards (7 → 68 findings on 41 slides). That trade-off is the
  user's decision and has not been made.
- **No full six-deck run at today's HEAD.** Since the last full decks (2026-10-13 / 10-16) these have been
  built but not seen together on fresh decks: the typed planner schema, the deck-output fixes, diagram direction +
  word fit, KPI label refs, `TEXT_BOX_UNSQUEEZED`, `fillLoneRows`, and the "never type the text" lines.

## 1. Successes (adopted, with evidence)

| Theme | What was tried | Outcome (numbers) | Cost | Evidence | Status |
|---|---|---|---|---|---|
| Colour / palette | Derived role tokens (`*Soft`, `*Text`, `onAccent`, `neutral`, `panelDark`), P3 palette fixes, colour roles good / bad / watch / one focus / grey rest, no literal hex in knowledge or prompts | Typed hex colours on the QBR deck 5 → **0** (step-0 baseline: 117 literal colours on 18 / 43 slides); 18 / 18 palettes pass the contrast / role tests; 1 `LOW_CONTRAST` left (`$positive` instead of `$positiveText`) | $0.19 | `palette-quality-research-2026-10-06.md` §13 | default |
| Colour / card edges | `border` derived to ≥ 1.4:1 on surface (was 1.12–1.29:1 on every light palette) | The critic's "flat cards" issue gone; card edges visible in paid check 2 | free | `geometry-check-2026-10-07.md` "KPI tiles, card edges" | default |
| Colour / contrast on dark | KPI text on a dark tile gets the fill's on-colour (`READS_ON`); `_unwrap_refs` | QBR `LOW_CONTRAST` 2 → 0; all-nodes dark-panel readability won blind pair P2 | free | `kpi-node-pilot` §12–13 | default |
| Colour / dark panels | At most one dark panel per deck (`DARK_PANEL_SOFTENED`) | XTSY had a dark panel on 6 of 8 slides → 1 | free | `hand-qbr/README.md` six-case section | default |
| Typography / font | Deck font Inter on every text node + deck-level subset font embedding (`font_embed.py`) | Broken glyphs and font fallback gone (pptx named "Noto Sans JP" before); Genspark showed the same need (Inter on one account, Noto / DejaVu on another) | free | `hand-qbr` #12, `derived-nodes-design.md` §14.8 point 4 | default |
| Typography / ramp | New type ramp: title 36, subtitle 18, body 18, stats 44–56, table 20–22; padding 48–56 | Hand-deck sizes reached (was headline 30 / body 14–15 / KPI 34) | $0.25 | `hand-qbr` changes table | default |
| Text hygiene | Control characters stripped from every LLM result (`CONTROL_CHAR_REMOVED`) | `42.3▯` glyphs: 9 per QBR plan → 0 | free | `hand-qbr` #5 | default |
| KPI tiles | **Element refs** (D13): the LLM composes the tiles, code writes every label / value / note verbatim, one number size per component, unit share by unit length, tone colours | Blind marks: replay **0.643**, paid 0.556, full decks run 2 **0.75**; mapping 100%; refs 48 / 48 first try; 0 off-plan values; QBR numbers 32 → 55–60 px; CHEFFIN 4 `WORD_TOO_WIDE` 6 → 0 | $0.30 + $1.13 + $1.18 | `kpi-node-pilot-2026-10-11.md` §7, §9, §13 | **default** (`POM_BLOCKS=kpi`) |
| KPI tiles / colour | Planner `kpi_tones` + `tones_from_hint` fallback | Tones on 8 / 8 KPI rows in both arms of the wide paid run; the hint fallback toned 37 of 71 saved rows with no misreading (hand check) | in the $2.74 wide run | `tile-nodes/wide/README.md` P2, `wide-paid/README.md` | default (both routes) |
| KPI tiles / accuracy | `fill_refs` field-order fix; KPI labels by ref only; code writes each label beside its value | A hand-typed tile with 4 wrong numbers had slipped through (`NODE_BYPASSED`), now `NODE_ITEM_MISSING` → repair; 38 saved KPI slides: 35 unchanged, 1 label restored, 0 to repair | free | `wide-paid/README.md`; commits `0131fdb`, `2c21147` | default |
| Card nodes | `<CardGrid ref>` / `<Card ref>`: code writes title / tag / body / key phrase; `lifted` look; one dark focus card; icons by density | Free replay: card output tokens −98%, title 22 → 26 px, `LOW_CONTRAST` 20 → 7; blind marks 0.313 (open columns) → 0.533 (lifted) → **paid 0.692 (B 6 / tie 6 / A 1), gate passed** | $1.80 | `card-nodes/paid/README.md`, `replay-2/summary.md` | **opt-in only** (shares `POM_BLOCKS=tiles` with KPI tiles; see §3) |
| Layout / spills | Geometry check on what is drawn (`GEOM_*`) + fit-grow `fixSpills`, `centreBody`; search rejects growth past the slide edge; Layer scaling | Dense-deck replay (37 slides): `GEOM_COLLISION` 21 → 7, `GEOM_SPILL` 14 → 7, `GEOM_OFF_SLIDE` 2 → 1 | free | `geometry-check-2026-10-07.md`; `hand-qbr` six-case table | default (report-only audit) |
| Layout / KPI rows | `KPI_ROWS` (lone row of 4–6 → rows of 2–3), `regridTiles`, stacked rows share one size | Numbers 34 → 85 px on the two saved KPI slides; QBR tiles 58 → 85–87 px | free | `geometry-check` "KPI tiles"; `tile-nodes/paid-2` fixes | default |
| Layout / generator rules | `capacity.yaml` `layout` rules (≤ 4 KPI per row, ≥ 260 px tiles, 60/40 splits, takeaway 35–40 %) | Visible in paid check 2: two equal 49 % cards, takeaway beside a chart, 0 retries | $0.49 | `geometry-check` paid check 2 | default |
| Broken words | Shrink guard (`WORD_TOO_WIDE`), growth may not make a word too wide, `wrapChipRows`, chevron / flow node sizes from the longest word | 1a: broken words 0 vs 6; deck-output fixes: word breaks 13 → 1 on 14 slides, paid re-run **0.93 → 0.14 per slide**; 120 diagram slides: chevron `WORD_TOO_WIDE` 36 → 6 | $0.52 | `1a/summary.md`; `deck-output-fixes-2026-10-15.md`; commit `e04963c` | default |
| Planner / content | Outline: slide count is a maximum, each fact once, claim headlines, no filler components, no "Note:" commentary | QBR 8 → 5 slides; no fact on two slides; Test 1 path proved headlines 0 / 13 → 13 / 13 and invented numbers → 0 | $0.25 | `hand-qbr`; `docs/eval/test-1/` | default |
| Planner / reliability | Typed planner schema (one model per component kind) | Unreadable content fields 24 → **0**, length-limit hits 3 → 0, re-asks 10 → 2, fallbacks 1 → 0, cost $1.48 → $1.16 | $1.16 | `planner-output-schema-research-2026-10-15.md` | **default** (`PLANNER_SCHEMA=string` = old) |
| Planner / empty plans | `plan_with_reask`, `holds_no_content` → fallback to the brief's lines | 7 of 1,989 saved plans caught, all empty; stops the generator inventing lists (XTSY 5) | free | `wide-paid/README.md` | default |
| Planner / instructions | Brief instructions and visual directions kept off slides; `LAYER_REPEATED`; `drop_shared_card_lines` | Paid re-run: compiled 92.9 → 100%, first pass 64.3 → 100%, layout issues 2.36 → 1.21 per slide, no instruction text on slides | $0.52 | `deck-output-fixes-2026-10-15.md` | default |
| Charts (small) | `CHART_FOCUS_LATEST`, `GROW_LONE_CARD`, `TABLE_NUMERIC_COLS_SHARED` | QBR chart 180 px with 40 % empty → fills; focus on the last period; table columns even | free | `hand-qbr` paid-run table | default |

## 2. Failures / dropped (and why)

| Theme | What was tried | Outcome | Cost | Evidence | Why dropped |
|---|---|---|---|---|---|
| Whole-slide code drawing | Phase 0b composer / code-drawn blocks ("route A") | Hold-out (17 new slides): mechanically sound, but 4 new failure types the in-sample decks never showed; every style pack gave the same slide structure (cross-deck sameness from code-chosen layout) | $0.78 | `derived-nodes-design.md` §14.3b, §14.9 | superseded by §14.6 (LLM layout, code content); kept as a tool / fallback |
| Derived nodes / slots (1a) | `<KpiRow ref>`, `<CardGrid ref>` etc. drawn by code in LLM slots | Kill criteria passed on compliance 91 %, invented 0, broken words 0 vs 6, output tokens −75 %; **blind marks: LLM route 18, nodes 7, 5 ties**; the 4 KPI slides 0–4 ("colour code", "size", "icons") | $0.74 | `1a/summary.md`; `kpi-node-pilot` §1 "Why" | paused; the lesson (colour, size, icons decide) shaped element refs |
| KPI variants as named looks | Option A `KpiGroup` + structure variants; colour-based variants | LLM left the default on 73 % of nodes in 1a; colour variants rejected by the user (colour only from palettes) | free | `kpi-node-pilot` §1 "Rejected" | replaced by element refs |
| KPI tile nodes | `<KpiGrid>` / `<Kpi>` tags, code expands | Paid 1: **0.5**; paid 2 (3 repeats): **0.33**; paid 3 (fresh plans): 0.67; wide full decks: **0.4** (with the wrong-number slide as a loss); same-plan: **0.375** (0 wins, 3 losses, 9 ties). Accurate (48 / 48, 0 off-plan) and −26 % to −36 % cost, but losses were layout defects and the LLM decorating its own tiles more | $0.058 + $0.092 + $0.274 + $1.45 + $0.48 | `tile-nodes/paid*`, `wide-paid`, `same-plan` | **not adopted** (opt-in); fixes since (pinned rows, `TEXT_BOX_UNSQUEEZED`, `fillLoneRows`, "never type") are unmeasured on fresh runs |
| Prompt wording as a colour lever | Tile prompt maps the hint's treatments to tile attributes | QBR still wrote a bare `<KpiGrid>` in 3 / 3 tries; colour only came once the planner wrote tones | $0.092 | `tile-nodes/paid-2/README.md` finding 1 | dropped as a lever; colour comes from the plan |
| Card default look | Open columns as the default card look | Blind marks **0.313** | free | `card-nodes/replay-2` | replaced by `lifted` (0.533, then 0.692 paid) |
| Planner fan-out / archetypes / blueprints | Layout archetypes A–E, `enforce_layout_variety`, golden examples and blueprint XML in the prompt | Layout regression (Sept); examples written in the old sizes | – | memory "slide-quality rework plan"; `hand-qbr` changes | examples off by default (`POM_EXAMPLES=on` for A/B); archetype removal deferred |
| One-example fixes | fit-grow rule turning a shrunk flow vertical | Fixed 4 of 6 shrunk workflows (5.25 → 10.5 pt), all from one brief | free | `deck-output-fixes` step 5 "Tried and removed" | removed (fitted to XTSY 6); fixed in the planner instead |
| Unsqueeze for any sibling | `TEXT_BOX_UNSQUEEZED` v1 on any `w="max"` sibling | Touched 97 slides, agency 2 broken words 0 → 10 | free | `same-plan/README.md` fix 2 | narrowed to tile / card siblings (10 slides) |
| Equal tile widths | `w="1"` on every tile of a row | Widest number 47 → 28 px | free | `kpi-node-pilot` §12 | dropped |
| Smaller cards for sparse content | §10f natural height × 1.25 | User rejected: grow the type, do not shrink the card | free | memory `feedback-fill-cards-not-shrink` | dropped |
| Test 1 planning path | Storyline + slide designer | Headlines and numbers better, but 1.8 components per slide vs 2.83 on thin briefs | ~$2 | `AGENTS.md` "Next work"; `docs/eval/test-1/` | not taken to production; fidelity fixes ported |
| Derived-components roadmap | Code-emitted structure for every component (Phase 4) | – | – | `roadmap-derived-components.md` | halted 2026-09-24 (history) |

## 3. Mixed or inconclusive

| Theme | What | Result | Why it is not settled |
|---|---|---|---|
| Cards vs KPI under one switch | Card nodes passed (0.692) but ship only with `POM_BLOCKS=tiles`, which also turns on KPI tile nodes that failed | Cards are not in the default decks | `element_refs.mode()` has one value for both. The prepared combined check measures both on the same plans |
| `fillLoneRows` | A lone card row ≥ 40 px short of its box takes the box | Corpus of 41 changed slides: compiled 36 → 39, `w="max"` squeeze 5 → 2, `WORD_TOO_WIDE` 4 → 0, broken 6 → 2, but **`GEOM_CARD_EMPTY` 7 → 68** (stretched rows) | The user's decision; `POM_FIT_LONE=0` restores the old look. The scorer counts a taller card as "empty" |
| Visual critic | Critic on, code owns size / spacing | Paid check 2: **1 of 3 critic repairs useful**, 1 wasted, 1 worse (second eyebrow). It did catch a generic context card (judgement code cannot make) | One deck, two runs. Eval runs keep the critic off; its value per dollar is unknown |
| KPI number size vs preference | Tiles drew larger numbers on 7 / 12 same-plan pairs | Larger numbers did not win a single pair (9 ties) | Size alone is not what the user marks; colour, decoration and fill are |
| Planner grouping into several kpi_rows | Prompt lets a slide split its numbers by role | Planner-only check: 5 of 12 KPI slides split, 0 numbers in two groups ($0.619) | No full-deck blind marks since; the marked losses were long single rows of 5–7 |
| Diagram direction and step limits | Planner prompt: direction from the space, one node per step, limits per direction; fit-grow word fit for chevrons / flow | Free: chevron `WORD_TOO_WIDE` 36 → 6 on 120 slides; flow is the only node that shrinks (7 of 16 flows drawn < 75 %) | The planner change has not had a paid run (the 10-16 run planned no flow) |
| Typed schema side effects | Typed default | One run dropped the "before" KPI values (product-launch r3 slide 4); XTSY r1 copied 7 areas into all 4 lever cards (28 bullets) | 1 run each; watch, do not fix yet |
| Label tier below 14 px | Genspark reference slides with 10–12 px mono labels | Read well in the Phase 0 render | Never decided; house floor is still 14 |
| Cross-deck sameness | 1a: nodes 0.6 vs off 0.0 (informational) | Code-chosen structure made decks look alike | Decided 2026-10-05 "the outline planner picks a palette when the brief names none"; no code for it was found in `src/` (grep), so to confirm |

## 4. Open problems (ranked by how many slides / decks they touch)

1. **Planner density and thin plans** — the largest source of visible gaps in every whole-deck comparison
   (hold-out §14.3b: "the biggest visible gaps come from the plan"; card paid: 19 of 22 missing lines on one
   8-component agency slide; empty cards left are all from plans). `plan_reviewer` is still advisory:
   `route_after_plan_review` always goes to `style_resolver` (`src/graph.py:158`).
2. **Empty space in cards and tiles** — `GEOM_CARD_EMPTY` 59 (refs) / 70 → 26 (tiles) on 68 KPI slides, 44 / 54
   on 75 card slides; low-fill cards 14–23 % per deck in every eval (`step0` 20.5 %, wide-paid 14.1–17.0 %,
   deck fixes 21.5 %). The `fillLoneRows` trade above is unresolved.
3. **Charts** — POM `<Chart>` has no data labels; `chart.yaml` and `blueprints.yaml` still show
   `showLegend="true"` examples against rule L6 (direct labels); focus colour on the first series instead of the
   one the headline names (geometry item 2(b)); time series coloured "worst" on the oldest period (hold-out
   failure 1); chart series not separable by lightness in any palette (palette A7, §5.4 not built).
4. **Diagrams** — flows shrink below 50 % (6 of 16 saved); text in shapes is outside the word guard
   ("Framewo / rk"); a 7-step `steps` grid loses its order and arrows (XTSY 6); matrix cells repeat one written
   line per row (XTSY 3); `<Layer>` shape-over-shape not checked.
5. **The `w="max"` squeeze and width shares** — squeezed tile rows fixed for tile / card siblings only; the
   longest value gets no wider tile in a row (all-nodes-dense 1: 36 vs 43 px; CHEFFIN 1 platform row beside a
   callout).
6. **Headlines and story** — Test 1: tension 5 / 15 vs 12 / 15 for the production deck, descriptive
   sub-headlines, no kickers. The user parked the story rules S1 / S3 / S5 / S7 (2026-10-15), so only headline
   sharpness inside a plan review is in scope.
7. **Planner-written prose** — written lines are checked in card grids only; narratives can carry planner prose
   (agency 6 closing line).
8. **Critic** — the manifest keeps the final round's issue texts only (keeping every round is open item 2(a) in
   `AGENTS.md`); the "kicker missing" rule was tightened on 2026-10-08 but has not had a paid re-check.
9. **Smaller items** — compound KPI values ("₹0.59 L / 9.13x / 11.0%": 28 of 317 values, old plans); KPI label
   colour (76 % muted is the LLM's own norm; one user note asks for colour); `pptx_merge` reuses slide media names
   (wrong icons in merged decks, fix proposed as its own session); tabular figures (T3) and line length (L5) not
   built.

## 5. Recommended next steps (ranked by expected effect on whole-deck quality)

Rules applied: no fix written for one slide or one brief; a free replay on the saved corpus before any paid
run; every paid run asks first with its cases and cost. Costs come from the saved manifests quoted in the docs.

| # | Step | Why (expected effect) | Free / paid | Cost estimate |
|---|---|---|---|---|
| **1** | **Measure HEAD on whole decks.** First a free replay of every saved six-deck slide (`output/step0`, q1008, wide-paid, deck-fixes) through today's normalizer + fit-grow, one scorecard (word breaks, `GEOM_*`, `LOW_CONTRAST`, `kpi_labels_wrong`, low-fill cards) against each run's own numbers. Then one paid six-deck run on the default route (`python -m scripts.eval_run deck-qbr-data deck-product-launch-data gate-deck-agency-takeover gate-deck-xtsy-qcomm gate-deck-cheffin-full gate-deck-all-nodes-dense --repeat 1 --label head-1021 --bundle`) and a blind deck-vs-deck sheet against `quality-1008` / wide-kpi | Seven changes since the last full decks have never been seen together on fresh plans (typed schema, deck fixes, diagram direction, KPI label refs, unsqueeze, lone rows, "never type"). Every later gate needs this baseline | free replay, then paid | replay $0; run ≈ $1.75–1.95 (six decks $1.74 at step 0 / q1008, $1.30 wide-kpi) |
| **2** | **Make `plan_reviewer` a real loop** for density and thinness (`docs/plan-reviewer-loop.md`): code checks first (components and text per slide vs the slide's room from `capacity.yaml`, slides thinner than their purpose, facts reused, planner prose outside card grids), re-plan only the named slides, ≤ 2 rounds | Planning is the largest source of gaps in hand-qbr, the hold-out, card paid and the agency 8-component slide; it is deck-wide, not per-component | free first (score the checks on all saved plans, count flags, read each by eye), then paid | checks $0; comparison per the doc ≈ $2 (gj-h1 × 3 + CHEFFIN-audit × 3) |
| **3** | **Give card nodes their own switch** (e.g. `POM_BLOCKS` values for cards and KPI tiles apart) and run the prepared combined check (`docs/eval/tile-nodes/combined/README.md`) to decide cards-on-by-default on the same plans | Cards passed the gate (0.692) and cut `LOW_CONTRAST` 20 → 7, but no default deck gets them because they ride on the failed KPI tile switch. Card grids are on most slides of XTSY / agency / launch | switch free (needs your OK); check paid | ≈ $2.1, ceiling $2.8 (`--repeat 1` ≈ $1.3, ceiling $1.7) |
| **4** | **A chart pass**: (a) remove `showLegend="true"` from knowledge examples where one series or direct labels fit (L6, decided 2026-10-15); (b) focus colour from the series / period the headline names, else the latest period, for every chart type; (c) a code-drawn column / bar block for small series with a value on every bar (hand-qbr #8), measured on every saved chart slide (64 chart components in the corpus) | Charts have had no look-and-feel pass; the hand deck's chart (value labels, one highlight) was one of its clearest wins | free replay on saved chart slides; then within run 1's successor | $0 (then rides on the next deck run) |
| **5** | **Decide the empty-space trade**: blind-mark a sheet of the 31 stretched-row slides `fillLoneRows` changes (with vs `POM_FIT_LONE=0`), and fix the `GEOM_CARD_EMPTY` scorer so a stretched card whose text grew to its type cap is reported apart from a genuinely empty one | The most frequent open geometry finding; the user's standing rule is "grow the type, don't shrink the card", and the current numbers cannot tell the two cases apart | free (your marks) | $0 |
| **6** | **Diagram readability, general rules**: (a) text in shapes in the word guard (plan item 2 of deck-output step 5); (b) count `steps` > `steps_max` in saved plans, then choose wrapped steps that keep arrows vs a re-ask; (c) shape-over-shape inside a `<Layer>` in the geometry report; (d) blind-mark native nodes (Tree, vertical Flow, Matrix, card grid) against the LLM's `<Layer>` on saved layer plans | Flows are the one node that shrinks badly (6 / 16 below 50 %); layers cause most overlaps | free | $0; the planner direction change rides on step 1's run |
| **7** | **Typography details**: decide the sub-14 px label tier (gallery of both on saved slides), tabular figures for number columns (T3), line length 60–75 characters (L5) | Small per slide, but on every slide; Genspark-level polish relies on the small label tier | free | $0 |
| **8** | **Colour for charts and colour-blind readers**: chart lightness rule (palette §5.4), positive / negative lightness gap (A6: 11 of 18 palettes under 1.3:1), sign or arrow on every coloured delta (R2); confirm whether a palette is picked when the brief names none (decided 2026-10-05, no code found) | Colour is solved for text and fills, not for series or for decks that all fall back to one theme | free (palette tests + preview) | $0 |
| **9** | **Critic: keep off by default; narrow it to content judgement** (generic text, filler boxes, kicker only when missing), then one paid A/B on a deck the critic has not seen | 1 of 3 repairs useful in the one measured run; it costs repairs | paid after a free prompt change | ≈ $0.5 (one deck × 2 arms, QBR was $0.45–0.49 with the critic on) |
| **10** | **KPI tile nodes: no more work until step 3's data** | Five gates, best 0.67 on 3 slides, 0.375 on the same 12 plans; the element-ref default already wins 0.75 | – | – |

### Order to work in

The ranking above is by effect; the order below is by what unblocks what, so each paid run measures several
free changes at once.

1. **Free, one session each, any order:** step 5 (your marks on `fillLoneRows` + the empty-card scorer), step 4
   (chart pass, replayed on saved chart slides), step 6 (diagram rules), step 7 / 8 (type and colour details).
   These change code only, so they need no paid run of their own.
2. **Free:** step 2's code checks on all saved plans (count and read the flags; no loop yet).
3. **Paid, about $1.9:** step 1, the six-deck run at HEAD, which now also covers steps 4–8. Blind-mark it against
   `quality-1008` / wide-kpi. This is the new baseline.
4. **Paid, about $1.3–2.1:** step 3, the combined check, with cards on their own switch. Decide cards-by-default.
5. **Paid, about $2:** step 2's plan-review loop, compared against the baseline from 3.
6. Step 9 (critic) only if 3 and 5 still show problems that need judgement (generic text, filler).

### More variants?

Not now. On this project's own evidence, more variants have not been what wins blind marks:
- In 1a the LLM left the default variant on 73 % of nodes, and the marks were decided by colour, size, icons and
  fill (`kpi-node-pilot` §1).
- On the same plans, tiles with larger numbers won 0 of 7 pairs (9 ties overall). The losses were layout
  defects and the LLM's own decoration, not a missing look (`same-plan/README.md`).
- Variety across slides already comes from the LLM laying out each slide (four KPI slides, four layouts,
  `kpi-node-pilot` §10). Code-chosen variants made decks look alike (`derived-nodes-design.md` §14.9).
- The draft variant shortlist from the Genspark runs (`docs/eval/genspark-variants/summary.md`) is enough to draw
  from when a gap shows up.

The exceptions are diagrams and charts, where a real gap has been seen: a stage / roadmap visual (the one card
loss, XTSY 3.4), and a labelled bar chart with one highlight (hand-qbr #8). Add those as general components
(step 4 / step 6, measured on all saved slides of that kind), not as more looks for KPI tiles or cards.

Not recommended now: more prompt wording for colour (failed twice), fixes from the 3 KPI slides (user,
2026-10-12), story-order rules S1 / S3 (parked by the user), new code-drawn whole-slide layouts (cross-deck
sameness, §14.9).

## Notes on this review

- Graphify: the code graph in `presentation-pipeline/graphify-out/` was updated with `graphify update .`
  (AST only, no LLM: 5,193 nodes, 11,057 edges, 297 communities). The 108 changed docs and 169 images were not
  re-extracted semantically (that needs subagents); the docs were read directly instead. The update modified the
  tracked `graphify-out/` files (`graph.json`, `GRAPH_REPORT.md`, `manifest.json`, …) and added a backup folder
  `graphify-out/2026-10-21/`; nothing was committed.
- Blind marks are on small samples (3–13 pairs, mostly QBR / CHEFFIN / XTSY / agency), often with one plan per
  arm; read them as direction, not as precise scores.
