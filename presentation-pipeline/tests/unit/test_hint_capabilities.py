"""Design-hint capabilities: planner and generator share one per-kind treatment list."""

import re
import typing
import xml.etree.ElementTree as ET

from jinja2 import Environment, FileSystemLoader

from src.agents.context_builder import build_contract
from src.agents.hint_capabilities import (
    hint_scopes, load_capabilities, planner_capabilities_section, visual_intent_techniques,
)
from src.agents.planner_schema import ComponentKindLiteral, PlannerComponent
from src.agents.slide_component_planner import _PROMPTS_DIR as _PLANNER_PROMPTS
from src.agents.style_resolver import DEFAULT_THEME
from src.compiler.content_model import find_violations

_CAPS = load_capabilities()
_KINDS = _CAPS["kinds"]
_TREATMENTS = _CAPS["treatments"]


def test_every_planner_kind_has_capabilities():
    assert set(typing.get_args(ComponentKindLiteral)) == set(_KINDS)


def test_treatment_references_are_consistent():
    used = {t for meta in _KINDS.values() for t in meta["treatments"]}
    assert used <= set(_TREATMENTS), used - set(_TREATMENTS)
    assert set(_TREATMENTS) <= used, set(_TREATMENTS) - used  # no dead treatments
    for name, meta in _TREATMENTS.items():
        assert meta.get("intent") and meta.get("technique"), name


def test_no_layout_enrichment_offered_for_text_only_kinds():
    """Tables and lists never get a treatment that nests nodes in their cells/items."""
    for kind in ("table", "chart", "timeline", "flow", "tree", "matrix", "process_arrow", "pyramid"):
        assert not {"icon_rows", "icon_tiles", "sparkline", "status_dots"} & set(_KINDS[kind]["treatments"]), kind
    assert "Td" in _KINDS["table"]["never"] and "Li" in _KINDS["bullet_list"]["never"]


def test_technique_snippets_respect_the_content_model():
    """Every complete XML example in a technique must itself be validly nested."""
    for name, meta in _TREATMENTS.items():
        for frag in re.findall(r"<(HStack|VStack|Text|Mark)\b.*?</\1>", meta["technique"]):
            snippet = re.search(rf"<{frag}\b.*?</{frag}>", meta["technique"]).group(0)
            xml = f'<Slide><VStack w="1280" h="720">{snippet}</VStack></Slide>'
            ET.fromstring(xml)
            assert find_violations(xml) == [], (name, snippet)


def test_generator_table_only_has_this_slides_treatments():
    table_only = visual_intent_techniques(["table"])
    assert "cell_fill" in table_only and "header_icon" in table_only
    for absent in ("icon_rows", "icon_tiles", "sparkline", "status_dots"):
        assert absent not in table_only
    assert "sparkline" in visual_intent_techniques(["kpi_row"])
    assert visual_intent_techniques(["unknown_kind"]) == ""


def test_hint_scopes():
    scopes = hint_scopes(["table", "kpi_row", "table", "unknown_kind"])
    assert list(scopes) == ["table", "kpi_row"]
    assert "never:" in scopes["table"] and "Td" in scopes["table"]
    assert "never:" not in scopes["kpi_row"]


def test_planner_prompt_renders_capabilities():
    env = Environment(loader=FileSystemLoader(str(_PLANNER_PROMPTS)), trim_blocks=True, lstrip_blocks=True)
    prompt = env.get_template("system.j2").render(hint_capabilities=planner_capabilities_section())
    assert "- **table**:" in prompt and "NEVER: icons, logos" in prompt
    assert "NO brand or company logos" in prompt
    assert "using nested VStack/HStack" not in prompt  # old unscoped enrichment claim
    assert "{{" not in prompt


def test_planner_schema_description_is_scoped():
    desc = PlannerComponent.model_fields["design_hint"].description
    assert "inside table cells or list items" in desc
    assert "intra-component" not in desc


def test_generator_user_prompt_shows_scope_under_component():
    env = Environment(loader=FileSystemLoader("src/prompts/generator"), trim_blocks=True, lstrip_blocks=True)
    comp = {"kind": "table", "component_id": "roas", "count": 1,
            "design_hint": "color ROAS below 1x in negative", "content_data": {}}
    contract = build_contract({"components": [comp], "slide_type": "data"}, DEFAULT_THEME)
    prompt = env.get_template("user.j2").render(components=[comp], hint_scopes=contract["hint_scopes"])
    # header on its own line (trim_blocks used to glue the hint onto it)
    assert "- table [roas]\n  visual-intent: color ROAS below 1x in negative\n  scope: treatments: emphasis" in prompt
    assert "never: icons, logos" in prompt


def test_generator_user_prompt_hero_table_never_grows_its_card():
    # eval phase-1: the planner marked tables hero and the generator put grow on the table card.
    env = Environment(loader=FileSystemLoader("src/prompts/generator"), trim_blocks=True, lstrip_blocks=True)
    table = {"kind": "table", "component_id": "t", "count": 1, "weight": "hero", "content_data": {}}
    chart = {"kind": "chart", "component_id": "c", "count": 1, "weight": "hero", "content_data": {}}
    prompt = env.get_template("user.j2").render(components=[table, chart])
    assert prompt.count("never grow on its card") == 1
    assert "- table [t]\n  height-weight: hero (see SIZING BY WEIGHT in layout grammar); a table's weight is rows" in prompt


def test_generator_system_prompt_has_icon_vocabulary_and_scoped_translation():
    env = Environment(loader=FileSystemLoader("src/prompts/generator"), trim_blocks=True, lstrip_blocks=True)
    contract = build_contract({"components": [{"kind": "table"}], "slide_type": "data"}, DEFAULT_THEME)
    prompt = env.get_template("system.j2").render(**contract)
    assert "Icon names (unknown names are removed; no brand logos): trending-up" in prompt
    assert "- cell_fill (" in prompt and "- sparkline (" not in prompt
    assert "<!-- archetype: X -->" in prompt  # deck_nodes.py parses this marker
