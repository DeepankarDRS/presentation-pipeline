# Timeline / process_arrow / flow nodes: free replay (2026-10-28)

Command: `python -m scripts.node_replay --kind <timeline|process_arrow|flow> --src <main checkout>/output` (bare tags, Inter render). Blind sheets and `marks.csv` in `output/<kind>-replay/sheets/`.

## 2026-11-02: timeline with the alternating rail as default (process / flow nodes dropped)

The bare tag now draws `native` (short labels), `rail` (dots on a line, date / head / detail alternating above and
below; ≤ 7 points) or `columns` (the old box-per-point rail); a vertical timeline that is not native draws `rows`
(rail and columns lay points side by side; `NODE_VERTICAL_ROWS`, render: `vertical-check.png`).

Fixes after the first runs:
- Six-point slides spilled their card (one text per sixth of the width): each text now spans two dot gaps (n + 1
  units, dot k at k + 1), neighbours on one side touch, none passes the edge.
- On 6 slides the LLM had drawn POM's timeline with short titles and typed the details itself beside it (a row of
  month notes, a list). Arm B kept that copy while the rail drew the details too, so they showed twice (user,
  2026-11-02). The replay now drops the LLM's own copy beside the tag (a sibling of ≥ 6 words, ≥ 60% the
  timeline's own); the generator line says "never type a date, label or detail yourself, beside it either".

Slides: 23 (one timeline component with an id, one LLM-drawn <Timeline>); the LLM's card around it replaced too on 1; the LLM's own copy of its words beside it dropped on 6. B compositions: {'rail': 17, 'native': 6}. Skipped (not well-formed XML): 1.

| | A (LLM's timeline) | B (Timeline tag) |
|---|---|---|
| compiled | 23 | 23 |
| plan items not all on the slide | 28 | 0 |
| GEOM_CARD_EMPTY | 7 | 1 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 11 | 11 |
| text overlaps (render) | 22 | 7 |
| WORD_TOO_WIDE | 5 | 5 |
| LOW_CONTRAST | 1 | 1 |
| timeline output tokens | 3377 | 342 (-90%) |

B issues: {'NODE_DEFAULT_FROM_CONTENT': 17, 'NODE_TEXT_SPLIT': 8}

### Earlier (2026-10-28, cards default)

## Timeline node: free replay (LLM layout kept), arm B = <Timeline ref>

Slides: 23 (one timeline component with an id, one LLM-drawn <Timeline>); the LLM's card around it replaced too on 1. B compositions: {'rail': 17, 'native': 6}. Skipped (not well-formed XML): 1.

| | A (LLM's timeline) | B (Timeline tag) |
|---|---|---|
| compiled | 23 | 23 |
| plan items not all on the slide | 28 | 0 |
| GEOM_CARD_EMPTY | 7 | 18 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 11 | 11 |
| text overlaps (render) | 22 | 16 |
| WORD_TOO_WIDE | 5 | 5 |
| LOW_CONTRAST | 1 | 1 |
| timeline output tokens | 3377 | 342 (-90%) |

B issues: {'NODE_DEFAULT_FROM_CONTENT': 17, 'NODE_TEXT_SPLIT': 8}

## ProcessArrow node: free replay (LLM layout kept), arm B = <ProcessArrow ref>

Slides: 21 (one process_arrow component with an id, one LLM-drawn <ProcessArrow>); the LLM's card around it replaced too on 5. B compositions: {'native': 18, 'steps': 3}.

| | A (LLM's process_arrow) | B (ProcessArrow tag) |
|---|---|---|
| compiled | 21 | 21 |
| plan items not all on the slide | 2 | 0 |
| GEOM_CARD_EMPTY | 4 | 2 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 9 | 9 |
| text overlaps (render) | 3 | 3 |
| WORD_TOO_WIDE | 6 | 6 |
| LOW_CONTRAST | 5 | 5 |
| process_arrow output tokens | 3027 | 394 (-87%) |

B issues: {'NODE_DEFAULT_FROM_CONTENT': 5, 'NODE_TEXT_SPLIT': 3}

## Flow node: free replay (LLM layout kept), arm B = <Flow ref>

Slides: 16 (one flow component with an id, one LLM-drawn <Flow>); the LLM's card around it replaced too on 0. B compositions: {'native': 16}.

| | A (LLM's flow) | B (Flow tag) |
|---|---|---|
| compiled | 16 | 16 |
| plan items not all on the slide | 0 | 0 |
| GEOM_CARD_EMPTY | 5 | 6 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 19 | 16 |
| text overlaps (render) | 8 | 1 |
| WORD_TOO_WIDE | 9 | 7 |
| LOW_CONTRAST | 1 | 1 |
| flow output tokens | 4481 | 277 (-94%) |

B issues: {}

## Notes

- Fixed before this run (`cbe7b8f`): an `h` the LLM sized for another drawing (a 92 px chevron row drawn as step
  boxes) is now a floor; process overlaps on those 2 slides 7 -> 0. A saved slide that is not well-formed XML is
  skipped (1 timeline).
- **Timeline empty cards 7 -> 18** come from 6 slides, 5 of them the product-launch deck: the LLM pinned its native
  timeline at `h="150"`; its labels carry details, so the bare tag draws `rail`, the height becomes a floor, the band
  grows and the short rail boxes stand mostly empty. Not changed before the marks (one deck): options are keeping
  the LLM's `h` when the slide has no spare height, or growing the rail text further.
- Plan items not all on the slide: the LLM's timelines dropped or re-cut words of 28 points (A); the tags 0.
