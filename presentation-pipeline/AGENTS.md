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

Known pre-existing unit-test failures on a clean `uv sync` (verified 2026-09-23: 370 pass, 4 fail — not regressions):
`test_critic.py::test_critic_medium_only_passes`, `test_layout_audit.py::test_font_at_minimum_ok`, and two routing tests in `test_graph.py` (`*_budget_exhausted*`: expect `evaluator`/`slide_router`, code now routes to `visual_repairer` — tests or routing are stale).
Always record your own baseline (`pytest tests/unit -q`) before a change and compare against it.

When judging slide quality, open the `.pptx` (or render via LibreOffice, see `.cursor/rules/offline-render-loop.mdc`) — don't trust pass/fail alone.

## Design hints, nesting and icons (implemented 2026-09-23)
Read `docs/design-hint-architecture.md` before touching prompts, knowledge YAML or the normalizer. Core nodes (Table/Td, Ul/Li, Text, Chart, ...) have fixed syntax; enrichment is composed AROUND them in VStack/HStack. Rules live as data: `nodes.yaml` (nesting), `core/hint-capabilities.yaml` (what a design_hint may ask per component kind), `core/icon-names.txt` (valid icons). Cursor rule: `.cursor/rules/pom-nesting-content-model.mdc`.

To check it live (needs OPENAI_API_KEY): generate a table-heavy slide, e.g.
`python -m src.graph "One data slide: ROAS by platform for Flipkart 0.34x and Zomato 0.32x, highlight the worst performer"`
then check the run's XML in `output/runs/<run_id>/`: no HStack/Icon inside `<Td>`, planner hint drawn from table treatments (color, shading, header icon), and normalize issues in the log (`TEXT_CONTAINER_FLATTENED`, `UNKNOWN_ICON_REMOVED`) should be rare.

## Next work: `docs/roadmap-derived-components.md`
Phase 0 quality baseline (needs OPENAI_API_KEY) -> 1 sizing grammar (grow/minH instead of pixel budgets; from docs/layout-sizing-plan.md) -> 2 deterministic data-shape routing + planner prompt fixes -> 3 real font metrics -> 4 derived nodes (KpiTile/TableCard/IconList) -> 5 remaining derived nodes + computed table/diagram sizing -> 6 measured critic loop. Each phase lists its files, tests, acceptance criteria and the decisions (marked DECIDE) to confirm with the user first.

## Where work stands (2026-09-23)
- Branch `feat/golden-reference-grounding`. Recent: design-hint/nesting/icon enforcement, fit-grow pass (`dd5c152`), layout archetype system (`d2b75b6`), 14pt minimum font, Cursor handoff docs.
- `house-style.yaml` and `generator/system.j2` WIP edits are committed. `lxml` (used by `src/compiler/pptx_merge.py`) is now a declared dependency.
- Not synced: local scratch outputs in `llm_test/` (generated .pptx / slide dumps).
- Note: `production-plan.mdc` says "no archetypes" (2026-09-03) but `d2b75b6` later added a layout archetype system — the newer commit reflects the current direction; confirm with the user if it matters.
- Memory rules mentioning `presentation-mvp/` refer to the older sibling MVP folder, not this repo.
