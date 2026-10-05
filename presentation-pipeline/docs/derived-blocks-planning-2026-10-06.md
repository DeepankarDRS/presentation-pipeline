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

The kickoff says "in `pptx-post.js`". `pptx-post.js` runs once **per slide** (each slide compiles to
its own one-slide pptx); `deck_assembler` then merges them with `merge_pptx_files`, which keeps only
the first file's `presentation.xml`. Per-slide embedding would put fonts in slide 1 only and could
not subset by the deck's characters. So embedding happens **after the merge** (and for a one-slide
run, on that file). Details:
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
python -m scripts.eval_run deck-qbr-data deck-product-launch-data gate-deck-agency-takeover gate-deck-xtsy-qcomm gate-deck-cheffin-full gate-deck-all-nodes-dense gj-h1-regen --repeat 1 --label step0 --compose --bundle
```

**The test PC sends back one file: the bundle zip.** After 0.1 it carries, per case,
`decks/<case>__r1/{llm.pptx, composed.pptx, slides.json, run-manifest.json}` (the earlier docs asked
for the six `output/runs/` folders because `run-manifest.json` was missing; once 0.1 copies it, that
is unnecessary). `slides.json` holds every slide's plan **and** XML, which is what 1a and step 3 need.
Plus a one-line reply: did `composed.pptx` open in PowerPoint with Inter drawn. Back up the bundle:
1a and step 3 depend on it. Import: `python -m scripts.eval_import <zip>` → `docs/eval/step0/`.

## 3. Slot contract (draft for approval)

**One syntax:** `<VStack id="slot-<component_id>" … />`, self-closing. It is valid POM (an unexpanded slot
compiles to an empty box, so a missed expansion is visible, not a crash), takes layout attributes
naturally, and the id is the reference. The §2 tag form (`<CardGrid ref=…>`) is dropped. The header
uses the reserved id `slot-header` (step 1). Kinds without a block (pyramid, tree, layer, group,
branching flow, matrix until step 4) get **no slot**; the LLM draws them as today.

**Attributes the LLM may set on a slot:** `w`, `h`, `grow`, `alignSelf` (POM's layout attributes) and
`variant`. Nothing else: the block owns padding, gap, fills, borders and type. Any other attribute is
removed with `SLOT_ATTR_IGNORED`. The highlighted item (inverted tile, featured card, highlighted
row) comes from the plan's `design_hint` / `weight`, as the blocks do now; a `highlight` attribute is
added only if 1a shows the LLM needs it (simplicity).

**Variants** live in one file, `src/knowledge/core/block-variants.yaml` (the prompt renders it and the
validator reads it; a test fails on drift, like `capacity.yaml`). From the Genspark shortlist
(`docs/eval/genspark-variants/summary.md`); the first name is the default:

| Block (plan kind) | `variant` values | Code decides, not a variant |
|---|---|---|
| KPI row (`kpi_row`) | `plain`, `filled`, `inverted`, `hero` | two tiers at 6+ metrics; number size |
| Card grid (`card_grid`, grid / matrix) | `outline`, `filled`, `featured`, `numerals` | 3 items → stacked rows; titles only → ruled list; no orphan last row |
| Card steps (`card_grid`, steps) | `cards`, `rail`, `columns` | — |
| Table (`table`) | `plain`, `zebra`, `highlight_row`, `dark_header` | column widths |
| Chart (`chart`) | `labelled`, `horizontal`, `native` (line / doughnut / area stay the planner's `chart_type`) | — |
| Bullets (`bullet_list`) | `plain`, `icon`, `tiles`, `columns` | tiles only when every word fits |
| Callout (`narrative`) | `rule`, `tinted`, `dark`, `quote` | — |
| Header (`slot-header`) | `standard`, `inverted` | — |
| Timeline (`timeline`) | `rail`, `cards`, `vertical`, `columns` | long labels → `cards` / `vertical` when no variant is set |
| Process steps (`process_arrow`, linear `flow`) | `chevrons`, `numbered`, `alternating`, `step_cards` | grows to fill a tall slot (§5.4) |

In **1a** the blocks have only their current single look: `variant` is accepted, validated and
counted, but not rendered. The look and the variants arrive in step 1.

**System-prompt rules (rendered once, ≈ 10 lines; recipes for block kinds are removed):**
1. For every component in the SLOTS list, write exactly one empty `<VStack id="slot-<id>" … />`. Never
   write its content and never put children in it.
2. Size a slot with `w`, `h`, `grow` like any box; set `variant` only from its listed names.
3. Components not in the SLOTS list (pyramid, tree, …) are drawn as before.
4. Text beside slots (headline, takeaway, labels) copies the plan's text; do not add facts.
5. Do not draw a component that has a slot.

**Prompt line per slot** (rendered from the plan; the data itself is not sent):
`slot-c2 · kpi_row · 4 tiles · weight hero · variants: plain|filled|inverted|hero`
`slot-c3 · table · 7 rows × 5 columns · weight supporting · variants: plain|zebra|highlight_row|dark_header`
`slot-c5 · card_grid(steps) · 4 phases with detail · weight hero`
Minimum-size hints per kind are left out of v1; 1a measures how often `SLOT_OVERFULL` happens first.

**Error codes** (validator diagnostics; errors go to the existing compile repairer with guidance text,
warnings go to the manifest and the `node_bypassed` counter):

| Code | Severity | Meaning → handling |
|---|---|---|
| `SLOT_UNKNOWN_REF` | error | id names no component → repair |
| `SLOT_DUPLICATE` | error | same ref twice → repair |
| `SLOT_MISSING` | error | a block-kind component has no slot and its text is not in the XML → repair (content would vanish) |
| `SLOT_BYPASSED` | warning | no slot, but ≥ 50% of its item text is hand-built in the XML → kept, counted (`node_bypassed`); the policy for step 2 is decided from 1a's rate |
| `SLOT_KIND_NO_BLOCK` | error | a slot for a kind without a block → "draw it yourself" |
| `SLOT_CHILDREN_DROPPED` | warning | the slot had children → replaced by the block |
| `SLOT_ATTR_IGNORED` | warning | attribute outside the allowed set removed |
| `SLOT_VARIANT_UNKNOWN` | warning | default variant used |
| `SLOT_NO_SIZE` | warning | no `w` / `h` / `grow` and none inherited → `grow="1"` |
| `SLOT_EMPTY_PLAN` | warning | the component has no content (step 0's re-ask failed) → nothing drawn, `plan_flags` |
| `SLOT_OVERFULL` | report | smallest type step still short (as `SLIDE_OVERFULL` today) → checking loop |
| `SLOT_UNDERFILLED` | report | block fills < 60% of its slot (§5.4) → checking loop |

## 4. 1a protocol (draft for approval)

**Question:** does the LLM write slots correctly, and does the slot route not lose on mistakes or variety?

**Inputs:** step 0's `slides.json` (plans + the off arm's XML) and its manifests. Models, temperature and
`max_tokens` fixed as in `models.yaml` (generator = gpt-4.1); one run, ×1.

**Slides (≈ 24; the exact list cannot exist before step 0's plans do).** A script
`scripts/slot_test_select.py` picks them by rule from step 0's plans and writes
`docs/eval/step0/1a-slides.json`; **you approve the list before any paid call**. Rule:
1. Pool = the three hold-out decks (qbr, launch, agency) + `gate-deck-all-nodes-dense` + XTSY.
2. Exclude every slide the slot prompt's examples were built from (Phase 0c skeletons: CHEFFIN 2 and
   the CPC slide, XTSY "automation", gj-h1 dense). The prompt must not be tested on its own examples.
3. Cover every block kind ≥ 3 times (kpi_row, card_grid grid / steps / matrix, table, chart, bullets,
   process_arrow / flow, timeline, narrative, caption), ≥ 3 slides with 3+ components, ≥ 3 slides holding
   a kind without a block (pyramid / tree / matrix → tests `SLOT_KIND_NO_BLOCK` and "draw it yourself"),
   ≥ 3 slides from each deck. Fill to ≈ 24 by lowest-numbered slide first.
(Hold-out plans were seen while fixing blocks, so they are no longer pristine for *block* behaviour, but the
LLM never saw them with a slot prompt, which is what 1a tests.)

**Arms:** (A) *off* = step 0's saved XML for the slide, no new call; (B) *slots* = the generator with the §3
slot prompt on the same plan, expanded by `scripts/phase0b/expand.py`. Same `<Theme>` in both: B's blocks
are recoloured from the deck's palette with role-based text colours (the §1a research-renderer change),
so the blind comparison judges layout and fill, not palette.

**Measures and kill criteria (§14.5 + the new cross-deck one):**

| # | Measure | How | Pass |
|---|---|---|---|
| 1 | **Slot compliance, first try** | classify every component of a block kind: ok / wrong ref / missing / duplicate / children / bypassed / attr / variant; slide-level "all ok" reported too | component-level ≥ 90% |
| 2 | Invented words inside blocks | words in rendered block text not in the plan | 0 |
| 3 | Broken words, overlapping text | LibreOffice render of the expanded deck vs step 0's `llm.pptx` (`fontcheck.py`, `check.py`) | ≤ off arm |
| 4 | **Blind side-by-side** | `scripts/slot_test_sheet.py`: per slide two images, left / right randomised by a fixed seed, no labels, 4 slides per sheet; you mark 1 / 2 / equal and a reason (readability, fill, overlap, empty, designed); key kept in a separate file | (slot wins + ½ ties) / N ≥ 0.6 |
| 5 | Within-deck variety | §1b | not > 0.05 below off |
| 6 | Cross-deck variety (informational, D2) | §1b | reported, not a kill criterion |
| 7 | Tokens and cost per slide | generator calls in the manifests: slots vs step 0's generator calls on the same plans (like-for-like) | informational; flag if input per slide is > 10% above off |
| 8 | Fallback rate | slides with a compile repair, an error code, a retry, `SLIDE_OVERFULL` | reported; used to size step 2 |

Fail on 1, 2, 3, 4 or 5 → stop slots, keep blocks: composer + planner `arrangement` field (§14.1
option 2). With ≈ 50 components the compliance estimate has a ±8-point margin, so a result near 90% is a
re-run decision, not a verdict (stated in the report next to the number).

**Build before the paid call (all LLM-free):** `scripts/from_plans.py` (the ≈ 30-line loader: a run's
`slides.json` → `state["slide_plans"]`; the graph's `route_after_start` already skips planning; also
reads the manifest's theme; Python 3.11-safe), `scripts/slot_test.py` (generator-only runner, writes
skeleton XML + manifest per slide), `src/prompts/generator/slots_system.j2` (the §3 rules),
`scripts/slot_test_select.py`, `scripts/slot_test_score.py`, `scripts/slot_test_sheet.py`,
`scripts/variety.py`, the role-based recolouring in the research renderer. The paid path is exercised
first by a scripted LLM that returns Phase 0c's 4 skeletons plus 6 deliberately broken ones (one per
`SLOT_*` error) so every classifier branch runs before money is spent. Cost ≈ **$0.5** (≈ $0.02 per slide,
24 slides). Test PC command (written when built): `python -m scripts.slot_test --run <step0 folders> --slides docs/eval/step0/1a-slides.json --label 1a`.
It sends back its output folder (skeleton XML per slide, manifests).

## 5. Open questions: recommendations

### 5.1 Checking-loop spec (for step 2; principle now, thresholds after 1a)

- **Trigger and place:** a graph node `layout_checker` after the validator succeeds (compile + slot
  expansion), before the visual critic. Only under `blocks: slots`; `off` stays the step 0 path.
- **Tier 1 (always, free, ≈ 1 s):** POM's own layout (`measure.mjs`): squashed boxes, overfull, words
  wider than their box (`WORD_TOO_WIDE`), `SLOT_OVERFULL`, `SLOT_UNDERFILLED`, text under its floor.
  **Tier 2 (render facts: broken words, overlaps, past-footer text)** only where a renderer exists, from
  the render the critic already makes; promoted to a loop trigger only if 1a / step 3 show tier 1
  missing things (both are computed there, so agreement is free to measure).
- **Fixes, code first:** for a block problem the code acts (switch to the next more compact variant, re-flow
  rows / columns, split KPI tiers). For a layout problem (slot too small, free text overflowing) one **LLM
  patch of the skeleton only** (≈ 600 tokens of XML + the issues stated in px: "slot-c3 needs 320 px, has
  240"), then re-expand, re-measure.
- **Best version:** lexicographic tuple (errors, squashed px, overfull px, broken words, overlaps, below-floor
  text); lower wins, a tie keeps the earlier version. ≤ 2 rounds; round 2 only if round 1 improved and a
  deficit above the 8 px tolerance remains.
- **Cost:** ≈ $0.01–0.025 per LLM round (design doc §14.6 token table), zero for code fixes. 1a's skeletons
  tell how many slides would trigger one; if under ~15%, the loop is a small cost.
- **Relation to today's nodes:** the compile `repairer` is unchanged (compile errors). The loop runs before
  the visual `critic`, which keeps judging what code cannot measure (hierarchy, balance); measured codes
  join `REPORT_ONLY_CODES`-style filtering so the critic never re-reports them; `visual_repairer`
  patches the skeleton (not whole XML) under slots.
- **Decide now:** the principle above. **Schedule for step 2:** thresholds, the code-fix list, tier 2 promotion.

### 5.2 #4 label tier ≥ 10 px

At 1280×720 one px = 0.75 pt (720 px = a 7.5 in slide), so 10 px is **7.5 pt**, 12 px is 9 pt (Genspark's
Super Agent spec used 9 pt tags), 14 px (the house floor) is 10.5 pt. **Recommendation: label-role text
(kickers, KPI labels, table captions) 12 px; 10 px only for the source / footnote line;** body stays ≥ 14.
You still have to look: before step 1 I produce one free test slide with the same mono label at 10 / 11 / 12 / 14 px
(and the same on a dark tile) from the research renderer; view it at 100% on the laptop and full-screen
projected. Rule: the smallest tier you can read comfortably from the back of the room. Needed before step 1
(blocks bake the tier in).

### 5.3 When `blocks: slots` becomes the default

Not after step 3: kinds without a block (matrix, pyramid, tree, layer, branching flow) would give a mixed
look, and the UI edit path is not planned. Recommended gates, all required: (1) step 3 passes the 1a criteria
on all six (seven) cases; (2) step 4 blocks are in; (3) **the edit service re-expands blocks after every edit**
(plan edit → re-draw; layout edit → XML edit → re-expand), which no step covers yet and which I add to
step 2's list; (4) fallback rate (slides sent to the composer or `off`) ≤ 10%; (5) cost per deck within ±20%
of off. Until then `slots` is opt-in per run (setting + UI advanced switch); `off` stays available.

### 5.4 Fill contract: blocks grow into a tall slot (for step 1)

Measure `fill = drawn height ÷ slot height`. Order, all within the plan's own text (never added content):
(1) type up to the role's maximum (step title ≤ 24, step detail ≤ 18, timeline label ≤ 32, date ≤ 14, short-list
text ≤ 28); (2) item boxes taller up to ×1.6 natural; (3) if `fill` < 0.6, **switch arrangement**:
process steps `chevrons` → `step_cards` / vertical, timeline `rail` → `cards` / `columns`, a ≤ 4-item list →
`tiles`; (4) otherwise centre the block in the slot (never a thin band hung at the top) and report
`SLOT_UNDERFILLED`, which the checking loop turns into a layout fix ("give slot-c3's height to slot-c2").
Caps follow the 2026-10-04 decision "fill the card, don't shrink it" (type grows, boxes do not balloon). Numbers
tuned in step 1 on the nodes demo render (free).

## 6. Decisions

| # | Decision | Recommendation | Status |
|---|---|---|---|
| D1 | §1a theme source: `palettes.yaml` only, derived role tokens + contrast test, packs carry structure, Inter + JetBrains Mono, `look` picked by the outline planner in step 2 | as written | **decided 2026-10-05: adopted as written** |
| D2 | §1b cross-deck check in the 1a kill criteria (content-controlled definition) | kill criterion | **decided 2026-10-05: within-deck only is the kill criterion; cross-deck measured and reported, informational** |
| D3 | Step 0 plan §2 incl. embedding at deck level in Python | as written | awaiting user |
| D4 | `gj-h1-regen` joins step 0's run (≈ +$0.7) | yes | awaiting user |
| D5 | Slot contract §3 | as written | awaiting user |
| D6 | 1a protocol §4 | as written | awaiting user |
| D7 | Checking-loop principle §5.1 | as written | awaiting user |
| D8 | Label tier (§5.2) | view the test slide first | scheduled, before step 1 |
| D9 | Default-switch gates (§5.3) | as written | awaiting user |
