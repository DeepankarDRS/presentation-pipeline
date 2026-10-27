# Style or composition? A free check on the variant split (2026-10-27)

This test cost nothing: no LLM calls and no pipeline changes. It ran on one palette, corporate-slate.
Script: `python -m scripts.composition_test q1` / `q2` (`scripts/composition_test.py`). Renders go to
`output/composition-test/`. The sheets and `metrics.json` are in this folder.

The split under test has not been confirmed by the user:
- **slide layout:** the generator decides it.
- **variant:** a different composition of one component's parts, drawn by code.
- **style:** free dot-name attributes, as in base POM.

## Q1. Can today's style variants be written as attributes alone?

**Method.** Each style variant is drawn twice through the card gallery's code path. That path is
`card_gallery.compile_one`: `tiles.fill` → `cards.expand` / `tiles.expand` → normalize → `compile-pom.js` with
fit-grow → Inter render.
- **A** uses `variant="<name>"`, exactly as `tile_gallery.variant_body` / `card_gallery.variant_body` write it.
- **B** uses no variant name. It writes the same look as `<Kpi>` / `<Card>` box and part attributes:
  - The values are the variant's `look` from `block-variants.yaml`, with `{role}` filled per item from the plan
    tone and the variant's `with_tone` applied.
  - Resets undo the default look underneath (`plain` for KPI, `lifted` for cards), because attributes can only
    override, never remove. The reset values are `backgroundColor="$surface"`, `border.width="0"`,
    `shadow.opacity="0"`, or the house-look value.

Plans: the tile gallery's QBR (4 KPIs with tones) and the card gallery's MOMENTS (5 cards, 2 toned, focus card 4).

Sheets: [q1-kpi.png](q1-kpi.png) and [q1-card.png](q1-card.png). In each pair, the left shot is `variant=` and the right shot is attributes only.

| Variant | Block | Style or composition | As attributes? | Pixel diff A vs B | Style attributes needed |
|---|---|---|---|---|---|
| `plain` | KPI | style (the default look) | — (base) | — | 0 |
| `filled` | KPI | style | **yes** | 0.0% | 8 |
| `toned` | KPI | style | **yes** | 0.0% | 9 |
| `bar` | KPI | style | **yes** | 0.0% | 18 |
| `dot` | KPI | style (+ a marker part) | **yes**: `marker.shapeType/w/h/fill.color` draws the dot | 0.0% | 34 |
| `bare` | KPI | style | **yes**: tiles identical (95 px numbers); see note 1 | 5.7% | 17 |
| `inverted` | KPI | style + an emphasis rule | **look yes** (0.0%). The rule "only on the plan's emphasis item" is lost | 0.0% | 6 |
| `divided` | KPI | **composition** (group box + dividers + no regrid) | **no**: see note 2 | 6.3% | 27 |
| `lifted` | card | style (the default look) | — (base) | — | 0 |
| `column` | card | style | **yes** | 0.0% | 28 |
| `filled` | card | style | **yes** | 0.0% | 20 |
| `outline` | card | style | **yes** | 0.0% | 17 |
| `toned` | card | style | **yes**: icon colour on untoned cards differs, see note 3 | 0.1% | 32 |
| `accent_top` | card | style | **yes** | 0.0% | 24 |
| `inverted` | card | style + an emphasis rule | look yes (code applies it to the focus card in both A and B). The rule is code's | — | — |
| `numerals` | card | **composition** (adds a `number` part) | **no**: `number.*` only colours a number that the variant creates | not drawn | — |
| `arrange` label-first / value-first / icon-top / side / inline (KPI) | KPI | **composition** | no: part order and tile direction | — | — |
| `layout` row / grid / column (KPI) | KPI | **composition** | no (already a group attribute, not a variant) | — | — |
| `arrange` stack / side (card) | card | **composition** | no | — | — |
| `layout` grid / steps / rail (card) | card | **composition** | no (arrows, rail line and numbers are drawn by code) | — | — |

**Notes**
1. **`bare`.** The tiles render identically. The 5.7% difference is fit-grow growing the slide's kicker
   from 14 to 24 px in A only. In B, the reset attributes (`backgroundColor`, `border.width="0"`) leave each tile
   with a box, so fit-grow treats the tiles differently. So a reset attribute is not the same as having no
   attribute.
2. **`divided`.** The group box (`backgroundColor` / `border` / `padding` on `<KpiGrid>`) and the hairlines
   (`borderLeft.*` + `padding.left` on each `<Kpi>` after the first) can all be written. But B still carries the
   `kpig-` id, so fit-grow regridded the 4-tile strip into 2 × 2. A divided row stays one row, and no attribute
   asks for that. On top of that, the dividers depend on position ("every tile after the first in its row"), and
   an attribute written per item cannot follow a regrid.
3. **Card `toned`.** `build_card` gives untoned cards the role `neutral` under `toned`, so their icon becomes
   `$textMain`. B keeps `$accentText`. One more per-item `icon.color` would close the gap.

**What attributes cannot express** (these hold even where the pixels match):
- **`with_tone` / `with_color`.** One `variant="bar"` on the group becomes a different colour per item, taken
  from the plan's tones. As attributes, every colour must be written on every `<Kpi>` / `<Card>`. Group
  attributes are the group's own box (user, 2026-10-26: no cascade), and `${role}` is not an attribute value the
  LLM can write. That is why `dot` needs 34 attributes and card `toned` needs 32, against 1 variant name. The
  plan-driven default (a bad / watch tile tinted with no attribute at all) has no attribute form. It is the
  base look's behaviour.
- **Emphasis rules.** Today `inverted` and `size="hero"` are allowed only on the plan's emphasis item, and the
  card focus is dark automatically. As attributes, any item can be made dark.
- **Undoing the default look.** Attributes only add or override. Turning `plain` / `lifted` into another look
  needs resets, and `bare` shows that resets are not neutral for fit-grow.
- **Parts that only a variant creates.** These are `numerals`' number Text and `divided`'s group box with
  dividers that are aware of rows. `dot`'s marker is **not** one of them: `marker.*` attributes draw it.
- **Fit decisions.** `divided`'s "stays one row" and the `kpig-` / `cardg-` regrid ids are code choices that no
  attribute reaches.

### What would change in the galleries and expanders

| File / function | Change | Kind |
|---|---|---|
| `src/knowledge/core/block-variants.yaml` `tile_nodes.kpi.variants` / `card.variants` | Move `filled toned bar dot bare inverted` (KPI) and `column filled outline toned accent_top inverted` (cards) to a `styles:` list. Keep them as named attribute bundles, or drop the names. Under `variants:` keep only compositions: KPI `divided` (+ arrange), cards `numerals` (+ arrange / layout). | **regrouping** |
| `tiles.build_tile`, `tiles._variant`, `cards.build_card`, `cards._variant` | Today `variant=` picks a look and `with_tone`. Under the split, a style bundle becomes a layer of attributes, applied before the LLM's own attributes. The composition decides which parts and which container to build (today: `arrange`, the numerals branch in `build_card`, `divided` in `build_group`). The tone defaults (`with_tone`) must live somewhere other than a style name: either the base look, or a `tone:` block per style. | **new code** (small): a `styles` layer + a `tone` default |
| `tiles.hint_looks` / `plan_checks.look_from_hint` | Hint cues that map to style names (bars, dots, dark tiles) map to style bundles instead. | rename |
| `tiles.build_group` (`divided`) | Already a composition. A future `KpiGrid variant="strip"` could keep this code as it is. | rename |
| `tiles.node_lines`, `cards.node_lines`, `variants_for`, `prompt_line` | The prompt lists compositions under `variant:` and styles as attribute recipes (like `treatments` today). | regrouping |
| `scripts/tile_gallery.py` `build` / `variant_body` | Loops `variants × arranges`. It would loop compositions (`arrange × layout × divided`), plus one style row through `styles`. | regrouping |
| `scripts/card_gallery.py` `VARIANTS` / `variant_body` / `LAYOUTS` | `VARIANTS` becomes the style row. `LAYOUTS` already holds the compositions (steps, rail, side, numerals). | regrouping |
| `scripts/kpi_gallery.py` | **No change.** It is the 2026-10-11 hand-written element-ref pilot (`POM_BLOCKS=kpi`), with no `variant` anywhere. Its `sheet()` is shared and stays. | none |

**Q1 verdict.** 10 of 12 style variants render pixel-identical from attributes alone, and the other two differ
only through fit-grow side effects. So the style variants **are** expressible, and the galleries need
regrouping, not new drawing code. The cost moves elsewhere: the LLM would write 6–34 attributes per group
instead of one name, and the tone-driven colours, emphasis rules and default look need a home that is not a
variant name.

## Q2. Do composition variants look more different than style variants?

**Method.** I hand-wrote the 8 Perceptis compositions as the XML a node would expand to, from sample
components that `content_from_data` validates against today's typed schema. Bento goes through the real card code
(`<Card ref>` placed apart + `<CardGrid ref>`). Each composition is drawn with two stylings: **accent**
(`$accent` / `$accentSoft`) and **dark** (`$panelDark` / `$surfaceAlt`). The first row of each sheet shows today's
style variants of the same block.

- [q2-table.png](q2-table.png): table `plain` / `zebra` / `dark_header` (today) | `numbered_rows`, `icon_header`, `chevron_rows`, `titled`
- [q2-cards.png](q2-cards.png): cards `lifted` / `filled` / `inverted` (today) | `columns`, `title_bar`, `bento`
- [q2-slide.png](q2-slide.png): bullet_list `plain`, callout `tinted` / `dark` (today) | bullets `boxed` + callout `icon_panel`

**What the sheets show**
- **Table.** `plain`, `zebra` and `dark_header` read as the same slide: a small grid with a different header
  shade (pixel diff plain vs zebra 0.4%). Each composition is a different slide at a glance: squares with
  numbers, an icon band, chevron arrows, a banner. Switching a composition between accent and dark changes
  less than switching to another composition. `numbered_rows` accent vs dark is 1.7%; `chevron_rows` 9.4%, mostly
  the fill of the dark label pills.
- **Cards.** `lifted` and `filled` are hard to tell apart (5.9%). `inverted` adds one dark card. `columns` (pill
  plus item boxes), `title_bar` (dark bands) and `bento` (one tall focus block beside a 3-up or 2 + 1 group)
  each change the reading order and how the content is grouped.
- **Slide.** The boxed points with the icon callout beside a table are a different slide from a plain list or a
  tinted panel. But that comes from several components placed together, which is slide layout.

**Pixel metric.** `metrics.json` holds the share of pixels that differ visibly. It weighs large dark fills
heavily, so a restyled dark header can score as high as a new composition (table dark_header 7.0% vs
numbered_rows 7.6%; callout dark vs tinted 37.8%). It does not measure structure. The verdict comes from the
sheets.

**Q2 verdict: yes.** Composition variants differ visibly much more than style variants. Two stylings of
one composition look like one design in two colours. Two of today's style variants of one block look like
the same slide. The user's reading is borne out by the renders.

### Data each composition needs

| # | Composition | Block | In today's plan? | Missing / note |
|---|---|---|---|---|
| 1 | `numbered_rows` | table | yes | The numbers are derived (01–04, computed by code). The first column becomes the row title. Drawn as boxes, not a native `Table` (gaps between cells, filled squares). |
| 2 | `icon_header` | table | partly | **One icon per column**: no plan field (`TableContent` has columns and rows only). The LLM picks them, as for bullet icons today. Boxes, because `<Td>` cannot hold an `Icon`. |
| 3 | `chevron_rows` | table | partly | **One icon per row**: no plan field. Chevron / homePlate `Shape`s with text fix the row height (96 px). Long cells shrink to 18 px (no wrap control). |
| 4 | `titled` | table | **no** | **A table title**: `TableContent` has no title. It needs a field, or the slide's title / caption component, and then it is slide layout. A native `Table` under a banner box works. |
| 5 | `columns` | cards | yes | Card `title` → the pill, `bullets` → the item boxes, `icon` from the card. It needs bullets on every card. Not drawable by `cards.py` today (its bullets are a `Ul`). |
| 6 | `title_bar` | cards | yes | Title + icon in the dark bar, bullets below. Not drawable by `cards.py` today (its title is a Text, not a band). |
| 7 | `bento` | cards | partly | `focus_card` gives the big block, and **today's code already draws it**: `<Card ref>` placed apart + `<CardGrid cols>`. A Perceptis bento (blocks spanning 2 rows or 2 columns) needs **a span per card**, which the plan lacks. |
| 8 | bullets `boxed` + callout `icon_panel` | bullets + callout + narrative + table | partly | **Slide layout**, not one component: 4 components (narrative, bullet_list, narrative as a callout, table). `boxed` alone is a bullet_list composition (each point in a box, from the plan's bullets). `icon_panel` needs **an icon for the narrative**: no plan field. |

So: compositions 1, 5 and 6 need nothing new; 2 and 3 need per-column or per-row icons (the LLM's, or a new plan field);
4 needs a table title; 7 needs a span per card for true bento; 8 is slide layout plus a callout icon.

### Render findings worth carrying forward
- **fit-grow and hand-built rows.** When a composition is built from hand-written Text with no peer ids, fit-grow
  grows only some rows: in `numbered_rows`, fit-grow grew row 1 to 40–48 px while rows 2–4 stayed at the
  written 20–22 px (`fitted.xml`). In `title_bar`, the two rows of blocks also differ in size. A composition node must give its rows the peer ids
  (`refGroups`) that tiles and cards use today, so that every row shares one size.
- **Small native tables.** `titled`, and today's table variants, draw the native `Table` at its small default
  size in a tall band. The table fill pass from `left_blocks_gallery` applies to both equally.

## Reproduce

```bash
python -m scripts.composition_test q1
```

```bash
python -m scripts.composition_test q2
```

Each run takes about 4–6 minutes on the build PC. Slides render one at a time.
