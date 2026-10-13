# KPI tile nodes: wide free evaluation (2026-10-13, build PC, no API)

The three paid checks judged `POM_BLOCKS=tiles` on the same 3 KPI slides (QBR, CHEFFIN 1, CHEFFIN 4). The user
asked for wider evidence before any further fix. This replay takes **every saved KPI slide** on the build PC and
compares the two routes on each; a scan of every saved compiled slide counts the `w="max"` squeeze.

    python -m scripts.tile_wide                               # 68 slides, both routes, renders -> output/tile-wide/
    python -m scripts.tile_wide --squeeze                     # the w="max" squeeze over every saved compiled slide
    python -m scripts.tile_wide --no-render --look padding=16 gap=6 --out output/tile-wide-look16   # look experiment

## What was compared

- **Slides:** 68 distinct slides with a `kpi_row` plan and XML (one per distinct XML), 83 `kpi_row`s, 317 values.
  17 are `tile_replay`'s (the paid checks' element-ref slides and the two decks runs). The other 51 come from every
  other saved run: r2 (old gj-h1 ×3 runs, xtsy ×3, 1b306e: 21), eval / step0 (9), old_zips gj-h1 (7), q1008 (6),
  critic-on / -on2 (6), colour-roles (1), run-1008 (1). The paid checks' own tile outputs are left out (the same 3
  slides, judged there). That is roughly 20 distinct brief slides in about 65 generations: much wider than 3, but
  the QBR / CHEFFIN / gj-h1 cases still dominate. None of the 83 plans has `kpi_tones` (all were written before
  `27b7aae`).
- **Arms:** A = today's default route (element refs: the LLM's own tiles, the plan's texts filled by
  `fill_refs`). B = tiles: `tile_replay.rewrite` turns the LLM's hand-drawn tiles into `<KpiGrid>` / `<Kpi>` tags
  with the look it drew (variant, colour, icon, arrangement, grouping), then `tiles.fill`. Both are normalized and
  compiled (fit-grow) with the run's theme, then rendered in LibreOffice and scored with `kpi_replay.score`.
- **Limit:** B is what tiles would draw **if the LLM asked for the same look**. Whether an LLM writing tile tags
  asks for that look (colour especially) cannot be replayed; for that the real tile first tries of the paid checks
  are counted below (20 distinct first tries).

## Fixed on the way (replay tool, not the product)

- `tile_replay._box` kept only attributes whose value starts with `$`, so every rewritten `<KpiGrid>` lost the
  LLM's `grow` / `w` / `h` / `gap`. One slide's KPI row lost `grow="3"` and its numbers stayed at 28 px (A: 92).
  Now only literal colours are dropped. **The earlier 17-slide `tile_replay` results under-drew tiles** wherever
  the LLM's row carried a size (re-run the replay before quoting its numbers again).
- Saved slides have no `<Theme>`: the run's manifest theme is used, else the run's saved `theme.xml` (r2) with
  today's derived tokens added (`upgrade_theme`; without them 8 old slides failed on tiles only, on `$accentText`),
  else the case file's theme, else corporate-slate.

## Results (68 slides; `summary.md` per slide)

| | A element refs | B tiles (house look today) | B tiles, padding 16 / gap 6 (experiment) |
|---|---|---|---|
| compiled | 68 | 67 (1 = rewrite artifact, below) | 68 |
| `w="max"` squeeze | 0 | 0 | 0 |
| broken words (rendered) | 13 | 16 (+3 on one old gj-h1 slide) | not rendered |
| `WORD_TOO_WIDE` | 27 | 24 | 24 |
| `GEOM_CARD_EMPTY` | 59 | **88** | **70** |
| `LOW_CONTRAST` | 24 | 22 | 22 |
| values off plan | 1 | 1 | 1 |
| number size, mean px | 48.1 | 46.9 | 49.5 |
| slides where B's numbers are larger / equal / smaller than A's | | 12 / 26 / **29** | **27** / 27 / 14 |
| KPI output tokens (hand-written XML vs tags) | 35,840 | 8,137 (−77%) | |

- **Tiles hold up on accuracy and robustness.** 313 / 317 values map to refs (4 were merged into longer texts by
  the old LLM), 0 off-plan values beyond the one A also has, no squeeze, contrast slightly better. The one B
  failure (`step0 … cheffin-full-s4`, `addTextBox: height`) is the rewrite's: the LLM drew five unboxed tiles inside
  one panel, and the rewrite read the panel as one tile column. It compiles with the padding experiment.
- **Tile numbers come out smaller and cards emptier, and the house look is the reason.** The LLM's hand tiles use
  padding 16 and gap 6 at the median (206 tiles: padding 16 ×57, 18 ×48, 14 ×41, 20 ×37; gap 6 ×86, 8 ×74; 190 of
  206 `w="max"`). The tile house look is padding 22 / gap 10 (the 2026-10-11 gallery tile, drawn with room to
  spare). On full slides that costs each tile 12 px of width and 8 px of height, so fit-grow stops earlier. With
  16 / 6 tiles are larger than the hand route on 27 slides and smaller on 14 (was 12 / 29), the empty cards drop
  88 → 70, and the paid-check slides improve too (QBR 83 → 95 px, hand 91; CHEFFIN 1 65 → 74, hand 71). Four
  slides gain one `GEOM_CARD_EMPTY` each; none gets smaller numbers. Renders: `sample-01.png` (the four slides
  where tiles did worst, today's look) vs `sample-03-padding16.png` (same four, 16 / 6).
- **Labels:** sizes match (mean 18.0 vs 17.8 px, none under 14; B smaller on 11 slides, larger on 6).
- **Values that are phrases** ("₹2.71 Cr (6.1% GMV)", "₹0.59 L / 9.13x / 11.0%", sentences): 28 of 317 values on
  10 slides, all from old plans. Both routes grow them as numbers (`sample-02.png`, first pair: tiles wrap them to
  three lines). The plan check `KPI_VALUE_TEXT` already re-asks for sentences; compound values are not checked.
  This affects both routes, so it is not a tile question.

## Colour

**What the LLM drew by hand (A, 82 `kpi_row`s, no plan tones anywhere):** it coloured 74 of 82 (90%): semantic
($positive / $negative / $warning) on 67, accent on most of the rest. Neither arm drew any colour on 6 rows, and on
5 of those the hint asked for colour. B carries A's colours (74 → 75: one lost, two gained by `with_color: toned`).

**What the LLM asks for when it writes tile tags** (the paid checks' real first tries, 20 distinct): colour on
**10 of 20**, semantic on 7. QBR asked for no colour in 6 of 6 tries (paid 1, paid 2 ×2, paid 3 ×3; paid 3's
colour came from the plan's tones). CHEFFIN 4 asked in 3 of 7 (paid 2 only). CHEFFIN 1 asked in 7 of 7. The tile prompt
says that tones, when given, already set the colour, so the LLM leaves colour to the plan. **Under tiles, colour
therefore depends on the planner writing `kpi_tones`.** The planner did so on 3 of 4 rows in the one fresh run
(p3); it missed CHEFFIN 4, whose hint asks for CPC in negative and Allowable CPC in warning.

**How often the hint already says it** (the 83 rows' plans): the hint asks for colour on 66. On 44 of those a hint
names an item next to a role word (negative / red / loss / positive / green / warning / amber / watch), and on 7
it gives one role to all / each / both items. That is 51 of 66 (77%) that code could turn into tones. The other 15
ask for colour without naming an item ("color-code deltas", "muted color", "highlight").

**Label colour (A → B per item, 310 items):** of the 281 labels found as their own Text, muted 214 (76%),
semantic 28, accent 27, on-dark 4, ink 2, other 6 (29 items: value or label merged into another Text). The LLM
coloured 55 of 281 labels (20%), mostly in toned or focus tiles. B keeps them, except 5 accent labels that became
muted. The user's "labels need colour" (QBR, paid 3) is one slide against a 76% muted norm.

## The `w="max"` squeeze (`squeeze.md`)

425 distinct slides the pipeline compiled (`input.xml` in `output/` and the `llm_test` zips, replays skipped). 163
have a `w="max"` box beside another box (the only shape that can hit it) and were compiled on today's compiler.
**3 hit the squeeze, all the same slide:** paid check 3's CHEFFIN 1 (×3 tries), a 170-character callout in a
`w="max"` box beside the tiles' `w="max"` panel. The older saved hits (gj-h1-regen-5a9e2d slides 4 and 10,
gj-h1-regen-7293ef) compile today. The 1a slot test's agency slide 2 still fails, but on height, and it comes from
the derived-blocks route. In the 68-slide replay neither route hits it.

## Planner reliability (step 2, `581d579`)

The cause of p3's 4 unreadable `content_data_json` and the CHEFFIN 6 reasoning-budget fallback is still unknown;
the saved run has no raw text. The planner now logs the start of the unreadable text and the text near the JSON
error, and for a call stopped at `max_tokens` how many output tokens were reasoning (recorded in history with
`failed="length"`, so its cost counts). The next paid run names the cause. No prompt was changed on a guess.

Files: `summary.md` (per slide, today's look), `summary-padding16.md` (the experiment's totals), `squeeze.md`,
`sample-01.png` / `sample-02.png` (8 pairs: hand-written left, tile tags right; first sheet = where tiles did
worst, second = typical), `sample-03-padding16.png`.
