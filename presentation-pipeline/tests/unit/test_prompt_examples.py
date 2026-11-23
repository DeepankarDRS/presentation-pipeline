"""Planner prompt / schema examples must not quote the decks we score on: a phrase from an eval case or the saved
A/B outlines gives that deck its answer, so its marks stop being an independent test (review 2026-11-23)."""

import re
from pathlib import Path

from src.agents.hint_capabilities import planner_capabilities_section
from src.agents.planner_schema_typed import PlannerSlideTyped
from src.agents.slide_component_planner import _jinja_env
from src.utils.strict_schema import sent_schema

ROOT = Path(__file__).resolve().parents[2]
EVAL_FILES = [*sorted((ROOT / "tests" / "cases").glob("*.yaml")), ROOT / "docs" / "eval" / "planner-ab" / "inputs.json"]
MIN_WORDS = 3


def _flat(text: str) -> str:
    return " ".join(text.split()).lower()


def _quoted(text: str) -> set[str]:
    """Double-quoted phrases, and single-quoted ones inside them, of MIN_WORDS words or more."""
    found = re.findall(r'"([^"\n]+)"', text) + re.findall(r"(?<!\w)'([^'\n]+)'(?!\w)", text)
    return {_flat(q) for q in found if len(q.split()) >= MIN_WORDS}


def _leaks(text: str) -> dict[str, str]:
    """Quoted phrase -> an eval file that holds it."""
    evals = {f.name: _flat(f.read_text(encoding="utf-8")) for f in EVAL_FILES}
    return {q: name for q in _quoted(text) for name, body in evals.items() if q in body}


def test_the_guard_finds_a_quoted_eval_phrase():
    assert _leaks('a purpose ("Close 3 enterprise logos worth $4M+ combined ARR") is split')


def test_no_planner_example_quotes_an_eval_deck():
    prompt = _jinja_env.get_template("system.j2").render(hint_capabilities=planner_capabilities_section())
    assert _leaks(prompt) == {}


def test_no_schema_description_quotes_an_eval_deck():
    texts: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("description"), str):
                texts.append(node["description"])
            node = list(node.values())
        if isinstance(node, list):
            for v in node:
                walk(v)

    walk(sent_schema(PlannerSlideTyped))
    assert texts and _leaks("\n".join(texts)) == {}
