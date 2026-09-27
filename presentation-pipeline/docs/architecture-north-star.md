# Architecture north star — slide-quality rebuild

> **Living document.** Created 2026-09-24 in the architecture-review session. It is the **plan of record for slide quality** and supersedes `docs/roadmap-derived-components.md`, which the user halted on 2026-09-24 because slide quality was not improving. Update it every session (§0).

**Status (2026-09-27, later):** Test 1 passed. **Direction changed (user, D14):** keep `outline_planner` + `slide_component_planner` and make `plan_reviewer` a real feedback loop; carry Test 1's fidelity fixes into them; the Test 1 planning path is not taken to production; **Tests 2 and 3 dropped**. Work paused until the user kicks off the build — plan in `AGENTS.md` "Next work". Open decisions: §12.

## Contents

0. [How to use this document](#0-how-to-use-this-document)
1. [Summary](#1-summary)
2. [The pipeline today](#2-the-pipeline-today)
3. [Evidence](#3-evidence)
4. [What is right — keep](#4-what-is-right--keep)
5. [Root causes](#5-root-causes)
6. [Why the halted roadmap did not raise quality](#6-why-the-halted-roadmap-did-not-raise-quality)
7. [Target architecture](#7-target-architecture)
8. [LLM calls and cost](#8-llm-calls-and-cost)
9. [Validation tests (gate before building)](#9-validation-tests-gate-before-building)
10. [Build milestones (after the tests)](#10-build-milestones-after-the-tests)
11. [What stays, what goes](#11-what-stays-what-goes)
12. [Decisions](#12-decisions)
13. [Issues found during the review](#13-issues-found-during-the-review)
14. [Session log](#14-session-log)
- [Appendix A — headlines: golden vs generated](#appendix-a--headlines-golden-vs-generated)
- [Appendix B — planned component kinds per slide across runs](#appendix-b--planned-component-kinds-per-slide-across-runs)
- [Appendix C — reproducing the evidence](#appendix-c--reproducing-the-evidence)

---

## 0. How to use this document

**Kick-off prompt for a new session (build device):**

> Read `AGENTS.md`, `docs/architecture-north-star.md` and `docs/session-kickoff.md` (two-device workflow and cost rule). We are working on **<Test N / milestone MN>**. Summarise its goal, pass criteria and the open decisions it touches, record the unit-test baseline (`uv run pytest tests/unit -q`), and ask me before coding. This device has no OpenAI key: verify everything LLM-free first and ask before any paid run, with the case list and a cost estimate.

**Update rules**

- Add one row per session to §14 (date, what was done, what changed in this document).
- Test and milestone status lives in the tables in §9 and §10 (status, date, cost, result folder).
- Decisions: move a row in §12 from *open* to *decided* with the date and who decided. Never delete a decision; mark it *superseded* and link its replacement.
- Evidence in §3 is dated. Add new measurements with their run id; do not overwrite old numbers, mark them *superseded*.
- Paid runs follow the cost rule in `docs/session-kickoff.md` §5: free replay first, at most one paid run per step, ask first with the case list and cost.
- Building and commits happen on the build PC; paid runs happen on the test PC; results come back as eval bundles (`llm_test/*.zip` → `docs/eval/<label>/`).

**Conventions:** slide numbers are 0-based as in eval folders (`slide-0` = cover). "Golden" = `tests/fixtures/golden/gj-h1-deck/` (renders in `docs/eval/golden-gj-h1/`). "CHEFFIN" = `tests/cases/gate-deck-cheffin-audit.yaml`.

---

## 1. Summary

**Problem.** Output quality is not good enough and has not improved across recent runs, although the mechanical metrics did (first-pass compile 50% → 93–96%, golden card-pattern match 0.38 → 0.55).

**What the evidence shows** (four saved gj-h1 runs with unchanged planning prompts, §3):

- Most of what makes the slides bad starts in **planning** (outline planner + slide component planner):
  - the brief's headline is lost on **13 of 13 content slides in every run**;
  - **7–13%** of the brief's numbers are dropped;
  - highlighting is requested on **14 of 14 slides** by the mandatory design hints;
  - the same brief gets different components from run to run: only **1 of 14** slides was planned the same way in all four runs.
- The **XML writer (generator) is faithful**: in the three recent runs it drops **0–3%** of the numbers it is given, and the losses it does cause come from a forced blueprint with no room or an overfilled component (§3.3). It compiles first time on **93–96%** of slides. Its real weaknesses are **inconsistent card styling** (about twice the golden's number of distinct KPI-tile and card styles) and **sizing without measurement** (~2 geometry fixes per slide, over-full tables).
- The generator prompt is **8–13k tokens per slide**, of which the slide's own data is **1–3%**. It forces a blueprint on **13 of 14** slides and contradicts itself (§3.4).
- The golden deck goes through the **same POM compiler** and looks right. The renderer is not the limit; the decisions made before it are.

**Direction**

1. **Keep LLM-authored POM XML** as the source of truth. POM is designed for it ("simple XML structure designed for LLM code generation", POM README), and `EDITING_ARCHITECTURE.md` principle 1 already says "XML is the source of truth".
2. **Fix planning first**: a fact store, a storyline (headline claim, facts per slide, parallel groups), component choice that respects capacity, no forced decoration.
3. **Clean the generator prompt**: no mandatory blueprints, archetypes or elements; no contradictions.
4. **Raise the XML's level with component tags** for repeated cards, **only if Test 2 shows it wins**.
5. **Size in code before rendering** (POM's own text measurement with the deck's real font). The critic and the editor work on named elements, not whole-slide rewrites.

**Next:** Test 1 (§9). About $5 of paid runs across Tests 1–3 settles the architecture before any large build.

---

## 2. The pipeline today

State on 2026-09-24, branch `feat/golden-reference-grounding`.

```
brief ─► elicitor (LLM) ─► outline_planner (LLM, 1 call) ─► slide_component_planner (LLM, 1 per slide, parallel)
      ─► plan_reviewer (LLM, advisory — routing ignores it) ─► style_resolver
      ─► per slide, one after another:
           context_builder (house style, recipes, blueprint picked by component-kind set)
           ─► generator (LLM, writes raw POM XML)
           ─► validator (normalize → parseXml → compile; fit-grow; pptx-post)
           ─► repairer (LLM, on compile failure) ─► [critic + visual_repairer: off by default]
           ─► slide_router
      ─► deck_assembler (combined compile, ZIP-merge fallback) ─► evaluator
```

| Stage | Produces | Where quality is lost (evidence in §3) |
|---|---|---|
| `outline_planner` | `slide_title` (≤ 8 words), `key_messages: list[str]`, `visual_emphasis` | headline replaced by the section label; data flattened into prose strings; allowed to invent numbers |
| `slide_component_planner` | components (POM node families), `content_data`, mandatory `design_hint`, `layout_hint` | numbers dropped; component chosen by message shape, not volume; decoration requested on every slide; different plan every run |
| `plan_reviewer` | score + issues | ignored by routing |
| `context_builder` | contract: house style, recipes, blueprint, notes | blueprint mandatory ("do NOT rearrange") on 13/14 slides, chosen by kind set only |
| `generator` | raw POM XML | inconsistent card styles; sizes guessed; content cut when the plan overfills a component or the blueprint has no room; told to invent when data is thin |
| `validator` / fit-grow | fixed XML, pptx | repairs syntax and geometry after the fact; cannot restore content or change a choice |
| critic (off) | issues + free-text XML fixes | would enforce gj-h1's template on every deck (§7.9) |

---

## 3. Evidence

### 3.1 Method (2026-09-24)

- **Runs:** the four saved gj-h1 runs:
  - `baseline` = `llm_test/gj-h1-regen-69af33.zip`
  - `phase-1` = `…-7293ef`
  - `phase-5-tables` = `…-5a9e2d`
  - `tables-check` = `…-bf396b`

  Each bundle has `slides.json` (per slide: plan + normalized XML) and `run-manifest.json` (per-call tokens and cost).
- **Planning unchanged across the four runs:** `git log ea80267..77000c3` shows no commits touching any of these:
  - `src/prompts/outline_planner/`, `src/prompts/slide_component_planner/`, `src/prompts/elicitor/`
  - `outline_planner.py`, `outline_planner_schema.py`, `slide_component_planner.py`, `planner_schema.py`
  - `settings_mapper.py`, `hint_capabilities.py`, `hint-capabilities.yaml`

  So run-to-run differences in planning are the model's own variance.
- **Numbers:** every number with at least two digits in each slide's section of `tests/cases/gj-h1-regen.yaml`, minus section numbers and the year (`01`–`05`, `26`), gives 365 numbers. Each was checked:
  - against the slide plan (`content_data` + title);
  - against the slide XML (text, text after inline tags, and content attributes such as `value`, `label`, `title`).
- **Headline kept:** the golden slide's headline text appears in the generated slide's text.
- **Decoration:** counts of
  - `<Icon>`
  - `<Mark>` or `highlight=`
  - small ellipse shapes (status dots)
  - nodes with `shadow`
  - `borderLeft` / `borderTop` accent bars
- **Style variety:**
  - *KPI tile* = a VStack with 2–5 leaf children, one text ≥ 22 and one ≤ 16. Its style is padding, gap, radius, background, alignment, and the child tags with their font sizes.
  - *Card* = a VStack with background + padding + radius. Its style is padding, radius, border, shadow and accent edge.
- **Sanity check:** the same number check on the golden deck finds **0 of 389** numbers missing.
- **Script:** `scripts/eval_lineage.py` (added 2026-09-24) reproduces every number in §3.2 and Appendix B; the command is in Appendix C. It reads run folders (`output/runs/<run_id>`, which contain `slides.json`) or zips of them. Eval bundles carry no slide plans.

### 3.2 Measured results

| Finding | Stage | baseline | phase-1 | phase-5-tables | tables-check | golden |
|---|---|---|---|---|---|---|
| Headline kept, content slides¹ | planning | 0/13 | 0/13 | 0/13 | 0/13 | 13/13 |
| Brief numbers dropped (of 365) | planning | 44 (12%) | 27 (7%) | 48 (13%) | 40 (11%) | — |
| Brief numbers dropped (of 365) | XML writing | 28 (8%)² | 1 (0%) | 11 (3%) | 7 (2%) | — |
| Brief numbers missing on the final slides | total | 20% | 8% | 16% | 13% | 0% |
| Slides whose hints ask for highlighting | planning | 14/14 | 14/14 | 14/14 | 14/14 | — |
| Marker highlights in the deck | planned, then written | 51 | 40 | 60 | 51 | 0 |
| Slides with highlights nobody asked for | XML writing | 0 | 0 | 0 | 0 | — |
| Icons in the deck | mostly planning | 47 | 39 | 55 | 50 | 1 |
| Slides with icons nobody asked for | XML writing | 2 | 3 | 3 | 4 | — |
| Nodes with a shadow | XML writing | 22 | 12 | 11 | 16 | 0 |
| KPI tiles / distinct tile styles | XML writing | 46 / 24 | 40 / 22 | 53 / 26 | 50 / 21 | 44 / 13 |
| Cards / distinct card styles | XML writing | 62 / 21 | 60 / 19 | 69 / 20 | 64 / 21 | 70 / 11 |

¹ The cover keeps "H1 2026" in every run, which is trivially inside its title; all 13 content-slide headlines are lost. Full list: Appendix A.
² `baseline` lost two slides to "could not be generated" placeholders, fixed later by deterministic normalizer rules.

Note for later runs: since commit `57ed26e` (2026-09-24), highlights are drawn as a coloured `<Span>` instead of `<Mark>`. The "marker highlights" count will therefore read 0 on new runs even when the hints still ask for highlighting. Track "slides whose hints ask for highlighting" instead.

- **Plan stability:** only **1 of 14** slides got the same component kinds in all four runs (slide 9: one table). For example, slide 1 was three bullet lists in `phase-1`, and chart + two KPI rows + table + bullets in `tables-check`. Appendix B has the full table.
- **Mechanics** (`docs/eval/tables-check/`, 25 slides in 7 runs):
  - compiled 100%, first-pass 96% (gj-h1 alone 92.9%)
  - 2.08 fit-grow changes per slide
  - 5 slides with over-full tables, 4 with table spill
  - mean fill 0.883
- **Golden composition** (`docs/eval/golden-gj-h1/`): 74 cards, all in five patterns (KPI tile 36, text card 13, table card 13, dark panel 6, chart card 6), and 1 icon in the whole deck. Its polish comes from density, semantic colour and read-out panels, not decoration.

### 3.3 Failures seen in the renders, with the stage that caused them

- **`tables-check` slide 5 (Swiggy):**
  - The title is the label "Platform Deep-Dive · Swiggy" instead of the brief's "Our efficiency engine — compounding since April".
  - There are 7 KPI tiles.
  - The city × category chart is flattened to four categories ("Hyderabad Paneer", …) instead of two series.
  - All of that was the planner's choice (`content_data` already had 7 tiles and flat labels); the generator drew it faithfully.
  - The generator placed the category table in a small squeezed card, and there are marker highlights.
- **`tables-check` slide 12 (roadmap):**
  - The planner put month-by-month actions into a Timeline.
  - The Timeline recipe allows labels of 1–3 words, so the generator cut the actions (e.g. "Baseline & Fix").
  - The H2 summary sits alone in a large dark panel.
  - The golden uses one full-width table with a "Key execution actions" column.
  - Causes: capacity-blind planning, then a cut at XML writing.
- **`phase-5-tables` slide 4 (Blinkit):**
  - The plan had both tables (category and ad type) with correct data.
  - The slide was forced into the `kpi_snapshot` blueprint (one chart + a 40% sidebar), and the XML has only one `<Table>`: the ad-type rows, under the title "Category Performance". The category table (Milk / Curd / Paneer) is gone, and the right 40% of the middle band is empty.
  - Cause: the forced blueprint, with the loss at XML writing.
- **CHEFFIN (`tables-check`):**
  - The chart "Allowable vs Actual CPC" plots actual CPC as 13.5 / 17.2, while the brief says ₹31.1 / ₹46.2. The chart contradicts the deck's main point. The stage is unknown: this bundle has no `content_data`.
  - A table of "City/Keyword 1/2/3" with values "high / low / varied" was invented.
  - Source dates were invented ("Q2 FY24", "May 2024").
  - CVR (%) and AOV (₹) share one axis, so the CVR bars are invisible.
  - The brief asked for "white background, dark text, and subtle FLIPCART orange + ZAROMA purple accents" and got the default blue palette.
  - All 6 titles carry a marker highlight, because every title's hint asked for one.
- **Blueprint replay** (`select_blueprint` on the `tables-check` plans): 13 of 14 slides get a blueprint that says "follow this structure — do NOT add, remove, or reorder bands". Slides 1, 4, 5 and 6 are deep-dives with tables, a chart and KPIs; they get `kpi_snapshot`, so their tables have to squeeze into its 40% sidebar.

### 3.4 Generator prompt audit

Rendered from the `tables-check` plans with the current code.

- **Size:** 33–51k characters per slide (≈ 8–13k tokens). The slide's own `content_data` is 1–3% of that.
- **Contradictions inside one prompt:**
  - "LAYOUT GRAMMAR — a GRAMMAR, not a template" vs "BLUEPRINT — do NOT add, remove, or reorder bands".
  - "LAYOUT ARCHETYPE (mandatory): pick A–E, different from the previous slide", although:
    - `layout_archetypes` is never rendered (`_HOUSE_STYLE_SECTIONS` in `context_builder.py` leaves it out);
    - no archetype comment appears in any saved XML;
    - the matched blueprint may itself be the archetype the prompt forbids.
  - Bullets: "4–6 concise takeaways" (`design-language.yaml`, content_invention) vs "max 3–4, ≤ 50 chars" (checklist).
  - "Invent realistic, specific figures" vs the planner's "ZERO IMPROVISATION". The invent instruction appears in four places: generator `user.j2`, `design-language.yaml`, the outline schema and the outline prompt.
  - "fontSize ≥ 14 is the #1 rule" vs the golden, which uses sizes 9–13 in 387 places and 14 only 34 times. At a floor of 14, the densest golden slides only fit if content is cut.
- **Mandatory on every non-cover slide:** an eyebrow kicker, a card shell around every table or chart, and a "Source:" line. The source line is where the invented source dates come from.

### 3.5 Other structural findings

- **Nothing checks quality at runtime.**
  - The critic is off by default (`critic_mode="off"` in `scripts/eval_run.py` and the API).
  - `plan_reviewer` scores the plan, but `route_after_plan_review` always continues.
- **Eval metrics measure mechanics** (fill, spill, overflow, first-pass) and similarity to one deck. Nothing measures headline quality, data coverage, variety or decoration.
- **`gj-h1-regen` is a transcription task:** the brief contains the whole deck's text. It tests layout, not storytelling.
- **Scale:** slides are generated one after another inside one graph run with `recursion_limit=150`. Each slide takes at least 4 steps, plus 2 per retry, and more with the critic on. `SLIDE_PLANNER_MAX_PARALLEL` and `MAX_CONCURRENCY` are declared in `slide_component_planner.py` but never applied.

### 3.6 Corrections made during the review

These are statements from earlier in the review that the data changed.

- **"The XML step loses data."** Measured, it barely does: 0–3% in the three recent runs, and those losses come from forced blueprints or overfilled components. Planning drops 7–13%.
- **"The LLM should never write XML."** Withdrawn. The XML writer is faithful and reliable, and POM is designed for LLM-authored XML. The revised design is in §7.
- **Audit bug:** the first pass of the audit missed text after inline tags (`<B>ROAS</B> 6.35x`). The numbers above are the corrected ones. The repo's `invented_numbers` metric has the same blind spot (§13).

---

## 4. What is right — keep

- **Deterministic back end:** POM compile (`compile-pom.js`), normalizer + content model + icon list, fit-grow, `pptx-post.js`. The rule "fix deterministically, never regenerate" is right.
- **Eval harness:** `eval_run` / `eval_import` / `eval_compare`, renders, golden target, LLM-free replay, cost discipline.
- **Knowledge as tested data:** `nodes.yaml`, `hint-capabilities.yaml`, the icon list, `test_upstream_reference.py`.
- **Hierarchical shape** (deck → slide → render) and the human-in-the-loop API (edit outline, refine plan, edit slide).
- **LLM-authored POM XML:** faithful and reliable (§3.2).
- **`recipes.yaml`:** compiled, audit-clean snippets. Raw material for component templates.

---

## 5. Root causes

1. **Content passes between stages as prose, and nothing checks it.**
   - Headlines are lost at the outline: there is no headline/label split and the title is limited to 8 words.
   - Numbers are dropped during planning.
   - Inventing is the default policy, in four places.
   - Nothing at runtime checks that a number on a slide came from the brief.
2. **Decoration and sameness are mandatory.**
   - A `design_hint` is required for every component ("generic hints NOT acceptable"), so highlighting is requested on 14/14 slides.
   - Blueprints are forced by component-kind set.
   - Kicker + card shell + source line appear on every slide, and the critic's polish rules would enforce the same.
3. **Component choice ignores capacity.**
   - Routing goes by message shape, not by how much content there is.
   - A component that can't hold its content makes the generator cut it (slide 12).
   - There are no chart checks (one unit per axis; real series instead of flattened categories).
4. **The LLM rewrites card internals on every slide.** This gives about twice the golden's style variety, and sizes are guessed without measurement, then fixed afterwards.
5. **The generator prompt is an over-long, self-contradicting rulebook** (§3.4).
6. **Nothing judges communication at runtime,** and the eval metrics reward mechanics.

---

## 6. Why the halted roadmap did not raise quality

The roadmap's executed work was all on the render layer: eval harness, sizing grammar, table sizing, cell centring, normalizer fixes. Its metrics moved: first-pass 50% → 93–96%, golden match 0.38 → 0.55, less table spill. But the failures a reader sees are decided before the render layer (the "planning" rows in §3.2), and sizing work cannot fix a wrong decision.

**Kept from it:** the eval harness, the deterministic normalizer fixes, table sizing in fit-grow, and the pptx post-process. Nothing else is carried forward as a plan. This document stands on the evidence in §3.

---

## 7. Target architecture

Revised 2026-09-24: LLM-authored XML is kept.

### 7.1 Principle

The LLM decides what to say and which design to use, and it writes POM XML. Code guarantees facts, consistency and fit:
- numbers come from a fact store;
- repeated cards come from designed templates;
- sizes are measured.

XML stays the source of truth.

### 7.2 Stages

```
A  Understand brief  1 LLM call → fact store: every number, name, date and quote with an id and its source
                     span (the LLM points, code copies the text); pasted tables parsed by code; style and
                     brand directives; deck type (presented / pre-read); missing-info questions
                     (replaces the elicitor)
B  Storyline         1 LLM call (> 15 slides: 1 skeleton call + 1 per section, in parallel) → per slide:
                     intent (§7.8), headline claim, label (kicker), subtitle, fact ids, so-what, parallel
                     group, emphasis target, speaker notes. Code checks coverage, conflicting values and
                     slide count
C  Slide design      1 LLM call per slide, in parallel, writes POM XML: layout + component tags bound to
                     facts + raw POM where no component fits. Code first picks the components and layouts
                     that can hold this slide's content and passes only those in
D  Measure + fit     code: expand component tags, measure text with the deck's font, choose component
                     variants; if it still doesn't fit → split the slide or move detail to appendix/notes
                     (logged). Never cut silently
E  Render            POM compile → pptx-post; the normalizer stays as the safety net for raw POM
F  Check             code checks (overlap, overflow, minimum font, contrast, number provenance, emphasis
                     budget) + optional vision critic; each fix goes to the stage that owns the problem
```

Test 2 (§9) decides whether B + C become one call per slide or stay as today's two calls (planner + generator).

### 7.3 Fact store (sketch)

```yaml
facts:
  - id: blinkit.jun.roas
    entity: Blinkit
    measure: ROAS
    period: "Jun '26"
    value: 6.35                    # parsed by code
    display: "6.35x"               # copied verbatim from the brief
    polarity: higher_is_better     # drives semantic colour
    source: {span: "L143:c20-c25"} # where the LLM pointed
  - id: t.blinkit.categories       # a whole table, parsed by code
    kind: table
    columns: [Category, Ad sales, Ad spend, ROAS, ACOS]
    rows: [...]
policy: {invent: never}            # D2 in §12
style: {background: white, accents: ["FLIPCART orange", "ZAROMA purple"]}
deck: {type: pre-read, audience: brand leadership, slides: 14}
```

### 7.4 Storyline (sketch)

```yaml
- slide: 4
  intent: deep_dive
  label: "PLATFORM DEEP-DIVE · 01"
  headline: "Efficient on ROAS, softened on top-line"
  subtitle: "June '26 · Milk, Paneer & Curd — search and recommendation ads"
  facts: [blinkit.jun.sales, blinkit.jun.roas, t.blinkit.categories]
  so_what: "Recommendation ads are the efficiency lever; Paneer drags"
  emphasis: [blinkit.jun.roas]
  parallel_group: platform_deep_dives   # slides 4–6 share one layout on purpose
```

### 7.5 Slide design: component-level POM XML

```xml
<!-- today: the LLM writes every node of every tile -->
<VStack w="max" padding="14" gap="3" backgroundColor="$surfaceAlt" borderRadius="12" border.color="$border" border.width="1" justifyContent="center">
  <Text fontSize="14" color="$textMuted">ROAS</Text>
  <Text fontSize="26" bold="true" color="$textMain">6.35<Span fontSize="16">x</Span></Text>
  <Text fontSize="14" color="$positive">Best of 3 platforms</Text>
</VStack>

<!-- target: still POM-style XML; code expands the tag into the designed tile -->
<KpiTile id="roas" fact="blinkit.jun.roas" note="Best of 3 platforms" tone="positive"/>
```

- **First tags to test:** `Header`, `KpiTile` / `KpiStrip`, `TableCard`, `ChartCard`, `ReadoutPanel`. These are the golden's repeating patterns (§3.2).
- **Raw POM stays allowed anywhere** (VStack, HStack, Text, …). Nothing the LLM can do today is taken away.
- **Every component has an `id`**, so the critic and the editor can address it.

### 7.6 Sizing and measurement

- POM already measures text with opentype.js and accepts caller-supplied font bytes. Measure with the font PowerPoint will actually draw (D4).
- POM master slides can carry the footer, source line and page number. Today the LLM is asked to write these on every slide.
- **Density tiers:** presented decks (minimum font 14–16) and pre-read decks like gj-h1 (minimum about 10–11). See D3.
- **When content is over-full:** switch to a smaller component variant, then split the slide or move detail to the appendix. Never cut silently.

### 7.7 Checks

- **Deterministic:**
  - overlap, overflow, out-of-bounds
  - minimum font per tier, contrast, grid alignment
  - every number traceable to a fact or a formula
  - emphasis budget: at most 2 emphasised items per slide
  - empty slots
- **Vision critic:** judges hierarchy, clarity, emphasis, and whether the slide supports its headline. It runs in batches of about 3 slides per call, plus one whole-deck contact-sheet check.

### 7.8 Coverage for any slide type

| Group | Slide intents |
|---|---|
| Framing | cover, agenda, section divider, closing / ask, contact |
| Key message | executive summary, big statement, quote / testimonial, single hero number |
| Numbers & data | KPI dashboard, trend, ranking, mix / breakdown, target vs actual, detailed table |
| Comparison | A vs B, before / after, pros / cons, options / pillars, pricing tiers |
| Sequence | process, timeline, roadmap with detail, action plan (what / who / when) |
| Frameworks | 2×2 matrix, pyramid / layers, org chart, architecture diagram, cycle / hub-and-spoke |
| Evidence & people | case study; team (user images via POM `<Image>`, otherwise icons or initials); product features; customer logos; risks and mitigations |
| Overflow | appendix |

**Components** (about 30 in total; build them only as the evidence justifies, starting with Test 2's five):
- **Text:** headline block, callout, statement, quote, bullets, numbered list, icon list, checklist.
- **Numbers:** KPI tile, KPI grid, big number, stat pair, progress bar.
- **Tables:** standard, compact, highlighted row, totals row.
- **Charts:** bar, column, line, area, donut, stacked, grouped.
- **Diagrams:** timeline, roadmap lanes, steps, chevrons, flow, matrix, pyramid, tree, cycle, boxes-and-arrows.
- **Containers:** card, pricing tier, comparison column, person card, image frame, logo row, footer.

**A component is production-grade when:**
- it is designed once and drawn by code;
- each slot has a length limit per density tier;
- numbers are formatted by locale (₹ L/Cr, $M);
- the metric's polarity drives its colour (e.g. higher ROAS is good, higher ACOS is bad);
- it has a defined shrink order (KPI tile: sparkline → note → delta, never the value);
- for charts, the type follows the data shape and message: rankings sorted, the focus series highlighted, one unit per axis;
- it passes a gallery test of every variant × theme × tier × content extreme.

**A layout is production-grade when:**
- it sits on one grid (fixed margins, title and footer zones);
- it has one focal point and a reading order;
- its slots have declared capacities;
- slides in the same parallel group share it on purpose;
- variety comes from slide intent, component variants, visual style (2–3 design languages), brand colours and free composition.

### 7.9 Visual critic and slide editor

**Today:**
- **Critic** (`src/prompts/visual_critic/system.j2`):
  - It gives fixes as free text.
  - `affected_nodes` must come from a list that includes names POM does not have (ZStack, KPI, Bullet, Divider, Spacer).
  - `visual_repairer.py` then rewrites the whole slide (PATCH) or re-plans and regenerates it (3 calls), and `critic.py` rolls back if the repair doesn't score better.
  - Its polish rules require a kicker on every slide, and a source line + dark panel on data slides. That is gj-h1's template applied to every deck.
- **Editor** (`src/agents/slide_edit_service.py`): already exists. Every edit asks the LLM for "the complete modified POM XML" (a full rewrite), then runs a compile-repair loop (2 attempts) and a visual check (1 repair).

| | Today | Target |
|---|---|---|
| Pointing at the problem | "an HStack", free text | `KpiTile#roas`, `TableCard#category` |
| Size of a fix or edit | whole slide rewritten; anything can drift | one attribute or element |
| Numbers | retyped on every rewrite | bound to facts; one fact update changes every slide that shows it |
| Where the fix goes | always the XML | the stage that owns it: headline → storyline; wrong component → planning; crowding → variant or split; style → the component, fixed once |
| Critic's job | also checks overflow and fonts by eye | code checks those; the critic judges hierarchy, clarity and support for the headline |
| Style rules | gj-h1's template for every deck | per design language |

There is no data for this part yet: the critic is off by default and the editor has not been measured. Test 3 covers it.

### 7.10 Scaling to 20–40 slides and dense slides

- **Long decks:** the storyline runs in two passes (skeleton, then sections in parallel).
- **Smaller calls:** each slide-design call gets a slice of the component catalog and the slide's facts instead of 8–13k tokens of rules, and it outputs tags instead of every node.
- **Concurrency and limits:** slide design runs in parallel under a real concurrency cap. Per-slide work moves out of the graph's recursion limit.
- **Dense slides** (5–20 components) are decided by measurement per density tier: fit, a smaller variant, or a split. The LLM doesn't guess.

### 7.11 State (`src/state.py`) and data contracts

`src/state.py` is the contract between the stages. Changing it does not improve slides by itself. It changes because the new stages produce new things: a fact store, a storyline, and components that can be addressed by id.

**Rules for every state change:**
- Make it per milestone, and additive first. All the TypedDicts are `total=False`, so new keys are optional and old runs still load.
- Make it in the same change as everything that reads the state:
  - the API payloads (`ComponentPlanPayload`, `SlidePlanPayload` and the outline endpoints in `src/api.py`);
  - the frontend models (`frontend/src/app/models/api.models.ts` and the plan editor);
  - `slides.json` (written by `evaluator.py`, read by the edit session);
  - `tests/unit/test_state.py`.
- Keep the state JSON-serializable (needed for checkpointing).

| When | Change in `src/state.py` | Why |
|---|---|---|
| Test 1 | None. Planning-only runs use their own schemas plus an adapter to today's `SlidePlan` | keeps the experiment cheap and reversible |
| M2 content layer | Add `Fact` and `FactStore` types and a `fact_store` key. Add storyline fields to the outline slide (`intent`, `headline`, `label`, `subtitle`, `fact_ids`, `so_what`, `parallel_group`, `emphasis`, `notes`), either as a new `StorylineSlide` or by extending `OutlineSlide`. Add `ComponentPlan.fact_ids`, with `content_data` filled from the facts by code. `data_provenance` is superseded by the fact ids | numbers and headlines travel as data, not prose |
| M3 / M4 components + fit | `ComponentPlan.component_id` becomes the component tag's `id` in the XML. Add `variant` and a fit report per component. Add a slide-level log of content moved to the appendix or notes. `design_hint` becomes optional | components can be addressed; nothing is dropped silently |
| M5 critic + editor | Critic issues point at component ids instead of `affected_nodes`. Edit operations are recorded per slide version | fixes and edits touch one element |
| M6 scale | The per-slide keys (`current_xml`, `retry_*`, `compile_result`, critic results) move into a per-slide sub-state that runs in parallel. This replaces today's single loop that resets them after each slide | long decks, recursion limit, speed |
| When the old parts retire | Remove `previous_slide_archetype`. `plan_review` is filled by code checks instead of an LLM. `elicitation_*` stays, because the API's question-and-answer flow uses it, but is produced by the brief-understanding stage. `key_messages` and `visual_emphasis` go if the storyline replaces them | dead fields mislead agents |

---

## 8. LLM calls and cost

### 8.1 Measured today

Run `gj-h1-regen-bf396b`: 14 slides, gpt-4.1.

| Step | Calls | Tokens in | Tokens out | Cost |
|---|---|---|---|---|
| elicitor | 1 | 7,075 | 57 | $0.015 |
| outline_planner | 1 | 8,517 | 5,001 | $0.057 |
| slide_component_planner | 14 | 119,004 | 13,933 | $0.349 |
| plan_reviewer | 1 | 8,058 | 83 | $0.017 |
| generator | 14 | 169,075 | 26,366 | $0.549 |
| repairer | 1 | 3,727 | 2,464 | $0.027 |
| **Total** | **32** | **315,456** | **47,904** | **$1.01** |

### 8.2 Target

Estimates, to be confirmed in Test 2.

| Stage | Calls | 14 slides | 20 slides | Replaces |
|---|---|---|---|---|
| Understand brief | 1 | 1 | 1 | elicitor |
| Storyline | 1 (+1 per ~6 slides above 15) | 1 | 5 | outline planner |
| Plan checks | 0 (code) | 0 | 0 | plan reviewer |
| Slide design | N merged, or 2N separate | 14 or 28 | 20 or 40 | slide planner + generator |
| Fixes when checks fail | ~0.1N | ~2 | ~2 | repairer |
| **Core total** | **≈ N + 3 merged / ≈ 2N + 3 separate** | **~18 / ~32** | **~28 / ~48** | today 32 / ~44 |
| Vision critic (optional) | ≈ N/3 batched + 1 deck check + ~0.25N redesigns | ~10 | ~13 | critic (off today) |

**Estimated cost with the merged call:**

| Deck | Today | Core | With critic |
|---|---|---|---|
| 14 slides | $1.01 | ≈ $0.45 | ≈ $0.65 |
| 20 slides | ≈ $1.45 (extrapolated) | ≈ $0.65 | ≈ $0.95 |

It's cheaper because the prompt drops most of today's 8–13k tokens of rules, and the output shrinks to component tags instead of every node.

---

## 9. Validation tests (gate before building)

**Rules:**
- Pass/fail criteria are fixed before running.
- Stop at the first failure.
- Each test is the first slice of the real build, not throwaway work.
- Build on the build PC; run on the test PC.

| # | Test | What | Cost | Pass if | Status |
|---|---|---|---|---|---|
| 1 | Planning | New fact-store, storyline and slide-planning prompts; planning only; gj-h1 + CHEFFIN, 3 repeats each | ≈ $2 (estimate after the build: ≈ $1.5) | gj-h1 headlines kept on ≥ 12/14; ≤ 2% of numbers dropped; 0 invented numbers; ≤ 2 emphasis marks per slide; same components across repeats on ≥ 10/14 slides. CHEFFIN (added 2026-09-27, user): CPC vs allowable CPC (₹31.1 / ₹46.2 vs ₹10.7 / ₹14.8) in one component, the missing sheet named as a gap, the brand colours captured, 0 invented numbers; headlines state conclusions (judged by the user from `storyline.md`) | **passed 2026-09-27 (user), stability carried forward** — final run: headlines 13/13, dropped mean 1.0%, 0 invented, ≤ 2 hints, CHEFFIN checks 3/3; stability 8/14 (target 10, old 1/14); $1.64 + $0.6 in rounds 1–2 |
| 2 | Rendered A/B | Test 1's plans through today's generator, with the prompt cleanup. Two comparisons: with vs without 5 component tags (Header, KpiTile, TableCard, ChartCard, ReadoutPanel), and merged vs separate planning + XML call | ≈ $2 | new slides preferred in ≥ 70% of blind pairs; distinct card styles ≤ the golden's; 0 over-full tables. If the tag version doesn't win, skip the component layer | **dropped 2026-09-27 (user, D14)** — it tested the Test 1 planning path |
| 3 | Critic + editor | 10 edit requests + 10 critic findings: whole-slide rewrite vs element-level edit | ≈ $1 | ≥ 90% done correctly; nothing else on the slide changes; no number changes; ≥ 50% fewer tokens | **dropped 2026-09-27 (user, D14)** — it tested the Test 1 planning path |

**Test 1 deliverables (build PC):**
- fact-store and storyline schemas and prompts;
- an adapter from the new plan to today's generator input;
- the scorer: extend `scripts/eval_lineage.py` to read the new plan format and to count emphasis marks per slide. It already measures headlines kept, numbers dropped and invented per stage, decoration, style variety and plan stability across runs.
- the test PC must send back the run folders (`output/runs/<run_id>` zips), not only the eval bundle, because the scorer needs `slides.json`.

**Test 1 as built (2026-09-27, branch `test-1-planning`):**
- `src/planning/` — its own LangGraph graph; `src/graph.py` and `src/state.py` untouched:
  `index_brief` (code) → `plan_storyline` (LLM) ⇄ `check_storyline` (code, 1 retry) → `Send` × N → `design_slide` (LLM + `check_slide` inside, ≤ 2 re-asks) → `to_slide_plans` (code adapter to today's `SlidePlan`).
- Simplification vs §7.2 (agreed 2026-09-27): the fact store is built by code (`brief_index.py`: every line, pipe table and chart block gets an id; tables and charts are parsed and filled by code). The storyline call does the brief-understanding (`audience_and_use`, `deck_argument`, `gaps`, `style_directives` come first in its schema). A separate "understand brief" LLM call is added only if the storyline call struggles.
- Prompts: `src/prompts/storyline/`, `src/prompts/slide_designer/` (~700 tokens each, vs ~6k for the old slide planner's template). Models: `storyline` and `slide_designer` steps in `models.yaml` (gpt-4.1, temperature 0.1).
- Runner: `python -m scripts.plan_only gj-h1-regen gate-deck-cheffin-audit --repeat 3 --label test-1 --bundle` → `output/plans/test-1/<run>/` (`slides.json`, `storyline.json`, `storyline.md`, `run-manifest.json`), `summary.md` with the criteria, and a zip in `llm_test/`. `--rescore` re-scores saved runs without the LLM. `--storyline-retries` / `--slide-retries` (default 1 / 2) cap the re-asks. Cheapest first look (user, 2026-09-27): `python -m scripts.plan_only gate-deck-cheffin-audit --repeat 1 --storyline-retries 1 --slide-retries 1 --label cheffin-1 --bundle` (≈ $0.15). Stability needs ≥ 2 repeats.
- New case `gate-deck-cheffin-full` (user, 2026-09-27): the same CHEFFIN brief plus the full per-slide specs for slides 1-6 (the original prompt had 18; the paste stops after 6). The short case tests a thin brief (slides 2-6 left to the planner); the full one tests following a per-slide spec: its plan checks require the 6 brief headlines verbatim, the CPC table, the ad-type table and the match-type ROAS each in one component, and the brand colours. Slide headings like "SLIDE 2: Executive Summary" are now sections in the indexer and the scorer (gj-h1's evidence unchanged). A headline that points at a "Headline:" label line is flagged.
- Code review 2026-09-27 (independent reviewer), fixed: a failed first design call no longer beats every later real design; a failed call records its tokens; a failed storyline retry keeps the previous storyline, and a worse retry is discarded; parsed tables are always shown whole (the prompt offered a column subset that the coverage check then rejected); "1.0x" → "1" is not required on a slide; a headline cut short from its brief block is replaced by the whole block; chart units are also read from metric names (CVR/AOV/CPC…) and from the categories of a single-series chart; integral chart values stay ints; the scorer ignores numbers the brief uses only as years; all runs failing no longer crashes the summary.
- Scorer: `eval_lineage.py` reads plan-only runs (headlines and numbers from the plan), counts design hints per slide, and no longer counts component counts (`rows`, `items`) as numbers — §3.2 still reproduces exactly. Baseline for hints: today's plans reach 5–7 per slide, 6–9 slides over 2.
- LLM calls: 1 + N if every check passes (gj-h1: 15; today's planning: 17), plus one call per failed check.

**Test 1 round 1 (paid, 2026-09-27, one run per case, `docs/eval/test-1/round-1/`):**

| | old planner (§3.2) | round 1 | pass if | |
|---|---|---|---|---|
| gj-h1 headlines kept | 0/13 | 5/13 | ≥ 12 | fail |
| gj-h1 numbers dropped by planning | 7–13% | 16/362 (4.4%) | ≤ 2% | fail |
| invented numbers (3 cases) | 0–2 per deck + CHEFFIN's invented table / dates | 0 | 0 | pass |
| design hints per slide (max) | 5–7 | 2 | ≤ 2 | pass |
| CHEFFIN-full plan checks (6/6 brief headlines, CPC / ad-type / match-type in one component, colours) | — | all pass | pass | pass |
| CHEFFIN-audit plan checks | — | all pass; but the brief's "mention the data-quality note" was set aside and never shown | pass | partial |
| gj-h1 planning cost | $0.44, 17 calls | $0.29, 19 calls (2 storyline, 17 designs) | ≤ today | pass |

Causes (all in the Test 1 prompts/checks, fixed LLM-free the same day; a replay of the returned plans through the new checks flags exactly these):
1. Headlines: the prompt said both "copy the brief's headline" and "a headline is a conclusion, not a topic"; on 9 gj-h1 slides whose brief headline reads like a topic ("Six-Month Sales Trajectory") the model wrote its own conclusion. Now: the brief's wording wins; the model's conclusion goes to `so_what`.
2. Dropped numbers: `not_shown` excused data — on gj-h1 slides 1 and 6 KPI notes and read-out figures ("6.1% of H1 GMV", "424K orders") went there. Now `not_shown` never excuses data; dropping data is only a storyline `set_aside` decision.
3. Dropped requirement: blocks that ask for content ("Mention that…", "Include…") must be on a slide (storyline check). Slide counts ("a 14-slide deck") are not data.
Also fixed after round 1: chart units by the first metric word, header repeated inside a component, "on no slide" measure (whole brief). Pending: user's judgement of the CHEFFIN-audit headlines; round 2 = gj-h1 + CHEFFIN-audit once (≈ $0.45).

**Test 1 round 2 (paid, 2026-09-27, label `test-1b`, `--slide-retries 1`, `docs/eval/test-1/round-2/`):**
- gj-h1: **headlines 13/13** (pass, was 5/13); numbers dropped 10/362 = 2.8% (fail, was 4.4%); invented 0; hints ≤ 2; 21 calls, $0.32.
- All 10 dropped numbers are on slide 11 (five pillars): the model put each pillar's goal / moves / target in the `detail` of a **process_arrow**, which draws labels only. The check counted the detail as shown; the adapter (correctly) passed only labels on. Fixed LLM-free: details of label-only kinds (process_arrow, flow, pyramid, tree, matrix) no longer count as shown, and the slide is asked to put them in a table or bullets. Replay flags slide 11.
- CHEFFIN-audit: CPC-vs-allowable check **fails**: slide 2 was designed as two KPI rows of 7 tiles (one per platform); the capacity check flagged it, but with `--slide-retries 1` the one re-ask did not fix it. The data-quality note is now on slide 3 (round-1 fix works). Invented 0, all numbers placed, 10 calls, $0.10.
- Next: gj-h1 + CHEFFIN-audit once more with the default 2 slide retries, then the stability repeats.

**Pre-run review for the final Test 1 run (2026-09-27, independent reviewer + own checks; no blocker).** Fixed: an empty block id could crash a paid run (now skipped; any error in fill/check is recorded as an issue instead of failing the run); numbers in a component's `emphasis` (it becomes the design hint) are now checked for invention; the scorer uses the planner's own rule for what a slide must show (per section: years, slide counts and single-digit values after normalizing like "2.0x" are not required; gj-h1 denominator 362 → 354; rounds re-scored: round 1 4.2%, round 2 2.8% — unchanged verdicts); every storyline and slide attempt's issues are saved (`issue_log`); progress is logged while running; "on no slide" ignores "Slide N:" headings; the storyline prompt says preamble blocks are shared context and set-aside reasons must be honest. Final run: `python -m scripts.plan_only gj-h1-regen gate-deck-cheffin-audit --repeat 3 --label test-1-final --bundle` (≈ $1.3–1.6, worst case ≈ $3).

**Test 1 final run (paid, 2026-09-27, label `test-1-final`, gj-h1 × 3 + CHEFFIN-audit × 3, default retries, $1.64, `docs/eval/test-1/final/`).** The test PC ran the code before `1d750ca` (no `issue_log` in the output): the pre-run fixes to the emphasis check, crash guard and logs were not active; scoring used the current scorer.

| criterion | old planner | final run | pass if | verdict |
|---|---|---|---|---|
| gj-h1 headlines kept | 0/13 | 13/13 in all 3 runs | ≥ 12 | **pass** |
| gj-h1 numbers dropped | 7–13% | 0.0% / 0.6% / 2.5% (mean 1.0%) | ≤ 2% | **pass on the mean**, 2 of 3 runs individually |
| invented numbers | 0–2 + CHEFFIN's invented table / dates | 0 in all 6 runs | 0 | **pass** |
| design hints per slide | 5–7 | ≤ 2 | ≤ 2 | **pass** |
| same component kinds across 3 runs | 1/14 | 8/14 (9/14 if a text read-out as bullets vs narrative counts as the same) | ≥ 10/14 | **fail** |
| CHEFFIN plan checks | invented table, wrong CPC values, default palette | 3/3 runs pass | pass | **pass** |
| cost per gj-h1 plan | $0.44, 17 calls | $0.32–0.35, 21–22 calls | ≤ today | pass |

- The 2.5% run: slide 1 (the densest: 5 KPIs, chart, 3 platform cards, read-out) left out two platform-card tables (9 numbers) after 3 attempts; the check caught it every time, the model did not comply. The 0.6% run: one read-out line left in `not_shown` after 3 attempts.
- Where the plans differ between runs (stability): slide 11 (five pillars: KPI + table / process arrow + bullets / bullets + table), slide 7 (one card list vs three), slide 8 (timeline alone or with narrative / bullets), slide 10 (an extra KPI row), slide 1 (the dropped tables), slide 3 (read-out as bullets vs narrative). These are slides whose content has several valid forms; the fix candidates are code-picked defaults for parsed tables / charts and for recurring content shapes (pillars, cards, playbooks), or a storyline-level layout decision per parallel group — not more retries.
- CHEFFIN-audit headlines (user to judge): mostly conclusions ("CHEFFIN is spending at scale, but current traffic economics are structurally weak across both platforms"); weak ones: "Data context and methodology notes." (a topic), "Current performance issues are structural, not just campaign-level." (generic); no kicker labels when the brief gives none.

**CHEFFIN headlines vs the production deck (user asked for this comparison instead of a verdict, 2026-09-27).** On the 15 content slides each: equal length (11.9 vs 11.5 words); a tension in the headline ("X – but Y", "one symptom: Z") in 5/15 of ours vs 12/15 of production; production sub-headlines carry the evidence ("₹29.4L spend, ₹10.1L ad sales, 0.34x ROAS. CPC ~2.9× the allowable line"), ours describe the slide ("Platform-wise performance snapshot (last 90 days)"); production has a kicker on every slide, ours none. Ours are correct conclusions but generic — they restate the brief's diagnosis instead of sharpening it. Partly structural (production had 17 slides + data files; "2.9×" is a derived number, D13), mostly the storyline prompt. Carried forward to the build: headline = one claim with a tension, ≤ ~12 words, naming the entity; sub-headline = 2–4 key numbers from the slide's blocks (checked by code); a kicker on every slide; story patterns per deck type (audit: summary → snapshot → per-entity deep-dives → gaps with evidence + fix → approach → roadmap → next step); style examples from the gj-h1 golden headlines, not CHEFFIN's.

**Reference: the production CHEFFIN deck (read 2026-09-27; kept locally in `llm_test/`, not pushed — real client and platform names).** 17 slides built on the **gj-h1 template** from the brief plus the data files (a search-term CSV of ~18.8k rows, targeting report, campaign / city / keyword sheets). What it tells us:
- Same arc and header as our storyline: diagnosis → per-platform evidence → cross-platform synthesis → approach → 30-60-90 roadmap → ask; kicker label + claim headline + one-line sub-headline; two platform deep-dives on one layout (= `parallel_group`).
- Components beyond Test 2's five: status chips (SCALE / PROTECT / REVIEW / CAP), a gap panel (actual vs allowable), numbered pillars mapped to gaps, phased roadmap with exit criteria, a source line from the real data files on every slide.
- ~60% of its content needs the data files (search-term leakage, winners vs weak terms, month / campaign-class / match / city cuts). From the text brief our planner can only name that gap. **Data-file input (CSV / XLSX → fact tables + aggregates by code, M6) is central, not late.**
- It relies on **derived numbers** (ACOS = spend ÷ sales, shares, multiples, row counts and sums). Our check rejects any number not written in the brief; §7.7 already says "traceable to a fact or a formula" → derived facts computed and verified by code are needed.
- It states **targets / projections** ("≥ 0.9x in 90 days", "~₹8.7L / month redirected"). Under D2 ("never invent") the planner refuses these → open decision D12.
- It contradicts itself (the same platform CPC / CVR / AOV differ between slides 2 and 3; one CVR is called "lower" while it is higher) — the fact store's one-value-per-fact check would catch this.

---

## 10. Build milestones (after the tests)

These are provisional; reorder them by the test results.

| # | Milestone | Acceptance | Status |
|---|---|---|---|
| M1 | **Quality bar:** rubric + vision judge calibrated on ~50 slide pairs the user rates; the deterministic checks from §7.7 added to the eval | judge agrees with the user on ≥ 80% of pairs | not started |
| M2 | **Content layer:** fact store + storyline in the graph (replaces elicitor, outline planner, plan reviewer); invent policy; generator-prompt cleanup | every number traceable; ≥ 95% of must-have facts shown; ≥ 90% claim headlines on content slides; exact slide count — on the gate decks | not started |
| M3 | **Components + layouts** (if Test 2 passes): tags, templates, grid, density tiers, 2 design languages, gallery tests | gallery compiles and renders clean at declared limits; user sign-off | not started |
| M4 | **Measure + fit stage,** component-aware checks, merged slide-design call (if Test 2 favours it) | 0 overlap / overflow / minimum-font violations; nothing dropped silently; blind win rate vs today ≥ 75%; cost ≤ today | not started |
| M5 | **Critic + editor on elements** (critic on by default if affordable) | QA win rate ≥ 60%; QA ≤ $0.25 per deck; edit success ≥ 90% | not started |
| M6 | **Scale:** 20–40 slides, concurrency cap, per-slide work outside the recursion limit, timeouts, cost caps, CSV / XLSX input, brand themes | 50 runs of a 30-slide deck with no failure, within agreed time and cost | not started |

**Gate set for milestones (D9):** about 8 decks across deck types, mixing detailed, partial and vague briefs.
- From existing cases: `deck-qbr`, `pitch-deck`, `deck-product-launch`, `deck-board-update`, `project-status`, `deck-sales-enablement`, `gate-deck-cheffin-audit`, `gj-h1-regen`.
- New cases to add: a training deck and a proposal.

---

## 11. What stays, what goes

- **Stays:**
  - POM + `compile-pom.js` + `pptx-post.js`
  - normalizer and content model (the safety net for raw POM)
  - icon validation
  - eval runner / import / compare / renders
  - API and UI (outline editing becomes storyline editing)
  - LangGraph as the orchestrator
  - LLM-authored POM XML
- **Goes**, once the milestone that replaces it passes:
  - blueprints and `blueprint_selector.py` as mandates
  - archetypes A–E
  - the mandatory kicker, card shell and source line
  - the mandatory `design_hint`
  - the invent instructions
  - golden-example injection
  - the generator's long rulebook, replaced by the component catalog + short design principles
  - fit-grow's after-the-fact heuristics (its text measurement can move into the fit stage)
- **Reused as material:** `recipes.yaml` snippets for component templates; the golden decks as design references.

---

## 12. Decisions

| # | Decision | Options | Recommendation | Status |
|---|---|---|---|---|
| D1 | Who writes the slide markup | keep LLM-authored POM XML / replace with a JSON spec | keep (§3.2, §7) | recommended 2026-09-24 — user to confirm |
| D2 | Invented numbers in data decks | never / "illustrative" only when the brief has no data, labelled on the slide | never | **decided 2026-09-27 (user): never** — missing data is named as a gap |
| D3 | Density tiers and minimum font | presented 14–16 / pre-read ~10–11 / one floor for all | two tiers | open |
| D4 | Deck font | must exist on Office machines: Calibri / Arial / Aptos | — | open |
| D5 | Slide planning + XML writing | one call per slide / two calls as today | decide on Test 2 data | open |
| D6 | Component-tag layer | build / skip | decide on Test 2 data | open |
| D7 | Blueprints | demote to reference now (Test 2 cleanup) / keep until components land | demote now | open |
| D8 | Critic polish rules | per design language / as today (gj-h1 template) | per design language (M5) | open |
| D9 | Gate set and budget per milestone | ~8 decks, ≈ $3 per gate run | as proposed | open |
| D10 | Stronger model for the storyline stage only | yes / no / later | later, if Test 1 falls short | open |
| D11 | `docs/roadmap-derived-components.md` | continue / halt | — | **decided 2026-09-24 (user): halted** |
| D12 | Targets and projections (e.g. "ROAS ≥ 0.9x in 90 days") | never / allowed when labelled as target or projection and tied to the facts they start from | allowed, labelled | open (raised 2026-09-27 from the production CHEFFIN deck) |
| D13 | Derived numbers (ACOS = spend ÷ sales, shares, multiples, row aggregates) | only numbers written in the brief / computed by code from facts with the formula recorded | computed by code | open |
| D14 | Planning path after Test 1 | new path (storyline + slide designer) / existing planners + fixes + reviewer loop | — | **decided 2026-09-27 (user): existing planners + fidelity fixes + `plan_reviewer` as a feedback loop.** Reason: the new slide designer gave too few components on thin briefs (CHEFFIN 1.8 per slide vs 2.83 for the old planner; gj-h1 equal at 3.04). Tests 2 and 3 dropped |

---

## 13. Issues found during the review

These can be fixed independently of the plan above.

- **`invented_numbers` blind spot.** `scripts/eval_metrics.py` `invented_numbers` reads `el.text` but not `el.tail`, so numbers after an inline tag (`<B>ROAS</B> 99.9x`) are never checked. The metric therefore under-reports invented numbers. Reproduced 2026-09-24; a separate task was suggested in that session.
- **Critic vocabulary.** The visual critic's `affected_nodes` list includes names that aren't POM nodes (ZStack, KPI, Bullet, Divider, Spacer).
- **Archetypes.** `layout_archetypes` is never rendered, but picking one is mandatory (`generator/system.j2`, `generator/user.j2`, the regex in `deck_nodes.py`).
- **Concurrency.** `SLIDE_PLANNER_MAX_PARALLEL` and `MAX_CONCURRENCY` are declared but never applied, so a 20-slide deck fires 20 planner calls at once.
- **Plan reviewer.** Its output is ignored by routing: one LLM call per deck with no effect.
- **Recursion limit.** The graph's limit of 150 vs the per-slide steps of long decks with the critic on.

---

## 14. Session log

| Date | Session | What happened | Changes to this document |
|---|---|---|---|
| 2026-09-24 | Architecture review | Traced the flow (graphify map + code); rendered real generator prompts; audited the four saved gj-h1 runs + CHEFFIN against the golden; revised the recommendation to keep LLM-authored XML; defined Tests 1–3 | Created |
| 2026-09-24 | Follow-up | `AGENTS.md` "Next work" now points here and marks the roadmap halted; added `scripts/eval_lineage.py`, which reproduces §3.2 exactly; planned the `src/state.py` changes. Next: Test 1 in a new session | §3.1, §7.11, §9, §14, Appendix C |
| 2026-09-27 | Test 1 build | Built planning v2 (`src/planning/`, 2 prompts, `scripts/plan_only.py`, scorer support, 8 unit tests; 450 pass, same 4 pre-existing failures). Dry run with a scripted LLM on the real gj-h1 and CHEFFIN briefs: 14/14 headlines copied, 0/365 dropped, CHEFFIN checks pass, capacity check fires and re-asks. User decisions: D2 never; CHEFFIN checks in Test 1; the Genspark UI tracking (2026-09-25) is the reference for pre-writing reasoning. Next: paid run on the test PC | Status, §9, §12, §14 |
| 2026-09-27 | Direction change | Measured component counts old vs new (gj-h1 3.04 = 3.04; CHEFFIN 2.83 vs 1.80) and block-id hallucination (0 bad ids in 3,194 references; 7 false set-aside claims in one run). User: keep the existing planners, make `plan_reviewer` a feedback loop, drop Tests 2 and 3, pause. `AGENTS.md` rewritten for the new direction | Status, §9, §12 D14, §14 |
| 2026-09-27 | Test 1 final | Final paid run (gj-h1 × 3 + CHEFFIN-audit × 3, $1.64): 5 of 6 criteria pass, stability 8/14; user: **Test 1 passed, stability carried forward**; CHEFFIN headlines compared with the production deck (generic vs sharp; carried forward). Also: pre-run review fixes, `llm_test/` gitignored and untracked, production-deck notes, D12 / D13 | Status, §9 final + comparison, §12, §14 |
| 2026-09-27 | Test 1 round 1 | Paid runs (one each): CHEFFIN-full passes; CHEFFIN-audit passes its checks but dropped a "mention" requirement; gj-h1 fails headlines (5/13) and dropped numbers (4.4%) — better than the old planner on every measure, causes found in the Test 1 prompts/checks and fixed LLM-free (replay confirms). Also: independent code review, `gate-deck-cheffin-full` case, `.env` loading, retry flags. Next: round 2 (gj-h1 + CHEFFIN-audit × 1) | §9 round 1 |

---

## Appendix A — headlines: golden vs generated

Planned slide titles from `tables-check` (`gj-h1-regen-bf396b`). The other three runs show the same pattern.

| # | Golden headline | Generated title |
|---|---|---|
| 0 | H1 2026 (cover) | Q-Commerce H1 2026 Review |
| 1 | H1 at a glance — ₹44 Cr GMV · ₹13.78 Cr Ad Sales · 5.09x blended ROAS | H1 2026 Snapshot |
| 2 | Six-Month Sales Trajectory | Performance Trend |
| 3 | June performance snapshot | Executive Summary · June |
| 4 | Efficient on ROAS, softened on top-line | Platform Deep-Dive · Blinkit |
| 5 | Our efficiency engine — compounding since April | Platform Deep-Dive · Swiggy |
| 6 | Our volume engine — efficiency to be unlocked | Platform Deep-Dive · Zepto |
| 7 | Where each category earns its keep | Category Intelligence |
| 8 | Actions that moved the numbers | What Worked |
| 9 | Where efficiency is leaking | What Didn't Work · Leaks to Fix |
| 10 | Where & when spend earns most | Geo & Day-Part Intelligence |
| 11 | Five pillars for H2 scale-up | Way Forward · H2 2026 |
| 12 | H2 Tactical Roadmap | Operational Roadmap |
| 13 | To execute H2, we need four things | Ask from Brand · Support Needed |

The brief contains every golden headline verbatim. The outline planner replaced them with the section labels.

---

## Appendix B — planned component kinds per slide across runs

Title components are omitted. Planning prompts and code were identical in all four runs.

| # | baseline | phase-1 | phase-5-tables | tables-check |
|---|---|---|---|---|
| 0 | narrative | narrative | narrative ×2 | narrative ×2 |
| 1 | chart, kpi_row ×2, narrative, table | bullet_list ×3 | chart, kpi_row, narrative, table | bullet_list, chart, kpi_row ×2, table |
| 2 | bullet_list, chart | chart, narrative ×3 | bullet_list, caption, chart | chart, table |
| 3 | kpi_row, narrative, table ×2 | kpi_row, narrative, table | bullet_list, kpi_row, table | bullet_list, kpi_row, table |
| 4 | kpi_row, narrative ×6 | bullet_list, kpi_row, narrative, table ×2 | bullet_list, chart, kpi_row, table ×2 | chart, kpi_row, narrative, table ×2 |
| 5 | bullet_list, chart, kpi_row ×2, table ×2 | bullet_list, chart, kpi_row, table ×2 | bullet_list, chart, kpi_row, table ×2 | bullet_list, chart, kpi_row, table ×2 |
| 6 | bullet_list, chart, kpi_row, table ×2 | kpi_row, narrative, table ×2 | bullet_list, chart, kpi_row, table | bullet_list, chart, kpi_row, table |
| 7 | bullet_list, table | bullet_list, table | bullet_list, narrative, table | bullet_list, table |
| 8 | timeline | narrative, timeline | narrative, timeline | narrative, timeline |
| 9 | table | table | table | table |
| 10 | bullet_list, chart, narrative, table | bullet_list, chart, narrative, table | caption ×2, kpi_row ×2 | bullet_list ×3, chart, table |
| 11 | bullet_list, process_arrow | table | bullet_list | bullet_list |
| 12 | narrative, timeline | narrative, table, timeline | narrative, timeline | narrative, table, timeline |
| 13 | bullet_list, kpi_row | bullet_list, kpi_row, narrative | bullet_list, kpi_row, narrative | bullet_list, kpi_row, narrative |

---

## Appendix C — reproducing the evidence

- **Command.** This reproduces §3.2 and Appendix B:

  ```
  python -m scripts.eval_lineage llm_test/gj-h1-regen-69af33.zip llm_test/gj-h1-regen-7293ef.zip llm_test/gj-h1-regen-5a9e2d.zip llm_test/gj-h1-regen-bf396b.zip --case tests/cases/gj-h1-regen.yaml --ignore 01,02,03,04,05,26 --detail
  ```

  Run ids: `69af33` = baseline, `7293ef` = phase-1, `5a9e2d` = phase-5-tables, `bf396b` = tables-check. The golden column comes from the case's `golden:` field. Add `--json <file>` to save the numbers.
- **Bundles:**
  - The four gj-h1 runs: `llm_test/gj-h1-regen-{69af33,7293ef,5a9e2d,bf396b}.zip`. They are local only and untracked; back them up. Each has `slides.json` (per-slide plan + normalized XML) and `run-manifest.json` (per-call tokens and cost).
  - CHEFFIN: `llm_test/tables-check-20260924-204854.zip`. `results.json` has component kinds and hints per slide, but not `content_data`; the slide XML is under `slides/`.
- **Golden:** `tests/fixtures/golden/gj-h1-deck/*.xml`. Headline = the first `<Text>` with fontSize 26, 27, 28 or 42.
- **Numbers:** `scripts/eval_metrics._numbers` rules (≥ 2 digits, thousands separators dropped, trailing zeros ignored). The brief is split per slide on `Slide N:`. Section numbers and the year (`01`–`05`, `26`) are excluded. Text after inline tags must be read (`el.tail`).
- **Prompt rendering:** `build_contract(plan, resolve_theme(""))`, then `generator._render_prompts(state)`, on the plans in `slides.json`.
- **Blueprint replay:** `blueprint_selector.select_blueprint(plan)` on the same plans.
- **Planning unchanged across runs:** `git log ea80267..77000c3 -- <planning files listed in §3.1>` returns nothing.
