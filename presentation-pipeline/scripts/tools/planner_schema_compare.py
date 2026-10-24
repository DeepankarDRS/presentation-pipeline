"""Compare candidate planner output schemas offline (free, no API): strict-mode validity, schema size,
round-trip of every saved plan component, and the output tokens each form costs.

    python -m scripts.tools.planner_schema_compare [--out docs/eval/planner-schema/summary.md]
    python -m scripts.tools.planner_schema_compare --logs output/card-plans/choice-plans/run.log output/card-plans/typed-schema/run.log
        # planner failures per run.log (unreadable content, length-limit hits, failed calls, re-asks, fallbacks)

Candidates (docs/planner-output-schema-research-2026-10-15.md):
  string   today's PlannerSlide: content as JSON inside the `content_data_json` string
  union    PlannerSlideTyped (src/agents/planner_schema_typed.py): one component model per kind (anyOf)
  slots    one PlannerComponent with a nullable typed field per kind; the model fills the one for its kind
  superset one PlannerComponent with one `content` object holding every kind's keys, all nullable

Corpus: the plan components in output/**/slides.json, output/**/runs.json and output/**/plans.json, deduplicated.
Round-trip: saved content_data -> typed content -> content_data, equal after dropping the keys code writes
(per_row, a card's body_source, the planning path's kicker).
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import statistics
from pathlib import Path
from typing import Any, Optional, Union, get_args

import tiktoken
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from src.agents.planner_schema import PlannerComponent, PlannerSlide
from src.agents.planner_schema_typed import (COMPONENT_BY_KIND, CONTENT_BY_KIND, PlannerSlideTyped, _trim,
                                             content_data_of, content_from_data)
from src.state import ChartTypeLiteral, ComponentKindLiteral, OrientationLiteral, SlideTypeLiteral, WeightLiteral
from src.utils.strict_schema import sent_schema, strict_problems

CODE_KEYS = {"per_row", "kicker"}
ENC = tiktoken.get_encoding("o200k_base")


def _tokens(obj: Any) -> int:
    return len(ENC.encode(json.dumps(obj, ensure_ascii=False)))


# ── the two extra candidates ────────────────────────────────────────────────

class _Trimmed(BaseModel):
    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return _trim(super().model_json_schema(*args, **kwargs))


_COMMON = {
    "component_id": (str, ...), "kind": (ComponentKindLiteral, ...), "count": (int, 1),
    "chart_type": (Union[ChartTypeLiteral, None], None), "series_count": (int, 0), "columns": (int, 0),
    "rows": (int, 0), "items": (int, 0), "content_summary": (str, ""),
}
_TAIL = {"orientation": (OrientationLiteral, ""), "design_hint": (str, ""), "weight": (WeightLiteral, "peer")}

SlotComponent = create_model(
    "SlotComponent", __config__=ConfigDict(extra="forbid"), **_COMMON,
    **{kind: (Optional[content], None) for kind, content in CONTENT_BY_KIND.items()}, **_TAIL)


def _superset_content() -> type[BaseModel]:
    fields: dict[str, list[Any]] = collections.defaultdict(list)
    for content in dict.fromkeys(CONTENT_BY_KIND.values()):
        for name, info in content.model_fields.items():
            ann = info.annotation
            for a in (get_args(ann) if type(None) in get_args(ann) else (ann,)):
                if a is not type(None) and a not in fields[name]:
                    fields[name].append(a)
    return create_model("AnyContent", __config__=ConfigDict(extra="forbid"),
                        **{n: (Optional[Union[tuple(a)]], None) for n, a in fields.items()})  # type: ignore[misc]


AnyContent = _superset_content()
SupersetComponent = create_model("SupersetComponent", __config__=ConfigDict(extra="forbid"), **_COMMON,
                                 content=(AnyContent, ...), **_TAIL)


def _slide_model(name: str, comp: type[BaseModel]) -> type[BaseModel]:
    return create_model(name, __base__=_Trimmed, slide_type=(SlideTypeLiteral, ...),
                        components=(list[comp], Field(min_length=1)), layout_hint=(str, ...))  # type: ignore[valid-type]


CANDIDATES: dict[str, type[BaseModel]] = {
    "string": PlannerSlide, "union": PlannerSlideTyped,
    "slots": _slide_model("PlannerSlideSlots", SlotComponent),
    "superset": _slide_model("PlannerSlideSuperset", SupersetComponent),
}


# ── corpus ──────────────────────────────────────────────────────────────────

def _components(obj: Any):
    if isinstance(obj, dict):
        if "kind" in obj and isinstance(obj.get("content_data"), dict):
            yield obj
        for v in obj.values():
            yield from _components(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _components(v)


def corpus(root: str = "output") -> list[dict[str, Any]]:
    seen, out = set(), []
    for pattern in ("slides.json", "runs.json", "plans.json"):
        for f in glob.glob(f"{root}/**/{pattern}", recursive=True):
            try:
                data = json.loads(Path(f).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for c in _components(data):
                if c["kind"] not in CONTENT_BY_KIND:
                    continue
                key = json.dumps([c["kind"], c.get("chart_type"), c["content_data"]], sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    out.append(c)
    return out


def saved_data(c: dict[str, Any]) -> dict[str, Any]:
    """The component's content_data without the keys code writes after the planner."""
    data = {k: v for k, v in c["content_data"].items() if k not in CODE_KEYS}
    if isinstance(data.get("cards"), list):
        data["cards"] = [{k: v for k, v in card.items() if k != "body_source"} if isinstance(card, dict) else card
                         for card in data["cards"]]
    return data


def _common(c: dict[str, Any]) -> dict[str, Any]:
    return {"component_id": c.get("component_id") or "x", "kind": c["kind"], "count": c.get("count") or 1,
            "content_summary": c.get("content_summary", ""), "design_hint": c.get("design_hint", ""),
            "weight": c.get("weight") or "peer"}


def as_union(c: dict[str, Any], content: BaseModel) -> BaseModel:
    model = COMPONENT_BY_KIND[c["kind"]]
    extra = {k: c.get(k) or model.model_fields[k].default for k in model.model_fields
             if k in ("series_count", "columns", "rows", "items", "orientation")}
    if c["kind"] == "chart":
        extra["chart_type"] = c.get("chart_type") or c["content_data"].get("chart_type") or "bar"
    return model(**_common(c), **extra, content=content)


def written_forms(c: dict[str, Any], content: BaseModel) -> dict[str, Any]:
    """What the model writes for this component under each candidate (strict: every key, nulls included)."""
    union = as_union(c, content).model_dump(mode="json")
    old = {f: (c.get(f) if c.get(f) is not None else PlannerComponent.model_fields[f].default)
           for f in PlannerComponent.model_fields if f != "content_data_json"}
    old.update(_common(c))
    old["chart_type"] = c.get("chart_type") or ""
    string = {**old, "content_data_json": json.dumps(content_data_of(as_union(c, content)), ensure_ascii=False)}
    slots = {**{k: v for k, v in old.items() if k in SlotComponent.model_fields},
             **{kind: None for kind in CONTENT_BY_KIND}}
    slots["chart_type"] = old["chart_type"] or None
    slots[c["kind"]] = content.model_dump(mode="json")
    superset = {**{k: v for k, v in slots.items() if k not in CONTENT_BY_KIND},
                "content": AnyContent.model_validate(content.model_dump()).model_dump(mode="json")}
    return {"string": string, "union": union, "slots": slots, "superset": superset}


def run(root: str = "output") -> dict[str, Any]:
    comps = corpus(root)
    by_kind = collections.Counter(c["kind"] for c in comps)
    ok, fails = collections.Counter(), collections.defaultdict(collections.Counter)
    tokens = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    for c in comps:
        data = saved_data(c)
        if not data:
            fails[c["kind"]]["empty (a failed plan, nothing to type)"] += 1
            continue
        try:
            content = content_from_data(c["kind"], data)
        except ValidationError as exc:
            err = exc.errors()[0]
            reason = f"{err['type']} at {'.'.join(str(p) for p in err['loc'][:2])}"
            fails[c["kind"]][reason] += 1
            if len(examples[c["kind"]]) < 3:
                examples[c["kind"]].append(f"{reason}: {json.dumps(data, ensure_ascii=False)[:160]}")
            continue
        back = content_data_of(as_union(c, content))
        back.pop("chart_type", None) if c["kind"] == "chart" and "chart_type" not in data else None
        if back != data:
            fails[c["kind"]]["changed in the round trip"] += 1
            continue
        ok[c["kind"]] += 1
        for name, form in written_forms(c, content).items():
            tokens[name] += _tokens(form)
    schemas = {}
    for name, model in CANDIDATES.items():
        s = sent_schema(model)
        problems, sizes = strict_problems(s)
        schemas[name] = {"problems": problems, "chars": len(json.dumps(s)), "tokens": _tokens(s), **sizes}
        try:
            CANDIDATES[name].model_json_schema()
        except Exception as exc:   # noqa: BLE001 - reported
            schemas[name]["problems"].append(f"pydantic: {exc}")
    return {"components": len(comps), "by_kind": by_kind, "ok": ok, "fails": fails, "examples": examples,
            "tokens": tokens, "schemas": schemas}


def summary(r: dict[str, Any]) -> str:
    n_ok = sum(r["ok"].values())
    lines = ["# Planner output schema: offline comparison", "",
             f"Corpus: {r['components']} distinct saved plan components; {n_ok} round-trip through the typed "
             f"content ({100 * n_ok / max(1, r['components']):.1f}%).", "",
             "| candidate | strict-mode problems | schema chars | schema tokens | object properties | depth | "
             "enum values | output tokens (round-tripped components) |", "|---|---|---|---|---|---|---|---|"]
    base = r["tokens"]["string"] or 1
    for name, s in r["schemas"].items():
        lines.append(f"| {name} | {len(s['problems']) or 0} | {s['chars']:,} | {s['tokens']:,} | {s['properties']} | "
                     f"{s['depth']} | {s['enum_values']} | {r['tokens'][name]:,} ({100 * r['tokens'][name] / base - 100:+.0f}%) |")
    lines += ["", "| kind | components | round-trip | not round-tripped (reason: count) |", "|---|---|---|---|"]
    for kind, n in r["by_kind"].most_common():
        why = "; ".join(f"{k}: {v}" for k, v in r["fails"][kind].most_common())
        lines.append(f"| {kind} | {n} | {r['ok'][kind]} | {why} |")
    for name, s in r["schemas"].items():
        for p in s["problems"]:
            lines.append(f"- {name}: {p}")
    lines += ["", "Examples of components that do not fit the typed content:"]
    for kind, ex in r["examples"].items():
        lines += [f"- {kind}: `{e}`" for e in ex]
    return "\n".join(lines) + "\n"


_CALL = re.compile(r"\[(?P<run>[^\]]+)\].*slide_component_planner: slide (?P<slide>\d+) \S+ tokens_in=(?P<i>\d+) "
                   r"tokens_out=(?P<o>\d+)")
_PATTERNS = {
    "unreadable content fields": r"invalid content_data_json for component",
    "length-limit hits": r"hit the output limit before answering",
    "failed calls (other)": r"attempt \d+ failed:",
    "re-asks": r"slide \d+ planner re-asked because",
    "fallback plans": r"planner failed twice: fallback plan",
    "no content after tries": r"holds no content after",
}


def log_stats(path: str) -> dict[str, Any]:
    """Planner outcome counts in one run.log (card_plan_only / eval_run bundles)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    calls = [m for m in _CALL.finditer(text)]
    outs = sorted(int(m["o"]) for m in calls)
    stats: dict[str, Any] = {"planner calls answered": len(calls)}
    for name, pattern in _PATTERNS.items():
        stats[name] = len(re.findall(pattern, text))
    bad = re.findall(r"\[([^\]]+)\].*invalid content_data_json", text)
    stats["runs with unreadable content"] = len(set(bad))
    if outs:
        stats["output tokens p50 / p90 / max"] = (f"{statistics.median(outs):.0f} / {outs[int(len(outs) * 0.9)]} / "
                                                  f"{outs[-1]}")
        stats["input tokens p50"] = f"{statistics.median(int(m['i']) for m in calls):.0f}"
    return stats


def logs_table(paths: list[str]) -> str:
    rows = [log_stats(p) for p in paths]
    lines = ["| | " + " | ".join(paths) + " |", "|---|" + "---|" * len(paths)]
    for key in rows[0]:
        lines.append(f"| {key} | " + " | ".join(str(r.get(key, "")) for r in rows) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default="output")
    ap.add_argument("--out", default="")
    ap.add_argument("--logs", nargs="+", default=None, help="run.log files to compare instead")
    args = ap.parse_args()
    text = logs_table(args.logs) if args.logs else summary(run(args.root))
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
