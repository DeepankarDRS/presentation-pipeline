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

## Blind marks (user, 2026-11-04): passed

`native/marks.csv` on the bare tag, `native/sheets/key.json`: **node 17, LLM's list 5, same 6 of 28 = 0.82 with ties
satisfied, 0.77 with ties left out.** These marks are on the sheets in `native/sheets/`, drawn before the changes below;
the changed slides have not been marked again. Before and after: `after-marks.png`.

| Your reason | Pairs | What changed |
|---|---|---|
| grow the type first, spacing only with what is left | 1.4, 3.4, 6.1, 6.2, 7.4 | fit-grow `spaceLists`: type up to 28 px first, then the gaps. Sizes: 3.4 18 -> 19, 4.3 16 -> 18, 7.1 20 -> 28, 2.3 16 -> 19 |
| a card title it would pass grows with it | (same) | hierarchy kept; without this 2.3 stayed at 16 px with 24 px gaps |
| side-by-side columns | 2.2, 4.3 | columns of a split list share one size and one gap, so their rows are level (2.2: 29 and 38 px -> 29 and 29) |
| spacing is a style choice | 2.4, 7.4 | `spacing="tight"` on native: no gaps, at the top of its box |
| bullet colour matches the theme | 4.1, 4.2 | already the default: accent markers |

Not changed:

- **1.4** stays at 18 px with 27 px gaps. At 19 px one more line wraps by POM's measure (155 -> 199 px of a 209 px box),
  past the 92% limit. POM measures wider than the render, so the slide looks as if it has room.
- **3.1, 7.3** "like the colour code": the bare tag has no colour, by design; that is `<Highlight>`, which the `native-attrs`
  run carries over from the LLM. Whether a real generator writes it is the paid check still owed.
- **6.4** "I do not need 2 recommendation": the card's title and the point's head are the same word. The LLM's own card
  title repeats the plan, on one slide: left alone (no rule for one example).

Numbers after the changes: the bare-tag table above is unchanged. `native-attrs/` and `rows/` were not re-run; their tables
are from before these changes.

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
- Slides with several `<Ul>`s are not covered; `native numbered` is checked in the gallery only.
- Past 6 points `rows` drops icons for dots with a report: rows that short never start growing (fit-grow needs 30 px spare).
