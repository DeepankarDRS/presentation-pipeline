# Chart pass (2026-10-22)

Steps 4 and 8 of `docs/look-and-feel-review-2026-10-21.md`. Everything here is LLM-free: no paid run and no
API key. The colour method and the validator come from the dataviz skill. Its Python validator is copied
unchanged into `src/compiler/dataviz_palette.py`, so the tests and the repair use the skill's own thresholds.

## What changed

| Area | Change | Files |
|---|---|---|
| Legends (L6) | All 8 `showLegend="true"` knowledge examples are gone (chart.yaml 1, blueprints 6, golden examples 1). Single-series examples now use one token or the focus pair. The two-series line example names its series in the title row: a 12 px square of the series colour, then the name. The golden QBR chart is now one series with the latest quarter in focus. The blueprint doughnut has 2 parts with a text caption. The literal hex in those chart examples is now tokens. | `components/chart.yaml`, `core/blueprints.yaml`, `core/golden-examples.yaml` |
| Teaching | chart.yaml has a focus-colour note and a no-legend note. The pitfall "list $chart1, $chart2 … so bars are distinguishable" taught one colour per bar, so it is reversed. house-style has a new `chart_rules` section (one paragraph, added to the generator's house-style block). The generator chart note covers every chart type plus the latest-period fallback. palettes.yaml usage line updated. | `core/house-style.yaml` (chart_rules only; no type ramp / font edits), `agents/context_builder.py`, `theme/palettes.yaml` |
| Focus colour in code | `CHART_FOCUS_LATEST` is now `_chart_focus`, which covers every chart type. The bar / slice (one series) or series (several) that the **headline** names gets the focus colour. The headline is the first Text of 24 px or more outside the chart. If the headline names none and the labels are periods, the **latest** gets it. The rule only *moves* a focus the LLM already drew (one focus colour against exactly one grey / pale base), so good / bad colourings are never touched. It also reads the `chartColors="[&quot;…&quot;]"` form, which the old rule missed. A one-series bar chart painted `$chart1, $chart2, …` bar by bar becomes one hue, or `$accent` on the named / latest bar. New codes: `CHART_FOCUS_NAMED`, `CHART_ONE_HUE`; `CHART_FOCUS_LATEST` is kept. | `compiler/normalizer.py` |
| Chart series colours | `separate_chart_colors` (palette_tokens) repairs each palette's chartColors in code; no hex was edited by hand. Hue is kept. Lightness moves into OKLCH 0.45–0.75 and chroma rises to the 0.10 floor. Greys (C < 0.03, the job of `$neutral`) are dropped. The order is chosen so every neighbour passes: colour-blind ΔE ≥ 8 (target), normal ΔE ≥ 15, lightness ratio ≥ 1.4 (§5.4). Any two series also stay ≥ 15 apart, because a line chart shows them all at once. A colour that no step can fit is dropped. Chart 1 keeps the first authored hue. | `compiler/palette_tokens.py`, `agents/style_resolver.py` |
| Positive / negative (A6) | `separate_polarity` takes the smallest lightness step (hue kept) of either colour that reaches a lightness ratio ≥ 1.3 and colour-blind ΔE ≥ 8. Both colours keep ≥ 3:1 on surface / surfaceAlt. It runs before the derived `*Soft` / `*Text`, so those follow. | same |
| Tests | `tests/unit/test_chart_palettes.py`: 6 checks × 28 palettes (seed palettes included) plus 3 unit cases. The 2 old focus tests are rewritten and 5 added in `test_deck_quality_fixes.py`. | |
| Tools | `python -m scripts.chart_survey --roots <output dirs>` gives every saved chart and what the focus rule changes. `python -m scripts.chart_gallery [palettes] --slide <input.xml>` gives before / after sheets with a deuteranopia row (needs LibreOffice; it uses a private profile). | `scripts/` |

Unit tests: baseline 1378 pass + 4 known failures. After this change: 1554 pass (176 new) + the same 4
known failures. The generator prompt stays under the `test_prompt_standard_components` budget because the chart
rule is written once (CHART RULES) and chart.yaml / the generator note point to it.

## Before / after: palettes (28, every palette in `palettes.yaml`)

| Check | Before | After |
|---|---|---|
| dataviz validator on chartColors (band, chroma, CVD, normal vision) | **0 / 28** pass | **28 / 28** (CVD at the 8.0 target, not only the 6.0 floor) |
| Neighbouring series ≥ 1.4:1 in lightness | 1 / 28 | 28 / 28 |
| positive / negative ≥ 1.3:1 lightness | 11 / 28 | 28 / 28 |
| positive / negative colour-blind ΔE ≥ 8 | 13 / 28 | 28 / 28 |
| `$accent` vs `$neutral` (focus pair) normal ΔE ≥ 15 and CVD ≥ 8 | (not measured) | 28 / 28 |

Cost: series per palette drop from 5–6 to 2–6 (median 5). Separable colours are fewer than authored ones:

| palette | series | worst adjacent CVD ΔE | adjacent lightness | pos/neg lightness | pos/neg CVD ΔE |
|---|---|---|---|---|---|
| corporate-slate | 5 → 4 | 12.2 → 14.1 | 1.11 → 1.42 | 1.04 → 1.71 | 8.6 → 8.3 |
| sky-minimal | 5 → 3 | 17.3 → 21.7 | 1.11 → 1.44 | 1.04 → 1.71 | 8.6 → 8.3 |
| teal-slate | 5 → 3 | 11.8 → 13.9 | 1.31 → 1.48 | 1.16 → 1.69 | 1.9 → 8.5 |
| emerald-clean | 5 → 5 | 9.6 → 15.0 | 1.11 → 1.41 | 1.14 → 1.33 | 8.6 → 9.7 |
| forest-editorial | 5 → 4 | 1.9 → 8.7 | 1.14 → 1.55 | 1.09 → 1.35 | 8.3 → 8.6 |
| warm-editorial | 5 → 4 | 8.1 → 12.4 | 1.13 → 1.46 | 1.30 → 1.72 | 1.5 → 8.4 |
| amber-mono | 5 → 4 | 12.5 → 16.1 | 1.16 → 1.43 | 1.19 → 1.65 | 2.2 → 8.2 |
| rose-report | 5 → 3 | 6.8 → 19.2 | 1.61 → 1.43 | 1.29 → 1.71 | 4.2 → 8.7 |
| violet-modern | 5 → 5 | 22.8 → 15.9 | 1.35 → 1.47 | 1.04 → 1.71 | 8.6 → 8.3 |
| saascolor | 6 → 5 | 2.8 → 24.5 | 1.30 → 1.43 | 1.30 → 1.66 | 2.8 → 8.4 |
| navy-orange | 6 → 6 | 1.2 → 16.8 | 1.05 → 1.43 | 1.15 → 1.67 | 1.2 → 8.8 |
| gj-h1 | 5 → 5 | 9.5 → 12.5 | 1.19 → 1.47 | 1.12 → 1.69 | 3.5 → 8.8 |
| claude-cream | 5 → 3 | 5.2 → 8.4 | 1.02 → 1.52 | 1.22 → 1.62 | 4.5 → 8.8 |
| graphite-mono | 5 → **2** | 11.4 → 16.1 | 1.00 → 1.90 | 1.04 → 1.71 | 8.6 → 8.3 |
| graphite-dark | 5 → 5 | 10.3 → 8.9 | 1.03 → 1.58 | 1.59 → 1.64 | 7.9 → 8.8 |
| midnight-indigo | 5 → 5 | 10.4 → 8.9 | 1.15 → 1.46 | 1.59 → 1.64 | 7.9 → 8.8 |
| forest-dark | 5 → 5 | 9.2 → 10.9 | 1.04 → 1.41 | 1.87 → 1.87 | 15.5 → 15.5 |
| carbon-dark | 5 → 5 | 1.4 → 10.4 | 1.11 → 1.51 | 1.59 → 1.64 | 7.9 → 8.8 |
| boardroom-orange | 6 → 4 | 2.9 → 9.3 | 1.04 → 1.74 | 1.18 → 1.65 | 2.9 → 8.1 |
| paper-clay | 6 → 5 | 8.4 → 10.7 | 1.08 → 1.46 | 1.58 → 1.58 | 8.8 → 8.8 |
| bone-copper | 6 → 5 | 9.8 → 19.2 | 1.15 → 1.61 | 1.02 → 1.32 | 9.9 → 8.7 |
| ocean-light | 6 → 5 | 2.8 → 8.2 | 1.00 → 1.48 | 1.04 → 1.71 | 8.6 → 8.3 |
| terracotta-light | 6 → 5 | 3.1 → 9.0 | 1.02 → 1.43 | 1.54 → 1.90 | 3.1 → 8.2 |
| ink-copper | 6 → 5 | 9.0 → 19.2 | 1.02 → 1.61 | 1.52 → 1.77 | 4.1 → 9.2 |
| lime-ink | 6 → 5 | 5.6 → 11.7 | 1.01 → 1.71 | 2.50 → 2.50 | 20.0 → 20.0 |
| ocean-dark | 6 → 5 | 6.6 → 8.5 | 1.02 → 1.40 | 1.59 → 1.64 | 7.9 → 8.8 |
| tropic-dark | 6 → 5 | 9.3 → 9.3 | 1.03 → 1.59 | 1.81 → 1.81 | 11.6 → 11.6 |
| terracotta-dark | 6 → 4 | 3.1 → 9.1 | 1.01 → 1.43 | 1.00 → 1.34 | 9.0 → 10.8 |

Charts on dark palettes sit on the light `$chartSurface` card, because POM draws axis text black. All series
are therefore checked in the light band against the chart surface.

Visible side effects: on the 5 light palettes with red `DC2626` and green `15803D` (corporate-slate,
sky-minimal, violet-modern, graphite-mono, ocean-light), `negative` becomes a deeper red (`9C060E`).
Darkening the green instead passes through red's lightness as protanopes see it (colour-blind ΔE falls to
0.5 at OKLCH L 0.44), so the red moves. On others the green
lightens a step (teal-slate `2F7D32` → `4C994D`). Dark inks and greys leave the chart palette (they read as
`$neutral`), and the second series is often a different authored hue than before.

## Before / after: saved chart slides (free survey)

`python -m scripts.chart_survey --roots <main checkout>/output`: 93 unique slides with a chart, 105 charts.
86 bar, 12 line, 3 area, 3 doughnut. 70 are one series, 35 are multi-series, and **all 35 multi-series have a
legend**. 102 / 105 carry literal hex (old runs). Colouring: 67 focus + rest, 20 colour per series, 12 one
colour per bar of a single series, 3 one colour.

Focus rule on the same files: the old rule changed 15. The new one changes **25** (19 latest, 6 named). The
extra 10 are all the `&quot;` form the old rule never read. All 25 are the same fault: the focus colour on
the first (or first and last) quarter of a revenue trend, moved to the latest / named quarter (e.g. "Revenue
accelerated to 48.2M in Q3 FY26" → Q3 FY26). I found no false move when reading the list
(`--list`). The 12 rainbow bars are literal hex, so `CHART_ONE_HUE` (token-only, by design) leaves them alone.

## Renders (LibreOffice, `python -m scripts.chart_gallery`)

Each sheet has BEFORE on the left and AFTER on the right. The second row is the same slide under simulated
deuteranopia. Each sheet shows a specimen slide (3-series line with a title-row key, every series as bars, a
focus bar, good / bad bars) and the saved QBR revenue slide (`run-1008` slide 2) re-skinned with theme_swap.

- `docs/eval/chart-pass/corporate-slate.png` (light, default)
- `docs/eval/chart-pass/terracotta-light.png` (light, worst before: CVD 3.1, normal 6.6)
- `docs/eval/chart-pass/navy-orange.png` (light, worst CVD before: 1.2)
- `docs/eval/chart-pass/midnight-indigo.png` (dark)

What they show: the QBR slide's two blue bars (Q2 FY25 and Q3 FY26) become one, on Q3 FY26. Neighbouring
bars now differ in lightness, so under deuteranopia terracotta-light's C / D / E bars (before: three similar
yellows) step dark / light. Good / bad bars differ in lightness in every palette, and the sign / arrow rule
still applies.

## Value labels on bars: decision note (not built)

POM's `<Chart>` writes no `<c:dLbls>`, so no chart shows its values. In the saved corpus, 54 of 94 unique
charts are one-series bars of 3–6 points with values of 3–5 characters. Every one of them would fit a
labelled bar. Another 21 are grouped bars of 2–3 series with 6 points or fewer.

| Option | What | Size | Risk |
|---|---|---|---|
| A. Code-drawn labelled column block (review step 4c) | A derived node that draws bars as Shapes with a Text value above each one, sized by fit-grow | New node, fit-grow sizing, geometry rules, prompt line; ~300+ lines | Gives up the native chart (no editing in PowerPoint). Layout bugs of the kind the KPI-tile and card nodes had. |
| **B. Native data labels in `pptx-post.js`** | Insert `<c:dLbls>` (`showVal`, `outEnd`, 14 pt bold, ink colour) into one-series bar charts of 8 points or fewer | ~30 lines + a test | The schema order inside `<c:ser>` must be right, or PowerPoint shows a repair prompt. **Only checked in LibreOffice so far.** |

I prototyped B in the scratchpad on the saved QBR slide. It rendered cleanly in LibreOffice
(`docs/eval/chart-pass/value-labels-labels.png` vs `value-labels-plain.png`).

**Recommendation: B, not A.** It stays a native, editable chart and touches no layout. It is not built here
because it is only safe after one PowerPoint open check on the test PC.

## Open decisions for the user

1. **Value labels (above).** Build option B? If yes, label **every bar** (the hand-QBR look, hand-qbr #8) or
   only the **focus bar** (dataviz: selective labels; `<c:dLbl>` per point)? It needs one PowerPoint open
   check either way.
2. **Fewer series per palette.** graphite-mono keeps 2 chart colours, and sky-minimal, teal-slate, rose-report
   and claude-cream keep 3. `$chart(N+1)` repeats `$chart1`. The planner rule is already "2–3 equally
   important series", so this rarely binds. A 4th series on those palettes needs a decision: fold it into
   "Other", use `$neutral`, or accept the repeat.
3. **Deeper red for bad.** `DC2626` → `9C060E` on the red / green palettes is what the colour-blind gap costs.
   The alternative is a sign / arrow only, with no lightness gap (A6 says both).
4. **Legends in code-drawn charts.** `nodes/native.py` (the `<Chart ref>` node) still turns the legend on for
   more than 1 series and for pie. Removing it needs the title-row key in code as well. I left it as it is
   (code, not knowledge).
5. **Rainbow bars in hex.** 12 saved charts colour one series bar by bar with literal hex. New runs write
   tokens, so the token-only `CHART_ONE_HUE` covers them. A hex version would need a theme in the
   normalizer, so I left it.
6. **Unmeasured on fresh decks.** The knowledge and prompt changes only show on the next paid six-deck run
   (review step 1). Things to count there: legends (0 expected), focus on the named / latest bar, and series
   named in the title row.
