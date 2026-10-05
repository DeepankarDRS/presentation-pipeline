"""The project supports Python >= 3.11 (pyproject `requires-python`), but development may run on
3.12+, where PEP 701 relaxed f-strings. Code that only parses on 3.12+ then breaks on the test PC
("SyntaxError: f-string expression part cannot include a backslash", compose_deck 2026-10-05).

This scans every project .py file with the running tokenizer and flags what Python 3.11 rejects
inside an f-string replacement field:
  - a backslash anywhere in the expression,
  - a string literal that would end the enclosing f-string (its quote character in a
    single-quoted f-string, the whole triple quote in a triple-quoted one),
  - a comment,
  - a line break inside a single-quoted f-string.
Needs a 3.12+ tokenizer (FSTRING_* tokens); on 3.11 the interpreter checks this itself.
"""

from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCAN = ["src", "scripts", "tests"]
TRIPLES = ('"' * 3, "'" * 3)


def _quote(token: str) -> str:
    body = token.lstrip("rRbBfFuU")
    return body[:3] if body[:3] in TRIPLES else body[:1]


def _clashes(inner: str, stack: list[dict]) -> bool:
    """An inner string literal that would end an enclosing f-string on 3.11."""
    for s in stack:
        if len(s["quote"]) == 3:
            if s["quote"] in inner:
                return True
        elif _quote(inner)[0] == s["quote"]:
            return True
    return False


def py311_fstring_problems(source: str) -> list[str]:
    """'line: problem' for f-string syntax that Python 3.11 cannot parse."""
    problems = []
    stack: list[dict] = []  # open f-strings: quote, depth of { } inside it
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.FSTRING_START:
            if stack and stack[-1]["depth"] > 0 and _clashes(tok.string, stack):
                problems.append(f"{tok.start[0]}: nested f-string ends an enclosing one on 3.11")
            stack.append({"quote": _quote(tok.string), "depth": 0})
            continue
        if not stack:
            continue
        top = stack[-1]
        if tok.type == tokenize.FSTRING_END:
            stack.pop()
        elif tok.type == tokenize.FSTRING_MIDDLE:
            pass
        elif tok.type == tokenize.OP and tok.string == "{":
            top["depth"] += 1
        elif tok.type == tokenize.OP and tok.string == "}":
            top["depth"] = max(0, top["depth"] - 1)
        elif top["depth"] > 0:  # inside a replacement field
            if "\\" in tok.string:
                problems.append(f"{tok.start[0]}: backslash inside an f-string expression")
            if tok.type == tokenize.STRING and _clashes(tok.string, stack):
                problems.append(f"{tok.start[0]}: string literal ends the enclosing f-string on 3.11")
            if tok.type == tokenize.COMMENT:
                problems.append(f"{tok.start[0]}: comment inside an f-string expression")
            if tok.type in (tokenize.NL, tokenize.NEWLINE) and len(top["quote"]) == 1:
                problems.append(f"{tok.start[0]}: line break inside a single-quoted f-string expression")
    return problems


def _files() -> list[Path]:
    return sorted(p for d in SCAN for p in (ROOT / d).rglob("*.py")
                  if "node_modules" not in p.parts and ".venv" not in p.parts)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="needs the 3.12+ f-string tokenizer")
@pytest.mark.parametrize("src", [
    'x = f"{a["k"]}"\n',                      # same quote inside
    "x = f'{chr(92).join(a) + \"\\n\"}'\n",   # backslash in the expression
    'x = f"{a # c\n}"\n',                     # comment
    "x = f'{a +\nb}'\n",                      # line break in a single-quoted f-string
])
def test_checker_flags_311_errors(src: str) -> None:
    assert py311_fstring_problems(src)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="needs the 3.12+ f-string tokenizer")
@pytest.mark.parametrize("src", [
    "x = f\"{a['k']}\"\n",                    # other quote inside
    'x = f"{a}\\n"\n',                        # backslash outside the expression
    'x = f"""{a +\nb}"""\n',                  # line break in a triple-quoted f-string
    'x = f"{a:>{w}}"\n',                      # nested format spec
    "x = f'''{g(a, 'k')}'''\n",               # single quote inside a triple-single-quoted f-string
])
def test_checker_accepts_311_code(src: str) -> None:
    assert not py311_fstring_problems(src)


def test_project_grammar_is_python_311() -> None:
    """ast in 3.11 mode rejects newer statement syntax (type aliases, generic def / class [T])."""
    import ast
    found = []
    for path in _files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 11))
        except SyntaxError as e:
            found.append(f"{path.relative_to(ROOT)}:{e.lineno}: {e.msg}")
    assert not found, "syntax newer than Python 3.11:\n" + "\n".join(found)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="needs the 3.12+ f-string tokenizer")
def test_project_parses_on_python_311() -> None:
    found = [f"{path.relative_to(ROOT)}:{p}" for path in _files()
             for p in py311_fstring_problems(path.read_text(encoding="utf-8"))]
    assert not found, "f-string syntax Python 3.11 rejects:\n" + "\n".join(found)
