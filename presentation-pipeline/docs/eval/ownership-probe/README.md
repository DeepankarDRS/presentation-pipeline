# Who owns what: free probe (2026-11-03)

`python -m scripts.ownership_probe` builds 10 hand-written slides that mix the three layers. Each one goes the validator's
way: `composed.expand` → `tiles.fill` → deck font → normalize → `compile-pom.js` (fit-grow, pptx-post) → LibreOffice with
Inter. The palette is corporate-slate. `POM_BLOCKS=tiles` and `POM_NODES=kpi_row,card_grid,chart,table,timeline,process_arrow,flow`.
Sheet: [sheet.png](sheet.png). Every issue and the fit-grow log are in [results.json](results.json). The slides are in
`output/ownership-probe/<case>/` (`tiles.xml` = what the "LLM" wrote, `in.xml` = after code, `fitted.xml`).
No API key and no paid run.

| Case | What the slide mixes | Rendered | Node codes | Result |
|---|---|---|---|---|
| a | `<KpiRow ref variant="rows">` in an LLM card with `item.borderLeft.color="$tone"`, `value.color="$toneText"`; `<Chart ref variant="native labelled">` with box attributes and `label.color` | yes | none | **holds.** Each styling attribute shows (tone edges, tone numbers, the chart card, the label ink). The LLM's layout around the refs is kept |
| b | `<Table ref variant="ledger" header.backgroundColor>` above an LLM-written native `<ProcessArrow>` (token colours) | yes | none | **holds.** Native and ref nodes sit side by side. The native chevrons are small (64 px), and "Re-budget" breaks in its chevron. This is the reason process_arrow was dropped as a node, and it stays the LLM's problem |
| c1 / c2 | KPI row + 4 cards; an LLM `<Layer position="absolute">` of `<Line>` arrows at the pixels of the un-grown layout; fit-grow off / on | yes | none | **lands** (ends ≤ 14 px from the anchor). fit-grow here only fixes spills (text heights) |
| c5 / c6 | sparse slide (KPI row + 2 short cards, both `grow`), same test | yes | none | **lands** (≤ 14 px off with fit-grow off, ≤ 9 px with it on). fit-grow grows text and moves icons *inside* the boxes. Flex `grow` had already fixed the box positions |
| c3 | POM `<Arrow from to>` on the ids the docs suggest (`kpiv-kpis-0`, `card-levers-2`) | yes | none (compile warning `ARROW_REF_NOT_FOUND` ×2) | **fails silently.** No arrow is drawn. Code wrote `kpiv0-kpis-0` (a weight rank), and `card-levers-2` is a VStack, which POM cannot connect |
| c4 | `<Arrow from to>` on the ids code really wrote (`kpiv0-kpis-0` → `cardt-levers-0`) | yes | none | **holds.** POM's connector attaches to the Text boxes wherever layout puts them. It attaches to the title's *box* edge, which spans the card, not the word |
| d1 | `<Chart ref>` and `<KpiRow ref variant="rows">` inside LLM-drawn cards | yes | none | **holds** |
| d2 | ref-in-ref: `<KpiRow ref>` inside `<CardGrid ref>`, `<Chart ref>` inside `<Table ref>` | yes | `NODE_ATTR_DROPPED` ×2 (report), `NODE_ITEM_MISSING` ×4 (error) | **partly caught.** Both inner refs are removed. The KPI loss is an error and goes to repair, but the message names the old tag `<KpiGrid ref>`. **The chart is lost silently**: a report-level "children removed", and no error that `roas` is no longer on the slide |
| e | content attributes: `fontSize`, `value.fontSize`, `value.text`, `label.fontFamily`, `id`, hex `item.backgroundColor` on KpiRow; `chartType`, `title`, `showTitle`, `chartColors`, `x`, `y` on Chart; `defaultRowHeight`, `label.fontSize` on Table; invented `kpi_values`, `table_rows` | yes | `NODE_ATTR_DROPPED` ×12 (report), `LITERAL_COLOR` (warning), `NODE_ATTR_UNKNOWN` ×4 (error: `x`, `y`, `kpi_values`, `table_rows`) | **holds for content.** No typed value, title, chart type, size or font reaches the slide. But the 4 unknown names are errors, so in the graph this slide would cost a repair call although code already drew it correctly |

## What this says about the model

1. **The layer split holds where the nesting is one level deep** (a, b, d1): the LLM's stacks, cards and native nodes
   wrap the refs, and its style attributes land.
2. **Code ownership of content holds** (e): every content attribute is dropped or rejected.
3. **Layers over blocks: the pixels are not the problem, knowing them is.** fit-grow kept box positions within
   ≤ 6 px in both the dense and the sparse slide, because flex `grow` fixes the boxes and fit-grow changes what is inside
   them. The real gap: the LLM writes `<KpiRow ref/>` and never sees where code puts the tiles, so it can only guess
   coordinates. c1–c6 were given the un-grown pixels, which the generator never has. Two fit-grow phases *do* move
   boxes and were not triggered here: `regridTiles` (a row of 4 becomes 2 × 2) and `fillLoneRows`. A pixel layer over
   such a block would miss.
4. **Anchoring to ids works in POM today** (c4: `<Arrow from to>` follows the boxes), but the ids are not a contract.
   They carry weight ranks (`kpiv0-`), part prefixes (`cardt-`), and the boxes cannot be connected (VStack). A guessed id
   gives only a compile warning, and the arrow disappears (c3).
5. **Ref-in-ref is not one rule today.** Each expander removes foreign children in its own way. The plan-level check
   that would catch a component dropped from the slide, `validate.check_skeleton` (`NODE_MISSING`,
   `NODE_CHILDREN_DROPPED`), exists but is not wired into `validator.py`.
