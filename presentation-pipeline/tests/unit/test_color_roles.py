"""C — colour carries meaning, the same on every slide (Genspark: clay = leak, teal = fix)."""

from src.agents.context_builder import _render_house_style
from src.agents.hint_capabilities import planner_capabilities_section, visual_intent_techniques
from src.agents.slide_component_planner import _jinja_env


def test_generator_sees_colour_roles_and_no_deltas_only_rule():
    hs = _render_house_style()
    assert "COLOR ROLES" in hs and "$negative = losses, leaks" in hs and "$positive = wins, fixes" in hs
    assert "only on deltas" not in hs


def test_planner_states_the_roles_for_its_hints():
    p = _jinja_env.get_template("system.j2").render(hint_capabilities=planner_capabilities_section())
    assert "Colour roles are fixed for the whole deck" in p
    assert "losses in negative, the fixes in positive" in p


def test_sentiment_technique_names_the_roles():
    line = next(l for l in visual_intent_techniques(["table"]).splitlines() if l.startswith("- sentiment"))
    assert "$negative = losses, leaks, risks" in line and "same colour on every slide" in line
