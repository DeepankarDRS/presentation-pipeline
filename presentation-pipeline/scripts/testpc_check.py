"""Is this PC set up to run the pipeline? Free: no LLM calls, nothing installed or changed.

    python -m scripts.testpc_check

Checks: the branch and commit; every package in requirements.txt against its version range; Node, and the Node packages
against src/node/package.json; the font files; the POM_* switches in .env; that an API key is set (never printed); and
one small real slide compiled, with fonts embedded, then exported through PowerPoint. Ends with a list of what to fix.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NODE = ROOT / "src" / "node"
SLIDE = '<Slide><VStack w="1280" h="720" padding="48" gap="16"><Text fontSize="32" bold="true">Setup check</Text></VStack></Slide>'


def run(*cmd: str) -> str:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=ROOT, shell=sys.platform == "win32")
        return done.stdout.strip() if done.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def python_packages() -> list[str]:
    bad = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        req = Requirement(line)
        if req.marker and not req.marker.evaluate():
            continue
        try:
            have = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            bad.append(f"{req.name}: not installed (needs {req.specifier})")
            print(f"  MISSING {req.name}")
            continue
        fits = req.specifier.contains(have, prereleases=True)
        print(f"  {'ok' if fits else 'WRONG'} {req.name} {have}")
        if not fits:
            bad.append(f"{req.name}: {have} installed, needs {req.specifier}")
    return bad


def node_packages() -> list[str]:
    bad = []
    version = run("node", "--version")
    print(f"  node {version or 'NOT FOUND'}")
    if not version:
        bad.append("node: not found")
    wanted = json.loads((NODE / "package.json").read_text(encoding="utf-8"))["dependencies"]
    for name, want in wanted.items():
        f = NODE / "node_modules" / name / "package.json"
        have = json.loads(f.read_text(encoding="utf-8"))["version"] if f.exists() else None
        print(f"  {'ok' if have == want else 'WRONG'} {name} {have or 'not installed'}")
        if have != want:
            bad.append(f"{name}: {have or 'not installed'}, needs {want} (run: npm install, in src/node)")
    return bad


def switches() -> list[str]:
    env = ROOT / ".env"
    lines = env.read_text(encoding="utf-8", errors="replace").splitlines() if env.exists() else []
    set_here = [ln.strip() for ln in lines if re.match(r"\s*POM_(NODES|BLOCKS)\s*=", ln)]
    for ln in set_here:
        print(f"  .env sets {ln}")
    if not set_here:
        print("  ok .env sets no POM_NODES or POM_BLOCKS: the defaults apply")
    keyed = any(re.match(r"\s*\w*API_KEY\s*=\s*\S", ln) for ln in lines) or any(k.endswith("API_KEY") and os.environ[k] for k in os.environ)
    print(f"  {'ok' if keyed else 'MISSING'} API key {'set' if keyed else 'not set'} (needed only for paid runs)")
    return ([f".env overrides the default: {', '.join(set_here)} (delete the line to use the default)"] if set_here else []) \
        + ([] if keyed else ["API key: not set (needed only for paid runs)"])


def real_slide() -> list[str]:
    """The path a real slide takes: compile, embed the fonts, export through PowerPoint."""
    from scripts.kpi_replay import compile_slide
    from src.agents.style_resolver import resolve_theme
    from src.compiler.compiler_client import deck_font
    from src.compiler.font_embed import embed_deck_fonts
    from src.compiler.screenshot import render_screenshots

    tmp = Path(tempfile.mkdtemp(prefix="testpc-check-"))
    try:
        compile_slide(deck_font(SLIDE), resolve_theme("corporate-slate")["element"], tmp)
        pptx = tmp / "presentation.pptx"
        if not pptx.exists():
            return [f"compile: no pptx made: {(tmp / 'compile-result.json').read_text(encoding='utf-8')[:200]}"]
        print("  ok compiled a slide")
        fonts = embed_deck_fonts(pptx)
        faces = [f"{e['family']} {e['face']}" for e in fonts.get("embedded") or []]
        print(f"  {'ok' if faces else 'WRONG'} fonts embedded: {', '.join(faces) or fonts.get('skipped')}")
        bad = [] if faces else [f"fonts: nothing embedded: {fonts.get('skipped')}"]
        shot = render_screenshots(str(pptx), str(tmp))
        print(f"  {'ok' if shot.ok else 'WRONG'} PowerPoint export{'' if shot.ok else ': ' + str(shot.error)}")
        return bad + ([] if shot.ok else [f"PowerPoint export: {shot.error}"])
    except Exception as e:   # the report must reach the end
        return [f"real slide: {type(e).__name__}: {e}"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    print(f"branch {run('git', 'rev-parse', '--abbrev-ref', 'HEAD') or '?'}, commit {run('git', 'rev-parse', '--short', 'HEAD') or '?'}, python {sys.version.split()[0]}")
    problems: list[str] = []
    for title, check in (("Python packages", python_packages), ("Node", node_packages), ("Settings", switches), ("A real slide", real_slide)):
        print(title)
        problems += check()
    print()
    if problems:
        print(f"FIX THESE ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
