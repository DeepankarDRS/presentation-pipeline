# Session kickoff — two-device workflow for roadmap Phases 0–4

- **Build device (this PC, no OpenAI key):** implements each phase and proves it LLM-free (unit tests, compiler, LibreOffice renders).
- **Test device (has `OPENAI_API_KEY`):** runs the real pipeline evals and commits the results.
- Git is the only channel between them. One Claude/Cursor session per phase.

---

## 1. Prompt to paste on the BUILD device (new session, change the phase number)

> Read `AGENTS.md`, `docs/roadmap-derived-components.md`, `docs/layout-sizing-plan.md`, `docs/design-hint-architecture.md` and `docs/session-kickoff.md`. We are implementing **Phase <N>** on the build device. This device has NO OpenAI key: everything you build must be verified without the LLM (unit tests, `node src/node/compile-pom.js`, `python -m scripts.render_check`, LibreOffice renders). Real-pipeline acceptance happens on the test device via `docs/eval/`.
>
> Before coding:
> 1. `git pull`, then create/checkout the phase branch named in docs/session-kickoff.md §3.
> 2. Record the unit-test baseline: `uv run pytest tests/unit -q` (known on 2026-09-23: 370 pass, 4 pre-existing failures).
> 3. If the phase depends on eval results, read the latest `docs/eval/*/summary.md` first.
> 4. Summarise the phase, list its DECIDE points with your recommendation, and ask me. Do not code until I answer.
>
> While working: follow `.cursor/rules/00-working-approach.mdc` (state assumptions, surgical changes, verifiable steps). Do not edit `src/node/fit-grow.js` unless the phase says so (another session owns it). End the phase with: tests green vs baseline, a short note in the roadmap's phase section ("built <date>, awaiting eval"), commit, push, and tell me the exact command for the test device.

## 2. Prompt to paste on the TEST device

> Read `AGENTS.md` and `docs/session-kickoff.md`. `git pull` and check out branch `<branch>`. Run the eval for label `<label>` as described in §3 of docs/session-kickoff.md, commit only `docs/eval/<label>/` (summary.md + the review PNGs), push, and give me the 5-line headline: first-pass compile rate, avg retries, audit issues, avg fill ratio, cost — each vs the previous eval.

(Until Phase 0 is built, the test device can only run `python -m src.runner …`.)

## 3. Phase-by-phase split

| Phase | Build device (no key) | Test device (key) | Handoff |
|---|---|---|---|
| **0 Baseline** — branch `phase-0-eval` | Build `scripts/eval_run.py` + `scripts/eval_compare.py` (roadmap §Phase 0): metrics, fill ratio from pptx frames, renders, gj-h1 regeneration case. Unit-test them with a mocked `run()` and one real compile. **DECIDE:** the gate case subset. | Merge `phase-0-eval` → run the gate set **on this unchanged code**, label `baseline`. Also run the gj-h1 case. | `docs/eval/baseline/summary.md` + ~10 PNGs. Tag that commit `eval-baseline`. **No Phase 1–4 code may be merged before this exists.** |
| **1 Sizing grammar** — branch `phase-1-sizing` | house-style/recipes/prompt rewrite to `grow`/`minH`, `layout_audit` rule, new fixtures in `tests/fixtures/layout_sizing/`; verify with compile + render (fill ratio of the fixtures). **DECIDE:** rewrite or retire blueprints/golden-examples. | Run gate set, label `phase-1`. | `docs/eval/phase-1/` → compare with `baseline`; merge only if not worse. |
| **2 Routing + planner fixes** — branch `phase-2-routing` | Planner prompt fixes (2.1), `data_shape.py`, `routing.yaml`, remap (2.3A) — table-driven unit tests incl. every `eval-*` case. **DECIDE:** 2A vs 2B. | Run gate set + all `eval-*` cases, label `phase-2`. | `docs/eval/phase-2/` |
| **3 Font metrics** — branch `phase-3-fonts` | Vendor Carlito (OFL), pass `fonts` to `buildPptx` + fit-grow context, normalizer `fontFamily`. Verify measurement on fit-grow fixtures. **DECIDE:** deck font. | Open the fixture decks in **PowerPoint** and confirm line wraps match; run gate set, label `phase-3`. | `docs/eval/phase-3/` + PowerPoint screenshots |
| **4 Derived nodes** — branch `phase-4-derived` | `derived-nodes.yaml`, `derived_nodes.py` expander, templates for KpiTile/TableCard/IconList, prompt section, recipe removal; every node × variant compiles, audit-clean, content-model valid. **DECIDE:** Jinja vs Python; slide-editor level. | Run gate set + gj-h1 case, label `phase-4`. | `docs/eval/phase-4/` — the gj-h1 score is the headline. |

Phases 1 and 2 are independent and may be built in either order, but each is merged only after its own eval.

## 4. Rules for both devices

- **Always `git pull` first.** Another session commits to `feat/golden-reference-grounding` (fit-grow). Phase work happens on the phase branches above, merged into `feat/golden-reference-grounding` after its eval passes.
- **Commit eval summaries, not raw output.** `output/` is gitignored; commit `docs/eval/<label>/summary.md` and at most ~15 small PNGs for review.
- **Baseline before change.** An eval is only meaningful against the previous label run on the same case set and the same `models.yaml`.
- **Record decisions.** Each DECIDE answer goes into the roadmap's phase section with the date, so the next session doesn't re-ask.
