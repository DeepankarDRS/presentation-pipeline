# KPI node pilot: decision record and replay plan (2026-10-11)

Branch `feat/kpi-node` (from `feat/slide-quality` at `a76a7a0`). Planned 2026-10-11; built and replayed the same day (§7).
Restarts derived nodes with one component, the KPI row, as an opt-in pilot. The bar is today's LLM KPI
slides (after palette tokens, geometry check, fit-grow fixes, `kpi_grid`), not the 1a ones.

## 1. Decision D13 (user, 2026-10-11): option B, element refs

**The LLM composes the KPI tiles with ordinary POM nodes; content comes by reference per element.**
It replaces, for `kpi_row` only, the D10 derived tag (`<KpiRow ref variant/>`) and the KPI variants of
`block-variants-look-spec.md` §4 (code-drawn looks). Native nodes keep D10's whole-component `ref`.
Card grid / callout / header are not in the pilot; if the pilot passes, the same mechanism is the
candidate for them (`cards.2.title`, `.body`, `.tag`).

```xml
<HStack h="170" gap="12">
  <VStack grow="1" padding="18" backgroundColor="$surfaceAlt" borderLeft.color="$accent" borderLeft.width="5">
    <Text ref="kpis.0.label"/>
    <Text ref="kpis.0.value"/>
    <Text ref="kpis.0.note"/>
  </VStack>
  <!-- one container per item, any arrangement: tiles, strips, a dark focus panel, stacked rows … -->
</HStack>
```

| The LLM decides | Code decides (overrides the LLM) |
|---|---|
| containers, arrangement and orientation, fills, borders, bars, dividers, icons, all colours as `$tokens` | the text of every ref Text, verbatim from the plan (`kpi_labels` / `kpi_values` / `kpi_deltas`) |
| where each label / value / note sits; `size="hero"` on the focus item's value only | **one number size for all `.value` refs of a component**, fitted to the tightest box; the unit span (one value parser, V15); the shrink guard |
| a `color="$token"` on a ref Text (e.g. light text on a dark panel it drew) | label / note size from the type ramp; `fontSize` on a value is removed |
| | colour of a ref Text with no `color`: the item's tone ink (`negativeText` …) or the role default (label `accentText`, value `textMain`, note `textMuted`) |

Ref grammar: `<component_id>.<item index>.<label|value|note>`; `component_id` is the plan's id (as in 1a).
Each item's **value** must be placed exactly once; label and note at most once (a note only when the plan
has one). Nothing else is content: any other Text, Shape or Icon is the LLM's decoration.

### Why (evidence)

**1a blind marks, KPI slides** (`output/1a-testpc2/sheets/marks.csv` joined with `key.json` and each
slide's `skeleton.xml`; the per-slide table was printed in this session):

| | nodes won | LLM route won | same |
|---|---|---|---|
| all 30 pairs | 7 | 18 | 5 |
| the 4 slides with a `KpiRow` | 0 | **4** | 0 |

Reasons on the 4 KPI losses: "kpi cards with color code is better", "green color, kpi cards center
association", "color code for the cards made it better than 2 kpi cards", "color code and size and spacing
look like a filled slide". Over the 18 LLM wins the reasons name colour 10 times, size 8, icons 4.

In 1a the KPI node drew one plain look: no tones (V10 not built), no icons (a block cannot choose one),
variants validated but not drawn. So the loss was mostly the look, not the abstraction. Option A
(`KpiGroup` + named variants) could add colour once tones exist, but every new look or icon needs code,
and the LLM left the default on 73% of nodes in 1a. Option B gives the LLM what it won on (colour by
token, icons, arrangement) and keeps in code what nodes did better (verbatim content; broken words 0 vs 6
in 1a; one number size).

**Rejected on the way (same session):**
- *The research brief's `KpiCard` with `hierarchy` / `surface` / `shape` / `accent` / `deltaStyle` attributes and
  `KpiItem` children*: raw hex accents and a different accent per card break D1 / colour roles; `role`
  primary / supporting re-adds the tiers dropped in V4; `trend` / `target_progress` need data the plan does
  not have (D12 open, §12 content policy); five free axes ≈ 100 combinations no one can contrast-check, with
  an LLM that mostly keeps defaults. Kept from it: data by reference, allowlists, code-owned geometry,
  "direction is not tone", and the metric list (repair rate added to the pass / kill line, §4).
- *Colour-based variants* (`plain` / `filled` differ only in fill): user, 2026-10-11, colour always comes
  from `palettes.yaml`; a variant may only change structure.
- *Structure-only variants on a group node* (`tiles` / `strip` / `edge` / `bare` / `inverted`, orientation by
  the box, `list` = a tall `strip`, tag `KpiGroup`): rendered (`docs/eval/kpi-node/option-a-*.png`), then
  superseded by B, which lets the LLM draw any of them and more without code.

Renders of five looks B allows, all from one JSON (`docs/eval/kpi-node/option-b-look-1..5.png`; hand-written
skeletons + a prototype fill step, `output/kpi-variants/kpi_refs_b.py`, gitignored): tiles with icons and
toned tints; two strips (totals / toned ROAS); side bars; the focus number in a dark panel beside a 2 × 2
grid; stacked rows with icons beside a chart.

### Validation codes (validator, before `normalize_xml`)

| Code | Severity | Meaning → handling |
|---|---|---|
| `NODE_REF_UNKNOWN` | error | a ref names no component, an index past the plan's items, or a field other than label / value / note → repair |
| `NODE_REF_DUPLICATE` | error | the same ref twice → repair |
| `NODE_ITEM_MISSING` | error | an item's value has no ref → repair (a number would vanish) |
| `NODE_FIELD_MISSING` | warning | an item's label, or a note the plan has, has no ref → counted; the policy is set from the paid check |
| `NODE_BYPASSED` | warning | a plan value typed as plain text instead of a ref → kept, counted |
| `NODE_ATTR_IGNORED` | warning | `fontSize` on a value ref, text inside a ref Text, a literal colour → removed |
| `NODE_FOCUS_UNNAMED` | report | one item's container is drawn apart from its peers (fill differs) but the plan names no focus, or names another → checking loop; the plan's design hint stays the only source of a singled-out item |
| `LITERAL_COLOR` | as today | — |

## 2. Free replay (LLM-free, this PC) — plan

**Approved 2026-10-11 (user), with the build in §3.**

**Question:** on today's compositions, does the ref-fill step lose anything, and can the LLM's KPI XML be
expressed as element refs at all?

**What it can and cannot show.** Converting the saved XML keeps the LLM's composition, so the replay tests
code's half of B (text, sizing, colour defaults) and the mapping, not the LLM's freedom with refs (the
paid check does). Saved plans have no `kpi_tones` (V10 not built), so the replay has no tone colours.

**Inputs** (counts from the `slides.json` scan in this session, before de-duplication):
- **Today's route:** `output/q1008/` (six-case run quality-1008, 6 decks, 8 `kpi_row` components on 6
  slides) and `output/run-1008/` (1 slide). The fair bar.
- **Older routes, recompiled on today's compiler:** `output/step0/` (7 KPI slides; `nk/` excluded as in
  D11), `output/colour-roles/` (1), `output/critic-on/` and `critic-on2/` (3 each; de-duplicated if one
  deck). Reported separately, since their XML is not today's generator.

**Steps** (`scripts/kpi_replay.py`, new):
1. **Map:** in each slide's XML find the Text whose text (Span markup stripped, whitespace and minus signs
   normalised, unit spans re-joined) equals a plan label / value / delta of a `kpi_row` component.
   Already seen: the LLM writes `₹4.2<Span>Cr</Span>`, so a plain substring check finds only 16 of 30
   values on q1008. Replace each match with `<Text ref="cid.i.field"/>`, keeping a `$token` colour.
2. **Fill + compile** (arm B): the fill step from §1 → normaliser → fit-grow → compile, Inter, today's
   commit. Arm A: the same XML compiled unchanged.
3. **Score** (both arms, per slide): broken words / `WORD_TOO_WIDE`; number sizes per component (count of
   distinct sizes, max / min); fill (`GEOM_CARD_EMPTY`, `GEOM_SLIDE_SPARSE`); `LOW_CONTRAST`; values on the
   slide that differ from the plan (A's retyping errors, by the same normalised match).
4. **Mapping rate:** share of plan items whose value / label / note were found, with every miss listed
   (dropped, retyped differently, merged into one Text, drawn as a table). This is the feasibility check.
5. **Blind sheet** (`scripts/node_test_sheet.py` reused): only slides whose renders differ, A / B sides
   shuffled, for you.

**Replay pass line** (all on today's-route slides): 0 broken words in B; 1 number size per component in B
(the hero excepted); 0 values in B that differ from the plan; B not worse than A on fill or contrast; no
blind loss beyond 1 slide. **Kill / rethink:** value mapping rate < 70% (the LLM's KPI XML does not split
into label / value / note per item, so the ref granularity is wrong).

## 3. Build, before the replay (after this plan is approved)

- Record the unit-test baseline first (AGENTS.md: 826 pass + the 4 known failures).
- `src/compiler/nodes/element_refs.py`: parse, validate (§1 codes), fill text, colour defaults, remove value
  font sizes, mark each component's values as one peer group for fit-grow (check first what fit-grow's
  `growStats` / `kpi_grid` already share; add a group marker only if they do not).
- One shared value parser (V15) in `src/compiler/`, used by the fill step, the composer and fit-grow's
  unit spans.
- Setting `blocks: off | kpi` (only `kpi_row` becomes refs; `off` = today). Generator prompt line for a
  `kpi_row` under `kpi`: ids and field names, item count, longest value length, the focus item and tones when
  the plan has them, the role colour tokens; no values (the 1a lesson: content by reference only).
- Unit tests: grammar, every code in §1, verbatim fill, peer size, tone defaults, token-only colours,
  Python 3.11 parse.

## 4. Paid check (after the replay; ask first)

Generator only, on saved plans (no planner rerun): `deck-qbr-data` + `gate-deck-cheffin-full` (3 KPI
components), arm B new vs today's route from `q1008` (already paid). Estimate ≈ $0.3–0.4; the exact list and
cost are asked for before running. Whether to add a planner call for `kpi_tones` first (V10) is a decision
for that request.

**Pass:** B preferred on ≥ 60% of KPI slides blind (a tie counts half); 0 broken words; 0 values not from the
plan; value refs ≥ 90% per item, first try; repair rate ≤ today's. **Kill:** B preferred on < 40%.

## 5. Look-spec decisions under B

**Decided 2026-10-11 (user): all six as recommended.** On V7 the user added: new colours may be authored in `palettes.yaml` for every palette. So `panelDark` / `onPanelDark` are derived by `palette_tokens.py` by default, and a palette entry may author them (authored wins, as `neutral` does today); the contrast test covers both

| # | Under B | Recommendation |
|---|---|---|
| V2 | number caps | code keeps them: 96 px for peers, 120 px for a `size="hero"` value |
| V7 | dark palettes | the LLM draws dark panels with tokens, so it needs a token that is dark on every palette: add derived `panelDark` + `onPanelDark` to `palette_tokens.py` (today `$textMain` is light on dark palettes) |
| V9 | tone tokens | no new tokens: `positiveSoft` / `negativeSoft` / `warningSoft` (tints) and `positiveText` / `negativeText` / `warningText` (ink) already exist |
| V10 | planner `kpi_tones` | yes, needed for B's colour defaults and the LLM's toned tints |
| V15 | one value parser | yes (§3) |
| V16 | tones as Keep / Remove | yes (tones are inferred content, §12) |

Spec names → `palette_tokens.py`: `accentTint` → `accentSoft`, `accentInk` → `accentText`, `positiveTint` /
`negativeTint` / `warningTint` → `*Soft`, `positiveInk` / `negativeInk` / `warningInk` → `*Text`, `onAccent` →
`onAccent`; `panelFill` → `surfaceAlt`; `darkFill` / `onDark` → the new `panelDark` / `onPanelDark` (V7).

## 6. Found on the way

`src/compiler/pptx_merge.py` does not rename slide media: in a merged deck a later slide's `image1.png` is
replaced by the first slide's (reproduced on `output/kpi-variants/b/`: slide 4 showed slide 1's wallet icon
for its gauge). Used by `src/agents/deck_nodes.py`, so merged decks with icons can show wrong icons. Proposed
as its own fix session; may explain 1a mark 6.4 ("1 has wrong icons") if the sheets were made from merged decks.

## 7. Build (§3) and free replay (§2) — done 2026-10-11

Unit-test baseline before the change: 839 pass + the 4 known failures.

**Built** (opt-in, `POM_BLOCKS=kpi`; unset / `off` = today's route, no behaviour change):
- `src/compiler/nodes/element_refs.py`: `fill_refs(xml, plan)` parses `<Text ref="cid.i.label|value|note"/>`,
  raises the §1 codes (`NODE_REF_UNKNOWN` / `NODE_REF_DUPLICATE` / `NODE_ITEM_MISSING` errors → repair;
  `NODE_FIELD_MISSING` / `NODE_BYPASSED` / `NODE_ATTR_IGNORED` warnings; `NODE_FOCUS_UNNAMED` report), writes the
  plan text verbatim, removes value `fontSize`, sets label / note to the ramp (16), colour defaults (LLM `$token`
  wins → tone ink from `kpi_tones` → light ink on a dark fill the LLM drew → role default). A slide that comes back
  already filled (visual repair) counts its values as placed. `prompt_line(comp)`: ids, fields, lengths, focus,
  tones, tokens; no values.
- Peer group: fit-grow's existing groups need tiles in one HStack (or a % grid), so B's free arrangements were not
  covered → the fill step ids values `kpiv-<cid>-<i>` (hero `kpih-…`); fit-grow `refGroups` grows each component's
  values together to its fullest box's target fill (cap 96, hero 120) wherever they sit, evens them after the
  guard, labels grow with them. Values start at 28 px (guard floor) — the ramp's 44 first tried was too wide on a
  dense slide (spill fixer shrank the whole slide) and too full to count as sparse elsewhere (nothing grew).
  A hero starts at 72 (ramp single stat; in a content-height card nothing grows it). A one-item `kpi_row` is a hero.
- `src/compiler/value_parts.py` (V15): one verbatim split (`"₹4.2 Cr"` → `"₹4.2"` + `" Cr"`); the composer
  (`scripts/phase0b/render.py`) and the variant gallery use it now.
- V7: `panelDark` / `onPanelDark` derived in `palette_tokens.py` (light palettes: `textMain` / white; dark: the
  accent hue at lightness 0.2), authored entries win; ≥ 4.5:1 on all 18 palettes (test). The one-dark-panel-per-deck
  softener also takes `$panelDark`. house-style prose still says "inverted panel `$textMain`" (left so `off` stays
  today's prompt); only the KPI prompt line names `$panelDark`.
- Validator: fill before `normalize_xml`; ref errors block with retryable diagnostics. Generator: under `kpi` a
  `kpi_row` gets the ref line instead of its data; slide-level `kpi_*` keys are dropped.
- Tests: `tests/unit/test_element_refs.py` (58: grammar, every code, verbatim fill, peer ids + one size through the
  real compiler, hero, tones, dark fill, token-only colours, panel tokens on every palette, parser, prompt, validator).

**Replay** (`python -m scripts.kpi_replay`; results `docs/eval/kpi-node/replay/summary.md`, run output in
`output/kpi-replay/`). Today's route = 7 slides / 9 `kpi_row` components (q1008 + run-1008, de-duplicated).

| pass line (today's route) | result |
|---|---|
| value mapping ≥ 70% (kill line) | **100%** values, 100% labels, 100% notes (older routes 98 / 98 / 79%: notes merged into the value Text) |
| 0 broken words in B | 1, the same word in A: the kicker "PERFORMANCE" (not KPI text, pre-existing) |
| 1 number size per component (hero excepted) | 9 / 9 (A also 9 / 9: fit-grow already evens a row) |
| 0 values in B that differ from the plan | 0 (A: 0 too) |
| B not worse than A on fill / contrast | contrast equal (4 / 4); `GEOM_CARD_EMPTY` 8 → **9** (CHEFFIN slide 4, the known 7-tile dense slide: its 7th tile 51% full) |
| blind: no loss beyond 1 slide | **passed**: B 3 wins, 3 ties, 1 loss (score 0.643; marks `docs/eval/kpi-node/replay/marks.csv`) |

Sizes: QBR exec summary 32 → 60 px (tiles filled), CHEFFIN 71 / 51 → 70 / 51, heroes 120 / 120 / 72 as A; product
launch 34 → 28 (slide full, table squeezed: nothing may grow), agency takeover 22 → 28.

**Found (not fixed):**
1. *Sentence "values"* — agency takeover's `kpi_row` has five sentences as `kpi_values` ("Generic search consumed
   the largest budget pool and returned around 0.29x ROAS."). A drew them as body text with coloured spans; B
   draws them bold at value size. A planner / plan-check issue (that is a card grid), but under B it shows.
2. *LLM text styling inside a KPI text is lost*: caps the LLM typed ("REPEAT REVENUE" for plan "Repeat revenue";
   POM has no text-transform) and coloured spans inside a value. Needs an attribute (e.g. caps) if it matters.
3. *Labels at the ramp's 16 px* break a word in a very narrow tile ("Ad / sales", CHEFFIN slide 4, A drew 14).

**Blind marks (user, 2026-10-11), unblinded:**

| pair | slide | preferred | user's reason |
|---|---|---|---|
| 1.1 | product launch / 3 | A | "liked that units size can be small or big" — B draws every unit at 0.45 × the number (V15) and its numbers at 28 vs A's 34 (full slide) |
| 1.2 | QBR exec summary / 1 | **B** | "better size for the kpi card values" (32 → 60 px) |
| 1.3 | agency takeover / 0 | **B** | "like the bold contrast but … not all things bold" — the sentence-values finding (1 above) |
| 1.4 | all-nodes dense / 1 | same | icons always on top; text in the "repeat revenue" card not readable — both arms, the LLM's composition, not the fill |
| 2.1 | CHEFFIN / 1 | same | "no change" |
| 2.2 | CHEFFIN / 4 | **B** | "proper use of logo size" |
| 2.3 | QBR run-1008 / 1 | same | "no change" |

**Replay verdict: pass** on today's route (mapping 100%, one size 9 / 9, 0 off-plan values, blind 1 loss), with two
misses against the letter of the pass line: 1 broken word (the same kicker in A) and `GEOM_CARD_EMPTY` 8 → 9.
Inputs for the paid check (§4): the unit-span ratio (1.1: the user wants it to vary, not fixed at 0.45), sentence
values in a `kpi_row` (plan check), icon position is the LLM's (1.4: a prompt-line hint at most).

## 8. After the marks: unit size, sentence values, icon hint, gallery (2026-10-11)

User on the three findings: units vary "small or large based on the characters count and spacing"; sentence
values: "you can, but how"; icons: a prompt-line hint. Then: show what B's KPI cards look like.

- **Unit size** (`value_parts.unit_share`): one share per component from its longest unit — 1 character
  (`%`, `x`, `M`, `L`) 0.6, 2-3 letters (`Cr`, `pts`, `ms`) 0.5, a word (`months`, `min/wk`) 0.42; floor 14 px.
  Word units now split ("14 months" → `14` + small ` months`). Spacing is fit-grow's: it grows the whole value.
- **fit-grow measured a sized Text as one size** (found by the gallery): word width (`overBy`, the guard),
  line count and natural height took every run at the Text's size, so a small unit counted as full size — a
  value with a word unit stopped growing (39 px in a 280 px tile) and the guard shrank numbers for their
  unit. Now run-aware (`runWidest`, `lineCount`, `natural`). POM itself lays such a Text out as two lines;
  `oneLineValues` gives a ref value whose runs fit one line `h` = one line (its tile sat out of line).
  A hero's label / note now grow with it (`growStatSides`, ≤ 24 px).
- **Sentence values**: plan check `KPI_VALUE_TEXT` (`plan_checks.find_problems`, a re-ask code: the planner
  is asked once more, told kpi_values hold the figure and findings go in a card_grid / bullet_list; still
  there → flagged in `plan_flags`). Fill fallback: a sentence value is drawn as body text (18 px, not bold, not
  in the size group), `NODE_VALUE_TEXT` warning. The plan check runs on both routes (`off` too): it is a plan
  fix, and saved-plan replays and the generator-only paid check are not affected.
- **Icon hint** in the KPI prompt line: an icon goes in the label row (left of the label, or right with
  `spaceBetween`), not alone and centred on top.
- **Gallery** (`python -m scripts.kpi_gallery`, `docs/eval/kpi-node/gallery/`): six looks the LLM may compose
  (tiles, strip, side bars, focus panel, rows beside a chart, hero tier) × two plans (QBR 4 KPIs, ROAS 5 KPIs
  with tones) × corporate-slate / gj-h1 / graphite-dark, real fill + fit-grow + POM. Skeletons are
  hand-written; the paid check shows which ones the LLM writes.
- **Item counts** (`focus-panel-counts.png`, the same focus-panel skeleton at 1-7 items): there are no
  variant triggers or count rules — the LLM picks the arrangement from the item count in its prompt line.
  Code's half holds at any count (text, one size, colours). What the LLM must get right: 1 item in a
  two-column shape leaves half the band empty; 6-7 items in a 2 × 2 grid drop items — the validator raises
  `NODE_ITEM_MISSING` and the slide goes to repair, so a value is never silently lost.

**Replay v2** (2026-10-11, after §8; `docs/eval/kpi-node/replay-v2/`, run output `output/kpi-replay/`, v1 kept in
`output/kpi-replay-v1/`). The fit-grow measuring fix applies to both arms (A's own unit spans too), so A moved
as well.

| today's route | v1 A / B | v2 A / B |
|---|---|---|
| value mapping | 100% | 100% |
| one number size (components with figures) | 9 / 9, 9 / 9 | 8 / 8, 8 / 8 (agency takeover: sentences, now body text) |
| `WORD_TOO_WIDE` · broken words | 7 / 7 · 1 / 1 | 7 / 7 · 1 / 1 (the same CHEFFIN 4 words and kicker) |
| `GEOM_CARD_EMPTY` | 8 / 9 | 7 / 9 (run-1008: the callout under the KPIs, 48% full; CHEFFIN 4: the 7th tile) |
| `LOW_CONTRAST` · values off the plan | 4 / 4 · 0 / 0 | 4 / 4 · 0 / 0 |

Older routes v2: one size 15 / 15 both, `GEOM_CARD_EMPTY` A 9 / B **6** (v1 9 / 12), sizes up on both arms
(critic-on exec summary A 47 → 57, B 48 → 67). By eye: the QBR "14 months" tile now lines up with its peers
in B (A still sits out of line: POM measures its span at full size, `oneLineValues` only takes ref values);
the agency-takeover sentences are 18 px body text in B, smaller and plainer than A's coloured 22 px lines;
word units now split in B ("15 min/wk" → small "min/wk"). The blind sheet is regenerated (same 7 slides),
`marks.csv` empty: marking it again is optional.
