# Tile nodes: combined paid check (prompt + planner changes, both routes) — PREPARED, NOT RUN

**Why.** Two changes from the last two paid checks need a paid run before they can count:

1. **"Never type the text yourself" in the tile and card prompt lines.** Under `POM_BLOCKS=tiles` the generator
   never sees KPI values, and its tile line did not say "never type a value" (the element-ref line does). On 2 of 2
   runs of the all-nodes-dense slide 1 plan the LLM typed the KPI tiles itself with made-up numbers (₹4.4Cr / +18% /
   4.2 / ₹1,200 for ₹14.2Cr / +38% / 2.4x / ₹410; caught by `NODE_ITEM_MISSING`, repaired) — wide-paid and same-plan
   runs. Cards: QBR r2 drew its 3 cards by hand and dropped the 3 body lines (card paid check). Built:
   `tiles.prompt_line` ends "never type a label, value or note yourself: code writes them from the plan",
   `cards.prompt_line` "never type a title, tag or body yourself".
2. **The planner gives each KPI item an icon** (`kpi_icons`, every item or none, real Lucide names; cleaned by
   `plan_checks.settle_kpi_icons`), as cards got per-card icons. Tiles draw the plan's icon unless the LLM names one;
   the element-ref line names them ("Icons from the plan: 0=wallet, ..."). Evidence: same-plan pair 3.1 (agency 2),
   the one decoration loss, where the element-ref side drew icons on its KPI tiles and the tile side had none.

**What runs** (`python -m scripts.tile_combined`): part 1, the planners only (`kpi_plan_only.plan_case`) on the six
decks, once each; part 2, every planned slide with a `kpi_row` or a `card_grid` drawn on that same plan by both routes,
twice: arm **A** `POM_BLOCKS=kpi` (element refs; cards drawn by hand, as today's default), arm **B** `POM_BLOCKS=tiles`
(KPI and card tags). Real graph from the slide plan (generator, validator, repairers; critic off). Free on the build
PC afterwards: `--rescore` (Inter renders, scores, blind sheet).

**Command (test PC, branch `feat/tile-nodes`, after `git pull`):**

    python -m scripts.tile_combined --label combined --bundle --no-render

It prints `EMAIL THIS FILE: output/tile-combined/combined.zip` (plans.json, runs.json, run.log, every run's first /
final XML). On the build PC: `python -m scripts.tile_combined --label combined --rescore` → `summary.md`, `sheets/`.

**Cases:** deck-qbr-data, deck-product-launch-data, gate-deck-agency-takeover, gate-deck-all-nodes-dense,
gate-deck-cheffin-full, gate-deck-xtsy-qcomm.

**Cost estimate (from saved manifests):**

| part | basis | estimate |
|---|---|---|
| plans, 6 decks × 1 | card-plans runs (same planner, 18 runs): $0.04–0.15 per deck, $0.51 per set of six | $0.51 |
| draws, ~19 KPI / card slides × 2 arms × 2 repeats = ~76 | same-plan: A $0.023, B $0.017 per slide; card paid B $0.020 | ~$1.60 |
| **total** | | **≈ $2.1, ceiling ≈ $2.8** (more slides on a fresh plan, repairs) |

`--repeat 1` halves the draws (≈ $1.3 in all, ceiling ≈ $1.7). KPI / card slides per set of six (card-plans runs):
QBR 2, launch 2–3, agency 3–5, all-nodes-dense 2–3, CHEFFIN 2–3 (KPI only), XTSY 6–7 (cards).

**Scored** (summary.md per slide): KPI number sizes, card title sizes, GEOM_CARD_EMPTY, broken words, plan text
missing, values off the plan, icons drawn (plan icons on the slide / planned), first try, cost; per arm: KPI tiles
typed by hand and cards drawn by hand (B), NODE_* errors, repairs. Then the blind marks (A vs B on the same plan).

**What passes:** B hand-typed KPI tiles 0 and hand-drawn cards ≤ 1 (from 2 / 2 and 1 of 14); values off the plan 0
on both arms; the planner writes `kpi_icons` on most KPI rows; blind marks tiles ≥ 0.5.

**Dry run (free, build PC, fake planner = the saved same-plan / card paid plans, fake generator = bare tags for B,
their expansion for A):** `python -m scripts.tile_combined deck-qbr-data gate-deck-agency-takeover --label
combined-dry-t3 --dry --repeat 1`: 2 decks, 6 KPI / card slides, 12 / 12 runs compiled first try, scores, renders and
the blind sheet built. (The saved plans have no `kpi_icons` yet, so the icon column reads 0 / 0 in the dry run.)
Use a fresh `--label` per run: two runs on one label overwrite each other's folders.
