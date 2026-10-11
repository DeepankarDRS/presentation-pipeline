"""One KPI value parser (look spec V15, 2026-10-11): "$48.2M" -> ("$48.2", "M").

Used by the KPI ref fill step (src/compiler/nodes/element_refs.py), the composer
(scripts/phase0b/render.py) and the variant gallery; fit-grow scales the unit <Span>
the fill step writes with its number. The split is verbatim: head + unit == value
(a space before the unit stays in the unit), so a drawn value always reads as the plan's.

A value that is not one number with an optional short unit ("14 months", "Q3 FY26",
"₹29.4L / ₹85.5L") is drawn whole: unit "".
"""

from __future__ import annotations

import re

_VALUE = re.compile(
    r"^(?P<head>[+\-−~<>≈]?[₹$€£¥]?\s?\d[\d,]*(?:\.\d+)?)"
    r"(?P<unit>\s?(?:%|x|×|[A-Za-z]{1,3}))?$")

UNIT_SCALE = 0.45   # a unit is drawn at this share of its number's size


def split_value(value: str) -> tuple[str, str]:
    """(number, unit) with number + unit == value (stripped); no full match -> (value, "")."""
    v = str(value).strip()
    m = _VALUE.match(v)
    return (m["head"], m["unit"] or "") if m else (v, "")


def unit_px(size: float) -> int:
    return round(size * UNIT_SCALE)
