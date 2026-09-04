"""YAML test case loader.

Loads test case definitions from tests/cases/*.yaml and converts them
into PresentationState initial states ready for pipeline execution.

Usage:
    from src.utils.case_loader import load_case, load_all_cases, case_to_state

    case = load_case("kpi-row")
    state = case_to_state(case)
    cases = load_all_cases()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.state import PresentationState, initial_state

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
_CASES_DIR = _PIPELINE_ROOT / "tests" / "cases"


def load_case(name: str) -> dict[str, Any]:
    """Load a single test case by name (without .yaml extension)."""
    path = _CASES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Test case not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_all_cases(directory: Path | None = None) -> list[dict[str, Any]]:
    """Load all YAML test cases from the cases directory."""
    cases_dir = directory or _CASES_DIR
    if not cases_dir.exists():
        return []
    cases = []
    for path in sorted(cases_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            cases.append(data)
    return cases


def case_to_state(
    case: dict[str, Any],
    *,
    run_id: str | None = None,
    critic_mode: str = "auto",
    deck_min_threshold: int = 0,
) -> PresentationState:
    """Convert a YAML test case dict into a PresentationState."""
    name = case.get("name", "unnamed")
    rid = run_id or f"case-{name}"

    supplied = case.get("supplied_content") or {}
    if isinstance(supplied, str):
        supplied = {}

    return initial_state(
        run_id=rid,
        raw_request=case.get("request", case.get("objective", "")),
        theme_name=case.get("theme", ""),
        supplied_content=supplied if supplied else None,
        test_case=case,
        deck_min_threshold=deck_min_threshold,
        critic_mode=critic_mode,
    )
