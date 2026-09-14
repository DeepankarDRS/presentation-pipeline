"""Test session setup.

Disable LangChain / LangSmith tracing before any ``src`` import. The tracer
(langchain_core/tracers/langchain.py) calls Pydantic's deprecated
``.dict()`` / ``.construct()`` on every run, emitting ~100
PydanticDeprecatedSince20 warnings across the suite. Tests never need tracing.
``load_dotenv()`` in src.graph does not override already-set env vars, so
setting these here wins over any local .env.
"""

import os

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ.pop("LANGCHAIN_API_KEY", None)
os.environ.pop("LANGSMITH_API_KEY", None)
