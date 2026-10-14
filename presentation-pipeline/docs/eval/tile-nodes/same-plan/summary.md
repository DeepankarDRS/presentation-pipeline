# Tile nodes, same-plan check (generator only; A = POM_BLOCKS=kpi, B = POM_BLOCKS=tiles)

- **A (kpi)**: 12 runs, $0.277; first try compiled 12/12, NODE_* error on the first try 0, final compiled 12/12, repair passes 0, errors 0
- **B (tiles)**: 12 runs, $0.206; first try compiled 11/12, NODE_* error on the first try 1, final compiled 12/12, repair passes 1, errors 0

| slide plan | smallest number A / B (px) | card empty A / B | broken A / B | off-plan A / B | first try A / B | $ A / B |
|---|---|---|---|---|---|---|
| tiles-plan-deck-product-launch-data-s3-r1 | 58.0 / 64.0 | 1 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.031 / 0.023 |
| tiles-plan-deck-qbr-data-s1-r1 | 88.0 / 95.0 | 0 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.019 / 0.012 |
| tiles-plan-gate-deck-agency-takeover-s2-r1 | 26.0 / 26.0 | 1 / 1 | 0 / 0 | 0 / 0 | ok / ok | 0.030 / 0.025 |
| tiles-plan-gate-deck-all-nodes-dense-s1-r1 | 28.0 / 28.0 | 4 / 4 | 0 / 1 | 0 / 0 | ok / fail | 0.026 / 0.041 |
| tiles-plan-gate-deck-cheffin-full-s1-r1 | 48.0 / 62.0 | 0 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.017 / 0.013 |
| tiles-plan-gate-deck-cheffin-full-s4-r1 | 74.0 / 73.0 | 0 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.019 / 0.011 |
| kpi-plan-deck-product-launch-data-s3-r1 | 65.0 / 85.0 | 0 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.020 / 0.009 |
| kpi-plan-deck-qbr-data-s1-r1 | 67.0 / 65.0 | 1 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.016 / 0.011 |
| kpi-plan-gate-deck-all-nodes-dense-s1-r1 | 44.0 / 47.0 | 1 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.037 / 0.013 |
| kpi-plan-gate-deck-cheffin-full-s1-r1 | 41.0 / 28.0 | 1 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.021 / 0.015 |
| kpi-plan-gate-deck-cheffin-full-s2-r1 | 28.0 / 33.0 | 0 / 0 | 0 / 0 | 0 / 0 | ok / ok | 0.023 / 0.019 |
| kpi-plan-gate-deck-cheffin-full-s4-r1 | 44.0 / 81.0 | 0 / 1 | 0 / 0 | 0 / 0 | ok / ok | 0.018 / 0.013 |

Tiles' smallest number vs element refs on the same plan: larger 7, smaller 3, same 2.

Blind sheet: sheets/ (fill marks.csv; key.json: the 'nodes' side is tiles).