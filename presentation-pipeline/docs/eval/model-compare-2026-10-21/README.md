# Model comparison: gpt-6.1-sol vs gpt-5-mini vs gpt-4.1 generator (2026-10-21, free review)

Same prompts (CHEFFIN and XTSY), no prompt change. Runs from the test PC (UI runs, zip
`gpt 5mini vs 6.1sol.zip`) and the gpt-4.1-generator runs of 2026-10-20 from Downloads. Rendered here with
LibreOffice (Inter installed, all decks drew Inter), scored with the project's own metrics
(`scripts.eval_metrics`, `src.compiler.geometry_audit`). No API calls.

| run | brief (request hash) | commit | models | theme | cost | retries |
|---|---|---|---|---|---|---|
| `cca9534ca34c` | CHEFFIN (`b796dd3b9e`) | `3729c60` | **gpt-6.1-sol** on every step | saascolor | $0.337 | 0 |
| `f64d81a71c5b` | CHEFFIN (`b796dd3b9e`) | `3729c60` | **gpt-5-mini** on every step | corporate-slate | $0.113 | 0 |
| `225dc465d0f4` | CHEFFIN (`b796dd3b9e`) | `39cf10a` | planners gpt-5-mini, **generator gpt-4.1** | corporate-slate | $0.183 | 0 |
| `8c45b663157b` | CHEFFIN (`b796dd3b9e`) | `39cf10a` | same as above | claude-cream | $0.180 | 0 |
| `32581ffab76d` | XTSY (`4f964e78da`) | `3729c60` | **gpt-6.1-sol** on every step | saascolor | $0.388 | 0 (2 repairs) |
| `fba41886e4fe` | XTSY (`c3cccbc162`, a different request) | `3729c60` | **gpt-5-mini** on every step | violet-modern | $0.175 | 0 (2 repairs) |
| `6066f16beedd` | XTSY (`4f964e78da`) | `39cf10a` | planners gpt-5-mini, **generator gpt-4.1** | corporate-slate | $0.270 | 0 (1 repair) |
| `88bc69445841` | CHEFFIN, anonymised second half (`9b36a05cd3`) | `3729c60` | gpt-6.1-sol | navy-orange | $0.352 | 0 |

Sheets (one column per run, one row per slide): `cheffin.png`, `xtsy.png`, `cheffin-b.png` (the anonymised brief
on 6.1-sol beside the claude-cream 4.1 run; not the same content).

**Not a clean A/B.** (1) Themes differ per run, so colour differences are the theme, not the model. (2) The
gpt-4.1 runs are on `39cf10a` (2026-10-20, before the diagram word-fit and KPI label commits). (3) "All 6.1-sol"
and "all 5-mini" change the planners and the generator together; the 4.1 runs keep gpt-5-mini planners. (4) One
run per arm. (5) The 5-mini XTSY run has a different request hash.

## Measured (whole decks)

| run | card fill (mean) | cards < 0.7 fill | `GEOM_CARD_EMPTY` | other geometry | word breaks | font size median | text ≤ 14 px |
|---|---|---|---|---|---|---|---|
| CHEFFIN 6.1-sol | 0.82 | 5 / 26 (19%) | 4 | – | 3 | 18 | **6%** |
| CHEFFIN 5-mini | **0.63** | 12 / 23 (**52%**) | **10** | collision 2, spill 1 | 1 | 14 | **57%** |
| CHEFFIN 4.1 gen | 0.86 | 5 / 26 (19%) | 3 | spill 1, off-slide 1 (cover word) | 2 | 22 | 32% |
| CHEFFIN 4.1 gen (cream) | 0.87 | 3 / 23 (13%) | 1 | spill 1, off-slide 1 (cover word) | 1 | 16 | 48% |
| XTSY 6.1-sol | 0.81 | 6 / 32 (19%) | 7 | – | **0** | 20 | **16%** |
| XTSY 5-mini | 0.80 | 7 / 46 (15%) | 5 | spill 1, collision 1 | 1 | 16 | 47% |
| XTSY 4.1 gen | 0.80 | 10 / 40 (25%) | **11** | empty box 1 | 3 | 18 | 29% |

Font sizes are every `fontSize` in the deck's fitted XML (not weighted by text length).

Cost by step (manifests): generator 6.1-sol $0.20–0.22 per deck vs gpt-4.1 $0.13–0.16 vs 5-mini $0.06–0.08;
slide planner 6.1-sol $0.12–0.13 vs 5-mini $0.04–0.09. 6.1-sol used 3.4–4.2k reasoning tokens per deck, 5-mini
37–59k. Whole deck: 6.1-sol ≈ 1.4–1.8× the gpt-4.1-generator runs, ≈ 2–3× all-5-mini.

## Per slide (my read of the renders; your blind marks would decide)

**CHEFFIN** (6.1-sol / 5-mini / 4.1):

| slide | best | why |
|---|---|---|
| 0 cover | 6.1-sol | 5-mini and 4.1 put "CHEFFIN" in the accent block at a size that runs off it ("HEFFIN", "CHEFF"; geometry `GEOM_OFF_SLIDE` on 4.1); 6.1-sol chose a word that fits |
| 1 summary | tie | all three: three totals + platform ROAS; 6.1-sol colours only the problem number, the others tint four tiles red |
| 2 CPC gap | tie | chart + gap callouts (6.1-sol), chart (5-mini), table with gap column (4.1) |
| 3 data reviewed | **6.1-sol** | five source cards + metric definitions + notes, full slide; 5-mini two large near-empty cards, 4.1 an empty "quality notes" card |
| 4 FLIPCART snapshot | **4.1** | 4 + 3 KPI grid at large numbers; 6.1-sol a plain 7-row metric table; 5-mini 7 narrow, mostly empty tiles |
| 5 ad type / match type | **6.1-sol** | two readable tables + a takeaway in body size; 5-mini and 4.1 small table text with empty space |

**XTSY** (6.1-sol / 5-mini, other request / 4.1):

| slide | best | why |
|---|---|---|
| 0 cover | 6.1-sol | clean platforms → engine diagram; 4.1 drew no diagram (two text cards) |
| 1 occasions | 6.1-sol / 5-mini | six cards with readable titles; 4.1 smaller type |
| 2 opportunities | 6.1-sol / 4.1 | 5-mini drew a matrix of icons only (cells without content) |
| 3 4-phase | tie | 5-mini leaves a large empty band |
| 4 platform | 6.1-sol | lists at body size; the others small |
| 5 automation | 6.1-sol | 5-mini flow boxes are empty; 4.1's flow is tiny with a broken word ("Optimizatio / n") |
| 6 impact | 6.1-sol / 4.1 | large titles with ↑; 5-mini small cards under a flow |
| 7 roadmap | tie | 4.1's dark focus month is a nice touch; 6.1-sol a larger closing line |

Tally (my read): **6.1-sol best or tied on 13 of 14 slides, 4.1 on 7, 5-mini on 5.** 5-mini as the generator
is the weakest: small type (57% / 47% of sizes ≤ 14 px), empty tiles and cards, content-less diagrams.

## Where the difference comes from

The plans have nearly the same components on every slide across models (e.g. CHEFFIN:
`kpi+text` for the snapshot slide in all three; XTSY: cards + one process / flow per slide). So the visible
gap is mostly **the generator**: how it divides the slide, how large it sets type, whether it fills boxes and
whether diagrams carry their items. That matches the project's earlier finding that the LLM's layout decides most
of the perceived quality (1a: LLM route 18 vs code blocks 7). One 6.1-sol choice is worth noting: on CHEFFIN 4
it drew the planned `kpi_row` as a metric table (flat), where gpt-4.1 drew the 4 + 3 grid the user preferred
before.

Weak spots of 6.1-sol seen here: 3 word breaks on CHEFFIN (`cca9534`), and on the anonymised brief (`88bc69`)
slide 2's "Winners / Weak terms" lists drawn in very narrow columns (words broken letter by letter).

## Next (proposed, ask before any paid run)

1. **Your blind marks** on these sheets (free): the tally above is one reviewer's read.
2. **Separate planner from generator** (paid, ≈ $0.45 for the two decks): gpt-6.1-sol as the generator only, on
   the saved gpt-5-mini plans of `225dc465d0f4` / `6066f16beedd` (same plans as the 4.1 runs, generator-only, like
   `scripts/tile_same_plan.py`). If 6.1-sol on 5-mini plans looks as good, keep the planners cheap and pay only
   for the generator (≈ $0.20 of the $0.34–0.39 per deck).
3. Same theme and commit for every arm next time (set the theme in the run, run all arms on one commit), and two
   repeats, so colour and code changes do not mix into the model comparison.

## Blind marks (user, 2026-10-21; `blind/marks.csv`, `blind/key.json`)

Sheets `blind/*.png`: every slide of the three arms recompiled on `3729c60` in one theme (corporate-slate, deck
font Inter), arms shuffled per slide (seed 20261021). Scoring per slide: best 2, middle 1, worst 0; arms named
together share the places; "all good" = 1 each; XTSY 3 ("none", the user wanted a table) = 1 each.

| slide | user's order (unblinded) | user's reason |
|---|---|---|
| CHEFFIN 1 cover | **6.1-sol** > 4.1 > 5-mini | 5-mini's "CHEFFIN" out of bounds |
| CHEFFIN 2 summary | all equal | all good; fonts could grow into the space |
| CHEFFIN 3 CPC gap | **6.1-sol** > 5-mini > 4.1 | the FLIPCART vs ZAROMA gap shown best |
| CHEFFIN 4 data reviewed | **5-mini** > 6.1-sol > 4.1 | space allocation; both could grow their type |
| CHEFFIN 5 snapshot | **4.1** > 6.1-sol > 5-mini | both define the context well |
| CHEFFIN 6 ad / match type | **6.1-sol** > 5-mini > 4.1 | spacing between component and table |
| XTSY 1 cover | **6.1-sol** > 5-mini > 4.1 | design and space |
| XTSY 2 occasions | **6.1-sol** > 5-mini > 4.1 | spacing, text aligned in the cards |
| XTSY 3 opportunities | none good | should be a Zepto vs Blinkit vs Instamart table of differences |
| XTSY 4 4-phase | **4.1** > 6.1-sol > 5-mini | asks why 6.1-sol's third card is larger (below) |
| XTSY 5 platform | **6.1-sol = 5-mini** > 4.1 | better points; why so much control-tower dashboard |
| XTSY 6 automation | **6.1-sol** > 5-mini = 4.1 | spacing; asks if the vertical flow is the LLM's choice |
| XTSY 7 impact | **4.1 = 6.1-sol** > 5-mini | space filled |
| XTSY 8 roadmap | all equal | all good; size could fill better |

| | gpt-6.1-sol | gpt-4.1 generator | gpt-5-mini |
|---|---|---|---|
| points (of 28) | **21** | 10 | 11 |
| score (points / 28) | **0.75** | 0.36 | 0.39 |
| best outright / shared | 6 / 2 | 2 / 1 | 1 / 1 |
| worst | **0** | 7 | 5 |

**Verdict: gpt-6.1-sol wins clearly and was never the worst on any slide.** gpt-4.1 and gpt-5-mini come out
about equal once the theme is the same (my earlier read had 5-mini last; the themes had flattered 4.1).

**The user's questions:**
- *XTSY 4, why is 6.1-sol's third card larger?* Not code, not intended: the LLM wrote the four phase cards
  `w="264"` with no height in a row with `alignItems="start"`, so each card is as tall as its text and Phase 3 has
  the longest bullets. The plan's hint asked for "equal visual treatment across all four". A general fix (peer
  cards in one row share one height: `alignItems="stretch"` on a row of same-styled cards) would follow rule K6
  "peers look alike"; not built, needs your OK.
- *XTSY 6, is the vertical flow the LLM's choice?* Yes: the gpt-6.1-sol **planner** wrote `direction: vertical`
  (the diagram-direction prompt of 2026-10-16 / 10-20: vertical when the flow shares the width) and the generator
  kept it. Code did not change it.
- *XTSY 3, a table of differences per platform:* the brief names the platforms and the levers but gives no
  platform-specific content per lever (the plan hint says so), so a filled table would be invented content. A
  table needs the brief to give those cells; the planner could draw an empty-celled matrix only.
- *"Fonts could grow into the space"* (CHEFFIN 2, 4, XTSY 8): fit-grow's growth limits on stretched cards; the
  open empty-space item of the look-and-feel review (step 5).

### Why only 6.1-sol's XTSY 4 had a larger third card (traced 2026-10-21)

The 6.1-sol **generator wrote it right**: the first try had the row `alignItems="stretch"` and four `w="max"`
cards (equal heights). That XML **did not compile**: `addTextBox: width must be a finite positive EMU value`
(it still fails on today's code). Cause: the "→" between the cards is a `<Text>` with no width. POM gives each
`w="max"` card flex-grow with its text's one-line width as the basis and the arrow a basis of 0, so the four cards
take all the room and the arrows are squeezed to zero width: the known `w="max"` squeeze. The
**repairer** (also 6.1-sol) then pinned the cards to `w="264"`, set the arrows to `w="20"` and switched the row and
root to `alignItems="start"`. That compiles, but every card is now as tall as its own text, so Phase 3 (longest
bullets) stands out.

The other arms avoided the crash by how they drew the arrows: gpt-4.1 used `<Icon name="arrow-right" size="20">`
(fixed size), gpt-5-mini a "→" Text in a row whose cards' text fit. So it is chance in the layout, not a 6.1-sol
habit; any model can hit it. `TEXT_BOX_UNSQUEEZED` (2026-10-14) only handles a long text box beside tile / card ids.

General fixes (not built, need your OK; free replay on all saved slides first, as with the squeeze fix):
1. normalizer: in an HStack with `w="max"` children, a sibling Text without `w` / `grow` and with ≤ 3 characters
   (arrows, "+", "·") gets a width from its font size, so it can never be squeezed to 0;
2. repairer: for this error, fix widths only and keep the row's `alignItems` (do not trade a crash for unequal
   peers);
3. (from the user's question) a row of same-styled peer cards stretches to one height (K6).

### The three fixes, built and replayed (2026-10-21, free)

| fix | where | code |
|---|---|---|
| 1. a short symbol Text (≤ 3 characters, no `w` / `grow`) in a row with a `w="max"` child gets `w` = 1.2 × its font size; wrapping rows (`flexWrap="wrap"`) are left alone | `grow_fallback.size_row_symbols`, normalizer | `ROW_SYMBOL_SIZED` |
| 2. a "width must be a finite positive EMU value" error gets repair guidance: give the squeezed node a width, change widths only, keep every `alignItems` / `justifyContent` / `grow` / `h` | `repair_guidance.SQUEEZE_GUIDANCE` | (prompt text) |
| 3. a row whose boxed children (≥ 2, same structure: attribute names + padding / borderRadius; fills may differ) set no height, with `alignItems` start / center / end, gets `alignItems="stretch"`; its other children keep their place with `alignSelf` | `grow_fallback.stretch_peer_cards`, normalizer | `PEER_CARDS_STRETCHED` |

**Replay** on every distinct saved slide (640: `output/`, `llm_test/`, and these runs), normalized with the fixes off
and on, compiled and geometry-checked: the fixes change **3 slides**, all from this comparison's 6.1-sol XTSY deck;
renders `fixes-before-after.png`.

| slide | before | after |
|---|---|---|
| XTSY 4, 6.1-sol first try | did not compile (`width must be a finite positive EMU value`) | compiles first time; four cards one height (no repair call needed) |
| XTSY 4, 6.1-sol after the repair | Phase 3 card taller than the others | four cards one height |
| XTSY 8, 6.1-sol | arrows between the month cards | arrows given a width; no visible change |

Geometry findings unchanged on all three (none before, none after). A first version gave arrows 1.5 × the font size
and also touched wrapping rows: on gpt-5-mini's XTSY 4 (`flexWrap="wrap"`) the wider arrows pushed Phase 4 onto a
second row; wrapping rows are now skipped and the width is 1.2 ×.

How often each case occurs in the 640 saved slides: rows of ≥ 2 boxed cards 762, of which 760 already stretch (the
default) and 2 are the 6.1-sol repair above. Unequal peer heights from `alignItems` are rare; the fix is a safety
net for repairs. Fix 2 changes only the repairer prompt; its effect shows on the next run that hits the error.

Unit tests: 1208 pass + the 4 known failures (`tests/unit/test_row_symbols_peer_cards.py`, 9 new).
