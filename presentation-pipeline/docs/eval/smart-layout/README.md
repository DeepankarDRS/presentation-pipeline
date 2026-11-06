# Smart-layout tests: what was run and how to rerun it

Free tests, 2026-11-06. No LLM calls, no pipeline change. Full write-up: `docs/smart-layout-research-2026-11-06.md`.

## Test set

27 saved slides with the real LLM's composition-node XML: 22 from `nodes-paid`, with the 6 rerun slides from `nodes-b6` in place of their first tries, and the 5 content slides of the 5 Nov run on `gpt-5-mini` planners. 3 hold one component, so 24 were tested.

Every arm keeps the header, the components and their style attributes as the LLM wrote them. Only the arrangement changes.

## Commands

Unzip `nodes-paid.zip`, `nodes-b6.zip` and the 5 Nov bundle into their own folders first. `--corpus` is the saved-runs folder.

```bash
python -m scripts.smart_layout_part1 prompts <slides.json> --out <dir>
```

```bash
python -m scripts.smart_layout_part1 predict --src <output dir> <unzipped dirs>
```

```bash
python -m scripts.smart_layout_lab run --np <nodes-paid> --b6 <nodes-b6> --deck <5 Nov bundle> --corpus <output dir> <nodes-paid> --k 6
```

```bash
python -m scripts.smart_layout_lab rescore --np <nodes-paid> --b6 <nodes-b6> --deck <5 Nov bundle>
```

```bash
python -m scripts.smart_layout_lab render
```

```bash
python -m scripts.smart_layout_lab sheets
```

```bash
python -m scripts.smart_layout_lab stress --corpus <output dir> --k 4
```

```bash
python -m scripts.smart_layout_scorecheck docs/eval/card-nodes/replay-2 <output>/card-replay docs/eval/card-nodes/paid <output>/card-paid/card-paid docs/eval/tile-nodes/same-plan <output>/tile-same-plan/same-plan
```

```bash
python -m scripts.smart_layout_summary
```

The worktree needs a junction from `src/node/node_modules` to the main checkout's copy (Windows: `mklink /J`).

## Files here

| File | What it holds |
|---|---|
| `results-summary.json` | Each arm's totals, the stress test, best arrangement by kinds |
| `blueprint-predicts.json` | Skeleton against drawn layout, all periods |
| `blueprint-by-period.json` | The same, split at 2026-10-08 |
| `prompts-nov5-mini.json` | Per slide of the 5 Nov run: the skeleton selected and whether it reached the system prompt |
| `example-blueprint-block.txt` | The skeleton block as the generator receives it |
| `sheets-public/` | Blind sheets of the three made-up decks only |

The sheets with client slides stay local: `output/smart-layout/pairs/` (today against best of 6) and `output/smart-layout/sheets/` (every arm). Each has a `marks.csv` to fill and a key file that says which side is which.

## The 24 slides (the paid test's case list)

- `deck-product-launch-data-s1-bullet`
- `deck-product-launch-data-s5-bullet`
- `deck-qbr-data-s1-kpi`
- `deck-qbr-data-s2-chart`
- `gate-deck-agency-takeover-s0-card-chart`
- `gate-deck-agency-takeover-s1-bullet-card-table`
- `gate-deck-all-nodes-dense-s1-chart-kpi`
- `gate-deck-all-nodes-dense-s2-table`
- `gate-deck-all-nodes-dense-s4-bullet-timeline`
- `gate-deck-cheffin-audit-s1-kpi`
- `gate-deck-cheffin-full-s2-chart-kpi`
- `gate-deck-cheffin-full-s3-bullet`
- `gate-deck-cheffin-full-s4-kpi`
- `gate-deck-cheffin-full-s5-table`
- `gate-deck-xtsy-qcomm-s0-bullet`
- `gate-deck-xtsy-qcomm-s3-card`
- `gate-deck-xtsy-qcomm-s4-card`
- `gate-deck-xtsy-qcomm-s6-card`
- `gate-deck-xtsy-qcomm-s7-timeline`
- `nov5-gate-deck-cheffin-full-s1`
- `nov5-gate-deck-cheffin-full-s2`
- `nov5-gate-deck-cheffin-full-s3`
- `nov5-gate-deck-cheffin-full-s4`
- `nov5-gate-deck-cheffin-full-s5`

## Limits

- The LLM's XML was written with the skeleton in its prompt, so "today" is not a slide written without one. Only a paid run tells that apart.
- The library arm drew on 390 saved slides, with each test slide's own deck held out. A real library could be larger or better curated.
- The score's weights were set by hand. The fill measure was chosen after the fault count failed against past marks, so 34 of 50 is an in-sample figure, on card and tile choices rather than arrangements.
- Rendered in LibreOffice with Inter, not PowerPoint.
- The bare-tag stress test draws components with default looks and a plain text box for narrative.
