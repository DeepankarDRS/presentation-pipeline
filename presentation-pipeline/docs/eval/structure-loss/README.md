# Where does the brief's structure get lost? (2026-10-15, free)

Question: when a slide plan holds a `bullet_list` of numbers or "Label: detail" items, did the
**outline planner** flatten the brief's structure into sentences (`key_messages`), or did the
**slide component planner** get the structure and still choose a list? This decides whether a
structured per-slide outline JSON (content blocks by data form) is the right lever.

**Answer: the outline is not where structure is lost.** Structured brief lines reach the
component planner as structured `key_messages` (~97%; no confirmed case of flattening). Since
the 2026-09-29 planner prompt, the component planner routes numeric structure correctly
(1 of 243 numeric messages went to a list by LLM choice). The structured lists still seen in
recent runs come from the planner's own rules and from brief instructions copied as content. A
structured outline would not change them.

Reproduce: `python -m scripts.structure_loss` (add `--examples 5`, `--json out.json`). No LLM, no
compiler. It reads the gitignored `output/`, so it runs only on the build PC.

## Method

1. **Corpus A: every saved slide plan.** All `output/**/slides.json`, deduplicated by the plan's
   components. That gives 470 distinct plans from 51 run folders, 2026-09-23 → 2026-10-13. Test 1's
   new planning path (`output/plans/test-1*`, storyline + slide designer, 2026-09-27) is counted
   separately because it is not the outline planner. Main path: 99 plans with a `bullet_list`,
   118 lists. Run dates come from the manifest's `git_commit` (commit date), else from the folder
   name / run id, else from the `llm_test/` zip date (`_FOLDER_DATES`).
2. **Corpus B: plan-only runs that kept the outline.** `output/card-plans/card-plans/runs.json`
   (18 runs) and `output/kpi-plans/{import-1012,p3}/runs.json` (11 runs). They hold the brief → outline →
   plan chain for 6 cases (`deck-qbr-data`, `deck-product-launch-data`, `gate-deck-agency-takeover`,
   `gate-deck-all-nodes-dense`, `gate-deck-cheffin-full`, `gate-deck-xtsy-qcomm`), run
   2026-10-12/13 on planners at `cd5b5e9`-era prompts (gpt-5-mini). **No other saved run keeps
   the outline**: `slides.json` and `run-manifest.json` have no `key_messages`, and the
   Test 1 zips keep a storyline, not an outline. So gj-h1 (the source of the September number lists)
   can only be traced brief → plan.
3. **Item shapes** (`item_shape`), used for bullet items, brief lines and key_messages alike:
   `series` (≥ 3 "name value" parts), `record` ("Label: measure value, measure value", or a
   `a | b | c` table row), `metric` ("Label: value"), `categorized` ("Label: a, b, c"),
   `label_detail` ("Label: a line"), `named` (a ≤ 5-word name, no number), `note` (Note / Source /
   formula), `claim` (a sentence citing figures), `prose`. A list takes the majority shape:
   **numeric** (series/record/metric), **label_detail** (incl. categorized), **named_items**,
   **claim**, **note**, **takeaway**.
4. **Brief source:** each bullet item is matched to the closest line of the case brief
   (`tests/cases/<case>.yaml`, request split into lines, plus supplied_content). Matching is by
   token overlap, with numbers counted double. The matched line gets the same shape label.
5. **Class** of each list:
   - **b**: the component planner had the structure. Either the items still carry it (Job 1 copies
     key_messages verbatim, so structured items mean structured input), or, in corpus B, the
     key_message they came from is structured. It still drew a list.
   - **a**: the brief line is structured, but the key_message is a sentence (outline flattened).
     **a?**: same, but no outline was saved (outline or planner).
   - **c**: the brief itself wrote sentences (read-outs, notes).
   - **ok**: plain takeaways from plain sentences.
   - **fallback**: the planner failed twice and code drew the outline's lines as one list
     (`fallback_plan`, component id `fallback_points`).
6. **Stage by stage on corpus B** (all key_messages, not only lists):
   (i) every structured brief line (series / record / metric / categorized) → its best-matching
   key_message: kept structured, flattened, or not matched;
   (ii) every key_message → the component whose `content_data` carries it → that kind.

The parent's figure ("~94 of 183 lists are mostly numbers") counts lists whose items mostly
*contain a digit*. Here that is 96 lists. 42 of them are read-out **sentences** the brief itself
wrote (class c), 50 are Test 1 path and 77 are gj-h1. Only **12** hold numbers *as data*
(series / record / metric items): 4 main path, all 2026-09-24, and 8 Test 1.

## Counts

### Corpus A, main path: 118 bullet lists

| list shape | a? | b | c | ok | total |
|---|---|---|---|---|---|
| numeric (series / record / metric) | 0 | **4** | 0 | 0 | 4 |
| label_detail (incl. "Label: a, b, c") | 0 | **34** | 0 | 0 | 34 |
| named_items (short names) | 0 | **32** | 0 | 0 | 32 |
| claim (sentences citing figures) | 4 | 0 | 21 | 0 | 25 |
| note (notes, formulas) | 0 | 0 | 7 | 0 | 7 |
| takeaway | 0 | 0 | 0 | 16 | 16 |

By date:

| runs | lists | numeric (b) | label_detail (b) | named_items (b) | claim | note | takeaway |
|---|---|---|---|---|---|---|---|
| before 2026-10-08 (Sep 23 → Oct 6) | 68 | 4 | 20 | 14 | 20 (4 a?) | 2 | 8 |
| **2026-10-08 onward** | **50** | **0** | 14 | 18 | 5 | 5 | 8 |
| Test 1 path, 2026-09-27 (separate) | 70 | 8 | 12 | 5 | 24 (3 a?) | 2 | 19 |

All 4 main-path numeric lists come from gj-h1 runs on 2026-09-24. That is before the
2026-09-29 planner prompt (`1b4aa9e` Examples 1–3: one entity's metrics → kpi_row, one measure
× entities → sorted chart, entities × measures → table; `3a5b588`: card_grid). No main-path run
since then has a numeric bullet list.

The 4 **a?** lists, checked by hand: none is flattening. They are read-outs the brief writes as
"Label: sentence" ("Curd is the star: 8.0x ROAS & only 12.5% ACOS"), reworded into sentences.
They belong in c.

### Corpus B: stage by stage (29 plan-only runs, 6 cases, 2026-10-12/13)

**(i) Brief → outline.** Structured brief lines and the key_message that carries them:

| brief line shape | kept structured | "flattened" | not matched |
|---|---|---|---|
| series | 24 | 0 | 6 |
| record | 66 | 3 | 0 |
| metric | 62 | 3 | 19 |
| categorized | 75 | 3 | 13 |

Every "not matched" line, checked by hand, is not data. They are headings ("SLIDE 6: Pillars
and 90-Day Plan", "TITLE: …", "Visual: 4-stage growth roadmap") or format instructions ("Use
Indian currency format: ₹, L for lakhs"). The 9 "flattened" are not flattening either:

- two of the brief's own records joined in one message ("Gap 1 - CPC above allowable level:
  [Platform B] CPC ₹31.1 vs allowable ₹10.7. [Platform A] CPC ₹46.2 vs allowable ₹14.8 …",
  agency r1, as the brief writes it);
- a table row with one pipe ("Allowable CPC for 1.0x ROAS | ₹10.7", CHEFFIN r1);
- architecture layers packed into one multi-line message that keeps every "Label: a, b" line
  (all-nodes-dense, import-1012 r1);
- a heading matched to the wrong line.

The outline also *adds* structure: the brief's `SD | 2.4% | 1.1% | 0.17x | Weak conversion quality`
becomes `SD: Spend Share 2.4%, Sales Share 1.1%, ROAS 0.17x, …` (kpi-plans p3), and the qbr
segment lines become `Enterprise: ARR $28.1M, QoQ Growth +22%, Customers 142 | Mid-Market: …`.
**Confirmed (a): 0.**

**(ii) Outline → component.** Each key_message and the kind that carries it:

| key_message shape | n | carried by |
|---|---|---|
| metric | 156 | kpi_row 126, table 12, **bullet_list 8**, timeline 6, not carried 3, card_grid 1 |
| record | 54 | table 40, **bullet_list 4**, chart 3, timeline 3, kpi_row 2, narrative 1, matrix 1 |
| series | 33 | chart 16, table 12, timeline 3, **bullet_list 1**, not carried 1 |
| categorized | 71 | card_grid 45, **bullet_list 14**, tree 4, timeline 3, pyramid 2, matrix 2, kpi_row 1 |
| label_detail | 163 | card_grid 42, narrative 37, **bullet_list 29**, not carried 15, table 12, kpi_row 8, … |
| named | 27 | **bullet_list 11**, caption 7, narrative 4, card_grid 3, … |
| note | 23 | **bullet_list 15**, narrative 5, caption 3 |
| claim | 86 | card_grid 25, table 18, bullet_list 13, kpi_row 9, narrative 8, caption 6, … |

The 13 numeric → bullet_list cases (metric 8, record 4, series 1) come from **one** slide,
CHEFFIN slide 5, in two runs. Two of the 8 "metric" ones are "Data reviewed: FLIPCART Targeting
last 90 days report", a named item the classifier misread as a metric.

- kpi-plans `p3` r1: a 12-item list of the ad-type table rows and the match-type ROAS metrics.
  This is the code's **fallback** (`fallback_points`, the planner failed twice), not an LLM
  choice.
- card-plans r3: an LLM choice (example b3 below).

The same outline form for that slide was drawn as two tables in the other 5 LLM plans. So, for
numbers: **1 LLM list of 243 numeric messages**.

Bullet lists in corpus B: 46. b 29 (numeric 1, label_detail 9, named_items 14, takeaway-from-label 5),
c 8, ok 8, fallback 1.

## Examples

Paths are under `output/` (gitignored, build PC). Corpus B paths are `runs.json#run_id`. All the
content quoted is in the tracked case briefs.

### (b) The component planner had the structure and drew a list

1. **Series → list, brief said "Chart (bar)".**
   `output/r2/inputs/gj-h1-regen-7293ef/slides.json`, slide 4 (2026-09-24). Items: "Milk 500ml:
   12.4", "Curd 400g: 9.8", "Paneer 200g: 7.2", "Milk 1L: 5.6", "Curd 200g: 4.3". The brief line
   is `Chart (bar): Ad Sales (L): Milk 500ml 12.4, Curd 400g 9.8, …`. Same run, slide 1: three
   monthly series ("Blinkit Jan–Jun sales (₹ Cr): 1.23, 1.11, …") and three per-platform records
   ("Blinkit: H1 GMV ₹8.37 Cr, Ad Spend ₹41.9 L, …") as two bullet lists. Both predate the
   2026-09-29 routing examples.
2. **Records → list.** `output/r2/inputs/gj-h1-regen-bf396b/slides.json`, slide 7 (2026-09-24):
   "Defend: Blinkit Milk + Curd (6.9–8.0x ROAS); retain top-2 scroll …", "Expand: Swiggy Paneer
   (9.94x ROI, 35.8% ad %); …", "Tighten: …". These are named items with figures and actions:
   card material.
3. **Series key_message → list (recent, LLM).**
   `output/card-plans/card-plans/runs.json#cardplan-gate-deck-cheffin-full-r3-1791907634`,
   slide 5 (2026-10-13). The key_message is "Match / targeting performance: Exact ROAS: 0.44x,
   Phrase ROAS: 0.26x, Auto ROAS: 0.30x, Category ROAS: 0.25x, Broad ROAS: 0.22x, Audience ROAS:
   0.15x". It became a 6-item list beside the ad-type table. In all 5 other LLM plans of this
   slide, the same form gave a second table.
4. **Categorized lists → list, as the prompt says.**
   `…#cardplan-gate-deck-agency-takeover-r1-1791906414` and `…-r3-1791906725`, slide 1, and
   `output/q1008/quality-1008-20261008-210801/decks/gate-deck-agency-takeover__r1/slides.json`,
   slide 1. "Winners: [Brand] phrase, [Brand] exact, paneer makhani, …", "Weak terms: butter chicken
   phrase, …". The outline kept them verbatim. The planner prompt routes exactly this to a list
   (routing row "Categorized list → bullet_list", Example 4).
5. **Named items beside another component.**
   `output/q1008/…/gate-deck-xtsy-qcomm__r1/slides.json`, slide 2 (2026-10-08). Also in
   kpi-decks, kpi-decks-2 and card-plans xtsy r1/r3. "Opportunity Areas: Search visibility
   expansion; Sponsored placements; …" becomes a 7-item list next to the levers × platforms
   `card_grid`. Slide 5 does the same: "Show Benefits: Faster optimization cycles; …" becomes a
   5-item list next to a `flow`.

### (a) The outline flattened the brief's structure

None confirmed (see the table under (i)). The closest cases keep the structure but pack two data
groups into one message:

1. `…#cardplan-gate-deck-agency-takeover-r1-1791906414`, slide 2: two platforms' CPC pairs in
   one "Gap 1 - …" message, as the brief writes it.
2. `output/kpi-plans/import-1012/runs.json#kpiplan-gate-deck-all-nodes-dense-r1-1791804913`,
   slide 3: architecture layers packed into one multi-line message that keeps every "Label: a, b"
   line.
3. qbr runs (`…#cardplan-deck-qbr-data-r*`): the three segment lines joined with "|" in one
   message. Still structured, and drawn as a table.

### (c) The brief itself was sentences

1. `output/old_zips/gj-h1-regen-5a9e2d/gj-h1-regen-5a9e2d/slides.json`, slide 4 (2026-09-24):
   "Recommendation ads deliver 11.3x ROAS at 1/3rd spend of Search but low NTB", "Curd is the star
   (8.0x ROAS, 12.5% ACOS)", … These are the brief's "KEY READ-OUTS" lines. A list is right here.
2. `…#cardplan-deck-product-launch-data-r1-1791906035` (r2, r3 the same), slide 1: "Teams manage
   4+ separate gateways averaging 2.3 hours/week each on config", "68% of outages last quarter
   traced to gateway misconfiguration", … These are the brief's "The problem (3 pain points)".
3. `output/wide-paid/kpi/wide-kpi-20261013-111701/decks/gate-deck-agency-takeover__r1/slides.json`
   (agency, city slide): "No major high-spend city crossed 0.5x ROAS.", "Bengaluru was the best
   large city at around 0.45x ROAS, …", as in the brief.
4. `output/eval/step0-20261006-215340/decks/gate-deck-cheffin-full__r1/slides.json`, slide 3:
   "Note: Some FLIPCART pivot metrics were unreliable …" and "Key formulas: ROAS = Revenue or
   Sales / Spend", … These are the brief's notes and formulas. They are caption / table material,
   but the brief gives them as lines.

### Not structure: brief instructions copied as content

These come from the outline, and a structured outline would carry them the same way.

- XTSY "Show: Category growth drivers, Consumer demand moments, Impulse purchase behaviour"
  became a 3-item list (every XTSY run, 2026-10-06 → 10-13).
- Agency "Speaker Notes: Explain each pillar in one line — …" became a 6-item list
  (`…#cardplan-gate-deck-agency-takeover-r1-1791906414`, slide 3).

## Conclusion

**Structure is not lost in the outline.** In the 29 runs that kept it, every structured brief line
(series, table row, metric, "Label: a, b, c") arrives as a structured key_message, often
tidier than the brief. No case of flattening was confirmed.

**The component planner already reads the structure.** Since the 2026-09-29 prompt it sends
metrics to kpi_row (81%), records to tables (74%) and series to charts or tables (85%). Only 1
LLM plan in 243 numeric messages chose a list, plus 1 code fallback.

**Where structured bullet lists really come from:**
- September runs (gj-h1 on 2026-09-24, Test 1 on 2026-09-27), before the routing examples and
  card_grid existed;
- in recent runs (50 lists since 2026-10-08, none numeric), the component planner's own rules:
  - "Categorized list → bullet_list" (routing row and Example 4) produces Winners / Weak terms /
    data-needed lists;
  - short named-item lists sit beside a card_grid, flow or layer the slide already has (rule K4
    territory);
  - one unstable choice (the same outline form gave a table in 5 of 6 plans and a list in 1);
  - one fallback after two planner failures;
- brief instructions ("Show:", "Speaker Notes:") that the outline copies as content.

**So the fix, if any, is in the component planner, not a structured outline.**

- Revisit the categorized-list row and Example 4, the named-items-beside-a-grid case and K4 in
  `src/prompts/slide_component_planner/system.j2`.
- Make planner failures rarer.
- Separately, keep instruction lines ("Show:", "Speaker Notes:", "Visual:") out of key_messages.

A form-tagged outline JSON would hand the planner information it already has. Test 1's evidence
also says that the more structured outline path made slides thinner. Caveats:
- the outline was saved only for 6 well-structured briefs on 2026-10-12/13;
- gj-h1 and the data-file input (CSV / XLSX) case are untested at the outline stage;
- a free check of any planner-rule change on these saved plans needs the outline saved.
  Plan-only runners save it; `eval_run` / `slides.json` do not.

## Changes built from this evidence (2026-10-15, free)

Five changes, each checked on the saved plans. Replay: `python -m scripts.structure_loss --replay` applies the
new code checks to every saved plan and outline, then prints the same tables. The corpus now also holds the
2026-10-15 combined run's fresh plans (`output/tile-combined/*/plans.json`): 507 distinct plans, 132 bullet
lists before the replay. Prompt changes (1, 2) cannot be replayed free; the paid check below measures them.
Slide numbers in this section count from 1 (the examples above use `slide_index`, from 0).

| # | change | where | free result |
|---|---|---|---|
| 1 | Grouped items keep their groups: a card per group with its items as bullets (a table when every group has the same fields); one list item per group only on a full slide. Example 4 rewritten in a neutral domain (library branches), with colour roles instead of colour names | `slide_component_planner/system.j2`: routing row, decision priority, Example 4 | prompt only |
| 2 | Short named items beside the main component: under the card they belong to, as its bullets (not a list beside it, not reworded into a written card line); the cards themselves when they are the slide's subject; a list beside it only when they support it (benefits / outcomes of a workflow) | same, decision priority (one bullet) | prompt only |
| 3 | K4: on a full slide, a grid of 6+ cards, 2 in 3 of them with ≤ 6 words of lines, becomes a bullet_list (`CARDS_TO_LIST`, note in `capacity_fixes`); one line in card_grid "Breaks when" | `plan_checks.cards_to_list` (in `finalize_plan`) | 4 plans change, all the agency Keyword & City slide |
| 4 | Presenter notes leave the outline's key_messages; "Visual Suggestion:" and a bare "Show:" are directions; "Show benefits: …" becomes "Benefits: …"; one line in the outline prompt | `written_lines.settle_direction_lines` (in `outline_planner_node`), `_DIRECTION`, `NOTES_LABEL` | 18 messages and 10 components out |
| 5 | Planner failures: `content_data_json` with text around the object is read; card lines read within one message / sentence (fewer false `CARD_LINES_DROPPED` re-asks); `card_plan_only` writes `run.log` | `slide_component_planner.parse_content_data`, `brief_text_for`, `plan_checks._BRIEF_PIECES` | see below |

### 1–2. What the prompt changes target

Corpus B: "categorized" key_messages go to card_grid 45 / bullet_list 14 of 71; label_detail lists (class b) are
38 of 132 lists in corpus A. The agency Winners / Weak terms pair is a list in every saved plan of slide 2.
XTSY slide 3: the 7 opportunity areas are a list beside the levers card grid in 9 of 10 saved plans, while the
planner wrote its own card lines paraphrasing them (`body_source: written`, combined run 2026-10-15) — the same
items twice, once invented. XTSY slide 6: the 5 benefits beside the automation flow are a list in 10 of 10;
change 2 keeps that (supporting outcomes).

### 3. K4 threshold and the slides it changes

The measure is the words in the slide's other components (headline and captions aside), set from every card grid
of 5+ cards in the corpus:

| slide | plans | cards | words in the other components |
|---|---|---|---|
| agency Keyword & City (slide 2) | 5 | 9 (8–9 title + "Needs immediate review") | **103, 104, 116, 132** (and 132 for a 5-card grid beside the 9) |
| CHEFFIN data sources (slide 4) | 3 | 5 | 107–123 (5 title-only cards beside the notes and formulas lists: under the 6-card floor, unchanged) |
| agency pillars (slide 4), with the speaker-notes list | 1 | 6 | 53 (the notes list goes with change 4) |
| XTSY occasions / impact / automation / matrix | 20 | 6–7 | 12–31 |
| everything else | | 5–6 | ≤ 53 |

Threshold 80 words, in the gap between 53 and 103. The replay changes exactly 4 plans:

| run | slide | other words | result |
|---|---|---|---|
| `eval/step0-20261006-205449` agency r1 | 2 | 103 | 9 cards → 2 items |
| `q1008/quality-1008-20261008-210801` agency r1 | 2 | 104 | 9 cards → 2 items |
| `card-plans/card-plans#…agency-takeover-r2` (2026-10-13) | 2 | 132 | 9 cards → 2 items |
| `tile-combined/combined#…agency-takeover` (2026-10-15) | 2 | 116 | 9 cards → 2 items |

The two items: "Bengaluru: Bengaluru was the best large city at around 0.45x ROAS, …" and "Hyderabad, Chennai,
Jaipur, Sas Nagar, Surat, Nashik, Mumbai, Delhi: Needs immediate review" (cards with the same lines share one
item; every word kept). No slide where cards had room changes: the XTSY 6–7 card grids (12–31 other words) stay
cards. In the replayed tables these two-item lists show up as 2 more "numeric" and 1 more "label_detail" list
(class b): the intended result on a full slide.

### 4. Direction lines

On the 29 plan-only runs: 18 presenter-note key_messages (all agency: the brief asks for "Speaker Notes" in its
output format and the outline wrote one per slide) are dropped; 5 text components that carried only them go
(4 `speaker_notes` narratives / lists, and a narrative paraphrasing the notes). 5 text components that only
repeat a direction go: the 3 XTSY slide 2 lists of "Category growth drivers, Consumer demand moments, Impulse
purchase behaviour" (bare "Show:") and 2 agency "Visual Suggestion" notes. "Show capabilities:", "Show
benefits:", "Show expected impact areas:" keep their content under the noun label. "Highlight:", "Note:",
"Include:", "Key Message:" are content and stay.

### 5. Planner failures

Re-asks and fallbacks in the 210 saved plan-only plans (card-plans, kpi-plans, combined): 32. Causes:

| cause | n | after these changes |
|---|---|---|
| instruction text: agency speaker notes | 12 | gone (change 4: the planner no longer sees the notes) |
| empty component(s): unreadable `content_data_json` | 9 | some read now (below) |
| `CARD_LINES_DROPPED` | 6 | false hits across two messages / sentences fixed: on the outline runs' saved card grids the old reading flags 4, the new 1 |
| `KPI_VALUE_TEXT` | 3 | unchanged (real) |
| call failed (exception) | 1 | cause not saved |
| fallback (failed twice) | 1 | kpi-plans p3, CHEFFIN slide 6; cause not saved |

Unreadable `content_data_json` texts in the logs that kept them (combined `run.log`): 6. 4 are a bare `{` (not
recoverable; the re-ask handles them), 2 repeat the field name before a valid object (`content_data_json': {"title": …}`):
`parse_content_data` reads those now. The wide-paid log showed 3 first tries that spent all 16000 output tokens
on reasoning; `models.yaml` already gives the planner 24000 (`1802455`). Whether that is enough is not
reproducible free; the paid check's `run.log` will show it.

### Proposed paid check (not run)

`python -m scripts.card_plan_only --repeat 3 --label choice-plans --bundle --workers 5` on the test PC (5 decks at once, same cost): the six cases ×
3 (planning only, outline saved, now with `run.log`). Cost ≈ $1.5 (the 2026-10-13 run of the same 18 was $1.52;
agency should cost less without the speaker-note re-asks); ceiling $2. Then free on this PC:
`python -m scripts.structure_loss` and `python -m scripts.card_plan_only --label choice-plans --rescore`.
What to read: agency slide 2 (Winners / Weak terms as cards or one list per group; K4 firing on the city cards),
XTSY slide 3 (opportunity areas under the matrix cards, no written lines), XTSY slide 2 (no "Show:" list),
no speaker notes anywhere, re-asks per run vs 32 / 210 plans, fallbacks 0, length-limit lines in `run.log`, and
that QBR / product-launch card slides stay cards.
