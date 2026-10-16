"""Fixes from the 2026-10-15 full-deck eval (docs/eval/deck-output-fixes-2026-10-15.md)."""

from src.agents.plan_checks import PLAN_INSTRUCTION_TEXT, find_problems, finalize_plan, is_instruction_text
from src.agents.written_lines import (brief_content, brief_instructions, instruction_lines, matches_instruction,
                                      settle_direction_lines, visual_directions)


def comp(cid, kind, data, weight="peer"):
    return {"component_id": cid, "kind": kind, "count": 1, "content_summary": "", "weight": weight,
            "content_data": data}


def plan(components, slide_type="content"):
    return {"slide_index": 5, "slide_type": slide_type, "components": components}


# ── step 1: brief instructions the outline rewords ─────────────────────────

AGENCY = ("SLIDE 6: Closing Recommendation & Data Needed  Headline: The current account needs a sharper operator.  "
          "Recommended next step: 30-day transition audit and account takeover sprint.  "
          "Speaker Notes: End with confidence. The audit already shows immediate improvement areas, and deeper access "
          "will allow the agency to move from diagnosis to execution.")
XTSY = ("SLIDE 7  TITLE: Expected Business Impact for XTSY  Visual: Growth Impact Framework  Show expected impact "
        "areas:  Category Visibility ↑  Search Share ↑  Use arrow visuals rather than hard numbers.  Message: "
        "Combining category intelligence, automation and performance execution creates a scalable growth engine.")
LAUNCH = "Slide 6: Compliance.  Note: SOC2 + HIPAA certification targeted for Apr 2027.  Visual: a badge row."


def test_brief_instructions_reads_notes_and_unlabelled_design_sentences():
    assert brief_instructions(AGENCY)["notes"] == [
        "End with confidence. The audit already shows immediate improvement areas, and deeper access will allow the "
        "agency to move from diagnosis to execution."]
    assert brief_instructions(XTSY)["directions"] == ["Use arrow visuals rather than hard numbers."]
    assert brief_instructions(LAUNCH) == {"notes": [], "directions": []}   # a data note is content


def test_outline_drops_reworded_notes_and_marks_unlabelled_directions():
    ins = brief_instructions(AGENCY)
    slide = {"key_messages": ["Note: End with confidence. The audit already shows immediate improvement areas, and "
                              "deeper access will allow the agency to move from diagnosis to execution.",
                              "Recommended next step: 30-day transition audit and account takeover sprint."]}
    notes = settle_direction_lines(slide, ins, brief_content(AGENCY, ins))
    assert len(notes) == 1
    assert slide["key_messages"] == ["Recommended next step: 30-day transition audit and account takeover sprint."]

    ins = brief_instructions(XTSY)
    slide = {"key_messages": ["Use arrow visuals rather than hard numbers.", "Category Visibility ↑"]}
    settle_direction_lines(slide, ins, brief_content(XTSY, ins))
    assert slide["key_messages"] == ["Visual: Use arrow visuals rather than hard numbers.", "Category Visibility ↑"]
    assert visual_directions(slide) == ["Use arrow visuals rather than hard numbers."]


def test_a_content_line_that_shares_words_with_the_notes_stays():
    brief = ("Gap 1: CPC above allowable level in both platforms.  "
             "Speaker Notes: Gap 1: CPC above allowable level in both platforms is the headline.")
    ins = brief_instructions(brief)
    slide = {"key_messages": ["Gap 1: CPC above allowable level in both platforms."]}
    settle_direction_lines(slide, ins, brief_content(brief, ins))
    assert slide["key_messages"] == ["Gap 1: CPC above allowable level in both platforms."]


def test_plan_checks_drop_text_that_words_a_brief_instruction():
    outline = {"brief_instructions": {**brief_instructions(AGENCY), "directions": ["Use arrow visuals rather than "
                                                                                    "hard numbers."]}}
    lines = instruction_lines(outline)
    brief = "Recommended next step: 30-day transition audit and account takeover sprint."
    note = comp("closing_note", "caption", {"text": "Note: End with confidence. The audit already shows immediate "
                                                    "improvement areas, and deeper access will allow the agency to "
                                                    "move from diagnosis to execution."})
    hint = comp("visual_hint", "caption", {"text": "Use arrow visuals rather than hard numbers."})
    step = comp("next_step", "narrative", {"text": "30-day transition audit and account takeover sprint."})
    p = plan([note, hint, step])
    assert [x["code"] for x in find_problems(p, brief, lines)] == [PLAN_INSTRUCTION_TEXT] * 2
    finalize_plan(p, brief, lines)
    assert [c["component_id"] for c in p["components"]] == ["next_step"]
    # without the brief's lines nothing changes (old outlines, plan editor)
    assert not is_instruction_text(note["content_data"]["text"], brief)


def test_a_data_note_and_short_lines_are_not_instructions():
    lines = ["End with confidence. The audit already shows immediate improvement areas."]
    assert not is_instruction_text("Note: SOC2 + HIPAA certification targeted for Apr 2027", "", lines)
    assert not matches_instruction("Note: confidence", lines)   # too few words to tell


# ── step 2: a layer beside a component that already shows its content ──────

from src.agents.plan_checks import LAYER_REPEATED, drop_repeated_layers  # noqa: E402

CARDS = comp("cards", "card_grid", {"card_layout": "grid", "cards": [
    {"title": "TRACKING", "bullets": ["Share of Search", "Share of Shelf", "Availability Monitoring"]},
    {"title": "INSIGHTS", "bullets": ["SKU-level performance", "Category trends"]}]}, "supporting")


def test_a_layer_that_only_names_the_visual_is_dropped_beside_cards():
    lay = comp("growth_framework", "layer", {"description": "Visual: Growth Impact Framework"}, "hero")
    p = plan([comp("t", "title", {"title": "x"}), lay, CARDS])
    notes = drop_repeated_layers(p)
    assert len(notes) == 1 and [c["kind"] for c in p["components"]] == ["title", "card_grid"]
    assert p["components"][1]["weight"] == "hero"   # the hero moves to what shows the content
    assert [f["code"] for f in p["plan_flags"]] == [LAYER_REPEATED]


def test_a_layer_that_repeats_the_cards_is_dropped():
    lay = comp("control", "layer", {"center": "Control Tower Dashboard", "nodes": [
        {"label": "TRACKING", "detail": "Share of Search; Share of Shelf; Availability Monitoring"},
        {"label": "INSIGHTS", "detail": "SKU-level performance; Category trends"}]})
    p = plan([lay, CARDS])
    assert drop_repeated_layers(p) and [c["kind"] for c in p["components"]] == ["card_grid"]


def test_a_layer_with_its_own_items_or_alone_stays():
    arch = comp("arch", "layer", {"layers": ["Client apps", "API gateway", "Services", "Data stores"]})
    p = plan([arch, CARDS])
    assert not drop_repeated_layers(p) and len(p["components"]) == 2
    alone = comp("eco", "layer", {"description": "Quick Commerce ecosystem"})
    p = plan([alone, comp("n", "narrative", {"text": "Quick Commerce is a primary channel."})])
    assert not drop_repeated_layers(p) and len(p["components"]) == 2


# ── step 4: a compile past the timeout, and the placeholder in the deck ─────

import json as _json  # noqa: E402
import subprocess  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402

from src.compiler import compiler_client  # noqa: E402


def test_a_result_written_before_the_timeout_is_kept(tmp_path):
    def run(cmd, **kw):
        (tmp_path / "compile-result.json").write_text(_json.dumps({"status": "success", "pptxPath": "x.pptx"}))
        raise subprocess.TimeoutExpired(cmd, 120)
    with patch.object(compiler_client.subprocess, "run", side_effect=run):
        cr = compiler_client.compile_xml("<Slide/>", tmp_path)
    assert cr["ok"] and cr["pptx_path"] == "x.pptx"


def test_a_timeout_without_a_result_still_fails(tmp_path):
    with patch.object(compiler_client.subprocess, "run", side_effect=subprocess.TimeoutExpired("node", 120)):
        with pytest.raises(compiler_client.CompilerError, match="timed out"):
            compiler_client.compile_xml("<Slide/>", tmp_path)


def test_the_placeholder_replaces_the_failed_slides_xml_for_the_deck():
    from src import graph
    from src.agents.deck_nodes import slide_router_node
    state = {"slide_plans": [{"slide_title": "Exact match"}], "current_slide_index": 0, "run_id": "t",
             "current_xml": "<Slide><Text>failed slide</Text></Slide>",
             "normalize_result": {"cleaned_xml": "<Slide><Text>failed slide</Text></Slide>"}}
    with patch.object(graph, "normalize_and_compile", return_value=(True, {"ok": True, "pptx_path": "p.pptx"})):
        out = graph.placeholder_node(state)
    saved = slide_router_node({**state, **out})["completed_slides"][0]
    assert "could not be generated" in saved["xml"] and "failed slide" not in saved["xml"]


# ── step 3: tag chips in narrow cards, one line on every card ─────────────

import re  # noqa: E402

from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.agents.written_lines import drop_shared_card_lines  # noqa: E402
from tests.unit.test_fit_grow_tables import _compile  # noqa: E402

_CHIPS = "".join(f'<Shape shapeType="roundRect" w="{w}" h="26" backgroundColor="$accentSoft" text="{t}" fontSize="14" '
                 f'bold="true" />' for t, w in (("Zepto", 64), ("Blinkit", 78), ("Instamart", 98)))


def _card_row(width, n=4):
    card = (f'<VStack w="{width}" padding="22" gap="10" backgroundColor="$surfaceAlt"><HStack gap="6">{_CHIPS}</HStack>'
            '<Text fontSize="20" bold="true">Visibility</Text></VStack>')
    return ('<Slide><VStack w="1280" h="720" padding="48" gap="28"><Text fontSize="36" bold="true">Levers</Text>'
            f'<HStack gap="18">{card * n}</HStack></VStack></Slide>')


def test_a_row_of_tags_wider_than_its_card_wraps(tmp_path):
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + _card_row(188), encoding="utf-8")
    res = _compile(xml, tmp_path / "out")
    assert len(re.findall(r'<HStack\b[^>]*flexWrap="wrap"', res["xml"])) == 4
    assert any("tags wraps" in r for r in res["fitGrow"])


def test_a_row_of_tags_that_fits_is_left_alone(tmp_path):
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + _card_row(300, 3), encoding="utf-8")
    res = _compile(xml, tmp_path / "out")
    assert "flexWrap" not in res["xml"]


def test_a_composed_line_on_every_card_is_removed():
    cards = [{"title": t, "body": "Applies to: Zepto · Blinkit · Instamart"} for t in
             ("Visibility", "Conversion", "Repeat Purchase", "Market Expansion")]
    p = plan([comp("m", "card_grid", {"card_layout": "grid", "cards": cards})])
    assert drop_shared_card_lines(p, "Rows: Visibility Conversion Repeat Purchase Market Expansion  Columns: Zepto "
                                     "Blinkit Instamart")
    assert all("body" not in c for c in cards)


def test_a_line_the_brief_writes_or_a_line_on_some_cards_stays():
    cards = [{"title": t, "body": "Status: on track"} for t in ("API", "Web", "Mobile")]
    p = plan([comp("s", "card_grid", {"cards": cards})])
    assert not drop_shared_card_lines(p, "API - Status: on track. Web - Status: on track. Mobile - Status: on track.")
    cards = [{"title": "A", "bullets": ["x one", "shared"]}, {"title": "B", "bullets": ["shared"]},
             {"title": "C", "body": "own line"}]
    p = plan([comp("s", "card_grid", {"cards": cards})])
    assert not drop_shared_card_lines(p, "") and cards[0]["bullets"] == ["x one", "shared"]
