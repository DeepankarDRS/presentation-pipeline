"""Index a brief into addressable blocks — the fact store of planning v2 (code, no LLM).

Every line of the brief becomes a block with an id the LLM can point at:
  L<n>  a line of text (long lines are split into sentences / list items)
  T<n>  a pipe table ("A | B | C" rows), parsed into header + rows
  C<n>  a chart block ("Chart (bar):" + "  Series: label value, ..." lines), parsed into series

Blocks are plain dicts so the planning state stays JSON-serializable.
"""

from __future__ import annotations

import re
from typing import Any

# Number rule shared with the eval (scripts/eval_metrics._numbers): ≥ 2 digits, thousands
# separators dropped, trailing decimal zeros ignored ("4.40" = "4.4").
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_SECTION = re.compile(r"^\s*Slide (\d+):\s*$")
_CHART = re.compile(r"^\s*Chart \(([\w -]+)\):\s*$")
_SERIES = re.compile(r"^\s+(.+?):\s+(.+)$")
_MARKER = re.compile(r"^\s*0\d\s*$")               # "01".."09": list numbering, not data
_YEAR = re.compile(r"'\d\d\b|\b(?:19|20)\d\d\b")   # "Jun '26", "2026": dates, not data
_LONG = 240                                       # split lines longer than this
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9₹\"'(])|\s+-\s+(?=\S)|\s+(?=\d\.\s+[A-Z])|\s{2,}")
_LIST_NO = re.compile(r"^\d\.$")


def norm(n: str) -> str:
    n = n.replace(",", "")
    return n.rstrip("0").rstrip(".") if "." in n else n


def numbers(text: str) -> list[str]:
    """Numbers with ≥ 2 digits, normalized."""
    return [norm(n) for n in _NUMBER.findall(text or "") if len(re.sub(r"\D", "", n)) >= 2]


def data_numbers(text: str) -> list[str]:
    """Numbers a slide must show: without years ('26, 2026) and list numbering (01)."""
    if _MARKER.match(text or ""):
        return []
    # "1.0x" normalizes to "1": a single digit is not required (a slide may show it as "1x")
    return [n for n in numbers(_YEAR.sub(" ", text or "")) if len(re.sub(r"\D", "", n)) >= 2]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.split("|")]


def _is_table_row(line: str) -> bool:
    return line.count("|") >= 1 and len([c for c in _cells(line) if c]) >= 2


def _points(spec: str) -> list[list[str]]:
    """"Jan 1.23, Feb 1.11" → [["Jan", "1.23"], ["Feb", "1.11"]] (value = last token)."""
    out = []
    for part in spec.split(", "):
        label, _, value = part.strip().rpartition(" ")
        out.append([label.strip(), value.strip()] if label else ["", value.strip()])
    return out


def _split_long(line: str) -> list[str]:
    if len(line) <= _LONG:
        return [line]
    parts: list[str] = []
    for p in (p.strip() for p in _SPLIT.split(line) if p and p.strip()):
        if parts and _LIST_NO.match(parts[-1]):  # keep "1." with its item
            parts[-1] += " " + p
        else:
            parts.append(p)
    return parts


def index_brief(brief: str) -> dict[str, Any]:
    """Split the brief into blocks. Returns {"blocks": [...], "has_sections": bool, "numbers": [...]}."""
    lines = (brief or "").replace("\r\n", "\n").split("\n")
    blocks: list[dict[str, Any]] = []
    counters = {"L": 0, "T": 0, "C": 0}
    section: int | None = None

    def add(kind: str, text: str, **extra: Any) -> dict[str, Any]:
        counters[kind] += 1
        block = {"id": f"{kind}{counters[kind]}", "kind": {"L": "text", "T": "table", "C": "chart"}[kind],
                 "section": section, "text": text, "numbers": numbers(text), **extra}
        block["data_numbers"] = [] if block.get("marker") else data_numbers(text)
        blocks.append(block)
        return block

    i = 0
    while i < len(lines):
        line = lines[i]
        m = _SECTION.match(line)
        if m:
            section = int(m.group(1)) - 1  # 0-based, like slide_index
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        m = _CHART.match(line)
        if m:
            series, raw = [], [line.strip()]
            j = i + 1
            while j < len(lines) and _SERIES.match(lines[j]) and lines[j][:1].isspace():
                sm = _SERIES.match(lines[j])
                series.append({"name": sm.group(1).strip(), "points": _points(sm.group(2))})
                raw.append(lines[j].strip())
                j += 1
            add("C", "\n".join(raw), chart_type=m.group(1).strip().lower(), series=series)
            i = j
            continue
        if _is_table_row(line):
            rows = []
            j = i
            while j < len(lines) and _is_table_row(lines[j]):
                rows.append(_cells(lines[j]))
                j += 1
            if len(rows) >= 2:
                has_header = not data_numbers(" ".join(rows[0]))  # "JAN '26 | FEB '26" is still a header
                add("T", "\n".join(lines[i:j]).strip(),
                    header=rows[0] if has_header else [], rows=rows[1:] if has_header else rows)
                i = j
                continue
        for part in _split_long(line.strip()):
            add("L", part, marker=bool(_MARKER.match(part)))
        i += 1

    all_numbers = sorted({n for b in blocks for n in b["numbers"]})
    return {"blocks": blocks, "has_sections": any(b["section"] is not None for b in blocks),
            "numbers": all_numbers}


def by_id(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {b["id"]: b for b in index["blocks"]}


def render_block(block: dict[str, Any]) -> str:
    """How a block is shown to the LLM: id, kind and the verbatim text."""
    if block["kind"] == "table":
        shape = f"{len(block['rows'])} rows × {len(block['header'] or block['rows'][0])} columns"
        body = "\n".join("     " + ln.strip() for ln in block["text"].split("\n"))
        return f"[{block['id']}] table, {shape} (parsed: code fills it)\n{body}"
    if block["kind"] == "chart":
        body = "\n".join("     " + ln for ln in block["text"].split("\n")[1:])
        return f"[{block['id']}] chart ({block['chart_type']}), {len(block['series'])} series (parsed: code fills it)\n{body}"
    return f"[{block['id']}] {block['text']}"


def render_blocks(blocks: list[dict[str, Any]]) -> str:
    out, last = [], object()
    for b in blocks:
        if b["section"] != last and b["section"] is not None:
            out.append(f"\n── Brief section for slide {b['section'] + 1} ──")
        last = b["section"]
        out.append(render_block(b))
    return "\n".join(out).strip()
