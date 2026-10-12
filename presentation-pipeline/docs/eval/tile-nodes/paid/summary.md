# KPI paid check (generator only, POM_BLOCKS=tiles; arm A = the element-ref route, 2026-10-11)

Generator first call, mean tokens: in 10449, cached 2688, out 320; KPI XML tokens (first try) mean 53; hand-written tiles in tiles runs: 0.

3 runs, $0.058. Value refs placed on the first try: **16/16** (100%); runs with a NODE_* error on the first try: 0; final compiled: 3/3; repair passes (validator passes - 1): 0.

| run | first try | refs | passes | broken A / B | sizes A / B | card empty A / B | off-plan B | $ |
|---|---|---|---|---|---|---|---|---|
| deck-qbr-data-s1-r1 | ok (clean) | 4/4 | 1 | 0 / 0 | 91 / 58 | 0 / 0 | 0 | 0.022 |
| gate-deck-cheffin-full-s1-r1 | ok (clean) | 5/5 | 1 | 0 / 0 | 72; 72 / 58; 28 | 0 / 0 | 0 | 0.025 |
| gate-deck-cheffin-full-s4-r1 | ok (clean) | 7/7 | 1 | 0 / 0 | 28 / 58 | 8 / 0 | 0 | 0.011 |

Blind sheet: sheets/ (fill marks.csv; B plays the 'nodes' role in key.json).