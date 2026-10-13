# KPI tile nodes: wider paid run, full decks (2026-10-13, test PC)

Both routes on commit `a74db88` (P1 tile padding 16 / 6 and P2 hint tones built). The six step-0 decks, one repeat each:

    $env:POM_BLOCKS="tiles"; python -m scripts.eval_run deck-qbr-data deck-product-launch-data gate-deck-agency-takeover gate-deck-xtsy-qcomm gate-deck-cheffin-full gate-deck-all-nodes-dense --repeat 1 --label wide-tiles --bundle
    $env:POM_BLOCKS="kpi";   python -m scripts.eval_run <same six cases> --repeat 1 --label wide-kpi --bundle

Each route plans its own decks, so plans, headlines and KPI groupings differ between the arms. The blind pairs
compare the same case and slide, not the same plan. Bundles: `output/wide-paid/{tiles,kpi}/` (gitignored).

## Decks (eval summaries)

| | tiles | kpi (element refs) |
|---|---|---|
| cost | **$1.45** | **$1.30** (both $2.74; estimate was $3.5–4.0) |
| decks passed / slides compiled | 6 / 6, 37 / 37 | 6 / 6, 37 / 37 |
| first try | 34 / 37 (91.9%) | 34 / 37 (91.9%) |
| retries (all on non-KPI slides) | width squeeze (agency 1), `<Ul gap>` (agency 4), height squeeze (xtsy 6) | `shadow="outer"` parse error ×3 (agency 0, 1, 3) |
| mean card fill / low-fill cards | 0.842 / 17.0% | 0.854 / 14.1% |
| word breaks / overflows per slide | 0.16 / 0 | 0.19 / 0.16 |
| table spill | 0 | 1 slide, 83 px |
| invented numbers (eval) | 4: **3 real** (below) + "12" | 8: all slide numbers "01"–"06", **0 real** |

## KPI slides

The planner wrote `kpi_tones` on every KPI row in both arms (8 / 8 and 8 / 8), so P2 never fired. Number sizes
(px, from the fitted XML):

| slide | tiles | kpi |
|---|---|---|
| QBR 1 | 95 | 67 |
| product launch 3 | 54 | 70 |
| CHEFFIN 1 | 51 | 82 / 95 |
| CHEFFIN 4 | 73 | 46 |
| all-nodes-dense 1 | **typed by hand, wrong numbers** | 43 / 72 |
| agency 2 (tiles only) | 26 | — |
| CHEFFIN 2 (kpi only) | — | 28 |

**The one real failure (tiles, all-nodes-dense slide 1):** the LLM wrote neither tile tags nor refs and typed the
tiles itself with numbers the plan does not have (₹4.4Cr / +18% / 4.2 / ₹1,250 for ₹14.2Cr / +38% / 2.4x / ₹410).
Code should have caught it: a value that is not on the slide is `NODE_ITEM_MISSING`, an error that sends the
slide to repair. But `element_refs.fill_refs` unpacked the plan's fields out of order (`values, labels, notes`
against `FIELDS = label, value, note`), so it looked for the label, found it typed, and kept the slide with a
`NODE_BYPASSED` warning. The bug dates from 2026-10-11 and sits on both routes. The two earlier deck runs on the
element-ref route never had a hand-typed KPI slide (0 invented numbers), so it had not shown before. **Fixed
after this run** (regression test `test_a_typed_label_with_a_wrong_typed_value_is_missing_not_bypassed`): a
wrong typed value is now an error and goes to repair; a right typed value stays a warning.

## Blind marks (yours)

`sheet-01.png` (pairs 1–3) and `sheet-02.png` (pairs 4–5): the same case and slide on both routes, sides
shuffled. Write 1, 2 or = and a reason in `marks.csv`; `key.json` says which side is tiles (open it only after
marking). Gate as before: tiles ≥ 0.5. One pair has the wrong-number slide on one side; a slide with wrong numbers
loses whatever it looks like.

## Planner log lines

Neither bundle includes the console log; the `.log` files hold the planner's new failure lines (step 2). Filter:

    Select-String -Path wide-tiles.log, wide-kpi.log -Pattern "invalid content_data_json|hit the output limit|failed twice|taken from the design hint|Traceback"
