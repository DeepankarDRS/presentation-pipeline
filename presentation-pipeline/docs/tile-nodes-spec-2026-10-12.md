# Tile nodes: `KpiGrid` / `Kpi` and `CardGrid` / `Card` (spec, 2026-10-12)

Status: **KPI built behind `POM_BLOCKS=tiles` (2026-10-12, branch `feat/tile-nodes`; §10); Card built 2026-10-13 (branch `feat/tile-cards`; §11), matrix deferred.**
Data: `src/knowledge/core/block-variants.yaml` → `tile_nodes` (read by `src/compiler/nodes/tiles.py`; the `blocks`
section above it still serves the 1a node route). Builds on the KPI node pilot
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

## 10. Build notes (2026-10-12, steps 1–4, free)

Built: cache order (step 1), `tiles.py` + checks + prompt lines for KPI (step 2), gallery (step 3,
`docs/eval/tile-nodes/gallery/`), free replay (step 4, `docs/eval/tile-nodes/replay/`). What differed from this spec:

| § | Spec | Built / measured |
|---|---|---|
| §5 | fixed node lines ~150 tokens | ~300 (all variant phrases from the YAML); in the cached prefix |
| §5 | per-component line ~35 tokens | ~60–85: it also names each item's label (needed to pick an icon per item) and the longest value |
| §5 | ~9k of ~11.7k input a shared prefix | static prefix 1.2k → 7.5k tokens on the 4 saved decks (system tokens shared 14% → 74%); the rest per slide: notes for its kinds, recipes, visual-intent techniques, allowed attributes |
| §7 | KPI output ~12–60 tokens | 12–60 is the floor without styling; reproducing the LLM's own part styling took 60–190 (replay: −78% overall, −84% on first tries) |
| §4 | resolution order house → group variant → group attrs → item variant → item attrs | an item's own variant **replaces** the group variant's look (else an inverted tile kept the plain hairline); the group's attributes still apply under it |
| §2 | `size` hero on the emphasis item | a hero tile inside its group's row needs equal columns (code sets `w="1" grow="1"`): the peers grew first and the shrink guard cut the hero below them |
| §2.1 | `toned` needs tones | the LLM tints tiles by meaning where the plan has no tones; proposal: `has_tones` also counts an item's explicit `color` |
| §2 | `size` on a group | dropped with info (`NODE_ATTR_DROPPED`), as on a part; not an error |
| — | — | an `icon` on a dark tile takes the readable ink (`$onPanelDark`), as its text does |
| §9 T4 | numerals Shape check in the gallery | a Card question; open until cards are built |
| §5 | the planner's `design_hint` reaches the generator as today | after the paid check (QBR: a bare `<KpiGrid>`, the hint's colours dropped): the fixed lines map each kpi_row treatment to tile attributes (`kpi.treatments` in block-variants.yaml; ~554 tokens now, cached); under tiles the hand-built KPI techniques leave VISUAL-INTENT TRANSLATION and `sparkline` leaves the kpi_row scope (a Kpi holds no chart); the per-component line lists the variants it can use (no `toned` without tones, no `inverted` without the plan's emphasis item) and says when there is no emphasis item / no tones; `<Kpi>` only for an item that differs |
| §2.1 | `color` picks the role; `toned` needs tones | after paid check 2 (CHEFFIN 4: `color` on plain tiles with no note / icon drew nothing): a variant may name a `with_color` look; `plain` → `toned`, taken by an item with its own `color` and no variant of its own (`1b9af6c`) |
| §2 | `layout` default: row, grid when more than 4 | a row code chose is id'd `kpig-<component>`; fit-grow `regridTiles` keeps its balanced two-row grid when the numbers end ≥ 15% larger (QBR: 58 px in one row of 4, width-bound by "14 months"; 85–87 px as 2 × 2). Content-sized ref tiles grow labels / notes with the numbers inside the search (`e57c8b4`) |
| — | — | a tile on the LLM's own box of the same fill draws bare (no fill / border / padding); a content-sized hero ≥ 48 px grows after the other KPI groups (CHEFFIN 1 platform row 28 → 49–60 px, `875a18b`). Paid-2 runs re-scored: `docs/eval/tile-nodes/paid-2/README.md` "Fixes" |
| §6 | planner fills `kpi_tones` reliably | built (`27b7aae`): prompt schema + example + rule (by meaning, from the key_messages / headline only), `plan_checks.settle_kpi_tones` (one per value, synonyms, none kept when all blank). §2.1: `plain` draws a tone with no colour asked (`with_tone`: bad / watch → toned, good → the number in its colour); `toned` now has tones to meet `has_tones`. Card `tone` not built (cards not started). `kpi_paid --plans` runs arm B on fresh planner plans (`b115ef9`) |

## 11. Card build (2026-10-13, branch `feat/tile-cards`, free)

Built from the KPI learnings (user's list, 2026-10-13), checked on saved runs only: no test-PC run yet.

**Decisions (user, 2026-10-13):**
- Grid emphasis comes from a planner field, `focus_card` (index, only when the brief singles one card out), not from
  the design hint. Evidence: of 60 saved card grids, 20 grid hints asked for emphasis, but the hint named exactly one
  card in only 4; the LLM still drew a dark card on 20 cards.
- The plan marks a card's coloured key phrase (`key_phrase`, exact words of its body, at most one per card). The LLM
  coloured spans inside card text on 14 of 60 grids (29 cards); under tile nodes code writes the text, so the plan carries it.
- Matrix card grids are deferred (2 of 60 saved): they keep the hand-written route and recipe.

**Planner** (`slide_component_planner/system.j2`, `planner_schema.py`, `plan_checks.settle_card_fields`): per-card
`tone` (as `kpi_tones`), optional `key_phrase` (kept only when its words are in the card's body / bullets, the whole
line never), optional `focus_card` (dropped out of range, on a matrix, or on the last step, where the destination is
the default). `spec.singled_out` reads `focus_card` before the hint, so every route sees it.

**Code** (`src/compiler/nodes/cards.py`; data `block-variants.yaml` `tile_nodes.card`), run by `tiles.fill` before the KPI tiles:

| Learning | Built |
|---|---|
| 1. defaults decide quality | a bare `<CardGrid ref/>` draws the plan's meaning: tones (bad / watch → toned, good → coloured left edge), the emphasis card dark (`focus_card` → hint → last step; the LLM can restyle it with a variant of its own), key phrases in the card's colour (bold on a dark card). Default variant `column` (user, 2026-10-13): an open text column with a 3 px left rule in the tone / `color`, no fill, so cards read apart from KPI tiles (boxed numbers); the other variants stay available |
| 2. emphasis readable from the plan | `focus_card`; steps → destination; matrix deferred |
| 3. anything asked must show | every variant shows an item's `color` (`with_color`: toned / left edge / numeral colour); `toned` leaves cards without a tone neutral; the per-component line lists only usable variants (no `inverted`, no `toned` without tones, no `numerals` on numbered titles) |
| 4. measured layouts | columns from text length (≤ 4 per row; long cards 3 or 2; 5 → 3 + 2, 7 → 4 + 3), peers `w="1" grow="1"`, group id `cardg-<cid>`; fit-grow `regridCards` tries balanced layouts with fewer columns and keeps one whose smallest title ends ≥ 15% larger (gallery: 4 short cards 37 → 48 px as 2 × 2; 4 cards in a half column 20 → 36 px) |
| 5. ids | `card-<cid>-<i>`, `cardt-` (title), `cardb-` (body), `cardn-` (numeral; fit-grow grows it as text to 72 px, never as a KPI number: it froze at 40 px and held titles at 0.62 × 40, or grew 40 → 96 px) |
| 6. the LLM's wrappers | a card on the LLM's panel of its own fill draws bare; a `<CardGrid>` / `<Card>` inside a `<Text>` (or inline run) replaces the wrapper (`NODE_ATTR_DROPPED`); the gallery has a wrappers sheet |
| 7. code writes the text | title, tag, body, bullets (`Ul`), key phrase (`Span` / `B`); body = list → bullets |
| thin plans | a group whose cards have only titles (21 of 80 saved plans) is drawn to its content and centred in its band (user: compact, centred); plan check `CARD_LINES_DROPPED` re-asks the planner once when a title-only card's title opens a line of the brief with 4+ more words (the brief gave it a line the plan dropped) |
| 9. cost | card node lines in the cached prefix; `card_grid` / `card_steps` recipes and hand-built card techniques dropped when every card_grid is code-drawn; card content left out of the user prompt (titles only in the line) |

Layouts: `grid`, `steps` (cards joined by `arrow-right` icons, the step number leads the tag line: "01 · DAY 0-30"),
`rail` (one card per row, the number and a line to its left). Dropped from the design: `columns` (segmented bar) and
`arrange="title-band"` (not needed by any saved slide); `numerals` uses a Text, not a transparent Shape (T4).
Square cards (`borderRadius` dropped, as KPI tiles).

**Gallery** (`python -m scripts.card_gallery`, `output/card-gallery/`): every variant on a 5-card grid, 9 layouts,
6 wrapper boxes, corporate-slate + graphite-dark; all compile. Found and fixed there: numerals as a KPI number,
toned tinting neutral cards, an invisible key phrase on dark cards, the rail number squeezed (POM sizes a `w="max"`
Text to its own measure), a numbered step's "01" outgrowing its title.

**Render font (found 2026-10-13):** `kpi_replay.compile_slide` (used by the KPI / tile / card replays and galleries) skips `compiler_client.deck_font`, so fit-grow measured Noto Sans JP and LibreOffice, which ignores the fonts embedded in the .pptx, drew bold text in Arial Black: the first card replay showed text overlaps the real deck does not have. The card replay and gallery now set the deck font and render through a private LibreOffice profile holding the deck fonts (`output/lo-inter`). The KPI replays still use the old path; their broken-word counts were measured in the wrong font.

**Replay** (`python -m scripts.card_replay`, `output/card-replay/`): 80 saved card slides (output/**/slides.json: eval, q1008, kpi-decks, kpi-decks-2, wide-paid, critic-on, colour roles, step 0),
75 replayed (5 skipped: a card title not on the slide, empty plans). A = the LLM's hand-drawn cards, B = the same slide with only
those cards replaced by one bare `<CardGrid ref>` at their place (with the LLM's `w` / `grow`; the generator writes bare tags,
learning 1; `--styled` writes the variant / icons read from the LLM's drawing instead). `focus_card` / tones / `key_phrase`
stand-ins are read from the LLM's dark card, tinted cards and coloured runs (19 / 21 / 22). Both rendered in Inter.

| | A | B bare (`column`) | B styled |
|---|---|---|---|
| compiled | 75 | 75 | 75 |
| GEOM_CARD_EMPTY | 44 | 44 | 34 |
| broken words / text overlaps (render) | 5 / 6 | 4 / 3 | 6 / 7 |
| WORD_TOO_WIDE | 2 | 2 | 2 |
| LOW_CONTRAST | 20 | 8 | 8 |
| plan text missing | 0 | 0 | 0 |
| smallest card title / body (median px) | 22 / 21 | 34.5 / 25.5 | 26.5 / 22.5 |
| card output tokens | 46,094 | 930 (−98%) | 4,744 (−90%) |

Before the compact title-only drawing and the `column` default (54 slides, `filled` default): GEOM_CARD_EMPTY 33 → 45.
Content B drops: the LLM's own lines that are not in the plan: 4 of 80 components, 31 lines (step labels, headers, and on
XTSY slide 3 bullets not in the brief: invented, so dropping them follows the content policy).
Blind sheets: `output/card-replay/sheets/` (marks.csv; key.json after marking). Gate before the paid check: marks ≥ 0.5.

**Blind marks (user, 2026-10-13, saved in `docs/eval/card-nodes/replay-2/`):**
- Round 1, bare `column` default: **0.313** (B 20 / tie 7 / A 48). Reasons: separation between cards (A won on it 31 times),
  icons (24), colour (8); B won on text size and space. The open column was dropped as the default.
- Round 2, `lifted` default (white card, 8 px radius, 10% shadow, tone tint, tone-coloured tags, plan icons in the tag line or
  above the title, key phrase as a `<Mark>` highlighter): **0.533** (B 24 / tie 32 / A 18, + 1 auto loss: the `w="max"`
  squeeze compile failure) - passes the tile gate (0.5), below the 1a gate (0.6). Replay: empty cards 54 (A 44), overlaps
  5 (A 6), LOW_CONTRAST 7 (A 20), titles 26 px (A 22), card output tokens -98%.
  B won on space allocation and consistent card sizes; A won on coloured text runs ("span text color", "I like span better
  than the mark"), content the plan lacks (bullets the LLM added, 4 pairs; an org chart planned as cards), two card groups drawn
  alike ("variants for 2 types of cards"), and a step number in front of year tags ("01 · 2021").

Open: the rail's text does not grow (wide cards, little spare height); a short last row stretches wider than the row
above (KPI rows do the same); numerals + icons on a 5-card grid leave little room to grow.
