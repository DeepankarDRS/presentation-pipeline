"""Central configuration: paths, env vars, model settings.

Every path is derived from this file's location so the project stays portable
(clone anywhere, run on Windows or POSIX). Nothing here is hardcoded to a user
directory. Secrets and model choice come from `.env` (see `.env.example`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency missing before pip install
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


# ── Paths ────────────────────────────────────────────────────────────────────
# config.py lives in <project>/python/config.py
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

ENV_FILE: Path = PROJECT_ROOT / ".env"
# Optional project-wide theme selection. See pom-knowledge/theme/palettes.yaml.
THEME_FILE: Path = PROJECT_ROOT / "theme.yaml"
NODE_DIR: Path = PROJECT_ROOT / "node"
COMPILE_SCRIPT: Path = NODE_DIR / "compile-pom.js"
KNOWLEDGE_DIR: Path = PROJECT_ROOT / "pom-knowledge"
EXAMPLES_DIR: Path = KNOWLEDGE_DIR / "examples"
PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"
TESTS_DIR: Path = PROJECT_ROOT / "tests"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"

# The XML used as the "generated" output when --dry-run skips the LLM call.
DRY_RUN_XML: Path = EXAMPLES_DIR / "text-slide.xml"

# Slide geometry — POM default, passed to buildPptx and used for bounds checks.
SLIDE_W: int = 1280
SLIDE_H: int = 720

POM_VERSION: str = "10.3.0"


# ── Loaded settings ──────────────────────────────────────────────────────────
def _get_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 2000
    openai_base_url: str | None = None
    node_bin: str = "node"
    retry_budget: int = 3

    # Convenience mirrors of the module-level path constants.
    project_root: Path = field(default=PROJECT_ROOT)
    compile_script: Path = field(default=COMPILE_SCRIPT)
    knowledge_dir: Path = field(default=KNOWLEDGE_DIR)
    output_dir: Path = field(default=OUTPUT_DIR)
    dry_run_xml: Path = field(default=DRY_RUN_XML)

    def require_api_key(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key, "
                "or run with --dry-run to skip the LLM call."
            )
        return self.openai_api_key


def load_settings(env_file: Path | None = None) -> Settings:
    """Read `.env` (if present) plus the process environment into a Settings."""
    target = env_file or ENV_FILE
    if target.exists():
        load_dotenv(target, override=False)

    # The openai SDK auto-reads OPENAI_BASE_URL / OPENAI_API_BASE from the
    # environment. An empty value (common in a copied .env) produces a hostless
    # URL and "Connection error". Drop empties so the SDK uses its default.
    for var in ("OPENAI_BASE_URL", "OPENAI_API_BASE"):
        if var in os.environ and not os.environ[var].strip():
            del os.environ[var]

    # Same story for LangSmith: an empty LANGSMITH_ENDPOINT from a copied .env
    # yields a hostless tracing URL. Drop it so the langsmith SDK falls back to
    # its default endpoint (https://api.smith.langchain.com).
    if "LANGSMITH_ENDPOINT" in os.environ and not os.environ["LANGSMITH_ENDPOINT"].strip():
        del os.environ["LANGSMITH_ENDPOINT"]

    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o",
        openai_temperature=_get_float("OPENAI_TEMPERATURE", 0.2),
        openai_max_tokens=_get_int("OPENAI_MAX_TOKENS", 2000),
        openai_base_url=(os.environ.get("OPENAI_BASE_URL", "").strip() or None),
        node_bin=os.environ.get("NODE_BIN", "node").strip() or "node",
        retry_budget=_get_int("RETRY_BUDGET", 3),
    )


def load_theme_config(theme_file: Path | None = None) -> tuple[str | None, dict]:
    """Read the project-root theme.yaml, if present.

    Returns (palette_name_or_None, token_overrides). Shape:

        theme: corporate-slate          # a palettes.yaml name (or dark/light)
        tokens:                         # optional per-token overrides
          accent: "0052CC"
        chartColors: ["0052CC", ...]    # optional

    A missing file (the common case) yields (None, {}) and the library default
    is used.
    """
    target = theme_file or THEME_FILE
    if not target.exists() or yaml is None:
        return None, {}
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return None, {}
    name = data.get("theme") or data.get("name") or data.get("palette")
    overrides: dict = dict(data.get("tokens") or {})
    if "chartColors" in data:
        overrides["chartColors"] = data["chartColors"]
    return (str(name).strip() if name else None), overrides


# A ready-to-use instance for simple imports. Call load_settings() directly in
# tests that need a custom env file.
settings: Settings = load_settings()
