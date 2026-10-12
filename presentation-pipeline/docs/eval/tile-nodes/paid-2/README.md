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
  colour), so a colour the LLM asks for always shows (also the replay's finding 4).
- (b) Planner `kpi_tones` (spec §6), so colour by meaning comes from the plan, not from the generator reading the hint.
- (c) Tiles inside the LLM's own filled panel: say so in the tile lines, or draw them `bare` / unfilled on a panel of
  the same colour; and the lower-weight row's 28 px (fit-grow).
- (d) Why tile values stop at 58–60 px in a growing band where hand-built tiles reach 72–91 px (fit-grow on the
  expanded tiles: does the group / its tiles grow with the band?).

Files: `sheet-01..03.png` (blind pairs), `marks.csv`, `key.json` (`nodes_side` = tiles), `summary.md` (scores per
run), `first-*.xml` (what the LLM wrote).
