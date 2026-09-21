"""Blueprint selector — deterministic matching of slide plans to blueprints.

No LLM involved. Scores each blueprint against the slide plan's component
kinds, slide_type, and density, then returns the best match (or None for
grammar-only fallback).
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@functools.lru_cache(maxsize=1)
def _load_blueprints() -> dict[str, dict[str, Any]]:
    path = _KNOWLEDGE_DIR / "core" / "blueprints.yaml"
    if not path.exists():
        logger.warning("blueprint_selector: blueprints.yaml not found")
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def _score_blueprint(
    bp_name: str,
    bp: dict[str, Any],
    slide_type: str,
    kinds: set[str],
    density: str,
    chart_count: int,
) -> float:
    """Score a blueprint against the slide plan. Higher = better match."""
    match = bp.get("match", {})
    score = 0.0

    allowed_types = match.get("slide_types", [])
    if allowed_types and slide_type not in allowed_types:
        return -1.0

    if allowed_types and slide_type in allowed_types:
        score += 20.0

    required_all = set(match.get("component_kinds_all", []))
    if required_all and not required_all.issubset(kinds):
        return -1.0
    score += len(required_all & kinds) * 10.0

    required_any = set(match.get("component_kinds_any", []))
    if required_any:
        overlap = required_any & kinds
        if not overlap:
            score -= 5.0
        else:
            score += len(overlap) * 3.0

    excluded = set(match.get("component_kinds_none", []))
    if excluded and excluded & kinds:
        return -1.0

    allowed_density = match.get("density", [])
    if allowed_density and density not in allowed_density:
        score -= 10.0
    elif allowed_density and density in allowed_density:
        score += 5.0

    min_charts = match.get("min_charts", 0)
    if min_charts and chart_count < min_charts:
        return -1.0
    if min_charts and chart_count >= min_charts:
        score += 5.0 + chart_count * 2.0

    return score


def select_blueprint(slide_plan: dict[str, Any]) -> dict[str, Any] | None:
    """Pick the best blueprint for a slide plan.

    Returns the full blueprint dict (with structure, reference_xml, etc.)
    or None if no blueprint matches well enough (generator uses grammar).
    """
    blueprints = _load_blueprints()
    if not blueprints:
        return None

    slide_type = slide_plan.get("slide_type", "content")
    components = slide_plan.get("components", [])
    kinds = {c.get("kind", "") for c in components} - {""}
    density = slide_plan.get("density", "normal")
    chart_count = sum(1 for c in components if c.get("kind") == "chart")

    best_name = None
    best_score = 0.0
    best_bp = None

    for name, bp in blueprints.items():
        s = _score_blueprint(name, bp, slide_type, kinds, density, chart_count)
        if s > best_score:
            best_score = s
            best_name = name
            best_bp = bp

    if best_bp is None or best_score < 10.0:
        logger.info(
            "blueprint_selector: no match (best=%s score=%.1f) → grammar fallback",
            best_name, best_score,
        )
        return None

    logger.info(
        "blueprint_selector: matched '%s' (score=%.1f) for kinds=%s type=%s",
        best_name, best_score, sorted(kinds), slide_type,
    )
    result = dict(best_bp)
    result["blueprint_name"] = best_name
    return result
