"""Remove characters that cannot appear in XML from LLM output (found in the step 0 test-PC run).

A QBR slide came back with "$28.1M \\x00b\\x00b +22%": NUL characters in the model's text. POM wrote them into
the slide XML, PowerPoint refused to open the deck and every XML reader failed on it. `find_nul` on the run showed
where they start: the outline planner's `subtitle` (the evidence line, gpt-5-mini), as "Acme Analytics \\x0b\\x0b
Executive Update" on one slide and "$28.1M \\x00b\\x00b +22% \\x00b\\x00b 142" on others. Every run sits between
spaces where a middle dot "·" belongs, so it is a mangled separator. A slide must survive one bad character, so
model text is cleaned where it enters the pipeline: the outline, the planner's content_data and the XML of the
generator / repairers (`normalize_xml`). A mangled separator becomes "·" again; any other illegal character is
removed.
"""

from __future__ import annotations

import re
from typing import Any

# XML 1.0 forbids 0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F, and the non-characters U+FFFE / U+FFFF
ILLEGAL_XML_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


# a mangled "·": a whitespace-delimited token made of control characters, each optionally followed by one hex
# character (seen: NUL+"b" twice, a vertical tab twice; the second run's shape was not kept, it came back as two
# spaces after the first fix, so the match is wide on purpose)
_MANGLED_SEPARATOR = re.compile(r"(?<=\s)(?:[\x00-\x08\x0b\x0c\x0e-\x1f][0-9a-fA-F]?){1,4}(?=\s)")


def strip_illegal(text: str) -> tuple[str, int]:
    """(text with a mangled separator restored and every other XML-illegal character removed, how many fixed)."""
    text, restored = _MANGLED_SEPARATOR.subn("\u00b7", text)
    cleaned, removed = ILLEGAL_XML_CHARS.subn("", text)
    return cleaned, restored + removed


def clean_data(value: Any) -> Any:
    """The same strings, cleaned, anywhere inside lists / dicts (a plan's content_data)."""
    if isinstance(value, str):
        return strip_illegal(value)[0]
    if isinstance(value, list):
        return [clean_data(v) for v in value]
    if isinstance(value, dict):
        return {k: clean_data(v) for k, v in value.items()}
    return value
