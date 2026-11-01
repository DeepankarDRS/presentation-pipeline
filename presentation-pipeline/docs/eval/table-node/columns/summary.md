# Table node: free replay (LLM layout kept), arm B = <Table ref variant='columns'>

Slides: 66 (one table component with an id, one LLM-drawn <Table>); the LLM's card around it replaced too on 38. B compositions: {'columns': 51, 'native': 15}.

| | A (LLM's table) | B (Table tag) |
|---|---|---|
| compiled | 66 | 63 |
| plan items not all on the slide | 0 | 13 |
| GEOM_CARD_EMPTY | 7 | 43 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 0 | 0 |
| text overlaps (render) | 31 | 39 |
| WORD_TOO_WIDE | 13 | 7 |
| LOW_CONTRAST | 13 | 9 |
| table output tokens | 38876 | 833 (-98%) |

B issues: {'NODE_VARIANT_UNMET': 15}
