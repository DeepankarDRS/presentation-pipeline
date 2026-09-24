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

Known pre-existing unit-test failures on a clean `uv sync` (verified 2026-09-24: 424 pass, 4 fail — not regressions):
`test_critic.py::test_critic_medium_only_passes`, `test_layout_audit.py::test_font_at_minimum_ok`, and two routing tests in `test_graph.py` (`*_budget_exhausted*`: expect `evaluator`/`slide_router`, code now routes to `visual_repairer` — tests or routing are stale).
Always record your own baseline (`pytest tests/unit -q`) before a change and compare against it.

When judging slide quality, open the `.pptx` (or render via LibreOffice, see `.cursor/rules/offline-render-loop.mdc`) — don't trust pass/fail alone.

## Design hints, nesting and icons (implemented 2026-09-23)
Read `docs/design-hint-architecture.md` before touching prompts, knowledge YAML or the normalizer. Core nodes (Table/Td, Ul/Li, Text, Chart, ...) have fixed syntax; enrichment is composed AROUND them in VStack/HStack. Rules live as data: `nodes.yaml` (nesting), `core/hint-capabilities.yaml` (what a design_hint may ask per component kind), `core/icon-names.txt` (valid icons). Cursor rule: `.cursor/rules/pom-nesting-content-model.mdc`.

To check it live (needs OPENAI_API_KEY): generate a table-heavy slide, e.g.
`python -m src.graph "One data slide: ROAS by platform for Flipkart 0.34x and Zomato 0.32x, highlight the worst performer"`
then check the run's XML in `output/runs/<run_id>/`: no HStack/Icon inside `<Td>`, planner hint drawn from table treatments (color, shading, header icon), and normalize issues in the log (`TEXT_CONTAINER_FLATTENED`, `UNKNOWN_ICON_REMOVED`) should be rare.

## Next work: `docs/roadmap-derived-components.md`
How to run it across two devices (ALL building + commits on this PC; the company test PC only runs evals and results come back by email), with copy-paste session prompts: `docs/session-kickoff.md`.
Phase 0 quality baseline (needs OPENAI_API_KEY) -> 1 sizing grammar (grow/minH instead of pixel budgets; from docs/layout-sizing-plan.md) -> 2 planner fixes + measured routing + table placement (revised 2026-09-24: code annotates, the LLM decides; no data-shape remap) -> 3 real font metrics -> 4 derived nodes (KpiTile/TableCard/IconList) -> 5 remaining derived nodes + computed table/diagram sizing -> 6 measured critic loop. Each phase lists its files, tests, acceptance criteria and the decisions (marked DECIDE) to confirm with the user first.

## Where work stands (2026-09-24)
- **Phase 0 done**: eval harness (`scripts/eval_run.py`, `eval_import.py`, `eval_compare.py`, `eval_metrics.py`), baseline in `docs/eval/baseline/` (tag `eval-baseline`: `gj-h1-regen` × 1 — first-pass 50%, 2 lost slides, golden match 0.38), golden target in `docs/eval/golden-gj-h1/`. Deterministic normalizer fixes merged (replay: first-pass 7/14 → 14/14). Details + findings: roadmap Phase 0 section.
- **Phase 1 merged** 2026-09-24 (grow/minH grammar, blueprints + golden examples rewritten, audit rule, `tests/fixtures/layout_sizing/`). Eval `docs/eval/phase-1/`: first-pass 92.9%, overflows 0, golden match 0.475, fill flat (+0.007); weak spot = tables (hero tables grow their card; 40 px rows spill wrapped text).
- **Phase 5 Step 3 merged** 2026-09-24 (`phase-5-table-sizing`, pulled forward): `src/node/fit-grow.js` `sizeTables` sizes a Table without h from its text — 14 px for `<Td>` without fontSize (POM's default is 18), column widths with the fewest wrapped lines (never narrower than a word), rows at least their text, a squeezed box protected with `minH` or reported ("over-full slide"; rows then no taller than the generator's), the slide's dominant table grows text (≤ 18 px) + rows into empty space. `compile-pom.js` compiles the original XML if the fitted XML fails to build. New eval metrics `table_spill`, `tables_overfull_slides`, `empty_cells`. Eval `docs/eval/phase-5-tables/` (fill 0.947 but that gain is generator variance) + LLM-free replays: table spill 76 → 34 px on that run, 187 → 91 px on phase-1, golden fill 0.896 → 0.891. Details, decisions (a)–(e), (b'), option B: roadmap Phase 5 Step 3.
- Known open issues (roadmap Phase 5 Step 3): over-full slides still hide table rows (slide 1 of the last eval) → **Phase 2 must not put a long-text table into a half-width card** (user decision "option B"; warn-only audit `TABLE_TOO_WIDE_FOR_CARD` now flags it); table cells touch their neighbours (POM writes 0 cell margins; user 2026-09-24: no margins for now); the generator drops table data (`empty_cells`); table cells carry no font → PowerPoint draws them in the theme font Aptos while fit-grow measures Noto Sans JP (Phase 3); crushed KPI tiles (Phase 4).
- **Tables finished** (2026-09-24, branch `tables-finish`, merged `a9b390e`, LLM-free): table cells vertically centred by a pptx post-process (`src/node/pptx-post.js`), the main table's rows may grow to min(96 px, 2× text) into spare height (was 64 px / 1.5×), audit `TABLE_TOO_WIDE_FOR_CARD` (low). Replays: no spill/overflow regression; table-only and chart-and-table cards now fill. Unit tests 434 pass, same 4 failures. Details: roadmap Phase 5 Step 3 "Tables finished". Not yet confirmed by a paid run (the gate run below measures it).
- **Review fix** (2026-09-24, `3e9d1dd`): if `pptx-post.js` throws, `compile-pom.js` writes POM's unprocessed pptx and records the warning `PPTX_POST_SKIPPED` instead of failing the compile (a post-process bug must not cost a paid retry; verified by forcing the failure). Known minor weakness, not fixed: `TABLE_TOO_WIDE_FOR_CARD` multiplies a pixel `w` (read as a share of the slide) by its parent's share, so a px-wide card inside a narrow card can raise a spurious low warning.
- **Paused 2026-09-24 at a clean point** (user): everything merged into `feat/golden-reference-grounding` and pushed; no feature branch pending. Table-sizing code is complete; what remains for tables is placement (Phase 2.4), fonts (Phase 3) and the paid gate run. Resume with **Next** below.
- **Eval `tables-check`** (2026-09-24, `docs/eval/tables-check/`: gj-h1 + 5 table cases): gj-h1 first-pass 92.9%, table spill 187 → 77 px vs phase-1, empty cells 0, golden match 0.547 (best so far). Fixed after it: two tables on one slide keep one type size; normalizer strips `<B>` markup from attribute values (`ATTR_MARKUP_STRIPPED`). Still open (roadmap): touching cells (0 cell margins, left as is), long timeline labels; tables top-aligned in stretched cards → fixed in `tables-finish` (centred cells + relaxed row cap).
- **Next** (order agreed 2026-09-24): **Phase 3 fonts** first (LLM-free; first check on the test PC whether Noto Sans JP is installed and decide the deck font, Calibri via Carlito recommended), then **data lineage** (the outline passes `source_refs`; the slide planner and generator get the brief's data verbatim; runtime invented-number check; invent-numbers policy for the user to decide — to be written into the roadmap), then the **slimmed Phase 2** (roadmap Phase 2, revised: 2.1 prompt fixes + varied planner examples, 2.2 `routing_match` + `--planner-only` eval, 2.3 plan facts, 2.4 table placement). Phase 2's baseline is `docs/eval/tables-check/` (gj-h1 + the 5 table gate cases, already run — do not ask for them again); only the 6 never-run gate cases remain, run once on `feat/golden-reference-grounding` before Phase 2 merges, same label so they merge into that folder: `python -m scripts.eval_run gate-deck-cheffin-audit gate-deck-xtsy-qcomm gate-deck-agency-takeover eval-categorized-list-routing eval-chart-vs-kpi-disambiguation kpi-row --repeat 1 --label tables-check --bundle`. Unit tests: 434 pass, same 4 pre-existing failures.
- Branch `feat/golden-reference-grounding` (pushed; `master` is 60+ commits behind and has none of the roadmap work — do not run from `master`). Recent: post-process fallback (`3e9d1dd`), tables finished (merge `a9b390e`), Phase 5 Step 3 table sizing (merge `300eafa`), Phase 1 grammar, design-hint/nesting/icon enforcement, fit-grow pass (`dd5c152`), layout archetype system (`d2b75b6`), 14pt minimum font, Cursor handoff docs.
- `house-style.yaml` and `generator/system.j2` WIP edits are committed. `lxml` (used by `src/compiler/pptx_merge.py`) is now a declared dependency.
- Not synced: local scratch outputs in `llm_test/` (generated .pptx / slide dumps), including the 9 emailed eval run zips (`baseline-*`, `gj-h1-regen-*`, `phase-1-*`, `phase-5-tables-*`, `tables-check-*`) — the only source for free LLM-less replays; back them up.
- Note: `production-plan.mdc` says "no archetypes" (2026-09-03) but `d2b75b6` later added a layout archetype system — the newer commit reflects the current direction; confirm with the user if it matters.
- Memory rules mentioning `presentation-mvp/` refer to the older sibling MVP folder, not this repo.
