# Frontend redesign and palette retune — change log (2026-09-29)

Two pieces of work:

1. **Visual redesign of the Angular UI.** Visual only: component logic, signals, service calls and the `GenerateRequest` payload are unchanged. No logo upload or output options were added, because the backend doesn't support them.
2. **Palette retune.** Nine light palettes in `palettes.yaml` got more distinct colors, which changes real deck output. Palette IDs are unchanged.

Verification: `npm run build --prefix frontend` builds cleanly. `pytest tests/unit -q` gives 442 passed and 4 failed; the 4 failures are the ones already listed in `AGENTS.md`. `graphify update .` was run.

---

## Design system

### `frontend/tailwind.config.js`
- Adds a `brand` color scale from 50 to 900; the primary is `brand-600` = `#1E6FE8`.
- Adds `fontFamily.sans` = Inter, with system-font fallbacks.
- Adds two shadows: `shadow-soft` for cards and `shadow-lift` for the slide preview.

### `frontend/src/index.html`
- Page title is now "Presentation Pipeline".
- Loads the Inter font from Google Fonts, weights 400 to 700.

### `frontend/src/styles.css`
Adds shared classes in `@layer components`, so templates no longer repeat long Tailwind class strings:

| Class | Use |
|---|---|
| `.card` | White rounded panel with a border and soft shadow |
| `.section-title`, `.section-hint`, `.field-label`, `.divider` | Section headings, hints, field labels and separators |
| `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-success` | Buttons |
| `.icon-btn` | Small square icon button (outline editor actions) |
| `.input` | Text inputs and textareas, with a brand focus ring |
| `.option-card`, `.option-card-selected`, `.check-badge` | Selectable cards with a thick brand border, ring and check badge |
| `.chip`, `.chip-selected` | Multi-select pills |
| `.segmented`, `.segmented-item`, `.segmented-item-active` | Segmented single-select control |
| `.badge`, `.stat-tile`, `.spinner` | Status badges, stat tiles and the loading spinner |

It also sets a base body style: slate background, antialiased text.

---

## Theme data

### `frontend/src/app/models/api.models.ts`
- `ThemePalette` gains `accentAlt`, `surface`, `surfaceAlt`, `textMain`, `textMuted`, `border` and `chartColors`, which the preview cards need.
- A new `ThemeMood` type (`'cool' | 'warm' | 'bold' | 'brand'`) for the theme-picker filters.

### `frontend/src/app/constants/theme.constants.ts`
- `THEME_PALETTES` now has the full color set for all 16 palettes, copied from `src/knowledge/theme/palettes.yaml`. The two files must be kept in sync by hand.
- The tone labels of the retuned palettes match their new descriptions in the YAML.
- `THEME_MOODS` maps each light palette to a theme-picker filter group (`cool`, `warm`, `bold` or `brand`). A new palette without an entry defaults to `cool`.

### `src/knowledge/theme/palettes.yaml`
Nine light palettes are retuned. Before, every light palette had a near-white background, near-black text and a single mid-tone accent. Now each one differs in three ways: background tint, colored text ink, and a contrasting second accent (`accentAlt`). The pairings come from presentation-design references: navy and gold, forest with cream and amber, sand with teal and copper, blush with berry, purple with coral, charcoal with electric blue, and the Coolors "ocean" set.

| ID | New look |
|---|---|
| `sky-minimal` | Ocean blues on a pale sky background, navy text |
| `teal-slate` | Warm sand, deep teal and copper |
| `emerald-clean` | Crisp mint, emerald and lime |
| `forest-editorial` | Cream paper, forest green and amber |
| `warm-editorial` | Peach cream, terracotta and teal, espresso text |
| `amber-mono` | Ivory, navy text, antique gold |
| `rose-report` | Blush, berry and wine |
| `violet-modern` | Lavender, deep violet and coral |
| `graphite-mono` | Pure white, charcoal, electric blue, grey cards |

Unchanged:
- `corporate-slate`: the default, hardcoded as `DEFAULT_THEME` in `src/agents/style_resolver.py`.
- `navy-orange` and `saascolor`: brand palettes from the test PC (the test PC copy still used the old agency-named ID; merged with the neutral name from `f51c3f6`).
- The 4 dark palettes.

Every retuned palette passes the file's `contrast_targets`. Text-on-background ratios are all at least 11:1. The lowest accent-on-surface ratio is 3.46 (`emerald-clean`), against a minimum of 3.0.

Impact: decks made with these themes look different from earlier eval runs, so golden-match and eval comparisons for them may shift.

### `tests/unit/test_style_resolver.py`
- The `sky-minimal` checks now expect the new values: `surface="EAF6FB"`, `accent="0077B6"`, `textMain="03045E"`, and chart color `0077B6`.

---

## Components

### `frontend/src/app/components/theme-picker/theme-picker.component.ts` (new)
A visual replacement for the old theme `<select>`, using design F from `docs/mockups/theme-picker-variations.html` (compact chips). It is built to scale to large theme catalogs.
- A search box that matches theme name, tone and mood.
- Mood tabs with live counts: All, Cool, Warm, Bold, Brand, Dark. Light palettes are grouped by `THEME_MOODS`; dark palettes are grouped by their `mode`.
- Each theme is a small pill: a split dot (cover color and accent), plus the name. The tone shows on hover. The selected chip is tinted with the theme's accent and shows a check mark.
- The chips sit in a scroll box about 3 rows tall, so the picker stays the same size however many themes exist. An empty state appears when nothing matches.
- A preview panel for the selected theme, tinted with its accent:
  - a cover slide (bold ink block, title, KPI, bars)
  - a data slide (title, KPI tile, labelled bar chart)
  - the color roles: background, cards, headings, accent and second accent
  - The preview text uses container-query units (`cqw`), so it scales with the panel width.
- Implements `ControlValueAccessor`, so the prompt form keeps using `formControlName="theme"`. Uses `role="radiogroup"` and `role="radio"`/`aria-checked` for accessibility.

### `frontend/src/app/components/prompt-form/prompt-form.component.ts`
- Split into sections with dividers: Prompt, Presentation Style (the new theme picker), Presentation Settings, and Advanced Options.
- The header has a soft brand gradient, and the prompt box shows a live character count.
- Critic mode is now two option cards with one-line descriptions instead of bare radio buttons.
- A new summary strip at the bottom shows theme, slides, amount of text, tone and critic mode, with the Generate button on the right.
- Removed the `lightPalettes`/`darkPalettes` split and the `selectedAccent` signal, which the picker replaces. Added `selectedPalette` (computed), `promptLength`, and a public `deckSettings`.
- `onSubmit` is unchanged.

### `frontend/src/app/components/deck-settings-form/deck-settings-form.component.ts`
- Content handling is now three option cards, each with an icon (`textModeIcon()`).
- Amount of text and Slide count use the segmented control.
- Write for and Tone are chips that show a check mark when selected.
- While settings load, a skeleton placeholder is shown; load errors appear in a red banner.
- The outer border and top margin were removed, because the prompt form now draws the dividers.

### `frontend/src/app/components/layout/layout.component.ts`
- Sticky, blurred header with a gradient logo mark and the subtitle "AI-generated, editable decks".
- A step indicator (Prompt, Outline, Generate, Review) driven by `GenerationService.view()`; finished steps turn green with a check mark.
- Main content widened from `max-w-3xl` to `max-w-5xl`, on a soft radial background.

### `frontend/src/app/app.component.ts`
- The error banner has a warning icon and the new red styling.
- The "planning" state is now a card with a pulsing ring, a spinner, and a two-line message.

### `frontend/src/app/components/elicitation-form/elicitation-form.component.ts`
- Header with an amber question icon.
- Each question is a numbered card that highlights once answered; option buttons use chips and free-text answers use `.input`.
- A footer bar holds the Back and Continue buttons, with an arrow on Continue.

### `frontend/src/app/components/plan-editor/plan-editor.component.ts`
- Deck Title and Core Hook sit side by side on desktop.
- Slide cards have a dark numbered pill, and the card being regenerated gets a highlight ring.
- The actions are SVG icon buttons instead of unicode characters: regenerate, move up, move down, delete. Up and down are disabled at the ends instead of hidden.
- Each key message is a row with a dot, and its remove button appears on hover.
- The regenerate panel is a tinted box with a spinner while it works.
- The dashed "Add Slide" button has an icon, and Back/Generate sit in a sticky footer.
- Class logic is unchanged.

### `frontend/src/app/components/progress-view/progress-view.component.ts`
- Large percentage readout and a gradient progress bar with a shimmer.
- A vertical stepper with connector lines: finished steps are green checks, the active step shows a spinner, and pending steps show their number.
- The slide counter ("Slide X of Y") sits under the active step.

### `frontend/src/app/components/result-view/result-view.component.ts`
- Success banner with a large green check; the quality-check and excluded-slide badges use `.badge`.
- Plan quality has a confidence meter bar, and issues are listed with dots.
- Tokens in, tokens out, cost and models are shown as 4 stat tiles.
- A footer holds the actions: Download PPTX (primary), Review & Edit (secondary) and New Presentation (ghost), with icons.
- The error state is a centered red card with the error in monospace.

### `frontend/src/app/components/slide-review/slide-review.component.ts`
- Gradient header; the Finalize button shows a spinner while it runs.
- Thumbnails carry a slide-number badge and a version badge (`vN`); the selected one has a brand ring.
- The main preview sits on a radial backdrop in a shadowed frame, with a blurred overlay while an edit is being applied.
- Edit history is shown as chat bubbles, with the user's request on the right and the result (Applied / repairs / error) on the left. It now sits above the input box.
- The input and the Apply Edit button (with an icon) use the shared classes.
- Class logic is unchanged.
