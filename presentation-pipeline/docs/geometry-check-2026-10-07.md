# Component-level geometry check — slide-quality item 2, step 1 (2026-10-07)

**Status:** built, report only. Branch `feat/slide-quality`.

## Why

POM 10.3.0's own diagnostics compare layout **boxes**: `NODE_OUT_OF_BOUNDS` (box past the slide)
and `NODE_OVERLAP` (sibling boxes in a stack). A component can draw past its box, and POM does not
see it:

- a squeezed table keeps every row: a 5-row table in a 120 px box draws 160 px, 40 px into the
  next card, with **0 POM diagnostics** (reproduced 2026-10-07);
- a table's columns can be wider than its box: in saved slides tables ran 47-96 px under the card
  beside them (columns cut off);
- diagram and layer labels draw over each other or off the slide;
- the opposite failure, a small component in a big box, has no check at all.

User decisions (2026-10-07): one check on what is **drawn**, the same rules for every component kind
(not one rule per kind), report only first; fixes in code later, the LLM only for what code cannot fix.
Compared with the HTML / headless-browser approach the user shared: same loop (measure the drawn
result, structured pixel report, fix, re-check), with the boxes from POM's layout instead of a browser
and code fixes before any LLM round.

## How it works

| Part | What |
|---|---|
| `src/node/geometry.js` | runs POM's own per-slide path (`autoFitSlide` → `toPositioned`, same fonts) and writes `geometry.json`: every box POM draws into, with tag, path, id, card frame |
| `src/node/compile-pom.js` | writes `geometry.json` after the build (`POM_GEOMETRY=0` turns it off; never fatal). Also: `process.exitCode` instead of `process.exit()` at the end — the extra layout pass made Node crash at exit on Windows (`UV_HANDLE_CLOSING`) in about 1 of 3 runs |
| `src/compiler/geometry_audit.py` | reads every drawn shape in the `.pptx` (a table = sum of its rows × sum of its columns; a text that clearly needs more lines = its estimated height), gives it to the component box it overlaps most, and checks the rules below |
| `src/agents/validator.py` | adds the findings to `layout_issues` after a successful compile (cover / section / closing slides skip `GEOM_SLIDE_SPARSE`) |
| `layout_audit.REPORT_ONLY_CODES` | all `GEOM_*` codes: the critic never sees them, no repair is triggered; the eval counts them in `layout_codes` |
| `scripts/geometry_replay.py` | LLM-free replay of saved slides (`--reaudit` re-checks without compiling) |

| Code | Rule |
|---|---|
| `GEOM_SPILL` | a drawn shape leaves the card its component sits in, or lies in no component box |
| `GEOM_COLLISION` | a drawn shape covers another component's box (> 4 px), or text covers text (also inside one component) |
| `GEOM_OFF_SLIDE` | a drawn shape leaves the slide |
| `GEOM_TEXT_OVERFLOW` | a text needs two lines more than its frame (estimate) |
| `GEOM_CARD_EMPTY` | a card ≥ 120 px tall whose content (at any depth) spans < 55 % of it |
| `GEOM_BOX_EMPTY` | a table / diagram / chart box ≥ 120 px whose content uses < 50 % of it |
| `GEOM_SLIDE_SPARSE` | content ends above 75 % of the slide height (not on cover / section / closing) |

## Replay on saved slides (LLM-free)

Set A: 48 slides (step 0 bundles + the colour-roles run). Set B: 31 older slides (baseline,
phase-5-tables, tables-check zips), recompiled with today's compiler.

| Code | A: findings / slides | B: findings / slides |
|---|---|---|
| `GEOM_COLLISION` | 24 / 4 | 8 / 4 |
| `GEOM_SPILL` | 9 / 2 | 12 / 7 |
| `GEOM_OFF_SLIDE` | 2 / 1 | 1 / 1 |
| `GEOM_CARD_EMPTY` | 18 / 7 | 5 / 2 |
| `GEOM_BOX_EMPTY` | 1 / 1 | 0 |
| `GEOM_SLIDE_SPARSE` | 9 / 9 (covers included: the replay has no slide type) | 0 |
| `GEOM_TEXT_OVERFLOW` | 0 | 1 / 1 |
| POM `NODE_OUT_OF_BOUNDS` | 2 / 1 | 0 |
| POM `NODE_OVERLAP` > 2 px | 0 | 0 |

**Checked by eye against renders:** 14 slides with spill / collision / off-slide findings — 11
clearly real (layer captions over each other and off the slide, matrix labels over each other, a
flow label jammed between nodes, a KPI value over its delta, tables cut off under the next card
(×3), timeline labels out of their card, a squeezed table), 3 borderline (6-10 px). Fill: 8 of 8
checked slides real (stretched KPI tiles, a half-empty table card, an empty timeline card, a big empty
dark card). False findings found and fixed during the check: text owned by the box above it
(owner = largest overlap now), nested cards not counted as content, rotated axis labels, 3 px
collisions (minimum now 4 px).

Known gaps: text inside a table cell running into the next cell, and text clipped inside a shape
(a pyramid's narrow top) are not seen; text height is an estimate (~0.5 em per character).
Compile time: +≈ 30 ms per slide.

## Next (item 2, approved order)

2. Spill fix in code: give a component its drawn height / width (`minH` / column widths), re-layout;
   dense order gaps → padding → fonts to 14 → re-flow; still too full → `SLIDE_DENSE` (a split is the
   user's call).
3. Sparse fix: the main component takes the free space, then scale ≤ 1.25×, then centre.
4. Stress fixtures per component kind as the gate. 5. LLM repair with the pixel report for what is
   left (paid, ask first). A code becomes a repair trigger only at ≥ 90 % precision.

## Step 2 built: spill fix in code (2026-10-07)

`src/node/fit-grow.js` phase 7 `fixSpills` (after `reserveWrap`, before the word guard; `POM_FIT_SPILL=0` turns
it off). It runs only when a component needs more room than its box (table columns / rows, text, list,
stack content; the slide root is never given minH):

1. **Give the space.** A table too wide: columns re-planned into the box when no column gets narrower than
   a word, else `minW` on the table **and its parent stacks up to the row** (a child's minW does not widen
   its parent: the agency card stayed narrow until this). Too tall: `minH` = what the rows / text / content
   need. Up to 3 rounds.
2. **Dense order** if the slide is then too tall, each step on the original XML, cumulative, space given
   again: gaps ×0.75, ×0.5 (≥ 8) → padding ×0.75, ×0.5 (≥ 12) → fonts ×0.92 … ×0.7 (≥ 14).
3. **Still too full:** left as generated, `SLIDE_DENSE` warning (a split is the user's call). Re-flow
   (lists / card grids / tighter table columns) is not built yet.

POM's own autoFit stays as the last resort; it only acts on a slide too tall overall and shrinks fonts to 10.

**Replay (same 79 slides, LLM-free), slides with the code, step 1 → step 2:**

| Code | Set A (48) | Set B (31) |
|---|---|---|
| `GEOM_SPILL` | 2 → 1 | 7 → 3 |
| `GEOM_COLLISION` | 4 → 3 | 4 → 2 |
| `GEOM_CARD_EMPTY` | 7 → 7 | 2 → 1 |
| `WORD_TOO_WIDE` | 5 → 5 | 6 → 5 |
| `SLIDE_DENSE` (new) | 0 | 3 |

Checked by eye before / after: the agency table's hidden CVR column is back, the Blinkit table no longer runs
under its chart (NTB % and ACOS visible), the Swiggy KPI "₹1.80 Cr" no longer breaks over its delta (dense
order gaps / padding / fonts ×0.85, type still ≥ 14). Left: the 3 `SLIDE_DENSE` slides (old gj-h1 regen,
two with a table wider than its card), the `<Layer>` slide (positions written by the LLM: captions over
each other, off the slide), timeline labels too long for their diagram, matrix labels over each other —
these need a layout change, not more room (candidates for the LLM repair with the pixel report).
Time: +1.8 s on a slide fixed with the dense order, +4.7 s on a slide that stays too dense; 0 on a slide
without spills. Unit tests 795 pass, the 4 known failures.

## Tiers and placeholder check (2026-10-07)

Compared with Genspark's `check_slide_layout` categories (user, 2026-10-07): covered — spill / card overflow,
text-on-text, contrast, font floor; not needed — ancestor clip (PPTX does not clip: it shows as a spill).
Added now: **tier** on every geometry finding and `LOW_CONTRAST` — `error` = measured defect (spill / collision /
off-slide > 10 px, placeholder text, contrast < 1.5:1): code fix or repairer; `warning` = borderline (4-10 px,
the 3 cases judged borderline by eye all land here; contrast 1.5-4.5): for the visual critic to confirm on the
screenshot; `info` = fill codes, owned by code. **`PLACEHOLDER_TEXT`** (report only, tier error): drawn
"X.XX" / "XX", `TBD` / `lorem`, "Insight 1 —", "METRIC A", a bracketed name the brief does not use (the brief's own
"[Platform B]" is content). 0 hits on the 79 saved slides: a guard. Later (rare in our renders): text over a card
that is not its own, collapsed line height.

## Step 3 built: sparse slides + critic hand-off (2026-10-07)

User decisions (2026-10-07): **grow the type, don't shrink the card** stays (a card can hold a chart or table
that uses the space); no big faint numeral as filler (1a marks: "the 01 02 03 is not helpful"); centre the
body block as the default. Sizes / spacing / fill belong to code, the visual critic judges what code cannot
measure and confirms borderline geometry warnings (as in Genspark's split of layout check vs visual check).

**fit-grow phase 8 `centreBody`** (after `fixSpills`; `POM_FIT_CENTRE=0` turns it off). Only when no root band
grows and ≥ 48 px are free: (1) the slide's only table grows past the normal caps (cell text ≤ 24 px, rows
≤ 140 px and ≤ 2.5 × their text — `growMainTable` takes the caps as a parameter now); (2) the body (below the
header texts, above a trailing source line) moves down by half the free height (`margin.top`), the source line
to the bottom. Kept only if nothing spills and the slide fits.

**Audit:** `GEOM_SLIDE_SPARSE` = more than a quarter of the usable height (inside the slide padding) empty
below the content; a card reaching down counts as filled (its inside is `GEOM_CARD_EMPTY`). A table box counts
its drawn rows as filled (rows grown on purpose are not "empty").

**Replay (79 slides):** sparse slides 2 → 1 (the one left is a cover; the pipeline skips covers by slide type);
QBR table slide: table text 18 → 24 px, rows 256 → 400 px, body centred with 57 px above (checked by eye: the
first try centred a small table under a 129 px gap and also moved the header — fixed). `GEOM_CARD_EMPTY`
stays at 7: KPI tiles stretched by a growing band, numbers already width-bound (QBR "$48.2M" stops at 50 px
in a ~280 px tile). Not shrinking them is the user's rule; the cause is upstream (which band gets `grow`:
the normalizer's `GROW_BAND_ADDED` or the generator) — a decision for the user.

**Visual critic** (`src/agents/critic.py`, `visual_critic.py`, `prompts/visual_critic/`):
- gets the **fitted XML** (what the screenshot shows), not the pre-fit XML;
- sees geometry **warnings** (borderline 4-10 px) to confirm on the screenshot; errors and fill findings are not
  sent (code fixes them / they are code's) — `critic_layout_issues`;
- prompt: a CODE-OWNED section (no issue about font size, gaps, padding, margins, grow, empty space; no patch of
  those attributes; visible overlap / clipping / unreadable text stays the critic's); the "under-filled →
  `grow="2"`" rule is replaced by a flag-only "unbalanced composition";
- issues that still talk only about size / space are dropped before repair and logged (`code_owned`).
Not measured yet with the critic on (paid; ask first). Unit tests 803 pass, the 4 known failures.

## Paid check with the critic on (test PC, 2026-10-07, commit `48af92a`, `deck-qbr-data` × 1, $0.45)

8 slides, all compiled (slide 6 after one compile repair). The critic passed 6 slides with no issue (≈ 15 output
tokens each) and raised no size / spacing complaint visible in the result: it did not fight fit-grow. On slide 5
it flagged the context card that held a generic description instead of content ("Presents the quarter's most
important accomplishments…"); the slide was re-planned and the repaired slide shows a dark read-out with the real
message — the kind of judgement code cannot make. 2 medium issues stayed open (slides 6–7; texts were not saved —
the manifest now keeps them). Fit-grow on the run: the segment table grew to 24 px text / 396 px rows; KPI tiles
remain the open `GEOM_CARD_EMPTY` case. Seen by eye: the revenue chart put the focus colour on the first quarter,
not the one the headline names; slide 6's icon chips drew odd small squares.
Follow-ups done (LLM-free): normalizer `SHAPE_TYPE_ALIAS` (`circle` → `ellipse`, … — slide 6's first compile
failed on it; the saved XML now compiles first time); manifest `critic.issues` keeps severity / type / description /
fix. Unit tests 804 pass, the 4 known failures. Note: the test PC reported uncommitted local changes.

## KPI tiles, card edges and the generator's layout rules (2026-10-07)

User decisions (2026-10-07): solve the "flat cards" problem in the **palette**; a code rule only for the
**KPI case**; other layouts stay with the LLM through **layout rules** in its prompt (adapted from a 1920x1080
reference deck guide the user shared).

- **Card edge (palette):** the critic's one remaining issue in run 5fb8a2 asked for a card background the NRR /
  Enterprise tiles already had; they looked flat because `border` E2E8F0 was 1.17:1 on the slide (F7F9FC), and
  every light palette was 1.12-1.29:1. `palette_tokens.derive_tokens` now derives `border` (same hue, lightness
  stepped) to ≥ 1.4:1 on `surface` and `surfaceAlt` (corporate-slate E2E8F0 → CAD5E4); dark palettes unchanged.
  Test: all 18 palettes.
- **KPI rows (`src/compiler/kpi_grid.py`, normalizer `KPI_ROWS`):** when the slide's only body band is a row of
  4-6 stat tiles, the tiles become rows of 2 or 3 at equal % widths (4 → 2+2, 5 → 3+2, 6 → 3+3). The four options
  are in `docs/eval/kpi-tiles/kpi-tile-options.png` (A stretched / B centred / C bigger numbers / D 2x2): centring
  alone (B) was worse than today; the width was the limit. Before / after on the two saved KPI slides:
  `docs/eval/kpi-tiles/kpi-rows-before-after.png` — numbers 34 → 85 px, no geometry finding.
- **fit-grow:** stat rows stacked as one grid (same % tile width) share one number size; tiers of different widths
  (hero + supporting) keep theirs — the first version merged CHEFFIN's two tiers and shrank the hero tier (caught by
  eye, fixed). New `growStatSides`: a tile's label and delta grow with its number (≈ 0.3 ×, ≤ 24 px), kept only if
  nothing spills.
- **Layout rules (capacity.yaml `layout`, rendered by `capacity.layout_rules()` into the generator's house style):**
  KPI ≤ 4 per row and ≥ 260 px per tile; hero number 64-120 px; two compared metrics as two equal cards; grids with
  equal widths and 12-20 px gaps; ≤ 3 table columns in a half-width card; rows 36-88 px; a takeaway card 35-40 %
  beside the evidence; two-column splits 60/40 or 40/60. `kpi_row.per_row` 2-5 → 2-4 (5 tiles were ~230 px wide),
  so planner and generator state one number. Prompt +≈ 170 tokens.
Replay of 48 slides with the new fit-grow and palette: no code got worse. Unit tests 826 pass, the 4 known failures.
Not run with the API yet.
