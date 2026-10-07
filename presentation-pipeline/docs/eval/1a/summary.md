# 1a node test: 1a

32 slides, 76 components · LLM `real` · commit `a2d0240`

## Kill criteria

- 1 compliance 93% (76 components; margin about ±7 points) -> pass, re-run zone
- 2 invented words in nodes 0 -> pass
- 3 broken words 0 vs off 6; overlap slides 2 vs 4 -> pass
- 4 blind side-by-side: scripts/node_test_sheet.py (your marks)
- 5 within-deck variety 1.0 vs off 1.0 -> pass

## Detail

- compliance: derived 0.974, native 0.892, slides all ok 0.969; status {'ok': 71, 'bypassed': 1, 'attr': 4}; unknown refs 0
- cross-deck (informational): nodes {'cross_deck_sameness': 0.6, 'cross_deck_pairs': 5, 'house_template_share': 0.094, 'house_template': 'V(V(text,text),cards)'}; off {'cross_deck_sameness': 0.0, 'cross_deck_pairs': 5, 'house_template_share': 0.031, 'house_template': 'V(V(text,text,text),V(text,text,text))'}
- tokens per slide (32 slides): off in 11708 / out 1036 / cached 724; nodes in 10489 / out 256 / cached 2396; nodes arm cost $0.7368
- fallback: repaired 0, error on first try 1, overfull 1, not compiled 2
- variants: {'plain': 33, 'cards': 4, 'rail': 3, 'native': 5, 'rule': 13, 'tinted': 2, 'outline': 9, 'accent_top': 3, 'quote': 1, 'boxes': 1, 'chevrons': 1}; LLM left the default 0.727

## Slides

| case | slide | all ok | repairs | first-try issues | invented | broken (nodes / off) |
|---|---|---|---|---|---|---|
| deck-product-launch-data | 2 | True | 0 | - | 0 | 0 / 0 |
| deck-product-launch-data | 3 | True | 0 | - | 0 | 0 / 5 |
| deck-product-launch-data | 4 | True | 0 | - | 0 | 0 / 0 |
| deck-product-launch-data | 5 | True | 0 | NODE_BYPASSED | 0 | 0 / 0 |
| deck-product-launch-data | 6 | True | 0 | - | 0 | 0 / 0 |
| deck-qbr-data | 2 | True | 0 | NODE_NO_SIZE, NODE_NO_SIZE | 0 | 0 / 0 |
| deck-qbr-data | 3 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| deck-qbr-data | 4 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| deck-qbr-data | 5 | True | 0 | - | 0 | 0 / 0 |
| gate-deck-agency-takeover | 1 | True | 0 | NODE_ATTR_IGNORED, NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-agency-takeover | 2 | True | 0 | NODE_NO_SIZE, NODE_NO_SIZE, NODE_OVERFULL | 0 | - / 0 |
| gate-deck-agency-takeover | 3 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-agency-takeover | 4 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-agency-takeover | 5 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-agency-takeover | 6 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-all-nodes-dense | 1 | True | 0 | NODE_ATTR_IGNORED | 0 | 0 / 0 |
| gate-deck-all-nodes-dense | 2 | True | 0 | NODE_NO_SIZE, NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-all-nodes-dense | 3 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-all-nodes-dense | 4 | False | 0 | NODE_EXPAND_FAILED | 0 | - / 0 |
| gate-deck-all-nodes-dense | 5 | True | 0 | - | 0 | 0 / 0 |
| gate-deck-all-nodes-dense | 6 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-cheffin-full | 1 | True | 0 | - | 0 | 0 / 0 |
| gate-deck-cheffin-full | 4 | True | 0 | - | 0 | 0 / 0 |
| gate-deck-cheffin-full | 5 | True | 0 | NODE_NO_SIZE, NODE_NO_SIZE, NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-cheffin-full | 6 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-xtsy-qcomm | 1 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-xtsy-qcomm | 2 | True | 0 | - | 0 | 0 / 0 |
| gate-deck-xtsy-qcomm | 3 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-xtsy-qcomm | 4 | True | 0 | NODE_ATTR_IGNORED | 0 | 0 / 1 |
| gate-deck-xtsy-qcomm | 5 | True | 0 | NODE_ATTR_IGNORED, NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-xtsy-qcomm | 7 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
| gate-deck-xtsy-qcomm | 8 | True | 0 | NODE_NO_SIZE | 0 | 0 / 0 |
