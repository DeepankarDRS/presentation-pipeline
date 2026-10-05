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

**Status (2026-10-05).** Batch A is built (§9.1). Since then the user decided two things
that change this plan's order and some items; the mapping is in §9.2:
- **Content policy (2026-10-04, `docs/derived-nodes-design.md` §12):** copied / derived
  (computed by code, marked) / inferred (qualitative, flagged Keep / Remove) / invented
  (never). Settles Q4; refines Q3.
- **Render route (2026-10-05, design doc §14.6):** the generator LLM writes each slide's
  layout with slots, code blocks draw the components from the plan, then a measured
  checking loop. Planner fixes come first (§14.6 step 0). Because blocks draw exactly what
  the plan holds, plan fidelity matters more than before: a thin or empty plan now shows.

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

### 3.6 Genspark on the same briefs (2026-09-28)

Five local traces the user captured from the Genspark UI (Desktop, not in the repo): three **AI Slides** runs (HTML slides) and two **Super Agent** runs (python-pptx in a sandbox). The AI Slides traces show the prompt, the visible thinking, the to-do list, layout-check output and the final report. The Super Agent traces show only the code it wrote, its commands and patches; no planning is visible, and the Super Agent CHEFFIN prompt is not in the trace.

| Trace | Product · brief | Slides |
|---|---|---|
| `cheffin_full_context.txt` | AI Slides · the `gate-deck-cheffin-audit` brief (per-slide spec for 6 slides, "refer attached sheet", no sheet attached) | 6 |
| `xtsy-full.txt` | AI Slides · the `gate-deck-xtsy-qcomm` brief (per-slide spec, no numbers, "arrows rather than hard numbers" on slide 7) | 8 |
| `gate-deck-agency-takeover genspark.txt` | AI Slides · the `gate-deck-agency-takeover` brief (`[Platform A]` / `[Platform B]` placeholders, 6-slide mapping, speaker notes asked) | 6 |
| `superagent_cheffin_full.txt` | Super Agent · CHEFFIN audit (prompt not in the trace) | 18 |
| `superagent_xtsy_full.txt` | Super Agent · the XTSY brief, plus web research | 8 |

**Flow common to the AI Slides runs:**
1. Reason over the whole brief before any tool call: slide count, the missing attached sheet, names to keep, agency name, date.
2. Read 2–4 reference decks picked by deck type (audit, capability pitch, QBR), as inspiration, not templates.
3. Fix one design system for the deck: colours with roles, type roles (display, body, numerals), grid, shared chrome.
4. Plan every slide in one pass with the whole deck in view, choosing each slide's visual form.
5. To-do list; write slides in batches.
6. Layout check → fix only the flagged items → re-check → screenshot the reported regions.
7. Final report: per-slide contents, the judgement calls the user can change, what was left out.

**What they did well (observed):**

| # | Behaviour | Where |
|---|---|---|
| G1 | **The brief is a spec.** Per-slide headlines, table columns, callouts and "include" lists copied as given; `[Platform A]`, FLIPCART, ZAROMA kept as written (it inferred the real platforms and still didn't substitute); "exactly 6 slides" kept although it wanted to add ZAROMA slides | all three AI Slides runs |
| G2 | **Assumptions and gaps are stated, not filled.** Noticed the missing sheet; did not invent city / keyword data; the report lists judgement calls (agency name placeholder, cover date) and follow-ups (ZAROMA data mentioned in the brief but no slide for it) | AI Slides CHEFFIN, agency |
| G3 | **The brief's "don'ts" are followed and reported:** arrows only on XTSY slide 7 (the report says no invented numbers); no criticism of the current agency | AI Slides XTSY, CHEFFIN; Super Agent XTSY |
| G4 | **Style directions become colour roles:** orange = FLIPCART data, purple = ZAROMA, red only for warnings, a separate colour for the agency's own part; the brief's number formats (0.34x, ₹31.1, L for lakhs) followed | AI Slides CHEFFIN, Super Agent CHEFFIN |
| G5 | **Visual form chosen from content, with the whole deck in view:** occasions → day timeline, rows × platforms → 4×3 matrix, phases → chevrons, engine → flow with a feedback arrow, impact → arrows; dark/light rhythm planned across slides | AI Slides XTSY |
| G6 | **One style kit, defined once:** slide frame (label above a claim headline, accent rule, footer with page number and a source line); KPI tile; table; bullets with a bold lead; a callout bar whose label follows the slide's job (INSIGHT, SO WHAT, THE PATTERN, METHOD, PATH) | both Super Agent runs; AI Slides shared CSS |
| G7 | **Derived numbers computed in code:** a verification script recomputes clicks, orders, CPA, allowable CPC, the CPC-cap ladder and scenarios from the brief's base numbers before any slide is written | Super Agent CHEFFIN |
| G8 | **Missing data → a method slide, labelled:** city and keyword slides became decision-rule tables ("CPC above ₹14.8 → city-level bid cap") marked as proposed thresholds | Super Agent CHEFFIN |
| G9 | **Checks run early and admit their limits:** slide 1 checked before writing the rest; findings tiered (errors = rules with ≥ 80% measured precision, warnings = verify with a region screenshot); a run where fonts failed to load was reported as "not a clean pass" | AI Slides agency, XTSY |
| G10 | **Speaker notes:** a presenter script per slide; Super Agent notes show the working behind each derived number | AI Slides agency, Super Agent CHEFFIN |
| G17 | **A named visual is kept when it suits the data and re-chosen when it doesn't:** the 4×3 opportunity grid stayed a grid; "Show table: Metric \| Value" (one platform's 7 metrics) became a 7-tile KPI grid; "two mini tables or one combined visual" became one table plus a sorted bar chart of match-type ROAS | AI Slides CHEFFIN-full (the user's screenshots, 2026-09-28), XTSY |

**What went wrong (observed):**

| # | Failure | Where |
|---|---|---|
| G11 | Numbers changed for looks: the cover shows ₹30L / ₹85L where the brief says ₹29.4L / ₹85.5L | AI Slides CHEFFIN |
| G12 | Computed numbers retyped by hand drift: ₹7.2 (slide 8) vs 7.1 (slide 15 notes) for the same cap; ₹14.7 and ₹14.8 for the same quantity on slide 9 | Super Agent CHEFFIN |
| G13 | Invented data dressed as a chart: a "target vs current trajectory" line on the cover; scenario inputs (CPC 24, CVR 10%) invented, though labelled illustrative | Super Agent CHEFFIN |
| G14 | Most favourable outside statistic picked: search results gave India energy-drink growth from 2.25% to 13.44% CAGR; the deck used 13.4% | Super Agent XTSY |
| G15 | Heavy-handed fixes and unverified "done": a whole slide rewritten for one contrast error; no re-render after the Super Agent XTSY fixes; clean checks while earlier runs had tiny secondary text | AI Slides CHEFFIN, Super Agent XTSY |
| G16 | Much of the visible thinking goes on process (whether to ask questions, which reference to open), not on the content | all AI Slides runs |

### 3.7 What to take from them

| Lesson | Evidence | Lands in | Our gap today |
|---|---|---|---|
| L1. Treat a per-slide brief as a spec: lock headlines, required items and callouts; keep stated visuals when they suit the data (L5); take the slide count from the brief; keep names and placeholders verbatim | G1, G17 | RQ1-C, RQ7, RQ11; outline planner | outline retypes into `key_messages`; slide count from settings (P3, P11) |
| L2. The outline states `assumptions` and `not_covered` (brief content on no slide, missing attachments), shown in the UI and the final report | G2 | RQ9, RQ12; outline schema; evaluator | no such field anywhere in `src/`; the CHEFFIN run filled the missing sheet with a fake table (P15) |
| L3. Pull the brief's constraints ("no hard numbers on slide 7", "don't attack the current agency") into requirement blocks; check them by code where possible | G3 | RQ3 (requirement blocks), RQ9 | constraints come only from the settings form (P16) |
| L4. Read style directions from the brief: colour roles tied to entities or meanings, number formats | G4 | P14, §7.2 item 6; `style_directives` | `resolve_theme()` only looks up a named palette |
| L5. Decide each slide's visual form in the outline, with the whole deck in view. The brief's content and intent are locked, and its named visual is kept when it suits the data. When the data calls for another form (one platform's 7 metrics asked as "Show table" → KPI tiles), switch and record why, shown in the outline so the user can override it (corrected 2026-09-29; it said "a brief's Visual: line is locked") | G5, G17 | RQ4-E (new) | the slide planner sees only other slides' titles (P17), and follows the brief's layout words literally ("Show table: Metric \| Value" → a two-column table on `1b306e1de67f` slide 5) |
| L6. A deck style kit: slide frame (label, claim headline, sub-headline, source line), a purpose-labelled callout, KPI tile, defined once and rendered by the generator | G6 | RQ7, Q9; §7.2 item 3 | kicker derived by the generator; no purpose-labelled callout |
| L7. Derived numbers computed by code **and referenced by id**, never retyped — Genspark computed them and still drifted when retyping | G7, G12 | RQ2-D, Q4 | numbers retyped three times (P1) |
| L8. Missing data → a method or rules slide, labelled as proposed | G8 | RQ10 option (d) | the pipeline invents (P4) |
| L9. Checks after rendering: first slide before the rest; always on; tiered by measured precision; report incomplete checks; fix one element | G9, G15 | RQ9 (render layer) — outside the planners, needed for the generator contract | POM overlap / out-of-bounds read only by the off-by-default critic; fit-grow measures a different font than tables use |
| L10. Speaker notes: presenter script plus the formula behind each derived number | G10 | generator | `speaker_notes` exists in state; filling it not verified |

**Do not copy:** rounding brief numbers for looks (G11), decorative invented data (G13), choosing outside statistics (G14), whole-slide rewrites for one finding (G15), a mandatory reference-deck step on every request (G16), HTML with absolute positioning, and running LLM-written code (the Super Agent sandbox). Our deterministic compiler already gives an editable .pptx without it.

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
| P14 | **Style asked for in the brief is ignored** (brand colours, colour roles, number formats) | §3.2, §3.6 G4 |
| P15 | **Assumptions and gaps are silent:** a missing attachment or brief content with no slide is filled or dropped without telling the user | §3.2 fake table; §3.6 G2 |
| P16 | **The brief's own constraints are not captured** ("no hard numbers here", "don't attack the current agency"), so nothing checks them | §3.6 G3 |
| P17 | **No deck-level visual plan:** each slide's form is chosen alone, seeing only the other titles | §1.2; §3.6 G5 |

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
| E. The outline assigns each slide a visual form (timeline, matrix, phases, flow, comparison, KPI + evidence …) in one call with the whole deck in view; a brief's "Visual:" line is copied and locked; the slide planner builds components for that form | Genspark AI Slides (§3.6 G5); fixes P17 |

- **Risk of B–E:** suggestions harden into templates, and every slide looks the same. B stays a suggestion, derived only from content, never decoration. E must stay the LLM's choice from content; a variety rule in code caused the 2026-09-10 regression.
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
| E | A purpose-labelled read-out (INSIGHT, SO WHAT, METHOD, PATH) on content slides; qualitative, so no invention risk (§3.6 G6) |
| F | Missing data turned into a method or rules slide (decision rules, thresholds labelled "proposed"), as Genspark did for the city and keyword views (§3.6 G8) |

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
| Report to the user | assumptions made, brief content on no slide, missing attachments, constraints honoured (§3.6 G2–G3) | code fills `not_covered` from the coverage check; the outline writes `assumptions`; shown with the outline and in the final evaluation |
| After rendering (outside the planners) | overlap, clipping, contrast, font floor, empty placeholders | first slide checked before the rest; always on; errors only for rules with measured precision, the rest advisory; a check that could not run is reported as incomplete, not passed; fixes touch one element (§3.6 G9, G15) |

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
- (d) Turn the slide into a method or rules slide (how the data would be read, with proposed thresholds), and list the missing data in `assumptions` / `not_covered`. Genspark did this for CHEFFIN's city and keyword views (§3.6 G8).

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
                    block_ids, points to make, emphasis (≤ 2), parallel group, visual form (RQ4-E)
                    per deck: audience and use, argument, gaps, style directives, set-aside blocks,
                              assumptions, not_covered, constraints (§3.7)
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
visual_form: kpi_plus_evidence    # decided with the whole deck in view; copied when the brief states a visual
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
| top level | `brief_index` (the blocks), `brief_kind`; later `fact_sheet` (id, value, unit, source block or formula, display string) for derived numbers (Q4, §3.6 L7) |
| `OutlinePlan` | `audience_and_use`, `gaps`, `style_directives` (incl. colour roles and number formats, §3.6 L4), `set_aside`, `assumptions`, `not_covered`, `constraints` (the brief's "don'ts", as block ids) |
| `OutlineSlide` | `intent`, `label`, `headline_block`, `subtitle`, `block_ids`, `emphasis`, `parallel_group`, `visual_form` (+ `visual_block` when the brief states it); `slide_title` = the headline; `key_messages` become the points the slide makes |
| `ComponentPlan` | `block_ids`; later `fact_ids`; `design_hint` optional |
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
6. Style: `style_resolver` should apply colours and brand directions found in the brief (P14), including colour roles (entity → colour, a colour reserved for warnings) and number formats (§3.6 G4).
7. A deck style kit rendered the same way on every slide: label, claim headline, sub-headline, source line, and a purpose-labelled read-out (§3.6 G6).
8. Numbers come from the plan's bound blocks or fact ids and are never retyped or rounded for looks (§3.6 G11, G12).
9. Speaker notes: a short presenter script, plus the formula for each derived number (§3.6 G10).

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

### 9.1 Priority order by impact on the output (2026-09-28)

Ranked by expected effect on the finished deck, from the evidence in §3 and the prompt lines cited below. Line numbers are as of 2026-09-28. Rows added on 2026-09-29 (planners 13–20, generator 11–12, R1–R4) come from reviewing three of our decks (§11) and cite lines as of that date, including the uncommitted matrix fix in `slide_component_planner/system.j2`.

**Planners** (`outline_planner`, `outline_replanner`, `slide_component_planner`, `state.py`):

| # | Change | Why (evidence) | Files | Effort | Free check |
|---|---|---|---|---|---|
| 1 | Remove invention: the "plausible / invent a number" lines and the $42.8M-style examples; missing data becomes a gap, never a number; "Generate" writes wording, never figures | fake table and dates (§3.2); invented numbers → 0 in §3.3 | `outline_planner/system.j2:43`, `outline_planner_schema.py:56`, `outline_replanner/system.j2:18`, `settings_mapper.py` | small | prompt render; grep |
| 2 | The brief as a spec: `label` / `headline` / `subtitle`, the brief's headline copied; slide count from the brief when stated; names and placeholders verbatim | headlines 0/13 → 13/13 (§3.1, §3.3); `EXACTLY {{ target_slides }}` overrides "6-SLIDE"; G1 | outline schema, `outline_planner.py`, prompts, `state.py` | small–medium | outline replay; `eval_lineage.py` |
| 3 | Content by reference: `block_ids` per slide (`brief_index.py`); the slide planner gets those lines verbatim; code fills parsed tables and charts; `key_messages` = points, not data; replaces `_filter_supplied_content_for_slide` | 7–13% numbers dropped in planning; wrong CPC chart (§3.1–3.2); 1% in §3.3 | both planners, prompts, `planner_schema.py` | medium | `eval_lineage.py` |
| 4 | Code checks + ≤ 1 re-ask inside each node: coverage, invented numbers, slide count, headline present; dropped numbers, capacity, mixed chart units; keep the better attempt (reuse `src/planning/checks.py`) | 8–10 / 14 slides flagged per old run; re-ask fixed 6/6 storylines (§3.3) | `outline_planner.py`, `slide_component_planner.py` | medium | scripted-LLM tests |
| 5 | Deck-level fields in the same outline call: `assumptions`, `not_covered`, `constraints`, `style_directives` | P14–P16; G2–G4 | outline schema and prompt, `state.py` | small–medium | replay |
| 6 | Richness without invention: claim + evidence pairing, a purpose-labelled read-out, a method slide for missing data; `design_hint` optional, ≤ 2 per slide (keep the uncommitted matrix fix) | 1.80 components per slide without invention; 14/14 slides ask for highlighting (§3.1, §3.3) | `slide_component_planner/system.j2:150`, `planner_schema.py` | small | single-slide cases (cents) |
| 7 | The slide planner sees a one-line summary of each other slide; parallel slides share a structure | the CHEFFIN table repeated as bullets; production deck's shared deep-dive layout (§3.4) | `slide_component_planner.py`, `user.j2` | small | replay |
| 8 | The replanner edits instead of regenerating: brief lines + neighbours' titles, locked fields kept, no new numbers; wire `/plan/refine` | §1.3 | `outline_replanner.py`, prompts, `api.py` | small | unit test |
| 9 | Planner temperature 0.3 → 0.1 | 1/14 stable (§3.1) | `models.yaml` | trivial | needs 2–3 paid runs |
| 10 | The outline picks each slide's visual form (RQ4-E) | G5; test first (Q13) | outline schema, slide planner | medium | outline-only runs |
| 11 | Keyed merge + the plan-reviewer loop | P8, P12 | `state.py`, `graph.py`, `plan_reviewer` | medium–large | unit tests |
| 12 | Derived numbers in a fact sheet (Q4) | §3.4; G7, G12 | new module + both planners | medium–large | unit tests |
| 13 | Remove the dated caption example ("Source: Company Q3 2025 earnings report"); a caption cites only what the plan names | invented dated sources on all three reviewed decks: "Q2 FY24", "May 2024" (CHEFFIN), "XTSY Consumer Occasion Study 2024" (XTSY) | `slide_component_planner/system.j2:218` | trivial | prompt render; grep |
| 14 | One entity's metrics → KPI tiles, not a two-column table: lift the "more than 5 tiles (use table)" cap; add a two-row KPI grid (6–8 tiles) | `1b306e1de67f` slide 5: FLIPCART's 7 metrics as "Metric \| Value"; Genspark drew the same content as a 7-tile grid (G17) | `slide_component_planner/system.j2:91`, `recipes.yaml` (kpi_row) | small | compile the grid recipe; single-slide cases (cents) |
| 15 | Replace worked Example 1 ("match types → table") with examples chosen by content shape, across domains: one entity's metrics → KPI grid; one measure across entities → sorted bar chart; entities × measures → table | `1b306e1de67f` slide 6: match-type ROAS (one measure, 6 types) drawn as a table, against the prompt's own "entity + single metric → chart" row; the example matched by topic | `slide_component_planner/system.j2:257` | small | prompt render; single-slide cases |
| 16 | Chevrons only for a real ordered sequence of ≤ 5 short labels (≤ 2 words) at full width; items that aren't a sequence → tiles or an icon list; capacity declared in the knowledge file | XTSY slides 4 and 7: 4 phases in a half-width card and 7 impact areas as chevrons, labels broken into single letters (13 broken words in the deck) | `slide_component_planner/system.j2:32, 80`, `components/process-arrow.yaml` | small | prompt render; R3 re-check of the saved deck |
| 17 | Flow with branches: a nodes + edges format (fan-out / fan-in) and a branching flow recipe | XTSY slide 6: "input → engine → 4 parallel actions → outcome" drawn as one line, the outcome dropped | `slide_component_planner/system.j2:224–226`, `components/flow.yaml`, `recipes.yaml` (flow) | medium | compile a branching Flow; render |
| 18 | Provenance: values found in the brief count as user data (or retire `data_provenance` for block ids, §7.1) | `1b306e1de67f` manifest: `user 0, sample 37`, though every number came from the brief | `settings_mapper.py:129` (`compute_provenance`) | small | unit test |
| 19 | Stop mapping words to components: remove `_INTENT_KEYWORDS`; with no plan, fall back to the slide planner or a neutral default; the slide editor passes the user's words to the planner | the XTSY slide 3 naming trap ("matrix" → 2×2; also "grid" → table, "funnel" → pyramid, "pipeline" → chevrons), live in single-slide runs and slide edits | `context_builder.py:29–55`, `slide_replanner.py:71`, `tests/unit/test_context_builder.py` | small–medium | unit tests |
| 20 | Caveats, data-quality notes and formulas go into footnotes, table captions or a read-out on the slide they qualify; a slide of their own only when the brief asks for one | `tables-check` CHEFFIN slide 5: a whole slide of caveats and formulas; Genspark put formulas in row captions and the caveat in footnotes | `outline_planner/system.j2` | small | outline replay |

**Generator** (`generator.py` and its prompts):

| # | Change | Why (evidence) | Files | Effort | Free check |
|---|---|---|---|---|---|
| 1 | Stop invention: remove the invent / "add substance" lines; a "Source:" line only when the plan has a source | fake sources ("Q2 FY24"), fake table, invented uplift (§3.2) | `generator/user.j2:55, 60, 73`, `generator/system.j2:109` | small | prompt render; replay saved plans |
| 2 | Draw the planned label, headline and subtitle instead of deriving a kicker | headline loss (§3.1) | `generator/system.j2:102–104`, `user.j2` | small–medium | `eval_lineage.py` |
| 3 | Only the slide's own data: per-component data from the plan, not the whole `supplied_content`; numbers never retyped or rounded | §1.5; G11, G12 | `generator.py`, `user.j2` | medium | `eval_lineage.py` |
| 4 | The brief's colours and number formats: theme override + colour-role map | default blue on CHEFFIN (§3.2); G4 | `style_resolver.py`, `context_builder.py` | small–medium | compile saved XML with the override; render |
| 5 | Remove forced variety and the rigid blueprint: drop the mandatory archetype and "do NOT rearrange"; the blueprint becomes a reference | the 2026-09-10 regression; G5 | `generator/system.j2:183, 218`, `user.j2:29–32` | small | prompt render; needs a paid A/B |
| 6 | Code-only layout checks on by default: POM overlap / out-of-bounds + layout audit; first slide checked before the rest; one-element fixes; "incomplete" rather than "passed" when a check can't be trusted | the CHEFFIN slide 5 table overflow went unflagged; `critic_mode` defaults to off; G9 | `graph.py`, critic / layout audit, repairer | medium | re-check saved XML |
| 7 | Read-out and method slide drawn as planned (pairs with planner #6) | P13 | recipes | small | single-slide cases |
| 8 | Report assumptions, `not_covered` and constraints in the final evaluation | G2–G3 | evaluator, UI | small–medium | replay |
| 9 | Derived numbers from the fact sheet (pairs with planner #12) | G7, G12 | generator | medium | unit tests |
| 10 | Speaker notes: a presenter script + the formula for each derived number | G10 | generator | small | prompt render |
| 11 | Theme colour tokens (`$accent`, `$accentAlt`, …) in the diagram examples instead of hard-coded blue hex | `1b306e1de67f` slide 4 and XTSY slides 4 and 7: blue chevrons in an orange / purple deck | `components/process-arrow.yaml:17–20, 45`, `recipes.yaml` (process_arrow) | trivial | compile with tokens; render |
| 12 | Card shells only where a component needs a frame; no top-right badges; no placeholder shapes for visuals the brief asks for but we can't draw (they go to `not_covered`, planner #5) | near-empty cards (`1b306e1de67f` slides 2, 4, 6); a green circle on both CHEFFIN covers; "TRAFFIC ECONOMICS" and "TECH ENABLED" badges; a gradient card (XTSY slide 7) | `generator/system.j2:105, 111`, `house-style.yaml:40, 50, 95` | small | prompt render; replay prompts |

**Render layer and tooling** (added 2026-09-29):

| # | Change | Why (evidence) | Files | Effort | Free check |
|---|---|---|---|---|---|
| R1 | Chart options: a second value axis, values on bars, horizontal and stacked bars. The normalizer lifts the extra `<Chart>` options (POM rejects unknown attributes) and `pptx-post.js` patches the chart XML (POM's writer hard-codes `barDir="col"` and `grouping="clustered"`, with no data labels) | `tables-check` CHEFFIN slide 4: CVR (%) and AOV (₹) on one axis, so the CVR bars vanish; Genspark's sorted horizontal bars with values (CHEFFIN-full slides 3 and 6) | `src/node/pptx-post.js`, `src/compiler/normalizer.py`, `components/chart.yaml`, the planner's chart format | medium | XML-patch unit tests; compile + LibreOffice render |
| R2 | Check every palette against `meta.contrast_targets` when themes load; flag accents that fail as text and use a darker text accent there | `saascolor` accent 2.44:1 and `navy-orange` 2.28:1 on their surfaces (target 3.0): faint orange labels and headline phrases on `1b306e1de67f` | `style_resolver.py`, `palettes.yaml` | small | unit test over all palettes |
| R3 | Broken-word and diagram label-fit checks on every compiled slide (promote `word_breaks`); on failure widen the band, switch the variant or re-plan the component | XTSY: 13 broken words on slides 4, 6 and 7; `1b306e1de67f` slide 4 | `scripts/eval_metrics.py:155` → `validator.py` / the layout checks (generator #6) | small–medium | re-check the saved decks |
| R4 | Record the git commit (plus an uncommitted-changes flag), the theme name and a hash of the request in every `run-manifest.json` | `1b306e1de67f` could not be traced to a commit (only eval bundles record `git_commit`), and its theme existed only on the test PC | `evaluator.py:144` | trivial | unit test |

**Batches:**
- **A:** planners 1, 2, 9 + generator 1, 2, 5. Prompts and schema; checked with free replays. The generator half is needed or the planner gains are lost at the XML step.
- **B:** planners 3, 4 + generator 3, 4. Content fidelity and brief style; reuses the Test 1 code.
- **C:** planners 5–8 + generator 6–8, then planners 10–12 and generator 9–10.
- **Proof:** one paid comparison after A + B on gj-h1 + CHEFFIN-audit (≈ $2), after asking.
- **Added 2026-09-29:** A += planners 13, 15, 16, 20, generator 12, R4 · B += planners 14, 18, generator 11, R2 · C += planners 17, 19, R1, R3.

**Batch A status (built 2026-09-29, LLM-free checks only; awaiting the paid comparison):**

| Item | Status | What was built | Free check |
|---|---|---|---|
| Planner 1 | built | invent lines and `$42.8M` examples removed from the outline schema and prompt, `outline_replanner/system.j2` and the "Generate" description (`settings_mapper.py`, `api.py`); examples are shapes (`"<metric>: <value> (<change>)"`); missing data → build the slide from what the brief has, no table or chart for data that is not there. The `gaps` / `not_covered` fields wait for planner 5 | rendered prompts on 6 briefs: 0 invent / plausible / `$42.8M`; unit test |
| Planner 2 | built | `label` / `slide_title` (the headline, no 8-word cap) / `subtitle` on the outline slide, copied into `SlidePlan` (so `slides.json`), the slide planner's prompt, the from-plan API payload, the repairer's and slide editor's re-plans; the plan editor has kicker / headline / subtitle boxes; the prompt copies the brief's headlines word for word and keeps names, placeholders and number formats. Slide count: test case → count stated in the request (`outline_planner.stated_slide_count`: "6-SLIDE", "five-slide", or "Slide 1 … Slide N") → settings bucket. A code copy of brief headlines (`apply_headline_blocks`) waits for planner 3 (block ids) | 53 cases: the count matches in all 14 that state one (gj-h1 target 8 → 14, CHEFFIN-audit 8 → 6); Angular build + browser check with a stubbed outline; unit tests |
| Planner 9 | built | `outline_planner` and `slide_component_planner` temperature 0.3 → 0.1 | config load; unit test |
| Planner 13 | built | caption example → "a note or source named in the key_messages", never a made-up source or date | prompt render; unit test |
| Planner 15 | built | worked examples by content shape outside the ad domain: one entity's metrics → `kpi_row` (≤ 5 tiles until planner 14), one measure across entities → sorted bar chart, entities × measures → table; "route by shape, not topic" | prompt render (7,033 → 7,468 tokens); unit test |
| Planner 16 | built | chevrons only for an ordered sequence of ≤ 5 steps with ≤ 2-word labels at full width; unordered items → `bullet_list` with icons; capacity and the 2026-09-29 failure in `process-arrow.yaml` pitfalls (reach the generator) | prompt render; the matrix fix's 10 lines unchanged |
| Planner 20 | built | caveats, data notes and formulas as a "Note:" key_message on the slide they qualify; a slide of their own only when asked | prompt render |
| Generator 1 | built | invent / "add substance" lines removed from `generator/user.j2`; "Source:" only when the plan names one. Three more invention sources found by the replay and fixed: `design-language.yaml` `content_invention` (in every slide's NOTES: "invent realistic figures", "at least 4-6 data points", "3-5 rows with named entities"; now `content_rules`), house-style "ADD a band (stat row …)" for thin slides, and the golden example's `Source: [data source] · [period]` line | replay of the 14 gj-h1 generator prompts: every pattern 0 (before: 14–96 each) |
| Generator 2 | built | a `HEADER` block (kicker / headline / subtitle, drawn as written) replaces "SLIDE OBJECTIVE"; no derived kicker (no label → no kicker) | replay; unit test |
| Generator 5 | built | mandatory archetype section, "PREVIOUS SLIDE ARCHETYPE" block and the archetype list removed; blueprint is a reference to adapt. `deck_nodes.py` still parses the (now absent) marker and `state.previous_slide_archetype` has no reader: retire with §7.1 | replay (archetype mentions 96 → 0); `test_hint_capabilities` flipped to assert the removal |
| Generator 12 | built | card shells only where a component needs a frame; no header badge or pill (house-style + the 7 `BADGE` pills in `blueprints.yaml` reference XML); no placeholder shapes for visuals the plan does not give | replay; `test_layout_sizing` compiles every reference slide |
| R4 | built | `run-manifest.json` records `git_commit`, `git_uncommitted_changes`, `theme`, `request_sha256` | unit tests (mocked and real git) |

Unit tests after batch A: 483 pass, the same 4 known failures (baseline 464). Found on the way, not fixed: `outline_planner/user.j2` crashes on a partial `deck_settings` dict with no `write_for` (the API always sends the full form); a count inside a longer brief ("3 slides on pricing") would be read as the deck size.

**Needs a paid run to confirm batch A:** the model copies brief headlines and fills label / subtitle (headlines kept, `eval_lineage.py`); no invented numbers in outline, plan or XML; the XML draws the planned header; stability at 0.1 (same components across runs); the layout effect of dropping forced variety (generator 5); routing on the `eval-*` single-slide cases (planners 15, 16).

**File order within batch A:** `outline_planner` (+ schema, prompts and the matching `state.py` fields) → generator prompts → `models.yaml`. Then `slide_component_planner` (batch B), and `outline_replanner` last (it only runs on a user's per-slide regenerate).

### 9.2 Alignment with the render route (`docs/derived-nodes-design.md` §14.6, 2026-10-05)

§14.6 build order: **0** planner fixes + font embedding + shrink guard → **1a** slot test
(≈ $0.5, kill criteria in design doc §14.5) → **1** blocks in `src/compiler/blocks/` →
**2** generator writes skeleton + slots, checking loop → **3** paid check → **4** more blocks,
plan reviewer loop. How the open §9.1 items sit in that order:

| §9.1 item | Status under §14.6 |
|---|---|
| **New, step 0** (from the hold-out test, design doc §14.3b) | re-ask instead of the silent empty plan in `slide_component_planner.py` (both `except` branches return `components: []`); reject planner instructions / speaker notes as slide text; `SLIDE_SPARSE` for thin slides; reject card bodies that repeat the title. These are the in-branch part of planner 4 |
| Planner 3 (content by reference) | unchanged, batch B; more important now, since blocks copy plan content verbatim |
| Planner 4 (code checks + re-ask) | split: the step 0 checks above first; coverage / invented numbers / capacity checks stay batch B (= `plan-reviewer-loop.md` step B) |
| Planner 6 (richness without invention) | unchanged; its gap is what `SLIDE_SPARSE` reports. Inferred card lines now allowed and flagged (§12 content policy) |
| Planner 11 (keyed merge + reviewer loop) | §14.6 step 4 (`docs/plan-reviewer-loop.md`) |
| Planner 12 (derived numbers) | principle decided (Q4); code later |
| Planner 14 (one entity's metrics → KPI tiles) | largely done in code by the 2026-09-29 layout batch (2-column label / number table → KPI tiers, L5); the KpiRow block draws 6+ tiles as tiers |
| Planner 17 (branching flow) | a flow block is step 4; linear flows are drawn as process steps (Phase 0b, uncommitted 2026-10-05) |
| Planners 5, 7, 8, 10, 18, 19 | unchanged |
| Generator 3 (only the slide's own data) | for kinds with a block: done by design (the prompt gets a slot line, not the data); still needed for kinds without a block |
| Generator 4 (brief colours) | unchanged; the theme override must also reach the blocks' style pack |
| Generator 6 (code layout checks on by default) | becomes the §14.6 checking loop (step 2) |
| Generator 11 (theme tokens in diagram examples) | blocks use tokens; still needed for diagrams without a block (timeline, pyramid, tree, layer, matrix) |
| Generator 12 (card shells) | card grids drawn by the block; the rule stays in the skeleton prompt |
| Generators 7–10 | unchanged |
| R1 (chart options) | unchanged; the chart block uses native `<Chart>` |
| R2 (contrast per palette) | unchanged; also applies to the style packs |
| R3 (broken-word checks) | shrink guard (step 0) + checking loop (step 2) |

---

## 10. Open decisions

| # | Question | Options | Suggestion | Status |
|---|---|---|---|---|
| Q1 | Keep two planning stages? | A / B / C / D / E / F in RQ1 | B + C + D: the outline assigns content and writes the argument; code builds spec outlines; single-slide skips the outline | open |
| Q2 | How content travels | prose / references / hybrid / fact store | hybrid now; a fact store when derived numbers are needed | open |
| Q3 | Missing data (RQ10) | ask / qualitative + gap / labelled samples | ask when the purpose needs data; otherwise qualitative + gap | open (you said "never invent numbers" on 2026-09-27; confirm it applies to topic-only requests too). 2026-10-04: refined by the content policy (design doc §12): invented never; inferred qualitative lines allowed and flagged. Still open: ask vs qualitative + gap |
| Q4 | Derived numbers (ratios, shares, multiples) | not allowed / computed by code with the formula recorded | computed by code, later phase | **decided 2026-10-04**: computed by code, marked as derived (design doc §12); build later |
| Q5 | Targets and projections | not allowed / allowed when labelled and tied to facts | — | open |
| Q6 | LLM reviewer call (≈ +$0.25 per 14 slides) | on / off / setting | on for decks ≥ 6 slides | open |
| Q7 | Stronger model for outline + reviewer | yes / no / test first | test once, if the key allows it | open |
| Q8 | Settings changes (RQ11) | as listed / partial | as listed; data upload later | open |
| Q9 | Kicker on every content slide | planner decides / generator decides / none | planner decides, generator renders | open |
| Q10 | Targets for the comparison run | set before running | — | open |
| Q11 | Budget for the comparison | full / 2 repeats / staged | staged | open |
| Q12 | Show `assumptions` / `not_covered` to the user | outline review only / also in the final report / off | both (§3.6 L2) | open |
| Q13 | Visual form decided in the outline (RQ4-E) | yes / no / test first | test first on xtsy + agency takeover (outline-only runs) | open |
| Q14 | Post-render checks on by default, first slide checked before the rest | yes / setting / no | yes; outside the planners but part of the generator contract (§3.6 L9) | **direction decided 2026-10-05**: the §14.6 checking loop (measured, ≤ 2 rounds, keep best); "first slide before the rest" still open |
| Q15 | Batch B timing under §14.6 | with step 0 / after the slot test (1a) / after step 3 | with step 0 for planners 3 and 4 (both free, both raise plan fidelity, which blocks now expose) | open (2026-10-05) |

---

## 11. Research log

| Date | Question | What was done | Finding |
|---|---|---|---|
| 2026-09-27 | RQ1–RQ3 | Read the planning code, prompts, state, API and settings form; rendered prompt sizes (slide planner 6,780 tokens) | §1; `/plan/refine` ignores feedback; keyword mapping of JSON; invention in 3 prompts + a setting description |
| 2026-09-27 | RQ3 | Indexed all 53 cases and a format zoo with `brief_index.py` | §2: 5 input kinds; parser gaps listed in RQ3; nothing lost |
| 2026-09-27 | RQ4, RQ9 | Replayed simple code checks over 4 saved old-planner gj-h1 runs | 8–10/14 slides flagged per run; the same slides every run |
| 2026-09-27 | RQ9, RQ14 | Checked LangGraph 0.6.11 (`Command`, `Send`, `interrupt`, `RetryPolicy`, `defer`; no `Overwrite`); read the docs and papers in §12 | StateGraph only; keyed reducer needed |
| 2026-09-28 | §9.1 | Read the three planners' and the generator's prompts and schemas; ranked changes by expected impact on the output | §9.1: invention lines in 6 prompt/schema places; header, slide count and forced-variety rules; batches A–C |
| 2026-09-28 | RQ2, RQ4, RQ6, RQ7, RQ9, RQ10 | Read five Genspark traces (3 AI Slides, 2 Super Agent) on the CHEFFIN, XTSY and agency-takeover briefs; checked our code for brief style handling (`style_resolver.resolve_theme()` reads only a named palette) and for any assumptions / gaps field (none) | §3.6–3.7: brief-as-spec, stated assumptions and gaps, colour roles, deck-level visual forms, code-computed numbers that still drift when retyped; new P15–P17, RQ4-E, RQ6-E/F, RQ10-(d), Q12–Q14 |
| 2026-09-29 | §9.1 batch A | Built batch A (planners 1, 2, 9, 13, 15, 16, 20; generator 1, 2, 5, 12; R4) with LLM-free checks: prompt renders on 6 briefs, a replay of the 14 saved gj-h1 generator prompts, the slide-count parse over all 53 cases, an Angular build and a stubbed browser check of the plan editor; 483 unit tests pass, 4 known failures | Three invention sources outside the §9.1 list reached every generator prompt (`design-language.yaml` `content_invention`, house-style "ADD a band", the golden `Source:` template); the default settings bucket told gj-h1 "EXACTLY 8" slides for a 14-slide brief. Status table under §9.1 |
| 2026-09-29 | RQ4, RQ5, RQ9 | Reviewed three of our decks against their briefs and Genspark's slides: `tables-check` (CHEFFIN short brief, commit 9b668e1), `1b306e1de67f` (CHEFFIN full brief, 2026-09-28, theme `saascolor`), `189ac04f3584` (XTSY); mapped every finding to §9.1 | 14 items were missing and are now in §9.1 (planners 13–20, generator 11–12, R1–R4); L1 / L5 corrected with G17: a named visual is kept when it suits the data, otherwise switched with a recorded reason |
| 2026-10-05 | §9, Q3, Q4, Q14 | Aligned with the content policy (2026-10-04) and the render route the user chose (`derived-nodes-design.md` §14.6); hold-out test on 3 new briefs (§14.3b) | §9.2: step 0 adds four planner fixes (empty-plan re-ask, no instruction / notes text, `SLIDE_SPARSE`, card body ≠ title); generator 3 / 6 / R3 absorbed by blocks and the checking loop; Q4 decided, Q3 refined, Q14 direction set, Q15 added |

---

## 12. References

- LangGraph: [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) (evaluator–optimizer, orchestrator–worker with `Send`); [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) (`Command`, `Send`, reducers).
- Outline review by a human before slides: [Gamma](https://gamma.app/explore/content/guides/how-do-i-turn-my-outline-into-a-deck-using-ai); [Microsoft Copilot in PowerPoint](https://support.microsoft.com/en-us/office/create-a-new-presentation-with-copilot-in-powerpoint-3222ee03-f5a4-4d27-8642-9c387ab4854d).
- [PPTAgent / PPTEval](https://arxiv.org/abs/2501.03936): reference-deck slide types and content schemas; judging content and design per slide, coherence per deck.
- [DeepPresenter](https://arxiv.org/abs/2602.22839): reflection grounded in rendered artifacts.
- [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) · [CRITIC](https://arxiv.org/abs/2305.11738): self-correction needs external feedback.
- [CheckEval](https://aclanthology.org/2025.emnlp-main.796/): yes/no checklists for reliable LLM judges.
- Genspark AI Slides and Super Agent: five UI traces captured by the user on 2026-09-27/28 (local only; file names in §3.6). Findings are paraphrased; the traces are not copied into the repo.
