# One composition convention for every derived node (spec draft, 2026-10-27)

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
| D7 | Card compositions | `grid` (default) · `grid numbered` · `rows` / `rows numbered` · `columns` · `banded` · `bento` · `steps` · `rail` (rendered: `rows numbered`, `columns`, `banded`, `bento`, §6) |

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
  `icons`), over joined rows tinted by turns. The table also takes the shared `grid` / `grid numbered` (every
  cell its own card under the header; `labels="inside"` writes each column name in its cards instead).

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
| `rail` | today's rail | as today | `outline` | the destination |

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
| table (`<Table>`) | `native` · `rows` / `rows numbered` · `columns` · `banded` | `columns`: ≤ 5 rows, ≤ 6 columns; `banded`: ≤ 6 rows → `native` | `plain` (default look), `zebra` (`stripe.`), `dark_header` (`header.` / `label.`); `highlight_row` = emphasis look; `minimal` dropped (C2) |
| chart (`<Chart>`) | `native` · `native labelled` · `rows` | `labelled` / `rows`: one series, ≤ 8 points (bar for `labelled`) → `native` | `focus_label` = emphasis look of `native labelled`; `horizontal` → `direction` |
| bullet_list (`<Ul>`, user 2026-11-04: `grid` / `banded` deleted as the card grid's looks, `docs/eval/bullet-node/`) | `native` · `native numbered` · `rows` (optional `icons`, ≤ 6 points) / `rows numbered` | numbered: no own numbers → `native` / `rows`; anything that cannot be composed → `native`, POM's real list | `lead` = `native` default; `icon` = `rows` + `icons`; `columns` = fit-grow's automatic split (4+ short points) |
| timeline (`<Timeline>`) | `rail` · `rows` · `banded` · `native` | `native`: every label fits the break-map room and has no detail → else `rail` (default chosen from content) | `vertical` → `direction` |
| process_arrow (`<ProcessArrow>`) | `native` · `steps` / `steps numbered` · `rail` | `native`: every step fits (≤ ~24 characters, C8) → else `steps` (default chosen from content); `numbered`: no dates, no own ordinals | — |
| flow (`<Flow>`) | `native` · `steps` / `steps numbered` | linear list only | — |
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
- **Timeline (C4):** `columns` is not used (timeline items have no sub-items). `banded` uses the date as the
  band, coloured done / now / ahead from the "now" item (hint only).
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
§2.5, §13): chart, then timeline + process_arrow + flow, then table, then bullet_list. Callout comes later, and
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
