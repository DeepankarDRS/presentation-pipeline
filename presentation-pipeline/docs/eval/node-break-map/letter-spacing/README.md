# Letter spacing after the last letter (node break map §4 C1, open edge)

POM's `measureText` adds `letterSpacing` after every letter, the last one too (`withLetterSpacing` in
`calcYogaLayout/measureText.js`), and fit-grow's `naturalWidth` keeps that count. Question: does a renderer
need the trailing spacing, or can a letter-spaced word be one spacing narrower than POM counts?

**Probe (2026-10-22, LLM-free).** `probe.mjs` writes `probe.xml`: ten rows, five words in Inter bold, each
with spacing 0 (control) and with spacing s. Each word sits in boxes of whole-px widths around POM's
count (POM writes text boxes with 0 insets, so the room is the box width; the pptx was checked to carry
exactly these widths). `d` = POM count − box width; `probe-meta.json` lists d per box, left to right.
`probe.pptx` is the compiled deck, `probe-libreoffice.png` its LibreOffice render.

| word, size | s | POM count | LibreOffice: whole up to d | first break at d |
|---|---|---|---|---|
| share 14 | 0 | 38.73 | −0.27 | 0.73 |
| share 14 | 1 | 43.73 | 0.73 | 1.73 |
| SHARE 14 | 0 | 47.78 | −0.22 | 0.78 |
| SHARE 14 | 2 | 57.78 | 1.78 | 2.78 |
| Projected 16 | 0 | 75.45 | 3.45 | none in range |
| Projected 16 | 2 | 93.45 | 2.45 | 3.45 |
| TARGETS 15 | 0 | 71.26 | −0.74 | 0.26 |
| TARGETS 15 | 3 | 92.26 | 4.26 | none in range |
| REVENUE 18 | 0 | 84.96 | −0.04 | 0.96 |
| REVENUE 18 | 4 | 112.96 | 3.96 | 4.96 |

**LibreOffice:** the break point moves by about one spacing (s) against the spacing-0 control for share,
SHARE and REVENUE, and by more for TARGETS: LibreOffice does not need the spacing after the last letter.
Every letter-spaced word was whole at d = s − 0.5 (count − s + `WORD_MARGIN`). "Projected" is the odd one:
without spacing it fits 3.45 px under POM's count (POM over-measures this word, likely kerning), with
spacing 2 it breaks at 3.45, so its spacing costs more than its count says; the count − s rule still held.

**PowerPoint: not checked.** It is not installed on this PC (no `PowerPoint.Application` ProgID, so
`src/compiler/screenshot.py` cannot run). To check: open `probe.pptx` in PowerPoint on the test PC and
note, per row, the first box whose word breaks; compare with the table.

**Decision: `naturalWidth` unchanged (conservative).** Counting the trailing spacing can only over-measure
a letter-spaced word by s (1–4 px on labels), which costs at most a slightly smaller label or a report
the render does not need ("Ad share" in g4). Change it to count − s only if PowerPoint agrees with the
table above.
