"""Load a saved run's plans (+ the XML the generator wrote, + its theme) for a run that starts from plans.

    run = load_run(Path("output/step0/b1/step0-20261006-202429/decks/deck-qbr-data__r1"))
    state = initial_state(run)      # slide_plans set: the graph's route_after_start skips planning

A run folder is a bundle's decks/<case>__rN/ (slides.json + run-manifest.json) or an output/runs/<run_id>/
folder with the same two files. The theme is the one the run used (manifest), not today's palettes.yaml.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_run(folder: Path) -> dict[str, Any]:
    slides = json.loads((folder / "slides.json").read_text(encoding="utf-8"))
    manifest_file = folder / "run-manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    theme = manifest.get("resolved_theme")
    if not theme or not manifest.get("theme_element"):
        from src.agents.style_resolver import resolve_theme
        theme = resolve_theme(manifest.get("theme") or "")
    else:
        theme = {**theme, "element": manifest["theme_element"]}
    case = folder.name.rsplit("__", 1)[0]
    return {
        "case": case,
        "folder": folder,
        "theme": theme,
        "manifest": manifest,
        "slides": [{"number": s["slide_plan"]["slide_index"] + 1, "plan": s["slide_plan"], "xml": s.get("xml") or ""}
                   for s in slides],
    }


def find_runs(root: Path) -> dict[str, Path]:
    """case -> run folder, for every decks/<case>__rN/slides.json under root (first match per case)."""
    out: dict[str, Path] = {}
    for f in sorted(root.glob("**/decks/*/slides.json")):
        case = f.parent.name.rsplit("__", 1)[0]
        out.setdefault(case, f.parent)
    return out


def initial_state(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "slide_plans": [s["plan"] for s in run["slides"]],
        "theme_name": run["theme"].get("name", ""),
        "theme_element": run["theme"]["element"],
        "resolved_theme": run["theme"],
    }
