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
| bullet_list output tokens | 3657 | 298 (-92%) |

B issues: {}
