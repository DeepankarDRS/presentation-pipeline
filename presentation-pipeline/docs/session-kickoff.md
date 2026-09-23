# Session kickoff — build here, test there, results by email (roadmap Phases 0–4)

- **Build device (this PC, no OpenAI key):** ALL code, docs and commits happen here. Each phase is proven LLM-free first (unit tests, compiler, LibreOffice renders).
- **Test device (company PC, has `OPENAI_API_KEY`):** only *runs* commands on a pulled checkout. It never commits or pushes (company policy).
- **Channel back:** the user emails the eval bundle (and anything else requested) to the build device; the build session imports it and commits the summary.
- One Claude/Cursor session per phase on the build device.

---

## 1. Prompt to paste on the BUILD device (new session, change the phase number)

> Read `AGENTS.md`, `docs/roadmap-derived-components.md`, `docs/layout-sizing-plan.md`, `docs/design-hint-architecture.md` and `docs/session-kickoff.md`. We are implementing **Phase <N>** on the build device. This device has NO OpenAI key and is the ONLY device that commits. Everything you build must be verified without the LLM (unit tests, `node src/node/compile-pom.js`, `python -m scripts.render_check`, LibreOffice renders). Real-pipeline results arrive from the test device by email as an eval bundle; ask me for exactly what you need (bundle, LangSmith trace export, a .pptx, a render) — I will fetch it.
>
> Before coding:
> 1. `git pull`, then create/checkout the phase branch named in docs/session-kickoff.md §3.
> 2. Record the unit-test baseline: `uv run pytest tests/unit -q` (known on 2026-09-23: 370 pass, 4 pre-existing failures).
> 3. If the phase depends on eval results, import them first (`docs/eval/<label>/summary.md`); if missing, ask me for the bundle.
> 4. Summarise the phase, list its DECIDE points with your recommendation, and ask me. Do not code until I answer.
>
> While working: follow `.cursor/rules/00-working-approach.mdc`. Do not edit `src/node/fit-grow.js` unless the phase says so (another session owns it). End the phase with: tests green vs baseline, a note in the roadmap's phase section ("built <date>, awaiting eval"), commit, push, and give me the exact test-device commands plus the list of files to email back.

## 2. What to run on the TEST device (copy-paste, no session needed)

```bash
git pull
git checkout <branch>
uv sync
npm install --prefix src/node
python -m scripts.eval_run --label <label> --bundle      # built in Phase 0
```

Email back the single file it prints: `output/eval/<label>-<timestamp>.zip` (summary.md, results.json, per-slide XML + compile-result.json, review PNGs; built to stay small enough to email).
Only if the build session asks: a LangSmith run export (JSON) for specific cases, or a specific `.pptx`.

Until Phase 0 exists, the test device can run `python -m src.runner <cases> --json > runner.json` and email `runner.json` plus the `output/runs/<run_id>/` folders requested.

**Data policy:** eval cases in `tests/cases/` are synthetic. Before emailing, make sure nothing in the bundle is client data your policy forbids sending; the bundle contains slide text and numbers from the prompts that were run.

## 3. Phase-by-phase split

| Phase | Build device | Test device runs | Email back → build device commits |
|---|---|---|---|
| **0 Baseline** — branch `phase-0-eval` | `scripts/eval_run.py` (+ `--bundle` zip), `scripts/eval_compare.py`, `scripts/eval_import.py <zip>` → `docs/eval/<label>/`; fill ratio from pptx frames; gj-h1 regeneration case. Tests with a mocked `run()` + one real compile. **DECIDE:** gate case subset. | `eval_run --label baseline` on this branch (its pipeline code is unchanged) + the gj-h1 case | baseline bundle → `eval_import` → `docs/eval/baseline/`, tag `eval-baseline`. **No Phase 1–4 code is merged before this exists.** |
| **1 Sizing grammar** — `phase-1-sizing` | grow/minH grammar, audit rule, `tests/fixtures/layout_sizing/`, render checks. **DECIDE:** blueprints/golden-examples. | `eval_run --label phase-1` | → `docs/eval/phase-1/`; merge only if not worse than baseline |
| **2 Routing + planner fixes** — `phase-2-routing` | prompt fixes, `data_shape.py`, `routing.yaml`, remap; table-driven tests. **DECIDE:** 2A vs 2B. | `eval_run --label phase-2` incl. all `eval-*` cases | → `docs/eval/phase-2/`; LangSmith planner traces for any mis-routed case |
| **3 Font metrics** — `phase-3-fonts` | Carlito (OFL) fonts, `buildPptx` fonts, normalizer `fontFamily`. **DECIDE:** deck font. | open the fixture decks in **PowerPoint**, screenshot; `eval_run --label phase-3` | screenshots + bundle |
| **4 Derived nodes** — `phase-4-derived` | derived-nodes spec + expander + KpiTile/TableCard/IconList; every variant compiles, audit-clean. **DECIDE:** Jinja vs Python; slide-editor level. | `eval_run --label phase-4` + gj-h1 case | → `docs/eval/phase-4/`; gj-h1 score is the headline |

Phases 1 and 2 are independent; each is merged into `feat/golden-reference-grounding` only after its own eval.

## 4. Rules

- **Build device always `git pull` first** (a parallel session commits fit-grow work to the same branch).
- **Commit summaries, not raw output.** `eval_import` writes `docs/eval/<label>/summary.md` + ≤15 review PNGs; raw bundles stay in `output/` (gitignored).
- **Baseline before change**, same case set, same `models.yaml`.
- **Record every DECIDE answer** in the roadmap phase section with the date.
