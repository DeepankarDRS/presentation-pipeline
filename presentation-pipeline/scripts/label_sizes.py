"""A test deck for the label tier (derived-nodes-design §14.4 #4, planning decision D8).

    python -m scripts.label_sizes [--out output/label-test]

Two slides (light, dark) with the same mono label at 10 / 11 / 12 / 14 px in three places a block puts
one: a kicker over a headline, a KPI tile label, a table caption. Inter + JetBrains Mono are embedded, so
it draws the same on any machine. At 1280 x 720 one px is 0.75 pt: 10 px = 7.5 pt, 12 px = 9 pt,
14 px = 10.5 pt. View it at 100% on a laptop and full-screen on the projector or a big screen from
where the audience sits; the label tier is the smallest size you can read comfortably there.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.compiler.font_embed import embed_deck_fonts  # noqa: E402
from src.compiler.pptx_merge import merge_pptx_files  # noqa: E402

SIZES = (10, 11, 12, 14)
LIGHT = dict(bg="F1ECE2", ink="111311", muted="6E6B63", panel="FFFFFF", line="D8D2C4", accent="A8441F", name="LIGHT")
DARK = dict(bg="0D0F0C", ink="F7F5EF", muted="A3A59C", panel="171A16", line="33372F", accent="C9F03D", name="DARK")


def row(p: dict, size: int) -> str:
    mono = f'fontFamily="JetBrains Mono" letterSpacing="1.6" fontSize="{size}"'
    return f"""
    <HStack gap="28" alignItems="stretch">
      <VStack w="150" justifyContent="center"><Text fontFamily="JetBrains Mono" fontSize="22" bold="true" color="$ink">{size} px</Text>
        <Text fontFamily="Inter" fontSize="14" color="$muted">{size * 0.75:g} pt</Text></VStack>
      <VStack grow="1" gap="6" justifyContent="center">
        <Text {mono} color="$accent">EXECUTIVE SUMMARY · 02</Text>
        <Text fontFamily="Inter" fontSize="26" bold="true" color="$ink">The account spends at scale, not yet at a profit.</Text>
      </VStack>
      <VStack w="300" gap="6" padding="14" backgroundColor="$panel" border.color="$line" border.width="1" justifyContent="center">
        <Text {mono} color="$muted">BLENDED ROAS</Text>
        <Text fontFamily="Inter" fontSize="44" bold="true" color="$ink">0.33x</Text>
        <Text {mono} color="$accent">H1 FY27 · TARGET 1.0x</Text>
      </VStack>
      <VStack w="260" gap="6" justifyContent="center">
        <Text {mono} color="$muted">TABLE 3 · ROAS BY PLATFORM</Text>
        <Text fontFamily="Inter" fontSize="14" color="$ink">Flipkart 0.34x · Zomato 0.32x</Text>
      </VStack>
    </HStack>"""


def slide(p: dict) -> str:
    rows = "".join(row(p, s) for s in SIZES)
    return f"""<Theme bg="{p['bg']}" ink="{p['ink']}" muted="{p['muted']}" panel="{p['panel']}" line="{p['line']}" accent="{p['accent']}" />
<Slide>
  <VStack w="1280" h="720" backgroundColor="$bg" padding="40" gap="14" alignItems="stretch">
    <Text fontFamily="Inter" fontSize="20" bold="true" color="$ink">Label tier test ({p['name']}): the same mono label at four sizes</Text>
    <VStack grow="1" gap="10" justifyContent="spaceBetween" alignItems="stretch">{rows}
    </VStack>
  </VStack>
</Slide>
"""


def build(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, p in enumerate((LIGHT, DARK), 1):
        xml = out / f"slide-{i}.xml"
        xml.write_text(slide(p), encoding="utf-8")
        build_dir = out / f"build-{i}"
        subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(xml), str(build_dir)],
                       check=True, capture_output=True, env={**__import__("os").environ, "POM_FIT_GROW": "0"})
        result = json.loads((build_dir / "compile-result.json").read_text(encoding="utf-8"))
        if result["status"] != "success":
            raise RuntimeError(f"slide {i} did not compile: {result.get('diagnostics')}")
        parts.append(build_dir / "presentation.pptx")
    deck = merge_pptx_files(parts, out / "label-sizes.pptx")
    embed_deck_fonts(deck)
    return deck


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "label-test")
    print(build(ap.parse_args().out))


if __name__ == "__main__":
    main()
