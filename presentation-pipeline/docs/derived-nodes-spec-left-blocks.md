# Derived nodes for the remaining blocks (spec draft, 2026-10-26)

Status: **draft for the user's approval. Nothing is built.** No code until the user approves it.
Scope: every block in `src/knowledge/core/block-variants.yaml` → `blocks` that has no code-drawn node yet:
callout, header, table, chart, bullet_list, timeline, process_arrow, flow. Pyramid / tree / matrix stay
native POM only.
Builds on: `docs/tile-nodes-spec-2026-10-12.md` (KPI tiles and cards; this doc keeps its structure, rules and
codes), `docs/tile-variant-choice-spec-2026-10-26.md` (the plan's hint picks the look), and the 2026-10-26
decisions on group `backgroundColor` / `border.color="$accent"` (being built on `feat/tile-nodes`).
Evidence: `docs/look-and-feel-review-2026-10-21.md` (chart pass = next step #4, diagrams = #6),
`docs/roadmap-derived-components.md` (the derived-node rule), `docs/eval/genspark-variants/summary.md`, and
on `claude/design-trunk`: `docs/chart-pass-2026-10-22.md`, `docs/eval/node-break-map/`.

## 0. Summary

- **Recommendation: build 4 of the 8 blocks, in this order: chart, timeline + process_arrow (+ flow), table,
  bullet_list.** Callout is a "maybe" (it repeats on almost every slide, but fails little). Header: not now (no
  failure in the data). Reason: the roadmap's rule, "add a derived node only for a composition that repeats
  AND fails in eval data", checked block by block in §1.
- **One naming rule makes the tags mirror the planner JSON** (§2.1). The group tag is the component `kind`
  (`bullet_list` → `<BulletList>`). The item tag is the plan's list key (`timeline_items` → `<TimelineItem>`).
  A part or attribute name is the content key without its kind prefix (`kpi_deltas` → `delta.`). Two KPI names
  break the rule today (`KpiGrid`, `note.`). §3 proposes the aligned names, with aliases so saved slides
  still work.
- **A `ref` on a native POM tag means "code draws it from the plan"** (the D10 node contract of
  2026-10-06). So `<Timeline ref="roadmap"/>` is code-drawn, and a `<Timeline>` without `ref` is the LLM's
  own native node, still allowed and counted.
- **Most new variants reuse code that exists.** Timeline `cards` and process `step_cards` are card layouts
  (`cards.py` steps / rail). Bullet `tiles` uses the KPI / card tile code. Chart `labelled` is the native
  data label the chart pass prototyped (`pptx-post.js`), not a hand-drawn bar chart.
- **Gates are as before:** a free gallery, then a free replay on saved slides with your blind marks (≥ 0.5).
  A paid check comes only after you OK its case list and cost (§13).

## 1. Why, block by block: does it repeat, does it fail?

Free census of the saved runs on the build PC (`output/**/slides.json`; 647 distinct slides, plan +
generated XML; scripts in the session scratchpad, to be committed as `scripts/block_census.py` in step 0).
"Re-cut" = an item's plan text is not on the slide word for word. It can be split, shortened or dropped;
step 0 sorts these by eye.

| Block (plan kind) | Components | How the LLM draws it today | Fails in eval data | Rule met? |
|---|---|---|---|---|
| chart | 102 | native `<Chart>` on all; legend on 25 / 64 slides; focus colour often on the wrong bar (chart pass: 25 moved) | **no values on bars** (POM writes no data labels; hand-QBR #8, the hand deck's clearest win); 54 of 94 charts are one-series bars of 3–6 points that would fit a label | **yes** |
| timeline | 28 | native `<Timeline>` 11, hand-built 3, rest not found | **31 of 81 labels re-cut (38%)**: "Growth Activation — Search scaling; Placement expansion; …" cut to fit; break map: a one-long-word title breaks a horizontal timeline at any count; `label_room` turns such timelines into card steps and loses the dates line | **yes** |
| process_arrow | 36 | native 9, hand-built 12 | 16 of 120 steps re-cut (13%); one long word holds 7 chevrons in a band and 3–5 in a 60% column (break map) | **yes** |
| flow | 16 | native 14 | 7 of 81 steps re-cut; flows shrink below 50% on 6 of 16 (review §4.4); "Yes: … / No: …" branches flattened into a line | yes, but few |
| table | 190 | native `<Table>`; header tinted on 101 of 105; body cells filled on 98 | the LLM types every cell (median **~550 output tokens** per table, the largest component); 17 of 101 tables have plan cells not found in the slide's first table (mostly a second table or blank cells: no proof of changed numbers yet, step 0 checks) | repeats; fails on cost, fidelity unproven |
| bullet_list | 213 | **icon rows built by hand 62**, `<Ul>` 51, tiles 2 | 21 of 461 bullets re-cut (5%); 88 hints ask for icons | repeats; fails a little |
| narrative (callout) | 390 | **a panel on 279 of 289 found**: tinted 241, dark 38, left rule 149, plain 10 | 31 of 331 re-cut (9%); dark panels overused (XTSY 6 of 8 → `DARK_PANEL_SOFTENED`); planner prose (review §4.7) | repeats; fails a little |
| title (header) | 622 | the LLM types the HEADER block as given | one measured fault: the critic added a second eyebrow (2026-10-07) | **no** |

The census counts slides, not marks. Blind marks decide (§13).

## 2. Shared contract (every block)

### 2.1 Names mirror the planner JSON

The planner's typed schema (`src/agents/planner_schema_typed.py`) is the source of every name:

| Rule | From the plan | To the tag | Examples |
|---|---|---|---|
| N1 group tag | component `kind` | PascalCase | `bullet_list` → `BulletList`, `process_arrow` → `ProcessArrow`, `narrative` → `Narrative` |
| N2 item tag | the kind's item list key, singular | PascalCase | `timeline_items` → `TimelineItem`, `process_steps` → `ProcessStep`, `flow_steps` → `FlowStep`, `bullets` → `Bullet`, `table_rows` → `TableRow`, `table_columns` → `TableColumn`, `chart_series` → `ChartSeries`, `cards` → `Card` |
| N3 attribute / part | a content key | the key without its kind prefix, singular | `card_layout` → `layout`, `kpi_deltas` → `delta.`, `direction` → `direction`, `date` / `label` / `description` → `date.` / `label.` / `description.` |
| N4 ref | the item's place in its list | `<component_id>.<index>` for the main list; `<component_id>.<list>.<index>` for a second list | `roadmap.2`, `ops_table.4` (row), `ops_table.columns.1`, `rev_chart.series.1` |

Exceptions (stated, not hidden):
- **kpi_row** has parallel lists and no item noun: the item stays `<Kpi>`.
- **chart** categories: `chart_labels` → `<ChartPoint>` (a label with its values). "ChartLabel" would read as text.
- **String items** (bullets, process / flow steps): the item is one string. Its part is `label.`. When the
  string holds a head and a detail ("Phase 3: Consumer Expansion — target new-to-brand…"), the variants
  that show a title and a body split it at the first " — " or ": " into `label.` + `description.`, the
  names `timeline_items` uses. The words stay verbatim (Q7).
- **Look parts** that hold no plan content keep look names: `marker.` (Shape), `number.` (code's 01 02 03),
  `connector.` (line / arrow).

A native tag with `ref` is code's. Without `ref` it is the LLM's own native node, checked as today.

### 2.2 Parts, box attributes, colours (as tiles and cards)

- A drawn item is a VStack of Text / Icon / Shape parts, reached with POM dot names (`label.color`,
  `icon.variant`, `marker.fill.color`). Part attributes are those of the part's node
  (`tile_nodes.part_nodes`). The box takes `tile_nodes.box_attributes`.
- Native-drawn variants (`<Table>`, `<Chart>`, chevrons, native `<Timeline>`) take the native node's own
  attributes on the group (`connectorColor`, `cellBorder.color`) and the item's own (`color`, `textColor`).
- Colours are `$tokens` only (`LITERAL_COLOR`). `color` takes the five role tokens. `{role}Soft` /
  `{role}Text` as in tiles; `$neutral` → `$surfaceAlt` / `$textMain`.
- **Group fill (2026-10-26):** a group's `backgroundColor` / `backgroundGradient` fills each drawn item, except
  the dark emphasis item and an item with a fill of its own. `border.color="$accent"` is allowed.
- Dropped with info `NODE_ATTR_DROPPED`: `tile_nodes.dropped` (font sizes, font family, `borderRadius` on
  square looks, positions, `id`, typed text or children inside an item tag).
- Resolution order (later wins): house look → group variant → group attributes → item variant → item
  attributes. An item's own variant replaces the group variant's look (tile spec §10).

### 2.3 Who chooses what

| Code (always) | LLM |
|---|---|
| every visible word, verbatim from the plan, in plan order | where the block sits, its box, `w` / `grow` |
| type sizes: one size per part across the group (fit-grow grows the group together) | `variant`, `arrange`, `direction` where the space allows it |
| word fit (break-map limits, `label_room`, `WORD_TOO_WIDE`) | `color` on an item, `icon` names, part styling |
| step numbers, arrows, connectors, rails | the group fill and an `$accent` border |
| readable ink on dark fills; at most one dark item per block | |
| the emphasis item (plan: `focus_card`-style field, hint, destination, the headline's named bar); never the LLM's pick (2026-10-07) | |

**The default look comes from the plan.** With no `variant` the look is read from the plan's `design_hint`
(the `look_from_hint` design of the variant-choice spec, option A, extended to these blocks), else the block's
default. The LLM wrote 0 variants on 13 `<KpiGrid>` and 1 on 32 `<CardGrid>` in the combined check. A
variant only the LLM can choose will rarely show.

### 2.4 Checks (`NODE_*`)

Reused: `NODE_REF_UNKNOWN`, `NODE_REF_DUPLICATE`, `NODE_ITEM_MISSING` (errors → repair), `NODE_VARIANT_UNKNOWN`,
`NODE_VARIANT_UNMET`, `NODE_ATTR_UNKNOWN` (error), `NODE_ATTR_DROPPED`, `NODE_LAYOUT_UNMET`, `NODE_BYPASSED`
(hand-drawn block whose plan text the LLM typed itself: counted, as KPI tiles).
New, shared:

| Code | Severity | When |
|---|---|---|
| `NODE_LOOK_FROM_HINT` | info | code set the variant from the hint (cue, variant) |
| `NODE_TEXT_SPLIT` | info | a string item was split into `label` + `description` (§2.1) |
| `NODE_DIRECTION_UNMET` | warning | the LLM's `direction` breaks a word at the measured limits; the plan's direction is used |
| `NODE_NATIVE_FALLBACK` | warning | a block variant cannot draw this content (counts, word room) and the native look is used |

### 2.5 Switch

Today one value, `POM_BLOCKS=tiles`, turns on both KPI tiles (failed their gate) and cards (passed). Proposal
(Q5, also review step 3): `POM_NODES` = a comma list of kinds drawn by code (`card_grid,chart,timeline,…`).
`POM_BLOCKS=tiles` stays an alias for `kpi_row,card_grid`. Each block ships on its own once its gate passes.

## 3. KPI and Card tags against the planner JSON

| Today | Plan key | Mismatch | Proposed |
|---|---|---|---|
| `<KpiGrid>` | kind `kpi_row` | N1 | **`<KpiRow>`** |
| `<Kpi>` | parallel `kpi_*` lists | none (exception, §2.1) | keep |
| `label.` `value.` `icon.` | `kpi_labels` `kpi_values` `kpi_icons` | none | keep |
| `note.` | `kpi_deltas` | N3 | **`delta.`** |
| `color` (role) | `kpi_tones` (meaning) | different on purpose: the tone is the plan's meaning, `color` the look it sets by default | keep; the prompt says "the plan's tone sets the default color" |
| `marker.` | none | look part | keep |
| `<CardGrid>` `<Card>` | `card_grid`, `cards` | none | keep |
| `layout` | `card_layout` | none by N3 | keep |
| `title.` `tag.` `body.` `icon.` | `title` `tag` `body` `icon` | none | keep |
| bullets drawn under `body.` | `bullets` | N3: no part of their own | **`bullets.`** (Text / Ul attributes; `body.` stops reaching them) |
| key phrase (Span, no attributes) | `key_phrase` | N3: no part | **`key_phrase.`** (Span: `color`, `bold`) |
| `number.` | none | look part | keep |

**Migration.**
1. The expander accepts both names for one release: `KpiGrid` → `KpiRow`, `note.` → `delta.`, with info
   `NODE_TAG_ALIAS`. Saved slides, replays and galleries keep working without edits.
2. Prompt lines, `nodes.yaml`, `block-variants.yaml` `tile_nodes`, `house-style.yaml` and the tests switch to
   the new names in one commit. The YAML's header promises a test that fails when a prompt or knowledge
   file names a tag or variant the YAML lacks, but no such test exists (grep, 2026-10-26). It is added
   here, so a missed rename fails a test.
3. `block-variants.yaml` `blocks.kpi_row.tag` is `KpiRow` for the paused 1a route (`validate.py`). It already
   uses the new name. The 1a `blocks` entries of each block built here move into `tile_nodes` (renamed
   `nodes`), so there is one table per block. The 1a route stays readable until it is removed (its own
   decision).
4. Remove the aliases after one paid run shows 0 `NODE_TAG_ALIAS` from the generator.

Cost: free. About 40 lines plus renames. Nothing changes on a slide.

## 4. Chart

```xml
<Chart ref="rev_chart" variant="labelled" h="max"/>
```

`<Chart ref>`: `variant` `title.*` `key.*` + native Chart attributes the LLM may set (`showTitle` no; `h`,
`minH`, layout) + box attributes on the card around it (`card="true"`). Children: `<ChartPoint>`, `<ChartSeries>` only.
`<ChartPoint ref="rev_chart.3">`: `color` (one bar / slice; one series only). `<ChartSeries ref="rev_chart.series.1">`: `color`.

| `variant` | Look | Rules | Grounded in |
|---|---|---|---|
| `plain` (default) | native chart, no legend, one hue, the focus bar / series in `$accent` and the rest `$neutral` (chart pass rule), series named in a title-row key | | chart pass 2026-10-22 (L6, focus rule) |
| `labelled` | `plain` + the value on every bar (native `<c:dLbls>` in `pptx-post.js`, chart pass option B), no value axis | `chart_is_bar`, ≤ 8 points, one series (else `plain`, `NODE_VARIANT_UNMET`) | hand-QBR #8; Genspark CHART-D; 54 of 94 saved charts fit |
| `focus_label` | `plain` + a value on the focus bar only | as `labelled` | dataviz "selective labels" (chart pass Q1) |
| `horizontal` | bars turned (`<c:barDir val="bar"/>` in `pptx-post.js`, categories top-down) | `chart_is_bar`; picked by code when a label is > 12 characters and the LLM set no variant | Genspark shortlist; 11 of 102 saved charts have labels > 12 characters |

The 1a `native` variant is renamed `plain`: under N1 the tag already says "native". The 1a `native.py` is
the start of the filler: it writes the series from `chart_values` / `chart_series`.

- **Code owns:** every label and value (parsed by `native.number`, the plan's text in labels), chart type
  (plan `chart_type`), series colours (`$chartN`, separable since the chart pass), the focus point (the
  headline names it, else the latest period: `_chart_focus`), the series key in the title row, data labels,
  bar direction.
- **LLM:** variant, box, `color` on one point or series (wins over the focus rule; logged).
- **Planner fields read:** `chart_type`, `chart_title`, `chart_labels`, `chart_values` / `chart_series`.
  **New: none** (the focus comes from the headline, as the chart pass built it).
- **Checks:** `NODE_ITEM_MISSING` when labels and values differ in length (→ re-ask the planner, not the
  generator); `NODE_NATIVE_FALLBACK` on `labelled` with too many points.
- **Prompt:** fixed ~70 tokens (tag line, 4 variant phrases); per chart ~30 (`rev_chart: bar, 6 points, 1
  series, focus Q3 FY26; <Chart ref="rev_chart"/>`). Output: ~150 → ~12–30 tokens per chart (measured
  median of the LLM's charts ~150).
- **Gallery:** every variant × 1 / 3 series × 3 / 6 / 8 points × short / long labels, on corporate-slate and
  graphite-dark (charts sit on `$chartSurface`). Plus a **PowerPoint open check on the test PC** before any
  default: a bad `<c:dLbls>` order makes PowerPoint show a repair prompt (chart pass note).

## 5. Timeline

```xml
<Timeline ref="roadmap" variant="cards" direction="horizontal"/>
```

`<Timeline ref>`: `variant` `direction` + parts `date.` `label.` `description.` `marker.` `connector.` `icon.` + box.
`<TimelineItem ref="roadmap.2">`: `color` `icon` `variant` (`inverted` only on the emphasis item) + parts + box.

| `variant` | Look | Rules | Grounded in |
|---|---|---|---|
| `rail` (default) | native POM Timeline, horizontal: line, dots, date over title; code fills `TimelineItem` (`date`, `title` ← `label`, `description`) and the item colours | every label fits the break-map room (`label_room`), else `cards` (`NODE_NATIVE_FALLBACK`) | Genspark TIMELINE-A; the LLM's own choice on 11 of 14 |
| `vertical` | native POM Timeline, vertical | room for the count (break map: 9 in a band, 6 under a KPI row, 5 in a card) | Genspark TIMELINE-C |
| `cards` | a line with a dot per item and one card per item: date as the card's tag, label as title, description as body (cards `steps` layout without arrows, a rail line instead) | any label length | Genspark TIMELINE-B (keeps long labels whole) |
| `columns` | columns under a segmented progress bar, the bar's segments coloured up to the plan's "now" item | needs a "now" item (hint or `focus`), else segments all `$neutral` | Genspark TIMELINE-D (both runs: "12 WEEKS" bar) |

- **Code owns:** dates, labels and descriptions verbatim; the split of "Head — detail" labels when the plan
  has no description (`NODE_TEXT_SPLIT`); one size per part; the line, dots and bar; the card text size
  (card code).
- **LLM:** variant, direction (checked: `NODE_DIRECTION_UNMET`), item colours and icons, box.
- **Planner fields read:** `direction`, `timeline_items[].date / label / description`; the hint's emphasis.
  **New: none.** The typed schema already has `description`, but the saved plans never fill it (0 of 28):
  the planner packs the detail into `label`. Fix by prompt line (fill `description` when the brief gives
  one), checked free on the next planner run. The code split covers old plans.
- **Checks:** `NODE_DIRECTION_UNMET`, `NODE_NATIVE_FALLBACK`, `NODE_TEXT_SPLIT`.
- **Prompt:** fixed ~80; per timeline ~40 (count, longest label, which variants fit). Output: ~130 → ~15–60.
- **Gallery:** 3 / 5 / 8 items × short / long-word / "Head — detail" labels × the break map's placements
  (band, under a KPI row, split-60, split-40, card) × 4 variants × 2 palettes.

## 6. Process arrow and flow (one expander)

```xml
<ProcessArrow ref="go_to_market" variant="step_cards"/>
<Flow ref="checkout" variant="numbered" direction="vertical"/>
```

`<ProcessArrow ref>` / `<Flow ref>`: `variant` `direction` + parts `label.` `description.` `number.` `marker.`
`connector.` `icon.` + box. Items `<ProcessStep ref="go_to_market.1">` / `<FlowStep ref="checkout.3">`.

| `variant` | Look | Rules | Grounded in |
|---|---|---|---|
| process `chevrons` (default) | native ProcessArrow; code fills the steps, sizes chevrons from the longest word (fit-grow, already built) | room per the break map, else `step_cards` | Genspark PROCESS-A; the LLM's own (9) |
| flow `boxes` (default) | native Flow, one `FlowConnection` per pair; vertical flows sized by code (fit-grow 2b, built) | as today | Genspark FLOW-A; the LLM's own (14) |
| `numbered` | a numbered circle over each box, arrows between | ≤ 6 steps in a row, else 2 rows | Genspark PROCESS-B / numbered circles |
| `alternating` (process only) | circles on one line, labels alternating above and below | horizontal only; ≥ 4 steps | Genspark PROCESS-C (Super Agent B) |
| `step_cards` | step cards joined by arrows, the destination card dark; label = title, description = body | any length; destination = emphasis | Genspark PROCESS-D (both runs); the card nodes' `steps` layout (passed 0.692) |

`step_cards` is drawn by `cards.py` (layout `steps`) from the process steps. No new card code.

- **Code owns:** step text verbatim (split as §2.1), numbers, arrows, chevron / node sizes, the destination
  card (last step, or the hint's).
- **Planner fields read:** `direction`, `process_steps` / `flow_steps`. **New: none.** Flow branches
  ("Yes: … / No: …") cannot be drawn from a linear list. That needs a planner shape change (Q9), not in this
  build.
- **Checks:** as timeline. **Prompt:** fixed ~90 for both; per component ~35. Output: process ~115 → ~15–50,
  flow ~280 → ~15–50.
- **Gallery:** 3 / 5 / 7 / 9 steps × short / long-word / "Head — detail" × placements × variants × 2 palettes.

## 7. Table

```xml
<Table ref="ops_table" variant="highlight_row">
  <TableRow ref="ops_table.3" color="$negative"/>
</Table>
```

`<Table ref>`: `variant` + parts `header.` `body.` `label.` (first-column cells) + native `cellBorder.*` + box
(on a card around it when `card="true"`). `<TableRow ref="ops_table.N">` and
`<TableColumn ref="ops_table.columns.N">`: `color` + Td attributes (`backgroundColor`, `color`, `bold`,
`italic`, `textAlign`) for their cells. The table stays a native `<Table>` on every variant.

| `variant` | Look | Rules | Grounded in |
|---|---|---|---|
| `plain` (default) | `$surfaceAlt` header row, bold header text, hairline rows, no body fills | | the LLM's own norm (tinted header 101 of 105) |
| `minimal` | no fills: a rule under the header, hairlines | | Genspark TABLE-A |
| `zebra` | every other body row `$surfaceAlt` | ≥ 4 body rows, else `plain` | Genspark TABLE-B |
| `highlight_row` | the emphasis row `{role}Soft`, its label cell `{role}Text` bold | `one_singled_out` (hint names one row), else `plain` | Genspark TABLE-C; 91 hints name a row |
| `dark_header` | `$panelDark` header, `$onPanelDark` text, first column `$accentText` bold | counts as the slide's dark panel (`DARK_PANEL_SOFTENED`) | Genspark TABLE-D (both runs) |

- **Code owns:** every cell verbatim from `table_columns` / `table_rows`; column widths
  (`TABLE_NUMERIC_COLS_SHARED`, fit-grow table sizing); numbers right-aligned; type size; padding a short
  row with empty cells (`NODE_TABLE_SHAPE`, warning).
- **LLM:** variant, row / column colours by meaning, box, placement.
- **Planner fields read:** `table_columns`, `table_rows`, `columns`, `rows`, the hint. **New, optional
  (Q8):** `focus_row` (index, as `focus_card`) and `row_tones` (as `kpi_tones`). The first build reads the
  hint (`one_singled_out`, `tones_from_hint`) and adds the fields only if the replay shows the hint misses.
- **Checks:** `NODE_TABLE_SHAPE`; `NODE_ITEM_MISSING` for a `TableRow` past the plan.
- **Prompt:** fixed ~70; per table ~35 (columns, rows, longest cell). **Output: ~550 → ~15–60 per table**,
  the largest saving of any block.
- **Gallery:** 2–10 columns × 2 / 6 / 14 rows × short / long cells × the break map's table placements × 5
  variants × 2 palettes. The break map's holds (≥ 14 rows in a band) are the floor.

## 8. Bullet list

```xml
<BulletList ref="actions" variant="icon" icon.color="$accent"/>
```

`<BulletList ref>`: `variant` `cols` + parts `label.` `description.` `icon.` `marker.` + box.
`<Bullet ref="actions.2">`: `color` `icon` + parts + box.

| `variant` | Look | Rules | Grounded in |
|---|---|---|---|
| `plain` (default) | native `<Ul>`, code writes each `<Li>` verbatim | | the LLM's own (51) |
| `icon` | one row per point: icon, then the text (the hint capability `icon_rows`) | an icon per point: the LLM's `icon` on the group / each `<Bullet>`, else a dot marker | the LLM's own (62 hand-built); 88 hints ask for icons |
| `lead` | "Head: detail" points with the head bold (`label.`) and the detail plain | most points split (§2.1), else `plain` | the LLM's own bold lead-ins; "Recommendation: …" points in saved plans |
| `tiles` | each point in its own tile (KPI / card tile code), 2–3 per row | every word fits the tile (shrink guard), else `icon` | Genspark BULLET-C |
| `columns` | two columns of points | ≥ 6 points, else `plain` | Genspark BULLET-D |

- **Code owns:** point text verbatim, order, the split for `lead`, one text size, columns, icon size.
- **Planner fields read:** `bullets`. **New, optional (Q8):** `bullet_icons` (mirrors `kpi_icons`, every
  point or none). The first build takes icons from the LLM's `icon` attributes, as cards did before `icon`.
- **Prompt:** fixed ~70; per list ~30. Output: not measured (estimate ~120–250 → ~15–60).
- **Gallery:** 2 / 4 / 7 points × short / long / "Head: detail" × 5 variants × placements × 2 palettes.

## 9. Callout (narrative)

```xml
<Narrative ref="takeaway" variant="tinted" color="$negative"/>
```

`<Narrative ref>`: `variant` `color` `icon` + parts `text.` `mark.` (the quote glyph) `icon.` + box. One item, so
no item tag. A caption stays `<Text ref="caption_id"/>`: an element ref on a Text, code writes the text (no
look of its own, so no tag of its own: Q10).

| `variant` | Look | Rules | Grounded in |
|---|---|---|---|
| `tinted` (default) | `{role}Soft` panel, 4 px `{role}` left edge, text `$textMain` | | the LLM's own (241 of 279; 149 with a left rule); Genspark CALLOUT-B |
| `rule` | no fill, 4 px `{role}` left rule | | Genspark CALLOUT-A |
| `dark` | `$panelDark`, `$onPanelDark` text | one dark panel per deck (`DARK_PANEL_SOFTENED`) | the LLM's own (38); Genspark CALLOUT-C |
| `quote` | a large `“` in `$accent` above italic text | the text is a quotation (starts with a quote mark, or ends "— Name"), else `tinted` | Genspark CALLOUT-D; 12 hints |
| `plain` | the text alone, body size | | prose paragraphs (10) |

`{role}` = the item's `color`, default `$accent`.

- **Code owns:** the text verbatim, its size (one-line takeaways grow to 24–28 px, paragraphs stay 18–20),
  readable ink on dark.
- **Planner fields read:** `text`. **New, optional (Q8):** `key_phrase` and `tone` (as cards). The census
  shows 157 "highlight" and 232 colour cues on narratives, and the card marks turned on coloured spans.
- **Prompt:** fixed ~60; per callout ~20. Output: ~60–120 → ~12–30 (estimate).
- **Gallery:** 1-line / 3-line / quote × 5 variants × 2 palettes, beside a chart and under a KPI row.

## 10. Header (title): specified, not proposed for building

```xml
<Title variant="inverted"/>
```

`<Title>` draws the slide's HEADER: kicker (outline `label`), headline (`slide_title`), subtitle. No `ref`:
one per slide. Parts `label.` `title.` `subtitle.` (N3: the outline's keys; `slide_title` → `title`).
Variants: `standard` (kicker, headline, subtitle on the background), `inverted` (dark band; counts as the dark
panel), `ruled` (hairline under the headline, Genspark HEADER-C). Code owns the text, the uppercase kicker,
the type ramp (36 / 18 / 14), and "no kicker in the plan, no kicker on the slide".
**Not proposed now:** no failure in the data. The one fault, a second eyebrow, came from the critic, and its
rule was tightened. It would save ~80–150 output tokens a slide. Revisit if step 0 finds headers that differ
from the plan.

## 11. Prompt budget

| | Tokens | Where |
|---|---|---|
| fixed lines, the 4 recommended blocks | ~310 (chart 70, timeline 80, process + flow 90, table 70) | cached prefix |
| + bullet list, callout | ~130 | cached prefix |
| per component | ~20–40 | per slide |
| recipes no longer injected for code-drawn kinds | `icon_bullet_list`, chart / table techniques (not measured; to count in step 1) | per slide |

Today's cached prefix is ~7.5k tokens (tile spec §10). Adding ~440 cached tokens costs about $0.0002 a slide
at gpt-6.1-sol's cached rate ($0.50 / M). The output saving is about 400–900 tokens on a slide with a table
and a chart ($0.003–0.007 at $8 / M). Every number above is an estimate until replay step 5 measures it.

## 12. Ownership of the data

All looks live in `block-variants.yaml` `tile_nodes` (renamed `nodes`, §3), one entry per block, the same
keys as `kpi` / `card`: `plan_kind`, `group_tag`, `item_tag`, `ref`, `emphasis_from`, `parts`,
`group_attributes`, `item_attributes`, `owned_by_code`, `treatments` (the hint's treatments as attributes),
`house_look`, `variants` (`prompt`, `look`, `requires`, `fallback`, `with_color`, `with_tone`, `draw: native |
block`). `nodes.yaml` lists the tags. One expander module per family: `src/compiler/nodes/diagrams.py`
(timeline, process, flow), `charts.py`, `tables.py`, `lists.py` (bullets, callout). The card-drawn variants
call `cards.py`.

## 13. Build and check order (per block, with gates)

| Step | What | Cost | Gate |
|---|---|---|---|
| 0 | Commit `scripts/block_census.py`. Re-run it and sort every "re-cut" item by eye (split / shortened / dropped / other table). Re-confirm §1 | free | you agree §1 holds |
| 1 | §3 renames with aliases | free | unit tests = baseline |
| 2 | Block YAML + expander + checks + prompt line, behind `POM_NODES=<kind>`; unit tests per variant, alias and fallback | free | tests pass; every variant compiles |
| 3 | Gallery (§4–9 lists), Inter render with the deck font (`card_replay.render` profile) | free | you look at it; 0 compile failures, 0 broken words at the break-map limits |
| 4 | Break-map sweep of the code-drawn variants (`scripts.node_break_map` with the new expansion) | free | holds ≥ the native node's counts |
| 5 | Free replay on every saved slide of the kind: A = the LLM's drawing, B = a bare `<Kind ref>` at its place (+ hint look). Scorecard: compiled, text verbatim (target 100%), broken words, `GEOM_*`, `LOW_CONTRAST`, output tokens. Blind sheet | free (your marks) | **marks ≥ 0.5**, text verbatim 100%, no score worse |
| 6 | Paid check, **only with your OK**: generator only on saved plans (same-plan design: `scripts.tile_same_plan` pattern), both arms | ≈ $0.02–0.03 per slide-arm at gpt-6.1-sol (11k input, ~75% cached; ~1.5k output with reasoning). 12 slides × 2 arms ≈ **$0.5–0.7**, ceiling $1 with repairs. The case list is the saved slides of that kind from wide-paid / combined / step0 decks, given when I ask | **marks ≥ 0.6** (1a gate), 0 values off the plan |

Chart extra: the PowerPoint open check on the test PC (step 3) before step 6.
Blocks can share step 6: one same-plan run of chart + timeline + process + table slides ≈ $1–1.5. That is
cheaper than one run per block, and it is asked for in one message.

## 14. Open questions (ranked by how much they change the build)

| # | Question | Draft answer |
|---|---|---|
| Q1 | Approve the naming rules N1–N4 and the KPI / card renames (`KpiGrid` → `KpiRow`, `note.` → `delta.`, new `bullets.` / `key_phrase.` parts), with aliases for one release? | yes |
| Q2 | Which blocks, in which order? | chart → timeline + process + flow → table → bullet list; callout after the first replays; header not now |
| Q3 | Base branch for the build: `claude/design-trunk` (chart pass, break map, `label_room`, deck font in diagrams) merged with `feat/tile-nodes` (tile code, the 2026-10-26 group fill)? | yes: both are needed; you merge, or tell me to |
| Q4 | Chart `labelled` by native data labels in `pptx-post.js` (chart pass option B), not a code-drawn bar block. Values on every bar, or the focus bar only (`focus_label`)? | native labels; offer both variants, default `plain` until the marks |
| Q5 | One switch per kind (`POM_NODES` list; `POM_BLOCKS=tiles` = alias)? | yes (also lets cards ship without KPI tiles) |
| Q6 | The default look read from the plan's hint (variant-choice spec option A) on every new block? | yes, with `NODE_LOOK_FROM_HINT` logged |
| Q7 | Split "Head — detail" / "Head: detail" strings in code into `label` + `description` (every word kept)? | yes; plus a planner prompt line to fill timeline `description` |
| Q8 | New planner fields (`focus_row`, `row_tones`, `bullet_icons`, narrative `key_phrase` / `tone`): add now or only when the replay shows a gap? Each costs a paid planner check | only on evidence |
| Q9 | Flow branches ("Yes: … / No: …"): leave linear for now? | yes; a branching flow needs a planner shape |
| Q10 | Caption as `<Text ref>` (no tag of its own), against N1? | yes: it has no look to choose |
| Q11 | `columns` timeline: what marks "now" when the hint names nothing (all neutral, or the first item)? | all neutral |

## 15. Recommended build order

1. **Step 0 + the §3 renames** (free, one session). They de-risk everything after.
2. **Chart** (free up to the PowerPoint check). The strongest evidence and the smallest code: the native
   filler exists (`native.py`), and the focus rule and labels are prototyped in the chart pass. Needs Q3 / Q4.
3. **Timeline + process_arrow + flow** (free). Most variants are card layouts already built. They fix the
   38% re-cut timeline labels and the long-word breaks `label_room` now turns into cards.
4. **Table** (free). The largest output saving; native drawing keeps editing in PowerPoint.
5. **One shared paid check** for 2–4 (≈ $1–1.5, asked first with the case list).
6. **Bullet list**, then **callout** only if 5 shows the generator still hand-builds them and the replay marks
   pass.
7. Header: revisit only on new evidence.
