# Table node: free replay (LLM layout kept), arm B = <Table ref variant='grid'>

Slides: 66 (one table component with an id, one LLM-drawn <Table>); the LLM's card around it replaced too on 38. B compositions: {'grid': 58, 'native': 8}.

| | A (LLM's table) | B (Table tag) |
|---|---|---|
| compiled | 66 | 65 |
| plan items not all on the slide | 0 | 0 |
| GEOM_CARD_EMPTY | 7 | 146 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 0 | 68 |
| text overlaps (render) | 31 | 47 |
| WORD_TOO_WIDE | 13 | 39 |
| LOW_CONTRAST | 13 | 9 |
| table output tokens | 38876 | 833 (-98%) |

B issues: {'NODE_VARIANT_UNMET': 8}
