# Card paid check (generator on fresh plans, POM_BLOCKS=tiles; arm A = the saved hand-drawn slides)

14 runs (22 skipped: the planner made no card_grid), $0.282. First try compiled: 12/14; NODE_* error on the first try: 0; final compiled: 13/14; repair passes: 2; cards drawn by hand instead of tags: 3; card tag tokens, mean: 12.

| | A (saved, hand-drawn) | B (tiles, fresh plan) |
|---|---|---|
| compiled | 13 | 13 |
| GEOM_CARD_EMPTY | 0 | 7 |
| broken words / overlaps (render) | 3 / 3 | 1 / 0 |
| LOW_CONTRAST | 3 | 0 |
| plan text missing | 0 | 22 |
| smallest card title / body (median px) | 26.0 / 20.0 | 26.0 / 25.0 |

Blind sheet: sheets/ (fill marks.csv; key.json after marking). Plans: B/<run>/plan.json.
