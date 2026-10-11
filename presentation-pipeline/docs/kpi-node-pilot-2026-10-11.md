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
| blind: no loss beyond 1 slide | **waiting for your marks** (7 slides whose renders differ, `sheet-01/02.png`) |

Sizes: QBR exec summary 32 → 60 px (tiles filled), CHEFFIN 71 / 51 → 70 / 51, heroes 120 / 120 / 72 as A; product
launch 34 → 28 (slide full, table squeezed: nothing may grow), agency takeover 22 → 28.

**Found (not fixed):**
1. *Sentence "values"* — agency takeover's `kpi_row` has five sentences as `kpi_values` ("Generic search consumed
   the largest budget pool and returned around 0.29x ROAS."). A drew them as body text with coloured spans; B
   draws them bold at value size. A planner / plan-check issue (that is a card grid), but under B it shows.
2. *LLM text styling inside a KPI text is lost*: caps the LLM typed ("REPEAT REVENUE" for plan "Repeat revenue";
   POM has no text-transform) and coloured spans inside a value. Needs an attribute (e.g. caps) if it matters.
3. *Labels at the ramp's 16 px* break a word in a very narrow tile ("Ad / sales", CHEFFIN slide 4, A drew 14).
