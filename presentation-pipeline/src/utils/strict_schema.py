"""Offline check of a response_format schema against OpenAI's documented strict Structured Outputs rules.

Checks the schema the openai SDK actually sends for a Pydantic model (`type_to_response_format_param`, the path
langchain's `with_structured_output(method="json_schema")` takes). Rules, from
developers.openai.com/api/docs/guides/structured-outputs ("Supported schemas", read 2026-10-15):
root is an object (not anyOf); every object has additionalProperties false and lists every property in
required; no allOf / not / if / then / else / dependentRequired / dependentSchemas (and no oneOf, which the
subset does not list); at most 5000 object properties, 10 levels of nesting, 1000 enum values and 120,000
characters of property names, definition names, enum and const values; a string enum over 250 values at most
15,000 characters.
"""

from __future__ import annotations

from typing import Any

UNSUPPORTED = ("allOf", "not", "if", "then", "else", "dependentRequired", "dependentSchemas", "oneOf",
               "patternProperties", "discriminator")
MAX_PROPERTIES, MAX_DEPTH, MAX_ENUM_VALUES, MAX_STRING_CHARS = 5000, 10, 1000, 120_000


def sent_schema(model: type) -> dict[str, Any]:
    """The json_schema the openai SDK sends for `model` (strict)."""
    from openai.lib._parsing._completions import type_to_response_format_param
    return type_to_response_format_param(model)["json_schema"]["schema"]  # type: ignore[index]


def _resolve(node: dict[str, Any], root: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    ref = node.get("$ref")
    if not ref:
        return node, None
    if ref == "#":
        return root, ref
    target: Any = root
    for part in ref.lstrip("#/").split("/"):
        target = target[part]
    return target, ref


def strict_problems(schema: dict[str, Any]) -> tuple[list[str], dict[str, int]]:
    """(problems, sizes) for a sent schema; sizes = properties, depth, enum_values, string_chars."""
    problems: list[str] = []
    sizes = {"properties": 0, "depth": 0, "enum_values": 0, "string_chars": 0}
    if schema.get("type") != "object" or "anyOf" in schema:
        problems.append("root must be an object, not anyOf")
    sizes["string_chars"] += sum(len(k) for k in schema.get("$defs", {}))

    def walk(node: dict[str, Any], path: str, depth: int, refs: tuple[str, ...]) -> None:
        node, ref = _resolve(node, schema)
        if ref:
            if ref in refs:      # recursion: allowed, counted once
                return
            refs = (*refs, ref)
        for key in UNSUPPORTED:
            if key in node:
                problems.append(f"{path}: unsupported keyword {key}")
        if "enum" in node:
            sizes["enum_values"] += len(node["enum"])
            sizes["string_chars"] += sum(len(str(v)) for v in node["enum"])
            if len(node["enum"]) > 250 and sum(len(str(v)) for v in node["enum"]) > 15_000:
                problems.append(f"{path}: enum over 250 values and 15,000 characters")
        if "const" in node:
            sizes["string_chars"] += len(str(node["const"]))
        types = node.get("type")
        if types == "object" or (isinstance(types, list) and "object" in types):
            sizes["depth"] = max(sizes["depth"], depth)
            props = node.get("properties", {})
            sizes["properties"] += len(props)
            sizes["string_chars"] += sum(len(k) for k in props)
            if node.get("additionalProperties") is not False:
                problems.append(f"{path}: additionalProperties must be false")
            if set(node.get("required", [])) != set(props):
                problems.append(f"{path}: every property must be required")
            for name, sub in props.items():
                walk(sub, f"{path}.{name}", depth + 1, refs)
        if "items" in node:
            walk(node["items"], f"{path}[]", depth, refs)
        for i, sub in enumerate(node.get("anyOf", [])):
            walk(sub, f"{path}|{i}", depth, refs)

    walk(schema, "$", 1, ())
    if sizes["properties"] > MAX_PROPERTIES:
        problems.append(f"{sizes['properties']} object properties (max {MAX_PROPERTIES})")
    if sizes["depth"] > MAX_DEPTH:
        problems.append(f"nesting depth {sizes['depth']} (max {MAX_DEPTH})")
    if sizes["enum_values"] > MAX_ENUM_VALUES:
        problems.append(f"{sizes['enum_values']} enum values (max {MAX_ENUM_VALUES})")
    if sizes["string_chars"] > MAX_STRING_CHARS:
        problems.append(f"{sizes['string_chars']} schema string characters (max {MAX_STRING_CHARS})")
    return problems, sizes
