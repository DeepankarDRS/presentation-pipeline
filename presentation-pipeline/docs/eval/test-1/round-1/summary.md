# Test 1 — planning only · label `test-1`

numbers dropped = per slide section (or whole brief without sections); on no slide = whole brief, including data above the slide sections

## gate-deck-cheffin-audit

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gate-deck-cheffin-audit-29337d | n/a | 0/21 (0.0%) | 0:  | 0 | 1 | 0 | 11 | $0.092 | CPC vs allowable CPC in one component: pass, missing sheet named as a gap: pass, brand colours captured: pass |

## gate-deck-cheffin-full

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gate-deck-cheffin-full-ab2c5e | n/a | 0/38 (0.0%) | 7: 6.1, 6.4, 27.3, 41.1, 85.5, 219, 230 | 0 | 2 | 1 | 8 | $0.086 | brief headlines used on their slides 6/6: pass, CPC vs allowable CPC in one component: pass, ad-type table in one component: pass, match-type ROAS in one component: pass, brand colours captured: pass |

## gj-h1-regen

| run | headlines kept | numbers dropped | on no slide | invented | max hints/slide | slides with issues | LLM calls | cost | plan checks |
|---|---|---|---|---|---|---|---|---|---|
| gj-h1-regen-7af681 | 5/13 | 16/362 (4.4%) | 11: 2.4, 2.71, 5.2, 6.1, 13, 19.83, 22.2, 24.25 | 0 | 2 | 0 | 19 | $0.294 | — |

Pass (docs/architecture-north-star.md §9): gj-h1 headlines ≥ 12/14 (13 content slides counted), ≤ 2% numbers dropped, 0 invented, ≤ 2 hints per slide, same components on ≥ 10/14 slides; CHEFFIN plan checks pass. Headlines as conclusions: read each run's storyline.md.