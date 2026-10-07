"""No literal hex colour in the knowledge files or prompts (2026-10-07).

The LLM copies example colours onto every deck, whatever its palette. Colours come
from palette tokens ($accentSoft, $negativeText, $neutral, ...). Allowed literals:
chartColors (POM does not resolve tokens there), a black shadow, the <Theme> element
itself, and lines that show a WRONG form.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
_ATTR = re.compile(r'([A-Za-z][\w.]*)=\\?["\']#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\\?["\']')
_COLOR_ATTR = re.compile(r"(?i)colou?r|fill|gradient")
_WRONG_LINE = re.compile(r"wrong:|INVALID|<Theme ")


def literal_colors(text: str) -> list[tuple[int, str]]:
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if _WRONG_LINE.search(line):
            continue
        for attr, value in _ATTR.findall(line):
            if not _COLOR_ATTR.search(attr) or attr == "chartColors":
                continue
            if attr.startswith("shadow") and set(value) == {"0"}:
                continue
            found.append((n, f"{attr}={value}"))
    return found


def test_no_literal_colors_in_knowledge_or_prompts():
    files = [p for p in (SRC / "knowledge").rglob("*.yaml") if "theme" not in p.parts]
    files += list((SRC / "prompts").rglob("*.j2"))
    hits = {str(p.relative_to(SRC)): literal_colors(p.read_text(encoding="utf-8")) for p in files}
    hits = {k: v for k, v in hits.items() if v}
    assert not hits, f"use a palette token instead: {hits}"


def test_detector_catches_and_allows():
    assert literal_colors('<Shape fill.color="DCFCE7" color="15803D" />') == [
        (1, "fill.color=DCFCE7"), (1, "color=15803D")]
    assert literal_colors('<Chart chartColors=\'["2563EB"]\' shadow.color="000" />') == []
    assert literal_colors('<ChartDataPoint label="Feb" value="120" />') == []


def test_layout_audit_reports_literal_colors_only_as_report():
    from src.compiler.layout_audit import REPORT_ONLY_CODES, audit_layout
    xml = ('<Theme accent="2563EB" /><Slide><VStack w="1280" h="720" backgroundColor="$surface">'
           '<VStack backgroundColor="FDEDED" shadow.color="000"><Text color="$accent">x</Text></VStack>'
           '</VStack></Slide>')
    hits = [i for i in audit_layout(xml) if i["code"] == "LITERAL_COLOR"]
    assert len(hits) == 1 and hits[0]["message"].startswith("1 colour")
    assert "LITERAL_COLOR" in REPORT_ONLY_CODES
