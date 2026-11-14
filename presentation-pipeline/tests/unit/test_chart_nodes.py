"""Chart composition node (docs/composition-convention-spec.md §8), POM_NODES=chart: every composition word, every
alias, every requires / fallback, the focus rule, the number format, attribute handling and NODE_* codes, the
generator / context / validator hooks, and the pptx-post data labels on a real compile (LLM-free)."""

import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from src.compiler.nodes import charts as C
from src.compiler.nodes import spec

ROAS = {"component_id": "roas", "kind": "chart", "chart_type": "bar",
        "design_hint": "accent the Generic search bar as the largest budget pool",
        "content_data": {"chart_title": "ROAS by campaign class", "chart_type": "bar",
                         "chart_labels": ["Generic search", "Category / PLA", "Brand", "Competitor"],
                         "chart_values": ["0.29x", "0.80x", "0.99x", "0.15x"]}}
TREND = {"component_id": "rev", "kind": "chart", "content_data": {
    "chart_type": "line", "chart_labels": ["Q1", "Q2", "Q3", "Q4"],
    "chart_series": [{"name": "Actual", "values": [1, 2, 3, 4]}, {"name": "Plan", "values": [1, 2, 2, 3]}]}}
PIE = {"component_id": "mix", "kind": "chart", "content_data": {
    "chart_type": "pie", "chart_labels": ["A", "B", "C"], "chart_values": [50, 30, 20]}}
MANY = {"component_id": "many", "kind": "chart", "content_data": {
    "chart_type": "bar", "chart_labels": [f"P{i}" for i in range(9)], "chart_values": list(range(9))}}


def plan(*comps, title="Generic search takes the most budget"):
    return {"slide_title": title, "components": [{"component_id": "title", "kind": "title", "count": 1},
                                                 *(dict(c, count=1) for c in comps)]}


def run(tag, *comps, **kw):
    return C.expand(f'<Slide><VStack w="1280" h="720">{tag}</VStack></Slide>', plan(*(comps or (ROAS,)), **kw))


def codes(res):
    return [i["code"] for i in res["issues"]]


def colors(xml):
    m = re.search(r'chartColors="([^"]*)"', xml)
    return json.loads(m.group(1).replace("&quot;", '"'))


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "chart")


# ── switch ────────────────────────────────────────────────────────────────────

def test_switch_is_a_comma_list(monkeypatch):
    monkeypatch.setenv("POM_NODES", "table, chart")
    assert C.on() and spec.nodes_on("table") and not spec.nodes_on("timeline")
    monkeypatch.setenv("POM_NODES", "")
    assert not C.on()


# ── compositions ──────────────────────────────────────────────────────────────

def test_native_default_one_hue_focus_from_headline():
    res = run('<Chart ref="roas" />')
    assert res["ok"] and codes(res) == [] and res["components"]["roas"] == {"composition": "native", "focus": 0}
    x = res["xml"]
    assert colors(x) == ["$accent", "$neutral", "$neutral", "$neutral"]
    assert 'backgroundColor="$chartSurface"' in x and ">ROAS by campaign class</Text>" in x
    assert 'value="0.29"' in x and "chart-post" not in x and "ref=" not in x


def test_native_labelled_writes_the_post_mark_with_the_unit():
    x = run('<Chart ref="roas" variant="native labelled" />')["xml"]
    mark = json.loads(re.search(r"<!-- chart-post (\{.*?\}) -->", x).group(1))
    assert mark == {"labels": True, "fmt": '0.00"x"', "ink": "$chartInk", "bold": "true"}
    assert x.index("chart-post") < x.index("<Chart")


def test_rows_values_verbatim_with_value_ids_and_peer_ids():
    res = run('<Chart ref="roas" variant="rows" />')
    x = res["xml"]
    assert res["components"]["roas"]["composition"] == "rows" and "<Chart" not in x
    for i, v in enumerate(["0.29x", "0.80x", "0.99x", "0.15x"]):
        assert re.search(rf'id="kpiv-roas-{i}"[^>]*>{re.escape(v)}</Text>', x)
        assert f'id="card-roas-{i}"' in x
    assert re.search(r'id="card-roasx-\d+"', x)                    # inner boxes: one peer group (C11)
    assert 'w="29%"' in x and 'w="100%"' in x                       # bar length from the parsed value
    assert re.search(r'id="kpiv-roas-0"[^>]*color="\$accentText"', x)   # the emphasis row


def test_one_series_line_is_one_colour_never_a_colour_per_point():
    """A line takes one colour per series: a per-point list drew the whole line in its first entry, $neutral."""
    for kind in C.SERIES_COLOUR_KINDS:
        comp = {"component_id": "rev", "kind": "chart", "content_data": {
            "chart_type": kind, "chart_labels": ["Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26"],
            "chart_values": [2.6, 2.9, 3.3, 3.6]}}
        res = run('<Chart ref="rev" />', comp, title="Revenue rose every quarter")
        assert colors(res["xml"]) == ["$accent"] * 4 and res["components"]["rev"]["focus"] is None, kind
    bars = {"component_id": "rev", "kind": "chart", "content_data": {
        "chart_type": "bar", "chart_labels": ["Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26"],
        "chart_values": [2.6, 2.9, 3.3, 3.6]}}
    assert colors(run('<Chart ref="rev" />', bars, title="Revenue rose every quarter")["xml"])[-1] == "$accent"


def test_no_focus_draws_every_bar_in_the_emphasis_colour():
    comp = dict(ROAS, design_hint="")
    x = run('<Chart ref="roas" />', comp, title="Return by class")["xml"]
    assert colors(x) == ["$accent"] * 4
    x = run('<Chart ref="roas" variant="rows" />', comp, title="Return by class")["xml"]
    assert 'fill.color="$neutral"' not in x and "$accentText" not in x


def test_several_series_and_pie_take_chart_tokens():
    assert colors(run('<Chart ref="rev" />', TREND)["xml"]) == ["$chart1", "$chart2"]
    assert colors(run('<Chart ref="mix" />', PIE)["xml"]) == ["$chart1", "$chart2", "$chart3"]


# ── requires / fallback, aliases, unknown ─────────────────────────────────────

@pytest.mark.parametrize("comp,variant,used", [
    (TREND, "native labelled", "native"), (TREND, "rows", "native"),    # one_series
    (PIE, "native labelled", "native"), (PIE, "rows", "rows"),          # chart_is_bar (rows takes any type)
    (MANY, "native labelled", "native"), (MANY, "rows", "native"),      # count_le_8
])
def test_requires_fall_back(comp, variant, used):
    res = run(f'<Chart ref="{comp["component_id"]}" variant="{variant}" />', comp)
    assert res["components"][comp["component_id"]]["composition"] == used
    assert ("NODE_VARIANT_UNMET" in codes(res)) == (used != variant)


@pytest.mark.parametrize("old,new", [("plain", "native"), ("labelled", "native labelled"),
                                     ("focus_label", "native labelled"), ("horizontal", "native")])
def test_aliases(old, new):
    res = run(f'<Chart ref="roas" variant="{old}" />')
    assert res["components"]["roas"]["composition"] == new and codes(res) == ["NODE_ATTR_ALIAS"]
    assert ('"barDir": "bar"' in res["xml"]) == (old == "horizontal")


def test_unknown_variant_and_spaces():
    res = run('<Chart ref="roas" variant="donut" />')
    assert res["components"]["roas"]["composition"] == "native" and codes(res) == ["NODE_VARIANT_UNKNOWN"]
    assert run('<Chart ref="roas" variant="native   labelled" />')["components"]["roas"]["composition"] == "native labelled"


def test_direction_turns_only_bars():
    assert '"barDir": "bar"' in run('<Chart ref="roas" direction="horizontal" />')["xml"]
    assert "chart-post" not in run('<Chart ref="rev" direction="horizontal" />', TREND)["xml"]


# ── attributes ────────────────────────────────────────────────────────────────

def test_box_and_parts_layer_over_the_look_but_keep_the_emphasis():
    x = run('<Chart ref="roas" variant="rows" grow="2" backgroundColor="$surfaceAlt" bar.fill.color="$border" '
            'value.color="$textMuted" />')["xml"]
    outer = re.search(r"<VStack w=\"1280\" h=\"720\"><VStack([^>]*)>", x).group(1)
    assert 'grow="2"' in outer and 'backgroundColor="$surfaceAlt"' in outer
    assert x.count('fill.color="$border"') == 3 and x.count('fill.color="$accent"') == 1
    assert re.search(r'id="kpiv-roas-0"[^>]*color="\$accentText"', x)
    assert re.search(r'id="kpiv-roas-1"[^>]*color="\$textMuted"', x)
    native = run('<Chart ref="roas" bar.fill.color="$border" />')["xml"]
    assert colors(native) == ["$accent", "$border", "$border", "$border"]


def test_a_chart_without_size_grows():
    assert 'grow="1"' in re.search(r'<VStack w="1280" h="720"><VStack([^>]*)>', run('<Chart ref="roas" />')["xml"]).group(1)
    assert 'grow="1"' not in re.search(r'<VStack w="1280" h="720"><VStack([^>]*)>',
                                       run('<Chart ref="roas" h="300" />')["xml"]).group(1)
    outer = re.search(r'<VStack w="1280" h="720"><VStack([^>]*)>', run('<Chart ref="roas" minH="180" />')["xml"]).group(1)
    assert 'grow="1"' in outer and 'minH="180"' in outer   # minH is a floor, not a size


@pytest.mark.parametrize("attr,code", [
    ('color="#FF0000"', "LITERAL_COLOR"), ('bar.fill.color="red"', "NODE_ATTR_DROPPED"),
    ('title.fontSize="30"', "NODE_ATTR_DROPPED"), ('chartColors="[]"', "NODE_ATTR_DROPPED"),
    ('chartType="pie"', "NODE_ATTR_DROPPED"), ('position="absolute"', "NODE_ATTR_DROPPED"),
    ('bar.foo="1"', "NODE_ATTR_UNKNOWN"), ('wiggle="1"', "NODE_ATTR_UNKNOWN"),
])
def test_attribute_codes(attr, code):
    res = run(f'<Chart ref="roas" {attr} />')
    assert codes(res) == [code]
    assert res["ok"] == (code != "NODE_ATTR_UNKNOWN")


def test_show_legend_is_the_charts_own():
    x = run('<Chart ref="roas" showLegend="true" />')["xml"]
    assert re.search(r'<Chart [^>]*showLegend="true"', x)


def test_children_are_dropped():
    res = run('<Chart ref="roas"><ChartSeries name="x"><ChartDataPoint label="a" value="9" /></ChartSeries></Chart>')
    assert codes(res) == ["NODE_ATTR_DROPPED"] and 'value="9"' not in res["xml"]


# ── refs ──────────────────────────────────────────────────────────────────────

def test_ref_errors():
    assert codes(run('<Chart ref="nope" />')) == ["NODE_REF_UNKNOWN"]
    res = run('<Chart ref="roas" /><Chart ref="roas" />')
    assert codes(res) == ["NODE_REF_DUPLICATE"] and not res["ok"]
    bad = dict(ROAS, content_data=dict(ROAS["content_data"], chart_values=["1", "2"]))
    assert codes(run('<Chart ref="roas" />', bad)) == ["NODE_ITEM_MISSING"]


def test_hand_drawn_chart_is_left_alone():
    tag = '<Chart chartType="bar" chartColors="[]"><ChartSeries name="x"><ChartDataPoint label="a" value="1" /></ChartSeries></Chart>'
    res = run(tag)
    assert tag in res["xml"] and codes(res) == []


# ── focus, number format ──────────────────────────────────────────────────────

def test_focus_order_headline_then_latest_period_then_hint():
    assert C.focus_index(ROAS, "Brand returns the most") == 2
    assert C.focus_index(ROAS, "Return by class") == 0                     # the hint names Generic search
    q = {"kind": "chart", "content_data": {"chart_type": "bar", "chart_labels": ["Q1", "Q2", "Q3"], "chart_values": [1, 2, 3]}}
    assert C.focus_index(q, "Revenue grew") == 2 and C.focus_index(q, "Q2 was the peak") == 1
    assert C.focus_index(dict(ROAS, design_hint=""), "Return by class") is None


@pytest.mark.parametrize("values,fmt", [
    (["0.29x", "0.80x"], '0.00"x"'), (["₹1,234 Cr", "₹56.5 Cr"], '"₹"#,##0.0" Cr"'), (["12%", "4%"], '0"%"'),
    (["-1.4 pts", "+2.0 pts"], '0.0" pts"'), ([1, 2], "General"), (["5x", "7%"], "General"), (["n/a", "2"], "General"),
])
def test_number_format(values, fmt):
    assert C.number_format(values) == fmt


# ── prompt, hooks ─────────────────────────────────────────────────────────────

def test_prompt_line_and_node_lines_carry_no_values():
    line = C.prompt_line(ROAS, "Generic search takes the most budget")
    assert "focus Generic search" in line and "variants native | native labelled | rows" in line
    assert "0.29" not in line and '<Chart ref="roas"/>' in line
    assert "variants native" in C.prompt_line(TREND) and "rows" not in C.prompt_line(TREND).split("variants")[1]
    lines = C.node_lines()
    assert "native labelled" in lines and "rows" in lines and "0.29" not in lines


def test_yaml_names_match():
    assert list(spec.blocks()["chart"]["variants"]) == list(C.node()["compositions"])
    assert set(C.tag_attributes()) >= {"ref", "variant", "direction", "title.*", "bar.*", "backgroundColor"}


def test_generator_prompt_hides_chart_data(monkeypatch):
    from src.agents import generator
    state = {"slide_plans": [plan(ROAS)], "current_slide_index": 0, "contract": {}, "raw_request": "x"}
    system, user = generator._render_prompts(state)
    assert "## CHARTS" in system and "CHART roas:" in user and "0.29x" not in user
    monkeypatch.setenv("POM_NODES", "")
    system, user = generator._render_prompts(state)
    assert "## CHARTS" not in system and "0.29x" in user


def test_context_builder_drops_hand_chart_guidance():
    from src.agents.context_builder import build_contract
    from src.agents.style_resolver import resolve_theme
    c = build_contract(plan(ROAS), resolve_theme("graphite-dark"))
    assert "variant" in c["allowed_attributes"]["Chart"] and "chartColors" not in " ".join(c["notes"])


def test_validator_expands_charts(monkeypatch, tmp_path):
    from src.agents import validator
    captured = {}

    def fake_norm(xml):
        captured["xml"] = xml
        return {"issues": [], "auto_fixed": 0, "blocking": True, "cleaned_xml": xml}
    monkeypatch.setattr(validator, "normalize_xml", fake_norm)
    monkeypatch.setattr(validator, "nesting_compile_failure", lambda issues: {"diagnostics": [], "ok": False})
    state = {"current_xml": '<Slide><VStack><Chart ref="roas" variant="rows" /></VStack></Slide>', "run_id": "t",
             "slide_plans": [plan(ROAS)], "current_slide_index": 0}
    validator.validator_node(state)
    assert 'id="kpiv-roas-0"' in captured["xml"]
    state["current_xml"] = '<Slide><VStack><Chart ref="nope" /></VStack></Slide>'
    out = validator.validator_node(state)
    assert out["compile_result"]["diagnostics"][0]["type"] == "NODE_REF_UNKNOWN"


# ── pptx-post on a real compile ───────────────────────────────────────────────

_COMPILER = Path(__file__).resolve().parents[2] / "src" / "node" / "compile-pom.js"


def test_labels_and_bar_direction_in_the_pptx(tmp_path):
    if not shutil.which("node") or not (_COMPILER.parent / "node_modules").exists():
        pytest.skip("node / POM not installed")
    from src.agents.style_resolver import resolve_theme
    theme = resolve_theme("graphite-dark")["element"]
    body = C.expand('<Chart ref="roas" variant="native labelled" h="400" /><Chart ref="roas2" direction="horizontal" h="200" />',
                    plan(ROAS, dict(ROAS, component_id="roas2")))["xml"]
    xml = f'{theme}\n<Slide><VStack w="1280" h="720" padding="40" gap="20">{body}</VStack></Slide>'
    (tmp_path / "in.xml").write_text(xml, encoding="utf-8")
    subprocess.run(["node", str(_COMPILER), str(tmp_path / "in.xml"), str(tmp_path)], check=True, capture_output=True,
                   timeout=180, env={**__import__("os").environ, "POM_GEOMETRY": "0"})
    with zipfile.ZipFile(tmp_path / "presentation.pptx") as z:
        c1, c2 = (z.read(f"ppt/charts/chart{i}.xml").decode("utf-8") for i in (1, 2))
    assert 'formatCode="0.00&quot;x&quot;"' in c1 and 'srgbClr val="1E293B"' in c1 and '<c:showVal val="1"/>' in c1
    assert re.search(r'<c:valAx>.*?<c:delete val="1"/>', c1, re.S)
    assert '<c:barDir val="bar"/>' in c2 and "<c:dLbls><c:numFmt" not in c2
