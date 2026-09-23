"""Quality baseline: run cases through the UNCHANGED pipeline and score every slide.

    python -m scripts.eval_run --label baseline --bundle              # gate cases (needs OPENAI_API_KEY)
    python -m scripts.eval_run kpi-row single-table --label smoke --repeat 2
    python -m scripts.eval_run --fixtures tests/fixtures/golden/gj-h1-deck --label golden   # LLM-free

Writes output/eval/<label>-<ts>/: results.json, summary.md, slides/<case>/slide-<i>/
(input.xml, fitted.xml, compile-result.json, presentation.pptx), renders/ (PowerPoint
COM, when available). --bundle zips that folder for email; import it on the build
device with `python -m scripts.eval_import <zip>`.

Per slide: first_pass_ok (compiled at retry 0), retries, max_tier, auto-fixes by code
(first attempt's normalize_result.issues), blocking codes during retries, layout issues
(final attempt), fit-grow changes, planner kinds + design hints, card fill ratios and
patterns (scripts/eval_metrics.py). A case with `golden: <dir>` is also scored per slide
against that fixture deck (card-pattern match).

The graph is streamed (same setup as src.graph.run) because in decks slide_router
resets normalize_result / layout_issues / retry_count per slide — the final state
alone has no per-slide numbers. Pipeline code is not modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PIPELINE_ROOT))

from scripts.eval_metrics import LOW_FILL, card_metrics, pattern_match  # noqa: E402
from src.compiler.layout_audit import audit_layout  # noqa: E402
from src.utils.case_loader import load_case  # noqa: E402

# Acceptance gate (DECIDE 2026-09-23): the user's deck prompts + single-slide cases.
GATE_CASES = [
    "eval-categorized-list-routing",
    "eval-chart-vs-kpi-disambiguation",
    "eval-table-vs-kpi-disambiguation",
    "maximal-density",
    "single-table",
    "kpi-row",
    "chart-and-table",
    "mixed-executive-slide",
    "gj-h1-regen",
]
_COMPILE_SCRIPT = _PIPELINE_ROOT / "src" / "node" / "compile-pom.js"


# ── running ─────────────────────────────────────────────────────────────────

def _stream_case(case: dict[str, Any], run_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run one case; return (final_state, validator attempts tagged with slide/retry)."""
    from src.graph import compile_graph
    from src.state import initial_state
    from src.utils.logging_config import set_context

    set_context(run_id=run_id)
    supplied = case.get("supplied_content")
    state = initial_state(
        run_id=run_id,
        raw_request=case.get("request", case.get("objective", "")),
        theme_name=case.get("theme", ""),
        deck_min_threshold=(case.get("expect") or {}).get("slide_count", 0),
        critic_mode="off",
        supplied_content=supplied if isinstance(supplied, dict) else None,
        test_case=case,
    )
    config = {
        "run_name": f"pom-eval-{run_id}",
        "tags": ["presentation-pipeline", "eval"],
        "metadata": {"run_id": run_id, "theme": state["theme_name"], "critic_mode": "off"},
        "recursion_limit": 150,
    }
    final: dict[str, Any] = {}
    attempts: list[dict[str, Any]] = []
    cur = {"current_slide_index": 0, "retry_count": 0, "retry_tier": 0}
    for mode, chunk in compile_graph().stream(state, config=config, stream_mode=["updates", "values"]):
        if mode == "values":
            final = chunk
            continue
        for node, update in chunk.items():
            if not isinstance(update, dict):
                continue
            if node == "validator":
                attempts.append({"slide": cur["current_slide_index"], "retry": cur["retry_count"],
                                 "tier": cur["retry_tier"], **update})
            cur.update({k: update[k] for k in cur if k in update})
    return final, attempts


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _slide_row(index: int, tries: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    first, last = tries[0], tries[-1]
    ok = bool((last.get("compile_result") or {}).get("ok"))
    pptx = (last.get("compile_result") or {}).get("pptx_path") if ok else None
    blocking = Counter(
        d.get("type", "?") for t in tries if not (t.get("compile_result") or {}).get("ok")
        for d in (t.get("compile_result") or {}).get("diagnostics", [])
    )
    auto = Counter(i["code"] for i in (first.get("normalize_result") or {}).get("issues", []) if i.get("auto_fixed"))
    return {
        "index": index,
        "compiled": ok,
        "first_pass_ok": first["retry"] == 0 and bool((first.get("compile_result") or {}).get("ok")),
        "retries": max(t["retry"] for t in tries),
        "max_tier": max(t["tier"] for t in tries),
        "auto_fixes": dict(auto),
        "blocking": dict(blocking),
        "layout_issues": dict(Counter(i.get("code", "?") for i in last.get("layout_issues") or [])),
        "fit_grow": _read_json(Path(pptx).parent / "compile-result.json").get("fitGrow", []) if pptx else [],
        "components": [{k: c.get(k, "") for k in ("kind", "weight", "design_hint")}
                       for c in plan.get("components", [])],
        "cards": card_metrics(pptx) if pptx else [],
        "_dir": str(Path(pptx).parent) if pptx else None,
    }


def evaluate_case(case: dict[str, Any], repeat: int) -> dict[str, Any]:
    name = case.get("name", "unnamed")
    run_id = f"{name}-{uuid.uuid4().hex[:6]}"
    print(f"\n>> {name} (run {repeat}) ...", flush=True)
    t0 = time.time()
    try:
        final, attempts = _stream_case(case, run_id)
        error = None
    except Exception as e:  # one broken case must not lose the whole eval
        final, attempts, error = {}, [], f"{type(e).__name__}: {e}"
        print(f"   ERROR: {error}")
    by_slide: dict[int, list[dict[str, Any]]] = {}
    for a in attempts:
        by_slide.setdefault(a["slide"], []).append(a)
    plans = final.get("slide_plans") or []
    evaluation = final.get("evaluation") or {}
    return {
        "name": name,
        "repeat": repeat,
        "run_id": run_id,
        "passed": bool(final.get("passed")),
        "error": error,
        "tokens_in": (evaluation.get("tokens") or {}).get("total_in", 0),
        "tokens_out": (evaluation.get("tokens") or {}).get("total_out", 0),
        "cost": (evaluation.get("cost") or {}).get("total_usd", 0.0),
        "elapsed": round(time.time() - t0, 1),
        "slides": [_slide_row(i, by_slide[i], plans[i] if i < len(plans) else {}) for i in sorted(by_slide)],
        "_deck_pptx": final.get("pptx_path"),
    }


def evaluate_fixtures(xml_dir: Path, out_dir: Path) -> dict[str, Any]:
    """LLM-free: compile every *.xml in xml_dir as one slide of a pseudo-case."""
    slides = []
    for i, xml_path in enumerate(sorted(xml_dir.glob("*.xml"))):
        d = out_dir / f"slide-{i}"
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run([os.environ.get("NODE_BIN", "node"), str(_COMPILE_SCRIPT), str(xml_path), str(d)],
                       capture_output=True, text=True, timeout=120)
        result = _read_json(d / "compile-result.json")
        pptx = d / "presentation.pptx"
        ok = result.get("status") == "success" and pptx.exists()
        slides.append({
            "index": i, "source": xml_path.name, "compiled": ok, "first_pass_ok": ok,
            "retries": 0, "max_tier": 0, "auto_fixes": {},
            "blocking": dict(Counter(x.get("type", "?") for x in result.get("diagnostics", []))) if not ok else {},
            "layout_issues": dict(Counter(i.get("code", "?") for i in audit_layout(xml_path.read_text(encoding="utf-8")))),
            "fit_grow": result.get("fitGrow", []), "components": [],
            "cards": card_metrics(pptx) if ok else [], "_dir": str(d),
        })
    return {"name": xml_dir.name, "repeat": 1, "run_id": "fixtures", "passed": all(s["compiled"] for s in slides),
            "error": None, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "elapsed": 0.0,
            "slides": slides, "_deck_pptx": None}


def score_against_golden(result: dict[str, Any], golden: dict[str, Any]) -> None:
    """Per-slide card-pattern match by slide index; missing/extra slides score 0."""
    gold = [[c["pattern"] for c in s["cards"]] for s in golden["slides"]]
    for i, s in enumerate(result["slides"]):
        s["golden_match"] = pattern_match([c["pattern"] for c in s["cards"]], gold[i]) if i < len(gold) else 0.0
    n = max(len(gold), len(result["slides"]))
    result["golden_match"] = round(sum(s["golden_match"] for s in result["slides"][:len(gold)]) / n, 3) if n else 0.0


# ── aggregation + report ────────────────────────────────────────────────────

def aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    slides = [s for c in cases for s in c["slides"]]
    fills = [card["fill"] for s in slides for card in s["cards"]]
    n = len(slides) or 1
    return {
        "runs": len(cases),
        "runs_passed": sum(c["passed"] for c in cases),
        "runs_errored": sum(bool(c["error"]) for c in cases),
        "slides": len(slides),
        "compiled_pct": round(100 * sum(s["compiled"] for s in slides) / n, 1),
        "first_pass_pct": round(100 * sum(s["first_pass_ok"] for s in slides) / n, 1),
        "mean_retries": round(sum(s["retries"] for s in slides) / n, 2),
        "cards": len(fills),
        "mean_fill": round(mean(fills), 3) if fills else None,
        "low_fill_pct": round(100 * sum(f < LOW_FILL for f in fills) / len(fills), 1) if fills else None,
        "auto_fixes_per_slide": round(sum(sum(s["auto_fixes"].values()) for s in slides) / n, 2),
        "layout_issues_per_slide": round(sum(sum(s["layout_issues"].values()) for s in slides) / n, 2),
        "fit_grow_changes_per_slide": round(sum(len(s["fit_grow"]) for s in slides) / n, 2),
        "tokens_in": sum(c["tokens_in"] for c in cases),
        "tokens_out": sum(c["tokens_out"] for c in cases),
        "cost_usd": round(sum(c["cost"] for c in cases), 4),
        "elapsed_s": round(sum(c["elapsed"] for c in cases), 1),
        "auto_fix_codes": dict(sum((Counter(s["auto_fixes"]) for s in slides), Counter()).most_common()),
        "blocking_codes": dict(sum((Counter(s["blocking"]) for s in slides), Counter()).most_common()),
        "layout_codes": dict(sum((Counter(s["layout_issues"]) for s in slides), Counter()).most_common()),
        "card_patterns": dict(Counter(c["pattern"] for s in slides for c in s["cards"]).most_common()),
        "component_kinds": dict(Counter(k["kind"] for s in slides for k in s["components"]).most_common()),
    }


def _slide_fill(s: dict[str, Any]) -> float:
    return min((c["fill"] for c in s["cards"]), default=1.0)


def write_summary(results: dict[str, Any], path: Path) -> None:
    agg = results["aggregate"]
    lines = [
        f"# Eval `{results['label']}`",
        "",
        f"{results['created']} · commit `{results['git_commit']}` · models.yaml `{results['models_sha']}` · "
        f"{agg['runs']} runs, {agg['slides']} slides",
        "",
        "| metric | value |", "|---|---|",
    ]
    for key in ("runs_passed", "runs_errored", "compiled_pct", "first_pass_pct", "mean_retries", "cards",
                "mean_fill", "low_fill_pct", "auto_fixes_per_slide", "layout_issues_per_slide",
                "fit_grow_changes_per_slide", "tokens_in", "tokens_out", "cost_usd", "elapsed_s"):
        lines.append(f"| {key} | {agg[key]} |")
    lines += ["", f"Fill = card content height ÷ inner height (1.0 = no dead space); low fill < {LOW_FILL}.", "",
              "## Cases", "",
              "| case | run | pass | slides | first-pass | retries | mean fill | low-fill cards | layout issues | golden match |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for c in results["cases"]:
        fills = [card["fill"] for s in c["slides"] for card in s["cards"]]
        lines.append(
            f"| {c['name']} | {c['repeat']} | {'ERROR' if c['error'] else 'PASS' if c['passed'] else 'FAIL'} "
            f"| {len(c['slides'])} | {sum(s['first_pass_ok'] for s in c['slides'])}/{len(c['slides'])} "
            f"| {sum(s['retries'] for s in c['slides'])} | {round(mean(fills), 2) if fills else '-'} "
            f"| {sum(f < LOW_FILL for f in fills)} | {sum(sum(s['layout_issues'].values()) for s in c['slides'])} "
            f"| {c.get('golden_match', '-')} |")
    for title, key in (("Auto-fix codes (first attempt)", "auto_fix_codes"),
                       ("Blocking codes during retries", "blocking_codes"),
                       ("Layout-audit codes (final attempt)", "layout_codes"),
                       ("Card patterns", "card_patterns"), ("Planner component kinds", "component_kinds")):
        lines += ["", f"## {title}", ""]
        lines += [f"- `{k}`: {v}" for k, v in agg[key].items()] or ["- none"]
    worst = sorted(((c, s) for c in results["cases"] for s in c["slides"] if s["cards"]),
                   key=lambda cs: _slide_fill(cs[1]))[:10]
    lines += ["", "## Lowest-fill slides", ""]
    lines += [f"- {c['name']} run {c['repeat']} slide {s['index']}: min fill {_slide_fill(s)}" for c, s in worst] or ["- none"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── output ──────────────────────────────────────────────────────────────────

def _git_commit() -> str:
    proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=_PIPELINE_ROOT)
    return proc.stdout.strip() or "unknown"


def _copy_slides(case: dict[str, Any], out_dir: Path) -> None:
    """Copy each slide's final compile folder into the eval folder; render with COM if available."""
    case_dir = out_dir / "slides" / f"{case['name']}__r{case['repeat']}"
    for s in case["slides"]:
        src = s.pop("_dir")
        if not src:
            continue
        dst = case_dir / f"slide-{s['index']}"
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("input.xml", "fitted.xml", "compile-result.json", "presentation.pptx"):
            if (Path(src) / f).exists() and Path(src) != dst:
                shutil.copy2(Path(src) / f, dst / f)
    deck = case.pop("_deck_pptx")
    if deck and Path(deck).exists():
        from src.compiler.screenshot import render_screenshots  # PowerPoint COM; no-op elsewhere
        render_screenshots(deck, str(out_dir / "renders" / f"{case['name']}__r{case['repeat']}"))


def make_bundle(out_dir: Path) -> Path:
    zip_path = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out_dir.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(out_dir.parent))
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score pipeline quality per slide")
    parser.add_argument("cases", nargs="*", help=f"case names (default: the gate, {len(GATE_CASES)} cases)")
    parser.add_argument("--label", required=True)
    parser.add_argument("--repeat", type=int, default=1, help="runs per case (LLM variance)")
    parser.add_argument("--fixtures", type=Path, help="LLM-free: score a folder of POM XML instead of cases")
    parser.add_argument("--bundle", action="store_true", help="also write <out>.zip for email")
    parser.add_argument("--out", type=Path, default=_PIPELINE_ROOT / "output" / "eval")
    args = parser.parse_args(argv)

    out_dir = args.out / f"{args.label}-{datetime.now():%Y%m%d-%H%M%S}"
    out_dir.mkdir(parents=True)

    if args.fixtures:
        cases = [evaluate_fixtures(args.fixtures, out_dir / "slides" / f"{args.fixtures.name}__r1")]
    else:
        from src.utils.logging_config import setup_logging
        setup_logging()
        cases = []
        for name in args.cases or GATE_CASES:
            case = load_case(name)
            golden = (evaluate_fixtures(_PIPELINE_ROOT / case["golden"], out_dir / "golden" / name)
                      if case.get("golden") else None)
            for r in range(1, args.repeat + 1):
                result = evaluate_case(case, r)
                if golden:
                    score_against_golden(result, golden)
                cases.append(result)
    for case in cases:
        _copy_slides(case, out_dir)

    results = {
        "label": args.label,
        "created": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "models_sha": hashlib.sha256((_PIPELINE_ROOT / "models.yaml").read_bytes()).hexdigest()[:8],
        "fit_grow": os.environ.get("POM_FIT_GROW", "1"),
        "aggregate": aggregate(cases),
        "cases": cases,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary(results, out_dir / "summary.md")
    print(f"\n{out_dir / 'summary.md'}")
    if args.bundle:
        print(f"EMAIL THIS FILE: {make_bundle(out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
