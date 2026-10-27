# Left-blocks gallery: can today's plan JSON draw every variant? (2026-10-27, free)

`python -m scripts.left_blocks_gallery` (corporate-slate; `--palettes graphite-dark` for the dark run, not run yet).
For `docs/derived-nodes-spec-left-blocks.md`. The script builds every variant **only** from a sample component in
today's typed planner schema; `content_from_data` checks each sample first. Each variant is hand-written as the
XML a node would expand to. `step_cards` goes through the real card code (`<CardGrid ref layout="steps">`). The
chart `labelled` / `focus_label` / `horizontal` variants edit the compiled chart XML (chart pass option B). Then
the real pipeline renders it: normalizer, compile-pom.js with fit-grow, LibreOffice in Inter.

**Result: 34 of 34 variants compile and render from today's fields. No new planner field is needed.**

| Sheet | Variants | Drawn as intended? | Found |
|---|---|---|---|
| [chart](corporate-slate-chart.png) | plain, labelled, focus_label, horizontal | yes | horizontal labels read "2.6", not the plan's "2.6x": values are parsed to numbers, so the unit is lost. Fix in the build: a number format from the plan text (`0.0"x"`) |
| [callout](corporate-slate-callout.png) | tinted, rule, dark, plain, quote | yes | `quote` gets the attribution by splitting the text at " — " (the plan has one `text` field) |
| [header](corporate-slate-header.png) | standard, inverted, ruled | yes | |
| [table](corporate-slate-table.png) | plain, minimal, zebra, highlight_row, dark_header | yes | on corporate-slate `$surfaceAlt` is close to the slide's `$surface`: `plain` reads like `minimal` and the zebra rows are faint. The table does not grow into its band (known open item) |
| [bullets](corporate-slate-bullets.png) | plain, lead, icon, tiles, columns | yes | the icons come from the LLM's `icon` (there is no plan field); `lead` needs "Head: detail" points |
| [timeline](corporate-slate-timeline.png) | rail, vertical, cards, columns | cards / columns yes; **rail / vertical no** | POM's native Timeline draws fixed small text; on the horizontal rail the descriptions overlap the titles. Native rail only when items have no description, else `cards` |
| [process](corporate-slate-process.png) | chevrons, numbered, alternating (detail / short), step_cards | yes | chevron text is POM's small fixed size (C4: kept); `numbered` boxes do not take their column's width yet (layout detail for the build) |
| [flow](corporate-slate-flow.png) | boxes, numbered, step_cards | yes | native flow-node text is tiny (POM's fixed size, as chevrons) |

The "now" item (timeline cards / columns) and the highlighted table row come from the plan's `design_hint`, as
`one_singled_out` reads it. The destination step card is the last step.
