# Tile nodes, wide replay (68 KPI slides; 0 the rewrite could not read)

| | A element refs | B tiles |
|---|---|---|
| compiled | 68 | 67 |
| squeeze (EMU error) | 0 | 1 |
| broken words (both compiled) | 13 | 16 |
| WORD_TOO_WIDE | 27 | 24 |
| GEOM_CARD_EMPTY | 59 | 88 |
| GEOM_SLIDE_SPARSE | 0 | 0 |
| LOW_CONTRAST | 24 | 22 |
| values off plan | 1 | 1 |
| number size mean / min (px) | 48.1 / 17 | 46.9 / 26 |
| sizes per slide: B larger / equal / smaller | 12 / 26 / 29 | |
| values mapped to refs | 313 / 317 | |
| KPI output tokens (replaced XML vs tags) | 35840 | 8137 |

## Colour (82 kpi_rows on slides both arms compiled)

- plan has tones: 0; no tones: 82
- no tones and the design hint asks colour: 65
- no tones, A draws colour (semantic / accent / literal): 74; semantic: 67
- no tones, B draws colour: 75; semantic: 66
- no tones, neither draws any colour: 6 (of them hint asks colour: 5)
- A coloured, B not: 1; B coloured, A not: 2

## Label colour per item

| label colour | A | B |
|---|---|---|
| accent | 27 | 22 |
| ink | 2 | 1 |
| missing | 23 | 23 |
| muted | 214 | 226 |
| none | 6 | 0 |
| on-dark | 4 | 4 |
| other | 6 | 6 |
| semantic | 28 | 28 |

A → B (items): muted → muted: 214, semantic → semantic: 28, missing → missing: 23, accent → accent: 22, other → other: 6, none → muted: 6, accent → muted: 5, on-dark → on-dark: 4, ink → ink: 1, ink → muted: 1

## Per slide

| slide | group | mapped | compiled A / B | broken A / B | card empty A / B | contrast A / B | mean size A / B | tones | colour A / B | labels A / B |
|---|---|---|---|---|---|---|---|---|---|---|
| decks2-deck-qbr-data-s1 | tile-replay | 4/4 | ok / ok | 0 / 0 | 1 / 0 | 0 / 0 | 65.0 / 57.0 | - | accent+semantic / accent+semantic | muted / muted |
| decks2-gate-deck-all-nodes-dense-s1 | tile-replay | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 66.4 / 68.0 | - | none+semantic,none / none+semantic,none | muted,on-dark / muted,on-dark |
| decks2-gate-deck-cheffin-full-s1 | tile-replay | 5/5 | ok / ok | 0 / 0 | 5 / 5 | 0 / 0 | 37.0 / 35.0 | - | none+semantic / none+semantic | muted/semantic / muted/semantic |
| decks2-gate-deck-cheffin-full-s4 | tile-replay | 7/7 | ok / ok | 0 / 0 | 6 / 6 | 0 / 0 | 30.0 / 28.0 | - | none+semantic / none+semantic | muted/semantic / muted/semantic |
| paid-deck-qbr-data-s1-r1 | tile-replay | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 91.0 / 83.0 | - | accent+semantic / accent+semantic | accent/muted/semantic / accent/muted/semantic |
| paid-deck-qbr-data-s1-r2 | tile-replay | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 86.0 / 83.0 | - | accent+semantic / accent+semantic | accent / accent/muted |
| paid-deck-qbr-data-s1-r3 | tile-replay | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 86.0 / 83.0 | - | accent+semantic / accent+semantic | accent / accent/muted |
| paid-gate-deck-cheffin-full-s1-r1 | tile-replay | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 70.8 / 65.0 | - | accent+dark,semantic / accent+dark,semantic | accent/on-dark,semantic / accent/on-dark,semantic |
| paid-gate-deck-cheffin-full-s1-r2 | tile-replay | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 68.4 / 63.4 | - | accent+dark,semantic / accent+dark,semantic | accent/on-dark,semantic / accent/on-dark,semantic |
| paid-gate-deck-cheffin-full-s1-r3 | tile-replay | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 72.0 / 69.2 | - | accent+dark,semantic / accent+dark,semantic | accent/on-dark,semantic / accent/on-dark,semantic |
| paid-gate-deck-cheffin-full-s4-r1 | tile-replay | 7/7 | ok / ok | 0 / 0 | 8 / 8 | 0 / 0 | 28.0 / 28.0 | - | none+semantic / none+semantic | muted/semantic / muted/semantic |
| paid-gate-deck-cheffin-full-s4-r2 | tile-replay | 7/7 | ok / ok | 0 / 0 | 8 / 8 | 0 / 0 | 28.0 / 28.0 | - | none+semantic / none+semantic | muted/semantic / muted/semantic |
| paid-gate-deck-cheffin-full-s4-r3 | tile-replay | 7/7 | ok / ok | 0 / 0 | 8 / 8 | 0 / 0 | 28.0 / 28.0 | - | accent+semantic / accent+semantic | accent/semantic / accent/semantic |
| decks1-deck-qbr-data-s1 | tile-replay | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 55.0 / 50.0 | - | accent+semantic / accent+dark+semantic | muted/other / muted/other |
| decks1-gate-deck-all-nodes-dense-s1 | tile-replay | 5/5 | ok / ok | 0 / 0 | 0 / 3 | 0 / 0 | 47.0 / 40.0 | - | accent+semantic / accent+semantic | accent / accent/muted |
| decks1-gate-deck-cheffin-full-s1 | tile-replay | 5/5 | ok / ok | 0 / 0 | 0 / 2 | 0 / 0 | 43.0 / 35.0 | - | accent+semantic / accent+semantic | muted / muted |
| decks1-gate-deck-cheffin-full-s4 | tile-replay | 7/7 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 58.0 / 58.0 | - | accent+none+semantic / accent+none+semantic | accent/muted/semantic / accent/muted/semantic |
| colour-roles-deck-qbr-data-s1 | colour-roles | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 1 / 1 | 95.0 / 95.0 | - | accent+semantic / accent+semantic | muted / muted |
| critic-on-deck-qbr-data-5fb8a2-s1 | critic-on | 4/4 | ok / ok | 0 / 0 | 1 / 1 | 1 / 1 | 67.0 / 59.0 | - | accent+semantic / accent+semantic | muted / muted |
| critic-on-deck-qbr-data-5fb8a2-s4 | critic-on | 3/3 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 95.0 / 86.0 | - | accent+semantic / accent+semantic | muted/semantic / muted/semantic |
| critic-on-deck-qbr-data-5fb8a2-s5 | critic-on | 1/3 | ok / ok | 0 / 0 | 2 / 2 | 1 / 1 | 87.0 / 87.0 | - | accent+semantic / accent+semantic | missing/muted / missing/muted |
| critic-on2-deck-qbr-data-e2e624-s1 | critic-on2 | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 1 / 0 | 66.0 / 59.0 | - | accent+semantic / accent+semantic | muted / muted |
| critic-on2-deck-qbr-data-e2e624-s4 | critic-on2 | 1/1 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 116.0 / 120.0 | - | semantic / semantic | muted / muted |
| critic-on2-deck-qbr-data-e2e624-s5 | critic-on2 | 2/2 | ok / ok | 0 / 0 | 1 / 1 | 0 / 0 | 95.0 / 95.0 | - | accent+semantic / accent+semantic | ink / ink/muted |
| eval-deck-qbr-data-s1-f000 | eval | 4/4 | ok / ok | 0 / 0 | 0 / 3 | 0 / 1 | 88.5 / 82.5 | - | none,semantic / semantic,semantic | other,muted / other,muted |
| eval-gate-deck-agency-takeover-s2 | eval | 2/2 | ok / ok | 0 / 0 | 0 / 0 | 1 / 1 | 50.0 / 35.0 | - | none+semantic / none+semantic | muted/other / muted/other |
| eval-deck-qbr-data-s1-6f46 | eval | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 1 | 87.8 / 80.2 | - | none,accent+semantic / semantic,accent+semantic | other,muted / other,muted |
| eval-deck-product-launch-data-s3 | eval | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 95.0 / 95.0 | - | semantic / accent | muted / muted |
| eval-gate-deck-all-nodes-dense-s1 | eval | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 68.0 / 69.6 | - | none+semantic,semantic / none+semantic,semantic | muted,muted / muted,muted |
| eval-gate-deck-cheffin-full-s1 | eval | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 39.0 / 37.0 | - | accent+semantic / accent+semantic | muted/semantic / muted/semantic |
| eval-gate-deck-cheffin-full-s4 | eval | 7/7 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 83.4 / 77.3 | - | accent+semantic,accent+semantic / accent+semantic,accent+semantic | muted,muted / muted,muted |
| old_zips-gj-h1-regen-5a9e2d-s1 | old_zips | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 52.0 / 64.0 | - | accent / accent | missing/muted / missing/muted |
| old_zips-gj-h1-regen-5a9e2d-s3 | old_zips | 4/4 | ok / ok | 1 / 1 | 0 / 1 | 1 / 1 | 28.0 / 28.0 | - | accent+semantic / accent+semantic | muted / muted |
| old_zips-gj-h1-regen-5a9e2d-s4 | old_zips | 5/5 | ok / ok | 8 / 8 | 1 / 1 | 1 / 1 | 28.0 / 28.0 | - | accent+literal+semantic / accent+semantic | muted / muted |
| old_zips-gj-h1-regen-5a9e2d-s5 | old_zips | 7/7 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 17.0 / 28.0 | - | accent+literal+none+semantic / accent+none+semantic | muted / muted |
| old_zips-gj-h1-regen-5a9e2d-s6 | old_zips | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 26.0 | - | accent+semantic / accent+semantic | muted / muted |
| old_zips-gj-h1-regen-5a9e2d-s10 | old_zips | 10/10 | ok / ok | 0 / 0 | 3 / 2 | 0 / 0 | 30.0 / 30.0 | - | ,none+semantic / ,accent+none+semantic | missing,muted / missing,muted |
| old_zips-gj-h1-regen-5a9e2d-s13 | old_zips | 3/3 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 28.0 | - | accent+semantic / accent+semantic | muted / muted |
| q1008-deck-product-launch-data-s3 | q1008 | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 37.0 | - | accent+semantic / accent+semantic | muted / muted |
| q1008-deck-qbr-data-s1 | q1008 | 4/4 | ok / ok | 0 / 0 | 0 / 0 | 1 / 1 | 60.0 / 58.0 | - | accent+semantic / accent+semantic | muted / muted |
| q1008-gate-deck-agency-takeover-s0 | q1008 | 5/5 | ok / ok | 0 / 0 | 0 / 2 | 0 / 0 | 0 / 0 | - | - / - | missing / missing |
| q1008-gate-deck-all-nodes-dense-s1 | q1008 | 5/5 | ok / ok | 1 / 1 | 0 / 0 | 1 / 0 | 48.8 / 68.0 | - | accent+semantic,accent+semantic / accent+semantic,none | muted,other / muted,other |
| q1008-gate-deck-cheffin-full-s1 | q1008 | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 63.2 / 60.8 | - | none,semantic / dark+none,semantic | muted/other,semantic / muted/other,semantic |
| q1008-gate-deck-cheffin-full-s4 | q1008 | 7/7 | ok / ok | 0 / 0 | 8 / 7 | 0 / 0 | 28.0 / 28.0 | - | accent+semantic / accent+semantic | muted/semantic / muted/semantic |
| r2-1b306e1de67f-s1 | r2 | 3/3 | ok / ok | 0 / 0 | 0 / 0 | 2 / 2 | 73.0 / 74.0 | - | accent+semantic / accent+semantic | muted/semantic / muted/semantic |
| r2-gj-h1-regen-69af33-s1 | r2 | 5/5 | ok / ok | 0 / 0 | 0 / 1 | 0 / 0 | 33.0 / 28.0 | - | accent, / accent, | missing/muted,missing / missing/muted,missing |
| r2-gj-h1-regen-69af33-s3 | r2 | 2/3 | ok / ok | 1 / 1 | 1 / 1 | 3 / 3 | 28.0 / 28.0 | - | accent+semantic / accent+semantic | missing/muted / missing/muted |
| r2-gj-h1-regen-69af33-s4 | r2 | 4/4 | ok / ok | 0 / 0 | 1 / 1 | 1 / 0 | 28.0 / 28.0 | - | accent+none+semantic / accent+none+semantic | muted / muted |
| r2-gj-h1-regen-69af33-s5 | r2 | 6/7 | ok / ok | 0 / 0 | 0 / 3 | 0 / 0 | 46.3 / 35.3 | - | none+semantic,accent / accent+none+semantic,accent | missing/none,none / missing/muted,muted |
| r2-gj-h1-regen-69af33-s6 | r2 | 4/4 | ok / ok | 0 / 0 | 0 / 1 | 0 / 0 | 28.0 / 28.0 | - | accent+none+semantic / accent+none+semantic | muted / muted |
| r2-gj-h1-regen-69af33-s13 | r2 | 3/3 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 36.0 / 32.0 | - | accent+semantic / accent+semantic | muted / muted |
| r2-gj-h1-regen-7293ef-s3 | r2 | 4/4 | ok / ok | 0 / 0 | 0 / 3 | 1 / 1 | 28.0 / 28.0 | - | accent+none+semantic / accent+none | muted / muted |
| r2-gj-h1-regen-7293ef-s4 | r2 | 6/6 | ok / ok | 2 / 5 | 3 / 3 | 1 / 1 | 28.0 / 28.0 | - | accent+none+semantic / accent+none+semantic | muted / muted |
| r2-gj-h1-regen-7293ef-s5 | r2 | 7/7 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 28.0 | - | accent+none+semantic / accent+none+semantic | muted / muted |
| r2-gj-h1-regen-7293ef-s6 | r2 | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 32.0 | - | accent+none+semantic / accent+none+semantic | muted / muted |
| r2-gj-h1-regen-7293ef-s13 | r2 | 3/3 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 32.0 | - | accent+semantic / accent+semantic | muted / muted |
| r2-gj-h1-regen-bf396b-s1 | r2 | 6/6 | ok / ok | 0 / 0 | 0 / 1 | 1 / 1 | 28.0 / 44.0 | - | accent+literal+semantic, / accent+semantic, | missing/muted,missing / missing/muted,missing |
| r2-gj-h1-regen-bf396b-s3 | r2 | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 2 / 2 | 28.0 / 30.0 | - | accent+semantic / accent+semantic | muted / muted |
| r2-gj-h1-regen-bf396b-s4 | r2 | 5/5 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 28.0 / 28.0 | - | none+semantic / none+semantic | muted / muted |
| r2-gj-h1-regen-bf396b-s5 | r2 | 7/7 | ok / ok | 0 / 0 | 0 / 4 | 0 / 0 | 28.0 / 28.0 | - | accent+literal+none+semantic / accent+none+semantic | muted / muted |
| r2-gj-h1-regen-bf396b-s6 | r2 | 6/6 | ok / ok | 0 / 0 | 1 / 4 | 1 / 1 | 28.0 / 28.0 | - | accent+semantic / accent+semantic | muted / muted |
| r2-gj-h1-regen-bf396b-s13 | r2 | 3/3 | ok / ok | 0 / 0 | 0 / 0 | 1 / 1 | 36.0 / 32.0 | - | accent+semantic / accent+semantic | muted / muted |
| r2-xtsy-23sep-1-s1 | r2 | 1/1 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 72.0 / 72.0 | - | accent+semantic / accent+semantic | muted / muted |
| r2-xtsy-23sep-2-s1 | r2 | 2/2 | ok / ok | 0 / 0 | 0 / 0 | 0 / 0 | 72.0 / 72.0 | - | accent+semantic,accent+semantic / accent+semantic,accent+semantic | muted,muted / muted,muted |
| r2-xtsy-23sep-3-s1 | r2 | 2/2 | ok / ok | 0 / 0 | 0 / 0 | 1 / 0 | 28.0 / 28.0 | - | accent+none / accent+none | accent/muted / accent/muted |
| run-1008-deck-qbr-data-30cd7b-s1 | run-1008 | 4/4 | ok / ok | 0 / 0 | 1 / 0 | 1 / 1 | 62.0 / 57.0 | - | accent+semantic / accent+semantic | muted / muted |
| step0-gate-deck-cheffin-full-s1 | step0 | 5/5 | ok / ok | 0 / 0 | 0 / 6 | 0 / 0 | 46.0 / 37.0 | - | accent+semantic / accent+semantic | muted / muted |
| step0-gate-deck-cheffin-full-s4 | step0 | 7/7 | ok / FAIL | 0 / None | 0 / 0 | 1 / 0 | 65.0 / 28.0 | - | accent+semantic / accent | muted/semantic / muted |
