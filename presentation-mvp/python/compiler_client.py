"""Subprocess bridge to node/compile-pom.js.

The contract (from plan.md): compile-pom.js writes compile-result.json into the
output dir and exits 0/1. Python reads that JSON and NEVER parses Node stderr.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import config
from models import CompileResult


class CompilerError(RuntimeError):
    """Raised when the Node process cannot be run or leaves no result file."""


def compile_xml(xml: str, output_dir: Path, *, timeout: int = 120) -> CompileResult:
    """Write `xml` to <output_dir>/input.xml, run compile-pom.js, parse the result.

    Returns a CompileResult mirroring compile-result.json. Raises CompilerError
    only for harness-level failures (node missing, no result file produced).
    """
    # Absolute paths: compile-pom.js runs with cwd=node/, so relative paths
    # would resolve against the wrong directory.
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = output_dir / "input.xml"
    input_path.write_text(xml, encoding="utf-8")

    result_path = output_dir / "compile-result.json"
    if result_path.exists():
        result_path.unlink()

    if not config.COMPILE_SCRIPT.exists():
        raise CompilerError(f"compile-pom.js not found at {config.COMPILE_SCRIPT}")

    cmd = [
        config.settings.node_bin,
        str(config.COMPILE_SCRIPT),
        str(input_path),
        str(output_dir),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(config.NODE_DIR),
        )
    except FileNotFoundError as exc:
        raise CompilerError(
            f"Could not execute Node ('{config.settings.node_bin}'). "
            "Set NODE_BIN in .env or put node on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CompilerError(f"compile-pom.js timed out after {timeout}s") from exc

    if not result_path.exists():
        raise CompilerError(
            "compile-pom.js produced no compile-result.json.\n"
            f"exit={proc.returncode}\nstderr:\n{(proc.stderr or '').strip()}"
        )

    data = json.loads(result_path.read_text(encoding="utf-8"))
    result = CompileResult.model_validate(data)

    # Keep the node stderr summary around for manual debugging only.
    result_meta = output_dir / "compile-stderr.txt"
    if (proc.stderr or "").strip():
        result_meta.write_text(proc.stderr, encoding="utf-8")

    return result


def validate_xml(xml: str, output_dir: Path, *, timeout: int = 30) -> CompileResult:
    """Run parseXml-only validation (no PPTX generation).

    Calls compile-pom.js --validate-only. Returns a CompileResult with
    structured parseXml errors. Faster than compile_xml because it skips
    buildPptx entirely.

    Falls back to None if the node binary or compile script is missing,
    letting the caller use pre_validator.py as a fallback.
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = output_dir / "input.xml"
    input_path.write_text(xml, encoding="utf-8")

    result_path = output_dir / "compile-result.json"
    if result_path.exists():
        result_path.unlink()

    if not config.COMPILE_SCRIPT.exists():
        return None

    cmd = [
        config.settings.node_bin,
        str(config.COMPILE_SCRIPT),
        "--validate-only",
        str(input_path),
        str(output_dir),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(config.NODE_DIR),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if not result_path.exists():
        return None

    data = json.loads(result_path.read_text(encoding="utf-8"))
    return CompileResult.model_validate(data)
