"""Render + audit a folder of POM XML files — the offline quality feedback loop.

For every *.xml in --in, this:
  1. runs the POM compiler (buildPptx) → presentation.pptx + compile diagnostics
  2. converts the pptx → PDF via LibreOffice (so the slide can be eyeballed)
  3. runs src.compiler.layout_audit on the cleaned XML → mechanical spatial warnings

Writes <out>/<name>/ with input.xml, presentation.pptx, <name>.pdf, and a
combined report.json + a top-level summary.md.

No API key needed. Use it to (a) lock golden references, (b) score generator
output before/after a change.

    python -m scripts.render_check --in knowledge/examples --out output/render_check
    python -m scripts.render_check --in some/dir/of/xml --out /tmp/rc
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PIPELINE_ROOT))

from src.compiler.layout_audit import audit_layout  # noqa: E402

_NODE_BIN = os.environ.get("NODE_BIN", "node")
_COMPILE_SCRIPT = _PIPELINE_ROOT / "src" / "node" / "compile-pom.js"

_SOFFICE_CANDIDATES = [
    os.environ.get("SOFFICE_BIN", ""),
    "soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def _find_soffice() -> str | None:
    for cand in _SOFFICE_CANDIDATES:
        if not cand:
            continue
        if cand == "soffice" and shutil.which("soffice"):
            return "soffice"
        if Path(cand).exists():
            return cand
    return None


def _compile(xml_path: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [_NODE_BIN, str(_COMPILE_SCRIPT), str(xml_path), str(out_dir)],
        capture_output=True, text=True, timeout=120,
    )
    result_file = out_dir / "compile-result.json"
    if result_file.exists():
        data = json.loads(result_file.read_text(encoding="utf-8"))
    else:
        data = {"status": "harness_error", "diagnostics": [{"type": "HARNESS",
                "message": proc.stderr.strip()[:500]}]}
    return data


def _to_pdf(pptx: Path, out_dir: Path, soffice: str | None) -> str | None:
    if not soffice or not pptx.exists():
        return None
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)],
        capture_output=True, text=True, timeout=180,
    )
    pdf = out_dir / (pptx.stem + ".pdf")
    return str(pdf) if pdf.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", required=True, help="folder of *.xml")
    ap.add_argument("--out", dest="out_dir", default="output/render_check")
    ap.add_argument("--glob", default="*.xml")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    if not in_dir.is_absolute():
        in_dir = _PIPELINE_ROOT / in_dir
    out_root = Path(args.out_dir)
    if not out_root.is_absolute():
        out_root = _PIPELINE_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)

    soffice = _find_soffice()
    if not soffice:
        print("WARN: LibreOffice not found — PDFs will be skipped", file=sys.stderr)

    xml_files = sorted(in_dir.glob(args.glob))
    if not xml_files:
        print(f"no {args.glob} in {in_dir}", file=sys.stderr)
        return 1

    reports: list[dict] = []
    for xml_path in xml_files:
        name = xml_path.stem
        case_dir = out_root / name
        case_dir.mkdir(parents=True, exist_ok=True)
        xml = xml_path.read_text(encoding="utf-8")

        compile_data = _compile(xml_path, case_dir)
        ok = compile_data.get("status") == "success"
        diags = compile_data.get("diagnostics", [])

        pdf_path = None
        if ok:
            pdf_path = _to_pdf(case_dir / "presentation.pptx", case_dir, soffice)

        audit = audit_layout(xml)
        audit_high = [a for a in audit if a.get("severity") == "high"]

        rep = {
            "name": name,
            "compiles": ok,
            "compile_diagnostics": diags,
            "audit_issues": audit,
            "audit_high_count": len(audit_high),
            "pdf": pdf_path,
        }
        (case_dir / "report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        reports.append(rep)

        flag = "OK " if ok and not audit_high else "!! "
        print(f"{flag}{name:<32} compile={'ok' if ok else 'FAIL'} "
              f"diags={len(diags)} audit_high={len(audit_high)} "
              f"pdf={'yes' if pdf_path else 'no'}")

    lines = ["# render_check summary", ""]
    for r in reports:
        lines.append(f"## {r['name']}")
        lines.append(f"- compiles: {r['compiles']}")
        if r["compile_diagnostics"]:
            for d in r["compile_diagnostics"]:
                lines.append(f"  - DIAG {d.get('type')}: {d.get('message')}")
        for a in r["audit_issues"]:
            lines.append(f"  - AUDIT[{a.get('severity')}] {a.get('code')}: {a.get('message')}")
        if r["pdf"]:
            lines.append(f"- pdf: {r['pdf']}")
        lines.append("")
    (out_root / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    n_ok = sum(1 for r in reports if r["compiles"])
    n_clean = sum(1 for r in reports if r["compiles"] and r["audit_high_count"] == 0)
    print(f"\n{n_ok}/{len(reports)} compile, {n_clean}/{len(reports)} compile + audit-clean")
    print(f"summary -> {out_root / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
