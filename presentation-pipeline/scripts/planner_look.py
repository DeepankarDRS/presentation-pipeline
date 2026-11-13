"""Planner look check (2026-11-13): the slides each planner's plans turn into. The saved plans of a planner A/B
(scripts/planner_ab.py: the old arm of one label, the new arm of another) go through THIS branch's generator,
validator and repairers (critic off), deck by deck, so the only difference between the two arms is the plan.

    python -m scripts.planner_look run --old-from ab1 --new-from ab3 --label look1 --bundle   # paid, ~$2 (10 decks)
    python -m scripts.planner_look run --old-from ab1 --new-from ab3 --label smoke --cases deck-qbr-data   # ~$0.4
    python -m scripts.planner_look sheet --label look1      # free, build PC (LibreOffice): blind sheets + marks.csv
    python -m scripts.planner_look score --label look1      # free: after you fill marks.csv

run (test PC): needs output/planner-ab/<old-from>/old.json and output/planner-ab/<new-from>/new.json. Per case and
arm, the case's request, theme and supplied content (tests/cases/<case>.yaml) with the arm's slide plans; the graph
skips planning (slide_plans set) and draws the deck. Arms alternate per case, so --max-cost (default $3.50) stops on
a whole pair. Writes output/planner-look/<label>/<arm>/<case>/ (presentation.pptx, slides.json, run-manifest.json)
and runs.json (cost, passed, repairs per deck); --bundle zips the label folder.

sheet (build PC): each deck to PDF with the deck fonts (scripts.card_replay.render), one image per slide, the two
arms side by side, left / right by a fixed seed, no labels, 3 pairs per sheet. marks.csv: write 1, 2 or = in
`choice` and a reason; key.json says which side is which, open it only after marking.
score: (new wins + half the ties) / pairs marked, per deck and in all; a slide one arm failed to draw counts as a loss
for that arm.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
AB = ROOT / "output" / "planner-ab"
OUT = ROOT / "output" / "planner-look"
ARMS = ("old", "new")
PER_SHEET = 3
W, H, GAP, LABEL = 960, 540, 24, 40


def arm_plans(label: str, arm: str) -> dict[str, list[dict[str, Any]]]:
    """case -> the arm's slide plans in slide order (planner_ab rows that planned)."""
    rows = json.loads((AB / label / f"{arm}.json").read_text(encoding="utf-8"))
    decks: dict[str, list[dict[str, Any]]] = {}
    for r in sorted(rows, key=lambda r: (r["case"], r["slide_index"] or 0)):
        if r.get("plan"):
            decks.setdefault(r["case"], []).append(r["plan"])
    return decks


# ── run (paid) ──────────────────────────────────────────────────────────────

def draw(case_name: str, plans: list[dict[str, Any]], dest: Path) -> dict[str, Any]:
    from src.graph import compile_graph
    from src.state import initial_state
    from src.utils.case_loader import load_case
    from src.utils.logging_config import set_context

    case = load_case(case_name)
    supplied = case.get("supplied_content")
    run_id = uuid.uuid4().hex[:12]
    set_context(run_id=run_id)
    state = initial_state(run_id=run_id, raw_request=case.get("request", case.get("objective", "")),
                          theme_name=case.get("theme", "") or "", deck_min_threshold=len(plans), critic_mode="off",
                          supplied_content=supplied if isinstance(supplied, dict) else None)
    state["slide_plans"] = plans
    cfg = {"run_name": f"planner-look-{run_id}", "tags": ["planner-look"], "recursion_limit": 150}
    t0 = time.time()
    final: dict[str, Any] = {}
    for final in compile_graph().stream(state, config=cfg, stream_mode="values"):
        pass
    src = ROOT / "output" / "runs" / run_id
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("presentation.pptx", "slides.json", "run-manifest.json"):
        if (src / name).exists():
            shutil.copy2(src / name, dest / name)
    pptx = final.get("pptx_path")
    if pptx and Path(pptx).exists() and not (dest / "presentation.pptx").exists():
        shutil.copy2(pptx, dest / "presentation.pptx")
    manifest = json.loads((dest / "run-manifest.json").read_text(encoding="utf-8")) \
        if (dest / "run-manifest.json").exists() else {}
    history = final.get("generation_history") or []
    return {"run_id": run_id, "slides": len(plans), "passed": manifest.get("passed", final.get("passed")),
            "cost_usd": (manifest.get("cost") or {}).get("total_usd", 0) or 0,
            "repairs": sum(1 for h in history if h.get("step") in ("repairer", "visual_repairer")),
            "seconds": round(time.time() - t0, 1), "pptx": (dest / "presentation.pptx").exists()}


def run(a: argparse.Namespace) -> int:
    from src.utils.logging_config import add_file_log, setup_logging
    out = OUT / a.label
    out.mkdir(parents=True, exist_ok=True)
    setup_logging()
    add_file_log(out / "run.log")
    plans = {"old": arm_plans(a.old_from, "old"), "new": arm_plans(a.new_from, "new")}
    cases = [c for c in plans["old"] if c in plans["new"] and (not a.cases or c in a.cases)]
    rows: list[dict[str, Any]] = []
    spent = 0.0
    for case in cases:
        if spent > a.max_cost:
            print(f"stopped at ${spent:.2f} (--max-cost {a.max_cost}) before {case}")
            break
        for arm in ARMS:
            print(f"{case} {arm}: {len(plans[arm][case])} slides ...", flush=True)
            try:
                row = draw(case, plans[arm][case], out / arm / case)
            except Exception as e:   # one deck must not cost the others
                row = {"error": str(e)[:300], "cost_usd": 0}
            row.update(case=case, arm=arm)
            spent += row.get("cost_usd") or 0
            rows.append(row)
            print(f"  ${row.get('cost_usd', 0):.3f} passed={row.get('passed')} repairs={row.get('repairs')} "
                  f"total=${spent:.3f}", flush=True)
            (out / "runs.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"total ${spent:.3f}, {len(rows)} decks -> {out}")
    if a.bundle:
        print(shutil.make_archive(str(OUT / f"{a.label}-{time.strftime('%Y%m%d-%H%M%S')}"), "zip", out))
    return 0


# ── sheet / score (free, build PC) ──────────────────────────────────────────

def _slide_pngs(deck: Path) -> list[Path]:
    import pymupdf

    from scripts.card_replay import render
    pdf = deck / "presentation.pdf"
    if not pdf.exists() and render(deck) is None:
        return []
    doc = pymupdf.open(pdf)
    pngs = []
    for i, page in enumerate(doc):
        p = deck / f"slide-{i + 1:02d}.png"
        if not p.exists():
            page.get_pixmap(dpi=96).save(p)
        pngs.append(p)
    return pngs


def sheet(a: argparse.Namespace) -> int:
    from PIL import Image, ImageDraw
    out = OUT / a.label
    sheets = out / "sheets"
    sheets.mkdir(exist_ok=True)
    rng = random.Random(f"planner-look-{a.label}")
    pairs = []
    for case_dir in sorted((out / "old").iterdir()):
        images = {arm: _slide_pngs(out / arm / case_dir.name) for arm in ARMS}
        for i in range(max(len(images["old"]), len(images["new"]))):
            left = rng.choice(ARMS)
            pairs.append({"pair": len(pairs) + 1, "case": case_dir.name, "slide": i, "left": left,
                          "images": {arm: str(images[arm][i]) if i < len(images[arm]) else "" for arm in ARMS}})
    for start in range(0, len(pairs), PER_SHEET):
        chunk = pairs[start:start + PER_SHEET]
        img = Image.new("RGB", (2 * W + 3 * GAP, len(chunk) * (H + LABEL + GAP) + GAP), "white")
        pen = ImageDraw.Draw(img)
        for row, p in enumerate(chunk):
            y = GAP + row * (H + LABEL + GAP)
            pen.text((GAP, y + 8), f"Pair {p['pair']}  ({p['case']}, slide {p['slide'] + 1})   1 = left, 2 = right",
                     fill="black")
            for col, arm in enumerate((p["left"], "new" if p["left"] == "old" else "old")):
                x = GAP + col * (W + GAP)
                if p["images"][arm]:
                    img.paste(Image.open(p["images"][arm]).convert("RGB").resize((W, H)), (x, y + LABEL))
                else:
                    pen.rectangle((x, y + LABEL, x + W, y + LABEL + H), outline="red")
                    pen.text((x + 20, y + LABEL + 20), "not drawn", fill="red")
        img.save(sheets / f"sheet-{start // PER_SHEET + 1:02d}.png")
    with open(out / "marks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "case", "slide", "choice", "reason"])
        for p in pairs:
            w.writerow([p["pair"], p["case"], p["slide"] + 1, "", ""])
    (out / "key.json").write_text(json.dumps([{k: p[k] for k in ("pair", "case", "slide", "left")} for p in pairs],
                                             indent=1), encoding="utf-8")
    print(f"{len(pairs)} pairs on {(len(pairs) + PER_SHEET - 1) // PER_SHEET} sheets in {sheets}; mark {out / 'marks.csv'}")
    return 0


def score(a: argparse.Namespace) -> int:
    out = OUT / a.label
    key = {p["pair"]: p for p in json.loads((out / "key.json").read_text(encoding="utf-8"))}
    per: dict[str, list[float]] = {}
    reasons = []
    with open(out / "marks.csv", encoding="utf-8") as f:
        for m in csv.DictReader(f):
            choice = (m.get("choice") or "").strip()
            if choice not in ("1", "2", "="):
                continue
            p = key[int(m["pair"])]
            right = "new" if p["left"] == "old" else "old"
            winner = "=" if choice == "=" else (p["left"] if choice == "1" else right)
            per.setdefault(p["case"], []).append(0.5 if winner == "=" else float(winner == "new"))
            reasons.append(f"pair {m['pair']} ({p['case']} {m['slide']}): {winner} - {m.get('reason', '')}")
    allv = [v for vs in per.values() for v in vs]
    lines = [f"# Planner look check · {a.label}", "", f"new planner score: **{sum(allv) / max(1, len(allv)):.3f}** "
             f"over {len(allv)} pairs (1 = new always better, 0.5 = even)", "", "| deck | pairs | new score |",
             "|---|---|---|"] + [f"| {c} | {len(v)} | {sum(v) / len(v):.3f} |" for c, v in sorted(per.items())]
    lines += ["", "## Marks", ""] + [f"- {r}" for r in reasons]
    (out / "score.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="paid: draw both arms' plans with this branch's generator")
    r.add_argument("--old-from", required=True, help="planner_ab label whose old.json to draw")
    r.add_argument("--new-from", required=True, help="planner_ab label whose new.json to draw")
    r.add_argument("--label", required=True)
    r.add_argument("--cases", nargs="*", default=[])
    r.add_argument("--max-cost", type=float, default=3.5)
    r.add_argument("--bundle", action="store_true")
    for name in ("sheet", "score"):
        s = sub.add_parser(name)
        s.add_argument("--label", required=True)
    a = ap.parse_args()
    return {"run": run, "sheet": sheet, "score": score}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
