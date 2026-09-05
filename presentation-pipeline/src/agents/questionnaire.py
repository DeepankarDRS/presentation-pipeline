"""Pre-generation questionnaire — collects audience/style/focus context.

Presents 5 fixed questions via CLI when interactive=True.
Skips entirely in non-interactive mode or when audience_context is pre-supplied.

Reads:  interactive, audience_context, raw_request
Writes: audience_context, theme_name, deck_min_threshold
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from src.state import PresentationState

logger = logging.getLogger(__name__)

_PALETTES_PATH = (
    Path(__file__).resolve().parent.parent / "knowledge" / "theme" / "palettes.yaml"
)

_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "audience",
        "prompt": "Who is the audience?",
        "options": ["Board", "C-suite", "All-hands", "External", "General"],
        "default": "General",
    },
    {
        "key": "data_density",
        "prompt": "How data-heavy should it be?",
        "options": ["High-level story", "Balanced", "Deep-dive"],
        "default": "Balanced",
    },
    # Theme is inserted dynamically from palettes.yaml
    {
        "key": "slide_count",
        "prompt": "How many slides?",
        "options": ["Single slide", "3-5 slides", "6-10 slides", "10+ slides"],
        "default": "Single slide",
    },
    {
        "key": "focus",
        "prompt": "What's the focus?",
        "options": ["Overview", "One metric deep-dive", "Comparison"],
        "default": "Overview",
    },
]


def _load_palette_names() -> list[tuple[str, str]]:
    """Return [(name, tone), ...] from palettes.yaml, light first then dark."""
    if not _PALETTES_PATH.exists():
        return [("corporate-slate", "Corporate / cool blue")]
    data = yaml.safe_load(_PALETTES_PATH.read_text(encoding="utf-8")) or {}
    palettes = data.get("palettes") or {}
    light, dark = [], []
    for name, info in palettes.items():
        tone = info.get("tone", "")
        if info.get("mode") == "dark":
            dark.append((name, tone))
        else:
            light.append((name, tone))
    return light + dark


def _ask(prompt: str, options: list[str], default: str) -> str:
    """Print numbered menu and collect user choice. Returns the selected option."""
    print(f"\n  {prompt}")
    for i, opt in enumerate(options, 1):
        marker = " *" if opt == default else ""
        print(f"    {i}. {opt}{marker}")
    raw = input(f"  Choice [default={default}]: ").strip()
    if not raw:
        return default
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass
    return default


def _slide_count_to_threshold(choice: str) -> int:
    """Map slide count answer to deck_min_threshold."""
    if choice == "Single slide":
        return 0
    return 3


def questionnaire_node(state: PresentationState) -> dict[str, Any]:
    """Collect audience context via interactive CLI questions."""
    if not state.get("interactive"):
        logger.info("questionnaire: skipped (non-interactive)")
        return {}

    if state.get("audience_context"):
        logger.info("questionnaire: skipped (audience_context pre-supplied)")
        return {}

    print("\n" + "=" * 60)
    print("PRE-GENERATION QUESTIONNAIRE")
    print("=" * 60)
    print(f"  Request: {state.get('raw_request', '')[:80]}")
    print("-" * 60)

    answers: dict[str, str] = {}

    # Fixed questions (audience, data_density)
    for q in _QUESTIONS[:2]:
        answers[q["key"]] = _ask(q["prompt"], q["options"], q["default"])

    # Theme question (dynamic from palettes.yaml)
    palette_entries = _load_palette_names()
    theme_options = [f"{name} — {tone}" for name, tone in palette_entries]
    theme_names = [name for name, _ in palette_entries]
    default_theme = "corporate-slate — Corporate / cool blue"
    theme_answer = _ask("Which theme?", theme_options, default_theme)
    theme_idx = theme_options.index(theme_answer) if theme_answer in theme_options else 0
    selected_theme = theme_names[theme_idx]
    answers["theme"] = selected_theme

    # Remaining fixed questions (slide_count, focus)
    for q in _QUESTIONS[2:]:
        answers[q["key"]] = _ask(q["prompt"], q["options"], q["default"])

    threshold = _slide_count_to_threshold(answers["slide_count"])

    print("-" * 60)
    print("  Context collected. Starting pipeline...")
    print("=" * 60)

    logger.info(
        f"questionnaire: audience={answers['audience']}, "
        f"theme={selected_theme}, slides={answers['slide_count']}"
    )

    return {
        "audience_context": answers,
        "theme_name": selected_theme,
        "deck_min_threshold": threshold,
    }
