# Tile nodes: same-plan check (generator only)

**Why.** In the wider paid run (`../wide-paid/README.md`) each route planned its own decks, so the blind marks
judged the text around the KPIs as much as the tiles: 3 of 5 pairs were decided on commentary / text sections.
Here both routes draw the **same** slide plans, so only the KPI drawing differs.

**What runs.** `inputs.json` holds every slide with a `kpi_row` in the two wide-paid runs: 12 plans (6 planned by
the tiles run, 6 by the element-ref run), each with its theme name and case request. Each plan goes through the
real graph from the plan twice (`scripts/experiments/kpi/kpi_paid.run_one`): arm **A** `POM_BLOCKS=kpi` (element refs, the
default) and arm **B** `POM_BLOCKS=tiles` (tile tags). Generator + validator + repairer as in a normal run, critic
off as in the eval runs; the slide is drawn alone (no deck context, no supplied data: the same for both arms).

**Command (test PC, branch `feat/tile-nodes`, after `git pull`):**

    python -m scripts.experiments.tiles.tile_same_plan --label same-plan --bundle

No `POM_BLOCKS` to set: the script switches it per arm. It prints `EMAIL THIS FILE: output/tile-same-plan/same-plan.zip`.
The zip holds `summary.md`, `results.json`, `runs.json`, `run.log` (every log line, uncut), each run's first / final
XML and `sheets/` (the blind pairs: `sheet-*.png`, `marks.csv` to fill, `key.json`).

**Cost.** 24 generator runs (12 plans × 2 arms). From the wide runs' manifests, generator + repair per KPI slide:
tiles $0.017, element refs $0.024 (max $0.027). Estimate **≈ $0.50, ceiling ≈ $0.75** (if several slides need a repair).

**Scored per pair** (`summary.md`): smallest KPI number (px), empty cards, broken words, values off the plan, first
try, cost; and the count of pairs where tiles' numbers are larger / smaller / the same. Then the blind marks.

**Dry run (free, build PC, fake generator = the source run's own XML carried over to the other route):** 24 / 24
runs end to end, scores and the sheet built. One tiles run failed in the dry path only: the rewrite tool kept the
hand-written labels and added tile tags (`NODE_REF_DUPLICATE`), which the LLM does not do. The dry sizes repeat
the free replays (tiles larger 3, smaller 2, same 7); the paid run replaces them with what the LLM writes.

Rebuild the inputs (build PC): `python -m scripts.experiments.tiles.tile_same_plan --make-inputs <wide-tiles run dir> <wide-kpi run dir>`.

## Result (paid run 2026-10-14, test PC, `7eaac43`; rescored + sheet built on the build PC)

**Cost $0.483** (element refs $0.277, tiles $0.206). `summary.md` has the per-pair table.

| | element refs (A) | tiles (B) |
|---|---|---|
| first try compiled | 12 / 12 | 11 / 12 |
| final compiled | 12 / 12 | 12 / 12 |
| values off the plan | 0 | 0 |
| generator output tokens (first call) | 683–1,619 | 192–1,124 |
| smallest KPI number vs the other route | | larger 7, smaller 3, same 2 |

**The one tile repair:** all-nodes-dense slide 1 (tiles run's plan). The LLM wrote no tile tags and typed the tiles
itself with the same wrong numbers as in the wide run (₹4.4Cr / +18% / 4.2 / ₹1,200 for ₹14.2Cr / +38% / 2.4x /
₹410). Code caught it (`NODE_ITEM_MISSING`, fixed in `7ff656f`), the repair placed the plan's values. The numbers
are made up because under tiles the generator never sees KPI values (`tiles.prompt_line`: "no values"); the
element-ref line says "never type a label, value or note yourself", the tile line has no such sentence. The plan's
hint asks for a custom dark hero tile. 2 of 2 runs of this plan (wide run + this run); none of the other 11 tile runs here.

### Blind marks (user, 2026-10-14; `marks.csv`, `key.json`, `sheet-0*.png`)

"same" = the user likes both. 12 pairs: **tiles 0 wins, element refs 3 wins, 9 same** → **0.375 with a tie as
half; gate (tiles ≥ 0.5) failed.** Every decided pair went to element refs:

| pair | plan | user's reason | what the tile side did |
|---|---|---|---|
| 1.2 | kpi run, QBR 1 | "empty space occupied better" | the LLM put 4 `<Kpi>` tags in its own content-height HStack inside a `grow="3"` box: the tiles stop at their content, an empty band sits between them and the commentary (numbers 65 px, width-bound). The same pattern as CHEFFIN 1 in the wide run. |
| 1.4 | kpi run, CHEFFIN 1 | "better space allocation, was fit_grow not used" | `<KpiGrid ref="platform_kpis" layout="row"/>` beside the LLM's `w="max"` box holding one long bullet: the text box took the width, the two platform tiles were squeezed to a few characters wide (labels and numbers broken letter by letter). The `w="max"` squeeze (wide README P3), again on CHEFFIN 1 (paid check 3 had it too). The broken-word count missed it (0): a scorer gap. |
| 3.1 | tiles run, agency 2 | "I like the highlighted cards" | both routes toned the two CPC tiles bad; the element-ref side drew icons, stronger borders and shadows on the KPI and gap cards. Partly the KPI tiles, partly the card grid (not tile code). |

The 9 ties include the slides where tiles drew larger numbers (launch 3 85 vs 65 px, CHEFFIN 4 81 vs 44, CHEFFIN 1
tiles-plan 62 vs 48): larger numbers did not win a pair.

### What it says

- On the same plan, tiles draw KPIs about as well as element refs (9 of 12 the user likes both), cheaper (−26%
  cost, far fewer output tokens), with no wrong values reaching the slide. They lose on three things, two of them
  layout defects code can fix in general: a tile row that does not fill the growing box it sits in (2 slides: QBR
  here, CHEFFIN 1 in the wide run) and the `w="max"` text box squeezing a tile row (2 runs, both CHEFFIN 1). The
  third is the LLM decorating its own hand-written tiles more.
- The hand-typed tiles with invented numbers come from the tile prompt line not saying "never type a value" while
  the values are hidden: a prompt change, paid check needed.

## Layout fixes after the marks (2026-10-14, free, build PC; branch `feat/tile-nodes` after merging `feat/tile-cards`)

Each fix proven on the saved slides before and after (deck font Inter, as the pipeline compiles):
`tile_same_plan --rescore` on copies of this run (`sp-before` / `sp-after`) and a corpus pass over every distinct
saved slide (573 `input.xml` in `output/` and the `llm_test` zips) that a change can touch (105), compiled both ways,
rendered and scored where the fitted XML differs (41).

1. **The broken-word scorer missed letter-stacked words** (`scripts/experiments/phase0b/fontcheck.broken`). It joined only two
   pieces; a word drawn over three or more lines, or whose last letters merge with the large number below into one
   PDF word ("ROA" | "S0."), was not counted. Now a run of pieces on successive lines joins longest first, and the last
   piece may start the next word. Pair 1.4 (tiles): 0 → 4 broken (FLIP|CAR|T, ZAR|OM|A, ROA|S…×2), as the sheet showed.
2. **A long text box in `w="max"` squeezed the tile row beside it** (normalizer `TEXT_BOX_UNSQUEEZED`,
   `grow_fallback.unsqueeze_text_boxes`). POM gives a `w="max"` child flexGrow 1 with an *auto* basis (its text's
   one-line width) while a sibling with no `w` gets basis 0 (llm.md says `w="max"` "behaves as grow=1"): a 110-character
   bullet took 1015 of 1184 px. A `w="max"` box of 60+ characters of text (no table / chart) in a row where a sibling
   holds KPI tiles or cards (ids `kpiv-` / `kpih-` / `kpig-` / `card-`) gets `grow="1"`. First version (any sibling)
   touched 97 slides and hurt agency 2 (a checklist beside a quote: 0 → 10 broken words); restricted to tile / card
   siblings: 10 slides.
3. **A lone row of cards left an empty band** (fit-grow `fillLoneRows`, after the growth phases; `POM_FIT_LONE=0`
   turns it off). A row or grid of boxed stacks that is the only child of a taller box, still ≥ 40 px short of it
   after growth, takes the box (its rows too); kept only if nothing spills. A first version in the normalizer (before
   growth) took growth away from content-sized tiles (launch 3: 2 × 2 at 64 px → one row at 54; tiles-plan CHEFFIN 1
   62 → 54 px): moved after growth, both back to 64 / 62.

| same-plan pair (tiles side) | before | after |
|---|---|---|
| 1.4 CHEFFIN 1 (kpi plan) | numbers 28 px, 4 broken words | 69 px, 0 broken (element-ref side 41 → 51 px) |
| 1.2 QBR (kpi plan) | 65 px, ~150 px empty band under the tiles | 65 px, tiles fill the band (as the element-ref side the user preferred) |
| the other 10 | | unchanged |

Corpus (41 saved slides whose output changes): compiled 36 → 39, `w="max"` squeeze compile errors 5 → 2 (the three
paid-check-3 CHEFFIN 1 tries now compile; the 2 left are the 8-component agency slide), `WORD_TOO_WIDE` 4 → 0, broken
words 6 → 2 (the 2 left unchanged), smallest KPI number larger on 5 slides, smaller on 0. **`GEOM_CARD_EMPTY` 7 → 68**:
31 slides have a stretched row, whose cards are now taller than their text (XTSY 1's 3 × 2 grid now ends level with
the side panel; QBR 4's three cards reach the bottom). That is the trade the fix makes: an empty band becomes
taller cards. The renders read better to me; it is your call (`POM_FIT_LONE=0` restores the old look).

**Cards, the empty cards (2d):** re-scored on the merged branch, 4 left, both from the plans (card paid README, last
section). **Open (2e, not changed):** width share of a tile row beside a neighbour (all-nodes-dense 1: the longest
value gets no wider tile; CHEFFIN 1 platform row beside a callout).
