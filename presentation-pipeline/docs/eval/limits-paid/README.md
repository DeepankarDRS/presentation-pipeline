# Paid check: diagram limits from the break map (prepared 2026-10-22, not run)

What it checks: the planner-prompt and plan-check changes of `94dd5cd` on the merged branch
`claude/node-break-map-981214` (fit-grow follow-ups, diagram text in the deck font, break map batch 2,
diagram limits):

- the planner prompt's **per-placement limits** (`capacity.yaml` `placement`, the "Where it sits" line): does
  the planner pick a direction that fits where it puts the diagram (band, under a KPI row, a 60 / 40 column,
  a card)?
- the **longest-word plan check** (`src/agents/label_room.py`): which diagrams it turns vertical or into
  card steps, and whether those changes read better in the render;
- **vertical flows sized by code** (fit-grow phase 2b): 8 nodes in a column at 14 px.

## On the test PC

```
git fetch
git checkout claude/node-break-map-981214
git pull
python -m scripts.eval_run base-process-overview base-roadmap architecture-diagram base-org-structure gate-deck-all-nodes --repeat 1 --label limits --bundle
```

Email back the bundle zip it prints. On this PC: `python -m scripts.eval_import <zip>` -> `docs/eval/limits/`.

**Cost:** 18 slides (4 one-slide cases + the 14-slide all-nodes deck, one slide per component kind), about
$0.047 a slide on past runs -> **≈ $0.85**, within the $1 cap. Optional second run, only if the first is
unclear: `gate-deck-xtsy-qcomm` (8 slides, qualitative, its timelines are the ones the free replay changes),
≈ $0.38 more; all six cases together would be ≈ $1.2, over the cap.

## Already known for free (not repeated by the paid run)

- Free replay of the label check on the 65 unique saved plans with a process_arrow / timeline / matrix /
  pyramid (C:\dev output/): 6 changes: 5 horizontal timelines -> vertical ("Benchmarking—" 113 px,
  "Travel/commuting" 127 px, "creative/audience," 129 px in a 101 px title box), 1 matrix reported
  ("subscription/repeat", 107 px in 81). Words joined by "/" are measured as one word; a renderer may break
  after the slash, so those may be false positives: look at them in the render.
- Break map on the merged code: flow holds 419 / 800 with fit-grow, process_arrow 569, none made worse;
  unit tests 1214 pass + the 4 known failures.

## What to look for in the bundle

1. Every diagram's direction against where it sits (the plan's `layout_hint`, the slide render): a horizontal
   diagram beside another component, or more items than the "Where it sits" number for that place = a miss.
2. `capacity_fixes` in each slide plan (run manifest / slides.json): the label-room notes; is each switch
   (vertical / card steps) a better slide than the original would have been?
3. No step, milestone or level dropped or shortened (compare the brief's items with the drawn ones).
4. Broken words and text below 14 px in the renders (eval scores, `WORD_TOO_WIDE`), especially vertical flows
   and timelines.
5. Cost per slide against the ≈ $0.047 estimate.
