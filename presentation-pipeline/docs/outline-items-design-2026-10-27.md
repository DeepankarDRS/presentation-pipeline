# Outline items: a three-level design (2026-10-27)

Status: **design only, nothing built.** Decided with the user on 2026-10-27. Before any code, read §2 (what was rejected and why) and §7 (the test gates).

## 1. Problem

The outline planner hands the slide component planner one flat list of strings per slide, `key_messages`
(`src/agents/outline_planner_schema.py`). The planner has to guess what each line is from its wording, and it
cannot tell lines copied from the brief from commentary the outline wrote. Evidence from the component-selection
review (`docs/eval/component-selection-bias/README.md` on the `layout-bias-audit` worktree) and the 2026-10-27
measurement (§8):

- `narrative` is the over-picked kind. In QBR and the product launch deck, 19 of 21 narratives are commentary
  the outline wrote, not the brief. The cause is the outline prompt: "NARRATIVE messages add insight… beyond the raw
  data" (`src/prompts/outline_planner/system.j2`, the key_messages count rule), and the planner must place every
  message. In the newest saved run (typed schema, 2026-10-15) all 9 narratives in those two decks are outline
  commentary; one adds a cause the brief does not give ("driven by stronger enterprise bookings").
- The outline does not keep to the five message shapes its prompt defines. Across 395 saved slides it wrote 105
  dated events (no shape for them), split tables into one message per pipe row (96 rows, 29 header rows; 18 slides
  with a table spread over several messages), and wrote 18 speaker notes as messages although the prompt forbids it.
- The planner copies faithfully once it has the content: every saved KPI value (87/87) and chart value and label
  (47/47) is in the outline's messages, and 80/81 table components' values are too.

So the loss is in the outline's output format, not in the planner's copying.

## 2. Decisions and rejected options

Top-down, one level at a time (user, 2026-10-27): the outline decides **what** the content is, the slide component
planner decides **which component** draws it, the generator decides **composition and style**. Each level is tested
before the next (§7).

Rejected on 2026-10-27, not to be proposed again unless the user reopens them:

| Option | Why rejected |
|---|---|
| Item `id` and `source` fields (`brief:L12`, `written`) | Extra structure for the LLM to get wrong; the outline stays the source of truth, as `key_messages` is today |
| Pointers to brief blocks (Test 1 `L` / `T` / `C` block ids) instead of copied text | User expects it to fail on future briefs |
| Datasets + `encode` / `bind()` (planner writes field mappings, code fills values) | Too deep a JSON for a 20-slide deck with 5–10 components per slide; one wrong key-value pair is a deck-level risk |
| A one-to-one map from content kind to component | Cuts variety, the September `layout_pattern` regression (see the slide-quality rework plan) |

## 3. Level 1: outline planner (what the content is)

### 3.1 Schema

```python
class OutlineItem(BaseModel):
    kind: Literal["metric", "series", "records", "steps", "point", "visual", "note"]
    text: str   # copied exactly from the brief, as key_messages is today

class OutlineSlide(BaseModel):
    label: str; slide_title: str; subtitle: str; section: str; narrative_role: str   # unchanged
    items: list[OutlineItem]   # replaces key_messages (min 1)
```

`OutlinePlannerOutput` (deck_title, core_hook, slides) is unchanged. Strict `json_schema` decoding stays, so key
names and structure cannot come out wrong; a wrong value stays inside one item, as today.

### 3.2 What each kind holds

| kind | text | Example |
|---|---|---|
| metric | one number with its label and change | `ARR: $42.8M (+18% QoQ)` |
| series | one measure over labels (periods or entities) | `Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M` |
| records | one table: entities × measures, rows split by ` \| ` | `Enterprise: ARR $28.1M, QoQ +22%, 142 customers \| Mid-Market: ARR $14.4M, …` |
| steps | an ordered sequence; dated events go here too | `Discovery → Design → Build` · `Oct 2026: Private beta; Apr 2027: SOC2 + HIPAA` |
| point | a qualitative statement, or named items | `Self-serve onboarding cuts CAC payback to 10 months` · `Pillars: Visibility; Conversion; Retention` |
| visual | the brief's own drawing direction, never drawn | `trend chart with KPIs on top` |
| note | a caveat, data note or formula the brief states | `ZAROMA sheets cover campaigns only` |

### 3.3 Example (QBR-style)

Brief:
```
Slide 3 — Revenue
Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M
ARR $42.8M (+18% QoQ), NRR 114%
Visual: trend chart with KPIs on top
```

Today:
```json
"key_messages": [
  "Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M",
  "ARR: $42.8M (+18% QoQ)",
  "NRR: 114%",
  "Visual: trend chart with KPIs on top",
  "Momentum reflects strong enterprise adoption and expansion revenue."
]
```

Proposed:
```json
"items": [
  {"kind": "series", "text": "Revenue by quarter: Q1 $28.4M, Q2 $31.2M, Q3 $36.1M, Q4 $42.8M"},
  {"kind": "metric", "text": "ARR: $42.8M (+18% QoQ)"},
  {"kind": "metric", "text": "NRR: 114%"},
  {"kind": "visual", "text": "trend chart with KPIs on top"}
]
```

The last line of today's version disappears because of the prompt rule below, not because of the schema.

### 3.4 Outline prompt rules (changes)

- The commentary rule changes: a `point` comes from the brief, or is written only when `amount_of_text` asks for
  narrative; it never repeats the slide's figures or headline. The "NARRATIVE messages add insight… beyond the raw
  data" wording goes.
- One table = one `records` item, rows split by ` | `, each row naming its measures. Never a message per row or a
  header row on its own.
- Dated events are one `steps` item.
- `visual` items carry no "Visual:" label (the kind says it); copied word for word from the brief, never made up.
- Speaker notes and talking points are never items.
- Unchanged: figures copied exactly, never invented; each fact on one slide; hero slides 1–2 items.

### 3.5 Compatibility

`key_messages` stays as a field computed from the items (`[i.text …]`, "Visual: " put back in front of visual
items), so code that reads it keeps working during the switch: `written_lines.py`, `repairer.py`,
`slide_replanner.py`, `outline_replanner.py`, `brief_text_for` / `_filter_supplied_content_for_slide` in
`slide_component_planner.py`, `scripts/structure_loss.py`, `scripts/kpi_plan_only.py`, the frontend plan editor
and `api.models.ts`. Behind a flag (name to decide at build time); off = today's route.

### 3.6 Code checks (no LLM)

- `POINT_NOT_IN_BRIEF` (report-only): a `point` whose words are mostly not in the brief is listed for review with
  Keep / Remove, like written card lines today. Without a `source` field this word check is what marks outline
  commentary; on the newest saved run it flagged all 9 written QBR / launch narratives.
- Numbers in items that are not in the brief (today's plan checks; 0 found in 1,662 saved messages).
- A `records` item whose rows do not all have measures, a `visual` item with numbers, a speaker-note prefix → one
  re-ask through the existing re-ask path.

## 4. Level 2: slide component planner (which component)

- **Input:** items numbered with their kind, e.g. `2. [metric] ARR: $42.8M (+18% QoQ)`, plus the header and visual
  direction as today.
- **Output:** today's typed schema (`src/agents/planner_schema_typed.py`), unchanged. The planner keeps writing
  `content_data`; the measurement shows it copies values faithfully.
- **Routing table** in `src/prompts/slide_component_planner/system.j2` is keyed by item kind instead of message
  shape, and lists the fit list's options for each kind. The existing decision priorities (entities × measures →
  table, unordered items never chevrons, grouping numbers into several kpi_rows by role, …) stay.
- **Merge and split stay allowed:** two metric items in one kpi_row, a series as a chart plus a hero tile for its
  latest value, several items in one table.
- **Points are placed, not padded:** every item is placed; a point may land in the subtitle, a caption or a
  narrative, and the planner never gives a component to a line that only repeats a label ("6 Pillars:").

### 4.1 The widened fit list

A new data file, e.g. `src/knowledge/core/kind-fit.yaml`, rendered into the planner prompt (one source, like
`capacity.yaml`). The draft list was widened after the free check in §8.2: many picks outside it were legitimate
(one entity's measures as KPI tiles, named items as a tree / matrix / pyramid).

```yaml
metric:  [kpi_row, table, narrative, bullet_list]
series:  [chart, kpi_row, table]
records: [table, chart, kpi_row, card_grid]
steps:   [process_arrow, flow, card_grid, timeline, pyramid]
point:   [narrative, bullet_list, card_grid, caption, tree, matrix, pyramid, layer]
note:    [caption]          # or a footnote inside the component it qualifies
visual:  []                 # steers the layout, never drawn
```

Notes per kind:
- series: chart by default (sorted when it is a ranking); two points → a before / after KPI pair; latest value as a
  hero tile beside the chart; a table when exact values matter.
- metric: tiles, one row or several rows by role, a hero, tones as today; a cell when it belongs with records.
- records: one measure across entities → a sorted bar chart; one entity with several measures → KPI tiles.

`KIND_OUTSIDE_FIT` is **report-only** at first: a pick outside the list is logged and counted, never blocked or
re-asked. It becomes a rule only if the level 2 gate (§7) shows the outside picks are mistakes.

## 5. Level 3: generator (composition and style)

Unchanged: refs for KPI tiles and cards (`fill_refs`, `cards.py`, tiles), design tokens, fit-grow, critic. Tested
only after levels 1 and 2 pass.

## 6. Review screen

Each slide shows its items as rows with a small kind icon and the text, editable in place; the kind can be changed
from the icon. `visual` shows as a line under the header. Points flagged `POINT_NOT_IN_BRIEF` are amber with
Keep / Remove. No ids or JSON are shown. Until the screen is changed, the computed `key_messages` keeps today's
screen working.

## 7. Test gates (top to bottom)

Free checks first, one paid run per level, case list and cost estimate shown before any paid run.

| Gate | Run | Pass |
|---|---|---|
| 0, free | unit tests: schema, computed `key_messages`, prompt rendering, the code checks of §3.6, the fit-list file rendered into the planner prompt | all pass; `pytest tests/unit -q` = baseline + new tests |
| 1, outline | plan-only run, six decks (`deck-qbr-data`, `deck-product-launch-data`, `gate-deck-agency-takeover`, `gate-deck-all-nodes-dense`, `gate-deck-cheffin-full`, `gate-deck-xtsy-qcomm`) × 3 repeats, flag on | no number dropped or invented against the brief; each table as one `records` item; 0 speaker notes; `POINT_NOT_IN_BRIEF` items far below today's (QBR + launch: 9 of 9 narratives written); item kinds agree with a hand check of the 37 slides read on 2026-10-27; the same kinds across repeats |
| 2, planner | the same run's plans (gates 1 and 2 cost one run, ≈ $1.2–1.5) against the saved `card-plans/typed-schema` plans | narrative share down; components per slide not lower; distinct kinds per deck not lower; every `KIND_OUTSIDE_FIT` pick read by hand; numbers dropped outline → plan ≤ today's |
| 3, generator | `scripts/gen_from_plans` on the gate 2 plans, then blind marks against the current route | no loss against the current route (blind marks ≥ 0.5) |

A gate that fails stops the levels below it; the fix goes into the level that failed.

## 8. Measurement (2026-10-27, free, LLM-free)

395 saved slides from the plan-only runs that kept the outline (`output/card-plans/{card-plans,choice-plans,
typed-schema}`, `output/kpi-plans/{import-1012,p3}`; 1,662 messages, 839 components). Kinds and sources were tagged
by code (`scripts/structure_loss.item_shape` plus patterns for dates, pipe rows and speaker notes), components
traced to messages by text match. The code tagger is noisy (it reads some series as records), so per-kind numbers
are indications. The scripts were run from a scratchpad and are not in the repo; port them to `scripts/eval/` if
gate 1 needs them again.

### 8.1 Copying and tracing

| Component | Values found in the outline's messages | Labels word for word |
|---|---|---|
| kpi_row | 87 / 87 | 81 / 87 |
| chart | 47 / 47 | 47 / 47 |
| table | 80 / 81 | 40 / 81 all, 71 / 81 at least 80% (the planner names columns) |

92% of components trace at least 80% of their content to the messages; 5% do not (written card lines, label-only
captions such as "CALL TO ACTION", notes, diagram ids). 7% of messages are placed nowhere (mostly points, and the 18
speaker notes); 6% feed two components.

### 8.2 Today's picks against the draft fit list

| Kind | Placements | Outside the draft list | What the planner picked |
|---|---|---|---|
| metric | 280 | 6% | kpi_row 235, table 28, bullet_list 14 |
| steps | 160 | 6% | card_grid 65, timeline 45, process_arrow 21, flow 20, pyramid 6 |
| records | 287 | 26% | table 130, chart 64, kpi_row 35, card_grid 19 |
| point | 848 | 22% | card_grid 329, narrative 188, bullet_list 127, tree / matrix / layer / pyramid 38 |
| note | 41 | 93% | inside lists and cards |

The draft list (in the 2026-10-27 discussion) was widened to §4.1 from this table.

## 9. Risks and open questions

- **Kind tagging by the outline:** unknown how reliably gpt-5-mini tags kinds; gate 1 measures it against the
  hand check. A wrong kind only changes the options the planner is shown, it never blocks a pick (§4.1).
- **Without `source`, written commentary is found by a word check** (§3.6). Commentary built from the brief's own
  words can pass it; gate 1 reads the flagged and unflagged points by hand.
- **Output size:** a kind field adds a few tokens per item; a 20-slide outline stays one call well inside the step's
  `max_tokens` (32,000). Measured in gate 1.
- **Notes:** 93% of notes land inside lists and cards today; whether a note in a card is wrong is decided at gate 2,
  not by the fit list.
- **Open:** the flag's name; whether the review screen change ships with gate 1 or after gate 2.

## 10. Files the build touches

`src/agents/outline_planner_schema.py`, `src/agents/outline_planner.py` (computed `key_messages`),
`src/prompts/outline_planner/system.j2`, `src/prompts/slide_component_planner/{system,user}.j2`, new
`src/knowledge/core/kind-fit.yaml`, `src/agents/plan_checks.py` (`POINT_NOT_IN_BRIEF`, `KIND_OUTSIDE_FIT`),
`src/state.py` if it declares the outline slide, the outline replanner, unit tests; later the frontend plan editor.
Paths as on this branch; the folder-layout refactor branch moves `src/agents/*` into sub-folders.
