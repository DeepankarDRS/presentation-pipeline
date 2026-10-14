# Card tile nodes: paid check on fresh plans (2026-10-13/14, test PC)

Spec: `docs/tile-nodes-spec-2026-10-12.md` §11. Part 1 `python -m scripts.card_plan_only --repeat 3 --label card-plans`
($1.517, 18 planner runs, `plans-summary.md`); part 2 `python -m scripts.card_paid --plans card-plans --repeat 3 --label card-paid`
($0.282, `summary.md`). Arm A = the saved hand-drawn slide on its own plan; arm B = `POM_BLOCKS=tiles` on the fresh plan's
matching card slide.

## Result

**Blind marks (user, 2026-10-14): 0.692 = B 6 / tie 6 / A 1 of 13, gate passed** (≥ 0.5; ≥ 0.6 too).
Without pair 2.1 (QBR r2: the LLM drew its 3 cards by hand, no tags) 0.667.

| pair | case | winner | reason |
|---|---|---|---|
| 1.1 | product-launch s2 r1 | tie | |
| 1.2 | product-launch s2 r2 | B | better overall |
| 1.3 | product-launch s2 r3 | tie | |
| 1.4 | QBR s4 r1 | B | more consistent |
| 2.1 | QBR s4 r2 | B (hand-drawn cards) | better context |
| 2.2 | QBR s4 r3 | B | the colour coding |
| 2.3 | agency-takeover s1 r2 | tie | both wrong |
| 2.4 | agency-takeover s4 r1 | B | more consistent |
| 3.1 | agency-takeover s4 r3 | B | better visual, colour coding |
| 3.2 | all-nodes-dense s3 r2 | tie | |
| 3.3 | XTSY s3 r1 | tie | |
| 3.4 | XTSY s3 r2 | A | a visual made for the 4-stage growth roadmap |
| 4.1 | XTSY s3 r3 | tie | both good |

## What the runs showed

- Coverage: only 14 of 36 planned slides ran; 22 skipped because the fresh plan had no card_grid on that slide (all 6
  CHEFFIN slides: the planner made no card grid in any of 3 runs). Marks cover product-launch, QBR, agency-takeover,
  all-nodes-dense and XTSY slide 3 only.
- First try 12 / 14, final 13 / 14, 0 NODE_* errors; card tag tokens mean 12; cards drawn by hand 3 (QBR r2, which also
  dropped the 3 card body lines).
- B vs A: empty cards 7 vs 0, broken words 1 vs 3, overlaps 0 vs 3, LOW_CONTRAST 0 vs 3, card body median 25 vs 20 px.
- Plan text missing 22 (B): 19 on agency-takeover s1 r2 — the planner put 8 components on one slide (table, card grids of 5
  and 9, two lists, two notes); the first try drew zero-height boxes and the two repairs cut the table and city cards
  (planner density, marked "both wrong"); 3 on QBR r2 (hand-drawn cards).
- Agency-takeover s1 r3 failed: a bare `&` ("KEYWORD & CITIES") made the expander's parse fail silently, so `<CardGrid>`
  reached POM (UNKNOWN_TAG). Fixed in `e799d56` (validator escapes bare `&` before tile / card / ref expansion).
- Planner (part 1): 16 components with unreadable `content_data_json` (missing leading `{"`, a lone `{` / `,`, a raw tab,
  and on CHEFFIN r1 a placeholder "…not shown here because of length restrictions…"). Proposed as its own session.
- Test PC has no LibreOffice / pymupdf: `--rescore --no-render` crashed; fixed in `0afc074`. Renders and sheets are built on
  the build PC.

Open: empty cards on agency-takeover s4 and XTSY s3 (7); a stage visual for growth roadmaps (the one A win).
