# Plan reviewer as a feedback loop — design proposal

> **Status: proposal, 2026-09-27. No code yet; waiting for the decisions in §11.**
> Direction D14 (`docs/architecture-north-star.md` §12): keep `outline_planner` + `slide_component_planner`, carry Test 1's fidelity fixes into them, and turn `plan_reviewer` into a feedback loop that changes the plan.
> Branch `test-1-planning`. Unit-test baseline this session: 464 pass, 4 known failures.
>
> **Update 2026-10-05 (alignment with `docs/derived-nodes-design.md` §14.6, chosen by the user):**
> - **Order.** The full loop here is **step 4** of the §14.6 build order (after planner fixes, the slot test, blocks and the generator change). Three small pieces of it move to **step 0** ("planner fixes first"): the in-branch re-ask for an empty plan (new row in §2), rejecting planner instructions / speaker notes as slide text (C16), and the thin-slide report (C14 ⇄ the renderer's `SLIDE_SPARSE`). Card bodies that repeat their title join C15.
> - **Content policy (user, 2026-10-04, design doc §12)** replaces the blanket D2 "never invent": copied / **derived** (allowed, computed by code, marked; settles D13) / **inferred** (allowed, qualitative, flagged Keep / Remove) / invented (never). Affects F4, §5.4 and decision 8.
> - **New input from the renderer:** blocks draw exactly what the plan holds, so thin or empty plans now *show* (hold-out test, design doc §14.3b). The renderer reports `SLIDE_SPARSE` / `SLIDE_OVERFULL`, and the duplicate check (two components on a slide with ≥ 70% overlapping items, design doc §5) becomes C17, also built in step 0.
> - **Naming.** "Skeleton" in §7 means *suggested components*, not the §14.6 XML skeleton with slots.
> - **Models.** Since 2026-10-01 the planners and the reviewer run on gpt-5-mini (`models.yaml`); the §8 costs are gpt-4.1 list prices and need re-estimating before the paid comparison.
> - Unit-test baseline now 557 pass, 4 known failures.

## 1. In short

- **A review loop can't fix what the planners never see.** On the four saved gj-h1 runs of the old planner, Test 1's checks (adapted to the old plan format) flag **8–10 of 14 slides in every run** (§3). Put a reviewer loop on today's planners and it would re-plan most of the deck every round. The re-planned slides still wouldn't see the brief data the outline dropped, because `slide_component_planner` only reads the outline's retyped `key_messages`. So the fidelity fixes go first, and the loop handles what remains.
- **Recommendation: a layered loop (option L in §4).** Each problem is fixed at the cheapest point where it can be seen:
  1. **Outline:** a code check, then at most one re-ask, inside `outline_planner`. This is Test 1's storyline gate; in 6 of 6 final runs, one re-ask cleared every issue.
  2. **Each slide branch:** code fills parsed tables and charts, then a code check, then at most one re-ask. In Test 1, 4–5 of the 14 gj-h1 slides needed a re-ask, and 1–3 of the 6 CHEFFIN slides.
  3. **`plan_reviewer`:**
     - deck-level code checks, plus one LLM *checklist* call for things only judgment can see (headline tension, evidence in the sub-headline, slides too thin for their job, story);
     - issues are tagged by slide and stage, and code does the routing:
       - outline issues → a patch to the named outline slides only;
       - slide issues → a `Send` re-plan of the flagged slides only;
     - changed slides are re-reviewed. At most 2 fix rounds, and the best version of each slide is kept.
  4. **Stability:** code suggests default components (a "skeleton") from each slide's content, and slides in a parallel group get the same skeleton.
- **Cost:** planning rises from **$0.44 to ≈ $0.9 per 14-slide deck**, and to ≈ $1.25 for 20 slides. These are list prices on gpt-4.1 with no cache discount, so they are an upper bound.
  - About $0.25 of the increase is the LLM reviewer; the rest is the fidelity re-asks.
  - A whole deck (with generation) goes from ≈ $1.01 to ≈ $1.5.
- **Paid comparison:** the *old* and *Test 1* arms cost nothing, because their saved runs can be reused (§9). The new arm at 3 repeats per case is **≈ $3.6, not ≈ $2**. Options are in Q3.

## 2. The code today

| Piece | Today | Effect |
|---|---|---|
| `outline_planner` ([outline_planner.py](../src/agents/outline_planner.py), [schema](../src/agents/outline_planner_schema.py), [prompt](../src/prompts/outline_planner/system.j2)) | 1 call over the raw brief; `slide_title` ≤ 8 words; `key_messages` retype the data as prose; the schema and prompt say to invent a plausible number when data is missing | headline lost; data flattened; invention allowed |
| `slide_component_planner` ([`plan_single_slide`](../src/agents/slide_component_planner.py:133)) | 1 call per slide via `Send` from `fan_out_slide_plans`; sees only its outline slide (and `supplied_content` filtered by keywords), **never the brief**; 6.8k-token system prompt; `design_hint` mandatory; temperature 0.3. `repair_context` already exists (used by the repairer's REGENERATE tier) | numbers dropped when the outline dropped them; decoration on every component; a different plan on every run |
| Failed slide plan (added 2026-10-05) | `plan_single_slide` raising is caught in both `slide_plan_serial_node` and `slide_component_planner_node`, which return `components: []` and log an error ([slide_component_planner.py](../src/agents/slide_component_planner.py)) | a silently empty slide: the generator invents content for it (XTSY gpt-5-mini slide 7, launch 5 in the hold-out) or code draws nothing; CHEFFIN r1 slide 3 lost its chart and table. Fixed in §14.6 step 0: re-ask instead |
| Fan-in | `assembled_slide_plans: Annotated[list, operator.add]` ([state.py:145](../src/state.py:145)) → `slide_plan_sorter` | a re-planned slide would be **appended**, giving duplicates |
| `plan_reviewer` ([plan_reviewer.py](../src/agents/plan_reviewer.py)) | 1 LLM call; score + issues (5 types); [`route_after_plan_review`](../src/graph.py:158) always goes to `style_resolver` | a paid call per deck that changes nothing |
| API `/plan/*` ([api.py:642–794](../src/api.py:642)) | `/plan/outline` (elicitor + outline); `PUT /plan/{id}/outline` (edited outline → the graph skips the outline planner); `/plan/outline/regenerate-slide` (`outline_replanner`, whose prompt also says "derive a plausible number"); `/plan/review` (standalone reviewer) | human review at the outline already exists, with no checkpointer |
| `/plan/refine` ([api.py:762](../src/api.py:762)) | sets `prior_plan` and `refine_feedback`, then re-runs `outline_planner_node`, **which reads neither** (grep: no reader in `src/`) | the user's feedback is ignored and the outline is re-planned from scratch. The outline reviser below fixes this for free (§6, step 7) |
| Config | `SLIDE_PLANNER_MAX_PARALLEL` / `MAX_CONCURRENCY` declared but never applied; `recursion_limit` 150; LangGraph **0.6.11** (no `Overwrite`, which arrived in 1.x) | a keyed reducer is needed instead of resetting the list |

## 3. Evidence gathered this session (LLM-free)

**Replay of the checks on the old planner's plans.** The script is in the session scratchpad. It applies the per-slide rules of `src/planning/checks.check_slide` to `slide_plan` in `llm_test/gj-h1-regen-{69af33,7293ef,5a9e2d,bf396b}.zip`. Planning code is unchanged since those runs (`git log 77000c3..HEAD` on the planning files is empty).

| | 69af33 | 7293ef | 5a9e2d | bf396b |
|---|---|---|---|---|
| Slides flagged by the hard checks (numbers, capacity, units) | 9/14 | 8/14 | 10/14 | 9/14 |
| Slides that drop brief numbers | 9 | 7 | 9 | 9 |
| Headline lost (content slides) | 13/13 | 13/13 | 13/13 | 13/13 |

- **Same slides every run:**
  - drops on the dense slides (1, 3, 4, 5, 6, 10; slide 10 drops 13–20 numbers);
  - timeline labels over 4 words (slides 8, 12);
  - 7 KPI tiles on slide 5 (3 of 4 runs);
  - invented numbers in 2 runs;
  - more than 2 hints on 6–9 slides.
- **Where the losses start:** old runs don't save the outline, so a replay cannot tell whether the outline or the slide planner lost a number. The new runner must save `outline_plan`.

**Test 1 re-ask data** (`output/plans/test-1-final/`):

| Check | gj-h1 | CHEFFIN |
|---|---|---|
| Storyline check re-asked once | 6 of 6 runs | (included in the 6) |
| Issues left after the re-ask | 0 | 0 |
| Slides that needed ≥ 1 slide re-ask | 4–5 of 14 (19–20 design calls) | 1–3 of 6 |

**Where the old planner's CHEFFIN richness came from** (2.83 vs Test 1's 1.80 components per slide; `tables-check` CHEFFIN):

| Source | Example | Keep? |
|---|---|---|
| Pairing a structure with its detail | process_arrow + bullets + table | yes |
| An evidence chart per claim | actual vs allowable CPC | yes |
| A KPI strip next to the table | on the snapshot slide | yes |
| Invented content | the "City/Keyword 1–3" table | no (D2) |

Test 1's thin slides: a snapshot that is one table, a diagnosis that is bullets only, and a methodology slide of five lists. The reviewer's "thin for its purpose" item (§5.2 R4) and the intent floor (§7) target exactly these.

## 4. Approaches compared

Costs are for gpt-4.1 at list price (§8). "Fixes" columns:
- **fid** = fidelity (numbers, headlines copied);
- **sharp** = headline and sub-headline quality;
- **rich** = components per slide;
- **stab** = the same plan across runs.

| # | Approach | fid | sharp | rich | stab | Extra calls (14 slides) | Extra $ (14 / 20) | Main risk | LangGraph mechanics |
|---|---|---|---|---|---|---|---|---|---|
| F | **Fidelity fixes** in both planners (§6) | ●● | ● | ○ | ○ | 0 | +$0.02 / +$0.03 (blocks in prompts) | edits to a 6.8k-token prompt can shift routing | none (prompt + schema) |
| G | **Outline gate:** code check + ≤ 1 re-ask inside `outline_planner` | ●● | ● | ○ | ○ | +1 (6/6 runs in Test 1) | +$0.06 / +$0.07 | a retry comes back worse → keep the better one (Test 1 rule) | loop inside the node; no new edges |
| B | **In-branch slide check** + ≤ 1 re-ask, keep the better | ●● | ○ | ● (capacity) | ○ | +5–6 | +$0.17 / +$0.22 | the model doesn't comply (gj-h1 slide 1 in `f56a45`: 3 tries) → keep best, log it | loop inside `plan_single_slide` (Test 1's `design_slide`) |
| D | **Reviewer loop, code checks only** (deck-level: coverage, parallel groups, fact reuse, set-aside claims) | ● | ○ | ○ | ● | +1–2 re-plans | +$0.05 / +$0.07 | little | conditional edge → `Send` re-plans; keyed reducer |
| R | **Reviewer loop with an LLM checklist**, targeted patches, ≤ 2 fix rounds, keep best | ● | ●● | ●● | ○ | +1 review, +1 outline patch, +4–6 re-plans, +1–2 small re-reviews | +$0.25 / +$0.35 | inconsistent judge, over-criticism, pressure to invent, oscillation → mitigations in §5.4 | as D, plus an `outline_reviser` node and per-slide version history |
| W | Whole-plan evaluator–optimizer (regenerate all slides each round) | ● | ● | ● | ✗ | +15 per round | +$0.40 per round | regressions on good slides, drift, worse stability | reflection loop on the whole plan. **Reject** |
| S | **Code skeleton:** default components from content shape + intent; one skeleton per parallel group (§7) | ○ | ○ | ● | ●● | 0 | $0 | rules harden into templates (the 2026-09-10 regression) → it is a suggestion; the LLM may override it with a reason | code before the LLM call |
| H | Human at the outline via `interrupt()` | ●● | ●● | ● | ● | 0 | $0 | needs a checkpointer + thread ids; the API already does this statelessly | keep the API flow; show the outline check results with the outline |
| N | Best-of-N outlines (N = 3, pick by code score) | ● | ● | ○ | ✗ | +2 | +$0.10 / +$0.13 | a different winner every run | parallel `Send` × N → pick. **Defer** unless outline issues remain after G |
| M | Stronger model for outline + reviewer only (D10) | ○ | ●● (likely) | ● | ○ | 0 | +$0.1–0.3 (depends on the model) | cost; availability on the company key | `models.yaml` step change |

●● strong effect · ● some effect · ○ none · ✗ makes it worse.

**Recommendation: L = F + G + B + S + R** (D is part of R). H is kept through the existing API, not `interrupt()`. N stays in reserve. M is an optional extra arm in the paid run (Q3).

**How others check before rendering** (research; sources at the end):

| Who | How they check before rendering | Consequence for us |
|---|---|---|
| Gamma, Microsoft Copilot in PowerPoint | a human reviews and edits the outline before slides are made ("the outline is your last cheap edit"). No automated plan critic is documented | our API already has this step: show the outline checks there, and never overwrite a user's edits (Q6) |
| Genspark (our 2026-09-25 transcripts) | little review of the plan; a strong lint loop *after* rendering, with rules tiered by measured precision, one-element fixes, and re-checks only on changed slides | same shape at plan level: re-review only the changed slides; rules we have measured route, unmeasured ones only advise |
| PPTAgent (PPTEval) | an LLM judge scores Content and Design per slide and Coherence per deck (1–5 plus a rationale); self-correction uses execution feedback | our rubric splits the same way, slide items vs deck items |
| DeepPresenter | reflection on the rendered artifact beats reflection on the model's own reasoning | a vision critic after rendering is the next loop (M5), not this one |
| Huang et al. 2024; CRITIC | LLMs don't reliably self-correct without external feedback; with tool feedback they do | code checks are the external feedback; the LLM judge is only for what code cannot see, and code validates its claims |
| CheckEval | binary yes/no checklists give much better judge agreement than Likert scores | the rubric is a closed yes/no checklist that needs evidence, not a score |

## 5. The reviewer

### 5.1 Code checks

Deterministic, free, and run on every review. "Reuse" means it is already in [`src/planning/checks.py`](../src/planning/checks.py) and needs an adapter to the old plan format.

| Id | Check | Stage | Severity | Source |
|---|---|---|---|---|
| C1 | a brief number assigned to the slide is not shown | slide | high | reuse (`check_slide`) |
| C2 | a block with numbers is on no slide and not set aside | outline | high | reuse (`check_storyline`) |
| C3 | a "Mention… / Include…" block is on no slide | outline | high | reuse |
| C4 | a number that is not in the brief (plan, outline text, hints) | where it appears | high | reuse |
| C5 | capacity: > 6 KPI tiles, > 10 rows, > 6 bullets, step labels > 4 words, details on label-only kinds, mixed units on one chart, a chart with no series | slide | high | reuse |
| C6 | more than 2 emphasis items or hints on a slide | slide | medium | reuse |
| C7 | headline empty, a field label ("…:"), equal to the label, or a brief headline exists and was not used | outline | high | reuse (`apply_headline_blocks` copies it first) |
| C8 | slide count differs from the request | outline | high | reuse |
| C9 | a set-aside reason claims "included on slide N" but slide N doesn't list the block (7 false claims in one Test 1 run) | outline | high | new |
| C10 | no kicker label on a content slide | outline | medium | new (Q7) |
| C11 | a data slide whose sub-headline has no number from its blocks | outline | medium | new |
| C12 | the same KPI label with different values on two slides; the same table shown in full twice | outline | medium | new (partial: labels only, no fact store yet) |
| C13 | slides in one parallel group plan different component kinds | slide (outliers) | medium | new |
| C14 | below the intent's richness floor (§7), e.g. an executive summary without a KPI strip or a deep-dive without an evidence component | slide | medium | new |
| C15 | a narrative or bullet repeats the headline or sub-headline; a card body repeats its card title (added 2026-10-05, hold-out agency 4) | slide | medium | reuse + new |
| C16 | planner instructions or speaker notes written as slide content ("Deepen the growth story by showing…", hold-out QBR 3–4; notes planned as a narrative, agency 2, 4–6) | slide | high | new (2026-10-05; built in §14.6 step 0) |
| C17 | two components on one slide whose item labels overlap ≥ 70% (phase cards + chevrons of the same items, 1 Oct decks slide 4) → keep the hero, report the other | slide | medium | new (2026-10-05; design doc §5; built in §14.6 step 0) |

C14 also receives the renderer's `SLIDE_SPARSE` (content fills < ~55% of the body, design
doc §10f) once blocks are built; before that it is the plan-side estimate.

C1, C4 and C5 also run inside each slide branch (step B), so the reviewer usually finds them already fixed. It re-runs them because a revision can break them.

### 5.2 The LLM checklist

One call on review 1; the input is the brief as numbered blocks, the outline and the slide plans (≈ 19k tokens in on gj-h1). Later reviews see only the changed slides and the deck items.

The judge answers **yes / no per item, per slide**. Every "no" must quote its evidence from the plan and propose a fix. Items marked *brief wins* are skipped when the headline was copied from the brief.

| Id | Item | Scope | Stage | Severity on "no" |
|---|---|---|---|---|
| R1 | The headline states one claim, not a topic; it names the entity; ≤ ~14 words (*brief wins*) | slide | outline | high if it's a pure topic, else medium |
| R2 | The headline carries a tension or comparison ("X — but Y"; 5/15 ours vs 12/15 production on CHEFFIN) (*brief wins*) | slide | outline | medium |
| R3 | The sub-headline carries the evidence (2–4 key numbers from the slide's blocks), not a description of the slide | slide | outline | medium |
| R4 | The slide is rich enough for its purpose with the brief's own content (e.g. "executive summary without KPIs", "data slide that is only a paragraph", "recommendations without owner or timing") | slide | slide; outline if the fix needs blocks from other slides | medium |
| R5 | The components prove the headline: the focal component is the evidence | slide | slide | medium |
| R6 | No filler: a narrative doesn't restate the header or another slide | slide | slide | low → medium when it is the only component |
| R7 | Parallel slides tell parallel stories: same metrics, same order | deck | slide (outliers) | medium |
| R8 | A key fact isn't repeated across slides without a new angle | deck | outline | medium |
| R9 | The arc fits the deck type (audit: summary → snapshot → per-entity deep-dives → gaps with evidence + fix → approach → roadmap → ask) | deck | outline | low (advisory in v1, Q5) |
| R10 | Gaps are named where the brief refers to missing data; set-aside reasons are honest | deck | outline | medium |

Code decides the stage and severity from the item id, not the model. The one exception: when a fix names blocks outside the slide's `block_ids`, the issue becomes an outline issue.

### 5.3 Issue format and routing

```yaml
- id: R3                     # C… = code, R… = rubric
  slide: 4                   # 0-based; null = deck
  stage: outline             # outline | slide — set by code
  severity: medium           # high | medium | low — set by code
  source: llm                # code | llm
  evidence: "sub-headline 'Platform-wise performance snapshot' has no numbers"
  fix: "carry spend ₹29.4L, ROAS 0.34x and CPC ₹31.1 vs ₹10.7 allowable"
  blocks: [L41, L44]         # blocks the fix needs (optional)
```

`plan_review` keeps `confidence_score`, `approved`, `summary` and the old issue fields (`type`, `slide_index`, `description` = evidence, `suggestion` = fix) so that `/plan/review` and the frontend keep working.

**Routing** (`route_after_plan_review`, a pure function like `fan_out_slide_plans`):

```
review 1  (all slides: code + LLM)       → fix round 1: slides with high or medium issues
review 2  (changed slides + deck checks) → fix round 2: only slides still high   [skipped if none]
review 3  (only if round 2 ran)          → keep the best version of each slide → style_resolver
```

- **Nothing to fix, or the budget is used:** keep the best per slide, then go to `style_resolver`.
- **Outline issues:** `outline_reviser`, one LLM call. It gets the outline, the issues and the blocks, and returns patches for the named slides only. Code applies the patches, re-copies brief headlines, and re-runs C2–C11. A patch that makes the outline checks worse is dropped.
- **Re-plans:** the patched slides and the slides with slide issues are re-planned: `Send("slide_component_planner", {…, current_repair_context: {previous_plan, issues}})`. The in-branch check still applies.
- **Low issues** never route. They are logged, and shown in the UI with the outline.

### 5.4 Keeping the reviewer honest

| Risk | Guard |
|---|---|
| Inconsistent judge | closed yes/no checklist; temperature 0; evidence required; code drops a "no" whose quoted evidence is not in the plan. Measured once in the paid run (the same plan reviewed 3×, ≈ $0.16) |
| Over-criticism | only listed items; at most 3 routed issues per slide; medium issues route only in round 1; low issues never route |
| Pressure to invent | a fix that needs a number that is not in the brief is not routed; it becomes a named gap (D2). Derived numbers wait for D13 — *2026-10-05: D13 settled by the content policy (design doc §12): derived values are allowed once code computes them; until that code exists the rule above stands* |
| Oscillation / moving goalposts | round 2 raises no new items on slides that were not revised; each slide is re-planned at most 2 times |
| A revision makes a slide worse | **keep-best per slide**: versions compared by (code high, code medium, LLM high, LLM medium); a tie keeps the earlier version (stability). The outline slide and its plan are kept as a pair; slides whose patch moved blocks between them are kept or reverted together, so coverage (C2) holds |
| Runaway cost or latency | hard caps: 2 fix rounds, 1 in-branch re-ask, `max_concurrency` 6; every call is recorded in `generation_history` |

## 6. Fidelity fixes to the old planners (what Test 1 proved)

| # | Change | Where |
|---|---|---|
| F1 | The brief is indexed into numbered blocks by code (`brief_index.py`), and the outline planner reads the blocks instead of the raw text | `outline_planner.py`, `user.j2` |
| F2 | The outline slide gains `intent`, `label` (kicker), `headline_block`, `subtitle`, `block_ids`, `emphasis` (≤ 2), `parallel_group`. The deck gains `audience_and_use`, `gaps`, `style_directives`, `set_aside`, with reasoning fields first (schema order). `slide_title` becomes the headline (key kept for API and frontend; the ≤ 8-word limit goes). `key_messages` stay as *the points the slide makes*, not the data carrier | `outline_planner_schema.py`, `state.OutlineSlide` (additive) |
| F3 | Code copies the brief's headline verbatim when the outline points at one (`apply_headline_blocks`) | reuse |
| F4 | Never invent (D2): remove the invent instructions from the outline schema, the outline prompt and `outline_replanner`. Missing data → `gaps` | 3 prompt / schema spots. The generator's own invent lines (north-star §3.4) are a separate small change. *Done in planner batch A (2026-09-29). Refined 2026-10-04 by the content policy (design doc §12): "invented" stays forbidden, "inferred" qualitative lines are allowed and flagged* |
| F5 | The slide planner sees its blocks verbatim, plus the header that has already been decided (label / headline / subtitle, so it never writes its own title). Components can bind a parsed `[T#]` / `[C#]` block and code fills `content_data` from it (`fill_component`). `reading` comes first in `PlannerSlide` | `slide_component_planner.py`, `planner_schema.py`, `user.j2` |
| F6 | `design_hint` becomes optional: only for the slide's `emphasis` items, ≤ 2 per slide. The "mandatory" section is removed; the treatment list stays as reference | `system.j2`, `planner_schema.py` |
| F7 | The planned kicker reaches the slide: the title component carries `kicker` (the adapter already does this), and the generator uses it instead of deriving one ([generator/system.j2:102](../src/prompts/generator/system.j2:102)) | one line in the generator prompt |
| F8 | Temperature 0.3 → 0.1 for both planners (Test 1 used 0.1) | `models.yaml` |

The slide planner's rich guidance stays: the routing table, the structure + detail pairing, the visual fitness guide and the worked examples. Only references to "key_messages are the source of truth for data" change to "the blocks are". That guidance is why the old planner produced more components (D14).

## 7. Stability and richness: the code skeleton

> *Naming (2026-10-05): "skeleton" here = code-suggested components for the planner. It is
> unrelated to the XML skeleton with slots in `docs/derived-nodes-design.md` §14.6.*

Before each slide call, code proposes default components from the slide's blocks and intent. The LLM receives them as *"SUGGESTED COMPONENTS — keep them unless the slide's purpose needs otherwise; say why in `reading`"*.

| Content shape (code-detected) | Default |
|---|---|
| parsed table `[T#]` | `table`, bound to the block (code fills every cell) |
| parsed chart `[C#]` | `chart`, bound to the block |
| ≥ 3 short "label: value" lines | `kpi_row` (≤ 6 tiles; more → `table`) |
| steps whose detail is over 4 words (pillars, month-by-month actions) | `table` (not timeline / process_arrow) — the gj-h1 slide 12 and slide 11 failures |
| "Mention… / Include…" block | a read-out `narrative` |

| Intent (from F2) | Richness floor (C14; the LLM may exceed it, never invent for it) |
|---|---|
| executive_summary | KPI strip + read-out |
| deep_dive | KPI strip + ≥ 1 evidence component (table or chart) + read-out |
| comparison / gap | one component holding actual vs target (e.g. CPC vs allowable) |
| recommendation / roadmap | a table of actions with phase, owner or timing where the brief gives them |
| cover / section / closing | none |

- **Parallel groups:** every slide in a group gets the same skeleton, built from the first member's content shape. C13 re-plans outliers.
- **Why this should raise stability:** Test 1's unstable slides were exactly those with several valid forms (pillars as table / arrow / bullets, one card list vs three, timeline ± narrative). A code default removes most of that choice.
- **Risk to guard against:** the halted blueprints forced structure ("do NOT rearrange"). The skeleton only suggests, only from content shape, and never asks for decoration.

## 8. Cost per deck (gpt-4.1 list price: $2 / M in, $8 / M out; no cache discount)

| Step | Calls (14 slides) | 14 slides (gj-h1) | 20 slides | CHEFFIN (6) |
|---|---|---|---|---|
| Outline + gate re-ask | 2 | $0.10 | $0.13 | $0.04 |
| Slide plans (6.8k-token system prompt + blocks) | 14 | $0.35 | $0.50 | $0.13 |
| In-branch re-asks (~40% of slides) | ~6 | $0.17 | $0.22 | $0.07 |
| *Subtotal without the LLM reviewer (code-only loop)* | *~22* | *≈ $0.65* | *≈ $0.90* | *≈ $0.25* |
| Review 1 (≈ 19k in, 2k out) | 1 | $0.05 | $0.08 | $0.02 |
| Outline patch | 0–1 | $0.03 | $0.04 | $0.01 |
| Re-plans, rounds 1 + 2 (~4 + ~1.5 slides) | ~6 | $0.17 | $0.23 | $0.05 |
| Reviews 2–3 (changed slides only) | 1–2 | $0.04 | $0.05 | $0.02 |
| **Planning total** | **~30** | **≈ $0.9** | **≈ $1.3** | **≈ $0.35** |
| Today's planning (§8.1 of the north-star) | 17 | $0.44 | ≈ $0.62 | ≈ $0.18 |

- **What pays for what:**
  - the fidelity fixes and in-branch re-asks cost ≈ $0.2 per 14 slides;
  - the LLM reviewer loop costs ≈ $0.25.
- **Cache discount:** OpenAI's automatic prompt cache (75% off repeated prefixes on gpt-4.1) should hit the shared 6.8k-token slide-planner prompt on re-asks and re-plans. We don't record cached tokens (`unpack_raw`), so the real bill should come in lower than this table.
- **Latency:** about +1–2 minutes per deck, from two extra sync points and the reviewer's output.
- **Model change (2026-10-05 note):** since 2026-10-01 `outline_planner`, `slide_component_planner` and `plan_reviewer` run on gpt-5-mini with `reasoning_effort: medium` (`models.yaml`). Reasoning tokens are billed as output, so this table is not valid for them; re-estimate from a recorded run's `tokens_reasoning` before asking for the paid comparison.

## 9. Topology

```
START ─► elicitor ─► outline_planner
                       │  (inside the node: blocks → LLM → copy brief headlines → check C2–C11 → ≤ 1 re-ask, keep the better)
                       ▼
                 fan_out_slide_plans ── Send × N ─────────────────────────────┐
                                                                               ▼
                                              slide_component_planner   (per slide, in parallel, max_concurrency 6:
                                                                         skeleton → LLM → code fills [T#]/[C#]
                                                                         → check C1/C4/C5/C6/C15 → ≤ 1 re-ask, keep the better)
                                                                               │
                         fan-in: assembled_slide_plans, KEYED by slide_index   │  (a re-plan replaces its slide, no duplicate)
                                                                               ▼
                                                                      slide_plan_sorter
                                                                               ▼
                                   ┌──────────────────────────────────── plan_reviewer ◄───────────────────────┐
                                   │   code checks C1–C15 + LLM checklist R1–R10 (review 1: all; later: changed) │
                                   │   records a version per slide; round += 1                                   │
                                   │                                                                             │
          route_after_plan_review ─┼─ nothing to fix / budget used ──► keep best per slide ──► style_resolver ─► … (unchanged)
                                   │                                                                             │
                                   ├─ outline issues ──► outline_reviser (1 LLM call, named slides only) ──┐    │
                                   │                                                                        ▼    │
                                   └─ slide issues ───────────────────────────► Send × flagged slides (repair_context)
                                                                                  → slide_component_planner → sorter
```

**LangGraph details:**
- `route_after_plan_review` and the edge after `outline_reviser` return `"style_resolver" | "outline_reviser" | list[Send]`. These are conditional edges in the same style as `fan_out_slide_plans`, so they stay pure functions and are easy to unit-test (`test_graph.py`). `Command(goto=[Send…], update=…)` from the reviewer would work too; conditional edges match the codebase.
- **Keyed reducer:**
  ```python
  def merge_by_slide(old, new):
      by = {p["slide_index"]: p for p in old or []}
      by.update({p["slide_index"]: p for p in new or []})
      return [by[i] for i in sorted(by)]
  ```
  It works on 0.6.11 and needs no `Overwrite`. Test 1 used the same idea (`designs` merged by index).
- **New state keys (additive, JSON-safe):**
  - `current_repair_context`: declared like `current_outline_slide`, so the contract is explicit (Send payloads are not filtered: Test 1's `design_slide` reads keys that are not in its state);
  - `plan_review_round`;
  - `plan_versions`: written only by `plan_reviewer`, so it needs no reducer;
  - `brief_index`.
- **Existing paths:**
  - serial mode (`SLIDE_PLANNER_SERIALIZE`) affects only the first fan-out; re-plans always use `Send`;
  - user-edited outlines skip the outline gate, and their outline issues are advisory only (Q6).
- **Config:** `max_concurrency: 6` is added to the invoke config in `graph.run`, the API and the runner. The recursion budget grows by ~8 steps, well within 150.

## 10. Build steps and test plan

Each step is verified LLM-free before the next. Unit tests use a scripted LLM (a fake `get_llm` returning canned JSON per step, as in the Test 1 dry run).

| # | Step | LLM-free verification |
|---|---|---|
| 1 | Reuse `brief_index.py`, `checks.py` and `fill_component` from `src/planning/`, plus a small adapter to the old plan format (nothing moved or deleted) | the replay in §3 as a unit test: the old gj-h1 plans flag the same slides |
| 2 | Outline fidelity (F1–F4, F8) + the outline gate (G) inside `outline_planner_node`; `outline_replanner` loses the invent line | schema tests; scripted LLM: a planted topic headline / missing block / invented number → one re-ask → fixed; a worse retry → the first is kept |
| 3 | Slide planner fidelity (F5–F7) + in-branch check (B) + skeleton (S) | tests per skeleton rule; print the skeletons for every slide of gj-h1 and CHEFFIN and read them; scripted LLM: 7 KPIs → re-ask |
| 4 | Reviewer: code checks C1–C15, checklist schema + prompt, issue mapping, `route_after_plan_review`, `outline_reviser`, keyed reducer, versions + keep-best, round caps, `plan_review` compatibility | routing tests (no issues / outline / slide / budget); reducer test (re-plan → no duplicate); keep-best and anti-oscillation tests; a full scripted planning run on the real gj-h1 and CHEFFIN briefs with planted defects: exactly the planted slides are re-planned, ≤ 2 rounds, final plans pass the code checks |
| 5 | Planning-only runner for the main graph: `scripts/plan_only.py --path main` (a planning graph built from the same nodes that ends after the reviewer). It writes `slides.json` (plan + outline slide + every review round), `outline.md` (to judge headlines), `run-manifest.json`. Scorer additions: components per slide, slides with ≤ 1 component, kicker rate, sub-headline-with-number rate, and per round: issues, re-plans, regressions, cost | `--rescore` on saved runs; old gj-h1 runs and `test-1-final` score as before |
| 6 | Render the reviewer prompt on saved plans and count tokens (tiktoken) | cost table in §8 confirmed before any paid run |
| 7 | API: `/plan/outline` runs the gate and returns the outline issues; `/plan/refine` uses `outline_reviser` with the user's feedback as the issue (fixes the bug in §2); `/plan/review` returns the new format (old fields kept); user-edited slides locked | API tests with a scripted LLM; the frontend is untouched (fields are additive) |

**Paid comparison** (after steps 1–6; one run; ask first).

| Arm | Source | Cost |
|---|---|---|
| **A** old planner | gj-h1: the 4 saved runs, reusable (planning unchanged). CHEFFIN: the saved run has no `content_data` → optional 3 planning-only runs | $0 (+ ≈ $0.55 for CHEFFIN) |
| **B** old + fixes + loop | gj-h1 × 3 + CHEFFIN-audit × 3 | ≈ $3.6 |
| **C** Test 1 path | `test-1-final` (6 runs, same code), reusable | $0 |
| B′ (optional, D10) | B with a stronger model on the outline + reviewer steps, gj-h1 × 1 + CHEFFIN × 1 | ≈ $1.4 + model premium |
| Judge consistency | the reviewer run 3× on one saved plan | ≈ $0.16 |

**Proposed pass criteria for B** (fixed before running, Q4):

| Case | Criteria |
|---|---|
| gj-h1 | headlines ≥ 12/13; numbers dropped ≤ 2% (mean); 0 invented; ≤ 2 hints per slide; same components on ≥ 10/14 slides; ≥ 2.8 components per slide (old 3.04) |
| CHEFFIN | plan checks 3/3; 0 invented; ≥ 2.5 components per slide (old 2.83 incl. invented; Test 1 1.80); a kicker on every content slide; ≥ 80% of data slides with numbers in the sub-headline |
| Loop | ≤ 2 fix rounds; no kept regression; judge agreement ≥ 80% of items across the 3 runs; planning ≤ $1.0 per gj-h1 deck |
| User | headline sharpness judged from `outline.md` against the production CHEFFIN deck |

## 11. Decisions for you

1. **Layered loop (recommended) or everything inside `plan_reviewer`?**
   - Layered: the code checks sit where problems are born, and the reviewer handles judgment and the deck.
   - All-in-reviewer: one loop, but round 1 would re-plan most slides, based on the replay in §3.
2. **The LLM checklist call** (≈ +$0.25 per 14 slides, +$0.35 per 20): on by default, or a setting `review: code | full` with code-only as the default? *Recommendation: on for decks of ≥ 6 slides, off for single slides.*
3. **Paid comparison budget.** Arms A and C are free (reuse). Arm B as specified is ≈ $3.6. Choose:
   - (a) as specified;
   - (b) staged: a smoke run B × 1 per case + judge consistency ≈ $1.4, then the remaining repeats ≈ $2.4 only if it's clean;
   - (c) × 2 repeats ≈ $2.4.
   - Also: add B′ (stronger model, D10)? If so, which model does the company key allow?
4. **Pass criteria** in §10: accept or adjust.
5. **Story-arc issues (R9):** advisory only in v1 (no reordering), or may the reviser reorder slides? *Recommendation: advisory.*
6. **User-edited outline slides:** locked. The reviewer only advises on the outline and still re-plans slides. Confirm.
7. **Kicker on every content slide** (C10, F7): the planner decides it, from the brief or its section, and the generator stops inventing one. North-star §11 dropped the *generator's* mandatory kicker; this makes it a planned field instead. Confirm.
8. **Derived numbers (D13)** are the biggest richness lever for thin briefs (CHEFFIN's "2.9×", ACOS). They stay out of this build: the reviewer routes such fixes to "gaps" for now. Confirm.
   *2026-10-05: the principle is decided (content policy, design doc §12: derived values allowed, computed by code, marked). What remains open is only timing: the derivation code (ratio, difference, share, rank, count, range split + provenance tag) is step 4 or later of §14.6, so until then the reviewer still routes such fixes to "gaps".*

Test 1 code that only serves its own path (`src/planning/graph.py`, `schemas.py`, the `storyline/` and `slide_designer/` prompts, their `models.yaml` steps) stays until arm C is no longer needed. I'll ask before deleting any of it.

## Sources

- LangGraph: [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) (evaluator–optimizer, orchestrator–worker with `Send`), [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) (`Command`, `Send`, reducers, `Overwrite` in 1.x). Installed version checked locally: 0.6.11.
- Gamma outline step: [Gamma guide](https://gamma.app/explore/content/guides/how-do-i-turn-my-outline-into-a-deck-using-ai), [MindStudio tutorial](https://www.mindstudio.ai/blog/how-to-use-gamma-ai-build-presentations-tutorial). Copilot: [Create a new presentation with Copilot in PowerPoint](https://support.microsoft.com/en-us/office/create-a-new-presentation-with-copilot-in-powerpoint-3222ee03-f5a4-4d27-8642-9c387ab4854d).
- [PPTAgent / PPTEval](https://arxiv.org/abs/2501.03936) · [DeepPresenter](https://arxiv.org/abs/2602.22839) · [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) · [CRITIC](https://arxiv.org/abs/2305.11738) · [CheckEval](https://aclanthology.org/2025.emnlp-main.796/).
- Genspark: the user's transcripts, analysed 2026-09-25 (session memory; not in the repo).
