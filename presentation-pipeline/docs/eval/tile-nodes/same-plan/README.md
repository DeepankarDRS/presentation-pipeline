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
