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
import time
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
    """Detect which screenshot backend to try first.

    This only checks that the Node runtime is reachable, not that
    LibreOffice/ImageMagick are actually installed — that is validated
    for real inside _render_via_node(), which falls back to COM on
    failure. Doing the LibreOffice/ImageMagick check here would require
    running screenshot-pom.js with a real PPTX, which is wasteful.
    """
    if _SCREENSHOT_SCRIPT.exists():
        try:
            proc = subprocess.run(
                [_NODE_BIN, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                logger.info("screenshot: node runtime available, will try node backend")
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


def _write_error_artifact(output_dir: str, backend: str, step: str, error: str) -> None:
    """Persist a failure record to disk. Log lines get missed; a file doesn't."""
    try:
        path = Path(output_dir) / "screenshot-error.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"backend": backend, "step": step, "error": error}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _list_powerpnt_pids() -> set[str]:
    """PIDs of currently running POWERPNT.EXE processes (Windows only)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        pids: set[str] = set()
        for line in result.stdout.strip().splitlines():
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) >= 2 and parts[0].upper() == "POWERPNT.EXE":
                pids.add(parts[1])
        return pids
    except Exception:
        return set()


def _kill_pids(pids: set[str]) -> None:
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, timeout=10)
        except Exception:
            pass


def _render_via_com(pptx_path: str, output_dir: str) -> ScreenshotBatchResult:
    """Use PowerPoint COM automation to export slides as PNG."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        import comtypes.client
    except ImportError:
        error = "comtypes not installed (pip install comtypes)"
        _write_error_artifact(output_dir, "com", "import", error)
        return ScreenshotBatchResult(ok=False, backend="com", error=error)

    pids_before = _list_powerpnt_pids() if sys.platform == "win32" else set()
    app = None
    pres = None
    step = "CreateObject"
    try:
        app = comtypes.client.CreateObject("PowerPoint.Application")

        step = "Presentations.Open"
        pres = app.Presentations.Open(
            str(Path(pptx_path).resolve()),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )

        slides: list[ScreenshotResult] = []
        for i, slide in enumerate(pres.Slides):
            step = f"Slide[{i}].Export"
            png_name = f"slide-{i}.png"
            png_full = str(output_path / png_name)
            slide.Export(png_full, "PNG", 1280, 720)
            slides.append(ScreenshotResult(
                ok=True, png_path=png_full, slide_index=i,
            ))

        return ScreenshotBatchResult(ok=True, slides=slides, backend="com")

    except Exception as e:
        error = f"{step} failed: {type(e).__name__}: {e}"
        logger.error(f"screenshot: COM error — {error}")
        _write_error_artifact(output_dir, "com", step, error)
        return ScreenshotBatchResult(ok=False, backend="com", error=error)
    finally:
        if pres is not None:
            try:
                pres.Close()
            except Exception as e:
                logger.warning(f"screenshot: COM presentation close failed: {e}")
        if app is not None:
            try:
                app.Quit()
            except Exception as e:
                logger.warning(f"screenshot: COM app quit failed: {e}")

        # Safety net: Quit() doesn't always fully tear down the underlying
        # process. A lingering POWERPNT.EXE left in a bad state gets
        # re-attached to by the *next* CreateObject call instead of a clean
        # instance, poisoning every screenshot after it (not just retries of
        # this one). Force-kill only PIDs that appeared during this specific
        # call — never a PID that existed before it — so a user's own
        # already-open PowerPoint windows are never touched.
        if sys.platform == "win32":
            _kill_new_powerpnt_processes(pids_before)


def _kill_new_powerpnt_processes(pids_before: set[str]) -> None:
    time.sleep(1)
    new_pids = _list_powerpnt_pids() - pids_before
    if new_pids:
        logger.warning(f"screenshot: force-killing lingering PowerPoint process(es): {new_pids}")
        _kill_pids(new_pids)


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
