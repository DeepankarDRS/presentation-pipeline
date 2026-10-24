"""What the prompts say a diagram node does is checked against POM (2026-10-16).

docs/node-facts-2026-10-16.md. The facts live in knowledge/components/<kind>.yaml
(`facts`, `open_choices`, `refuted`); src/compiler/node_facts.py runs and renders them.

- every syntax / layout fact has probes, and every probe holds when POM compiles it
- attribute lists in the component files and nodes.yaml match POM's own rules
- no prompt or knowledge file states a claim recorded as refuted
- no example fixes a choice the plan makes per slide (direction, layout)
- the planner and generator prompts carry the facts written for them
"""

import re
import shutil
from pathlib import Path

import pytest
import yaml

from src.compiler import node_facts as nf

_ROOT = Path(__file__).resolve().parents[2]
_POM = _ROOT / "src" / "node" / "node_modules" / "@hirokisakabe" / "pom"
_needs_pom = pytest.mark.skipif(not _POM.exists() or not shutil.which("node"), reason="POM/node not installed")

_PROMPTS = sorted((_ROOT / "src" / "prompts").rglob("*.j2"))
_KNOWLEDGE = sorted((_ROOT / "src" / "knowledge").rglob("*.yaml"))
_EXAMPLES = sorted((_ROOT / "src" / "knowledge" / "examples").glob("*.xml"))
_OWN_KEYS = ("facts", "refuted", "open_choices")  # a component file's fact blocks state / quote claims on purpose


# ── the facts themselves ───────────────────────────────────────────────────────

def test_every_diagram_has_facts_with_valid_fields():
    ids = set()
    for kind, f in nf.all_facts():
        assert f["id"].startswith(kind + "."), f["id"]
        assert f["id"] not in ids, f"duplicate fact id {f['id']}"
        ids.add(f["id"])
        assert f["kind"] in nf.FACT_KINDS, f["id"]
        assert f.get("for") and set(f["for"]) <= set(nf.AUDIENCES), f["id"]
        assert str(f.get("text", "")).strip() and f.get("source"), f["id"]
        if f["kind"] in nf.PROBED_KINDS:
            assert f.get("probes"), f"{f['id']}: a {f['kind']} fact needs a probe"
            assert all(p.get("expect") for p in f["probes"]), f["id"]
    for kind in nf.DIAGRAM_TAGS:
        assert nf.facts(kind), f"{kind} has no facts"
        for choice in (nf.component(kind).get("open_choices") or {}).values():
            assert choice["rule"] in ids, f"{kind}: open choice points to unknown fact {choice['rule']}"
        for r in nf.component(kind).get("refuted") or []:
            assert r["fact"] in ids, f"{kind}: refuted claim points to unknown fact {r['fact']}"
            re.compile(r["pattern"])


@pytest.fixture(scope="module")
def probe_results(tmp_path_factory):
    probes, index = [], {}
    for _, f in nf.all_facts():
        for i, p in enumerate(f.get("probes") or []):
            pid = f"{f['id']}#{i}"
            probes.append((pid, nf.probe_slide(p)))
            index[pid] = p
    # a control the checker must fail: a fact that is wrong on purpose
    control = {"xml": '<Pyramid w="1000" h="600"><PyramidLevel label="A"/><PyramidLevel label="B"/></Pyramid>',
               "expect": ["ok", 'near(t("A").h, 600 / 2)']}
    probes.append(("control#0", nf.probe_slide(control)))
    index["control#0"] = control
    return index, nf.run_probes(probes, tmp_path_factory.mktemp("probes"))


@_needs_pom
def test_every_probe_holds_on_pom(probe_results):
    index, results = probe_results
    failed = {pid: (results[pid]["errors"][:1], nf.check_probe(p, results[pid]))
              for pid, p in index.items() if pid != "control#0"}
    failed = {k: v for k, v in failed.items() if v[1]}
    assert not failed, failed


@_needs_pom
def test_a_wrong_fact_fails_its_probe(probe_results):
    index, results = probe_results
    assert nf.check_probe(index["control#0"], results["control#0"]) == ['near(t("A").h, 600 / 2)']


# ── attribute lists come from POM ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def schema(tmp_path_factory):
    return nf.pom_schema(tmp_path_factory.mktemp("schema"))


_TYPES = {"number": "number", "bool": "boolean", "string": "string", "hex": "string", "enum": "enum",
          "object": "object"}


def _component_attrs(kind: str) -> dict[str, dict]:
    data = nf.component(kind)
    return {k[: -len("_attributes")]: v for k, v in data.items() if k.endswith("_attributes")}


@_needs_pom
def test_component_attribute_lists_match_pom(schema):
    assert schema["pomVersion"] == "10.3.0"
    problems = []
    for kind, tag in nf.DIAGRAM_TAGS.items():
        pom = {tag: schema["nodes"][tag]["attributes"], **schema["nodes"][tag]["children"]}
        ours = _component_attrs(kind)
        assert set(ours) == set(pom), f"{kind}: tags {sorted(ours)} vs POM {sorted(pom)}"
        for node, attrs in ours.items():
            box = {"w", "h"} if node == tag else set()
            for name, spec in attrs.items():
                if name in box:
                    continue
                if name not in pom[node]:
                    problems.append(f"{node}.{name}: POM has no such attribute")
                    continue
                p = pom[node][name]
                if _TYPES.get(spec.get("type")) not in (p["type"], None) and p["type"] != "union":
                    problems.append(f"{node}.{name}: type {spec.get('type')} vs POM {p['type']}")
                if p.get("values") and spec.get("values") != p["values"]:
                    problems.append(f"{node}.{name}: values {spec.get('values')} vs POM {p['values']}")
                if bool(spec.get("required")) != p["required"]:
                    problems.append(f"{node}.{name}: required={bool(spec.get('required'))} vs POM {p['required']}")
            missing = set(pom[node]) - set(attrs)
            if missing:
                problems.append(f"{node}: POM attributes not listed {sorted(missing)}")
    assert not problems, problems


@_needs_pom
def test_nodes_yaml_teaches_only_pom_attributes(schema):
    nodes = yaml.safe_load((_ROOT / "src/knowledge/core/nodes.yaml").read_text(encoding="utf-8"))
    flat = {name: meta for section in nodes.values() if isinstance(section, dict)
            for name, meta in section.items() if isinstance(meta, dict)}
    problems = []
    for tag, spec in schema["nodes"].items():
        for node, pom in {tag: spec["attributes"], **spec["children"]}.items():
            meta = flat[node]
            listed = set(meta.get("node_attributes") or []) - ({"w", "h"} if node == tag else set())
            if listed - set(pom):
                problems.append(f"{node}: not in POM {sorted(listed - set(pom))}")
            if set(pom) - listed:
                problems.append(f"{node}: POM attributes not taught {sorted(set(pom) - listed)}")
            for key, value in meta.items():
                if key.endswith("_values") and value != pom[key[: -len("_values")]].get("values"):
                    problems.append(f"{node}.{key}: {value} vs POM {pom[key[: -len('_values')]].get('values')}")
            if node != tag and sorted(meta.get("required") or []) != sorted(k for k, a in pom.items() if a["required"]):
                problems.append(f"{node}: required {meta.get('required')} vs POM")
    assert not problems, problems


# ── refuted claims stay gone ───────────────────────────────────────────────────

def _texts():
    """(where, text) for every prompt, knowledge value and example file the LLMs may see."""
    for p in _PROMPTS + _EXAMPLES:
        yield str(p.relative_to(_ROOT)), p.read_text(encoding="utf-8")
    for p in _KNOWLEDGE:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        own = p.parent.name == "components"
        for key, value in data.items() if isinstance(data, dict) else []:
            if own and key in _OWN_KEYS:
                continue
            yield f"{p.relative_to(_ROOT)}:{key}", yaml.safe_dump(value, allow_unicode=True, width=10_000) \
                if not isinstance(value, str) else value


def test_no_refuted_claim_is_taught():
    refuted = [(kind, r) for kind in nf.DIAGRAM_TAGS for r in nf.component(kind).get("refuted") or []]
    hits = [f"{where}: {r['pattern']!r} (see {r['fact']})"
            for where, text in _texts() for kind, r in refuted if re.search(r["pattern"], text)]
    assert not hits, hits


# ── examples show the choices the plan makes ───────────────────────────────────

def test_examples_do_not_fix_an_open_choice():
    out = []
    for where, text in _texts():
        out += nf.open_choice_violations(text, where)
    for kind in nf.DIAGRAM_TAGS:  # the component's own example too
        structure = nf.component(kind).get("structure")
        if structure:
            out += nf.open_choice_violations(structure, f"{kind}.yaml:structure")
    assert not out, out


def test_flow_examples_connect_each_node_to_the_next():
    out = []
    for where, text in _texts():
        out += nf.flow_link_violations(text, where)
    for kind in nf.DIAGRAM_TAGS:
        out += nf.flow_link_violations(str(nf.component(kind).get("structure") or ""), f"{kind}.yaml:structure")
    assert not out, out
    back = ('<Flow><FlowNode id="a" shape="flowChartProcess" text="A"/><FlowNode id="b" shape="flowChartProcess" text="B"/>'
            '<FlowConnection from="a" to="b"/><FlowConnection from="b" to="a"/></Flow>')
    assert nf.flow_link_violations(back, "x") == ["x:1: FlowConnection b -> a is not to the next node (flow.back_link)"]


def test_lint_catches_a_fixed_choice():
    planner = 'For flow:\n  { "direction": "horizontal", "flow_steps": [] }'
    xml = '<Flow direction="horizontal" h="max"><FlowNode id="a" shape="flowChartProcess" text="A"/></Flow>'
    assert nf.open_choice_violations(planner, "p")
    assert nf.open_choice_violations(xml, "x")
    assert not nf.open_choice_violations('For flow:\n  { "direction": "horizontal | vertical" }', "p")
    assert not nf.open_choice_violations("# direction: horizontal | vertical\n" + xml, "x")


# ── both prompts render the facts ──────────────────────────────────────────────

def test_planner_prompt_renders_planner_facts():
    from src.agents.planning.slide_component_planner import _jinja_env
    text = " ".join(_jinja_env.get_template("system.j2").render(
        content_field="content_data_json").split())
    for kind in nf.DIAGRAM_TAGS:
        assert nf.facts_text(kind, "planner") in text, kind


def test_generator_notes_render_generator_facts():
    from src.agents.generation.context_builder import _select_notes
    notes = _select_notes(list(nf.DIAGRAM_TAGS), {}, {}, {k: nf.component(k) for k in nf.DIAGRAM_TAGS},
                          {"name": ""}, has_grammar=True)
    joined = " ".join(" ".join(n.split()) for n in notes)
    for kind in nf.DIAGRAM_TAGS:
        for f in nf.facts(kind, "generator"):
            assert " ".join(f["text"].split()) in joined, f["id"]
