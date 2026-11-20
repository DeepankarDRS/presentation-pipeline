"""Is the critic-auto loop working on slides with composition nodes (code-drawn KPI rows, charts, tables, ...)?

    python -m scripts.critic_check            # free: the real loop on a fixture slide, the LLMs faked
    python -m scripts.critic_check --paid     # also one real deck with critic auto (deck-qbr-data, about $0.25)
    python -m scripts.critic_check --paid --case deck-overflow-repair   # 2 overfull slides that should repair

Prints PASS / FAIL / SKIP per step and exits 1 when a step fails. Free steps:
  1 screenshot backend    comtypes + PowerPoint COM (without it the critic passes every slide unseen)
  2 validator             the ref tags (<KpiRow ref>, <Chart ref>) are drawn by code and compile
  3 screenshot            the compiled slide renders to a PNG (the critic's input)
  4 critic prompt         the critic is told which components code draws and gets the XML the repair edits
  5 visual repair         a patch of the ref-tag XML compiles on the validator's path and is accepted
  6 deck gets the repair  slide_router saves the repaired slide, not the pre-repair one
  7 rollback              a repair that scores worse restores the pre-repair XML and compiled results
--paid: runs the deck and reads its log: every slide reviewed, no screenshot failure, no repair discarded
for an unknown tag; counts patch / regenerate repairs and prints each issue the code-owned filter dropped. The log is written to output/critic-check/<run_id>.log.
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
from src.agents.deck_nodes import slide_router_node  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.agents.validator import validator_node  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "nodes" / "runs" / "decks" / "gate-deck-all-nodes-dense__r1" / "slides.json"
OUT = ROOT / "output" / "critic-check"
RESULTS: list[tuple[str, str, str]] = []


def report(step: str, status: str, detail: str = "") -> None:
    RESULTS.append((step, status, detail))
    print(f"[{status:4}] {step}" + (f" - {detail}" if detail else ""), flush=True)


def _slide() -> tuple[dict, str, str]:
    """A fixture slide with two KPI rows and a chart, written as the generator writes it: ref tags only."""
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))[1]["slide_plan"]
    kpis = [c["component_id"] for c in plan["components"] if c["kind"] == "kpi_row"]
    chart = next(c["component_id"] for c in plan["components"] if c["kind"] == "chart")
    xml = ('<Slide><VStack w="1280" h="720" padding="48" gap="20" alignItems="stretch" backgroundColor="$surface">'
           f'<Text fontSize="36" bold="true" color="$textMain">{plan["slide_title"]}</Text>'
           + "".join(f'<KpiRow ref="{k}"/>' for k in kpis)
           + f'<Chart ref="{chart}" grow="1" h="max" minH="180"/>'
           '<Text fontSize="18" color="$textMain">Repeat customers carry the growth.</Text></VStack></Slide>')
    return plan, xml, chart


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

    plan, xml, chart = _slide()
    theme = resolve_theme("corporate-slate")
    run_id = f"critic-check-{uuid.uuid4().hex[:6]}"
    state = {"current_xml": xml, "slide_plans": [plan], "current_slide_index": 0, "retry_count": 0, "run_id": run_id,
             "completed_slides": [], "theme_element": theme["element"], "resolved_theme": theme,
             "contract": build_contract(plan, theme), "raw_request": "critic check", "critic_mode": "auto"}

    # 2 validator
    state.update(validator_node(state))
    cr = state.get("compile_result") or {}
    if not cr.get("ok"):
        report("2 validator", "FAIL", f"compile failed: {[d.get('message') for d in cr.get('diagnostics', [])][:2]}"
               " (is `npm install --prefix src/node` done?)")
        return
    report("2 validator", "PASS", "ref tags drawn by code, slide compiles")

    # 3 screenshot
    from src.compiler.screenshot import render_screenshots
    shots = render_screenshots(cr["pptx_path"], str(OUT / run_id / "shots"))
    if shots.ok and shots.slides and shots.slides[0].png_path:
        report("3 screenshot", "PASS", shots.slides[0].png_path)
    else:
        report("3 screenshot", "FAIL", shots.error or "no PNG")

    # 4 critic prompt (the vision call is faked: it records the prompt and fails open)
    seen: dict[str, str] = {}

    class _FakeVision:
        def with_structured_output(self, schema, *a, **k):
            schema.model_json_schema()   # the real call builds this first: a broken schema fails every review
            return SimpleNamespace(invoke=lambda messages: seen.setdefault("text", messages[1]["content"][1]["text"])
                                   and (_ for _ in ()).throw(RuntimeError("faked")))

    png = shots.slides[0].png_path if shots.ok and shots.slides else None
    if not png:   # the prompt does not depend on the picture: a stand-in file keeps this step independent of step 3
        png = str(OUT / run_id / "stand-in.png")
        Path(png).parent.mkdir(parents=True, exist_ok=True)
        Path(png).write_bytes(b"\x89PNG\r\n\x1a\n")
    try:
        with patch.object(visual_critic, "get_llm", lambda _name: _FakeVision()):
            visual_critic.run_visual_critic(png, state["current_xml"], plan, theme["element"], state["contract"],
                                            tags_xml=state["normalize_result"]["tags_xml"])
    except Exception as exc:   # critic_node fails open on this: every slide passes unreviewed
        report("4 critic prompt", "FAIL", f"the critic's output schema does not build: {exc}".split("\n")[0])
        return
    text = seen.get("text", "")
    repair_xml = text.split("THE XML THE REPAIR EDITS")[-1]
    ok = "CODE-DRAWN COMPONENTS" in text and "<KpiRow" in repair_xml and "<Chart ref=" in repair_xml
    report("4 critic prompt", "PASS" if ok else "FAIL",
           "lists the code-drawn components and the ref-tag XML" if ok else "code-drawn context missing")

    # 5 visual repair: the faked repairer tints the chart's card on the ref-tag XML
    patched = xml.replace(f'<Chart ref="{chart}"', f'<Chart ref="{chart}" backgroundColor="$surfaceAlt" padding="16"')
    fake = SimpleNamespace(content=patched, response_metadata={"finish_reason": "stop"})
    usage = {"tokens_in": 0, "tokens_out": 0, "tokens_reasoning": 0, "tokens_cached": 0, "model": "fake"}
    state["visual_critic_result"] = {"issues": [{"severity": "medium", "description": "the chart floats", "fix": "tint "
                                                 "its card", "affected_nodes": ["Chart"]}],
                                     "repair_hints": {"strategy": "patch"}}
    pre = {k: state.get(k) for k in critic._ROLLBACK_KEYS}
    with patch.object(visual_repairer, "get_llm", lambda _name: SimpleNamespace(invoke=lambda m: fake)), \
            patch.object(visual_repairer, "extract_usage", lambda r: usage):
        out = visual_repairer.visual_repairer_node(state)
    if out.get("visual_repair_outcome") == "improved" and (out.get("compile_result") or {}).get("ok"):
        report("5 visual repair", "PASS", "patched ref-tag XML compiled and was accepted")
    else:
        report("5 visual repair", "FAIL", f"outcome {out.get('visual_repair_outcome')} (a discarded repair here is "
               "the unknown-tag bug)")
        return

    # 6 the deck gets the repaired slide
    repaired = {**state, **out}
    saved = slide_router_node(repaired)["completed_slides"][0]
    ok = 'padding="16"' in (repaired["normalize_result"].get("tags_xml") or "") and saved["xml"] != \
        (pre["normalize_result"] or {}).get("cleaned_xml")
    report("6 deck gets the repair", "PASS" if ok else "FAIL",
           "slide_router saves the repaired slide" if ok else "the deck would keep the pre-repair slide")

    # 7 rollback: a re-review that scores worse restores the pre-repair XML and compiled results
    rr = {**repaired, "visual_repair_count": 1, "pre_critic_xml": xml, "pre_critic_score": 0,
          "pre_critic_slide_plans": [plan], "pre_critic_contract": state["contract"], "pre_critic_results": pre,
          "visual_critic_result": {"issues": []}}
    worse = ([{"severity": "high", "description": "x", "fix": "y", "affected_nodes": []}], None,
             {"tokens_in": 0, "tokens_out": 0, "model": "fake"}, {"strategy": "patch", "assessment": "good"})
    with patch.object(critic, "_run_visual_review", lambda *a, **k: worse):
        upd = critic._critic_inner(rr, 0)
    ok = upd.get("current_xml") == xml and upd.get("compile_result") == pre["compile_result"] \
        and upd.get("normalize_result") == pre["normalize_result"]
    report("7 rollback", "PASS" if ok else "FAIL",
           "XML and compiled results restored" if ok else "rollback leaves the repaired results in place")


def paid_check(case: str) -> None:
    from src.graph import run
    from src.utils.case_loader import load_case
    from src.utils.logging_config import add_file_log, setup_logging
    setup_logging()
    c = load_case(case)
    run_id = f"{case}-critic-{uuid.uuid4().hex[:6]}"
    OUT.mkdir(parents=True, exist_ok=True)
    log_path = OUT / f"{run_id}.log"
    handler = add_file_log(log_path)
    try:
        supplied = c.get("supplied_content")
        final = run(c.get("request", c.get("objective", "")), theme=c.get("theme", ""), critic_mode="auto",
                    run_id=run_id, supplied_content=None if isinstance(supplied, str) else supplied, test_case=c)
    finally:
        import logging
        logging.getLogger().removeHandler(handler)
        handler.close()
    log = log_path.read_text(encoding="utf-8")
    slides = len(final.get("completed_slides") or [])
    reviews = len(re.findall(r"critic: passed=", log))
    shot_fail = len(re.findall(r"critic: screenshot failed", log))
    accepted = len(re.findall(r"visual_repairer: compiled OK", log))
    discarded = len(re.findall(r"repair broke compilation", log))
    unknown = len(re.findall(r"Unknown tag: <(KpiRow|CardGrid|Kpi|Card)>", log))
    rollbacks = len(re.findall(r"rolling back to pre-repair", log))
    patches = len(re.findall(r"visual_repairer: PATCH,", log))
    regens = len(re.findall(r"visual_repairer: REGENERATE,", log))
    no_change = len(re.findall(r"visual_repairer: identical XML", log))
    dropped = re.findall(r"visual_critic: dropped (?:low|medium|high) issue[^\n]*", log)
    cost = ((final.get("evaluation") or {}).get("cost") or {}).get("total_usd", 0.0)
    print(f"\n{case}: {slides} slides, {reviews} critic reviews, {patches} patch + {regens} regenerate repairs, "
          f"{accepted} accepted, {no_change} unchanged, {rollbacks} rolled back, {discarded} discarded, "
          f"${cost:.3f} - log {log_path}")
    for line in dropped:   # what the code-owned filter took away: check each against the slide's screenshot
        print("  " + line)
    report("P1 deck finished", "PASS" if final.get("passed") else "FAIL", f"{slides} slides")
    report("P2 critic reviewed slides", "PASS" if reviews and not shot_fail else "FAIL",
           f"{reviews} reviews, {shot_fail} screenshot failures")
    report("P3 no repair lost to an unknown tag", "PASS" if not unknown else "FAIL",
           f"{unknown} unknown-tag errors, {discarded} discarded repairs")
    # whether a repair runs is the critic's call on what it sees: none is not a failure (deck-overflow-repair aims at both)
    report("P4 a visual repair ran", "PASS" if patches + regens else "SKIP",
           f"{patches} patch, {regens} regenerate" if patches + regens else "the critic left nothing to repair")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--paid", action="store_true", help="also run one deck with critic auto (uses the API)")
    ap.add_argument("--case", default="deck-qbr-data", help="the deck for --paid")
    args = ap.parse_args()
    print("Critic-auto check, free steps (LLMs faked)\n")
    free_checks()
    if args.paid:
        print(f"\nPaid step: {args.case} with critic auto\n")
        paid_check(args.case)
    failed = [s for s, st, _ in RESULTS if st == "FAIL"]
    print("\n" + ("ALL PASSED" if not failed else f"FAILED: {', '.join(failed)}"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
