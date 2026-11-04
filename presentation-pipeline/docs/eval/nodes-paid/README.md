# Composition nodes: paid same-plan check

Does the generator use the six code-drawn nodes well, and are the slides better than today's route? This is the first run where a real LLM writes the final tags. Free gates so far drew bare tags with no LLM.

**Status: first run done 2026-11-04, $1.40; gate not met yet.** Fixes made; rerun of the 6 B slides below, approved by the user.

## First run

| | A (today) | B (all six) |
|---|---:|---:|
| Compiled on first try | 21 of 22 | 16 of 22 |
| Repair passes | 1 | 10 |
| Failed to compile, placeholder | 0 | 1 |
| Plan words lost | 0 | 12, on 2 slides |
| Cost | $0.675 | $0.726 |
| Blind marks | 4 | 8 (10 the same) |

Two of A's four wins are the two failed B slides. What failed, and the fix:

1. The LLM wrote `connector.color` and `bullets.color` (5 first-try errors): now read as the real attribute, `NODE_ATTR_ALIAS`.
2. A patch changed the slide's `alignItems="stretch"` to `start`: the repairer's prompt did not list `stretch`. It does now.
3. Under `start` a node shrank to no width and the compile crashed: a node with no `w` now takes `alignSelf="stretch"`.
4. The LLM wrote `<CardGrid>` on a narrative: `NODE_REF_UNKNOWN` now says what the component is, and hands over its words.
5. Regenerate re-planned from `content_summary` when the run had no outline, wrote the summaries as slide text, and its prompt had no node tags. With no outline it now keeps the plan (a full deck has one and still re-plans from it), and both regenerate paths use the generator's prompts.

## Rerun: the 6 B slides that failed their first try

B only; A's saved runs are joined for the sheets. Estimate $0.24; these six cost $0.30 last time. Stops at $1.00.

On the test PC, one after another:

```bash
git pull
```

```bash
python -m scripts.composition_paid --estimate --arm B --names deck-product-launch-data-s4-timeline,gate-deck-agency-takeover-s0-card-chart,gate-deck-agency-takeover-s1-bullet-card-table,gate-deck-all-nodes-dense-s4-bullet-timeline,gate-deck-xtsy-qcomm-s4-card,gate-deck-xtsy-qcomm-s7-timeline
```

```bash
python -m scripts.composition_paid --label nodes-b6 --max-cost 1 --bundle --no-render --arm B --names deck-product-launch-data-s4-timeline,gate-deck-agency-takeover-s0-card-chart,gate-deck-agency-takeover-s1-bullet-card-table,gate-deck-all-nodes-dense-s4-bullet-timeline,gate-deck-xtsy-qcomm-s4-card,gate-deck-xtsy-qcomm-s7-timeline
```

Email back `output/composition-paid/nodes-b6.zip`. Free, on the build PC, with the first run's folder in place:

```bash
python -m scripts.composition_paid --label nodes-b6 --rescore --a-from nodes-paid
```

## What runs

The same saved plans go through the real graph from the plan (style resolver, context builder, generator, validator, repairers), generator on `gpt-6.1-sol`, critic off, twice:

| Arm | Switches | Route |
|---|---|---|
| A | `POM_BLOCKS=tiles`, `POM_NODES` empty | Today: tile tags for KPI and cards; the LLM writes charts, tables, timelines and lists |
| B | `POM_BLOCKS=tiles`, `POM_NODES=chart,timeline,kpi_row,card_grid,table,bullet_list` | All six drawn by code |

22 plans x 2 arms = 44 runs ([inputs.json](inputs.json), saved plans of `tests/cases` decks; `gj-h1` left out).

| Node | Plans holding it |
|---|---:|
| `bullet_list` | 6 |
| `kpi_row` | 5 |
| `card_grid` | 5 |
| `table` | 5 |
| `chart` | 4 |
| `timeline` | 3 (few saved plans have one) |

17 plans hold one node, 5 mix two or three.

## Cost

Measured prompts: A about 12,400 input tokens a call, B about 12,700, of which about 9,000-9,900 are the cached prefix. `gpt-6.1-sol`: $2.00 input, $0.50 cached, $8.00 output per million.

| | Per run | 22 runs |
|---|---:|---:|
| A | $0.03-0.06 | about $1.00 |
| B | $0.02-0.05 | about $0.70 |

Estimate **$1.76**. A repair adds a call, so the stop is **$3.50** (`--max-cost`); it stops before a pair could pass it and keeps what was paid for.

## Run it on the test PC

```bash
git pull
```

```bash
python -m scripts.composition_paid --estimate
```

```bash
python -m scripts.composition_paid --label nodes-paid --bundle --no-render
```

Email back `output/composition-paid/nodes-paid.zip`. Scoring and the blind sheets run free on the build PC:

```bash
python -m scripts.composition_paid --label nodes-paid --rescore
```

## What it reads

- **Faithfulness:** plan words missing from the slide, values off the plan, both arms.
- **Reliability:** first try compiled, `NODE_*` errors, repairs, slides left as placeholders.
- **Use of the nodes:** variant written vs the default code would pick, per node; attributes dropped or doing nothing; `<Highlight>` written on lists and tables and whether it was valid (owed from the bullet node).
- **Cost:** per arm.
- **Quality:** blind marks on `sheets/` (`marks.csv`; `key.json` says which side is B).

Gate (user, 2026-11-04): B loses no plan words, no slide ends as a placeholder, and B wins the blind marks. Then `POM_NODES` becomes the default.

## What it does not cover

- **The planners.** Plans are saved ones, so the planner's new timeline `description` field is not exercised: none of the saved timelines has it. A full-deck run after this one covers it.
- **The visual critic and its repairer.** Critic off here; they still see expanded XML.
- **Plans from today's planners.** Saved plans date from 2026-10-11 to 2026-10-16.
