"""Phase 0b criterion 2: every plan string is on its slide, and no other words are.

    python -m scripts.phase0b.check scripts/phase0b/plans/xtsy.json output/phase0b/xtsy [output/phase0b/ours-xtsy]

Words, not exact strings: the renderer may split "Phase 1: Foundation" into a label
and a title, or a comma list into bullets. Frame words (KEY MESSAGE, brand, running
title, page numbers, card numbers) are allowed.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SKIP_KEYS = {"card_layout", "chart_type", "direction", "per_row", "body_source", "kpi_directions"}
FRAME = {"key", "message", "phase", "month", "step", "stage"}
WORD = re.compile(r"[a-z0-9₹%]+(?:[.'’][a-z0-9]+)*")


def words(text: str) -> list[str]:
    return WORD.findall(html.unescape(text).lower())


def plan_strings(plan: dict) -> list[str]:
    out = [plan.get(k) or "" for k in ("label", "slide_title", "subtitle")]

    def walk(v, key=""):
        if key in SKIP_KEYS:
            return
        if isinstance(v, dict):
            for k, w in v.items():
                walk(w, k)
        elif isinstance(v, list):
            for w in v:
                walk(w, key)
        elif isinstance(v, (str, int, float)) and str(v).strip():
            out.append(str(v))

    for c in plan["components"]:
        walk(c.get("content_data") or {})
    return [s for s in out if s]


def visible_text(xml: str) -> str:
    xml = re.sub(r"<Theme[^>]*/>", "", xml)
    attrs = " ".join(re.findall(r'\btext="([^"]*)"', xml))
    xml = re.sub(r"</?Span[^>]*>", "", xml)  # inline runs: "₹114.9<Span>L</Span>" is one word
    body = re.sub(r"<[^>]+>", " ", xml)
    return attrs + " " + body


def check(plans_file: Path, xml_dir: Path) -> tuple[int, int, list[str]]:
    data = json.loads(plans_file.read_text(encoding="utf-8"))
    deck = data["deck"]
    frame = FRAME | set(words(deck["brand"])) | set(words(deck.get("running", "")))
    files = sorted(xml_dir.glob("slide-*.xml"))
    missing_total = extra_total = 0
    lines = []
    for i, (plan, f) in enumerate(zip(data["slides"], files), start=1):
        seen = words(visible_text(f.read_text(encoding="utf-8")))
        seen_set = set(seen)
        strings = plan_strings(plan)
        plan_words = {w for s in strings for w in words(s)}
        missing = sorted({w for w in plan_words if w not in seen_set})
        extra = sorted({w for w in seen_set if w not in plan_words and w not in frame and not re.fullmatch(r"\d{1,2}", w)})
        missing_total += len(missing)
        extra_total += len(extra)
        lines.append(f"slide {i}: missing {len(missing)} {missing[:12]} | extra {len(extra)} {extra[:12]}")
    return missing_total, extra_total, lines


def main() -> None:
    plans = Path(sys.argv[1])
    for d in sys.argv[2:]:
        m, e, lines = check(plans, Path(d))
        print(f"== {d}: plan words missing {m}, words not in plan {e}")
        for line in lines:
            print("  " + line)


if __name__ == "__main__":
    main()
