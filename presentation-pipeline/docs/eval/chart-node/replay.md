# Chart node: free replay (LLM layout kept), arm B = <Chart ref>

Slides: 56 (one chart component with an id, one hand-drawn <Chart>); the LLM's chart card replaced with the chart on 47. B compositions: {'native': 55}.

| | A (LLM's chart) | B (Chart tag) |
|---|---|---|
| compiled | 54 | 54 |
| chart labels missing vs the plan | 2 | 3 |
| chart values changed vs the plan | 27 | 3 |
| GEOM_CARD_EMPTY | 9 | 13 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 9 | 12 |
| text overlaps (render) | 12 | 9 |
| WORD_TOO_WIDE | 9 | 9 |
| LOW_CONTRAST | 19 | 19 |
| chart output tokens | 15351 | 1020 (-93%) |

B issues: {'NODE_ITEM_MISSING': 1}

## Notes (2026-10-28)

- Command: `python -m scripts.chart_replay --src <main checkout>/output` (POM_NODES=chart, Inter render). Blind sheets
  and `marks.csv` in `output/chart-replay/sheets/` (`key.json` there says which side is which).
- Fixed before this run: on 3 dense slides the node's card was taller than the LLM's (the inner Chart's own
  `minH="160"` on top of the card's padding and title), fit-grow starved a text box to 0 px and the slide failed to
  build. A card the LLM sized (`h` / `minH`) now holds the chart with no minimum of its own. B compiled 51 → 54.
- B's 3 label / 3 value misses are one slide whose plan gives 4 labels and 3 values: `NODE_ITEM_MISSING` (error →
  repair in a live run). A changed a plan value 27 times.
- B is worse on one slide only (`r2-gj-h1-regen-bf396b-s6-429b`): broken words 0 → 3, empty cards 2 → 5. The LLM
  drew that donut as an 80 × 32 px mark beside a table; the bare tag draws a full chart card in that box. Not fixed
  (one example): a size floor for the chart card, or the LLM keeps tiny inline marks, is a question for the marks.
- Every B chart is `native` (bare tags). `--variant rows` / `--variant "native labelled"` replay the other compositions.

## Blind marks (user, 2026-10-28): gate passed

53 of 54 pairs marked (`marks.csv`, `key.json` here): **B 3 · A 7 · same 43**. User rule: "same" counts as
satisfied, so **(B + same) / marked = 0.868 ≥ 0.5, passed** (0.462 when "same" counts as half).

Why A won (the user's reasons): space occupied (1.1); spacing, and a smaller font for the Q3 FY26 label (2.1);
different colours (2.3); the icon in the chart's title row ("logo", 2.4); no reason (4.1); A had content (11.2);
the chart was the slide's highlight (14.1). Why B won: consistent, no icon (3.2); bigger (4.3); no overlap (9.1).
Open from these, not built (each one example so far): an icon in the chart card's title row (`icon` on the tag), and
per-bar colours the LLM chose over the one-hue focus rule.
