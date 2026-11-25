"""Subprocess bridge to compile-pom.js (src/node/).

The Node script writes compile-result.json into the output dir;
Python reads that JSON and NEVER parses Node stderr.
"""

from __future__ import annotations

import json
import logging
import os
import re
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


# The deck font (2026-10-08): POM names "Noto Sans JP" and nothing is embedded, so each viewer drew a
# different substitute while fit-grow measured another. Inter ships in src/node/fonts (OFL) and is
# embedded by font_embed. POM_DECK_FONT=none keeps POM's default.
FONT_TAGS = ("Text", "Ul", "Ol", "Td", "Timeline", "ProcessArrow", "Pyramid", "Shape")
DECK_FONT = os.environ.get("POM_DECK_FONT", "Inter")


# The run's font pair (palettes.yaml font_pairs), a comment beside the <Theme>; none = DECK_FONT everywhere.
_FONTS_RE = re.compile(r'<!-- deck-fonts heading="([\w ]+)" body="([\w ]+)"(?: scale="([\d.]+)")? -->')
HEADLINE_MIN = 28   # px: a slide's first <Text> this large is its headline (the prompts write 30-38, covers more)
_TEXT_TAG_RE = re.compile(r"<Text\b[^<>]*>")
_FONT_SIZE_RE = re.compile(r'\sfontSize="(\d+(?:\.\d+)?)"')


def deck_fonts(xml: str) -> tuple[str, str, float] | None:
    """(heading, body, headline size factor) of the font pair the XML names; None for the default."""
    m = _FONTS_RE.search(xml)
    return (m.group(1), m.group(2), float(m.group(3) or 1)) if m else None


def _headline_font(slide: str, family: str, scale: float) -> str:
    """The slide with its headline in `family`, its size times `scale`."""
    for m in _TEXT_TAG_RE.finditer(slide):
        size = _FONT_SIZE_RE.search(m.group(0))
        if size and float(size.group(1)) >= HEADLINE_MIN:
            if "fontFamily=" in m.group(0):
                return slide
            tag = m.group(0)
            if scale < 1:
                tag = _FONT_SIZE_RE.sub(f' fontSize="{int(float(size.group(1)) * scale)}"', tag, count=1)
            return f'{slide[:m.start()]}<Text fontFamily="{family}"{tag[len("<Text"):]}{slide[m.end():]}'
    return slide


def deck_font(xml: str, family: str | None = DECK_FONT) -> str:
    """Every text-bearing node without a fontFamily gets the deck font: the XML's own font pair
    (the headline its heading font, the rest its body font), else `family`."""
    pair = deck_fonts(xml)
    if pair:
        family = pair[1]
        if pair[0] != family:
            xml = re.sub(r"<Slide\b.*?</Slide>", lambda m: _headline_font(m.group(0), pair[0], pair[2]),
                         xml, flags=re.DOTALL)
    if not family or family.lower() == "none":
        return xml
    pat = re.compile(rf"<({'|'.join(FONT_TAGS)})\b(?![^<>]*\bfontFamily=)")
    return pat.sub(lambda m: f'<{m.group(1)} fontFamily="{family}"', xml)


def compile_xml(xml: str, output_dir: Path, *, timeout: int = 120) -> dict[str, Any]:
    """Write xml (in the deck font) to output_dir/input.xml, run compile-pom.js, return CompileResult dict."""
    pair = deck_fonts(xml)
    xml = deck_font(xml)
    env = {**os.environ, "POM_FONT_FAMILIES": "|".join(sorted({
        *re.findall(r'\sfontFamily="([^"]+)"', xml), pair[1] if pair else DECK_FONT}))}
    if pair:
        env["POM_DECK_FONT"] = pair[1]   # for the text POM takes no fontFamily on (fonts.js DECK_FONT)
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
            env=env,
        )
    except FileNotFoundError as exc:
        raise CompilerError(
            f"Could not execute Node ('{_NODE_BIN}'). "
            "Set NODE_BIN env var or put node on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        # the result was written but Node did not exit (an open handle): the compile itself finished
        if result_path.exists():
            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                data = None
            if data and data.get("status"):
                logger.warning(f"compile-pom.js wrote its result but did not exit within {timeout}s; result kept")
                return _parse_result(data)
        raise CompilerError(f"compile-pom.js timed out after {timeout}s") from exc

    if not result_path.exists():
        raise CompilerError(
            "compile-pom.js produced no compile-result.json.\n"
            f"exit={proc.returncode}\nstderr:\n{(proc.stderr or '').strip()}"
        )

    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise CompilerError(f"corrupt compile-result.json: {exc}") from exc
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

    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None
    return _parse_result(data)
