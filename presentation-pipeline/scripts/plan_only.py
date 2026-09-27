"""Test 1: planning-only runs of planning v2 (src/planning), scored against the pass criteria.

    python -m scripts.plan_only gj-h1-regen gate-deck-cheffin-audit --repeat 3 --label test-1 --bundle

Per run it writes output/plans/<label>/<run_id>/:
  slides.json        per slide: slide_plan (today's SlidePlan, read by eval_lineage), story, design, issues
  storyline.json     the storyline + the issues its check left
  storyline.md       human-readable storyline and components (to judge headlines)
  run-manifest.json  every LLM call with tokens and cost
Then output/plans/<label>/summary.md with the Test 1 criteria per case. --bundle zips the label folder
into llm_test/ so the test PC can send it back. Needs OPENAI_API_KEY (paid).
--rescore only re-scores the saved runs of a label (no LLM).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import traceback
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv

from scripts.eval_lineage import _canon, _norm, _plan_nums, golden_headlines, load_brief, score, stability
from src.planning.brief_index import _YEAR, data_numbers, numbers
from src.utils.llm_client import get_pricing, get_step_config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "plans"
CASES = ROOT / "tests" / "cases"
# brief numbers that are not content: pillar numbers (gj-h1); a number-format example and "1.0x" in
# "Allowable CPC for 1.0x ROAS" (CHEFFIN). Years are removed before scoring (see score_label).
LINEAGE_IGNORE = {"gj-h1-regen": "01,02,03,04,05", "gate-deck-cheffin-audit": "290,1",
                  "gate-deck-cheffin-full": "290,1"}
_BRIEF_HEADLINE = re.compile(r"slide\s+(\d+)\s*:[^\n]*\n\s*headline:\s*\n\s*([^\n]+)", re.I)
HEADLINE_SIZES = {"26", "27", "28", "42"}


def _cost(call: dict) -> float:
    p = get_pricing(call.get("model", ""))
    return round(call.get("tokens_in", 0) * p["input"] / 1e6 + call.get("tokens_out", 0) * p["output"] / 1e6, 5)


def _unshown(case: dict, slides: list[dict]) -> list[str]:
    """Brief numbers that are on no slide of the deck, whole brief — also the part above any "SLIDE N:"
    section, which the per-slide scorer does not count (e.g. CHEFFIN's platform summary)."""
    ignore = {_norm(n) for n in LINEAGE_IGNORE.get(case["name"], "").split(",") if n}
    planned = set().union(*(_plan_nums(s) for s in slides)) if slides else set()
    return sorted(set(data_numbers(case.get("request", ""))) - ignore - planned, key=lambda n: float(n))


def _storyline_md(story: dict, issues: list[str], designs: dict, unshown: list[str]) -> str:
    lines = [f"# {story.get('deck_title', '')}", "", f"**Argument:** {story.get('deck_argument', '')}",
             f"**Audience:** {story.get('audience_and_use', '')}",
             "**Gaps:** " + ("; ".join(story.get("gaps", [])) or "none"),
             "**Style:** " + ("; ".join(story.get("style_directives", [])) or "none"), ""]
    for s in story.get("slides", []):
        d = designs.get(s["slide_index"], {})
        lines += [f"## {s['slide_index']} · {s.get('label', '')}", f"**{s.get('headline', '')}**"
                  + (" (copied from the brief)" if s.get("headline_block") else ""),
                  f"_{s['subtitle']}_" if s.get("subtitle") else "_(no subtitle)_",
                  f"- so what: {s.get('so_what', '')}",
                  f"- emphasis: {', '.join(s.get('emphasis', [])) or '—'}"
                  + (f" · group: {s['parallel_group']}" if s.get("parallel_group") else ""),
                  f"- components: " + ", ".join(f"{c['kind']}[{c['role']}]" for c in d.get("components", [])),
                  f"- layout: {d.get('layout', '')}"]
        if d.get("issues"):
            lines.append(f"- open issues: {'; '.join(d['issues'])}")
        lines.append("")
    if issues:
        lines += ["## Storyline issues left", *[f"- {i}" for i in issues]]
    lines += ["", "## Brief numbers on no slide", ", ".join(unshown) or "none"]
    return "\n".join(lines)


def run_case(case: dict, label: str, **retries: int) -> Path:
    name = case["name"]
    rid = f"{name}-{uuid.uuid4().hex[:6]}"
    from src.planning.graph import run_planning  # imported late: --rescore needs no LLM stack

    t0 = time.time()
    out = run_planning(case["request"], target_slides=(case.get("expect") or {}).get("slide_count"), **retries)
    seconds = round(time.time() - t0, 1)
    folder = OUT / label / rid  # only after a run that finished: a failed run leaves no empty folder
    folder.mkdir(parents=True, exist_ok=True)
    story, designs = out["storyline"], out.get("designs", {})
    slides = [{"slide_index": p["slide_index"], "slide_plan": p, "story": story["slides"][p["slide_index"]],
               "design": designs.get(p["slide_index"], {}),
               "issues": designs.get(p["slide_index"], {}).get("issues", [])} for p in out.get("slide_plans", [])]
    calls = [{**c, "cost": _cost(c)} for c in out.get("calls", [])]
    (folder / "slides.json").write_text(json.dumps(slides, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "storyline.json").write_text(json.dumps(
        {"storyline": story, "issues": out.get("storyline_issues", []),
         "attempts": out.get("storyline_attempts", 0)}, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "storyline.md").write_text(
        _storyline_md(story, out.get("storyline_issues", []), designs, _unshown(case, slides)), encoding="utf-8")
    (folder / "run-manifest.json").write_text(json.dumps(
        {"case": name, "run_id": rid, "seconds": seconds, "calls": calls,
         "llm_calls": len(calls), "cost": round(sum(c["cost"] for c in calls), 4)}, indent=2), encoding="utf-8")
    print(f"  {rid}: {len(slides)} slides, {len(calls)} calls, ${sum(c['cost'] for c in calls):.3f}, {seconds}s")
    return folder


# ── Scoring ─────────────────────────────────────────────────────────────────

def _plan_checks(case: dict, slides: list[dict], story: dict) -> list[tuple[str, bool]]:
    results = []
    for chk in (case.get("plan_checks") or []):
        if "same_component" in chk:
            want = {_norm(n) for n in chk["same_component"]}
            ok = any(want <= set(numbers(json.dumps(c.get("content_data", {}), ensure_ascii=False)))
                     for s in slides for c in s["slide_plan"]["components"])
        elif chk.get("headlines_from_brief"):
            # "SLIDE N: ...\nHeadline:\n<text>" in the brief → <text> must be slide N's planned title
            want = {int(n) - 1: h.strip() for n, h in _BRIEF_HEADLINE.findall(case.get("request", ""))}
            titles = {s["slide_index"]: s["slide_plan"].get("slide_title", "") for s in slides}
            kept = sum(1 for i, h in want.items() if _canon(h) and _canon(h) in _canon(titles.get(i, "")))
            results.append((f"{chk['name']} {kept}/{len(want)}", bool(want) and kept == len(want)))
            continue
        elif "gaps_mention" in chk:
            ok = all(any(w.lower() in g.lower() for g in story.get("gaps", [])) for w in chk["gaps_mention"])
        elif "style_mentions" in chk:
            text = " ".join(story.get("style_directives", [])).lower()
            ok = all(w.lower() in text for w in chk["style_mentions"])
        else:
            continue
        results.append((chk["name"], ok))
    return results


def score_label(label: str) -> str:
    if not (OUT / label).is_dir():
        return f"No runs saved under output/plans/{label} (every run failed? see the errors above)."
    folders = sorted(p for p in (OUT / label).iterdir() if (p / "slides.json").exists())
    by_case: dict[str, list[Path]] = {}
    for f in folders:
        by_case.setdefault(json.loads((f / "run-manifest.json").read_text(encoding="utf-8"))["case"], []).append(f)
    md = [f"# Test 1 — planning only · label `{label}`", "",
          "numbers dropped = per slide section (or whole brief without sections); on no slide = whole brief, "
          "including data above the slide sections", ""]
    for name, runs in by_case.items():
        case = yaml.safe_load((CASES / f"{name}.yaml").read_text(encoding="utf-8"))
        brief, sections = load_brief(case)
        ignore = {_norm(n) for n in LINEAGE_IGNORE.get(name, "").split(",") if n}
        # the planner's own rule: numbers the brief uses only as years ("Jun '26", "2026") are dates, not data
        ignore |= set(numbers(" ".join(_YEAR.findall(brief)))) - set(numbers(_YEAR.sub(" ", brief)))
        heads = golden_headlines(ROOT / case["golden"], HEADLINE_SIZES) if case.get("golden") else None
        loaded = {f.name: json.loads((f / "slides.json").read_text(encoding="utf-8")) for f in runs}
        md += [f"## {name}", "", "| run | headlines kept | numbers dropped | on no slide | invented "
               "| max hints/slide | slides with issues | LLM calls | cost | plan checks |", "|---" * 10 + "|"]
        for f in runs:
            slides = loaded[f.name]
            m = score(slides, brief, sections, ignore, heads)
            man = json.loads((f / "run-manifest.json").read_text(encoding="utf-8"))
            story = json.loads((f / "storyline.json").read_text(encoding="utf-8"))["storyline"]
            checks = _plan_checks(case, slides, story)
            if not slides:
                md.append(f"| {f.name} | run produced no slides | | | | | | {man['llm_calls']} | ${man['cost']:.3f} | |")
                continue
            dropped = f"{m['dropped_planning']}/{m['brief']} ({100 * m['dropped_planning'] / max(1, m['brief']):.1f}%)"
            heads_cell = f"{m['headlines_kept']}/{m['headlines_counted']}" if "headlines_kept" in m else "n/a"
            unshown = _unshown(case, slides)
            md.append(f"| {f.name} | {heads_cell} | {dropped} | {len(unshown)}: {', '.join(unshown[:8])} | "
                      f"{m['invented_planning']} | "
                      f"{m.get('max_hints_per_slide', 0)} | {sum(1 for s in slides if s['issues'])} | "
                      f"{man['llm_calls']} | ${man['cost']:.3f} | "
                      + (", ".join(f"{n}: {'pass' if ok else 'FAIL'}" for n, ok in checks) or "—") + " |")
        if len(loaded) > 1:
            st = stability(loaded)
            md += ["", f"Plan stability: {st['same']}/{st['slides']} slides with the same component kinds "
                       f"in all {len(loaded)} runs"]
        md.append("")
    md += ["Pass (docs/architecture-north-star.md §9): gj-h1 headlines ≥ 12/14 (13 content slides counted), "
           "≤ 2% numbers dropped, 0 invented, ≤ 2 hints per slide, same components on ≥ 10/14 slides; "
           "CHEFFIN plan checks pass. Headlines as conclusions: read each run's storyline.md."]
    text = "\n".join(md)
    (OUT / label / "summary.md").write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Test 1: planning-only runs of planning v2")
    ap.add_argument("cases", nargs="*", default=["gj-h1-regen", "gate-deck-cheffin-audit"])
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--label", default="test-1")
    ap.add_argument("--bundle", action="store_true", help="zip output/plans/<label> into llm_test/")
    ap.add_argument("--storyline-retries", type=int, default=1, help="re-asks after a failed storyline check")
    ap.add_argument("--slide-retries", type=int, default=2, help="re-asks per slide after a failed check")
    ap.add_argument("--rescore", action="store_true", help="only re-score the saved runs of --label (no LLM)")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    if not args.rescore:
        load_dotenv(ROOT / ".env")
        if get_step_config("storyline").get("provider", "openai") == "openai" and not os.environ.get("OPENAI_API_KEY"):
            print(f"No OPENAI_API_KEY: put it in {ROOT / '.env'} (OPENAI_API_KEY=sk-...) or set it in the shell. "
                  "Nothing was run.")
            return 2
        for name in args.cases:
            case = yaml.safe_load((CASES / f"{name}.yaml").read_text(encoding="utf-8"))
            print(f"{name} × {args.repeat}")
            for _ in range(args.repeat):
                try:
                    run_case(case, args.label, storyline_retries=args.storyline_retries,
                             slide_retries=args.slide_retries)
                except Exception:  # one failed run must not lose the others
                    print("  run failed:")
                    traceback.print_exc()
    print(score_label(args.label))
    if args.bundle and not any((OUT / args.label).glob("*/slides.json")):
        print("bundle: skipped, no saved runs")
    elif args.bundle:
        (ROOT / "llm_test").mkdir(exist_ok=True)
        base = ROOT / "llm_test" / f"plans-{args.label}-{time.strftime('%Y%m%d-%H%M%S')}"
        print("bundle:", shutil.make_archive(str(base), "zip", OUT, args.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
