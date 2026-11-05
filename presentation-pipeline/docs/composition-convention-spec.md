# Composition nodes: reference and design record

**Status: for senior review, 2026-11-05.** This document has two parts:

- **Part A (reference)** describes the code on `feat/tile-nodes` at `b1d1328`: every native node, every reference binding and every derived node. Variant tables are generated from `block-variants.yaml`, and each behaviour stated was run through the real expander and compiler.
- **Part B (design record)** is the spec as approved on 2026-10-27 and extended on 2026-11-03, kept so its decisions and reasons stay readable. Other documents cite its section numbers, so they are unchanged. **Where the two differ, Part A is right.**

## A.0 Summary

A slide reaches the `.pptx` like this:

```text
plan JSON -> generator LLM writes POM XML -> composed.expand (derived nodes) -> element_refs / tiles fill (references)
          -> normalize_xml -> fit-grow (sizes type to the boxes) -> POM 10.3.0 compile -> pptx-post
```

| Topic | Position today |
|---|---|
| Families | Three: **native** (the LLM writes POM XML), **reference binding** (the LLM lays out, code writes the words), **derived** (the LLM places one tag, code draws the block) |
| Derived nodes built | Six: `chart`, `timeline`, `kpi_row`, `card_grid`, `table`, `bullet_list`, with 28 variants in all |
| Plan kinds still written by hand | Nine: `title`, `narrative`, `caption`, `layer`, `process_arrow`, `flow`, `pyramid`, `tree`, `matrix` |
| On by default? | **No.** With no settings, only KPI text is bound by reference. All six nodes need `POM_NODES` (A.1) |
| Proof with a real LLM | One paid same-plan run; its rerun's result is not in the repo, and the full-deck run has not been run (A.8) |

**Please review first:** the open points in A.9, especially the missing rerun result, the three overlapping variant vocabularies, and the 280 px box.

## A.1 The three families and the switches

| Family | What the LLM writes | What code does | Example |
|---|---|---|---|
| **Native** | The POM node in full, with its text | Normalizes and fits it; never changes POM's syntax | `<Pyramid h="240"><PyramidLevel label="Top"/></Pyramid>` |
| **Reference binding** | Its own boxes, with a reference where each piece of plan text goes | Writes the text, sizes and ids | `<Text ref="kpis.0.value"/>` |
| **Derived** (also "composition node") | One tag naming a plan component | Expands it into native nodes from the plan | `<CardGrid ref="levers" variant="banded" grow="1"/>` |

**A naming trap:** `variant="native"` on a derived node is still derived. The LLM writes `<Table ref="gaps" variant="native"/>`, and code writes the real `<Table><Tr><Td>`. `blocks.*.family: native` in the YAML means the same thing, and `spec.DERIVED_TAGS` lists only the two tags that are not POM names.

Two settings choose the route (`.env`, read per process):

| Route | `POM_BLOCKS` | `POM_NODES` | Effect |
|---|---|---|---|
| Old | `off` | empty | Everything by hand |
| **Default** | `kpi` (also when unset) | empty | KPI text by field reference; everything else by hand |
| A | `tiles` | empty | Older tile tags `<KpiGrid>` / `<CardGrid>`; the rest by hand |
| **B** | `tiles` | `chart,timeline,kpi_row,card_grid,table,bullet_list` | All six derived. `python -m scripts.eval_run ... --nodes` sets this |

Each kind in `POM_NODES` switches on alone. `kpi_row` also needs `POM_BLOCKS` to be `kpi` or `tiles`, because `<KpiRow>` expands into field references that `fill_refs` then fills.

## A.2 Every plan kind, by route

These are the 15 kinds of `state.ComponentKindLiteral`. "Hand" means the LLM writes native POM XML from the plan's text.

| Plan kind | Plan content (`planner_schema_typed.py`) | Default | Route A | Route B |
|---|---|---|---|---|
| `kpi_row` | `kpi_labels`, `kpi_values`, optional `kpi_deltas`, `kpi_directions`, `kpi_tones`, `kpi_icons` | `<Text ref>` | `<KpiGrid ref>` | `<KpiRow ref>` |
| `card_grid` | `card_layout`, `cards[]` (`title`, `tag`, `body`, `bullets`, `tone`, `key_phrase`, `icon`), `focus_card` | Hand | `<CardGrid ref>`, tile variants | `<CardGrid ref>`, compositions |
| `card_grid`, `card_layout: matrix` | also `columns`, `rows` | Hand | Hand | Hand (deferred) |
| `chart` | `chart_title`, `chart_labels`, `chart_values` or `chart_series` | Hand | Hand | `<Chart ref>` |
| `table` | `table_columns`, `table_rows` | Hand | Hand | `<Table ref>` |
| `timeline` | `direction`, `timeline_items[]` (`date`, `label`, `description`) | Hand | Hand | `<Timeline ref>` |
| `bullet_list` | `bullets` | Hand | Hand | `<Ul ref>` |
| `process_arrow` | `direction`, `process_steps` | Hand | Hand | Hand (node dropped) |
| `flow` | `direction`, `flow_steps` | Hand | Hand | Hand (node dropped) |
| `pyramid` | `direction`, `pyramid_levels` | Hand | Hand | Hand |
| `tree` | `layout`, `tree_nodes` | Hand | Hand | Hand |
| `matrix` | `x_axis`, `y_axis`, `quadrants`, `matrix_items` | Hand | Hand | Hand |
| `title` | `title`, `subtitle` | Hand | Hand | Hand |
| `narrative`, `caption` | `text` | Hand | Hand | Hand |
| `layer` | `description`, `layers`, `center`, `nodes`, `connections` | Hand | Hand | Hand |

### When each was introduced

| Date | What | Code | Evidence |
|---|---|---|---|
| 2026-10-11 | KPI field references, on by default | `element_refs.py` | `docs/kpi-node-pilot-2026-10-11.md` |
| 2026-10-12 | KPI tile tags `<KpiGrid>` / `<Kpi>`, route A | `tiles.py` | `docs/tile-nodes-spec-2026-10-12.md` |
| 2026-10-13 | Card tile tags `<CardGrid>` / `<Card>`, route A | `cards.py` | same, §11 |
| 2026-10-28 | Chart node; timeline, process arrow and flow nodes | `charts.py`, `sequences.py`, `composed.py` | `docs/eval/chart-node/`, `docs/eval/sequence-nodes/` |
| 2026-11-01 | KPI and card compositions; table node | `tile_groups.py`, `tables.py` | `docs/eval/composition-convention/`, `docs/eval/table-node/` |
| 2026-11-02 | **Process arrow and flow nodes dropped**: POM's fixed boxes hold about two words, and the code-drawn steps were card grids under another name | `sequences.py` | `docs/eval/sequence-nodes/` |
| 2026-11-04 | Bullet node; **five table variants and card `rail` deleted** | `bullets.py` | `docs/eval/bullet-node/`, `docs/syntax-audit-2026-11-04.md` |

## A.3 Native nodes

These are the POM 10.3.0 tags the LLM may write, from `knowledge/core/nodes.yaml`. Every tag below compiled in a test slide at this commit. The attribute lists come from `nodes.yaml`; `tests/unit/test_upstream_reference.py` compiles POM's own reference examples. This project never changes POM's syntax.

### Structure and layout

| Tag | Own attributes | Children |
|---|---|---|
| `Slide` | none | any layout or content node |
| `Theme` | one per colour token, 6-digit hex only | none |
| `VStack`, `HStack` | `gap`, `alignItems`, `justifyContent`, `flexWrap` | any layout or content node |
| `Layer` | `w`, `h`, `padding`, `margin`, `backgroundColor`, `border`, `borderRadius`, `opacity`, `shadow` | any node, each with `x` and `y` |

### Content

| Tag | Own attributes | Children |
|---|---|---|
| `Text` | `fontSize`, `color`, `textAlign`, `bold`, `italic`, `underline`, `strike`, `subscript`, `superscript`, `fontFamily`, `lineHeight`, `letterSpacing`, `textGradient`, `glow.*`, `outline.*`, `rotate` | inline tags |
| `Shape` | `shapeType` (required), `text`, `fill.*`, `line.*`, `outline.*`, `glow.*`, `rotate`, and the text attributes | none |
| `Icon` | `name`, `size`, `color`, `variant`, `bgColor`, `rotate` | none |
| `Svg` | `w`, `h`, `color` | one `<svg>` |
| `Ul` | `fontSize`, `color`, `textAlign`, `bold`, `italic`, `strike`, `subscript`, `superscript`, `underline`, `fontFamily`, `lineHeight` | `Li` |
| `Ol` | as `Ul`, plus `numberType`, `numberStartAt` | `Li` |
| `Li` | `bold`, `italic`, `strike`, `subscript`, `superscript`, `underline`, `color`, `fontSize`, `fontFamily` | inline tags |

**Inline tags:** `B`, `I`, `U`, `S`, `Sub`, `Sup`, `Span` (`color`, `fontFamily`, `fontSize`, `letterSpacing`), `A` (`href`).

**Common attributes** on most nodes (`core/attributes.yaml`): `id`, `w`, `h`, `grow`, `minW`, `maxW`, `minH`, `maxH`, `padding`, `margin`, `backgroundColor`, `backgroundGradient`, `border`, `borderTop` / `Right` / `Bottom` / `Left`, `borderRadius`, `opacity`, `zIndex`, `position`, `top`, `right`, `bottom`, `left`, `alignSelf`, `shadow`.

### Data and diagrams

| Tag | Own attributes | Children |
|---|---|---|
| `Table` | `defaultRowHeight`, `cellBorder.color` / `width` / `dashType` | `Col`, `Tr` |
| `Col` | `width` (not `w`) | none |
| `Tr` | `height` | `Td` |
| `Td` | `fontSize`, `color`, `textAlign`, `bold`, `italic`, `underline`, `strike`, `subscript`, `superscript`, `fontFamily`, `backgroundColor`, `colspan`, `rowspan` | inline tags |
| `Chart` | `chartType` (`bar`, `line`, `pie`, `area`, `doughnut`, `radar`), `h` (required), `showLegend`, `showTitle`, `title`, `chartColors`, `radarStyle`, `sparkline` | `ChartSeries` |
| `ChartSeries` | `name` | `ChartDataPoint` |
| `ChartDataPoint` | `label`, `value` (both required) | none |
| `Timeline` | `direction`, `dateColor`, `titleColor`, `descriptionColor`, `connectorColor`, `connectorGradient`, `useColorForDate`, `fontFamily`, `w`, `h` | `TimelineItem` |
| `TimelineItem` | `date`, `title` (both required), `description`, `color`, `dateColor` | none |
| `ProcessArrow` | `direction`, `itemWidth`, `itemHeight`, `gap`, `fontSize`, `bold`, `italic`, `strike`, `underline`, `highlight`, `fontFamily`, `w`, `h` | `ProcessArrowStep` |
| `ProcessArrowStep` | `label` (required), `color`, `textColor` | none |
| `Flow` | `direction`, `nodeWidth`, `nodeHeight`, `nodeGap`, `connectorStyle.*`, `w`, `h` | `FlowNode`, `FlowConnection` |
| `FlowNode` | `id`, `shape`, `text` (all required), `color`, `textColor`, `width`, `height` | none |
| `FlowConnection` | `from`, `to` (both required), `label`, `color`, `labelColor` | none |
| `Pyramid` | `direction`, `fontSize`, `bold`, `fontFamily`, `w`, `h` | `PyramidLevel` |
| `PyramidLevel` | `label` (required), `color`, `textColor` | none |
| `Tree` | `layout`, `nodeShape`, `textColor`, `nodeWidth`, `nodeHeight`, `levelGap`, `siblingGap`, `connectorStyle.*`, `w`, `h` | one `TreeItem` |
| `TreeItem` | `label` (required), `color`, `textColor` | `TreeItem` |
| `Matrix` | `w`, `h`, `axisLabelColor`, `quadrantLabelColor`, `itemLabelColor` | `MatrixAxes`, `MatrixQuadrants`, `MatrixItem` |
| `MatrixAxes` | `x`, `y` (label strings, both required) | none |
| `MatrixQuadrants` | `topLeft`, `topRight`, `bottomLeft`, `bottomRight` (all required) | none |
| `MatrixItem` | `label`, `x`, `y` (0 to 1; all required), `color`, `textColor` | none |
| `Line` | `x1`, `y1`, `x2`, `y2` (all required), `color`, `lineWidth`, `dashType`, `beginArrow`, `endArrow` | none |
| `Arrow` | `from`, `to` (both required), `color`, `lineWidth`, `dashType`, `beginArrow`, `endArrow` | none |

`Image` is deferred and not offered to the LLM.

### Limits to review against

- **POM's flexbox is Yoga.** There is no `alignContent` and no min-content width, `grow="0"` is rejected on `Text`, and `w="max"` grows along the parent's main axis (`docs/syntax-audit-2026-11-04.md` §6).
- **Item tags reject borders:** `Td`, `Li`, `Col`, `FlowNode`, `TimelineItem`, `ProcessArrowStep`, `PyramidLevel`, `MatrixItem`. The normalizer removes them (`ITEM_BORDER_REMOVED`).
- **`Td` holds no `Icon` or stack.** Enrichment is composed around core nodes, never inside them.
- **Native diagrams have small fixed boxes** that only shrink: chevrons 150 × 80, flow nodes 120 × 60, timeline titles 120 px. This is why process arrow and flow left the derived set.
- **`Theme` is hex only,** with no fonts or alpha.
- **The normalizer repairs some native XML without a retry,** for example `SHAPE_TYPE_ALIAS`, `ALPHA_COLOR_BLENDED`, `TEXT_BOX_UNSQUEEZED`, `GROW_BAND_ADDED`, `GROW_ROWS_ADDED`, `TEXT_CONTAINER_FLATTENED`, `UNKNOWN_ICON_REMOVED`.

## A.4 Reference bindings

A reference ties something on the slide to the plan by id, so the LLM never types the content. There are five forms.

| Form | Written as | Binds to | Available on |
|---|---|---|---|
| **Group** | `<CardGrid ref="levers"/>` | A whole plan component | The six derived tags (and `<KpiGrid>` in route A) |
| **Item** | `<Card ref="levers.1"/>` | One item, by index from 0 | `<Kpi>`, `<Card>` only |
| **Field** | `<Text ref="kpis.0.value"/>` | One field of one item | `kpi_row` only: `label`, `value`, `note` |
| **Marks by name** | `<Highlight column="Fix" color="good"/>` inside the tag | Rows, columns, cells, points or phrases, by their text | `<Table ref>`, `<Ul ref>` only |
| **POM ids** | `<Arrow from="s1" to="s2"/>` | Another node's `id` | POM's own, unrelated to `ref` |

### Group and item references

```xml
<CardGrid ref="levers" grow="1">
  <Card ref="levers.1" title.color="$negativeText" item.backgroundColor="$warningSoft"/>
</CardGrid>

<HStack grow="1" gap="18">
  <Card ref="levers.0" w="40%"/>
  <CardGrid ref="levers" cols="2" w="1" grow="1"/>
</HStack>
```

An item tag **inside** its group restyles that item. **Outside**, it places the item anywhere, and the group skips it; this is how the LLM gets flexbox freedom with no new syntax.

### Field references

The LLM draws its own tiles and code fills the text:

```xml
<HStack gap="12" grow="1">
  <VStack padding="16" gap="6" backgroundColor="$surfaceAlt">
    <Text ref="kpis.0.label"/>
    <Text ref="kpis.0.value"/>
    <Text ref="kpis.0.note"/>
  </VStack>
</HStack>
```

| Field | Plan key | Code also sets |
|---|---|---|
| `label` | `kpi_labels` | Size 16; a role or tone colour if the LLM gave no `$token` |
| `value` | `kpi_values` | One size per component, the unit as a span, peer ids so values grow together (28 to 96 px; a hero starts at 72 and reaches 120) |
| `note` | `kpi_deltas` | Size 16; a role or tone colour if the LLM gave no `$token` |

Everything else on the tile (boxes, fills, bars, icons) is the LLM's. Text on a dark fill gets a readable colour. If the LLM leaves out a label, code draws it (`NODE_LABEL_PLACED`, a warning). **Cards have no field references**: `<Text ref="levers.0.title"/>` is an error. They were prototyped for the audit and rejected as a default (`docs/syntax-audit-2026-11-04.md` §5: 46 × the tokens, and swapped fields pass unseen).

### Marks by name

| On | Target | Effect | Rules |
|---|---|---|---|
| `<Table ref>` | `row`, `column`, `cell="row / column"`, `phrase` | `fill` (background), `color` (text) | `above` / `below` / `else`, `max` / `min`; `show="arrows"` (`invert`), `show="pills"` and `show="bars"` (those two on `rows` and `ledger` only) |
| `<Ul ref>` | `item`, `phrase` | `color`, `fill` (on rows only), `bold` | |

Tones are `good`, `bad`, `watch`, `focus`. A name or phrase not in the plan is `NODE_HIGHLIGHT_UNKNOWN` (error). Other tags drop `<Highlight>` with a report.

### Binding rules

- **One nesting level.** A reference is never placed inside another. `<Table ref>` inside `<CardGrid ref>` is removed and becomes `NODE_ITEM_MISSING` (error), because the table is then missing from the slide.
- **Each component once.** A second copy, or the same item twice, is `NODE_REF_DUPLICATE` (error).
- **Each drawn component must appear.** Leaving it out, or typing it by hand, is `NODE_ITEM_MISSING` (error).
- **Wrong kind.** A derived tag on a component with no node (a narrative written as `<CardGrid ref>`) is `NODE_REF_UNKNOWN` (error); the message hands over the component's words so the repair can write it by hand.
- **Kinds that can never be referenced:** `title` and `layer` (`spec.NO_REF_KINDS`).

### Ids code writes

fit-grow reads these to size peers together. The LLM does not see or write them.

| Id prefix | Marks |
|---|---|
| `kpiv<rank>-`, `kpih<rank>-` | KPI values, and a hero value; rank comes from the plan's `weight` |
| `kpil-` | KPI labels |
| `kpig-`, `cardg-` | A KPI or card group whose columns code chose, so fit-grow may re-grid it |
| `card-<cid>-<i>`, `card-<cid>x-<n>` | Items, and their inner boxes |
| `cardt-`, `cardb-`, `cardn-`, `cardf-` | Card title, body, numeral, and the `bento` focus block |
| `tbl-` | Table |
| `lst-`, `lsth-` | Bullet list, and a row head |

## A.5 Derived nodes

### How a tag resolves

1. **Alias:** an old variant name maps to its replacement (`NODE_ATTR_ALIAS`, a report). Saved slides keep working.
2. **No variant:** on KPI and cards, the design hint can name a word (hero or spotlight gives `bento`, ruled gives `rows`, strip gives `strip`; `NODE_LOOK_FROM_HINT`). Otherwise the first variant whose `requires` hold, along the fallback chain (`NODE_DEFAULT_FROM_CONTENT`).
3. **Unknown variant:** the default (`NODE_VARIANT_UNKNOWN`, a warning).
4. **`requires` fails:** the `fallback` chain (`NODE_VARIANT_UNMET`, a warning). The prompt line offers only the variants that fit.
5. **Emphasis** always comes from the plan (`focus_card`, the hint, or the last step), never from the LLM.

The tables below come from `nodes.<kind>` in `block-variants.yaml`. "In the `.pptx`" was read from compiled files. **Only `table native`, `chart native` / `native labelled` and `bullet_list native` / `native numbered` stay real PowerPoint objects** that a person can edit as one; everything else is loose shapes.

**`requires` checks** (`spec.check`), all on the plan, none on the box: `count_le_N` / `count_ge_3` count items; `layout_grid` / `layout_steps` read `card_layout`; `has_emphasis` means the plan singles out one item; `no_own_numbers` means no item already carries a number or date; `bullets_every_card`; `rows_fit` estimates bullet height; `columns_le_6`; `labels_short` means every label is at most 24 characters with no detail; `one_series`; `chart_is_bar`.

### `chart`: `<Chart ref>`

The chart type, colours and focus bar are code's. `direction="horizontal"` turns native bars. Chart text takes no attribute, so style power lives in `rows`.

| Variant | What it draws | Needs → else | Ignores (reported if written) | In the `.pptx` |
|---|---|---|---|---|
| `native` | the chart, one hue, the focus bar in the accent | nothing | `alignItems`, `label`, `value`; only `bar.fill.color` | real chart |
| `native labelled` | each bar's value written on it, no value axis | `one_series`, `count_le_8`, `chart_is_bar` → `native` | `alignItems`, `value`; only `label.color/bold`, `bar.fill.color` | real chart |
| `rows` | one row per point: label, a bar, the value as written | `one_series`, `count_le_8` → `native` | `showLegend` | loose shapes |

- **Tag attributes:** `ref`, `variant`, `direction`
- **Parts:** `title.` (Text), `label.` (Text), `value.` (Text), `bar.` (Shape)
- **Native attributes passed on:** `showLegend`. **Code-owned, dropped if written:** `chartColors`, `chartType`, `title`, `showTitle`
- **Recipes:** none
- **Aliases:** `plain` → `native`, `labelled` → `native labelled`, `focus_label` → `native labelled`, `horizontal` → `native`

### `timeline`: `<Timeline ref>`

The default is chosen from the content: `native` needs short labels with no detail, so a timeline with detail starts at `rail`. A vertical timeline that is not native draws `rows`. With this node on, the planner fills `description` as its own field.

| Variant | What it draws | Needs → else | Ignores (reported if written) | In the `.pptx` |
|---|---|---|---|---|
| `native` | POM's timeline: dots on a line, short labels only | `labels_short` → `rail` | `alignItems`, `gap`, `justifyContent`, `band`, `item`; only `date.color`, `title.color`, `description.color`, `marker.fill.color`, `connector.fill.color` | loose shapes |
| `rail` | dots on a line, date and label alternating above and below | `count_le_7` → `columns` | `band`, `item` | loose shapes |
| `columns` | a line with a dot per point, one box per point under it | nothing | `band` | loose shapes |
| `rows` | one point per ruled row: date, head, detail; what a vertical timeline with details draws | nothing | `marker`, `connector`, `band` | loose shapes |
| `banded` | equal boxes, the date in a solid band: done / now / ahead | nothing | `marker`, `connector` | loose shapes |

- **Tag attributes:** `ref`, `variant`, `direction`
- **Parts:** `date.` (Text), `title.` (Text), `description.` (Text), `marker.` (Shape), `connector.` (Shape), `band.` (Box), `item.` (Box)
- **Native attributes passed on:** none. **Code-owned, dropped if written:** `dateColor`, `titleColor`, `descriptionColor`, `connectorColor`, `useColorForDate`
- **Recipes:** none
- **Aliases:** `vertical` → `native`, `cards` → `columns`, `alternating` → `rail`

### `kpi_row`: `<KpiRow ref>` and `<Kpi ref>`

Expands into field references (A.4). `cols` is a measured knob that code may overrule. `size="hero"` on an item needs the plan's emphasis item.

| Variant | What it draws | Needs → else | Ignores (reported if written) | In the `.pptx` |
|---|---|---|---|---|
| `grid` | separate tiles, icon and label over the value and delta (default) | nothing | `band`, `divider`, `value.bold`, `item.grow`, `item.borderRadius` | loose shapes |
| `strip` | one shared box, items side by side split by hairlines, one row (at most 5) | `count_le_5` → `grid` | `borderRadius`, `band`, `value.bold`, `item.borderRadius` | loose shapes |
| `rows` | one item per ruled row: icon badge, label over delta, the value at the right | nothing | `borderRadius`, `band`, `value.bold`, `item.borderRadius` | loose shapes |
| `banded` | equal boxes, each with a solid coloured band holding icon + label (at most 5) | `count_le_5` → `grid` | `marker`, `divider`, `value.bold`, `item.borderRadius` | loose shapes |
| `bento` | the emphasis item as one large dark block, the others as rows beside it | `count_ge_3`, `has_emphasis` → `grid` | `band`, `divider`, `value.bold`, `item.borderRadius` | loose shapes |

- **Tag attributes:** `ref`, `variant`, `cols`, `color`, `icon`. On the item tag: `ref`, `variant`, `color`, `icon`, `size`
- **Parts:** `label.` (Text), `value.` (Text), `delta.` (Text), `icon.` (Icon), `marker.` (Shape), `band.` (Box), `divider.` (Rule), `item.` (Box)
- **Native attributes passed on:** none. **Code-owned, dropped if written:** none
- **Recipes:** `filled`, `toned`, `bar`, `dot`, `bare`
- **Aliases:** `plain` → `grid`, `filled` → `grid`, `toned` → `grid`, `bar` → `grid`, `dot` → `grid`, `bare` → `grid`, `inverted` → `grid`, `divided` → `strip`

### `card_grid`: `<CardGrid ref>` and `<Card ref>`

`rows_fit` (`cards.rows_fit`) estimates bullet lines against a full slide, because bullets set a row's height while body text can shrink. A `card_layout: matrix` plan has no node and stays hand-written.

| Variant | What it draws | Needs → else | Ignores (reported if written) | In the `.pptx` |
|---|---|---|---|---|
| `grid` | separate cards: icon, tag, title, body, bullets (default for grid plans) | `layout_grid` → `steps` | `number`, `band`, `bullets`, `divider` | loose shapes |
| `grid numbered` | cards with a large 01 02 03 above each title | `layout_grid`, `no_own_numbers` → `grid` | `band`, `bullets`, `divider` | loose shapes |
| `rows` | one card per ruled full-width row: icon, tag over title, body, bullets | `count_le_6`, `rows_fit` → `grid` | `number`, `band`, `bullets`, `item.grow` | loose shapes |
| `rows numbered` | rows led by a large 01 02 03 | `count_le_6`, `no_own_numbers`, `rows_fit` → `rows` | `icon`, `band`, `bullets`, `item.grow` | loose shapes |
| `columns` | one column per card: the tag, a coloured pill head, the body, each bullet in its own box | `bullets_every_card`, `count_le_5` → `grid` | `number`, `divider`, `item.grow` | loose shapes |
| `banded` | boxes with a solid coloured band (icon, title, tag) over body and bullets | `count_le_6` → `grid` | `number`, `bullets`, `divider`, `item.grow` | loose shapes |
| `bento` | the focus card as one large dark block, the others beside it; at least 500 px wide | `layout_grid`, `count_ge_3`, `count_le_5`, `has_emphasis` → `grid` | `number`, `band`, `bullets`, `divider` | loose shapes |
| `steps` | cards in a row joined by arrows, the destination dark (default for steps plans) | `layout_steps` → `grid` | `gap`, `number`, `band`, `bullets`, `divider` | loose shapes |

- **Tag attributes:** `ref`, `variant`, `cols`, `color`, `icon`. On the item tag: `ref`, `variant`, `color`, `icon`
- **Parts:** `tag.` (Text), `title.` (Text), `body.` (Text), `icon.` (Icon), `number.` (Text), `band.` (Box), `bullets.` (Box), `divider.` (Rule), `item.` (Box)
- **Native attributes passed on:** none. **Code-owned, dropped if written:** none
- **Recipes:** `column`, `filled`, `outline`, `toned`, `accent_top`
- **Aliases:** `lifted` → `grid`, `rail` → `steps`, `column` → `grid`, `filled` → `grid`, `outline` → `grid`, `toned` → `grid`, `accent_top` → `grid`, `numerals` → `grid numbered`, `inverted` → `grid`

### `bullet_list`: `<Ul ref>`

`native` is the default and the end of every fallback. `spacing="tight"` keeps points at the top, and fit-grow splits 4+ short points into two real lists. `icons` works on `rows`, up to 6 points.

| Variant | What it draws | Needs → else | Ignores (reported if written) | In the `.pptx` |
|---|---|---|---|---|
| `native` | a real editable list: bold lead-ins, accent markers, points spaced to fill its box; 4+ short points split into two columns by themselves | nothing | none | real list (one text box) |
| `native numbered` | the same list, auto-numbered | `no_own_numbers` → `native` | none | real list (one text box) |
| `rows` | one ruled row per point: a dot (or an icon), the head over the detail | nothing | none | loose shapes |
| `rows numbered` | rows with 01 02 03 leading each | `no_own_numbers` → `rows` | none | loose shapes |

- **Tag attributes:** `ref`, `variant`, `icons`, `spacing`
- **Parts:** `head.` (Run), `detail.` (Run), `marker.` (Marker), `item.` (Box)
- **Native attributes passed on:** `color`, `textAlign`, `italic`. **Code-owned, dropped if written:** none
- **Recipes:** none
- **Aliases:** `plain` → `native`, `icon` → `rows`, `columns` → `native`

### `table`: `<Table ref>`

`native` is the only real PowerPoint table, so a person can drag its columns. Pills and bars work only on `rows` and `ledger`; `icons` only on `ledger`.

| Variant | What it draws | Needs → else | Ignores (reported if written) | In the `.pptx` |
|---|---|---|---|---|
| `native` | POM's table: solid header band, striped rows, no borders, bold first column, the hinted row / column tinted | nothing | `alignItems`, `gap`, `justifyContent` | real table |
| `rows` | one ruled row per table row: the first cell as its title, the other cells to the right | nothing | `cellBorder.color`, `cellBorder.dashType`, `cellBorder.width`, `stripe` | loose shapes |
| `ledger` | one solid header band (an icon over each column name) over joined, tinted rows | `columns_le_6` → `native` | `cellBorder.color`, `cellBorder.dashType`, `cellBorder.width`, `stripe.bold`, `stripe.color`, `stripe.italic`, `stripe.textAlign`, `stripe.underline` | loose shapes |

- **Tag attributes:** `ref`, `variant`, `icons`
- **Parts:** `header.` (Cell), `label.` (Cell), `cell.` (Cell), `stripe.` (Cell), `item.` (Box)
- **Native attributes passed on:** `cellBorder.color`, `cellBorder.width`, `cellBorder.dashType`. **Code-owned, dropped if written:** `defaultRowHeight`, `labels`
- **Recipes:** `borderless`, `bordered`, `dark_header`, `accent_edge`, `lifted`
- **Aliases:** `plain` → `native`, `rows numbered` → `rows`, `columns` → `native`, `banded` → `native`, `grid` → `native`, `grid numbered` → `native`, `highlight_row` → `native`, `zebra` → `native`, `dark_header` → `native`

### Names that no longer exist

Table and card names still work as aliases, so saved slides keep drawing.

| Removed | Now draws | Why |
|---|---|---|
| Table `rows numbered` | `rows` | Hand-editability: only `native` is a real table (user, 2026-11-04) |
| Table `columns`, `banded`, `grid`, `grid numbered` | `native` | Same |
| Card `rail` | `steps` (`grid` on a grid plan) | Spilled from 4 cards (user, 2026-11-04) |
| Bullet `grid`, `banded` | Unknown, so the default | Removed before merging, as duplicates of the card grid (user, 2026-11-04) |
| `process_arrow`, `flow` nodes | Hand-written POM | See A.2 |

Older names still read: KPI `plain`, `filled`, `toned`, `bar`, `dot`, `bare`, `inverted`, `divided`, and card `lifted`, `column`, `filled`, `outline`, `toned`, `accent_top`, `numerals`, `inverted`. `arrange` and `layout` also map to compositions, and `<KpiGrid>` to `<KpiRow>` (`NODE_TAG_ALIAS`).

### Never built

`Callout` and `SlideHeader` appear in `spec.DERIVED_TAGS` and `blocks`, but no expander exists. Narratives and titles are written by hand. Matrix `grid` was rendered only.

## A.6 Who owns what, and how style works

| Owner | Controls |
|---|---|
| **Code** | Every word and number, verbatim and in plan order; which parts appear and their order; type sizes; word fit; the emphasis item; ids |
| **LLM** | Layout around the tag; `w`, `h`, `grow`, `min*`, `max*`, `alignSelf`; the variant; every style attribute |

Later layers win: **composition `look` → `tone` → `emphasis` → the hint's or alias's recipe → group attributes → item tag.**

| Written as | Reaches | Example |
|---|---|---|
| A box attribute on the group | The group's own box only, no cascade | `backgroundColor="$surfaceAlt"` |
| `item.<box attribute>` on the group | Every item's box | `item.borderLeft.color="$tone"` |
| `<part>.<attribute>` on the group | That part in every item | `title.color="$toneText"` |
| Either, on an item tag | That one item | `<Card ref="levers.1" title.color="$negativeText"/>` |

**Part attribute types** (`compose.part_attrs`):

| Type | Attributes |
|---|---|
| Text | `color`, `bold`, `italic`, `underline`, `letterSpacing`, `textAlign`, `textGradient`, `glow.size`, `glow.opacity`, `glow.color`, `outline.size`, `outline.color` |
| Icon | `name`, `color`, `variant`, `bgColor`, `glow.size`, `glow.opacity`, `glow.color`, `outline.size`, `outline.color` |
| Shape | `shapeType`, `w`, `h`, `fill.color`, `fill.transparency`, `line.color`, `line.width`, `line.dashType`, `glow.size`, `glow.opacity`, `glow.color` |
| Rule | `color`, `width` |
| Cell | `backgroundColor`, `color`, `bold`, `italic`, `underline`, `textAlign` |
| Run | `color`, `bold`, `italic`, `underline` |
| Marker | `color` |
| Box | the box attributes below |

**Box attributes:** `backgroundColor`, `backgroundGradient`, `border`, `border.color`, `border.width`, `border.dashType`, `borderTop.color`, `borderTop.width`, `borderRight.color`, `borderRight.width`, `borderBottom.color`, `borderBottom.width`, `borderLeft.color`, `borderLeft.width`, `padding`, `padding.top`, `padding.right`, `padding.bottom`, `padding.left`, `gap`, `alignItems`, `justifyContent`, `shadow.type`, `shadow.blur`, `shadow.offset`, `shadow.color`, `shadow.opacity`, `opacity`, `w`, `h`, `grow`, `minW`, `maxW`, `minH`, `maxH`, `alignSelf`, `margin`.

**Colours are `$tokens` only.** A typed hex is removed (`LITERAL_COLOR`, a warning), so a theme switch restyles the slide. `$tone`, `$toneSoft`, `$toneText` and `$toneDark` follow each item's plan tone: good is `$positive*`, bad is `$negative*`, watch is `$warning*`, and none is `$accent*`. Charts and timelines have no item tones, so there `$tone*` becomes the accent, with a report.

**Dropped with a report, never followed:** `fontSize`, `fontFamily`, `lineHeight`, `text`, `size`, `highlight` on parts; `position`, `top`, `right`, `bottom`, `left`, `zIndex`, `id` on boxes; and each node's code-owned attributes.

**Style recipes** (`styles:`) are prompt examples, not values the tag accepts as a recipe name. The LLM can write any allowed combination.

## A.7 Validation codes

An **error** goes to the repairer, which costs a call. A **warning** or **report** is logged and the slide proceeds.

| Code | Level | Trigger |
|---|---|---|
| `NODE_REF_UNKNOWN` | Error | Bad id or index; a tag on a kind with no node; `<Text ref>` on a card or with field `delta`; a tag from another route |
| `NODE_REF_DUPLICATE` | Error | The same group or item placed twice |
| `NODE_ITEM_MISSING` | Error | A drawn component left out, nested in another reference, or missing items |
| `NODE_ATTR_UNKNOWN` | Error | An invented attribute or part (`foo="1"`, `nosuch.color`) |
| `NODE_HIGHLIGHT_UNKNOWN` | Error | A `<Highlight>` target or attribute not in the plan or grammar |
| `NODE_LABEL_MISSING` | Error | A label typed by hand in a tile, where it could sit beside the wrong value |
| `NODE_XML_INVALID` | Error | A slide with KPI references that cannot be parsed |
| `NODE_VARIANT_UNKNOWN`, `NODE_VARIANT_UNMET` | Warning | Unknown variant; `requires` failed, fallback drawn |
| `LITERAL_COLOR` | Warning | A typed colour |
| `NODE_HIGHLIGHT_LIMIT`, `NODE_HIGHLIGHT_RULE` | Warning | More than 6 marks (all drawn); a value rule on cells without one unit |
| `NODE_LABEL_PLACED`, `NODE_FIELD_MISSING` | Warning | Code placed a label; a field reference left out |
| `NODE_ATTR_DROPPED`, `NODE_ATTR_NO_EFFECT` | Report | Code-owned attribute removed; the variant does not draw it |
| `NODE_ATTR_ALIAS`, `NODE_TAG_ALIAS` | Report | An old name was read |
| `NODE_DEFAULT_FROM_CONTENT`, `NODE_LOOK_FROM_HINT`, `NODE_TEXT_SPLIT`, `NODE_VERTICAL_ROWS` | Report | Code chose a default; a hint named the look; a label split into head and detail; a vertical timeline drew `rows` |

## A.8 Evidence

**Measured at this commit (free):**

| Check | Result |
|---|---|
| Every variant compiled on a sample plan | 28 of 28 |
| Attribute × variant pairs that silently do nothing | 0 of 3,904 on five nodes; `bullet_list` 0 flagged of 344 on its own probe, after discarding on/off values equal to the default |
| Unit tests | 2120 pass, with the 4 known failures. Left out: one new test in `b1d1328` that leaks `POM_NODES` and fails 6 later tests; the next local commit, `b2ed3c5`, fixes it |

**Free blind marks.** The user's marks on bare tags against the LLM's own drawing, with no LLM writing the tags. The gate is at least 0.5, and by the user's rule a tie counts as satisfied. The other two columns show how much rests on that rule.

| Node | Node wins | LLM wins | Same | Ties satisfied | Ties split | Ties left out | Source (`docs/eval/`) |
|---|---:|---:|---:|---:|---:|---:|---|
| `kpi_row`, `card_grid` | 11 | 2 | 26 | 0.949 | 0.615 | 0.846 | `composition-convention/replay.md` |
| `chart` | 3 | **7** | 43 | 0.868 | **0.462** | **0.300** | `chart-node/replay.md` |
| `timeline` | 14 | 3 | 6 | 0.870 | 0.739 | 0.824 | `sequence-nodes/replay.md` |
| `table` | 10 | 2 | 54 | 0.970 | 0.561 | 0.833 | `table-node/replay.md` |
| `bullet_list` | 17 | 5 | 6 | 0.821 | 0.714 | 0.773 | `bullet-node/replay.md` |

**Card stress review** (8 variants × 8 cases, `docs/syntax-audit-2026-11-04.md` §7): 33 pass, 23 warn, 8 break, and all 8 breaks are the 280 px box. The other nodes had the wider audit run before this round's changes, not a re-run.

**Paid same-plan check** (22 saved plans, each drawn by routes A and B, first run 2026-11-04, $1.40, `docs/eval/nodes-paid/README.md`):

| | Route A | Route B |
|---|---:|---:|
| Compiled first try | 21 of 22 | 16 of 22 |
| Repair passes | 1 | 10 |
| Placeholder slides | 0 | 1 |
| Plan words lost | 0 | 12, on 2 slides |
| Cost | $0.675 | $0.726 |
| Blind marks | 4 | 8 (10 the same) |

So the first run did **not** meet the gate (no words lost, no placeholder, B wins the marks). Five causes were fixed, in `05a69db` and `98e800d`, and the 6 failed slides were set for a rerun. See A.9 item 1 for that rerun's status.

**Not yet run:** the full-deck run on fresh plans (`docs/eval/nodes-deck/README.md`, about $1.05, stops at $2). It is the first test of the planner's timeline `description` field and of the real repair cost.

## A.9 Open points for review

**Evidence**

1. **The rerun's result is not in the repo.** `docs/eval/nodes-deck/README.md` says the same-plan check passed the gate; `docs/eval/nodes-paid/README.md` still says "gate not met yet", and `0aaeab5` ("gate confirmed") only records the gate's wording. No `nodes-b6` results exist in `docs/` or on the build PC. Until they are added, treat the pass as unverified.
2. **`chart` passes only because ties count as satisfied.** The LLM won 7 of the 10 decisive pairs (0.462 with ties split, 0.300 with ties left out). Every other node stays above 0.5 under all three rules.
3. **The silent-attribute probe proves an attribute reaches the XML,** not that it changes the picture.

**Design**

4. **Three variant vocabularies share one YAML.** `nodes` is what route B reads, `tile_nodes` is route A's, and `blocks` holds the 1a route's plus the prompt phrases for four nodes. Route A's code (`tiles.py`, `cards.py`) sits beside `tile_groups.py`, which reuses parts of it. Should route A go once B is the default?
5. **Code that production does not call.** `validate.check_skeleton`, `prompt_lines.py` and most `native.py` fillers are reached only from the 1a harnesses (`scripts/node_test.py`, `scripts/phase0b/expand.py`) and tests. In `native.py`, `x`, `number`, `chart`, `_direction` and `LAYOUT` are live.
6. **Words that break spec D2** ("a word means the same on every block"): timeline `rail` and `columns` draw differently from what the words meant on cards. Field `note` and part `delta.` also name the same thing.
7. **Should `NODE_ATTR_UNKNOWN` stay an error?** Code draws the block correctly without the attribute, so an invented name pays for a repair. The first paid run had 5 such first-try errors, since aliased.
8. **Only 5 of 28 variants stay real PowerPoint objects.** The user weighs hand-editing heavily; `rows` and `ledger` on tables were kept knowingly.

**Known limits**

9. **Narrow boxes.** All variants break in a 280 px box, and `requires` checks only content, never the box. `reflowNarrow` in fit-grow helps columns of code-drawn items, but a composition cannot switch at that point, because fit-grow runs after expansion. How often real slides get such a box is not measured.
10. **`rows_fit` assumes a full slide body.** Card `rows` beside another component can still overflow.
11. **`grid` spills on 5 to 6 cards with three bullets each.** Left unfixed on purpose: none of the 63 saved `grid` plans with 5+ cards has bullets. Re-count if the planner changes.
12. **Layers over derived blocks.** The LLM cannot know where a block ends after fit-grow. Anchors (Part B §13.2) are not built, and a missed `<Arrow>` id is only a compile warning.
13. **No result is recorded for `<Highlight>` written by a real generator on lists,** which the bullet node still owes.
14. **Route A lacks the attribute filter.** `POM_BLOCKS=tiles` without `POM_NODES` does not report attributes that do nothing.
15. **Visual polish:** a long tag on one `columns` card drops its pill below its peers; a `bento` box needs at least 500 px, stated in the prompt but not enforced.
16. **Still open from the audit:** `docs/syntax-audit-2026-11-04.md` §7 decisions 3, 6, 7, 8, 9 and 10, and whether callout and header stay hand-written.

## A.10 Where the code is

| Path | Holds |
|---|---|
| `src/knowledge/core/block-variants.yaml` | `nodes` (route B), `tile_nodes` (route A), `blocks` |
| `src/knowledge/core/nodes.yaml`, `attributes.yaml` | The native allowlist and attributes |
| `src/compiler/nodes/composed.py` | One interface for all six nodes; missing-node and wrong-kind checks |
| `src/compiler/nodes/compose.py` | Shared attribute reading, `$tone`, the no-effect filter |
| `src/compiler/nodes/spec.py` | YAML loading, `requires` checks, `POM_NODES` |
| `charts.py`, `sequences.py`, `tile_groups.py`, `tables.py`, `bullets.py` | The six expanders |
| `element_refs.py` | Field references and `fill_refs` |
| `tiles.py`, `cards.py` | Route A's tile tags, parts reused by `tile_groups.py` |
| `src/agents/validator.py` | Where expansion runs, before `normalize_xml` |
| `src/node/fit-grow.js` | Type sizing, peer groups, regrid, reflow |

The node tests, free and with no API key:

```bash
pytest tests/unit/test_block_variant_names.py tests/unit/test_tile_groups.py tests/unit/test_table_nodes.py tests/unit/test_bullet_nodes.py tests/unit/test_sequence_nodes.py tests/unit/test_cards.py tests/unit/test_attribute_layer.py tests/unit/test_node_prompts.py -q
```

---

# Part B: design record (2026-10-27 to 2026-11-03)

Kept as written, with section numbers unchanged, apart from notes marked **Now:** where the text would mislead. Part A is the current state.

**Superseded since this was written:** `variant` on an item is read as an alias, not dropped (§2.2). A nested or missing component is now an error through `composed.unplaced`, although `validate.check_skeleton` stays unwired (§12.6, §13.3). Of §13.5, the merge and the unit tests are done; the `NODE_ATTR_UNKNOWN` severity and the anchor decision are not, and the paid run went ahead without them. The undated evidence in §6 and the old variant names in §5, §7 and §11 predate the deletions.

## One composition convention for every derived node (spec draft, 2026-10-27)

Status: **approved by the user, 2026-10-27**: D1–D5, plus the §8 replacement and edits C1–C14 from
`docs/eval/composition-left/README.md` (folded in below). Build per §10; the 8 remaining blocks go one block per
step, behind `POM_NODES` (chart first). Free proof renders: `scripts/composition_convention.py` (KPI / cards) and
`scripts/composition_gallery_left.py` (the other blocks), sheets in `docs/eval/composition-convention/` and
`docs/eval/composition-left/`.
Builds on:
- `docs/derived-nodes-spec-left-blocks.md` §2.1 (naming rules N1–N4: group tag = plan `kind`, item tag = list key,
  part = key without its prefix).
- `docs/eval/composition-test/README.md`: 10 of 12 style variants render identically from attributes, and only
  `divided`, `numerals`, `arrange` and `layout` are compositions.
- The user's definition (2026-10-27):
  - **Composition** = the same plan JSON drawn a different way: which parts appear and where. Code draws it.
  - **Style** = attributes. The generator LLM has complete power over them.

## 0. Summary (the decisions this spec asks you to approve)

| # | Decision | Proposal |
|---|---|---|
| D1 | The composition attribute | **`variant`, on the group tag only, meaning composition only.** It absorbs today's `layout`, `arrange`, `divided` and `numerals`. Nothing else on a tag chooses structure, apart from the measured knobs `cols` / `direction`, which code may overrule. |
| D2 | Value grammar | **One structure word from a shared vocabulary of 8, plus at most one part modifier (`numbered` or `labelled`).** Examples: `variant="rows"`, `variant="rows numbered"`. A word means the same structure on every block (§2). |
| D3 | How style is written | Dot-name attributes on the group, item or part, plus two small additions. **`item.` on the group** styles every item's box. **`$tone`, `$toneSoft`, `$toneText`** are colour tokens that code resolves per item from the plan's tone. Group box attributes stay on the group's own box (user, 2026-10-26). |
| D4 | Today's style variant names | **They leave the tag.** `plain filled toned bar dot bare inverted` (KPI) and `lifted column filled outline toned accent_top inverted` (cards) become **style recipes**: 1–4 attributes each with `item.` / `$tone`, down from 6–34. They stay in `block-variants.yaml` for the prompt's examples and for the hint mapping. Emphasis and tone colours become part of each composition's default look (§3). |
| D5 | Where the theme defaults live | **One place: `block-variants.yaml` (renamed `nodes`), one `look` per composition, written only in palette tokens and `$tone*`.** `palettes.yaml` keeps supplying the token values, and `house-style.yaml` keeps the type ramp. Resolution order: composition look → group attributes → item attributes (§4). |
| D6 | KPI compositions | `grid` (default) · `strip` · `rows` · `banded` · `bento` (rendered, §6) |
| D7 | Card compositions | `grid` (default) · `grid numbered` · `rows` / `rows numbered` · `columns` · `banded` · `bento` · `steps` · `rail` (rendered: `rows numbered`, `columns`, `banded`, `bento`, §6). **Now:** `rail` removed (A.5) |

## 1. Why one convention

- **One pattern to learn.** Today a generator meets `variant` (a look on KPI and cards), `layout` (group
  arrangement), `arrange` (part order inside an item) and `cols`. On top of that come the left-blocks draft's
  per-block names (`labelled`, `zebra`, `cards`, `step_cards`, `tiles`, `tinted`…). Every block names a
  different thing with the same attribute. In the combined check the LLM wrote 0 variants on 13 `<KpiGrid>` and
  1 on 32 `<CardGrid>`. A choice the generator has to relearn on every block goes unused, or it gets invented.
- **The renders agree with the user.** In the composition test, two of today's style variants of one block
  looked like the same slide, while two compositions looked like two slides (Q2 verdict). The proof sheets here
  show the same for KPI tiles and cards (§6).
- **Style is cheap once it has two helpers.** The test's cost of 6–34 attributes per group came from two
  gaps. No attribute reached every item (group box ≠ items), and no colour token followed the plan's tone.
  `item.` and `$tone` close both gaps (D3). The LLM then gets complete power over style at a few attributes per
  group.

## 2. The convention

### 2.1 Tags and parts (unchanged from the left-blocks spec)

N1–N4 of `derived-nodes-spec-left-blocks.md` §2.1 hold: `<KpiRow ref>` / `<Kpi ref>`, `<CardGrid ref>` /
`<Card ref>`, `<Timeline ref>` / `<TimelineItem ref>`… Parts carry the plan key's name (`label.`, `value.`,
`delta.`, `title.`, `tag.`, `body.`, `bullets.`, `key_phrase.`, `icon.`). Look parts that hold no plan content
are named for what they draw. This spec fixes their list, so that one name means one thing on every block:

| Look part | Node | Drawn by | Appears in |
|---|---|---|---|
| `number.` | Text | code's 01 02 03 | the `numbered` modifier; `steps` (undated) |
| `marker.` | Shape | a dot / square before a label | any composition, when `marker.shapeType` is set (style) |
| `band.` | HStack box | the solid head of an item | `banded`, `columns` (the pill) |
| `divider.` | the hairline between items | — | `strip`, `rows` |
| `connector.` | Shape / line | arrows, rail line | `steps`, `rail` |
| `item.` | each item's own box | — | every composition (D3) |

### 2.2 `variant` = composition only (D1)

- **Only on the group tag.** An item tag (`<Card ref="levers.3" w="34%"/>` placed apart) is drawn in its group's
  item form. A `variant` on an item is dropped with `NODE_ATTR_DROPPED`. Today's item variants were looks
  (`inverted`, `toned`): they become attributes or the emphasis default (§3).
- **No `variant`** → code picks a default from the plan: `card_layout` (`steps` → `steps`), the count (a KPI
  row of 6+ → `grid` in two tiers, as today), and the hint (`look_from_hint`, extended to name compositions:
  "hero" / "spotlight" → `bento`, "ruled list" → `rows`, "strip" → `strip`), else `grid`. It is logged with
  `NODE_LOOK_FROM_HINT`, as today.
- **A composition the content cannot hold** (`requires` fails) → the block's `fallback`, with
  `NODE_VARIANT_UNMET`. The test is the same as today's, per composition (§5).
- **`cols` / `direction`** stay as measured knobs. They do not choose structure, and code overrules them on
  the break-map limits (`NODE_DIRECTION_UNMET`, `regridTiles`).
- **Part order inside an item is the composition's, never the LLM's.** Today's `arrange` values map to
  compositions (§7). fit-grow's `stackTileIcons` already moves icons above sparse labels on its own.

### 2.3 The value grammar (D2)

```
variant = WORD [ MODIFIER ]
WORD     = grid | strip | rows | columns | banded | bento | steps | rail | native
MODIFIER = numbered | labelled
```

**Shared structure words.** Each word has one meaning on every block:

| Word | Structure (which parts appear, and where) | Evidence |
|---|---|---|
| `grid` | equal separate boxes in rows × columns (code picks the columns); each item's parts stacked | today's KPI / card default |
| `strip` | one shared box, the items side by side in **one** row, a divider between them; never regridded | KPI `divided` (2026-10-22 review of 25 example decks) |
| `rows` | one item per full-width row, its parts left to right (lead · title / label · body · value or detail at the right), a divider between rows | KPI `inline` / `side`, example 7 "ruled list"; Genspark "3 items → stacked rows", CARD-F; Perceptis `numbered_rows`; the LLM's 62 hand-built icon rows |
| `columns` | one column per item: a `band.` head on top, then each sub-item (bullet / sub-row) in its own box | Perceptis `columns` (composition test) |
| `banded` | equal boxes; each box has a solid `band.` head (icon + title / label) over the rest | Perceptis `title_bar`, `icon_header` |
| `bento` | the plan's emphasis item as one large block (value or title first), the others grouped beside it | Genspark KPI-E / KPI-F, CARD-C featured card; tile examples 3 and 7; `bento` in the composition test |
| `steps` | items in one row joined by `connector.` arrows; the destination item is the emphasis | cards `steps`; Genspark PROCESS-B / -D |
| `rail` | items along a `connector.` line with a dot per item (down the slide by default) | cards `rail`; Genspark STEPS-A, TIMELINE-B |
| `native` | the block's own POM node, filled by code (`Table`, `Chart`, `Ul`, `Timeline`, `ProcessArrow`, `Flow`) | left-blocks spec: the D10 node contract |

**Modifiers** (parts code adds that the plan does not name; each also means the same everywhere):

| Modifier | Adds | Rule |
|---|---|---|
| `numbered` | `number.`: 01 02 03 leading each item (above it in `grid`, at the left in `rows`, over it in `steps`) | not when the items carry dates (today's dated-steps rule) **or their own ordinal** ("Phase 1: …", "01. …"; C10) |
| `labelled` | the item's value written on its mark (chart bars, rail dots) | only where an item has one value (left-blocks spec, chart `labelled`) |

**Block-specific words.** None are needed for KPI tiles, cards or the 8 other blocks (C5: a callout's
quotation is a content rule of `native`, not a word). A later block that needs a structure no word covers
adds one word to this table, with its meaning. It never reuses a word with a new meaning.
- **`ledger`** (table, user 2026-11-01): one solid header band, an icon over each column name (the tag's
  `icons`), over joined rows tinted by turns. The table also took the shared `grid` / `grid numbered`. **Now:**
  both removed, along with `labels` (A.5).

**Head / detail split (C10).** Where a composition shows a string item as a head and a detail, code splits it
at the first " — " and only then at ": ", so "Phase 1: Foundation — detail" gives the head "Phase 1:
Foundation". Every word is kept (`NODE_TEXT_SPLIT`, info).

### 2.4 How style is written (D3)

| Where | Reaches | Example |
|---|---|---|
| group box attribute | **the group's own box only** (user, 2026-10-26) | `<KpiRow backgroundColor="$surfaceAlt" padding="22">` |
| `item.<box attribute>` on the group | **new:** every item's box | `item.borderLeft.color="$tone" item.borderLeft.width="6"` |
| `<part>.<attribute>` on the group | that part in every item (as today's `shared: parts`) | `value.color="$toneText"`, `band.backgroundColor="$panelDark"` |
| box attribute on an item tag | that item's box | `<Card ref="levers.2" backgroundColor="$warningSoft"/>` |
| `<part>.<attribute>` on an item tag | that part of that item | `<Kpi ref="kpis.0" value.glow.size="6"/>` |

- **`$tone`, `$toneSoft`, `$toneText`** (new, code-resolved): the item's plan tone as a role token. good →
  `$positive*`, bad → `$negative*`, watch → `$warning*`, none → `$accent*`. An item's own `color="$negative"`
  sets its tone. They are accepted wherever a `$token` is accepted, and code swaps them per item before
  `normalize_xml`. So `LITERAL_COLOR` and the palette rules are unchanged. This is what the test could not
  write (`${role}`). With it, `dot` drops from 34 attributes to 3, and card `toned` from 32 to 3.
- **`item.` on `native` (C1).** `item.` reaches every item of a code-drawn composition. On a `native` node no
  item tag takes a box attribute (R2), so `item.` is limited to the colours each item tag takes: table
  `item.backgroundColor`, which code writes onto every `Td`, and diagram items' `item.color` / `item.textColor`.
  Any other `item.` attribute on `native` → `NODE_ATTR_DROPPED`. So do attributes that POM accepts and
  silently ignores (`Tr`, `ChartSeries`, `ChartDataPoint`, `TreeItem` apart from its colours): they are
  dropped and logged, never passed on (F12). The exception is a row's colour, which code writes onto that
  row's cells.
- **Dropped** (`NODE_ATTR_DROPPED`), unchanged: font sizes, font family, positions, `id`, typed text. Corner
  radius stays code's for KPI tiles (square) and cards (8 px).
- **Code still owns:** every word (verbatim, in plan order), type sizes (one per part per group, fit-grow),
  word fit, numbers / arrows / rails, readable ink on dark fills (`ON_FILL`), and **which item is the emphasis**
  (the plan's). The LLM may restyle the emphasis item but cannot move the emphasis. At most one dark item per
  block stays a check (`DARK_PANEL_SOFTENED`). It is not an attribute ban.
- **Table highlights (user, 2026-11-02).** A table colours by meaning with `<Highlight>` children inside
  `<Table ref>`, written by the generator (it reads the cells in its slide line, never types them); the planner
  only says in its `design_hint` what matters. Targets by name: `row` (its first cell), `column`, `cell="<row> /
  <column>"`, `phrase` (words inside a cell). Tones good / bad / watch. `fill` = the cell's background
  (`$<role>Soft`), `color` = its text (`$<role>Text`): separate, so a tinted row can carry a differently coloured
  phrase. Phrases are `<Span color>`, never POM's `<Mark>`. Value rules colour the text, code compares the numbers:
  `above` / `below` a number or another column (`else` for the rest), `max` / `min` (highest / lowest). A name or
  phrase not in the table: `NODE_HIGHLIGHT_UNKNOWN` (error, the LLM fixes it); more than 6: `NODE_HIGHLIGHT_LIMIT`
  (a warning, all drawn: no cap, user 2026-11-02); cells without numbers in one unit: `NODE_HIGHLIGHT_RULE` (left uncoloured). With highlights there
  is no emphasis from the hint; a bare tag keeps it.

## 3. Today's style variants: where they go (D4)

The test shows three costs of losing the names. Each one gets a home:

| What the name carried | New home |
|---|---|
| the look (fill, borders, part colours) | a **style recipe**: a few attributes, listed in `block-variants.yaml` `styles:` (as `treatments` are today) and shown in the prompt as examples. The LLM writes the attributes, not the name |
| tone-driven colours (`with_tone`, `with_color`) | `$tone*` in the composition's **default look** (§4). With no attributes, a bad tile is tinted and a good number is green, as today. A recipe or an LLM attribute that names `$tone` follows the plan item by item |
| emphasis rules (`inverted` only on the emphasis item, card focus dark, `size="hero"`) | the composition's **`emphasis` look**: code applies it to the plan's emphasis item (dark block in `bento`, dark band in `banded` / `columns`, the dark focus card in `grid`) |
| the default look (`plain`, `lifted`) | each composition's `look`. Because the default is a layer the LLM writes over, not a variant to undo, the resets of the test (`border.width="0"`…) are no longer needed for the common case |

Recipes after the change (written against the `grid` default; `{t}` = `$tone`):

| Today | Recipe | Attributes (test → now) |
|---|---|---|
| KPI `filled` | `item.backgroundColor="$toneSoft" value.color="$toneText"` | 8 → 2 |
| KPI `toned` | `item.backgroundColor="$toneSoft" item.border.color="$tone" value.color="$toneText"` | 9 → 3 |
| KPI `bar` | `item.borderLeft.color="$tone" item.borderLeft.width="6"` | 18 → 2 |
| KPI `dot` | `marker.shapeType="ellipse" marker.fill.color="$tone" label.color="$toneText"` | 34 → 3 |
| KPI `bare` | `item.backgroundColor="$surface" item.border.width="0"` (fit-grow: see §9 risk 2) | 17 → 2 |
| KPI `inverted` | the emphasis look (no attribute) | 6 → 0 |
| KPI `divided` | **composition** `strip` | — |
| card `column` | `item.backgroundColor="$surface" item.shadow.opacity="0" item.borderLeft.color="$tone" item.borderLeft.width="3"` | 28 → 4 |
| card `filled` | `item.backgroundColor="$surfaceAlt" item.shadow.opacity="0"` | 20 → 2 |
| card `outline` | `item.shadow.opacity="0"` | 17 → 1 |
| card `toned` | `item.backgroundColor="$toneSoft" item.borderLeft.color="$tone" title.color="$toneText"` | 32 → 3 |
| card `accent_top` | `item.borderTop.color="$tone" item.borderTop.width="4"` | 24 → 2 |
| card `numerals` | **composition** `grid numbered` | — |
| card `inverted` | the emphasis look | — |

## 4. Complementing the theme: one approach (D5)

**Every composition has one default look in `block-variants.yaml`, written only in palette tokens and
`$tone*`. Palettes give the tokens their values. The LLM's attributes layer on top.**

```yaml
nodes:                         # today's tile_nodes, renamed (left-blocks spec §3)
  kpi:
    compositions:              # first = default
      grid:
        look:     {item.backgroundColor: $surfaceAlt, item.border.color: $border, item.border.width: 1,
                   item.padding: 16, label.color: $textMuted, value.color: $textMain, delta.color: $toneText}
        tone:     {bad: {item.backgroundColor: $toneSoft, item.border.color: $tone, value.color: $toneText},
                   watch: same as bad, good: {value.color: $toneText}}
        emphasis: {item.backgroundColor: $panelDark, label.color: $onPanelDark, value.color: $onPanelDark, size: hero}
      strip:   {requires: [count_le_5], fallback: grid, look: {...}, emphasis: {...}}
      ...
    styles:                    # recipes (§3): prompt examples and the hint mapping, never a tag value
      bar: 'item.borderLeft.color="$tone" item.borderLeft.width="6"'
```

- **Resolution order (later wins):** composition `look` → `tone` (per the item's plan tone) → `emphasis` (the
  plan's emphasis item) → group attributes → item attributes. This is today's order with "house look + style
  variant" folded into one composition layer, so the expander loses a layer instead of gaining one.
- **Why not `palettes.yaml` / the Theme:** a Theme is hex only, with no fonts or alpha
  (`pom-chartcolors-tokens` note). It holds colours, not structure. And the same composition must look right on
  every one of the ~20 palettes. Tokens give that: the proof draws **one XML** per composition on
  corporate-slate and graphite-dark, and the theme alone restyles it (§6).
- **Why not `house-style.yaml`:** it is prompt prose for the LLM's own drawing, and no expander reads it as
  data. The type ramp and spacing scale stay there, and code keeps reading sizes from its own constants as today.
- **Per-template house looks** (gj-h1 and others) later override a composition's `look` by palette name in the
  same file (`look_by_palette:`). Not proposed now. It is noted so the place is fixed.

## 5. KPI and card compositions from the same plan JSON

Fields: `kpi_row` = `kpi_labels / kpi_values / kpi_deltas / kpi_tones / kpi_icons`, emphasis from
`design_hint`. `card_grid` = `cards[].title / tag / body / bullets / icon / tone / key_phrase`,
`focus_card`, `card_layout`.

### 5.1 KPI (`<KpiRow ref variant>`)

| Composition | Parts and where | requires → fallback | Default look (theme) | Emphasis item |
|---|---|---|---|---|
| `grid` (default) | separate tiles; icon + label, value, delta stacked | — | today's `plain` with tones | dark tile, `size=hero` |
| `strip` | one shared box, tiles side by side, dividers, one row | ≤ 5 items → `grid` | `$surfaceAlt` box, `$border` dividers, value in `$toneText` | value hero size only (no dark item inside a strip) |
| `rows` | icon badge (`$toneSoft`) · label over delta · value right-aligned; dividers | — | no fill, `$border` dividers | its row's value hero size |
| `banded` | a `band.` head (icon + label) in `$tone` over value + delta | ≤ 5 items → `grid` | band `$tone` / `$onAccent`, body `$surfaceAlt` | band `$panelDark` |
| `bento` | the emphasis tile large and value first, the rest as `rows` beside it | an emphasis item and ≥ 3 items → `grid` | big block `$panelDark`; small tiles as `grid` | is the big block |

### 5.2 Cards (`<CardGrid ref variant>`)

| Composition | Parts and where | requires → fallback | Default look | Emphasis (focus card) |
|---|---|---|---|---|
| `grid` (default for `card_layout: grid`) | today's card: icon, tag, title, body (+ key phrase span), bullets | — | today's `lifted` with tones | dark card |
| `grid numbered` | + `number.` above the title | no dated tags → `grid` | `$surfaceAlt`, number `$textMuted` | dark card |
| `rows` / `rows numbered` | (number) · tag over title · body · bullets, one card per row, dividers | ≤ 6 cards → `grid` | no fill, `$border` dividers, number / tag `$toneText` | its title in `$toneText`, bold number |
| `columns` | a `band.` pill (icon + title), body, each bullet in its own box | bullets on every card, ≤ 5 cards → `grid` | pill `$tone` / `$onAccent`, boxes `$surfaceAlt` | pill `$panelDark` |
| `banded` | a `band.` (icon, title, tag at right) over body + bullets | ≤ 6 cards → `grid` | band `$tone`, body `$surfaceAlt` | band `$panelDark` |
| `bento` | the focus card as a large block, the others 2 + 1 beside it | `focus_card` set, 3–5 cards → `grid` | big `$panelDark`; small cards toned | is the big block |
| `steps` (default for `card_layout: steps`) | today's steps (arrows; numbered unless dated) | as today | `lifted` | the destination |
| `rail` | **Now:** removed, the name draws `steps` (A.5) | | | |

## 6. Proof (free): the sheets

`python -m scripts.composition_convention` renders one sample plan per block, `kpis` (4 KPIs, tones good /
good / bad / watch, icons, hint "highlight ARR as the hero") and `levers` (4 cards with tag, body, bullets,
icon, tones, key phrases, focus card 0). The plans are validated against today's typed schema. Each block gets:
- **Rows 1–2:** today's real `<KpiGrid>` / `<CardGrid>` code (`POM_BLOCKS=tiles`) in three style variants, on
  corporate-slate and graphite-dark.
- **The rows below:** one proposed composition per row, written as the XML its node would expand to, with
  only its default look (tokens + `$tone` roles resolved by hand, no LLM attributes). The **same XML** is drawn
  on both palettes.

KPI parts are element refs (`<Text ref="kpis.0.value"/>`), so code writes the text and the `kpiv-` peer ids.
Card boxes carry the cards' `card-<cid>-<i>` ids, so fit-grow grows every card of a group to one size.

- [kpi.png](eval/composition-convention/kpi.png): today `plain` / `filled` / `bar` | `strip`, `rows`, `banded`, `bento`
- [card.png](eval/composition-convention/card.png): today `lifted` / `filled` / `accent_top` | `rows numbered`, `columns`, `banded`, `bento`

**What the sheets show**
- **Today's three styles are one slide.** The KPI `plain`, `filled` and `bar` are the same 2 × 2 of tiles with
  a different fill or edge, and the card styles are the same 2 × 2 of cards. Each proposed composition is a
  different slide at a glance: a ruled strip, a ruled list with right-hand numbers, banded columns, a hero
  block beside a list.
- **The theme carries the colours.** Each composition drawn on graphite-dark reads as the same design in
  the dark palette, with no attribute changed. This supports D5: default looks in tokens are enough to
  complement any palette.
- **Peers share one size.** In `rows` all four values grew to 76 px and all labels to 23 px (`fitted.xml`). The
  composition test's uneven `numbered_rows` came from missing peer ids, not from the composition.

**Render findings to carry into the build** (none blocks the convention):
Each was traced in fit-grow's own layout (`layout` / `natural` / `fill`, measured on the slides' `in.xml`):

1. **`strip` icons sit unevenly: a per-tile decision.** `stackTileIcons` (`src/node/fit-grow.js`) moves a
   tile's icon above its label when *that tile* is below `LOW_FILL` (0.70) after growth. It decides tile by
   tile, while the values next to it are grown as one group (`refGroups`). ARR (short label, one line) stayed
   just above 0.70, and the three tiles whose labels wrapped fell below it. **Fix (small, fit-grow):** decide once
   per ref group. If any tile of the group qualifies, move the icon on every tile of the group, so that peers
   match. This holds for every composition, not just `strip`. Under the convention, a composition node could
   also fix the icon position itself (`banded` / `rows` / `bento` already put it in the band, badge or lead).
2. **Tall bands stay empty: the width binds the numbers, and nothing can use the height.** In `strip` the
   values grew 28 → 65 px and stopped at the tile width (4 across, ~270 px each). The box's fill went only
   20% → 30% (`banded`: 15% → 26%). A one-row composition cannot use the height by definition, and neither can
   a `regridTiles` split, because `strip` never regrids. **Proposal (a fit rule in code, not an LLM rule):**
   one-row compositions (`strip`, `banded` with ≤ 5 items) take content height and do not `grow`, so that the
   slide's other bands take the spare height. When the block is the slide's only growing band and its fill after
   growth stays under 50%, code draws the fallback instead (`grid`, which can regrid to 2 × 2) and logs
   `NODE_VARIANT_UNMET`. The same check is useful for any composition whose `requires` depends on space.
3. **"Card text does not grow" was a misreading: those cards are full by height.** fit-grow does run
   (`compile-result.json` `fitGrow: []`, nothing changed). By its measure today's `lifted` 2 × 2 cards are
   **87–92% full**. Card 3 has an inner height of 208 px: tag 18 + title 26 + body 22 + three bullets 97 +
   gaps 24 = 188 px. The proposed `banded` cards measure 88%, and `rows numbered` 96–97%. The cards look small
   on the sheet because each line uses ~40% of a 494 px wide card: the stacked parts fill the **height**, and
   the **width** stays spare. fit-grow grows type only into spare height (`LOW_FILL` on height), so it is right
   not to grow them. A bigger size would overflow the card.
   - **What does grow the type is a composition that spends the width.** `columns` (each bullet in its own
     box) grew to 28 / 39 px. The `bento` big block grew 30 → 44 px. The small `bento` cards sit at 0.71, just
     above the 0.70 threshold, so they stayed.
   - **Consequence for the convention:** for cards with a body *and* bullets, `grid` is the composition that
     keeps type smallest. A default chosen from the content (body + ≥ 3 bullets per card, ≤ 4 cards →
     `columns`, else `grid`) would follow the user's rule "grow the type, never shrink the card" better than
     a fixed `grid` default. This is a code choice from the plan's shape, checked on the saved card slides
     (free replay) before it becomes a default.
   - **My proof bug, now fixed:** in `rows numbered` the "01" Text had no width, so its column took 248 px of
     the row. The number now sits in a 72 px column (`scripts/composition_convention.py`), and the card sheet
     is re-rendered.
4. On graphite-dark the `banded` band's `$onAccent` ink sits on light tone fills. It reads, but the contrast
   check should run on `band.` like any dark fill (`ON_FILL` table: add `$positive` / `$negative` / `$warning`
   → `$onAccent`, after a contrast check per palette).

## 7. Migration

| Today | After | How |
|---|---|---|
| `<KpiGrid>` | `<KpiRow>` | alias for one release, `NODE_TAG_ALIAS` (left-blocks §3) |
| `note.` | `delta.` | alias |
| KPI `variant="plain|filled|toned|bar|dot|bare"` | no variant (`grid`) + the recipe's attributes | the expander reads an old name as its recipe, `NODE_ATTR_ALIAS` (info), for one release |
| KPI `variant="inverted"` on an item | dropped: the emphasis look already draws it | info |
| KPI `variant="divided"` | `variant="strip"` (or `rows` with `arrange="inline"`) | alias |
| KPI `arrange="label-first|icon-top"` | `grid` (the icon placement is fit-grow's) | alias |
| KPI `arrange="value-first"` | `bento` for the emphasis item; otherwise `grid` | alias |
| KPI `arrange="side|inline"` | `rows` | alias |
| KPI `layout="row|grid|column"` | `grid` (+ `cols`); `column` → `rows` | alias |
| card `variant="lifted|column|filled|outline|toned|accent_top"` | `grid` + recipe | alias as above |
| card `variant="numerals"` | `grid numbered` | alias |
| card `layout="grid|steps|rail"` | `variant="grid|steps|rail"` | alias |
| card `arrange="side"` | `rows` | alias |
| `look_from_hint` cues → variant names | cues → a composition (hero / ruled / strip) **or** a recipe's attributes | rename in `plan_checks` |

Galleries:
- `scripts/tile_gallery.py` and `card_gallery.py` loop over compositions (rows) × one style row of recipes,
  instead of `variants × arranges`.
- `scripts/composition_convention.py` (this proof) becomes the composition gallery once the nodes exist: its
  hand-written bodies turn into bare `<KpiRow ref variant>` / `<CardGrid ref variant>` tags, and the sheets
  must match.
- `kpi_gallery.py`: no change. The blind-mark sheets of the passed card gate stay valid, because `grid` +
  `lifted` is today's default pixel for pixel.

Saved slides and replays keep working through the aliases. Remove them after one paid run shows 0
`NODE_*_ALIAS` from the generator (left-blocks spec, same rule).

### Plan fields each composition needs

| Composition | Needs | In today's plan? |
|---|---|---|
| KPI `grid`, `strip`, `rows`, `banded` | labels, values, (deltas, tones, icons optional) | yes |
| KPI `bento` | an emphasis item | partly: from `design_hint` only. **New field recommended: `focus_kpi`** (index, mirroring `focus_card`; `settle_card_fields`-style check). Until then the hint, and `bento` falls back to `grid` when the hint names none |
| card `grid`, `grid numbered`, `rows`, `banded`, `steps`, `rail` | title (+ optional tag, body, bullets, icon, tone, key_phrase) | yes |
| card `columns` | bullets on **every** card | yes (field exists; `requires` checks it) |
| card `bento` | `focus_card` | yes |
| card true bento (blocks spanning 2 cells, Perceptis) | a span per card | **no, new field; not proposed** (composition test Q2 row 7) |
| table `banded` with icons per column | an icon per column | **no, new field** (`column_icons`), or the LLM's `icon` per `<TableColumn>` as for bullets today |

## 8. The other blocks on the same convention (approved 2026-10-27)

Drawn and rendered in `docs/eval/composition-left/` (R1; the hand-written XML each node expands to is in
`scripts/composition_gallery_left.py`). Today's style names become recipes or the default / emphasis look.

| Block (tag) | Compositions (`variant`, default first) | requires → fallback | Becomes a style recipe |
|---|---|---|---|
| table (`<Table>`) | **Now:** `native` · `rows` · `ledger` (A.5). Approved then: `native` · `rows` / `rows numbered` · `columns` · `banded` | `ledger`: ≤ 6 columns → `native` | `plain` (default look), `zebra` (`stripe.`), `dark_header` (`header.` / `label.`); `highlight_row` = emphasis look; `minimal` dropped (C2) |
| chart (`<Chart>`) | `native` · `native labelled` · `rows` | `labelled` / `rows`: one series, ≤ 8 points (bar for `labelled`) → `native` | `focus_label` = emphasis look of `native labelled`; `horizontal` → `direction` |
| bullet_list (`<Ul>`, user 2026-11-04: `grid` / `banded` deleted as the card grid's looks, `docs/eval/bullet-node/`) | `native` · `native numbered` · `rows` (optional `icons`, ≤ 6 points) / `rows numbered` | numbered: no own numbers → `native` / `rows`; anything that cannot be composed → `native`, POM's real list | `lead` = `native` default; `icon` = `rows` + `icons`; `columns` = fit-grow's automatic split (4+ short points) |
| timeline (`<Timeline>`) | `native` · `rail` · `columns` · `rows` · `banded` | `native`: every label ≤ 24 characters with no detail → else `rail` (dots on a line, date / head / detail alternating above and below); `rail`: ≤ 7 points → else `columns` (a box per point under the line). Default chosen from content (2026-11-02) | `vertical` → `direction`; `cards` → `columns`; `alternating` → `rail` |
| process_arrow (`<ProcessArrow>`) | **no node (user, 2026-11-02)** | — | the LLM draws it as before (`chevrons` / `numbered` / `alternating` / `step_cards`) |
| flow (`<Flow>`) | **no node (user, 2026-11-02)** | — | the LLM draws it as before (`boxes` / `numbered` / `step_cards`) |
| callout (`<Narrative>`) | `native` (a quotation draws its `mark.` and attribution by content rule, C5) | — | `tinted` (default look), `rule`, `dark`, `plain` |
| header (`<Title>`) | `native` | — | `standard` (default), `inverted`; `ruled` needs a `rule.` look part (C13), not built |
| matrix (`<Matrix>`) | `native` · `grid` | `grid`: `quadrants` present → `native` | — |

Pyramid and tree stay `native` (C9).

**Notes carried from the check:**
- **Table look parts (C2, F11).** Table `native` gets the look parts `header.` (the header row), `label.` (the
  first column) and `stripe.` (alternate rows), which code writes onto the `Td`s. `cellBorder` is uniform and
  `Td` takes no border, so `minimal` cannot be written.
- **Chart `native labelled` (C6)** needs two code fixes: the label ink from `$chartInk`, and a number format
  derived from the plan's unit when the values share one ("0.29x" → `0.00"x"`). Chart text takes no attribute,
  so style power on charts lives in `rows`, where every part is a Text / Shape.
- **Timeline (C4):** `banded` uses the date as the band, coloured done / now / ahead from the "now" item (hint
  only). **2026-11-02 (user):** process_arrow's alternating `rail` moved to the timeline as `rail`, the default for
  labels with detail (the timeline's problem was long text: POM's 120 px titles); the old timeline `rail` (a line
  with a box per point) is now `columns`, used past 7 points. A vertical timeline that is not native draws `rows`.
  **Fields follow POM's `<TimelineItem date title description>` (user, 2026-11-02):** the parts are `date.`
  `title.` `description.` (`label.` read as an alias of `title.`). With `POM_NODES=timeline` the planner gets the
  `description` field back (label = the milestone's name, ≤ 3 words; description ≤ 20 words, capacity.yaml) and
  the label-room check leaves timelines alone; with the node off its prompt is unchanged (short labels only, the
  user's overflow fix for POM's own timeline). Splitting a label at " — " / ": " / an unspaced dash between
  letters stays as the fallback for plans without a description.
- **Process arrow and flow dropped (user, 2026-11-02).** POM's chevrons (150 × 80) and flow nodes (120 × 60) hold
  about two words at a fixed size and only shrink (`process-arrow.yaml` / `flow.yaml` facts), and the code-drawn
  `steps` were card grids under another name (`docs/eval/sequence-nodes/native-vs-derived-*.png`). Their nodes are
  gone; the planner still plans them and the LLM writes POM's `<ProcessArrow>` / `<Flow>` as before.
- **Inner boxes (C11).** A composition node gives its inner boxes one peer group, `card-<cid>x-<n>`, as well as
  the item ids `card-<cid>-<i>`, so that fit-grow grows peers to one size when an item's children stretch.
- **Value refs (C12).** A code-drawn `rows` writes its value / label as element refs (role ids), so that
  fit-grow grows them as values, not as body text held to its caps.
- **Knowledge (C14).** List per item tag what it takes (from `r2-attributes.json`) in the knowledge files.

## 9. Risks and open questions

| # | Question / risk | Draft answer |
|---|---|---|
| Q1 | Approve D1–D5 as one convention (one `variant` = composition, the shared words, `item.` + `$tone`, recipes, defaults in `block-variants.yaml`)? | yes |
| Q2 | `bare` as attributes leaves fit-grow treating tiles as boxes (test note 1) | a recipe value of `item.border.width="0"` with no fill counts as "no box" in `hasBoxStyle`. A small fit-grow change, checked on the KPI gallery |
| Q3 | Should the LLM still be able to make a non-emphasis item dark? | yes (complete power over style). `DARK_PANEL_SOFTENED` stays a report and does not undo it |
| Q4 | New planner field `focus_kpi`? | build only if the free replay shows `bento` falling back on hints that do name a KPI (paid planner check, ask first) |
| Q5 | The KPI gate failed on today's tiles. Do compositions change that? | unknown until marked. Next free step: a blind sheet of saved KPI slides, LLM vs `grid` vs the composition the hint asks for (no cost) |
| Q6 | Prompt size | the shared vocabulary is ~120 cached tokens once (§2.3 table as one line per word), and per component one line names the compositions its content allows (~20 tokens). Recipes replace today's per-variant prompts (net ≈ 0) |

## 10. Build order (after approval; free until the last step)

1. `block-variants.yaml`: `compositions:` + `styles:` for `kpi` and `card`, the `$tone*` resolver, `item.` in
   `_read`, and aliases (§7). Unit tests: every alias, every `requires` / fallback, `$tone` per tone.
2. Expanders: KPI `strip` reuses `build_group` (divided), `rows` reuses `inline`, `bento` reuses the item
   placed apart + `size=hero`. New: the `band.` part (banded / columns) and card `rows` / `columns` / `bento`.
   Inner boxes carry the peer ids `card-<cid>x-<n>` (C11), and code-drawn `rows` write value refs (C12).

The 8 other blocks (§8) follow the same steps, one block per step behind `POM_NODES=<kind>` (left-blocks spec
§2.5, §13): chart, then timeline (+ process_arrow + flow, dropped 2026-11-02), then table, then bullet_list. Callout comes later, and
header is not built now. Each block stops at its gate for the user's marks.
3. Composition gallery = this proof with bare tags. It must match these sheets.
4. Free replay on the saved KPI / card slides: the bare tag with the hint's composition, scorecard + blind sheet
   (your marks ≥ 0.5).
5. Paid check only with your OK: same-plan generator run on the saved plans (≈ $0.5, ceiling $1).

## 11. Left to find or define (2026-10-27)

Everything this spec has not settled, in one list. **find** = needs evidence (a render, a census or a replay).
**define** = needs a decision or a written rule. **build** = understood, but waits for approval.

### 11.1 Status of today's names (from the user's status board, 2026-10-27)

| Block | Built (style → recipe) | Built (composition → word) | Left to build | Dropped |
|---|---|---|---|---|
| KPI tiles | `plain` `filled` `toned` `bar` `dot` `inverted` `bare`; `hero` → `size="hero"` | `divided` → `strip`; `row` / `grid` / `column` → `grid` (+ `cols`) / `rows`; `label-first` / `icon-top` → `grid`; `value-first` → `bento`; `side` / `inline` → `rows` | **hero note pill** (the delta as a pill under a hero value, Genspark KPI-E). Decide: a part of `bento`'s emphasis look (style), or a part `delta.` drawn as a pill (a recipe: `delta.backgroundColor` needs a box around the Text, which a Text part cannot carry, so this is **find**: can POM draw a pill from Text attributes alone, or does it need a `pill.` look part?) | — |
| Cards | `lifted` (default) `column` `outline` `filled` `toned` `accent_top` `inverted` | `grid` `steps` `rail`; `numerals` → `grid numbered`; `stack` → `grid`; `side` → `rows` | **featured left column** = `bento` (§5.2; rendered, not built). **matrix** (deferred): a card_grid with `columns` / `rows` axes. **find**: is a card matrix `grid` with axis labels (a new word `matrix`), or slide layout? | `columns` and `title-band` as old card layouts. Note: the **word** `columns` and the composition `banded` (= title band) come back here as compositions with new meanings (§2.3). Confirm this is wanted, since the user once dropped them |
| The other 8 blocks | — | §8 (approved 2026-10-27): every name has a home except table `minimal` (dropped) | each block's node, in the §10 order | table `minimal` |

### 11.2 Define (decisions still open)

| # | What | Why it is open |
|---|---|---|
| F1 | D1–D5 approval (§9 Q1) | the whole convention waits on it |
| F2 | Whether `$tone*` tokens and `item.` are accepted by the normalizer as written, or swapped by the expander before `normalize_xml` | the spec assumes the expander swaps them. `LITERAL_COLOR` / the token check must not reject `$tone` first |
| F3 | The fit rule for one-row compositions (§6 finding 2): no `grow`, and the fallback when they are the only band, under 50% full | a threshold to agree on; checked on the KPI gallery |
| F4 | The default composition chosen from the plan's shape (§6 finding 3: body + ≥ 3 bullets per card → `columns`) | needs the free replay on saved card slides before it becomes a rule (no one-example rules) |
| F5 | `look_from_hint` cues → composition words (hero / spotlight → `bento`, ruled → `rows`, strip → `strip`) | the cue list today maps to style names only (`plan_checks.look_from_hint`) |
| F6 | Per-template looks (`look_by_palette:`) for gj-h1 and others | place fixed (§4), content not written |
| F7 | `focus_kpi` planner field (§9 Q4) | only if the replay shows `bento` falling back |
| F8 | Whether the LLM may still put `variant` on an item placed apart (today `<Kpi ref variant="inverted">`) | the spec drops it. Saved slides use it (tile example 3) |
| F9 | ~~The `quote` word for callouts~~ | **resolved (C5):** no `quote` word; `native` draws a quotation's `mark.` and attribution from the content |
| F10 | `ON_FILL` for `band.` on `$positive` / `$negative` / `$warning` fills (§6 finding 4) | needs a contrast check on every palette |
| F11 | The look parts the native table needs (`header.` `label.` `stripe.`), written onto `Td`s by code | needed for `zebra` / `dark_header` (C2); built with the table step |
| F12 | Attributes POM accepts and silently ignores (`Tr`, `ChartSeries`, `ChartDataPoint`, `TreeItem`) | drop with `NODE_ATTR_DROPPED`, except a row's colour, which code moves onto its cells (§2.4) |
| F13 | Defaults chosen from the content for timeline / process (with F4) | one rule per block with a measured limit (break-map label room); checked by free replay before it becomes the default |

### 11.3 Find (evidence still missing)

| # | What | How (free unless marked) |
|---|---|---|
| R1 | **Done (2026-10-27, `docs/eval/composition-left/`).** Compositions for the 8 remaining blocks: which of the shared words each block's plan JSON can fill, drawn and rendered from today's `slide_component_planner` output, beside today's style names | a composition gallery like `scripts/composition_convention.py`, one sample plan per kind from saved runs (`output/**/slides.json`). **Started as its own session, 2026-10-27** |
| R2 | **Done (`docs/eval/composition-left/r2-attributes.md`).** Which style attributes POM accepts on each native node, because style can only be "complete power" where the syntax allows it. Known limits: `<Td>` holds no `Icon` / HStack; borders are rejected on `Td` / `Li` / `FlowNode` / `TimelineItem` / `ProcessArrowStep` / `PyramidLevel` / `MatrixItem` (`ITEM_BORDER_REMOVED`, POM 10.3.0); `Chart` text is black on dark palettes (`chartSurface`); no data labels in POM charts | compile a probe slide per native node with every box / part attribute (`attributes.yaml`, `llm.md`); record accept / reject / ignored. It decides where a composition must be drawn by code (boxes) instead of the native node |
| R3 | **Done:** the kinds with no item list are `title`, `narrative`, `caption` and `tree`, and `layer` is free-form (`pyramid` and `matrix` have lists; C9). Was: which plan kinds have no item list to compose, and whether a composition word applies to them at all | from `planner_schema_typed.py` + R1 |
| R4 | **Done (README R4).** The plan fields each composition of the 8 blocks needs, marked "new planner field" where missing (as §7 does for KPI / cards): known gaps are per-column / per-row icons (table), a table title, a span per card, a narrative icon, timeline `description` (in the schema, filled 0 of 28 times) | R1 + the left-blocks census |
| R5 | The per-group icon fix (§6 finding 1) on the KPI gallery | **build** after approval (fit-grow, a few lines) |
| R6 | A blind sheet of saved KPI slides: LLM vs `grid` vs the composition the hint asks for (§9 Q5) | free; your marks |
| R7 | The prompt cost of the vocabulary and the per-component line, measured rather than estimated (§9 Q6) | count tokens on 10 saved slides |
| R8 | A unit test that every tag / variant / style name a prompt or knowledge file uses exists in `block-variants.yaml` (promised in its header, missing; left-blocks §3) | **build** with step 1 |
| R9 | Code fixes found by R1–R4 (C6, C10, C11, C12): chart label ink from `$chartInk` and a number format from the plan's unit; the split " — " before ": " and the `numbered` ordinal rule; inner-box peer ids; value refs for code-drawn `rows` | **build**, each with its block (chart: the label ink and unit format) |

## 12. Who owns what (2026-11-03)

One rule for every block from here on. The free probe that tested it (§12.6) is `scripts/ownership_probe.py`, with its sheet
and results in `docs/eval/ownership-probe/`.

### 12.1 Three layers

| Layer | What | Who writes it | Changed by us? |
|---|---|---|---|
| 1 native POM nodes | `Text`, `Shape`, `VStack` / `HStack`, `Layer`, `Line`, `Arrow`, `Table`, `Chart`, `Ul`, `Timeline`, `ProcessArrow`, `Flow`, `Pyramid`, `Tree`, `Matrix`… | the LLM (free XML), or code inside a composition node | **never.** Fixed syntax (POM 10.3.0); we only compose around it |
| 2 composition nodes | `<Tag ref variant …/>`: `KpiRow`, `CardGrid`, `Chart`, `Table`, `Timeline`, and **now** `Ul` (`src/compiler/nodes/`: `tile_groups`, `cards`, `charts`, `sequences`, `tables`, `bullets`) | the LLM places the tag; code expands it from the plan into layer-1 nodes | yes, one kind at a time behind `POM_NODES` |
| 3 free LLM XML | slide layout, header (`title`), decor and arrow layers (`layer`), and any block with no node | the LLM | prompt and knowledge only |

### 12.2 The rule

- **Code owns everything inside a block's box:** every word and number (verbatim, in plan order), the parts and their
  order, type sizes, word fit, the emphasis item, and the ids.
- **The LLM owns everything outside it and every style choice on it:** layout, placement, size (`w h grow min* max*
  alignSelf`), the `variant` pick, and every styling attribute (box, `item.`, `<part>.`, `$tone*`, gradients, borders,
  per-item looks).
- **Colour freedom stays.** Fill, text colour and visuals are separate explicit choices with no auto-coupling
  (2026-11-02). Colours are `$tokens` only (`LITERAL_COLOR`), so a theme switch restyles the slide. A group's own box
  attributes stay on its own box (no cascade, 2026-10-26).
- **Content attributes the LLM writes are dropped, never followed** (`NODE_ATTR_DROPPED`): text, `fontSize`,
  `fontFamily`, `id`, `chartType`, `title`, positions.

### 12.3 One nesting level

The LLM places refs inside its own layout, and code builds a ref out of native nodes. **A ref is never placed inside
another ref**, and an LLM-placed ref never holds LLM children, except the documented ones (`<Card>` / `<Kpi>` item
tags, `<Highlight>` in `<Table>`). A ref inside an LLM card is fine (probe d1).

### 12.4 Admission and fallback

- **A kind becomes a node only if its free replay and the user's blind marks beat the LLM.** process_arrow and flow
  were dropped on 2026-11-02 (`claude/left-blocks-build-0fe007`, f49fab6): POM's fixed-size chevrons and flow boxes hold
  about 2 words, and the code-drawn steps were card grids under another name. They stay layer-1 native nodes that the
  LLM draws. **Now:** merged.
- **Every kind keeps a native fallback** (`variant="native"`, or the `requires` → `fallback` chain).
- **One source of truth:** `block-variants.yaml` (`nodes.<kind>`: tag, parts, compositions, styles, aliases). It is read
  by `spec.py` and guarded by the R8 test (`tests/unit/test_block_variant_names.py`).

### 12.5 Layers are the LLM's: the open risk

`NO_REF_KINDS` = `title`, `layer` stay with the LLM. The risk is absolute-positioned arrows and overlays over blocks
whose final size code or fit-grow decides. The LLM writes `<KpiRow ref/>` and never sees where the tiles end up.

### 12.6 Free probe (results: `docs/eval/ownership-probe/README.md`)

| Case | Result |
|---|---|
| a refs in LLM stacks with styling | holds |
| b Table ref + LLM native ProcessArrow | holds (the native chevrons stay small: an LLM / native-node problem) |
| c Line layer over ref blocks, fit-grow on | lands within ≤ 14 px, **given the pixels**. fit-grow moved boxes ≤ 6 px. The generator never has those pixels, and `regridTiles` / `fillLoneRows` (not triggered here) do move boxes |
| c POM `<Arrow from to>` on code ids | works with the real ids (`kpiv0-kpis-0` → `cardt-levers-0`). With the guessed ids it fails silently (`ARROW_REF_NOT_FOUND` is only a compile warning). Box ids (VStack) cannot be connected |
| d ref in LLM card / ref-in-ref | in a card: holds. Ref-in-ref: the inner KPI row is an error (`NODE_ITEM_MISSING`, which names the old tag `<KpiGrid>`). **The inner chart is lost with only a report.** `validate.check_skeleton` (`NODE_MISSING`) is not wired |
| e content attributes | all dropped. Invented names (`x`, `y`, `kpi_values`, `table_rows`) are `NODE_ATTR_UNKNOWN` **errors**: a repair call for a slide code already drew correctly |

## 13. Implementation plan from here (2026-11-03; code changes wait for the user's OK)

### 13.1 Which kind is where

| Status | Kinds |
|---|---|
| node (layer 2) | kpi_row (KpiRow), card_grid (CardGrid), chart, table, timeline, bullet_list (all merged, **Now:** 2026-11-04) |
| native, drawn by the LLM (layer 1 / 3) | process_arrow, flow (dropped 2026-11-02), pyramid, tree, matrix (C9; matrix `grid` only rendered), title / header, layer |
| undecided | **Now:** bullet_list is a node (A.5). **callout** (narrative: one item, so the gain is only the quote rule C5; candidate to stay LLM-drawn), **header** (`title` is in `NO_REF_KINDS`; keep it LLM-drawn unless a blind sheet says otherwise) |

### 13.2 Fixing the layer risk (proposal, in order)

1. **Anchor layers to block ids, not pixels.** Each node writes one stable, documented anchor id per item:
   `<cid>-<i>` on a connectable `Shape` (a `rect` with no fill, the item's size) or on the item's main Text. The prompt line
   names them, and the LLM draws `<Layer><Arrow from="kpis-0" to="levers-2"/></Layer>`. POM's connector then follows the
   boxes after fit-grow (probe c4).
2. **Turn a missed anchor into a node error** (`NODE_ANCHOR_UNKNOWN`, before compile), not a compile warning that
   leaves no arrow.
3. **Pixel layers over a ref block**: a `<Layer position="absolute">` whose children overlap a ref's box →
   `NODE_LAYER_OVER_REF` (warning, report the miss). fit-grow keeps `regridTiles` / `fillLoneRows` off for a block that a
   layer points at.

### 13.3 Validator gaps found

- Wire `validate.check_skeleton`'s plan-level check (`NODE_MISSING`, `NODE_REF_DUPLICATE`, `NODE_CHILDREN_DROPPED` →
  `NODE_REF_NESTED`) into `validator.py` before `composed.expand`, so that a ref-in-ref or a dropped component is one
  error with one message (d2).
- `NODE_ITEM_MISSING` names `<KpiGrid>`: under `POM_NODES=kpi_row` it should name `<KpiRow>`.
- Decide: should invented attribute names (`NODE_ATTR_UNKNOWN`) be an error (repair) or a dropped report? Code already
  draws the block right without them (e). A proposed split: unknown *part* attributes stay errors (the LLM meant a
  style), and unknown bare names on the tag are dropped with a report.

### 13.4 Per-node checklist (every new or changed kind)

1. `block-variants.yaml` `nodes.<kind>`: tag, parts, compositions (`requires` → `fallback`, ending in `native`), look,
   emphasis, styles, aliases. R8 passes.
2. Expander in `src/compiler/nodes/` from `compose.py` helpers: reads only the plan, writes the anchor ids (§13.2), peer
   ids (C11) and value refs (C12).
3. Prompt line (`prompt_line`, `node_lines`): the compositions the content allows, the style parts, and the anchor ids.
4. Validator codes: dropped / unknown / variant / nesting / missing, each with a unit test.
5. Gallery: a row per composition, two palettes, plus an ownership-probe row (refs in LLM stacks, a layer anchored to
   the node).
6. Free replay on saved slides (LLM layout kept, bare tag): scorecard + blind sheet.
7. The user's blind marks ≥ 0.5 (admission, §12.4); else the kind stays native.
8. Paid same-plan check, only with the user's OK, a case list and a cost estimate.

### 13.5 Before the paid same-plan runs (`scripts/composition_paid.py`, ≈ $0.87)

- The timeline (`0fe007`) and table (`3cf2e1`) branches are merged into one tree with f49fab6's process_arrow / flow drop,
  and unit tests pass apart from the 4 known failures.
- §13.3 is wired (no silent component loss), and the `NODE_ATTR_UNKNOWN` severity is decided, so that a paid run does not
  pay for repairs of slides that are already right.
- The anchor-id decision (§13.2) is made, at least for the prompt line: either the ids go into the prompt, or the
  prompt says "no layer over a ref block".
- The ownership probe and every gallery re-render clean on the merged tree.
