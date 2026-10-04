# Phase 0 — Genspark-level reference slides (POM, hand-written)

Goal: prove which parts of the Genspark deck's polish POM 10.3.0 can produce
before building code-drawn chrome / recipes (Phases 1–3). Three XTSY slides
(brief: `tests/cases/gate-deck-xtsy-qcomm.yaml`), written by hand, no LLM:

| Slide | Genspark original | What it tests |
|---|---|---|
| 1 Cover | dark hero, platforms → engine | radial gradient background, 54px two-tone headline (`<I><Span color>`), `Layer` diagram (Shape boxes + Lines), mono kicker, footer `01 / 08` |
| 7 Impact | 7 arrow tiles + "7" tile | card micro-labels (`IMPACT 01`), title with italic last word, 3 card fills (white / ink / lime), `Icon arrow-up` per card, divider, key-message row, hero number tile |
| 8 Roadmap | 3 month cards + closing line | square cards with `borderTop` accent, `MONTH 01 · DAY 1–30` labels, dark highlight card, bullet rows (6px square + Text, `Ul` has no indent control), closing statement with a rule |

Files:
- `genspark-ref-segoe.xml` — Segoe UI + Consolas (installed on every Windows PC)
- `genspark-ref-gfonts.xml` — same slides in Space Grotesk + JetBrains Mono (Google
  Fonts; install both first, or PowerPoint / LibreOffice substitute a fallback)

Content rule: only brief text, plus wording derived from it (the count "7",
"Month 01 · Day 1–30" from "90 days / 3 months"). Headlines follow the
proposed rule — brief title as the kicker, a claim headline built from the
brief ("Seven growth levers, one scalable engine." from the slide 7 message).

## Render (test PC)

```bash
python -m scripts.render_check --in docs/eval/genspark-ref --out output/render_check/genspark-ref
```

Then open `output/render_check/genspark-ref/<name>/presentation.pptx` in PowerPoint
and Save As PDF (or `soffice --convert-to pdf`, see `.cursor/rules/offline-render-loop.mdc`).
PNGs per slide: `soffice --headless --convert-to pdf presentation.pptx`, then pymupdf
(`page.get_pixmap(dpi=110).save(...)`).

## Expected / what to check

- **Audit warnings expected:** labels and footers are 10–12px; house style's floor
  is 14 (`house-style.yaml: min_font`). Genspark's micro-labels are ~10–11px — the
  test is whether they read well, i.e. whether to allow a label tier below 14.
- Compiles at all? If not, the error names the unsupported attribute — that is the
  finding (most likely suspects: `$token` in `Icon color` / `Line color`,
  `letterSpacing` decimals, `<I><Span color>` nesting).
- Fonts: do Segoe UI and Space Grotesk both render as named, and does text wrap where
  expected (headline 2 lines on slides 7 and 8, 3 lines on the cover)?
- Layout: cards equal height per row, nothing clipped, footer at the bottom edge,
  cover diagram lines meet the engine box.
- Compare side by side with the Genspark screenshots (slides 1, 7, 8).

## Results

- 2026-10-01, first compile: `line.width="0"` rejected (stroke must be a positive EMU) —
  known (`ZERO_STROKE_REMOVED` in the normalizer; `llm.md`'s KPI-dot example is wrong
  here). Fix: no `line.*` at all on fill-only shapes. `line.width="1"` without a
  colour would draw a default-colour outline around the small markers.
- 2026-10-04, first render (LibreOffice → PDF → PNG via pymupdf, build PC): both
  decks compile, 0 diagnostics. Audit: 25 `FONT_TOO_SMALL` per deck (the 10–12px
  labels, intended) and 3 `LOW_CONTRAST` on the cover — false alarms: the audit
  measures text against `#FFFFFF`, not the dark `backgroundGradient` (gap in the
  contrast check for gradient backgrounds).
- **POM can produce the polish:** radial gradient, two-tone 54px headline, `Layer`
  diagram, mono micro-labels, three card fills, `Icon` arrows per card, `borderTop`
  month cards, dark highlight card, hero number tile. 10–12px mono labels read well
  in the render → a label tier below 14 looks viable.
- **Layout fixes needed (applied 2026-10-04):**
  - Header / footer right side sat mid-slide: a `<VStack grow="1"/>` spacer leaves
    the right-hand Text in a wide box, drawn left-aligned. Fix: the row gets
    `justifyContent="spaceBetween"`, the right Text `textAlign="right"`.
  - `w="max"` cards size to their content → uneven columns, rows misaligned. Fix:
    `w="1" grow="1"` gives equal columns that reach the right margin (fixed widths
    such as `w="281"` ended ~15px short).
  - Impact slide: the "7" tile moved into the grid as the 8th cell (4 + 4); card 05's
    2px ink border made consistent; key message as a full-width labelled row.
  - Roadmap: `Ul` bullets sit far from their markers and POM has no indent setting →
    rows of a 6px square + Text, coloured per phase.
- **fit-grow findings (affect generated decks too):**
  - `reserveWrap` measures headings ≥ 20px at 85% width in Noto Sans JP and adds
    `minH` for a second line that never appears in Segoe UI → a blank band under
    40px headlines with `maxW="900"`. `minH` overrides an explicit `h` on the Text;
    only a fixed-height parent (`<VStack h="34"><Text/></VStack>`) holds it.
    Removing `maxW` from the headlines avoided it.
  - fit-grow raised `lineHeight` 1.15 → 1.6 on some two-line card titles
    ("Sponsored placement share"), so they look more spaced than their row.
- Space Grotesk + JetBrains Mono not installed on the build PC: the fallback runs
  wider, the impact headline wraps and clips into the cards — not judged yet.
  Install both fonts (or open in PowerPoint on a PC with them) before comparing.
