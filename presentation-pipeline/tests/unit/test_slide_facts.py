"""Component ids, boxes, marks and measured facts for the visual critic and fixer (2026-11-20)."""

import json

from src.agents import slide_facts
from src.compiler.nodes import compose, composed

PLAN = {"components": [{"component_id": "slide_title", "kind": "title"},
                       {"component_id": "takeaways", "kind": "bullet_list"},
                       {"component_id": "rev", "kind": "chart"}]}
NORM = {"component_boxes": {"takeaways": ["cmp-takeaways"], "rev": ["cmp-rev"]}}
GEO = {"slideSize": {"w": 1280, "h": 720}, "slides": [{"type": "vstack", "x": 0, "y": 0, "w": 1280, "h": 720, "children": [
    {"type": "text", "id": "slide_title", "x": 40, "y": 40, "w": 1200, "h": 44},
    {"type": "vstack", "id": "cmp-rev", "x": 40, "y": 100, "w": 590, "h": 580, "children": []},
    {"type": "vstack", "id": "cmp-takeaways", "x": 650, "y": 100, "w": 590, "h": 394, "children": [
        {"type": "ul", "id": "lst-takeaways", "x": 650, "y": 100, "w": 590, "h": 394}]}]}]}
TAGS = '<Slide><VStack><Text id="slide_title">T</Text><Chart ref="rev"/><Ul ref="takeaways" variant="rows"/></VStack></Slide>'


def _comps(tmp_path):
    geo = tmp_path / "geometry.json"
    geo.write_text(json.dumps(GEO), encoding="utf-8")
    return slide_facts.components(PLAN, NORM, geo, TAGS)


def test_stamp_adds_the_component_id_to_the_outer_box_or_keeps_its_own():
    assert compose.stamp('<VStack padding="8"><Text>a</Text></VStack>', "cmp-x") == \
        ('<VStack id="cmp-x" padding="8"><Text>a</Text></VStack>', "cmp-x")
    assert compose.stamp('<Table id="tbl-x" w="max"/>', "cmp-x") == ('<Table id="tbl-x" w="max"/>', "tbl-x")
    assert compose.stamp('<!-- note --><Ul><Li>a</Li></Ul>', "cmp-x")[1] == "cmp-x"


def test_a_hand_drawn_component_without_its_id_is_warned():
    plan = {"components": [{"component_id": "t", "kind": "title"}, {"component_id": "n", "kind": "narrative"}]}
    issues = composed.unmarked('<Slide><Text id="t">x</Text></Slide>', plan)
    assert [(i["code"], i["ref"], i["severity"]) for i in issues] == [("NODE_ID_MISSING", "n", "warning")]


def test_components_get_numbers_boxes_and_variants(tmp_path):
    comps = _comps(tmp_path)
    assert [(c.n, c.id, c.by) for c in comps] == [(1, "slide_title", "hand"), (2, "takeaways", "code"), (3, "rev", "code")]
    assert comps[1].variant == "rows" and comps[2].variant == "native (default)"
    assert comps[1].box == (650, 100, 590, 394)


def test_slide_dense_names_the_component_and_is_a_defect(tmp_path):
    comps = _comps(tmp_path)
    warn = {"code": "SLIDE_DENSE", "message": "...", "spills": [
        {"type": "vstack", "kind": "h", "need": 551, "have": 426, "ids": []},
        {"type": "ul", "kind": "h", "need": 519, "have": 394, "ids": ["lst-takeaways", "cmp-takeaways"]}]}
    facts = slide_facts.measured_facts(comps, [warn], [])
    assert len(facts) == 1 and facts[0].defect and facts[0].component == "takeaways"
    assert "519" in facts[0].text and comps[1].needs == ["height 394 -> 519px"]


def test_geometry_findings_are_placed_on_their_component_in_plain_words(tmp_path):
    comps = _comps(tmp_path)
    issues = [{"code": "GEOM_SPILL", "tier": "error",
               "message": "ul vstack > vstack[2]#cmp-takeaways > ul[0]#lst-takeaways draws past its card bottom by 40px"},
              {"code": "GEOM_CARD_EMPTY", "tier": "info", "message": "card vstack > vstack[1]#cmp-rev is 580px tall"}]
    spill, empty = slide_facts.measured_facts(comps, [], issues)
    assert spill.defect and spill.component == "takeaways" and "a part draws past its card" in spill.text
    assert not empty.defect and empty.component == "rev" and "#cmp-rev" not in empty.text


def test_annotate_puts_one_comment_before_each_component(tmp_path):
    comps = _comps(tmp_path)
    slide_facts.measured_facts(comps, [{"code": "SLIDE_DENSE", "spills": [
        {"type": "ul", "kind": "h", "need": 519, "have": 394, "ids": ["lst-takeaways"]}]}], [])
    out = slide_facts.annotate(TAGS, comps)
    assert '<!-- [3] rev · chart · variant native (default) · 590x580px -->\n<Chart ref="rev"/>' in out
    assert "<!-- [2] takeaways · bullet_list · variant rows · 590x394px · needs height 394 -> 519px -->" in out
    assert '<!-- [1] slide_title · title · drawn by hand' in out


def test_marks_are_drawn_on_the_screenshot(tmp_path):
    from PIL import Image
    png = tmp_path / "s.png"
    Image.new("RGB", (1920, 1080), "white").save(png)
    out = slide_facts.draw_marks(png, _comps(tmp_path), tmp_path / "marked.png")
    img = Image.open(out)
    assert img.size == (1920, 1080)
    assert img.getpixel((int(650 * 1.5) + 1, int(300 * 1.5))) != (255, 255, 255)   # the takeaways box edge


def test_colour_roles_not_the_whole_theme():
    roles = slide_facts.colour_roles('<Theme accent="2563EB" positive="15803D" step1="7FA9FD" chart3="199E8F" />')
    assert roles == "accent #2563EB, positive #15803D"


def test_the_generator_may_write_the_hand_drawn_id():
    """2026-11-25 paid run: the prompt asked for id="<component_id>" but ALLOWED ATTRIBUTES left id out: 0/12 written."""
    from src.agents.context_builder import build_contract
    from src.agents.style_resolver import resolve_theme
    plan = {"components": [{"component_id": "note", "kind": "narrative", "content_data": {"text": "x"}}]}
    attrs = build_contract(plan, resolve_theme("corporate-slate"))["allowed_attributes"]
    assert all("id" in attrs[n] for n in ("VStack", "HStack", "Text"))
