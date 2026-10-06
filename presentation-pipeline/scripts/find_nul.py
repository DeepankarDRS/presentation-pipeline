"""Find where a NUL / control character enters a run (step 0 run, deck-qbr-data-900d4d: PowerPoint could not open the deck).

    python -m scripts.find_nul output/runs/<run_id>

For every slide folder it checks, in pipeline order, the XML the generator wrote and the validator compiled
(input.xml), what fit-grow wrote (fitted.xml), and every part of the slide's presentation.pptx and the deck's
pptx; plus slides.json and the saved plans. Prints the FIRST stage that has an XML-illegal character
(0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F) with the characters around it, so the cause is the stage before it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def around(text: str, m: re.Match) -> str:
    a, b = max(0, m.start() - 50), min(len(text), m.end() + 50)
    return repr(text[a:b])


def scan_text(label: str, text: str) -> int:
    hits = list(ILLEGAL.finditer(text))
    for m in hits[:3]:
        print(f"  {label}: U+{ord(m.group()):04X} at {m.start()} in ...{around(text, m)}...")
    return len(hits)


def scan_pptx(label: str, path: Path) -> int:
    found = 0
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".xml"):
                continue
            text = z.read(name).decode("utf-8", errors="replace")
            found += scan_text(f"{label} {name}", text)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    a = ap.parse_args()
    total = 0
    for slide in sorted(a.run.glob("slide-*")):
        print(slide.name)
        for stage in ("input.xml", "fitted.xml"):
            f = slide / stage
            if f.exists():
                total += scan_text(f"{slide.name}/{stage}", f.read_text(encoding="utf-8", errors="replace"))
        for pptx in (slide / "presentation.pptx",):
            if pptx.exists():
                total += scan_pptx(f"{slide.name}/presentation.pptx", pptx)
    deck = a.run / "deck" / "presentation.pptx"
    if deck.exists():
        print("deck")
        total += scan_pptx("deck/presentation.pptx", deck)
    sj = a.run / "slides.json"
    if sj.exists():
        print("slides.json")
        total += scan_text("slides.json", json.dumps(json.loads(sj.read_text(encoding="utf-8")), ensure_ascii=False))
    print("illegal characters found:", total)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
