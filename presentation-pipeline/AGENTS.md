# AGENTS.md — context for Cursor / any coding agent

Prompt → LangGraph pipeline → LLM writes POM XML → Node.js compiler (`@hirokisakabe/pom` v10.3.0) → `.pptx`.

## Read first
- `ARCHITECTURE.md` — system overview, graph nodes, compiler bridge
- `CODE_FLOW.md` — which function runs when, which `PresentationState` keys change
- `llm.md` — POM's own XML reference (upstream). Audit source for our knowledge YAML, NOT a prompt: pasting it in lost to selective context (2026-09-02). `tests/unit/test_upstream_reference.py` compiles every example in it.
- `.cursor/rules/` — project memory carried over from Claude Code (working style is always applied; the rest load when relevant)

## Setup on a new machine
Needs Python ≥3.11, Node.js, and (optional) LibreOffice for rendering slides to images.
The git repo root is the folder ABOVE this one; open `presentation-pipeline/` itself in Cursor.

**Windows:** the repo tracks `graphify-out/cache/` files with very long names — clone into a short path (e.g. `C:\dev`) and enable long paths first, or checkout fails with "Filename too long":

```bash
git config --global core.longpaths true
git clone -b feat/golden-reference-grounding https://github.com/DeepankarDRS/presentation-pipeline.git
cd presentation-pipeline/presentation-pipeline
uv sync                               # installs deps + dev group (pytest etc.); or: pip install -e ".[dev]" lxml
cp .env.example .env                  # then put your real OPENAI_API_KEY in .env
npm install --prefix src/node         # POM compiler
npm install --prefix frontend         # Angular UI (only if you use the web UI)
```

`.env` is gitignored — it never travels with the repo; create it on every machine.
Models per pipeline step (all OpenAI, mostly `gpt-4.1`) are set in `models.yaml`.

## Testing outputs (with OPENAI_API_KEY)
All run from `presentation-pipeline/`. Every run writes to `output/runs/<run_id>/` (input XML, `compile-result.json`, `presentation.pptx`; multi-slide runs use `slide-N/` and `retry-N/` subfolders). `output/` is gitignored.

| Goal | Command |
|---|---|
| One prompt, end to end | `python -m src.graph "Create a 3-slide Q2 performance deck for ..."` — prints `pptx_path`, pass/fail, retries, evaluation |
| Regression cases (fixed prompts in `tests/cases/*.yaml`) | `python -m src.runner` (all) or `python -m src.runner base-revenue-trend base-risks` — prints pass/retries/tokens/cost table |
| Cases with a theme / critic on | `python -m src.runner --theme corporate-slate --critic-mode auto` |
| Web UI | `python -m src.api` (port 8000) + `npm run start --prefix frontend` (port 4200) |
| Re-render XML without the API | `python -m scripts.render_check --in <dir-of-xml> --out output/render_check` (compile + layout audit + summary.md) |
| Unit tests (LLM + compiler mocked, no key) | `pytest tests/unit -q` |
| Score a folder of POM XML without the API (fill, table spill, empty cells, ...) | `python -m scripts.eval_run --fixtures <dir-of-xml> --label <label>` |
| Paid eval, bundle for email (test device) | `python -m scripts.eval_run gj-h1-regen --repeat 1 --label <label> --bundle` (no case names = the 12-case gate) |
| Where a deck loses the brief's headlines / numbers (saved runs, no API) | `python -m scripts.eval_lineage <run zips> --case tests/cases/<case>.yaml` (north-star Appendix C) |
| Planning-only runs of the Test 1 path + scoring (paid; `--rescore` is free) | `python -m scripts.plan_only <cases> --repeat 1 --label <label> --bundle` |

Known pre-existing unit-test failures on a clean `uv sync` (verified 2026-09-27: 464 pass, 4 fail — not regressions):
`test_critic.py::test_critic_medium_only_passes`, `test_layout_audit.py::test_font_at_minimum_ok`, and two routing tests in `test_graph.py` (`*_budget_exhausted*`: expect `evaluator`/`slide_router`, code now routes to `visual_repairer` — tests or routing are stale).
Always record your own baseline (`pytest tests/unit -q`) before a change and compare against it.

When judging slide quality, open the `.pptx` (or render via LibreOffice, see `.cursor/rules/offline-render-loop.mdc`) — don't trust pass/fail alone.

## Design hints, nesting and icons (implemented 2026-09-23)
Read `docs/design-hint-architecture.md` before touching prompts, knowledge YAML or the normalizer. Core nodes (Table/Td, Ul/Li, Text, Chart, ...) have fixed syntax; enrichment is composed AROUND them in VStack/HStack. Rules live as data: `nodes.yaml` (nesting), `core/hint-capabilities.yaml` (what a design_hint may ask per component kind), `core/icon-names.txt` (valid icons). Cursor rule: `.cursor/rules/pom-nesting-content-model.mdc`.

To check it live (needs OPENAI_API_KEY): generate a table-heavy slide, e.g.
`python -m src.graph "One data slide: ROAS by platform for Flipkart 0.34x and Zomato 0.32x, highlight the worst performer"`
then check the run's XML in `output/runs/<run_id>/`: no HStack/Icon inside `<Td>`, planner hint drawn from table treatments (color, shading, header icon), and normalize issues in the log (`TEXT_CONTAINER_FLATTENED`, `UNKNOWN_ICON_REMOVED`) should be rare.

## Next work (updated 2026-09-27) — PAUSED, waiting for the user to kick off
**Direction (user, 2026-09-27):** keep the existing planners — `outline_planner` + `slide_component_planner` — and make `plan_reviewer` a real feedback loop. The new planning path from Test 1 (`src/planning/`: storyline + slide designer) is **not** taken to production: its slides had too few components on thin briefs (CHEFFIN: 1.8 per slide vs 2.83 for the old planner; gj-h1 equal at 3.04).

Proposed build (not started; confirm with the user first):
1. Carry Test 1's fidelity fixes into the old planners: `slide_component_planner` gets the brief's own lines for its slide (not the outline's retyped `key_messages`); the outline splits label / headline and copies the brief's headlines; never invent numbers (D2); `design_hint` optional.
2. `plan_reviewer` = code checks (coverage, invented numbers, capacity — reuse `src/planning/checks.py`) + an LLM rubric (headline sharpness, evidence in the sub-headline, slides too thin for their purpose, fact reuse, parallel slides consistent, story arc). Issues tagged by slide and stage → outline issues patch the named outline slides, slide issues re-plan only those slides (`plan_single_slide(repair_context=…)`); ≤ 2 rounds, keep the best version. Today `route_after_plan_review` ignores the review.
3. Fan-in `assembled_slide_plans` (`operator.add`) becomes a merge keyed by slide index, or re-planned slides duplicate.
4. A planning-only runner for the main graph, scored with the Test 1 scorer (`scripts/eval_lineage.py`, `scripts/plan_only.py`).
5. One paid comparison: old / old + fixes + loop / new, on gj-h1 × 3 + CHEFFIN-audit × 3 (≈ $2).

**Test 1 (done, passed 2026-09-27, user; stability carried forward)** — `docs/eval/test-1/`, `docs/architecture-north-star.md` §9. What it proved: pointers to the brief + code checks give headlines 0/13 → 13/13 (gj-h1), numbers dropped 7–13% → 1.0%, invented numbers → 0 (11 runs), design hints ≤ 2. Weak: plan stability 8/14, sparse slides on thin briefs, generic headlines vs the production deck (tension 5/15 vs 12/15, descriptive sub-headlines, no kickers).
**Tests 2 and 3: dropped** with the direction change (they tested the new path). Component tags and element-level editing remain ideas, not gates.
Open decisions: D12 (targets / projections), D13 (derived numbers such as ACOS or "2.9×"), the storyline/plan reviewer's extra call, data-file input (CSV / XLSX) — the production CHEFFIN deck (gj-h1 template, local only in `llm_test/`) got ~60% of its content from data files.

Background: `docs/architecture-north-star.md` (evidence audit, decisions, session log §14 — add a row per session). `docs/roadmap-derived-components.md` is halted (2026-09-24), kept as history. The two-device workflow and paid-run cost rule in `docs/session-kickoff.md` still apply.

## Where work stands (2026-09-27)
- **Branch `test-1-planning`** (pushed, based on `feat/golden-reference-grounding`, **not merged**): Test 1 code + docs. `feat/golden-reference-grounding` holds all earlier work; `master` is 60+ commits behind — do not run from `master`.
- **Test 1 code** (keep until the useful parts are ported; then remove what is unused — ask the user): `src/planning/` (brief index, checks, adapter reusable; `graph.py`, `schemas.py` and prompts `src/prompts/storyline/`, `slide_designer/` only serve the new path), `scripts/plan_only.py`, `tests/unit/test_planning_v2.py`, case `gate-deck-cheffin-full`. `models.yaml` has steps `storyline`, `slide_designer`.
- **Unit tests** 464 pass, 4 pre-existing failures (listed above).
- **Render layer (done 2026-09-24, still in the code):** eval harness (`scripts/eval_*.py`), deterministic normalizer fixes, table sizing in `src/node/fit-grow.js`, pptx post-process (`src/node/pptx-post.js`, falls back to POM's pptx with `PPTX_POST_SKIPPED`). Evals in `docs/eval/` (baseline, phase-1, phase-5-tables, tables-check, test-1). Still open: over-full slides hide table rows; 0 cell margins (user: leave); tables drawn in Aptos while fit-grow measures Noto Sans JP; crushed KPI tiles; long timeline labels. Details: roadmap Phase 5 Step 3.
- **`llm_test/` is gitignored and untracked** (2026-09-27): local run zips (the only source for LLM-free replays — back them up), the production CHEFFIN deck (real client names — never push), old slide dumps. Keep results worth sharing as text in `docs/eval/`.
- `pymupdf` is installed on the build PC only (`uv pip install pymupdf`, removed by `uv sync`) to render decks: `soffice --convert-to pdf`, then pymupdf to PNG.
- `production-plan.mdc` says "no archetypes" (2026-09-03) but `d2b75b6` added a layout archetype system — the newer commit reflects the current direction; confirm with the user if it matters.
- Memory rules mentioning `presentation-mvp/` refer to the older sibling MVP folder, not this repo.
