# Ul node: free replay (LLM layout kept), arm B = <Ul ref>

Slides: 30 (one bullet_list component with an id, one LLM-drawn <Ul>); the LLM's card around it replaced too on 0. B compositions: {'native': 30}.

| | A (LLM's bullet_list) | B (Ul tag) |
|---|---|---|
| compiled | 28 | 28 |
| plan items not all on the slide | 0 | 0 |
| GEOM_CARD_EMPTY | 4 | 5 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 16 | 10 |
| text overlaps (render) | 14 | 13 |
| WORD_TOO_WIDE | 7 | 7 |
| LOW_CONTRAST | 4 | 4 |
| bullet_list output tokens | 3657 | 1663 (-55%) |

B issues: {'NODE_HIGHLIGHT_LIMIT': 3}
Highlights from the LLM's colours: 22 slides with marks; marks per table {0: 8, 1: 9, 2: 5, 3: 2, 5: 2, 6: 1, 8: 1, 17: 2} (more than 6: 3)

What became of the LLM's native list attributes:

- Icon in Li: POM strips it (rows + icons replaces it): 3
- Mark: changed to colour (user rule): 37
- bold lead-in: code draws it: 20
- inline B bold: carried: 10
- inline B colour: carried: 2
- inline Span colour: carried: 22
- inline Span: lost (words not one piece of the plan's point): 7
- inline Span: no effect: 3
- inline fontSize: code-owned: 7
- li bold: carried: 11
- li bold: lost (point not in the plan as written): 1
- li color: carried: 12
- li color: lost ($textMain): 1
- list bold: carried: 3
- list color: carried: 2
- list color: default: 28
- list fontSize: code-owned: 30
- list lineHeight: code-owned: 30
- list textAlign: carried: 1
