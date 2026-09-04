"""generate.py — CLI entry point for the POM XML generation MVP.

    python python/generate.py --request "A title slide about Q3 results"
    python python/generate.py --request "..." --dry-run            # no API key needed
    python python/generate.py --request "..." --theme emerald-clean
    python python/generate.py --test-case-file tests/cases/kpi-row.yaml

Full pipeline:
    request -> SlideIR -> context_selector -> GenerationContract
            -> prompt_builder -> [LLM] -> pre_validator -> compiler -> evaluator
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make sibling modules importable when run as `python python/generate.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import prompt_builder  # noqa: E402
import slide_ir  # noqa: E402
from compiler_client import CompilerError, compile_xml, validate_xml  # noqa: E402
from context_selector import select_context  # noqa: E402
from evaluator import evaluate, new_run_id  # noqa: E402
from llm_client import LLMClient  # noqa: E402
from models import AttemptRecord, RetryOutcome, SlideIR, TokenUsage  # noqa: E402
from pre_validator import normalize_xml, pre_validate  # noqa: E402
from repair_guidance import (  # noqa: E402
    build_error_guidance, error_signatures, is_stalled,
)

# A source of raw XML for one attempt: (system_prompt, user_prompt, attempt_idx)
# -> (raw_xml, TokenUsage). Lets tests drive the retry loop without an API.
from typing import Callable  # noqa: E402
XmlProvider = Callable[[str, str, int], "tuple[str, TokenUsage]"]


def _llm_provider(system: str, user: str, attempt: int) -> "tuple[str, TokenUsage]":
    resp = LLMClient().complete(system, user)
    print(f"llm: {resp.model}  in={resp.tokens.input} out={resp.tokens.output} "
          f"finish={resp.finish_reason}")
    return resp.text, resp.tokens


# ── Pipeline ────────────────────────────────────────────────────────────────
def run(
    ir: SlideIR,
    *,
    output_root: Path,
    dry_run: bool,
    test_case: str | None = None,
    xml_provider: "XmlProvider | None" = None,
    run_id: str | None = None,
) -> Path:
    run_id = run_id or new_run_id()
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    required_components = [c.value for c in ir.component_kinds]

    print(f"run {run_id}  dry_run={dry_run}")
    print(f"output: {out_dir}")
    print(f"slide-ir: objective={ir.objective!r}  components={required_components}")

    (out_dir / "slide-ir.json").write_text(ir.model_dump_json(indent=2), encoding="utf-8")

    # 0. Context selection ------------------------------------------------
    contract = select_context(ir)
    (out_dir / "contract.json").write_text(
        contract.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"contract: nodes={contract.allowed_nodes}  "
          f"examples={len(contract.examples)}  notes={len(contract.notes)}")

    system_prompt, user_prompt = prompt_builder.build(ir, contract)
    (out_dir / "prompt-system.txt").write_text(system_prompt, encoding="utf-8")
    (out_dir / "prompt-user.txt").write_text(user_prompt, encoding="utf-8")
    approx_ctx_chars = len(system_prompt) + len(user_prompt)
    print(f"prompt: ~{approx_ctx_chars} chars (~{approx_ctx_chars // 4} tokens)")

    tokens = TokenUsage()
    retry = RetryOutcome()

    if xml_provider is None:
        if dry_run:
            import re as _re
            _raw = config.DRY_RUN_XML.read_text(encoding="utf-8")
            _theme_el = contract.theme_element
            if _theme_el:
                _body = _re.sub(r"<Theme\b[^>]*?/>\s*", "", _raw, count=1).lstrip()
                _canned = f"{_theme_el}\n{_body}"
            else:
                _canned = _raw

            def xml_provider(_s: str, _u: str, _a: int):  # noqa: ANN202
                print(f"dry-run: using {config.DRY_RUN_XML.name} as the generated XML")
                return _canned, TokenUsage()
        else:
            xml_provider = _llm_provider

    budget = max(0, config.settings.retry_budget)
    current_user = user_prompt

    def _one_pass(attempt: int, tag: str):
        raw_xml, tok = xml_provider(system_prompt, current_user, attempt)
        (out_dir / f"response-raw{tag}.xml").write_text(raw_xml, encoding="utf-8")

        # Step 1: Normalize (always — strip fences, # colors, br/hr, zero spacing)
        pv = normalize_xml(raw_xml)
        (out_dir / f"cleaned{tag}.xml").write_text(pv.cleaned_xml, encoding="utf-8")
        if pv.issues:
            print(f"normalize: {pv.issues_found} issue(s), {pv.auto_fixed} auto-fixed"
                  + ("  [BLOCKING]" if pv.blocking else ""))
            for i in pv.issues:
                print(f"  - {i.code}: {i.message}")

        # Step 2: Validate via parseXml (fast structural check, no PPTX gen)
        val = validate_xml(pv.cleaned_xml, out_dir)
        if val is None:
            # parseXml unavailable — fall back to full regex-based pre_validate
            print("validate: parseXml unavailable, using pre_validator fallback")
            pv = pre_validate(raw_xml, contract)
            (out_dir / f"cleaned{tag}.xml").write_text(pv.cleaned_xml, encoding="utf-8")
            if pv.issues:
                print(f"pre-validator: {pv.issues_found} issue(s), {pv.auto_fixed} "
                      f"auto-fixed{'  [BLOCKING]' if pv.blocking else ''}")
                for i in pv.issues:
                    print(f"  - {i.code}: {i.message}")
        elif not val.ok:
            # parseXml found errors — skip expensive buildPptx compile
            print(f"validate (parseXml): FAILED -- {len(val.diagnostics)} error(s)")
            for d in val.diagnostics:
                print(f"  ! {d.type}: {d.message}")
            return raw_xml, pv, val, tok

        # Step 3: Compile (buildPptx) — only reached if validation passed
        try:
            cr = compile_xml(pv.cleaned_xml, out_dir)
        except CompilerError as exc:
            print(f"compiler error: {exc}", file=sys.stderr)
            raise
        print(f"compile: {cr.status}"
              + (f"  ({cr.primary_error_type})" if not cr.ok else ""))
        for d in cr.diagnostics:
            print(f"  ! {d.type}: {d.message}")
        for w in cr.warnings:
            print(f"  ~ warning {w.code}: {w.message}")
        return raw_xml, pv, cr, tok

    def _problems(pv, cr) -> list[str]:
        out = [f"{i.code}: {i.message}" for i in pv.issues if not i.auto_fixed]
        out += [f"{d.type}: {d.message}" for d in cr.diagnostics]
        return out

    def _issue_dicts(pv) -> list[dict]:
        return [i.model_dump() for i in pv.issues if not i.auto_fixed]

    def _diag_dicts(cr) -> list[dict]:
        return [d.model_dump() for d in cr.diagnostics]

    def _select_template() -> str:
        """Pick the best verified example XML for tier 3 fallback."""
        comp_kinds = ir.component_kinds
        from models import ComponentKind as CK
        if CK.chart in comp_kinds and CK.table in comp_kinds:
            name = "mixed-slide.xml"
        elif CK.chart in comp_kinds:
            name = "chart-slide.xml"
        elif CK.table in comp_kinds:
            name = "table-slide.xml"
        elif CK.kpi_row in comp_kinds:
            name = "kpi-slide.xml"
        else:
            name = "text-slide.xml"
        path = config.EXAMPLES_DIR / name
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return (config.EXAMPLES_DIR / "text-slide.xml").read_text(encoding="utf-8").strip()

    def _simplify_instructions(problems: list[str]) -> str:
        """Generate simplification instructions for tier 2."""
        lines = [
            "The previous XML was too complex or structurally broken.",
            "Simplify the layout:",
            "- Reduce to at most 3 visual sections (header, body, footer)",
            "- Use body fontSize=12, heading fontSize=18 (compact tier)",
            "- Reduce root padding to 32, gaps to 8-12",
            "- If there are >4 KPI tiles, reduce to 3",
            "- If there are 2 charts, keep only the most important one",
            "- Drop the bullet list if charts+table are present",
            "- Ensure all dimensions are positive and fit within 1280x720",
        ]
        return "\n".join(lines)

    # 1-3. First pass --------------------------------------------------------
    raw_xml, pre, compiled, tokens = _one_pass(0, "")

    # Record initial attempt
    init_record = AttemptRecord(
        attempt=0,
        tier=0,
        errors_out=_problems(pre, compiled),
        tokens=tokens,
    )
    retry.attempt_records.append(init_record)

    # 4. Retry loop — 3-tier escalating strategy ─────────────────────────────
    #
    #   Tier 1 (PATCH): feed back the failing XML + annotated errors +
    #          error-specific guidance. Asks the AI to fix in place.
    #   Tier 2 (SIMPLIFY): regenerate with a reduced/simpler layout.
    #          Fresh generation with simpler constraints.
    #   Tier 3 (TEMPLATE): use a verified example as a structural skeleton.
    #          The AI fills in content only — can't break the structure.
    #
    #   Stall detection: if ≥80% of errors repeat, skip to next tier.
    prev_sigs: set[str] = error_signatures(_issue_dicts(pre), _diag_dicts(compiled))
    current_tier = 1
    attempt = 0

    while attempt < budget:
        needs_retry = not compiled.ok and compiled.retryable
        if not needs_retry:
            break
        attempt += 1
        if not retry.attempted:
            retry.attempted = True
            retry.reason = ("compile_error" if not compiled.ok else "prevalidation_blocking")

        problems = _problems(pre, compiled)
        retry.diagnostics_fed_back = problems

        # Check for stall → escalate tier
        curr_sigs = error_signatures(_issue_dicts(pre), _diag_dicts(compiled))
        if attempt > 1 and is_stalled(prev_sigs, curr_sigs):
            current_tier = min(current_tier + 1, 3)
            retry.stall_count += 1
            print(f"retry {attempt}/{budget}: STALL detected, escalating to tier {current_tier}")

        retry.max_tier_used = max(retry.max_tier_used, current_tier)
        tier_name = {1: "PATCH", 2: "SIMPLIFY", 3: "TEMPLATE"}.get(current_tier, "?")
        print(f"retry {attempt}/{budget}: tier {current_tier} ({tier_name}), "
              f"{len(problems)} problem(s) (reason={retry.reason})")

        # Build the repair prompt based on current tier
        if current_tier == 1:
            guidance = build_error_guidance(_issue_dicts(pre), _diag_dicts(compiled))
            current_user = prompt_builder.build_repair_patch(
                user_prompt, pre.cleaned_xml, problems, guidance,
            )
        elif current_tier == 2:
            simplify = _simplify_instructions(problems)
            current_user = prompt_builder.build_repair_simplify(
                user_prompt, problems, simplify, contract.allowed_nodes,
            )
        else:  # tier 3
            template_xml = _select_template()
            current_user = prompt_builder.build_repair_template(
                user_prompt, template_xml,
            )

        (out_dir / f"prompt-user-retry{attempt}.txt").write_text(
            current_user, encoding="utf-8"
        )
        raw_xml, pre, compiled, tok = _one_pass(attempt, f"-retry{attempt}")
        tokens = TokenUsage(input=tokens.input + tok.input,
                            output=tokens.output + tok.output)

        # Record this attempt
        record = AttemptRecord(
            attempt=attempt,
            tier=current_tier,
            errors_in=problems,
            errors_out=_problems(pre, compiled),
            stalled=is_stalled(prev_sigs, curr_sigs) if attempt > 1 else False,
            tokens=tok,
        )
        retry.attempt_records.append(record)
        prev_sigs = curr_sigs

        # If still failing after this tier's attempt, escalate for next round
        still_failing = not compiled.ok and compiled.retryable
        if still_failing and current_tier < 3:
            current_tier += 1

    retry.attempts = attempt
    if retry.attempted:
        retry.succeeded = compiled.ok
        print(f"retry: {retry.attempts} attempt(s), max_tier={retry.max_tier_used}, "
              f"{'RECOVERED' if retry.succeeded else 'still failing'}")

    # final.xml = the exact XML that produced the final compile result. Deck
    # assembly and any downstream tooling should read this, not cleaned*.xml.
    (out_dir / "final.xml").write_text(pre.cleaned_xml, encoding="utf-8")

    # 5. Evaluate --------------------------------------------------------
    ev = evaluate(
        run_id=run_id,
        request=ir.request,
        pre=pre,
        compiled=compiled,
        required_components=required_components,
        tokens=tokens,
        retry=retry,
        test_case=test_case,
    )
    eval_path = out_dir / "evaluation.json"
    eval_path.write_text(ev.to_json(), encoding="utf-8")
    print(f"evaluation: {'PASS' if ev.passed else 'FAIL'}  -> {eval_path}")
    if compiled.ok:
        print(f"pptx: {compiled.pptx_path}")
    return eval_path


def _build_ir(args: argparse.Namespace) -> tuple[SlideIR, str | None]:
    if args.test_case_file:
        path = Path(args.test_case_file)
        if not path.is_absolute():
            path = config.PROJECT_ROOT / path
        import yaml
        case = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        ir = slide_ir.from_test_case(case)
        if args.theme:
            ir.theme = args.theme
        return ir, case.get("name") or path.stem

    if not args.request:
        raise SystemExit("error: one of --request or --test-case-file is required")

    supplied = json.loads(args.supplied) if args.supplied else None
    ir = slide_ir.from_request(
        args.request,
        objective=args.objective,
        components=args.components,
        theme=args.theme or "",
        supplied_content=supplied,
    )
    return ir, args.test_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a POM XML slide -> PPTX.")
    parser.add_argument("--request", help="Natural-language slide request.")
    parser.add_argument("--test-case-file", help="Path to a tests/cases/*.yaml file.")
    parser.add_argument("--objective", default=None, help="Override the slide objective.")
    parser.add_argument(
        "--output",
        default=str(config.OUTPUT_DIR / "runs"),
        help="Root directory for run output (a per-run subdir is created).",
    )
    parser.add_argument(
        "--theme", default=None,
        help="Palette name from pom-knowledge/theme/palettes.yaml (or dark/light). "
             "Overrides the test case / theme.yaml; unset uses those / the default.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the LLM call; use a canned example XML. No API key needed.",
    )
    parser.add_argument("--test-case", default=None, help="Optional test-case label.")
    parser.add_argument("--supplied", default=None, help="JSON string of supplied content.")
    parser.add_argument(
        "--component",
        action="append",
        default=None,
        dest="components",
        help="Required component (repeatable): title, narrative, caption, kpi_row, "
        "bullet_list, chart, table. Overrides keyword detection.",
    )
    args = parser.parse_args(argv)

    try:
        ir, test_case = _build_ir(args)
        run(
            ir,
            output_root=Path(args.output),
            dry_run=args.dry_run,
            test_case=test_case,
        )
    except (CompilerError, RuntimeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
