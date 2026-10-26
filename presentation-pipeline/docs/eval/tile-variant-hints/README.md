# Tile / card looks from the design hint: build and free replay (2026-10-26)

Spec: `docs/tile-variant-choice-spec-2026-10-26.md`, option A. Under `POM_BLOCKS=tiles` the generator writes bare
`<KpiGrid>` / `<CardGrid>` tags almost every time (combined check arm B: 0 of 13 KpiGrids and 1 of 32 CardGrids named
a variant), so the looks the planner's `design_hint` asks for (accent bars, status dots, dark tiles) never showed.
Now code reads the hint and sets the variant on a bare tag. The LLM's own variant still wins.

## What was built

| Piece | Where |
|---|---|
| `look_from_hint(comp)`: the look a kpi_row / card_grid hint asks for | `src/agents/plan_checks.py`, next to `tones_from_hint` (same clause split and item names) |
| hook: LLM variant > hint > default; looks whose `requires` fail are left out quietly | `tiles.hint_looks`, called in `tiles.expand` and `cards.expand` |
| report `NODE_LOOK_FROM_HINT` per pick (logged by the validator at info) | `tiles.SEVERITY` |
| startup line `POM_BLOCKS=<mode>` | `src/api.py` lifespan |
| unit tests (one per mapping row, LLM wins, fallbacks, lone items, startup line) | `tests/unit/test_tile_variant_hints.py` |
| free replay | `python -m scripts.tile_hint_replay` -> `output/tile-hint-replay/` |

Mapping (user decisions 2026-10-26 in brackets):

| Hint cue | KPI tiles | Cards |
|---|---|---|
| accent / coloured / left border, bar, edge, stripe (a plain "border" is not a cue) | `bar`: the named tiles, else the group | `accent_top` on the group, when the clause names every card or none |
| status dot(s) | `dot`: the named tiles, else the group | none |
| dark / inverted | `inverted` on the plan's emphasis item, 3 or more tiles only (Q3: a single tile stays plain) | already drawn (the focus card) |
| hero / focus / emphasise alone | nothing (Q1: no hero size) | already drawn |
| tint / fill / shade, with tones | `filled` on the named tiles | nothing: `lifted` is already tinted by tone |
| numbered | none | `numerals` on a grid (steps number themselves) |
| lift / shadow | nothing (Q2: KPI tiles stay flat) | `lifted` default (Q4: `accent_top` stays flat) |
| several cues | bar > dot > filled. An item keeps its own look only when it ranks above the group's | accent_top > numerals |

Negations ("no status dots", "without an accent bar") are skipped. KPI items the LLM places alone (`<Kpi>` outside
any group) take the look too: the replay found 2 gj-h1 slides drawn that way (commit `6cdb367`).

## Step 0: census and check of the picks (free)

Over the 265 distinct saved components (`output/**/slides.json`, galleries skipped), 52 get a look: KPI group bar 14,
item bar 9, group dot 4, item dot 5, item filled 3, dark asked 11 (3 drawable); cards accent_top 9 (2 on matrix
plans, which still use the hand-drawn route). The user checked about 20 picks: "Picks OK" (2026-10-26).

## Step 2: free replay

`python -m scripts.tile_hint_replay`: every saved slide whose hint gives a look. KPI slides: the LLM's hand tiles
rewritten as tile tags (`tile_replay.rewrite`), then every `variant` removed. Cards: a bare `<CardGrid>` at the
LLM's cards' place (`card_replay`), with the LLM's layout kept. Both arms use the same tags and plan (kpi_tones
settled). **A = bare tags (today), B = bare tags + the hint's look.** Deck font, normalize, fit-grow, LibreOffice
with Inter.

| | A | B |
|---|---|---|
| slides | 52 (44 KPI, 8 card; 1 more card slide skipped: no cards in the plan) | 52 |
| compiled | 52 | 52 |
| GEOM_CARD_EMPTY | 40 | 33 |
| GEOM_SLIDE_SPARSE | 1 | 1 |
| broken words (render) | 10 | 11 |
| WORD_TOO_WIDE | 11 | 12 |
| LOW_CONTRAST | 29 | 18 |
| KPI number px, median | 41 | 43 |
| card title px, median of the smallest | 32 | 36 |

**Every look asked for is drawn**: bar 23 / 23, dot 12 / 12, filled 1 / 1, accent_top 8 / 8. Dark: 5 of 15. The
other 10 are single tiles (8) or a pair (2), plain by decision Q3. The smallest KPI number per slide: larger on 5,
the same on 36, smaller on 1 (gj-h1 5a9e2d s5, 28 -> 26 px: a bar and a dot in a row of 7).

Where B is worse:
- **1 broken word** (gj-h1 7293ef s4): the dot's marker narrows the label of an already crowded row of 7
  ("customers" -> "custome rs"). A already broke "10,332" in the same tile. This is the narrow-row problem; the dot
  only makes it visible here.
- **GEOM_CARD_EMPTY up on 2 card slides** (1 -> 2 each). On xtsy s4 the second card group is title-only: A drew open
  columns (the second group's default) with 28 px titles, B draws `accent_top` cards (the hint: "supporting panels
  with an accent border") with 20 px titles, the compact title-only size. Net over all slides: 40 -> 33.
- `NODE_FOCUS_UNNAMED` (report only) 7 -> 8: a tile given its own bar or dot from the hint counts as "drawn apart
  from its peers", although the hint named it. Harmless; it could skip hint picks later.
- `NODE_ATTR_IGNORED` 4 -> 6: colours the LLM asked for on a now-dark tile are swapped for readable ones (as
  designed).

LOW_CONTRAST falls 29 -> 18 because the dark tiles and bars replace pale tinted text.

## Blind marks (your turn)

44 pairs, those where B drew a look (the others are the same slide twice): `output/tile-hint-replay/sheets/`
(sheet-01 ... sheet-11.png on the build PC). Mark each pair in `marks.csv` (choice 1 / 2 / same, reason);
`key.json` says which side is B. The gate is 0.5 or more.

## Not done

- **Paid run**: none of its own. It rides on the next combined check (`python -m scripts.tile_combined --repeat 1`,
  about $1.3), only after asking.
- `NODE_FOCUS_UNNAMED` on hint picks, and the dot marker in narrow rows: noted above, not changed.
