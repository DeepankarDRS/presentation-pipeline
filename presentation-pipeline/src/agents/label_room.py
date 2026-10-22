"""Plan check: does each diagram label's longest word fit the room POM gives it? (user decision 2026-10-21)

Labels break on their longest word in px, not on their word count (docs/eval/node-break-map/README.md §3
item 2): "Profitability" breaks a chevron that "Plan the launch" fits. So each label's longest word is
measured with POM's own text measurement (src/node/break-map.js measure: the fonts in src/node/fonts) in
the deck font, at the size it is drawn, against the room the map measured for its kind and direction:

  process_arrow horizontal  itemWidth - 0.7 x itemHeight - 2 x 9.6 px insets (process_arrow.label_box,
                            label_inset), itemWidth as fit-grow sizes a row across the band (n chevrons
                            interlocking 28 px in 97 % of 1168 px), at 14 px bold: the smallest size
                            fit-grow lowers a chevron row to
  process_arrow vertical    the chevron's full width (process_arrow.vertical_label): fit-grow makes it
                            90 % of the column; checked for the narrowest column, 38 % of the slide (444 px)
  timeline horizontal       a 120 px title box (timeline.horizontal) less insets, 14 px bold
  timeline vertical         the box width less 80 px (timeline.vertical), checked for a 444 px column
  matrix                    a 100 px item label box less insets, 11 px bold (matrix.labels)
  pyramid                   band k of n is 400 x k / n px wide (up; down mirrors it), less insets,
                            14 px (pyramid.bands), measured bold to be safe

Past the room: a horizontal process_arrow / timeline turns vertical when every word fits there and the
vertical capacity holds the count, else becomes card_grid steps (capacity._to_cards); a pyramid becomes
card_grid steps in its order. A matrix is only reported: its items are positions, which cards would lose.
Never a word dropped or shortened. One node spawn per slide plan; without node the check is skipped.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.agents.capacity import _as_cards, _label, _to_cards, direction_of, max_of

logger = logging.getLogger(__name__)

_RUNNER = Path(__file__).resolve().parent.parent / "node" / "break-map.js"
WORD_MARGIN = 0.5     # px a word needs to spare (fit-grow WORD_MARGIN: LibreOffice breaks a word 0.3 px over)
INSETS = 2 * 9.6      # the renderer's default left + right text insets (process_arrow.label_inset)
BAND_W = 1168 * 0.97  # the slide's main band as fit-grow sizes a diagram in it (padding 56, 3 % margin)
COLUMN_W = 444        # the narrowest column a vertical diagram is planned into (split 60 / 40, 38 %)
ARROW_DEPTH = 28      # chevrons interlock by ARROW_DEPTH_RATIO 0.35 x itemHeight 80

# (px, bold) each kind's labels are drawn at
_SIZE = {"process_arrow": (14, True), "timeline": (14, True), "matrix": (11, True), "pyramid": (14, True)}


def _deck_font() -> str:
    family = os.environ.get("POM_DECK_FONT", "Inter")
    return "Noto Sans JP" if not family or family.lower() == "none" else family


def arrow_room(n: int) -> float:
    """The label room of a middle chevron in a row of n across the band."""
    item_w = (BAND_W + (n - 1) * ARROW_DEPTH) / n
    return item_w - 2 * ARROW_DEPTH - INSETS


def pyramid_rooms(n: int, direction: str) -> list[float]:
    widths = [400 * (k + 1) / n for k in range(n)]
    return [w - INSETS for w in (widths if direction != "down" else widths[::-1])]


def _labels(comp: dict[str, Any]) -> list[str]:
    data = comp.get("content_data") or {}
    items = {"process_arrow": data.get("process_steps"), "timeline": data.get("timeline_items"),
             "matrix": data.get("matrix_items"), "pyramid": data.get("pyramid_levels")}.get(comp.get("kind")) or []
    return [_label(i) for i in items]


def _rooms(comp: dict[str, Any], direction: str) -> list[float]:
    kind, n = comp.get("kind"), len(_labels(comp))
    if kind == "process_arrow":
        return [arrow_room(n) if direction == "horizontal" else COLUMN_W * 0.9 - INSETS] * n
    if kind == "timeline":
        return [120 - INSETS if direction == "horizontal" else COLUMN_W - 80 - INSETS] * n
    if kind == "matrix":
        return [100 - INSETS] * n
    return pyramid_rooms(n, str((comp.get("content_data") or {}).get("direction") or "up"))


def measure_words(labels: list[tuple[str, int, bool]]) -> list[tuple[str, float]] | None:
    """(longest word, px) of each (text, px, bold), in the deck font; None when node cannot run."""
    if not labels:
        return []
    family = _deck_font()
    reqs = [{"text": t, "family": family, "px": px, "bold": bold, "width": 10000} for t, px, bold in labels]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "in.json", Path(tmp) / "out.json"
            src.write_text(json.dumps(reqs), encoding="utf-8")
            subprocess.run(["node", str(_RUNNER), "measure", str(src), str(dst)], check=True, capture_output=True,
                           timeout=60, cwd=_RUNNER.parent)
            return [(r["word"], r["wordW"]) for r in json.loads(dst.read_text(encoding="utf-8"))]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        logger.warning(f"label_room: words not measured, check skipped: {exc}")
        return None


def _too_wide(words: list[tuple[str, float]], rooms: list[float]) -> tuple[str, float, float] | None:
    for (word, w), room in zip(words, rooms):
        if w > room - WORD_MARGIN:
            return word, w, room
    return None


def enforce_label_room(components: list[dict[str, Any]]) -> list[str]:
    """Fix the plan in place where a diagram label's longest word cannot fit its room; one note per change."""
    comps = [c for c in components if c.get("kind") in _SIZE and _labels(c)]
    if not comps:
        return []
    measured = measure_words([(t, *_SIZE[c["kind"]]) for c in comps for t in _labels(c)])
    if measured is None:
        return []
    notes, i = [], 0
    for comp in comps:
        kind, labels = comp["kind"], _labels(comp)
        words, i = measured[i:i + len(labels)], i + len(labels)
        cid = comp.get("component_id") or kind
        direction = direction_of(comp)
        wide = _too_wide(words, _rooms(comp, direction))
        if not wide:
            continue
        word, w, room = wide
        what = f"{cid}: {kind} label word '{word}' is {w:.0f} px, its box holds {room:.0f}"
        data = comp.setdefault("content_data", {})
        if kind in ("process_arrow", "timeline"):
            if direction == "horizontal" and len(labels) <= max_of(kind, direction="vertical") \
                    and not _too_wide(words, _rooms(comp, "vertical")):
                data["direction"] = comp["orientation"] = "vertical"
                notes.append(f"{what} -> vertical")
                continue
            items = data.get("process_steps") if kind == "process_arrow" else data.get("timeline_items")
            _to_cards(comp, _as_cards(items, tag_key="date" if kind == "timeline" else None))
            notes.append(f"{what} -> card_grid ({comp['content_data']['card_layout']})")
        elif kind == "pyramid":
            _to_cards(comp, _as_cards(data["pyramid_levels"]))
            notes.append(f"{what} -> card_grid ({comp['content_data']['card_layout']})")
        else:  # matrix: reported and kept; cards would lose the positions
            notes.append(f"{what}; kept as a matrix (the renderer will break it)")
    return notes
