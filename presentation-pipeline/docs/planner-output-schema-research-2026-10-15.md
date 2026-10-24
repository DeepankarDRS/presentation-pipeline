# Planner output schema for a reasoning model (2026-10-15)

**Question.** The slide component planner (`src/agents/planning/slide_component_planner.py`, gpt-5-mini, reasoning effort
medium, `max_tokens` 24000) returns `PlannerSlide` through langchain `with_structured_output(method="json_schema")`.
Each component carries its content as `content_data_json: str`, JSON written inside a string. On a reasoning model
that string is sometimes unreadable. Which output schema should replace it, so content is a typed object?

**Answer (recommendation).** Candidate **B, "union"**: `components` is a list of one component model per kind
(JSON-schema `anyOf` of 15 objects, each starting `component_id`, `kind` const), each with only the fields its kind
uses and a typed `content` whose keys are today's content_data keys. Built behind `PLANNER_SCHEMA=typed`
(`src/agents/schemas/planner_schema_typed.py`); the string path stays the default until the paid check below passes.
Offline it passes every documented strict-mode rule, round-trips 99.6% of saved non-layer components unchanged,
and writes **13% fewer output tokens** than today's string form. Its cost is a larger schema: +3.6k input tokens a
call (about +28% of the planner's 12.9k input; part of the cached prefix).

## 1. Evidence: what fails, and why only on gpt-5-mini

`output/card-plans/choice-plans/run.log` (test PC, 2026-10-15, 18 plan-only runs, 119 answered planner calls),
scored with `python -m scripts.tools.planner_schema_compare --logs ...`:

| | choice-plans (10-15) | tile-combined (10-15) |
|---|---|---|
| planner calls answered | 119 | 44 |
| unreadable `content_data_json` fields | 24 | 6 |
| runs with unreadable content | 7 of 18 | 2 |
| re-asks (all causes) | 10 | 5 |
| first tries that spent all output tokens on reasoning | 3 | 0 |
| fallback plans | 1 (XTSY r2 slide 6) | 0 |
| output tokens p50 / p90 / max (incl. reasoning) | 3438 / 5670 / 19526 | 3766 / 5441 / 8474 |
| input tokens p50 | 12933 | 12576 |

What the unreadable strings look like:
- 13 of 24 are **exactly `{`** (1 character), and they come in whole calls: every component of that call is `{`
  (QBR r2 s5: 2 of 2; all-nodes r1 s5: 4 of 4; XTSY r2 s2: 3; XTSY r2 s5: 4 on both tries → fallback).
- The rest are the model giving up on the string form: `content_data_json:INVALID_PLACEHOLDER_REPLACED_BY_VALID_JSON`
  (4 components of one call), `design_hint_raw_workaround_field_ignore_if_parser_accepts_objects_please_put…`,
  `content_data_json_raw_not_string_error_workaround_do_not_edit_this_field_p…`, `title`, a sentence about the JSON.
  The model's own words name the conflict: it wants to write an object and the schema says string.

**Cause.** Strict structured outputs constrain decoding to the schema's grammar. Inside a JSON string the next
unescaped `"` *ends* the string. All five worked examples in `system.j2` (since `a332842`, 2026-09-21) write
`"content_data_json": {"title": ...}` as an **object**, contradicting the schema. When the model starts the object
inside the string (`"{` then `"title"`), the grammar takes that `"` as the string's end: the value is `{`, and every
later component of the same answer repeats the pattern. When the model notices the conflict while reasoning, it
writes a placeholder instead. No parser can recover either. The tolerant read added on 10-15 (`parse_content_data`,
field name glued before the object) covers a third, rarer form.

**Why not on gpt-4.1.** The same object-shaped examples were in the prompt for the gpt-4.1 planner (09-21 → 10-01), so
gpt-4.1 escaped the inner quotes correctly. The log text of unreadable fields is only kept since `581d579`
(2026-10-13), so the gpt-4.1 period has no log lines to search; the proxy is the saved plans: across the deck runs
saved up to 09-30 (planner gpt-4.1) no component has empty content apart from one mocked integration-test run
(`output/runs/planner-e2e`), while the gpt-5-mini period has them in 9 real decks. This agrees with the user's
observation. Outside reports describe similar breakage on GPT-5-family models: unescaped quotes breaking out of a
string under `json_schema` (GPT-5.5), malformed / concatenated JSON with `.parse` on GPT-5 models that went away on
gpt-4o (sources below).

The 3 length-limit first tries (all 24000 output tokens spent on reasoning, no answer) are a separate failure: a
typed schema removes the escaping work, but whether it shortens runaway reasoning is unknown until a paid run.

## 2. What strict Structured Outputs allow (OpenAI docs, read 2026-10-15)

From developers.openai.com/api/docs/guides/structured-outputs, "Supported schemas":
- Types: string, number, boolean, integer, object, array, enum, **anyOf**. Constraints: string `pattern` / `format`;
  number `minimum` / `maximum` / `multipleOf`; array `minItems` / `maxItems`; `$defs` + `$ref`, **recursion**
  (`"$ref": "#"` or a `$defs` self-reference).
- Not supported: `allOf`, `not`, `if` / `then` / `else`, `dependentRequired`, `dependentSchemas`; `oneOf` /
  `discriminator` are not in the subset (so a Pydantic `Field(discriminator=...)` union, which emits `oneOf`, is
  out; a plain `Union` emits `anyOf` and is fine).
- Every object needs `additionalProperties: false` and **every property in `required`**; optional = a union with
  null. The root must be an object, not `anyOf` (a union is fine one level down, e.g. inside `components`).
- Limits: 5000 object properties, **10 levels of nesting**, 1000 enum values, 120,000 characters of property names,
  definition names, enum and const values; a string enum over 250 values at most 15,000 characters.
- Output keys follow the schema's key order. The first request with a new schema has extra latency (the grammar is
  built once, then cached).

How our stack sends it: `with_structured_output(PlannerSlide, method="json_schema")` passes the Pydantic class through
(`_convert_to_openai_response_format`), and the openai SDK (`type_to_response_format_param` →
`to_strict_json_schema`) sends it with **`strict: true`**, adding `additionalProperties: false` and making every
field required; `None` defaults are stripped, other defaults and titles stay in the schema text. langchain 0.3.86 /
langchain-openai with openai 1.109.1, pydantic 2.13.5 (this PC). `src/utils/strict_schema.py` re-checks the exact
schema the SDK sends against the rules above (no API call).

Tool / function calling with `strict: true` uses the same constrained decoding and the same schema subset, so it is
not a fix on its own; it only changes where the schema sits in the request.

## 3. Candidates

All four keep the content keys downstream code reads today (plan_checks, generator, tile / card nodes, written-line
flags); typed content → `content_data_of` → the same dict.

| | design | what the model writes per component |
|---|---|---|
| **string** (today) | `content_data_json: str` | the content as escaped JSON text |
| **union** (B) | `components: list[TitleComponent \| KpiRowComponent \| … ]` (anyOf, 15 objects); each: `component_id`, `kind` const, kind fields (chart: `chart_type`, `series_count`; table: `columns`, `rows`; list kinds: `items`, `orientation`), `count`, typed `content`, `content_summary`, `design_hint`, `weight` | only its kind's fields; content keys of its kind, nulls for absent optional keys |
| **slots** (A) | today's flat `PlannerComponent` + one nullable field per kind (`title`, `kpi_row`, …, `layer`) | all common fields + 14 nulls + its kind's content |
| **superset** (C) | today's flat component + one `content` object with every kind's keys, all nullable | every key of every kind, mostly null |
| two-step (D) | plan kinds first, then one call per component for its content | not built: 2–4× the calls and latency, and the slide-level fidelity rules (each number once across components) span components |

Per-kind content (`src/agents/schemas/planner_schema_typed.py`): title `{title, subtitle?}`; narrative / caption `{text}`;
kpi_row `{kpi_labels, kpi_values, kpi_deltas?, kpi_directions? ("" up down neutral), kpi_tones? (good bad watch ""),
kpi_icons?}`; chart `{chart_title?, chart_labels, chart_values?, chart_series? [{name, values}]}` (values: number or
the brief's own text such as `"₹8.2"`, which the chart node already parses; the type is the component's
`chart_type`, copied into content_data as today); table `{table_columns, table_rows: [[str]]}`; bullet_list
`{bullets}`; timeline `{direction, timeline_items [{date, label, description?}]}`; flow / process_arrow
`{direction, flow_steps | process_steps}`; pyramid `{direction up|down, pyramid_levels}`; tree `{layout,
tree_nodes [{label, children?}]}` (recursive `$ref`); matrix `{x_axis, y_axis, quadrants?, matrix_items [{label, x,
y: low|mid|high}]}`; card_grid `{card_layout grid|steps|matrix, cards [{title, tag?, body?, bullets?, tone?,
key_phrase?, icon?}], focus_card?, columns?, rows?}`; layer `{description?, layers? [{title, items}], center?,
nodes? [{label, detail?}], connections? [{source, target, label?}]}`. Icons stay strings: the icon list
(1953 names) is over the 1000-enum limit.

## 4. Free tests (`python -m scripts.tools.planner_schema_compare`, `docs/eval/planner-schema/summary.md`)

Corpus: 1476 distinct saved plan components (output/**/slides.json, runs.json, plans.json, deduplicated).

| candidate | strict problems | schema chars | schema tokens | properties | depth | enum values | output tokens, 1439 round-tripped components |
|---|---|---|---|---|---|---|---|
| string | 0 | 6,285 | 1,657 | 16 | 2 | 34 | 269,150 (baseline) |
| **union** | 0 | 18,428 | 5,307 | 192 | 4 | 114 | **234,292 (−13%)** |
| slots | 0 | 10,773 | 3,174 | 99 | 4 | 64 | 392,406 (+46%) |
| superset | 0 | 8,076 | 2,494 | 81 | 4 | 60 | 573,113 (+113%) |

(Tokens: tiktoken o200k_base. Output = the component as the model would write it under strict mode, every key
present, nulls included; the string form counts the escaping: each inner `"` becomes `\"`.) The union schema is
written without per-field titles and defaults (`_trim`; every key is required in strict mode, so a default only
costs prompt tokens): 30k → 18k characters.

Round trip (saved content_data → typed content → content_data, equal after dropping keys code writes: `per_row`, a
card's `body_source`, the planning path's `kicker`): **1439 of 1476 (97.5%)**; without the 8 empty components (failed
plans, nothing to type) and `layer`: **1438 of 1444 (99.6%)**. The 6 that do not fit: 3 matrices in an older
rows × columns shape (23 Sep; the prompt now routes those to card_grid matrix), 1 chart with an off-schema
`chart_series_formatted`, 1 card whose body is a list, 1 integration-test fixture without kpi_values. `layer`: 1 of
24 fit; today it has no documented shape and the model invented a new one each time (`layers`,
`layers_top_to_bottom`, `nodes` as strings / dicts with id / role / type, `links`, `diagram_nodes`, `center_node`,
`center_label`, `platform_logos`, …). The typed layer gives it two shapes (stacked layers, or nodes + links around a
centre). Layer is drawn by the LLM from the content (`NO_REF_KINDS`), so a new shape changes nothing downstream.

Unit tests: `tests/unit/test_planner_schema_typed.py` (29 tests: strict rules on both schemas, the checker catches
`oneOf` / missing `additionalProperties` / `required`, every kind's sample content gives today's dict, mismatched
kind / content and bad enum values are rejected, the typed and string replies give the same SlidePlan, the switch
picks the model and names the field in both prompts). `pytest tests/unit -q`: before 1110 pass / 4 known failures;
after 1139 pass, the same 4 known failures.

## 5. Trade-offs

- **union** — kind and content cannot disagree (the grammar ties a `kind` const to its content); no irrelevant
  zero fields (`chart_type: ""`, `columns: 0`, … on every component today); fewest output tokens. Costs: the biggest
  schema (+3.6k input tokens a call; at gpt-5-mini $0.25/M ≈ $0.0009 uncached, a tenth of that cached; 125 calls ≈
  $0.11 at most), 15 near-identical branches in the grammar (well inside the limits).
- **slots** — smallest code change (one flat component), but 14 nulls a component (+46% output) and nothing stops
  the model filling the slot of another kind (the adapter would have to guess).
- **superset** — smallest schema, but every component writes every key (+113% output tokens; reasoning models are
  billed for output, and a longer answer is more room to mix kinds' data).
- **string + fixed examples** (not a candidate, a fallback) — show the examples as escaped strings and keep the
  schema. Cheapest, but keeps a parse step and keeps asking a reasoning model to plan text it must escape; the
  give-up placeholders show the model fights the form itself, not only the examples.
- **Reasoning budget** — none of the schemas is known to stop the 3 runaway first tries; levers for those are
  separate (reasoning effort, `max_tokens`, a shorter prompt) and should be tested on their own.

## 6. Chosen design and how it is wired

- `src/agents/schemas/planner_schema_typed.py`: content models, `COMPONENT_BY_KIND` (built with `create_model` so
  `component_id`, `kind` come first), `PlannerSlideTyped`, `content_data_of` / `content_from_data`.
- `src/agents/planning/slide_component_planner.py`: `planner_schema()` reads `PLANNER_SCHEMA` per call (`string` default,
  `typed`); `plan_single_slide` picks the model and renders both prompts with `content_field` ("content" or
  "content_data_json"); `_planner_slide_to_state` takes either reply (typed: `content_data_of`, no parse step), then
  the same `clean_data`, `_settle_chart_type`, capacity, written-line and plan checks. The repairer, visual repairer
  and slide replanner call `plan_single_slide`, so they follow the switch.
- Prompts: `system.j2` / `user.j2` name the field through `{{ content_field }}`; the worked examples were already
  objects, so under `typed` the examples and the schema finally agree. The per-kind schema text in the prompt is
  unchanged (the grammar drops what the typed content does not have, e.g. `chart_type` inside a chart's content).
- `src/utils/strict_schema.py`: offline strict-mode check of the sent schema.
- `scripts/tools/planner_schema_compare.py`: the comparison above, and `--logs` to score run.logs.
- `scripts/experiments/cards/card_plan_only.py --schema typed|string`: sets `PLANNER_SCHEMA`, recorded per run and in summary.md.

## 7. Risks

- The model now *must* produce content for every component (no `{}` escape); an empty list is still possible and
  plan_checks' "has no content" re-ask still catches it.
- Stricter enums (tones, directions, matrix levels, card layout) reject values the string path let through; the
  grammar makes them impossible rather than failing, so the model picks the nearest allowed value.
- The schema is resent on every call; if OpenAI does not cache it with the prompt prefix, input cost rises by
  about a quarter (still ≈ $0.1 per 18-run check). First request per schema: extra latency once.
- Reasoning models may still run out of output tokens; a typed schema does not promise fewer length-limit hits.
- `PlannerSlideTyped.model_json_schema` is overridden to drop titles / defaults; a test pins that the openai SDK
  still sends the trimmed schema (an SDK upgrade that stops calling `model_json_schema` would only make the schema
  larger, not invalid).

## 8. Proposed paid check (not run; ask first)

One planning-only run of the same 6 decks × 3 as `choice-plans`, on the test PC at this branch's commit:

```
python -m scripts.experiments.cards.card_plan_only --repeat 3 --label typed-schema --schema typed --bundle --workers 5
```

Cost: choice-plans was $1.48; the typed schema adds ≤ $0.11 of input and should save some output, so **≈ $1.5,
ceiling $2**. Then, free on this PC:

```
python -m scripts.tools.planner_schema_compare --logs output/card-plans/choice-plans/run.log output/card-plans/typed-schema/run.log
python -m scripts.experiments.cards.card_plan_only --label typed-schema --rescore
python -m scripts.eval.structure_loss --replay
```

Compare against choice-plans: unreadable fields (24 → expected 0), "has no content" re-asks (7), all re-asks
(10), length-limit hits (3), fallbacks (1), output tokens p50 / p90, and plan quality from summary.md and the
structure-loss replay (card grids, lists, tones, focus cards, written card lines). Pass: 0 unreadable, ≤ 1
no-content re-ask, 0 fallbacks, length-limit hits ≤ 3, p90 output tokens not more than +10%, no loss in the plan
summary. Then `typed` becomes the default (and the string path can go).

Unit tests (`pytest tests/unit -q`): before 1110 pass, after 1139 pass (+29, all in the new test file), the same 4 known failures.

## Sources

- OpenAI, Structured Outputs guide, "Supported schemas": https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI community, GPT-5.5: keys out of schema order (Chat Completions), unescaped double quotes breaking out of
  string values (Responses API):
  https://community.openai.com/t/api-chat-completions-issue-json-schema-in-wrong-order-gpt-5-5/1381253
- OpenAI community, GPT-5 models (gpt-5-mini included) returning the JSON object twice with `.parse` ("trailing
  characters"), not seen on gpt-4o:
  https://community.openai.com/t/harmony-based-gpt-5-models-return-malformed-structured-outputs-sdk-1-100-2/1353934
- Local code read: langchain_openai `with_structured_output` / `_convert_to_openai_response_format`, openai
  `lib/_pydantic.py` `to_strict_json_schema` (installed versions above).

## Paid check result (test PC, 2026-10-15, $1.16, `output/card-plans/typed-schema/`)

`card_plan_only --repeat 3 --schema typed --workers 5` at `adebe9d`, against `output/card-plans/choice-plans`
(the same 18 runs on the string schema, $1.48). `python -m scripts.tools.planner_schema_compare --logs …`:

| | string (choice-plans) | typed |
|---|---|---|
| planner calls answered | 119 | 113 |
| unreadable content fields | 24 | **0** |
| length-limit hits (24000 output tokens) | 3 | **0** |
| re-asks | 10 | **2** |
| fallback plans | 1 | **0** |
| output tokens p50 / p90 / max | 3438 / 5670 / 19526 | 3254 / 5095 / 6405 |
| input tokens p50 | 12933 | 14785 |
| cost | $1.48 | **$1.16** |

Every gate passes (0 unreadable, ≤ 1 empty re-ask, 0 fallbacks, ≤ 3 length hits, p90 output −10%). The two
re-asks are content checks, not parse failures (agency slide 2 "Recommendation:" narrative read as an
instruction; XTSY slide 7 title-only impact cards).

Plan quality, same scorer as the structure-loss README:
- bullet lists 18 → 14; card grids 53 = 53; tables 20 → 24; agency Winners / Weak terms 2 cards in 3 of 3; XTSY
  slide 2 has no "Show:" list in 3 of 3 (string: 1 of 3).
- key messages under 60% carried: 17 of 449 (string) vs 18 of 467 (typed), the same; the outline's "Note:" lines all carried (captions
  16 → 7: the notes moved into narratives and cards).
- numbers in the key messages missing from the plan: real losses 0 (string) vs 4 (typed): product-launch r3
  slide 4 kept only the "after" values in its KPI tiles (15 min/wk, 1/quarter, 38ms, 71) and dropped the
  "before" values (2.3 hrs/wk, 12/quarter, 142ms, 22); r1 / r2 of that slide kept them. One run; watch it.
- XTSY r1 slide 3: the 7 opportunity areas copied into all 4 lever cards of a matrix (28 bullets). The brief
  does not say which area belongs to which lever; the string runs kept them as one list beside the cards. Comes
  from the planner prompt's "put each under the card it belongs to" (structure-loss change 2), not the schema.
