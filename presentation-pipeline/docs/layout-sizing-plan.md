# Layout Sizing Plan: let POM allocate, compute only what POM can't

Status: proposed (2026-09-23). Branch `feat/golden-reference-grounding`.
Step 1 built 2026-09-24 on `phase-1-sizing` — results and findings in `docs/roadmap-derived-components.md` Phase 1.
Scope: how bands, cards and pixel-based nodes (Chart, Table, Flow, Tree,
ProcessArrow, Timeline, Matrix, Pyramid) get their size — and why slides end
up half empty or overflowing.

Every "fact" below was verified against the installed `@hirokisakabe/pom`
10.3.0 (source in `src/node/node_modules/@hirokisakabe/pom/dist`, the official
docs in the POM repo `packages/pom/docs/*.md`, or an experiment whose numbers
are quoted). Nothing here assumes a POM feature that does not exist.

---

## 1. The problem

Today the generator (an LLM) is asked to do pixel arithmetic: `house-style.yaml`
`height_budget` / `worked_example` tell it to pick `h="300"` for a chart,
`h="240-360"` for a table, etc. It is bad at arithmetic, and POM then resizes
those boxes in ways the prompt does not describe. Result: boxes much larger
than their content (tables with dead space, 60px Flow nodes in a 560px card,
KPI rows at 2x their `h`), or overflow. `src/node/fit-grow.js` repairs some of
this after the fact; this plan removes most of the cause.

## 2. Verified facts (POM 10.3.0)

| # | Fact | Evidence |
|---|---|---|
| F1 | `w="max"` / `h="max"` = `flexGrow=1` on the **parent's main axis**. In a VStack, `w="max"` grows the **height** and overrides a numeric `h`. Width in a VStack comes from `alignItems="stretch"` (the default). | POM docs `layout-system.md` ("Fill Available Space"); `calcYogaLayout.js applyStyleToYogaNode`; fixture s1: `h="150"` KPI row rendered 300px |
| F2 | `grow="N"` shares remaining main-axis space by ratio and takes precedence over `max`. `minH`/`maxH`/`minW`/`maxW` clamp. | POM docs `layout-system.md`; experiment: bands `grow=2`/`grow=1` → 385px / 195px; cards `grow=3`/`grow=2` → 709px / 483px |
| F3 | A Chart with `h="max" minH="160"` and **no pixel h** fills its card and renders correctly. | experiment render (scratch `exp.xml`) |
| F4 | A Table with **no `h` and no `w`** in a stretching VStack sizes to exactly Σ row heights at full width; `<Tr height="52">` sets one row. Text placed after it follows directly. | experiment: table 452×84 = 32 + 52; `tableUtils.calcTableIntrinsicSize`, `parseXml.js` `Tr` height |
| F5 | Table rows never grow with their text; `<Td>` has **no vertical-align**; columns without `<Col width>` split equally. | `tableUtils.resolveRowHeights/resolveColumnWidths`; `coercionRules.js` `Td` |
| F6 | All six diagram renderers use `resolveScaledContentArea`: scale = min(box/intrinsic, 1) — never above 1. What it scales differs: **Matrix** quadrant area fills the whole box; **horizontal Timeline** line spans full width but items stay ~128px tall, centred; **Pyramid** fixed 400w × ~52px/level, centred; **Flow/Tree/ProcessArrow** nodes stay at intrinsic size. | `renderPptx/nodes/{matrix,timeline,pyramid,flow,tree,processArrow}.js`, `measureCompositeNodes.js`, `utils/scaleToFit.js` |
| F7 | Size attributes that exist: Flow `nodeWidth/nodeHeight/nodeGap`; Tree `nodeWidth/nodeHeight/levelGap/siblingGap`; ProcessArrow `itemWidth/itemHeight/gap/fontSize`. Timeline/Matrix/Pyramid have none. | `coercionRules.js` |
| F8 | Every generated .pptx declares font **"Noto Sans JP"** (default). Office machines normally lack it, so PowerPoint substitutes → wrapping differs from POM's measurement. `<Theme>` holds colours only (no font). `Text/Ul/Ol/Shape/Td/Timeline` accept `fontFamily`; Flow and Pyramid labels are hard-coded "Noto Sans JP". | pptx `typeface` inspection; `parseThemeElement`; `renderPptx/nodes/flow.js` |
| F9 | `buildPptx(xml, size, { fonts: [{ name, data }] })` registers real font metrics for measurement (not embedding). Carlito bytes registered as "Calibri" measure **identically** to Calibri (433.0 px = 433.0 px); Liberation Sans = Arial (470.7 = 470.7). Both are SIL OFL fonts. | POM docs `text-measurement.md`; experiment `font.mjs` |
| F10 | 10.3.0 is the latest POM release; since then only dependency/editor commits. No upstream work on scale-up, Td valign or row auto-height. Open #682 is a dagre layout PoC for Tree/Flow. | npm `versions`, GitHub commits + issue search, 2026-09-23 |

## 3. Decision

Three layers, cheapest first. Most of the fix is **grammar**, not code.

| Layer | What | Code cost |
|---|---|---|
| A. Grammar | Generator expresses *weights and minimums* with POM's own `grow` / `h="max"` / `minH`; POM's flexbox does the allocation (F1–F4). | Prompt/YAML edits + one audit rule |
| B. Measure | Register the real font's metrics so POM's measurement matches PowerPoint (F8, F9). | ~30 lines + one font file |
| C. Compute | Only what POM cannot size itself: table column widths / row heights (F5), Flow/Tree/ProcessArrow node sizes (F6, F7) — extensions of the existing `fit-grow.js`. | Small, per node type |

Not possible with 10.3.0 without composing or upstream changes: vertically
centred table cells, enlarging Timeline height / Pyramid / diagram labels
(F5, F6). Section 5 covers how to live with that.

## 4. Steps (in order)

Record a baseline first: `pytest tests/unit -q` (known: 4 pre-existing
failures) and the fit-grow regression below.

### Step 1 — Grammar: allocation by `grow`, not pixels (Layer A)

Files: `src/knowledge/core/house-style.yaml`, `src/knowledge/core/recipes.yaml`,
`src/prompts/generator/user.j2` (text-limit line), `src/prompts/generator/system.j2`
(if it repeats sizing rules).

Rules to teach (each backed by F1–F4):

1. **Width in a VStack comes from stretch.** Never put `w="max"` on a child of
   a VStack; omit `w` (or use `%` only inside an HStack). `w="max"` is for
   children of an **HStack** only.
2. **Height is shared by `grow`.** Map the planner's component weight to
   `grow` on the band/card: hero `grow="3"`, peer `grow="2"`, supporting
   `grow="1"`, minor → no `grow` (content-sized). Text-only bands keep no `h`.
3. **Chart:** `<Chart h="max" minH="…">` inside its card; the card gets the
   weight's `grow`. `minH` = readability floor (start: 180; tune from renders).
   No pixel `h`.
4. **Table:** no `h`, no `w`. The card that holds it gets **no `grow`**
   (content-sized) so there is no dead space (F4, F5).
5. **Flow / Tree / ProcessArrow:** `h="max" minH="…"`; node sizes are filled in
   by fit-grow (Step 4).
6. **Timeline / Pyramid:** size the box to the diagram, not the diagram to the
   box: horizontal Timeline `h="150"` and no `grow`; Pyramid `h` ≈ 52 × levels
   + 20 and no `grow` (F6). **Matrix** may take `h="max" minH="260"` (it fills).
7. Keep one overflow rule: the sum of `minH`s + text bands must fit 720; POM's
   autoFit still shrinks if not.

Remove / rewrite in `house-style.yaml`: the `'w="max"'` vocabulary entry
("DEFAULT for anything that should stretch"), `'h="188" (fixed px)'` ("REQUIRED
on rigid nodes"), `height_budget` + `worked_example` arithmetic, `rigid_nodes`
("MUST be an explicit pixel h"), the checklist items about adding up heights,
and `weight_allocation` (replace by the weight → `grow` table). Update the
matching recipes in `recipes.yaml`.

Also change `src/compiler/layout_audit.py`: `_check_missing_dims` currently
flags any Chart/Table/diagram without both `w` and `h` (`_NEEDS_DIMS`). New
rule: Table needs neither; Chart/Matrix/Flow/Tree/ProcessArrow need `h`
(numeric or `max`) and, if `max`, a `minH`; Timeline/Pyramid need numeric `h`.
Update `tests/unit/test_layout_audit.py` accordingly.

Verify:
- Hand-write 3 slides in the new grammar (dashboard, table+text, flow) under
  `tests/fixtures/layout_sizing/`; compile; render; check no dead space.
- Golden set still compiles: `python -m scripts.render_check --in tests/fixtures/golden --out output/render_check_golden` (golden files use the old style; they must keep working, since POM semantics don't change).
- Generate 5 regression cases (`python -m src.runner …`) and compare renders
  before/after.

### Step 2 — Real font metrics (Layer B)

1. Vendor `Carlito-Regular.ttf` and `Carlito-Bold.ttf` (SIL OFL; include the
   licence file) under `src/node/fonts/`.
2. `compile-pom.js`: pass `fonts: [{ name: "Calibri", data: regular }, { name: "Calibri", data: bold, weight: "bold" }]`
   to `buildPptx` (F9). fit-grow's `createBuildContext` gets the same list so
   its measurement matches.
3. Normalizer (`src/compiler/normalizer.py`): add `fontFamily="Calibri"` to
   every `Text`, `Ul`, `Ol`, `Shape`, `Td`, `Timeline` that has no
   `fontFamily` (F8). Flow/Pyramid labels stay Noto Sans JP (hard-coded in POM).

Why Calibri: installed with Office, so the PowerPoint machine renders exactly
what POM measured. If the house style wants another face, only a
metric-compatible OFL twin can be vendored (Liberation Sans for Arial).

Verify: compile the fit-grow fixtures; open on the PowerPoint machine; wrapped
lines must match `fitted.xml` expectations; fit-grow's `LOW_FILL` and the
85% heading margin can then be re-tuned (they compensate for the old drift).

### Step 3 — Tables sized from content (Layer C)

Extend `fit-grow.js` (new phase, before `fitTables`), only when the table has
no `<Col width>` set by the generator:

- **Column widths** (HTML auto-layout, simplified): per column, `min` = widest
  single word, `pref` = widest cell text on one line (measured with
  `measureText`). If Σpref ≤ table width → widths ∝ pref; else give each its
  `min`, share the rest ∝ (pref − min). Write `<Col width>`.
- **Row heights**: per row, lines of the tallest cell at its column width ×
  fontSize × 1.3 + 8 → write `<Tr height>` when above the default 32 (F4).
- Keep the existing row-growth / box-clamp phase for leftover space.

Verify: `tests/fixtures/fit_grow/s5-review-edge-cases.xml` (long cells) — no
cell text outside its row; golden tables unchanged or better.

### Step 4 — Diagram node sizes (Layer C, mostly exists)

Already in `fit-grow.js` (`diagramEdit`) for Flow/Tree/ProcessArrow. Two
changes once Step 1 lands:
- it runs on the grown `h="max"` box, so the absorb-card-slack step (2a) and
  `respectHeights` (phase 0) become safety nets for old-style XML only;
- add a Tree fixture (none exists; the Tree path is untested).

### Step 5 — Critic uses measurements

`compile-result.json.fitGrow` already lists what was changed. Add per-card fill
ratios to it and pass them to the visual critic as data, so "large empty
area" is a measured fact instead of a guess from the screenshot.

## 5. What stays impossible in 10.3.0 and how to handle it

| Limit | Handling |
|---|---|
| Td vertical-align (F5) | Keep rows tight to text (Step 3) so there is nothing to centre. |
| Timeline height, Pyramid, diagram label size (F6) | Size the box to the diagram (Step 1 rule 6). For a bigger visual, compose it from `VStack`/`HStack`/`Shape`/`Line`/`Text` as a recipe (they flex like everything else) — consistent with the "core nodes fixed, derived components composed around them" rule. |
| Flow/Pyramid label font is Noto Sans JP | Accept; labels are short. |
| Upstream | Optional issues to the POM author (GitHub `hirokisakabe/pom`): Td `verticalAlign`, opt-in scale-up for diagrams, row auto-height. Do not depend on them; do not patch `node_modules`. |

## 6. Risks

- **Generator compliance**: it may keep writing pixel `h`. Old-style XML still
  compiles (POM semantics unchanged) and fit-grow still repairs it; the audit
  rule (Step 1) makes violations visible.
- **`minH` too high** on several cards → autoFit shrinks text. Start low, tune
  from renders.
- **Font change is visible**: slides switch from Noto Sans JP (as substituted
  on the viewer's machine) to Calibri. Confirm the look with the user before
  Step 2 ships.
- **Golden fixtures** are old-style; keep them as a compatibility suite, and
  add new-style fixtures rather than rewriting them.

## 7. Regression commands

```bash
# fit-grow + golden compile check (with vs without the pass)
for f in tests/fixtures/fit_grow/*.xml tests/fixtures/golden/*.xml tests/fixtures/golden/gj-h1-deck/*.xml; do
  n=$(basename "$f" .xml)
  node src/node/compile-pom.js "$f" "output/reg/$n"
  POM_FIT_GROW=0 node src/node/compile-pom.js "$f" "output/reg0/$n"
done
# render one to PNG (this machine: LibreOffice; PowerPoint machine: src/compiler/screenshot.py)
soffice --headless --convert-to png --outdir output/reg/<name>/png output/reg/<name>/presentation.pptx
pytest tests/unit -q
```
