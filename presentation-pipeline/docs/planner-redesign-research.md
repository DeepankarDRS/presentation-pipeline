# Planner redesign: research and plan

**Scope.** The outline planner and the slide component planner:
- what they receive (the user's request, deck settings, structured data, clarification answers);
- what they produce (outline, slide plans);
- the contract they hand to the generator.

**How to use this document**
- It is a standalone working document. It starts from the code as it is on branch `test-1-planning`, the saved runs in `llm_test/` and `output/plans/`, and the test cases in `tests/cases/`.
- It inherits no decisions from other planning docs. Where an earlier choice exists, it appears as a question to confirm (§10).
- Update it as research happens: add findings to the log (§11), move questions to decided with a date, and keep evidence dated.

**Rules for this work**
- Verify without paid LLM calls first: replays of saved runs, unit tests, prompt rendering.
- Ask before any paid run, with the case list and a cost estimate.
- Keep changes small and measurable.

---

## Contents

1. [How planning works today](#1-how-planning-works-today)
2. [What users actually send](#2-what-users-actually-send)
3. [Evidence](#3-evidence)
4. [Problems to solve](#4-problems-to-solve)
5. [Research questions and options](#5-research-questions-and-options)
6. [A candidate design (to be validated)](#6-a-candidate-design-to-be-validated)
7. [Contracts: state and generator](#7-contracts-state-and-generator)
8. [How we measure](#8-how-we-measure)
9. [Plan of work](#9-plan-of-work)
10. [Open decisions](#10-open-decisions)
11. [Research log](#11-research-log)
12. [References](#12-references)

---

## 1. How planning works today

```
request + deck settings + supplied_content (JSON, optional)
   │
   ▼
elicitor (LLM) ── not enough content? → questions to the user
   ▼
outline_planner (LLM, 1 call)        → per slide: slide_title, section, narrative_role,
   │                                   key_messages (prose), visual_emphasis
   ▼  Send() × N
slide_component_planner (LLM, 1/slide) → per slide: slide_type, components (kind, content_data,
   │                                     weight, design_hint), layout_hint
   ▼  fan-in: assembled_slide_plans (operator.add) → slide_plan_sorter
plan_reviewer (LLM) → score + issues (routing ignores them)
   ▼
style_resolver → context_builder → generator (LLM writes POM XML) → validator → …
```

### 1.1 Outline planner

Files: [outline_planner.py](../src/agents/outline_planner.py), [outline_planner_schema.py](../src/agents/outline_planner_schema.py), [prompts/outline_planner/](../src/prompts/outline_planner/).

| Aspect | Today |
|---|---|
| Input | The raw request text, deck settings, clarification answers, `supplied_content` JSON, target slide count |
| Output per slide | `slide_title` (≤ 8 words), `section`, `narrative_role`, `key_messages` (list of prose strings), `visual_emphasis` |
| Output per deck | `deck_title`, `core_hook` |
| Role of `key_messages` | "The ABSOLUTE source of truth": every number, series and table row is retyped into sentences |
| Missing data | Schema and prompt: "invent a plausible concrete number" |
| Message count | Tied to "amount of text" (minimal → 1 message per slide … extensive → 4–6) |
| Model | gpt-4.1, temperature 0.3, max 12,000 output tokens |

### 1.2 Slide component planner

Files: [slide_component_planner.py](../src/agents/slide_component_planner.py), [planner_schema.py](../src/agents/planner_schema.py), [prompts/slide_component_planner/](../src/prompts/slide_component_planner/).

| Aspect | Today |
|---|---|
| Input | One outline slide, the deck's `core_hook`, the other slides' titles, settings. Also `supplied_content` keys whose name fragments appear in the messages (`_filter_supplied_content_for_slide`). **It never sees the request itself** |
| How it picks components | A routing table: "read the SHAPE of each key_message" → kpi_row / chart / table / bullet_list / timeline / … (14 kinds) |
| Output | `slide_type`; components with `component_id`, `kind`, counts, `content_data_json` (a JSON string), `weight`, **mandatory** `design_hint`; `layout_hint` |
| Prompt size | System prompt 6,780 tokens (641 of them the design-hint capability list), plus the user part |
| Model | gpt-4.1, temperature 0.3, max 4,000 output tokens |
| Re-planning | `plan_single_slide(repair_context=…)` exists and is used by the repairer's regenerate tier |

### 1.3 Around them

- **Fan-in.** `assembled_slide_plans` uses `operator.add`, so a slide planned twice appears twice. The installed LangGraph is 0.6.11, which has no `Overwrite` to reset the list.
- **Concurrency.** `SLIDE_PLANNER_MAX_PARALLEL` and `MAX_CONCURRENCY` are declared but never applied.
- **Plan reviewer.** One LLM call per deck; `route_after_plan_review` always continues.
- **API.**
  - `/plan/outline` runs the elicitor, then the outline planner.
  - `PUT /plan/{id}/outline` stores an edited outline; the graph then skips the outline planner.
  - `/plan/outline/regenerate-slide` calls `outline_replanner`, whose prompt also says to invent a number.
  - `/plan/refine` sets `prior_plan` and `refine_feedback`, but **nothing reads either**, so the user's feedback is ignored.

### 1.4 Deck settings

Sources: [deck-settings-form.component.ts](../frontend/src/app/components/deck-settings-form/deck-settings-form.component.ts), [`/deck-settings-schema`](../src/api.py:525), [settings_mapper.py](../src/agents/settings_mapper.py).

| Field | What it does today |
|---|---|
| Content handling (`text_mode`) | "Generate" is described as "LLM invents the content from your prompt" and maps to `llm_generates_freely` |
| Amount of text | Sets how many `key_messages` each slide gets |
| Slide count | Buckets. The default "6–10" becomes 8 ([prompt-form.component.ts:141](../frontend/src/app/components/prompt-form/prompt-form.component.ts:141)), and the outline is told "EXACTLY 8", even when the brief states a count |
| Write for, Tone | Passed into the outline and slide prompts |
| Additional instructions | Passed into the outline prompt and the elicitor as free text |

### 1.5 What the generator takes from the plan

Sources: [generator.py](../src/agents/generator.py), [generator/user.j2](../src/prompts/generator/user.j2).

- **From the plan:**
  - `slide_title` (shown as "SLIDE OBJECTIVE"), `slide_type`, `layout_hint`;
  - per component: kind, id, count, chart type, `content_summary`, weight, `design_hint`, `content_data`.
- **Also:** the whole `supplied_content` on every slide ("use these values EXACTLY").
- **When data is missing,** it is told to "invent realistic, specific figures" ([user.j2:55](../src/prompts/generator/user.j2:55), [:60](../src/prompts/generator/user.j2:60)) and to "add substance" when content is thin ([:73](../src/prompts/generator/user.j2:73)).
- **Its system prompt** ([system.j2](../src/prompts/generator/system.j2)):
  - derives a kicker from the section or topic (:102);
  - adds a "Source:" line (:109);
  - forces a blueprint "do NOT rearrange" (:183) and a layout archetype (:218).

Planner changes only pay off if the generator draws what the plan says, so this contract is part of the work (§7.2).

---

## 2. What users actually send

All 53 cases in `tests/cases/` were run through a code indexer (`src/planning/brief_index.py`) on 2026-09-27.

| Kind of input | Cases | Examples | What planning must do |
|---|---|---|---|
| Topic only, no data | 13 | "Show our revenue trend", `base-vague` | Decide the story; there is no data to place. What happens when the topic implies data (a trend, metrics) is a policy question (§10) |
| Short prompt + structured JSON | 27 | `kpi-row`, `deck-qbr-data` | The JSON already has component shape (`kpi_labels`, `chart_values`, `table_rows`). Map it to slides without guessing |
| Short prompt with a few numbers | 8 | `deck-qbr`, `eval-*` | Place every number; the story is light |
| Long material, no slide structure | 3 | `gate-deck-cheffin-audit` (71 blocks, 25 numbers), `gate-deck-agency-takeover` (96 / 39), `gate-deck-xtsy-qcomm` (92 blocks, 2 numbers) | Choose the slides and the story; assign content to them |
| Per-slide spec | 2 | `gj-h1-regen` (346 blocks, 408 numbers, 14 tables), `gate-deck-cheffin-full` | Follow the spec: section N = slide N, keep the brief's headlines and every number |
| Not yet supported | — | CSV / XLSX data files | Real audit decks draw most of their content from these |

**Formats users paste**, tested against today's indexer:

| Input | Result |
|---|---|
| Markdown table | parsed, but the `\|---\|` line becomes a data row and empty edge columns appear |
| Excel paste (tab-separated) | not recognised as a table |
| Bullets (•), Indian number formats (₹1,00,50,000) | fine |
| Pasted JSON | one unstructured block |
| "Slide 2:" in the middle of a line | not detected, so its content lands under the wrong slide |
| `supplied_content` JSON | not indexed at all |

In every test, nothing was lost: all text stays verbatim.

---

## 3. Evidence

All of it from saved runs; no new cost.

### 3.1 The old planners on the gj-h1 brief

Four saved runs: `llm_test/gj-h1-regen-{69af33,7293ef,5a9e2d,bf396b}.zip`. The planning code is unchanged since then (`git log 77000c3..HEAD` on the planning files is empty).

| Measure | Result | How measured |
|---|---|---|
| The brief's headline kept on content slides | 0/13 in every run: replaced by section labels ("Platform Deep-Dive · Swiggy") | `scripts/eval_lineage.py` |
| Brief numbers dropped during planning | 7–13% (27–48 of 365) | `eval_lineage.py` |
| Brief numbers dropped by the generator | 0–3% in the three recent runs | `eval_lineage.py` |
| Slides flagged by simple code checks (dropped or invented numbers, over capacity, mixed chart units) | 9, 8, 10, 9 of 14 | replay script, 2026-09-27 |
| Recurring failures | drops on the dense slides 1, 3, 4, 5, 6 and 10 (slide 10 loses 13–20 numbers); timeline labels over 4 words (slides 8, 12, every run); 7 KPI tiles on slide 5 (3 of 4 runs); invented numbers (2 runs) | replay |
| Design hints on more than 2 components of a slide | 6–9 slides per run; highlighting requested on 14/14 slides | `eval_lineage.py` |
| Same component kinds in all 4 runs | 1 of 14 slides | `eval_lineage.py --detail` |

- **Where each number is lost cannot be told apart:** old runs don't save the outline, so a replay can't separate outline losses from slide-planner losses. Any new runner must save the outline.
- **What the evidence points to:** the generator is faithful with what it is given; the losses happen while planning.

### 3.2 The old planners on the CHEFFIN brief

From `llm_test/tables-check-20260924-204854.zip`: 6 slides, $0.36 for the whole deck.

- **Richness:** 2.83 components per slide. The richness came from:
  - pairing a structure with its detail (process arrow + bullets + table);
  - an evidence chart (actual vs allowable CPC);
  - a KPI strip beside a table;
  - an invented "City / Keyword 1–3" table.
- **Invented or wrong content:**
  - source dates ("Q2 FY24") that are not in the brief;
  - a CPC chart plotted at 13.5 / 17.2, while the brief says ₹31.1 / ₹46.2;
  - CVR (%) and AOV (₹) on one axis;
  - the default blue palette, although the brief asked for orange and purple accents;
  - a highlight on every title.

### 3.3 An earlier experiment on this branch: `src/planning/`

A separate planning path was built and paid-tested on 2026-09-27 (`output/plans/test-1-final/`, $1.64 for 6 runs). Its steps:
1. code indexes the brief into numbered blocks;
2. one LLM call writes a storyline that refers to block ids;
3. a code check, with one re-ask;
4. one LLM "slide designer" call per slide;
5. code fills parsed tables and charts, checks, and re-asks up to 2 times.

It is evidence for mechanisms, not a design to adopt as-is.

| Measure (gj-h1 × 3, CHEFFIN × 3) | Result |
|---|---|
| Headlines kept (gj-h1) | 13/13 in all 3 runs |
| Numbers dropped (gj-h1) | 0.0%, 0.6%, 2.5% (mean 1.0%) |
| Invented numbers | 0 in all runs |
| Hints per slide | ≤ 2 |
| Same components across 3 runs | 8/14 (gj-h1), 2/6 (CHEFFIN) |
| Components per slide on CHEFFIN | **1.80**: a snapshot that is one table, a diagnosis that is bullets only, a methodology slide of five lists |
| Re-asks | the storyline check re-asked once in 6/6 runs, leaving 0 issues; 4–5 of 14 gj-h1 slides and 1–3 of 6 CHEFFIN slides needed a slide re-ask |
| Cost per gj-h1 plan | $0.32–0.35 (21–22 calls) vs $0.44 for the old planners |
| Headline style vs a real production CHEFFIN deck | tension in 5/15 headlines vs 12/15; our sub-headlines describe the slide ("Platform-wise performance snapshot"), production ones carry evidence ("₹29.4L spend, 0.34x ROAS…"); no kicker labels |
| Block-id references | 0 bad ids in 3,194; 7 false "set aside, included on slide 2" claims in one run |

### 3.4 What the real production CHEFFIN deck does

Built by hand for the client (kept locally only).

- **Size and sources:**
  - 17 slides;
  - about 60% of the content comes from data files (search terms, cities, keywords);
  - it uses derived numbers (ACOS, shares, "2.9×") and targets ("≥ 0.9x in 90 days").
- **Header on every slide:**
  - a kicker label;
  - a claim headline with a tension;
  - a sub-headline that carries the numbers.
- **Components:**
  - KPI strips with notes;
  - an evidence card beside a dark read-out panel;
  - status chips;
  - a gap panel (actual vs allowable);
  - numbered pillars;
  - a 30-60-90 roadmap.
- **Structure:** two platform deep-dives that share one layout.
- **Mistakes:** it contradicts itself in places (the same CPC with different values on two slides).

### 3.5 Cost today

Run `gj-h1-regen-bf396b`, 14 slides:

| Step | Calls | Cost |
|---|---|---|
| Elicitor | 1 | $0.015 |
| Outline | 1 | $0.057 |
| Slide planner | 14 | $0.349 |
| Plan reviewer | 1 | $0.017 |
| **Planning subtotal** | **17** | **$0.44** |
| Generator | 14 | $0.549 |
| Repairer | 1 | $0.027 |
| **Whole deck** | **32** | **$1.01** |

We don't record cached tokens, so these are list prices.

---

## 4. Problems to solve

| # | Problem | Seen in |
|---|---|---|
| P1 | **Content travels between LLMs as prose.** Numbers are retyped three times (outline → slide plan → XML) and nothing checks the copies | §3.1 drops; §3.2 wrong CPC values |
| P2 | **The slide planner never sees the source.** It can only use what the outline wrote | the dense-slide drops in §3.1 |
| P3 | **Headline, label and sub-headline are one ≤ 8-word field,** so the brief's headlines are replaced by labels | 0/13 headlines |
| P4 | **Invention is allowed** in the outline, the outline replanner and the generator, and "Generate" is described as inventing | §3.2 fake table and dates |
| P5 | **Components are chosen by sentence shape, not by content volume or capacity** | 7 KPI tiles; timelines with sentence labels |
| P6 | **Decoration is mandatory** (a hint on every component) | 14/14 slides ask for highlighting |
| P7 | **Unstable plans:** the same brief gives different components on every run | 1/14 stable |
| P8 | **No feedback:** the reviewer's findings change nothing | §1.3 |
| P9 | **One prompt handles very different inputs** (topic, JSON, material, per-slide spec) | §2 |
| P10 | **Structured JSON is mapped by keyword fragments,** then sent whole to every slide's generator prompt | §1.2, §1.5 |
| P11 | **Settings conflict with the brief:** the slide count overrides the brief's count; "amount of text" limits data | §1.4 |
| P12 | **Edit paths are broken or thin:** `/plan/refine` ignores the feedback; re-planning a slide duplicates it | §1.3 |
| P13 | **Richness depends on invention on thin briefs:** removing invention alone made slides sparse (1.80 components) | §3.2, §3.3 |
| P14 | **Style asked for in the brief is ignored** (brand colours) | §3.2 |

---

## 5. Research questions and options

Each question lists today's behaviour, the options, what would settle it, and the cheapest way to find out.

### RQ1 — Do we need an outline step, and what should it do?

| Option | For | Against |
|---|---|---|
| A. Keep outline + per-slide planner (today) | per-slide attention; parallel; a reviewable outline for the UI | two LLM hops if content passes as prose |
| B. Keep both, but the outline only **assigns content and writes the argument** (no retyping) | fixes P1 and P3; keeps the UI's outline editing | outline schema change |
| C. Build the outline in code when the brief is a per-slide spec; use the LLM for the rest | per-slide specs become exact and cheap | two paths to maintain |
| D. No outline for single-slide requests | removes a pointless call | none |
| E. One LLM call plans the whole deck in detail | one hop | a 14–20 slide deck in one output hits token limits; attention spread thin; the old outline hit 4k tokens and was cut off |
| F. Merge the slide planner into the generator (plan + XML in one call) | one fewer hop | the plan can no longer be checked before XML is paid for; the generator prompt is already 8–13k tokens |

- **Settle it by** headlines kept, numbers dropped, components per slide and cost, on the per-slide spec (gj-h1) and material (CHEFFIN) briefs.
- **Cheapest test:** B vs A on outline-only runs (≈ $0.05 per outline call).

### RQ2 — How should content travel from the input to a slide?

| Option | Description |
|---|---|
| A. Prose `key_messages` (today) | the LLM retypes data into sentences |
| B. References | the outline lists block ids; code copies text, tables and charts into the slide plan; the LLM never retypes data |
| C. Hybrid | references for data; short "points this slide makes" in the LLM's words for the argument |
| D. Typed fact store | every number becomes a fact (entity, measure, period, value); plans refer to fact ids; enables derived numbers and consistency checks |

- **Settle it by** numbers dropped or invented per stage, and whether headlines and arguments stay sharp.
- **Evidence so far:** B worked in §3.3 (1% dropped, 0 invented). D is more work and is needed for derived numbers.
- **Cheapest test:** replay the outline prompt variants on saved briefs; count retyping errors.

### RQ3 — How should any input be normalised before planning?

| Option | Description |
|---|---|
| A. Raw text to the LLM (today) | none |
| B. Code parser → numbered blocks | extend `brief_index.py` |
| C. Code parser + a small LLM "labelling" pass | the LLM tags blocks by role and entity, pointing at ids and never retyping; code validates (≈ $0.01–0.03 per deck) |
| D. Document-parsing libraries for files | pandas for CSV / XLSX; a document parser for PDF / DOCX (e.g. Docling, Unstructured, to be evaluated) |

**Gaps in the current parser** (§2):
- markdown separator rows;
- tab-separated tables;
- inline "Slide N:" headings;
- `supplied_content` JSON not indexed;
- "label: value" groups under an entity heading are not turned into a table;
- style examples ("Use ROAS as 0.34x") counted as data;
- the brief's slide count ("6-SLIDE") not read.

**Production bar for the parser** (definition of done):
1. A typed, versioned schema.
2. Lossless: every character of the input lands in exactly one block (property test).
3. Structure only when the pattern is unambiguous; otherwise verbatim text plus a logged warning.
4. Deterministic, never crashes, linear time (fuzz tests).
5. A format corpus with expected outputs: the 53 cases, the real briefs, and a "format zoo" of tables, bullets, headings, number formats, JSON and HTML.
6. No per-case exceptions (the `src/planning/` experiment needed an ignore list for CHEFFIN).
7. Per-run metrics logged: blocks by kind, and the share of numbers inside structured blocks.

- **Settle it by** running the corpus. This needs no LLM at all.

### RQ4 — How should components be chosen?

| Option | Description |
|---|---|
| A. LLM by sentence shape (today) | unstable (1/14); capacity-blind |
| B. Code suggests defaults from content shape; the LLM keeps them or overrides with a reason | parsed table → table; parsed chart → chart; ≥ 3 short "label: value" lines → KPI row (≤ 6); steps with long detail → table, not timeline or arrow; "Mention…" → read-out |
| C. Code decides for parsed tables and charts; the LLM decides the rest | stricter B |
| D. Layouts learned from reference decks | PPTAgent-style: slide types and content schemas taken from a golden deck, matched to each slide's content |

- **Risk of B–D:** suggestions harden into templates, and every slide looks the same. B stays a suggestion, derived only from content, never decoration.
- **Settle it by** stability across 3 runs, components per slide, and capacity violations.
- **Cheapest test:** print the code suggestions for every slide of gj-h1 and CHEFFIN (free), then single-slide cases with and without the suggestions (cents each).

### RQ5 — What should the slide planner's prompt contain?

Today it is 6,780 tokens: a routing table, a visual fitness guide, structure + detail pairing, weight rules, a mandatory design-hint section, and three worked examples, all in the ROAS / ₹ domain.

| Keep (richness came from here) | Change | Remove |
|---|---|---|
| structure + detail pairing; visual fitness guide; weight rules | "key_messages are the source of truth" → "the blocks are"; worked examples in more domains; a thinking field first (`reading`) | the mandatory design-hint section (make it optional, ≤ 2 per slide); anything that invites invention |

- **Settle it by** components per slide and routing errors on the single-slide eval cases (`eval-*-disambiguation`, `eval-categorized-list-routing`).

### RQ6 — Richness without invention

**What legitimately makes a slide richer:**
- every fact the input has for that slide;
- the evidence behind each claim (a KPI strip on a summary; a table or chart on a deep-dive);
- structure paired with detail;
- a read-out (the so-what);
- qualitative content the LLM may write (actions, explanations, questions to investigate);
- numbers computed by code from facts (ratios, shares, multiples), once allowed (§10).

**Options:**

| Option | Description |
|---|---|
| A | A minimum set of components per slide purpose (e.g. executive summary = KPI strip + read-out; deep-dive = KPIs + evidence + read-out), checked by code |
| B | A reviewer that flags slides too thin for their purpose |
| C | Derived numbers computed by code |
| D | Ask the user for data (elicitor) when a slide's purpose needs data the input lacks |

- **Settle it by** components per slide on thin inputs (CHEFFIN), with invented numbers staying at 0.

### RQ7 — Headlines

- **Options:**
  - copy the brief's headline verbatim when it gives one (code copies);
  - otherwise the LLM writes a claim.
- **Fields:** split into `label` (kicker), `headline` and `subtitle`.
- **Style targets to research:**
  - a claim with a tension, naming the entity, ≤ ~14 words;
  - a sub-headline with 2–4 key numbers;
  - a kicker on every content slide.
- **Settle it by** headlines kept (spec briefs), plus a tension / evidence / kicker rate judged by you from a readable outline file (material briefs).

### RQ8 — Stability

| Lever | Cost |
|---|---|
| lower temperature (0.3 → 0.1) | free |
| code suggestions (RQ4) | free |
| parallel groups: slides that repeat a structure (one per platform) share one suggestion | free |
| keep-best selection | free |
| best-of-N | more calls, and a different winner each run, so it worsens stability |

- **Settle it by** the same component kinds across 3 runs. Also report "same up to bullets vs narrative".

### RQ9 — Checking and feedback

| Layer | What it catches | Mechanism |
|---|---|---|
| Inside the outline node | coverage (content on no slide), requirements ("Mention…") not placed, slide count, invented numbers, missing headline | code check → ≤ 1 re-ask, keep the better |
| Inside each slide branch | dropped or invented numbers, capacity, mixed chart units, too many hints | code check → ≤ 1 re-ask, keep the better |
| Deck reviewer | cross-slide issues (the same fact with different values; parallel slides inconsistent); judgment (headline tension, evidence in the sub-headline, too thin, story order, the brief's own rules such as "don't attack the current agency") | code checks + an LLM yes/no checklist → patch the named outline slides / re-plan only the flagged slides; ≤ 2 rounds; keep the best version of each slide |

**Research points:**
- LLMs fix things reliably with external feedback (code checks, tools) and poorly without it (Huang et al.; CRITIC).
- Yes/no checklists give much better LLM-judge agreement than scores (CheckEval).
- Commercial tools (Gamma, Microsoft Copilot) put a human at the outline instead of an automated plan critic.
- Settle it by issues per round, slides re-planned, regressions and cost, plus the judge's agreement with itself (the same plan reviewed 3×).

### RQ10 — Missing data policy (product decision)

When the input implies data it doesn't contain (a "revenue trend" with no numbers), what happens?
- (a) Ask the user (elicitor).
- (b) Build a qualitative slide and name the gap.
- (c) Allow sample data, clearly labelled on the slide.

It affects the 13 topic-only cases most. Today the pipeline invents.

### RQ11 — Settings semantics

Candidate changes:
- **Content handling:** "Generate" writes the wording and never the numbers.
- **Amount of text:** controls words only, never drops data.
- **Slide count:** add "Auto (from brief)" as the default.
- **Additional instructions:** indexed like the brief, so requirements become checkable.
- **New fields (optional):** "Deck use: presented / pre-read"; data-file upload later.

Settle it by walking each field through the candidate design on the 5 input kinds.

### RQ12 — Human edits

- Keep the outline review step in the UI, and show the checks' findings with it.
- Slides the user edited are not overwritten by automatic fixes.
- `/plan/refine` should apply the user's feedback as issues through the same patch mechanism as the reviewer.
- Per-slide regenerate re-plans only that slide, with no duplicate (keyed fan-in).

### RQ13 — Models per step

- **Today:** gpt-4.1 everywhere.
- **Candidate:** a stronger reasoning model only for the outline and the reviewer (2–3 calls per deck), since that's where headlines and story are decided.
- **To find out:** which models the company key allows; cost per deck; headline quality on the same inputs.

### RQ14 — LangGraph mechanics

**`StateGraph` only.** Everything needed exists in 0.6.11:
- nodes and conditional edges;
- `Send` fan-out;
- a custom reducer keyed by slide index, so re-plans replace instead of duplicating;
- `RetryPolicy` on LLM nodes for API errors (not used today);
- `max_concurrency` in the run config;
- optionally a planning subgraph, reused by the API and by a planning-only runner.

**Not needed:** the Functional API, prebuilt or tool-calling agents, multi-agent supervisors, `interrupt()` with a checkpointer, or an upgrade to 1.x.

---

## 6. A candidate design (to be validated)

This is one candidate that combines the options with the best evidence so far. It is not decided; each part maps to a research question above.

```
any input ─► INTAKE (code)                                                         RQ3
               text → numbered blocks (lines, tables, charts, slide sections, headlines, requirements, style)
               supplied_content JSON → the same blocks · later CSV/XLSX → table blocks
               + input kind: topic / single slide / material / per-slide spec + slide count if stated
   ├ topic, and it needs data it doesn't have → elicitor asks (RQ10)
   ├ single slide → skip the outline: one slide gets all the blocks                RQ1-D
   └ otherwise ─► OUTLINE PLANNER (LLM; code check + ≤ 1 re-ask inside the node)   RQ1-B, RQ7, RQ9
                    per slide: intent, label, headline (copied when the brief gives one), subtitle,
                    block_ids, points to make, emphasis (≤ 2), parallel group
                    per deck: audience and use, argument, gaps, style directives, set-aside blocks
 ─► SLIDE COMPONENT PLANNER × N (LLM; code suggestions in, tables/charts filled by code,  RQ2-B, RQ4-B, RQ5
    code check + ≤ 1 re-ask inside the node)
 ─► fan-in keyed by slide index
 ─► DECK REVIEWER (code checks + LLM checklist → outline patches / targeted re-plans, ≤ 2 rounds, keep best)  RQ9
 ─► generator (draws the plan; invents nothing; renders the planned header)        §7.2
```

**Candidate outline slide.** Additive: `slide_title` stays as the headline field for API and UI compatibility.

```yaml
slide_index: 3
intent: deep_dive                 # cover | executive_summary | deep_dive | comparison | roadmap | …
label: "PLATFORM DEEP-DIVE · 01"
slide_title: "Efficient on ROAS, softened on top-line"   # the headline
headline_block: L143              # set when copied from the brief
subtitle: "₹1.32 Cr sales · 6.35x ROAS · Jun '26"
block_ids: [L140, L141, T4, C2]
key_messages: ["Recommendation ads carry the efficiency", "Paneer drags the mix"]   # points, not data
emphasis: ["ROAS 6.35x"]
parallel_group: platform_deep_dive
```

**Candidate component.** Additive:

```yaml
component_id: category_table
kind: table
block_ids: [T4]                   # code fills content_data from the parsed block
weight: hero
design_hint: ""                   # optional; only for the slide's emphasis items
content_data: {…}                 # filled by code for bound blocks; written by the LLM for text components
```

**Estimated cost.** Upper bound: gpt-4.1 list price, no cache discount.

| Deck | Today (whole deck) | Candidate | Main driver of the increase |
|---|---|---|---|
| CHEFFIN, 6 slides | $0.36 | ≈ $0.53 | re-asks + reviewer |
| gj-h1, 14 slides | $1.01 | ≈ $1.47 | ≈ $0.2 re-asks, ≈ $0.25 LLM reviewer |
| 20 slides | ≈ $1.45 | ≈ $2.1 | same |

A code-only reviewer saves about $0.25 per 14 slides.

**What the candidate cannot fix without more input:**
- content that lives in data files;
- derived numbers (until code computes them);
- targets and projections (a policy question).

---

## 7. Contracts: state and generator

### 7.1 `src/state.py` (additive; old runs keep loading)

| Where | Change |
|---|---|
| top level | `brief_index` (the blocks), `brief_kind` |
| `OutlinePlan` | `audience_and_use`, `gaps`, `style_directives`, `set_aside` |
| `OutlineSlide` | `intent`, `label`, `headline_block`, `subtitle`, `block_ids`, `emphasis`, `parallel_group`; `slide_title` = the headline; `key_messages` become the points the slide makes |
| `ComponentPlan` | `block_ids`; `design_hint` optional |
| `SlidePlan` | `label`, `subtitle` |
| `assembled_slide_plans` | keyed reducer by `slide_index` instead of `operator.add` |
| feedback loop | `current_repair_context`, `plan_review_round`, `plan_versions` |
| retire later | `data_provenance` (block ids replace it), `previous_slide_archetype`; wire or remove `prior_plan` / `refine_feedback` |

These change in the same step as the readers of these structures:
- the API payloads (`ComponentPlanPayload`, `SlidePlanPayload`, the outline endpoints);
- `frontend/src/app/models/api.models.ts`;
- `slides.json` (written by the evaluator, read by the edit session);
- `tests/unit/test_state.py`.

### 7.2 What the generator must change so the planning gains survive

1. Remove the three invent / "add substance" lines ([user.j2:55, 60, 73](../src/prompts/generator/user.j2:55)).
2. Stop sending the whole `supplied_content` to every slide; the plan carries each component's data.
3. Render the planned kicker and sub-headline, instead of deriving a kicker ([system.j2:102](../src/prompts/generator/system.j2:102)). Write the "Source:" line only when the plan has a source ([:109](../src/prompts/generator/system.j2:109)).
4. Drop the mandatory layout archetype and `previous_slide_archetype` ([:218](../src/prompts/generator/system.j2:218)).
5. Make the blueprint a reference, not "do NOT rearrange" ([:183](../src/prompts/generator/system.j2:183)).
6. Style: `style_resolver` should apply colours and brand directions found in the brief (P14).

---

## 8. How we measure

| Metric | Tool | Today (gj-h1 / CHEFFIN) |
|---|---|---|
| Headlines kept (spec briefs) | `scripts/eval_lineage.py` | 0/13 / — |
| Brief numbers dropped, per stage | `eval_lineage.py` | 7–13% planning, 0–3% generator |
| Invented numbers, per stage | `eval_lineage.py` | 0–2 per deck / fake table + dates |
| Hints per slide | `eval_lineage.py` | 5–7 max |
| Same components across 3 runs | `eval_lineage.py` stability | 1/14 |
| Components per slide | to add | 3.04 / 2.83 |
| Kicker rate; sub-headline with numbers; headline with tension | to add (code proxy + your judgment from a readable outline file) | — |
| Capacity violations (KPIs > 6, rows > 10, long step labels, mixed chart units) | replay script → promote to a scorer | see §3.1 |
| Loop: issues per round, re-plans, regressions, cost per round | to add | — |
| Cost per deck, calls per step | run manifest | §3.5 |

**Test set by input kind:**

| Input kind | Cases |
|---|---|
| Per-slide spec | gj-h1, CHEFFIN-full |
| Material | CHEFFIN-audit, agency takeover, xtsy |
| JSON | `deck-qbr-data`, `deck-sales-data`, 4 single-slide cases |
| Topic | `base-revenue-trend`, `deck-product-launch`, `base-vague` |
| Routing | the three `eval-*` cases |

**Tooling needed first:** a planning-only runner for the main graph. It stops after planning and saves the outline, the slide plans, every check or review round, and a readable `outline.md`. It needs a `--rescore` mode that re-scores saved runs for free.

---

## 9. Plan of work

Every phase ends with LLM-free proof. Paid runs only at the end of a phase, after asking.

| Phase | Work | Exit criteria | Cost |
|---|---|---|---|
| 0. Baseline and tools | planning-only runner for the main graph (saves the outline); new scorer metrics (§8); replay harness for the code checks; the input corpus | old saved runs re-score to the §3.1 numbers; the replay runs in CI | $0 |
| 1. Intake | parser fixes (RQ3 list); JSON → blocks; input kind; slide count from the brief; production-bar tests | corpus passes: lossless, deterministic, expected structure on every format; CHEFFIN platform summary becomes one table | $0 |
| 2. Outline planner | new schema fields; blocks as input; headline copy; no invention; code check + re-ask; settings semantics (RQ11) | scripted-LLM tests (a planted defect → re-ask → fixed; a worse retry → first one kept); then a small paid outline-only run on 3 briefs (≈ $0.3–0.6) | small |
| 3. Slide component planner | blocks + decided header as input; code suggestions; bound tables and charts; optional hints; `reading` first; code check + re-ask; temperature | printed suggestions reviewed for gj-h1 and CHEFFIN; scripted-LLM tests; single-slide paid cases (cents each) | small |
| 4. Generator contract | §7.2 changes | re-render saved plans' prompts; the invent lines are gone; token count drops | $0 |
| 5. Feedback loop | deck reviewer (code + checklist), outline patcher, targeted re-plans, keyed reducer, keep-best, `/plan/refine` fix | routing, reducer and keep-best unit tests; a full scripted planning run with planted defects re-plans exactly those slides | $0 |
| 6. Comparison | old (saved runs, free) vs new, on gj-h1 × 3 + CHEFFIN-audit × 3 (+ a judge-consistency check) | the targets you set in §10 | ≈ $3.6 for the new arm at 3 repeats; ≈ $2.4 at 2 repeats; a staged ≈ $1.4 smoke run first |

---

## 10. Open decisions

| # | Question | Options | Suggestion | Status |
|---|---|---|---|---|
| Q1 | Keep two planning stages? | A / B / C / D / E / F in RQ1 | B + C + D: the outline assigns content and writes the argument; code builds spec outlines; single-slide skips the outline | open |
| Q2 | How content travels | prose / references / hybrid / fact store | hybrid now; a fact store when derived numbers are needed | open |
| Q3 | Missing data (RQ10) | ask / qualitative + gap / labelled samples | ask when the purpose needs data; otherwise qualitative + gap | open (you said "never invent numbers" on 2026-09-27; confirm it applies to topic-only requests too) |
| Q4 | Derived numbers (ratios, shares, multiples) | not allowed / computed by code with the formula recorded | computed by code, later phase | open |
| Q5 | Targets and projections | not allowed / allowed when labelled and tied to facts | — | open |
| Q6 | LLM reviewer call (≈ +$0.25 per 14 slides) | on / off / setting | on for decks ≥ 6 slides | open |
| Q7 | Stronger model for outline + reviewer | yes / no / test first | test once, if the key allows it | open |
| Q8 | Settings changes (RQ11) | as listed / partial | as listed; data upload later | open |
| Q9 | Kicker on every content slide | planner decides / generator decides / none | planner decides, generator renders | open |
| Q10 | Targets for the comparison run | set before running | — | open |
| Q11 | Budget for the comparison | full / 2 repeats / staged | staged | open |

---

## 11. Research log

| Date | Question | What was done | Finding |
|---|---|---|---|
| 2026-09-27 | RQ1–RQ3 | Read the planning code, prompts, state, API and settings form; rendered prompt sizes (slide planner 6,780 tokens) | §1; `/plan/refine` ignores feedback; keyword mapping of JSON; invention in 3 prompts + a setting description |
| 2026-09-27 | RQ3 | Indexed all 53 cases and a format zoo with `brief_index.py` | §2: 5 input kinds; parser gaps listed in RQ3; nothing lost |
| 2026-09-27 | RQ4, RQ9 | Replayed simple code checks over 4 saved old-planner gj-h1 runs | 8–10/14 slides flagged per run; the same slides every run |
| 2026-09-27 | RQ9, RQ14 | Checked LangGraph 0.6.11 (`Command`, `Send`, `interrupt`, `RetryPolicy`, `defer`; no `Overwrite`); read the docs and papers in §12 | StateGraph only; keyed reducer needed |

---

## 12. References

- LangGraph: [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) (evaluator–optimizer, orchestrator–worker with `Send`); [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) (`Command`, `Send`, reducers).
- Outline review by a human before slides: [Gamma](https://gamma.app/explore/content/guides/how-do-i-turn-my-outline-into-a-deck-using-ai); [Microsoft Copilot in PowerPoint](https://support.microsoft.com/en-us/office/create-a-new-presentation-with-copilot-in-powerpoint-3222ee03-f5a4-4d27-8642-9c387ab4854d).
- [PPTAgent / PPTEval](https://arxiv.org/abs/2501.03936): reference-deck slide types and content schemas; judging content and design per slide, coherence per deck.
- [DeepPresenter](https://arxiv.org/abs/2602.22839): reflection grounded in rendered artifacts.
- [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) · [CRITIC](https://arxiv.org/abs/2305.11738): self-correction needs external feedback.
- [CheckEval](https://aclanthology.org/2025.emnlp-main.796/): yes/no checklists for reliable LLM judges.
