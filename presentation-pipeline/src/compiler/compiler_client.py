"""Subprocess bridge to compile-pom.js (src/node/).

The Node script writes compile-result.json into the output dir;
Python reads that JSON and NEVER parses Node stderr.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SRC_DIR = Path(__file__).resolve().parent.parent
_NODE_DIR = _SRC_DIR / "node"
_COMPILE_SCRIPT = _NODE_DIR / "compile-pom.js"

_NODE_BIN = os.environ.get("NODE_BIN", "node")


class CompilerError(RuntimeError):
    """Raised when the Node process cannot be run or leaves no result file."""


def _parse_result(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize compile-result.json into our standard CompileResult shape."""
    ok = data.get("status") == "success"
    diagnostics = data.get("diagnostics", [])
    warnings = data.get("warnings", [])

    retryable = False
    if not ok and diagnostics:
        retryable_types = {
            "UNKNOWN_TAG", "UNKNOWN_ATTRIBUTE", "PARSE_ERROR",
            "INVALID_VALUE", "INVALID_CHILD", "THEME_ERROR", "DIAGNOSTIC",
        }
        retryable = any(d.get("type") in retryable_types for d in diagnostics)

    return {
        "ok": ok,
        "pptx_path": data.get("pptxPath"),
        "diagnostics": diagnostics,
        "warnings": warnings,
        "retryable": retryable,
    }


def compile_xml(xml: str, output_dir: Path, *, timeout: int = 120) -> dict[str, Any]:
    """Write xml to output_dir/input.xml, run compile-pom.js, return CompileResult dict."""
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = output_dir / "input.xml"
    input_path.write_text(xml, encoding="utf-8")

    result_path = output_dir / "compile-result.json"
    if result_path.exists():
        result_path.unlink()

    if not _COMPILE_SCRIPT.exists():
        raise CompilerError(f"compile-pom.js not found at {_COMPILE_SCRIPT}")

    cmd = [_NODE_BIN, str(_COMPILE_SCRIPT), str(input_path), str(output_dir)]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(_NODE_DIR),
        )
    except FileNotFoundError as exc:
        raise CompilerError(
            f"Could not execute Node ('{_NODE_BIN}'). "
            "Set NODE_BIN env var or put node on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CompilerError(f"compile-pom.js timed out after {timeout}s") from exc

    if not result_path.exists():
        raise CompilerError(
            "compile-pom.js produced no compile-result.json.\n"
            f"exit={proc.returncode}\nstderr:\n{(proc.stderr or '').strip()}"
        )

    data = json.loads(result_path.read_text(encoding="utf-8"))
    return _parse_result(data)


def validate_xml(xml: str, output_dir: Path, *, timeout: int = 30) -> dict[str, Any] | None:
    """Run parseXml-only validation (no PPTX generation).

    Returns a CompileResult dict with structured errors, or None if the
    compiler is not available.
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = output_dir / "input.xml"
    input_path.write_text(xml, encoding="utf-8")

    result_path = output_dir / "compile-result.json"
    if result_path.exists():
        result_path.unlink()

    if not _COMPILE_SCRIPT.exists():
        return None

    cmd = [_NODE_BIN, str(_COMPILE_SCRIPT), "--validate-only", str(input_path), str(output_dir)]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(_NODE_DIR),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if not result_path.exists():
        return None

    data = json.loads(result_path.read_text(encoding="utf-8"))
    return _parse_result(data)
