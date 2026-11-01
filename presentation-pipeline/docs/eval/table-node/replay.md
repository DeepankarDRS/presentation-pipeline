# Table node: free replay (2026-11-01)

`python -m scripts.node_replay --kind table [--variant rows|columns|banded] --src <main checkout>/output` (POM_NODES
on, Inter render, no LLM). 66 saved slides: one table component with an id, one LLM-drawn `<Table>`. Arm A is the
slide as the LLM wrote it. Arm B replaces the LLM's table (and its card on 38 slides) with one `<Table ref>` that keeps
the LLM's layout attributes. Blind sheets are in `output/table-replay[-<variant>]/sheets/`; `key.json` and an empty
`marks.csv` per run are in this folder (`native/`, `rows/`, `columns/`, `banded/`).

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
rule). The `rows/`, `columns/` and `banded/` marks are optional; they say whether a word should stay on offer.
