"""PPTX-to-PNG screenshot service.

Primary: Node.js script (screenshot-pom.js) using LibreOffice + ImageMagick.
Fallback: PowerPoint COM automation via comtypes (Windows only).

All public functions return ScreenshotResult — callers never crash.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

_SRC_DIR = Path(__file__).resolve().parent.parent
_NODE_DIR = _SRC_DIR / "node"
_SCREENSHOT_SCRIPT = _NODE_DIR / "screenshot-pom.js"
_NODE_BIN = os.environ.get("NODE_BIN", "node")


@dataclass
class ScreenshotResult:
    ok: bool
    png_path: str | None = None
    slide_index: int = 0
    error: str | None = None


@dataclass
class ScreenshotBatchResult:
    ok: bool
    slides: list[ScreenshotResult] = field(default_factory=list)
    backend: str = ""
    error: str | None = None


Backend = Literal["node", "com", None]


@lru_cache(maxsize=1)
def _check_screenshot_backend() -> Backend:
    """Detect which screenshot backend is available."""
    if _SCREENSHOT_SCRIPT.exists():
        try:
            proc = subprocess.run(
                [_NODE_BIN, str(_SCREENSHOT_SCRIPT)],
                capture_output=True, text=True, timeout=10,
            )
            stderr = proc.stderr or ""
            if "LibreOffice" not in stderr and "ImageMagick" not in stderr:
                logger.info("screenshot: node backend available")
                return "node"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    if sys.platform == "win32":
        try:
            import comtypes.client  # noqa: F401
            logger.info("screenshot: PowerPoint COM backend available")
            return "com"
        except ImportError:
            pass

    logger.warning("screenshot: no backend available")
    return None


def _render_via_node(pptx_path: str, output_dir: str) -> ScreenshotBatchResult:
    """Call screenshot-pom.js and parse screenshot-result.json."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    result_path = output_path / "screenshot-result.json"

    cmd = [_NODE_BIN, str(_SCREENSHOT_SCRIPT), str(pptx_path), str(output_dir)]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            cwd=str(_NODE_DIR),
        )
    except FileNotFoundError:
        return ScreenshotBatchResult(
            ok=False, backend="node",
            error=f"Could not execute Node ('{_NODE_BIN}')",
        )
    except subprocess.TimeoutExpired:
        return ScreenshotBatchResult(
            ok=False, backend="node",
            error="screenshot-pom.js timed out after 180s",
        )

    if not result_path.exists():
        return ScreenshotBatchResult(
            ok=False, backend="node",
            error="screenshot-pom.js produced no screenshot-result.json",
        )

    data = json.loads(result_path.read_text(encoding="utf-8"))
    slides = [
        ScreenshotResult(ok=True, png_path=s["pngPath"], slide_index=s["index"])
        for s in data.get("slides", [])
    ]

    if not data.get("ok", False):
        return ScreenshotBatchResult(
            ok=False, slides=slides, backend="node",
            error=data.get("error", "Unknown screenshot error"),
        )

    return ScreenshotBatchResult(ok=True, slides=slides, backend="node")


def _render_via_com(pptx_path: str, output_dir: str) -> ScreenshotBatchResult:
    """Use PowerPoint COM automation to export slides as PNG."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        import comtypes.client
    except ImportError:
        return ScreenshotBatchResult(
            ok=False, backend="com",
            error="comtypes not installed (pip install comtypes)",
        )

    app = None
    pres = None
    try:
        app = comtypes.client.CreateObject("PowerPoint.Application")
        pres = app.Presentations.Open(
            str(Path(pptx_path).resolve()),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )

        slides: list[ScreenshotResult] = []
        for i, slide in enumerate(pres.Slides):
            png_name = f"slide-{i}.png"
            png_full = str(output_path / png_name)
            slide.Export(png_full, "PNG", 1280, 720)
            slides.append(ScreenshotResult(
                ok=True, png_path=png_full, slide_index=i,
            ))

        return ScreenshotBatchResult(ok=True, slides=slides, backend="com")

    except Exception as e:
        return ScreenshotBatchResult(
            ok=False, backend="com",
            error=f"PowerPoint COM error: {e}",
        )
    finally:
        if pres is not None:
            try:
                pres.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass


def render_screenshots(
    pptx_path: str,
    output_dir: str,
) -> ScreenshotBatchResult:
    """Render each slide in a PPTX to PNG. Tries node first, then COM fallback.

    Always returns a result — never raises.
    """
    if not Path(pptx_path).exists():
        return ScreenshotBatchResult(
            ok=False, error=f"PPTX not found: {pptx_path}",
        )

    backend = _check_screenshot_backend()

    if backend == "node":
        result = _render_via_node(pptx_path, output_dir)
        if result.ok:
            logger.info(f"screenshot: rendered {len(result.slides)} slide(s) via node")
            return result
        logger.warning(f"screenshot: node failed ({result.error}), trying COM fallback")
        if sys.platform == "win32":
            return _render_via_com(pptx_path, output_dir)
        return result

    if backend == "com":
        result = _render_via_com(pptx_path, output_dir)
        if result.ok:
            logger.info(f"screenshot: rendered {len(result.slides)} slide(s) via COM")
        return result

    return ScreenshotBatchResult(
        ok=False,
        error="No screenshot backend available. Install LibreOffice+ImageMagick or comtypes.",
    )
