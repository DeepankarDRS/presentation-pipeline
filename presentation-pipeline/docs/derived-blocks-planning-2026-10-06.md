# §14.6 planning session — drafts for approval (2026-10-06)

Branch `feat/derived-blocks-step0`. **No pipeline code changed in this session.** This file holds the
drafts the session produced; nothing here is decided until a row in §6 says so, with a date (the machine
clock, 2026-10-05; the file name keeps the kickoff's 10-06).
Unit-test baseline recorded before any change (build PC, `uv run pytest tests/unit -q`):
**572 pass, 4 known failures** (`test_critic_medium_only_passes`, `test_font_at_minimum_ok`, the two
`*_budget_exhausted*` routing tests). The 557 in older notes is stale.

## 1. Theme source and cross-deck variety (§14.9 proposals)

### 1a. Theme source — recommendation: one palette, derived role tokens, a contrast check

**Decided by the user, 2026-10-05 (D1): adopted as written below.**

**Today there are two colour sources that cannot agree on one slide:** the LLM skeleton uses the deck's
`<Theme>` (`palettes.yaml`, 16 palettes, 12 tokens, picked by `style_resolver` from the brief / UI
theme or the `corporate-slate` default), and the blocks use `style_packs.yaml` (own colours, own
fonts). On a §14.6 slide the LLM's free text and the blocks share one canvas, so they must read one palette.

**Recommended design**
1. **`palettes.yaml` is the only colour source.** A style pack carries structure only (type scale,
   badge / rule options, card border, ghost numerals, fills rhythm, headline style) and no colours.
2. **Derived role tokens, added to the slide's `<Theme>` by code** (not by the LLM), so the skeleton
   prompt can use them too: `panelInk` (text on `surfaceAlt`), `darkFill` + `onDark` (hero / inverted
   tiles, dark table header), `onAccent` (text on accent fills), `accentOnDark` (labels on dark).
   Each is chosen from the palette's own colours by contrast: pick the first of
   `{textMain, surface, white, black}` that reaches 4.5:1 on the background (3:1 for ≥ 24 px text).
   Dark palettes get `darkFill` = a step lighter than `surface`, not black.
3. **A contrast check** at resolve time over every (text role, background role) pair the blocks use,
   reusing `layout_audit._check_contrast`'s maths (a second copy lives in `normalizer.py`; use one).
   A pair under the limit is auto-fixed from the candidates; if none passes, `THEME_CONTRAST` is
   logged and the palette is flagged. A unit test runs all 16 palettes × all packs (this is the
   test that would have caught §14.9 finding 3).
4. **Fonts:** every production pack uses Inter + JetBrains Mono (OFL; the files POM measures with
   and the font embedding ships). Segoe UI / Consolas packs stay experiment-only. More OFL
   families later; they would need files in `src/node/fonts/` and an embed entry.
5. **Picking a look when the brief names no colours:** each palette carries `pack:` (palette → pack, one
   choice not two). The outline planner gets one enum field `look` (palette name, listed with its
   `tone:` line; dark palettes only if the brief asks), written when no theme came from the UI or case.
   Zero extra calls; the choice is logged in the manifest and shown in the UI for override.
6. **When:** the role tokens + contrast test + `pack:` mapping are **step 1** (they live in
   `src/compiler/blocks/`). The `look` field is **step 2**, measured in step 3 as a side check (6 picks).
   Step 3's arms keep step 0's theme so slots vs off differ only by the slot route. The 1a blind sheet
   needs the role-based recolouring in the *research* renderer (`pack_replay.from_palette` + `render.py`
   text roles), about half a day, because both arms must show the same palette (§4).

Cost: nothing paid. Risk: gpt-5-mini picks an odd palette → logged, user override, a short tone list,
light-only default. *Rejected:* choosing by hash or keyword (arbitrary / brittle); a separate LLM call
(extra latency for a one-word decision).

### 1b. Cross-deck variety — recommendation was a kill criterion; decided: within-deck only, cross-deck informational

**Decided by the user, 2026-10-05 (D2): the kill criterion stays within-deck only** (slots not more than 0.05
below the off arm). The cross-deck sameness and house-template numbers below are still computed and
reported in 1a and step 3, informational, with their counts; they are not a pass / fail. If they show a
house look, that goes back to the user as a finding. The recommendation as drafted (kill criterion) is
kept below for the record.

Equal layouts across decks are expected when the *content* is the same shape (a KPI row over a table is
the natural layout twice). So the metric must hold content fixed. Definitions (script
`scripts/variety.py`, shared by 1a and step 3, run on the skeleton XML of the slots arm and the XML
of the off arm):
- **Layout signature (fine):** container tree of the slide body after dropping the header and
  decoration: for each Stack its orientation and children; leaves are `text`, a slot's component kind,
  or the native node class (`Table`→table, `Chart`→chart, `Ul`→bullets …); each child's share of the
  parent's width (or height) is bucketed narrow ≤ 33% / mid / wide ≥ 60%. Single-child containers are
  flattened. **Coarse signature:** same, sizes dropped.
- **Within-deck variety** = distinct fine signatures ÷ content slides, per deck, averaged. Kill if slots
  falls more than 0.05 below the off arm.
- **Cross-deck sameness** = among content slides that share the same component-kind multiset and come
  from ≥ 2 decks, the share of pairs with an identical coarse signature. Kill if slots exceeds the off
  arm by more than 10 points.
- **House-template share** = share of all content slides using the single most common coarse
  signature. Kill if above max(off arm, 25%).
- With ≈ 24 slides these are indicative, not tight (state the counts next to each figure). The
  variant choice distribution (which names the LLM picks) is reported as a fourth number, informational.

## 2. Step 0 plan

**Approved by the user 2026-10-05 (D3), run set decided in D4: six cases.** The `gj-h1-regen` recommendation below
was declined; read the run block as six cases, ≈ $1.8.

**Goal:** make the plans the blocks will read trustworthy, and measure what every call costs.
Everything is verified LLM-free first; one paid run at the end.

### Order and files

| # | Item | Files | Why this order |
|---|---|---|---|
| 0.1 | **Usage logging** | `src/utils/llm_client.py` (`extract_usage` adds `tokens_cached` from `token_usage.prompt_tokens_details.cached_tokens`; `_ZERO_USAGE`); `src/state.py` (`AttemptRecord`: `step`, `slide_index`, `tokens_reasoning`, `tokens_cached`); one helper `usage_record(usage, step, slide_index=None)` in `llm_client.py`; the 12 writers of `generation_history` call it: `elicitor.py` (2), `outline_planner.py`, `slide_component_planner.py` (serial + fan-out), `plan_reviewer.py`, `generator.py`, `repairer.py` (3), `critic.py`, `visual_repairer.py` (2); `evaluator._build_step_summary` and the manifest `tokens` block (add `total_reasoning`, `total_cached`); new `scripts/usage_report.py` (per case × step × slide table from manifests); `eval_run._collect_run` copies `run-manifest.json` into `decks/<case>__rN/` | everything after is measured with it; pure plumbing |
| 0.2 | **Planner checks + re-ask** | new `src/agents/plan_checks.py`; `slide_component_planner.py` (one wrapper `plan_with_reask` used by `slide_plan_serial_node` and `slide_component_planner_node`, replacing both `except` branches); `written_lines.py` (card body = title); `src/state.py` (`SlidePlan.plan_flags`); `src/prompts/slide_component_planner/user.j2` (the existing `repair_context` block carries the named problems) | largest visible gap in the hold-out |
| 0.3 | **Shrink guard** | `src/node/fit-grow.js` (+ `tests/unit/test_fit_grow_*.py`) | independent of 0.2; free replay |
| 0.4 | **Font embedding** | new `src/compiler/font_embed.py` (from `scripts/embed_fonts.py` + `fontTools.subset`); called by `deck_assembler` after `merge_pptx_files`; `scripts/phase0b/compose_deck.py` switched to it; `pyproject.toml` + `requirements.txt` + `uv.lock` add `fonttools` | last: dormant for LLM decks (below) |
| 0.5 | Docs, push, hand-over commands | AGENTS.md, this file, `docs/session-kickoff.md` | |

### 0.2 in detail (what each check is)

| Code | Check | Action |
|---|---|---|
| `PLAN_EMPTY` | the call raised, returned no components, or a block-kind component (kpi_row, table, chart, card_grid, bullet_list, timeline, process_arrow, flow, narrative) has empty `content_data`. The launch-5 case was valid JSON with `{}` inside, not an exception | **re-ask once** with the named failure in `repair_context`; keep the plan with fewer problems; if both fail, a deterministic plan from the outline's own content lines (`written_lines.content_lines`: a `bullet_list`, copied, flagged `plan_source: fallback`) instead of `components: []` |
| `PLAN_INSTRUCTION_TEXT` (C16) | a narrative / caption / bullet / card line not from the brief (`from_brief`) that starts with a planner verb ("Deepen", "Break down", "Show", "Highlight", "Illustrate", "Emphasize" …) or addresses the slide or presenter ("this slide", "the audience", "speaker notes", "talking points") | re-ask (same single re-ask as above); anything left after it is dropped and noted |
| `PLAN_CARD_BODY_REPEATS_TITLE` | a card body equals its title, or ≥ 80% word overlap | drop the body (code), noted |
| `PLAN_DUPLICATE_ITEMS` (C17) | two components whose item labels (card titles, steps, bullets, timeline labels, table first column) overlap ≥ 70% of the smaller, both with ≥ 3 items | keep the higher weight (tie: more text), drop the other, noted |
| `SLIDE_SPARSE` | plan-side estimate: content words (chart point = 1, table cell = 1) < ~25 on a content / data slide, or one content component with ≤ 3 items. The renderer's real `SLIDE_SPARSE` (fills < 55% of the body) arrives with blocks in step 1 | **report only** (flag + manifest + eval summary). No re-ask: a thin brief makes a thin slide, and the §12 fix (derived values, flagged lines) is not built |

At most **one** re-ask per slide, and only for `PLAN_EMPTY` / `PLAN_INSTRUCTION_TEXT`; expected cost
≈ $0.009 per re-ask (design doc §14.6 token table). Thresholds (25 words, 70%, verb list) are set on
saved plans, not guessed: every check runs over the 17 hold-out plans plus every `slides.json` under
`output/runs/` (the false-positive pass), and the doc records counts.

### 0.3 in detail (shrink guard)

`fit-grow` only grows. 7 broken words remained in R1's real-font run ("Recommendation" in a narrow
table column, "Projected" / "₹1.80" in narrow KPI tiles, labels in narrow chevrons). The guard, per
text node, using the real font widths (`fontRegistry.hasFont`; other fonts keep fit-grow's 85% margin):
1. a word wider than the box's inner width → **widen first** where the node can (table column: min
   width = longest word + padding if the table still fits);
2. else **step the type down** ×0.92 per step to the role's floor (house floor 14 px for body text;
   KPI numbers ≥ 28 px);
3. else report `WORD_TOO_WIDE` (node, word, box width, size) in the compile warnings → critic /
   checking loop. **Never grows, never goes under the floor, idempotent.**

### 0.4 finding that changes the stated plan: embed at deck level, in Python

The kickoff says "in `pptx-post.js`". **Correction (2026-10-06, build session):** the first version of this
paragraph said `pptx-post.js` runs only per slide. That was wrong for the main path: `deck_assembler`
compiles the combined deck XML in one `buildPptx`, so `pptx-post.js` does see the whole deck there. What is
still true: every slide also compiles to its own one-slide pptx (critic screenshots), and the ZIP-merge
fallback (`merge_pptx_files`) keeps only the first file's `presentation.xml`. Embedding **after assembly,
in Python** (`src/compiler/font_embed.py`, called by `deck_assembler` for the final file whichever path made
it, and by the evaluator for a one-slide run) covers both paths in one place, leaves the per-slide files
alone, and needs only `fonttools` for subsetting (the Node side would need a new subsetting library). Details:
- Embed only families the deck's slide XML names and whose files exist in `src/node/fonts/`; faces
  regular / bold (the folder's italics are skipped like in POM's registry, since JetBrains Mono has none).
- **Subset** to Basic Latin + Latin-1 + General Punctuation + ₹ € £ + the arrows / maths the blocks
  use, ∪ the deck's own characters, keeping `GPOS` kerning (so measured widths still match) and the
  `name` table the EOT header reads. Check `OS/2.fsType == 0` before embedding.
- **The LLM path writes no `fontFamily` today** (POM default, Noto Sans JP), so embedding is a no-op
  for step 0's `llm.pptx` decks, which stays right: they are step 3's `off` arm and must not change.
  It becomes active when blocks write `fontFamily="Inter"` (step 1). Step 0 proves it on
  `composed.pptx` (already Inter) and on fixture XML.
- Size target ≤ 300 KB per deck (full Inter Regular is 411 KB, so subsetting is required, not optional).
- `fonttools` is a new dependency (not installed on this PC); add to `pyproject.toml`,
  `requirements.txt` and refresh `uv.lock` (the same refresh adds the pending `pillow`).

### Acceptance checks (all LLM-free unless marked)

| Item | Pass when |
|---|---|
| 0.1 | a scripted-LLM unit test shows every manifest `steps` entry has `step`, `slide_index` (null for deck-level calls), `tokens_reasoning`, `tokens_cached`; totals add up; `usage_report.py` prints the hold-out manifest without crashing (old manifests default to 0) |
| 0.2 | on the hold-out plans the checks flag QBR 3–4 (instruction text), agency 4 (card body = title), launch 5 (empty), the phase-card + chevron pair (C17 on the 1 Oct plans); flag none of QBR 2, agency 1–3; the false-positive pass over saved plans is listed, each flag read by eye; a scripted LLM returning `{}` then a valid plan produces exactly one re-ask; two failures produce the fallback plan, never `components: []`; `slide_plan_sorter` still gets one plan per slide |
| 0.3 | replaying R1's 28 saved LLM slides with Inter on: broken words 7 → ≤ 2 and each left one reported as `WORD_TOO_WIDE`; no text goes under its floor; running twice changes nothing; no word that fit before changes size (the replay diff is empty for fitting nodes) |
| 0.4 | deck with fixtures using Inter + JetBrains Mono: pptx grows ≤ 300 KB; opens in LibreOffice with Inter uninstalled and draws Inter; advance widths of the subset equal the full font on a sample string set (kerning kept); a deck naming no known family is byte-identical; the user opens the step-end `composed.pptx` on the test PC and reports Inter is drawn |
| all | unit tests ≥ 572 pass + the new ones; the same 4 failures, no new; `test_py311_syntax` passes; the six step 3 cases compile first pass at least as often as the hold-out (94%) in the step-end run |

### Step-end paid run

Ask before running. Six cases (37 slides) ≈ **$1.8**; **recommended: add `gj-h1-regen` (14 slides,
≈ +$0.7, total ≈ $2.5)** because it is the only deck of 10+ slides: the within-deck variety numbers
(§1b, 1a, step 3) are weak on 5–8 slide decks, it stresses fan-out and the empty-plan rate, and it has a
golden deck for per-slide scoring. Its plans cannot be regenerated identically later, so the choice is
made now; whether it also runs in step 3 (≈ +$0.4, slots arm only) is decided later from 1a.

```bash
python -m scripts.eval_run deck-qbr-data deck-product-launch-data gate-deck-agency-takeover gate-deck-xtsy-qcomm gate-deck-cheffin-full gate-deck-all-nodes-dense --repeat 1 --label step0 --compose --bundle
```

**The test PC sends back one file: the bundle zip.** After 0.1 it carries, per case,
`decks/<case>__r1/{llm.pptx, composed.pptx, slides.json, run-manifest.json}` (the earlier docs asked
for the six `output/runs/` folders because `run-manifest.json` was missing; once 0.1 copies it, that
is unnecessary). `slides.json` holds every slide's plan **and** XML, which is what 1a and step 3 need.
Plus a one-line reply: did `composed.pptx` open in PowerPoint with Inter drawn. Back up the bundle:
1a and step 3 depend on it. Import: `python -m scripts.eval_import <zip>` → `docs/eval/step0/`.

## 3. Node contract (rewritten 2026-10-06 from the slot form; decision D10)

**Why the change** (user, 2026-10-06, after the variant gallery):
- The slot form's advantage is gone. `<VStack id="slot-…">` was chosen because an unexpanded slot is
  valid POM, but `<VStack variant="…">` fails with `UNKNOWN_ATTRIBUTE` (verified), so a pass that strips
  the extra attributes must run in either form.
- A named tag reads like every other node in the generator's node list (`<Table>`, `<Chart>`). An
  anonymous VStack with a magic id invites children, styling and forgetting it is special.
- The same `ref` mechanism gives the **native** nodes (Table, Timeline, Pyramid, Tree, …) the content
  fidelity the blocks have, at small build cost: code only fills in their children.
- Content stays **by reference**, never typed into attributes (the 2026-09-23 `<KpiTile label value>`
  form): retyped content is how numbers were dropped (Test 1: 7–13% before pointers) and card text
  invented.

Terms: a **node** is the tag the LLM writes; its **box** (called "slot" in older sections and docs) is the
space the layout gives it.

### 3.1 One rule: every plan component is placed by one self-closing tag with `ref`

The tag follows the plan kind (`ComponentKindLiteral`, `src/agents/planner_schema.py`):

| Plan kind | Tag the LLM writes | Family | Code writes |
|---|---|---|---|
| `kpi_row` | `<KpiRow ref="c2" />` | derived | the block (look spec §4) |
| `card_grid` (grid / matrix / steps) | `<CardGrid ref="c3" />` | derived | the block (look spec §5, §6); layout from the plan's `card_layout` |
| `narrative` | `<Callout ref="c6" />` or `<Text ref="c6" />` | derived / native | Callout: the panel block; Text: the text, verbatim |
| `caption` | `<Text ref="c7" />` | native | the text, verbatim (source-line tier) |
| `bullet_list` | `<Ul ref="c4" />` | native | one `<Li>` per bullet |
| `table` | `<Table ref="c3" />` | native | `<Col>` widths (measured), `<Tr>` / `<Td>`, first row the header; variant cell fills |
| `chart` | `<Chart ref="c5" />` | native | `chartType` and title from the plan, `<ChartSeries>` / `<ChartDataPoint>`, palette `chartColors` |
| `timeline` | `<Timeline ref="c4" />` | native | `<TimelineItem date title>` per item |
| `process_arrow` | `<ProcessArrow ref="c4" />` | native | `<ProcessArrowStep label>` per step |
| `flow` | `<Flow ref="c4" />` | native | a `<FlowNode>` per step and a `<FlowConnection>` between consecutive steps (the plan holds a linear list) |
| `pyramid` | `<Pyramid ref="c4" />` | native | `<PyramidLevel label>` per level |
| `tree` | `<Tree ref="c4" />` | native | nested `<TreeItem label>` from `tree_nodes` |
| `matrix` | `<Matrix ref="c4" />` | native | `<MatrixAxes>`, `<MatrixQuadrants>`, `<MatrixItem>`; positions low / mid / high → 0.2 / 0.5 / 0.8 (derived by code) |
| `title` (slide header) | `<SlideHeader ref="header" />` from step 1 | derived | kicker, headline, sub-headline; in 1a the LLM still writes them, copying the HEADER block |
| `layer` | — no ref | LLM | free-form; drawn by the LLM as today (no content shape in the plan) |

Everything else stays the LLM's: VStack / HStack bands and panels, Shapes, Icons, dividers, and the free
Text around the nodes (headline, takeaway, labels).

### 3.2 Attributes

- **Every ref tag:** `ref` (required), `w`, `h`, `grow`, `alignSelf` (POM's layout attributes) and `variant`.
- **Derived tags** (`KpiRow`, `CardGrid`, `Callout`, `SlideHeader`): nothing else. The block owns
  padding, gap, fills, borders and type.
- **Native tags:** also that node's own presentation attributes from `nodes.yaml`, e.g. Timeline
  `direction`, `connectorColor`; Flow `direction`, `connectorStyle`, `nodeGap`; Tree `layout`, `nodeShape`;
  Table `cellBorder.*`; Chart `showLegend`; Ul `fontSize`, `color`. Colours as `$tokens`. The plan's
  `direction` / `orientation` is the default when the LLM sets none. **Content attributes are code's**
  and are overwritten (`NODE_ATTR_IGNORED`): Chart `chartType` and `title`, a Text's body, and every
  per-item attribute (items are children, which code writes).
- **No children.** Anything inside a ref tag is dropped (`NODE_CHILDREN_DROPPED`).
- The emphasised item (inverted tile, featured card, highlighted row) and each item's tone come from the
  plan (`design_hint`, `weight`, `kpi_tones` / card `tone`), not from attributes. A `highlight`
  attribute is added only if 1a shows the LLM needs it.

### 3.3 Variants

Names, conditions and fallbacks live in `src/knowledge/core/block-variants.yaml` (each block names its
tag; each variant says whether it is drawn `native` or as a `block`). Look: `docs/block-variants-look-spec.md`.

- On a **derived** tag every variant is a block look.
- On a **native** tag the `native` variants keep POM's own drawing with code-filled children (Timeline
  `rail` / `vertical`, ProcessArrow `chevrons`, Flow `boxes`, Ul `plain`, Text, Chart `native`, every
  Table variant, which only sets cell fills). A `block` variant (Timeline `cards` / `columns`,
  ProcessArrow and Flow `numbered` / `step_cards`, Ul `icon` / `tiles` / `columns`, Chart `labelled` / `horizontal`, which POM's Chart cannot draw: it has no data labels or
  horizontal bars) makes code replace the native node with a block of the same box.
- Kinds with no variants yet (pyramid, tree, matrix) are drawn native only.
- Who chooses: the generator picks `variant` from its component's line; the planner supplies tones and
  emphasis; code checks `requires` and falls back (look spec §7).
- **In 1a** derived nodes have their single current look and native nodes POM's look: `variant` is
  validated and counted, not drawn. Block looks arrive in step 1. **Amended by D12 (2026-10-07):** a native tag's
  block variant that Phase 0b can draw (Timeline cards / columns, ProcessArrow / Flow numbered / step_cards, Ul tiles /
  columns) is drawn by that Phase 0b block in 1a.

### 3.4 Validity and where the pass runs

`ref`, `variant` and the derived tags are not POM. The **node pass** runs in the validator, before
`normalize_xml` (which never sees the plan), on every slide under `blocks: nodes` (the setting was
`off | slots`), and always strips them. Two layout passes as in `scripts/phase0b/expand.py`: lay out
with empty boxes, draw each node for its box, lay out again. If code cannot draw a node (an exception),
it leaves an empty VStack with the node's size attributes and logs `NODE_EXPAND_FAILED`: the slide still
compiles and the gap is visible.

### 3.5 Prompt

**System prompt (fixed, ≈ 140 tokens of rules + ≈ 60 for the derived tags in the node list; the recipes
of every ref kind are removed):**
1. Place every component listed under COMPONENTS with its tag, self-closing, `ref="<id>"`, exactly once.
   Never write its content, items or children.
2. Size it with `w` / `h` / `grow` / `alignSelf` like any box; set `variant` only to a name on its line
   (omit it for the first).
3. On a native tag you may set its own presentation attributes (direction, connector, legend); colours
   as `$tokens`.
4. Choose the variant from the slide's purpose and the room the node gets.
5. Text you write beside the nodes (headline, takeaway, labels) copies the plan's text; add no facts and
   do not repeat a node's content.

**One line per component (user prompt), rendered from the plan and `block-variants.yaml`.** It replaces
the component's data and recipe. Only variants whose `requires` hold are listed, each with its short
phrase. A shape hint is included from v1 (the slot draft left it out), because the LLM no longer sees the
data and must size the box from something; lengths, not the text itself, so nothing invites retyping:

```
c2 · <KpiRow ref="c2"/> · 4 tiles, longest value 7 chars · weight hero · variants: plain = light tiles, numbers in ink; inverted = one dark tile for the number the slide is about; …
c3 · <Table ref="c3"/> · 7 rows × 5 cols, longest cell 18 chars · weight supporting · variants: plain | zebra | highlight_row | dark_header
c4 · <Timeline ref="c4"/> · 5 items, longest label 6 words · weight peer · variants: rail = …; vertical = …; cards = …
c5 · <Tree ref="c5"/> · 7 nodes, 3 levels, widest level 4 · weight hero
```

The planner's `content_summary` line stays, for context. Measured cost (look spec §7, 64 saved slides):
output ≈ −50 to −67% (1,830 → ≈ 600–900 tokens per slide), input ≈ −6 to −9%.

### 3.6 Error codes

Validator diagnostics. Errors go to the existing compile repairer with guidance text; warnings go to the
manifest and the `node_bypassed` counter; reports go to the checking loop (§5.1).

| Code | Severity | Meaning → handling |
|---|---|---|
| `NODE_REF_UNKNOWN` | error | `ref` names no component of this slide → repair |
| `NODE_REF_DUPLICATE` | error | the same `ref` twice → repair |
| `NODE_MISSING` | error | a component has no node and its text is not in the XML → repair (content would vanish) |
| `NODE_BYPASSED` | warning | no node, but ≥ 50% of its item text is hand-built in the XML → kept, counted (`node_bypassed`); the policy for step 2 is decided from 1a's rate |
| `NODE_KIND_MISMATCH` | warning | the tag does not match the plan kind (`<Table ref="c2">` for a kpi_row) → the plan kind's tag is used |
| `NODE_KIND_NO_REF` | error | `ref` on a kind without content (`layer`) → "draw it yourself" |
| `NODE_CHILDREN_DROPPED` | warning | children inside a ref tag → replaced by code's |
| `NODE_ATTR_IGNORED` | warning | an attribute outside §3.2, or a content attribute, removed / overwritten |
| `NODE_VARIANT_UNKNOWN` | warning | not a name of this tag → default used |
| `NODE_VARIANT_UNMET` | warning | the variant's `requires` failed, or the block re-flowed → fallback used, check named |
| `NODE_NO_SIZE` | warning | no `w` / `h` / `grow` and none inherited → `grow="1"` |
| `NODE_EMPTY_PLAN` | warning | the component has no content (step 0's re-ask failed) → nothing drawn, `plan_flags` |
| `NODE_EXPAND_FAILED` | error (code bug) | drawing raised → empty box of the same size, logged, no repair call |
| `NODE_OVERFULL` | report | smallest type step still short (as `SLIDE_OVERFULL` today) → checking loop |
| `NODE_UNDERFILLED` | report | the node fills < 60% of its box (§5.4) → checking loop |

## 4. 1a protocol (revised 2026-10-06 for the node form; made exact 2026-10-06 on step 0's plans)

**Question:** does the LLM place ref nodes correctly, and does the node route not lose on mistakes or
variety?

**Status (2026-10-06, follow-up session):** protocol written against step 0's real plans; nothing built,
nothing spent. The changes to the earlier text are **D11** in §6, approved as written by the user 2026-10-07.

**Inputs:** step 0's four bundles, extracted at `output/step0/{b1,b2x,b3x,b4x}/<bundle>/decks/<case>__r1/`
(`slides.json` = every slide's plan + the off arm's XML; `run-manifest.json` = theme, per-call usage).
Not `output/step0/nk/` (the neutral-KPI side run, not a step 0 deck). Models, temperature and `max_tokens`
as in `models.yaml` (generator = gpt-4.1); one run, ×1. The zips (`Downloads\step0-20261006-*.zip`) are the
only copy of these plans: back them up before 1a.

**`ref` value = the plan's `component_id`** (`summary_kpis`, `cpc_comparison_chart`), as Phase 0c's slots
used; §3's `c2` / `c3` are placeholders. The ids are already unique per slide in all 37 plans.

### 4.1 Slide selection (exact rule; replaces "fill to ≈ 24")

`scripts/node_test_select.py` (replaces the planned `slot_test_select.py`, never built) reads the four
bundles and writes `docs/eval/step0/1a-slides.json` (case, slide number, title, component ids + kinds, and
the reason any slide is left out). **Rule:**
1. **Pool:** all six step 0 decks (37 slides). CHEFFIN joins the pool (the earlier rule left it out
   wholesale because its slides were the examples; now only the example slides themselves are excluded).
2. **Exclude the prompt's own examples.** The node prompt's examples are Phase 0c's skeletons rewritten to
   ref tags (`scripts/phase0b/phase0c/m1`–`m4`). They were drawn from CHEFFIN slide 2 (exec summary),
   CHEFFIN slide 3 (CPC), XTSY slide 6 (automation) and gj-h1 slide 2 (not in step 0). So CHEFFIN 2, CHEFFIN 3
   and XTSY 6 are out. The rule is "by title of the source slide", so it also holds if the examples change.
3. **Exclude slides with nothing to place:** every component is `title` or `layer` (QBR 1, launch 1).
4. **Take every slide left: 32 slides, 78 ref components** (17 slides with 3+ components). No sampling,
   so no judgement in the list.

Why all 32 rather than ≈ 24: the rule needs no tie-breaks, compliance is measured on 78 components instead of
≈ 60 (margin ±7 points instead of ±8), and the within-deck variety (measure 5) is computed on near-whole decks
(4–7 slides each) instead of 3-slide fragments. Cost ≈ +$0.2 (§4.5).

**Coverage this gives** (slides holding the kind; the old rule asked ≥ 3 each):

| Kind | Slides | | Kind | Slides |
|---|---|---|---|---|
| narrative | 15 | | table | 5 |
| card_grid grid | 11 | | kpi_row | 4 |
| bullet_list | 10 | | chart, timeline | 3 each |
| caption | 9 | | process_arrow + flow | 3 (2 + 1) |
| card_grid steps | 4 | | pyramid + tree + matrix | 2 slides, 3 components |
| layer (tests `NODE_KIND_NO_REF`) | 2 (all there are) | | **card_grid matrix** | **0** |

Per deck: XTSY 7, agency 6, all-nodes-dense 6, launch 5, QBR 4, CHEFFIN 4. **Gaps, stated, not filled:**
no `card_grid` matrix in step 0's plans; pyramid / tree / matrix, flow and layer appear once or twice, so
their results are anecdotes. Filling them needs new plans (a paid planner run), which the paid-run rule
argues against for 1a; they are covered by the scripted dry run (§4.6) and by step 3.

### 4.2 Arms

- **(A) off** = step 0's saved XML for the slide, **recompiled on the 1a commit** (free). Step 0 compiled
  at `3caf03e`; fit-grow has changed since (card text fill, KPI tile sharing). Both arms go through the
  same compiler, fit-grow and shrink guard, so measure 3 compares layouts, not compiler versions.
- **(B) nodes** = the generator with the §3.5 node prompt on the same plan, then the node pass (§3.4):
  derived nodes drawn by the Phase 0b blocks (`expand.py`, extended to read ref tags), native nodes filled
  by the native fillers (POM's own look, as in A). Same `<Theme>` in both, from the manifest's theme; B's
  blocks are recoloured from that palette with role-based text colours (§1a) so the blind comparison
  judges layout and fill, not palette. The palette file is read, not edited (the palette session owns it).
- B is scored on its **first try only** (D12, 2026-10-07): no repair calls; an error or a failed compile is counted in
  measure 8, and a slide that does not compile is a loss for nodes in measure 4.

### 4.3 Measures and kill criteria (unchanged criteria; how each is computed)

| # | Measure | How (script) | Pass |
|---|---|---|---|
| 1 | **Node compliance, first try** | `node_test_score.py` classifies each of the 78 components on B's first XML: ok / unknown ref / missing / duplicate / kind mismatch / children / bypassed / attr / variant (the §3.6 codes, from the validator's own classifier). Derived and native reported separately; slide-level "all ok" too | component-level ≥ 90% (≥ 71 of 78); 86–93% is a re-run decision, not a verdict |
| 2 | Invented words inside nodes | every word in the drawn text of a node (derived and native) must occur in that component's `content_data` (case- and punctuation-folded; numbers as in the step 0 invented-number check) | 0 |
| 3 | Broken words, overlapping text | LibreOffice render of both arms, `fontcheck.py` (broken words) + `check.py` (overlaps), per slide | B ≤ A, totals over the 32 slides |
| 4 | **Blind side-by-side** | `node_test_sheet.py`: per slide A and B images, left / right by a fixed seed (`1a`), no labels, 4 slides per sheet, 8 sheets; you mark 1 / 2 / equal + a reason (readability, fill, overlap, empty, designed); key in a separate file | (B wins + ½ ties) / 32 ≥ 0.6 |
| 5 | Within-deck variety | `variety.py` (§1b), fine signatures, per deck on its selected slides, averaged over the six decks | B not > 0.05 below A |
| 6 | Cross-deck variety (D2) | `variety.py`, cross-deck sameness + house-template share | informational |
| 7 | Tokens and cost per slide | B's generator calls (manifest `steps`, `step == "generator"`, first attempt) vs A's on the same 32 slides from step 0's manifests: input, output, cached separately; repairs separately. **A's baseline on these 32 slides: 11.7k input, 1.04k output tokens per slide, ≈ $0.032 per slide for the generator** (whole step 0: 11.5k / 1.0k, $0.047 per slide all steps) | informational; flag if B's input per slide is above A's, or output falls < 30% |
| 8 | Fallback rate | slides with a compile repair, a `NODE_*` error, a retry, `SLIDE_OVERFULL` / `NODE_OVERFULL` | reported; sizes step 2 |
| 9 | Variant choice | variant per node, default share, `requires` fallbacks | informational |

Fail on 1, 2, 3, 4 or 5 → stop nodes, keep blocks: composer + planner `arrangement` field (§14.1 option 2).

### 4.4 Files

New (all LLM-free to test; Python 3.11-safe; `test_py311_syntax` covers them):

| File | What |
|---|---|
| `src/compiler/nodes/validate.py` | the node pass's checks: parse ref tags, classify each component (§3.6 codes), strip `ref` / `variant` / derived tags' extra attributes, drop children. Used by the scorer, so measure 1 and the pipeline share one classifier |
| `src/compiler/nodes/native.py` | one filler per native kind (Table, Chart, Ul, Timeline, ProcessArrow, Flow, Pyramid, Tree, Matrix, Text): `content_data` → POM children, verbatim text |
| `src/compiler/nodes/prompt_lines.py` | one prompt line per component (§3.5: tag, shape hint in lengths, weight, variants whose `requires` hold, from `block-variants.yaml`) |
| `src/prompts/generator/nodes_system.j2` | the §3.5 rules + the derived tags in the node list + the rewritten examples |
| `scripts/from_plans.py` | a run's `slides.json` + manifest → `state["slide_plans"]` and theme (`route_after_start` already skips planning) |
| `scripts/node_test_select.py` | §4.1 → `docs/eval/step0/1a-slides.json` |
| `scripts/node_test.py` | generator-only runner for arm B: per slide the node prompt, first XML, node pass, compile; writes `output/1a/<label>/<case>/slide-N/{skeleton.xml, expanded.xml, compile-result.json}` + one manifest; `--llm scripted:<dir>` replays fixed responses instead of calling the API; `--off` recompiles arm A |
| `scripts/node_test_score.py` | measures 1, 2, 3, 7, 8, 9 → `docs/eval/1a/summary.md` + `results.json` |
| `scripts/node_test_sheet.py` | measure 4 sheets + key |
| `scripts/variety.py` | measures 5, 6 (§1b), shared with step 3 |
| `tests/fixtures/nodes/` | m1–m4 rewritten to ref tags; one broken skeleton per `NODE_*` code (§4.6) |
| `tests/unit/test_nodes_validate.py`, `test_nodes_native.py`, `test_nodes_prompt_lines.py`, `test_node_test_select.py`, `test_variety.py`, `test_node_test_dryrun.py` | per file above |

Changed: `scripts/phase0b/expand.py` (reads ref tags instead of `slot-` ids; native kinds go to `native.py`),
`scripts/phase0b/render.py` (role-based recolouring from the deck palette), this doc, AGENTS.md.
Not touched: the graph, `src/node/fit-grow.js`, `palettes.yaml`. The node code sits in `src/compiler/nodes/`
**unwired** (no `blocks:` setting yet): step 1 wires it if 1a passes; if 1a fails it is removed.

### 4.5 Cost and run order

Per slide for B: input ≈ 11.7k × 0.92 ≈ 10.8k tokens, output ≈ 0.45k (−55%), at gpt-4.1 list price ≈ **$0.026**;
no repair calls (D12). **32 slides ≈ $0.8** (≈ $0.9 with the repairs first planned) (the $0.5 estimate assumed $0.02 per slide on 24 slides; $0.02 was
below step 0's measured generator cost). Run order (one case first): `deck-qbr-data` (4 slides, ≈ $0.11),
check its folder and scores, then the other five in one command. Test PC commands (final form when built):

```bash
python -m scripts.node_test --run output/step0 --slides docs/eval/step0/1a-slides.json --cases deck-qbr-data --label 1a
python -m scripts.node_test --run output/step0 --slides docs/eval/step0/1a-slides.json --label 1a --bundle
```

The test PC needs the four step 0 bundles extracted at the same paths (copy the zips across). It sends back
the bundle zip (skeleton + expanded XML per slide, manifests). Scoring, renders and sheets run on this PC, free.

### 4.6 Scripted-LLM dry run (before any paid call; all on this PC)

`node_test.py --llm scripted:tests/fixtures/nodes/` swaps the generator's model for a stub that returns a
fixed XML per (case, slide) and a fixed usage record, so the whole path runs: prompt render → "call" →
validator → node pass → compile → manifest → scorer → sheets → variety.

| # | Run | Pass when |
|---|---|---|
| 1 | **Mechanical skeleton for all 32 slides**: code writes the header copied from the plan + one ref tag per component in a VStack (`grow="1"` each) | every slide expands and compiles; 78 / 78 components ok; measure 2 = 0 (nothing invented by fillers or blocks); every native kind drawn at least once; renders and sheets produced |
| 2 | **m1–m4 rewritten** (the prompt examples), on their own Phase 0b plans | compile, 100% ok; render matches Phase 0c's (no new overlap / broken word) |
| 3 | **One broken skeleton per code**: unknown ref, duplicate ref, missing node, missing but hand-built (bypassed), kind mismatch, `ref` on a layer, children inside, content attribute (`chartType`), unknown variant, no size, empty plan, a filler that raises | the scorer reports exactly that code on exactly that component; errors reach the repair path (stub returns the fixed XML on retry), warnings are kept; `NODE_EXPAND_FAILED` leaves an empty box and the slide compiles |
| 4 | **Prompt size**: render the node prompt for the 32 slides, count tokens (`tiktoken`, gpt-4.1 encoding) | input per slide ≤ A's 11.7k; the printed estimate replaces §4.5's |
| 5 | **Off arm recompile**: A's 32 saved XML on the current compiler | all compile; broken words / overlaps recorded as A's numbers |
| 6 | Unit tests | baseline + the new tests, no new failure, `test_py311_syntax` passes |

Only after all six: ask for the paid run with the case list and cost.

### 4.7 Build and dry-run log (2026-10-07, branch `feat/derived-blocks-step0`, LLM-free)

**Built** (file list §4.4): `src/compiler/nodes/` (`spec.py`, `validate.py`, `native.py`, `prompt_lines.py`;
unwired), `src/prompts/generator/nodes_rules.j2` + `nodes_user.j2` and a `nodes` flag in `system.j2` (off: the
rendered prompt is byte-identical on all 37 step 0 plans), `scripts/from_plans.py`, `node_test_select.py`,
`node_test.py`, `node_test_score.py`, `node_test_sheet.py`, `variety.py`; `scripts/phase0b/expand.py`
(`expand_nodes`), `render.py` (`deck_pack`, `retoken`), `fontcheck.py` (CLI moved under `main()`, same output);
fixtures `tests/fixtures/nodes/` (two fictional step 0 decks, one scripted broken skeleton per code); 46 new tests.

**Choices made while building (for the user's check):**
- Both arms are drawn in the deck font Inter (`--font`; code adds `fontFamily` where the XML names none) and
  compiled with fit-grow on (`--fit-grow`): font-neutral comparison, D1's font, exact measurement.
- Block text is clamped to the 12 px label floor (D8); the blocks' type is raised to body 14 / label 12.
- Blocks take the deck palette by role (`deck_pack`): panel = surfaceAlt, dark tile = textMain, text on dark = surface.
- Repairs: first built as a node-aware re-ask on the skeleton; **D12 (2026-10-07): 1a scores the first try only**,
  no repair calls (`--repairs 0`); a slide that does not compile is a loss for nodes in the blind comparison.
- `ref_tags` sizes: layout attributes also `minW` / `maxW` / `minH` / `maxH`; `NODE_NO_SIZE` does not apply to
  Text / Table / Ul (content-sized). Native nodes carry `id="node-<ref>"` for scoring.
- The matrix filler spreads items that share a cell (two "low / high" items were drawn on one point).

**Dry-run results:**

| §4.6 | Result |
|---|---|
| 1 mechanical skeleton, 32 slides | 32 / 32 compile; 78 / 78 components ok; 0 invented words in nodes; broken words 0 (off arm 6); overlap slides 2 (off 4): CHEFFIN 6 (table without cell margins, as off), XTSY 8 (native Timeline, labels up to 20 words); overfull 2 (agency 2, dense 3). Variety 0.943 vs 1.0 is code's one-band layout, not a result |
| 2 prompt examples m1–m4 on their own plans | all compile, all components ok, 0 invented; m2 overlap inside the native table (no cell margins) |
| 3 one broken skeleton per code | each code reported on its slide; errors repaired in one re-ask; all 10 compile; `NODE_EMPTY_PLAN` / `NODE_EXPAND_FAILED` covered by unit tests |
| 4 prompt size | 32 slides: 10,478 vs 11,539 tokens (tiktoken, −9.2%); est. input 10.6k per slide vs step 0's measured 11.7k; cost ≈ $0.025 per slide, ≈ $0.8 for 32 with no repair calls (D12) |
| 5 off arm recompile | 32 / 32 compile; broken words 6, overlap slides 4 |
| 6 unit tests | **680 pass, the 4 known failures** (634 + 46 new); `test_py311_syntax` passes |

**Decided (D12, 2026-10-07):** POM's native Timeline cannot fit long labels (XTSY 8), so in 1a the block variants
Phase 0b already has are drawn when the LLM picks them (§3.3 amended for 1a). First try only; Inter + fit-grow on both arms.

## 5. Open questions: recommendations

### 5.1 Checking-loop spec (for step 2; principle now, thresholds after 1a)

- **Trigger and place:** a graph node `layout_checker` after the validator succeeds (compile + node
  expansion), before the visual critic. Only under `blocks: nodes`; `off` stays the step 0 path.
- **Tier 1 (always, free, ≈ 1 s):** POM's own layout (`measure.mjs`): squashed boxes, overfull, words
  wider than their box (`WORD_TOO_WIDE`), `NODE_OVERFULL`, `NODE_UNDERFILLED`, text under its floor.
  **Tier 2 (render facts: broken words, overlaps, past-footer text)** only where a renderer exists, from
  the render the critic already makes; promoted to a loop trigger only if 1a / step 3 show tier 1
  missing things (both are computed there, so agreement is free to measure).
- **Fixes, code first:** for a block problem the code acts (switch to the next more compact variant, re-flow
  rows / columns, split KPI tiers). For a layout problem (slot too small, free text overflowing) one **LLM
  patch of the skeleton only** (≈ 600 tokens of XML + the issues stated in px: "c3 needs 320 px, has
  240"), then re-expand, re-measure.
- **Best version:** lexicographic tuple (errors, squashed px, overfull px, broken words, overlaps, below-floor
  text); lower wins, a tie keeps the earlier version. ≤ 2 rounds; round 2 only if round 1 improved and a
  deficit above the 8 px tolerance remains.
- **Cost:** ≈ $0.01–0.025 per LLM round (design doc §14.6 token table), zero for code fixes. 1a's skeletons
  tell how many slides would trigger one; if under ~15%, the loop is a small cost.
- **Relation to today's nodes:** the compile `repairer` is unchanged (compile errors). The loop runs before
  the visual `critic`, which keeps judging what code cannot measure (hierarchy, balance); measured codes
  join `REPORT_ONLY_CODES`-style filtering so the critic never re-reports them; `visual_repairer`
  patches the skeleton (not whole XML) under nodes.
- **Decide now:** the principle above. **Schedule for step 2:** thresholds, the code-fix list, tier 2 promotion.

### 5.2 #4 label tier ≥ 10 px

**Label tier decided by the user 2026-10-05 (D8), after viewing the test deck:** label-role text (kickers, KPI labels, table captions) has a **floor of 12 px (9 pt)**; 10 px (7.5 pt) only for the source / footnote line; body text stays >= 14 px. **The floor is not a fixed size: when a slot has room left, label type grows into it** (up to the role's maximum, §5.4 fill contract), as with every other type role ("fill the card, don't shrink it", 2026-10-04). Blocks bake in the floor in step 1.

At 1280×720 one px = 0.75 pt (720 px = a 7.5 in slide), so 10 px is **7.5 pt**, 12 px is 9 pt (Genspark's
Super Agent spec used 9 pt tags), 14 px (the house floor) is 10.5 pt. **Recommendation: label-role text
(kickers, KPI labels, table captions) 12 px; 10 px only for the source / footnote line;** body stays ≥ 14.
You still have to look: before step 1 I produce one free test slide with the same mono label at 10 / 11 / 12 / 14 px
(and the same on a dark tile) from the research renderer; view it at 100% on the laptop and full-screen
projected. Rule: the smallest tier you can read comfortably from the back of the room. Needed before step 1
(blocks bake the tier in).

### 5.3 When `blocks: nodes` becomes the default

Not after step 3: kinds without a block (matrix, pyramid, tree, layer, branching flow) would give a mixed
look, and the UI edit path is not planned. Recommended gates, all required: (1) step 3 passes the 1a criteria
on all six (seven) cases; (2) step 4 blocks are in; (3) **the edit service re-expands blocks after every edit**
(plan edit → re-draw; layout edit → XML edit → re-expand), which no step covers yet and which I add to
step 2's list; (4) fallback rate (slides sent to the composer or `off`) ≤ 10%; (5) cost per deck within ±20%
of off. Until then `nodes` is opt-in per run (setting + UI advanced switch); `off` stays available.

### 5.4 Fill contract: blocks grow into a tall slot (for step 1)

Measure `fill = drawn height ÷ slot height`. Order, all within the plan's own text (never added content):
(1) type up to the role's maximum (step title ≤ 24, step detail ≤ 18, timeline label ≤ 32, date ≤ 14, short-list
text ≤ 28); (2) item boxes taller up to ×1.6 natural; (3) if `fill` < 0.6, **switch arrangement**:
process steps `chevrons` → `step_cards` / vertical, timeline `rail` → `cards` / `columns`, a ≤ 4-item list →
`tiles`; (4) otherwise centre the block in the slot (never a thin band hung at the top) and report
`NODE_UNDERFILLED`, which the checking loop turns into a layout fix ("give c3's height to c2").
Caps follow the 2026-10-04 decision "fill the card, don't shrink it" (type grows, boxes do not balloon). Numbers
tuned in step 1 on the nodes demo render (free).

## 6. Decisions

| # | Decision | Recommendation | Status |
|---|---|---|---|
| D1 | §1a theme source: `palettes.yaml` only, derived role tokens + contrast test, packs carry structure, Inter + JetBrains Mono, `look` picked by the outline planner in step 2 | as written | **decided 2026-10-05: adopted as written** |
| D2 | §1b cross-deck check in the 1a kill criteria (content-controlled definition) | kill criterion | **decided 2026-10-05: within-deck only is the kill criterion; cross-deck measured and reported, informational** |
| D3 | Step 0 plan §2 incl. embedding at deck level in Python | as written | **decided 2026-10-05: approved as written** (`SLIDE_SPARSE` report-only; one re-ask max; `fonttools` added) |
| D4 | `gj-h1-regen` joins step 0's run (≈ +$0.7) | yes | **decided 2026-10-05: no, six cases only** (37 slides, ≈ $1.8). Within-deck variety is judged on 5–8 slide decks; a long deck can be added to step 3 only if its plans are generated then |
| D5 | Slot contract §3 | as written | **decided 2026-10-05: approved as written** (no `highlight` attribute until 1a shows it is needed); **superseded 2026-10-06 by D10** |
| D6 | 1a protocol §4 | as written | **decided 2026-10-05: approved as written** (slide list still needs the user's approval once step 0's plans exist); revised 2026-10-06 for the node form (D10) |
| D7 | Checking-loop principle §5.1 | as written | **decided 2026-10-05: principle approved**; thresholds, code-fix list and tier-2 promotion scheduled for step 2 from 1a's data |
| D8 | Label tier (§5.2) | view the test slide first | **decided 2026-10-05: 12 px label floor that grows into spare room, 10 px source lines only, body >= 14 px (user, after viewing the test deck).** Earlier note: scheduled. The free 10 / 11 / 12 / 14 px test slide is built in the step 0 build session; the user views it (100% and projected) and the tier is recorded before step 1. Starting recommendation 12 px labels, 10 px source lines only |
| D9 | Default-switch gates (§5.3) and fill contract (§5.4) | as written | **decided 2026-10-05: both approved.** `slots` stays opt-in until the five gates hold (a separate decision after step 4); step 2 gains "the edit service re-expands blocks after every edit"; fill numbers tuned in step 1 |
| D10 | Contract form (§3, §4): named self-closing tags with `ref` for every plan kind except `layer` (derived `KpiRow` / `CardGrid` / `Callout` / `SlideHeader`; native `Table` / `Chart` / `Ul` / `Timeline` / `ProcessArrow` / `Flow` / `Pyramid` / `Tree` / `Matrix` / `Text`, code fills their children), content by reference only, shape hints in each component's prompt line, `NODE_*` codes, setting `blocks: off / nodes` | as written | **decided 2026-10-06 (user): rewrite the contract into the node form** |
| D11 | 1a made exact on step 0's plans (§4, 2026-10-06 follow-up session): `ref` = the plan's `component_id`; all 32 eligible slides (six decks; CHEFFIN 2, CHEFFIN 3, XTSY 6 out as prompt-example sources; QBR 1, launch 1 out, nothing to place), not ≈ 24; arm A recompiled on the 1a commit; node code in `src/compiler/nodes/`, unwired until step 1; cost ≈ $0.9 (was ≈ $0.5), `deck-qbr-data` first (≈ $0.11); scripted dry run §4.6 before any paid call; card_grid matrix not covered (no such plan in step 0) | as written | **decided 2026-10-07 (user): approved as written** |
| D12 | 1a dry-run choices (§4.7, 2026-10-07): (1) draw the block variants Phase 0b has when the LLM picks them; (2) repairs; (3) both arms in Inter with fit-grow on; (4) who fixes the ₹59.8 fit-grow regression | (1) yes; (2) node-aware re-ask, then revised: first try only; (3) yes; (4) the font-size session, else me | **decided 2026-10-07 (user): (1) yes: Timeline cards / columns, ProcessArrow and Flow (linear) numbered / step_cards, Ul tiles / columns drawn by the closest Phase 0b block; Ul icon, ProcessArrow alternating, Chart labelled / horizontal stay native (no block yet); (2) first try only: no repair calls in 1a, an error is a fallback (measure 8), a node slide that does not compile counts as a loss in the blind comparison; the re-ask stays in `node_test.py` behind `--repairs N` (0 in 1a); step 2 decides the repair route, likely today's repairer fed the skeleton; (3) yes; (4) fixed in this session (§7)** |

## 7. Step 0 build log (build session 2026-10-06, branch `feat/derived-blocks-step0`)

All LLM-free; one paid run still to do (§2). Baseline before the first change: **572 pass, 4 known failures**
(the same four). **After step 0: 619 pass, the same 4 known failures** (47 new tests: usage logging 7, plan checks 20,
shrink guard 11, font embedding 9; one existing test, `test_extract_usage_reads_reasoning_tokens`, pinned the
exact usage dict and now expects `tokens_cached`). Commits: 0.1 `178244b`, 0.2 `e57fb9b`, 0.3 `fa43cc4`,
0.4 + docs in the commit after it.

**0.1 Usage logging.** `llm_client.usage_record(usage, step, slide_index)` + `tokens_cached`
(`prompt_tokens_details.cached_tokens`); `AttemptRecord` carries `step`, `slide_index`, `tokens_reasoning`,
`tokens_cached`, `reask`; the 12 `generation_history` writers use it. Two calls that were not recorded at all
now are: the planner re-plan inside the compile repairer's REGENERATE and inside the visual repairer's
REGENERATE. Manifest `steps` entries and `tokens.total_reasoning` / `total_cached`;
`python -m scripts.usage_report <folders>` (`--per-slide`); the eval bundle copies `run-manifest.json` into
`decks/<case>__rN/`. Old manifests read as step "unknown".

**0.2 Plan checks and one re-ask** (`src/agents/plan_checks.py`, `plan_with_reask` in
`slide_component_planner.py`, `scripts/plan_flags_report.py`). As §2, with these differences found while
calibrating on the 17 hold-out plans:
- **C17 keeps the component with more text, not the hero** (launch 3: chevrons with 5 words vs cards with 53
  words of descriptions; keeping the hero would have thrown the descriptions away). The kept one takes the
  better weight. Rule recorded here because §14.6 / the reviewer doc say "keep the hero".
- Thin-slide estimate in units: KPI tile 3, card 2, chart 10, a table at least the limit (so a table slide is
  never thin), list items 1 + words / 12; limit 9. On the hold-out it flags QBR 5, launch 2, launch 6 and agency 5
  (after its speaker-notes narrative is dropped), not QBR 2–4, launch 3–4, agency 1–4 or 6.
- Hold-out result: instruction text found on 8 of 17 slides (QBR 3, 4; agency 1–6, all of them speaker notes
  or "Walk through…" paragraphs), card bodies repeating the title on agency 4, the empty `kpi_row` on launch 5
  (the empty caption beside it is dropped without a re-ask), the chevron / card duplicate on launch 3.
- **False-positive pass:** 169 unique saved slides with content (every `slides.json` under `output/runs/` and the
  `llm_test/` zips): 0 instruction text, 0 duplicates, 0 repeated bodies, 6 empty components (single-component
  test runs that never went through the planner), 6 thin slides (3.6%).
- A planner that fails twice gives `plan_source: "fallback"`: the outline's own content lines as one bullet list
  (copied), or no components when there are none, flagged `PLAN_EMPTY`; never the silent `components: []`.
- Found, not fixed (outside step 0): `slide_replanner.resolve_slide_plan` unpacks `plan_single_slide`'s return as
  a plan, but it returns `(plan, usage)`; the unit tests mock the function, so the UI "revise with feedback" path
  that replans a slide would raise a `TypeError` for a real call.

**0.3 Shrink guard** (`src/node/fit-grow.js`, last phase; fixtures `tests/fixtures/shrink_guard/`). As §2 with
these rules, found by replaying R1's 28 saved LLM slides (Inter added, fit-grow on, scored with `fontcheck.py`
on the LibreOffice render; `output/fontexp3/`, replay script in the session scratchpad):
- First version (shrink every too-wide word to the floor): broken words 7 → 6, but it **moved** a break: shrinking
  "Projected" narrowed its content-sized KPI tile and broke "₹59.8" beside it (gj-h1 slide 14).
- Final rule: every edit is tried and kept only if the slide's **total overflow in px goes down** and no piece
  elsewhere is newly too wide. Table columns use the existing 85% inset margin (a 95% first try broke "Type" /
  "Search" in a 6-column table). Floors: 14 px, 28 px for a number or title. Scope: text, `Ul` / `Ol`,
  `ProcessArrow` labels, table cells. Not covered: Flow, Tree, Timeline, Pyramid, Matrix labels.
- **Result: broken words 7 → 5, none new** (fixed: "Economics", "Diagnostics"; left: "Governance", "Recalculation",
  "Recommendation" in a 6-column table, "₹1.80", "Projected"). The plan's "≤ 2 left" is **not met**: the five left
  are boxes too narrow for the word at the floor size (the layout, not the type, is wrong); each carries a
  `WORD_TOO_WIDE` compile warning (≤ 5 per slide, read by the critic), which the checking loop of step 2 will act on.
  Some warnings are conservative (the 85% table margin): 12 on the 28 slides for 5 real breaks.

**0.4 Font embedding** (`src/compiler/font_embed.py`; deck_assembler and the evaluator call it; compose_deck uses
it; `scripts/embed_fonts.py` keeps its CLI). See the correction in §2. Three faces (Inter regular + bold,
JetBrains Mono regular) add **148 KB** to a deck zipped (323 KB of raw EOT, 94–116 KB per subset face; the full
fonts are 411 / 420 / 274 KB). LibreOffice opens the result. `saveSubsetFonts="1"` is set next to
`embedTrueTypeFonts="1"` (as PowerPoint's own subset embedding); R4 passed without it, so the PowerPoint check
below also covers it. Not embedded: the per-slide files; fonts the deck does not name (the LLM path names none).

**Label tier (D8).** `python -m scripts.label_sizes` builds `output/label-test/label-sizes.pptx` (light and dark
slide, the same mono label at 10 / 11 / 12 / 14 px as a kicker, a KPI tile label and a table caption); sent to
the user for the projected view. The decision is the user's, recorded here when given.

**First paid run (test PC, 2026-10-06): `deck-qbr-data` ($0.19) broke on a NUL character.** Not caused by step 0's code.
`scripts/find_nul.py` on the run folder showed the garbage already in the **outline planner's `subtitle`** (the
evidence line, gpt-5-mini): "Acme Analytics \x0b\x0b Executive Update", "$28.1M \x00b\x00b +22% \x00b\x00b 142",
on slides 1-4, each run sitting between spaces where a middle dot belongs. The generator copied it into the slide
XML; POM wrote it into the pptx, PowerPoint refused the deck, `font_embed` skipped it (as designed) and `eval_run`
crashed reading the slide. Fix (`src/utils/text_clean.py`): a mangled separator (`NUL b`, or a vertical tab, once or
twice, between whitespace) becomes "·" again, any other XML-illegal character is removed; applied to the outline
planner's output, the slide planner's `content_data` and every generator / repair XML in `normalize_xml`
(`ILLEGAL_CHARS_REMOVED` issue). `eval_run` scoring survives an unreadable slide (`score_error`). Lesson for the
runs: one case at a time, `find_nul` before re-running.

### Step-end run result (test PC, 2026-10-06; imported to `docs/eval/step0/`)

Six cases, 37 slides, **$1.74** (estimate $1.8), no run errored, 6 of 6 passed, compiled 100%, first pass 94.6% (hold-out
was 94%), invented numbers 0, mean card fill 0.83, `find_nul` 0 on all six decks, composed decks 204-319 KB with 4-6
subset font parts. Run in three terminals at once (the output-folder collision fix made that safe). Order of events:
the first attempt of `deck-qbr-data` crashed on NUL characters from the outline planner (see above; $0.19 spent, re-run
once after the fix).

| Check (§2 acceptance) | Result |
|---|---|
| no empty component, instruction text or duplicate item left in any plan | **yes, all six** (`plan_flags_report --recheck`: 0 plans with problems) |
| every manifest step named, with slide index, reasoning and cached tokens | **yes** (100 calls: generator 37, slide planner 43, outline 6, reviewer 6, elicitor 6, repairer 2) |
| re-asks | **6 in 37 slides, $0.062 in total** (3.6% of cost); reasons: instruction / speaker-notes text (agency, xtsy, qbr), a footnote false positive (launch 6, fixed) |
| thin slides reported (`SLIDE_SPARSE`) | qbr 1, launch 2, xtsy 1, others 0; report only |
| duplicate dropped | launch 3 (chevrons vs cards, as on the hold-out) |
| shrink guard | `WORD_TOO_WIDE` warnings reach the critic; xtsy has 5 word breaks on 8 slides, the rest 0-1 |
| font embedding | active on the composed decks (6 faces, ≤ 319 KB); the LLM decks name no font, so none embedded, as designed |
| PowerPoint opens `composed.pptx` with Inter drawn (the user's check, also covers `saveSubsetFonts`) | **yes (user, 2026-10-06): opens, Inter drawn** (subset embedding + `saveSubsetFonts` accepted) |

**Where the money goes (all six, list price):** generator 66% ($1.15; 11.5k tokens in and 1.0k out per slide, only 5% of
the input cached because the prompt differs per slide), slide planner 25% ($0.43; 85% of its input cached), outline
3%, reviewer 3%, repairs 1%, elicitor 2%. Baseline for 1a and step 3: **≈ $0.047 per slide, generator input ≈ 11.5k
tokens per slide** (the step 3 cache comparison starts from 5%). The plan reviewer's confidence score still changes nothing.

### Follow-up session (2026-10-06): merge check, still on hold

Baseline on this PC (`.venv/Scripts/python.exe -m pytest tests/unit -q`; the system `python` lacks `fonttools`):
**630 pass, 5 fail**: the 4 known plus `test_fit_grow_text.py::test_kpi_row_shares_the_height_a_sparse_callout_took`,
measured with the font-size session's **uncommitted** `fit-grow.js` edits in the working tree (new phases
`equalTiles` and `evenStats`; `evenStats` runs after the shrink guard and re-runs it). The test's message string is
stale ("KPI row takes a share" vs the code's "KPI row beside a sparse text band takes a share") and its KPI number
comes out 41 px (< 48). Both belong to that session; not edited here. The guard checks (runs last, idempotent, floors)
and the `fontexp_replay` numbers wait until that work is committed; then the step 0 merge (a fast-forward,
`feat/derived-blocks` is an ancestor) goes to the user.

**Merge check on the committed font-size work (2026-10-07, `a77dc23`):** unit tests **634 pass, the 4 known failures**
(the KPI test passes once committed). Shrink guard: still the last phase (every growing phase runs before it;
`evenStats` only shrinks and the guard runs again after it); no text under 14 px on R1's replay; a second compile
never shrinks anything. A second compile still grows type on 3 of 24 fitted slides (step 0's fit-grow: 5 of 24), a
grow-phase trait, not the guard. **R1 replay (`fontexp_replay`, `output/fontexp4`): broken words 5 → 6, overlap slides
4 → 5** against step 0: "₹59.8" breaks again on gj-h1 slide 14. Cause: `growText` grows the left column's card titles
(16 → 19 px) and icons, then pins both `w="max"` columns (789 / 405 px), so the KPI tiles on the right lose ~10 px; the
growth search rejects a word that becomes too wide but lets a word that was already too wide get narrower room. Not a
guard fault (the number is at its 28 px floor).

**Fixed (D12 (4), this session, 2026-10-07), two parts in `src/node/fit-grow.js`:**
1. Growth search: a growth step is rejected when it makes any word on the slide too wide, or a too-wide word wider,
   by more than 1 px (`overAll`; before, only the growing texts were checked). Alone this was not enough: "₹59.8"
   was already 16 px too wide before any growth (72 px box), and step 0 had escaped only because growing text in its
   `w="max"` column happened to widen the column, which the new width pinning prevents.
2. Shrink guard, new first step: a text too wide inside a box fit-grow pinned (its w was flexible; never an author's
   width) takes the px it lacks from its wider pinned neighbour, innermost box first (tile, then column), scaled by
   the word's share of the box; kept only under the guard's rule (total overflow down, no new too-wide word), else
   it shrinks as before. gj-h1 slide 14: right column +76 px, no warning left.
**R1 replay (`output/fontexp6`): broken words 4, overlap slides 4** (step 0: 5 / 4; committed font-size work: 6 / 5):
"₹59.8" and "Projected" now fit. Left: "Governance", "Recalculation", "Recommendation" (6-column table), "₹1.80".
Fixture `tests/fixtures/shrink_guard/g4-pinned-columns.xml` + test; a second compile makes no guard edit.
