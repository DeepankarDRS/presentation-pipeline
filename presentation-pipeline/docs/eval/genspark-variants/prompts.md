# Prompts used for the variant runs (2026-10-06)

Each prompt was run once in Genspark AI Slides and once in Genspark Super Agent, each run in a
fresh account (four runs). Results: `summary.md`. Lessons for a re-run are in `summary.md`,
Learnings §9 (quadrant positions, per-slide claim headlines, the variant table as a slide).

## Shared design system block (in both prompts)

```text
DESIGN SYSTEM (use exactly these values; do not change them per slide)
- Canvas 16:9. Sizes below are px on a 1920x1080 canvas; in PowerPoint use half the number as pt
  (44 px = 22 pt).
- Colours: background FFFFFF · panel F6F3EF · ink 1C1A17 · muted text 6B645C · lines E3DDD5 ·
  accent (coffee) 7A4A2A · secondary (teal) 0F8B8D · highlight panel 1C1A17 with white text ·
  positive 2E7D4F · negative B23A2E.
- Fonts: Inter for all text (Arial if Inter is not available); JetBrains Mono for small labels and
  tags (Consolas if not available).
- Header on every slide: kicker 22 px mono, uppercase, muted, letter-spaced · headline 44 px bold
  ink · subtitle 26 px muted · a 1 px line under the header.
- Footer on every slide: 1 px line, then "BREWLY" left and "NN / NN" page number right, 18 px muted.
- Margins 96 px left and right, 72 px top and bottom. Gap between panels 32 px.
- Cards: panel colour F6F3EF, 1 px border E3DDD5, corner radius 12 px, padding 32 px.
- Variant tag: top-left of each panel, 18 px mono, teal, uppercase.
- Body text never below 24 px (12 pt); small labels never below 18 px (9 pt).
```

## Prompt A: data components

```text
Create a 14-slide "component variant gallery" deck for an internal design review. It is NOT a client
pitch: its job is to show several visual variants of the same slide component, so a design team can
compare them and pick a house style.

[DESIGN SYSTEM block above]

RULES (apply to every slide)
- Use ONLY the content given below. Do not add numbers, names, sources, dates or list items. If a
  variant needs a short label, use the labels given. No source lines, no "illustrative" data.
- Every variant keeps the same content; only the design changes.
- Put the variant tag exactly as listed on every variant panel, e.g. "KPI-A  plain tiles". These
  tags are how the review maps variants, so never omit, merge or rename them.
- Slides with several variants: lay the variants out as equal panels (2 or 4 per slide).
- Indian number formats: ₹, L for lakhs, Cr for crores, ROAS as "2.4x", growth as "+38%".
- After the deck, write a short table, one row per variant tag: what makes it different
  (fills, borders, type sizes, number size, spacing, emphasis treatment).

CONTENT
Brand: BREWLY, a direct-to-consumer specialty coffee brand selling on its website and on two
quick-commerce apps, QUIKMART and DASHCART.

Metrics (H1 FY27): Revenue ₹4.2 Cr (+38%) · Ad spend ₹96 L · ROAS 2.4x · Repeat rate 31% ·
Average order ₹540 · Orders 77.8K · New customers 41.2K · Cart abandonment 64%

Platform table:
| Channel  | Revenue  | Ad spend | ROAS | Repeat rate |
| Website  | ₹1.9 Cr  | ₹38 L    | 3.1x | 36% |
| QUIKMART | ₹1.4 Cr  | ₹33 L    | 2.2x | 28% |
| DASHCART | ₹0.9 Cr  | ₹25 L    | 1.8x | 24% |

Monthly revenue (₹ L): Jan 58, Feb 61, Mar 66, Apr 72, May 79, Jun 84

Growth levers (title + one line each):
1. Search share: exact-match bids on the 40 hero keywords
2. Bundles: 2-pack and gift box on both apps
3. Subscriptions: monthly refill plan on the website
4. City expansion: launch in the next six cities
5. Availability: no stock-outs on the top 12 SKUs
6. Pricing: one price ladder across all channels
7. Loyalty: points on every repeat order

Key message: "Website customers come back; the apps bring them in."
Closing statement: "Grow where customers return, buy reach where they discover."

SLIDES
1. Cover: title "BREWLY growth review, H1 FY27", subtitle "Component variant gallery".
2. HEADER-A/B/C/D: the same content slide header (kicker "PERFORMANCE", headline "Revenue grew 38%
   while ROAS held at 2.4x", subtitle "₹4.2 Cr revenue · ₹96 L ad spend · 2.4x ROAS") drawn four ways,
   including the footer "BREWLY · 02 / 14".
3. KPI-A/B/C/D, 4 metrics (Revenue, Ad spend, ROAS, Repeat rate): A plain tiles, B filled tiles,
   C one highlighted tile (ROAS), D tiles with a small trend note under each value.
4. KPI-E/F: one hero number (Revenue ₹4.2 Cr, +38%) with the other three as supporting tiles,
   two ways.
5. KPI-G/H: all 8 metrics, two ways (two tiers vs one dense grid).
6. CARD-A/B/C/D, the 7 growth levers as cards: A outline cards, B filled cards, C mixed with one
   highlighted card (Search share), D numbered cards with large faint numerals.
7. CARD-E/F, the first 3 levers only (title + line): see how 3 cards fill the same space, two ways.
8. CARD-G/H, the 7 levers as titles only (no line): two ways.
9. STEPS-A/B, levers 1-4 as ordered phases ("Phase 1-4") as step cards: two ways.
10. TABLE-A/B/C/D, the platform table: A plain rows, B zebra rows, C highlighted best row (Website),
    D table with a bold header band and one coloured column (ROAS).
11. CHART-A/B/C/D, monthly revenue: A vertical bars, B horizontal bars, C line, D bars with value
    labels and one highlighted bar (Jun).
12. BULLET-A/B/C/D, levers 1-5 as bullets (title + line): A plain bullets, B icon bullets,
    C bullet tiles, D two-column bullets.
13. CALLOUT-A/B/C/D, the key message: A rule + text, B tinted panel, C dark panel, D quote style.
14. Closing: the closing statement, two ways (CLOSE-A/B).
```

## Prompt B: diagrams

```text
Create a 12-slide "diagram variant gallery" deck for an internal design review. It is NOT a client
pitch: its job is to show several visual variants of the same diagram, so a design team can compare
them and pick a house style.

[DESIGN SYSTEM block above]

RULES (apply to every slide)
- Use ONLY the content given below. Do not add numbers, names, dates, sources or items. Do not
  invent times of day, durations or extra steps.
- Every variant keeps the same content; only the design changes.
- Put the variant tag exactly as listed on every variant panel, e.g. "TIMELINE-A  rail with dots".
  Never omit, merge or rename the tags.
- Slides with several variants: equal panels (2 per slide unless stated).
- After the deck, write a short table, one row per variant tag: what makes it different and how it
  handles long labels.

CONTENT (brand BREWLY, a specialty coffee brand on its website and the apps QUIKMART and DASHCART)

90-day plan (date + label):
- Week 1-2: Audit — catalogue, prices and stock on both apps
- Week 3-4: Search — exact-match bids on the 40 hero keywords
- Week 5-8: Bundles — 2-pack and gift box live in top cities
- Week 9-12: Scale — budget moved to the proven cities

Customer path (ordered): Search → Add to cart → Checkout → Dark-store pick → 10-min delivery
Automation engine (ordered): Platform data → Decision engine → Bid changes → Business outcome
Budget approval (with a branch): Request → ROAS check → "Above 1.0x?" → Yes: Approve / No: back to ROAS check
Priorities, 2x2 matrix, x = Effort (low → high), y = Impact (low → high):
  Search (low effort, high impact), Bundles (low effort, high impact), New cities (high effort,
  high impact), Video ads (high effort, low impact). Quadrants: Plan, Do first, Skip, Quick wins.
Brand priorities, bottom to top: Availability, Search share, Bundles, Loyalty
Growth team: Growth lead → QUIKMART (Search, Catalogue), DASHCART (Search, Pricing)
Ecosystem: the "BREWLY growth engine" at the centre serving QUIKMART, DASHCART and Website

SLIDES
1. Cover: "BREWLY diagram variants", subtitle "Internal design review".
2. TIMELINE-A/B: the 90-day plan, A rail with dots and labels, B rail with one card per item.
3. TIMELINE-C/D: the same, C vertical timeline, D phases as columns with a progress bar.
4. PROCESS-A/B: customer path, A chevrons, B numbered steps with arrows.
5. PROCESS-C/D: customer path, C circles on a line, D step cards with the last step highlighted.
6. FLOW-A/B: automation engine, A boxes and arrows, B an engine card holding the middle steps.
7. FLOW-C: budget approval with the decision branch, full width.
8. MATRIX-A/B: priorities, A dots in quadrants, B quadrant cards listing the items.
9. PYRAMID-A/B: brand priorities, A pyramid, B stacked bars widening downward.
10. TREE-A/B: growth team, A org chart, B indented list with group cards.
11. HUB-A/B: ecosystem, A hub and spokes, B centre card with three connected cards.
12. Summary slide: one example of each diagram at small size, labelled.
```
