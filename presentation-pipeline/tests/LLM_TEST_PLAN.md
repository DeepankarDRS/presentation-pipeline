# LLM Test Plan — Planner & Generator Output

> Focus: exercise the **LLM path** end to end and eyeball what actually comes out.
> Created 2026-09-06. Companion to [`../CODE_FLOW.md`](../CODE_FLOW.md) and [`../CODE_REVIEW.md`](../CODE_REVIEW.md).

---

## 0. Why this plan exists

Every current case in `tests/cases/` carries a `components:` list. That means
`route_after_start` ([`src/graph.py:55`](../src/graph.py)) **skips the planner** and
the plan is built mechanically by `context_builder._build_default_plan`. So today:

- The **planner LLM is almost untested** (only one mocked integration test hits it).
- **Multi-slide decks are impossible without the planner** —
  `_build_default_plan` only ever returns *one* slide. A case with `components:`
  can never become a deck, no matter the `deck_min_threshold`.

This plan adds two families of cases that force the LLM to do real work:

| Family | `components:` in YAML? | Path exercised |
|---|---|---|
| **A. Base-prompt (single slide)** | ❌ omitted | planner decomposes 1 request → 1 slide plan → generator |
| **B. Deck (explicit per-slide brief)** | ❌ omitted | planner decomposes "Slide 1… Slide 2…" → N slide plans → slide_router loop → deck_assembler |

---

## 1. How to run

Prereq: a funded `OPENAI_API_KEY` in `.env` (memory notes a past `credit_balance_exhausted` — verify first with a one-case run).

```bash
# Single base-prompt case, full LLM run
python -m src.runner base-strategy-statement

# All base-prompt cases
python -m src.runner base-strategy-statement base-quarterly-metrics base-revenue-trend base-competitor-comparison base-roadmap base-process-overview base-org-structure base-risks base-vague base-overstuffed

# A deck case — MUST lower the threshold so N slides trip deck mode
python -m src.runner deck-minimal-2slide --deck-min-threshold 2
python -m src.runner deck-qbr deck-board-update deck-product-launch --deck-min-threshold 3

# Everything, JSON out for diffing
python -m src.runner --json > ../output/llm-test-$(date +%Y%m%d).json

# Turn the critic off to isolate planner+generator+compiler
python -m src.runner base-revenue-trend --critic-mode off
```

Artifacts per run land in `output/runs/<run_id>/`:
`input.xml` (final compiled XML), `compile-result.json`, `run-manifest.json`,
and `retry-N/` subdirs for each repair attempt.

---

## 2. What to inspect — beyond PASS/FAIL

The runner table only shows compile result + retries + cost. For LLM-quality
testing, open `output/runs/<run_id>/input.xml` and check:

| # | Check | Where it can go wrong |
|---|---|---|
| 1 | **Component match** — did the planner pick the components a human would? | planner LLM |
| 2 | **`core_hook` is a real sentence with tension**, not a topic label | planner LLM |
| 3 | **Invented data is plausible and internally consistent** (chart totals vs table totals, deltas match values) | planner `content_data_json` + generator |
| 4 | **Every color is a `$token`** — no raw hex except `chartColors` | generator; `context_builder` note |
| 5 | **`<Theme>` element emitted verbatim** and matches the requested palette | style_resolver → generator |
| 6 | **Root `VStack` is `w="1280" h="720"`**, content fits (no `audit_layout` `ROOT_SIZE`/overflow) | generator; layout_audit |
| 7 | **Font sizes ≥ 11**, KPI values large, labels muted | generator; `FONT_TOO_SMALL` audit |
| 8 | **No HTML** (`<div>`, `<br>`, `<p>`, `style=`) — should be caught pre-compile | normalizer / pre_validate |
| 9 | **Dark theme → `<Chart>` wrapped** in `$chartSurface` container | `context_builder:288` note |
| 10 | **Tables: every `<Td>` has `backgroundColor` + `color`** | `context_builder:295` note |
| 11 | **retries used** — 0 is ideal; if >0 read `retry-N/` to see what failed and whether the tier escalated | repairer |
| 12 | **Deck: `len(completed_slides) == len(slide_plans)`** — `deck_assembler` drops slides silently on regex miss | `deck_nodes:87-93` |
| 13 | **Deck: adjacent slides look different** — layout variety | planner `_enforce_layout_variety` (note: partly ineffective, CODE_REVIEW #7) |
| 14 | **Speaker notes** — if the prompt asks for them, they will NOT be in the .pptx (CODE_REVIEW #5) | known gap |

---

## 3. Family A — base-prompt single-slide cases

One plain-English request. No `components`, no `supplied_content`. The planner must
choose the component vocabulary and invent all data.

| Case | Request gist | Component(s) a human would pick | Layout expectation | Watch for |
|---|---|---|---|---|
| `base-strategy-statement` | One bold strategic claim about 2026 priorities | `title`, `narrative` | `hero_statement`, sparse | planner over-building (adds chart/kpi that weren't asked for) |
| `base-quarterly-metrics` | "Our Q3 headline numbers" | `title`, `kpi_row` | `hero_big_number` / 3-4 tiles | tile count sane (3-5); delta direction colours |
| `base-revenue-trend` | "How revenue trended over 2 years" | `title`, `chart` (line/bar), maybe `caption` | `full_width_chart` | 8 quarters of plausible monotonic-ish data; axis labels |
| `base-competitor-comparison` | "Us vs top 3 competitors on price/features/support" | `title`, `table` **or** `matrix` | `two_column` / full table | which does planner pick? table is safer |
| `base-roadmap` | "Product roadmap, next 4 quarters" | `title`, `timeline` | timeline-roadmap layout | timeline vs bullet_list fallback |
| `base-process-overview` | "Explain customer onboarding" | `title`, `flow` **or** `process_arrow` | stacked / horizontal steps | 4-6 steps, not 12 |
| `base-org-structure` | "Structure of the engineering org" | `title`, `tree` | tree layout | tree vs bullet fallback; depth ≤ 3 |
| `base-risks` | "Top risks + mitigations" | `title`, `table` **or** `bullet_list` | two-column or stacked | pairing risk↔mitigation |
| `base-vague` *(adversarial)* | "Make me a good slide about the business" | anything coherent | any | does it invent something sensible or produce mush? fallback path (`title/narrative/bullet_list`) |
| `base-overstuffed` *(adversarial)* | One run-on sentence demanding KPIs + 2 charts + a table + a timeline + 5 bullets on one slide | all of them, `density: tight_fit` | `dashboard_grid` | **overflow → repairer → SIMPLIFY tier**; this is the layout stress case for the planner path |

**Pass bar for Family A:** compiles on ≤1 retry, component choice defensible,
data plausible, fits 1280×720, all-tokens colour.

---

## 4. Family B — deck cases with explicit per-slide briefs

The request enumerates slides ("Slide 1: … Slide 2: …"). The planner must emit one
`PlannerSlide` per enumerated slide. Run with `--deck-min-threshold` ≤ slide count.

| Case | Slides | Per-slide brief | Exercises |
|---|---|---|---|
| `deck-minimal-2slide` | 2 | 1: cover statement. 2: three supporting bullets. | the `len(slide_plans) > 1` boundary; smallest `slide_router` loop |
| `deck-qbr` | 5 | 1 cover · 2 KPI dashboard · 3 revenue chart + commentary · 4 segment table · 5 closing / next steps | mixed slide_types, per-slide contract rebuild, theme consistency across slides |
| `deck-product-launch` | 4 | 1 hero cover · 2 problem (bullets) · 3 solution (flow) · 4 timeline to GA | flow + timeline in one deck; section coherence |
| `deck-board-update` | 6 | 1 cover · 2 section_break "Financials" · 3 P&L table · 4 section_break "Product" · 5 roadmap timeline · 6 asks/closing | `section_break` slide_type handling; 6-slide cost; variety enforcement across 6 |
| `deck-sales-enablement` | 5 | 1 cover · 2 buyer personas (matrix/table) · 3 competitive matrix · 4 pricing table · 5 objection-handling bullets | table-heavy deck; `chart_table_split` vs `two_column` |
| `deck-strategy-3slide` | 3 | 1 where we are (KPIs) · 2 where we're going (chart) · 3 how we get there (process_arrow) | tight narrative arc; `core_hook` must tie all three |

**Pass bar for Family B:**
- `slide_plans` length == enumerated slide count
- `completed_slides` length == `slide_plans` length (no silent drops — CODE_REVIEW #13)
- final `deck_assembler` compile OK
- one shared `<Theme>` in the combined XML
- each slide's `slide_type` matches the brief (cover / data / content / section_break / closing)

---

## 5. Adversarial / edge cases (add as time permits)

| Case | Prompt shape | What it probes |
|---|---|---|
| `edge-contradictory` | "A minimal, uncluttered slide packed with every metric we track" | planner resolving sparse vs tight_fit conflict |
| `edge-no-topic` | "Slide." | degenerate input; fallback plan |
| `edge-huge-table` | "A table of all 40 sales reps and their quota attainment" | density, font floor, `audit_layout` FONT_TOO_SMALL, repairer SIMPLIFY |
| `edge-non-english-data` | request in English, data labels in German/Japanese | unicode through normalizer + compiler (`errors="replace"` path) |
| `edge-deck-1slide` | "A one-slide deck: just the title." | deck request that resolves to single mode; `mode` vs routing mismatch (CODE_REVIEW #8) |
| `edge-deck-15slide` | 15 enumerated slides | cost ceiling, per-slide retry accumulation in `generation_history`, timeout |
| `edge-notes-requested` | "…and put detailed speaker notes on each slide" | confirms CODE_REVIEW #5 — notes are extracted then dropped |

---

## 6. Known-broken paths to watch during these runs

From [`../CODE_REVIEW.md`](../CODE_REVIEW.md) — expect these to misbehave; the test
runs are a good chance to confirm/measure:

1. **Deck `passed` ignores the critic** (#1) — a deck with a bad slide can still
   report `passed=True`. Cross-check each slide's XML manually.
2. **No retry after `deck_assembler`** (#2) — if the combined compile fails, the
   run just fails. Note which deck cases trigger it.
3. **Stall detection underfires** (#3) + **tier doesn't escalate by attempt** (#4)
   — on `base-overstuffed` / `edge-huge-table`, watch whether retries stay at
   tier 1 (PATCH) forever instead of reaching SIMPLIFY/TEMPLATE.
4. **`layout_pattern` from the planner is discarded** (#7) — `deck-board-update`
   variety will come only from the freeform `layout_hint`.
5. **`data_provenance` empty on non-planner path** — N/A here (all these cases use
   the planner) but the manifest's user/sample counts should now be non-zero;
   confirm.

---

## 7. Scorecard template

Track per case in `output/llm-test-<date>.md`:

```
| case | compiled | retries | max_tier | components (planned) | component match? | data plausible? | fits? | tokens | cost | notes |
|------|----------|---------|----------|----------------------|------------------|-----------------|-------|--------|------|-------|
```

Roll-up: pass-rate, mean retries, mean cost/slide, count of runs needing tier ≥ 2,
count of manual-review "component mismatch".
