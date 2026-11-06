"""Smart-layout research, Part 1 (docs/smart-layout-research-2026-11-06.md). Free, no LLM, reads saved runs only.

    python -m scripts.smart_layout_part1 prompts <slides.json> --out <dir>   # the real generator prompt per slide: is the skeleton in it?
    python -m scripts.smart_layout_part1 predict --src <dir> [<dir> ...]     # how much does the blueprint predict the layout drawn?

predict: every saved slides.json (one per distinct XML, content / data slides with 2+ body components). For each slide,
today's select_blueprint(plan) against the XML's first-level arrangement, and the plan's layout_hint against the same.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.variety import _parse, signature  # noqa: E402
from src.agents.blueprint_selector import select_blueprint  # noqa: E402

SIDE_WORDS = re.compile(r"\b(beside|side[- ]by[- ]side|alongside|left|right|column|columns|next to|share the band|sidebar|rail)\b", re.I)
CONTENT = ("VStack", "HStack", "Table", "Chart", "Ul", "Timeline", "ProcessArrow", "Flow", "Pyramid", "Tree", "Matrix",
           "KpiRow", "CardGrid", "KpiGrid", "Text", "Layer")


def prompts(slides_json: Path, out: Path) -> dict:
    from src.agents.context_builder import build_contract
    from src.agents.generator import _render_prompts
    from src.agents.style_resolver import resolve_theme
    out.mkdir(parents=True, exist_ok=True)
    theme = resolve_theme("corporate-slate")
    rows = []
    for s in json.loads(slides_json.read_text(encoding="utf-8")):
        plan = s["slide_plan"]
        contract = build_contract(plan, theme)
        system, user = _render_prompts({"contract": contract, "slide_plans": [plan], "current_slide_index": 0, "raw_request": ""})
        m = re.search(r"## BLUEPRINT.*?(?=\n## |\Z)", system, flags=re.S)
        block = m.group(0) if m else ""
        (out / f"slide-{s['slide_index']}-blueprint-block.txt").write_text(block, encoding="utf-8")
        rows.append({"slide": s["slide_index"], "kinds": [c.get("kind") for c in plan.get("components", [])],
                     "blueprint": contract["blueprint_name"], "in_system_prompt": bool(block), "chars": len(block),
                     "reference_xml_empty": "```xml\n\n```" in block, "in_user_prompt": "BLUEPRINT" in user,
                     "system_chars": len(system)})
    (out / "prompts.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return {"rows": rows}


def bp_shape(bp: dict) -> dict:
    st = bp.get("structure", {})
    bands = [b for b in st.get("bands", []) if not re.search("header|title|footer|source|caption", b.get("role", ""))]
    split = st.get("root") == "HStack" or any(b.get("split") or len(b.get("children") or []) >= 2 for b in bands)
    required = [b for b in bands if not b.get("optional")]
    return {"bands": len(bands), "required": len(required), "split": bool(split),
            "padding": str(st.get("padding", 36)), "gap": str(st.get("gap", 14))}


def body(xml: str):
    root = _parse(xml)
    if root is None:
        return None
    out = []
    for k in list(root):
        if k.tag in ("Shape", "Icon", "Line", "Arrow", "Svg"):
            continue
        txt = "".join(k.itertext())
        is_stack = k.tag in ("VStack", "HStack") and not k.get("ref")
        only_text = all(c.tag in ("Text", "Span", "B", "I", "VStack", "HStack", "Shape", "Icon") for c in k.iter() if c is not k)
        if not out and (k.tag == "Text" or (is_stack and len(txt) < 260 and only_text and not k.get("grow"))):
            continue   # the header
        if k.tag == "Text" and not k.get("grow") and len(txt) < 40:
            continue
        out.append(k)
    return root, out


def drawn_shape(xml: str) -> dict | None:
    b = body(xml)
    if not b:
        return None
    root, kids = b

    def shape(e) -> tuple:   # a row of like children (hand-drawn KPI tiles, cards) is one component, not a split
        return tuple(sorted(Counter(c.tag for c in e.iter() if c.tag not in ("Span", "B", "I")).items()))

    def split_stack(e) -> bool:
        kids = [c for c in e if c.tag in CONTENT]
        return e.tag == "HStack" and len(kids) >= 2 and len({shape(c) for c in kids}) > 1
    return {"bands": len(kids), "split": split_stack(root) or any(split_stack(k) for k in kids),
            "padding": root.get("padding"), "gap": root.get("gap")}


def entropy(xs: list) -> float:
    n = len(xs)
    return -sum(v / n * math.log2(v / n) for v in Counter(xs).values()) if n else 0.0


def cond_entropy(pairs: list[tuple]) -> float:
    groups = defaultdict(list)
    for g, x in pairs:
        groups[g].append(x)
    n = len(pairs)
    return sum(len(v) / n * entropy(v) for v in groups.values())


def kappa(pairs: list[tuple[bool, bool]]) -> float:
    n = len(pairs)
    if not n:
        return 0.0
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 0.0


def collect(srcs: list[Path]) -> list[dict]:
    seen, rows = set(), []
    for src in srcs:
        for sj in src.rglob("slides.json"):
            try:
                data = json.loads(sj.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for s in data:
                if not isinstance(s, dict):
                    continue
                xml, plan = s.get("xml"), s.get("slide_plan")
                if not xml or not isinstance(plan, dict):
                    continue
                h = hashlib.sha1(xml.encode("utf-8", "ignore")).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                comps = [c for c in plan.get("components", []) if c.get("kind") not in ("title", "caption")]
                if plan.get("slide_type") not in ("content", "data"):
                    continue
                rows.append({"xml": xml, "plan": plan, "n": len(comps), "kinds": tuple(sorted(c.get("kind", "") for c in comps))})
    return rows


def copy_test(with_bp: list[dict], no_bp: list[dict]) -> dict:
    """Do the root padding and gap follow the skeleton's numbers? Rows of root padding/gap per skeleton value."""
    out = {}
    for field in ("padding", "gap"):
        table = defaultdict(Counter)
        for r in with_bp:
            table[r["bp_shape"][field]][r["drawn"][field]] += 1
        table["(no blueprint)"] = Counter(r["drawn"][field] for r in no_bp)
        out[field] = {k: {"n": sum(v.values()), "same_as_skeleton": round(v.get(k, 0) / max(1, sum(v.values())), 3),
                          "top": v.most_common(4)} for k, v in table.items()}
    return out


def predict(srcs: list[Path], out: Path) -> dict:
    rows = collect(srcs)
    res = []
    for r in rows:
        if r["n"] < 2:
            continue
        d = drawn_shape(r["xml"])
        if d is None:
            continue
        bp = select_blueprint(r["plan"])
        res.append({"kinds": r["kinds"], "bp": (bp or {}).get("blueprint_name"), "bp_shape": bp_shape(bp) if bp else None,
                    "drawn": d, "sig": signature(r["xml"], fine=False), "hint": r["plan"].get("layout_hint", "")})
    with_bp = [r for r in res if r["bp"]]
    split = [(r["bp_shape"]["split"], r["drawn"]["split"]) for r in with_bp]
    hint_pairs = [(bool(SIDE_WORDS.search(r["hint"])), r["drawn"]["split"]) for r in res if r["hint"]]
    sigs = [r["sig"] for r in with_bp]
    # natural experiment: the same kinds, more than one blueprint chosen (slide type / density differ)
    by_kinds = defaultdict(set)
    for r in with_bp:
        by_kinds[r["kinds"]].add(r["bp"])
    multi = [r for r in with_bp if len(by_kinds[r["kinds"]]) > 1]
    per_bp = {}
    for name in sorted({r["bp"] for r in with_bp}):
        g = [r for r in with_bp if r["bp"] == name]
        per_bp[name] = {"n": len(g), "skeleton_bands": g[0]["bp_shape"]["bands"], "skeleton_split": g[0]["bp_shape"]["split"],
                        "drawn_same_band_count": round(sum(x["drawn"]["bands"] == g[0]["bp_shape"]["bands"] for x in g) / len(g), 2),
                        "drawn_split": round(sum(x["drawn"]["split"] for x in g) / len(g), 2),
                        "distinct_layouts": len({x["sig"] for x in g})}
    summary = {
        "slides_total_seen": len(rows),
        "slides_scored_2plus_components": len(res), "with_blueprint": len(with_bp), "no_blueprint": len(res) - len(with_bp),
        "band_count_within_skeleton_range": round(sum(r["bp_shape"]["required"] <= r["drawn"]["bands"] <= r["bp_shape"]["bands"] for r in with_bp) / max(1, len(with_bp)), 3),
        "copy_test": copy_test(with_bp, [r for r in res if not r["bp"]]),
        "split_agree_blueprint": round(sum(a == b for a, b in split) / max(1, len(split)), 3), "split_kappa_blueprint": round(kappa(split), 3),
        "split_agree_layout_hint": round(sum(a == b for a, b in hint_pairs) / max(1, len(hint_pairs)), 3),
        "split_kappa_layout_hint": round(kappa(hint_pairs), 3), "hint_slides": len(hint_pairs),
        "drawn_split_rate": round(sum(r["drawn"]["split"] for r in res) / max(1, len(res)), 3),
        "distinct_layouts": len(set(sigs)), "H_layout_bits": round(entropy(sigs), 2),
        "H_layout_given_blueprint": round(cond_entropy([(r["bp"], r["sig"]) for r in with_bp]), 2),
        "H_layout_given_kinds": round(cond_entropy([(r["kinds"], r["sig"]) for r in with_bp]), 2),
        "H_layout_given_kinds_and_blueprint": round(cond_entropy([((r["kinds"], r["bp"]), r["sig"]) for r in with_bp]), 2),
        "same_kinds_two_blueprints": {
            "slides": len(multi), "kind_sets": sum(1 for v in by_kinds.values() if len(v) > 1),
            "H_layout_given_kinds": round(cond_entropy([(r["kinds"], r["sig"]) for r in multi]), 2),
            "H_layout_given_kinds_and_blueprint": round(cond_entropy([((r["kinds"], r["bp"]), r["sig"]) for r in multi]), 2),
            "split_kappa": round(kappa([(r["bp_shape"]["split"], r["drawn"]["split"]) for r in multi]), 3)},
        "per_blueprint": per_bp,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "blueprint-predicts.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["prompts", "predict"])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--src", nargs="*", default=[])
    ap.add_argument("--out", default="docs/eval/smart-layout")
    a = ap.parse_args()
    if a.what == "prompts":
        print(json.dumps(prompts(Path(a.paths[0]), Path(a.out)), indent=1))
    else:
        print(json.dumps(predict([Path(p) for p in a.src], Path(a.out)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
