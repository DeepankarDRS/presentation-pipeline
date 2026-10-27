# Outline items, gates 1-2 (2026-10-28)

Design: `docs/outline-items-design-2026-10-27.md` §7. Run on the test PC, branch
`claude/component-selection-analysis-3e46a9` at `81bf603`, `OUTLINE_ITEMS=on`, typed planner schema, all planners on
gpt-5-mini:

```bash
python -m scripts.card_plan_only --repeat 2 --label outline-items-2 --schema typed --outline-items --bundle --workers 5
```

Compared with the saved `typed-schema` plan-only run (2026-10-15, same six decks × 3, same models, no items) using
`python -m scripts.outline_items_report outline-items-2 --base typed-schema`; the full report is `report.md` here.
12 runs, 74 slides, $0.811 ($0.068 a run vs $0.064). No connection errors, no failed runs, 2 planner re-asks (XTSY
card lines).

An earlier attempt (`outline-items`, 2026-10-27) is not counted: the test PC's `models.yaml` had the planners on
gpt-6.1-sol, a first invocation hit connection errors, and the elicitor stopped XTSY with no error (fixed in `81bf603`:
a plan-only run with no outline now fails loudly).

## Gate 1, outline: passed

| | Items | Saved run |
|---|---|---|
| Brief figures not in the outline | 21 of 280 (7.5%) | 28 of 420 (6.7%) |
| Outline figures not in the brief | 0 | 0 |
| Speaker notes in items | 0 | - |
| `POINT_NOT_IN_BRIEF` | 6, all on launch slide 6 | - |
| Slides with the same item kinds in both repeats | 24 of 37 | - |

Items: 245; metric 18%, series 2%, records 7%, steps 8%, point 45%, visual 19%, note 2%.

Read by hand:
- The 6 flagged points are real outline writing: the launch brief's pipeline steps reworded with an added purpose
  ("Auto-discovery of existing APIs to centralize management") plus three written benefits ("Eliminates gateway sprawl
  and reduces manual configuration time"). They became card bodies. The check works; the review screen (§6) is where
  the user would remove them.
- Kind stability is the weak spot: in the agency deck the same table is one `records` item in one repeat and a list of
  `point` / `metric` items in the other (agency slides 1, 2, 3, 6; XTSY 3). Most differences are records vs point (16
  of 24 kind changes). It did not make the plans less stable (gate 2).
- Item-form flags: all-nodes slide 2's visual item repeats the chart data the series item also carries (the chart is
  drawn from the series); three `records` items hold words, not measures (an org chart, a platform × lever grid, data
  requests). Report-only; no data lost.

## Gate 2, planner: passed

| | Items | Saved run |
|---|---|---|
| Components per slide | 1.82 | 2.10 |
| Without narratives | 1.47 | 1.50 |
| Narrative share | 19% (26 of 135) | 29% (67 of 233) |
| Narratives copied from the brief | 26 of 26 | QBR + launch: all 9 written by the outline |
| Narratives on QBR + launch | 0 in 4 runs | 9 in 6 runs |
| Distinct kinds per deck, without narratives | 5.92 | 6.00 |
| Same component kinds on a slide in repeats 1 and 2 | 28 of 37 | 21 of 37 |
| Outline figures missing from the plan | 2 (CHEFFIN r1 slide 3: "~2.9x", "~3.1x") | 4 |
| `KIND_OUTSIDE_FIT` | 5, all legitimate picks | - |

The drop in components per slide is the removed outline commentary: without narratives the count, the variety and
the kinds per deck are unchanged. The 13 XTSY narratives are the brief's own "key insight" lines.

`KIND_OUTSIDE_FIT`, read by hand: an org chart tagged `records` drawn as a tree; CHEFFIN data notes drawn as a
narrative / bullet list on its data-caveats slide; XTSY "Visibility → Offtakes → Market Share → Profitability" tagged
`point` drawn as a process arrow. In each the pick is right and the item's kind is the questionable part; the fit
list stays as it is.

## Open

- Gate 3 (generator on these plans + blind marks): prepared, see below.
- Kind stability of tables (records vs a list of points / metrics).
- The review screen (design §6), where `POINT_NOT_IN_BRIEF` items get Keep / Remove.

## Gate 3, generator: prepared, not run

`scripts/outline_items_gen.py`. Inputs (`gate3-inputs.json`, built free from the two `runs.json`): repeat 1 of
`outline-items-2` paired with repeat 1 of `typed-schema`, each items slide with the base slide of the same deck whose
words overlap most (at least a third; the outlines may order slides differently), kept only when the two plans draw
different component kinds: 20 pairs. The user reviewed them side by side (`gate3-pairs-review.md`, 2026-10-28) and
dropped 4 that are not a fair test: `gate-deck-cheffin-full-s4` (the key formulas are only in base),
`gate-deck-xtsy-qcomm-s5` (overlap 0.33, base adds descriptions and an empty visual), `gate-deck-agency-takeover-s4`
(near-identical plans), `gate-deck-xtsy-qcomm-s3` (both plans share the same card defect). **16 pairs** remain: QBR 3,
launch 3 (the cover included), agency 3, all-nodes 1, CHEFFIN 5 (the cover included), XTSY 1. Pair rule from the
review: both plans carry the same figures and points; no near-identical pairs or shared defects. Items defects kept
on purpose (the gate should see them): agency s1 chart values are text, all-nodes s2 a sentence as a KPI label, QBR s5
"core_hook" in the subtitle, XTSY s6 steps as cards rather than a flow.

```bash
python -m scripts.outline_items_gen --make-inputs --items output/card-plans/outline-items-2/runs.json --base output/card-plans/typed-schema/runs.json --drop gate-deck-cheffin-full-s4,gate-deck-xtsy-qcomm-s5,gate-deck-agency-takeover-s4,gate-deck-xtsy-qcomm-s3
```

Both arms run the real graph from the slide plan (generator, validator, repairers; critic off; `models.yaml` as
committed: generator gpt-6.1-sol), then compile with the deck font, render in Inter and go on blind A / B sheets.

```bash
python -m scripts.outline_items_gen --label gate3 --no-render --bundle --max-usd 1.5      # test PC, paid
python -m scripts.outline_items_gen --label gate3 --rescore                               # build PC, after the bundle
python -m scripts.node_test_sheet --score output/outline-items-gen/gate3/sheets          # after the marks
```

Pass: blind marks ≥ 0.5 for the items slides (wins + ½ ties), no more first-try compile failures or repairs than base.
