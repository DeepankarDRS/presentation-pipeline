"""Bullet list composition node (approved 2026-11-04), POM_NODES=bullet_list: the native fallback, requires, words kept
verbatim, <Highlight>, attributes dropped with a report rather than silently, no duplicate attributes, and the real
compile: a real list in the .pptx with its marker colour and spacing (LLM-free)."""

import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from src.compiler.nodes import bullets as B
from src.compiler.nodes import composed, spec

_ROOT = Path(__file__).resolve().parents[2]
LEADS = {"component_id": "pts", "kind": "bullet_list", "content_data": {"bullets": [
    "Recommendation ads: 11.3x ROAS at a third of Search spend",
    "Product C drags: 4.3x ROAS & 23% ACOS",
    "Generic keywords — keep them despite lower ROAS",
    "Review bids weekly"]}}
OWN = {"component_id": "pts", "kind": "bullet_list", "content_data": {"bullets": ["1. First move", "2. Second move"]}}
MANY = {"component_id": "pts", "kind": "bullet_list", "content_data": {"bullets": [f"Point {i}" for i in range(8)]}}
HINTED = dict(LEADS, design_hint="flag Product C drags in red as the weak spot")
ALL = list(spec.nodes()["bullet_list"]["compositions"])


@pytest.fixture(autouse=True)
def nodes_on(monkeypatch):
    monkeypatch.setenv("POM_NODES", "bullet_list")


def run(tag, comp=LEADS):
    return B.expand(f'<Slide><VStack w="1280" h="720">{tag}</VStack></Slide>', {"components": [comp]})


def codes(res):
    return [i["code"] for i in res["issues"]]


def text_of(xml):
    root = etree.fromstring(f"<x>{xml}</x>")
    return "".join(root.itertext())


# ── the native fallback ───────────────────────────────────────────────────────

def test_bare_tag_is_the_real_list():
    r = run('<Ul ref="pts"/>')
    assert r["ok"] and r["components"]["pts"]["composition"] == "native"
    assert len(re.findall(r"<Ul\b", r["xml"])) == 1 and len(re.findall(r"<Li\b", r["xml"])) == 4


@pytest.mark.parametrize("tag,comp,code", [
    ('<Ul ref="pts" variant="no_such_look"/>', LEADS, "NODE_VARIANT_UNKNOWN"),
    ('<Ul ref="pts" variant="native numbered"/>', OWN, "NODE_VARIANT_UNMET"),
])
def test_what_cannot_be_composed_is_the_native_list(tag, comp, code):
    r = run(tag, comp)
    assert r["components"]["pts"]["composition"] == "native" and code in codes(r)
    assert "<Ul " in r["xml"] and "<Ol" not in r["xml"]


def test_rows_numbered_with_own_numbers_falls_back_to_rows():
    r = run('<Ul ref="pts" variant="rows numbered"/>', OWN)
    assert r["components"]["pts"]["composition"] == "rows" and "NODE_VARIANT_UNMET" in codes(r)


def test_numbered_is_a_real_ol():
    r = run('<Ul ref="pts" variant="native numbered"/>')
    assert re.search(r'<Ol id="lst-pts"', r["xml"]) and "<Ul" not in r["xml"]


def test_a_list_without_ref_stays_the_llms_own():
    xml = '<Slide><Ul fontSize="14"><Li>Mine</Li></Ul></Slide>'
    assert B.expand(xml, {"components": [LEADS]})["xml"] == xml


def test_unknown_ref_and_empty_plan_are_errors():
    assert "NODE_REF_UNKNOWN" in codes(run('<Ul ref="nope"/>'))
    empty = {"component_id": "pts", "kind": "bullet_list", "content_data": {"bullets": []}}
    assert "NODE_ITEM_MISSING" in codes(run('<Ul ref="pts"/>', empty))


# ── words ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("variant", ALL)
def test_every_word_is_kept_in_plan_order(variant):
    r = run(f'<Ul ref="pts" variant="{variant}"/>')
    drawn = re.sub(r"\s+", " ", text_of(r["xml"]))
    pos = -1
    for s in B.items(LEADS):   # each point's head, in plan order
        at = drawn.find(B.compose.split(s)[0], pos + 1)
        assert at > pos, s
        pos = at
        for word in s.replace(":", "").replace("—", "").split():
            assert word in drawn, word


def test_native_keeps_the_separator_and_bolds_the_head():
    r = run('<Ul ref="pts"/>')
    assert "<Li><B>Product C drags</B>: 4.3x ROAS &amp; 23% ACOS</Li>" in r["xml"]
    assert "<Li><B>Generic keywords</B> — keep them despite lower ROAS</Li>" in r["xml"]
    assert "<Li>Review bids weekly</Li>" in r["xml"]


def test_rows_split_head_over_detail():
    r = run('<Ul ref="pts" variant="rows"/>')
    assert 'id="lsth-pts-1"' in r["xml"] and ">Product C drags</Text>" in r["xml"]
    assert 'id="card-pts-0"' in r["xml"] and 'id="card-pts-3"' in r["xml"]


# ── highlights ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("variant", ALL)
def test_phrase_colours_only_those_words(variant):
    r = run(f'<Ul ref="pts" variant="{variant}"><Highlight phrase="4.3x ROAS" color="bad"/></Ul>')
    assert r["ok"] and '<Span color="$negativeText">4.3x ROAS</Span>' in r["xml"]


def test_phrase_bold():
    r = run('<Ul ref="pts"><Highlight phrase="11.3x ROAS" bold="true"/></Ul>')
    assert "<B>11.3x ROAS</B>" in r["xml"]


def test_item_by_head_or_whole_text():
    for name in ("Product C drags", "product c drags: 4.3x roas &amp; 23% acos"):
        r = run(f'<Ul ref="pts" variant="rows"><Highlight item="{name}" color="bad"/></Ul>')
        assert r["ok"] and 'color="$negativeText"' in r["xml"], name


def test_fill_only_on_rows_and_reported_on_native():
    r = run('<Ul ref="pts" variant="rows"><Highlight item="Product C drags" fill="bad"/></Ul>')
    assert 'backgroundColor="$negativeSoft"' in r["xml"]
    n = run('<Ul ref="pts"><Highlight item="Product C drags" fill="bad"/></Ul>')
    assert "NODE_ATTR_DROPPED" in codes(n) and "Soft" not in n["xml"]


@pytest.mark.parametrize("mark", [
    '<Highlight phrase="not in the list" color="bad"/>',
    '<Highlight item="No such point" color="bad"/>',
    '<Highlight phrase="4.3x ROAS" color="red"/>',
    '<Highlight phrase="4.3x ROAS" fill="bad"/>',
    '<Highlight phrase="4.3x ROAS"/>',
    '<Highlight column="x" color="bad"/>',
])
def test_a_wrong_highlight_is_an_error(mark):
    r = run(f'<Ul ref="pts">{mark}</Ul>')
    assert not r["ok"] and "NODE_HIGHLIGHT_UNKNOWN" in codes(r)


def test_other_children_are_reported():
    r = run('<Ul ref="pts"><Li>typed</Li></Ul>')
    assert "NODE_ATTR_DROPPED" in codes(r) and "typed" not in r["xml"]


def test_many_highlights_are_all_drawn_with_a_warning():
    marks = "".join(f'<Highlight phrase="{w}" color="bad"/>' for w in
                    ("11.3x", "ROAS", "third", "Search", "spend", "4.3x", "ACOS"))
    r = run(f'<Ul ref="pts">{marks}</Ul>')
    assert r["ok"] and "NODE_HIGHLIGHT_LIMIT" in codes(r)


def test_hint_colours_the_named_point_only_without_highlights():
    r = run('<Ul ref="pts" variant="rows"/>', HINTED)
    assert r["components"]["pts"]["focus"] == 1 and 'backgroundColor="$negativeSoft"' in r["xml"]
    m = run('<Ul ref="pts" variant="rows"><Highlight phrase="11.3x" color="good"/></Ul>', HINTED)
    assert m["components"]["pts"]["focus"] is None and "$negativeSoft" not in m["xml"]


# ── attributes: no silent no-ops, no duplicates ───────────────────────────────

@pytest.mark.parametrize("variant", ALL)
def test_no_attribute_is_written_twice(variant):
    """syntax audit 2026-11-04: an expander's literal attribute + the LLM's blanked a KPI row on the slide."""
    attrs = ('gap="9" alignItems="start" justifyContent="center" padding="3" grow="2" w="50%" item.padding="4" '
             'item.gap="2" item.grow="1" item.w="40" item.alignItems="center"')
    xml = run(f'<Ul ref="pts" variant="{variant}" {attrs}/>')["xml"]
    etree.fromstring(f"<x>{xml}</x>")   # lxml rejects a duplicate attribute


@pytest.mark.parametrize("variant", ALL)
def test_every_allowed_part_attribute_shows_or_is_reported(variant):
    """syntax audit: 31% of attribute x composition pairs silently did nothing."""
    plain = run(f'<Ul ref="pts" variant="{variant}"/>')["xml"]
    for attr in ('head.color="$accentAlt"', 'detail.color="$accentAlt"', 'marker.color="$accentAlt"',
                 'item.backgroundColor="$accentAlt"', 'head.italic="true"', 'detail.underline="true"'):
        r = run(f'<Ul ref="pts" variant="{variant}" {attr}/>')
        assert r["xml"] != plain or "NODE_ATTR_DROPPED" in codes(r), attr


@pytest.mark.parametrize("attr", ['fontSize="14"', 'lineHeight="1.9"', 'fontFamily="Arial"', 'color="1E293B"'])
def test_code_owned_and_literal_colours_are_reported(attr):
    r = run(f'<Ul ref="pts" {attr}/>')
    assert r["issues"] and attr not in r["xml"]


def test_tag_color_reaches_the_words_on_every_composition():
    for variant in ALL:
        assert 'color="$textMuted"' in run(f'<Ul ref="pts" variant="{variant}" color="$textMuted"/>')["xml"]


def test_native_box_attributes_go_on_its_box():
    r = run('<Ul ref="pts" padding="20" backgroundColor="$surfaceAlt" h="300"/>')
    assert re.search(r'<VStack[^>]*padding="20"[^>]*backgroundColor="\$surfaceAlt"', r["xml"])
    assert not re.search(r'<Ul[^>]*padding', r["xml"])


# ── icons ─────────────────────────────────────────────────────────────────────

GOOD = "target,scissors,wallet,truck"


def test_icons_on_rows():
    r = run(f'<Ul ref="pts" variant="rows" icons="{GOOD}"/>')
    assert re.findall(r'<Icon name="(\S+)"', r["xml"]) == GOOD.split(",") and not codes(r)


@pytest.mark.parametrize("tag", [
    '<Ul ref="pts" variant="rows" icons="target,not-an-icon,wallet,truck"/>',
    '<Ul ref="pts" variant="rows" icons="target,scissors"/>',
    f'<Ul ref="pts" variant="rows numbered" icons="{GOOD}"/>',
    f'<Ul ref="pts" icons="{GOOD}"/>',
])
def test_bad_icons_are_reported_and_removed(tag):
    r = run(tag)
    assert "NODE_ATTR_DROPPED" in codes(r) and "<Icon" not in r["xml"]


def test_past_six_points_icons_become_dots():
    names = ",".join(["target"] * 8)
    r = run(f'<Ul ref="pts" variant="rows" icons="{names}"/>', MANY)
    assert "NODE_ATTR_DROPPED" in codes(r) and "<Icon" not in r["xml"] and "ellipse" in r["xml"]


# ── the composed hooks and the prompt ─────────────────────────────────────────

def test_composed_hooks():
    assert "bullet_list" in composed.kinds_on() and composed.tag("bullet_list") == "Ul"
    assert composed.drawn({"components": [LEADS]}, "bullet_list")
    assert composed.PLAN_KEYS["bullet_list"] == ("bullets",)
    assert composed.expand('<Slide><Ul ref="pts"/></Slide>', {"components": [LEADS]})["components"]["pts"]


def test_prompt_shows_the_points_to_read_and_forbids_typing():
    line = B.prompt_line(LEADS)
    assert "Product C drags: 4.3x ROAS & 23% ACOS" in line and "never type one" in line and 'ref="pts"' in line
    lines = B.node_lines()
    assert "<Highlight" in lines and "fontSize" in lines and "<Mark" not in lines
    for variant in ALL:
        assert variant in lines


def test_block_variants_match_the_compositions():
    assert list(spec.blocks()["bullet_list"]["variants"]) == ALL


# ── the real compile ──────────────────────────────────────────────────────────

SLIDE = ('<Theme surface="FFFFFF" accent="2563EB" textMain="16202E" textMuted="55627A" border="CAD5E4" />'
         '<Slide><VStack w="1280" h="720" padding="48" gap="24" alignItems="stretch">'
         '<Text fontSize="32" bold="true">Title</Text>{body}</VStack></Slide>')


def compile_slide(tmp_path: Path, tag: str, comp=LEADS, env: dict | None = None) -> tuple[list[str], dict]:
    if not shutil.which("node") or not (_ROOT / "src" / "node" / "node_modules").exists():
        pytest.skip("node compiler not installed")
    import os
    xml = SLIDE.format(body=B.expand(f"<x>{tag}</x>", {"components": [comp]})["xml"][3:-4])
    (tmp_path / "in.xml").write_text(xml, encoding="utf-8")
    subprocess.run(["node", str(_ROOT / "src" / "node" / "compile-pom.js"), str(tmp_path / "in.xml"), str(tmp_path)],
                   check=True, capture_output=True, timeout=180, env={**os.environ, **(env or {})})
    x = zipfile.ZipFile(tmp_path / "presentation.pptx").read("ppt/slides/slide1.xml").decode("utf-8")
    lists = [s for s in re.findall(r"<p:sp>.*?</p:sp>", x, re.S) if "<a:buChar" in s or "<a:buAutoNum" in s]
    return lists, json.loads((tmp_path / "compile-result.json").read_text(encoding="utf-8"))


def test_compiled_is_one_real_list_with_marker_colour_and_spacing(tmp_path):
    lists, _ = compile_slide(tmp_path, '<Ul ref="pts"/>')
    assert len(lists) == 1 and lists[0].count("<a:buChar") == 4
    assert lists[0].count('<a:buClr><a:srgbClr val="2563EB"/></a:buClr>') == 4
    assert lists[0].count("<a:spcBef>") == 3 and 'anchor="ctr"' in lists[0]


def test_without_fit_grow_it_stays_pom_s_plain_list(tmp_path):
    lists, _ = compile_slide(tmp_path, '<Ul ref="pts"/>', env={"POM_FIT_GROW": "0"})
    assert len(lists) == 1 and lists[0].count("<a:buChar") == 4 and "<a:buClr" not in lists[0] and "<a:spcBef" not in lists[0]


def test_compiled_numbers_have_no_restart(tmp_path):
    lists, _ = compile_slide(tmp_path, '<Ul ref="pts" variant="native numbered"/>')
    assert lists[0].count("<a:buAutoNum") == 4 and "startAt" not in lists[0]


def test_short_points_split_into_two_real_lists_both_marked(tmp_path):
    short = {"component_id": "pts", "kind": "bullet_list", "content_data": {"bullets": [f"Short point {i}" for i in range(6)]}}
    lists, res = compile_slide(tmp_path, '<Ul ref="pts"/>', short)
    assert len(lists) == 2 and any("split" in f for f in res["fitGrow"])
    assert all("<a:buClr" in s for s in lists)
