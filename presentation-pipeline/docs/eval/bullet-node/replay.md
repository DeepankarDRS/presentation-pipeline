# Bullet list node: free replay (2026-11-04)

`python -m scripts.node_replay --kind bullet_list [--marks-from-llm | --variant rows] --src <main checkout>/output`
(POM_NODES on, Inter render, no LLM). 30 saved slides: one bullet_list component with an id and exactly one LLM-drawn
`<Ul>`. Arm A is the slide as the LLM wrote it; arm B replaces the `<Ul>` with one `<Ul ref>`, and the LLM's card stays.
Slides with several `<Ul>`s are not in it. Two of the 30 do not compile in either arm (both CHEFFIN `runs-same-*`).
Blind sheets, `key.json` and an empty `marks.csv` per run: `native/` (the gate: the bare tag), `native-attrs/` (the LLM's
own attributes carried onto the tag), `rows/` (a stress test: forced on boxes sized for a compact list).

| 28 compiled slides | A (LLM) | B `native` | B `native` + LLM's attributes | B `rows` |
|---|---|---|---|---|
| plan points not on the slide | 0 | 0 | 0 | 0 |
| broken words (render) | 16 | 10 | 10 | 16 |
| text overlaps (render) | 14 | 13 | 13 | 33 |
| WORD_TOO_WIDE | 7 | 7 | 7 | 9 |
| GEOM_CARD_EMPTY | 4 | 5 | 5 | 4 |
| LOW_CONTRAST | 4 | 4 | 4 | 4 |
| list output tokens | 3,657 | 298 (-92%) | 1,663 (-55%) | 418 (-89%) |

`rows` overlaps: 16 of its 33 are one slide, 7 rows in a 138 px box pushing the matrix above it (r2-xtsy-23sep-2-s2). The
prompt now says rows needs about 40 px per point. This replay ran before that line and no LLM chose these variants.

## Can the tag replicate the LLM's native attributes?

`census.json`: 47 distinct slides, 70 LLM-written lists (every saved run). On the 30 replay slides, what became of each:

| The LLM wrote | Count | On the tag |
|---|---|---|
| list `fontSize` / `lineHeight` | 30 / 30 | code-owned: starts at 16 px and 1.4, fit-grow grows it |
| list `color` | 2 (28 the default) | carried: `color` |
| list `bold`, `textAlign` | 3, 1 | carried: `detail.bold`, `textAlign` |
| `<Li>` `color` / `bold` | 12 / 11 | carried: `<Highlight item>`. Lost: 1 neutral `$textMain`, 1 point not in the plan as written |
| coloured `Span` / `B` | 22 / 2 | carried: `<Highlight phrase color>` |
| bold `B` not a head | 10 | carried: `<Highlight phrase bold>` |
| bold lead-in | 20 | code draws it |
| `Span` across head and detail, or text not in the plan | 7 | **lost**: colour is not drawn (a real generator would get `NODE_HIGHLIGHT_UNKNOWN`) |
| `<Mark>` | 37 | **changed**: words take colour, never Mark (user rule). 35 were literal yellow hex; the replay maps them to `watch` |
| inline `fontSize` | 7 | code-owned (unit sizing inside a list is not reproduced) |
| `<Icon>` in `<Li>` | 3 | POM strips them; `rows` + `icons` is the way |

Marks per slide: 8 slides none, 3 slides past the warning of 6 (8, 17, 17: a yellow highlight on every number). All are drawn.

## Limits

- No real generator wrote these tags. The marks are built from saved colours by `bullet_marks`, so this says the tag *can*
  express them, not that a generator *will*. Highlight needs its own paid check (ask first).
- LibreOffice render plus slide XML; PowerPoint itself not opened.
- In a 360 px side panel a native list stops at 17 px (fit-grow's 88% fill limit); the rest goes into point spacing. It
  sat at 20 px with 4 px gaps when started larger, which broke words in narrow boxes elsewhere.
- Past 6 points `rows` drops icons for dots with a report: rows that short never start growing (fit-grow needs 30 px spare).
