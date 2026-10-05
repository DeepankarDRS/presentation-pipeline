# Session kickoff — build here, test there, results by email (§14.6 build)

Updated 2026-10-05 for the build route the user chose: `docs/derived-nodes-design.md` §14.6
(the generator LLM writes each slide's layout with slots, code blocks draw the components
inside them from the plan, a measured checking loop, planner fixes first). The earlier
roadmap phases 0–4 (`docs/roadmap-derived-components.md`) are history; their eval tooling
(`scripts/eval_*.py`) is still used.

- **Build device (this PC, no OpenAI key):** ALL code, docs and commits happen here. Every
  step is proven LLM-free first (unit tests, compiler, LibreOffice renders, replays of saved
  runs).
- **Test device (company PC, has `OPENAI_API_KEY`):** only *runs* commands on a pulled
  checkout. It never commits or pushes (company policy). It runs **Python 3.11.9** in a pip
  venv (`senv\Scripts\activate`, `requirements.txt`), not uv; code must parse on 3.11
  (`tests/unit/test_py311_syntax.py`).
- **Channel back:** the user emails the eval bundle (and anything else requested) to the
  build device; the build session imports it and commits the summary.
- One Claude/Cursor session per step on the build device. Branch: **`feat/derived-blocks`** (created
  2026-10-06 from `test-1-planning` at `2e5f0ab`; all §14.6 work goes here, `test-1-planning` stays as
  the record up to the plan).

---

## 1. Prompts for the BUILD device

### 1a. Planning session (next session, before any code)

```text
Planning session for the derived design (docs/derived-nodes-design.md §14.6). No code yet: we plan and settle
the open items, then I approve before anything is built. Work on branch feat/derived-blocks (already created
and pushed): git fetch, git checkout feat/derived-blocks, git pull, and confirm the branch before anything else.

Read first: AGENTS.md ("Where work stands"), docs/session-kickoff.md, docs/derived-nodes-design.md (the
"Current plan" box at the top, then §14.4–14.7 and the LLM calls / tokens subsection),
docs/plan-reviewer-loop.md (2026-10-05 note), docs/planner-redesign-research.md §9.2–9.3,
docs/eval/genspark-variants/summary.md (variant shortlist per block; learnings in §14.8).
Decided, don't reopen: §14.6 route; Q15 = planner batch B after step 3 (planner 3 parked in §9.3);
step 3 runs from step 0's saved plans, slots arm only; CHEFFIN stays in.

Goals for this session, in order:
1. Step 0 plan: file list and order for the planner fixes (empty-plan re-ask in both except branches of
   slide_component_planner.py, instruction / notes text, card body = title, SLIDE_SPARSE, C17 duplicates),
   usage logging (step name, slide index, tokens_reasoning, tokens_cached in run-manifest steps; also copy
   run-manifest.json into the eval bundle's decks/<case>__rN/), subset font embedding in pptx-post.js,
   shrink guard; acceptance checks; the step-end paid run (6 cases, ≈ $1.8) and what the test PC must
   send back. Also: should gj-h1-regen (14 slides) join that run as the long-brief case?
2. Draft for my approval: (a) the slot contract (one syntax, attributes the LLM may set incl. the variant
   names from the Genspark shortlist, prompt line per kind, error codes); (b) the 1a protocol (exact slides, variety metric definition, blind side-by-side
   sheet, scoring scripts, from-plans runner, token comparison vs step 0).
3. Open questions to settle or schedule: theme colours / fonts — one source for blocks (style_packs.yaml)
   and the LLM skeleton (palettes.yaml via <Theme>); the checking-loop spec (triggers, code vs LLM fixes,
   best-version score, cost per round, how it relates to critic / visual_repairer); #4 label tier ≥ 10 px
   (I still have to view a projected deck); when blocks: slots becomes the default.

Rules: record the unit-test baseline before any change (last known 557 pass / 4 known failures); code must
parse on Python 3.11 (test PC); verify LLM-free on this PC; ask before any paid run with cases + cost;
write decisions into the docs with dates; one topic at a time, recommend rather than list options.
```

### 1b. Build session (one per step; change the step)

```text
Build §14.6 step <0 | 1a | 1 | 2> of docs/derived-nodes-design.md on branch feat/derived-blocks.
Read first: AGENTS.md, docs/session-kickoff.md, docs/derived-nodes-design.md ("Current plan" box, §14.6
and the specs approved for this step). This device has NO OpenAI key and is the ONLY device that commits.

Before coding:
1. git pull; record the unit-test baseline (pytest tests/unit -q; last known 557 pass / 4 known failures).
2. Summarise the step, its acceptance checks and any open point with your recommendation; show me a plan
   and the file list. Do not edit until I approve.

While working: verify LLM-free (unit tests, node src/node/compile-pom.js, python -m scripts.render_check,
replays of saved plans / XML, LibreOffice renders); code must parse on Python 3.11; follow the cost rule in
§5. End the step with: tests vs baseline, the step's status written into §14.6 with the date, commit, push,
and the exact test-device commands plus the list of files to email back.
```

## 2. What to run on the TEST device (copy-paste, no session needed)

```bash
git pull
git checkout feat/derived-blocks
senv\Scripts\activate
pip install -r requirements.txt
npm install --prefix src/node
```

Then the run for the step (the build session gives the exact command; these are the planned ones):

| Step | Command | Email back |
|---|---|---|
| **0 (step-end run, ≈ $1.8)** | `python -m scripts.eval_run deck-qbr-data deck-product-launch-data gate-deck-agency-takeover gate-deck-xtsy-qcomm gate-deck-cheffin-full gate-deck-all-nodes-dense --repeat 1 --label step0 --compose --bundle` | the bundle zip it prints (`decks/<case>__r1/` holds `llm.pptx`, `composed.pptx`, `slides.json`). Until step 0 adds `run-manifest.json` to `decks/`, also zip the six `output/runs/<run_id>/` folders: step 1a and step 3 reuse these plans, and the token analysis needs the manifests |
| **1a slot test (≈ $0.5)** | from-plans runner, generator only, on step 0's saved plans (command written in step 1a) | its output folder (skeleton XML per slide, run manifests) |
| **3 paid check (≈ $1.2–1.5)** | from-plans runner, `blocks: slots`, all six cases on step 0's plans (command written in step 2) | bundle + run folders |

On the build device: `python -m scripts.eval_import <zip>` → `docs/eval/<label>/` (LibreOffice
renders), then compare with the earlier label (`python -m scripts.eval_compare docs/eval/<a> docs/eval/<b>`).
Only if the build session asks: a LangSmith run export (JSON) for specific cases, or a specific `.pptx`.

**Data policy:** eval cases in `tests/cases/` are synthetic. Before emailing, make sure nothing in
the bundle is client data your policy forbids sending; the bundle contains slide text and numbers
from the prompts that were run.

## 3. Step-by-step split (§14.6)

| Step | Build device | Test device runs | Email back → build device |
|---|---|---|---|
| **0 Planner fixes + prerequisites** | empty-plan re-ask; instruction / notes text and card body = title rejected; `SLIDE_SPARSE`; duplicate items (C17); usage logging (step names, slide index, reasoning + cached tokens; `run-manifest.json` in the bundle); subset font embedding in `pptx-post.js`; shrink guard | the step-end run (§2) | bundle + run folders → `docs/eval/step0/`; its plans become the input of 1a and step 3; its `llm.pptx` decks are step 3's `off` arm |
| **1a Slot test (gate)** | from-plans runner; slot prompt; expansion with `scripts/phase0b/expand.py`; scoring (kill criteria §14.5, tokens vs step 0) | generator-only run (§2) | skeletons → scored here. **Fail → stop slots; composer + planner `arrangement` field (§14.1 option 2)** |
| **1 Blocks into the pipeline** | `src/compiler/blocks/` from `scripts/phase0b/`; hold-out failures fixed; slot expansion in the validator behind `blocks: off \| slots`; `SlideHeader`; attribute check vs pom-jsx `types.ts` + `attributes.yaml` | nothing | — |
| **2 Generator + checking loop** | skeleton prompt (only under `blocks: slots`); checking loop ≤ 2 rounds; repair / edit on the skeleton; scripted-LLM dry run of step 3 | nothing | — |
| **3 Paid check** | scoring, side-by-side sheets, token report | slots arm on step 0's plans (§2) | bundle + run folders → user's review |
| **4 Breadth** | remaining blocks (matrix, pyramid, tree, layer, branching flow); plan reviewer loop; §12 content policy | step-end run | as above |
| **Then: planner 3** | the parked redesign (`docs/planner-redesign-research.md` §9.3), its own project | its own comparison | — |

Specs that must be approved before their step: slot contract + 1a protocol (before 1a), theme ↔
style-pack source and the #4 label tier (before step 1), checking-loop spec (before step 2).

## 4. Rules

- **Build device always `git pull` first.**
- **Commit summaries, not raw output.** `eval_import` writes `docs/eval/<label>/summary.md` + ≤ 15
  review PNGs; raw bundles and run folders stay in `output/` (gitignored). Back up run folders
  that later steps reuse.
- **Baseline before change**, same case set, same `models.yaml`.
- **Record every decision** in the doc that owns it (§14.4 of the design doc, §10 of the planner
  research doc) with the date, and a row in `docs/architecture-north-star.md` §14 per session.

## 5. Cost rule (paid LLM runs — user, 2026-09-24; figures updated 2026-10-05)

Paid runs are budget-limited. Measured: the 2026-10-05 hold-out run (3 decks, 17 slides,
gpt-5-mini planners + gpt-4.1 generator) cost **$0.78**, ≈ $0.05 per slide; the generator is
≈ 69% of the cost, mostly its input (~12k tokens per slide). Earlier, with gpt-4.1 planners, a
14-slide deck (`gj-h1-regen`) cost ≈ $1.0–1.2; a single-slide case ≈ $0.03–0.06. §14.6 plans
three paid runs before the go / no-go: step 0 ≈ $1.8, 1a ≈ $0.5, step 3 ≈ $1.2–1.5 (≈ $3.5–3.8).

1. **Free first.** Anything that acts after the LLM (blocks, expansion, fit-grow, normalizer,
   compiler, fonts, eval metrics) is verified by replaying saved plans or XML —
   `python -m scripts.eval_run --fixtures <dir>`, `scripts/phase0b/replay.py`, `compose_deck.py`
   — plus unit tests and LibreOffice renders. No paid run for these.
2. **Planner changes** are tested first on saved plans (`output/runs/<run_id>/slides.json` holds
   each slide's `slide_plan`) and with a scripted LLM before any paid run.
3. **One paid run per step**, only when the step is ready for acceptance — never one per fix.
4. **Smallest case set that answers the question;** reuse saved plans (the from-plans runner)
   instead of re-planning when only generation changes.
5. **Never re-run a case whose result is already usable.** Check `docs/eval/*/` and the saved run
   folders first. A crashed eval is re-scored LLM-free from its run folder, not re-run.
6. **Ask before every paid run** with the case list and an estimated cost; state which cases are
   already covered.
7. Keep `models.yaml` fixed for comparable evals (a cheaper model is fine for smoke tests, never
   for acceptance).
