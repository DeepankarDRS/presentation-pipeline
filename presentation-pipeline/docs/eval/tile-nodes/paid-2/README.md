# KPI tile nodes: paid check 2, 3 repeats (2026-10-12, test PC)

`python -m scripts.kpi_paid --blocks tiles --arm-a kpi --repeat 3 --label tiles-paid-2 --no-render --bundle` on
`7dad9cd` (the visual-intent → tile attributes prompt, spec §10 last row; the test PC also had uncommitted local
changes). Generator only (gpt-4.1), the same 3 saved KPI slide plans as check 1 (`../paid/`), 3 tries each. Arm A =
the 2026-10-11 element-ref slides, recompiled. Re-scored and rendered on the build PC (`--rescore --arm-a kpi`).

## Gate (spec §8): failed

| | result | gate |
|---|---|---|
| blind marks (user, `marks.csv`; 1.3 / 2.1 / 2.2 corrected by the user after unblinding: the choices had been entered for the wrong side, the reasons were right) | **0.33**: tiles win 3 (CHEFFIN 4 ×3), lose 6 (QBR ×3, CHEFFIN 1 ×3) | ≥ 0.5 |
| KPI output tokens | 9 / 81–89 / 105 a slide vs ~400–760 hand-written | ≥ −50% |

## Accuracy

Values placed on the first try 48/48; NODE_* errors 0; repairs 0; compiled 9/9; values off plan 0; broken words
0 / 0; hand-written fallback tiles 0. The emphasis held where the plan has one (CHEFFIN 1: `inverted` + `hero` on
Combined ROAS, 3/3). Runs were near-identical across repeats (same tags in all three tries of each slide).

## Tokens and cost (generator)

9 runs $0.092 (≈ $0.010 a slide; the cold first call $0.021). Input 93,288 tokens, of which cached 78,336 (84%);
output 2,920 (324 a slide). Check 1: $0.058 for 3 slides (≈ $0.019 a slide, one cache hit).

## What the LLM wrote and why each slide went the way it did

| slide | tags (all 3 tries) | value px tiles / refs | marks | user's reason |
|---|---|---|---|---|
| QBR | `<KpiGrid ref="kpi_metrics"/>` | 58 / 86–91 | refs 3/3 | "better use of space and color code" |
| CHEFFIN 1 | scorecard + `inverted` / `hero` on Combined ROAS; platform ROAS tiles `color="$negative"` (`filled` in 2 of 3) inside the LLM's own `$negativeSoft` panel | 56–60; 28–29 / 72; 66–72 | refs 3/3 | "size is better for roas but combined roas should be with both roas" |
| CHEFFIN 4 | `<KpiGrid>` with 7 `<Kpi>`, `color="$warning"` on CPC, `color="$positive"` on Allowable CPC | 58 / 28 | **tiles 3/3** | "better use of space but color code needs work" |

1. **The prompt change did not move QBR.** The fixed lines now map each treatment to tile attributes, and the line says
   "no tones (colour by the visual-intent)", yet all three tries wrote the bare group again: the hint's colours are
   lost. Prompt wording is not a reliable lever here; the plan has to carry the colours (planner `kpi_tones`, spec §6),
   so code draws them by default.
2. **Tile values stop at 58–60 px.** On QBR the row of four sits in a growing band and stays at 58 px with empty space
   above and below, where the hand-built tiles grew to 86–91 px. Same on CHEFFIN 1's scorecard (56–60 vs 72).
3. **CHEFFIN 1's platform row is 28–29 px.** The LLM put the `<KpiGrid>` inside its own pink panel (padding 20); with
   `filled` tiles of the same pink the tiles vanish into it (2 of 3), and the lower-weight row stays near 28 px (the
   fit-grow issue seen on both routes, made worse by the panel's padding). The user's note on grouping (Combined ROAS
   with the platform ROAS figures) is the plan's grouping, the same on both routes.
4. **`color` on a plain tile shows nothing without a note or icon.** CHEFFIN 4's `$warning` / `$positive` items have
   neither, so the colours the LLM asked for never drew; the hand-built side drew those tiles tinted with a coloured
   border. The 4 + 3 grid won the space anyway.
5. The LLM still wrote attribute-less `<Kpi>` tags (CHEFFIN 4) despite the new "only for an item that differs" line;
   harmless (a few tokens).

## Proposed next (free)

- (a) An item with its own `color` and no `variant` takes the toned look (soft fill, coloured border, number in that
  colour), so a colour the LLM asks for always shows (also the replay's finding 4). **Built** (`1b9af6c`).
- (b) Planner `kpi_tones` (spec §6), so colour by meaning comes from the plan, not from the generator reading the hint.
  **Built** (user's go-ahead, `27b7aae`; the planner's prompt and schema text, not `slide_component_planner.py`).
- (c) Tiles inside the LLM's own filled panel: say so in the tile lines, or draw them `bare` / unfilled on a panel of
  the same colour; and the lower-weight row's 28 px (fit-grow). **Built in code** (`875a18b`; no prompt line).
- (d) Why tile values stop at 58–60 px in a growing band where hand-built tiles reach 72–91 px (fit-grow on the
  expanded tiles: does the group / its tiles grow with the band?). **Found and fixed** (`e57c8b4`).

## Fixes (2026-10-12, free; `fixes/`)

Re-scored on the same 9 saved runs, arm B expanded again from each run's `first.xml` on the new code
(`python -m scripts.kpi_paid --blocks tiles --arm-a kpi --label <copy> --rescore --refill`, `6ee2255`); renders in
`fixes/sheet-01..03.png` (same blind order as `sheet-01..03.png`, `key.json`), scores in `fixes/summary.md`.

**Why 58 px (d).** Not a cap: the width. tiles.py laid the bare `<KpiGrid>` of four as one row of 285 px tiles; at
~60 px "14 months" wraps (fit-grow's line check), with ~200 px of the band left empty. The hand-built route's LLM
had drawn the same four as 2 × 2. CHEFFIN 1's scorecard stops at 60 px for a different reason: its tiles reach the
fill target beside the 72 px hero tile (as on the hand route); its platform row stayed at 28 px because the slide
was full: the LLM's panel padding (20) plus the tiles' own (22) and the hero first in line for any spare height.

| | before | after | hand-built (A) |
|---|---|---|---|
| QBR values (r1 / r2 / r3) | 58 / 58 / 58, one row of 4 | **85 / 87 / 85**, 2 × 2 (`regridTiles`), labels 16 → 24 | 91 / 86 / 86 |
| CHEFFIN 1 scorecard; platform row | 60; 29 / 56; 28 / 60; 29 | 60; **60** / 60; **49** / 60; **60** (bare on the LLM's pink panel) | 72; 69 / 72; 63 / 72; 72 |
| CHEFFIN 4 values; `$warning` / `$positive` items | 58; colours not drawn | 58; CPC toned amber, Allowable CPC toned green | 28 |
| first try / errors / repairs / broken words / card empty B | 48/48, 0, 0, 0, 0 | unchanged | |

The hand-built route moved too, a little: CHEFFIN 1's platform row 72 → 69 (r1) and 66 → 63 (r2), because
content-sized ref tiles now grow their labels with the numbers inside the search (labels 16 → 18–24).

What the fixes do:
- (a) `with_color: toned` on `plain` (block-variants.yaml): an item with its own `color` and no variant of its own
  draws toned. Explicit variants, a group `color`, and variants that already show the colour are unchanged.
- (d) tiles.py ids a row it chose itself (no `layout` / `cols` from the LLM) `kpig-<component>`; fit-grow's new
  phase `regridTiles` grows the row and its balanced two-row grid and keeps the grid when its numbers end ≥ 15%
  larger. Content-sized ref tiles grow their labels / notes with the numbers inside the search (0.3 ×, ≤ 24 px).
- (c) a tile whose fill equals the fill of the nearest box the LLM drew around its tag (not the slide root) draws
  without fill, border or padding: the panel is the tile, the number keeps its colour. A content-sized hero already
  ≥ 48 px grows after the other KPI groups.

**(b) planner tones** (`27b7aae`, `b115ef9`). The slide component planner writes `kpi_tones` per item (good / bad /
watch / "", by what the number means: payback shorter = good); `plan_checks.settle_kpi_tones` keeps one per value.
Under tiles a plain tile with no colour asked draws its tone (`with_tone` on `plain`): bad / watch tinted, good in
the number; a colour or variant the LLM writes wins. The element-ref route already colours ref text by tone.
Not measurable on the saved runs (their plans have no tones): `fixes/tones-demo.png` re-expands the saved first
tries with tones taken from each plan's own hint (QBR good, good, bad, good; CHEFFIN 1 platform bad, bad; CHEFFIN 4
CPC bad, Allowable CPC good) — an illustration, not evidence. QBR then reads like the hand route (green numbers, the
margin tile tinted red); CHEFFIN 1 and 4 do not change (the LLM's own colours already win there). Evidence needs a
planner run: `kpi_paid --plans` puts arm B on a `kpi_plan_only` run's plans. Gallery (free): where several items share a bad tone, all of them
tint, so example 2 ("one tile singled out", one item toned by hand) now shows three red tiles; emphasis stays the
plan's inverted / hero item. Unit tests 1031 pass / 4 known.

Before (b), still open: QBR's tiles have no colour at all (the plan has no tones and the LLM writes a bare `<KpiGrid>`): the
user's other reason for the QBR loss ("color code"), (b). CHEFFIN 1's tile labels stay 16 px (the slide is full).
The user's CHEFFIN 1 note (Combined ROAS with the platform ROAS figures) is the plan's grouping, both routes: kept
separate (user, 2026-10-12).

Files: `sheet-01..03.png` (blind pairs), `marks.csv`, `key.json` (`nodes_side` = tiles), `summary.md` (scores per
run), `first-*.xml` (what the LLM wrote).
