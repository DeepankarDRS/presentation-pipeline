# KPI node pilot: free replay

Arm A = the saved XML on today's compiler; arm B = the same XML with each KPI text mapped to a ref and filled by `element_refs.fill_refs`. Produced by `python -m scripts.experiments.kpi.kpi_replay`.

## Today (7 slides, 9 kpi_row components)

Mapping rate: values 34/34 (100%), labels 34/34 (100%), notes 14/14 (100%).

| | A (today) | B (refs) |
|---|---|---|
| compiled | 7 | 7 |
| WORD_TOO_WIDE | 7 | 7 |
| broken words in the render | 1 | 1 |
| components with one number size | 9 / 9 | 9 / 9 |
| GEOM_CARD_EMPTY | 8 | 9 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| LOW_CONTRAST | 4 | 4 |
| plan values not on the slide | 0 | 0 |

| slide | values mapped | A sizes | B sizes (hero) | broken A / B | fill A / B | contrast A / B |
|---|---|---|---|---|---|---|
| q1008-deck-product-launch-data__r1 / 3 | 4/4 | 34 | 28 | 0 / 0 | 0 / 0 | 0 / 0 |
| q1008-deck-qbr-data__r1 / 1 | 4/4 | 32 | 60 | 0 / 0 | 0 / 0 | 1 / 1 |
| q1008-gate-deck-agency-takeover__r1 / 0 | 5/5 | 22 | 28 | 0 / 0 | 0 / 0 | 0 / 0 |
| q1008-gate-deck-all-nodes-dense__r1 / 1 | 5/5 | 30; 72 | 28;  (76) | 1 / 1 | 0 / 0 | 2 / 2 |
| q1008-gate-deck-cheffin-full__r1 / 1 | 5/5 | 71; 51 | 70; 51 | 0 / 0 | 0 / 0 | 0 / 0 |
| q1008-gate-deck-cheffin-full__r1 / 4 | 7/7 | 28 | 28 | 0 / 0 | 7 / 8 | 0 / 0 |
| run1008-deck-qbr-data-30cd7b / 1 | 4/4 | 48 | 45 | 0 / 0 | 1 / 1 | 1 / 1 |

## Older routes (12 slides, 15 kpi_row components)

Mapping rate: values 44/45 (98%), labels 45/46 (98%), notes 22/28 (79%).

| | A (today) | B (refs) |
|---|---|---|
| compiled | 12 | 12 |
| WORD_TOO_WIDE | 0 | 0 |
| broken words in the render | 0 | 0 |
| components with one number size | 15 / 15 | 15 / 15 |
| GEOM_CARD_EMPTY | 9 | 12 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| LOW_CONTRAST | 5 | 5 |
| plan values not on the slide | 0 | 0 |

| slide | values mapped | A sizes | B sizes (hero) | broken A / B | fill A / B | contrast A / B |
|---|---|---|---|---|---|---|
| step0-deck-qbr-data__r1 / 1 | 4/4 | 120; 62 |  (120); 61 | 0 / 0 | 0 / 0 | 1 / 1 |
| step0-deck-product-launch-data__r1 / 3 | 4/4 | 86 | 86 | 0 / 0 | 0 / 0 | 0 / 0 |
| step0-gate-deck-all-nodes-dense__r1 / 1 | 5/5 | 28; 120 | 28;  (120) | 0 / 0 | 0 / 0 | 0 / 0 |
| step0-gate-deck-cheffin-full__r1 / 1 | 5/5 | 43 | 40 | 0 / 0 | 0 / 0 | 0 / 0 |
| step0-gate-deck-cheffin-full__r1 / 4 | 7/7 | 89; 77 | 89; 77 | 0 / 0 | 0 / 0 | 0 / 0 |
| colour-deck-qbr-data__r1 / 1 | 4/4 | 85 | 85 | 0 / 0 | 0 / 0 | 1 / 1 |
| critic-on-deck-qbr-data-5fb8a2 / 1 | 4/4 | 47 | 48 | 0 / 0 | 4 / 5 | 1 / 1 |
| critic-on-deck-qbr-data-5fb8a2 / 4 | 3/3 | 66 | 65 | 0 / 0 | 0 / 0 | 0 / 0 |
| critic-on-deck-qbr-data-5fb8a2 / 5 | 1/2 | 85 | 82 | 0 / 0 | 0 / 2 | 1 / 1 |
| critic-on2-deck-qbr-data-e2e624 / 1 | 4/4 | 38 | 38 | 0 / 0 | 4 / 4 | 1 / 1 |
| critic-on2-deck-qbr-data-e2e624 / 4 | 1/1 | 72 |  (72) | 0 / 0 | 0 / 0 | 0 / 0 |
| critic-on2-deck-qbr-data-e2e624 / 5 | 2/2 | 96 | 95 | 0 / 0 | 1 / 1 | 0 / 0 |

Misses (plan text with no Text of its own):

- step0-deck-product-launch-data__r1 / 3 `kpi_scorecards.0.note` "(-89%)": merged into a longer text
- step0-deck-product-launch-data__r1 / 3 `kpi_scorecards.1.note` "(-92%)": merged into a longer text
- step0-deck-product-launch-data__r1 / 3 `kpi_scorecards.2.note` "(-73%)": merged into a longer text
- step0-deck-product-launch-data__r1 / 3 `kpi_scorecards.3.note` "(+49 pts)": merged into a longer text
- critic-on-deck-qbr-data-5fb8a2 / 5 `headline_kpis.2.value` "142 enterprise customers": merged into a longer text
- critic-on-deck-qbr-data-5fb8a2 / 5 `headline_kpis.2.label` "Enterprise customers": merged into a longer text
- critic-on2-deck-qbr-data-e2e624 / 5 `kpi_metrics.0.note` "(-1.4 pts)": merged into a longer text
- critic-on2-deck-qbr-data-e2e624 / 5 `kpi_metrics.1.note` "(-2 months)": merged into a longer text
