# KPI tile nodes: free replay (2026-10-12)

`python -m scripts.tile_replay` (spec §8 step 4, `docs/tile-nodes-spec-2026-10-12.md`). No API calls.

## Method

- **Slides (17 KPI slides, 3 cases).** The 4 genuine first tries the 2026-10-12 decks run saved (`generated.xml` /
  `first-generated.xml`: what the generator wrote on today's route, `POM_BLOCKS=kpi`), plus 13 recovered from final
  XML: the 2026-10-11 paid check's 9 runs and the 2026-10-11 decks run's 4 KPI slides (filled text mapped back to
  `<Text ref>`, code's ids dropped; the colours the fill step wrote can't be told from the LLM's, so the recovered
  hand-written XML is slightly overstated, a few tokens per item). The paid check predates first-try saving.
- **Rewrite** (`rewrite` in the script, no hand edits): per KPI component, read what the LLM drew. That covers the
  tile fill → variant (`$panelDark` → `inverted` on the plan's emphasis item, `*Soft` → `filled` / `toned`, a ≥ 4 px
  left edge → `bar`, a small ellipse → `dot`, no box → `bare`, else `plain` + its fill), and the role colour → `color`.
  It also takes icon → `icon`, order → `arrange`, the tiles' row / grid / column → `layout` / `cols` (`layout="row"`
  written when the LLM put 5+ tiles in one row), the group box (`w`, `grow`, `gap`), outside tiles → `<Kpi>` in
  place with their `w` / `grow`, and each part's own styling (label / value / note `color`, `bold`,
  `letterSpacing`) where it differs from the look (shared by every tile → on the group).
  Not carried: tile shadows.
- **Both versions** through the same path: fill (`element_refs.fill_refs` / `tiles.fill`) → `normalize_xml` →
  `compile-pom.js` (fit-grow) → LibreOffice, scored with `scripts/kpi_replay.score`.
- **KPI output tokens**: the hand-written XML the tags replace vs the tags, o200k, whitespace between tags removed on both.

## Results

| | hand-written (A) | tile tags (B) |
|---|---|---|
| KPI output tokens, all 17 | 9,567 | **2,095 (−78%)** |
| KPI output tokens, the 4 genuine first tries | 2,260 | **371 (−84%)** |
| compiled | 17 / 17 | 17 / 17 |
| tile-node errors (NODE_* error) | – | 0 |
| hand-written ref tiles left (T2 fallback) | – | 0 |
| broken words (LibreOffice render) | 0 | 0 |
| `GEOM_CARD_EMPTY` | 36 | 39 |
| `LOW_CONTRAST` | 0 | 0 |
| values off plan | – | 0 |

Per slide: `summary.md`. Renders, hand-written left and tile tags right: `pairs-01.png` … `pairs-05.png`.

The spec gate for the paid check is KPI output tokens down ≥ 50%; the replay shows −78% / −84% when the LLM writes
the same looks with tags. Spec §7's "~12–60" is the floor (no styling). Reproducing the LLM's own part styling
costs 60–190 tokens a slide.

## Findings

1. **Looks reproduce.** Every hand-written KPI block in the 17 slides maps onto a variant + attributes; the pairs read
   the same (sheets). Differences left: tile shadows (not carried by the rewrite; `shadow.*` is a box attribute the
   LLM may write), and on CHEFFIN slide 1 the supporting row draws smaller (46 vs 72 px). The rewrite gives the
   inverted tile `size="hero"`, which the hand route never set, and the hero row takes more height.
2. **`GEOM_CARD_EMPTY` is the LLM's layout, not the tiles.** With the LLM's own layout kept, card-empty is level
   (36 vs 39). A first rewrite that left `layout` out gave 36 → 0: the default for 5+ items (a balanced grid: 7 → 4 + 3)
   fills CHEFFIN slide 4's tiles where the LLM put 7 in one row. A grid default helps only when the LLM omits `layout`.
3. **The plan's tones carry the meaning colours.** Without `kpi_tones` (QBR, CHEFFIN plans) a tile's note falls to the
   accent colour (`${role}Text` with role accent), where the LLM had coloured "+2 pts" green and "-1.4 pts" red by
   meaning. The LLM can still write `note.color`, and did in every rewrite here. The spec's planner change (§6:
   `kpi_tones` filled reliably, look spec V10) decides the default.
4. **`toned` needs plan tones**, but the LLM tints tiles by meaning when the plan has none (CHEFFIN slides 1 and 4:
   negative / positive tiles). The rewrite had to write `filled` + `border.*` + `color` instead. Proposal: let
   `has_tones` also count an item's explicit `color`.
5. **A hero tile in its group's row** needed equal columns (fixed in step 3; the gallery README has the numbers).
