"""The closed value sets in src/state.py match the code and knowledge that own them.

state.py is the one source the LLM schemas import (2026-10-12): a value set that
drifts from POM or from the code writing the field would let a bad value through.
"""

import re
from pathlib import Path
from typing import get_args

import pytest
import yaml
from pydantic import ValidationError

from src.agents.planning import plan_checks
from src.agents.generation import repairer
from src.agents.schemas.planner_schema import PlannerComponent
from src.agents.planning.slide_component_planner import _settle_chart_type
from src.agents.planning.style_resolver import theme_names
from src.state import (ChartTypeLiteral, PlanFlagCodeLiteral, RetryTierLiteral, StepLiteral,
                       initial_state)

_SRC = Path(__file__).resolve().parents[2] / "src"


def test_chart_types_are_the_ones_pom_accepts():
    nodes = yaml.safe_load((_SRC / "knowledge" / "core" / "nodes.yaml").read_text(encoding="utf-8"))
    assert set(get_args(ChartTypeLiteral)) == set(nodes["phase_b"]["Chart"]["chartType_values"])


def test_plan_flag_codes_are_the_ones_plan_checks_writes():
    # read from the code that writes plan_flags, so a new flag code fails here until it is listed
    text = (_SRC / "agents" / "planning" / "plan_checks.py").read_text(encoding="utf-8")
    codes = {getattr(plan_checks, name) for name in re.findall(r"\b_flag\(\w+, ([A-Z_]+),", text)}
    thin = {"slide_type": "content", "components": [{"kind": "narrative", "content_data": {"text": "Hi"}}]}
    codes.add(plan_checks.sparse_flag(thin)["code"])
    assert set(get_args(PlanFlagCodeLiteral)) == codes


def test_retry_tiers_are_initial_patch_regenerate():
    assert set(get_args(RetryTierLiteral)) == {0, repairer.PATCH, repairer.REGENERATE}


def test_every_step_name_written_in_src_is_a_known_step():
    written = set()
    for path in _SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        written |= set(re.findall(r'usage_record\([^,]+,\s*"([a-z_]+)"', text))
        written |= set(re.findall(r'\bstep="([a-z_]+)"', text))
        written |= set(re.findall(r'\b_call\("([a-z_]+)"', text))   # src/planning/graph.py
    assert {"slide_component_planner", "storyline"} <= written <= set(get_args(StepLiteral))


def test_planner_answers_only_pom_chart_types():
    with pytest.raises(ValidationError):
        PlannerComponent(component_id="c", kind="chart", chart_type="donut")
    assert PlannerComponent(component_id="c", kind="chart", chart_type="doughnut").chart_type == "doughnut"
    assert PlannerComponent(component_id="t", kind="table").chart_type == ""


def test_chart_type_in_content_data_follows_the_checked_field():
    comp, data = {"component_id": "c", "chart_type": "pie"}, {"chart_type": "bar"}
    _settle_chart_type(comp, data)
    assert comp["chart_type"] == data["chart_type"] == "pie"

    comp, data = {"component_id": "c"}, {"chart_type": "Donut"}
    _settle_chart_type(comp, data)
    assert comp["chart_type"] == data["chart_type"] == "doughnut"

    comp, data = {"component_id": "c"}, {"chart_type": "waterfall"}
    _settle_chart_type(comp, data)
    assert "chart_type" not in comp and "chart_type" not in data


def test_unknown_theme_fails_at_run_start():
    with pytest.raises(ValueError, match="unknown theme"):
        initial_state(run_id="r", raw_request="x", theme_name="corporte-slate")
    for name in ["", *theme_names()]:
        assert initial_state(run_id="r", raw_request="x", theme_name=name)["theme_name"] == name
