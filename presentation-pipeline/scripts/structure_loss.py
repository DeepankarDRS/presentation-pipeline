"""Where does the brief's structure get lost on the way to a slide plan? (free, no LLM)

    python -m scripts.structure_loss                      # summary table
    python -m scripts.structure_loss --examples 5         # + examples per class
    python -m scripts.structure_loss --json out.json      # every classified list
    python -m scripts.structure_loss --replay             # the same, after the 2026-10-15 code checks

Reads every saved `output/**/slides.json` (one entry per distinct slide plan) and the plan-only
`runs.json` files that also kept the outline (`output/card-plans`, `output/kpi-plans`). For every
`bullet_list` it classifies the items by data form (series / record / metric / categorized /
label-detail / note / prose), finds each item's source in the case brief (`tests/cases/*.yaml`),
classifies that source the same way, and, where the outline was saved, the key_message that
carried the item. Method and results: docs/eval/structure-loss/README.md.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import glob
import json
import re
import subprocess
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import yaml

from src.agents import plan_checks
from src.agents.written_lines import (NOTES_LABEL, content_lines, drop_visual_directions, from_brief,
                                      settle_direction_lines, visual_directions)

ROOT = Path(__file__).resolve().parents[1]
_NUM = re.compile(r"[₹$€£]?\d[\d,]*(?:\.\d+)?\s*(?:%|x|×|L|K|M|Cr|B|pts?|h|months?)?(?![A-Za-z])")
_LABEL = re.compile(r"^\s*([^:]{1,60}?)\s*:\s+(.+)$")
_NOTE = re.compile(r"^\s*(note|notes|source|key formulas?|caveat|formula)\b", re.I)
SHAPES_NUMERIC = {"series", "record", "metric"}
SHAPES_STRUCTURED = SHAPES_NUMERIC | {"categorized", "label_detail"}


# ── Item shape ──────────────────────────────────────────────────────────────

def nums(text: str) -> list[str]:
    return [n for n in _NUM.findall(text) if re.search(r"\d", n)]


def item_shape(text: str) -> str:
    """The data form of one bullet item (or one brief line):
    series / record / metric (numbers per label), categorized ("Label: a, b, c"),
    label_detail ("Label: a line"), note (note / source / formula), claim (a sentence citing
    figures), prose (a sentence)."""
    t = text.strip().rstrip(".")
    if _NOTE.match(t) or re.search(r"\w\s*=\s*\w+\s*[÷/×*]", t):
        return "note"
    if t.count("|") >= 2:  # a table row as the brief writes one
        return "record" if len(nums(t)) >= 2 else "label_detail"
    m = _LABEL.match(t)
    label, rest = (m.group(1), m.group(2)) if m and len(m.group(1).split()) <= 6 else ("", t)
    parts = [p for p in re.split(r"\s*[,;·]\s*|\s+vs\.?\s+", rest) if p.strip()]
    num_parts = [p for p in parts if nums(p)]
    n = len(nums(rest))
    short = lambda ps, k: all(len(p.split()) <= k for p in ps)
    if len(num_parts) >= 3 and len(num_parts) >= 0.6 * len(parts) and short(num_parts, 7):
        return "series"
    if label and len(num_parts) >= 2 and short(num_parts, 7):
        return "record"
    if label and 1 <= n <= 2 and len(rest.split()) <= 6:
        return "metric"
    if not label and n >= 1 and len(t.split()) <= 6 and len(re.findall(r"[A-Za-z]{2,}", t)) <= 4:
        return "metric"
    if label and len(parts) >= 2 and short(parts, 5) and n <= 1:
        return "categorized"
    if label:
        return "label_detail"
    if not n and len(t.split()) <= 5:
        return "named"
    return "claim" if n else "prose"


def list_shape(items: list[str]) -> str:
    """numeric / label_detail / named_items (short names) / note / claim (sentences citing
    figures) / takeaway."""
    shapes = Counter(item_shape(i) for i in items)
    k = len(items) or 1
    num = sum(shapes[s] for s in SHAPES_NUMERIC)
    lab = shapes["categorized"] + shapes["label_detail"]
    if num / k >= 0.5:
        return "numeric"
    if shapes["note"] / k >= 0.5:
        return "note"
    if (num + lab) / k >= 0.5:
        return "label_detail"
    if shapes["named"] / k >= 0.5:
        return "named_items"
    if shapes["claim"] / k >= 0.5:
        return "claim"
    return "takeaway"


def dominant(items: list[str]) -> str:
    return Counter(item_shape(i) for i in items).most_common(1)[0][0] if items else "prose"


# ── Briefs ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def cases() -> dict[str, dict]:
    out = {}
    for f in (ROOT / "tests" / "cases").glob("*.yaml"):
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict):
            out[d.get("name") or f.stem] = d
    return out


def case_of(path: str) -> str | None:
    hits = [c for c in cases() if c in path.replace("\\", "/")]
    return max(hits, key=len) if hits else None


@lru_cache(maxsize=None)
def brief_chunks(case: str, supplied: bool = True) -> list[str]:
    """The brief as lines: request split on newlines, list markers and sentence ends; supplied
    content as one chunk per list entry / table row."""
    c = cases()[case]
    req = c.get("request") or ""
    chunks: list[str] = []
    for line in re.split(r"\n|(?<=[.!?])\s{1,3}(?=[A-Z\[])|\s{2,}|\s[-*•]\s(?=\S)", req):
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if len(line) > 3:
            chunks.append(line)
    sc = (c.get("supplied_content") or {}) if supplied else {}

    def walk(v, key=""):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            if v and all(not isinstance(x, (list, dict)) for x in v) and key not in ("bullets", "key_points"):
                chunks.append(f"{key}: " + ", ".join(map(str, v)))
            else:
                for x in v:
                    walk(x, key)
        elif isinstance(v, str) and len(v) > 3:
            chunks.append(v)
    walk(sc)
    return chunks


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}|\d[\d.,]*", s.lower())}


def source_of(item: str, chunks: list[str]) -> tuple[str, float]:
    """The brief chunk an item came from (token overlap, numbers count double)."""
    it = _tokens(item)
    if not it:
        return "", 0.0
    best, score = "", 0.0
    for ch in chunks:
        ct = _tokens(ch)
        common = it & ct
        s = (len(common) + sum(1 for w in common if w[0].isdigit())) / (len(it) + 1)
        if s > score:
            best, score = ch, s
    return best, score


# ── Run dates ───────────────────────────────────────────────────────────────

# Saved folders without a manifest commit or a date in the name (dates from the llm_test zips).
_FOLDER_DATES = {"plans/test-1": "2026-09-27", "old_zips/gj-h1-regen-5a9e2d": "2026-09-24",
                 "r2/inputs/gj-h1-regen": "2026-09-24", "r2/inputs/xtsy-23sep": "2026-09-23",
                 "r2/inputs/1b306e1de67f": "2026-09-28", "eval/composetest": "2026-10-05"}

@lru_cache(maxsize=None)
def commit_date(sha: str) -> str:
    try:
        out = subprocess.run(["git", "show", "-s", "--format=%cs", sha], cwd=ROOT, capture_output=True,
                             text=True, timeout=10).stdout.strip()
        return out
    except Exception:
        return ""


def run_date(path: Path) -> str:
    run_dir = path.parent
    man = run_dir / "run-manifest.json"
    if man.exists():
        try:
            sha = json.loads(man.read_text(encoding="utf-8")).get("git_commit") or ""
            if sha and (d := commit_date(sha)):
                return d
        except Exception:
            pass
    s = str(path).replace("\\", "/")
    for key, date in _FOLDER_DATES.items():
        if key in s:
            return date
    if m := re.search(r"(20\d\d)(\d\d)(\d\d)", s):
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if m := re.search(r"\b(17\d{8})\b", s):
        return dt.datetime.fromtimestamp(int(m.group(1)), dt.timezone.utc).date().isoformat()
    return ""


# ── Corpus ──────────────────────────────────────────────────────────────────

def bullet_lists(plan: dict) -> list[list[str]]:
    out = []
    for c in plan.get("components") or []:
        if c.get("kind") != "bullet_list":
            continue
        cd = c.get("content_data") or c.get("content_data_json") or {}
        if isinstance(cd, str):
            try:
                cd = json.loads(cd)
            except Exception:
                cd = {}
        items = cd.get("bullets") or cd.get("items") or []
        items = [i if isinstance(i, str) else json.dumps(i, ensure_ascii=False) for i in items]
        if items:
            out.append(items)
    return out


def load_slides() -> dict[str, dict]:
    """Distinct slide plans (by components) → first path, date, case."""
    seen: dict[str, dict] = {}
    for f in sorted(glob.glob(str(ROOT / "output" / "**" / "slides.json"), recursive=True)):
        p = Path(f)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, list):
            continue
        date = None
        for s in d:
            plan = s.get("slide_plan") or {}
            if not plan.get("components"):
                continue
            key = json.dumps(plan.get("components"), sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            if date is None:
                date = run_date(p)
            seen[key] = {"path": str(p.relative_to(ROOT)), "date": date, "case": case_of(f), "plan": plan,
                         "outline": None}
    # the combined tile check's fresh plans (2026-10-15; no outline saved)
    for f in sorted(glob.glob(str(ROOT / "output" / "tile-combined" / "*" / "plans.json"))):
        p = Path(f)
        for r in json.loads(p.read_text(encoding="utf-8")).get("runs") or []:
            for plan in r.get("slide_plans") or []:
                key = json.dumps(plan.get("components"), sort_keys=True, ensure_ascii=False)
                if plan.get("components") and key not in seen:
                    seen[key] = {"path": f"{p.relative_to(ROOT)}#{r.get('run_id')}", "date": run_date(Path(r.get("run_id", ""))),
                                 "case": r.get("case"), "plan": plan, "outline": None}
    return seen


def load_outline_runs() -> list[dict]:
    """Plan-only runs that kept the outline: per slide, the outline entry and the plan."""
    out = []
    for f in glob.glob(str(ROOT / "output" / "*-plans" / "**" / "runs.json"), recursive=True):
        p = Path(f)
        try:
            runs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in runs:
            outline = {s.get("slide_index"): s for s in (r.get("outline") or {}).get("slides") or []}
            date = run_date(Path(r.get("run_id", "")))
            for plan in r.get("slide_plans") or []:
                out.append({"path": f"{p.relative_to(ROOT)}#{r.get('run_id')}", "date": date, "case": r.get("case"),
                            "plan": plan, "outline": outline.get(plan.get("slide_index"))})
    return out


def message_for(item: str, messages: list[str]) -> tuple[str, float]:
    return source_of(item, messages)


def classify(entry: dict, items: list[str]) -> dict:
    """One bullet list → its shape, its brief source shape, the class (a/b/c) and evidence."""
    shape = list_shape(items)
    rec = {"path": entry["path"], "date": entry["date"], "case": entry["case"],
           "slide": entry["plan"].get("slide_index"), "title": entry["plan"].get("slide_title", ""),
           "shape": shape, "item_shapes": [item_shape(i) for i in items], "items": items,
           "other_kinds": sorted({c.get("kind") for c in entry["plan"].get("components") or []} - {"title", "bullet_list"})}
    if entry["case"] and entry["case"] in cases():
        srcs = [source_of(i, brief_chunks(entry["case"])) for i in items]
        rec["sources"] = [s for s, _ in srcs]
        rec["source_match"] = round(sum(sc for _, sc in srcs) / len(srcs), 2)
        rec["source_shape"] = list_shape([s for s, sc in srcs if s]) if any(s for s, _ in srcs) else "?"
    else:
        rec["sources"], rec["source_match"], rec["source_shape"] = [], 0.0, "?"
    if entry["outline"]:
        msgs = [m for m in entry["outline"].get("key_messages") or [] if isinstance(m, str)]
        hits = [message_for(i, msgs) for i in items]
        rec["messages"] = [m for m, _ in hits]
        uniq = list(dict.fromkeys(m for m, _ in hits if m))
        rec["message_shape"] = list_shape(uniq) if uniq else "?"
        rec["message_item_shapes"] = [item_shape(m) for m in uniq]
        rec["visual_emphasis"] = entry["outline"].get("visual_emphasis", "")
    # class: where the brief's structure went
    #   b  = the component planner had it (structured items, or a structured key_message) and drew a list
    #   a  = the brief had it, the outline's key_message is a sentence (a? = no outline saved: outline
    #        or planner flattened it)
    #   c  = the brief itself is sentences
    #   ok = a list of plain takeaways from plain sentences (no structure to lose)
    structured_items = shape in ("numeric", "label_detail", "named_items")
    src_structured = rec["source_shape"] in ("numeric", "label_detail") and rec["source_match"] >= 0.5
    if "message_shape" in rec:
        rec["cls_basis"] = "outline"
        msg_structured = rec["message_shape"] in ("numeric", "label_detail")
        if structured_items or msg_structured:
            rec["cls"] = "b"
        elif src_structured:
            rec["cls"] = "a"
        else:
            rec["cls"] = "c" if shape in ("claim", "note") else "ok"
    else:
        # Job 1 copies key_messages verbatim, so items that still carry "Label: value" form reached
        # the component planner structured.
        rec["cls_basis"] = "items+brief"
        if structured_items:
            rec["cls"] = "b"
        elif src_structured:
            rec["cls"] = "a?"
        else:
            rec["cls"] = "c" if shape in ("claim", "note") else "ok"
    rec["brief_structured"] = src_structured
    # the planner failed twice and code drew the outline's lines as one list (fallback_plan)
    if any(c.get("component_id") == "fallback_points" and (c.get("content_data") or {}).get("bullets") == items
           for c in entry["plan"].get("components") or []):
        rec["cls"] = "fallback"
    return rec


# ── Replay of the 2026-10-15 code checks (README "Changes") ─────────────────

_OLD_PIECES = re.compile(r"\n|(?:^|\s)[*•·]\s|;")   # dropped_card_lines' pieces before 2026-10-15


def _cd(c: dict) -> dict:
    cd = c.get("content_data") or c.get("content_data_json") or {}
    if isinstance(cd, str):
        try:
            cd = json.loads(cd)
        except Exception:
            cd = {}
    return cd if isinstance(cd, dict) else {}


def replay(entry: dict) -> tuple[dict, dict]:
    """A saved plan as the new code checks leave it, and what changed. With the outline: presenter notes leave the
    key_messages (a text component carrying only them goes too: the planner no longer sees them), "Show:" /
    "Visual Suggestion:" become directions (`drop_visual_directions`). Every plan: K4 (`cards_to_list`)."""
    plan = copy.deepcopy(entry["plan"])
    for c in plan.get("components") or []:
        c["content_data"] = _cd(c)
    out = {"notes_dropped": 0, "notes_components": [], "direction_components": [], "k4": []}
    if entry["outline"]:
        slide = copy.deepcopy(entry["outline"])
        notes = [m for m in slide.get("key_messages") or [] if isinstance(m, str) and NOTES_LABEL.match(m)]
        out["notes_dropped"] = len(settle_direction_lines(slide))
        if notes:
            keep = []
            for c in plan.get("components") or []:
                text = " ".join(_flat(v) for v in c["content_data"].values())
                if c.get("kind") in ("narrative", "caption", "bullet_list") and text.strip() \
                        and from_brief(text, " ".join(notes)) and not from_brief(text, content_lines(slide, [])):
                    out["notes_components"].append(f"{c.get('kind')} {c.get('component_id', '')}")
                    continue
                keep.append(c)
            plan["components"] = keep
        dirs = visual_directions(slide)
        before = [c.get("component_id") for c in plan.get("components") or []]
        drop_visual_directions(plan, dirs, content_lines(slide, dirs))
        out["direction_components"] = [b for b in before if b not in {c.get("component_id") for c in plan["components"]}]
    out["k4"] = plan_checks.cards_to_list(plan)
    return plan, out


def card_line_reasks(entry: dict) -> tuple[int, int]:
    """CARD_LINES_DROPPED on the saved plan with the brief text read before (messages joined by spaces, no sentence
    split) and after 2026-10-15. Needs the outline."""
    slide = entry["outline"]
    msgs = [m for m in slide.get("key_messages") or [] if isinstance(m, str)]
    tail = [slide.get("slide_title", ""), slide.get("subtitle", ""), slide.get("visual_emphasis", "")]
    grids = [{**c, "content_data": _cd(c)} for c in entry["plan"].get("components") or [] if c.get("kind") == "card_grid"]
    new = sum(bool(plan_checks.dropped_card_lines(g, "\n".join(msgs + tail))) for g in grids)
    saved, plan_checks._BRIEF_PIECES = plan_checks._BRIEF_PIECES, _OLD_PIECES
    try:
        old = sum(bool(plan_checks.dropped_card_lines(g, " ".join(msgs + tail))) for g in grids)
    finally:
        plan_checks._BRIEF_PIECES = saved
    return old, new


# ── Stage by stage on the runs that kept the outline ───────────────────────

def _flat(v) -> str:
    return json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v


def stages(outline_runs: list[dict]) -> dict:
    """brief line → outline key_message (kept structured / flattened / missing) and
    outline key_message → the component kind that carries it."""
    by_run: dict[str, list[dict]] = defaultdict(list)
    for e in outline_runs:
        by_run[e["path"]].append(e)
    brief_to_outline = Counter()
    brief_examples = defaultdict(list)
    msg_to_kind = Counter()
    msg_examples = defaultdict(list)
    for run, entries in by_run.items():
        case = entries[0]["case"]
        if case not in cases():
            continue
        msgs = [(e, m) for e in entries if e["outline"] for m in e["outline"].get("key_messages") or []
                if isinstance(m, str)]
        texts = [m for _, m in msgs]
        for ch in brief_chunks(case, supplied=False):
            sh = item_shape(ch)
            if sh not in ("series", "record", "metric", "categorized") or len(_tokens(ch)) < 4:
                continue
            best, sc = source_of(ch, texts)
            if sc < 0.5:
                brief_to_outline[(sh, "missing")] += 1
                brief_examples[(sh, "missing")].append({"run": run, "brief": ch, "message": best, "score": round(sc, 2)})
                continue
            got = item_shape(best)
            kept = "kept" if got in SHAPES_STRUCTURED else ("as note" if got == "note" else "flattened")
            brief_to_outline[(sh, kept)] += 1
            brief_examples[(sh, kept)].append({"run": run, "brief": ch, "message": best})
        for e, m in msgs:
            sh = item_shape(m)
            comps = [c for c in e["plan"].get("components") or [] if c.get("kind") != "title"]
            if not comps:
                continue
            best_kind, best_sc = "", 0.0
            for c in comps:
                _, scc = source_of(m, [_flat(c.get("content_data") or c.get("content_data_json") or {})])
                if scc > best_sc:
                    best_kind, best_sc = c.get("kind"), scc
            kind = best_kind if best_sc >= 0.5 else "(not carried)"
            msg_to_kind[(sh, kind)] += 1
            msg_examples[(sh, kind)].append({"run": run, "slide": e["plan"].get("slide_index"), "message": m})
    return {"brief_to_outline": brief_to_outline, "brief_examples": brief_examples,
            "msg_to_kind": msg_to_kind, "msg_examples": msg_examples}


def _print_replay(slides: dict[str, dict], outline_runs: list[dict]) -> None:
    """Replace every entry's plan by its replayed plan (in place) and print what the code checks changed."""
    k4, notes_msgs, notes_comps, dir_comps, reask = [], 0, [], [], [0, 0]
    for e in [*slides.values(), *outline_runs]:
        e["plan"], ch = replay(e)
        k4 += [f"{e['date']} {e['case']} slide {e['plan'].get('slide_index', 0) + 1}: {n}  ({e['path']})" for n in ch["k4"]]
        notes_msgs += ch["notes_dropped"]
        notes_comps += [f"{e['case']} slide {e['plan'].get('slide_index', 0) + 1}: {c}" for c in ch["notes_components"]]
        dir_comps += [f"{e['case']} slide {e['plan'].get('slide_index', 0) + 1}: {c}" for c in ch["direction_components"]]
        if e["outline"]:
            old, new = card_line_reasks({**e, "plan": e["plan"]})
            reask[0] += old
            reask[1] += new
    print(f"## Replay of the 2026-10-15 code checks")
    print(f"K4 (cards -> list): {len(k4)} plan(s)")
    for line in k4:
        print("  " + line)
    print(f"presenter-note key_messages dropped: {notes_msgs}; text components that carried only them: {len(notes_comps)}")
    for line in notes_comps:
        print("  " + line)
    print(f"text components dropped as a direction (Show: / Visual Suggestion:): {len(dir_comps)}")
    for line in dir_comps:
        print("  " + line)
    print(f"CARD_LINES_DROPPED re-asks on the outline runs' card grids: before {reask[0]}, after {reask[1]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", type=int, default=0)
    ap.add_argument("--json")
    ap.add_argument("--replay", action="store_true", help="classify the plans as the 2026-10-15 code checks leave them")
    args = ap.parse_args()

    slides = load_slides()
    outline_runs = load_outline_runs()
    if args.replay:
        _print_replay(slides, outline_runs)
    recs = []
    for e in list(slides.values()):
        for items in bullet_lists(e["plan"]):
            recs.append({**classify(e, items), "corpus": "slides"})
    for e in outline_runs:
        for items in bullet_lists(e["plan"]):
            recs.append({**classify(e, items), "corpus": "outline"})

    def table(rs, title):
        print(f"\n## {title}: {len(rs)} bullet lists")
        c = Counter((r["shape"], r["cls"]) for r in rs)
        shapes = ["numeric", "label_detail", "named_items", "claim", "note", "takeaway"]
        classes = sorted({r["cls"] for r in rs})
        print("shape        " + "".join(f"{k:>9}" for k in classes) + "  total")
        for s in shapes:
            print(f"{s:<13}" + "".join(f"{c[(s, k)]:>9}" for k in classes) + f"  {sum(c[(s, k)] for k in classes):>5}")

    t1 = [r for r in recs if r["corpus"] == "slides" and "test-1" in r["path"].replace("\\", "/")]
    sl = [r for r in recs if r["corpus"] == "slides" and r not in t1]
    print(f"distinct slide plans: {len(slides)}; with bullet_list: "
          f"{len({(r['path'], r['slide']) for r in sl})}; bullet lists: {len(sl)}")
    table(sl, "All saved slides")
    table([r for r in sl if r["date"] >= "2026-10-08"], "Runs dated 2026-10-08 onward")
    table([r for r in sl if r["date"] and r["date"] < "2026-10-08"], "Runs before 2026-10-08")
    table(t1, "Test 1 new planning path (storyline + slide designer, 2026-09-27), not in the tables above")
    ol = [r for r in recs if r["corpus"] == "outline"]
    table(ol, "Plan-only runs with the outline saved")
    print("\nby date:", sorted(Counter(r["date"][:7] + ("b" if r["date"][8:] >= "08" else "a") for r in sl if r["date"]).items()))
    print("dominant item shape of numeric/label lists:",
          Counter(dominant(r["items"]) for r in sl if r["shape"] in ("numeric", "label_detail")))
    print("outline: message shape for structured lists:",
          Counter(r.get("message_shape") for r in ol if r["shape"] in ("numeric", "label_detail")))

    st = stages(outline_runs)
    print("\n## brief line (structured) -> outline key_message, runs with the outline saved")
    for (sh, k), n in sorted(st["brief_to_outline"].items()):
        print(f"  {sh:<12} {k:<10} {n}")
    print("\n## outline key_message shape -> component kind carrying it")
    kinds = defaultdict(Counter)
    for (sh, k), n in st["msg_to_kind"].items():
        kinds[sh][k] += n
    for sh, c in sorted(kinds.items()):
        print(f"  {sh:<12} {sum(c.values()):>4}  " + ", ".join(f"{k} {n}" for k, n in c.most_common()))
    if args.json:
        Path(args.json).with_suffix(".stages.json").write_text(json.dumps(
            {"brief_examples": {f"{a}|{b}": v for (a, b), v in st["brief_examples"].items()},
             "msg_examples": {f"{a}|{b}": v for (a, b), v in st["msg_examples"].items()}},
            ensure_ascii=False, indent=1), encoding="utf-8")

    if args.examples:
        for cls in sorted({r["cls"] for r in recs}):
            print(f"\n### class {cls}")
            for r in [r for r in recs if r["cls"] == cls and r["shape"] != "takeaway"][: args.examples]:
                print(json.dumps({k: r.get(k) for k in ("path", "date", "slide", "shape", "items", "sources",
                                                        "messages", "visual_emphasis")}, ensure_ascii=False)[:1200])
    if args.json:
        Path(args.json).write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
