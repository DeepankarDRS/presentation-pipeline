# KPI tile nodes: gallery (2026-10-12, free)

`python -m scripts.experiments.tiles.tile_gallery` (spec §8 step 3, `docs/tile-nodes-spec-2026-10-12.md`). Hand-written tile tags,
then the real path: `tiles.fill` (expand + `element_refs.fill_refs`) → `normalize_xml` → `compile-pom.js`
(fit-grow, POM) → LibreOffice. One slide per variant × arrange (7 × 4) on the QBR plan (4 items, tones good / good /
bad / good, emphasis ARR, an icon per item; `inverted` = the plan's emphasis item in a `plain` group), plus the
spec's §2.2 examples 1–5 on the ROAS plan (5 items, emphasis Blended ROAS).

| Sheet | |
|---|---|
| `corporate-slate-variants.png` / `graphite-dark-variants.png` | rows: plain, filled, toned, bar, dot, inverted, bare; columns: label-first, value-first, icon-top, side |
| `corporate-slate-examples.png` / `graphite-dark-examples.png` | spec §2.2 examples 1–5 |

## What it shows

- **Every variant × arrange compiles and renders on both palettes** (56 + 10 slides, 0 NODE_* errors). Colours come
  from the role tokens only; no literal hex; `$panelDark` reads apart on the dark palette by hue (navy on graphite).
- **The spec's examples work as written.** Example 3 (grid + dark focus panel, ~55 output tokens; the LLM wrote
  ~750 for it by hand) draws the focus value at hero size beside a 2 × 2 dot grid; example 4's two groups get the
  plan weights' ranks (hero row larger than the supporting row).
- **Found and fixed during the gallery** (both in `tiles.py`, unit-tested):
  1. An item's own `variant` sat on top of the group variant's look: an `inverted` tile in a `plain` group kept the
     plain hairline border. Now an item variant replaces the group variant; the group's attributes still apply.
  2. `dot` + `side` + an icon dropped the dot (one lead beside the text); the dot now stays beside the label.
  3. (from the paid-check dry run, CHEFFIN slide 1) a `size="hero"` tile inside its group's row: the peers' numbers
     grew first (28 → 79 px) and took its width, the shrink guard then cut the hero to 35 px, smaller than its peers.
     A row holding a hero tile now gets equal columns (`w="1" grow="1"`): hero 107 px, peers 70 px.
- **Not tile-specific, seen on both routes** (the pilot's hand-written gallery has the same numbers):
  - Peer labels are not sized together: one-word labels grow to 24 px, two-word labels to 28 px with `reserveWrap`'s
    `minH` for a second line the renderer never draws, so values sit at different heights across a row
    (plain · label-first). A follow-up: id the labels like the values (`kpil<rank>-…`) so fit-grow sizes them as one group.
  - In a 3-row grid the supporting row (a lower plan weight) can stay at 28 px while the higher rows take the room.
- `value.textGradient` (example 5) renders as a flat colour in LibreOffice; PowerPoint not checked.
- `cols="2"` on 5 items leaves the last tile alone at full width (example 2): the LLM's choice, kept.
- **T4 (Card `numerals` with a transparent Shape)** is a Card question; nothing to check until cards are built.
