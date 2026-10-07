# Palette quality: what to add to `palettes.yaml` — research (2026-10-06)

**Status:** research only. Nothing in this document is built. It extends D1 in
`docs/derived-blocks-planning-2026-10-06.md` §1a (decided 2026-10-05), which already adds derived
text-colour roles and a contrast test in step 1. Read that first; this note says what D1 leaves out
and why it matters for how decks look.

**The question:** which colour terms should each palette carry, beyond today's 12 tokens, to raise
the visual quality of the decks the pipeline produces?

**Short answer:** D1 covers the *text-on-fill* problem (`onAccent`, `onDark`, `panelInk`,
`accentOnDark`). Four more things move quality, and none is in D1:

1. **Tints** (`accentSoft`, `positiveSoft`, …): row highlights, delta chips, badges, callouts. Today
   these are hard-coded hex values copied from examples, so they ignore the deck's palette.
2. **Text-safe variants** of accent and status colours (`accentText`, `warningText`, …): several
   palettes' accent, warning or negative colour fails as small text on the palette's own surface.
3. **A `neutral` grey and chart roles**: the "grey out everything except the one series that
   matters" technique has no colour to draw with, and chart series are not separable by lightness.
4. **A per-element role table**: nothing today says which token colours the hero fill, the delta
   chip, the highlighted row or the ghost numeral.

Plus fixes to existing palettes (role collisions, `gj-h1` warning, one duplicated default).

---

## 1. How a palette reaches the slide today

| Step | File | What happens |
|---|---|---|
| Library | `src/knowledge/theme/palettes.yaml` | 18 palettes, 10 colour tokens each plus `chartColors`; dark palettes add `chartSurface` / `chartInk` |
| Resolve | `src/agents/style_resolver.py` | `_TOKEN_KEYS` (12 names) become one `<Theme .../>` element; `corporate-slate` (or no name) returns a **hard-coded `DEFAULT_THEME`**, not the YAML entry |
| Prompt | `context_builder.py` → `generator.py` | The `<Theme>` element, `chartColors` and role text (`house-style.yaml` `color_roles`, `design-language.yaml` `color_usage`) go into the generator prompt |
| Compile | POM | `$token` references resolve against the `<Theme>`; chart colours are literal hex (`$tokens` do not resolve in `chartColors`) |
| Checks | `layout_audit.py` `LOW_CONTRAST` (report-only), `normalizer.py` highlight darkening | Contrast is measured against fixed colours (white, or `(22,32,46)` for dark), not the slide's own theme or gradient |

Three structural facts follow:

- **The LLM can only use colours the Theme gives it.** When a recipe needs a pale tint it has none,
  so it copies a literal. A palette that lacks a role does not get a worse version of that role; it
  gets a different deck's colour.
- **`style_packs.yaml` has roles the palettes lack** (`dark`, `onAccent`, `accent2`-on-dark,
  `panel`, a whole `colors_dark` set). D1 moves those into `palettes.yaml` by derivation.
- **Two sources already disagree.** `DEFAULT_THEME` in `style_resolver.py` lists chart colours
  `2563EB 0EA5E9 10B981 F59E0B EF4444 8B5CF6` while the YAML `corporate-slate` lists
  `2563EB 0EA5E9 14B8A6 6366F1 F59E0B`, and only the default carries `chartSurface`/`chartInk`
  for a light palette. The default palette is the one used when a brief names no colours.

## 2. Evidence from our own decks

| Symptom | Where recorded | Colour cause |
|---|---|---|
| Orange labels and headline phrases faint on white/cream | `docs/planner-redesign-research.md` R2; layout-batch run `1b306e1de67f` | `saascolor` accent 2.44:1, `navy-orange` 2.28:1 used as small text |
| QBR cover title dark on the dark cover; highlighted card turned light with light text | `docs/derived-nodes-design.md` §14.3b finding 3 | recolouring by swapping tokens; no text colour per background role (D1 point 2 fixes) |
| `LOW_CONTRAST` false alarm on gradient covers | `docs/eval/genspark-ref/README.md`; `docs/worklog-2026-09-30-to-10-04.md` | audit measures against `#FFFFFF`; no palette-level gradient or dark-hero colour to measure against |
| "A brief with no colours falls back to the default theme, so different briefs share one look" | `docs/derived-nodes-design.md` §14.3b finding 4 | few palettes with a distinct, recognisable identity; D1 point 5 (`look`) addresses the choice |
| Generic look versus Genspark decks | `AGENTS.md`, `docs/eval/genspark-variants/summary.md` | single accent used flat; no tints, no emphasis colour, no grey-out of non-focus data |
| Chart axis text black on dark slides | `components/chart.yaml` | POM hard-codes it; only workaround is a light `chartSurface` card |

### Hard-coded colours in the knowledge files

These teach the LLM by example, so every literal is a colour it will copy onto a deck with a
different palette:

| File | Literal colour attributes | Most common |
|---|---|---|
| `knowledge/core/recipes.yaml` | 60 | `FFFFFF` ×18, `2563EB` ×6, `15803D` ×5, `60A5FA` ×4 |
| `knowledge/core/blueprints.yaml` | 23 | `E0F2EC` ×12 (a mint tint from the gj-h1 deck) |
| `knowledge/core/golden-examples.yaml` | 16 | `F1C7D2` ×4 (a pink tint) |
| `prompts/**/*.j2` | 7 | repairer and generator system prompts |

Two concrete cases in `recipes.yaml`: the `badge` recipe uses `fill.color="DCFCE7" color="15803D"`
(a green pill that is correct on `corporate-slate` and wrong on `claude-cream` or `navy-orange`), and
the `callout` recipe uses `backgroundColor="EEF2FD"` (a blue wash on every palette).

## 3. Audit of the 18 palettes (measured 2026-10-06)

Contrast ratios are WCAG relative-luminance ratios, computed from the hex values in `palettes.yaml`.
Targets: 4.5:1 for small text, 3.0:1 for large text and graphics.

### 3.1 Findings

| # | Finding | Palettes | Why it matters |
|---|---|---|---|
| A1 | **White text on the accent fill fails 4.5:1** | `saascolor` 2.59, `navy-orange` 2.28, `emerald-clean` 3.77, `amber-mono` 3.81, `claude-cream` 4.07; dark palettes: `graphite-dark` 2.54, `midnight-indigo` 2.98, `forest-dark` 1.74, `carbon-dark` 2.26 | any accent-filled chip, step number or button needs a computed `onAccent` (D1 has it) |
| A2 | **Accent fails 4.5:1 as small text on surface** | `navy-orange` 2.28 and `saascolor` 2.44 (both also below the file's own 3.0 target), `emerald-clean` 3.46, `claude-cream` 3.50, `amber-mono` 3.52, `teal-slate` 4.37, `sky-minimal` 4.42 | eyebrows, kickers, delta labels; D1 does **not** cover accent-as-text |
| A3 | **Accent text on its own tint is worse than on surface** (accent on a 12% accent tint) | `navy-orange` 1.89, `saascolor` 2.32, `emerald-clean` 3.25, `amber-mono` 3.33 | the exact use of a highlighted-row or badge: coloured text on a pale fill |
| A4 | **Two roles share one colour** | `gj-h1` and `forest-editorial` and `forest-dark`: accent = positive; `saascolor`, `navy-orange`: negative = warning | breaks `house-style.yaml` rule "never give one meaning two colours"; a "watch" figure reads as a loss |
| A5 | **Status colours under 4.5:1 as small text on surface** | `gj-h1` warning `F59E0B` 1.95 and negative `E54D2E` 3.51 (the bad ones); marginal at 4.06–4.48: `claude-cream` warning and positive, `teal-slate` warning and positive, `forest-editorial` warning, `warm-editorial` warning and positive, `rose-report` warning, `emerald-clean` / `sky-minimal` / `violet-modern` negative | `gj-h1` copies the golden deck's colours as-is; amber as text is unreadable |
| A6 | **Positive and negative have almost the same lightness** | 11 of 18 are under 1.3:1; `corporate-slate`, `sky-minimal`, `violet-modern` and `graphite-mono` are at 1.04. Only `forest-editorial`, `saascolor`, `gj-h1` and the four dark palettes reach 1.3 | about 1 in 12 men cannot separate red from green; with equal lightness the two are indistinguishable. Deltas must also carry an arrow or sign |
| A7 | **Chart series are not separable by lightness** | nearest pair of series differs by ratio 1.0–1.3 in every palette (`graphite-mono` 1.00, `claude-cream` 1.02) | in greyscale print, on a projector or for colour-blind viewers two series look the same; direct labels are the only fix |
| A8 | **No grey for "everything else"** | all | the standard emphasis technique (one coloured series or bar, the rest grey) has no token; the LLM invents a grey that clashes with the palette's warm or cool ink |
| A9 | **Dark palettes use `textMain` on accent** at 1.6–2.6:1 | all four | same cause as A1: the right text colour on an accent fill is a computed pairing, not `textMain` |

### 3.2 What is fine

Body text (`textMain`, `textMuted`) passes in every palette: `textMain` ≥ 11.6:1 and `textMuted`
≥ 4.68:1 on `surface`. Dark-palette status colours (`positive`, `negative`, `warning`) are 6.5–10.7:1.
The retune of 2026-09-29 (`docs/frontend-redesign-changes.md`) did its job on text.

## 4. What good token systems do

| Source | Idea | What we take |
|---|---|---|
| Material 3 ([colour roles](https://developer.android.com/design/ui/wear/guides/styles/color/roles-tokens)) | Every fill role has a paired `on-` text role (`primary` / `on-primary`, `primary-container` / `on-primary-container`); a *container* is the pale tint of an accent; surfaces come in graded levels; roles are generated from a seed colour via tonal palettes (5 palettes × 13 tones, 29 roles) | Pair every fill with its text colour; add a **container (soft) tint** per accent and status; derive rather than hand-pick |
| Radix Colors ([12-step scale](https://radix-ui.com/colors/docs/palette-composition/understanding-the-scale)) | Each step has one job: 1–2 backgrounds, 3–5 component fills, 6–8 borders, **9 solid fill**, 10 hover, **11 low-contrast text, 12 high-contrast text** | The accent needs a **text step (11)** distinct from the **fill step (9)**; tints (3) and a hairline (6) are separate steps, not the same colour |
| Okabe-Ito palette and data-viz guidance ([summary](https://datavizs25.classes.andrewheiss.com/resource/colors.html)) | Categorical colours must differ in hue *and* lightness; ≤ 7–8 categories; never rely on red versus green alone; sequential data uses one hue from light to dark | `chartColors` ordered so adjacent series differ in lightness; a sequential **ramp** from the accent; red/green status always paired with an arrow or sign |
| 60-30-10 rule for presentations ([Ethos3](https://ethos3.com/color-rules-for-presentation-design/)) | ~60% dominant (background), ~30% secondary (cards, supporting colour), ~10% accent that draws the eye | The accent must stay rare; a `neutral` grey lets the other 90% recede so the 10% reads |
| Anthropic published styling ([skills.sh brand-guidelines](https://www.skills.sh/anthropics/skills/brand-guidelines), [palette summary](https://www.designpieces.com/palette/claude-color-palette-hex-and-rgb/)) | Ink `141413`, ivory `FAF9F5` / `F0EEE6`, greys `E8E6DC` `B0AEA5` `87867F`; three accents: clay `D97757`, blue `6A9BCC`, green `788C5D`; Poppins / Lora | A brand palette is **one dominant accent plus two supporting accents** with a named neutral ramp, and its accents are too light as text (2.5–3.2:1 on cream), which confirms the need for text-safe variants |

## 5. Recommendation

Split the work by who supplies each colour. **Authored** colours are chosen by a person per palette
(few, because each one is a judgement). **Derived** colours are computed by code from the authored
ones, by a rule that guarantees contrast. D1 already commits to derivation; this extends the list.

### 5.1 Fix existing palettes (small, no new tokens)

| Fix | Palettes | Change |
|---|---|---|
| Separate roles that share a colour (A4) | `gj-h1`, `forest-editorial`, `forest-dark`: give `positive` a green distinct from `accent` (or accept and document); `saascolor`, `navy-orange`: give `warning` an amber distinct from `negative` | one hex each |
| Status colours readable as text (A5) | `gj-h1`: darken `warning` and `negative`, keep the original as `*Soft`-adjacent fill | two hexes |
| One default (§1) | `style_resolver.py` | build `DEFAULT_THEME` from the YAML entry so chart colours and chart tokens cannot drift |
| Light palettes get `chartSurface` / `chartInk` explicitly or the prompt stops referring to them for light mode | all light | verify what `$chartSurface` resolves to on a light palette before choosing |

### 5.2 Derived tokens (extends D1; computed in `src/compiler/blocks/` by D1's rule)

D1 already derives `panelInk`, `darkFill`, `onDark`, `onAccent`, `accentOnDark`. Add:

| Token | Rule | Used for |
|---|---|---|
| `accentSoft`, `positiveSoft`, `negativeSoft`, `warningSoft` | mix of `surfaceAlt` with the colour at about 12–14% (22% on dark palettes) | highlighted table row / `cell_fill`, delta chip, badge, callout background, selected card |
| `accentText`, `positiveText`, `negativeText`, `warningText` | the colour, lightness reduced (hue kept) until ≥ 4.5:1 on `surface`, `surfaceAlt` **and** its own `*Soft`; if already passing, unchanged. On dark palettes lighten instead | eyebrow, kicker, delta text, highlighted number inside a tint |
| `hairline` | `border` already; add `borderStrong` = `border` mixed 35% toward `textMuted` | table rules, ghost numerals, card outlines that must survive a projector |
| `ramp1`…`ramp5` | accent mixed into `surfaceAlt` at 10 / 25 / 50 / 75 / 100% | heat cells, progress bars, matrix intensity, ghost numerals (`ramp2`) |

Rules the derivation must follow: darken in a hue-preserving space (OKLCH or HSL lightness), never by
mixing toward the ink colour; my prototype mixed toward `textMain` and turned orange into mud
(`F7941D` → `845C2E`), so the real implementation needs a lightness step, not a mix. Each `*Text`
is the colour a designer would hand-pick (orange → burnt orange `C25E00`-ish, not brown).

### 5.3 Authored tokens (new, optional per palette, with defaults)

| Token | Default if absent | Why it cannot be derived |
|---|---|---|
| `neutral` | `textMain` mixed 18–25% into `surface` (≈ `C8CECC` on `gj-h1`) | a designer may want a warm or cool grey that matches the ink; drives grey-out in charts and "no change" deltas |
| `info` | a blue chosen to differ from `accent` by hue ≥ 60° | the `badge` recipe has an `info` variant and no colour for it; blue is the conventional fourth status |
| `heroFrom` / `heroTo` | `darkFill` flat, no gradient | gradient covers are in every reference deck; a declared pair lets the audit measure text against it (fixes the `LOW_CONTRAST` false alarm) |
| `chartColors` | unchanged, but ordered by rule below | already authored; needs a quality rule, not a new token |

### 5.4 `chartColors` rules (A7)

1. First colour = `accent` (already true in all 18 palettes; keep it as a test).
2. Adjacent series differ by at least 1.4:1 in lightness (today's best is 1.31, worst 1.00).
3. At most six series; the planner already limits charts, make the palette limit explicit.
4. Add a `chartFocus` convention: the focus series takes `accent`, all others take `neutral`.
5. Charts on dark slides keep the `chartSurface` card (POM's black axis text is unfixable).
6. A unit test fails any palette whose `chartColors` break rules 1–3.

### 5.5 Colour-blind rule (A6)

Keep `positive` / `negative` as authored, but require every delta, status or good/bad mark to carry
a non-colour cue (▲ ▼, +/−, an icon). The planner and recipes largely do this already; make it a
checked rule, and add a palette test that the two colours differ in lightness by at least 1.3:1
(11 of 18 fail it today; see A6).

## 6. Which colour goes on which element

The table the code and prompts should share. A token in **bold** is new in this note; `(D1)` marks
a token D1 already derives.

| Element | Fill / background | Text | Border / mark |
|---|---|---|---|
| Slide background | `surface` | `textMain` | none |
| Card, KPI tile, table body | `surfaceAlt` | `textMain` (values), `textMuted` (labels) | `border` hairline; never accent on all four sides |
| Eyebrow / kicker | none | **`accentText`** | optional `accent` dot or short rule |
| Headline | none | `textMain`; emphasised phrase `accent` or **`accentText`** | optional `accent` bar under it |
| Body paragraph | none | `textMain` | none |
| Caption, source line, footer | none | `textMuted` | none |
| KPI value | `surfaceAlt` | `textMain` | `accent` top or left edge on the hero tile only |
| Delta text | none | **`positiveText`** / **`negativeText`** / `textMuted` for flat | arrow glyph in the same colour |
| Delta chip / badge | **`positiveSoft`** / **`negativeSoft`** / **`warningSoft`** / **`accentSoft`** | matching **`*Text`** | none |
| Table header | `surfaceAlt` (light) or `darkFill` (D1) | `textMain` or `onDark` (D1) | `borderStrong` under it |
| Table highlighted row | **`accentSoft`** | `textMain`; the key cell **`accentText`** bold | none (borders on `<Td>` are rejected by POM) |
| Table total row | `surface` | `textMain` bold | **`borderStrong`** above |
| Callout / narrative strip | **`accentSoft`** | `panelInk` (D1) | `accent` left edge, 5 px |
| Hero / inverted panel | `darkFill` (D1) or **`heroFrom`→`heroTo`** | `onDark` (D1); label `accentOnDark` (D1) | none |
| Accent-filled chip, step number | `accent` | `onAccent` (D1) | none |
| Chart, focus series | `accent` | axis text black (POM) on a light card | none |
| Chart, other series | **`neutral`**, then `accentAlt`, rest of `chartColors` | direct label `textMuted` | none |
| Matrix / heat cell | **`ramp1`…`ramp5`** | `panelInk` or `onAccent` by the cell's contrast | none |
| Process step, timeline marker | `accent` filled, upcoming steps `border` | step number `onAccent` (D1) | connector `borderStrong` |
| Ghost numeral (01 / 02) | none | **`ramp2`** | none |
| Icon | none | `accent` (decorative) or `textMuted` | none |
| Status dot | `positive` / `negative` / `warning` / `neutral` | none | none |

## 7. Worked example (prototype rule, 2026-10-06)

Derived with the §5.2 rules, using a simple mix for tints and a lightness search for text variants.
Ratios are measured. Values marked "approx" show where the real implementation, using lightness
instead of mixing toward ink, would give a cleaner hue than this prototype.

| Palette | Token | Today | Derived | Ratio / note |
|---|---|---|---|---|
| `navy-orange` | accent text on white | `F7941D` 2.28:1 | burnt orange (approx `C25E00`) | ≥ 4.5:1 on surface and on `accentSoft` `F4E6D2` |
| | onAccent | white 2.28:1 | `112340` | 6.9:1 |
| | warning | same as negative `A84531` | needs its own amber | A4 |
| `saascolor` | accent text | `F5821F` 2.44:1 | burnt orange (approx `B85A10`) | ≥ 4.5:1 |
| | onAccent | white 2.59:1 | `041E42` | 6.4:1 |
| `gj-h1` | warningText | `F59E0B` 1.95:1 | dark amber (approx `906513`) | ≥ 4.5:1 on `warningSoft` `FEF1DD` |
| | negativeText | `E54D2E` 3.51:1 | `B1422A` | ≥ 4.5:1 on `negativeSoft` `FBE6E2` |
| | accentSoft | none (hard-coded `E0F2EC` in blueprints) | `DDEAE6` | accent `0D6B4E` on it 5.4:1 |
| | neutral | none | `C8CECC` | graphic only |
| `claude-cream` | accentText | `C4623F` 3.50:1 | `A15236` | ≥ 4.5:1 |
| | onAccent | white 4.07:1 | `141413` | 4.5:1 |
| | accentSoft | none | `F7E9E4` | textMain on it 15.9:1 |
| `graphite-dark` | accentSoft | none | `2D456C` | text variant `80B7FB` 4.5:1+ |

## 8. How this fits the build order

| Step (from D1 / §14.6) | Change |
|---|---|
| Step 1 (role tokens + contrast test) | add the §5.2 derived tokens next to D1's; extend the contrast test to every (`*Text`, `*Soft`) and (`on*`, fill) pair; add the §5.4 chart rules and §5.5 lightness check as palette unit tests |
| Step 1 | replace literal hex in `recipes.yaml`, `blueprints.yaml`, `golden-examples.yaml` and the three `.j2` prompts with tokens; add a test that fails on a new literal colour attribute outside `chartColors` |
| Step 1 | build `DEFAULT_THEME` from the YAML (§1) |
| Before step 3 | fix the palettes in §5.1 (done together with the test, so the test passes) |
| Step 2 (`look` field) | list palettes with a `tone` line; add the authored `neutral` / `info` / `heroFrom` / `heroTo` to the palettes the picker offers first |
| Step 3 (paid comparison) | no extra paid run; the check below is LLM-free |

**Cost:** unit tests and a prompt-text edit; nothing paid. Roughly one day on top of D1's step 1,
mostly the literal-colour replacement.

**Prompt size:** the `<Theme>` element goes from 12 to about 30 attributes. Expose to the LLM only the
tokens its recipes use (about 10 new: the four `*Soft`, the four `*Text`, `neutral`, `borderStrong`).
Keep `ramp*`, `heroFrom` / `heroTo` and derived `on*` tokens for code-drawn blocks.

## 9. How to know it worked

LLM-free, on the saved run folders and the six step-0 cases:

| Metric | Today | Target |
|---|---|---|
| Colour attributes in final XML that are literal hex and not in the deck's palette | not measured (the badge and callout recipes force it) | 0 outside `chartColors` |
| `LOW_CONTRAST` findings per deck (existing audit, extended to measure against the slide's own fill and gradient) | recorded per run in `layout_codes` | 0 on all 18 palettes |
| Palettes failing the §5 unit tests | 16 of 18 fail at least one of A1, A2, A4, A5, A9 (only `corporate-slate` and `graphite-mono` pass); 18 of 18 fail the chart lightness rule (A7); 11 of 18 fail the colour-blind check (A6). A1/A2/A5/A9 are fixed by derived tokens, not by editing the palette | 0 after the derived tokens and the §5.1 palette fixes |
| Delta / status marks with colour but no glyph | not measured | 0 |
| Chart series pairs closer than 1.4:1 in lightness | every palette | 0 |

Judged by eye: the 1a blind sheet (`docs/derived-blocks-planning-2026-10-06.md` §4) already shows both
arms in one palette; add one row of badge, callout and highlighted-row slides on `navy-orange` and
`claude-cream`, where today's literals are most wrong.

## 10. Open decisions

| # | Decision | Recommendation |
|---|---|---|
| P1 | Add the §5.2 tokens to D1's step 1, or keep D1 as written and add them as step 1b | add to step 1; they share the derivation function and the contrast test |
| P2 | Authored `neutral` / `info` / `heroFrom` / `heroTo`: required or optional with defaults | optional with defaults, so existing palettes keep working |
| P3 | Fix A4 / A5 palette collisions now or after step 3 | now; they are one hex each and change deck output, so do them before the paid comparison, not during it |
| P4 | Keep `claude-cream` (clay as the single accent) or give it the brand's blue and green as `accentAlt` / a third chart colour | add them; the brand is one dominant accent plus two supporting ones, and the blue gives charts a second hue that is not red-adjacent |
| P5 | Expose all new tokens to the LLM, or only those its recipes use | only those its recipes use (§8) |

## 11. Risks

- **Token count in the prompt.** More tokens means more chances to misuse one; limit to the ones a
  recipe names, and test the prompt on the six cases.
- **Muddy derived colours.** Mixing toward ink turns saturated accents brown; the implementation
  must change lightness in a perceptual space and the unit test must also check hue drift.
- **Tints on dark palettes.** A 22% mix reads as a dim slab on some surfaces; the dark ramp needs an
  eye check, not only a ratio.
- **Over-reading a screenshot or a brand page.** The Anthropic values come from a skill listing and a
  palette site, not Anthropic's own brand page; treat them as a reference palette, not a spec.
- **Contrast is necessary, not sufficient.** Passing 4.5:1 does not make a slide look designed;
  the quality gain here comes mainly from tints, grey-out and one-accent discipline (§4), which a
  ratio test cannot see.

## 12. Sources

- Material 3 colour roles and tokens: [Android developer guide](https://developer.android.com/design/ui/wear/guides/styles/color/roles-tokens), [Flutter `ColorScheme`](https://api.flutter.dev/flutter/material/ColorScheme-class.html)
- Radix Colors, understanding the scale: [radix-ui.com](https://radix-ui.com/colors/docs/palette-composition/understanding-the-scale)
- Okabe-Ito and categorical / sequential / diverging guidance: [Andrew Heiss, colour palettes](https://datavizs25.classes.andrewheiss.com/resource/colors.html), [Aimpoint Digital](https://www.aimpointdigital.com/blog/color-best-practices-in-data-visualization)
- 60-30-10 for presentations: [Ethos3](https://ethos3.com/color-rules-for-presentation-design/), [Prezi](https://prezi.com/blog/designer-tips-volume-2-common-color-mistakes-and-the-60-30-10-rule/)
- Anthropic published styling: [skills.sh brand-guidelines](https://www.skills.sh/anthropics/skills/brand-guidelines), [designpieces Claude palette](https://www.designpieces.com/palette/claude-color-palette-hex-and-rgb/)
- Internal: `docs/derived-blocks-planning-2026-10-06.md` §1a (D1), `docs/planner-redesign-research.md` R2, `docs/derived-nodes-design.md` §14.3b and §14.8, `docs/frontend-redesign-changes.md`, `src/knowledge/theme/palettes.yaml`, `src/agents/style_resolver.py`, `src/knowledge/core/recipes.yaml`

## 13. Built: slide-quality item 1 (2026-10-07, branch `feat/slide-quality`)

User decisions (2026-10-07): build the colour roles for today's route (the LLM writes the whole slide);
**P1** derived tokens built now, in the pipeline (not tied to derived blocks); **P2** `neutral` optional
with a default; **P3** palette fixes now; **P5** only role tokens reach the LLM (`ramp*`, `borderStrong`,
`hero*`, `info` not built).

| Part | What |
|---|---|
| `src/compiler/palette_tokens.py` | derives `accentSoft` / `positiveSoft` / `negativeSoft` / `warningSoft` (13% mix into `surfaceAlt`, 22% dark), `*Text` (HLS lightness step, hue kept, ≥ 4.5:1 on `surface`, `surfaceAlt` and its own Soft), `onAccent` (white, else the palette ink), `neutral` (authored, else `textMain` 22% into `surface`, 32% dark) |
| `src/agents/style_resolver.py` | every `<Theme>` carries the 10 derived tokens; a light palette gets `chartSurface` / `chartInk` = `surfaceAlt` / `textMain`; `DEFAULT_THEME` is built from the YAML entry (default chart colours now the YAML's 5); `chart_focus` = literal accent + neutral hex for a focus chart (prompt note in `context_builder`) |
| `palettes.yaml` (P3) | `gj-h1` positive `2E7D32`, negative `B83A22`, warning `A15C00`; `forest-editorial` positive `1F6F5C`; `forest-dark` positive `5EEAD4`; `saascolor`, `navy-orange` warning `8A6A00` |
| Roles (`house-style.yaml` `color_roles`, `hint-capabilities.yaml`) | good / bad / watch = `*Text` text, `*Soft` fill, base colour for dots / bars; ONE focus item = `$accentSoft` + `$accentText`; the rest `$neutral` / `$textMuted`; new treatment `focus` on kpi_row, table, card_grid, timeline, flow, process_arrow; every good / bad mark carries a sign or arrow |
| Literal hex removed | recipes, blueprints, golden examples, component files, prompts: ≈ 200 → 0 outside `chartColors`, a black shadow, `<Theme>` and "wrong" examples (`tests/unit/test_literal_colors.py` fails on a new one) |
| Audit | `LITERAL_COLOR` (report only, in `REPORT_ONLY_CODES`, never reaches the critic) |

LLM-free checks (this PC): all 18 palettes pass contrast, hue and distinct-role tests
(`tests/unit/test_palette_tokens.py`); unit tests 787 pass, the 4 known failures; the 43 saved step-0 slides
recompile 43/43 with the new `<Theme>`; `python -m scripts.palette_preview` (now drawing the shipped tokens)
checked by eye on `navy-orange`, `gj-h1`, `claude-cream`, `graphite-dark`: tints follow the palette, the focus
series stands out from grey, the dark highlighted row is readable (before: white row, invisible text).
Generator contract +≈ 490 tokens per slide (+5%; budgets in `test_context_builder.py` raised).
Baseline for the paid check: step-0 LLM output has **117 literal colours on 18 of 43 slides**; target 0.
Not done: chart lightness rule (§5.4), colour-blind lightness check (§5.5).
