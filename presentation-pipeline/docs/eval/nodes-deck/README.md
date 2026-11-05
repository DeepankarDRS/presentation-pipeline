# Composition nodes: full-deck run

**2026-11-05: `POM_NODES` (all six) and `POM_BLOCKS=tiles` are now the code default on `feat/tile-nodes`; `POM_NODES=` (set, empty) turns them off.** One smaller confirming run replaces the table below: `gate-deck-xtsy-qcomm` and `deck-product-launch-data`, about $0.54, `--max-cost 1`.

The same-plan check (`docs/eval/nodes-paid/README.md`) passed the user's gate on saved plans, one slide at a time. This run covers what it could not: fresh plans from today's planners, whole decks, and the real repair count, which decides whether route B saves money.

**Status: prepared 2026-11-05; the user runs it on the test PC.** Estimate about $1.05, stops by itself at $2.00.

## What runs

The whole graph, route B only, critic off: outline planner, slide component planner, generator, validator, repairers. `--nodes` turns on `POM_BLOCKS=tiles` and all six in `POM_NODES`, whatever the test PC's `.env` says. Planners on `gpt-5-mini`, generator and repairer as in `models.yaml` (`gpt-6.1-sol` for the generator).

| Deck | Slides | Why this deck | Nodes it should reach |
|---|---:|---|---|
| `gate-deck-xtsy-qcomm` | 8 | Gave both bad slides in the first paid run | cards, timeline, lists |
| `gate-deck-agency-takeover` | 6 | Dense: where hand-typed slides spilled | tables, charts, cards, lists |
| `gate-deck-all-nodes-dense` | 6 | Most kinds on a slide; hand-drawn `<Flow>` beside nodes | KPI, chart, table, timeline, lists |
| `deck-product-launch-data` | 6 | Timeline with supplied detail: the planner's `description` field | timeline, lists |

4 decks, 26 slides, one run each. The nodes reached depend on the fresh plans. `gj-h1` is left out for cost.

## Cost

Measured: planners on these decks' saved runs of 2026-10-13 to 2026-10-16; generator $0.028 a clean slide and about $0.05 a repaired one, from the same-plan check.

| Deck | Planners | Generator, no repairs | Deck |
|---|---:|---:|---:|
| `gate-deck-xtsy-qcomm` | $0.08-0.11 | $0.22 | about $0.32 |
| `gate-deck-agency-takeover` | $0.08-0.12 | $0.17 | about $0.27 |
| `gate-deck-all-nodes-dense` | $0.05 | $0.17 | about $0.22 |
| `deck-product-launch-data` | $0.05 | $0.17 | about $0.22 |
| **Total** | about $0.28 | $0.73 | **about $1.05** |

If every slide needed one repair: about $1.60. `--max-cost 2` is checked between decks: a deck under way always finishes, so a very bad run could end a little above $2.00.

Time: not measured on whole decks. At about 40 seconds a slide on the last run, plus planning, expect 20-30 minutes.

## Run it on the test PC

One after another, from `presentation-pipeline/`, on `feat/tile-nodes`:

```bash
git pull
```

```bash
python -m scripts.eval_run gate-deck-xtsy-qcomm gate-deck-agency-takeover gate-deck-all-nodes-dense deck-product-launch-data --repeat 1 --label nodes-deck --nodes --max-cost 2 --bundle
```

The last lines print `EMAIL THIS FILE:` and the zip's path, `output/eval/nodes-deck-<date>-<time>.zip`. Email that file back. Each deck's `llm.pptx` is inside, under `decks/`, to open and look at.

## What it reads (free, on the build PC)

- **Repairs:** slides compiled on the first try, repair passes, slides that reached regenerate, per slide with its cause.
- **Failures:** placeholder slides; plan words missing from the slide.
- **Cost:** per deck and per step (`python -m scripts.usage_report <folder>`), against the estimate.
- **The three prompt-only fixes, first time with a real LLM:** text callouts not written as ref tags; a heading above tables; neighbours sharing a panel.
- **Planner:** whether timelines now fill `description`.
- **Quality:** the user looks at the decks. There is no route A in this run, so no blind marks.

## What it does not cover

- **A cost comparison on these plans:** A does not run. B's cost per slide is compared with A's $0.031 from the same-plan check, on different plans.
- **The visual critic and its repairer:** critic off. The regenerate change in the visual repairer stays covered by unit tests only.
- **Variance:** one run per deck.
