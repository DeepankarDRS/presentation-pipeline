"""deck.py — multi-slide deck generation (Phase 9).

Each slide is generated independently through the single-slide pipeline
(generate.run), then the slides are assembled under ONE shared <Theme> and
compiled once into a single .pptx.

    python python/deck.py --deck-file tests/decks/quarterly-review.yaml
    python python/deck.py --deck-file tests/decks/quarterly-review.yaml --dry-run
    python python/deck.py --deck-file ... --theme emerald-clean

Cross-slide theme consistency is enforced structurally: every slide's own
<Theme> element is stripped and the canonical deck theme (resolved from
pom-knowledge/theme/palettes.yaml via python/theme.py) is prepended once.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import generate  # noqa: E402
import slide_ir  # noqa: E402
import theme as theme_lib  # noqa: E402
import yaml  # noqa: E402
from compiler_client import CompilerError, compile_xml  # noqa: E402
from evaluator import new_run_id  # noqa: E402
from models import DeckEvaluationResult, DeckIR, TokenUsage  # noqa: E402

_THEME_RE = re.compile(r"<Theme\b[^>]*?/>", re.IGNORECASE)
_SLIDE_RE = re.compile(r"<Slide\b.*?</Slide>", re.IGNORECASE | re.DOTALL)


# ── spec -> DeckIR ─────────────────────────────────────────────────────────
def from_spec(spec: dict) -> DeckIR:
    if "title" not in spec:
        raise ValueError("deck spec is missing 'title'")
    raw_slides = spec.get("slides") or []
    if not raw_slides:
        raise ValueError("deck spec has no 'slides'")

    # Deck-wide palette: spec `theme:` > project theme.yaml > library default.
    cfg_name, _ = config.load_theme_config()
    deck_theme = str(spec.get("theme") or cfg_name or "").strip()

    slides = []
    for entry in raw_slides:
        if isinstance(entry, str):
            entry = {"request": entry}
        if "request" not in entry:
            raise ValueError(f"deck slide is missing 'request': {entry!r}")
        slides.append(slide_ir.from_request(
            entry["request"],
            objective=entry.get("objective"),
            components=entry.get("components"),
            theme=deck_theme,
            supplied_content=entry.get("supplied_content") or entry.get("supplied"),
        ))

    return DeckIR(
        title=spec["title"],
        objective=spec.get("objective", ""),
        theme=deck_theme,
        slides=slides,
    )


# ── assembly ──────────────────────────────────────────────────────────────
def _canonical_theme(theme_name: str) -> str:
    cfg_name, cfg_overrides = config.load_theme_config()
    resolved = theme_lib.resolve(theme_name or cfg_name, cfg_overrides)
    for w in resolved.warnings:
        print(f"theme: {w}", file=sys.stderr)
    return theme_lib.theme_element(resolved)


def assemble_deck(slide_xmls: list[str], theme_name: str) -> tuple[str, bool]:
    """Strip each slide's <Theme>, keep the <Slide> blocks, prepend one theme.

    Returns (deck_xml, theme_consistent). theme_consistent is False if any slide
    emitted a <Theme> that differs from the canonical deck theme.
    """
    theme = _canonical_theme(theme_name)
    consistent = True
    blocks: list[str] = []

    for sx in slide_xmls:
        for found in _THEME_RE.findall(sx):
            if theme and found.strip() != theme:
                consistent = False
        body = _THEME_RE.sub("", sx).strip()
        slides = [m.group(0) for m in _SLIDE_RE.finditer(body)]
        blocks.extend(slides if slides else [body])

    parts = ([theme] if theme else []) + blocks
    return "\n".join(parts).strip() + "\n", consistent


# ── generation ────────────────────────────────────────────────────────────
def generate_deck(
    deck_ir: DeckIR,
    *,
    output_root: Path,
    dry_run: bool,
    xml_provider=None,
) -> Path:
    run_id = new_run_id()
    deck_dir = output_root / run_id
    deck_dir.mkdir(parents=True, exist_ok=True)
    (deck_dir / "deck-ir.json").write_text(deck_ir.model_dump_json(indent=2), encoding="utf-8")

    print(f"deck {run_id}  '{deck_ir.title}'  "
          f"slides={deck_ir.slide_count}  theme={deck_ir.theme or '(default)'}  dry_run={dry_run}")
    print(f"output: {deck_dir}\n")

    slide_summaries: list[dict] = []
    slide_xmls: list[str] = []
    total_in = total_out = 0

    for i, s_ir in enumerate(deck_ir.slides, 1):
        sid = f"slide-{i:02d}"
        print(f"================  {sid}  ================")
        eval_path = generate.run(
            s_ir,
            output_root=deck_dir,
            dry_run=dry_run,
            run_id=sid,
            xml_provider=xml_provider,
        )
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        final_xml = (eval_path.parent / "final.xml").read_text(encoding="utf-8")
        slide_xmls.append(final_xml)

        tok = ev.get("tokens", {})
        total_in += tok.get("input", 0)
        total_out += tok.get("output", 0)
        slide_summaries.append({
            "slide": sid,
            "objective": s_ir.objective,
            "components": [c.value for c in s_ir.component_kinds],
            "compiled": ev["compilation"]["status"] == "success",
            "passed": bool(ev.get("passed")),
            "error_type": ev["compilation"].get("error_type"),
            "warnings": len(ev["compilation"].get("warnings", [])),
            "retry": ev.get("retry", {}),
            "tokens": tok,
        })
        print()

    # Assemble + compile the whole deck once.
    deck_xml, consistent = assemble_deck(slide_xmls, deck_ir.theme)
    (deck_dir / "deck.xml").write_text(deck_xml, encoding="utf-8")
    n_slides = len(_SLIDE_RE.findall(deck_xml))
    print(f"================  deck  ================")
    print(f"assembled {n_slides} <Slide> block(s), theme_consistent={consistent}")

    try:
        compiled = compile_xml(deck_xml, deck_dir / "deck")
    except CompilerError as exc:
        print(f"deck compiler error: {exc}", file=sys.stderr)
        raise

    print(f"deck compile: {compiled.status}"
          + (f"  ({compiled.primary_error_type})" if not compiled.ok else ""))
    for d in compiled.diagnostics:
        print(f"  ! {d.type}: {d.message}")
    for w in compiled.warnings:
        print(f"  ~ warning {w.code}: {w.message}")

    slides_all_pass = all(s["passed"] for s in slide_summaries)
    dev = DeckEvaluationResult(
        run_id=run_id,
        title=deck_ir.title,
        slide_count=deck_ir.slide_count,
        slides=slide_summaries,
        deck_compilation={
            "status": compiled.status,
            "error_type": compiled.primary_error_type,
            "diagnostics": [d.model_dump() for d in compiled.diagnostics],
            "warnings": [w.model_dump() for w in compiled.warnings],
            "pptx_path": compiled.pptx_path,
            "slide_blocks": n_slides,
        },
        tokens=TokenUsage(input=total_in, output=total_out),
        theme_consistent=consistent,
        passed=compiled.ok and not compiled.warnings and slides_all_pass and consistent,
    )
    out = deck_dir / "deck-evaluation.json"
    out.write_text(dev.to_json(), encoding="utf-8")
    print(f"\ndeck: {'PASS' if dev.passed else 'FAIL'}  "
          f"(slides {sum(s['passed'] for s in slide_summaries)}/{deck_ir.slide_count} pass)  -> {out}")
    if compiled.ok:
        print(f"pptx: {compiled.pptx_path}")
    return out


# ── CLI ───────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a multi-slide POM deck -> PPTX.")
    parser.add_argument("--deck-file", required=True, help="Path to a tests/decks/*.yaml spec.")
    parser.add_argument("--output", default=str(config.OUTPUT_DIR / "decks"))
    parser.add_argument("--theme", default=None,
                        help="Override the deck spec's theme with a palette name "
                             "from pom-knowledge/theme/palettes.yaml (or dark/light).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip the LLM; canned XML per slide. No API key.")
    args = parser.parse_args(argv)

    try:
        path = Path(args.deck_file)
        if not path.is_absolute():
            path = config.PROJECT_ROOT / path
        spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if args.theme:
            spec["theme"] = args.theme
        deck_ir = from_spec(spec)
        generate_deck(
            deck_ir,
            output_root=Path(args.output),
            dry_run=args.dry_run,
        )
    except (CompilerError, RuntimeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
