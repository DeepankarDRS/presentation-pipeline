"""Build the (system, user) message pair from a GenerationContract.

The wording lives in editable template files under prompts/ (see prompts/README.md):

  prompts/system-selective.txt + prompts/user-selective.txt

Placeholder values come from the GenerationContract and the SlideIR.
Substitution is a literal {{key}} -> value replace; an unresolved {{token}} left
in a template raises rather than reaching the model.
"""

from __future__ import annotations

import json
import re

import config
from models import GenerationContract, SlideIR

_PLACEHOLDER_RE = re.compile(r"\{\{([a-z_]+)\}\}")


def _load_template(name: str) -> str:
    path = config.PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"prompt template not found: {path}. Expected it under prompts/ "
            "(see prompts/README.md)."
        )
    return path.read_text(encoding="utf-8")


def _render(template_name: str, values: dict[str, str]) -> str:
    text = _load_template(template_name)

    def sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(
                f"{template_name}: unknown placeholder {{{{{key}}}}}. "
                f"Known: {', '.join(sorted(values))}."
            )
        return values[key]

    return _PLACEHOLDER_RE.sub(sub, text).strip()


def _or_none(value: str) -> str:
    return value if value.strip() else "(none)"


def _fmt_attributes(contract: GenerationContract) -> str:
    lines: list[str] = []
    for node, attrs in contract.allowed_attributes.items():
        lines.append(f"  <{node}>: {', '.join(attrs) if attrs else '(text content only)'}")
    return "\n".join(lines)


def _fmt_examples(contract: GenerationContract) -> str:
    blocks = []
    for i, ex in enumerate(contract.examples, 1):
        blocks.append(f"--- example {i} ---\n{ex}")
    return "\n\n".join(blocks)


def build(ir: SlideIR, contract: GenerationContract) -> tuple[str, str]:
    system = _render("system-selective.txt", {
        "forbidden_tags": " ".join(f"<{t}>" for t in contract.forbidden_tags),
        "forbidden_attrs": ", ".join(contract.forbidden_attributes),
        "allowed_nodes": _or_none(", ".join(contract.allowed_nodes)),
        "allowed_attributes": _or_none(_fmt_attributes(contract)),
        "theme": _or_none(contract.theme_element),
        "layout_pattern": _or_none(contract.layout_pattern),
        "examples": _or_none(_fmt_examples(contract)),
        "notes": _or_none("\n".join(f"- {n}" for n in contract.notes)),
    })

    supplied = ""
    if ir.supplied_content:
        supplied = (
            "\nSUPPLIED CONTENT (use these values exactly; invent the rest):\n"
            + json.dumps(ir.supplied_content, indent=2)
        )

    user = _render("user-selective.txt", {
        "objective": ir.objective,
        "components": "\n".join(f"- {c.value}" for c in ir.component_kinds),
        "request": ir.request,
        "supplied_content": supplied,
    })
    return system, user


# ── repair (retry) ─────────────────────────────────────────────────────────
def build_repair(previous_user: str, problems: list[str]) -> str:
    """Legacy repair prompt (backward compat). Prefer build_repair_v2."""
    return _render("repair-user.txt", {
        "previous_user": previous_user,
        "problems": _or_none("\n".join(f"- {p}" for p in problems)),
    })


def build_repair_patch(
    previous_user: str,
    failing_xml: str,
    problems: list[str],
    guidance: str,
) -> str:
    """Tier 1: feed back the failing XML + error-specific guidance."""
    return _render("repair-patch.txt", {
        "previous_user": previous_user,
        "failing_xml": failing_xml,
        "problems": _or_none("\n".join(f"- {p}" for p in problems)),
        "guidance": _or_none(guidance),
    })


def build_repair_simplify(
    previous_user: str,
    problems: list[str],
    simplify_instructions: str,
    allowed_nodes: list[str],
) -> str:
    """Tier 2: regenerate with a simpler layout."""
    return _render("repair-simplify.txt", {
        "previous_user": previous_user,
        "problems": _or_none("\n".join(f"- {p}" for p in problems)),
        "simplify_instructions": simplify_instructions,
        "allowed_nodes": ", ".join(allowed_nodes),
    })


def build_repair_template(
    previous_user: str,
    template_xml: str,
) -> str:
    """Tier 3: use a verified template as skeleton."""
    return _render("repair-template.txt", {
        "previous_user": previous_user,
        "template_xml": template_xml,
    })
