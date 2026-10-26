# Tile and card variants chosen from the plan — spec draft (2026-10-26, nothing built)

## 1. Problem

`POM_BLOCKS=tiles` works on every entry point that reads `.env` (`src.api`, `src.runner`, `scripts.eval_run`):
checked on the test PC 2026-10-26, `element_refs.mode()` = `tiles`. Scripts that set it themselves:
`kpi_paid` (`--blocks`, default `kpi`), `tile_combined` / `tile_same_plan` (arm A `kpi`, arm B `tiles`).

But the variants never show. In the combined check's arm B (test PC, 2026-10-26) the LLM wrote:

| Tag | Written | With `variant=` |
|---|---|---|
| `<KpiGrid>` | 13 | 0 |
| `<CardGrid>` | 32 | 1 (`inverted` on a whole group, which code limits to the focus card) |
| `<Kpi>` / `<Card>` | 0 | — |

Why: the prompt gives each variant one line of words and no example tag; every example tag it shows is bare
(`<KpiGrid ref="cid"/>` ends the per-slide line); it says "write a `<Kpi>` only for an item that differs" and
"a bare tag is a finished slide part". So a bare tag draws the defaults (`plain` tiles, `lifted` cards).

## 2. Evidence: the plan already asks for looks

Census of the design hints on saved plans (build PC, `output/**/slides.json`, distinct components, keyword cues):

| Cue in `design_hint` | kpi_row (134; 13 no hint) | card_grid (131) | Drawn by a bare tag today? |
|---|---|---|---|
| colour / sentiment | 79 | 46 | yes: tones (`kpi_tones`, `tones_from_hint`, card `tone`) |
| emphasis ("emphasise X") | 78 | 47 | cards: the focus card dark; KPI: no |
| dark / inverted / focus / hero | 26 | 56 | cards: yes (focus card); **KPI: no** |
| accent border / bar / edge | 24 | 11 | **no** |
| lift / shadow | 17 | 49 | cards: yes (`lifted`); KPI: no (flat by decision) |
| icons | 14 | 102 | yes (plan `kpi_icons`, card `icon`) |
| status dots | 12 | — | **no** |
| tint / fill / shade | 7 | 4 | partly (tones) |
| numbered | — | 6 | **no** |

So the hint asks for a variant on many components (KPI: 24 bar, 12 dot, 26 dark; cards: 11 edge, 6 numbered)
that nothing draws, because only the LLM was meant to translate the hint, and it writes bare tags.

## 3. Options

| | How | For | Against |
|---|---|---|---|
| **A (proposed)** | Code reads the plan's `design_hint` and sets the variant on a bare tag, as `tones_from_hint` already does for colour | Same on every run and entry point; free to build and replay; follows "colour comes from the plan" and "anything asked must show" | Keyword reading of free text; needs a check of its picks |
| B | Planner field `kpi_variant` / `card_variant` | Structured | Planner prompt + schema change, a paid planner check; one more field the planner can drop |
| C | One example tag per variant in the prompt | Small change | Prompt wording was a weak lever before (paid-2: QBR bare 3 / 3); more input tokens; untested |

## 4. Design (option A)

**Where:** a `look_from_hint(comp)` helper next to `tones_from_hint` in `src/agents/plan_checks.py`, reusing its
clause split and item-name matching; read in `tiles.expand` and `cards.expand` where the group and item
variants are resolved. Runs only under `POM_BLOCKS=tiles`, inside the validator, so every entry point gets it.

**Order:** the LLM's own `variant` wins; else the hint's; else the default. Every pick is logged as info
`NODE_LOOK_FROM_HINT` (component, cue, variant) so a run shows what was applied.

**Mapping (draft):**

| Hint cue | KPI tiles | Cards |
|---|---|---|
| status dot(s) | group `dot` | — |
| accent border / bar / edge / stripe | group `bar` | group `accent_top` |
| dark / inverted / hero / focus on the plan's emphasis item | that item `inverted` (needs `is_emphasis_item`) | already drawn (focus card) |
| tint / fill / shade, with tones | group `filled` | group `toned` |
| numbered / numerals | — | group `numerals` (its own `requires`) |
| lift / shadow | none (KPI tiles stay flat, user 2026-10-13) — Q2 | already `lifted` |
| several cues | one group variant, priority: bar > dot > filled; the item `inverted` on top | accent_top > numerals > toned |

A variant whose `requires` fails falls back as today (`NODE_VARIANT_UNMET`).

## 5. Steps

0. **Measure (free).** Run `look_from_hint` over the 265 saved components; print each hint with its pick. You check
   about 20 picks; wrong-reading rate must be ≤ 1 in 20 before building on.
1. **Build (free).** Helper + the two expand hooks + unit tests (each mapping row, the LLM's variant winning,
   `requires` fallbacks). Also a startup log line in `src.api` with the `POM_BLOCKS` mode.
2. **Replay (free).** `tile_replay` / `card_replay` on the saved slides: bare tags vs bare tags + hint looks;
   renders, `GEOM_*`, compile count; blind sheet for your marks (gate ≥ 0.5).
3. **Paid:** none of its own; it rides on the next combined check (`--repeat 1` ≈ $1.3). Asked before running.

**Done when:** every mapped cue on the saved plans draws its variant (count), 0 new compile failures,
`GEOM_*` and number / title sizes not worse, blind marks ≥ 0.5.

## 6. Questions for the user

- **Q1** "emphasise X" on a KPI row (78 hints): also give that item `size="hero"`, or only `inverted` when the
  hint says dark / hero / focus?
- **Q2** "lift / shadow" on a KPI row (17 hints): keep KPI tiles flat (your 2026-10-13 decision) or allow the shadow?
- **Q3** Option A, B or C (proposed: A).
