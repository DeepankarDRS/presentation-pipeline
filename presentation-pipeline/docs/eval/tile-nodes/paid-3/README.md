# KPI tile nodes: paid check 3, fresh planner plans (2026-10-12, test PC)

On `d64108d` (fixes a / c / d and planner `kpi_tones`, `paid-2/README.md` "Fixes"). Planners first, then the
generator on their plans:

    python -m scripts.experiments.kpi.kpi_plan_only deck-qbr-data gate-deck-cheffin-full --repeat 1 --label p3        # $0.131
    python -m scripts.experiments.kpi.kpi_paid --blocks tiles --arm-a kpi --plans p3 --repeat 3 --label tiles-paid-3 --no-render --bundle   # $0.143

Arm B = tiles on the fresh plans (one plan per case, 3 generator tries); arm A = the 2026-10-11 element-ref slides,
recompiled. Re-scored and rendered on the build PC. **Not fully blind:** B's plans have their own headlines and
an extra callout, so the sides differ in content, not only in KPI drawing.

## Gate (spec §8): passed

| | result | gate |
|---|---|---|
| blind marks (user, `marks.csv`) | **0.67**: tiles win 6 (QBR ×3, CHEFFIN 4 ×3), lose 3 (CHEFFIN 1 ×3) | ≥ 0.5 |
| KPI output tokens | 14 a slide (first try, mean) vs ~400–760 hand-written | ≥ −50% |

Checks 1 → 2 → 3: 0.5 → 0.33 → 0.67.

## Accuracy and cost

Values placed on the first try 48/48; NODE_* errors 0; compiled 9/9; values off plan 0; broken words 0 / 0;
repairs 3 (all CHEFFIN 1). Generator $0.143 (9 runs), planners $0.131 (2 runs).

## Per slide

| slide | plan tones | tiles drew | marks | user's reason |
|---|---|---|---|---|
| QBR | good, good, bad, bad | one row, ARR / NRR numbers green, Gross Margin and CAC Payback tinted red; 58 px (a callout under the row: two rows measured 51 px, so the row was kept) | **tiles 3/3** | "better but heading needs color for kpi labels arr nrr" |
| CHEFFIN 1 | combined "", "", bad; platforms bad, bad | first try failed to compile ×3, repaired into narrow fixed widths, numbers 28 px | refs 3/3 | "better use of space", "need color though" |
| CHEFFIN 4 | none (the hint asks CPC red, Allowable CPC amber; the planner wrote no tones) | 4 + 3 grid in one white panel, 66 px, no colour | **tiles 3/3** | "need color though" |

CHEFFIN 1's failure is not a tile problem: the LLM put its callout in a `w="max"` box beside the tiles' `w="max"`
panel; POM sizes the callout to its unwrapped one-line text and squeezes the panel to zero width (`addTextBox:
width must be a finite positive EMU value`). Either route can hit it (removing that `w="max"`, or `grow` on both,
compiles). The repairer then pinned 320 / 480 px widths.

## Planner run (p3)

Tones were written on 3 of 4 KPI rows; CAC Payback "bad" is debatable (−2 months, but the brief's priority is
10 months). Outside the KPI slides the planners were less reliable than the previous planner-only run (9 runs:
0 empty components, 0 fallbacks): 4 components with unreadable `content_data_json` (two fixed by the re-ask, QBR's
chart slide left empty) and one slide (CHEFFIN 6) where gpt-5-mini spent its 16,000 tokens reasoning twice and
fell back. Candidates: `e2fed2d` (data conserved / composition prompt) or `27b7aae` (tones); not identified (the
log does not keep the raw text).

## Not done, on purpose

No further fixes from these three slides (user, 2026-10-12: do not fit the system to 3 examples). Open items are
general and need wider evidence before any change: KPI colour when the plan has no tones (CHEFFIN 4), label
colour, the `w="max"` squeeze, planner reliability.

Files: `sheet-01..03.png`, `marks.csv`, `key.json` (`nodes_side` = tiles), `summary.md`.
