# Composition nodes: paid same-plan check

Does the generator use the six code-drawn nodes well, and are the slides better than today's route? This is the first run where a real LLM writes the final tags. Free gates so far drew bare tags with no LLM.

**Status: approved by the user 2026-11-04, not run yet.** Estimate $1.76, stops by itself at $3.50.

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
