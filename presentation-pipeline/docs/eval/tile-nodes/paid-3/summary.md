# KPI paid check (generator only, POM_BLOCKS=tiles; arm A = the element-ref route, 2026-10-11)

Generator first call, mean tokens: in 10581, cached 7808, out 334; KPI XML tokens (first try) mean 14; hand-written tiles in tiles runs: 0.

9 runs, $0.143. Value refs placed on the first try: **48/48** (100%); runs with a NODE_* error on the first try: 0; final compiled: 9/9; repair passes (validator passes - 1): 3.

| run | first try | refs | passes | broken A / B | sizes A / B | card empty A / B | off-plan B | $ |
|---|---|---|---|---|---|---|---|---|
| deck-qbr-data-s1-r1 | ok (clean) | 4/4 | 1 | 0 / 0 | 91 / 58 | 0 / 0 | 0 | 0.023 |
| gate-deck-cheffin-full-s1-r1 | fail (NODE_VARIANT_UNMET) | 5/5 | 2 | 0 / 0 | 72; 69 / 28; 28 | 0 / 0 | 0 | 0.036 |
| gate-deck-cheffin-full-s4-r1 | ok (clean) | 7/7 | 1 | 0 / 0 | 28 / 66 | 8 / 0 | 0 | 0.010 |
| deck-qbr-data-s1-r2 | ok (clean) | 4/4 | 1 | 0 / 0 | 86 / 58 | 0 / 0 | 0 | 0.008 |
| gate-deck-cheffin-full-s1-r2 | fail (NODE_VARIANT_UNMET) | 5/5 | 2 | 0 / 0 | 72; 63 / 28; 28 | 0 / 0 | 0 | 0.020 |
| gate-deck-cheffin-full-s4-r2 | ok (clean) | 7/7 | 1 | 0 / 0 | 28 / 66 | 8 / 0 | 0 | 0.010 |
| deck-qbr-data-s1-r3 | ok (clean) | 4/4 | 1 | 0 / 0 | 86 / 58 | 0 / 0 | 0 | 0.008 |
| gate-deck-cheffin-full-s1-r3 | fail (NODE_VARIANT_UNMET) | 5/5 | 2 | 0 / 0 | 72; 72 / 28; 28 | 0 / 0 | 0 | 0.020 |
| gate-deck-cheffin-full-s4-r3 | ok (clean) | 7/7 | 1 | 0 / 0 | 28 / 66 | 8 / 0 | 0 | 0.008 |

Blind sheet: sheets/ (fill marks.csv; B plays the 'nodes' role in key.json).