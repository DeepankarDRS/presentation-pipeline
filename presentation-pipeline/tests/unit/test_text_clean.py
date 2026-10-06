"""NUL / control characters from a model must not reach the slide XML (step 0 test-PC run, deck-qbr-data)."""

import json
import xml.etree.ElementTree as ET

from src.agents.planner_schema import PlannerSlide
from src.agents.slide_component_planner import _planner_slide_to_state
from src.compiler.normalizer import normalize_xml
from src.utils.text_clean import clean_data, strip_illegal

NUL = chr(0)


def test_strip_illegal_removes_control_characters_and_keeps_text_whitespace():
    text = f"a{NUL}b{chr(7)}c\tline\nnext\r{chr(0x1f)}{chr(0xfffe)}d"
    cleaned, n = strip_illegal(text)
    assert cleaned == "abc\tline\nnext\rd" and n == 4


def test_clean_data_reaches_into_lists_and_dicts_and_leaves_numbers_alone():
    data = {"cards": [{"title": f"A{NUL}", "n": 3}], "labels": [f"{NUL}x", "y"], "ok": True, "none": None}
    assert clean_data(data) == {"cards": [{"title": "A", "n": 3}], "labels": ["x", "y"], "ok": True, "none": None}


def test_normalize_xml_strips_them_and_says_so():
    raw = f'<Slide><VStack><Text fontSize="14">$28.1M {NUL}b{NUL}b +22%</Text></VStack></Slide>'
    out = normalize_xml(raw)
    assert NUL not in out["cleaned_xml"]
    ET.fromstring(out["cleaned_xml"])  # well-formed again
    issue = next(i for i in out["issues"] if i["code"] == "ILLEGAL_CHARS_REMOVED")
    assert issue["auto_fixed"] is True and "2" in issue["message"]
    assert not out["blocking"]


def test_clean_xml_gets_no_such_issue():
    out = normalize_xml('<Slide><VStack><Text fontSize="14">fine</Text></VStack></Slide>')
    assert all(i["code"] != "ILLEGAL_CHARS_REMOVED" for i in out["issues"])


def test_a_planner_reply_with_a_nul_in_its_content_is_cleaned():
    reply = PlannerSlide.model_validate({
        "slide_type": "data", "layout_hint": "list",
        "components": [{"component_id": "n", "kind": "narrative", "count": 1, "weight": "hero",
                        "content_data_json": json.dumps({"text": f"$28.1M {NUL}b +22%"})}],
    })
    plan = _planner_slide_to_state(0, reply)
    assert plan["components"][0]["content_data"]["text"] == "$28.1M b +22%"
    assert NUL not in json.dumps(plan["content_data"]).replace("\\u0000", NUL)
