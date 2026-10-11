# KPI node pilot: paid check (generator only, POM_BLOCKS=kpi)

9 runs, $0.296. Value refs placed on the first try: **48/48** (100%); runs with a NODE_* error on the first try: 0; final compiled: 9/9; repair passes (validator passes - 1): 2.

| run | first try | refs | passes | broken A / B | sizes A / B | card empty A / B | off-plan B | $ |
|---|---|---|---|---|---|---|---|---|
| deck-qbr-data-s1-r1 | ok (NODE_ATTR_IGNORED, NODE_FIELD_MISSING) | 4/4 | 1 | 0 / 0 | 32 / 91 | 0 / 0 | 0 | 0.029 |
| gate-deck-cheffin-full-s1-r1 | ok (clean) | 5/5 | 1 | 0 / 0 | 71; 51 / 72; 72 | 0 / 0 | 0 | 0.030 |
| gate-deck-cheffin-full-s4-r1 | ok (NODE_ATTR_IGNORED) | 7/7 | 1 | 0 / 0 | 28 / 28 | 7 / 8 | 0 | 0.031 |
| deck-qbr-data-s1-r2 | fail (NODE_ATTR_IGNORED) | 4/4 | 2 | 0 / 0 | 32 / 86 | 0 / 0 | 0 | 0.042 |
| gate-deck-cheffin-full-s1-r2 | ok (clean) | 5/5 | 1 | 0 / 0 | 71; 51 / 72; 66 | 0 / 0 | 0 | 0.030 |
| gate-deck-cheffin-full-s4-r2 | ok (NODE_ATTR_IGNORED) | 7/7 | 1 | 0 / 0 | 28 / 28 | 7 / 8 | 0 | 0.031 |
| deck-qbr-data-s1-r3 | fail (NODE_ATTR_IGNORED) | 4/4 | 2 | 0 / 0 | 32 / 86 | 0 / 0 | 0 | 0.042 |
| gate-deck-cheffin-full-s1-r3 | ok (clean) | 5/5 | 1 | 0 / 0 | 71; 51 / 72; 72 | 0 / 0 | 0 | 0.030 |
| gate-deck-cheffin-full-s4-r3 | ok (clean) | 7/7 | 1 | 0 / 0 | 28 / 28 | 7 / 8 | 0 | 0.030 |

Blind sheet: sheets/ (fill marks.csv; B plays the 'nodes' role in key.json).