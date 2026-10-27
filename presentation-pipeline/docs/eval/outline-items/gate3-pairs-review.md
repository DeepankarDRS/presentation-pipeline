# Gate 3 — slide pairs review

Review of the 20 pairs in `gate3-inputs.json` before the paid generator run.
**items** = plan from the new outline (kind + text items). **base** = saved plan from the old outline (key_messages).
Each section: what differs, whether both carry the same content, then both plans (header, then each component in short form; the title component is shown in the header line).

## Summary

| # | pair | overlap | main difference | same content? |
|---|------|---------|-----------------|---------------|
| 1 | deck-qbr-data-s2 | 0.59 | base + narrative | yes |
| 2 | deck-qbr-data-s4 | 0.66 | base + narrative | yes |
| 3 | deck-qbr-data-s5 | 0.57 | base + narrative; items subtitle leaks "core_hook" | yes |
| 4 | deck-product-launch-data-s1 | 0.50 | title slide; items + 2 cards repeating title | yes (nothing to judge) ⚠ |
| 5 | deck-product-launch-data-s2 | 0.53 | base + narrative | yes |
| 6 | deck-product-launch-data-s4 | 0.62 | base + narrative + caption | yes |
| 7 | gate-deck-agency-takeover-s1 | 0.73 | items chart has text values; base chart + table | yes (items defect) |
| 8 | gate-deck-agency-takeover-s2 | 0.82 | chart+layer (items) vs table+cards (base) | yes |
| 9 | gate-deck-agency-takeover-s4 | 0.84 | base + "6 Pillars:" line | yes (near-identical) |
| 10 | gate-deck-agency-takeover-s6 | 0.94 | ask as card vs narrative | yes |
| 11 | gate-deck-all-nodes-dense-s2 | 0.94 | chart hero vs KPI hero; items KPI label malformed | yes (items defect) |
| 12 | gate-deck-cheffin-full-s1 | 0.60 | title slide; base + source list | mostly ⚠ |
| 13 | gate-deck-cheffin-full-s2 | 0.80 | bullets vs narrative | yes |
| 14 | gate-deck-cheffin-full-s3 | 0.89 | base + gap table | yes |
| 15 | gate-deck-cheffin-full-s4 | 0.56 | base has key formulas, items not | **no** ⚠ |
| 16 | gate-deck-cheffin-full-s5 | 0.82 | 1 KPI row vs 2 | yes |
| 17 | gate-deck-cheffin-full-s6 | 0.98 | chart vs table | yes |
| 18 | gate-deck-xtsy-qcomm-s3 | 0.90 | items + bullets; both card grids odd | yes (both defective) |
| 19 | gate-deck-xtsy-qcomm-s5 | 0.33 | 2 list cards vs empty visual + 9 described cards | partly ⚠ |
| 20 | gate-deck-xtsy-qcomm-s6 | 0.89 | cards (items) vs flow (base) | yes |

**Flagged as not a fair test:** 15 (base has content items lacks), 19 (low overlap, base adds descriptions). **Weak tests (little to judge):** 4 and 12 (title slides), 9 (near-identical), 18 (both plans have the same card defect).
**Real items defects worth knowing before the run** (fair to keep — they are what items produces): 7 (text chart values), 11 (sentence as KPI label), 3 (core_hook leak), 20 (steps lost the flow).

## Decisions (2026-10-28)

- Drop 15 (content differs: formulas only in base) and 19 (overlap 0.33, base adds descriptions and an empty visual).
- Drop 9 (near-identical, nothing to judge) and 18 (both plans have the same card defect).
- Keep the other 16, including the cover slides 4 and 12.
- Pair choice: also require both plans to carry the same content (same figures and points), not only word overlap >= 1/3; skip pairs whose plans are near-identical or share a defect.
- Known items defects, kept in the run on purpose: 7 (chart values are text), 11 (sentence as KPI label), 3 ("core_hook" in subtitle), 20 (steps as cards, not a flow).

## Node changes (18 kept pairs, title node left out)

| node | items | base |
|------|-------|------|
| narrative | 8 | 18 |
| kpi_row | 5 | 7 |
| table | 3 | 6 |
| chart | 5 | 3 |
| card_grid | 8 | 6 |
| bullet_list | 4 | 3 |
| layer / flow | 1 / 0 | 0 / 1 |
| caption | 1 | 2 |

Hero node: kpi_row 4 vs 5, table 2 vs 3, chart 4 vs 2, card_grid 4 vs 4, flow 0 vs 1.
Pairs whose node mix changes beyond "base adds a narrative": 7, 8, 11, 13, 14, 16, 17, 20.
- Table → chart: 8 (match-type figures), 17 (match ROAS). Table dropped where it repeated the chart: 7, 14.
- Two KPI rows → one: 11 (and hero moves KPI → chart), 16.
- Narrative → bullets: 13. Flow → cards: 20 (a loss).


## 1. deck-qbr-data-s2
slide 2 vs base slide 2 · overlap 0.59 · theme corporate-slate

**Differs:** base adds a narrative that restates the KPIs. Headlines differ in wording.

**Same content?** Yes. Same 4 KPIs, same values and deltas.

**items** — label: EXECUTIVE SUMMARY · headline: ARR is up while margin dipped and CAC payback improved · subtitle: Q3 FY26 vs Q2 FY26

- **kpi_row** (hero): ARR = $48.2M (+18% QoQ); NRR = 114% (+2 pts); Gross Margin = 72.1% (-1.4 pts); CAC Payback = 14 months (-2 months)

**base** — label: EXECUTIVE SUMMARY · headline: Strong revenue and retention, with mixed efficiency signals · subtitle: Q3 FY26 · QoQ changes

- **kpi_row** (hero): ARR = $48.2M (+18% QoQ); NRR = 114% (+2 pts); Gross Margin = 72.1% (-1.4 pts); CAC Payback = 14 months (-2 months)
- **narrative** (supporting): Momentum is driven by ARR growth and NRR expansion while Gross Margin dipped; CAC Payback improved but remains a focus for efficiency.

## 2. deck-qbr-data-s4
slide 4 vs base slide 4 · overlap 0.66 · theme corporate-slate

**Differs:** base adds a narrative (Enterprise = most ARR, SMB = most customers).

**Same content?** Yes. Same table.

**items** — label: SEGMENT PERFORMANCE · headline: Enterprise drives the largest ARR and fastest growth · subtitle: Q3 FY26 segment ARR, QoQ growth and customer counts

- **table** (hero): 3 rows; columns: Segment / ARR / QoQ Growth / Customers
    - Enterprise / $28.1M / +22% / 142
    - Mid-Market / $14.4M / +14% / 487
    - SMB / $5.7M / +8% / 2,341

**base** — label: SEGMENT PERFORMANCE · headline: Enterprise leads ARR at $28.1M in Q3 FY26 · subtitle: ARR and customer counts by segment

- **table** (hero): 3 rows; columns: Segment / ARR / QoQ Growth / Customers
    - Enterprise / $28.1M / +22% / 142
    - Mid-Market / $14.4M / +14% / 487
    - SMB / $5.7M / +8% / 2,341
- **narrative** (supporting): Enterprise represents the largest ARR concentration while SMB holds the largest customer count, indicating higher ARR per customer in Enterprise.

## 3. deck-qbr-data-s5
slide 5 vs base slide 5 · overlap 0.57 · theme corporate-slate

**Differs:** base adds a narrative tying the 3 priorities together. items card bodies repeat the card title. items subtitle leaks an internal word: "close the core_hook gap".

**Same content?** Yes. Same 3 priorities and targets.

**items** — label: LOOKING AHEAD · headline: Q4 priorities to convert growth into more efficient, durable ARR · subtitle: Focused actions to close the core_hook gap

- **card_grid** (hero): 3 cards
    - *Close 3 enterprise logos*: Close 3 enterprise logos worth $4M+ combined ARR
    - *Launch self-serve onboarding*: Launch self-serve onboarding to reduce CAC payback to 10 months
    - *Ship analytics v2 dashboard*: Ship analytics v2 dashboard before Jan board meeting

**base** — label: Q4 PRIORITIES · headline: Three operational priorities to convert momentum into durable growth · subtitle: Targets for Q4 FY26

- **card_grid** (hero): 3 cards
    - *Close 3 enterprise logos*: worth $4M+ combined ARR
    - *Launch self-serve onboarding*: to reduce CAC payback to 10 months
    - *Ship analytics v2 dashboard*: before Jan board meeting
- **narrative** (supporting): These priorities directly target revenue expansion, CAC payback reduction, and product readiness ahead of the Jan board meeting.

## 4. deck-product-launch-data-s1  ⚠ title slide
slide 1 vs base slide 1 · overlap 0.5 · theme midnight-indigo

**Differs:** Title slide. items adds 2 cards that repeat the title and the subtitle; base is title only.

**Same content?** Yes, but nothing new on either side. Tests only whether the extra cards hurt a cover slide.

**items** — label:  · headline: Nexus API Gateway · subtitle: One gateway. Every API. Zero downtime.

- **card_grid** (supporting): 2 cards
    - *Nexus API Gateway*: (title only)
    - *One gateway. Every API. Zero downtime.*: (title only)

**base** — label:  · headline: Nexus API Gateway · subtitle: One gateway. Every API. Zero downtime.


## 5. deck-product-launch-data-s2
slide 2 vs base slide 2 · overlap 0.53 · theme midnight-indigo

**Differs:** base adds a narrative ("increase risk, slow development…").

**Same content?** Yes. Same 3 bullets.

**items** — label: PROBLEM · headline: Multiple gateways cause configuration toil, outages and blindspots · subtitle: 

- **bullet_list** (hero):
    - Teams manage 4+ separate gateways averaging 2.3 hours/week each on config
    - 68% of outages last quarter traced to gateway misconfiguration
    - No unified view of API traffic across services — teams fly blind

**base** — label: THE PROBLEM · headline: Multiple gateways create time drain and operational risk · subtitle: Observed across engineering organizations

- **bullet_list** (hero):
    - Teams manage 4+ separate gateways averaging 2.3 hours/week each on config
    - 68% of outages last quarter traced to gateway misconfiguration
    - No unified view of API traffic across services — teams fly blind
- **narrative** (supporting): These operational issues increase risk, slow development, and make incidents harder to diagnose.

## 6. deck-product-launch-data-s4
slide 4 vs base slide 4 · overlap 0.62 · theme midnight-indigo

**Differs:** base adds a narrative and a caption that repeats the label ("BETA RESULTS").

**Same content?** Yes. Same 4 KPIs.

**items** — label: BETA RESULTS · headline: Early beta delivers large improvements in operations and developer experience · subtitle: Beta results vs baseline

- **kpi_row** (hero): Config Time = 15 min/wk (-89%); Outages = 1/quarter (-92%); API Latency = 38ms (-73%); Dev NPS = 71 (+49 pts)

**base** — label: BETA RESULTS · headline: Private beta delivered large improvements in operations and developer experience · subtitle: Measured during private beta

- **caption** (minor): BETA RESULTS
- **kpi_row** (hero): Config Time = 15 min/wk (-89%); Outages = 1/quarter (-92%); API Latency = 38ms (-73%); Dev NPS = 71 (+49 pts)
- **narrative** (supporting): These metrics were observed during our private beta and indicate material improvement in stability and developer satisfaction.

## 7. gate-deck-agency-takeover-s1
slide 1 vs base slide 1 · overlap 0.73 · theme 

**Differs:** base: numeric ROAS chart + 1-row table (CPD/BOTD spend vs revenue) + narrative. items: chart whose values are text ("around 0.29x ROAS", "consumed the largest budget pool") + narrative; the CPD/BOTD figures sit in a note series of the chart.

**Same content?** Same figures and recommendation. But the items chart has text, not numbers, as values: it may render badly or not at all. That is a real items defect, not unfair.

**items** — label: PLATFORM A · DIAGNOSIS · headline: Campaign-purpose governance is the biggest [Platform A] unlock. · subtitle: 

- **chart** (hero): bar "ROAS by campaign class (with spend overlay)"
    - series ROAS: Generic search = around 0.29x ROAS; Category / PLA = around 0.80x ROAS; Brand = around 0.99x ROAS but under-allocated; Competitor = around 0.15x ROAS
    - series Spend / revenue notes: Generic search = consumed the largest budget pool; CPD/BOTD = consumed around ₹10.0L and generated only around ₹9.7K revenue
- **narrative** (supporting): Recommendation: Separate performance media from visibility/awareness placements. CPD/BOTD should not be funded like performance campaigns unless the objective is clearly awareness or incrementality.

**base** — label: [Platform A] Campaign Diagnosis · headline: Campaign-purpose governance is the biggest [Platform A] unlock. · subtitle: 

- **chart** (hero): bar "Campaign-class ROAS"
    - Generic search = 0.29x; Category / PLA campaigns = 0.80x; Brand campaigns = 0.99x; Competitor campaigns = 0.15x
- **table** (supporting): 1 rows; columns: Placement / Spend / Revenue
    - CPD/BOTD placements / ₹10.0L / ₹9.7K
- **narrative** (supporting): Separate performance media from visibility/awareness placements. CPD/BOTD should not be funded like performance campaigns unless the objective is clearly awareness or incrementality.

## 8. gate-deck-agency-takeover-s2
slide 2 vs base slide 2 · overlap 0.82 · theme 

**Differs:** items: spend+ROAS chart (two units on one bar chart) + table + 4 cards (winners, weak terms, 2 recommendations) + city heatmap layer. base: one 6-column table + 2 keyword cards + narrative + 2 city cards + narrative. Both are dense.

**Same content?** Yes. Same match-type figures, terms, cities and both recommendations.

**items** — label: PLATFORM A · LEAKAGE · headline: Exact match outperforms phrase and broad, but keyword governance needs sharper control. · subtitle: 

- **chart** (hero): bar "Spend and ROAS by Match Type"
    - series Spend: Phrase Match = ₹45.5L; Exact Match = ₹21.3L; Broad Match = ₹1.9L
    - series ROAS: Phrase Match = 0.32x; Exact Match = 0.41x; Broad Match = 0.23x
- **table** (supporting): 3 rows; columns: Match Type / Revenue / CPC / CVR
    - Phrase Match / ₹14.6L / ₹62.0 / 8.6%
    - Exact Match / ₹8.8L / ₹59.5 / 10.9%
    - Broad Match / ₹0.4L / ₹64.7 / 6.2%
- **card_grid** (supporting): 4 cards
    - *Winners*: [[Brand] phrase; [Brand] exact; paneer makhani; curry; shahi paneer gravy]
    - *Weak terms*: [butter chicken phrase; instant food phrase; ready to cook paneer phrase; mix phrase; instant gravy broad; ready masala; instant dal makhani; meat masala; kilrr chicken masala]
    - *Recommendation: keywords*: Scale exact winners, reduce phrase/broad leakage, and create strict budgets for competitor and generic discovery terms.
    - *Recommendation: city-level realloc*: Reallocate budget based on City-level ROAS, SKU availability, delivery strength, inventory depth, price competitiveness, conversion rate, CPC, and organic demand.
- **layer** (peer): India city ROAS heatmap with flagged cities. No major high-spend city crossed 0.5x ROAS. Bengaluru was the best large city at around 0.45x ROAS, but still below desired efficiency. Flagged cities: Hyderabad, Chennai, Jaipur, Sas Nagar, Surat, Nashik, Mumbai, Delhi.
    - nodes: Bengaluru (around 0.45x ROAS), Hyderabad, Chennai, Jaipur, Sas Nagar, Surat, Nashik, Mumbai, Delhi

**base** — label: [Platform A] Keyword & City Inefficiencies · headline: Exact match outperforms phrase and broad, but keyword governance needs sharper control. · subtitle: City allocation must follow conversion economics, not uniform pressure.

- **table** (hero): 3 rows; columns: Match Type / Spend / Rev / ROAS / CPC / CVR
    - Phrase Match / ₹45.5L / ₹14.6L / 0.32x ROAS / ₹62.0 / 8.6%
    - Exact Match / ₹21.3L / ₹8.8L / 0.41x ROAS / ₹59.5 / 10.9%
    - Broad Match / ₹1.9L / ₹0.4L / 0.23x ROAS / ₹64.7 / 6.2%
- **card_grid** (supporting): 2 cards
    - *Winners*: [[Brand] phrase; [Brand] exact; paneer makhani; curry; shahi paneer gravy]
    - *Weak terms*: [butter chicken phrase; instant food phrase; ready to cook paneer phrase; mix phrase; instant gravy broad; ready masala; instant dal makhani; meat masala; kilrr chicken masala]
- **narrative** (supporting): Recommendation (keywords): Scale exact winners, reduce phrase/broad leakage, and create strict budgets for competitor and generic discovery terms.
- **card_grid** (peer): 2 cards
    - *City performance*: [No major high-spend city crossed 0.5x ROAS.; Bengaluru was the best large city at around 0.45x ROAS, but still below desired efficiency.]
    - *Cities needing immediate review*: [Hyderabad; Chennai; Jaipur; Sas Nagar; Surat; Nashik; Mumbai; Delhi]
- **narrative** (supporting): Recommendation (cities): Reallocate budget based on City-level ROAS, SKU availability, delivery strength, inventory depth, price competitiveness, conversion rate, CPC, and organic demand.

## 9. gate-deck-agency-takeover-s4
slide 4 vs base slide 4 · overlap 0.84 · theme 

**Differs:** base adds a one-line narrative "6 Pillars:". Otherwise identical 6 title-only cards.

**Same content?** Yes. Near-identical; little to judge.

**items** — label: AGENCY SYSTEM · headline: We would run this as a profit-led marketplace growth system. · subtitle: 

- **card_grid** (hero): 6 cards
    - *Raw-data reporting and weekly diagnostics*: (title only)
    - *Intent-layer campaign structure*: (title only)
    - *Break-even CPC and target ACOS bidding*: (title only)
    - *Weekly search-term harvesting and negative keyword loop*: (title only)
    - *SKU, city, and inventory-aware budget allocation*: (title only)
    - *AOV and CVR improvement through bundles, multipacks, PDP, offers, and creative*: (title only)

**base** — label: What Our Agency Would Do Differently · headline: We would run this as a profit-led marketplace growth system. · subtitle: 

- **narrative** (supporting): 6 Pillars:
- **card_grid** (hero): 6 cards
    - *Raw-data reporting and weekly diagnostics.*: (title only)
    - *Intent-layer campaign structure.*: (title only)
    - *Break-even CPC and target ACOS bidding.*: (title only)
    - *Weekly search-term harvesting and negative keyword loop.*: (title only)
    - *SKU, city, and inventory-aware budget allocation.*: (title only)
    - *AOV and CVR improvement through bundles, multipacks, PDP, offers, and creative.*: (title only)

## 10. gate-deck-agency-takeover-s6
slide 6 vs base slide 6 · overlap 0.94 · theme 

**Differs:** items puts the "30-day sprint" ask in its own card; base puts it in a closing narrative. Data-needed cards the same.

**Same content?** Yes.

**items** — label: RECOMMENDATION · headline: The current account needs a sharper operator, not just more spend. · subtitle: 

- **narrative** (supporting): The data shows that [Brand] has demand pockets that work, but the current operating model is allowing too much budget to flow into weak-intent, high-CPC traffic. Our agency would bring a structured, data-led marketplace growth system that connects media spend to SKU economics, city performance, search intent, and profitability.
- **card_grid** (peer): 1 cards
    - *Recommend*: 30-day transition audit and account takeover sprint.
- **card_grid** (peer): 3 cards
    - *[Platform B] data needed*: [Search term; placement; advertised product reports; SQP data]
    - *[Platform A] data needed*: [SKU-level campaign data; city-wise availability; organic sales; keyword-level order/revenue]
    - *Business data needed*: [Target ACOS by SKU; Margin by SKU; Launch vs profitability priorities]

**base** — label: Closing Recommendation & Data Needed · headline: The current account needs a sharper operator, not just more spend. · subtitle: 

- **narrative** (peer): The data shows that [Brand] has demand pockets that work, but the current operating model is allowing too much budget to flow into weak-intent, high-CPC traffic. Our agency would bring a structured, data-led marketplace growth system that connects media spend to SKU economics, city performance, search intent, and profitability.
- **card_grid** (hero): 3 cards
    - *[Platform B]*: [Search term; placement; advertised product reports; SQP data]
    - *[Platform A]*: [SKU-level campaign data; city-wise availability; organic sales; keyword-level order/revenue]
    - *Business data needed*: [Target ACOS by SKU; Margin by SKU; Launch vs profitability priorities]
- **narrative** (supporting): 30-day transition audit and account takeover sprint.

## 11. gate-deck-all-nodes-dense-s2
slide 2 vs base slide 2 · overlap 0.94 · theme 

**Differs:** items: chart is hero, one KPI row of 5 where the 5th tile's label is the whole sentence ("62% of revenue comes from repeat customers…"). base: 62% as its own hero KPI, then 4 KPIs, chart supporting.

**Same content?** Yes. Same figures. items KPI label is malformed (a real items defect).

**items** — label: PERFORMANCE · headline: Repeat customers now drive most of BREWLY's revenue. · subtitle: 

- **chart** (hero): bar "Quarterly revenue (₹ Cr)"
    - Q1 FY26 = 2.6; Q2 FY26 = 2.9; Q3 FY26 = 3.3; Q4 FY26 = 3.6; Q1 FY27 = 3.9; Q2 FY27 = 4.4
- **kpi_row** (supporting): Annual revenue = ₹14.2Cr; Revenue growth = +38%; Blended ROAS = 2.4x; Customer acquisition cost = ₹410; 62% of revenue comes from repeat customers, up from 41% a year ago. = 62% (up from 41% a year ago.)
- **narrative** (minor): Growth came from retention and pricing, not from buying more traffic.

**base** — label: PERFORMANCE · headline: Repeat customers now drive most of BREWLY's revenue. · subtitle: 

- **kpi_row** (hero): Repeat customers = 62% (up from 41% a year ago)
- **kpi_row** (peer): Annual revenue = ₹14.2Cr; Revenue growth = +38%; Blended ROAS = 2.4x; Customer acquisition cost = ₹410
- **chart** (supporting): bar "Quarterly revenue (₹ Cr)"
    - Q1 FY26 = 2.6; Q2 FY26 = 2.9; Q3 FY26 = 3.3; Q4 FY26 = 3.6; Q1 FY27 = 3.9; Q2 FY27 = 4.4
- **narrative** (supporting): Growth came from retention and pricing, not from buying more traffic.

## 12. gate-deck-cheffin-full-s1  ⚠ title slide
slide 1 vs base slide 1 · overlap 0.6 · theme 

**Differs:** Title slide. base adds a bullet list of the data sources; items has only the "Prepared by" caption.

**Same content?** Mostly. base carries 4 extra lines (the source list) that items leaves for the methodology slide.

**items** — label:  · headline: CHEFFIN FLIPCART & ZAROMA Ads Audit · subtitle: Last 90 Days Performance Review | Key Gaps, Opportunities & Takeover Roadmap

- **caption** (minor): Prepared by our agency

**base** — label:  · headline: CHEFFIN FLIPCART & ZAROMA Ads Audit · subtitle: Last 90 Days Performance Review | Key Gaps, Opportunities & Takeover Roadmap

- **bullet_list** (supporting):
    - FLIPCART Targeting (last 90 days)
    - FLIPCART Search Term report
    - ZAROMA April–June campaign
    - city and keyword views
- **caption** (minor): Prepared by our agency

## 13. gate-deck-cheffin-full-s2
slide 2 vs base slide 2 · overlap 0.8 · theme 

**Differs:** Main insight as 2 bullets (items) vs one narrative (base). items has a subtitle.

**Same content?** Yes. Same 5 KPIs, same insight text.

**items** — label: EXECUTIVE SUMMARY · headline: The account is spending at scale, but not yet buying profitable demand. · subtitle: Last 90 days · FLIPCART + ZAROMA

- **kpi_row** (hero): Combined spend = ₹114.9L; Combined revenue = ₹37.4L; Combined ROAS = 0.33x; FLIPCART ROAS = 0.34x; ZAROMA ROAS = 0.32x
- **bullet_list** (supporting):
    - Both FLIPCART and ZAROMA show the same structural issue: CPC is too high relative to AOV and CVR.
    - “This is a media economics problem, not just a campaign hygiene problem.”

**base** — label: EXECUTIVE SUMMARY · headline: The account is spending at scale, but not yet buying profitable demand. · subtitle: 

- **kpi_row** (hero): Combined spend = ₹114.9L; Combined revenue = ₹37.4L; Combined ROAS = 0.33x; FLIPCART ROAS = 0.34x; ZAROMA ROAS = 0.32x
- **narrative** (supporting): Main insight: Both FLIPCART and ZAROMA show the same structural issue: CPC is too high relative to AOV and CVR. “This is a media economics problem, not just a campaign hygiene problem.”

## 14. gate-deck-cheffin-full-s3
slide 3 vs base slide 3 · overlap 0.89 · theme 

**Differs:** base adds a table repeating the chart plus a Gap column (~2.9x, ~3.1x).

**Same content?** Yes. The gap multiples in base are derived from the same figures.

**items** — label: CORE ECONOMICS · headline: CPC is nearly 3x higher than what current conversion economics can support. · subtitle: Actual vs allowable CPC for 1.0x ROAS (Allowable CPC = AOV × CVR)

- **chart** (hero): bar "Actual vs Allowable CPC"
    - series Actual CPC: FLIPCART = ₹31.1; ZAROMA = ₹46.2
    - series Allowable CPC for 1.0x ROAS: FLIPCART = ₹10.7; ZAROMA = ₹14.8
- **narrative** (supporting): At the current AOV and CVR, the brand needs CPC reduction, CVR improvement, AOV improvement, or all three together.

**base** — label: ECONOMICS · headline: CPC is nearly 3x higher than what current conversion economics can support. · subtitle: 

- **chart** (hero): bar "Actual vs Allowable CPC by Platform"
    - series Actual CPC: FLIPCART = ₹31.1; ZAROMA = ₹46.2
    - series Allowable CPC for 1.0x ROAS: FLIPCART = ₹10.7; ZAROMA = ₹14.8
- **table** (supporting): 2 rows; columns: Platform / Actual CPC / Allowable CPC for 1.0x ROAS / Gap
    - FLIPCART / ₹31.1 / ₹10.7 / Actual CPC is ~2.9x allowable
    - ZAROMA / ₹46.2 / ₹14.8 / Actual CPC is ~3.1x allowable
- **narrative** (supporting): At the current AOV and CVR, the brand needs CPC reduction, CVR improvement, AOV improvement, or all three together.

## 15. gate-deck-cheffin-full-s4  ⚠ content differs
slide 4 vs base slide 4 · overlap 0.56 · theme 

**Differs:** items: 5 title-only source cards + a long data-quality narrative. base: 3 cards with bullets (sources, data-quality notes, key formulas).

**Same content?** No. base has the 8 key formulas (ROAS, ACOS, CPC… Allowable CPC = AOV × CVR); items has none. Sources and quality notes are on both.

**items** — label: METHODOLOGY · headline: We rebuilt the audit from raw performance data, not surface-level reports. · subtitle: Data sources and quality caveats

- **card_grid** (hero): 5 cards
    - *FLIPCART Targeting last 90 days report*: (title only)
    - *FLIPCART Search Term report*: (title only)
    - *ZAROMA campaign-level data*: (title only)
    - *ZAROMA city-level data*: (title only)
    - *ZAROMA keyword-level data*: (title only)
- **narrative** (supporting): Some FLIPCART pivot metrics were unreliable or zeroed, so ratios were recalculated from raw data. ZAROMA campaign, city, and keyword sheets may not reconcile perfectly because they appear to have slightly different coverage. Use ZAROMA campaign-level data as the primary platform total source, while city and keyword sheets should be used for diagnostic insights.

**base** — label: DATA & METHODOLOGY · headline: We rebuilt the audit from raw performance data, not surface-level reports. · subtitle: 

- **card_grid** (hero): 3 cards
    - *Data sources reviewed*: [Data sources reviewed: FLIPCART Targeting last 90 days report; Data sources reviewed: FLIPCART Search Term report; Data sources reviewed: ZAROMA campaign-level data; Data sources reviewed: ZAROMA city-level data; Data sources reviewed: ZAROMA keyword-level d…
    - *Data quality notes*: [Note: Some FLIPCART pivot metrics were unreliable or zeroed, so ratios were recalculated from raw data.; Note: ZAROMA sheets appear to have different coverage; campaign-level totals were used as the primary platform total source and city/keyword sheets were …
    - *Key formulas*: [Key formulas: ROAS = Revenue or Sales / Spend; Key formulas: ACOS = Spend / Sales; Key formulas: CTR = Clicks / Impressions; Key formulas: CPC = Spend / Clicks; Key formulas: CVR = Orders or Purchases / Clicks; Key formulas: CPA = Spend / Orders or Purchases…

## 16. gate-deck-cheffin-full-s5
slide 5 vs base slide 5 · overlap 0.82 · theme 

**Differs:** One KPI row of 7 (items) vs two rows, 3 + 4 (base).

**Same content?** Yes. Same 7 KPIs and narrative.

**items** — label: FLIPCART SNAPSHOT · headline: FLIPCART is generating traffic, but at weak revenue efficiency. · subtitle: Last 90 days

- **kpi_row** (hero): Spend = ₹29.4L; Ad sales = ₹10.1L; ROAS = 0.34x; CPC = ₹31.1; CVR = 5.5%; AOV = ₹195; Allowable CPC for 1.0x ROAS = ₹10.7
- **narrative** (supporting): FLIPCART’s CPC is almost 3x higher than the CPC the current AOV and CVR can support.

**base** — label: FLIPCART SNAPSHOT · headline: FLIPCART is generating traffic, but at weak revenue efficiency. · subtitle: 

- **kpi_row** (hero): Spend = ₹29.4L; Ad sales = ₹10.1L; ROAS = 0.34x
- **kpi_row** (supporting): CPC = ₹31.1; CVR = 5.5%; AOV = ₹195; Allowable CPC for 1.0x ROAS = ₹10.7
- **narrative** (supporting): FLIPCART’s CPC is almost 3x higher than the CPC the current AOV and CVR can support.

## 17. gate-deck-cheffin-full-s6
slide 6 vs base slide 6 · overlap 0.98 · theme 

**Differs:** Match/targeting ROAS as a bar chart (items) vs a second table (base).

**Same content?** Yes. Same figures and insight.

**items** — label: FLIPCART DIAGNOSIS · headline: SBT and exact match are the strongest pockets; discovery layers are dragging ROAS down. · subtitle: 

- **table** (hero): 4 rows; columns: Ad Type / Spend Share / Sales Share / ROAS / Interpretation
    - SP / 75.6% / 75.3% / 0.34x / Main volume driver, but inefficient overall
    - SBV / 12.8% / 8.5% / 0.23x / Weak video efficiency
    - SBT / 9.3% / 15.1% / 0.56x / Best ad type; under-allocated
    - … (+1 more)
- **chart** (peer): bar "ROAS by match/targeting"
    - Exact = 0.44x; Phrase = 0.26x; Auto = 0.30x; Category = 0.25x; Broad = 0.22x; Audience = 0.15x
- **narrative** (supporting): Exact match and SBT should be protected and scaled carefully. Phrase, auto, category, broad, and audience layers need tighter control.

**base** — label: FLIPCART DIAGNOSIS · headline: SBT and exact match are the strongest pockets; discovery layers are dragging ROAS down. · subtitle: 

- **table** (hero): 4 rows; columns: Ad Type / Spend Share / Sales Share / ROAS / Interpretation
    - SP / 75.6% / 75.3% / 0.34x / Main volume driver, but inefficient overall
    - SBV / 12.8% / 8.5% / 0.23x / Weak video efficiency
    - SBT / 9.3% / 15.1% / 0.56x / Best ad type; under-allocated
    - … (+1 more)
- **table** (supporting): 6 rows; columns: Match/Targeting / ROAS
    - Exact / 0.44x
    - Phrase / 0.26x
    - Auto / 0.30x
    - … (+3 more)
- **narrative** (supporting): Main insight: Exact match and SBT should be protected and scaled carefully. Phrase, auto, category, broad, and audience layers need tighter control.

## 18. gate-deck-xtsy-qcomm-s3
slide 3 vs base slide 3 · overlap 0.9 · theme 

**Differs:** items adds a bullet list of the 7 levers. Both card grids are odd: items cards each list "Zepto; Blinkit; Instamart"; base cards each repeat the same 7 levers.

**Same content?** Yes, same points. Both plans have a card defect, so this pair says little.

**items** — label:  · headline: Growth Opportunities for XTSY Across Quick Commerce Platforms · subtitle: 

- **card_grid** (hero): 4 cards
    - *Visibility*: [Zepto; Blinkit; Instamart]
    - *Conversion*: [Zepto; Blinkit; Instamart]
    - *Repeat Purchase*: [Zepto; Blinkit; Instamart]
    - *Market Expansion*: [Zepto; Blinkit; Instamart]
- **bullet_list** (supporting):
    - Search visibility expansion
    - Sponsored placements
    - Category page dominance
    - New city penetration
    - Portfolio expansion
    - Basket attachment opportunities
    - Subscription/repeat purchase growth
- **narrative** (minor): Growth is not limited to ad spends; it is unlocked through visibility, availability, discoverability and repeat purchase strategies.

**base** — label:  · headline: Growth Opportunities for XTSY Across Quick Commerce Platforms · subtitle: 

- **card_grid** (hero): 4 cards
    - *Visibility*: [Search visibility expansion; Sponsored placements; Category page dominance; New city penetration; Portfolio expansion; Basket attachment opportunities; Subscription/repeat purchase growth]
    - *Conversion*: [Search visibility expansion; Sponsored placements; Category page dominance; New city penetration; Portfolio expansion; Basket attachment opportunities; Subscription/repeat purchase growth]
    - *Repeat Purchase*: [Search visibility expansion; Sponsored placements; Category page dominance; New city penetration; Portfolio expansion; Basket attachment opportunities; Subscription/repeat purchase growth]
    - *Market Expansion*: [Search visibility expansion; Sponsored placements; Category page dominance; New city penetration; Portfolio expansion; Basket attachment opportunities; Subscription/repeat purchase growth]
- **narrative** (supporting): Growth is not limited to ad spends; it is unlocked through visibility, availability, discoverability and repeat purchase strategies.

## 19. gate-deck-xtsy-qcomm-s5  ⚠ low overlap (0.33)
slide 5 vs base slide 5 · overlap 0.33 · theme 

**Differs:** items: 2 cards (TRACKING, INSIGHTS) listing the 9 features + tagline. base: a "control tower" visual with no nodes (empty) + 5 feature cards + 4 insight cards, each with a one-line description + tagline.

**Same content?** Partly. Same 9 feature names, but base adds a description per feature (written by the planner, not in the outline) and a visual placeholder. Different slide shape and depth.

**items** — label:  · headline: How Our Commerce Intelligence Platform Drives Faster Growth · subtitle: 

- **card_grid** (hero): 2 cards
    - *TRACKING*: [Share of Search; Share of Shelf; Availability Monitoring; Pricing Intelligence; Competitor Monitoring]
    - *INSIGHTS*: [SKU-level performance; City-level opportunity mapping; Platform-wise growth pockets; Category trends]
- **narrative** (supporting): What gets measured gets scaled.

**base** — label:  · headline: How Our Commerce Intelligence Platform Drives Faster Growth · subtitle: 

- **layer** (hero): Control Tower Dashboard (platform control tower as visual)
    - nodes: 
- **card_grid** (peer): 5 cards
    - *Share of Search*: Measures brand visibility in platform search results
    - *Share of Shelf*: Tracks on-shelf presence and prominence across listings
    - *Availability Monitoring*: Monitors in-stock status across stores and dark stores
    - *Pricing Intelligence*: Detects price placement and promotional activity across SKUs
    - *Competitor Monitoring*: Tracks competitor assortment, pricing and availability
- **card_grid** (supporting): 4 cards
    - *SKU-level performance*: Fine-grained SKU metrics to spot winners and laggers
    - *City-level opportunity mapping*: Identifies high-opportunity cities and gaps in distribution
    - *Platform-wise growth pockets*: Surfaces platform-specific pockets of demand
    - *Category trends*: Tracks category-level shifts and emerging purchase drivers
- **narrative** (minor): What gets measured gets scaled.

## 20. gate-deck-xtsy-qcomm-s6
slide 6 vs base slide 6 · overlap 0.89 · theme 

**Differs:** The 7 engine steps as a flow (base) vs 7 title-only cards (items). Same benefits bullets and tagline.

**Same content?** Yes. Note: items lost the flow; steps would read better as a flow.

**items** — label:  · headline: Ads Automation Engine Designed for Quick Commerce · subtitle: 

- **card_grid** (hero): 7 cards
    - *Input: Platform Data*: (title only)
    - *Decision Engine*: (title only)
    - *Bid Optimization*: (title only)
    - *Budget Reallocation*: (title only)
    - *Keyword Expansion*: (title only)
    - *Placement Optimization*: (title only)
    - *Business Outcome*: (title only)
- **bullet_list** (supporting):
    - Faster optimization cycles
    - Reduced manual intervention
    - Improved ROAS
    - Improved share of visibility
    - Higher conversion efficiency
- **narrative** (minor): Automation allows brands to react in hours instead of weeks.

**base** — label:  · headline: Ads Automation Engine Designed for Quick Commerce · subtitle: 

- **flow** (hero): Platform Data → Decision Engine → Bid Optimization → Budget Reallocation → Keyword Expansion → Placement Optimization → Business Outcome
- **bullet_list** (supporting):
    - Faster optimization cycles
    - Reduced manual intervention
    - Improved ROAS
    - Improved share of visibility
    - Higher conversion efficiency
- **narrative** (supporting): Automation allows brands to react in hours instead of weeks.
