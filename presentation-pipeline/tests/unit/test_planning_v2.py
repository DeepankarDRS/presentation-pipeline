"""Planning v2 (src/planning): brief index, checks, adapter and the graph with a mocked LLM."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import yaml

from src.planning.adapter import fill_component, to_slide_plan
from src.planning.brief_index import by_id, data_numbers, index_brief, numbers
from src.planning.checks import apply_headline_blocks, check_slide, check_storyline, fill_design
from src.planning.graph import run_planning
from src.planning.schemas import SlideDesign, Storyline

_CASES = Path(__file__).resolve().parents[1] / "cases"


def _case(name: str) -> str:
    return yaml.safe_load((_CASES / f"{name}.yaml").read_text(encoding="utf-8"))["request"]


BRIEF = """Create a 2-slide deck.

Slide 1:
Q-COMMERCE REVIEW
H1 2026

Slide 2:
PLATFORM DEEP-DIVE · 01
Efficient on ROAS, softened on top-line
TOTAL SALES
₹1.32 Cr
ROAS
6.35x
CATEGORY | AD SALES | ROAS
Milk | ₹20.8 L | 6.89x
Curd | ₹15.4 L | 8.00x
Chart (bar):
  Ad Sales (L): Milk 500ml 12.4, Curd 400g 9.8, Paneer 200g 7.2
Curd is the star: 8.0x ROAS at 12.5% ACOS
"""


# ── Brief index ─────────────────────────────────────────────────────────────

def test_numbers_rule():
    assert numbers("₹1.32 Cr · 10,332 · 4.40x · 7 days") == ["1.32", "10332", "4.4"]
    assert data_numbers("June '26 · FY 2026 · 62% share") == ["62"]
    assert data_numbers("01") == []


def test_index_gj_h1_parses_tables_and_charts():
    ix = index_brief(_case("gj-h1-regen"))
    kinds = [b["kind"] for b in ix["blocks"]]
    assert kinds.count("table") == 14 and kinds.count("chart") == 6
    s4 = [b for b in ix["blocks"] if b["section"] == 4]  # "Slide 5:" = Blinkit deep-dive
    cat = next(b for b in s4 if b["kind"] == "table")
    assert cat["header"] == ["CATEGORY", "AD SALES", "AD SPEND", "ROAS", "ACOS"]
    assert [r[0] for r in cat["rows"]] == ["Milk", "Curd", "Paneer", "TOTAL"]
    chart = next(b for b in s4 if b["kind"] == "chart")
    assert chart["chart_type"] == "bar" and chart["series"][0]["points"][0] == ["Milk 500ml", "12.4"]
    assert "Efficient on ROAS, softened on top-line" in [b["text"] for b in s4]


def test_index_cheffin_splits_long_paragraph():
    ix = index_brief(_case("gate-deck-cheffin-audit"))
    texts = [b["text"] for b in ix["blocks"]]
    assert not ix["has_sections"]
    assert "CPC: ₹31.1" in texts and "Allowable CPC for 1.0x ROAS: ₹10.7" in texts and "ZAROMA:" in texts
    assert "1. Lower CPC on weak traffic." in texts
    assert {"31.1", "46.2", "10.7", "14.8"} <= set(ix["numbers"])


# ── Checks ──────────────────────────────────────────────────────────────────

def _story(**over):
    s = {"slide_index": 1, "intent": "deep_dive", "label": "PLATFORM DEEP-DIVE · 01", "headline_block": "",
         "headline": "Efficient on ROAS", "subtitle": "", "block_ids": [], "so_what": "", "emphasis": [],
         "parallel_group": "", "notes": ""}
    s.update(over)
    return s


def test_storyline_checks_coverage_headline_and_invention():
    ix = index_brief(BRIEF)
    ids = {b["text"]: b["id"] for b in ix["blocks"] if b["kind"] == "text"}
    story = {"slides": [
        _story(slide_index=0, intent="cover", label="", headline="Q-Commerce Review", block_ids=[]),
        _story(label="PLATFORM DEEP-DIVE · 01", headline="PLATFORM DEEP-DIVE · 01",
               emphasis=["a", "b", "c"], so_what="ROAS up 12%"),
    ], "set_aside": []}
    issues = check_storyline(story, ix, 2)
    text = " ".join(issues)
    assert "repeats the label" in text and "at most 2" in text and "12" in text and "no slide shows" in text

    story["slides"][1].update(headline_block=ids["Efficient on ROAS, softened on top-line"], emphasis=[],
                              so_what="", block_ids=[b["id"] for b in ix["blocks"] if b["section"] == 1])
    story["slides"][0]["block_ids"] = [b["id"] for b in ix["blocks"] if b["section"] == 0]
    apply_headline_blocks(story, ix)
    assert story["slides"][1]["headline"] == "Efficient on ROAS, softened on top-line"
    assert check_storyline(story, ix, 2) == []


def test_slide_check_and_fill():
    ix = index_brief(BRIEF)
    blocks = by_id(ix)
    s2 = [b["id"] for b in ix["blocks"] if b["section"] == 1]
    table = next(b["id"] for b in ix["blocks"] if b["kind"] == "table")
    chart = next(b["id"] for b in ix["blocks"] if b["kind"] == "chart")
    story = _story(block_ids=s2)
    kpi_blocks = [b for b in s2 if blocks[b]["kind"] == "text"]

    filled = fill_component({"id": "t", "kind": "table", "role": "hero", "block_ids": [table],
                             "columns": ["ROAS", "category"]}, blocks)
    assert filled["columns"] == ["ROAS", "CATEGORY"] and filled["rows"] == [["6.89x", "Milk"], ["8.00x", "Curd"]]

    design = {"components": [
        {"id": "kpis", "kind": "kpi_row", "role": "strip", "block_ids": kpi_blocks,
         "kpis": [{"label": "Total sales", "value": "₹1.32 Cr", "note": ""},
                  {"label": "ROAS", "value": "6.35x", "note": "+99%"}]},
        {"id": "t", "kind": "table", "role": "hero", "block_ids": [table]},
        {"id": "c", "kind": "chart", "role": "hero", "block_ids": [chart]},
    ], "not_shown": []}
    issues = check_slide(fill_design(design, ix), story, ix)
    text = " ".join(issues)
    assert "99" in text                       # invented
    assert "2 hero" in text                   # one focal point
    assert "12.5 is not shown" in text          # read-out block lost

    design["components"][0]["kpis"][1]["note"] = ""
    design["components"][2]["role"] = "support"
    design["components"].append({"id": "r", "kind": "bullet_list", "role": "readout", "block_ids": kpi_blocks,
                                 "bullets": ["Curd is the star: 8.0x ROAS at 12.5% ACOS"]})
    assert check_slide(fill_design(design, ix), story, ix) == []


def test_slide_check_capacity_and_units():
    ix = index_brief(BRIEF)
    story = _story(block_ids=[])
    design = {"components": [
        {"id": "tl", "kind": "timeline", "role": "hero", "block_ids": [],
         "items": [{"label": "Roll out day-parting on Blinkit", "detail": ""}]},
        {"id": "c", "kind": "chart", "role": "support", "block_ids": [],
         "labels": ["A", "B"], "series": [{"name": "CVR (%)", "values": ["6.4"]}, {"name": "AOV (₹)", "values": ["230"]}]},
    ]}
    text = " ".join(check_slide(design, story, ix))
    assert "≤ 4 words" in text and "mix units" in text


def test_adapter_maps_to_todays_slide_plan():
    story = _story(headline="Efficient on ROAS", subtitle="June '26")
    design = {"layout": "kpis on top", "components": [
        {"id": "kpis", "kind": "kpi_row", "role": "strip", "block_ids": [], "emphasis": "ROAS 6.35x",
         "kpis": [{"label": "ROAS", "value": "6.35x", "note": "▲ best of 3"}]},
        {"id": "c", "kind": "chart", "role": "hero", "block_ids": [], "chart_type": "bar", "labels": ["a", "b"],
         "series": [{"name": "s", "values": ["1.5", "2"]}]},
    ]}
    plan = to_slide_plan(story, design)
    assert plan["slide_title"] == "Efficient on ROAS" and plan["slide_type"] == "data"
    title, kpis, chart = plan["components"]
    assert title["content_data"] == {"title": "Efficient on ROAS", "subtitle": "June '26",
                                     "kicker": "PLATFORM DEEP-DIVE · 01"}
    assert kpis["content_data"]["kpi_directions"] == ["up"] and kpis["design_hint"] == "emphasise ROAS 6.35x"
    assert kpis["weight"] == "peer" and chart["weight"] == "hero" and chart["content_data"]["chart_values"] == [1.5, 2.0]


# ── Graph with a mocked LLM ─────────────────────────────────────────────────

class _FakeLLM:
    """Returns canned structured outputs; the first storyline and the first design of slide 2 are wrong."""

    def __init__(self, index):
        self.index, self.calls = index, []

    def with_structured_output(self, schema, **_):
        self.schema = schema
        return self

    def invoke(self, messages):
        user = messages[-1].content
        self.calls.append((self.schema.__name__, user))
        ids = lambda sec: [b["id"] for b in self.index["blocks"] if b["section"] == sec]
        if self.schema is Storyline:
            retry = "PROBLEMS FOUND" in user
            head = next(b["id"] for b in self.index["blocks"] if b["text"].startswith("Efficient"))
            return Storyline(
                audience_and_use="brand leadership, pre-read", deck_argument="Blinkit is efficient",
                gaps=[], style_directives=[], deck_title="Q-Commerce Review", set_aside=[],
                slides=[
                    dict(slide_index=0, intent="cover", label="", headline_block="", headline="Q-Commerce Review",
                         subtitle="H1 2026", block_ids=ids(0), so_what="", emphasis=[], parallel_group="", notes=""),
                    dict(slide_index=1, intent="deep_dive", label="PLATFORM DEEP-DIVE · 01", headline_block=head,
                         headline="x", subtitle="", block_ids=ids(1) if retry else ids(1)[:3], so_what="",
                         emphasis=["ROAS 6.35x"], parallel_group="", notes=""),
                ])
        slide = int(re.search(r"SLIDE (\d+) of", user).group(1)) - 1
        if slide == 0:
            return SlideDesign(reading="cover", layout="title only", components=[
                dict(id="n", kind="narrative", role="hero", block_ids=[], text="H1 2026")])
        blocks = by_id(self.index)
        texts = [b for b in ids(1) if blocks[b]["kind"] == "text"]
        comps = [
            dict(id="kpis", kind="kpi_row", role="strip", block_ids=texts, emphasis="ROAS 6.35x",
                 kpis=[dict(label="Total sales", value="₹1.32 Cr"), dict(label="ROAS", value="6.35x")]),
            dict(id="t", kind="table", role="hero", block_ids=[b for b in ids(1) if blocks[b]["kind"] == "table"]),
            dict(id="c", kind="chart", role="support", block_ids=[b for b in ids(1) if blocks[b]["kind"] == "chart"]),
        ]
        if "PROBLEMS FOUND" in user:
            comps.append(dict(id="r", kind="bullet_list", role="readout", block_ids=texts,
                              bullets=["Curd is the star: 8.0x ROAS at 12.5% ACOS"]))
        return SlideDesign(reading="deep dive", layout="kpis on top; table beside chart", components=comps)


def test_graph_end_to_end_with_retries():
    fake = _FakeLLM(index_brief(BRIEF))
    with patch("src.planning.graph.get_llm", return_value=fake):
        out = run_planning(BRIEF, target_slides=2, max_concurrency=2)

    steps = [s for s, _ in fake.calls]
    assert steps.count("Storyline") == 2                       # coverage issue → one retry
    assert steps.count("SlideDesign") == 3                     # slide 2's lost read-out → one re-ask
    story = out["storyline"]
    assert story["slides"][1]["headline"] == "Efficient on ROAS, softened on top-line"  # copied verbatim
    assert out["designs"][1]["issues"] == [] and out["designs"][1]["attempts"] == 2
    plans = out["slide_plans"]
    assert [p["slide_index"] for p in plans] == [0, 1]
    table = next(c for c in plans[1]["components"] if c["kind"] == "table")
    assert table["content_data"]["table_rows"] == [["Milk", "₹20.8 L", "6.89x"], ["Curd", "₹15.4 L", "8.00x"]]
    chart = next(c for c in plans[1]["components"] if c["kind"] == "chart")
    assert chart["content_data"]["chart_labels"] == ["Milk 500ml", "Curd 400g", "Paneer 200g"]
    assert len(out["calls"]) == 5
