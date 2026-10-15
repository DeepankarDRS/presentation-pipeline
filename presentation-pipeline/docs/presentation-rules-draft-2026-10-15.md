# Generalised presentation rules — draft (2026-10-15)

Source: `new 62.xml` (user, 2026-10-15): AI summaries of four reference decks (platform / agency
takeover, CHEFFIN audit, QBR, XTSY) and the deck "skills" behind them (consulting diagnostic audit,
consulting final deck, capability pitch, CSV-to-chart, SQL KPI weekly, QBR, annual report art
direction, CRM funnel QBR, annual marketing plan).

**How this was drawn up.** Only reasoning that recurs across several decks / skills became a rule.
Left out on purpose (example bias): named frameworks as content (RAPID, MEDDIC, SPICED, flywheel
40/35/25, OKR R/Y/G thresholds), fixed slide positions ("slide 02 is X"), deck lengths, pixel
coordinates, font names, print specs, colophons. The source's own numbers are for 1920×1080; ours
is 1280×720, so any size below is already scaled by ⅔. The file is a summary written after the
fact: its "dictated by" attributions are not evidence that a rule works — each rule still needs our
own check (free replay or paid A/B) before it counts.

Each rule says **where it lives** (O = outline planner, P = slide component planner, G = generator /
house style, C = code check or fit-grow) and its **status** here (has = already in the pipeline,
part = partly, new = not built). "Never invent" (content policy §12) overrides every rule.

## 1. Story (deck level)

| # | Rule | Where | Status |
|---|---|---|---|
| S1 | **Answer first.** The deck's main conclusion comes before its evidence: an early slide states it, with the 3–4 reasons the later slides prove. | O | new (O follows the brief's slide order today) |
| S2 | **Headlines are conclusions.** Every body slide's headline is a full sentence stating what the slide shows; reading only the headlines tells the whole story. Topic labels ("Revenue Trend") go in the kicker. | O | has (claim headlines + label) |
| S3 | **Argue, don't narrate.** Slides follow the argument (claim → evidence), not the order the work was done. Chronology only where time is the point (a roadmap, a history). | O | new |
| S4 | **One message per slide.** Everything on a slide supports its headline; a second message is a second slide (when the brief allows the count). | O, P | part |
| S5 | **End in decisions.** The last slide carries what the brief asks of the audience: actions, owners, dates, asks. Only what the brief gives; never invented owners or dates. | O | part (no Q&A / Thank-you slides) |
| S6 | **Caveats on the slide they qualify,** as a footnote, never their own slide unless asked. | O, P | has ("Note:") |
| S7 | **Front-load the verdict data.** The scorecard / headline numbers sit near the start, detail later. | O | part |

## 2. Choosing the component (slide level)

| # | Rule | Where | Status |
|---|---|---|---|
| K1 | **Chart by comparison type:** rank / items → horizontal bars, sorted; change over time → columns or a line; parts of a whole → one stacked bar (pie / doughnut only for 2–3 parts); target vs actual → bars with the target as a line or outline; correlation → scatter. | P | part (routing table has some) |
| K2 | **Position and length read most exactly:** a preference, not a ban (user, Q2) — bars and dots for exact comparison; pie, doughnut and radar stay available where the shape is the point (share of a whole, a profile); no dual y-axes. | P | new |
| K3 | **Structure beats prose:** content with rows × columns (who decides what, gap × platform, phase × task) is a table or card matrix, not paragraphs. | P | has |
| K4 | **Match the component to how full the slide is.** Cards when the slide has room to fill; on a slide already full, many short named items become a list (or pills, K8) instead of a card each. | P, C | new (agency s1, 2026-10-15) |
| K5 | **One hero number** when the headline rests on one figure: shown 3–4× the body size, its context smaller beside it. | P, C | has (hero stat) |
| K6 | **Peers look alike:** items of the same kind (platforms, reps, segments) are equal cards / columns of one size — small multiples. | P, C | has (one size per group) |
| K7 | **No number → no fake number:** when the brief gives a direction but no figure, show the direction (↑, "grows"), not an estimate. | P | has (never invent) |
| K8 | **Small labels ride inside components:** delta chips, status badges, term pills, tags belong inside a tile, card or table, not as components of their own. | P, G | part |

## 3. Layout and position

| # | Rule | Where | Status |
|---|---|---|---|
| L1 | **Top → middle → bottom = claim → evidence → so-what.** Headline at the top, the main exhibit in the middle, at most one takeaway strip at the bottom — only when the brief has a takeaway (no filler). | G | part |
| L2 | **The main exhibit gets most of the width** (about 60–65%); commentary or implications take the rest as a side panel. | G | part |
| L3 | **Two data sets on one slide → two zones** (top / bottom or left / right) of similar size, each with its own label, not interleaved. | G | new |
| L4 | **One grid, equal gutters:** peers align on shared edges; the same gap between all peers. | G, C | part (fit-grow) |
| L5 | **Readable line length:** body text lines of about 60–75 characters; a wider text box becomes two columns or a narrower box. | G, C | new |
| L6 | **Label the data directly:** values and series names on or beside the bars / lines, no separate legend; annotations on the chart instead of bullets under it. | G | new (blueprints still use `showLegend="true"`) |
| L7 | **Data-ink:** no 3D, no heavy gridlines, no decorative shadows on charts or tables. | G | part (see doubt 5 for cards) |

## 4. Size and type

| # | Rule | Where | Status |
|---|---|---|---|
| T1 | **A fixed type ramp:** headline ≈ 24–30 px, body ≥ 16 px (the source's 24 px floor at 1920), labels ≥ 12 px, hero numbers 3–4× the body. | G, C | part (type ramp 2026-10-08) |
| T2 | **Few weights:** one family (Inter) in two or three weights; no extra fonts for decoration. | G | has (deck font Inter) |
| T3 | **Numbers in tabular figures** so columns of numbers line up. | G, C | new |
| T4 | **One size per peer group** (all tile numbers, all card titles). | C | has |

## 5. Colour

| # | Rule | Where | Status |
|---|---|---|---|
| R1 | **Colour carries meaning, never decoration:** bad = losses / risks, good = wins / fixes, watch = near a limit, one accent for the focus, grey for the rest — the same on every slide. | P, G | has (colour roles) |
| R2 | **Colour is never the only signal:** a sign, arrow, label or position says the same thing (colour-blind readers, print). | G | new |
| R3 | **Brand colours only identify:** a platform's own colour marks that platform's column / chip, from the brief or theme; it does not mean good or bad. | G | new |
| R4 | **One dark panel per deck at most;** a dark slide is a deliberate anchor (cover, verdict), not a style. | G, C | has (DARK_PANEL_SOFTENED) |

## 6. What this changes first (proposal, nothing built)

1. **K4** (dense slide → list / pills) — the agency s1 failure; free check on saved plans.
2. **L6** (direct labels, no legends) and **K2** (no pie / donut / radar beyond 2–3 parts) — chart quality, LLM-free replay of saved chart slides.
3. **S1 / S3** (answer first, argument order) — outline planner; needs a paid A/B because it changes slide order.
4. **L5, T3, R2** — small generator / fit-grow rules.

## 7. Decisions (user, 2026-10-15)

- **Q1 answer-first (S1):** out of scope. The insights file is for the visual, layout and design
  side only; the story rules in §1 (S1, S3, S5, S7) are parked, not built.
- **Q2 charts:** drop legends in favour of direct labels (L6). K2 is a preference, not a ban: every
  chart type POM offers stays available (pie, doughnut, radar included); K1 says which fits which
  comparison.
- **Q3 dense lists:** a bullet list is fine. The real problem is upstream: the outline's
  `key_messages` are flat strings, so most slides end up as bullet lists. Direction: a structured
  per-slide outline JSON (our own schema) — spec to be drafted, see below.
- **Q4 takeaway strip:** whichever holds long term without inventing or overlapping → only when the
  brief gives a takeaway (no filler), and its size follows the slide's room (a strip on a sparse
  slide, one footnote line on a dense one).
- **Q5 card shadows:** keep the lifted cards; L7 applies to charts and tables only.
- **Q6 source / exhibit footers:** skip.
- **Q7 phase colours:** only when the brief itself calls a phase urgent or names it the goal.
- **Q8 order of work:** as in §6.
