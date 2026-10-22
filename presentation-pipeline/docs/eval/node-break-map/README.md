# Node break map: where each diagram breaks and where it holds (2026-10-21)

**Why.** e04963c found POM draws chevron / flow-node text with the renderer's default 0.1 in insets, so
"Profitability" broke in a chevron the capacity numbers said would hold. Those numbers were derived by
hand. This map measures them instead: every diagram swept over item count, label length, direction,
label style and the **placement** (the parent it sits in, as the generator writes it), compiled raw and
with fit-grow, scored on what is drawn. LLM-free, no paid run.

```bash
python -m scripts.node_break_map                 # all six (~25 min, 3,525 cases x 2 compiles)
python -m scripts.node_break_map --kinds flow    # one kind;  --quick = the edges only
python -m scripts.node_break_map --write-points  # refresh the regression fixture from output/
```

Per-kind maps: [flow](flow.md) · [process_arrow](process_arrow.md) · [timeline](timeline.md) ·
[tree](tree.md) · [matrix](matrix.md) · [pyramid](pyramid.md). Every case: `output/node-break-map/<kind>.json`.

## 1. Method

**Placements** (Slide > VStack padding 56 > 36 px headline > body; the box comes from POM's own stretch
rules, so "hero" means different boxes for a VStack band and an HStack column):

| placement | XML | diagram box |
|---|---|---|
| band | diagram `h="max"` in the root VStack | 1168 × 538 |
| band-under-kpi | 150 px KPI row, then the diagram | 1168 × 364 |
| split-60 | HStack: diagram `w="62%"` + text column | 665 × 538 |
| split-40 | HStack: text column + diagram `w="38%"` | 444 × 538 |
| card | one card of a 2 × 2 card grid, under its title | ~550–840 × 190–310 |

These are the layouts Gamma (cards, column splits) and Genspark (full-width band, 60/40) use, written
in our XML. **Labels**: 1 short word, 1 long word (Profitability, Reconciliation, Implementation …), 2 /
3 / 4 words. **Style**: POM's default vs `fontFamily="Inter"` (+ bold 16 px where the node takes it).

**Failure codes** (the Genspark lint, on POM's output): W word broken (longest word wider than its box
less insets, at the drawn font and typeface) · T text leaves the visible shape it sits on (chevron,
node, band) · O two texts' drawn extents overlap · S drawn below min(14 px, the node's own default) · F
`SCALE_BELOW_THRESHOLD` · P spills onto a neighbour or > 8 px out of its box · X off the slide · G
fit-grow `WORD_TOO_WIDE` (shown, not counted: see §4). Text is measured by POM's own `measureText` with
the fonts in `src/node/fonts` and placed by the shape's anchor / alignment.

**Checked against a render** (LibreOffice, 5 slides): the pyramid top band breaks "Market research",
the timeline breaks "Implementatio-n", both as measured. The render also caught a measuring bug of
mine (POM's `measureText` adds 10 px to every width; corrected before the final run — §4 item C1).

## 2. Results (fit-grow on; "holds N" = the most items with no break)

| node | holds well | breaks |
|---|---|---|
| flow | horizontal band 9 (2–4 words; raw POM 6), vertical 7 anywhere 538 px tall | a 1-long-word horizontal flow 7; decision / terminator shapes ("mixed") 6–7 (their text rect is half / 0.9 of the node); split-40 horizontal 3–4; vertical under a KPI row or in a card 3 |
| process_arrow | horizontal band ≥ 10 at ≤ 4 words; vertical 9 in any 538 px column, Inter 16 bold ≥ 10 | **one long word: 7 across the band**, 3–5 in split-60 / card; **horizontal in split-40: 4 at best, a long word never**; 4-word Inter labels overflow a vertical chevron from 6 |
| timeline | horizontal band 9, vertical 9 | **a title of one long word breaks at any count** (120 px label box); split-60 horizontal 5, split-40 horizontal 3; vertical under a KPI row 6, in a card 5 |
| tree | band ≥ 8 leaves either layout | vertical layout in split-60: 4 leaves, split-40: 3; depth-3 horizontal in split-40: none; any shrink is below its 12 px default |
| matrix | ≥ 8 items of 1–2 words when ≥ 0.18 apart (band, split-60, card) | **one long word: breaks at 2** (100 px label at 11 px bold); 0.1 apart in a ≤ 665 px box overlaps |
| pyramid | short words ≥ 7 levels | long word: 4 levels (Inter 16: 3); 2–3 words: 5 (Inter: 4 / 3); 4 words: 4 levels (Inter: none) — the top band is 400 / levels px wide whatever the box |

fit-grow: rescues 263 flow cases (raw POM holds 101 / 800), 107 process_arrow, 20 timeline, 8 tree;
makes 1 matrix case worse (the 4 process_arrow cases under a KPI row are fixed, C2b). (Before C1 / C2 were fixed: 64 rescued, 15 made worse by the chevron height growth.)

## 3. capacity.yaml against the map (band placement, the capacity's label length)

| limit | capacity | measured | verdict |
|---|---|---|---|
| flow horizontal | 6 | 9 (2 words; 1 long word 7) | capacity is safe; could be 7 |
| **flow vertical** | **8** | **7** | **over** — capacity assumes 40 px nodes + gap 24 (`flow.box_for_direction`, advice the generator may not follow); at POM's sizes the 8th node draws < 14 px. Recorded in the fixture as open |
| process_arrow horizontal | 7 | ≥ 10 (2 words); **7 with one long word** | holds, with a long word just at the limit |
| process_arrow vertical | 9 | 9 | matches |
| timeline horizontal | 8 | 9 (3 words); **0 with one long word** | count is safe; `max_label_words: 3` is safe (titles wrap, nothing below them), the long word is not |
| timeline vertical | 8 | 9 | safe |
| matrix | [3, 4] | ≥ 8 when ≥ 0.18 apart and short words | count limit is not the problem — word length and spacing are |
| pyramid | [3, 5] | 5 at 2–3 words, 4 with a long word | upper bound right for 2–3 words only |

**Proposed (not applied, needs your OK):**
1. flow vertical 8 → 7, *or* keep 8 and have code write `nodeHeight="40" nodeGap="24"` on vertical flows.
2. A **longest-word** limit beside `max_label_words` (the word count is not what breaks): px at the
   drawn size, e.g. process_arrow horizontal ≤ 90 px at 14 px (≈ 12 letters) past 7 steps, timeline
   horizontal title ≤ 100 px, matrix item ≤ 80 px, pyramid top band 400 / levels − 19 px. The plan check
   can measure it (POM's `measureText`), not guess it from letters.
3. **Placement-aware limits**: today's numbers are the band's. In split-40 a horizontal process_arrow /
   timeline / flow holds 3 — the planner should get "a narrow column → vertical" as a measured fact,
   with these numbers, instead of one count per direction.
4. flow horizontal 6 → 7 (optional; the 2-word band holds 9).

## 4. What code can fix vs what the planner must choose

**Code (proposed, not applied):**
- **C1. fit-grow over-measured every word by 10 px — FIXED (2026-10-21, user).** `widestPiece` /
  `runWidest` / table `measureCell` / the one-line run check / the list split read
  `measureText(...).widthPx`, which includes POM's 10 px box padding (`calculateResult`); `runWidest`
  added it per run (a "₹114.9" + "L" value counted 20 px too much). Now one helper, `naturalWidth`.
  The padding had hidden that fit-grow called a word 0.5 px *wider* than its box a fit: a LibreOffice
  render breaks "Profitabilit-y" 0.3 px short, so a word now needs 0.5 px to spare (`WORD_MARGIN`, in
  the diagram sizing, the shrink guard, its overflow total and the growth checks).
  Replay of 577 saved slides (the main checkout's `output/`, every unique `input.xml`, fit-grow on,
  words measured run by run): broken words 32 → 31 (no slide worse), `WORD_TOO_WIDE` 75 → 51; 170
  slides laid out differently, total type larger on 118, smaller on 4. Tests changed: the narrow
  chevron row now stops at 14 px with the word fitting (a new test keeps "never below 14, warns" with
  "Reconciliation"); the g4 pinned-columns fixture no longer needs widening ("₹59.8" is 78 px in 90,
  render-checked), so the pinned-neighbour widening path lost its fixture. Its fixture now is
  `g5-pinned-column-widened.xml` (2026-10-22): "spend" and "₹12" in a pinned KPI tile break in
  LibreOffice without the widening and are whole with it. Two guard fixes came with it: the column's
  need now includes `WORD_MARGIN` (before: 63 px given, "spend" left at 48 px in 48), and an edit that
  clears every overflow is kept even when the total was under the 0.5 px step. Open edge: POM counts
  letter spacing after the last letter too (LibreOffice draws "share", 52 px with it, whole in 52 px);
  kept conservative until PowerPoint is checked. LibreOffice probe (2026-10-22, `letter-spacing/`): five
  words, spacing 1–4 px, all drawn whole at count − spacing + 0.5, so LibreOffice does not need the
  trailing spacing; PowerPoint is not installed here, `letter-spacing/probe.pptx` is ready for the test PC.
- **C2. `growDiagrams` grew chevron itemHeight 80 → 120 — FIXED (2026-10-21, user).** A taller chevron
  has a narrower label box (itemWidth − 0.7 × itemHeight) and a larger font: at 9 steps "program" fit
  POM's raw drawing and broke after fit-grow (15 map cases). `diagramEdit` now grows the row only to the
  tallest height at which every label's longest word fits (`arrowShort`, `WORD_MARGIN`); when none does,
  it keeps height and font and only fits the chevrons' width to the box, as before, and phase 3' widens
  them for their words. Map: process_arrow holds 510 → 560 of 800, made worse 15 → 4, the band's 2-word
  row 9 → ≥ 10 steps, split-40 horizontal 3 → 4. Replay of the 577 saved slides: 2 slides change,
  broken words 31 → 30, none worse. New test: 9 three-word steps grow to 99 px (was 120), every word fits.
- **C2b. The spill fix shrank a diagram below 14 px — FIXED (2026-10-22).** A vertical 8-step chevron
  column under a KPI row squeezes the title to 41 px for its 47 px line; phase 7 gave the title its room
  from the `h="max"` diagram, which POM then drew at 13.84 px (raw 14.01): a 6 px title overhang into an
  empty 24 px gap traded for labels under the floor. `fixSpills` now rejects a fix that takes a
  ProcessArrow / Flow below `DIAGRAM_FONT_FLOOR` when it was not (drawn size = attribute × scale-to-fit,
  as phase 2d), so the dense steps run: gaps × 0.75 give the title its line, labels 14.16 px (test d8).
  Map: process_arrow holds 560 → 569, made worse 4 → 0; the vertical card column (default style) holds
  5 → 8 steps. Replay of the 577 saved slides: the check changes none of them.
- **C3. Diagram text is written in "Noto Sans JP"** (POM's default) when no `fontFamily` is given — not
  installed on this PC, not embedded (`font_embed.py` embeds src/node/fonts only), so viewers see a
  substitute. Flow, Tree and Matrix take no `fontFamily` at all. Fix: pptx-post rewrites the diagram
  runs' typeface to the deck font (and fit-grow measures in it), or the generator always writes
  `fontFamily` where POM accepts it. **FIXED (2026-10-21, `3ff0f94`):** pptx-post names the deck font
  (`POM_DECK_FONT`, default Inter) in POM's "Noto Sans JP" runs, font_embed embeds it, fit-grow measures
  in it; `POM_DECK_FONT=none` is the old behaviour. Measured 2026-10-22 (same code, the env switch as
  "before"): map holds with fit-grow unchanged for timeline 492, process_arrow 560, pyramid 119, tree 420,
  matrix 186 of their grids; flow 364 -> 359: 5 horizontal flows with decision / terminator shapes now
  score a word 0-1 px over its estimated text rectangle ("Scale" 36 px in 36) where the guard's 8 %
  slack for an unloadable Noto used to hide it; LibreOffice draws all 5 whole (checked by render), so the
  scorer's shape rectangle (FLOW_TEXT_RECT) is the soft spot, not the font. Replay of the 38 unique saved
  slides with a Flow / Tree / Matrix (C:\dev output/, LibreOffice renders): broken words 27 -> 27
  ("leadershi|p" fixed, "Bough|t" in a decision diamond that already could not hold "before?" newly
  broken: Inter is wider than the Liberation Sans LibreOffice substituted), WORD_TOO_WIDE 16 -> 16;
  every Noto run is now drawn in Inter (before: Liberation Sans, bold matrix labels in Arial Black).
- **C4. Fixed small sizes POM gives no attribute for:** tree labels 12 px, matrix labels 11 px, timeline
  dates 12 / descriptions 11 px. Only pptx-post can raise them; any scale-to-fit puts them further
  below 14. **Decision (user, 2026-10-22): keep POM's own sizes for now**; the options below stay on record.
  **Options measured (2026-10-22, not applied):** POM's renderer constants (matrix item /
  quadrant labels 11, axis labels 12; timeline dates 12, descriptions 11; tree labels 12, each × the
  diagram's scale) raised to 13 or 14 px in a patched copy, maps re-run with fit-grow (C3 in). "Clean" =
  no word broken, overflow, overlap or spill (shrink codes left out, they move with the size itself):

  | kind (grid) | as POM draws | all to 13 | all to 14 | per diagram: largest of 14 / 13 / 12 that is clean |
  |---|---|---|---|---|
  | tree (560) | 532 clean, 0 at ≥ 14 px | 510 (22 newly broken) | 405 (127 newly broken: POM lays nodes out for 12 px, 14 px wraps and overflows them), 372 at ≥ 14 | 532 clean: 405 at 14, 105 at 13, 22 at 12 |
  | matrix (315) | 186 clean, 0 at ≥ 12 px | 156 (30 newly broken) | 158 (29 newly broken: 100 px item label, "Reconciliati-on"), 158 at ≥ 14 | 187 clean: 158 at 14, 29 at 12 |
  | timeline (800) | 720 clean, 0 at ≥ 14 | 720 | 720, 492 at ≥ 14 | 720 at 14 |

  Checked by render: tree at 14 wraps "Market research" in its 30 px node, matrix at 14 breaks and
  overlaps its labels in a card. The timeline grid has short dates and no descriptions, so descriptions
  at 13 / 14 are not measured yet. Implementation note: tree and matrix runs are the ones POM writes in
  "Noto Sans JP", so pptx-post can find them before it renames the font; timeline runs carry the deck
  font like all other text, so a per-diagram size needs fit-grow to pass which runs to change.
- **C5. Vertical flow sizing** (§3 item 1) and **chevron width from the longest word** (phase 3' already
  does this; with C1 / C2 fixed it rescues more).

**Planner (choose another kind or direction):**
- A horizontal process_arrow / timeline / flow in split-40 (or any ≤ 450 px column): vertical.
- A label set with a word over the limits in §3 item 2: another kind (card_grid steps), not a
  narrower diagram; for a timeline, vertical (its titles get the box width − 80 px).
- Matrix: one long word per item never fits (100 px at 11 px bold) → shorter item names or a table.
- Pyramid: more than 4 levels only with short top labels; long labels → a vertical list / layer.
- Vertical diagrams under a KPI row or inside a card hold 3–6: past it, a horizontal one in the band.

## 5. The regression test

`tests/unit/test_node_break_map.py` (3 tests, ~12 s): 13 series of the grid (`TEST_SLICE`) compiled at
the recorded break point and one past it; fails when a break point moves (a POM upgrade, a fit-grow
change) and when capacity.yaml promises more than the band holds — except `flow.vertical`, recorded in
`tests/fixtures/node_break_map/break_points.yaml` as open until you decide. Checked that it fails: a
recorded pyramid point moved by one is reported. After a deliberate change: re-run the kind, then
`--write-points`.

## 6. Checks

Unit tests: 1198 pass + the 4 known failures (critic medium-only, layout-audit font minimum, two
graph routing tests). New: `scripts/node_break_map.py`, `src/node/break-map.js`, the test + fixture;
`node_facts.drawn_shapes` reads vertical insets, bold, typeface, fill, anchor, alignment (the
node-facts probes still pass). Not yet mapped: Table, KpiGrid / Kpi, CardGrid / Card, Text, Ul, Chart,
Icon, Shape, Layer (next batch, same harness).

## 7. Table, KPI and card nodes (batch 2, 2026-10-22)

Maps: [table.md](table.md) (3640 cases), [kpi.md](kpi.md) (840), [cards.md](cards.md) (792). KpiGrid / Kpi and
CardGrid / Card go through the pipeline's own expansion (`scripts/node_break_map_blocks.py`) before compile;
words are measured run by run (a KPI value "₹114.9" + a smaller "L" span is two runs); table cells are read
with the insets the pptx gives them (0). Scorer checked by LibreOffice renders: a 10-column table in the 38 %
column breaks its words ("Busin-ess", "Recon-ciliati-on") as scored; a 13-row two-column table in a card holds
(fit-grow gives the card the height); a matrix of 3-6-word cells in the band at 9 rows holds, but with 0 cell
insets neighbouring columns touch ("Volume falls after|Fill rate held"; insets left at 0 by the user's choice).

**fit-grow:** table holds 1152 -> 2787 (rescued 1635, made worse 0); kpi 646 -> 680 (34 / 0); cards 356 -> 396
(44 / 4: a steps row under a KPI band and a 7-card long-body grid in split-60 where the dense spill fix leaves
'a tile' past its box). **POM crashes** (`addTextBox: width / height must be a finite positive EMU value`): cards
108 with fit-grow (102 raw), all steps rows in split-60 / split-40 past what fits; table 5 with fit-grow (112 raw,
fit-grow re-plans the rest), 8-10 columns of 3-6-word cells in a card. A crash fails the slide's compile.

What holds (fit-grow on; rows / tiles / cards, the first break in brackets):

| node | band 1168 × 537 | under a KPI row 1168 × 331-363 | split-60 555-724 px | split-40 419-444 px | card 550-970 × 214 |
|---|---|---|---|---|---|
| table, ≤ 6 columns, short cells | ≥ 14 rows | 10 (P) | ≥ 14 | ≥ 14 up to 4 columns; 5+ columns with a long word: none (W) | 13 (P) |
| table, 3-6-word cells | 11 rows at 5-6 cols, 8-9 at 8-10 | 9-10 at ≤ 6 cols, 6-8 at 8-10 | 8-11 at 4-6 cols, 7 at 8 | 11 at 3 cols, 9-10 at 4, 4-8 at 5-6 | 7-11 at 3-5 cols, 6-7 at 6-10 |
| kpi, code's grid (auto) | ≥ 8 tiles | ≥ 8 | ≥ 8 | 6 (W, O) | ≥ 8 |
| kpi, one row (pinned) | 7 with a long-word label, else ≥ 8 | same | 5 | 3 | 4-5 |
| cards grid, title / short body | ≥ 12 | ≥ 12 | ≥ 12 (one-long-word title: 7-9) | 6 (W) | |
| cards grid, ~22-word body | 9 (P) | 6 (P) | 6 (P) | 4 (P) | |
| cards steps | 5 (long-word title) - 7 | 6-7; long body 4 | 3-4 | 2 | |

KPI number size falls with tiles in one row (pinned, band): 4 tiles 67-88 px, 5 -> 51-61, 8 -> 28-33; split-60
3 tiles 53-70 px; split-40 2 tiles 49-65 px. Code's grid keeps 67-95 px in the band up to 8 tiles.

**Proposed capacity changes (not applied; for the user):**
- `table.max_cols` per placement instead of one 8: band 10 (holds ≥ 14 rows of short cells; 3-6-word cells 8-9
  rows), split-60 6 (8 columns with a long word break at once), split-40 4 (5 columns with a long word break at
  once). `layout.table_cols_half: 3` is stricter than the measured 4 in the 38 % column; keep 3 for 3-6-word
  cells (4 columns hold 9-10 rows), allow 4 for numbers / one-word cells.
- `table.max_rows: 10` holds under a KPI row (10, then P) and everywhere for short cells; with 3-6-word cells
  in 8+ columns the measured limit is 6-9 rows: a plan check on (columns × words per cell) rather than rows alone.
- `kpi_row.per_row: [2, 4]` stays (number size, not breaks, sets it: 5 tiles in a row drop the number to
  ~51-61 px); per placement for one row: split-60 3, split-40 2 (3 hold but at 28-38 px), a card 4 (4-5 hold, numbers 32-44 px).
- `card_grid.steps_max: 5` holds in the band; per placement: under a KPI row 4 with body text, split-60 3,
  split-40 2 (and the planner must not put more steps there: POM crashes, above).
- `card_grid.items: [2, 12]` holds for titles / short bodies in the band, split-60 and under a KPI row; with
  ~22-word bodies: band 9, under a KPI row or split-60 6, split-40 4.
