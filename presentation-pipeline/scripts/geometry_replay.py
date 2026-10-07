"""Replay saved slides through today's compiler and the component-level geometry check. LLM-free.

    python -m scripts.geometry_replay                      # output/step0 + output/colour-roles
    python -m scripts.geometry_replay --roots output/step0 --out output/geometry_replay

For each saved generator XML (slides/<case>/slide-N/input.xml) it compiles again (fit-grow,
POM, geometry.json), runs src/compiler/geometry_audit.py on the result and also keeps POM's
own NODE_OVERLAP / NODE_OUT_OF_BOUNDS warnings. Writes <out>/results.json and <out>/summary.md
with counts per code and every finding next to the slide's saved render, for a precision check
by eye (slide-quality item 2, step 1, 2026-10-07).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.compiler.geometry_audit import audit_run_folder  # noqa: E402

_POM_PX = re.compile(r"overlap by ([\d.]+)x([\d.]+)px")


def _pom_codes(result: dict) -> list[dict]:
    out = []
    for w in result.get("warnings") or []:
        code = w.get("code", "")
        if code == "NODE_OVERLAP":
            m = _POM_PX.search(w.get("message", ""))
            if m and min(float(m.group(1)), float(m.group(2))) <= 2:
                continue  # rounding, not a defect
        if code in ("NODE_OVERLAP", "NODE_OUT_OF_BOUNDS", "AUTOFIT_OVERFLOW", "WORD_TOO_WIDE"):
            out.append({"code": code, "severity": "pom", "message": w.get("message", "")})
    return out


def _render_for(xml: Path) -> str:
    # <bundle>/slides/<case>/slide-N/input.xml -> <bundle>/renders/<case>/slide-N.png
    bundle, case, slide = xml.parents[3], xml.parents[1].name, xml.parent.name
    png = bundle / "renders" / case / f"{slide}.png"
    return str(png.resolve().relative_to(ROOT)) if png.exists() else ""


def run(roots: list[Path], out: Path) -> list[dict]:
    rows = []
    for xml in sorted(p for r in roots for p in r.resolve().glob("**/slides/*/slide-*/input.xml")):
        case, slide = xml.parents[1].name, xml.parent.name
        bundle = xml.parents[3].name
        dest = out / "slides" / bundle / case / slide
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["node", str(ROOT / "src" / "node" / "compile-pom.js"), str(xml), str(dest)],
                       capture_output=True, timeout=300)
        result = json.loads((dest / "compile-result.json").read_text(encoding="utf-8"))
        issues = audit_run_folder(dest) if result.get("status") == "success" else []
        rows.append({"bundle": bundle, "case": case, "slide": slide, "compiled": result.get("status") == "success",
                     "render": _render_for(xml), "issues": issues + _pom_codes(result)})
        print(f"{case}/{slide}: {Counter(i['code'] for i in rows[-1]['issues']) or 'clean'}")
    return rows


def reaudit(out: Path) -> list[dict]:
    rows = json.loads((out / "results.json").read_text(encoding="utf-8"))
    for r in rows:
        pom = [i for i in r["issues"] if i["severity"] == "pom"]
        r["issues"] = audit_run_folder(out / "slides" / r["bundle"] / r["case"] / r["slide"]) + pom
    return rows


def write(rows: list[dict], out: Path) -> None:
    (out / "results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    codes = Counter(i["code"] for r in rows for i in r["issues"])
    slides = Counter(c for r in rows for c in {i["code"] for i in r["issues"]})
    lines = [f"# Geometry replay ({len(rows)} slides, {sum(r['compiled'] for r in rows)} compiled)", "",
             "| code | findings | slides |", "|---|---|---|"]
    lines += [f"| {c} | {n} | {slides[c]} |" for c, n in codes.most_common()]
    lines += ["", "## Findings by slide", ""]
    for r in rows:
        if not r["issues"]:
            continue
        lines.append(f"### {r['case']} / {r['slide']}" + (f" — `{r['render']}`" if r["render"] else ""))
        lines += [f"- `{i['code']}` {i['message']}" for i in r["issues"]]
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="*", type=Path,
                    default=[ROOT / "output" / "step0", ROOT / "output" / "colour-roles"])
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "geometry_replay")
    ap.add_argument("--reaudit", action="store_true", help="re-check the compiled folders of a previous run, no compile")
    args = ap.parse_args()
    rows = reaudit(args.out) if args.reaudit else run(args.roots, args.out)
    write(rows, args.out)
    print(f"summary: {args.out / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
