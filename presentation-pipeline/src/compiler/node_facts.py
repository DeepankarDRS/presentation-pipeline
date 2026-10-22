"""Verified facts about what each POM node draws — one source for both prompts (2026-10-16).

Each diagram component file (knowledge/components/<kind>.yaml) carries a ``facts:`` list.
A fact is one sentence a prompt may say about the node, tagged with its kind
(syntax / layout / capacity / advice), who reads it (planner / generator) and, for every
syntax and layout fact, probes: tiny slides POM compiles, each with assertions on what it
drew. ``tests/unit/test_node_facts.py`` compiles every probe (one node spawn), so a wrong
fact or a POM upgrade that changes a behaviour fails a test instead of showing up in a deck.

The same files carry ``open_choices`` (attributes the plan chooses per slide, such as a
diagram's direction: examples must show every value, never fix one) and ``refuted``
(claims found wrong, as patterns no prompt or knowledge file may state again).

Probe assertions are Python expressions over:
  ok, errors (joined text), warnings (codes)
  box            the diagram's own box (positioned tree): .x .y .w .h .r .b .cx .cy
  t("A")         the drawn shape whose text is "A" (same fields, + .font px, .geom, .pad: left + right
                 text inset px, the OOXML default 0.1 in each side where bodyPr sets none)
  shapes, fills  every drawn shape / the textless filled ones (chevrons, bands, dots)
  lines          textless zero-thickness shapes (connectors, axes)
  near(a, b, tol=1.5), same(values, tol=1.5), extent(shapes) -> box of their union
"""

from __future__ import annotations

import functools
import json
import re
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import yaml

_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE = _ROOT / "src" / "knowledge" / "components"
_RUNNER = _ROOT / "src" / "node" / "probe-facts.js"

# component kind -> POM tag; the kinds with a facts block (2026-10-16: the six diagrams)
DIAGRAM_TAGS = {
    "flow": "Flow", "process_arrow": "ProcessArrow", "timeline": "Timeline",
    "tree": "Tree", "matrix": "Matrix", "pyramid": "Pyramid",
}
FACT_KINDS = ("syntax", "layout", "capacity", "advice")
AUDIENCES = ("planner", "generator")
PROBED_KINDS = ("syntax", "layout")  # a claim about POM must be shown by POM

_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
_EMU = 9525
_DEFAULT_INSET = 91440  # EMU: OOXML bodyPr lIns / rIns when not written (0.1 in)
_DEFAULT_INSET_V = 45720  # EMU: tIns / bIns when not written (0.05 in)
_PROBE_ROOT = '<VStack w="1280" h="720" padding="40" alignItems="{align}">'


def component_file(kind: str) -> Path:
    return _KNOWLEDGE / f"{kind.replace('_', '-')}.yaml"


@functools.lru_cache(maxsize=None)
def component(kind: str) -> dict[str, Any]:
    return yaml.safe_load(component_file(kind).read_text(encoding="utf-8")) or {}


def facts(kind: str, audience: str | None = None) -> list[dict[str, Any]]:
    out = component(kind).get("facts") or []
    return [f for f in out if audience is None or audience in (f.get("for") or [])]


def facts_text(kind: str, audience: str) -> str:
    """The verified sentences one reader gets about a component, as one paragraph."""
    return " ".join(" ".join(str(f["text"]).split()) for f in facts(kind, audience))


def all_facts() -> list[tuple[str, dict[str, Any]]]:
    return [(kind, f) for kind in DIAGRAM_TAGS for f in facts(kind)]


def probe_slide(probe: dict[str, Any]) -> str:
    xml = str(probe["xml"]).strip()
    if xml.startswith("<Slide"):
        return xml
    return f"<Slide>{_PROBE_ROOT.format(align=probe.get('align', 'start'))}{xml}</VStack></Slide>"


# ── running the probes ─────────────────────────────────────────────────────────

def run_probes(probes: list[tuple[str, str]], workdir: Path) -> dict[str, dict[str, Any]]:
    """Compile [(id, slide xml)] in one node spawn; id -> raw result."""
    workdir.mkdir(parents=True, exist_ok=True)
    src = workdir / "probes.json"
    src.write_text(json.dumps([{"id": i, "xml": x} for i, x in probes]), encoding="utf-8")
    subprocess.run(["node", str(_RUNNER), str(src), str(workdir)], check=True,
                   capture_output=True, encoding="utf-8", errors="replace", cwd=_RUNNER.parent)
    res = json.loads((workdir / "probe-results.json").read_text(encoding="utf-8"))
    return {r["id"]: r for r in res["results"]}


def pom_schema(workdir: Path) -> dict[str, Any]:
    """POM's own attribute rules for the diagram tags (probe-facts.js --schema)."""
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "pom-schema.json"
    subprocess.run(["node", str(_RUNNER), "--schema", str(out)], check=True,
                   capture_output=True, encoding="utf-8", errors="replace", cwd=_RUNNER.parent)
    return json.loads(out.read_text(encoding="utf-8"))


# ── what was drawn ─────────────────────────────────────────────────────────────

@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    text: str = ""
    font: float | None = None
    geom: str = ""
    pad: float = 0.0
    vpad: float = 0.0     # top + bottom text inset px (OOXML default 0.05 in each)
    bold: bool = False
    family: str = ""      # the first run's latin typeface ("" = the theme font)
    filled: bool = False  # spPr has a fill (a visible shape, not a bare text box)
    anchor: str = "t"     # bodyPr anchor: t / ctr / b
    algn: str = "l"       # the first paragraph's alignment: l / ctr / r

    @property
    def r(self) -> float:
        return self.x + self.w

    @property
    def b(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def drawn_shapes(pptx: str | Path) -> list[Box]:
    with zipfile.ZipFile(pptx) as z:
        root = ET.fromstring(z.read("ppt/slides/slide1.xml"))
    out = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] not in ("sp", "cxnSp"):
            continue
        off, ext = el.find(".//a:off", _NS), el.find(".//a:ext", _NS)
        if off is None or ext is None:
            continue
        text = "".join(t.text or "" for t in el.iter(f"{{{_NS['a']}}}t")).strip()
        sz = next((r.get("sz") for r in el.iter(f"{{{_NS['a']}}}rPr") if r.get("sz")), None)
        prst = el.find(".//a:prstGeom", _NS)
        body = el.find(".//a:bodyPr", _NS)
        ins = [int(body.get(k, _DEFAULT_INSET)) if body is not None else _DEFAULT_INSET for k in ("lIns", "rIns")]
        vins = [int(body.get(k, _DEFAULT_INSET_V)) if body is not None else _DEFAULT_INSET_V for k in ("tIns", "bIns")]
        rpr = next((r for r in el.iter(f"{{{_NS['a']}}}rPr")), None)
        ppr = el.find(".//a:pPr", _NS)
        sppr = next((c for c in el if c.tag.endswith("}spPr")), None)
        latin = rpr.find("a:latin", _NS) if rpr is not None else None
        out.append(Box(int(off.get("x")) / _EMU, int(off.get("y")) / _EMU,
                       int(ext.get("cx")) / _EMU, int(ext.get("cy")) / _EMU, text,
                       round(int(sz) / 100 / 0.75, 2) if sz else None,
                       prst.get("prst") if prst is not None else
                       "cust" if el.find(".//a:custGeom", _NS) is not None else "", sum(ins) / _EMU,
                       sum(vins) / _EMU, rpr is not None and rpr.get("b") in ("1", "true"),
                       latin.get("typeface", "") if latin is not None else "",
                       sppr is not None and any(sppr.find(f"a:{f}", _NS) is not None for f in ("solidFill", "gradFill")),
                       body.get("anchor", "t") if body is not None else "t",
                       ppr.get("algn", "l") if ppr is not None else "l"))
    return out


def _diagram_box(geometry: dict[str, Any] | None) -> Box | None:
    stack = [geometry] if geometry else []
    while stack:
        n = stack.pop(0)
        if n["type"] not in ("vstack", "hstack", "layer"):
            return Box(n["x"], n["y"], n["w"], n["h"])
        stack.extend(n.get("children", []))
    return None


def _near(a: float, b: float, tol: float = 1.5) -> bool:
    return abs(a - b) <= tol


def _same(values: list[float], tol: float = 1.5) -> bool:
    return bool(values) and max(values) - min(values) <= tol


def _extent(boxes: list[Box]) -> Box:
    x0, y0 = min(b.x for b in boxes), min(b.y for b in boxes)
    return Box(x0, y0, max(b.r for b in boxes) - x0, max(b.b for b in boxes) - y0)


def check_probe(probe: dict[str, Any], result: dict[str, Any]) -> list[str]:
    """Failed assertions of one probe (empty = the fact holds)."""
    shapes = drawn_shapes(result["pptx"]) if result.get("pptx") else []

    def t(text: str) -> Box:
        hit = [s for s in shapes if s.text == text]
        if not hit:
            raise LookupError(f"no drawn shape with text {text!r} (drawn: {[s.text for s in shapes if s.text]})")
        return hit[0]

    ns = {
        "__builtins__": {}, "any": any, "all": all, "range": range,
        "ok": result["status"] == "success", "errors": " | ".join(result.get("errors") or []),
        "warnings": result.get("warnings") or [], "box": _diagram_box(result.get("geometry")),
        "t": t, "shapes": shapes, "fills": [s for s in shapes if not s.text and s.w > 0 and s.h > 0],
        "lines": [s for s in shapes if not s.text and (s.w == 0 or s.h == 0)],
        "near": _near, "same": _same, "extent": _extent, "abs": abs, "min": min, "max": max,
        "len": len, "round": round,
    }
    failed = []
    for expr in probe.get("expect") or []:
        try:
            if not eval(expr, ns):  # noqa: S307 — repo-owned test data
                failed.append(expr)
        except Exception as e:  # noqa: BLE001 — report the assertion, not crash the run
            failed.append(f"{expr}  ({type(e).__name__}: {e})")
    return failed


# ── the lint over examples ─────────────────────────────────────────────────────

def open_choice_violations(text: str, where: str) -> list[str]:
    """Examples in *text* that fix an open choice instead of showing its values.

    JSON example (planner): ``"direction": "horizontal"`` must read
    ``"direction": "horizontal | vertical"``. XML example (generator, repairer):
    ``<Flow direction="horizontal">`` is fine only when the same block names every value
    (``direction: horizontal | vertical``, in a comment) — it then reads as one of them.
    """
    out = []
    for kind, tag in DIAGRAM_TAGS.items():
        for attr, spec in (component(kind).get("open_choices") or {}).items():
            values = [str(v) for v in spec["values"]]
            one = "(?:" + "|".join(map(re.escape, values)) + ")"
            alts = re.compile(rf"{attr}\W+{one}(?:\s*\|\s*{one})+")  # "direction: horizontal | vertical"
            key = spec.get("plan_key", attr)
            for m in re.finditer(rf'"{key}"\s*:\s*"([^"]*)"', text):
                if set(v.strip() for v in m.group(1).split("|")) != set(values):
                    line = text.count("\n", 0, m.start()) + 1
                    if _json_kind(text, m.start()) in (kind, None):
                        out.append(f"{where}:{line}: {key} example fixes {m.group(1)!r} (show {' | '.join(values)})")
            for m in re.finditer(rf'<{tag}\b[^>]*\s{attr}="([^"]*)"', text):
                if not alts.search(text):
                    line = text.count("\n", 0, m.start()) + 1
                    out.append(f"{where}:{line}: <{tag} {attr}=\"{m.group(1)}\"> with no '{attr}: "
                               f"{' | '.join(values)}' beside it ({spec['rule']})")
    return out


def _json_kind(text: str, pos: int) -> str | None:
    """Which component a planner JSON example belongs to: the nearest 'For <kind>' above it."""
    heads = list(re.finditer(r"^For (\w+)", text[:pos], re.M))
    return heads[-1].group(1) if heads else None


def flow_link_violations(text: str, where: str) -> list[str]:
    """Flow examples whose connections skip a node or go back (facts flow.back_link).

    Every node is drawn in one line in document order, so only a connection from a node to
    the next one is drawn between them; any other is drawn through nodes.
    """
    out = []
    for flow in re.finditer(r"<Flow\b.*?</Flow>", text, re.S):
        ids = re.findall(r'<FlowNode\b[^>]*\bid="([^"]+)"', flow.group(0))
        order = {node: i for i, node in enumerate(ids)}
        for a, b in re.findall(r'<FlowConnection\b[^>]*\bfrom="([^"]+)"[^>]*\bto="([^"]+)"', flow.group(0)):
            if a in order and b in order and order[b] != order[a] + 1:
                line = text.count("\n", 0, flow.start()) + 1
                out.append(f"{where}:{line}: FlowConnection {a} -> {b} is not to the next node (flow.back_link)")
    return out
