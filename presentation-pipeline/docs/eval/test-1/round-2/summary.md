# Test 1 — planning only · label `test-1b`

numbers dropped = per slide section (or whole brief without sections); on no slide = whole brief, including data above the slide sections

## gate-deck-cheffin-audit

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gate-deck-cheffin-audit-0352c8 | n/a | 0/21 (0.0%) | 0:  | 0 | 2 | 1 | 10 | $0.104 | CPC vs allowable CPC in one component: FAIL, missing sheet named as a gap: pass, brand colours captured: pass |

## gj-h1-regen

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gj-h1-regen-bfe3d4 | 13/13 | 10/362 (2.8%) | 2: 0.6, 13 | 0 | 2 | 0 | 21 | $0.322 | — |

Pass (docs/architecture-north-star.md §9): gj-h1 headlines ≥ 12/14 (13 content slides counted), ≤ 2% numbers dropped, 0 invented, ≤ 2 hints per slide, same components on ≥ 10/14 slides; CHEFFIN plan checks pass. Headlines as conclusions: read each run's storyline.md.