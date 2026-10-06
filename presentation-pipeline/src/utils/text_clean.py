"""Remove characters that cannot appear in XML from LLM output (found in the step 0 test-PC run).

A QBR slide came back with "$28.1M \\x00b\\x00b +22%": NUL characters in the model's text. POM wrote them into
the slide XML, PowerPoint refused to open the deck and every XML reader failed on it. A slide must survive one
bad character, so text from a model is cleaned where it enters the pipeline (the planner's content_data and the
generator's / repairers' XML in `normalize_xml`).
"""

from __future__ import annotations

import re
from typing import Any

# XML 1.0 forbids 0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F, and the non-characters U+FFFE / U+FFFF
ILLEGAL_XML_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def strip_illegal(text: str) -> tuple[str, int]:
    """(text without XML-illegal characters, how many were removed)."""
    cleaned, n = ILLEGAL_XML_CHARS.subn("", text)
    return cleaned, n


def clean_data(value: Any) -> Any:
    """The same strings, cleaned, anywhere inside lists / dicts (a plan's content_data)."""
    if isinstance(value, str):
        return strip_illegal(value)[0]
    if isinstance(value, list):
        return [clean_data(v) for v in value]
    if isinstance(value, dict):
        return {k: clean_data(v) for k, v in value.items()}
    return value
