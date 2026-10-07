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

from src.compiler.palette_tokens import derive_tokens
from src.state import PresentationState

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@functools.lru_cache(maxsize=8)
def _load_yaml(relpath: str) -> dict[str, Any]:
    path = _KNOWLEDGE_DIR / relpath
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


_TOKEN_KEYS = [
    "surface", "surfaceAlt", "accent", "accentAlt",
    "positive", "negative", "warning",
    "textMain", "textMuted", "border",
    "chartSurface", "chartInk",
]

_DEFAULT_NAME = "corporate-slate"


def _build_theme(name: str, palette_data: dict[str, Any]) -> dict[str, Any]:
    """One palette entry -> theme dict. Authored tokens, then the derived colour
    roles (src/compiler/palette_tokens.py, 2026-10-07). A light palette without
    chartSurface / chartInk gets surfaceAlt / textMain so $chartSurface always resolves."""
    mode = palette_data.get("mode", "light")
    tokens = {k: palette_data[k] for k in _TOKEN_KEYS if k in palette_data}
    tokens.setdefault("chartSurface", palette_data["surfaceAlt"])
    tokens.setdefault("chartInk", palette_data["textMain"])
    tokens.update(derive_tokens(palette_data))
    chart_colors = list(palette_data.get("chartColors") or [palette_data["accent"]])

    token_attrs = " ".join(f'{k}="{v}"' for k, v in tokens.items())
    return {
        "name": name,
        "mode": mode,
        "is_dark": mode == "dark",
        "chart_colors": chart_colors,
        "chart_colors_json": str(chart_colors).replace("'", '"'),
        # chartColors can't use $tokens: the literal pair for a one-series-in-focus chart
        "chart_focus": {"focus": tokens["accent"], "rest": tokens["neutral"]},
        "element": f"<Theme {token_attrs} />",
    }


def _palettes() -> dict[str, Any]:
    return _load_yaml("theme/palettes.yaml").get("palettes") or {}


# The default is the YAML entry, so its chart colours and tokens cannot drift (2026-10-07).
DEFAULT_THEME: dict[str, Any] = _build_theme(_DEFAULT_NAME, _palettes()[_DEFAULT_NAME])


def resolve_theme(theme_name: str) -> dict[str, Any]:
    """Resolve a theme name to a full theme dict.

    Returns: {name, mode, is_dark, chart_colors, chart_colors_json, chart_focus, element}
    Callable from any node — not coupled to the graph.
    """
    if not theme_name or theme_name == _DEFAULT_NAME:
        return dict(DEFAULT_THEME)

    palette_data = _palettes().get(theme_name)
    if not palette_data:
        logger.warning(f"theme '{theme_name}' not found, using default")
        return dict(DEFAULT_THEME)
    return _build_theme(theme_name, palette_data)


def style_resolver_node(state: PresentationState) -> dict[str, Any]:
    """LangGraph node: resolve theme and write to state."""
    theme_name = state.get("theme_name", "")
    theme = resolve_theme(theme_name)
    logger.info(f"style_resolver: {theme['name']} ({theme['mode']})")
    return {
        "theme_element": theme["element"],
        "resolved_theme": theme,
    }
