# KPI planning-only runs (9 runs, $0.619)

KPI slides: 12; split into several kpi_rows: 5; numbers in two groups: 0; key-message numbers no component carries: 1.

| case | run | slide | numbers | groups (id, weight, items) | other components | in two groups | not carried |
|---|---|---|---|---|---|---|---|
| deck-qbr-data | 1 | 1 | 4 | headline_kpis (hero, 4) | title | - | - |
| deck-qbr-data | 2 | 1 | 4 | kpi_metrics (hero, 4) | title | - | - |
| deck-qbr-data | 3 | 1 | 4 | kpi_dashboard (hero, 4) | title, narrative, table | - | - |
| gate-deck-cheffin-full | 1 | 1 | 5 | kpi_summary (hero, 5) | title, narrative | - | - |
| gate-deck-cheffin-full | 1 | 4 | 7 | flipkart_kpis (hero, 7) | title, narrative | - | 1.0x |
| gate-deck-cheffin-full | 2 | 1 | 5 | combined_kpis (hero, 3); platform_roas (peer, 2) | title, narrative, narrative | - | - |
| gate-deck-cheffin-full | 2 | 4 | 7 | platform_metrics_hero (hero, 4); efficiency_kpis_support (supporting, 3) | title, narrative | - | - |
| gate-deck-cheffin-full | 3 | 1 | 5 | combined_kpis (hero, 3); platform_roas_kpis (peer, 2) | title, narrative | - | - |
| gate-deck-cheffin-full | 3 | 4 | 7 | flipcart_kpis (hero, 7) | title, narrative | - | - |
| gate-deck-all-nodes-dense | 1 | 1 | 5 | hero_repeat_kpi (hero, 1); top_kpi_row (peer, 4) | title, chart, narrative | - | - |
| gate-deck-all-nodes-dense | 2 | 1 | 5 | top_kpis (peer, 4); repeat_kpi (hero, 1) | title, chart, narrative | - | - |
| gate-deck-all-nodes-dense | 3 | 1 | 5 | kpi_metrics (hero, 5) | title, chart, narrative | - | - |

## Groups in detail

**deck-qbr-data r1 slide 1** — Headline KPIs: strong growth with mixed unit economics
- `headline_kpis` hero: ARR $48.2M, NRR 114%, Gross Margin 72.1%, CAC Payback 14 months — _make deltas visually prominent next to each value; color-code positive deltas (ARR, NRR) in positive color and the Gross Margin delta in negative color; include_

**deck-qbr-data r2 slide 1** — ARR $48.2M; retention up, margin down, CAC improving
- `kpi_metrics` hero: ARR $48.2M, NRR 114%, Gross Margin 72.1%, CAC Payback 14 months — _hero KPI row; emphasize the ARR tile as the primary tile; color-code deltas by meaning — ARR and NRR deltas in positive color, Gross Margin delta in negative co_

**deck-qbr-data r3 slide 1** — ARR up, NRR improving, margin compressed, payback shortening
- `kpi_dashboard` hero: ARR $48.2M, NRR 114%, Gross Margin 72.1%, CAC Payback 14 months — _color-code tiles by meaning: ARR and NRR tiles in positive color, Gross Margin in negative color, CAC Payback tile in positive color; show the CAC Payback unit _

**gate-deck-cheffin-full r1 slide 1** — The account is spending at scale, but not yet buying profitable demand.
- `kpi_summary` hero: Combined spend ₹114.9L, Combined revenue ₹37.4L, Combined ROAS 0.33x, FLIPCART ROAS 0.34x, ZAROMA ROAS 0.32x — _highlight the ROAS tiles (Combined ROAS, FLIPCART ROAS, ZAROMA ROAS) in negative color to emphasize the ROAS gap; mute the spend and revenue tiles_

**gate-deck-cheffin-full r1 slide 4** — FLIPCART is generating traffic, but at weak revenue efficiency.
- `flipkart_kpis` hero: Spend ₹29.4L, Ad sales ₹10.1L, ROAS 0.34x, CPC ₹31.1, CVR 5.5%, AOV ₹195, Allowable CPC ₹10.7 — _emphasize CPC (₹31.1) in negative color and Allowable CPC (₹10.7) in a contrasting/warning color; make those two tiles the visual focus (one item in focus)_

**gate-deck-cheffin-full r2 slide 1** — The account is spending at scale, but not yet buying profitable demand.
- `combined_kpis` hero: Spend ₹114.9L, Revenue ₹37.4L, ROAS 0.33x — _emphasize the ROAS tile (0.33x) in negative color; other tiles recede_
- `platform_roas` peer: FLIPCART ROAS 0.34x, ZAROMA ROAS 0.32x — _color both platform ROAS tiles in negative (underperforming) and keep tiles equal weight_

**gate-deck-cheffin-full r2 slide 4** — FLIPCART is generating traffic, but at weak revenue efficiency.
- `platform_metrics_hero` hero: Spend ₹29.4L, Ad sales ₹10.1L, ROAS 0.34x, Allowable CPC for 1.0x ROAS ₹10.7 — _make 'Allowable CPC for 1.0x ROAS' the visual focus (elevated/inverted panel); color ROAS in negative color to indicate underperformance_
- `efficiency_kpis_support` supporting: CPC ₹31.1, CVR 5.5%, AOV ₹195 — _color-code the CPC tile in negative color (actual > allowable); keep CVR and AOV neutral to support the CPC comparison_

**gate-deck-cheffin-full r3 slide 1** — The account is spending at scale, but not yet buying profitable demand.
- `combined_kpis` hero: Combined spend ₹114.9L, Combined revenue ₹37.4L, Combined ROAS 0.33x — _emphasize the Combined ROAS tile and color it negative (red); other tiles muted so ROAS stands out_
- `platform_roas_kpis` peer: FLIPCART ROAS 0.34x, ZAROMA ROAS 0.32x — _color both FLIPCART ROAS and ZAROMA ROAS in negative (red); keep both tiles equal weight_

**gate-deck-cheffin-full r3 slide 4** — FLIPCART is generating traffic, but at weak revenue efficiency.
- `flipcart_kpis` hero: Spend ₹29.4L, Ad sales ₹10.1L, ROAS 0.34x, CPC ₹31.1, CVR 5.5%, AOV ₹195, Allowable CPC for 1.0x ROAS ₹10.7 — _make flipcart_kpis the primary scorecard; highlight the 'CPC' tile and the 'Allowable CPC for 1.0x ROAS' tile: color the CPC tile in negative tone, color the Al_

**gate-deck-all-nodes-dense r1 slide 1** — Repeat customers now drive most of BREWLY's revenue.
- `hero_repeat_kpi` hero: Repeat customers 62% of revenue — _render as a large dark/inverted tile on the left; emphasize the '62% of revenue' value and show the delta 'up from 41% a year ago' in positive color; lift the c_
- `top_kpi_row` peer: Annual revenue ₹14.2Cr, Revenue growth +38%, Blended ROAS 2.4x, Customer acquisition cost ₹410 — _render four peer tiles across the top to the right of the hero tile; color '+38%' and '2.4x' in positive color, keep '₹410' neutral; include an icon in each til_

**gate-deck-all-nodes-dense r2 slide 1** — Repeat customers now drive most of BREWLY's revenue.
- `top_kpis` peer: Annual revenue ₹14.2Cr, Revenue growth +38%, Blended ROAS 2.4x, Customer acquisition cost ₹410 — _KPI tiles across the top; color Revenue growth in positive/accent and render Customer acquisition cost in a muted tone so it recedes_
- `repeat_kpi` hero: Repeat revenue 62% — _dark / inverted panel that visually elevates and emphasizes the 62% tile as the hero metric_

**gate-deck-all-nodes-dense r3 slide 1** — Repeat customers now drive most of BREWLY's revenue.
- `kpi_metrics` hero: Annual revenue ₹14.2Cr, Revenue growth +38%, Blended ROAS 2.4x, Customer acquisition cost ₹410, Repeat revenue share 62% — _one item in focus: dark / inverted panel and elevated treatment on the 'Repeat revenue share' (62%) tile; keep other tiles large but visually receded_
