# The 8 remaining blocks on the composition convention (R1–R4, free, 2026-10-27)

Free check for `docs/composition-convention-spec.md` §11.3 R1–R4. No LLM calls, no `src/` changes.
Scripts:
- `python -m scripts.composition_gallery_left` (R1): sheets in this folder, slides in `output/composition-left/`.
  The run takes about 10 minutes, one slide at a time.
- `python -m scripts.native_style_probe` (R2, uses `scripts/native_style_probe.mjs`): writes
  [r2-attributes.md](r2-attributes.md) and `r2-attributes.json`. The run takes about 1 minute: 660 probe slides
  through one POM import.

**Samples.** A census of the saved `slide_component_planner` output (`output/**/slides.json` on the build PC)
found 932 distinct components that pass `content_from_data`. One sample per block copies a common real shape:
- table: 4 × 4 comparison whose hint names a column;
- chart: one-series bar with unit strings ("0.29x");
- bullets: 4 points, 3 of them "Head: detail";
- timeline: 4 dated items whose labels carry the detail after " — ". This is the real case: 0 of 19 saved
  timelines fill `description`.
- process: 5 short steps, and 4 long "Phase N: head — detail" steps;
- flow: 4 linear steps;
- callout: a one-sentence takeaway, and a quotation;
- matrix: effort / impact with quadrants.

The words are synthetic or anonymised. Each composition is the hand-written XML its node would expand to, in its
theme-default look: `$tokens` plus the plan's emphasis and tone roles, with no LLM attributes. The same XML is drawn
on corporate-slate and on graphite-dark. Repeated items carry `card-<cid>-<i>` ids, so fit-grow grows peers to one
size. The first row of each sheet shows today's style names (`left_blocks_gallery`, corporate-slate).

## Verdict per block

Sheets: [table](table.png) · [chart](chart.png) · [bullets](bullets.png) · [timeline](timeline.png) ·
[process](process.png) · [flow](flow.png) · [callout](callout.png) · [header](header.png) · [matrix](matrix.png).
All 83 slides compiled and rendered (compositions on both palettes, today's names on corporate-slate). **No block needed a block-specific word**: every composition
is one of the shared words of spec §2.3. "Recipe in POM?" uses R2 below.

| Block | Words (default first) | What the sheet shows | Today's names → | Recipe in POM attributes? |
|---|---|---|---|---|
| **table** | `native` · `rows` / `rows numbered` · `columns` (≤ 5 rows) · `banded` (≤ 6 rows) | `native` stays a small table at the top of a tall band (fit-grow: "rows 32 → 47 px, cell text × 1.00"), the known table-fill gap. The emphasis column ($positive from the hint) reads on both palettes. `rows numbered`, `columns` and `banded` are three different slides from the same rows, and each fills its band | `plain` → `native`'s default look. `zebra`, `dark_header` → recipes. `highlight_row` → `native`'s emphasis look. `minimal` → not writable (C2) | `dark_header`: yes, through look parts `header.` / `label.` that code writes onto `Td`. `zebra`: only with a `stripe.` part. `minimal`: **no** (`Td` takes no border). Row styles: code must write them onto every `Td` (`Tr` ignores everything) |
| **chart** | `native` · `native labelled` · `rows` (one series, ≤ 8 points) | `native labelled` loses the unit ("0.29", not "0.29x"), and on graphite-dark its labels and axis text vanish. `rows` keeps "0.29x" verbatim and reads on both palettes, but its type stays at 20 / 24 px (C12) | `plain` → `native`. `labelled` → `native labelled`. `focus_label` → the emphasis look of `native labelled`. `horizontal` → `direction` (or `rows`, which is horizontal by nature) | `native`: **barely**. Chart text takes no attribute, and the only colour is `chartColors` (code's focus rule). Style power on charts lives in `rows`, where every part is a Text / Shape |
| **bullet_list** | `native` · `rows` / `rows numbered` · `grid` · `banded` (≥ 75% split) | `native` `<Ul>` stays small at the top. `rows` and `grid` turn the same 4 points into a ruled list and 2 × 2 tiles. `banded` shows why it needs split points: the one unsplit point fills its band and leaves an empty body | `plain` → `native`. `lead` → `native`'s default (code bolds a split head). `icon` → `rows` + the LLM's `icon` per `<Bullet>`. `tiles` → `grid`. `columns` → `rows cols="2"` | `native`: list-level text and colour only (`Li` takes no box). `rows` / `grid` / `banded`: everything, `item.` included |
| **timeline** | `rail` (default when any label splits) · `rows` · `banded` · `native` (default only for short labels with no detail) | `native`: tiny type, and the description runs over the title (the gallery finding, again). `rail`, `banded` and `rows` all keep every word whole. `rows` uses the slide's width best, and `banded` shows done / now / ahead at a glance | `rail` (native) → `native`. `vertical` → `native direction="vertical"`. `cards` → `rail`. `columns` → `banded` (C4) | `native`: item colour only (`TimelineItem` takes `color` / `dateColor`). The code-drawn words: everything |
| **process_arrow** | `native` (short steps only) · `steps` · `steps numbered` · `rail` | Short steps read well as chevrons. Long steps are cramped and wrap into 5-line chevrons. `steps` (the real card code) and `steps numbered` carry the same long steps at 28 px. `rail` alternates the labels well | `chevrons` → `native`. `numbered` → `steps numbered`. `alternating` → `rail`. `step_cards` → `steps` | `native`: step colour + group text weight (`ProcessArrowStep` takes `color` / `textColor`; `fontSize` is code's). The code-drawn words: everything |
| **flow** | `native` · `steps` · `steps numbered` | Native flow nodes stay tiny inside a large band (fixed node size). `steps` and `steps numbered` fill the row at 37 px | `boxes` → `native`. `numbered` → `steps numbered`. `step_cards` → `steps` | `native`: node `color` / `textColor`, `connectorStyle`. The code-drawn words: everything |
| **callout** (narrative) | `native` only | The default look `tinted` reads on both palettes. A quotation draws its mark and attribution from the content (C5) | `tinted` → `native`'s default. `rule`, `dark`, `plain` → recipes. `quote` → a content rule | **yes, all of them**: it is one box (`backgroundColor`, `borderLeft.*`, `item.` not needed). The mark is `mark.color` |
| **header** (title) | `native` only | the same three slides as today. Nothing composes: one item, no list | `standard` → `native`. `inverted` → recipe. `ruled` → needs a look part (C13) | `standard` / `inverted`: yes (box + text colours). `ruled`: no |
| **matrix** (extra) | `native` · `grid` (requires `quadrants`) | Native: 9 px labels, two of them stacked over each other. `grid`: each item listed in its named quadrant, emphasis from the hint. Its type did not grow (the rows are uneven: fit-grow saw no spare room in the top row) | `native` → `native` | `native`: item `color` / `textColor`, label colours. `grid`: everything |

**Defaults chosen from the content.** Timeline and process each show a case where the safe default depends on the
plan: `native` when labels are short and have no detail, else a code-drawn word. This is the same shape as spec
F4 (cards: `columns` when body + bullets). It is one rule per block with a measured limit (the break-map's label
room), not a one-example rule, and it should be checked on the saved slides by free replay before it becomes a
default.

**Proposed default looks** (for `block-variants.yaml` `nodes.<block>.compositions.<word>.look`, tokens only, as
drawn):
- `rows`: no fill, `$border` dividers. Title or head `$textMain` bold, detail `$textMuted`, `number.` / date
  `$accentText`. Emphasis row: `$accentSoft` fill.
- `banded`: `band.` `$accent` with ink `$onAccent`, body `$surfaceAlt`, `$border` outline. Timeline bands: done
  `$accent`, now `$panelDark`, ahead `$neutral`. Emphasis: band `$panelDark`.
- `columns`: `band.` pill `$accent` with ink `$onAccent`. Each cell in a `$surfaceAlt` box with an 8 px radius and
  its column name as a `$textMuted` caps label. Emphasis column: `$positiveSoft` / `$positive` (its tone from the
  hint).
- `grid`: `$surfaceAlt` boxes with an 8 px radius and a `$border` outline, head bold over detail.
- `steps`: `$surfaceAlt` boxes, `$neutral` arrows, the destination `$panelDark`. `numbered`: `$accent` circles.
- `rail`: `$border` line, `$accent` dots, the emphasis item's box (or label) `$panelDark` (or `$accentText`).
- table `native`: header `$surfaceAlt` bold, first column bold, `cellBorder` `$border`. Emphasis row / column:
  `$toneSoft` with `$toneText` bold, and its header `$tone` / `$onAccent`.
- chart `native`: `$neutral` bars, the focus bar `$accent`.
- callout `native`: `$toneSoft` panel, a 4 px `$tone` left edge, text `$textMain`.

Every look drew correctly on graphite-dark with the same XML. The one failure is the chart's own text (R2 point 4).


## R2: what the LLM's style attributes can reach on each native node

660 probes. Each one adds a single attribute to a baseline slide.
- **yes** = applied (the pptx differs from the baseline).
- **silent** = accepted, but nothing changes in the pptx.
- **no** = POM throws.
- **(N)** = `normalize_xml` already removes the attribute.

Colours were written as `$tokens`: **every colour attribute that POM accepts also resolves a token**, and no
probe needed a hex value. Full list per tag, including each node's own attributes:
[r2-attributes.md](r2-attributes.md). `borderRadius` and `opacity` were probed on a filled box and compared with
the fill-only probe.

Box attributes:

| tag | backgroundColor | border | borderLeft | borderRadius | padding | shadow | opacity | backgroundGradient |
|---|---|---|---|---|---|---|---|---|
| `Table` | yes | yes | yes | yes | yes | yes | yes | yes |
| `Tr` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `Td` | yes | no (N) | no (N) | no | no | no | no | no |
| `Chart` | yes | yes | yes | yes | yes | yes | yes | yes |
| `ChartSeries` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `ChartDataPoint` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `Ul` | yes | yes | yes | yes | yes | yes | yes | yes |
| `Li` | no | no (N) | no (N) | no | no | no | no | no |
| `Timeline` | yes | yes | yes | yes | yes | yes | yes | yes |
| `TimelineItem` | no | no (N) | no (N) | no | no | no | no | no |
| `ProcessArrow` | yes | yes | yes | yes | yes | yes | yes | yes |
| `ProcessArrowStep` | no | no (N) | no (N) | no | no | no | no | no |
| `Flow` | yes | yes | yes | yes | **silent** | yes | yes | yes |
| `FlowNode` | no | no (N) | no (N) | no | no | no | no | no |
| `FlowConnection` | – | – | – | – | – | – | – | – |
| `Pyramid` | yes | yes | yes | yes | **silent** | yes | yes | yes |
| `PyramidLevel` | no | no (N) | no (N) | no | no | no | no | no |
| `Tree` | yes | yes | yes | yes | **silent** | yes | yes | yes |
| `TreeItem` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `Matrix` | yes | yes | yes | yes | yes | yes | yes | yes |
| `MatrixItem` | no | no (N) | no (N) | no | no | no | no | no |

Text attributes:

| tag | fontSize | color | bold | italic | fontFamily | textAlign | lineHeight | letterSpacing | underline | textColor |
|---|---|---|---|---|---|---|---|---|---|---|
| `Table` | no | no | no | no | no | no | no | no | no | no |
| `Tr` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `Td` | yes | yes | yes | yes | yes | yes | no | no | yes | no |
| `Chart` | no | no | no | no | no | no | no | no | no | no |
| `ChartSeries` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `ChartDataPoint` | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** |
| `Ul` | yes | yes | yes | yes | yes | yes | yes | no | yes | no |
| `Li` | yes | yes | yes | yes | yes | no | no | no | yes | no |
| `Timeline` | no | no | no | no | yes | no | no | no | no | no |
| `TimelineItem` | no | yes | no | no | no | no | no | no | no | no |
| `ProcessArrow` | yes | no | yes | yes | yes | no | no | no | yes | no |
| `ProcessArrowStep` | no | yes | no | no | no | no | no | no | no | yes |
| `Flow` | no | no | no | no | no | no | no | no | no | no |
| `FlowNode` | no | yes | no | no | no | no | no | no | no | yes |
| `FlowConnection` | no | yes | – | – | – | – | – | – | – | – |
| `Pyramid` | yes | no | yes | no | yes | no | no | no | no | no |
| `PyramidLevel` | no | yes | no | no | no | no | no | no | no | yes |
| `Tree` | no | no | no | no | no | no | no | no | no | yes |
| `TreeItem` | **silent** | yes | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | **silent** | yes |
| `Matrix` | no | no | no | no | no | no | no | no | no | no |
| `MatrixItem` | no | yes | no | no | no | no | no | no | no | yes |

Own attributes (all applied unless named):
- `Table`: `defaultRowHeight`, `cellBorder.*`.
- `Tr`: `height`.
- `Td`: `strike`, `subscript`. `colspan` is not settled: the probe put it on a 2-cell row, and POM threw a table-shape error ("one cell per grid column"), not an unknown-attribute error.
- `Chart`: `showLegend`, `showTitle`, `chartColors` (tokens resolve; this is the only per-point colour, see below),
  `chartType`.
- `Timeline`: `dateColor`, `titleColor`, `descriptionColor`, `connectorColor`, `connectorGradient`,
  `useColorForDate`, `direction`.
- `TimelineItem`: `color`, `dateColor`, `description`.
- `ProcessArrow`: `itemWidth`, `itemHeight`, `gap`, `strike`, `direction`.
- `Flow`: `nodeWidth`, `nodeHeight`, `nodeGap`, `connectorStyle.*`, `direction`.
- `FlowNode`: `shape`, `width`, `height`, `color`, `textColor`.
- `FlowConnection`: `label`, `color`, `labelColor`.
- `Pyramid`: `direction`.
- `Tree`: `nodeShape`, `nodeWidth`, `nodeHeight`, `levelGap`, `siblingGap`, `connectorStyle.*`, `layout`.
- `Matrix`: `axisLabelColor`, `quadrantLabelColor`, `itemLabelColor`.

**What R2 decides**
1. **The group box is complete everywhere.** All 8 box attributes work on all 9 native group tags. The exceptions
   are `padding`, which `Flow`, `Pyramid` and `Tree` silently ignore, and `Td` (below). So "group box attributes =
   the group's own box" (D3) holds on every block with no extra work.
2. **Item boxes do not exist on native nodes.** `Li`, `TimelineItem`, `ProcessArrowStep`, `FlowNode`, `PyramidLevel`
   and `MatrixItem` reject every box attribute. `Td` takes only `backgroundColor`. So `item.<box attribute>` (D3)
   **cannot be written on a `native` composition**. Every recipe that styles an item's box (an edge, radius, shadow
   or padding per item) needs a code-drawn composition. On `native`, the per-item style power is colour only:
   `color` / `textColor` on diagram items, and fill + text on `Td`.
3. **Four tags accept and ignore everything: `Tr`, `ChartSeries`, `ChartDataPoint` and `TreeItem`** (except `color`
   / `textColor` on `TreeItem`). This is the worst case for an LLM, because nothing fails, so no repair is
   triggered, and the style is simply lost. A row style (`<TableRow ref backgroundColor>`) must be written by code
   onto every `Td` of that row. A point colour must be written into `Chart chartColors`. The normalizer should log
   these as dropped, not pass them on.
4. **Chart text cannot be styled at all.** Every text attribute on `Chart` is rejected, and `chartColors` is the only
   colour. Together with the data labels that `post_chart` writes in a fixed dark ink, this is why `native
   labelled` is unreadable on graphite-dark (chart sheet). It is a code fix in `pptx-post.js`: the label ink from
   `$chartInk`.
5. **Text style on the group works for `Ul`, `ProcessArrow`, `Pyramid` (partly) and `Td`.** It is rejected on `Table`,
   `Chart`, `Timeline`, `Flow`, `Tree` and `Matrix`, where the only text control is the node's own `*Color`
   attributes. Type sizes are code's anyway (D3 "dropped"), so this matters only for colour and weight.

## R3: plan kinds with no item list to compose

| Kind | List in the plan | A composition word applies? |
|---|---|---|
| `title` | none (title, subtitle; the kicker comes from the outline) | **no**: `native` only. Today's `standard` / `inverted` / `ruled` are style recipes on the header box. `ruled` needs a look part (a rule Shape) that the convention lacks |
| `narrative` | none (one `text`) | **no**: `native` only. `quote` is a content rule, not a word (see callout) |
| `caption` | none | no: `<Text ref>`, no tag of its own (left-blocks Q10) |
| `layer` | two optional shapes: `layers[]` (title + items) or `center` + `nodes[]` + `connections[]` | not now. Only 6 valid of 17 saved; the hub shape (5 of 6) is a picture, not a list. `layers[]` would fit `rows` (one row per layer: title, then items) if it ever repeats |
| `tree` | nested `tree_nodes` | **no**: a hierarchy, not a list; `native` only. 1 saved sample |
| `pyramid` | **yes**, `pyramid_levels` (strings) | words fit (`rows`, `steps`), but there is 1 saved sample. Leave `native` until the data repeats (no one-example rules) |
| `matrix` | **yes**, `matrix_items` (label, x, y) + optional `quadrants` | **`grid`** fits: the 2 × 2 quadrants as equal boxes, each item listed in its cell (sheet `matrix.png`). It fixes the native matrix's small, overlapping labels (AGENTS open item 2d). 4 valid saved samples |

**Contradiction with spec §11.3 R3:** `pyramid` and `matrix` do have item lists. Matrix has a fitting word
today. The spec's list of "no item list" should be `title`, `narrative`, `caption` and `tree`, with `layer` as a
free-form diagram.

## R4: the plan fields each composition needs

"Code" = derived by code from fields that exist. **New** = a planner field that does not exist today. Every
new field is optional: the composition falls back (`NODE_VARIANT_UNMET`) or uses the hint until a free replay shows
the hint misses (left-blocks Q8: only on evidence).

| Block · composition | Needs | In today's plan? |
|---|---|---|
| table · `native` | `table_columns`, `table_rows`; the emphasis row or column and its tone from the hint ("accent the Fix column positive") | yes. Emphasis: hint only. **New, optional: `focus_row` / `focus_column`** (index, like `focus_card`) and a tone, if the replay shows the hint misses |
| table · `rows` / `rows numbered` | the same. The first column becomes the row title; the header row becomes small labels on top; the numbers are code's | yes. Not when the first cell already carries an ordinal ("01. Format rebalance", seen in a saved plan): the `numbered` rule must also skip items that **carry their own number**, not only dated ones |
| table · `columns` | the same, ≤ 5 rows and ≤ 6 columns (one column per row, a box per cell) | yes |
| table · `banded` | the same, ≤ 6 rows | yes |
| table · icon header (Q2) | an icon per column | **no: `column_icons`**, or the LLM's `icon` on `<TableColumn>`. Not a word (see contradictions) |
| table · any, with a title band | a table title | **no: `table_title`** (chart has `chart_title`). Low priority: the slide headline usually is the title |
| chart · `native` | `chart_type`, `chart_labels`, `chart_values` / `chart_series`; the focus point from the hint or headline | yes |
| chart · `native labelled` | one series, bar; the value's **unit** for the label format | values: yes. **The unit is in the plan's strings ("0.29x") but is lost**, because `native.number` parses them to floats. Code fix, no new field: derive a number format (`0.00"x"`, `"₹"0.0" Cr"`) from the strings when they share one unit |
| chart · `rows` | one series of any type, ≤ 8 points; values parsed for the bar length, **written verbatim** | yes. 19 of the 46 saved charts fit (one-series bar, 4–6 points) |
| bullet_list · `native` | `bullets`; the head / detail split (code, Q7) | yes |
| bullet_list · `rows` / `rows numbered` / `grid` | `bullets` | yes. Icons per point: **no plan field (`bullet_icons`)**. The default look uses a `marker.` dot, and icons come from the LLM's `icon` per `<Bullet>`, as for cards before `icon` |
| bullet_list · `banded` | most points split into head + detail (66 of 142 saved lists have ≥ half split) | yes (code split). Requires: ≥ 75% of points split, else `grid` |
| timeline · `native` | `date`, `label`; a `description` | yes, but `description` is filled 0 of 19 times. Code splits the label (" — ") as the description. **Prompt line** for the planner to fill `description` (left-blocks Q7), no new field |
| timeline · `rail` / `rows` | the same | yes |
| timeline · `banded` | the same + the "now" item to colour the bands done / now / ahead | "now" from the hint only. **New, optional: `focus_item`** (index), same rule as `focus_row` |
| process_arrow · `native` | `process_steps` | yes; long steps break (sheet row 2), so `native` needs `requires: every step ≤ ~24 characters`, else `steps` |
| process_arrow · `steps` / `steps numbered` | `process_steps`, split into title + detail; the destination = the last step (code) | yes. "Phase N: head — detail" splits at ": " into head "Phase N" (sheet). **Code split rule: split at " — " first, then ": "**; and `numbered` must drop a leading "Phase N" / "Step N" ordinal, or not number |
| process_arrow · `rail` | short steps (≤ 7) | yes |
| flow · `native` / `steps` / `steps numbered` | `flow_steps` (linear), destination last | yes. Branches ("Yes: … / No: …", 1 of 10 saved) cannot be drawn by any word: **planner shape change** (left-blocks Q9), not a field |
| callout · `native` | `text`; quotation detected from the text (code) | yes. **New, optional: `tone`, `key_phrase`, `icon`** for the narrative (left-blocks Q8; Q2 `icon_panel`). Today `$tone` resolves to `$accent` |
| header · `native` | outline `label`, `slide_title`, `subtitle` | yes |
| matrix · `grid` | `x_axis`, `y_axis`, `quadrants` (**optional in the schema**), `matrix_items` (x / y low / mid / high) | partly. Requires `quadrants` (else the cells have no names → `native`). `mid` has no cell in a 2 × 2 (drawn as low here): a **rule to define** (`mid` → its own centre band, or `native`). Emphasis cell: hint only (no field) |

## Contradictions with the spec, and proposed edits

| # | Spec says | The renders / probe show | Proposed edit |
|---|---|---|---|
| C1 | §2.4 / D3: `item.<box attribute>` on the group styles every item's box | true on code-drawn compositions only. On a `native` node no item takes a box attribute (R2), and `Tr` / `ChartSeries` / `ChartDataPoint` / `TreeItem` ignore it silently | §2.4: "`item.` reaches code-drawn items. On `native` it is limited to the colours each item tag takes (table: `item.backgroundColor` written by code onto every `Td`; diagram items: `item.color` / `item.textColor`). Other `item.` attributes on `native` → `NODE_ATTR_DROPPED`". The normalizer logs the silently ignored attributes too |
| C2 | §8: table recipes `plain` `minimal` `zebra` `highlight_row` `dark_header` "all five" become style recipes | `plain` and `dark_header` can be written as part attributes **only if** the table node has look parts that code maps onto `Td`s: `header.` (header row), `label.` (first column) and `stripe.` (alternate rows, for `zebra`). `minimal` (a rule under the header only) **cannot be written**: `Td` takes no border, and `cellBorder` is uniform. `highlight_row` is the emphasis look of `native` | §8: table `native` gets the look parts `header.` `label.` `stripe.`; recipes `plain` / `zebra` / `dark_header` in those parts; `minimal` dropped (or drawn as `rows` without numbers, which is the same look); `highlight_row` → emphasis look |
| C3 | §8: table compositions `native`, `rows numbered`, `banded` (icon header) | the Q2 icon header is **not `banded`** by §2.3 (banded = equal boxes, each with a band head over its rest). It is the native table plus an icon per header cell, and it needs a field that does not exist. `banded` by its §2.3 meaning (one box per row, the first cell as the band) renders well, and so does **`columns`** (one column per row, each cell in its own box) | §8 table: `native` (default) · `rows` / `rows numbered` · `columns` (≤ 5 rows) · `banded` (≤ 6 rows). Icon header: not a word; revisit only if `column_icons` is ever added |
| C4 | §8: timeline `columns` = "a segmented bar as the band" | by §2.3, `columns` = one column per item with each **sub-item** in its own box; timeline items have no sub-items. A solid head per item over its text is **`banded`** | §8 timeline: `native` · `rail` · `banded` (the date as the band, coloured done / now / ahead from the "now" item) · `rows`. `columns` is not used for timelines |
| C5 | §8 / F9: callout `quote` is the one block-specific word | a quotation is known from the text (opening quote mark, "— Name" at the end). `native` can draw the mark glyph and the attribution from the content, as "dated steps are not numbered" is a content rule. No word is needed, and **no block in this check needed a block-specific word** | F9 → resolved: no `quote` word. `native` draws a quotation with a `mark.` look part (style: `mark.color`). §2.3 "block-specific words": none needed for the 8 blocks |
| C6 | §8: chart `native`, `native labelled` | `native labelled` loses the plan's unit and is unreadable on dark palettes (labels in a fixed dark ink; R2: chart text cannot be styled). A code-drawn **`rows`** (label · bar · the plan's value verbatim) keeps "0.29x" and reads on both palettes, and every part is style-able | §8 chart: `native` (default) · `native labelled` (after two code fixes: label ink from `$chartInk`, number format from the plan's unit) · **`rows`** (one series, ≤ 8 points) |
| C7 | §8: bullet_list `native`, `rows` (`cols="2"` = two columns), `grid` | all three render; **`banded`** also fits when most points split, and **`rows numbered`** works as on cards | §8 bullet_list: `native` (default; a split point's head bold) · `rows` / `rows numbered` · `grid` · `banded` (≥ 75% of points split). `lead` and `icon` stop being names: `lead` is `native`'s default, and icons are the LLM's `icon` per `<Bullet>` |
| C8 | §8: process_arrow `native` (default) for any steps | long "Phase N: head — detail" steps break the native chevrons (sheet row 2) | process `native` requires every step ≤ ~24 characters (the break-map measure), else `steps`. The default is chosen from the content, as F4 proposes for cards |
| C9 | §8 / §11.3 R3: "Pyramid, tree and matrix stay native POM only"; they have "no item list" | matrix has items and fits **`grid`** (sheet `matrix.png`), which removes the overlapping labels of the native matrix; pyramid has a list but 1 saved sample | §8: matrix `native` · `grid` (requires `quadrants`). Pyramid / tree stay `native`. R3 list: `title`, `narrative`, `caption`, `tree`, and `layer` as free-form |
| C10 | §2.3 modifier `numbered`: "not when the items carry dates" | items that carry their **own ordinal** ("Phase 1: …", "01. Format rebalance" in a saved table) get a second number | `numbered`: not when the items carry dates **or their own ordinal**. Code splits at " — " before ": ", so "Phase 1: Foundation — detail" gives a head of "Phase 1: Foundation", not "Phase 1" |
| C11 | §6: peer ids on the items (`card-<cid>-<i>`) make peers one size | **not enough when an item's children stretch.** The item box is then never sparse, and fit-grow grows each inner box alone. In the first render, table `columns` column 4 and the `banded` top row ended larger than their peers. Fixed in the script by giving every inner box `card-<cid>x-<n>` (one peer group per block) | §6 / build step 2: a composition node ids its inner boxes as one peer group (`card-<cid>x-<n>`), or fit-grow learns that the inner boxes of one `card-` group are peers by position. Note for the KPI / card nodes, which have the same shape in `columns` / `banded` |
| C12 | §6 finding 2 (one-row compositions are width-bound) | the same holds for code-drawn **rows with a bar or number column**: chart `rows` stayed at 20 / 24 px with 40% of the box empty. fit-grow grows unboxed body text only up to its caps; the KPI `rows` proof grew to 76 px because its values were `kpiv-` refs | build: a code-drawn `rows` writes its value / label as element refs (or role ids) so fit-grow grows them as values. Same check as F3 |
| C13 | §8 header: `standard` `inverted` `ruled` become recipes | `standard` and `inverted` are header box attributes. `ruled` draws a Shape (the accent rule) that no attribute can add | header: `ruled` needs a `rule.` look part, like `marker.` (drawn when `rule.fill.color` is set) — or drop it. Not built (no failure in the data) |
| C14 | §11.3 R2 known limit: "borders rejected on `Td` / `Li` / …" | confirmed, and wider: these tags reject **every** box attribute. `Td` takes only `backgroundColor`; and `padding` on `Flow` / `Pyramid` / `Tree` is silently ignored | `llm.md`-derived knowledge (`attributes.yaml` / `nodes.yaml`): list per item tag what it takes (from `r2-attributes.json`) |


### Proposed replacement for spec §8 (for your approval; the spec itself is not edited)

| Block (tag) | Compositions (`variant`, default first) | requires → fallback | Becomes a style recipe |
|---|---|---|---|
| table (`<Table>`) | `native` · `rows` / `rows numbered` · `columns` · `banded` | `columns`: ≤ 5 rows, ≤ 6 columns; `banded`: ≤ 6 rows → `native` | `plain` (default look), `zebra` (`stripe.`), `dark_header` (`header.` / `label.`); `highlight_row` = emphasis look; `minimal` dropped |
| chart (`<Chart>`) | `native` · `native labelled` · `rows` | `labelled` / `rows`: one series, ≤ 8 points (bar for `labelled`) → `native` | `focus_label` = emphasis look of `native labelled`; `horizontal` → `direction` |
| bullet_list (`<BulletList>`) | `native` · `rows` / `rows numbered` · `grid` · `banded` | `banded`: ≥ 75% of points split → `grid` | `lead` = `native` default; `icon` = `rows` + LLM `icon`; `tiles` = `grid`; `columns` = `rows cols="2"` |
| timeline (`<Timeline>`) | `rail` · `rows` · `banded` · `native` | `native`: every label fits the break-map room and no detail → else `rail` (default chosen from content) | `vertical` → `direction` |
| process_arrow (`<ProcessArrow>`) | `native` · `steps` / `steps numbered` · `rail` | `native`: every step fits → else `steps` (default chosen from content); `numbered`: no dates, no own ordinals | — |
| flow (`<Flow>`) | `native` · `steps` / `steps numbered` | linear list only | — |
| callout (`<Narrative>`) | `native` (quotation drawn by content rule) | — | `tinted` (default look), `rule`, `dark`, `plain` |
| header (`<Title>`) | `native` | — | `standard` (default), `inverted`; `ruled` needs `rule.` |
| matrix (`<Matrix>`) | `native` · `grid` | `grid`: `quadrants` present → `native` | — |

Pyramid and tree stay `native`.

### Proposed edits to spec §11

- §11.1 "The other 8 blocks" row: replace "only names" with the table above. Today's names map as in the verdict
  table, and none is dropped without a home except table `minimal`.
- §11.2: **F9 resolved** (no `quote` word, C5). **New F11:** the look parts the native table needs (`header.`
  `label.` `stripe.`), written onto `Td`s by code. **New F12:** what the normalizer does with attributes POM
  silently ignores (`Tr`, `ChartSeries`, `ChartDataPoint`, `TreeItem`): drop with `NODE_ATTR_DROPPED`, or move a
  row's attributes onto its cells. **New F13:** defaults chosen from the content for timeline / process (with F4).
- §11.3: **R1–R4 done** (this folder). **New R9:** the code fixes found here, all free to check:
  - chart label ink from `$chartInk` and a number format from the plan's unit (C6);
  - the split order " — " before ": " and the `numbered` ordinal rule (C10);
  - inner-box peer ids for composition nodes (C11);
  - value refs for code-drawn `rows` (C12).
- §2.3: "Block-specific words: none needed for the 8 blocks" (C5).
- §2.4: the `item.` limit on `native` (C1).

## Other things found (outside this task, not fixed)

- `scripts/composition_convention.py` lines 101 and 130 fail `tests/unit/test_py311_syntax.py`: a backslash
  inside an f-string expression, which will not parse on the test PC's Python 3.11. A two-line fix.
- POM gives an unsized `VStack` in an `HStack` an equal share of the row. The arrow columns between step boxes
  took 161 px each, and the boxes shrank to their text. `left_blocks_gallery.numbered` (today's `numbered` row)
  has this flaw. Pin connector columns (`w="32"`).
- On that layout, fit-grow threw `Cannot read properties of undefined (reading 'f')` and skipped the slide (it is
  never fatal; it compiled the original). It did not recur after the arrows were pinned. It is worth a regression
  case: `output/composition-left/` reproduces it if the arrow width is removed.
- `native.process_arrow` / `flow` / `pyramid` / `tree` write `textColor="FFFFFF"`, a literal hex, against the
  tokens-only rule. White text on `$accent` is low-contrast where the palette's accent is light (graphite-dark's light blue). `$onAccent` is the token for it.

## Reproduce

```bash
python -m scripts.composition_gallery_left
```

```bash
python -m scripts.native_style_probe
```
