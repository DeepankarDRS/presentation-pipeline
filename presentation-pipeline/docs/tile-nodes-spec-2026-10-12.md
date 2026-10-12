# Tile nodes: `KpiGrid` / `Kpi` and `CardGrid` / `Card` (spec, 2026-10-12)

Status: **design, not built.** Data: `src/knowledge/core/block-variants.yaml` → `tile_nodes` (not read by
code yet; the `blocks` section above it still serves the 1a node route). Builds on the KPI node pilot
(`docs/kpi-node-pilot-2026-10-11.md`, D13) and replaces, for the element-ref route, the variant syntax of
`docs/block-variants-look-spec.md` §4–§6. The colour roles, number caps, tones and value parser of those
docs carry over unchanged.

## 1. Why

Today (element refs, `POM_BLOCKS=kpi`) the LLM writes every KPI tile by hand and code fills the text:

| Measured | Tokens |
|---|---|
| generator call, per slide (1a summary, 32 slides) | 11.7k in (724 cached, 6%) / 1.04k out |
| KPI tiles the LLM writes, 4 tiles | ~600 out (2×2 grid + dark focus panel ~750) |
| kpi_row + dark_callout_panel recipe injected on a KPI slide | ~1,380 in |
| element-refs prompt line | ~250 in |

The look the LLM composes won the blind marks (§10–§13: layouts the LLM chose, dark focus panels,
4 + 3 grids). The 1a skeleton (`<KpiRow ref variant/>`, ~15 tokens) was cheap but code chose the whole
look. Goal: keep the LLM's freedom over arrangement, colour, icons and per-tile look, and cut the tokens.

Decisions (user, 2026-10-12):
1. Tiles are written like native POM data nodes: a group tag and an item tag (`Timeline` / `TimelineItem`),
   a one-word `variant` (`Icon variant`), a per-item `color` (`TimelineItem color`), shared attributes on
   the group that items override (`Timeline.dateColor` → `TimelineItem.dateColor`).
2. A tile is a VStack holding Text, Icon and Shape parts, so its attributes are those nodes' own
   attributes, reached with POM's dot style (`label.color`, `value.glow.size`, `icon.variant`,
   `marker.fill.color`). No invented names such as `labelColor`.
3. Notes are always drawn: the LLM cannot hide plan content.
4. `borderRadius` stays banned for now (square tiles, §11 of the pilot).

## 2. KPI

```xml
<KpiGrid ref="kpi_metrics" variant="filled" cols="2" />
```

`<KpiGrid>`: `ref` (required) `layout` `cols` `variant` `arrange` `color` `icon` + part attributes + box attributes. Children: `<Kpi>` only.
`<Kpi>`: `ref` (required) `variant` `arrange` `size` `color` `icon` + part attributes + box attributes. Self-closing.

### `<KpiGrid>`: the group

Draws every item of the component, in plan order, except items a `<Kpi>` places outside it.

| Attribute | Values | Default |
|---|---|---|
| `ref` (required) | component id | |
| `layout` | `row` / `grid` / `column` | `row`; `grid` when more than 4 items |
| `cols` | number (with `grid`) | balanced: 5 → 3 + 2, 7 → 4 + 3 |
| `variant`, `arrange`, `color`, `icon`, part attributes | defaults for every tile | |
| `gap` + box attributes | the box around the whole group | |

### `<Kpi>`: one tile

Inside a `KpiGrid` it overrides that item; outside, it places the item anywhere on the slide.

| Attribute | Values | Default |
|---|---|---|
| `ref` (required) | `<component_id>.<index>` | each item exactly once |
| `variant` | §2.1 | the group's, else `plain` |
| `arrange` | `label-first` / `value-first` / `icon-top` / `side` (icon or marker left, text right) | `label-first` |
| `size` | `normal` / `hero` | `normal`; `hero` only on the emphasis item |
| `color` | `$accent` / `$positive` / `$negative` / `$warning` / `$neutral` | the plan tone (good → positive, bad → negative, watch → warning, none → accent) |
| `icon` | an icon name (shorthand for `icon.name`) | none |
| `label.*` `value.*` `note.*` | Text: `color` `bold` `italic` `underline` `highlight` `letterSpacing` `textAlign` `textGradient` `glow.*` `outline.*` | from the variant |
| `icon.*` | Icon: `name` `color` `variant` `bgColor` `glow.*` `outline.*` | from the variant |
| `marker.*` | Shape (a dot or bar before the label): `shapeType` `w` `h` `fill.*` `line.*` `glow.*` | from the variant; drawn only when the variant has one or `marker.shapeType` is set |
| box attributes | `backgroundColor` `backgroundGradient` `border.*` `borderTop/Right/Bottom/Left.*` `padding(.*)` `gap` `alignItems` `justifyContent` `shadow.*` `opacity` `w` `h` `grow` `min/maxW/H` `alignSelf` `margin` | from the variant |

**Dropped with info `NODE_ATTR_DROPPED`** (code owns them): `fontSize`, `fontFamily`, `lineHeight` and
`size` on any part (icon size follows the label), `borderRadius`, `position` / `top` / `left` / …,
`zIndex`, `id`, typed text or children inside `<Kpi>`.

**Code owns:** the label, value and note text, word for word from the plan; one value size per group
(hero larger, `weight` ranks from §9); unit spans (`value_parts`, V15); word fit (fit-grow `kpiv-` ids);
readable text on dark fills; the icon size.

### 2.1 KPI variants

`{role}` = the item's `color` role. `$neutral` has no Soft / Text token: Soft → `$surfaceAlt`, Text → `$textMain`.

| `variant` | Look | Rules |
|---|---|---|
| `plain` (default) | `$surfaceAlt` tile, `$border` hairline, number in `$textMain`, note in `{role}Text` | |
| `filled` | `{role}Soft` tile, number in `{role}Text` | |
| `toned` | `{role}Soft` tile, `{role}` border, number and note in `{role}Text` | needs tones, else `plain` |
| `bar` | `$surfaceAlt` tile, 6 px left bar in `{role}` | |
| `dot` | `$surface` tile, hairline, 8 px `{role}` dot, spaced label in `{role}Text` (llm.md "KPI Tile with Dot Indicator") | |
| `inverted` | `$panelDark` tile, text `$onPanelDark` | emphasis item only, 3+ items, else `plain` |
| `bare` | no tile: label, number, note | |

The exact attribute values of each look are in `block-variants.yaml`.

### 2.2 KPI examples

```xml
<!-- 1. one tag (~12 output tokens) -->
<KpiGrid ref="kpi_metrics" variant="filled"/>

<!-- 2. one tile singled out (~35) -->
<KpiGrid ref="kpi_metrics" variant="plain" cols="2" icon.color="$accent">
  <Kpi ref="kpi_metrics.2" variant="toned" icon="alert-triangle"/>
</KpiGrid>

<!-- 3. grid + dark focus panel (~55; today ~750) -->
<HStack gap="18" grow="1">
  <KpiGrid ref="kpi_metrics" variant="dot" cols="2" w="max"/>
  <Kpi ref="kpi_metrics.4" variant="inverted" size="hero" arrange="value-first" w="36%"/>
</HStack>

<!-- 4. two groups by role (§14 planner grouping) -->
<KpiGrid ref="kpi_hero" variant="bare" value.glow.size="6" value.glow.color="$accent"/>
<KpiGrid ref="kpi_support" variant="bar"/>

<!-- 5. a native effect on one part -->
<Kpi ref="kpi_metrics.0" icon="trending-up" icon.variant="circle-filled" icon.bgColor="$accentSoft"
     value.textGradient="linear-gradient(90deg, $accent 0%, $accentText 100%)"/>
```

Example 3's focus tile expands to roughly:

```xml
<VStack id="kpit-…" backgroundColor="$panelDark" padding="24" gap="8" w="36%">
  <Text id="kpiv-…" color="$onPanelDark" bold="true" fontSize="(code)">…value…</Text>
  <Text color="$onPanelDark" bold="true">…label…</Text>
  <Text color="$onPanelDark">…note…</Text>
</VStack>
```

## 3. Card

```xml
<CardGrid ref="cards" variant="outline" cols="3" />
```

`<CardGrid>`: `ref` (required) `layout` `cols` `variant` `arrange` `color` `icon` + part attributes + box attributes. Children: `<Card>` only.
`<Card>`: `ref` (required) `variant` `arrange` `color` `icon` + part attributes + box attributes. Self-closing.

| | KPI | Card |
|---|---|---|
| `layout` | `row` / `grid` / `column` | `grid` / `matrix` / `steps` (cards in a row with arrows) / `rail` (vertical line, a dot per step, text right) / `columns` (columns under a segmented bar). Must match the plan's `card_layout`: grid → grid; matrix → matrix; steps → steps / rail / columns. Otherwise `NODE_LAYOUT_UNMET` and the plan's layout is used |
| `arrange` | as §2 | `stack` (icon or marker, title, body) / `side` (icon left) / `title-band` (title on a coloured strip) |
| parts | `label.` `value.` `note.` | `title.` `body.` (Text; one Text per body line), `icon.`, `marker.` (Shape; on steps and numerals code writes the number into it) |
| emphasis | design hint | design hint, matrix priority, the last step (steps layouts) |

**Code owns:** title and body text, the card's tag line, type sizes shared by all cards, step numbers,
arrows between steps, word fit, readable text on dark fills.

### 3.1 Card variants

| `variant` | Look | Rules |
|---|---|---|
| `outline` (default) | hairline card on the background | |
| `filled` | `$surfaceAlt` card, no border | |
| `toned` | `{role}Soft` card, 6 px `{role}` left edge, title in `{role}Text` | needs tones, else `filled` |
| `accent_top` | 4 px `{role}` bar on top (pillars, workstreams) | |
| `numerals` | large faint 01 02 03 above each title | not matrix, titles not already numbered, else `outline` |
| `inverted` | `$panelDark` card: the featured item or the destination step | emphasis item only, 3+ cards, not matrix, else `filled` |

```xml
<CardGrid ref="cards" layout="steps" variant="outline" icon.variant="circle-filled">
  <Card ref="cards.3" variant="inverted"/>          <!-- the destination step -->
</CardGrid>

<CardGrid ref="pillars" variant="accent_top" arrange="side" cols="3">
  <Card ref="pillars.1" color="$negative" icon="shield-alert"/>
</CardGrid>
```

## 4. Rules and checks

- **Placement.** A group draws its component's items minus those placed by item tags outside it. Each
  item drawn exactly once: `NODE_REF_DUPLICATE`, `NODE_ITEM_MISSING` (existing codes). An item tag
  inside a group must name that group's component: `NODE_REF_UNKNOWN`. With no group, every item
  needs its own item tag.
- **Resolution order** (later wins): house look → group `variant` → group attributes → item `variant`
  → item attributes.
- **Variants.** Unknown → the default (`NODE_VARIANT_UNKNOWN`). `requires` not met → the `fallback`
  chain (`NODE_VARIANT_UNMET`), with the same `spec.resolve_variant` as the 1a route.
- **Emphasis.** `inverted` and `size="hero"` are allowed only on the item an `emphasis_from` source
  names (`spec.singled_out`, destination, priority). The LLM never picks the emphasised item
  (user, 2026-10-07). New check `is_emphasis_item`.
- **Attributes.** A part attribute must be in `part_nodes` for its node, a box attribute in
  `box_attributes`; anything else → `NODE_ATTR_UNKNOWN` (error, re-ask). Dropped attributes → info.
  Colours are `$tokens` (`LITERAL_COLOR`); `color` takes the five role tokens.
- **Fallback route.** A tile written by hand with `<Text ref="….label"/>` (today's route) stays valid,
  and the eval counts how often the LLM uses it. Frequent use means a variant or arrange is missing.

## 5. Prompt

| Part | Today | Tile nodes |
|---|---|---|
| Fixed node lines (same every slide, so cacheable) | none | ~150 tokens: the four tag lines, the part → node rule, the variant names with their `prompt` phrases |
| Per KPI component | ~1,380 recipe + ~250 ref block | ~35: `kpi_metrics: 5 items (0-4), emphasis 4, tones 1=good 2=bad; <KpiGrid ref="kpi_metrics"/> or <Kpi ref="kpi_metrics.N"/>` |
| Per card component | ~1,000+ (card_grid / card_steps / card_matrix recipes) | ~35 |

The Text / Icon / Shape attribute lists are already in the system prompt (`allowed_attributes`), so the
part attributes need no new text.

**Companion change: cache order.** Only 6% of generator input is cached today: the slide-type block
(`src/prompts/generator/system.j2:76`) and the component recipes sit in the system prompt before the
static node reference. Moving every per-slide part to the user message (or the end of the system
prompt) makes ~9k of ~11.7k tokens a shared prefix. OpenAI bills cached input at ~25% on gpt-4.1, so
generator input cost would drop by roughly half (estimate). It doesn't depend on tile nodes and can
ship first.

## 6. Changes by stage

**slide_component_planner** (small; the plan stays the content truth, it picks no looks):
- `kpi_tones` and card `tone` filled reliably (good / bad / watch / "", by meaning: churn down = good);
  V10 of the look spec.
- The emphasis item named in `design_hint` next to an emphasis word (already read by `spec.singled_out`).
- Card body lines and step order as today; the §14 KPI grouping by role stays.

**generator:**
- `nodes.yaml` / validator: `KpiGrid`, `Kpi`, `CardGrid`, `Card` with the attribute rules of §4.
- `element_refs.prompt_line` → the ~35-token line; recipes for `kpi_row` / `card_*` not injected when
  tile nodes are on.
- New `src/compiler/nodes/tiles.py`: expand group and item tags from `tile_nodes` looks into VStack /
  Text / Icon / Shape before fit-grow, with the same `kpiv-` / `kpih-` ids and `refGroups`, so the
  pilot's §8–§13 code (one size per group, unit share, `stackTileIcons`, dark-tile colours) applies
  unchanged.
- Repairer: `NODE_*` messages as in `element_refs.repair_note`.

**Setting:** `POM_BLOCKS=tiles` (opt-in) beside `kpi` (today's default) and `off`.

## 7. Estimated cost

| Per KPI slide | Today | Tile nodes + cache order |
|---|---|---|
| Input | ~11.7k, ~6% cached | ~10.4k, ~9k of it cached |
| KPI output | ~600–750 | ~12–60 |
| Card output (6 cards) | ~700–900 | ~15–60 |

Every figure except "today" is an estimate until the paid check.

## 8. Build and check order

1. Cache order in `system.j2` / `user.j2` (free; check the system prompt is identical across one
   deck's slides; the cached share shows in the next paid run's `tokens_cached`).
2. `tiles.py` + validator + prompt line for KPI, behind `POM_BLOCKS=tiles`; unit tests.
3. Gallery of every KPI variant × arrange on two palettes (free; `scripts/kpi_gallery.py`).
4. Free replay: rewrite the saved `first-generated.xml` KPI tiles as tile tags and compare the renders.
5. One paid check, `python -m scripts.kpi_paid` (~$0.30, ask first): refs first try, output tokens,
   hand-written fallback count, then blind marks against today's route. **Gate:** marks ≥ 0.5 and KPI
   output tokens down ≥ 50%.
6. Card: the same steps.

## 9. Open questions

| # | Question | Draft |
|---|---|---|
| T1 | May `color` / `value.color` override the plan's tone colour? | yes (the plan's tone is the default) |
| T2 | Keep the hand-written `<Text ref>` tile as a fallback? | yes, counted in the eval |
| T3 | Icon size code-owned (follows the label)? | yes |
| T4 | `numerals` drawn with a transparent Shape carrying the number: check in the gallery that it renders | check |
| T5 | `matrix` layout: row / column headers from the plan, `Card` per cell; same rules as card_matrix today | confirm when cards are built |
| T6 | Should `CardGrid` steps arrows take a style attribute (`connector.color`)? | no, code draws them in `$neutral` |
