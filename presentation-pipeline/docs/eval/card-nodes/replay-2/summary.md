# Card tile nodes: free replay (LLM layout kept)

Slides: 80 with a card_grid plan; 75 replayed; 5 skipped (card 0 title not on the slide 4, no cards in the plan; no cards in the plan 1).

| | A (LLM's cards) | B (CardGrid tag) |
|---|---|---|
| compiled | 75 | 74 |
| GEOM_CARD_EMPTY | 44 | 54 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| broken words (render) | 5 | 5 |
| text overlaps (render) | 6 | 5 |
| WORD_TOO_WIDE | 2 | 2 |
| LOW_CONTRAST | 20 | 7 |
| plan text missing (lines) | 0 | 0 |
| card title px, median of the smallest | 22.0 | 26.0 |
| card body px, median of the smallest | 21.0 | 23.0 |
| card output tokens | 46094 | 930 (-98%) |

Stand-ins read from the LLM's drawing (old plans have no focus_card / tone / key_phrase):
- focus card (one dark card): 19
- cards with a tone: 21
- key phrases: 22
- card groups with icons: 73
- B issues: {'NODE_BYPASSED': 2, 'NODE_FIELD_MISSING': 8}
