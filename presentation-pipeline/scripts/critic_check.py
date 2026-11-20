"""Is the critic-auto loop working (2026-11-20 redesign: code first, then eyes; one fix on the drawn XML)?

    python -m scripts.critic_check            # free: the real loop on fixture slides, the LLMs faked
    python -m scripts.critic_check --paid --case deck-overflow-repair                      # one paid deck
    python -m scripts.critic_check --paid --case deck-overflow-repair --critic-model gpt-6.1-sol   # critic A/B arm

Prints PASS / FAIL / SKIP per step and exits 1 when a step fails. Free steps:
  1 screenshot backend    comtypes + PowerPoint COM (without it the critic passes every slide unseen)
  2 component boxes       ref tags drawn by code and compiled; each component has one box in geometry.json
  3 screenshot + marks    the slide renders to a PNG and the marked copy has a numbered box per component
  4 critic input          one fixed system prompt, clean + marked image, component table, annotated ref-tag XML
  5 code first           a SLIDE_DENSE slide goes to the fixer as a relayout with no vision call
  6 fix kept             a faked edit on the drawn XML compiles with fit-grow off and is kept as written
  7 fix rolled back      a faked edit that rewords a code-drawn component is rolled back
  8 deck as drawn        slide_router saves the fixed slide; the deck compile changes no value (fit-grow off)
--paid: runs the deck and reads its log: reviews, measured defects sent to the fixer, fixes kept / rolled back,
code defects logged. The log is written to output/critic-check/<run_id>.log.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agents import critic, visual_critic, visual_repairer  # noqa: E402
from src.agents.context_builder import build_contract  # noqa: E402
from src.agents.critic_schema import ComponentVerdict, VisualCriticOutput  # noqa: E402
from src.agents.deck_nodes import assemble_deck_xml, slide_router_node  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.agents.validator import validator_node  # noqa: E402
from src.agents.visual_repairer import Edit, FixerOutput  # noqa: E402
from src.compiler.compiler_client import drawn_xml  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "nodes" / "runs" / "decks" / "gate-deck-all-nodes-dense__r1" / "slides.json"
OUT = ROOT / "output" / "critic-check"
RESULTS: list[tuple[str, str, str]] = []


def report(step: str, status: str, detail: str = "") -> None:
    RESULTS.append((step, status, detail))
    print(f"[{status:4}] {step}" + (f" - {detail}" if detail else ""), flush=True)


def _slide() -> tuple[dict, str]:
    """A fixture slide with two KPI rows and a chart, written as the generator writes it: ref tags + hand-drawn ids."""
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))[1]["slide_plan"]
    kpis = [c["component_id"] for c in plan["components"] if c["kind"] == "kpi_row"]
    chart = next(c["component_id"] for c in plan["components"] if c["kind"] == "chart")
    note = next(c["component_id"] for c in plan["components"] if c["kind"] == "narrative")
    xml = ('<Slide><VStack w="1280" h="720" padding="48" gap="20" alignItems="stretch" backgroundColor="$surface">'
           f'<Text id="slide_title" fontSize="36" bold="true" color="$textMain">{plan["slide_title"]}</Text>'
           + "".join(f'<KpiRow ref="{k}"/>' for k in kpis)
           + f'<Chart ref="{chart}" grow="1" h="max" minH="180"/>'
           f'<Text id="{note}" fontSize="18" color="$textMain">Repeat customers carry the growth.</Text></VStack></Slide>')
    return plan, xml


class _FakeVision:
    """Records the critic's messages; answers with `verdicts` (or fails when none are given)."""
    def __init__(self, output=None):
        self.output, self.messages = output, None

    def with_structured_output(self, schema, *a, **k):
        schema.model_json_schema()   # the real call builds this first: a broken schema fails every review
        return SimpleNamespace(invoke=self._invoke)

    def _invoke(self, messages):
        self.messages = messages
        if self.output is None:
            raise RuntimeError("no vision call expected")
        return {"parsed": self.output, "raw": SimpleNamespace(response_metadata={}, usage_metadata={})}


def _fixer(*outputs):
    calls = []

    def invoke(messages):
        calls.append(messages)
        return {"parsed": outputs[min(len(calls), len(outputs)) - 1],
                "raw": SimpleNamespace(response_metadata={}, usage_metadata={})}
    return SimpleNamespace(with_structured_output=lambda *a, **k: SimpleNamespace(invoke=invoke))


def free_checks() -> None:
    # 1 screenshot backend
    try:
        import comtypes.client as cc
        app = cc.CreateObject("PowerPoint.Application")
        app.Quit()
        report("1 screenshot backend", "PASS", "PowerPoint COM opens")
    except ImportError:
        report("1 screenshot backend", "FAIL", "comtypes missing: run `uv sync` (the critic passes every slide unseen)")
    except Exception as exc:   # comtypes there, PowerPoint not
        report("1 screenshot backend", "FAIL", f"PowerPoint COM failed: {exc}")

    plan, xml = _slide()
    theme = resolve_theme("corporate-slate")
    run_id = f"critic-check-{uuid.uuid4().hex[:6]}"
    state = {"current_xml": xml, "slide_plans": [plan, {}], "current_slide_index": 0, "retry_count": 0,
             "run_id": run_id, "completed_slides": [], "theme_element": theme["element"], "resolved_theme": theme,
             "contract": build_contract(plan, theme), "raw_request": "critic check", "critic_mode": "auto"}

    # 2 validator + one box per component
    state.update(validator_node(state))
    cr = state.get("compile_result") or {}
    if not cr.get("ok"):
        report("2 component boxes", "FAIL", f"compile failed: {[d.get('message') for d in cr.get('diagnostics', [])][:2]}"
               " (is `npm install --prefix src/node` done?)")
        return
    _plan, comps, _facts = critic.slide_context(state)
    boxed = [c.id for c in comps if c.box]
    ok = len(boxed) == len(comps) and drawn_xml(cr)
    report("2 component boxes", "PASS" if ok else "FAIL",
           f"{len(boxed)}/{len(comps)} components have a box" + ("" if drawn_xml(cr) else "; no drawn.xml"))

    # 3 screenshot + marks
    from src.agents import slide_facts
    from src.compiler.screenshot import render_screenshots
    shots = render_screenshots(cr["pptx_path"], str(OUT / run_id / "shots"))
    png = shots.slides[0].png_path if shots.ok and shots.slides else None
    if png:
        marked = slide_facts.draw_marks(png, comps, OUT / run_id / "marked.png")
        report("3 screenshot + marks", "PASS" if marked else "FAIL", marked or "no component box to mark")
    else:
        report("3 screenshot + marks", "FAIL", shots.error or "no PNG")
        png = str(OUT / run_id / "stand-in.png")   # steps 4-8 do not depend on the picture
        from PIL import Image
        Path(png).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1280, 720), "white").save(png)

    shot = SimpleNamespace(ok=True, error=None, slides=[SimpleNamespace(png_path=png)])
    ok_all = VisualCriticOutput(observations="fine", regenerate=False, verdicts=[
        ComponentVerdict(id=c.id, verdict="ok", severity="none", check="none", what_i_see="reads", owner="slide")
        for c in comps])

    # 4 critic input
    seen = _FakeVision(ok_all)
    with patch.object(visual_critic, "get_llm", lambda _n: seen), \
            patch.object(critic, "render_screenshots", lambda *a, **k: shot):
        out = critic.critic_node(state)
    if not seen.messages:
        report("4 critic input", "FAIL", "the vision critic was not called")
        return
    system, user = seen.messages
    text = user["content"][-1]["text"]
    images = sum(c["type"] == "image_url" for c in user["content"])
    checks = {"fixed system prompt": system["content"] == visual_critic.system_prompt(),
              "two images": images == 2, "component table": "[1] slide_title" in text,
              "annotated ref tags": "<!-- [2]" in text and "<KpiRow ref=" in text,
              "passed": out["critic_result"]["passed"]}
    bad = [k for k, v in checks.items() if not v]
    report("4 critic input", "FAIL" if bad else "PASS", ("missing: " + ", ".join(bad)) if bad else
           f"{len(comps)} components, {len(system['content'])} chars of fixed system prompt")

    # 5 code first: a measured defect goes to the fixer, no vision call
    kpi = next(c for c in comps if c.kind == "kpi_row")
    dense = {**state, "compile_result": {**cr, "warnings": [{"code": "SLIDE_DENSE", "message": "...", "spills": [
        {"type": "vstack", "kind": "h", "need": 260, "have": 180, "ids": kpi.box_ids}]}]}}
    with patch.object(visual_critic, "get_llm", lambda _n: _FakeVision()), \
            patch.object(critic, "render_screenshots", lambda *a, **k: shot):
        out = critic.critic_node(dense)
    strat = out["visual_critic_result"]["repair_hints"]["strategy"]
    ok = strat == "relayout" and kpi.id in out["critic_result"]["issues"][0]["description"]
    report("5 code first", "PASS" if ok else "FAIL", f"strategy {strat}")

    # 6 a fix on the drawn XML compiles with fit-grow off and is kept as written
    drawn = drawn_xml(cr)
    box = re.search(rf'<VStack id="{re.escape(kpi.box_ids[0])}"', drawn) or re.search(rf'id="{re.escape(kpi.box_ids[0])}"', drawn)
    if not box:
        report("6 fix kept", "FAIL", f"{kpi.box_ids[0]} not in the drawn XML")
        return
    old = box.group(0)
    edit = Edit(old=old, new=old + ' backgroundColor="$accentSoft" padding="14"')
    state["visual_critic_result"] = {"issues": [{"severity": "medium", "description": f"[Visual] [{kpi.n}] {kpi.id}: flat"}],
                                     "repair_hints": {"strategy": "fix"}}
    with patch.object(visual_repairer, "get_llm", lambda _n: _fixer(FixerOutput(plan="tint", edits=[edit]))):
        fixed = visual_repairer.visual_repairer_node(state)
    new_drawn = drawn_xml(fixed.get("compile_result")) if fixed.get("compile_result") else ""
    ok = fixed.get("visual_repair_outcome") == "improved" and 'backgroundColor="$accentSoft" padding="14"' in new_drawn
    report("6 fix kept", "PASS" if ok else "FAIL", f"outcome {fixed.get('visual_repair_outcome')}"
           + ("" if ok else " (the fixer's values were not drawn as written)"))
    if not ok:
        return

    # 7 a rewording of code-drawn content is rolled back
    start = drawn.index(old)
    word = re.search(r">([^<>]*\d[^<>]*)<", drawn[start:])
    if not word:
        report("7 fix rolled back", "SKIP", "no number in the KPI row to reword")
    else:
        end = start + word.end()
        snippet = drawn[max(0, end - 80):end]
        reword = Edit(old=snippet, new=snippet[:-len(word.group(0))] + ">reworded<")
        with patch.object(visual_repairer, "get_llm", lambda _n: _fixer(FixerOutput(plan="x", edits=[reword]))):
            rb = visual_repairer.visual_repairer_node({**state, "visual_repair_count": 6})   # its own folder
        report("7 fix rolled back", "PASS" if rb.get("visual_repair_outcome") == "rolled_back" else "FAIL",
               f"outcome {rb.get('visual_repair_outcome')}")

    # 8 the deck gets the fixed slide, as drawn
    saved = slide_router_node({**state, **fixed})["completed_slides"][0]["xml"]
    deck, n = assemble_deck_xml([saved], theme["element"])
    ok = saved == new_drawn and "<!-- fit-grow: off -->" in deck and n == 1
    report("8 deck as drawn", "PASS" if ok else "FAIL",
           "slide_router saves the fixed drawn XML; the deck compiles it with fit-grow off" if ok else "deck differs")


def paid_check(case: str, critic_model: str | None) -> None:
    from src.graph import run
    from src.utils import llm_client
    from src.utils.case_loader import load_case
    from src.utils.logging_config import add_file_log, setup_logging
    setup_logging()
    c = load_case(case)
    run_id = f"{case}-critic-{uuid.uuid4().hex[:6]}"
    OUT.mkdir(parents=True, exist_ok=True)
    log_path = OUT / f"{run_id}.log"
    handler = add_file_log(log_path)
    real = llm_client.get_llm
    # the critic A/B arm: the vision critic on another model (a reasoning model needs the larger budget)
    arm = {"model": critic_model, "max_tokens": 16000, "reasoning_effort": "medium"} if critic_model else {}
    try:
        with patch.object(visual_critic, "get_llm", lambda step, **kw: real(step, **{**arm, **kw})):
            supplied = c.get("supplied_content")
            final = run(c.get("request", c.get("objective", "")), theme=c.get("theme", ""), critic_mode="auto",
                        run_id=run_id, supplied_content=None if isinstance(supplied, str) else supplied, test_case=c)
    finally:
        import logging
        logging.getLogger().removeHandler(handler)
        handler.close()
    log = log_path.read_text(encoding="utf-8")
    slides = len(final.get("completed_slides") or [])
    count = lambda pat: len(re.findall(pat, log))   # noqa: E731
    reviews, shot_fail = count(r"critic: passed="), count(r"critic: screenshot failed")
    measured = count(r"strategy=relayout \(")
    kept, rolled = count(r"visual_repairer: kept"), count(r"visual_repairer: rolled_back")
    errors, noop = count(r"visual_repairer: error"), count(r"visual_repairer: noop")
    fixes = count(r"visual_repairer: (FIX|RELAYOUT|REGENERATE),")
    defects = ROOT / "output" / "runs" / run_id / "code-defects.jsonl"
    n_defects = len(defects.read_text(encoding="utf-8").splitlines()) if defects.exists() else 0
    cost = ((final.get("evaluation") or {}).get("cost") or {}).get("total_usd", 0.0)
    print(f"\n{case} (critic {critic_model or 'models.yaml'}): {slides} slides, {reviews} reviews, {measured} measured "
          f"-> relayout, {fixes} fixes: {kept} kept, {rolled} rolled back, {errors} errors, {noop} no change; "
          f"{n_defects} code defects; ${cost:.3f} - log {log_path}")
    for line in re.findall(r"visual_critic: (?:high|medium|low) [^\n]*|visual_repairer: (?:rolled_back|error)[^\n]*", log):
        print("  " + line)
    report("P1 deck finished", "PASS" if final.get("passed") else "FAIL", f"{slides} slides")
    report("P2 critic reviewed slides", "PASS" if reviews and not shot_fail else "FAIL",
           f"{reviews} reviews, {shot_fail} screenshot failures")
    report("P3 a fix ran", "PASS" if fixes else "SKIP", f"{fixes} fixes, {kept} kept" if fixes else "nothing to fix")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--paid", action="store_true", help="also run one deck with critic auto (uses the API)")
    ap.add_argument("--case", default="deck-overflow-repair", help="the deck for --paid")
    ap.add_argument("--critic-model", default=None, help="--paid: run the vision critic on this model instead")
    args = ap.parse_args()
    print("Critic-auto check, free steps (LLMs faked)\n")
    free_checks()
    if args.paid:
        print(f"\nPaid step: {args.case} with critic auto\n")
        paid_check(args.case, args.critic_model)
    failed = [s for s, st, _ in RESULTS if st == "FAIL"]
    print("\n" + ("ALL PASSED" if not failed else f"FAILED: {', '.join(failed)}"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
