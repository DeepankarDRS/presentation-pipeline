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
| process_arrow | horizontal band 9 at ≤ 4 words; vertical 9 in any 538 px column, Inter 16 bold ≥ 10 | **one long word: 6 across the band**, 3–4 in split-60 / card; **horizontal in split-40: 3 at best, a long word never**; 4-word Inter labels overflow a vertical chevron from 6 |
| timeline | horizontal band 9, vertical 9 | **a title of one long word breaks at any count** (120 px label box); split-60 horizontal 5, split-40 horizontal 3; vertical under a KPI row 6, in a card 5 |
| tree | band ≥ 8 leaves either layout | vertical layout in split-60: 4 leaves, split-40: 3; depth-3 horizontal in split-40: none; any shrink is below its 12 px default |
| matrix | ≥ 8 items of 1–2 words when ≥ 0.18 apart (band, split-60, card) | **one long word: breaks at 2** (100 px label at 11 px bold); 0.1 apart in a ≤ 665 px box overlaps |
| pyramid | short words ≥ 7 levels | long word: 4 levels (Inter 16: 3); 2–3 words: 5 (Inter: 4 / 3); 4 words: 4 levels (Inter: none) — the top band is 400 / levels px wide whatever the box |

fit-grow: rescues 263 flow cases (raw POM holds 101 / 800), 64 process_arrow, 20 timeline, 8 tree;
**makes 15 process_arrow cases worse and 1 matrix case** (§4 C2).

## 3. capacity.yaml against the map (band placement, the capacity's label length)

| limit | capacity | measured | verdict |
|---|---|---|---|
| flow horizontal | 6 | 9 (2 words; 1 long word 7) | capacity is safe; could be 7 |
| **flow vertical** | **8** | **7** | **over** — capacity assumes 40 px nodes + gap 24 (`flow.box_for_direction`, advice the generator may not follow); at POM's sizes the 8th node draws < 14 px. Recorded in the fixture as open |
| process_arrow horizontal | 7 | 9 (2 words); **6 with one long word** | holds for the 2-word cap only when no word is longer than "Profitability" |
| process_arrow vertical | 9 | 9 | matches |
| timeline horizontal | 8 | 9 (3 words); **0 with one long word** | count is safe; `max_label_words: 3` is safe (titles wrap, nothing below them), the long word is not |
| timeline vertical | 8 | 9 | safe |
| matrix | [3, 4] | ≥ 8 when ≥ 0.18 apart and short words | count limit is not the problem — word length and spacing are |
| pyramid | [3, 5] | 5 at 2–3 words, 4 with a long word | upper bound right for 2–3 words only |

**Proposed (not applied, needs your OK):**
1. flow vertical 8 → 7, *or* keep 8 and have code write `nodeHeight="40" nodeGap="24"` on vertical flows.
2. A **longest-word** limit beside `max_label_words` (the word count is not what breaks): px at the
   drawn size, e.g. process_arrow horizontal ≤ 90 px at 14 px (≈ 12 letters) past 6 steps, timeline
   horizontal title ≤ 100 px, matrix item ≤ 80 px, pyramid top band 400 / levels − 19 px. The plan check
   can measure it (POM's `measureText`), not guess it from letters.
3. **Placement-aware limits**: today's numbers are the band's. In split-40 a horizontal process_arrow /
   timeline / flow holds 3 — the planner should get "a narrow column → vertical" as a measured fact,
   with these numbers, instead of one count per direction.
4. flow horizontal 6 → 7 (optional; the 2-word band holds 9).

## 4. What code can fix vs what the planner must choose

**Code (proposed, not applied):**
- **C1. fit-grow over-measures every word by 10 px.** `widestPiece` / `runWidest` / table `measureCell`
  read `measureText(...).widthPx`, which includes POM's 10 px box padding (`calculateResult`);
  `runWidest` adds it per run (a "₹114.9" + "L" value counts 20 px too much). Effect: false
  `WORD_TOO_WIDE` (23 of the 170 process_arrow guard warnings are on labels whose word fits), chevrons / nodes widened or
  fonts lowered for nothing. Fix: subtract 10 px (touches table sizing too — needs its own replay).
- **C2. `growDiagrams` grows chevron itemHeight 80 → 120**, which takes 2 × 0.35 × 40 = 28 px off every
  label box; at 9 steps "program" fits POM's raw drawing and breaks after fit-grow (15 cases). Fix:
  grow itemHeight only while every label's longest word still fits (or let phase 3' lower it again).
- **C3. Diagram text is written in "Noto Sans JP"** (POM's default) when no `fontFamily` is given — not
  installed on this PC, not embedded (`font_embed.py` embeds src/node/fonts only), so viewers see a
  substitute. Flow, Tree and Matrix take no `fontFamily` at all. Fix: pptx-post rewrites the diagram
  runs' typeface to the deck font (and fit-grow measures in it), or the generator always writes
  `fontFamily` where POM accepts it.
- **C4. Fixed small sizes POM gives no attribute for:** tree labels 12 px, matrix labels 11 px, timeline
  dates 12 / descriptions 11 px. Only pptx-post can raise them; any scale-to-fit puts them further
  below 14.
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
