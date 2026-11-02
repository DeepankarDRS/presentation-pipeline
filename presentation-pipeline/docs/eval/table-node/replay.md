# Table node: free replay (2026-11-01)

`python -m scripts.node_replay --kind table [--variant rows|columns|banded|grid|"grid numbered"|ledger] --src <main checkout>/output` (POM_NODES
on, Inter render, no LLM). 66 saved slides: one table component with an id, one LLM-drawn `<Table>`. Arm A is the
slide as the LLM wrote it. Arm B replaces the LLM's table (and its card on 38 slides) with one `<Table ref>` that keeps
the LLM's layout attributes. Blind sheets are in `output/table-replay[-<variant>]/sheets/`; `key.json` and an empty
`marks.csv` per run are in this folder (`native/`, `rows/`, `columns/`, `banded/`, `grid/`, `grid-numbered/`,
`ledger/`). `native/`, `grid/`, `grid-numbered/` and `ledger/` also hold their sheets (`sheets/`), so they can be
marked from the repo.

**The gate is `native/`**, the bare tag, which is what a `<Table ref>` without `variant` draws. The other three runs
force one word onto every slide, so you can see each word on real content. They are a stress test, not the LLM's
choice: the box was sized for the LLM's compact table, while a generator that picks `rows` also sizes its box.

| | A (LLM) | B `native` | B `rows` | B `columns` | B `banded` |
|---|---|---|---|---|---|
| compiled | 66 | 66 | 66 | 63 | 66 |
| drawn as asked | – | 66 | 66 | 51 (15 too big → native) | 65 (1 → native) |
| plan cells not on the slide | 0 | 0 | 0 | 13 * | 15 * |
| broken words (render) | 0 | 0 | 83 | 0 | 85 |
| text overlaps (render) | 31 | 46 | 63 | 39 | 76 |
| WORD_TOO_WIDE | 13 | 12 | 50 | 7 | 79 |
| GEOM_CARD_EMPTY | 7 | 6 | 43 | 43 | 15 |
| LOW_CONTRAST | 13 | 9 | 9 | 9 | 9 |
| table output tokens | 38 876 | 569 (−99%) | 833 | 833 | 899 |

\* only the first column's *name* ("Segment", "Match Type"). `columns` and `banded` show each row's first cell as its
pill / band, which leaves no place for that column's name. No data cell is lost.

## What changed during the replays

- **Native fills its band (the gap the task named).** The node table carries an id (`tbl-<cid>`) and no cell
  `fontSize`. fit-grow sizes it from its text: 14 px cells, column widths, rows as tall as their text. As the slide's
  main table, it then grows into spare height further than an LLM table: text ≤ 22 px, rows ≤ 120 px or 3× their
  text (`NODE_TABLE_CAPS`). Gallery: rows 160 → 532 px, text 14 → 22 px. A first try that grew the text in fixed
  equal columns (26 px) ran words into the next column; it was dropped.
- **Cells left-aligned.** With POM's 0 cell margins, right-aligned numbers touched the next column's text
  ("₹10.7Actual CPC is"). Text overlaps went 56 → 48.
- **No growth that widens the table** (fit-grow `tableFits`, all tables). Growing a main table's text made it wider,
  and a side panel beside it was squeezed to a sliver (pair 14.1). Broken words went 1 → 0.

## Native vs the LLM (the gate)

Equal on data (0 cells lost), broken words (0 / 0) and squeeze. Better on WORD_TOO_WIDE (13 → 12), empty cards (7 → 6)
and contrast (13 → 9). Tokens −99%. **Worse on text overlaps (31 → 46)**: 9 slides worse, 3 better. 11 of the 15
extra overlaps come from two slides (wide-paid agency s1, gj-h1 bf396b s6), where a wide table with many columns
sits beside other blocks. Most of the rest are adjacent header cells touching ("Actual CPC│Allowable CPC") because
cells have 0 margins (AGENTS.md: "0 cell margins (user: leave)").

What B does differently, as seen on the sheets:
- the emphasis row or column comes from the hint, in the hint's tone (green "Fix" column, blue "Enterprise" row);
- the LLM colours several rows by meaning (one red, one green), while the node draws one emphasis only;
- B's table is larger where the slide has room.

## The forced words

- **`rows`** reads well with the slide's width (pair 1: Enterprise row in its tone, values large). It breaks in a
  narrow box or beside a side panel (3.2: it took the width, and the city tiles beside it broke letter by letter).
  It needs room, as the gallery showed.
- **`columns`** (≤ 5 rows, ≤ 6 columns; 15 slides fell back) has 0 broken words. It is the strongest of the three
  on short tables (pair 1). 3 slides failed to build: one box per cell in a band too short for them ended at 0 px
  (`addTextBox: height must be a finite positive EMU value`). In a live run that error goes to a repair.
- **`banded`** breaks on tables with many rows in a short band (13.2: six month boxes, labels stacked letter by
  letter). It reads well on 3–4 rows with room (13.4 left).

## The card tables (2026-11-02, after `evenTableParts`)

The user's card-table set (spec §2.3): `grid` = header pills over a card per cell, `grid numbered` = 01–04 tiles
leading the rows, `ledger` = one header band over joined, striped rows. Forced onto every slide, like the words above.

| | A (LLM) | B `grid` | B `grid numbered` | B `ledger` |
|---|---|---|---|---|
| compiled | 66 | 65 | 65 | 66 |
| drawn as asked | – | 58 (8 → native) | 56 (2 → grid, 8 → native) | 59 (7 → native) |
| plan cells not on the slide | 0 | 0 | 0 | 0 |
| broken words (render) | 0 | 68 (10 slides) | 126 (12 slides) | 41 (10 slides) |
| text overlaps (render) | 31 | 47 | 61 | 49 |
| WORD_TOO_WIDE | 13 | 39 | 55 | 33 |
| GEOM_CARD_EMPTY | 7 | 146 | 186 | 197 |
| LOW_CONTRAST | 13 | 9 | 9 | 9 |
| table output tokens | 38 876 | 833 (−98%) | 899 (−98%) | 833 (−98%) |

Before `evenTableParts` (2026-11-01): broken words grid 82, grid numbered 131, ledger 54; overlaps 51 / 63 / 62.
Each part now has one size per table (pair 1.1: all cells 24 px).

- Broken words sit on 10–12 slides: the same squeeze as `rows` / `banded` (a card table beside a side panel or in a
  short band). Fixing it is open item 1 below.
- `GEOM_CARD_EMPTY` counts each cell card: a cell holding "$5.7M" in a card sized to its row's tallest cell is mostly
  empty. It is the look of the composition, not lost content.
- The `label_cards` and `lifted` styles hide the card border with the card's own fill colour, not a 0 width
  (`test_knowledge_never_teaches_zero_strokes`).

## Open (not built; each needs your call)

1. A size floor per word: `rows` / `banded` / `columns` fall back to `native` when the box is too small. Code
   knows the box only after layout (fit-grow), so this means a fit-grow fallback or a prompt rule ("give rows its
   own band"). Not built.
2. `columns` / `banded` could show the first column's name (e.g. as a caption over the pills). Not built.
3. Several rows coloured by meaning (the LLM's red / green rows) has no plan field. Same open item as the chart's
   colours by meaning.
4. Cell margins (header cells touching) were left as the user decided earlier.

## Blind marks

`native/marks.csv` (66 pairs) is the gate: fill `choice` with 1, 2 or same per pair. "Same" counts as satisfied (user
rule). The `rows/`, `columns/`, `banded/`, `grid/`, `grid-numbered/` and `ledger/` marks are optional; they say whether a
word should stay on offer.

## Native marks (user, 2026-11-02)

66 pairs: table tag 10, LLM 9, same 47 (8.3 written "]same", read as same). **Ties as satisfied: 57 / 66 = 0.86.
Ties left out: 10 / 19 = 0.53.**

- LLM wins: colours by meaning (2.2, 3.1, 3.2: rows / a value coloured by what it means; 4.1: two highlight colours in
  one sentence), sizing (5.4, 10.1, 11.1), the table squeezing the stack beside it (14.1), a table taking room from a
  hero chart (17.2).
- Tag wins: space allocation (2.4, 3.3, 4.3, 6.2, 9.2, 9.3, 16.1), no icon on a dense slide (2.3), no overflow (11.2),
  table and chart side by side at one height (6.4).
- Found from the marks: on 38 slides the replay replaced the LLM's card (the VStack / HStack around the table, with its
  title row) by the tag, and the table node draws no card and no title (the chart node draws both; the table plan has
  no title field). Not fixed yet.

## Round 2 and 3 (2026-11-02)

- **Round 2** (`native-2/`): the replay keeps the LLM's card and heading around the tag (round 1 had replaced them on
  38 slides; the table node draws no card). Overlaps 46 -> 36.
- **Round 3** (`native-3/`, user decisions): native default is **striped** (solid `$accent` header, `$surfaceAlt`
  alternate rows, `cellBorder.width="0"`); recipes `borderless` (pale header, plain rows: compact number tables) and
  `bordered`; dashed dropped. **Cell margins on**: one margin per table, 8% of its average column width, 4-12 px
  (`src/node/cell-margin.js`), written by pptx-post into every cell and taken off each column's width by fit-grow.
  A flat 12 px broke words in narrow tables (A 71 / B 41 broken words, 6 slides: e.g. 7 columns in 446 px).
  Margins apply to the LLM's own tables too (arm A).

| | A r2 | B r2 | A r3 | B r3 |
|---|---|---|---|---|
| compiled | 66 | 66 | 66 | 66 |
| broken words (render) | 0 | 0 | 0 | 0 |
| text overlaps (render) | 31 | 36 | 35 | 37 |
| WORD_TOO_WIDE | 13 | 14 | 23 | 14 |
| GEOM_CARD_EMPTY | 7 | 7 | 5 | 4 |
| LOW_CONTRAST | 13 | 9 | 13 | 9 |

WORD_TOO_WIDE rose on the LLM's tables (13 -> 23): the word guard now counts the margins, and the LLM's own column
widths leave less room for them. Highlights (`<Highlight>`) are not in these sheets: the saved slides predate them.

## Can the tag reproduce the LLM's colour coding? (2026-11-02, `native-marks/`)

`python -m scripts.node_replay --kind table --marks-from-llm`: arm B's tag gets `<Highlight>` marks made from the
LLM's own colours (whole toned rows / columns, then toned cells, then toned `<Span>`s; a new `focus` tone carries
the LLM's accent emphasis). 43 of the 66 LLM tables colour cells by meaning (median 2 toned cells, up to 18).

| | A (LLM) | B (tag + marks) |
|---|---|---|
| compiled | 66 | 66 |
| broken words | 0 | 0 |
| text overlaps | 35 | 37 |
| WORD_TOO_WIDE | 23 | 15 |
| LOW_CONTRAST | 13 | 9 |
| table output tokens | 36 083 | 3 909 (−89%) |

58 slides got marks; marks per table {0: 8, 1: 8, 2: 15, 3: 11, 4: 5, 5: 6, 6: 8, 8+: 5}. 19 tables need more
than 4: the tag keeps the first 4 (rows, then columns, then cells), so their per-cell colours are partly lost
(pair 4.1: the LLM's tinted platform columns). The commonest overflow is a toned row plus its first cell's text in
the same tone (two marks for one idea).

`show=` visuals (gallery, `shows-gallery.png`): arrows (native too), pills and data bars (card compositions).

**No cap (user, 2026-11-02).** `highlight-limits.png` draws one 15-mark table (pair 4.1) at caps 4, 6, 10 and none:
every cap leaves it half-coloured (limit 10 still drops the red Gap 5 row the slide is about); no cap matches the
LLM. So every `<Highlight>` is drawn; more than 6 gives the warning `NODE_HIGHLIGHT_LIMIT` (5 of the 66 tables here),
and the prompt says to colour a whole row or column first, then mark its exceptions (later marks win).
