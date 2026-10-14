# Tile nodes: same-plan check (generator only)

**Why.** In the wider paid run (`../wide-paid/README.md`) each route planned its own decks, so the blind marks
judged the text around the KPIs as much as the tiles: 3 of 5 pairs were decided on commentary / text sections.
Here both routes draw the **same** slide plans, so only the KPI drawing differs.

**What runs.** `inputs.json` holds every slide with a `kpi_row` in the two wide-paid runs: 12 plans (6 planned by
the tiles run, 6 by the element-ref run), each with its theme name and case request. Each plan goes through the
real graph from the plan twice (`scripts/kpi_paid.run_one`): arm **A** `POM_BLOCKS=kpi` (element refs, the
default) and arm **B** `POM_BLOCKS=tiles` (tile tags). Generator + validator + repairer as in a normal run, critic
off as in the eval runs; the slide is drawn alone (no deck context, no supplied data: the same for both arms).

**Command (test PC, branch `feat/tile-nodes`, after `git pull`):**

    python -m scripts.tile_same_plan --label same-plan --bundle

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

Rebuild the inputs (build PC): `python -m scripts.tile_same_plan --make-inputs <wide-tiles run dir> <wide-kpi run dir>`.

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
