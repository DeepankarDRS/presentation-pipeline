# Genspark component and diagram variants (2026-10-06)

Input for the block catalogue and the slot contract (`docs/derived-nodes-design.md` §14.6,
variants per block, decision #5 of §14.2 as changed in §14.6). Synthetic content (BREWLY, the
coffee brand of the `gate-deck-all-nodes*` cases), so no client data.

## Setup

Two prompts (full text in `prompts.md`), each with the same fixed design system (colours,
Inter + JetBrains Mono, sizes, margins, card style) and the rule "use ONLY the content given":

- **Prompt A**, 14 slides: header, KPI (4 metrics, hero, 8 metrics), card grid (7 levers, 3
  levers, titles only), steps, table, chart, bullets, callout, closing — 2–4 tagged variants each.
- **Prompt B**, 12 slides: timeline, process, linear flow, branching flow, 2×2 matrix, pyramid,
  tree, hub — 2–4 tagged variants each.

Four runs, one free account each: Super Agent A and B (python-pptx, received as PDF) and AI
Slides A and B (HTML, received as screenshots, 3 slides per image, so small details are
approximate). Super Agent PDFs were read with pymupdf (text, font, size and colour per line).
Not yet received: AI Slides B slide 4 (PROCESS-A / B); the variant tables Super Agent wrote in
chat (A and B) and AI Slides A's. AI Slides B put its table on slide 13.

## Results per run

### Super Agent A (14 slides, PDF)
- Spec followed exactly: Inter and JetBrains Mono embedded, the given colours, 22 pt headline,
  13 pt subtitle, 9 pt tags; every variant tag present. **No number outside the prompt.**
- Every slide repeats the cover header ("PERFORMANCE / BREWLY growth review, H1 FY27 /
  Component variant gallery"): the prompt gave no per-slide headlines and it wrote none.
- Header variants A–D barely differ (left rule, underline). CARD-A–D came out as one-line
  pill rows, not cards; outline vs filled is hard to tell apart.
- Unfilled space: tall tiles with the value at the top (KPI-E/F supporting tiles, KPI-H,
  CARD-F). KPI-D "trend note" is real only on Revenue (+38%); the other three repeat "H1 FY27".
- Default drop shadow on every panel and tile; CARD-H leaves Loyalty alone on the last row.
- Good: KPI-C inverted tile, KPI-E dark hero with a teal "+38%" pill, KPI-G two tiers with a
  muted second tier, STEPS-A vertical rail, STEPS-B 2×2 numbered cards, TABLE-D dark header band
  + teal ROAS column, CHART-D labelled bars with one dark bar, BULLET-B square icon bullets, the
  four callouts.

### AI Slides A (14 slides, screenshots)
- Per-slide claim headlines ("Four metric tiles, four treatments") and named variants
  ("HEADER-A classic, B display, C ruled, D inverted"). High variety.
- **Content changed:** lever lines shortened to fit small cards in CARD-C ("Refill plan",
  "No gaps.", "One ladder", "Points.", titles cut to "Subscribe", "Cities", "Available");
  descriptions added under KPI-G's secondary tiles ("AOV across all channels", "Total orders
  in the half", "Acquired on site or app"); filler on the closing slide ("The shape of H1 FY27
  in one breath.") and the cover ("Nine components, thirty-eight variants").
- Layout bugs: KPI-E "+38%" over "Cr"; CALLOUT-D quote mark over "Website"; TABLE-D last row
  near or past the panel edge (unclear at this size).
- Good: real 4 + 3 card grids, CARD-B filled accent cards, CARD-C one featured dark card,
  CARD-D faint numerals, CARD-F stacked rows with numerals (fills well), KPI-B filled tiles,
  KPI-F full-width dark hero, STEPS-A columns with numerals, STEPS-B rail over cards, HEADER-D
  inverted, the editorial close.

### Super Agent B (12 slides, PDF)
- **Fonts fell back** to Noto Sans / DejaVu Sans (A, same design system, other account: Inter).
- Content faithful: every label from the prompt, every tag present, nothing added. Matrix
  quadrant names placed by meaning (Quick wins top-left, Skip bottom-right); the prompt did not
  say where each quadrant name goes.
- Topic titles ("90-day plan", "Customer path"), subtitle = variant names.
- **Diagrams do not fill their panels:** TIMELINE-A, PROCESS-A–D, FLOW-A/B sit as a thin band
  in a tall panel (the same gap our process-steps block shows in the nodes demo, 2026-10-05).
- Weak: PYRAMID-A lower levels near-white on cream; HUB-A faint spokes; summary thumbnails
  without content.
- Good: TIMELINE-B one card per item, C vertical, D columns with a progress bar (all keep long
  labels whole); PROCESS-C circles on a line with labels alternating above and below; PROCESS-D
  step cards with a dark destination; FLOW-B engine card holding the middle steps; FLOW-C loop
  arrow; MATRIX-B quadrant cards; PYRAMID-B stacked bars; TREE-A org chart with leaf chips;
  HUB-B dark centre card.

### AI Slides B (13 slides, screenshots; slide 4 missing)
- Claim headlines, a structure caption under every panel ("ONE RAIL · 90 DAYS · FOUR DOTS"),
  diagrams fill their panels, all four timelines handle long labels; slide 13 is its variant
  table (tag, differentiator, long-label handling).
- **Content added:** PROCESS-C a line per step ("Opens the path", "Selection saved", "Order
  placed", "Packed for route", "On the doorstep"); FLOW-B "Read signals, pick a bid, push it
  back."; FLOW-C a "BUDGET LIVE" end state; MATRIX-B "Major projects, plan carefully.";
  PYRAMID-A "Base is the load-bearing priority; the apex is the loyalty goal."; the cover says
  "06 … six diagram types" and "7 diagram types · 19 variants".
- Layout bugs: PYRAMID-A malformed (top level cut, "Loyalty" not visible); FLOW-B outcome card
  clipped at the panel edge; TREE-A "Pricing" chip past the panel edge; HUB-B centre card tiny.
- Good: TIMELINE-D columns with a "12 WEEKS" progress bar, PROCESS-D, FLOW-B dark engine card,
  FLOW-C teal decision diamond, MATRIX-A axes with LOW / HIGH, MATRIX-B quadrant cards with a
  coloured edge and "no items" for an empty quadrant, PYRAMID-B stacked bars darkest at the base,
  TREE-B dark lead bar with group cards and chips, HUB-A dark centre "THE ENGINE".

## Comparison

| | Super Agent A | Super Agent B | AI Slides A | AI Slides B |
|---|---|---|---|---|
| Font / colour spec | exact (Inter embedded) | fonts fell back | close | close |
| Content kept as given | yes | yes | no: shortened + added | no: added in 5 places |
| Per-slide headline | no (cover header) | topic | claim | claim |
| Variety between variants | low | medium | high | high |
| Fills the space | often not | often not | mostly | mostly |
| Layout bugs | none seen | faint pyramid / spokes | 2 overlaps | 4 |

## Learnings

1. **Fidelity and design trade off in both engines.** Super Agent copies content exactly and
   draws plainly with empty space; AI Slides designs well but shortens and adds text, and
   nothing checks it. The §14.6 blocks aim at both: AI Slides' variety, text copied from the plan.
2. **Shortening text to fit is how a free design engine breaks content.** Blocks never reword;
   they measure, grow or step type, re-flow (rows, columns, vertical), or switch variant.
3. **Neither engine guarantees "fill the slot".** Super Agent leaves thin bands, AI Slides fills
   but clips edges. Measured sizing is the part neither has; process steps and timeline must
   grow into a tall slot (open since the nodes demo).
4. **Fonts must be embedded by the pipeline.** One design system gave Inter on one account and
   Noto / DejaVu on another (supports §14.6 step 0 font embedding).
5. **Long labels need layouts that give room, not smaller text:** vertical timelines, columns,
   one card per item, labels alternating above and below a line.
6. **Captions and descriptions the brief did not give** are "inferred" content (§12): blocks
   never create them; a planner may propose them, flagged for Keep / Remove.
7. **A spec in the prompt is not enough to get a frame:** with no per-slide headlines in the
   brief, one engine repeated the cover header on every slide. The `SlideHeader` block plus
   planned headlines covers this.
8. **Design ideas that transfer to POM** (all compositions of primitives): dark hero tile with a
   pill, one inverted tile, featured card, faint numerals, dark table header band with an accent
   column, labelled bars with one highlight, engine card grouping middle steps, quadrant cards,
   stacked bars instead of a pyramid, chips for tree leaves, dark hub centre, progress bar over
   columns. Effects to avoid or check in POM: default shape shadows (flatten hierarchy).
9. **Prompt lesson for re-runs:** give quadrant positions explicitly; ask for per-slide claim
   headlines; ask for the variant table as a slide (AI Slides did, Super Agent did not).

## Variant shortlist per block (draft for the slot contract)

| Block | Variants the LLM may choose | Adapted by code, not a variant |
|---|---|---|
| KPI row | plain · filled · one inverted tile · hero (dark, pill) | two tiers at 6+ metrics; number size to the tile |
| Card grid | outline · filled · one featured large card · large faint numerals | 3 items → stacked rows; titles only → ruled list; no orphan last row |
| Card steps | numbered cards · vertical rail with phases · columns with a progress bar | — |
| Table | plain · zebra · highlighted row · dark header + accent column | column widths measured |
| Chart | labelled bars + one highlight · horizontal bars · line | — |
| Bullets | plain · icon · tiles · two columns | tiles only when every word fits |
| Callout | rule · tinted panel with edge · dark panel · quote | — |
| Header | standard · inverted dark band | — |
| Timeline | rail with dots (short labels) · rail + one card per item · vertical · columns with a progress bar | long labels → cards or vertical |
| Process steps | chevrons · numbered circles + boxes · circles on a line, labels alternating · step cards, destination dark | grow to fill a tall slot |
| Linear flow | boxes and arrows · engine card grouping the middle steps | — |
| Step 4 (no block yet) | matrix: quadrant cards / dots with axes · pyramid: stacked bars · tree: org chart with chips / indented groups · hub: dark centre · branching flow: boxes + decision diamond | — |

Next: confirm against the variant tables still to come and the user's own gj-h1 / XTSY /
CHEFFIN / Platform A notes, then write the catalogue into the slot-contract draft.

Local files (not in git): Super Agent PDFs on the user's PC
(`Downloads/superagent_BREWLY_component_variant_gallery.pdf`,
`Desktop/superagent_BREWLY_diagram_variants.pdf`); AI Slides screenshots in the session.
