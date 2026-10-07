# Block variants: look spec for KPI row and cards (draft, 2026-10-06)

What each `variant` in `src/knowledge/core/block-variants.yaml` draws, for the KPI row, card grid and
card steps blocks (tags `<KpiRow ref>` and `<CardGrid ref>`). It is the step 1 spec for
`src/compiler/blocks/` (route `docs/derived-nodes-design.md` §14.6; node contract
`docs/derived-blocks-planning-2026-10-06.md` §3, D10, which replaced the slot form on 2026-10-06).
Nothing here is built. In 1a `variant` is only validated and counted. "Slot" below means the node's box.

The spec is grounded in the Phase 0b renderer (`scripts/phase0b/render.py`: `kpi_row`, `card_grid`,
`card_role`), the Genspark variant galleries (`docs/eval/genspark-variants/summary.md`) and the
decisions D1 (one palette, derived role tokens) and D8 (12 px label floor that grows).

## 1. Who decides what

| Layer | Decides | Never decides |
|---|---|---|
| **Plan** (`content_data`, `design_hint`, `weight`) | every word and number; which item is singled out; each item's **tone** (§4a) | look |
| **LLM** (node attributes) | node size (`w`, `h`, `grow`, `alignSelf`), `variant` | content, colours, type, the emphasised item |
| **Variant** (this doc) | fills, borders, where emphasis goes, decorations (numerals, pill, rail, bar) | sizes, columns, rows |
| **Pack** (structure only, D1) | type scale, title style (`italic_last`), badge, **default variant per block** | colours |
| **Palette** (`palettes.yaml` + derived tokens, D1) | every colour | — |
| **Block code** (fit) | number / title / body size, columns per row, rows, re-flow, fallback variant | wording |

**Change to the packs (proposal):** the pack options `fills`, `card_border` and `ghost_numerals`
overlap with variants, so they are replaced by one entry per pack,
`default_variants: {kpi_row: plain, card_grid: outline, card_steps: cards}`. A slot's `variant`
overrides that entry. `studio` becomes `{card_grid: outline, card_steps: cards}` + `italic_last`
titles. Its "fills rhythm" (every 4th card dark, one lime) is dropped, because it singled out cards
that the brief never named (§12 content policy, user highlight rule 2026-09-29).

## 1b. Syntax: one form for every tag and variant

Every variant uses the same syntax: the tag, `ref`, and optionally `variant` and layout attributes.
A variant never adds attributes, and its content always comes from the plan. **Minimal form:**
`<KpiRow ref="c2" />` (default variant; `NODE_NO_SIZE` gives it `grow="1"` when nothing sizes it).

```
<Tag ref="<component id>" [variant="<name>"] [w h grow alignSelf] [native presentation attributes] />
```

What a variant needs is a condition on the **plan's content** (item count, a design hint naming an
item, tones), checked by code; it is never an attribute. Generated from `block-variants.yaml`:

| Tag (plan kind) | Variant → what the LLM writes | Needs in the plan (else fallback) | Drawn by |
|---|---|---|---|
| `KpiRow`<br>kpi_row | `plain` (default): `<KpiRow ref="c2" />` | — | block |
|  | `filled`: `<KpiRow ref="c2" variant="filled" />` | — | block |
|  | `inverted`: `<KpiRow ref="c2" variant="inverted" />` | ≥ 3 items, the design hint names one item → `plain` | block |
|  | `hero`: `<KpiRow ref="c2" variant="hero" />` | exactly 1 item → `inverted` | block |
|  | `bare`: `<KpiRow ref="c2" variant="bare" />` | — | block |
| `CardGrid`<br>card_grid (grid / matrix) | `outline` (default): `<CardGrid ref="c2" />` | — | block |
|  | `filled`: `<CardGrid ref="c2" variant="filled" />` | — | block |
|  | `featured`: `<CardGrid ref="c2" variant="featured" />` | ≥ 3 items, the design hint names one item, not a matrix → `filled` | block |
|  | `numerals`: `<CardGrid ref="c2" variant="numerals" />` | not a matrix, titles not already numbered → `outline` | block |
|  | `toned`: `<CardGrid ref="c2" variant="toned" />` | ≥ 1 item has a tone → `filled` | block |
|  | `accent_top`: `<CardGrid ref="c2" variant="accent_top" />` | — | block |
| `CardGrid`<br>card_grid (steps) | `cards` (default): `<CardGrid ref="c2" />` | — | block |
|  | `rail`: `<CardGrid ref="c2" variant="rail" />` | — | block |
|  | `columns`: `<CardGrid ref="c2" variant="columns" />` | — | block |
| `Callout`<br>narrative | `rule` (default): `<Callout ref="c2" />` | — | block |
|  | `tinted`: `<Callout ref="c2" variant="tinted" />` | — | block |
|  | `dark`: `<Callout ref="c2" variant="dark" />` | — | block |
|  | `quote`: `<Callout ref="c2" variant="quote" />` | — | block |
| `SlideHeader`<br>title | `standard` (default): `<SlideHeader ref="header" />` | — | block |
|  | `inverted`: `<SlideHeader ref="header" variant="inverted" />` | — | block |
| `Text`<br>narrative, caption | `plain` (default): `<Text ref="c2" />` | — | POM (native) |
| `Table`<br>table | `plain` (default): `<Table ref="c2" />` | — | POM (native) |
|  | `zebra`: `<Table ref="c2" variant="zebra" />` | — | POM (native) |
|  | `highlight_row`: `<Table ref="c2" variant="highlight_row" />` | the design hint names one item → `plain` | POM (native) |
|  | `dark_header`: `<Table ref="c2" variant="dark_header" />` | — | POM (native) |
| `Chart`<br>chart | `native` (default): `<Chart ref="c2" />` | — | POM (native) |
|  | `labelled`: `<Chart ref="c2" variant="labelled" />` | a bar chart → `native` | block |
|  | `horizontal`: `<Chart ref="c2" variant="horizontal" />` | a bar chart → `native` | block |
| `Ul`<br>bullet_list | `plain` (default): `<Ul ref="c2" />` | — | POM (native) |
|  | `icon`: `<Ul ref="c2" variant="icon" />` | — | block |
|  | `tiles`: `<Ul ref="c2" variant="tiles" />` | — | block |
|  | `columns`: `<Ul ref="c2" variant="columns" />` | — | block |
| `Timeline`<br>timeline | `rail` (default): `<Timeline ref="c2" />` | — | POM (native) |
|  | `vertical`: `<Timeline ref="c2" variant="vertical" />` | — | POM (native) |
|  | `cards`: `<Timeline ref="c2" variant="cards" />` | — | block |
|  | `columns`: `<Timeline ref="c2" variant="columns" />` | — | block |
| `ProcessArrow`<br>process_arrow | `chevrons` (default): `<ProcessArrow ref="c2" />` | — | POM (native) |
|  | `numbered`: `<ProcessArrow ref="c2" variant="numbered" />` | — | block |
|  | `alternating`: `<ProcessArrow ref="c2" variant="alternating" />` | — | block |
|  | `step_cards`: `<ProcessArrow ref="c2" variant="step_cards" />` | — | block |
| `Flow`<br>flow | `boxes` (default): `<Flow ref="c2" />` | — | POM (native) |
|  | `numbered`: `<Flow ref="c2" variant="numbered" />` | — | block |
|  | `step_cards`: `<Flow ref="c2" variant="step_cards" />` | — | block |
| `Pyramid`<br>pyramid | `native` (default): `<Pyramid ref="c2" />` | — | POM (native) |
| `Tree`<br>tree | `native` (default): `<Tree ref="c2" />` | — | POM (native) |
| `Matrix`<br>matrix | `native` (default): `<Matrix ref="c2" />` | — | POM (native) |

Native tags may also carry their own presentation attributes (never content):
- `Text`: fontSize, color, bold, textAlign
- `Table`: cellBorder.color / .width
- `Chart`: showLegend, showTitle
- `Ul`: fontSize, color, lineHeight
- `Timeline`: direction, dateColor, titleColor, connectorColor
- `ProcessArrow`: direction, gap, fontSize
- `Flow`: direction, connectorStyle, nodeWidth / nodeHeight / nodeGap
- `Pyramid`: direction, fontSize
- `Tree`: layout, nodeShape, connectorStyle, levelGap / siblingGap
- `Matrix`: axisLabelColor, quadrantLabelColor, itemLabelColor

## 2. Tokens: every colour comes from `palettes.yaml`

The ten palette colours (`surface`, `surfaceAlt`, `accent`, `accentAlt`, `positive`, `negative`,
`warning`, `textMain`, `textMuted`, `border`) are used as they are. The role colours the blocks need
are **derived by code from the same palette**: a palette colour, or a mix of two palette colours,
moved in small steps until the text drawn on it reaches 4.5:1. The LLM never names a colour inside a
node. Reference implementation: `tokens()` in `scripts/variant_gallery.py` (becomes step 1 code).

| Role | Rule | Used by |
|---|---|---|
| `panelFill` | `surfaceAlt` if it shows against `surface` (≥ 1.12:1), else `surface` stepped 8 → 3% toward `textMain`, the first step on which `textMuted` still reads | `plain` tiles, `filled` cards (V8) |
| `panelInk` | `textMain` (checked on `panelFill`) | text on panels |
| `darkFill` | light palettes `textMain`; dark palettes `surface` 12% toward `textMain` | `inverted`, `hero`, `featured`, destination step |
| `onDark` | first of `surface`, `surfaceAlt`, `textMain` reading on `darkFill` | text on dark fills |
| `accentOnDark` | `accent` moved toward `onDark` until it reads on `darkFill` | labels on dark fills |
| `accentInk` | `accent` moved toward `textMain` until it reads on `surface`, `panelFill`, `surfaceAlt` | every small accent **text** (tags, kickers, numerals). Raw `accent` is kept for fills, bars, dots |
| `accentSolid` + `onAccent` | `accent` and the first palette text colour reading on it; for a mid-tone accent no text reads on, `accent` is darkened toward `darkFill` until `surface` reads | the hero pill |
| `accentTint` | `accent` mixed 88% (dark palettes 80%) toward `surface`, then further until `textMain` and `textMuted` read | `filled` tiles, progress-bar track (V1) |
| `positiveTint` / `negativeTint` / `warningTint` | the tone mixed 90% (dark 80%) toward `surface`, then further until text reads | `toned` cards (V9) |
| `positiveInk` / `negativeInk` / `warningInk` | the tone moved toward `textMain` until it reads on its tint, `panelFill` and `surface` | KPI notes, tone tags (V9) |

**Checked 2026-10-07 on all 18 palettes** (19 text pairs each):
- **Text pairs:** 0 below 4.5:1, and no role fell back to a white or black outside the palette.
- **First version, before the fix:** 34 failures. It darkened `accentTint` toward the text colour (grey tints on gj-h1 and claude-cream), coloured notes with the raw tone instead of its ink, and drew tags in raw `accent` (2.3:1 on navy-orange). Those three fixes are in the rules above.
- **Non-text pairs (WCAG 3:1, informational):**
  - `border` hairlines are 1.2–1.9:1 on every palette (decorative card outlines).
  - `accent` bars in saascolor and navy-orange are 2.3–2.4:1.
  - The gj-h1 warning edge is 1.9:1 on its tint.
  - None of these carries meaning alone: the tone is also in the tag's ink.

## 3. Shared type and spacing (all three blocks)

- **Labels** (KPI label, card tag): mono, uppercase, letter-spacing 1.6. The **12 px floor** grows
  into spare height up to 14 px (D8). Today `kpi_label_fs` starts at the pack's 10 px; that changes.
- **Body** (card description, bullets, KPI note): ≥ 14 px, and grows to fill (`fill_card_text`).
  The KPI note currently drawn at 11 px moves to the 12 px label tier (it is a caption, not body).
- **Numbers**: bold sans. They fill the tile's width (95%) and free height, at a line height of
  `GLYPH_H` 1.2. The unit is drawn as a span at 0.45×. Caps: 120 px for `hero`, 96 px for the
  others (decision V2; today every slot-sized tile caps at 120).
- **Peers share a size:** all tiles in a row use one number size, and all cards in a grid use one
  title and one body size. A peer grid beside it takes the smaller of the two (`_fit`).
- Tile and card padding 20 / 18, gap 12 between tiles and cards, as in Phase 0b.
- **Never** shrink text to fit and never drop items. The fallbacks are re-flow, then a more compact
  variant, then `NODE_OVERFULL` to the checking loop.

## 4. KPI row

Content: `kpi_labels`, `kpi_values`, `kpi_deltas` (note or change, may be null), `kpi_directions`.
Tile anatomy, top to bottom: label → number → note. The note is shown only when the plan has one.
The note colour follows `kpi_directions` and house-style `color_roles` (negative = losses / risks,
positive = wins), not the variant.

| Variant | Tiles | Emphasis | Requires → fallback |
|---|---|---|---|
| `plain` (default) | fill `panelFill`, label `textMuted`, number `panelInk`, no border | none | — |
| `filled` | fill `accentTint`, label `textMuted`, number `textMain`, no border | none | — |
| `inverted` | as `plain`; the tile the design hint names is `darkFill`, label `accentOnDark`, number and note `onDark` | 1 tile | ≥ 3 tiles and the design hint names one → `plain` |
| `hero` | one tile, `darkFill`; label `accentOnDark`; number up to 120 px `onDark`; the note as a **pill** (rounded rect, fill `accentSolid`, text `onAccent`, 12–14 px), placed under the number | the tile itself | exactly 1 value → `inverted` |
| `bare` | no tiles: number over label, spaced across the slot, on whatever the slot sits on (slide background or a panel / dark band the LLM drew). On `darkFill`: number `onDark`, label `accentOnDark` | none | — (added 2026-10-06, from the hand-written examples: a supporting row, a cover / closing band) |

### 4a. Tones (added 2026-10-06)

`kpi_directions` (up / down) says which way a number moved, not whether that is good: churn going
down is good news. The slide component planner therefore writes a second field,
`kpi_tones: ["good" | "bad" | "watch" | "", …]` (cards: `tone` per card), from what the number
means for the audience. `""` when the brief does not say. Code maps good → `positive`, bad →
`negative`, watch → `warning`. In **every** KPI variant the note line takes the tone's ink (`positiveInk` …), and
code puts ▲ / ▼ in front of it from `kpi_directions` (derived, not content). The number stays ink.
A tone is never written as a word on the slide. Planner prompt cost: ≈ 60 tokens (§7a).

**Which tile is singled out:** only a tile the plan's `design_hint` names (next to "inverted /
highlight"). Nothing else singles one out: no headline matching (V3 dropped 2026-10-07, user: no
biases from examples). With no named tile, `inverted` is not offered and falls back to `plain`.

**Hero pill:** its text is `kpi_deltas[0]`, verbatim. With no delta there is no pill, and the
block never writes one.

**Code decides (not variants):** tiles per row (`per_row` from `capacity.yaml`, 2–5); rows of
equal tiles. There is **no tier concept**: a `kpi_row` is one entity's metrics in the brief's order
(neutral KPI rules, `86b20c1`), and the plan's `weight` only sizes its box. Which variants a KPI row is
offered depends only on its content (count, a named tile), never on its position or on an earlier
row (V4 and the 6+ → two tiers rule dropped 2026-10-07).

**Contrast pairs for the D1 test:** `panelInk` / `textMuted` on `panelFill`; `textMain` / `textMuted`
on `accentTint`; `onDark` and `accentOnDark` on `darkFill` (labels are 12 px, so 4.5:1);
`onAccent` on `accentSolid` (pill); tone inks on `panelFill` (§2).

## 5. Card grid (layouts `grid`, `matrix`)

Content: `cards[{title, tag, body, bullets}]`; a matrix also has `columns`, `rows`.
Card anatomy: tag label (or the numeral) → title → body or bullets.

| Variant | Cards | Emphasis | Requires → fallback |
|---|---|---|---|
| `outline` (default) | fill `surface`, 1 px `border`, title `textMain`, body `textMuted`, tag `accentInk` | none | — |
| `filled` | fill `panelFill`, no border, title `panelInk`, body `textMuted`, tag `accentInk` | none | — |
| `featured` | the card the design hint names is a **full-height left column** (≈ 40% of the slot width), fill `darkFill`, title `onDark`, body `onDark`, tag `accentOnDark`, title one step larger. The other cards are drawn as `filled` in a grid to its right | 1 card | ≥ 3 cards, the design hint names one, not a matrix → `filled` |
| `numerals` | as `outline`, with a large numeral (`01`, `02`, …) at the top of each card in `border` colour (faint), sized from the spare height (Phase 0b: up to 96 px). The tag moves under the numeral | none | not a matrix, titles not already numbered → `outline` |
| `toned` | each card tinted by its tone (`positiveTint` / `negativeTint` / `warningTint`), a 5 px left edge in the tone colour, the tag in the tone's ink (`positiveInk` …); cards with no tone are `panelFill` with a `border` edge | none | at least one toned card → `filled` |
| `accent_top` | `outline` cards with a 4 px `accent` top bar (pillars, workstreams). A singled-out card is drawn as the **contrast card**: `panelFill`, no border, top bar `textMain` (e.g. the brief's "Not doing") | optional | — |

(`toned` and `accent_top` added 2026-10-06 from the hand-written examples: status cards GROWTH /
WATCH / OUTLOOK, and pillar cards with one contrasting card. The examples' per-pillar colours are
not copied: one accent, so the palette stays the only colour source.)

**Matrix:** `outline` / `filled` only. Priority cells (user rule 2026-09-29: "every priority cell")
get `accentTint` in either variant. The row and column headers are labels.

**Code decides:** columns per row (`capacity.yaml` 2–4, the longest word must fit: `fit_columns`).
No orphan last row (7 → 4 + 3, 9 → 3 + 3 + 3). Cards with titles only (no body or bullets) become
a ruled list (title rows separated by `border` hairlines) in every variant. The shortlist line
"3 items → stacked rows" is read as: 3 cards in a slot narrower than half the slide are stacked one
per row (decision V5: confirm that reading).

**Contrast pairs:** `textMain`, `textMuted` and `accent` (12 px tag) on `surface`; `panelInk`,
`textMuted` and `accent` on `surfaceAlt`; `onDark` and `accentOnDark` on `darkFill`.

## 6. Card steps (layout `steps`, ≤ 5 steps; more becomes a grid, `capacity.yaml` `steps_max`)

The **destination** (last step) is singled out unless `design_hint` names another step. This is
the user rule from 2026-09-29.

| Variant | Drawing | Emphasis |
|---|---|---|
| `cards` (default) | one row of cards with a 3 px `accent` top border and an arrow between cards. Phase tag ("Phase 1", from the title prefix or `tag`) as the label. Destination card `darkFill` / `onDark`, top border `accentOnDark` | destination card |
| `rail` | a vertical line in `border` at the left of the slot, one dot per step (`accent`; destination dot filled larger), and tag + title + body to the right of each dot. Rows share the slot height. For 3–5 steps with long bodies in a tall or narrow slot | destination dot |
| `columns` | a segmented progress bar across the top (track `accentTint`, one segment per step; destination segment `accent`), with one column of text under each segment and no card fills. Each column carries its numeral, then title, then body | destination segment |

**Code decides:** when `cards` cannot fit the longest word at the 14 px body floor (narrow slot),
it re-flows to `rail` (`NODE_VARIANT_UNMET` with reason `reflow`). The rail grows to fill a tall
slot (the §5.4 underfill rule).

## 7. Who chooses the variant, and what it costs

**Choosing.** The split follows what each step can see:

| Step | Sees | Decides |
|---|---|---|
| slide component planner | the brief's meaning | content, `weight`, which item is singled out (`design_hint`), **tones** |
| generator LLM | the whole slide: neighbours, box sizes | node size and **`variant`**, from the component's line (only the variants that fit) |
| code (node pass) | the plan + the measured slot | checks `requires`, falls back, re-flows, colours tones |

The planner could pick the variant instead (zero generator tokens), but it decides before the
layout exists: `rail` vs `cards` depends on how tall the slot is, and `bare` on whether the LLM
put a dark band behind it. So the generator chooses, and the planner supplies the meaning.

**Where the text goes, and its size** (measured with the gpt-4.1 / gpt-5 tokenizer, o200k):

| Place | Text | Tokens |
|---|---|---|
| generator **system** prompt, fixed | the 5 node rules (§3.5 of the planning doc), incl. "choose by the slide's purpose and the slot's room" | ≈ 140 |
| generator **user** prompt, per component | `c2 · <KpiRow ref="c2"/> · 4 tiles, longest value 7 chars · weight hero · variants: plain = light tiles…; inverted = …` — only the variants whose `requires` hold, each with its ≤ 12-word phrase from `block-variants.yaml` | 40–90 per component; a 2–3-component slide 170–180 (names only: 60–75) |
| generator, removed | the recipe of each kind that gets a node (kpi_row 614, card_grid 989, card_steps 649, hero_stat 551 tokens) | −550 to −990 per kind |
| slide component planner prompt | the tones rule + schema line | ≈ 60 |
| not sent | the look (this doc), fallbacks, checks | 0: code only |

Net for a slide with a KPI row and a card grid: about +310 for node rules and variant lines, −1,600 for
recipes, so **≈ −1,300 tokens** against today's 8–13k generator prompt. The whole catalogue of all
ten blocks would be ≈ 420 tokens if it were put in the system prompt instead. The per-component lines
are used because they show only what fits that component, so the LLM picks from 3–6 names instead of 40.

**Output side (node form, measured 2026-10-06 on 64 generator slides from 5 saved runs):** the generator
writes ≈ 1,830 tokens per slide; ≈ 22% is native-node content (Table, Chart, Timeline, Ul …) and up to
≈ 45% hand-built KPI / card rows (pattern match, an upper bound). A ref node replaces each with ≈ 15
tokens, so output falls ≈ 50–67% (≈ 600–900 per slide), and with it most of the generation time.

More variants later cost only on the components where they apply. The limit to watch is choice quality,
not tokens: 1a reports the default share and the fallback rate per check (below).

## 7c. Edge cases and capacity (2026-10-07)

Scope: Latin-script text only (user, 2026-10-07), so font coverage beyond Inter / JetBrains Mono is
out of scope.

### Capacity rules that change the plan (`enforce_capacity`, `src/agents/capacity.py`)

They run inside the slide component planner (`slide_component_planner.py`, before the plan is
saved), so a component's prompt line, its tag and its offered variants always come from the plan
**after** these rules. Each change is noted in `SlidePlan.capacity_fixes`.

| Rule (limit in `capacity.yaml`) | Code does | Tag the LLM then writes | Variant consequence |
|---|---|---|---|
| `process_arrow` > 5 steps, or a label > 2 words | → `card_grid`, `steps` if ≤ 5 cards else `grid` | `CardGrid` | ProcessArrow variants gone; steps without detail are title-only cards (ruled list) |
| `timeline` > 5 items | → `card_grid` (grid), dates as card tags | `CardGrid` | **Conflict:** Timeline `vertical` could hold 6–8 items but is pre-empted (V13) |
| `flow` > 6 steps | reported only, stays a flow | `Flow` | crowded native flow; `step_cards` would suit but nothing steers to it |
| `table`: 2 columns, ≥ 3 rows, mixed units (one entity's metrics) | → `kpi_row` in the table's order, its weight and design hint kept; `per_row` if > 5 | `KpiRow` | no deltas / directions / tones: `toned` and notes absent; `inverted` only if the hint names a row (it becomes the tile) |
| `card_grid` matrix whose cells only repeat row / column names | → `grid`, one card per row | `CardGrid` | matrix limits lifted; `featured` / `numerals` possible |
| `card_grid` steps > 5 | → `grid` | `CardGrid` | step variants replaced by grid variants |
| every `card_grid` grid | writes `per_row` (7 → 4 + 3, 9 → 3 + 3 + 3) | `CardGrid` | **`featured`** draws one card apart: the block recomputes `per_row` for the other n − 1 |

**Stated in `capacity.yaml` but only in the prompt (not enforced):**
- **`kpi_row.per_row` 2–5:** written only by the table → KPI switch, so the block computes rows itself.
- **`table.max_rows` 10 / `max_cols` 8:** spill past 10 rows is an open issue, and variants don't change it.
- **`bullet_list.two_columns_from` 6:** becomes a code decision. At 6+ points the Ul draws two columns whatever the variant (V14).
- **`chart.min_points` 3:** a 2-point chart can reach the node.
- **`timeline.max_label_words` 3:** becomes a size fallback, `rail` → `vertical` / `cards` (below).
- **`matrix.items` 3–4, `pyramid.items` 3–5:** native drawing limits.
- **`card_grid.items` 2–12:** covered by the size fallbacks.

**No capacity at all:** `tree` (depth / width), `narrative` / `caption` length, card body length.
Only measuring after layout guards them (`NODE_OVERFULL`).

### Edge cases and readiness

| Area | Case | Ready? | Handling |
|---|---|---|---|
| Content | KPI values that don't split into number + unit: `-12%`, `¥42.8B`, `3.07×`, `$1.2M–$1.5M`, `N/A`. Tested 2026-10-07: `render.py` `_NUM` matches 5 of 18 common values; the gallery's split cut `2.4x faster` into `2.4x faste` + `r` | **No** | One shared value parser (V15): optional sign / approx (`+ - − ~ < > ≈`), optional currency (`₹ $ € £ ¥`), digits with `,` `.`, optional space, unit `%`, `x`, `×` or 1–3 letters. No full match → the whole value drawn as one run. A row whose values do not all split draws every tile without unit spans, so the row stays consistent. Checked on the 18 values: all split or stay whole as intended; `18 Sep` gives `18` + a small `Sep` (accepted for dates) |
| Content | empty plan, 1 tile, 12 cards, 7 cards, missing deltas | yes | `NODE_EMPTY_PLAN`, `per_row`, variant `requires`, blank note |
| Content | very long labels / titles | partly | blocks re-flow, never reword; `NODE_OVERFULL` → checking loop (step 2) |
| Variant meaning | `labelled` / `horizontal` on a pie, doughnut, line, area or radar chart | **fixed in this draft** | `requires: [chart_is_bar]` → `native` |
| Variant meaning | `toned` before the planner writes tones | yes | not offered (`has_tones`) until V10 lands |
| Variant meaning | a tone judged wrong (is "spend +42%" good or bad?) | partly | planner leaves `""` when the brief doesn't say. Tones are **inferred** content (§12), so they belong in the review screen with Keep / Remove (V16) |
| Variant meaning | the hint names an item loosely ("the ROAS row") | partly | substring match as today; ambiguous → nothing singled out, variant falls back |
| Box size | a variant that doesn't fit the box the LLM gave it: `featured` in a half-width box, `hero` in a short box, `bare` with 5 values in a narrow box, `rail` timeline with long labels, step `cards` in a narrow box | **No (biggest gap)** | each block variant gets a minimum box, checked in the node pass's second layout pass; below it → next variant in the fallback chain, `NODE_VARIANT_UNMET` reason `box`. Minimums are measured in step 1 (free renders), not guessed |
| Context | `bare` on a band, gradient or image the LLM drew | partly | the block reads the nearest ancestor `backgroundColor` and picks `onDark` or `textMain` by contrast; a gradient / image → its first stop, else `surface`, plus the `LOW_CONTRAST` report |
| Context | two nodes of the same kind on one slide with different variants (one KPI row `filled`, the other `inverted`) | **No** | report `NODE_VARIANT_MIXED` (informational) in 1a; decide from its rate whether siblings must share |
| Context | emphasis on dark palettes | open | V7 |
| Context | the same variant on every slide | measured | within-deck variety (D2); not controlled |
| Lifecycle | a user edits a node in the UI | **No** | node content is the plan's: edits change the plan and re-draw (gate 3 of §5.3 in the planning doc, step 2) |
| Lifecycle | capacity changes a component's kind | yes | prompt line rendered after `enforce_capacity` (above) |
| Lifecycle | POM native limits (timeline labels collide, diagrams never scale up) | known | unchanged by variants; size fallbacks to block variants help |
| LLM | unknown variant, content inside a node, hand-built content | yes | `NODE_*` codes; 1a measures the rates |

## 7d. Validator and prompt

- **`variant` is not a POM attribute** (verified 2026-10-06: `<VStack variant="…" />` fails with
  `UNKNOWN_ATTRIBUTE`). This removed the slot form's one advantage and led to the node form (D10):
  the node pass always strips `ref` / `variant` and replaces derived tags, expanded or not.

- **Prompt line:** list only the variants whose `requires` hold for that component, default first.
  For example, a 4-tile KPI row with nothing singled out gets `variants: plain|filled`, and a
  1-value row gets `plain|filled|hero`. Fewer wrong picks, same validator.
- **Warning `NODE_VARIANT_UNMET`:** the variant's requires failed (or the block re-flowed), so
  the fallback was used. It records the failed check (in the §3.6 code table of the planning doc).
- **Test (step 1):** every variant named in a prompt template, pack `default_variants` or recipe
  exists in `block-variants.yaml`; every `fallback` names a variant of the same block; every check
  name is implemented; the contrast pairs above pass for all 16 palettes.
- **1a counts:** the variant chosen per node, the rate of fallback by check, and the share of
  defaults (an LLM that always omits `variant` gets no variety; see the D2 variety metric).

Gallery deck of every KPI / card variant: `python -m scripts.variant_gallery [--palette <name>]`
→ `output/variant-gallery/` (fixed sizes; the blocks will measure).

## 8. Decisions for the user

| # | Question | Recommendation |
|---|---|---|
| V1 | Add derived token `accentTint` | yes |
| V2 | Number cap 96 px for non-hero tiles, 120 px for hero | yes (otherwise a 2-tile row looks like two heroes) |
| V3 | ~~Single out the KPI tile the headline names when the hint names none~~ | **dropped 2026-10-07 (user): no biases from examples; only the design hint singles out** |
| V4 | ~~Supporting KPI tier offered `plain` / `filled` only~~ | **dropped 2026-10-07 (user): the plan has no tiers; variants depend only on content** |
| V5 | "3 items → stacked rows" means only in a slot narrower than half the slide | confirm |
| V6 | Packs lose `fills` / `card_border` / `ghost_numerals`, gain `default_variants`; studio's fill rhythm dropped | yes |
| V8 | Derived token `panelFill`: `surfaceAlt` when it shows against the slide, else `surface` stepped 6% toward `textMain`. Found in the gallery: on corporate-slate `surfaceAlt` is white on `F7F9FC`, so `plain` tiles and `filled` cards were invisible. Used by `plain` KPI, `filled` cards and the other cards beside `featured` (in place of `surfaceAlt`) | yes |
| V9 | Derived tone tokens `positiveTint` / `negativeTint` / `warningTint` (tone mixed 90% toward `surface`) and `positiveInk` / … (the tone, darkened until 4.5:1 on its tint), for `toned` cards and tone-coloured notes | yes |
| V10 | Planner writes `kpi_tones` / card `tone` (good / bad / watch / ""), separate from `kpi_directions`. The planner schema and prompt are being edited in another session; add after it lands | yes |
| V11 | The generator chooses `variant` from a filtered per-slot list; the planner supplies tones and emphasis only | yes |
| V12 | Role colours `accentInk` (accent as small text) and `accentSolid` (accent fill under text), and the corrected derivation in §2 (checked on all 18 palettes) | yes |
| V13 | `timeline` > 5 items: report instead of switching to cards; the node pass measures and falls back `rail` → `vertical` → `cards` | **yes** (the node form can measure the box; today's switch pre-empts `vertical`) |
| V14 | Bullets at 6+ points draw two columns in code, whatever the variant (`two_columns_from` enforced) | yes |
| V15 | One shared KPI value parser (rule in §7c) used by the blocks, the composer and fit-grow's unit spans | yes |
| V16 | Tones are inferred content: shown in the review screen with Keep / Remove, like written card lines | yes |
| V7 | Dark palettes: `darkFill` is only a step lighter than `surface`, so an inverted tile barely stands out. Use `accent` fill + `onAccent` for emphasis on dark palettes instead | yes; check on the label-test deck |
