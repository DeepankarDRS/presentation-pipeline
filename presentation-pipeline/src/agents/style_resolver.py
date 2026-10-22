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
import json
import logging
from pathlib import Path
from typing import Any

import yaml

from src.compiler.palette_tokens import MAX_CHART_COLORS, derive_tokens, expand_seed
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
    """One palette entry -> theme dict. A `seed:` entry is expanded first
    (palette_tokens.expand_seed, 2026-10-22). Authored tokens, then the derived colour
    roles (src/compiler/palette_tokens.py, 2026-10-07). A light palette without
    chartSurface / chartInk gets surfaceAlt / textMain so $chartSurface always resolves.
    chartColors become chart1..chartN tokens: POM 10.3.0 resolves $tokens inside
    chartColors (verified 2026-10-22), so charts follow a theme switch."""
    if "seed" in palette_data:
        palette_data = expand_seed(palette_data["seed"])
    mode = palette_data.get("mode", "light")
    tokens = {k: palette_data[k] for k in _TOKEN_KEYS if k in palette_data}
    tokens.setdefault("chartSurface", palette_data["surfaceAlt"])
    tokens.setdefault("chartInk", palette_data["textMain"])
    tokens.update(derive_tokens(palette_data))
    chart_colors = [str(c).upper() for c in (palette_data.get("chartColors") or [palette_data["accent"]])]
    chart_colors = chart_colors[:MAX_CHART_COLORS]
    # chart1..chartMAX always exist (a short list repeats), so any $chartN a slide uses resolves
    tokens.update({f"chart{i + 1}": chart_colors[i % len(chart_colors)] for i in range(MAX_CHART_COLORS)})
    chart_refs = [f"$chart{i}" for i in range(1, len(chart_colors) + 1)]

    token_attrs = " ".join(f'{k}="{v}"' for k, v in tokens.items())
    return {
        "name": name,
        "mode": mode,
        "is_dark": mode == "dark",
        "chart_colors": chart_colors,
        "chart_tokens": chart_refs,
        "chart_colors_json": json.dumps(chart_refs, separators=(",", ":")),
        # the pair for a one-series-in-focus chart
        "chart_focus": {"focus": "$accent", "rest": "$neutral"},
        "element": f"<Theme {token_attrs} />",
    }


def _palettes() -> dict[str, Any]:
    return _load_yaml("theme/palettes.yaml").get("palettes") or {}


# The default is the YAML entry, so its chart colours and tokens cannot drift (2026-10-07).
DEFAULT_THEME: dict[str, Any] = _build_theme(_DEFAULT_NAME, _palettes()[_DEFAULT_NAME])


def palette_entry(name: str) -> dict[str, Any]:
    """A palette as authored tokens: a `seed:` entry comes back expanded."""
    entry = _palettes()[name]
    return expand_seed(entry["seed"]) if "seed" in entry else entry


def theme_names() -> list[str]:
    """Every palette name a run may ask for (palettes.yaml)."""
    return list(_palettes())


def resolve_theme(theme_name: str) -> dict[str, Any]:
    """Resolve a theme name to a full theme dict.

    Returns: {name, mode, is_dark, chart_colors, chart_tokens, chart_colors_json, chart_focus, element}
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
