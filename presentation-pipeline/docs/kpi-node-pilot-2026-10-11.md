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

## 9. Paid check: runner ready (2026-10-11), run on the test PC

User: go ahead. This PC has no API key (two-device workflow), so the run is the test PC's.
`python -m scripts.kpi_paid --repeat 3 --label kpi-paid --bundle` — generator only from the saved plans in
`docs/eval/kpi-node/paid-inputs.json` (q1008: deck-qbr-data slide 1, gate-deck-cheffin-full slides 1 and 4;
4 `kpi_row` components, corporate-slate), `POM_BLOCKS=kpi`, the real graph (generator → validator with the
ref fill → repairs; critic off). Arm A = q1008's XML recompiled on the same commit. 9 generator calls,
estimate ≈ $0.3–0.4 with repairs. Records the first try (refs placed, `NODE_*` codes), repair passes, cost, the
replay scores and a blind sheet; `output/kpi-paid/kpi-paid.zip` to email back (`--no-render` if LibreOffice is
missing there; `--rescore` here redoes the scores and sheet for free). Dry run here (`--dry`: a fake generator
answering with the mapped XML): 3 / 3 compile first try, refs 16 / 16, path and bundle work. Noted: the QBR
plan's hint names all four tiles (for colours), so `singled_out` finds no focus and the ARR tile drawn apart
reports `NODE_FOCUS_UNNAMED` (report only).

**Paid check result** (test PC, 2026-10-11, `--repeat 3`: 9 runs, **$0.296**; `docs/eval/kpi-node/paid/`; scores and
sheet redone here with `--rescore` on this commit):

| §4 pass line | result |
|---|---|
| value refs ≥ 90% per item, first try | **48 / 48 (100%)**; 0 runs with a `NODE_*` error |
| 0 broken words | **0** (A 0) |
| 0 values not from the plan | **0** |
| repair rate ≤ today's | 2 repairs in 9 runs (QBR r2, r3: 2 XML errors each, not refs; +$0.012 each). Today's route on these slides: 0 in q1008 (one run each), so not directly comparable; the first try's error text was not saved (runner gap) |
| B preferred on ≥ 60% blind | **0.556** (B 5, A 4, no ties): below pass, above kill (< 40%) |

What the LLM did with refs: all values placed every time; it still writes `fontSize` on values (removed,
`NODE_ATTR_IGNORED`, harmless); in QBR r1 it typed the four labels as plain text (verbatim, `NODE_FIELD_MISSING`
warnings); icons in the label row on QBR (the new hint), none on two of three CHEFFIN slide 4 runs.

Found by the paid runs and fixed in code (scores above include them):
1. *A KPI row sized by its content never grew* (CHEFFIN slide 1's second row stayed at 28 px under a
   `grow="3"` row; the LLM's own XML had 51): a ref group in cards without `grow` / `h` may grow while the slide
   fits and nothing overflows (`search(..., ignoreFill)`).
2. *Then it outgrew the main row* (92 px under 72): the plan's `weight` now reaches fit-grow — value ids carry
   the rank (`kpiv<rank>-…`, 0 hero … 3 minor) and a component never grows past one the plan weights higher;
   a content-sized group also not past the slide's other KPI numbers. CHEFFIN slide 1 now 72 / 72, 72 / 66,
   72 / 72. The test-PC runs were filled before ids carried the rank; `--rescore` adds it from the plan.
3. *A Python string turned `\b` into a backspace in a fit-grow regex* while I edited (cap silently off); fixed,
   no other control characters in the changed files.

**Blind marks (user), unblinded:** QBR exec summary B 2 / 3 ("better size", "better positioning"; A once:
"executive summary better"); CHEFFIN slide 1 B 3 / 3 ("overall better", "heading colors" ×2); CHEFFIN slide 4
(7 tiles) A 3 / 3 ("icon look cool"). All three B runs of slide 4 drew no icons; A has one per tile. Likely the §8
icon hint ("in the label row, not alone and centred on top"): 7 narrow tiles have no room beside the label, so
the LLM left icons out. Without slide 4 B is 5 / 6. **Verdict: rethink zone (§4), one cause.** Proposed (not
built, asking the user): the prompt line says an icon per item is welcome, in the label row where it fits,
above the label in a narrow tile; then a paid re-run of CHEFFIN slide 4 × 3 (≈ $0.10) and marks on those pairs.

## 10. Next: the KPI looks in full decks (user, 2026-10-11)

User: no icon re-run; move on and see the variants in action. Layouts the LLM chose in the 9 paid runs, the
same in every repeat: QBR 4 KPIs → 2 × 2 grid, ARR tile tinted, icons in the label row; CHEFFIN slide 1 →
3 tiles with Combined ROAS on a dark panel + 2 red-toned tiles; CHEFFIN slide 4 → 7 tiles in a row, no icons.
Variety comes per slide, not per run.

**Run (test PC, approved to plan; ≈ $1.0–1.3):** the full pipeline (planner included) with refs on, in one
PowerShell window (`$env:` lasts only for that window; a `POM_BLOCKS=kpi` line in `.env` works too but stays on
for every later run until removed):

    $env:POM_BLOCKS="kpi"; python -m scripts.eval_run deck-qbr-data gate-deck-cheffin-full gate-deck-all-nodes-dense gate-deck-xtsy-qcomm --repeat 1 --label kpi-decks --bundle

**Then, here (free):** render the bundle; per KPI slide, name the layout the LLM chose and its item count; a
contact sheet per deck beside its q1008 version (today's route, 2026-10-08); blind pairs of the KPI slides if
the user wants to mark them. The planner reruns, so plans differ from q1008: a deck-level look, not a strict A/B.

**Full-deck run done** (test PC, 2026-10-11, commit `a1cc01c`, 4 decks / 25 slides, **$1.13**; `docs/eval/kpi-node/decks/`).
The test PC ran before the paid-check sizing fixes; the 4 KPI slides were recompiled here on the current commit
for `kpi-slides.png` (both runs), the deck sheets use the bundles' own renders. The planner reran, so plans
differ from q1008 (XTSY: no `kpi_row` in either run).

| KPI slide | refs on: layout the LLM composed | sizes (today's route → refs) |
|---|---|---|
| QBR exec summary (4) | row of 4, ARR on a dark panel (the hint asked "inverted panel"), icons in the label row; callout + segment table below | 32 → 55 px |
| all-nodes dense (5) | row of 5 above a full-width chart, first tile tinted; the planner put "repeat revenue 62%" in the row (q1008 had it as a separate hero panel) | 30 / 72 → 47 px |
| CHEFFIN slide 1 (5) | one row of 5 (the planner made one component, q1008 two tiers), Combined spend tinted, a dark "core diagnosis" panel below | 71 / 51 → 43 px |
| CHEFFIN slide 4 (7) | 4 + 3 grid with an accent rule, ROAS toned red, Allowable CPC tinted, no icons | 28 → 58 px, words too wide 6 → 0 |

Four slides, four layouts: the LLM varies the composition with the content, without rules. Not seen: a hero tier,
rows beside a chart, a strip. Weak: CHEFFIN 4's last row of 3 does not fill the width; CHEFFIN 1 tiles 5
`GEOM_CARD_EMPTY` (tall tiles, one row); QBR's ARR value in `$accent` on the dark panel + green delta read low
(`LOW_CONTRAST` 2). KPI slides first try 3 / 4: all-nodes put the refs and an `Icon` inside a `<Text>`
(`INVALID_CHILD`, repaired).

Deck level (vs q1008, the same 4 cases): cost $1.13 vs $1.11; first pass 22 / 25 vs 25 / 25; word breaks 12 vs 8
(9 of the 12 on all-nodes slide 3, a non-KPI slide). **Not from the refs:** the CHEFFIN cover did not compile —
the LLM typed literal colours with an alpha channel (`7B3FE41A`, 8 digits), POM rejects them, the slide was not
retried and the deck shows "Slide could not be generated" (also a ZIP-level merge, so `pptx_merge`'s media-name
bug can show wrong icons in that deck). Normalizer fix proposed separately.

## 11. Decision: refs on by default, square KPI tiles, alpha colours (user, 2026-10-11)

- **`POM_BLOCKS` defaults to `kpi`** (`element_refs.mode()`): every `kpi_row` goes through element refs.
  `POM_BLOCKS=off` gives the old route; any other value reads as `kpi`.
- **KPI tiles have square corners** (user: so the KPI tiles read apart from the slide's other cards): `fill_refs`
  drops `borderRadius` from each value's tile (the nearest stack with a fill or border). Callouts, chart and table
  cards keep theirs. `docs/eval/kpi-node/decks/kpi-slides-square.png`: the 4 KPI slides of §10, recompiled
  (right column = refs, square tiles).
- **8-digit literal colours** (the §10 CHEFFIN cover): normalizer `ALPHA_COLOR_BLENDED` blends `RRGGBBAA` on a
  `*color` / `fill` attribute onto white (`7B3FE41A` → `F2EBFC`). The saved cover now compiles (it failed before).
- Unit tests 916 pass + the 4 known failures.

## 12. Fixes from the full decks, checked on the saved slides (2026-10-12)

The 4 KPI slides of §10 turned back into refs (`map_refs`, the LLM's own attributes kept), filled and compiled
on the new code: `docs/eval/kpi-node/decks/kpi-slides-fixes.png` (right column).

| Fix | Where | Before → after on the saved slides |
|---|---|---|
| 1. A KPI text on a dark tile (`$panelDark` / `$textMain` / `$accent`) whose colour does not read there gets the fill's on-colour (`READS_ON`, `NODE_ATTR_IGNORED`) | `element_refs.fill_refs` | QBR `LOW_CONTRAST` 2 → 0 (ARR + its delta white on the dark tile) |
| 2. A row of content-sized tiles (`w="max"`) spans its width: each tile `grow="1"` (content width + an even share), an empty spacer stack goes; widths the LLM set stay. fit-grow counts `grow` on a tile in a row as width, not height (the row still grows its numbers) | `element_refs._fill_rows`, fit-grow `growStats` | CHEFFIN 4's row of 3 reaches the right edge; numbers 58 px unchanged |
| 3. A ref tile still sparse after growth (fit-grow's `LOW_FILL`) with an icon beside its label: icon above the label, the label stretched to the tile | fit-grow `stackTileIcons` | CHEFFIN 1 `GEOM_CARD_EMPTY` 5 → 0; labels wrap between words in the narrowest tiles, 0 broken words |
| 4. The LLM's XML before the fill is kept: `generated.xml` per try (validator), `first-generated.xml` in eval bundles (`eval_run`), `first.xml` + `first_diagnostics` in `kpi_paid` | validator, `scripts/eval_run.py`, `scripts/kpi_paid.py` | `kpi_paid --dry` writes `first.xml` |

Number sizes on the 4 slides unchanged (55 / 47 / 43 / 58 px); a first try at equal tile widths (`w="1"`)
squeezed the widest number (47 → 28 px on all-nodes) and was dropped. Not covered: icons, other
colour-on-fill pairs outside KPI tiles. A paid check is not needed for these (code-only, the LLM's input is
unchanged); one full-deck run before the merge covers them.

## 13. Full decks, run 2 (test PC, 2026-10-12, commit a883687, $1.18)

Same 4 cases as §10, refs on by default. `docs/eval/kpi-node/decks-2/`: `kpi-slides-3-runs.png` (today's route,
refs run 1, refs run 2; PowerPoint renders from the test PC), `blind.png` + `marks.csv` (today vs run 2, sides
shuffled; `key.json` holds the answer).

| | run 1 (§10) | run 2 |
|---|---|---|
| first pass (deck) | 22 / 25 | 22 / 25 |
| KPI slides first try | 3 / 4 | 2 / 4 |
| word breaks (4 decks) | 12 | 5 |
| low contrast on KPI slides | QBR 2 | all-nodes 2 (after repair) |
| cost | $1.13 | $1.18 |

- **Both KPI repairs: the LLM wrapped each ref in a styled Text** (`<Text fontSize color><Text ref="…"/></Text>`,
  `INVALID_CHILD`; run 1's one repair was the same). The repairer then flattened the *filled* slide: CHEFFIN 1
  drew every label twice, all-nodes kept `$accentText` / `$positiveText` on its dark hero panel (no refs left, so
  §12 fix 1 never ran). **Fixed:** `element_refs._unwrap_refs` puts the ref Text in the wrapper's place with the
  attributes it lacks (`NODE_ATTR_IGNORED`). Re-filled from the saved `first-generated.xml` (§12 fix 4): both
  compile first time, no doubled labels, `LOW_CONTRAST` 0, all-nodes 53 px + a 120 px hero.
  The blind sheet uses these two re-fills (LibreOffice renders; the rest are PowerPoint renders).
- The 3rd repair (all-nodes slide 4) is a `connectorGradient` parse error on a Timeline, not KPI.
- **CHEFFIN 4: the LLM put all 7 tiles in one row** (run 1: 4 + 3): numbers 37 px, bound by the tile width,
  `GEOM_CARD_EMPTY` 7. CHEFFIN 1: 5 tiles without icons, 37 px, `GEOM_CARD_EMPTY` 5, labels stay 14 px. Not
  fixed: a layout choice (user: no rules); open whether the prompt line should state the row width per tile.

**Blind marks (user, 2026-10-12): B (refs run 2) 3 wins, A (today) 1, 0 ties → 0.75** (replay 0.643, paid check
0.556). Note: the seeded shuffle put B on the left in all 4 pairs.

| pair | case | winner | user's note |
|---|---|---|---|
| P1 | QBR exec summary | B | better space allocation and font size |
| P2 | all-nodes | B | colour visibility in the repeat-revenue panel (the re-fill with `_unwrap_refs`) |
| P3 | CHEFFIN 1 | A | five cards better shown (today: 3 big tiles + a row of 2) |
| P4 | CHEFFIN 4 | B | font size; both would be better as 4 cards above, 3 below |

The one loss and the P4 note point the same way: 5-7 tiles in one narrow row (37 px numbers, empty tiles) lose to
fewer, wider tiles per row.

## 14. Variety from the plan: a slide's numbers in several kpi_rows (user, 2026-10-12)

User: let the LLM decide; a slide may carry several KPI components so it is not one node drawn once. Where P3's
winner came from: q1008's planner split CHEFFIN 1 into `combined_kpi_scorecard` (hero, 3) + `platform_roas_tiles`
(peer, 2, "group as a callout panel"); both refs runs planned one row of 5 (and one of 7 on slide 4). In the 3
runs the planner split 3 times (that slide, and all-nodes' 4 + a hero of 1 twice); every split slide drew well, the
marked losses were long single rows.

**Changed (prompt only):** `src/prompts/slide_component_planner/system.j2` — the component table says "count =
tiles in this group … a slide's numbers may be several kpi_rows, one per role" (was "more metrics → a second
kpi_row"), and the kpi_row description gains *Grouping a slide's numbers*: totals vs a breakdown, inputs vs the
result, the headline's number vs context, a target vs its actual → one kpi_row each with its own weight and
design_hint; peers stay one row; by meaning, never by count; each number in one group. Nothing downstream changes:
refs, number sizes per component and the weight cap already handle several kpi_rows (§9). C17
(`drop_duplicate_items`) needs ≥ 3 shared labels, so a split never trips it. Test:
`test_planner_prompt_lets_a_slide_group_its_numbers_into_several_kpi_rows`. Not yet run with the LLM (paid).

**Planner-only check (test PC, 2026-10-12, `python -m scripts.kpi_plan_only --repeat 3`, $0.619, 9 runs;
`docs/eval/kpi-node/plans/summary.md`).** 12 KPI slides, 5 split into several kpi_rows; 0 numbers in two
groups; 1 key-message number not carried.

| slide | split, this check | split, the 3 runs before (q1008, decks 1, decks 2) | groups |
|---|---|---|---|
| QBR exec summary (4 peers) | 0 / 3 | 0 / 3 | one row of 4 each time (peers stay one row, as asked) |
| CHEFFIN 1 (5) | 2 / 3 | 1 / 3 | combined spend / revenue / ROAS (hero) + the 2 platform ROAS (peer), both times |
| CHEFFIN 4 (7) | 1 / 3 | 0 / 3 | Spend, Ad sales, ROAS, Allowable CPC (hero) + CPC, CVR, AOV (supporting) |
| all-nodes (5) | 2 / 3 | 2 / 3 | the 62% repeat-revenue hero + a row of 4; the third run: one row with 62% in focus |

Found: CHEFFIN 4's split puts the target (Allowable CPC) in a different group from the actual it is compared
with (CPC) and moves it ahead of CPC — against the brief's order and the slide's point (CPC almost 3× the
allowable); the prompt's "a target vs the actual" example may read as "split them". r1 shortened the label
"Allowable CPC for 1.0x ROAS" to "Allowable CPC" (the only not-carried number, 1.0x). Cost per planning run
$0.05-0.09 (above the $0.30-0.50 estimate for 9).

**Prompt fix after the check (user, 2026-10-12): the planner conserves the data, the composition is its own
choice.** `slide_component_planner/system.j2`: Job 1 now says labels are content, copied word for word, never
shortened, and every number and label of the slide sits in exactly one component; Job 2 says which items go
together, whether a group stays whole or splits, which kind carries it and what is hero is the planner's choice,
there is no single right arrangement and variety between slides and runs is welcome. The grouping paragraph
gives the groupings as examples, not rules, and says numbers compared directly (an actual and its target or
benchmark) stay in one group, side by side; within a group the brief's order. Not yet run with the LLM.
