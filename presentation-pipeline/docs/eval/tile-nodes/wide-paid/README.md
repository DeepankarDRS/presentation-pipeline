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

## Blind marks (user, 2026-10-13; `marks.csv`, `key.json`)

| pair | slide | tiles side | chosen | winner | user's reason |
|---|---|---|---|---|---|
| 1 | QBR 1 | 2 | 1 | kpi | better content for the commentary section |
| 2 | product launch 3 | 2 | 2 | tiles | better content for the text section |
| 3 | CHEFFIN 1 | 2 | 1 | kpi | text could have been better, but 2 sections were better |
| 4 | CHEFFIN 4 | 1 | 1 | tiles | better use of space |
| 5 | all-nodes-dense 1 | 2 | 2 | (tiles side) | space allocation is better |

**Score: 0.6 as marked (tiles 3 of 5); 0.4 under the agreed rule** that a slide with wrong numbers loses: pair 5's
tiles side is the hand-typed slide with four wrong numbers, and it was not drawn by tiles at all (no tile tags).
Gate: tiles ≥ 0.5, so **failed** under the rule.

What the marks measure: pairs 1–3 were decided on the text around the KPIs ("commentary", "text section"). Those
texts come from each arm's own plan and generator call, not from how KPI tiles are drawn. Pair 4 is the one
decision on a tile-drawn KPI block (tiles' 4 + 3 grid at 73 px vs the element-ref row of six at 46 px plus a large
callout): tiles won. With one plan per arm, this run cannot separate the KPI drawing from the content.

## Planner log lines

Neither bundle includes the console log; the `.log` files hold the planner's new failure lines (step 2). Filter:

    Select-String -Path wide-tiles.log, wide-kpi.log -Pattern "invalid content_data_json|hit the output limit|failed twice|taken from the design hint|Traceback"

Result (user), matched to the saved plans:

| log line | slide | outcome |
|---|---|---|
| `hit the output limit … 16000 of 16000 output tokens were reasoning` ×3 | tiles: agency 5, CHEFFIN 6, XTSY 6 (first tries) | second try fine; ≈ $0.10 wasted |
| `invalid content_data_json` on 3 components | tiles: agency 6, first try | second try fine |
| `invalid content_data_json` on all 5 components, **both tries** ("Expecting property name", then "Expecting value") | kpi: XTSY 5 "How Our Commerce Intelligence Platform…" | **plan kept with every component empty; the generator wrote the TRACKING / INSIGHTS lists and the tagline itself** (none from the brief; no numbers, so the invented-number check passed it) |

Every log line was cut at about 100 characters (PowerShell saves a console log at the window width), so the
start of the unreadable text that step 2 logs was lost. The error types say the whole call broke the same way
(single-quoted keys or not JSON at all), not one field.

**Fixed after this run (free):**
1. `plan_checks.holds_no_content`: a plan whose components past the title / captions carry no content at all
   (cover and closing slides excepted: their visual may be decoration) is re-asked (`PLAN_EMPTY` "no component
   holds any content"), and when the second answer is still empty the slide gets `fallback_plan` (the brief's
   own lines) instead of the generator's inventions. Across 1,989 saved plans it catches 7, all empty.
2. `eval_run` writes `run.log` (every log line, UTF-8, uncut) into the run folder, so the bundle carries it.

Open: the cause of the unreadable `content_data_json`. The schema asks for JSON inside a string; the other
session's typed-schema work (its sections 3 / 4: typed content data instead of a JSON string) would remove the
parse step, and needs a paid check.
