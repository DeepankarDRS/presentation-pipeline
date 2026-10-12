# KPI tile nodes: paid check (2026-10-12, test PC)

`python -m scripts.kpi_paid --blocks tiles --arm-a kpi --label tiles-paid --no-render --bundle` on `bb52ca5`
(spec §8 step 5, `docs/tile-nodes-spec-2026-10-12.md`). Generator only (gpt-4.1), on the 3 saved KPI slide plans
(`docs/eval/kpi-node/paid-inputs.json`), **one try each** (the command left out `--repeat 3`: these numbers show the
route works, not how stable it is). Arm A = the same slides from the 2026-10-11 element-ref paid check, recompiled on
this commit. Re-scored and rendered on the build PC (`--rescore --arm-a kpi`).

## Gate (spec §8): passed, at the threshold

| | result | gate |
|---|---|---|
| blind marks (user, `marks.csv`) | **0.5**: tiles win 1.3, tie 1.2, lose 1.1 | ≥ 0.5 |
| KPI output tokens | 10 / 131 / 17 a slide vs ~400–760 hand-written: **~−90%** | ≥ −50% |

## Accuracy

KPI values placed on the first try 16/16; NODE_* errors 0; repairs 0; compiled 3/3; values off plan 0; broken words
0 / 0; hand-written fallback tiles 0. Emphasis held: `inverted` + `size="hero"` only on Combined ROAS, the one item
the plan singles out.

What the LLM wrote (`first-*.xml`):

| slide | KPI tags | tokens |
|---|---|---|
| QBR 1 | `<KpiGrid ref="kpi_metrics" layout="row" cols="4"/>` | 17 |
| CHEFFIN 1 | group of 3 with the emphasis tile `inverted` + `hero`; second group `filled` + `color="$negative"` on both tiles | 131 |
| CHEFFIN 4 | `<KpiGrid ref="flipkart_kpis"/>` | 10 |

No icons and, apart from CHEFFIN 1, no variant: the LLM took the defaults.

## Tokens and cost (generator, same 3 slides; cost with cached input at $0.50/M, `bb52ca5`)

| | 2026-10-11 element refs | tile nodes | change |
|---|---|---|---|
| input | 35,001 | 31,347 | −10% |
| of which cached | 0 | 8,064 | CHEFFIN 4 reused the deck's prefix from CHEFFIN 1 (0 on 2026-10-11) |
| output | 2,582 | 959 | **−63%** |
| cost | $0.091 | $0.058 | **−36%** |

CHEFFIN 1 got no cache hit from the QBR call before it although the first ~7k system tokens are the same across
decks (OpenAI's cache is best effort; one sample).

## Marks and why

| pair | slide | user's choice | reason (user) |
|---|---|---|---|
| 1.1 | QBR 1 | element refs | better usage and colour code |
| 1.2 | CHEFFIN 1 | same | |
| 1.3 | CHEFFIN 4 | **tile nodes** | best space allocation for the 7 cards (default grid 4 + 3 vs 7 in a row) |

**The loss (1.1) is the prompt, not the drawing.** The QBR plan has no `kpi_tones`, but its design hint names the
colours: "Emphasize the ARR tile as the hero …; color-code Gross Margin in the negative palette; show ARR and NRR in
positive color; render CAC Payback's −2 months delta in positive color". On the element-ref route the LLM drew that
(tinted tiles, coloured numbers, a lifted ARR tile). On tiles it wrote a bare `<KpiGrid>`; the tile syntax could say
all of it (`color`, `note.color`, `variant`), but nothing in the prompt asks for the visual-intent to be applied to the
tiles, and the defaults read as "code draws it". Notes then fell to the accent colour (no tones → role accent). The hero
was lost too: `spec.singled_out` only accepts a hint that names exactly one label, and this one names four.
Also on 1.1 (not tile-related): the LLM's header stack had `alignItems="start"`, and the headline wrapped at half
width in the render (the known POM-measure vs drawn-font gap).

## Proposed next (free unless noted)

1. **Prompt**: one line in the fixed tile lines, roughly "apply the component's visual-intent with `color` /
   `note.color` / `variant` per item; with no tones given, colour each item by what the hint says".
2. **Emphasis**: `spec.singled_out` takes the label nearest the emphasis word ("ARR tile as the hero") when the hint
   names several labels. It is still the plan that picks the item, not the LLM; needs your OK (rule of 2026-10-07).
3. **Planner tones** (spec §6, look spec V10): fill `kpi_tones` so colour by meaning doesn't depend on the generator
   reading the hint.
4. Then the 3-repeat paid check (`--repeat 3`, ≈ $0.17) for stability and a firmer mark.
