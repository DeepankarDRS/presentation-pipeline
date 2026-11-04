# Syntax audit: the composition tags judged side by side (2026-11-04)

Free work: no API calls, no LLM, `src/` untouched. Everything here re-runs with `python -m scripts.syntax_audit <command>`
(`catalogue`, `consistency`, `stress`, `tables`, `duplicates`, `atomic`, `flex`, `bisect`, `census`). Sheets, numbers and the full
catalogue are in [eval/syntax-audit/](eval/syntax-audit/).

The timeline is audited from `claude/left-blocks-build-0fe007` (53e74ca): the script loads its `sequences.py` and `nodes.timeline` from
git in its own process and merges nothing. process_arrow and flow are treated as dropped.

**Limits.** "Blank", "breaks" and "survives" are measured on hand-written tags and plans built for the test. No real LLM wrote any tag
here, so this audit cannot say how often the LLM would hit each case; the paid same-plan run is what measures that.
Automatic checks caught most breaks, and I read every sheet by eye on top; where only my eye found something, the text says so.

## Short answers to your questions

| Question | Answer |
|---|---|
| Is the syntax sound? | **The tag is: 15–27 tokens against 108–1,739 expanded, and no way to get a word wrong. The attribute layer is not.** 31% of attribute × composition pairs silently do nothing, and one allowed attribute can blank a KPI row with no error |
| Where does it break? | **Boxes narrow for the content** (28 of 30 cases at 280 px: `requires` counts items and never looks at the box), card `rail` / `steps` with many or long items, and attributes the expander writes twice |
| Should anything be introduced? | **No new structure: no slots, spans or item overrides.** Fix the attribute gate first. One optional addition: a parts escape for looks no composition reaches |
| Build atomically instead? | **No, keep composition as the default.** Atomic reaches the same looks but costs 30–51 × the output tokens, and swapped fields pass unseen. Keep element refs as the escape hatch for looks a composition cannot draw |
| Are we really using flexbox? | **Yes.** POM is Yoga, and the expanders use it well for boxes. Flexbox cannot size type, and that is most of what fit-grow does. The real savings are small |

## Most serious finding: an allowed attribute blanks the KPI text

`<KpiRow ref="kpis" variant="strip" alignItems="center"/>` compiles, reports no error, and draws an empty strip. The same happens to a KPI row on the
**same slide as** `<Table ref="gaps" variant="rows" gap="20"/>`: 12 of 12 KPI strings are gone, `node_ok` is true, and there are no codes
([duplicates.png](eval/syntax-audit/duplicates.png), [duplicates.json](eval/syntax-audit/duplicates.json)).

**Cause (traced).** Expanders write an attribute literally and then add the LLM's box attributes, e.g. `<HStack alignItems="stretch"{A(gbox)}>`
(`tile_groups.py:274`), so the attribute appears twice. POM's parser accepts that and the last value wins (measured: `gap="8" gap="40"` lays out at 40).
`tiles.fill` parses with lxml, gets a syntax error and returns the slide unfilled by design (`element_refs.py:155`), so every `<Text ref>` stays empty.

The attributes that do this are all on the allowed list. Full list per node in `consistency.json` → `duplicates`:

| Node | Compositions that write it twice | Attributes |
|---|---|---|
| kpi_row | strip, banded, bento | `alignItems`; bento also `item.justifyContent`, `item.w`; banded and bento also `icon.name` |
| chart | native, native labelled | `alignItems` |
| timeline | rail, columns, rows, banded | `gap`, plus `alignItems` / `justifyContent` / `item.gap` / `item.grow` / `item.padding` per composition |
| table | all but native | `gap`, plus `item.padding`, `item.gap`, `item.grow`, `item.w`, `band.padding` per composition |
| card_grid | none | built through lxml, so one value wins |

On the node's own slide the damage is a silently wrong value. **With a KPI row anywhere on the slide, its text disappears.**

This must be fixed before any paid run: a fixed slide would look like a generator failure.

## 1. Catalogue

[catalogue.md](eval/syntax-audit/catalogue.md) has, for all 39 variants: the plan JSON, the minimal tag, a styled tag, the tag with every allowed attribute,
the XML the real expander writes, and the atomic form. Each sheet has one row per variant and four columns: **tag · styled · every attribute · atomic form**.

[kpi_row](eval/syntax-audit/catalogue-kpi_row.png) · [card_grid](eval/syntax-audit/catalogue-card_grid.png) · [chart](eval/syntax-audit/catalogue-chart.png) ·
[timeline](eval/syntax-audit/catalogue-timeline.png) · [table](eval/syntax-audit/catalogue-table.png) · [bullets](eval/syntax-audit/catalogue-bullets.png) ·
[callout](eval/syntax-audit/catalogue-callout.png) · [header](eval/syntax-audit/catalogue-header.png)

**How the atomic form is made.** It is the expansion with code's peer ids and the `alignItems="stretch"` default removed: every typed word, size and colour stays.
So it is derived from the expansion, not typed by me (§5 has three really hand-written samples), and it is a floor on what an LLM must type for that look.

**bullets, callout and header have no expander.** Their tags are hypothetical and their XML is the 2026-10-27 proof's.

A worked example, KPI `rows`:

```xml
<!-- what the LLM writes: 17 tokens -->
<KpiRow ref="kpis" variant="rows" grow="1" />

<!-- what code writes: 748 tokens, 29 elements; the first of 4 rows -->
<VStack gap="0" padding.left="8" padding.right="8" grow="1">
  <HStack grow="1" gap="18" alignItems="center" padding.top="10" padding.bottom="10" id="card-kpis-0">
    <Icon name="trending-up" size="22" variant="square-filled" bgColor="$positiveSoft" color="$positiveText"/>
    <VStack gap="4" grow="1" id="card-kpisx-1"><Text color="$positiveText" fontSize="16" id="kpil-kpis-0">ARR</Text>
      <Text color="$positiveText" fontSize="16">+18% QoQ</Text></VStack>
    <Text color="$positiveText" textAlign="right" fontSize="28" bold="true" id="kpiv0-kpis-0">$48.2<Span fontSize="14">M</Span></Text>
  </HStack>...
```

Tokens (o200k_base), minimum to maximum across a node's variants. "Elements" is the number of XML elements, which is the line count when each sits on its own line.

| Node | Variants | Plan JSON | Tag | Styled tag | Every attribute | Expanded | Atomic form | Elements |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| kpi_row | 5 | 111 | 17–18 | 83 | 1,157 | 626–830 | 538–645 | 29–33 |
| card_grid | 9 | 289 | 16–17 | 62 | 1,427 | 826–1,312 | 751–1,170 | 43–60 |
| chart | 3 | 60 | 16–17 | 67 | 597 | 181–697 | 176–529 | 8–31 |
| timeline | 5 | 68 | 16–17 | 63 | 1,156 | 108–879 | 108–847 | 5–40 |
| table | 8 | 137 | 15–27 | 60 | 982 | 447–1,739 | 441–1,507 | 30–79 |
| bullets (no expander) | 5 | 113 | 9–14 | – | – | 154–605 | 154–573 | 8–24 |
| callout (no expander) | 2 | 22–30 | 8–9 | – | – | 65–101 | 65–101 | 2–4 |
| header (no expander) | 2 | 39 | 8–13 | – | – | 95–108 | 95–108 | 4 |

**What the ids buy.** Removing them changes KPI `grid` by 29% of pixels and table `banded` by 16%. KPI `grid` stays 4 across instead of regridding to 2 × 2, and table `grid` / `grid numbered` / `ledger`
rows end up in different type sizes ([table sheet](eval/syntax-audit/catalogue-table.png), right column). Ids are small in tokens and carry fit-grow's peer rule, so any atomic route needs code to write them (§5).

**What the every-attribute tag shows.** It fails to compile on 10 of 30 variants, on attributes the validator allows:

| Attribute on the tag | Where | Result |
|---|---|---|
| `gap`, `alignItems`, `justifyContent` | native `<Table>` and `<Timeline>` | `Unknown attribute` |
| `cellBorder.*` (`native_attributes`) | every table composition but native | `Unknown attribute "cellBorder"` on a VStack / HStack |
| `showLegend` | chart `rows` | `Unknown attribute "showLegend"` on a VStack |
| `stripe.color` and other text attributes | table `ledger` | `Unknown attribute "color"` and others (41 errors): `stripe.` is spread onto a box |

Each of these goes to a repair call and is not reported before compile.

## 2. Consistency against the planner JSON

**Tag and part names line up with plan keys, with these exceptions:**

| Plan key | Tag / part | Problem | Needed? |
|---|---|---|---|
| `kpi_deltas` | part `delta.`, but ref field `kpis.0.note` | one thing, two names on one node | no: use `delta` everywhere |
| `timeline_items[].label` | part `title.` (`label.` an alias) | breaks spec N3 (part = key), for POM's own word | decide: rename the plan key or the part; the alias costs little |
| `cards[].bullets` | text styled by `body.`; `bullets.` is a **box**, only in `columns` | `bullets.backgroundColor` does nothing on 8 of 9 compositions, and `bullets.color` is an error | no: `bullets.` should style the bullets |
| `cards[].key_phrase` | no part | its colour cannot be styled | fine: the phrase colour is code's |
| `table_rows[][0]` | `label.` | `label.` means the first column here, a KPI's label there, and chart labels elsewhere | acceptable: each is "the row's name" |
| `chart_type`, `chart_title` | code-owned; `title.` | fine | – |
| bullets / callout / header | `<Ul>` in `blocks`, `<BulletList>` in spec §8; `<Callout>` in `spec.py`, `<Narrative>` in spec §8; `<SlideHeader>` vs `<Title>` | three nodes have two tag names each | settle if built |

**Same idea, different name:**

| Idea | Names today | Suggestion |
|---|---|---|
| layout hint | `cols` (kpi, card), `direction` (chart, timeline), none (table) | fine: different questions |
| per-item icon override | `icon` (kpi, card; one value), `icons` (table; a comma list) | fine, but `icons` works only on `ledger` and is silently ignored elsewhere |
| restyle one item | item tags `<Kpi>` / `<Card>`, `<Highlight>` (table), nothing (chart, timeline) | two mechanisms for one idea; see §4 |
| the emphasis | `focus_card` (card), hint words (kpi, table, timeline), headline / latest period / hint (chart) | fine as code's, but the rule differs per node and the prompt doesn't say which |
| fill | `backgroundColor` (boxes), `fill.color` (`bar.`, `marker.`, `connector.`) | unavoidable: POM's Shape vs box. The prompt must keep saying which part is which |
| tone tokens | `$tone*` resolve on kpi and card, on table as the accent only, and **stay literal on chart and timeline** | see below |
| composition words | `rail` = vertical numbered line (card) but horizontal dots with text above and below (timeline); `columns` = pill + boxes (card, table) but dot + box (timeline) | breaks spec §2.3 ("a word keeps its meaning") |

**`$tone*` fails on chart and timeline.** `<Chart bar.fill.color="$tone"/>` and `<Timeline marker.fill.color="$tone"/>` end in a compile error: `Unknown theme token "$tone"` (stress case `tone`). The prompt for kpi and cards teaches these tokens, so an LLM can carry them across.

**Silent no-ops.** Each allowed attribute was tried alone on every composition and looked for in the expansion ([reach.json](eval/syntax-audit/reach.json)): **1,601 of 5,091 pairs (31%) reach nothing, with no report.**

| Node | Pairs | No effect | Examples |
|---|---:|---:|---|
| kpi_row | 860 | 25% | `band.*` outside `banded`; `divider.*` on `grid`; `value.bold`; `item.borderRadius` on `grid` (code's square) |
| card_grid | 1,899 | 36% | `band.*`, `bullets.*` on most; `number.*` outside numbered; `tag.*` on `columns` |
| chart | 264 | 27% | `label.*`, `value.*`, `bar.*` on `native` |
| timeline | 860 | 37% | `date.bold` and all text styling on `native`; `item.*`, `band.*` on `rail` |
| table | 1,208 | 25% | `band.*`, `number.*`; `stripe.*` outside native and ledger |

Part of this is by design (a part the composition doesn't draw), and `marker.*` needs `marker.shapeType` first, so the test overstates it slightly. But your rule is that styling freedom stays with the LLM, and today it cannot tell a style that worked from one that vanished.

One more silent loss: `Text` allows `highlight`, and the normalizer strips it (`_HIGHLIGHT_ATTR_RE`), so `delta.highlight` reaches the expansion and never the slide.

**Aliases.** In the 33 saved tile-tag slides: `CardGrid layout=` 13 times, `KpiGrid layout=` 6, `cols` 15, `variant="inverted"` twice, and `<KpiGrid>` 12 times. So only 2 of 37 group tags named a variant, and all of them wrote old names. Aliases are needed for replaying saved slides and for nothing else; the spec's rule (remove after one paid run shows zero) holds. **Whether the LLM picks a variant at all is still unmeasured**, and that is the largest open risk in the design.

**Two sources for prompt lines.** kpi and card keep theirs in `nodes.<kind>.prompts`, while chart, timeline and table read `blocks.<kind>.variants`. Move them to `nodes`.

## 3. Stress cases

300 rendered slides: 115 pass, 103 warn, 82 break by the automatic checks (words lost, overlap, broken words, spill, compile, node errors). Node-level cases ran on two variants per node. Table with causes: [stress-table.md](eval/syntax-audit/stress-table.md).

Sheets: [kpi_row](eval/syntax-audit/stress-kpi_row.png) ([node](eval/syntax-audit/stress-kpi_row-node.png)) · [card_grid](eval/syntax-audit/stress-card_grid.png) ([node](eval/syntax-audit/stress-card_grid-node.png)) · [chart](eval/syntax-audit/stress-chart.png) ([node](eval/syntax-audit/stress-chart-node.png)) · [timeline](eval/syntax-audit/stress-timeline.png) ([node](eval/syntax-audit/stress-timeline-node.png)) · [table](eval/syntax-audit/stress-table.png) ([node](eval/syntax-audit/stress-table-node.png))

✓ pass, ~ warn (mostly `GEOM_CARD_EMPTY`), ✗ break. Empty cells were not run.

| Node | Variant | one | sparse | many | long | odd | narrow | short | side | nested | mixed | missing | invented | ref-in-ref | item | tone | dark |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kpi_row | grid | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| | strip | ~ | ~ | ~ | ~ | ✓ | ✗ | ~ | | | | | | | | | |
| | rows | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| | banded | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ | | | | | | | | | |
| | bento | ~ | ~ | ~ | ~ | ✓ | ✗ | ~ | | | | | | | | | |
| card_grid | grid | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✓ | ✓ | ✓ |
| | grid numbered | ~ | ✓ | ~ | ✓ | ~ | ✗ | ~ | | | | | | | | | |
| | rows | ✓ | ~ | ~ | ✗ | ✓ | ✗ | ✓ | | | | | | | | | |
| | rows numbered | ~ | ~ | ~ | ✗ | ~ | ✗ | ~ | | | | | | | | | |
| | columns | ✗ | ~ | ~ | ✗ | ✗ | ✗ | ✗ | | | | | | | | | |
| | banded | ✓ | ~ | ~ | ✓ | ✓ | ✗ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✓ | ✓ | ✓ |
| | bento | ~ | ~ | ~ | ✓ | ✗ | ✗ | ✗ | | | | | | | | | |
| | steps | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ~ | | | | | | | | | |
| | rail | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | | | | | | | | | |
| chart | native | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| | native labelled | ✓ | ✓ | ~ | ✓ | ✓ | ~ | ~ | | | | | | | | | |
| | rows | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| timeline | native | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ~ | | | | | | | | | |
| | rail | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ~ | ~ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ |
| | columns | ~ | ~ | ~ | ~ | ~ | ✗ | ~ | ✗ | ✗ | ~ | ~ | ✗ | ✗ | ~ | ✗ | ~ |
| | rows | ✓ | ~ | ✓ | ✓ | ~ | ✗ | ~ | | | | | | | | | |
| | banded | ~ | ~ | ~ | ✗ | ~ | ✗ | ~ | | | | | | | | | |
| table | native | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| | rows | ✓ | ~ | ✓ | ✓ | ~ | ✗ | ~ | | | | | | | | | |
| | rows numbered | ✓ | ~ | ✓ | ✓ | ~ | ✗ | ~ | | | | | | | | | |
| | columns | ✗ | ✗ | ~ | ✗ | ~ | ✗ | ✗ | | | | | | | | | |
| | banded | ✗ | ✗ | ~ | ✗ | ✓ | ✗ | ✗ | | | | | | | | | |
| | grid | ~ | ~ | ~ | ~ | ~ | ✗ | ~ | | | | | | | | | |
| | grid numbered | ~ | ~ | ~ | ~ | ~ | ✗ | ~ | | | | | | | | | |
| | ledger | ~ | ~ | ~ | ~ | ~ | ✗ | ~ | ~ | ~ | ✓ | ~ | ✗ | ✗ | ✓ | ✓ | ✓ |

Breaks by case: narrow 28, invented 10, ref-in-ref 10, long 7, short 5, missing 4, tone 4, one 3, odd 3, many 2, sparse 2, nested 2, side 1, mixed 1. The invented and ref-in-ref cases were planted, so their breaks are the expected error or a known gap.

### Causes

| Case | What happens | Cause | Severity |
|---|---|---|---|
| **narrow** (280 px beside a note) | 28 of 30 break, with letter-stacked or overlapping text; **strip, KPI banded, card columns, bento and steps fail to compile** (`addTextBox: width must be a finite positive EMU value`) | `requires` checks counts only; no composition knows its box. Yoga has no min-content width, so columns shrink to nothing (flex test `squeeze`) | **high** |
| **card rail** (odd, long, many, short) | text overlaps and spills past the slide; even the sample of 4 full cards spills (`GEOM_SPILL`) | rail stacks 4+ full cards down the slide; its only `requires` is the layout | **high**: needs a cap, or a rule on bullets |
| **card steps, many** | 9 cards in one row, letter-stacked | no count cap (`rows`, `columns`, `banded` have one) | medium |
| **words dropped by design** | card `columns` and small `bento` cards drop the `tag`; table `columns` / `banded` drop the first column's name | composition doesn't draw the part. **It breaks "every word, verbatim"** (14 of the breaks outside narrow) | your call |
| **tone** on chart, timeline | no compile, as §2 | `$tone*` resolved only in `tile_groups` and `tables` | high |
| **missing** | KPI: a label with no value is dropped with **no report**. Chart: an error, then repair. Timeline and cards with empty items: an empty box, no report | checks differ per node | medium |
| **mixed units** on native chart | "₹31.2L", "2.8x", "41%" on one axis, every unit gone | `number_format` gives "General" and `requires` has no one-unit check. `rows` keeps each value verbatim, so it reads, but its bars still compare unlike things | medium |
| **ref-in-ref** | inner KPI: an error naming `<KpiGrid>`. Inner chart or table: **lost with only a report** | known (§13.3): `validate.check_skeleton` not wired | high |
| **invented** | error → repair, though the slide is right | known (§13.3) | medium |
| **item** on chart, timeline | `<ChartDataPoint>` / `<TimelineItem>` children dropped with a report | no item form there | low, see §4 |
| **dark** | passes; the native chart stays a white block on a dark slide (by design, POM's black axis) | known | low |

### Found by eye (the checks passed)

- **Native timeline text is very small** on a full slide, in every case, and native is what a bare tag picks for short labels. Its size is fixed by POM, and fit-grow cannot change it.
- **Empty cards.** Timeline `columns` and `banded`, and card `banded` with sparse text, leave the lower half or more empty; `one` and `sparse` show it most. This is your "grow the type" rule failing. I did not trace why growth stops here.
- **Peers out of line.** KPI `banded` and `strip` put one-line and two-line labels in the same row, so the values do not line up. `strip` still decides the icon per tile (spec §6 finding 1, open as R5).
- **Uneven grid tiles.** KPI `grid` with long values or an odd count draws unequal widths in a row (content width plus a share), because no `w` is set.
- **A style that doesn't travel.** My styled tag `title.color="$toneText"` is fine on `grid` and **invisible on `columns` and `banded`**, where it sits on a `$tone` band. The same holds for `label.color` on table bands. `LOW_CONTRAST` reports it, and this follows your no-auto-coupling rule, so the choice is yours: the prompt could say which parts sit on bands.
- **Rail, rows and table `long`:** close line spacing where a long head wraps.

Where the syntax holds: `one`, `odd`, `sparse`, `dark`, `side` and `nested` on KPI `grid` / `rows`, card `grid` / `banded`, chart `rows` and table `native` / `rows`; `many` falls back correctly on KPI `strip` / `banded` and on most card and table compositions.

## 4. Should we introduce something?

Checked against the stress cases, [composition-test](eval/composition-test/README.md) (table of data needs), [genspark-variants](eval/genspark-variants/summary.md), and spec §7 / §11.

**Fixes that come first (no new syntax):**

| # | Change | Evidence |
|---|---|---|
| F1 | One merge helper: an LLM attribute replaces the expander's literal, never adds a second | the blank KPI row; 70 attribute × composition pairs write twice |
| F2 | Filter per composition before the XML is written: an attribute this composition doesn't draw → `NODE_ATTR_NO_EFFECT` (report). Native tags pass only what POM accepts | 1,601 silent no-ops; 10 of 30 variants fail compile on allowed attributes |
| F3 | Parse check in `tiles.fill`: a syntax error is an error, not "the normalizer reports it" (it doesn't) | the blank KPI row reports nothing |
| F4 | `$tone*` either resolve to `accent` on chart and timeline, or drop with a report | compile failure |
| F5 | Remove `highlight` from `part_nodes.Text` (the normalizer strips it) | `delta.highlight` has no effect |

**Applied 2026-11-04 (free, no API calls).** Render of the two formerly blank slides: [fixed-blank-kpi.png](eval/syntax-audit/fixed-blank-kpi.png).

| # | How | Measured after |
|---|---|---|
| F1 | `validate.one_value`: one pass after the expanders and before any lxml parse; the last value wins, as in POM. The expanders' f-strings are untouched | both blank slides: 0 words lost |
| F2 | `ignores` / `draws_only` per composition in `block-variants.yaml`, applied by `compose.undrawn` to the LLM's attributes only. An item placed apart keeps its own box attributes | every-attribute tag compiles on all 29 compositions (10 failed before); of 4,839 attribute × composition pairs, 0 are silent |
| F3 | `element_refs.fill_refs`: `NODE_XML_INVALID` (error, goes to repair) when the slide has KPI content or a `<Text ref>` | unit tests |
| F4 | `compose.no_item_tones`: `$tone*` on chart and timeline → accent, reported | all four tokens compile on both nodes |
| F5 | `highlight` moved from the allowed Text attributes to `dropped.parts` (a report, not a repair) | unit tests |

Bare and lightly styled tags are unchanged: 102 expansions identical to the commit before. Unit tests: 2,035 pass, the same 4 known failures (+29 in `tests/unit/test_attribute_layer.py`).

**Corrections to this report's measure.** The reach check first looked for the value in quotes, so it missed `bar.fill.color` in `chartColors` JSON; it also tested `marker.*` without a `shapeType`, and counted plans that fell back to another composition. Measured properly on this branch's nodes, 1,502 of 4,839 pairs (31%) do not reach the XML, the same share as the 1,601 of 5,091 above. The per-attribute lists in `reach.json` predate this and use the other branch's timeline.

**Open from this fix.**
- `ignores` for `timeline` describe this branch's node. `claude/left-blocks-build-0fe007` renames parts and adds `columns`, so re-measure that node's list when it merges, and add the two `compose` calls to its `draw` if the merge drops them.
- "Reaches the XML" is not "changes the picture": an attribute can reach the XML and still look the same.
- `POM_BLOCKS=tiles` without `POM_NODES` (the older tile route in `tiles.py` and `cards.py`) is not filtered. It gets F1, F3 and F5, not F2.

**Candidates for new syntax:**

| Candidate | Evidence | Verdict |
|---|---|---|
| Slots (`<Card ref><slot .../></Card>`) | no case needs it: an LLM card around a ref holds (probe d1, `nested`) | **not needed** |
| Spans (true bento) | no plan field; `<Card ref w="34%"/>` apart already gives uneven widths | **not needed now** |
| Item overrides for chart / timeline | `item` case: no way to mark one point. But the emphasis already comes from the plan, and table has `<Highlight>` | **wait**: if the paid run shows the need, reuse `<Highlight>` rather than add tags |
| Space-aware fallback (not syntax) | 28 of 30 narrow breaks; 5 compile failures | **yes, top need.** Fit-grow can measure the box and pick the fallback, as `regridTiles` already re-lays out |
| Parts escape (`<Text ref="levers.0.title"/>` on every node) | Looks no composition reaches, rendered in [atomic.png](eval/syntax-audit/atomic.png), right column: the KPI delta as a pill beside the value (Genspark KPI-E, spec §11.1, still "find"), a card as title · body · bullets · tag pill, the date inside a large marker | **optional.** Exists for KPI, about 70 lines of prototype for cards and timeline. Only if you want those looks |
| Per-row / per-column icons on table | composition test rows 2–3; `icons` works only on `ledger` | **small, optional**: extend `icons` to `rows` and `grid`, or say in the prompt that it's ledger only |

**The pill.** Spec §11.1 asked whether POM can draw a pill from Text attributes alone. **No**: `highlight` is stripped and a Text has no box, so it needs a box part or the escape.

Nothing is needed for odd counts, per-item KPI and card styling, nesting, or dark themes: those already work.

## 5. Atomic vs composition

Three nodes built as small parts the LLM assembles, each part drawn from the plan by ref. KPI uses the real `fill_refs`. Card and timeline refs (`<Text ref="levers.0.title"/>`, `<Ul ref="levers.0.bullets"/>`, `<Icon ref="levers.0.icon"/>`, `<Text ref="roadmap.0.date"/>`) **don't exist**: a prototype of about 70 lines in the script (`atomic_fill`) stands in, writing the same ids the expanders write.

**The limit of this comparison:** I wrote the atomic XML by hand, correctly, knowing the target. An LLM would make mistakes I didn't, so atomic's risk and its look quality are both best cases here.

[atomic.png](eval/syntax-audit/atomic.png): composition · atomic, same look · atomic, a new look.

| | Composition | Atomic |
|---|---|---|
| Output tokens, KPI rows | **17** | 513 (30 ×) |
| Output tokens, card banded | **17** | 783 (46 ×) |
| Output tokens, timeline rail | **16** | 814 (51 ×), and the LLM must get the half-unit grid right |
| Same look reachable? | yes | **yes**: 1–2% of pixels differ, 0% on the rail. The card lost the key-phrase colour (the LLM would have to write spans) |
| Looks a composition can't reach | no | **yes**: 3 rendered, all compile and pass |
| Fit-grow and the fixes | all | **survive if code writes the ids**: same growth (76 px, 2.73 ×), peers equal, regrid and guards work. Without ids, peers split (§1) |
| Type sizes across peers | code's | code's where refs are used. Boxes, padding and part order are the LLM's, per item |
| Prompt, fixed part | 1,826 tokens for 5 nodes (compositions, parts, recipes) | 286 for the grammar, **but it teaches no looks**: an equal-quality prompt needs a look library, not measured |
| Prompt, per component | 51–209 tokens | same |

**What the validator sees, with mistakes planted** ([atomic.json](eval/syntax-audit/atomic.json)):

| Mistake | Caught? | Possible under composition? |
|---|---|---|
| item left out; index past the plan; same ref twice; word typed instead of a ref | **yes** (`NODE_ITEM_MISSING`, `NODE_REF_*`) | no |
| **value ↔ delta swapped on an item** | **no** | no |
| **values of two items swapped (the $48.2M under the wrong label)** | **no** | no |
| **title ↔ tag swapped; card order changed** | **no** | no |
| **body or bullets forgotten on one card** | **no** (the prototype checks items only; KPI `note` has a check that a real fill could copy) | no |
| one peer styled apart | **no** | only if the LLM does it on an item tag |

Swaps are the serious ones: a number under the wrong label is a wrong slide that passes every check. The validator could check "every field placed" and part order in peers, but no check can tell that a value under a label is the right pair when the refs inside one box are all legal, except comparing indices within a box, which would forbid some free layouts.

**Evidence from the KPI element-ref arm** ([same-plan](eval/tile-nodes/same-plan/README.md), paid 2026-10-14, 12 plans): generator output 683–1,619 tokens with refs vs 192–1,124 with tile tags; cost −26% for tags; 0 values off the plan both ways; larger numbers with tags in 7 of 12, smaller in 3. Blind marks: tags 0, refs 3, same 9 (0.375). Two of the three losses were layout bugs fixed afterwards; the third was "the LLM decorating its own tiles more". So with refs the LLM did sometimes draw livelier tiles, at more output. Later free gates passed on compositions (kpi_row, card_grid 0.949, chart 0.868, timeline 0.739, table 0.97), but those drew bare tags with no LLM.

**Recommendation: a hybrid, with composition as the rule.**

| Where | Use | Why |
|---|---|---|
| table, chart, timeline | **composition only** | atomic would be 800–1,700 tokens and has real geometry (rail units, bar lengths, the highlight rules) |
| KPI, cards, default | **composition** | 17 tokens, no swaps, peers alike |
| KPI, cards, a look no composition draws | **parts escape, opt-in** | KPI element refs already exist. Extend to cards only if you want those looks, with the "every field placed" check. Allow only when the plan's hint asks for something the variants can't do, and count how often the LLM takes it in the paid run: if it takes it everywhere, the savings are gone |
| bullets, callout, header | see decision 8 | gains are small on two of them |

## 6. Flexbox audit

**POM's engine is Yoga (Facebook's flexbox) for every box** (`calcYogaLayout.js`, `registry/definitions/stack.js`). Tested with POM's own layout on small slides ([flex-probes.png](eval/syntax-audit/flex-probes.png); numbers in [flex.json](eval/syntax-audit/flex.json)):

| Feature | POM | Measured | Used by code / LLM |
|---|---|---|---|
| `gap`, `padding`, `grow`, `justifyContent`, `alignItems` | yes | as CSS. **`alignItems` defaults to stretch**, so writing it does nothing | heavily |
| Equal columns | **automatic**: HStack children with no `w` get basis 0, grow 1 | `equal_no_w` = `w="1" grow="1"` to the pixel (393 / 394 / 393) | code writes `w="1"` 166 times across 30 expansions; redundant in an HStack, tested there |
| `w="max"` | `flexGrow: 1` **on the parent's main axis** | in a VStack it grows the **height** (367 of 400 px); `h="max"` in an HStack grows the **width** | the LLM wrote `w="max"` 309 times; fit-grow's `respectHeights` exists to undo the ballooning |
| Content width, no growth | `w="max" grow="0"` works on a stack | 30, 123 px. **`grow="0"` on a Text is rejected**; with no `w` a stack collapses to 0 | unused |
| Equal rows | `h="1" grow="1"` | 160 / 160 / 160 vs `grow="1"` alone 111 / 258 / 111; **but text overflows a full row** | unused |
| `flexWrap` | yes | wraps at `minW`, last line widens | LLM 0 uses; code only `wrapChipRows` |
| `alignContent` | **not exposed** | **wrapped lines stay at the top: 23 px tall in a 500 px box** | verified limit |
| `minW`, `maxW`, `minH`, `maxH` | yes | `minW` holds while siblings shrink | LLM minW 1, maxW / maxH 0; code minW 4 |
| Min-content width | **no** (Yoga default) | a 60 px column breaks "Internationalisation" | verified limit: why the word guard exists |
| Shrink | all stack children but icons | over-tall slides crush boxes below their text | verified: why `fixSpills` exists |
| `position="absolute"` in a stack | yes | anchored to its parent (`top` / `right`) | 0 uses; a ref can't take children, so it doesn't help layers |
| Negative margin | yes | 40 px overlap | unused |
| Percent width | yes | of the parent's content box | code 67, LLM 136 |
| Column alignment across sibling rows | **impossible** | content leads 67 / 174 / 61 px: no grid in flexbox | verified limit: why rows use `w="24%"` |
| Sizing type to a box | **impossible** | a 500 px box, its type unchanged | verified limit: fit-grow's main job |
| `Table`, `Chart`, `Timeline` | not flex inside | fixed rows, fixed node type | `RIGID` in fit-grow |

**Census** of stacks, by attribute (first LLM output of paid runs; code = the 30 catalogue expansions):

| | Free LLM XML | KPI refs | Tile / card tags | Code |
|---|---:|---:|---:|---:|
| Slides / stacks | 104 / 1,428 | 30 / 389 | 33 / 172 | 30 / 513 |
| `gap` | 1,308 | 389 | 159 | 321 |
| `grow` | 165 (12%) | 38 (10%) | 42 (24%) | **365 (71%)** |
| `alignItems` (of them stretch) | 711 (279) | 159 (89) | 101 (76) | 162 (51) |
| `justifyContent` | 489 | 156 | 13 | 119 |
| `w` px / % / max / share `1` / none | 146 / 136 / 309 / 0 / 837 | 31 / 80 / 85 / 0 / 193 | 33 / 0 / 6 / 0 / 133 | 30 / 67 / 2 / 166 / 248 |
| `h` px | 147 | 30 | 33 | **0** |
| `minW` + `minH` | 34 | 3 | 12 | 6 |
| `alignSelf` | 68 | 100 | 0 | 3 |
| `flexWrap`, `maxW`, `maxH`, absolute | 0 | 0 | 0 | 0 |

The px rows include each slide's root (`w="1280" h="720"`). Saved slides are from older prompts, so the free column is the better read of LLM habit. Code never hardcodes a height, and that part is good flexbox.

**Literal sizes in expander source**, per file (`census.json`): `tiles` 1 px / 1 %, `cards` 3 / 1, `tile_groups` 3 / 5, `charts` 2 / 2, `tables` 7 / 3, `sequences` 4 / 1. Most are one of:
- lead columns for numbers and dates (`w="72"`, `"64"`, `"150"`);
- first columns (`22%`, `24%`, `34%`) and value columns (`16%`), which must be shared across rows.

**fit-grow, 2,874 lines, 23 phase calls:**

| Phases | Could flexbox do it? |
|---|---|
| `growText`, `growStats`, `growStatSides`, `evenStats`, `evenTableParts`, `oneLineValues`, `reserveWrap`, `sizeDiagramWords`, `fitTableText` | **no**: type. Verified limit |
| `guardWords`, `fixSpills` | **no**: no min-content, and shrink crushes. Verified limit |
| `fitTables`, `sizeTables`, `growDiagrams`, `splitLists` | **no**: rigid nodes |
| `regridTiles`, `regridCards` | **no**: wrap can't stretch lines (`wrap_stretch`), and the decision is "do numbers grow 15% more", which needs measured type |
| `shareHeight`, `fillLoneRows` | **partly**: the `grow` they write is flexbox, but when to write it needs a measure. An expander could write `grow` on its row where it knows |
| `centreBody` | **yes**: a band with `grow="1" justifyContent="center"` is **pixel-identical** to the margin it computes |
| `respectHeights`, `wrapChipRows` | they repair LLM flex: `w="max"` ballooning, tags in a row. They write flex attributes, so a prompt line on the `w="max"` trap might cut them |

**Before and after, through the full pipeline** ([flex-before-after.png](eval/syntax-audit/flex-before-after.png); edits on real expansions in the script, `src/` untouched):

| Change | Result | Verdict |
|---|---|---|
| Drop `w="1"` and `alignItems="stretch"` from a KPI grid | **0.0% of pixels differ**, −2% tokens, regrid intact | Safe on this slide; **replay before adopting**. Tidiness only: low priority |
| `centreBody` → flex | **0.0%** | Works; small gain, simple case only |
| Equal rows: `h="1" grow="1"` on card rows | rows equal, but **peers split: sizes 20–48 px on the slide (before: 25–34), row 1 small and row 2 large** | **Rejected**: worse under your rule, today's stays |
| The same on table grid rows | long row still taller after the spill fix; type smaller | **Rejected** |
| Chart rows: value column `w="16%"` → content-sized | values 66 → 75 px, labels 20 → 23 px here, but **bar tracks differ when value widths differ**, and a bar's length is a share of its track, so **the chart would misstate the data** (`rows_cols_align`) | **Rejected as written. Better:** code computes that shared share from the longest value string (not rendered) |
| `band.minH` to line up KPI bands | no fixed value works: type grows afterwards | **Rejected**: flexbox can't align across siblings. A fit-grow step that sets peer bands to the tallest would do it (not built) |

**So:** we do use flexbox, for boxes, and well: 71% of code's stacks use `grow`, and no fixed heights. fit-grow isn't doing flexbox's job: nearly all of it is type, which flexbox cannot do. Two real improvements come out of this: teach the `w="max"` axis trap in the prompt, and let code size shared columns from their content. Removing redundant attributes is cosmetic.

## 7. Decisions for you, ranked

1. **Fix the attribute layer before any paid run (F1–F5).** *Done 2026-11-04, see §4.*
2. **Narrow boxes.** *Part done 2026-11-04:* fit-grow phase `reflowNarrow` gives a row of code-drawn items fewer columns when a word cannot fit even at the guard's floor (`POM_FIT_REFLOW=0` turns it off). The 30 narrow cases: compile 25 → 30; verdicts BREAK 28 → 24, WARN 2 → 6; four KPI compositions go BREAK → WARN ([narrow-after.png](eval/syntax-audit/narrow-after.png)). `long`: no verdict changed. `many`: card `steps` BREAK → PASS, nothing worse. The break map's short `steps` point moved from 7 to 12 cards (re-measured, 12 is the top of the sweep). *Still breaking:* every table composition, card and timeline `rows`, timeline `columns`, and `rail`. Cards now keep whole words but overlap or spill: four full cards do not fit the height of that box in any layout. A stacked `steps` card keeps its right arrow. *Still open: should a composition switch to another one when its box is narrow?* That needs a Python change, since fit-grow runs after the tag is expanded. How often real slides get a box this narrow is not measured.
3. **Keep composition as the default, element refs as an opt-in escape.** *Recommend: yes. Not atomic: 30–51 × the tokens and swapped values pass unseen.*
4. **Caps and defaults.** Card `rail`: cap it (or ban it with bullets on 4+ cards). Card `steps`: at most 6. Timeline bare tag: start at `rail`, not `native`, whose type is fixed and tiny. *Recommend: all three.*
5. **Words dropped by design.** Card `columns` and small `bento` drop `tag`; table `columns` and `banded` drop the first column's name. Does "every word" hold here? *Recommend: draw them, or say in the prompt the part is omitted; your call.*
6. **Empty cards in timeline `columns` / `banded` and sparse cards.** I did not find why growth stops. *Recommend: trace it as its own small task, since it's your rule.*
7. **Names.** `note` → `delta`; `bullets.` should style bullets; timeline's `rail` and `columns` mean something else than on cards; prompts all in `nodes`. *Recommend: fix `note` and `bullets.` now; rename the timeline words before the prompt reaches the paid run.*
8. **Undecided nodes.** *Recommend: callout and header stay LLM-drawn: 65–108 tokens is little to save, one item leaves no composition, and the header is the LLM's voice. Bullets: run the free replay first (66 of 142 saved lists split, 154–605 tokens); `rows` and `grid` are the cases.*
9. **The look-parts question.** Do you want the pill, the side-by-side card and date-in-marker looks? If yes, that decides the escape in 3 for cards and timeline. *Recommend: decide from the right column of [atomic.png](eval/syntax-audit/atomic.png).*
10. **Flexbox tidying** (`w="1"`, stretch, `centreBody`). *Recommend: later, after a replay. A prompt line on the `w="max"` axis trap is the one piece worth doing soon.*

**After these,** the paid same-plan run (`scripts/composition_paid.py`) answers what this audit can't: does the LLM pick variants at all? In saved tile-tag slides only 2 of 37 group tags named one.
