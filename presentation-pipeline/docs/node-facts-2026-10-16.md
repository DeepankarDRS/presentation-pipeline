# Node facts: what the prompts say a node does, checked against POM (2026-10-16)

**Why.** On 2026-10-16 a review found the prompts teaching things POM 10.3.0 does not do (flow "branching /
auto-layout", a flow example with a back-loop drawn across the nodes, "needs explicit w and h", examples
that fixed a free choice — `docs/eval/deck-output-fixes-2026-10-15.md`, last review section). Those were
fixed by hand in `39cf10a`. This doc is the systematic version: every behaviour claim about the six
diagram nodes, checked against POM's source and by compiling a probe slide, plus the machinery that keeps
the next wrong claim out.

**Result.** 56 entries for flow, tree, timeline, matrix, process_arrow and pyramid (§3): **32 wrong,
partly wrong or fixing a free choice** — all fixed in the prompts and knowledge, except two capacity
numbers left to the user (§5) — 17 verified or consistent, 2 unverifiable from source (kept), and 5 POM
behaviours the prompts never taught, now facts. 34 facts, 43 probes, all passing on POM 10.3.0; a POM
upgrade or a wrong fact fails `tests/unit/test_node_facts.py`.

## 1. The machinery

| piece | where | what it does |
|---|---|---|
| facts | `src/knowledge/components/<kind>.yaml` → `facts:` | one sentence per fact, `kind` (syntax / layout / capacity / advice), `for` (planner / generator), `source` (POM file + function), `probes` (tiny slide XML + assertions) |
| open choices | same file → `open_choices:` | attributes the plan chooses per slide (`direction`, tree `layout`) with their values and the fact that states the rule |
| refuted claims | same file → `refuted:` | regex of each claim found wrong + the fact that refutes it; no prompt or knowledge file may state it again |
| probe runner | `src/node/probe-facts.js` | compiles every probe with POM (one node spawn: `buildPptx` + the positioned tree from `geometry.js`, no fit-grow); `--schema` dumps POM's own attribute rules (`coercionRules.js` + the zod schemas in `types.js`: names, types, enum values, required) |
| checks | `src/compiler/node_facts.py` | reads the drawn shapes from each probe's .pptx (position, size, font px, preset), evaluates the assertions; `open_choice_violations`, `flow_link_violations` lints |
| rendering | planner: `{{ facts('<kind>') }}` (jinja global in `slide_component_planner.py`) in the Visual Fitness Guide; generator: `_select_notes` adds the `generator` facts of each kind on the slide; repairer: `select_repair_knowledge` adds them as "How POM draws it" | the prompts say what the facts say, word for word |
| test | `tests/unit/test_node_facts.py` (11 tests) | see below |

What the test enforces:

1. Every syntax / layout fact has probes; every probe holds on POM (43 probes). A control fact that is
   wrong on purpose must fail (guards against assertions that always pass).
2. **Attribute lists come from POM:** every `<Tag>_attributes` block of the six component files and every
   `node_attributes` / `*_values` / `required` in `core/nodes.yaml` is compared with POM's schema dump —
   unknown attributes, missing ones, wrong enum values or required flags fail.
3. No prompt (`src/prompts/**/*.j2`), knowledge value (`src/knowledge/**/*.yaml`) or example
   (`src/knowledge/examples/*.xml`) matches a `refuted` pattern.
4. **Lint, open choices:** a planner JSON example must write every value (`"direction": "horizontal |
   vertical"`); an XML example that sets one (`<Flow direction="horizontal">`) needs the alternatives named
   in the same block (`direction: horizontal | vertical — …`). Tested on a fixed example too.
5. **Lint, flow links:** in every Flow example each connection goes to the next node (fact
   `flow.back_link`).
6. The rendered planner prompt contains each kind's planner facts; the generator notes contain each
   generator fact.

How to add a fact: write the sentence, tag it, give it a probe (`xml` = the node, wrapped in a 1280 × 720
slide with `padding="40"`; `align: stretch` for a stretching parent) and assertions over `ok`, `errors`,
`warnings`, `box` (the node's own box), `t("label")` (the drawn shape with that text: `.x .y .w .h .r .b
.cx .cy .font .geom`), `fills`, `lines`, `near`, `same`, `extent`. When a claim turns out wrong, add its
pattern to `refuted` with the fact that replaces it.

## 2. One fact for all six

`calcScaleFactor` (`renderPptx/utils/scaleToFit.js`): a diagram is drawn at its natural size and shrunk,
text included, to fit its box: `scale = min(boxW / natW, boxH / natH, 1)`. POM never enlarges it; below 0.5
it stops at 0.5, draws past its box and warns `SCALE_BELOW_THRESHOLD`. Without `w` / `h` the box **is** the
natural size (`applyCompositeMeasure` in `registry/definitions/compositeNodes.js`; in a VStack the width
stretches to the parent). In the pipeline, fit-grow's `growDiagrams` then enlarges flow / tree /
process_arrow node sizes to fill their box (not timeline, matrix, pyramid) — so the planner prompt no longer
says "never enlarged", only "shrunk to fit".

| node | natural size (defaults) | what fills / grows with the box |
|---|---|---|
| flow | nodes × 120 + gaps × 80, by 60 (vertical: 120 wide) | nothing; nodes centred |
| process_arrow | steps × 150 − (steps − 1) × 28, by 80 | nothing; chevrons centred |
| timeline | 120 × items by 128 (vertical 180 by 24 + 60 per further item) | dots spread over the box; labels stay 120 px (horizontal) |
| tree | leaves × 120 + gaps × 20 by levels × 40 + gaps × 60 (vertical) | nothing; centred |
| matrix | 220 × 220 | the axes fill the box; dots and labels stay 24 / 11 px |
| pyramid | 400 by 52 × levels − 2 | nothing; at most 400 px wide, centred |

## 3. Inventory with verdicts

Files: planner `src/prompts/slide_component_planner/system.j2` (P), component files
`src/knowledge/components/*.yaml` (C), `core/nodes.yaml` (N), `core/recipes.yaml` (R),
`core/house-style.yaml` (H), `core/capacity.yaml` (K), `knowledge/examples/*.xml` (X). Class: S syntax,
L layout, K capacity, A advice. Probe ids are the facts in the component files.

### flow

| # | claim (where) | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 1 | "Flowchart with auto-layout" (N) | L | **wrong** | `flow.js` places nodes by index; probe `flow.one_line` | fixed, refuted |
| 2 | "Flow needs explicit w and h" / "Missing w/h — will not render correctly" / `w: required` (C) | L | **wrong** | natural size via measure func; probe `flow.wh_optional` (box 1200 × 60, nodes centred) | fixed, refuted |
| 3 | "Decision nodes (shape='decision') auto-size their diamond" (C) | L/S | **wrong** | diamond = nodeWidth × nodeHeight like every node; the shape is `flowChartDecision`; probe `flow.natural_size` | fixed, refuted |
| 4 | "FlowConnection from/to referencing a nonexistent id will fail" (C) | S | **wrong** | `drawConnection` skipped silently (`if (!fromLayout‖!toLayout) continue`); probe `flow.connections#1` | fixed, refuted |
| 5 | (not taught) a Flow with no FlowConnection | S | **new** | POM throws `node.connections is not iterable`; probe `flow.connections#0` | fact |
| 6 | nodes in one line in document order (C, P; `39cf10a`) | L | verified | probe `flow.one_line` (row and column) | fact |
| 7 | "connect neighbours only: one that skips or goes back is drawn through the nodes between" (C) | L | verified, sharpened | a link back to the node just before is also drawn through both nodes; probe `flow.back_link#1` | fact |
| 8 | drawn at nodeWidth / nodeHeight / nodeGap, shrunk, never enlarged, < 50 % overflows (C) | L | verified | `scaleToFit.js`; probes `flow.scale` ×3 | fact |
| 9 | FlowNode `width`: "Override flow-level nodeWidth for this node" (C) | L | **partly wrong** | only the shape; the slot stays nodeWidth → overlaps the neighbour; probe `flow.node_override` | fixed |
| 10 | "Nodes are roughly 120×60px" (P) | L | verified | defaults in `flow.js` / `measureFlow` | fact |
| 11 | "a horizontal row of nodes in half the slide is drawn at half size" (P) | L | roughly right | 5 nodes need 920 px | replaced by `flow.natural_size` |
| 12 | recipe flow with `c → b "No"` (R); example `check → ingest "No"` (X) | L | **wrong teaching** | back link drawn across the nodes (#7) | fixed; lint `flow_link_violations` |
| 13 | "FlowNode text MUST be >= 14pt" (R), "FlowNode / Timeline fontSize >= 14" (H) | S | **wrong** | FlowNode has no fontSize: text is 14 px × scale (`flow.js`); Timeline has none either | fixed, refuted |
| 14 | "short node text (6+ overflows at default nodeWidth)" (R) | A | unverifiable from source | needs a render (text wrap inside the shape) | kept |
| 15 | direction examples all `horizontal` (C, R, X) | A | **fixed a free choice** | 36/36 saved plans horizontal (deck-output-fixes review) | examples name both values; lint |

### process_arrow

| # | claim | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 16 | "ProcessArrow needs explicit w and h. w=max works; h must be a pixel number" (C) | L | **wrong** | probe `process_arrow.wh_optional` | fixed, refuted |
| 17 | "Horizontal needs the full slide width" (P), "(full slide width)" in the routing and component tables (P), "full slide width" (C note), "ONE row: give it full width" (R, H) | L | **wrong as stated** | 4 steps are 516 px, 5 are 638 px at full size (`measureProcessArrow`); a half-width box (~580 px) holds 4 unshrunk; probe `process_arrow.natural_size` | replaced by the facts (P); recipes / house-style: "horizontal across the full width, vertical in a narrow card" |
| 18 | "roughly 150×80px" (P) | L | verified | defaults | fact |
| 19 | `gap`: "can be negative for overlap" (C), example `gap="8"` | S | **partly wrong** | the default is already −0.35 × itemHeight (the chevrons interlock); `gap="8"` in the example switched that off | fixed (example uses the default) |
| 20 | labels > 2 words clip / wrap (C, P, H) | K | consistent | label box 94 px (first 122 px) at 14 px; probe `process_arrow.label_box` | fact explains it |
| 21 | "Give a horizontal ProcessArrow h>=80 if labels must be two words" (C) | L | **wrong** | the box h does not size the chevrons (itemHeight does; the row is centred) — `renderHorizontalProcessArrow` | removed |
| 22 | "More than 5 steps, or a horizontal one in a half-width card, breaks labels" (C) | K | consistent | 6 steps = 760 px → 0.76 scale in 580 px; label font 10.7 px | kept |
| 23 | "No newlines in a label — they do not render as line breaks" (C) | S | unverifiable from source | needs a render | kept |
| 24 | (not taught) vertical is 150 px wide | L | **new** | probe `process_arrow.vertical` | fact |

### timeline

| # | claim | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 25 | "Timeline needs explicit w and h — it does not auto-size" (C) | L | **wrong** | probe `timeline.natural_size` (360 × 128 for 3 items) | fixed, refuted |
| 26 | "Full sentences WILL collide — each column is only w/N px wide" (R) | L | **wrong** | every label is 120 px × scale wide, centred on its dot, whatever w / N (`renderHorizontalTimeline`); probe `timeline.horizontal` | fixed, refuted |
| 27 | "Too many items (>5) in horizontal mode will cause cramping" (C), capacity "labels collide past 5" (K) | K | **partly wrong** | labels overlap only when the dots are < 120 px apart: `(boxW − 120) / (items − 1) < 120`. 5 items need ≥ 600 px; a full-width timeline (1180 px) holds 9 without overlap (probe: 7 items, no overlap). What does break at full width is a title over ~2 words (120 px box). | pitfall rewritten; **capacity number left for the user** (§5) |
| 28 | "rendered at fixed small sizes" (P) | L | verified | date 12, title 14 bold, description 11 px, × scale | fact |
| 29 | "Each item has date + title + description" (P) | S | true for POM, not for the plan | the plan's `timeline_items` carry date + label | reworded |
| 30 | (not taught) TimelineItem `description`, Timeline `descriptionColor` (C, N) | S | **missing** | `coercionRules.js` TimelineItem; probe `timeline.description` | added (schema test) |
| 31 | (not taught) vertical titles run the box width − 80 px | L | **new** | probe `timeline.vertical` | fact |
| 32 | "Use horizontal for left-to-right chronology, vertical for top-to-bottom roadmaps" (C) | A | fixed nothing, no reason | — | replaced by `timeline.direction` (from the box and the label length) |
| 33 | direction example `horizontal` (C, R, X) | A | **fixed a free choice** | 55/55 saved plans horizontal | alternatives named; lint |

### tree

| # | claim | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 34 | `nodeShape` default `roundRect` (C) | S | **wrong** | `tree.js`: `nodeShape ?? "rect"`; probe `tree.node` (preset `rect`) | fixed, refuted |
| 35 | "Tree needs explicit w and h" (C) | L | **wrong** | probe `tree.natural_size` (400 × 140) | fixed, refuted |
| 36 | "exactly one root TreeItem — multiple roots will fail" (C) | S | verified | `convertTreeChildren`; probe `tree.one_root` | fact |
| 37 | `levelGap` "Vertical gap", `siblingGap` "Horizontal gap" (C) | S | **partly wrong** | they swap with `layout="horizontal"` | notes fixed |
| 38 | TreeItem `color` "overrides parent level" (C) | S | **wrong** | no inheritance: a node without color is 1D4ED8 | fixed |
| 39 | "≤ 3 levels, labels 2–3 words", "Nodes roughly 120×40px" (P) | K/L | verified defaults; depth advice incomplete | a vertical tree's width is its leaves × 120 + gaps: breadth shrinks it more than depth | fact `tree.natural_size` |
| 40 | "Deep trees (5+ levels) … overflow" (C) | K | consistent | height = levels × 40 + gaps × 60 | merged into a breadth pitfall |
| 41 | layout example `vertical` (C, R) | A | **fixed a free choice** | 22/22 saved plans vertical | alternatives named; lint |

### matrix

| # | claim | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 42 | "Matrix needs explicit w and h; h must be a pixel number (>=200)" (C) | L | **wrong** | natural 220 × 220; probe `matrix.fills_box#1` | fixed, refuted |
| 43 | MatrixQuadrants: each label optional (C, N) | S | **wrong** | zod `matrixQuadrantsSchema`: all four required when the element is there (`Missing required attribute "quadrants"`); probe `matrix.quadrants` | fixed |
| 44 | MatrixItem x / y 0–1 (C, N) | S | verified | `z.number().min(0).max(1)`; probe `matrix.coordinates` | fact |
| 45 | "item labels are drawn beside the dot" (C), "the label renders BESIDE the dot" (H) | L | **wrong** | drawn in a 100 px box just above the dot; probe `matrix.labels` | fixed, refuted |
| 46 | "no collision avoidance and no leader lines" (C) | L | verified | `matrix.js` draws at fixed offsets | fact |
| 47 | (not taught) the map fills its box; dot and label sizes never grow | L | **new** | probe `matrix.fills_box`, `matrix.labels` | fact |
| 48 | "4 items safe max, 1-word labels, no two within 0.18, ≥ 520 px wide" (C, R, H) | A | consistent | labels 100 px wide at 11 px, spacing grows with the box | kept |

### pyramid

| # | claim | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 49 | "The POM renderer divides the total Pyramid height equally among levels" (C) | L | **wrong** | bands are 50 px × scale whatever the height; probe `pyramid.size` (h=600 → 50 px bands) | fixed, refuted |
| 50 | "fontSize MUST scale down with level count to prevent overflow" (C, R, H) | A | **reason wrong** | band height never changes with the count; what shrinks is the top band's width (400 / levels px) | sizing_rules rewritten; the font steps (16 / 15 / 14) kept as advice |
| 51 | "Missing h on Pyramid — it needs a pixel h" (C) | L | **wrong** | natural 400 × (52 × levels − 2); probe `pyramid.size#1` | fixed, refuted |
| 52 | "w='max' grows its HEIGHT, not its width" (C) | L | verified | probe `pyramid.w_max` (box 609 px tall, drawing 400 px, `NODE_OVERLAP`) | fact |
| 53 | "never scales up" (C, R, H) | L | verified | 400 px base max | fact |
| 54 | "up: first level = top / narrowest", default white text (C) | L/S | verified | probe `pyramid.bands`; `pyramid.js` | fact |
| 55 | "Labels must be 3-6 words max" (P) | K | **inconsistent with the geometry** | the top band of 5 levels is 80 px wide | P: "1-2 words on the top levels, up to 6 on the wide bottom bands" |

### all six

| # | claim | class | verdict | evidence | action |
|---|---|---|---|---|---|
| 56 | "drawn at their own size … shrunk … never enlarged" (P) | L | true for POM, not for the pipeline | fit-grow `growDiagrams` enlarges flow / tree / process_arrow nodes | "never enlarged" dropped |

Unverifiable from source (kept): #14, #23, the 2026-09 render notes behind #22 and #48, and the palette /
contrast advice (`text_color_rules`). They need a render, not a compile.

## 4. Other changes

- `nodes.yaml` (the generator's allowed attributes): Timeline `descriptionColor`, TimelineItem
  `description`, ProcessArrow `highlight` added; MatrixQuadrants `required`.
- Planner prompt: the six diagram entries render their facts; the direction paragraph keeps the shared rule
  and points to the entries. Rendered planner system prompt: 42.9k → 45.5k characters (+6 %). Generator:
  each diagram on a slide adds its generator facts (0.6–1.5k characters) and loses the wrong pitfalls.
- Examples now show the choice: component `structure` blocks, recipes and `examples/*.xml` name both
  values beside the one they draw (flow and process_arrow structure examples draw `vertical` /
  `horizontal` respectively, so the two directions are both shown).

## 5. Open, for the user

- **Timeline capacity** (`capacity.yaml` `timeline.items: [3, 5]`, "labels collide past 5"): the
  collision limit depends on the box width (#27). Keep 5 (it also bounds the title wrap), or make the
  plan check box-aware? Not changed — it changes plan checks (`enforce_capacity` turns a long timeline into
  cards).
- **Timeline `max_label_words: 3`**: a 3-word title at 14 px bold does not fit the 120 px label box on one
  line (horizontal). The vertical direction fits it. Not changed for the same reason.

## 6. What remains for the other nodes

Same pattern (facts + probes + schema check + refuted + open choices), in order of how much the prompts
claim about them:

| node | claims to check first | schema source |
|---|---|---|
| Table (`table.yaml`, house-style tables, fit-grow table sizing) | row height / `defaultRowHeight`, column widths, cell text size, cells top-anchored (pptx-post), rows past the box | `table` + `Td` / `Col` coercion |
| Chart (`chart.yaml`) | axis text black on dark themes, legend / title space, sparkline, `chartColors` literal only | `chart` + zod `chartTypeSchema` |
| Ul / Ol / Li (`list.yaml`) | no indent control, bullet spacing, `items` | `ul`, `ol`, `Li` |
| Text / Span (`text.yaml`) | line breaks around inline tags, `w="max"` sizes to content, lineHeight | `text`, `Span` |
| Shape / Icon (`shape.yaml`, `icon.yaml`) | roundRect radius, text inside a pill, icon names (`icon-names.txt` vs `ICON_DATA`) | `shape`, `icon` |
| Layer / Line / Arrow (`drawing.yaml`) | absolute x / y, Arrow targets, "Layer MUST have explicit pixel w and h" | `layer`, `line`, `arrow` |
| VStack / HStack (house-style, generator system prompt) | `w="max"` = flex grow on the main axis, `grow`, stretch | `vstack`, `hstack` |
| card_grid recipe `layout` values in planner examples (`"card_layout": "grid"`) | an open choice the examples fix (grid in 3 / 3 examples) | our own schema |

`probe-facts.js --schema` already reads every tag's coercion map; extending `DIAGRAMS` there and
`DIAGRAM_TAGS` in `node_facts.py` is the only code change per node.

## 7. Checks

- Unit tests: before 1155 pass + the 4 known failures; after **1166 pass + the same 4** (11 new in
  `tests/unit/test_node_facts.py`; `test_planner.py` updated where it pinned the refuted "full slide width"
  text; `test_py311_syntax.py` passes in the full run).
- The lints found what the 2026-10-16 hand review had missed: `nodes.yaml` "auto-layout", the recipe and
  `examples/flow-slide.xml` back-loops, six recipe / example directions without alternatives.
- No paid run made. Proposed paid check: §8.

## 8. Proposed paid check (not run)

Prompt text changed (planner diagram entries, generator notes, recipes), so one run on cases with
diagrams, to see that the planner chooses directions from the space and that diagrams compile first try:

```bash
uv run python -m scripts.eval_run gate-deck-xtsy-qcomm gate-deck-all-nodes-dense --repeat 1 --label node-facts --bundle
```

Cost ≈ $0.6, ceiling $0.8 (XTSY ≈ $0.3: the 2026-10-15 eval of two decks cost $0.585; the dense
all-nodes deck has 6 slides with 17 components, ≈ $0.3 at ~$0.05 per slide). The dense deck puts several
diagrams on one slide, which is where the direction choice matters. What to look for:
directions mixed where diagrams share a slide (not 100 % horizontal), no diagram drawn below 75 %, no
flow connection that goes back, no `Missing required attribute "quadrants"` / `connections` compile
errors, matrix labels unchanged, repairs per slide not higher than the last run.
