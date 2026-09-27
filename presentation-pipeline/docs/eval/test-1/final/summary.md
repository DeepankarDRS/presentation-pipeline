# Test 1 — planning only · label `test-1-final`

numbers dropped = per slide section (or whole brief without sections); on no slide = whole brief, including data above the slide sections

## gate-deck-cheffin-audit

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gate-deck-cheffin-audit-4a628c | n/a | 0/21 (0.0%) | 0:  | 0 | 1 | 0 | 11 | $0.115 | CPC vs allowable CPC in one component: pass, missing sheet named as a gap: pass, brand colours captured: pass |
| gate-deck-cheffin-audit-65d54f | n/a | 0/21 (0.0%) | 0:  | 0 | 1 | 0 | 11 | $0.112 | CPC vs allowable CPC in one component: pass, missing sheet named as a gap: pass, brand colours captured: pass |
| gate-deck-cheffin-audit-6e7be4 | n/a | 0/21 (0.0%) | 0:  | 0 | 1 | 0 | 10 | $0.104 | CPC vs allowable CPC in one component: pass, missing sheet named as a gap: pass, brand colours captured: pass |

Plan stability: 2/6 slides with the same component kinds in all 3 runs

## gj-h1-regen

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gj-h1-regen-534e32 | 13/13 | 0/354 (0.0%) | 0:  | 0 | 2 | 0 | 21 | $0.330 | — |
| gj-h1-regen-9d3f22 | 13/13 | 2/354 (0.6%) | 0:  | 0 | 2 | 1 | 22 | $0.352 | — |
| gj-h1-regen-f56a45 | 13/13 | 9/354 (2.5%) | 7: 1.42, 4.78, 8.25, 20.3, 20.9, 27.45, 34.8 | 0 | 2 | 1 | 21 | $0.323 | — |

Plan stability: 8/14 slides with the same component kinds in all 3 runs

Pass (docs/architecture-north-star.md §9): gj-h1 headlines ≥ 12/14 (13 content slides counted), ≤ 2% numbers dropped, 0 invented, ≤ 2 hints per slide, same components on ≥ 10/14 slides; CHEFFIN plan checks pass. Headlines as conclusions: read each run's storyline.md.