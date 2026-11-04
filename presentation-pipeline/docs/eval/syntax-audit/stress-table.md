# Stress table (generated: `python -m scripts.syntax_audit tables`)

✓ pass, ~ warn, ✗ break, by the automatic checks (words lost, overlap, broken words, spill, compile, node errors); blank = not run. The report's reading by eye comes on top.

## kpi_row

| variant | one | sparse | many | long | odd | narrow | short | side | nested | mixed | missing | invented | refinref | item | tone | dark |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grid | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| strip | ~ | ~ | ~ | ~ | ✓ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| rows | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| banded | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| bento | ~ | ~ | ~ | ~ | ✓ | ✗ | ~ |  |  |  |  |  |  |  |  |  |

| variant | case | verdict | cause | drawn as | codes |
|---|---|---|---|---|---|
| grid | narrow | BREAK | text overlap (6) | grid |  |
| grid | short | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | nested | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | missing | BREAK | words lost: CAC payback | grid |  |
| grid | invented | BREAK | node error NODE_ATTR_UNKNOWN | grid | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| grid | refinref | BREAK | words lost: ROAS by campaign class | grid | NODE_ATTR_DROPPED |
| strip | one | WARN | GEOM_CARD_EMPTY | strip |  |
| strip | sparse | WARN | GEOM_CARD_EMPTY | strip |  |
| strip | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| strip | long | WARN | GEOM_CARD_EMPTY | strip | NODE_VALUE_TEXT |
| strip | narrow | BREAK | no compile: addTextBox: width must be a finite positive EMU value | strip |  |
| strip | short | WARN | GEOM_CARD_EMPTY | strip |  |
| rows | narrow | BREAK | WORD_TOO_WIDE | rows |  |
| rows | short | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | nested | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | missing | BREAK | words lost: CAC payback | rows |  |
| rows | invented | BREAK | node error NODE_ATTR_UNKNOWN | rows | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| rows | refinref | BREAK | words lost: ROAS by campaign class | rows | NODE_ATTR_DROPPED |
| banded | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| banded | narrow | BREAK | no compile: addTextBox: width must be a finite positive EMU value | banded |  |
| banded | short | WARN | GEOM_CARD_EMPTY | banded |  |
| bento | one | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| bento | sparse | WARN | GEOM_CARD_EMPTY | bento | NODE_ATTR_IGNORED |
| bento | many | WARN | GEOM_CARD_EMPTY | bento |  |
| bento | long | WARN | NODE_VARIANT_UNMET | grid | NODE_VALUE_TEXT NODE_VARIANT_UNMET |
| bento | narrow | BREAK | text overlap (11) | bento |  |
| bento | short | WARN | GEOM_CARD_EMPTY | bento |  |

## card_grid

| variant | one | sparse | many | long | odd | narrow | short | side | nested | mixed | missing | invented | refinref | item | tone | dark |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grid | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✓ | ✓ | ✓ |
| grid numbered | ~ | ✓ | ~ | ✓ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| rows | ✓ | ~ | ~ | ✗ | ✓ | ✗ | ✓ |  |  |  |  |  |  |  |  |  |
| rows numbered | ~ | ~ | ~ | ✗ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| columns | ✗ | ~ | ~ | ✗ | ✗ | ✗ | ✗ |  |  |  |  |  |  |  |  |  |
| banded | ✓ | ~ | ~ | ✓ | ✓ | ✗ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✓ | ✓ | ✓ |
| bento | ~ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |  |  |  |  |  |  |  |  |  |
| steps | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| rail | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |  |  |  |  |  |  |  |  |  |

| variant | case | verdict | cause | drawn as | codes |
|---|---|---|---|---|---|
| grid | narrow | BREAK | broken words (8): leakag/e | grid |  |
| grid | nested | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | missing | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | invented | BREAK | node error NODE_ATTR_UNKNOWN | grid | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| grid | refinref | BREAK | words lost: Gap | grid | NODE_ATTR_DROPPED |
| grid numbered | one | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| grid numbered | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| grid numbered | odd | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| grid numbered | narrow | BREAK | broken words (8): leakag/e | grid | NODE_VARIANT_UNMET |
| grid numbered | short | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| rows | sparse | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| rows | long | BREAK | text overlap (4) | rows |  |
| rows | narrow | BREAK | text overlap (91) | rows |  |
| rows numbered | one | WARN | NODE_VARIANT_UNMET | rows | NODE_VARIANT_UNMET |
| rows numbered | sparse | WARN | GEOM_CARD_EMPTY | rows numbered |  |
| rows numbered | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| rows numbered | long | BREAK | text overlap (4) | rows numbered |  |
| rows numbered | odd | WARN | NODE_VARIANT_UNMET | rows | NODE_VARIANT_UNMET |
| rows numbered | narrow | BREAK | text overlap (90) | rows | NODE_VARIANT_UNMET |
| rows numbered | short | WARN | NODE_VARIANT_UNMET | rows | NODE_VARIANT_UNMET |
| columns | one | BREAK | words lost: LEVER 1 | columns |  |
| columns | sparse | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| columns | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| columns | long | BREAK | words lost: A LONG TAG THAT RUNS ON | columns |  |
| columns | odd | BREAK | words lost: LEVER 1 | columns |  |
| columns | narrow | BREAK | no compile: addTextBox: width must be a finite positive EMU value | columns |  |
| columns | short | BREAK | words lost: LEVER 1 | columns |  |
| banded | sparse | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| banded | narrow | BREAK | text overlap (24) | banded |  |
| banded | nested | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | missing | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | invented | BREAK | node error NODE_ATTR_UNKNOWN | banded | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| banded | refinref | BREAK | words lost: Gap | banded | NODE_ATTR_DROPPED |
| bento | one | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| bento | sparse | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| bento | many | WARN | NODE_VARIANT_UNMET | grid | NODE_VARIANT_UNMET |
| bento | odd | BREAK | words lost: LEVER 3 | bento |  |
| bento | narrow | BREAK | no compile: addTextBox: width must be a finite positive EMU value | bento |  |
| bento | short | BREAK | words lost: LEVER 3 | bento |  |
| steps | many | BREAK | text overlap (20) | steps |  |
| steps | narrow | BREAK | no compile: addTextBox: width must be a finite positive EMU value | steps |  |
| steps | short | WARN | GEOM_CARD_EMPTY | steps |  |
| rail | many | BREAK | text overlap (63) | rail |  |
| rail | long | BREAK | GEOM_OFF_SLIDE,GEOM_SPILL | rail |  |
| rail | odd | BREAK | text overlap (8) | rail |  |
| rail | narrow | BREAK | GEOM_SPILL | rail |  |
| rail | short | BREAK | text overlap (90) | rail |  |

## chart

| variant | one | sparse | many | long | odd | narrow | short | side | nested | mixed | missing | invented | refinref | item | tone | dark |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| native | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| native labelled | ✓ | ✓ | ~ | ✓ | ✓ | ~ | ~ |  |  |  |  |  |  |  |  |  |
| rows | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |

| variant | case | verdict | cause | drawn as | codes |
|---|---|---|---|---|---|
| native | narrow | BREAK | text overlap (2) | native |  |
| native | short | WARN | GEOM_CARD_EMPTY | native |  |
| native | nested | WARN | GEOM_CARD_EMPTY | native |  |
| native | mixed | BREAK | words lost: 1.9 L | native |  |
| native | missing | BREAK | node error NODE_ITEM_MISSING |  | NODE_ITEM_MISSING |
| native | invented | BREAK | node error NODE_ATTR_UNKNOWN | native | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| native | refinref | BREAK | words lost: Gap | native | NODE_ATTR_DROPPED |
| native | tone | BREAK | no compile: Unknown theme token "$toneText"; Unknown theme token "$tone"; Unknown theme token "$tone"; Unknown | native |  |
| native labelled | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| native labelled | narrow | WARN | GEOM_CARD_EMPTY | native labelled |  |
| native labelled | short | WARN | GEOM_CARD_EMPTY | native labelled |  |
| rows | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| rows | narrow | BREAK | broken words (1): Competit/or | rows |  |
| rows | short | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | nested | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | missing | BREAK | node error NODE_ITEM_MISSING |  | NODE_ITEM_MISSING |
| rows | invented | BREAK | node error NODE_ATTR_UNKNOWN | rows | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| rows | refinref | BREAK | words lost: Gap | rows | NODE_ATTR_DROPPED |
| rows | tone | BREAK | no compile: Unknown theme token "$toneText"; Unknown theme token "$tone"; Unknown theme token "$tone"; Unknown | rows |  |

## timeline

| variant | one | sparse | many | long | odd | narrow | short | side | nested | mixed | missing | invented | refinref | item | tone | dark |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| native | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ~ |  |  |  |  |  |  |  |  |  |
| rail | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ~ | ~ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ |
| columns | ~ | ~ | ~ | ~ | ~ | ✗ | ~ | ✗ | ✗ | ~ | ~ | ✗ | ✗ | ~ | ✗ | ~ |
| rows | ✓ | ~ | ✓ | ✓ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| banded | ~ | ~ | ~ | ✗ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |

| variant | case | verdict | cause | drawn as | codes |
|---|---|---|---|---|---|
| native | long | WARN | NODE_VARIANT_UNMET | rail | NODE_TEXT_SPLIT NODE_VARIANT_UNMET |
| native | narrow | WARN | GEOM_CARD_EMPTY | native |  |
| native | short | WARN | GEOM_CARD_EMPTY | native |  |
| rail | many | WARN | NODE_VARIANT_UNMET,GEOM_CARD_EMPTY | columns | NODE_VARIANT_UNMET |
| rail | narrow | BREAK | text overlap (1) | rail | NODE_TEXT_SPLIT |
| rail | short | WARN | GEOM_CARD_EMPTY | rail | NODE_TEXT_SPLIT |
| rail | side | WARN | GEOM_CARD_EMPTY | bento,rail | NODE_LOOK_FROM_HINT NODE_TEXT_SPLIT |
| rail | nested | WARN | GEOM_CARD_EMPTY | rail | NODE_TEXT_SPLIT |
| rail | invented | BREAK | node error NODE_ATTR_UNKNOWN | rail | NODE_ATTR_ALIAS NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN NODE_TEXT_SPLIT |
| rail | refinref | BREAK | node error NODE_ITEM_MISSING | rail | NODE_ATTR_DROPPED NODE_ITEM_MISSING NODE_TEXT_SPLIT |
| rail | tone | BREAK | no compile: Unknown theme token "$toneText"; Unknown theme token "$tone"; Unknown theme token "$tone"; Unknown | rail | NODE_TEXT_SPLIT |
| columns | one | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | sparse | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | many | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | long | WARN | GEOM_CARD_EMPTY | columns | NODE_TEXT_SPLIT |
| columns | odd | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | narrow | BREAK | text overlap (75) | columns | NODE_TEXT_SPLIT |
| columns | short | WARN | GEOM_CARD_EMPTY | columns | NODE_TEXT_SPLIT |
| columns | side | BREAK | text overlap (1) | bento,columns | NODE_LOOK_FROM_HINT NODE_TEXT_SPLIT |
| columns | nested | BREAK | text overlap (1) | columns | NODE_TEXT_SPLIT |
| columns | mixed | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | missing | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | invented | BREAK | node error NODE_ATTR_UNKNOWN | columns | NODE_ATTR_ALIAS NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN NODE_TEXT_SPLIT |
| columns | refinref | BREAK | node error NODE_ITEM_MISSING | columns | NODE_ATTR_DROPPED NODE_ITEM_MISSING NODE_TEXT_SPLIT |
| columns | item | WARN | GEOM_CARD_EMPTY | columns | NODE_ATTR_DROPPED NODE_TEXT_SPLIT |
| columns | tone | BREAK | no compile: Unknown theme token "$tone"; Unknown theme token "$toneText"; Unknown theme token "$tone"; Unknown | columns | NODE_TEXT_SPLIT |
| columns | dark | WARN | GEOM_CARD_EMPTY | columns | NODE_TEXT_SPLIT |
| rows | sparse | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | odd | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | narrow | BREAK | text overlap (82) | rows | NODE_TEXT_SPLIT |
| rows | short | WARN | GEOM_CARD_EMPTY | rows | NODE_TEXT_SPLIT |
| banded | one | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | sparse | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | many | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | long | BREAK | text overlap (16) | banded | NODE_TEXT_SPLIT |
| banded | odd | WARN | GEOM_CARD_EMPTY | banded |  |
| banded | narrow | BREAK | text overlap (30) | banded | NODE_TEXT_SPLIT |
| banded | short | WARN | GEOM_CARD_EMPTY | banded | NODE_TEXT_SPLIT |

## table

| variant | one | sparse | many | long | odd | narrow | short | side | nested | mixed | missing | invented | refinref | item | tone | dark |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| native | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| rows | ✓ | ~ | ✓ | ✓ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| rows numbered | ✓ | ~ | ✓ | ✓ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| columns | ✗ | ✗ | ~ | ✗ | ~ | ✗ | ✗ |  |  |  |  |  |  |  |  |  |
| banded | ✗ | ✗ | ~ | ✗ | ✓ | ✗ | ✗ |  |  |  |  |  |  |  |  |  |
| grid | ~ | ~ | ~ | ~ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| grid numbered | ~ | ~ | ~ | ~ | ~ | ✗ | ~ |  |  |  |  |  |  |  |  |  |
| ledger | ~ | ~ | ~ | ~ | ~ | ✗ | ~ | ~ | ~ | ✓ | ~ | ✗ | ✗ | ✓ | ✓ | ✓ |

| variant | case | verdict | cause | drawn as | codes |
|---|---|---|---|---|---|
| native | narrow | BREAK | broken words (15): Market/place | native |  |
| native | short | WARN | GEOM_CARD_EMPTY | native |  |
| native | nested | BREAK | WORD_TOO_WIDE | native |  |
| native | invented | BREAK | node error NODE_ATTR_UNKNOWN | native | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| native | refinref | BREAK | words lost: ROAS by campaign class | native | NODE_ATTR_DROPPED |
| rows | sparse | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | odd | WARN | GEOM_CARD_EMPTY | rows |  |
| rows | narrow | BREAK | text overlap (4) | rows |  |
| rows | short | WARN | GEOM_CARD_EMPTY | rows |  |
| rows numbered | sparse | WARN | GEOM_CARD_EMPTY | rows numbered |  |
| rows numbered | odd | WARN | GEOM_CARD_EMPTY | rows numbered |  |
| rows numbered | narrow | BREAK | text overlap (37) | rows numbered |  |
| rows numbered | short | WARN | GEOM_CARD_EMPTY | rows numbered |  |
| columns | one | BREAK | words lost: Gap | columns |  |
| columns | sparse | BREAK | words lost: A | columns |  |
| columns | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| columns | long | BREAK | words lost: Gap and its consequences for the plan | columns |  |
| columns | odd | WARN | GEOM_CARD_EMPTY | columns |  |
| columns | narrow | BREAK | words lost: Gap | columns |  |
| columns | short | BREAK | words lost: Gap | columns |  |
| banded | one | BREAK | words lost: Gap | banded |  |
| banded | sparse | BREAK | words lost: A | banded |  |
| banded | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| banded | long | BREAK | words lost: Gap and its consequences for the plan | banded |  |
| banded | narrow | BREAK | words lost: Gap | banded |  |
| banded | short | BREAK | words lost: Gap | banded |  |
| grid | one | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | sparse | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| grid | long | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | odd | WARN | GEOM_CARD_EMPTY | grid |  |
| grid | narrow | BREAK | text overlap (1) | grid |  |
| grid | short | WARN | GEOM_CARD_EMPTY | grid |  |
| grid numbered | one | WARN | GEOM_CARD_EMPTY | grid numbered |  |
| grid numbered | sparse | WARN | GEOM_CARD_EMPTY | grid numbered |  |
| grid numbered | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| grid numbered | long | WARN | GEOM_CARD_EMPTY | grid numbered |  |
| grid numbered | odd | WARN | GEOM_CARD_EMPTY | grid numbered |  |
| grid numbered | narrow | BREAK | text overlap (86) | grid numbered |  |
| grid numbered | short | WARN | GEOM_CARD_EMPTY | grid numbered |  |
| ledger | one | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | sparse | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | many | WARN | NODE_VARIANT_UNMET | native | NODE_VARIANT_UNMET |
| ledger | long | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | odd | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | narrow | BREAK | text overlap (1) | ledger |  |
| ledger | short | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | side | WARN | GEOM_CARD_EMPTY | ledger,native |  |
| ledger | nested | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | missing | WARN | GEOM_CARD_EMPTY | ledger |  |
| ledger | invented | BREAK | node error NODE_ATTR_UNKNOWN | ledger | NODE_ATTR_DROPPED NODE_ATTR_UNKNOWN |
| ledger | refinref | BREAK | words lost: ROAS by campaign class | ledger | NODE_ATTR_DROPPED |
