"""1a node test runner (docs/derived-blocks-planning-2026-10-06.md §4, D11): generator-only, from step 0's plans.

    # arm B, paid (gpt-4.1 per models.yaml), one case first:
    python -m scripts.node_test --slides docs/eval/step0/1a-slides.json --label 1a --cases deck-qbr-data
    python -m scripts.node_test --slides docs/eval/step0/1a-slides.json --label 1a --bundle
    # free:
    python -m scripts.node_test --slides docs/eval/step0/1a-slides.json --label 1a-off --off          # arm A recompiled
    python -m scripts.node_test --slides ... --label dry --llm mechanical                             # code writes the skeleton
    python -m scripts.node_test --slides ... --label dry --llm scripted:tests/fixtures/nodes/scripted # fixed answers

Per slide: the node prompt (prompt_lines.render_prompts) -> one generator call -> the node pass
(scripts/phase0b/expand.expand_nodes: checks, native fillers, derived blocks in their boxes) -> compile.
A NODE_* error or a failed compile -> a node-aware re-ask on the skeleton (the same prompts + the
previous skeleton + the errors), at most MAX_REPAIRS. Writes output/1a/<label>/<case>/slide-NN/
{user-prompt.txt, skeleton.xml, skeleton-repair-N.xml, expanded.xml, check.json, compile-result.json,
presentation.pptx} and output/1a/<label>/node-test-manifest.json (settings, every call's usage, per-slide result).
Both arms are drawn in the deck font (--font, default Inter) and compiled with fit-grow (--fit-grow, default on).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any

from scripts.from_plans import load_run
from scripts.phase0b.expand import deck_font, expand_nodes
from scripts.phase0b.fit import Measurer

ROOT = Path(__file__).resolve().parents[1]
MAX_REPAIRS = 2
FENCE = re.compile(r"^```(?:xml)?\s*|\s*```\s*$")


# ── LLMs ─────────────────────────────────────────────────────────────────────

class Reply:
    def __init__(self, content: str, usage: dict[str, Any]) -> None:
        self.content, self.usage = content, usage


class RealLLM:
    def __init__(self) -> None:
        from src.utils.llm_client import get_llm
        self.llm = get_llm("generator")

    def __call__(self, messages: list[dict], case: str, number: int, attempt: int, plan: dict) -> Reply:
        from src.utils.llm_client import extract_usage
        r = self.llm.invoke(messages)
        usage = extract_usage(r)
        usage["truncated"] = (r.response_metadata or {}).get("finish_reason") == "length"
        return Reply(r.content, usage)


class ScriptedLLM:
    """Fixed answers: <dir>/<case>/slide-<n>.xml, a repair answer slide-<n>.repair-<k>.xml (else the first
    answer again); usage from <dir>/usage.json {"tokens_in", "tokens_out"} or a fixed small number."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        u = folder / "usage.json"
        self.usage = json.loads(u.read_text(encoding="utf-8")) if u.exists() else {"tokens_in": 10000, "tokens_out": 500}

    def __call__(self, messages, case, number, attempt, plan) -> Reply:
        base = self.folder / case
        f = base / (f"slide-{number}.repair-{attempt}.xml" if attempt else f"slide-{number}.xml")
        if not f.exists():
            f = base / f"slide-{number}.xml"
        if not f.exists():
            raise FileNotFoundError(f"scripted answer missing: {f}")
        return Reply(f.read_text(encoding="utf-8"), {**self.usage, "tokens_reasoning": 0, "tokens_cached": 0,
                                                      "model": "scripted", "truncated": False})


def mechanical_skeleton(plan: dict) -> str:
    """Code's own skeleton: the header from the plan, then one ref tag per component, each its own band."""
    from src.compiler.nodes import spec
    from src.compiler.nodes.native import x

    head = ""
    if plan.get("label"):
        head += f'<Text fontSize="14" color="$accent" bold="true" letterSpacing="2">{x(plan["label"].upper())}</Text>'
    head += f'<Text fontSize="30" bold="true" color="$textMain">{x(plan.get("slide_title", ""))}</Text>'
    if plan.get("subtitle"):
        head += f'<Text fontSize="16" color="$textMuted">{x(plan["subtitle"])}</Text>'
    tags = ""
    for c in plan.get("components") or []:
        if c["kind"] in spec.NO_REF_KINDS:
            continue
        tag = spec.tags_for(c["kind"])[0]
        size = "" if tag in ("Text", "Table", "Ul") else ' grow="1"'
        tags += f'<{tag} ref="{c["component_id"]}"{size} />'
    return (f'<Slide><VStack w="1280" h="720" padding="40" gap="16" alignItems="stretch" backgroundColor="$surface">'
            f"{head}{tags}</VStack></Slide>")


class MechanicalLLM:
    def __call__(self, messages, case, number, attempt, plan) -> Reply:
        return Reply(mechanical_skeleton(plan), {"tokens_in": 0, "tokens_out": 0, "tokens_reasoning": 0,
                                                 "tokens_cached": 0, "model": "mechanical", "truncated": False})


def make_llm(spec_: str):
    if spec_ == "real":
        return RealLLM()
    if spec_ == "mechanical":
        return MechanicalLLM()
    if spec_.startswith("scripted:"):
        return ScriptedLLM(Path(spec_.split(":", 1)[1]))
    raise SystemExit(f"--llm must be real, mechanical or scripted:<dir>, not {spec_}")


# ── one slide ────────────────────────────────────────────────────────────────

def clean(raw: str) -> str:
    return FENCE.sub("", raw.strip()).strip()


def compile_slide(xml: str, theme_element: str, out: Path, fit_grow: bool) -> dict:
    from src.agents.validator import normalize_and_compile
    body = xml if fit_grow else "<!-- fit-grow: off -->\n" + xml
    ok, cr = normalize_and_compile(body, theme_element, out)
    cr = dict(cr)
    cr["ok"] = bool(ok)
    return cr


def _cost(usage: dict) -> float:
    from src.agents.evaluator import _compute_cost
    if usage.get("model") in ("mechanical", "scripted"):
        return 0.0
    return _compute_cost(usage.get("tokens_in", 0), usage.get("tokens_out", 0), usage.get("model", ""))


def run_slide(run: dict, slide: dict, llm, measure: Measurer, out: Path, font: str | None, fit_grow: bool,
              calls: list[dict]) -> dict:
    from src.agents.context_builder import build_contract
    from src.compiler.nodes.prompt_lines import render_prompts
    from src.compiler.nodes.validate import repair_note

    plan, theme, case, n = slide["plan"], run["theme"], run["case"], slide["number"]
    contract = build_contract(plan, theme)
    system, user = render_prompts(plan, contract)
    out.mkdir(parents=True, exist_ok=True)
    (out / "user-prompt.txt").write_text(user, encoding="utf-8")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    first = None
    for attempt in range(MAX_REPAIRS + 1):
        reply = llm(messages, case, n, attempt, plan)
        u = reply.usage
        calls.append({"case": case, "slide": n, "step": "generator" if attempt == 0 else "node_repair",
                      "attempt": attempt, **{k: u.get(k, 0) for k in ("tokens_in", "tokens_out", "tokens_reasoning", "tokens_cached")},
                      "model": u.get("model", ""), "truncated": u.get("truncated", False), "cost": _cost(u)})
        skeleton = clean(reply.content)
        (out / ("skeleton.xml" if attempt == 0 else f"skeleton-repair-{attempt}.xml")).write_text(skeleton, encoding="utf-8")
        try:
            xml, rep = expand_nodes(skeleton, plan, theme["element"], measure, theme, font)
        except Exception as e:   # unparseable skeleton: a repair with the error
            xml, rep = "", {"check": {"ok": False, "components": {}, "issues": [], "unknown_refs": 0},
                            "issues": [{"code": "NODE_EXPAND_FAILED", "severity": "error", "ref": None,
                                        "message": f"{type(e).__name__}: {e}"}], "scale": None, "deficit": None}
        cr = compile_slide(xml, theme["element"], out / f"compile-{attempt}", fit_grow) if xml else {"ok": False, "diagnostics": []}
        if first is None:
            first = rep
        errors = [i for i in rep["issues"] if i["severity"] == "error"]
        if cr["ok"] and not errors:
            break
        if attempt == MAX_REPAIRS:
            break
        diags = "\n".join(f"- {d.get('type', '')}: {d.get('message', '')}" for d in (cr.get("diagnostics") or [])[:8])
        note = repair_note(errors) + ("\n" + diags if diags else "")
        messages = messages[:2] + [{"role": "assistant", "content": skeleton},
                                   {"role": "user", "content": "That skeleton has these problems:\n" + note +
                                    "\nOutput the corrected skeleton: the whole <Slide>, same rules."}]
    (out / "expanded.xml").write_text(xml, encoding="utf-8")
    final = out / f"compile-{attempt}"
    if (final / "presentation.pptx").exists():
        shutil.copy2(final / "presentation.pptx", out / "presentation.pptx")
    (out / "compile-result.json").write_text(json.dumps(cr, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (out / "check.json").write_text(json.dumps({"first": first, "final": rep}, ensure_ascii=False, indent=1, default=str),
                                    encoding="utf-8")
    return {"case": case, "slide": n, "repairs": attempt, "compiled": cr["ok"],
            "first_ok": first["check"].get("ok", False) if first else False,
            "issues_first": [i["code"] for i in first["issues"]] if first else [],
            "issues_final": [i["code"] for i in rep["issues"]], "scale": rep.get("scale"), "deficit": rep.get("deficit"),
            "warnings": [w.get("code") for w in cr.get("warnings") or []]}


def run_off(run: dict, slide: dict, out: Path, font: str | None, fit_grow: bool) -> dict:
    """Arm A: step 0's saved XML on today's compiler, in the same deck font."""
    out.mkdir(parents=True, exist_ok=True)
    xml = deck_font(slide["xml"], font)
    (out / "expanded.xml").write_text(xml, encoding="utf-8")
    cr = compile_slide(xml, run["theme"]["element"], out / "compile-0", fit_grow)
    if (out / "compile-0" / "presentation.pptx").exists():
        shutil.copy2(out / "compile-0" / "presentation.pptx", out / "presentation.pptx")
    (out / "compile-result.json").write_text(json.dumps(cr, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"case": run["case"], "slide": slide["number"], "compiled": cr["ok"],
            "warnings": [w.get("code") for w in cr.get("warnings") or []]}


# ── main ─────────────────────────────────────────────────────────────────────

def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slides", type=Path, default=ROOT / "docs" / "eval" / "step0" / "1a-slides.json")
    ap.add_argument("--label", required=True)
    ap.add_argument("--cases", nargs="*", help="only these cases (default: all in --slides)")
    ap.add_argument("--llm", default="real", help="real | mechanical | scripted:<dir>")
    ap.add_argument("--off", action="store_true", help="arm A: recompile step 0's saved XML, no LLM")
    ap.add_argument("--font", default="Inter", help='deck font for both arms; "none" leaves POM\'s default')
    ap.add_argument("--fit-grow", choices=["on", "off"], default="on")
    ap.add_argument("--bundle", action="store_true", help="zip the output folder for the trip back")
    a = ap.parse_args()

    font = None if a.font.lower() == "none" else a.font
    fit_grow = a.fit_grow == "on"
    sel = json.loads(a.slides.read_text(encoding="utf-8"))["slides"]
    if a.cases:
        sel = [r for r in sel if r["case"] in a.cases]
    out_root = ROOT / "output" / "1a" / a.label
    out_root.mkdir(parents=True, exist_ok=True)
    runs: dict[str, dict] = {}
    llm = None if a.off else make_llm(a.llm)
    measure = None if a.off else Measurer()
    calls: list[dict] = []
    results: list[dict] = []
    t0 = time.time()
    try:
        for row in sel:
            run = runs.get(row["case"]) or runs.setdefault(row["case"], load_run(ROOT / row["run"]))
            slide = next(s for s in run["slides"] if s["number"] == row["slide"])
            out = out_root / row["case"] / f"slide-{row['slide']:02d}"
            if a.off:
                r = run_off(run, slide, out, font, fit_grow)
            else:
                r = run_slide(run, slide, llm, measure, out, font, fit_grow, calls)
            results.append(r)
            print(f"{row['case']} {row['slide']}: compiled {r['compiled']}"
                  + ("" if a.off else f", repairs {r['repairs']}, first-try issues {r['issues_first']}"), flush=True)
    finally:
        if measure:
            measure.close()
    manifest = {"label": a.label, "arm": "off" if a.off else "nodes", "llm": None if a.off else a.llm,
                "git_commit": _git("rev-parse", "--short", "HEAD"), "git_dirty": bool(_git("status", "--porcelain")),
                "font": font, "fit_grow": fit_grow, "slides_file": str(a.slides), "elapsed_s": round(time.time() - t0, 1),
                "calls": calls, "cost_usd": round(sum(c["cost"] for c in calls), 4), "results": results}
    (out_root / "node-test-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(results)} slides, {sum(r['compiled'] for r in results)} compiled, ${manifest['cost_usd']} -> {out_root}")
    if a.bundle:
        z = out_root.with_suffix(".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in out_root.rglob("*"):
                if f.is_file() and "compile-" not in f.parent.name:
                    zf.write(f, f.relative_to(out_root.parent))
        print(f"bundle: {z}")


if __name__ == "__main__":
    main()
