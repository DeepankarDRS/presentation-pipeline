# KPI / card composition nodes: free replay (spec §10 step 4, 2026-11-01)

`python -m scripts.composition_replay --src C:/dev/presentation-pipeline/presentation-pipeline/output`
(sheets in `output/composition-replay/sheets/`, 10 sheets, 40 pairs; `marks.csv` / `key.json` here).

Saved KPI slides (kpi_replay sources, the LLM's ref tiles rewritten as one tile tag) and card slides (card_replay
sources), the LLM's layout kept. Both arms get the **bare** tag:
- **A** today's tile node: `<KpiGrid ref>` / `<CardGrid ref>`, POM_BLOCKS=tiles (hint styles via look_from_hint);
- **B** the composition node: `<KpiRow ref>` / `<CardGrid ref>`, POM_NODES=kpi_row,card_grid (the composition the
  design hint names, else the default from the content).

Only pairs whose drawing differs go on the blind sheet (40 of 131). Your marks: per pair left / right / same in
`marks.csv`; the gate is ≥ 0.5 (spec §10 step 4).

## KPI: 19 slides (0 drawn the same)

Compositions in B: grid 22, bento 2

| | A today | B composition |
|---|---|---|
| compiled | 19 | 19 |
| GEOM_CARD_EMPTY | 9 | 13 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 0 | 0 |
| WORD_TOO_WIDE | 0 | 0 |
| LOW_CONTRAST | 0 | 0 |
| plan text missing / off plan | 0 | 0 |
| B errors | | 2 |

B issues: NODE_LOOK_FROM_HINT 5, NODE_FOCUS_UNNAMED 1, NODE_VALUE_TEXT 1, NODE_ATTR_IGNORED 1, NODE_ITEM_MISSING 1

## CARD: 112 slides (91 drawn the same)

Compositions in B: grid 83, steps 35, bento 4

| | A today | B composition |
|---|---|---|
| compiled | 111 | 111 |
| GEOM_CARD_EMPTY | 114 | 127 |
| GEOM_SLIDE_SPARSE | 2 | 2 |
| broken words (render) | 31 | 31 |
| WORD_TOO_WIDE | 6 | 6 |
| LOW_CONTRAST | 6 | 6 |
| plan text missing / off plan | 0 | 0 |
| B errors | | 2 |

B issues: NODE_DEFAULT_FROM_CONTENT 35, NODE_LOOK_FROM_HINT 12, NODE_FIELD_MISSING 2, NODE_BYPASSED 1, NODE_LABEL_MISSING 1, NODE_LABEL_PLACED 1

## Reading the scorecard
- **KPI: the fitted XML differs on all 19.** Expected sources: B's `grid` draws the plan's emphasis tile dark with a
  hero value when the plan singles one out (spec §5.1; today only when the hint says "dark"), and two hints named a
  hero ("... as the hero") -> `bento`. Not checked slide by slide; the blind sheet shows it.
- **Cards: 91 of 112 drawn the same:** a bare `grid` / `steps` gives today's card. The 21 that differ: a slide's
  second card group (today the `column` variant, now the `column` recipe over the lifted card), hint styles as
  recipes over the lifted card (`accent_top`), and 4 hint-driven `bento`.
- **No saved hint asks for `strip`, `rows`, `banded` or `columns`:** they appear only when the generator writes the
  word (the paid step, not run).
- **GEOM_CARD_EMPTY up** (KPI 9 -> 13: all four on one `bento` slide, colour-roles QBR s1; cards 114 -> 127, on the
  21 differing slides). Report-only, as before; your marks decide.
- **B errors 2:** both also in A (hand-drawn KPI refs on those saved slides), not from the nodes.
- Broken words, WORD_TOO_WIDE, LOW_CONTRAST, missing / off-plan text: equal in both arms.
