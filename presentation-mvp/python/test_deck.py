"""Exercise deck assembly + compile without an API key.

A stateful fake xml_provider hands out one distinct, valid slide XML per slide.
Checks: 3 <Slide> blocks in deck.xml, one shared <Theme>, deck compiles,
theme_consistent True, per-slide + deck evaluation recorded.

    python python/test_deck.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import deck  # noqa: E402
import theme as theme_lib  # noqa: E402
from models import TokenUsage  # noqa: E402

# Must match what deck._canonical_theme("dark") resolves to, so the assembled
# deck stays theme_consistent.
THEME = theme_lib.theme_element(theme_lib.resolve("dark"))

SLIDE_1 = THEME + """
<Slide>
  <VStack w="1280" h="720" padding="72" gap="24" backgroundColor="$surface" alignItems="start" justifyContent="center">
    <Text fontSize="44" bold="true" color="$textMain">Quarterly Business Review</Text>
    <Shape shapeType="rect" w="120" h="6" backgroundColor="$accent" />
    <Text fontSize="22" color="$textMuted" lineHeight="1.45" w="960">Revenue grew 18% quarter over quarter on enterprise expansion and better net retention, while operating margin held steady.</Text>
    <Text fontSize="16" italic="true" color="$textMuted">Prepared for the executive team</Text>
  </VStack>
</Slide>
"""

SLIDE_2 = THEME + """
<Slide>
  <VStack w="1280" h="720" padding="64" gap="28" backgroundColor="$surface" alignItems="start">
    <Text fontSize="40" bold="true" color="$textMain">Where We Landed</Text>
    <HStack w="1152" h="300" gap="28" justifyContent="spaceBetween">
      <VStack grow="1" h="300" padding="24" gap="10" backgroundColor="$surfaceAlt" borderRadius="12" justifyContent="center">
        <Text fontSize="16" color="$textMuted">ARR</Text>
        <Text fontSize="42" bold="true" color="$textMain">$42.8<Span fontSize="20">M</Span></Text>
        <Text fontSize="14" color="$positive">+18% QoQ</Text>
      </VStack>
      <VStack grow="1" h="300" padding="24" gap="10" backgroundColor="$surfaceAlt" borderRadius="12" justifyContent="center">
        <Text fontSize="16" color="$textMuted">Net Revenue Retention</Text>
        <Text fontSize="42" bold="true" color="$textMain">114<Span fontSize="20">%</Span></Text>
        <Text fontSize="14" color="$positive">+3 pts QoQ</Text>
      </VStack>
    </HStack>
  </VStack>
</Slide>
"""

SLIDE_3 = THEME + """
<Slide>
  <VStack w="1280" h="720" padding="64" gap="24" backgroundColor="$surface" alignItems="start">
    <Text fontSize="38" bold="true" color="$textMain">Revenue Trajectory</Text>
    <HStack w="1152" h="470" gap="32" alignItems="start">
      <VStack w="620" h="470" gap="8">
        <Chart chartType="bar" w="620" h="440" showLegend="false" chartColors='["3B82F6"]'>
          <ChartSeries name="Revenue ($M)">
            <ChartDataPoint label="Q2 FY25" value="28.4" />
            <ChartDataPoint label="Q3 FY25" value="31.2" />
            <ChartDataPoint label="Q4 FY25" value="34.9" />
            <ChartDataPoint label="Q1 FY26" value="37.1" />
            <ChartDataPoint label="Q2 FY26" value="40.3" />
            <ChartDataPoint label="Q3 FY26" value="42.8" />
          </ChartSeries>
        </Chart>
      </VStack>
      <VStack w="500" h="470" gap="12">
        <Text fontSize="18" color="$textMain" bold="true">The read</Text>
        <Text fontSize="16" color="$textMuted" lineHeight="1.5" w="500">Six straight quarters of growth, accelerating in H2 on enterprise wins. Next quarter we shift spend toward expansion and retention.</Text>
      </VStack>
    </HStack>
  </VStack>
</Slide>
"""


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="pom-deck-")
    failures: list[str] = []
    try:
        spec = {
            "title": "Test Deck",
            "theme": "dark",
            "slides": [
                {"request": "opener", "components": ["title", "narrative", "caption"]},
                {"request": "kpis", "components": ["title", "kpi_row"]},
                {"request": "chart", "components": ["title", "chart", "narrative"]},
            ],
        }
        deck_ir = deck.from_spec(spec)

        seq = [SLIDE_1, SLIDE_2, SLIDE_3]
        state = {"i": 0}

        def provider(_s, _u, _a):
            xml = seq[min(state["i"], len(seq) - 1)]
            state["i"] += 1
            return xml, TokenUsage(input=100, output=40)

        out = deck.generate_deck(
            deck_ir,
            output_root=Path(tmp),
            dry_run=False,
            xml_provider=provider,
        )
        dev = json.loads(out.read_text(encoding="utf-8"))
        deck_xml = (out.parent / "deck.xml").read_text(encoding="utf-8")

        print(f"slide_count={dev['slide_count']} "
              f"theme_consistent={dev['theme_consistent']} "
              f"deck_compile={dev['deck_compilation']['status']} "
              f"passed={dev['passed']} tokens={dev['tokens']}")

        if deck_xml.count("<Theme") != 1:
            failures.append(f"deck.xml should have exactly 1 <Theme>, has {deck_xml.count('<Theme')}")
        if deck_xml.count("<Slide>") != 3:
            failures.append(f"deck.xml should have 3 <Slide>, has {deck_xml.count('<Slide>')}")
        if dev["deck_compilation"]["status"] != "success":
            failures.append("deck should compile")
        if not dev["theme_consistent"]:
            failures.append("theme should be consistent")
        if dev["slide_count"] != 3 or len(dev["slides"]) != 3:
            failures.append("expected 3 slide summaries")
        if dev["tokens"]["input"] != 300:
            failures.append(f"expected 300 input tokens summed, got {dev['tokens']['input']}")
        if not all(s["compiled"] for s in dev["slides"]):
            failures.append("every slide should compile individually")
        if not dev["passed"]:
            failures.append("deck should PASS (all slides pass + deck compiles clean)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\ndeck assembly test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
