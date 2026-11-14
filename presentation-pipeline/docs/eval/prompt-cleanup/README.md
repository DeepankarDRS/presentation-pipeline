# Generator prompt cleanup: same-plan check (paid, test PC)

**Question:** does the generator prompt cleanup (`5491bf7`) change the slides on the same plans?
It removed contradictions (root padding, spacing scale, hex vs tokens, dark panel limit, delta colours),
duplicate notes and node notes on slides that cannot use them; data-slide prompt 11,587 → 11,143 tokens.
OpenAI's GPT-5 guidance: a reasoning model spends reasoning tokens reconciling conflicting instructions.

**Design:** generator only (`scripts.gen_from_plans`), planners skipped, so both arms draw the same saved
plans. Arm OLD = `747ce68` (feat/tile-nodes tip), arm NEW = OLD + `prompt-cleanup.patch` (the `5491bf7`
diff, prompts and knowledge only). Same day, same models (`models.yaml`: generator + repairer gpt-6.1-sol),
critic off, one run per arm.

| deck | plans from | commit | slides | component kinds |
|---|---|---|---|---|
| `cheffin` | `6.1 planner.zip` (2026-11-06) | `747ce68` | 6 | kpi_row 3, bullet_list 5, table 2, chart, card_grid, narrative, caption |
| `xtsy` | `diagram-direction-20261020-212232.zip` | `58c93b6` | 8 | card_grid 7, narrative 7, layer, flow, process_arrow, bullet_list |
| `agency` | `deck-fixes-20261016-085148.zip` | `39cf10a` | 6 | card_grid 5, narrative 5, table 2, chart, bullet_list, caption 2 |

20 slides per arm. XTSY's layer and flow slides are the ones whose per-slide notes changed most. The briefs in
`requests/` are the cases' `request:` text byte for byte; their fingerprints match each run's `request_sha256`
(checked on the build PC, 2026-11-11), and every plan renders a prompt with today's code.

**Cost:** generator-only slides on gpt-6.1-sol cost $0.026-0.039 each (`nodes-paid.zip`, 2026-11-04):
≈ $0.65 per arm, **≈ $1.30 for both, stop if it passes $1.80** (repairs).

## Steps on the test PC

Unzip `prompt-cleanup-check.zip` to a folder outside the repo, e.g. `C:\pc-check\` (it holds `plans\`,
`requests\`, `prompt-cleanup.patch` and this README). In the repo's `presentation-pipeline\` folder, venv on:

```bash
git status
git log -1 --format=%h
```
Clean, and `747ce68`. Then arm OLD:

```bash
python -m scripts.gen_from_plans C:/pc-check/plans/cheffin C:/pc-check/plans/xtsy C:/pc-check/plans/agency --requests C:/pc-check/requests/cheffin.txt C:/pc-check/requests/xtsy.txt C:/pc-check/requests/agency.txt --label prompt-old --bundle
```
Then arm NEW (the patch changes files only, nothing is committed). `git apply` runs from the repo root, the
folder above `presentation-pipeline\`:

```bash
cd ..
git apply --check C:/pc-check/prompt-cleanup.patch
git apply C:/pc-check/prompt-cleanup.patch
cd presentation-pipeline
python -m scripts.gen_from_plans C:/pc-check/plans/cheffin C:/pc-check/plans/xtsy C:/pc-check/plans/agency --requests C:/pc-check/requests/cheffin.txt C:/pc-check/requests/xtsy.txt C:/pc-check/requests/agency.txt --label prompt-new --bundle
```
Undo the patch afterwards (back to a clean `747ce68`):

```bash
cd ..
git apply -R C:/pc-check/prompt-cleanup.patch
git status
```
Email `output/gen-only/prompt-old.zip` and `output/gen-only/prompt-new.zip`.

## Scored on the build PC (free)

Per arm, per slide: first-try compile, repairs and their codes, `GEOM_*` error / warning counts, fill, word
breaks, invented numbers (`scripts.eval_run --fixtures`, `src.compiler.geometry_audit`), reasoning and
output tokens, cost; then blind A/B sheets for your marks. Gate: NEW no worse on first-try compile and
repairs, and blind marks ≥ 0.5. One run per arm: a difference of a slide or two is noise.

## Results

Not run yet.
