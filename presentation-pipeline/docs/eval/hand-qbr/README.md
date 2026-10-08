# Hand-written QBR deck vs the pipeline (2026-10-08)

Same brief (`tests/cases/deck-qbr-data.yaml`), same theme (corporate-slate), same facts.
`xml/` = 5 slides written by hand (POM 10.3.0, `fit-grow: off`, all compile and pass the layout audit).
`hand-deck.png` = those slides (Inter, LibreOffice). `pipeline-deck.png` = the paid run
`deck-qbr-data-e2e624` (commit `3b03a4d`, critic on, PowerPoint screenshots).
Derived numbers used by hand: 58% / 30% / 12% share, 16x customers, +$5.9M, +70% (content policy: derived).

Re-render: `python -m scripts.render_check --in docs/eval/hand-qbr/xml --out output/hand-qbr`.

## Where each difference comes from

| # | Pipeline deck | Hand deck | Cause (part of the system) | Fix type |
|---|---|---|---|---|
| 1 | 8 slides; NRR, gross margin, CAC payback and both initiatives each shown twice | 5 slides, each fact once | `outline_planner`: no "each fact once" rule; `plan_reviewer` result ignored | planner + code check for repeated figures |
| 2 | NRR slide filled with customer counts (unrelated chart) | no NRR-only slide | follows from 1: a slide with one number, so the planner borrowed data | same as 1 |
| 3 | Label headlines: "Revenue Trend ($M)", "ARR by Segment", "Q4 Priorities" | claim headlines | outline prompt "copy the brief's headlines" takes `chart_title` as the headline | prompt: a chart title is a caption; the headline states the point |
| 4 | Subtitles repeat the numbers ("$48.2M · 114% · 72.1% · 14 months") | subtitle gives context or one derived fact | outline prompt: subtitle = "2-4 key figures" | prompt |
| 5 | Broken glyphs (`42.3▯`, `$28.1M▯`) | none | the plan (`slides.json`, 9 times) holds the control character `\x7f` as a separator; the generator copies it; nothing cleans it | code: sanitize every LLM text field |
| 6 | Headline 30, subtitle / body 14-15, KPI value 34 px | headline 36, subtitle 18, body 18, KPI 48, table 22 | `house-style.yaml` `type_ramp` (title 27-32, body 14-16, stat 26-36) | knowledge numbers, then code enforces the ramp |
| 7 | Filler boxes that restate the slide (trend summary, segment footnote, initiative intent, summary panel) | none; the spare room holds derived facts (+$5.9M, share bar) | `slide_component_planner` adds narrative / callout components to fill | planner rule: no component that repeats the slide; use derived facts |
| 8 | Chart: no value labels, gridlines, focus on the first bar | value on every bar, latest period highlighted | POM `<Chart>` has no data-label option; focus colour chosen by the LLM | code-drawn column chart for small series (one block, not a one-slide rule) |
| 9 | Stretched cards with empty middles (priorities, NRR tile) | content at the top, target pinned to the bottom, equal heights | house style: tiles stretch + `justifyContent="center"` + grow text afterwards | layout rule: spacer / `spaceBetween` inside cards |
| 10 | Card in card, left borders, shadows, icons on every tile, eyebrow as a badge | flat tiles, one emphasis per slide (red margin tile, blue latest bar, blue Enterprise) | recipes + critic rule "bare table/chart without card shell = MEDIUM" | knowledge + critic rules |
| 11 | Plain centred cover | colour block + left-aligned title | cover recipe | knowledge |
| 12 | pptx names "Noto Sans JP", no embedded font; looks right only where PowerPoint substitutes well | Inter, embedded | production compile does not set a deck font (only test scripts do) | code: set + embed the deck font in production |

Not seen as a cause here: the generator model's ability (it followed the plan and the ramp it was given) and
`state.py` (no field changed the result on this deck).

## What this says
Most of the gap is **planning** (1-4, 7) and **house-style numbers / rules** (6, 9-11). Two are plain **code bugs**
(5, 12). One needs a **new drawing block** (8). None needs a bigger model.

## Changes made from this comparison (2026-10-08, LLM-free so far)

| # | Change | Files |
|---|---|---|
| 5 | Control characters removed from every parsed LLM result and in the normalizer (`CONTROL_CHAR_REMOVED`) | `src/utils/llm_client.py` (`unpack_raw`), `src/compiler/normalizer.py` |
| 12 | Deck font Inter on every text node (incl. Shape) in `compile_xml`, so fit-grow measures and `font_embed` embeds it; `POM_DECK_FONT=none` turns it off | `src/compiler/compiler_client.py` |
| 1, 2 | Slide count from settings is a maximum, not "EXACTLY"; each fact on one slide; no slide for one number already on a summary | `src/prompts/outline_planner/user.j2`, `system.j2` |
| 3, 4 | A chart title is not a headline; headline says what the data shows; subtitle adds the period or one fact, never a list of the slide's figures | outline `system.j2`, `outline_planner_schema.py`, `outline_replanner/system.j2` |
| 7 | No filler components (summary / intent boxes) in the component planner | `src/prompts/slide_component_planner/system.j2` |
| 6, 9-11 | Type ramp (title 36, subtitle 18, body 18, stats 44-56, table 20-22), root padding 48-56 / gap 24-36, flat cards, content top + pinned footer in tall tiles, one card style per deck, at most one dark panel per deck; table rows 56-88, grid gap 20-24 | `house-style.yaml`, `capacity.yaml`, `generator/system.j2` |
| 10 | Critic: kicker issue only when the header has no uppercase label (stops the second eyebrow); "dark anchor panel" and "bare table/chart" rules removed; new "filler box" issue. Repairer adds no panels or wrappers | `visual_critic/*.j2`, `repairer.py`, `repairer/patch.j2` |
| - | Golden examples and blueprint reference XML off by default (written in the old sizes); `POM_EXAMPLES=on` for an A/B | `src/agents/context_builder.py` |

Checked: replaying the saved slides 1-3 and 5 through normalize + compile_xml gives no DEL character and every run in Inter; Inter is embedded.
Not done: the chart block (#8), and a paid run to see what the planners and generator now write.
