"""One KPI value parser (look spec V15, 2026-10-11): "$48.2M" -> ("$48.2", "M").

Used by the KPI ref fill step (src/compiler/nodes/element_refs.py), the composer
(scripts/experiments/phase0b/render.py) and the variant gallery; fit-grow scales the unit <Span>
the fill step writes with its number. The split is verbatim: head + unit == value
(a space before the unit stays in the unit), so a drawn value always reads as the plan's.

Units: a short one glued or spaced ("%", "x", "M", " Cr", " pts") or one spaced word
("14 months", "15 min/wk"). A value that is not one number with a unit ("Q3 FY26",
"₹29.4L / ₹85.5L") is drawn whole: unit "".

Unit size (user, 2026-10-11 marks, pair 1.1: "units size can be small or big"): not one fixed
share. A one-character unit sits beside the number as part of it (0.6); a 2-3 letter unit
reads as a suffix (0.5); a word unit is a caption to the number (0.42). One component takes
the smallest share any of its values needs, so peers match; never below the 14 px floor.
"""

from __future__ import annotations

import re

_VALUE = re.compile(
    r"^(?P<head>[+\-−~<>≈]?[₹$€£¥]?\s?\d[\d,]*(?:\.\d+)?)"
    r"(?P<unit>\s?(?:%|x|×|[A-Za-z]{1,3})|\s[A-Za-z][A-Za-z/.]{3,9})?$")

UNIT_SCALE = 0.45   # default share (composer, gallery)
UNIT_SHARES = ((1, 0.6), (3, 0.5), (99, 0.42))   # unit length (letters) -> share of the number's size
UNIT_FLOOR = 14


def split_value(value: str) -> tuple[str, str]:
    """(number, unit) with number + unit == value (stripped); no full match -> (value, "")."""
    v = str(value).strip()
    m = _VALUE.match(v)
    return (m["head"], m["unit"] or "") if m else (v, "")


def unit_share(values: list[str]) -> float:
    """The unit's share of the number's size for a group of peer values (see module doc)."""
    units = [split_value(v)[1].strip() for v in values]
    units = [u for u in units if u]
    if not units:
        return UNIT_SCALE
    longest = max(len(u) for u in units)
    return next(share for limit, share in UNIT_SHARES if longest <= limit)


def unit_px(size: float, share: float = UNIT_SCALE) -> int:
    return max(UNIT_FLOOR, round(size * share))


def is_sentence(value: str) -> bool:
    """A KPI value that is prose, not a figure ("Generic search consumed the largest budget pool
    and returned around 0.29x ROAS."): no number + unit shape and more than 3 words or 24 chars."""
    v = str(value).strip()
    if not v or split_value(v)[1] or _VALUE.match(v):
        return False
    return len(v.split()) > 3 or len(v) > 24
