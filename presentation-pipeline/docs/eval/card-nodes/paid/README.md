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

## Empty-card fixes (2026-10-14, free, re-scored with `card_paid --rescore --refill`)

- fit-grow: the cards of one card_grid (ids `card-<cid>-<i>`) grow as one group across their rows, and a group's
  inner stacks are not grown alone after it (XTSY 4-phase grid: rows 28 / 23 px → one size 24 px; agency 30/60/90:
  the middle step 27 px beside 20 / 20 → 20 / 20 / 20).
- cards.py: a steps row gives each card a width share by its text (sqrt, 0.7–1.6) when the texts differ ≥ 1.5×;
  grid rows keep equal columns.
- Empty cards (B) 7 → 4; the 4 left: two cards of planner instruction text (XTSY r2 "Visual: 4-stage growth roadmap",
  "Progression"), two on the 8-component agency-takeover slide. `summary-after-fixes.md`.

**Re-marked pairs (user): 2.4 B, 3.1 B, 3.4 A → still 0.692** (`marks-after-fixes.csv`). Notes: 3.1 "I need points or
a new line between the points" (a step body of several sentences runs as one paragraph); 3.4 the planner made an
arrow-diagram brief a card_grid (not a card problem).

## Step bodies as points (2026-10-14, free, user's note on pair 3.1)

A steps card whose body holds several sentences or "a; b; c" items draws one point per line (a `<Ul>`, the plan's
words unchanged; a split needs a capital or "[" after the full stop, so "0.25x." mid-sentence stays whole). Grids keep
their body line. The list carries the body id so fit-grow grows it. Re-scored (`--rescore --refill`): agency 30/60/90
r3 and XTSY phases r3 now read as points; the cost is smaller type where the fullest card fills (XTSY r3 titles
26 → 22 px, points 16 px vs a 19 px paragraph; agency r3 titles 20 → 18 px). Empty cards unchanged (4).

## The 4 empty cards on the merged branch (2026-10-14, free; tile-nodes session after the merge)

Re-scored on `feat/tile-nodes` after merging `feat/tile-cards` (`card_paid --label cp-merged --rescore --refill
--no-render`): empty cards (B) still 4, the same two slides; both come from the plan, not from the card drawing:
- XTSY s3 r2 (2): the planner made a 5th card "Progression" out of the brief's visual direction ("4-stage growth
  roadmap"); its body is an arrow chain, not a card's content. `PLAN_INSTRUCTION_TEXT` does not catch it.
- agency-takeover s1 r2 (2): the 8-component slide (planner density, marked "both wrong").
No card code change. Follow-ups: planner density, a stage visual for growth roadmaps, instruction text as a card.
