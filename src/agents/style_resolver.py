"""Style resolver — loosely-coupled theme resolution.

Public API:
  resolve_theme(theme_name) → dict   # callable from any node
  DEFAULT_THEME                       # fallback constant

Graph node:
  style_resolver_node(state) → {theme_element, resolved_theme}

Reads:  theme_name
Writes: theme_element, resolved_theme
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any

import yaml

from src.state import PresentationState

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@functools.lru_cache(maxsize=8)
def _load_yaml(relpath: str) -> dict[str, Any]:
    path = _KNOWLEDGE_DIR / relpath
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


DEFAULT_THEME: dict[str, Any] = {
    "name": "corporate-slate",
    "mode": "light",
    "is_dark": False,
    "chart_colors": ["2563EB", "0EA5E9", "10B981", "F59E0B", "EF4444", "8B5CF6"],
    "chart_colors_json": '["2563EB","0EA5E9","10B981","F59E0B","EF4444","8B5CF6"]',
    "element": '<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" '
               'accentAlt="0EA5E9" positive="15803D" negative="DC2626" '
               'warning="B45309" textMain="16202E" textMuted="55627A" '
               'border="E2E8F0" chartSurface="FFFFFF" chartInk="334155" />',
}

_TOKEN_KEYS = [
    "surface", "surfaceAlt", "accent", "accentAlt",
    "positive", "negative", "warning",
    "textMain", "textMuted", "border",
    "chartSurface", "chartInk",
]


def resolve_theme(theme_name: str) -> dict[str, Any]:
    """Resolve a theme name to a full theme dict.

    Returns: {name, mode, is_dark, chart_colors, chart_colors_json, element}
    Callable from any node — not coupled to the graph.
    """
    if not theme_name or theme_name == "corporate-slate":
        return dict(DEFAULT_THEME)

    palettes = _load_yaml("theme/palettes.yaml")
    palette_data = (palettes.get("palettes") or {}).get(theme_name)
    if not palette_data:
        logger.warning(f"theme '{theme_name}' not found, using default")
        return dict(DEFAULT_THEME)

    tokens = {k: palette_data[k] for k in _TOKEN_KEYS if k in palette_data}
    mode = palette_data.get("mode", "light")
    chart_colors = palette_data.get("chartColors", DEFAULT_THEME["chart_colors"])

    token_attrs = " ".join(f'{k}="{v}"' for k, v in tokens.items())
    element = f"<Theme {token_attrs} />"

    return {
        "name": theme_name,
        "mode": mode,
        "is_dark": mode == "dark",
        "chart_colors": chart_colors,
        "chart_colors_json": str(chart_colors).replace("'", '"'),
        "element": element,
    }


def style_resolver_node(state: PresentationState) -> dict[str, Any]:
    """LangGraph node: resolve theme and write to state."""
    theme_name = state.get("theme_name", "")
    theme = resolve_theme(theme_name)
    logger.info(f"style_resolver: {theme['name']} ({theme['mode']})")
    return {
        "theme_element": theme["element"],
        "resolved_theme": theme,
    }
