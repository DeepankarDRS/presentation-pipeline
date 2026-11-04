"""Composition nodes, paid same-plan check (docs/eval/nodes-paid/README.md): generator only, one saved plan through both routes.

    python -m scripts.composition_paid --estimate                             # free: cases + cost estimate only
    python -m scripts.composition_paid --label dry --dry --limit 2            # free: fake generator (path check)
    python -m scripts.composition_paid --label nodes-paid --bundle            # paid, test PC (OPENAI_API_KEY)
    python -m scripts.composition_paid --label nodes-paid --rescore           # free: score + blind sheet again

The same saved slide plans go through the real graph from the plan (scripts.kpi_paid.run_one: style resolver ->
context builder -> generator -> validator -> repairers; critic off), twice:
- A = today's route: POM_BLOCKS=tiles, POM_NODES empty (tile tags for KPI and cards; charts, tables, timelines and
  lists written by the LLM);
- B = composition nodes: POM_BLOCKS=tiles, POM_NODES = all six (src/compiler/nodes/composed.py).
The script sets both switches per arm before each run (they are read at call time; .env values are loaded first and
never override them). Cases: docs/eval/nodes-paid/inputs.json.
Per run: the first try's NODE_* codes, the composition the generator wrote vs the default code would pick (B), repairs,
cost, plan words missing from the slide, and the final slide scored like the replays (scripts.kpi_replay.score). Writes
output/composition-paid/<label>/: runs.json, results.json, summary.md, sheets/ (blind A / B: fill marks.csv; key.json
says which side is the composition nodes) and, with --bundle, <label>.zip to email back.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import kpi_paid as KP  # noqa: E402
from scripts import tile_same_plan as TS  # noqa: E402
from scripts.kpi_replay import compile_slide, score  # noqa: E402
from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.compiler_client import deck_font  # noqa: E402
from src.compiler.nodes import cards, composed, element_refs, tiles, validate  # noqa: E402

INPUTS = ROOT / "docs" / "eval" / "nodes-paid" / "inputs.json"
OUT = ROOT / "output" / "composition-paid"
NODES = ("chart", "timeline", "kpi_row", "card_grid", "table", "bullet_list")   # composed.kinds_on()'s order
ARMS = {"A": {"POM_BLOCKS": "tiles", "POM_NODES": ""},
        "B": {"POM_BLOCKS": "tiles", "POM_NODES": ",".join(NODES)}}
# per run on gpt-6.1-sol: 11-13k input tokens (mostly cached after the first), 300-3,000 output + reasoning; a repair
# adds a call. The tile-node runs cost $0.029 a first try and $0.052 with a long repair; arm A now hand-writes charts,
# tables and lists, so both are set higher
EST_RUN, EST_RUN_MAX = 0.04, 0.08
WATCH = ("NODE_ITEM_MISSING", "NODE_ATTR_UNKNOWN", "NODE_ATTR_NO_EFFECT", "NODE_ATTR_DROPPED", "NODE_ATTR_ALIAS", "NODE_TAG_ALIAS",
         "NODE_VARIANT_UNMET", "NODE_VARIANT_UNKNOWN", "NODE_LOOK_FROM_HINT", "NODE_HIGHLIGHT_UNKNOWN", "NODE_HIGHLIGHT_RULE")
_GROUP = re.compile(r"<(KpiRow|KpiGrid|CardGrid|Chart|Timeline|Table|Ul)\b([^>]*\sref=[^>]*)>")
_ATTR = re.compile(r'\s(variant|layout|arrange)="[^"]*"')


def set_arm(arm: str) -> None:
    """The arm's switches (an empty POM_NODES also keeps a .env value out: load_dotenv never overrides a set key)."""
    os.environ.update(ARMS[arm])
    want = list(NODES) if arm == "B" else []
    assert tiles.on() and sorted(composed.kinds_on()) == sorted(want), (arm, os.environ.get("POM_NODES"), composed.kinds_on())


def items() -> list[dict]:
    from src.utils.case_loader import load_case
    out = []
    for it in json.loads(INPUTS.read_text(encoding="utf-8")):
        c = load_case(it["case"])
        out.append(dict(it, request=c.get("request", c.get("objective", ""))))
    return out


def plan_texts(comp: dict) -> list[str]:
    """The words a component must show, whichever route drew it."""
    cd, kind = comp.get("content_data") or {}, comp.get("kind")
    if kind == "kpi_row":
        return [str(x) for k in ("kpi_labels", "kpi_values", "kpi_deltas") for x in cd.get(k) or []]
    if kind == "card_grid":
        out = []
        for c in cards.cards_of(comp):
            body, bullets = cards._lines(c)
            out += [str(c.get("title") or ""), str(c.get("tag") or ""), body, *bullets]
        return out
    if kind == "chart":
        return [str(x) for x in cd.get("chart_labels") or []]
    if kind == "table":
        return [str(x) for x in cd.get("table_columns") or []] + [str(x) for r in cd.get("table_rows") or [] for x in r]
    if kind == "timeline":
        return [str(i.get(k) or "") for i in cd.get("timeline_items") or [] if isinstance(i, dict) for k in ("date", "label", "description")]
    if kind == "bullet_list":
        return [str(x) for x in cd.get("bullets") or []]
    return []


def missing_words(final_xml: str, plan: dict) -> list[str]:
    """Plan texts the slide does not show: under 80% of their words on it (a split or wrapped text still counts)."""
    # also with inline tags closed up: a number and its unit are one word split by a span ("$48.2<Span>M</Span>")
    closed = re.sub(r"</?(?:Span|B|I|U|S|Mark)[^>]*>", "", final_xml)
    seen, out = validate.xml_words(final_xml) | validate.xml_words(closed), []
    for comp in plan.get("components") or []:
        for t in plan_texts(comp):
            ws = validate.words(t)
            if ws and sum(w in seen for w in ws) / len(ws) < 0.8:
                out.append(f'{comp.get("component_id")}: {t[:44]}')
    return out


def estimate(n_items: int, repeat: int) -> tuple[int, float, float]:
    n = n_items * repeat * len(ARMS)
    return n, n * EST_RUN, n * EST_RUN_MAX


def _dry_xml(it: dict, arm: str) -> str:
    """--dry: a bare slide of the arm's tags; B writes a variant the plan may not allow (the written-variant path)."""
    plan = it["plan"]
    if arm == "A":
        tags = "".join(f'<KpiGrid ref="{cid}"/>' for cid in element_refs.kpi_components(plan))
        tags += "".join(f'<CardGrid ref="{cid}"/>' for cid in cards.card_components(plan))
    else:
        tags = ""
        for kind in composed.kinds_on():
            for cid in composed.drawn(plan, kind):
                v = ' variant="rows"' if kind in ("kpi_row", "table", "bullet_list", "timeline", "chart") else ""
                tags += f'<{composed.tag(kind)} ref="{cid}"{v} grow="1"/>'
    title = str(plan.get("slide_title", "")).replace("&", "&amp;").replace("<", "&lt;")
    return (f'<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch" backgroundColor="$surface">'
            f'<Text fontSize="30" bold="true" color="$textMain">{title}</Text>{tags}</VStack></Slide>')


# ── the paid run ──────────────────────────────────────────────────────────────

def run(label: str, repeat: int, cases: list[dict], max_cost: float, dry: bool = False) -> list[dict]:
    out = OUT / label
    runs, spent = [], 0.0
    for r in range(1, repeat + 1):
        for it in cases:
            if not dry and spent + len(ARMS) * EST_RUN_MAX > max_cost:
                print(f"STOP: ${spent:.3f} spent; the next pair could pass --max-cost ${max_cost:.2f}", flush=True)
                break
            for arm in ARMS:
                set_arm(arm)
                case = f"{it['name']}-r{r}"
                rid = f"comp-{arm}-{it['case']}-s{it['slide']}-r{r}-{int(time.time())}"
                print(f"run {case} {arm} (POM_NODES={os.environ['POM_NODES'] or '-'}) ...", flush=True)
                try:
                    if dry:
                        from src.agents import generator
                        generator.get_llm = lambda step, _x=_dry_xml(it, arm): KP._FakeLLM(_x)
                    res = KP.run_one(it, rid)
                except Exception as e:   # one failure must not cost the other runs
                    res = {"error": str(e)[:300], "final_ok": False, "first_ok": False, "first_issues": [],
                           "first_codes": [], "final_xml": "", "first_xml": "", "cost_usd": 0.0,
                           "validator_passes": 0, "generator_calls": 0}
                spent += res["cost_usd"]
                d = out / arm / case
                d.mkdir(parents=True, exist_ok=True)
                (d / "final.xml").write_text(res["final_xml"], encoding="utf-8")
                if res.get("first_xml"):
                    (d / "first.xml").write_text(res["first_xml"], encoding="utf-8")
                runs.append({"case": case, "arm": arm, "kind": it["kind"], "item": it["name"], "repeat": r,
                             "run_id": rid, "env": dict(ARMS[arm]),
                             **{k: v for k, v in res.items() if k not in ("final_xml", "first_xml", "repaired_xml")}})
                print(f"  first try ok={res['first_ok']} codes={sorted({c['code'] for c in res['first_codes']})} "
                      f"passes={res['validator_passes']} final ok={res['final_ok']} ${res['cost_usd']:.3f} "
                      f"(total ${spent:.3f})", flush=True)
                out.mkdir(parents=True, exist_ok=True)   # saved after every run: a stop keeps what was paid for
                (out / "runs.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    return runs


# ── scoring (free) ────────────────────────────────────────────────────────────

def compositions(first_xml: str, plan: dict) -> dict[str, dict]:
    """Arm B's first try, per component: the variant the generator wrote, the default code picks for the bare tag (the
    design hint's composition, else the first that fits) and the composition drawn."""
    set_arm("B")
    written = {}
    for m in _GROUP.finditer(first_xml):
        ref = re.search(r'\sref="([^"]*)"', m.group(2))
        if ref:
            v = re.search(r'\svariant="([^"]*)"', m.group(2))
            written[ref.group(1)] = {"tag": m.group(1), "written": v.group(1) if v else None}
    bare = _GROUP.sub(lambda m: f"<{m.group(1)}{_ATTR.sub('', m.group(2))}>", first_xml)
    try:
        drawn = composed.expand(first_xml, plan)["components"]
        default = composed.expand(bare, plan)["components"]
    except Exception as e:   # an unparsable first try: the written variants only
        return {cid: dict(w, error=str(e)[:120]) for cid, w in written.items()}
    return {cid: {**written.get(cid, {"tag": None, "written": None}),
                  "default": (default.get(cid) or {}).get("composition"), "drawn": (drawn.get(cid) or {}).get("composition")}
            for cid in {*written, *drawn}}


def rescore(label: str, render: bool = True) -> list[dict]:
    out = OUT / label
    by_name = {it["name"]: it for it in items()}
    runs = json.loads((out / "runs.json").read_text(encoding="utf-8"))
    for row in runs:
        it = by_name[row["item"]]
        d = out / row["arm"] / row["case"]
        first = (d / "first.xml").read_text(encoding="utf-8") if (d / "first.xml").exists() else ""
        row["compositions"] = compositions(first, it["plan"]) if row["arm"] == "B" and first else {}
        xml = (d / "final.xml").read_text(encoding="utf-8") if (d / "final.xml").exists() else ""
        if not xml:
            row["score"] = None
            continue
        set_arm(row["arm"])
        dest = d / "slide-0"
        row["score"] = score(row["arm"], dest, compile_slide(deck_font(xml), resolve_theme(it["theme"])["element"], dest),
                             it["plan"], row["case"], render)
        row["score"]["missing"] = missing_words(row["score"].get("final_xml") or xml, it["plan"])
    (out / "results.json").write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    if render:
        from scripts import node_test_sheet as S
        S.build(out / "B", out / "A", out / "sheets")   # B (composition nodes) plays the "nodes" role in key.json
    write_summary(out, runs)
    return runs


def write_summary(out: Path, runs: list[dict]) -> None:
    by = {(r["case"], r["arm"]): r for r in runs}
    lines = ["# Composition nodes, same-plan check (generator only; A = today's route, B = POM_NODES of all six; "
             "both POM_BLOCKS=tiles)", ""]
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        codes = [c["code"] for r in rs for c in r.get("first_codes") or []]
        first_err = sum(1 for r in rs if any(c["severity"] == "error" for c in r.get("first_codes") or []))
        lines.append(f"- **{arm}**: {len(rs)} runs, ${sum(r['cost_usd'] for r in rs):.3f}; first try compiled "
                     f"{sum(r['first_ok'] for r in rs)}/{len(rs)}, NODE_* error on the first try {first_err}, final "
                     f"compiled {sum(r['final_ok'] for r in rs)}/{len(rs)}, repair passes "
                     f"{sum(max(0, r['validator_passes'] - 1) for r in rs)}, errors {sum(1 for r in rs if r.get('error'))}; "
                     + ", ".join(f"{c} {codes.count(c)}" for c in WATCH))
    lines += ["", "## Compositions (B, first try): written by the generator / default for the bare tag / drawn", "",
              "| run | group | tag | written | default | drawn |", "|---|---|---|---|---|---|"]
    for r in runs:
        for cid, c in sorted((r.get("compositions") or {}).items()):
            lines.append(f"| {r['case']} | {cid} | {c.get('tag')} | {c.get('written') or '-'} | {c.get('default')} | "
                         f"{c.get('drawn')} |")
    lines += ["", "## Pairs (final slide)", "",
              "| slide plan | smallest number A / B (px) | card empty A / B | broken A / B | off-plan / missing A / B "
              "| first try A / B | codes B | $ A / B |", "|---|---|---|---|---|---|---|---|"]

    for case in dict.fromkeys(r["case"] for r in runs):
        a, b = by.get((case, "A"), {}), by.get((case, "B"), {})
        sa, sb = a.get("score") or {}, b.get("score") or {}
        f = lambda s: sum((s.get("fill") or {}).values()) if s else "-"
        m = lambda s: len(s.get("off_plan") or []) + len(s.get("missing") or [])
        lines.append(f"| {case} | {TS._min_size(sa)} / {TS._min_size(sb)} | {f(sa)} / {f(sb)} | {sa.get('broken')} / "
                     f"{sb.get('broken')} | {m(sa)} / {m(sb)} | {'ok' if a.get('first_ok') else 'fail'} / "
                     f"{'ok' if b.get('first_ok') else 'fail'} | "
                     f"{' '.join(sorted({c['code'][5:] for c in b.get('first_codes') or []})) or '-'} | "
                     f"{a.get('cost_usd', 0):.3f} / {b.get('cost_usd', 0):.3f} |")
    lines += ["", "Blind sheet: sheets/ (fill marks.csv; key.json: the 'nodes' side is B, the composition nodes)."]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", default="composition-paid")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", help="only the plans holding this node (table, chart, timeline, bullet_list, kpi_row, card_grid)")
    ap.add_argument("--limit", type=int, help="the first N plans (a dry path check)")
    ap.add_argument("--max-cost", type=float, default=3.5, help="stop before a pair could pass this total (USD)")
    ap.add_argument("--estimate", action="store_true", help="free: print the cases and the cost estimate, then stop")
    ap.add_argument("--rescore", action="store_true", help="free: score saved runs again")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--bundle", action="store_true")
    ap.add_argument("--dry", action="store_true", help="free: fake generator, checks the path end to end")
    a = ap.parse_args()
    cases = [it for it in items() if not a.only or a.only in it["kind"].split("+")][:a.limit]
    if not a.rescore:
        n, est, worst = estimate(len(cases), a.repeat)
        print(f"{len(cases)} plans x {a.repeat} repeat x {len(ARMS)} arms = {n} runs; estimate ${est:.2f} "
              f"(all long repairs ${worst:.2f}); stop at --max-cost ${a.max_cost:.2f}")
        for it in cases:
            print(f"  {it['kind']:30} {it['name']}")
        if a.estimate:
            return 0
    if a.dry:
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        run(a.label, a.repeat, cases, a.max_cost, dry=True)
    elif not a.rescore:
        if not os.environ.get("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")   # before set_arm: the arm's switches override any POM_* in .env
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set (.env): the paid check runs on the test PC")
            return 2
        from src.utils.logging_config import add_file_log, setup_logging
        setup_logging()
        shutil.rmtree(OUT / a.label, ignore_errors=True)
        (OUT / a.label).mkdir(parents=True, exist_ok=True)
        add_file_log(OUT / a.label / "run.log")
        run(a.label, a.repeat, cases, a.max_cost)
    rescore(a.label, render=not a.no_render)
    if a.bundle:
        print(f"EMAIL THIS FILE: {TS.bundle(a.label, OUT)}")   # zip layout as the tile same-plan check
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
