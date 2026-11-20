"""Every LLM output schema builds. A model that is not fully defined (a type used but not imported) fails only
when the LLM call is made, and the critic fails open on that: from 2026-10-14 to 2026-11-20 a missing
`Literal` import made every visual review pass without one."""

import importlib
import inspect
from pathlib import Path

import pytest
from pydantic import BaseModel

_AGENTS = Path(__file__).resolve().parents[2] / "src" / "agents"
_MODULES = sorted(f"src.agents.{p.stem}" for p in _AGENTS.glob("*_schema*.py"))


def _models():
    for name in _MODULES:
        module = importlib.import_module(name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseModel) and obj.__module__ == name:
                yield pytest.param(obj, id=f"{name.rsplit('.', 1)[-1]}.{obj.__name__}")


def test_schema_modules_found():
    assert "src.agents.critic_schema" in _MODULES


@pytest.mark.parametrize("model", list(_models()))
def test_schema_builds(model):
    model.model_json_schema()
