# Theme gallery (2026-10-27)

One slide, every palette: the gj-h1 golden H1 snapshot (`tests/fixtures/golden/gj-h1-deck/02-h1-snapshot.xml`:
KPI tiles, chip, bar chart, dark platform panels) re-coloured with `src/compiler/theme_swap.swap_theme`, the
path the review screen's theme switch uses, then compiled (POM) and rendered (LibreOffice). Free, no LLM.

    python -m scripts.theme_gallery            # all palettes -> output/theme_gallery/
    python -m scripts.theme_gallery --out docs/eval/theme-gallery

- `sheet.png` — all 36 palettes (36 / 36 compiled).
- `sheet-new.png` — the 8 Perceptis palettes added 2026-10-27: mbb-blue (+ -dark) exact from a Perceptis export,
  perceptis / mbb-green / mbb-red (+ -dark) assumed from the template dropdown swatches.

Seen on the sheets:
- The tiny sub-headline drawn over the KPI row is in the original gj-h1 render too (the slide, not the themes).
- Fixed 2026-10-27 (re-rendered): the slide's dark panels (`$textMain` / dark hex fills) went WHITE with pale text on
  every dark theme; theme_swap now maps them to `$panelDark` and white ink on them to `$onPanelDark`.
- Contrast review: `python -m scripts.palette_contrast` (token pairs of every palette + LOW_CONTRAST on this slide).
- Chart colours too pale for the white chart card (2:1) or near-duplicates are swapped for the default green /
  amber by `palette_tokens.guard_chart_colors` (6FD2EF, C5EDF8, 9FE8CF, 6FE3B8); on mbb-green and perceptis-dark
  the third series (Zepto) falls to grey 808080.
- mbb-red: the accent CC2225 and the bad-number red DC2626 are nearly the same colour.
