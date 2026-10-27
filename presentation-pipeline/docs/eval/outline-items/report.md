# Outline items, gates 1-2: outline-items-2 vs typed-schema

| | outline-items-2 | typed-schema |
|---|---|---|
| runs / cost | 12 / $0.811 | 18 / $1.157 |
| runs with no outline or an error | 0 | 0 |
| slides (outline / plans) | 74 / 74 | 111 / 111 |

**Gate 1, outline**

| | outline-items-2 | typed-schema |
|---|---|---|
| brief figures not in the outline | 21 of 280 | 28 of 420 |
| outline figures not in the brief | 0 | 0 |
| items | 245 | - |
| kind metric | 43 (18%) | - |
| kind series | 4 (2%) | - |
| kind records | 18 (7%) | - |
| kind steps | 19 (8%) | - |
| kind point | 110 (45%) | - |
| kind visual | 47 (19%) | - |
| kind note | 4 (2%) | - |
| POINT_NOT_IN_BRIEF review points | 6 | - |
| VISUAL_WITH_NUMBERS | 3 | - |
| RECORDS_WITHOUT_MEASURES | 3 | - |
| speaker notes in items | 0 | - |
| slides with the same kinds across repeats | 24 of 37 | - |

**Gate 2, planner**

| | outline-items-2 | typed-schema |
|---|---|---|
| components / per slide | 135 / 1.82 | 233 / 2.10 |
| narrative share | 26 (19%) | 67 (29%) |
| distinct kinds per deck | 6.58 | 6.89 |
| outline figures not in the plan | 2 | 4 |
| KIND_OUTSIDE_FIT | 5 | - |

## Runs with no outline or an error (left out of every count above)

- (none)

## POINT_NOT_IN_BRIEF (read: outline commentary or brief?)

- deck-product-launch-data s6: Auto-discovery of existing APIs to centralize management
- deck-product-launch-data s6: Drag-and-drop routing with automatic conflict detection to remove fragile manual configs
- deck-product-launch-data s6: Auto-scaling and zero-downtime deploys to maintain reliability during load changes
- deck-product-launch-data s6: Eliminates gateway sprawl and reduces manual configuration time
- deck-product-launch-data s6: Prevents misconfiguration-driven outages and improves API reliability
- deck-product-launch-data s6: Provides unified visibility and per-route controls with zero-downtime scaling

## KIND_OUTSIDE_FIT (read: mistake or a legitimate pick?)

- gate-deck-all-nodes-dense s4: KIND_OUTSIDE_FIT: records item drawn as tree (org_tree): Head of Growth: Performance Lead, Retention Lead, Marketplace Lead
- gate-deck-cheffin-full s4: KIND_OUTSIDE_FIT: note item drawn as narrative (data_caveats): Some FLIPCART pivot metrics were unreliable or zeroed, so ratios were recalculat
- gate-deck-cheffin-full s4: KIND_OUTSIDE_FIT: note item drawn as bullet_list (key_formulas): KEY FORMULAS: ROAS = Revenue or Sales / Spend
ACOS = Spend / Sales
CTR = Clicks 
- gate-deck-cheffin-full s4: KIND_OUTSIDE_FIT: note item drawn as narrative (data_quality_notes): - Some FLIPCART pivot metrics were unreliable or zeroed, so ratios were recalcul
- gate-deck-xtsy-qcomm s4: KIND_OUTSIDE_FIT: point item drawn as process_arrow (progression_flow): Show progression from Visibility → Offtakes → Market Share → Profitability

## Item-form issues

- gate-deck-agency-takeover s5 VISUAL_WITH_NUMBERS: Horizontal 3-phase timeline (Stabilize 0-7, Rebuild 8-30, Scale 31-90) with platform-specific bullets under each phase for [Platform B] and [Platform A]
- gate-deck-agency-takeover s6 RECORDS_WITHOUT_MEASURES: [Platform B] data needed: Search term, placement, advertised product reports, SQP data [Platform A] data needed: SKU-level campaign data, city-wise availability, organic sales, keyword-level order/revenue Business data needed: Target ACOS by SKU, Margin by SKU, Launch vs profitability priorities
- gate-deck-all-nodes-dense s2 VISUAL_WITH_NUMBERS: bar chart of quarterly revenue (₹ Cr): Q1 FY26: 2.6 | Q2 FY26: 2.9 | Q3 FY26: 3.3 | Q4 FY26: 3.6 | Q1 FY27: 3.9 | Q2 FY27: 4.4
- gate-deck-all-nodes-dense s4 RECORDS_WITHOUT_MEASURES: Head of Growth: Performance Lead, Retention Lead, Marketplace Lead
- gate-deck-all-nodes-dense s2 VISUAL_WITH_NUMBERS: bar chart of quarterly revenue (₹ Cr): Q1 FY26: 2.6 | Q2 FY26: 2.9 | Q3 FY26: 3.3 | Q4 FY26: 3.6 | Q1 FY27: 3.9 | Q2 FY27: 4.4
- gate-deck-xtsy-qcomm s3 RECORDS_WITHOUT_MEASURES: Visibility: Zepto, Blinkit, Instamart | Conversion: Zepto, Blinkit, Instamart | Repeat Purchase: Zepto, Blinkit, Instamart | Market Expansion: Zepto, Blinkit, Instamart
