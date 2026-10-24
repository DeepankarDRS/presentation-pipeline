"""Generator-only runs: draw a saved run's slide plans again with today's generator (models.yaml), no planning.

    python -m scripts.tools.gen_from_plans output/runs/225dc465d0f4 output/runs/6066f16beedd \
        --requests cheffin.txt xtsy.txt --label gen61 --bundle

Each run folder needs slides.json + run-manifest.json (an output/runs/<run_id>/ folder, or a bundle's
decks/<case>__rN/). The plans and the theme are the saved run's; planning is skipped (the graph's
route_after_start goes straight to style_resolver when slide_plans are set), so only the generator /
validator / repairer steps run, on the models models.yaml names for them. Critic off, as in eval runs.

--requests: one text file per run with the exact brief that run was made from (the generator reads it as the
slide objective). The UI does not save the brief, so it has to be supplied; its fingerprint is checked against
the saved run's request_sha256 and the run stops on a mismatch (--force to run anyway).

Each new run lands in output/runs/<new_run_id>/ (deck, slides.json, run-manifest.json) like any run;
--bundle zips them as output/gen-only/<label>.zip with a summary.json (source run -> new run, cost).
Model comparison background: docs/eval/model-compare-2026-10-21/README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Any

_PIPELINE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PIPELINE_ROOT))


def request_fingerprint(request: str, supplied_content: Any = None) -> str:
    """The evaluator's request_sha256 (src/agents/review/evaluator.py _run_provenance)."""
    blob = json.dumps({"request": request, "supplied_content": supplied_content},
                      sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load(folder: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    slides = json.loads((folder / "slides.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "run-manifest.json").read_text(encoding="utf-8"))
    plans = sorted((s["slide_plan"] for s in slides), key=lambda p: p.get("slide_index", 0))
    return plans, manifest


def run(folder: Path, request: str, force: bool) -> dict[str, Any]:
    from src.graph import compile_graph
    from src.state import initial_state
    from src.utils.logging_config import set_context

    plans, manifest = load(folder)
    saved = (manifest.get("request_sha256") or "")[:16]
    mine = request_fingerprint(request)
    if saved and saved != mine and not force:
        raise SystemExit(f"{folder}: the request file does not match the saved run (sha {mine} vs {saved}); "
                         "use the exact brief of that run, or --force")
    run_id = uuid.uuid4().hex[:12]
    set_context(run_id=run_id)
    state = initial_state(run_id=run_id, raw_request=request, theme_name=manifest.get("theme") or "",
                          deck_min_threshold=len(plans), critic_mode="off")
    state["slide_plans"] = plans
    cfg = {"run_name": f"gen-only-{run_id}", "tags": ["presentation-pipeline", "gen-only"],
           "metadata": {"run_id": run_id, "source_run": folder.name}, "recursion_limit": 150}
    print(f"{folder.name}: {len(plans)} slide plans, theme {state['theme_name'] or 'default'} -> run {run_id}", flush=True)
    final: dict[str, Any] = {}
    for final in compile_graph().stream(state, config=cfg, stream_mode="values"):
        pass
    out = _PIPELINE_ROOT / "output" / "runs" / run_id
    new = json.loads((out / "run-manifest.json").read_text(encoding="utf-8")) if (out / "run-manifest.json").exists() else {}
    row = {"source_run": folder.name, "source_commit": manifest.get("git_commit"), "run_id": run_id,
           "request_match": saved == mine, "passed": new.get("passed"), "cost": (new.get("cost") or {}).get("total_usd"),
           "models": (new.get("cost") or {}).get("models_used"), "pptx": final.get("pptx_path")}
    print(f"  done: passed {row['passed']}, cost ${row['cost']}, models {row['models']}, {out}", flush=True)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", type=Path, help="saved run folders (slides.json + run-manifest.json)")
    ap.add_argument("--requests", nargs="+", type=Path, required=True, help="one brief text file per run, same order")
    ap.add_argument("--label", default="gen-only")
    ap.add_argument("--bundle", action="store_true", help="zip the new run folders to output/gen-only/<label>.zip")
    ap.add_argument("--force", action="store_true", help="run even when a brief does not match its saved run")
    a = ap.parse_args(argv)
    if len(a.requests) != len(a.runs):
        ap.error("give one --requests file per run folder")
    for f in a.runs:
        if not (f / "slides.json").exists() or not (f / "run-manifest.json").exists():
            ap.error(f"{f}: needs slides.json and run-manifest.json")
    rows = [run(f, r.read_text(encoding="utf-8"), a.force) for f, r in zip(a.runs, a.requests)]
    print(f"total cost ${sum(r['cost'] or 0 for r in rows):.3f}")
    if a.bundle:
        dest = _PIPELINE_ROOT / "output" / "gen-only"
        dest.mkdir(parents=True, exist_ok=True)
        zpath = dest / f"{a.label}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{a.label}/summary.json", json.dumps(rows, indent=1))
            for r in rows:
                out = _PIPELINE_ROOT / "output" / "runs" / r["run_id"]
                for f in sorted(out.rglob("*")):
                    if f.is_file() and "screenshots" not in f.parts:
                        z.write(f, f"{a.label}/{r['run_id']}_from_{r['source_run']}/{f.relative_to(out)}")
        print(f"EMAIL THIS FILE: {zpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
