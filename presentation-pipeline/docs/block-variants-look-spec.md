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
| **Block code** (fit) | number / title / body size, columns per row, rows, tiers, re-flow, fallback variant | wording |

**Change to the packs (proposal):** the pack options `fills`, `card_border` and `ghost_numerals`
overlap with variants, so they are replaced by one entry per pack,
`default_variants: {kpi_row: plain, card_grid: outline, card_steps: cards}`. A slot's `variant`
overrides that entry. `studio` becomes `{card_grid: outline, card_steps: cards}` + `italic_last`
titles. Its "fills rhythm" (every 4th card dark, one lime) is dropped, because it singled out cards
that the brief never named (§12 content policy, user highlight rule 2026-09-29).

## 2. Tokens

Palette tokens: `surface`, `surfaceAlt`, `accent`, `textMain`, `textMuted`, `border`, `positive`,
`negative`, `warning`. Derived by code (D1): `panelInk`, `darkFill`, `onDark`, `onAccent`,
`accentOnDark`.

**One new derived token is needed:** `accentTint` = `accent` mixed 88% toward `surface`, darkened in
steps until `textMain` reaches 4.5:1 and `textMuted` reaches 4.5:1 on it. It is used by `filled` KPI
tiles and the `columns` progress bar track. → Add it to the D1 list (decision V1).

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
| `plain` (default) | fill `surfaceAlt`, label `textMuted`, number `textMain`, no border | none | — |
| `filled` | fill `accentTint`, label `textMuted`, number `textMain`, no border | none | — |
| `inverted` | as `plain`; the singled-out tile is `darkFill`, label `accentOnDark`, number and note `onDark` | 1 tile | ≥ 3 tiles and one singled out → `plain` |
| `hero` | one tile, `darkFill`; label `accentOnDark`; number up to 120 px `onDark`; the note as a **pill** (rounded rect, fill `accent`, text `onAccent`, 12–14 px), placed under the number | the tile itself | exactly 1 value → `inverted` |
| `bare` | no tiles: number over label, spaced across the slot, on whatever the slot sits on (slide background or a panel / dark band the LLM drew). On `darkFill`: number `onDark`, label `accentOnDark` | none | — (added 2026-10-06, from the hand-written examples: a supporting row, a cover / closing band) |

### 4a. Tones (added 2026-10-06)

`kpi_directions` (up / down) says which way a number moved, not whether that is good: churn going
down is good news. The slide component planner therefore writes a second field,
`kpi_tones: ["good" | "bad" | "watch" | "", …]` (cards: `tone` per card), from what the number
means for the audience. `""` when the brief does not say. Code maps good → `positive`, bad →
`negative`, watch → `warning`. In **every** KPI variant the note line takes the tone colour, and
code puts ▲ / ▼ in front of it from `kpi_directions` (derived, not content). The number stays ink.
A tone is never written as a word on the slide. Planner prompt cost: ≈ 60 tokens (§7a).

**Which tile is singled out:** a `design_hint` that names a tile next to "inverted / highlight"
wins. Otherwise use the tile whose value or label the slide headline contains, and only when exactly
one tile matches. If neither applies, nothing is singled out and `inverted` falls back to `plain`.
The headline rule is new (decision V3). The brief's key message already puts that number in the
headline, so this is copied emphasis, not invented emphasis.

**Hero pill:** its text is `kpi_deltas[0]`, verbatim. With no delta there is no pill, and the
block never writes one.

**Code decides (not variants):** tiles per row from `capacity.yaml` (2–5). Six or more metrics
become two `kpi_row` components in the plan (hero tier + supporting tier), each with its own slot
and its own variant. Recommended pairing: `hero` or `inverted` on the hero tier, `plain` on the
supporting tier. The prompt line says so: the supporting tier lists only `plain | filled`
(decision V4).

**Contrast pairs for the D1 test:** `textMain`/`textMuted` on `surfaceAlt`; `textMain`/`textMuted`
on `accentTint`; `onDark` and `accentOnDark` on `darkFill` (labels are 12 px, so 4.5:1);
`onAccent` on `accent` (pill).

## 5. Card grid (layouts `grid`, `matrix`)

Content: `cards[{title, tag, body, bullets}]`; a matrix also has `columns`, `rows`.
Card anatomy: tag label (or the numeral) → title → body or bullets.

| Variant | Cards | Emphasis | Requires → fallback |
|---|---|---|---|
| `outline` (default) | fill `surface`, 1 px `border`, title `textMain`, body `textMuted`, tag `accent` | none | — |
| `filled` | fill `surfaceAlt`, no border, title `panelInk`, body `textMuted`, tag `accent` | none | — |
| `featured` | the singled-out card is a **full-height left column** (≈ 40% of the slot width), fill `darkFill`, title `onDark`, body `onDark`, tag `accentOnDark`, title one step larger. The other cards are drawn as `filled` in a grid to its right | 1 card | ≥ 3 cards, one singled out, not a matrix → `filled` |
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

## 7b. Validator and prompt

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
| V3 | Single out the KPI tile the headline names when the hint names none | yes |
| V4 | Supporting KPI tier offered `plain` / `filled` only | yes |
| V5 | "3 items → stacked rows" means only in a slot narrower than half the slide | confirm |
| V6 | Packs lose `fills` / `card_border` / `ghost_numerals`, gain `default_variants`; studio's fill rhythm dropped | yes |
| V8 | Derived token `panelFill`: `surfaceAlt` when it shows against the slide, else `surface` stepped 6% toward `textMain`. Found in the gallery: on corporate-slate `surfaceAlt` is white on `F7F9FC`, so `plain` tiles and `filled` cards were invisible. Used by `plain` KPI, `filled` cards and the other cards beside `featured` (in place of `surfaceAlt`) | yes |
| V9 | Derived tone tokens `positiveTint` / `negativeTint` / `warningTint` (tone mixed 90% toward `surface`) and `positiveInk` / … (the tone, darkened until 4.5:1 on its tint), for `toned` cards and tone-coloured notes | yes |
| V10 | Planner writes `kpi_tones` / card `tone` (good / bad / watch / ""), separate from `kpi_directions`. The planner schema and prompt are being edited in another session; add after it lands | yes |
| V11 | The generator chooses `variant` from a filtered per-slot list; the planner supplies tones and emphasis only | yes |
| V7 | Dark palettes: `darkFill` is only a step lighter than `surface`, so an inverted tile barely stands out. Use `accent` fill + `onAccent` for emphasis on dark palettes instead | yes; check on the label-test deck |
