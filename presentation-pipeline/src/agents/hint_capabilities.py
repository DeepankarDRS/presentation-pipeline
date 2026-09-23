"""Design-hint capabilities — what a visual-intent may ask for, per component kind.

Renders knowledge/core/hint-capabilities.yaml for both sides of the hint so the
planner only asks for treatments the generator can build without breaking a
core node:
  - planner_capabilities_section()  -> slide_component_planner system prompt
  - visual_intent_techniques(kinds) -> generator system prompt (this slide's kinds only)
  - hint_scopes(kinds)              -> generator user prompt, one line per component
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

_CAPABILITIES_YAML = Path(__file__).resolve().parent.parent / "knowledge" / "core" / "hint-capabilities.yaml"


@functools.lru_cache(maxsize=1)
def load_capabilities() -> dict[str, Any]:
    return yaml.safe_load(_CAPABILITIES_YAML.read_text(encoding="utf-8")) or {}


def _kind(kind: str) -> dict[str, Any]:
    return (load_capabilities().get("kinds") or {}).get(kind) or {}


def planner_capabilities_section() -> str:
    """One line per kind: the treatment intents it supports, plus what it must never get."""
    caps = load_capabilities()
    treatments = caps.get("treatments") or {}
    lines: list[str] = []
    for kind, meta in (caps.get("kinds") or {}).items():
        intents = "; ".join(treatments[t]["intent"] for t in meta.get("treatments", []))
        line = f"- **{kind}**: {intents}"
        if meta.get("never"):
            line += f". NEVER: {meta['never']}"
        lines.append(line)
    return "\n".join(lines)


def visual_intent_techniques(kinds: list[str]) -> str:
    """'- id (intent): technique' lines for the treatments these kinds support, in YAML order."""
    wanted = {t for k in kinds for t in _kind(k).get("treatments", [])}
    treatments = load_capabilities().get("treatments") or {}
    return "\n".join(
        f"- {t} ({meta['intent']}): {meta['technique']}"
        for t, meta in treatments.items() if t in wanted
    )


def hint_scopes(kinds: list[str]) -> dict[str, str]:
    """kind -> 'treatments: a, b, c. never: ...' for the generator's per-component line."""
    scopes: dict[str, str] = {}
    for kind in dict.fromkeys(kinds):
        meta = _kind(kind)
        if not meta:
            continue
        scope = "treatments: " + ", ".join(meta.get("treatments", []))
        if meta.get("never"):
            scope += f". never: {meta['never']}"
        scopes[kind] = scope
    return scopes
