# Eval `kpi-decks`

2026-10-11T21:29:10 · commit `a1cc01c` · models.yaml `2518d873` · 4 runs, 25 slides

| metric | value |
|---|---|
| runs_passed | 4 |
| runs_errored | 0 |
| slide_count_off | 0 |
| compiled_pct | 96.0 |
| first_pass_pct | 88.0 |
| mean_retries | 0.08 |
| cards | 112 |
| mean_fill | 0.828 |
| low_fill_pct | 23.2 |
| word_breaks_per_slide | 0.48 |
| text_overflows_per_slide | 0.0 |
| table_spill_slides | 0 |
| table_spill_px | 1 |
| tables_overfull_slides | 0 |
| empty_cells | 0 |
| invented_numbers | 0 |
| auto_fixes_per_slide | 2.08 |
| layout_issues_per_slide | 1.56 |
| fit_grow_changes_per_slide | 2.04 |
| tokens_in | 623482 |
| tokens_out | 140992 |
| cost_usd | 1.1255 |
| elapsed_s | 1335.2 |

Fill = card content height ÷ inner height (1.0 = no dead space); low fill < 0.7. Word breaks = text boxes narrower than their longest word; text overflows = text needing 2+ lines more than its box; table spill = table rows past their frame (slides, px); tables over-full = slides where fit-grow could not fit a table (the slide holds more than 720 px); empty cells = blank table cells (dropped data); invented numbers = numbers on slides that are not in the brief; slide_count_off = runs whose slide count differs from the case target.

## Cases

| case | run | pass | slides (target) | first-pass | retries | mean fill | low-fill cards | word breaks | overflows | invented numbers | layout issues | golden match |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deck-qbr-data | 1 | PASS | 5 (5) | 5/5 | 0 | 0.78 | 3 | 0 | 0 | 0 | 4 | - |
| gate-deck-cheffin-full | 1 | PASS | 6 (6) | 4/6 | 1 | 0.84 | 7 | 2 | 0 | 0 | 8 | - |
| gate-deck-all-nodes-dense | 1 | PASS | 6 (6) | 5/6 | 1 | 0.8 | 8 | 9 | 0 | 0 | 16 | - |
| gate-deck-xtsy-qcomm | 1 | PASS | 8 (8) | 8/8 | 0 | 0.85 | 8 | 1 | 0 | 0 | 11 | - |

## Auto-fix codes (first attempt)

- `NODE_ATTR_IGNORED`: 25
- `TEXT_WHITESPACE_TRIMMED`: 6
- `NODE_FIELD_MISSING`: 4
- `GROW_LONE_CARD`: 3
- `ZERO_SPACING`: 3
- `NODE_FOCUS_UNNAMED`: 2
- `BORDER_ACCENT_FIX`: 2
- `GROW_ROWS_ADDED`: 2
- `DARK_PANEL_SOFTENED`: 2
- `AMPERSAND_ESCAPED`: 2
- `TABLE_NUMERIC_COLS_SHARED`: 1

## Blocking codes during retries

- `INVALID_CHILD`: 2
- `RENDER_ERROR`: 1
- `INVALID_VALUE`: 1

## Blocking messages (first 3 per slide)

- `RENDER_ERROR: addShape: fill.color must be an srgb 6-digit hex color`: 1
- `INVALID_VALUE: addTextBox: width must be a finite positive EMU value`: 1
- `INVALID_CHILD: <Icon> is not allowed inside <Text>. <Text> holds text + inline tags only (A, B, I, Mark, S, Span, Sub, Sup, U). Put plain text there; to show icons/layout, split into sibling nodes inside an <HStack>`: 1
- `INVALID_CHILD: <Text> is not allowed inside <Text>. <Text> holds text + inline tags only (A, B, I, Mark, S, Span, Sub, Sup, U). Put plain text there; to show icons/layout, split into sibling nodes inside an <HStack>`: 1

## Layout-audit codes (final attempt)

- `GEOM_CARD_EMPTY`: 19
- `GEOM_COLLISION`: 7
- `LOW_CONTRAST`: 6
- `GEOM_BOX_EMPTY`: 3
- `GEOM_SPILL`: 3
- `LITERAL_COLOR`: 1

## Card patterns

- `text_card`: 68
- `kpi_tile`: 28
- `dark_panel`: 7
- `table_card`: 6
- `chart_card`: 3

## Planner component kinds

- `title`: 25
- `narrative`: 17
- `card_grid`: 11
- `table`: 6
- `bullet_list`: 5
- `kpi_row`: 4
- `chart`: 3
- `caption`: 3
- `process_arrow`: 2
- `layer`: 2
- `flow`: 2
- `pyramid`: 1
- `matrix`: 1
- `tree`: 1
- `timeline`: 1

## Lowest-fill slides

- deck-qbr-data run 1 slide 0: min fill 0.213
- gate-deck-all-nodes-dense run 1 slide 0: min fill 0.213
- gate-deck-all-nodes-dense run 1 slide 2: min fill 0.383
- deck-qbr-data run 1 slide 3: min fill 0.471
- gate-deck-cheffin-full run 1 slide 2: min fill 0.51
- deck-qbr-data run 1 slide 2: min fill 0.574
- gate-deck-cheffin-full run 1 slide 1: min fill 0.583
- gate-deck-xtsy-qcomm run 1 slide 5: min fill 0.594
- gate-deck-cheffin-full run 1 slide 5: min fill 0.631
- gate-deck-xtsy-qcomm run 1 slide 1: min fill 0.64
