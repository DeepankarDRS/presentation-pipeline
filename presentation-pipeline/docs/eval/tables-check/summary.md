# Eval `tables-check`

2026-09-24T14:49:47 · commit `77000c3` · models.yaml `919e01fa` · 6 runs, 19 slides

| metric | value |
|---|---|
| runs_passed | 6 |
| runs_errored | 0 |
| slide_count_off | 0 |
| compiled_pct | 100.0 |
| first_pass_pct | 94.7 |
| mean_retries | 0.05 |
| cards | 89 |
| mean_fill | 0.892 |
| low_fill_pct | 14.6 |
| word_breaks_per_slide | 0.05 |
| text_overflows_per_slide | 0.16 |
| table_spill_slides | 3 |
| table_spill_px | 88 |
| tables_overfull_slides | 4 |
| empty_cells | 0 |
| invented_numbers | 79 |
| auto_fixes_per_slide | 0.05 |
| layout_issues_per_slide | 0.11 |
| fit_grow_changes_per_slide | 2.11 |
| tokens_in | 383005 |
| tokens_out | 55136 |
| cost_usd | 1.2071 |
| elapsed_s | 109.2 |

Fill = card content height ÷ inner height (1.0 = no dead space); low fill < 0.7. Word breaks = text boxes narrower than their longest word; text overflows = text needing 2+ lines more than its box; table spill = table rows past their frame (slides, px); tables over-full = slides where fit-grow could not fit a table (the slide holds more than 720 px); empty cells = blank table cells (dropped data); invented numbers = numbers on slides that are not in the brief; slide_count_off = runs whose slide count differs from the case target.

## Cases

| case | run | pass | slides (target) | first-pass | retries | mean fill | low-fill cards | word breaks | overflows | invented numbers | layout issues | golden match |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single-table | 1 | PASS | 1 (1) | 1/1 | 0 | 0.67 | 1 | 0 | 0 | 16 | 0 | - |
| chart-and-table | 1 | PASS | 1 (1) | 1/1 | 0 | 0.71 | 1 | 0 | 0 | 16 | 0 | - |
| eval-table-vs-kpi-disambiguation | 1 | PASS | 1 (1) | 1/1 | 0 | 0.65 | 1 | 0 | 0 | 2 | 0 | - |
| mixed-executive-slide | 1 | PASS | 1 (1) | 1/1 | 0 | 0.9 | 1 | 0 | 0 | 14 | 0 | - |
| maximal-density | 1 | PASS | 1 (1) | 1/1 | 0 | 0.96 | 0 | 0 | 0 | 29 | 0 | - |
| gj-h1-regen | 1 | PASS | 14 (14) | 13/14 | 1 | 0.9 | 9 | 1 | 3 | 2 | 2 | 0.547 |

## Auto-fix codes (first attempt)

- `AMPERSAND_ESCAPED`: 1

## Blocking codes during retries

- `UNKNOWN_ATTRIBUTE`: 6

## Blocking messages (first 3 per slide)

- `UNKNOWN_ATTRIBUTE: <Tr>.<Td>: Unknown attribute "borderLeft"`: 1

## Layout-audit codes (final attempt)

- `COL_WIDTH_SUM`: 1
- `XML_PARSE_ERROR`: 1

## Card patterns

- `kpi_tile`: 30
- `text_card`: 22
- `table_card`: 17
- `chart_card`: 12
- `dark_panel`: 8

## Planner component kinds

- `title`: 15
- `table`: 13
- `bullet_list`: 10
- `narrative`: 7
- `kpi_row`: 7
- `chart`: 6
- `timeline`: 2

## Lowest-fill slides

- gj-h1-regen run 1 slide 12: min fill 0.245
- chart-and-table run 1 slide 0: min fill 0.425
- gj-h1-regen run 1 slide 8: min fill 0.459
- eval-table-vs-kpi-disambiguation run 1 slide 0: min fill 0.51
- mixed-executive-slide run 1 slide 0: min fill 0.519
- gj-h1-regen run 1 slide 2: min fill 0.599
- gj-h1-regen run 1 slide 5: min fill 0.638
- gj-h1-regen run 1 slide 0: min fill 0.643
- gj-h1-regen run 1 slide 10: min fill 0.644
- gj-h1-regen run 1 slide 6: min fill 0.654
