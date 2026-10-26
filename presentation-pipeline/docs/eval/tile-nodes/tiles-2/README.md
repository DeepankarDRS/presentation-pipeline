# Tile nodes: wider check after the prompt fixes (arm B again, same plans) — PREPARED, NOT RUN

**Why.** One slide (CHEFFIN 4, `scripts.tile_one`, 2026-10-26) showed the tiles route working end to end only after
four fixes; a wider run must show how often it holds across the six decks:

1. a hand-drawn KPI row is sent back to `<KpiGrid ref>`, not to `<Text ref>` label notes (`906bc91`);
2. a bare `KpiGrid` / `CardGrid` takes the look its design hint asks for (option A, `d091371`);
3. a dot on a bad / watch item keeps its tone (`fdb1346`);
4. the tile tags are allowed nodes in the generator prompt and the house style names `<KpiGrid ref>` (`ab36c50`).

CHEFFIN 4 before (4): hand-drawn tiles on the first try 3 / 3, each repaired. After (4): the first try wrote
`<KpiGrid>` with its own variants (dot + hero on CPC, toned Allowable CPC) and passed, no repair.

**What runs.** Arm B only (`POM_BLOCKS=tiles`) on the **same 17 slide plans** as the combined check
(`output/tile-combined/combined/plans.json` on the test PC, reused with `--from combined`: no planning is paid).
That check's arm A runs (`POM_BLOCKS=kpi`, repeat 1) are copied in, so the summary and the blind sheet compare new B
with the A drawn on the same plans. Real graph from each plan (generator, validator, repairers; critic off), once.

**Command (test PC, branch `feat/tile-nodes`, after `git pull`):**

    uv run python -m scripts.tile_combined --label tiles-2 --from combined --arms B --repeat 1 --bundle --no-render

If the saved check has another label, use it in `--from` (`ls output\tile-combined`). It prints
`EMAIL THIS FILE: output/tile-combined/tiles-2.zip`. On the build PC: `python -m scripts.tile_combined --label tiles-2
--rescore` (Inter renders, summary.md, blind sheets A / B).

**Cases (17 slides, from `tile_one --list`):**

| deck | slides |
|---|---|
| deck-qbr-data | s1, s4 |
| deck-product-launch-data | s2, s3 |
| gate-deck-agency-takeover | s1, s2, s3, s4 |
| gate-deck-all-nodes-dense | s1 (hint: dark emphasis), s5 |
| gate-deck-cheffin-full | s1, s4 (hint: dot on CPC) |
| gate-deck-xtsy-qcomm | s1, s2, s3, s6, s7 |

**Cost.** Per slide on the tiles route, gpt-6.1-sol: $0.029 when the first try passes, $0.021–0.022 with one cheap
repair, $0.052 with a long repair (CHEFFIN 4, four runs). Card slides were about $0.02 each (card paid check).
Estimate **≈ $0.35–0.6** for 17 slides, **ceiling ≈ $1.0** (several repairs). No planning cost (about $1.5 for the six
decks in the card paid check). A fresh full combined check instead (new plans, both arms, `--repeat 1`) would cost the
planning again plus 34 draws.

**What to read in the result.** Per slide: first try passed (no repair), tile tags written on the first try (vs drawn
by hand), variants the LLM chose itself, `NODE_LOOK_FROM_HINT` picks, KPI number / card title sizes, broken words,
values missing or off the plan, cost. Compare with the combined check's own arm B (same plans, before the fixes).
