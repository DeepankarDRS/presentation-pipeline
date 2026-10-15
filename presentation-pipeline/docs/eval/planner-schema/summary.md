# Planner output schema: offline comparison

Corpus: 1476 distinct saved plan components; 1439 round-trip through the typed content (97.5%).

| candidate | strict-mode problems | schema chars | schema tokens | object properties | depth | enum values | output tokens (round-tripped components) |
|---|---|---|---|---|---|---|---|
| string | 0 | 6,285 | 1,657 | 16 | 2 | 34 | 269,150 (+0%) |
| union | 0 | 18,428 | 5,307 | 192 | 4 | 114 | 234,292 (-13%) |
| slots | 0 | 10,773 | 3,174 | 99 | 4 | 64 | 392,406 (+46%) |
| superset | 0 | 8,076 | 2,494 | 81 | 4 | 60 | 573,113 (+113%) |

| kind | components | round-trip | not round-tripped (reason: count) |
|---|---|---|---|
| title | 436 | 435 | empty (a failed plan, nothing to type): 1 |
| narrative | 248 | 247 | empty (a failed plan, nothing to type): 1 |
| card_grid | 175 | 173 | empty (a failed plan, nothing to type): 1; string_type at cards.0: 1 |
| bullet_list | 167 | 166 | empty (a failed plan, nothing to type): 1 |
| kpi_row | 150 | 148 | empty (a failed plan, nothing to type): 1; missing at kpi_values: 1 |
| table | 100 | 100 |  |
| chart | 64 | 62 | extra_forbidden at chart_series_formatted: 1; empty (a failed plan, nothing to type): 1 |
| caption | 51 | 50 | empty (a failed plan, nothing to type): 1 |
| layer | 25 | 1 | extra_forbidden at nodes.0: 6; missing at layers.0: 5; model_type at nodes.0: 3; extra_forbidden at order: 1; extra_forbidden at visual: 1; empty (a failed plan, nothing to type): 1; extra_forbidden at center_label: 1; extra_forbidden at orientation: 1; extra_forbidden at diagram_type: 1; extra_forbidden at visual_suggestion: 1; extra_forbidden at diagram_nodes: 1; extra_forbidden at center_node: 1; extra_forbidden at layers_top_to_bottom: 1 |
| timeline | 22 | 22 |  |
| matrix | 14 | 11 | missing at x_axis: 3 |
| flow | 12 | 12 |  |
| process_arrow | 10 | 10 |  |
| tree | 1 | 1 |  |
| pyramid | 1 | 1 |  |

Examples of components that do not fit the typed content:
- layer: `extra_forbidden at order: {"order": "top-to-bottom", "layers": [{"title": "Channels", "items": ["Website", "QUIKMART", "DASHCART"]}, {"title": "Customer data", "items": ["profiles", "pur`
- layer: `extra_forbidden at visual: {"visual": "Control Tower Dashboard"}`
- layer: `extra_forbidden at nodes.0: {"nodes": [{"id": "zepto", "label": "Zepto"}, {"id": "blinkit", "label": "Blinkit"}, {"id": "instamart", "label": "Instamart"}, {"id": "growth_engine", "label":`
- card_grid: `string_type at cards.0: {"card_layout": "steps", "cards": [{"title": "Days 0–7 (Stabilize)", "body": ["[Platform B]: Pause or negative 10+ click zero-sales terms. Reduce bids on ROAS <`
- matrix: `missing at x_axis: {"matrix_axes": {"rows": ["Zepto", "Blinkit", "Instamart"], "columns": ["Search visibility expansion", "Sponsored placements", "Category page dominance", "New c`
- matrix: `missing at x_axis: {"matrix_axes": {"rows": ["Zepto", "Blinkit", "Instamart"], "columns": ["Visibility", "Conversion", "Repeat Purchase", "Market Expansion"]}, "matrix_items": [{"`
- matrix: `missing at x_axis: {"matrix_axes": {"columns": ["Zepto", "Blinkit", "Instamart"], "rows": ["Visibility (search, sponsored placements, category page)", "Conversion (basket attachme`
- kpi_row: `missing at kpi_values: {"kpi_labels": ["ARR", "NRR", "Margin", "CAC"]}`
- chart: `extra_forbidden at chart_series_formatted: {"chart_type": "bar", "chart_title": "Actual CPC vs Allowable CPC for 1.0x ROAS", "chart_labels": ["FLIPCART", "ZAROMA"], "chart_series": [{"name": "Actual CPC"`
