# Golden slide fixtures

Compile + render-verified reference slides in the dense editorial house style.
They define the quality bar and act as a regression set — **they are NOT
injected into any prompt.** The generator learns the style from
`src/knowledge/core/house-style.yaml` (the grammar); these prove the grammar
can express that quality and catch regressions when the grammar or generator
prompt changes.

| fixture | exercises |
|---|---|
| editorial-earnings   | KPI card row + bar chart + dark hero panel + accent callouts |
| editorial-dashboard  | 3-band multi-chart dashboard (area / doughnut / bar / radar) |
| editorial-roadmap    | ProcessArrow + Matrix + phase cards + value-case panel |
| editorial-strategy   | hero-panel choice + Matrix + 4 "how" cards |
| editorial-comparison | Table + pull-quote hero panel + callout — built from the grammar ALONE (not one of the 4 source references) to prove generalization |

Run:

    python -m scripts.render_check --in tests/fixtures/golden --out output/render_check_golden

Then open the PDFs under `output/render_check_golden/<name>/presentation.pdf`.
All five must stay `compile=ok` and `audit_high=0`.
