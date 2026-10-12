"""KPI element refs (docs/kpi-node-pilot-2026-10-11.md §1 / §3): grammar, every validation code, verbatim
fill, one number size per component, tone and dark-fill colour defaults, token-only colours, the value
parser, panelDark tokens, the generator prompt under POM_BLOCKS=kpi and the validator hook."""

import re

import pytest
import yaml

from src.compiler.nodes import element_refs as E
from src.compiler.palette_tokens import TEXT_MIN, contrast, derive_tokens
from src.compiler.value_parts import is_sentence, split_value, unit_px, unit_share

PLAN = {"components": [
    {"component_id": "title", "kind": "title", "count": 1},
    {"component_id": "kpis", "kind": "kpi_row", "count": 3, "design_hint": "highlight Blended ROAS as the hero",
     "content_data": {"kpi_labels": ["Spend", "Revenue", "Blended ROAS"],
                      "kpi_values": ["₹114.9L", "₹37.4L", "0.33x"],
                      "kpi_deltas": ["Amazon ₹29.4L", "", "ACOS ~307%"]}},
]}


def tile(i, extra="", note=True, value_attrs=""):
    n = f'<Text ref="kpis.{i}.note"/>' if note else ""
    return (f'<VStack grow="1" padding="18" backgroundColor="$surfaceAlt"{extra}><Text ref="kpis.{i}.label"/>'
            f'<Text ref="kpis.{i}.value"{value_attrs}/>{n}</VStack>')


def slide(body):
    return f'<Slide><VStack w="1280" h="720" padding="40"><HStack h="200" gap="12">{body}</HStack></VStack></Slide>'


def value_tag(xml, vid):
    return re.search(rf'<Text[^>]*id="{vid}"[^>]*>', xml).group(0)


def codes(res):
    return [i["code"] for i in res["issues"]]


def full():
    return slide(tile(0) + tile(1, note=False) + tile(2))


# ── grammar + fill ────────────────────────────────────────────────────────────

def test_full_skeleton_fills_verbatim_with_no_issues():
    res = E.fill_refs(full(), PLAN)
    assert res["ok"] and res["issues"] == [], res["issues"]
    xml = res["xml"]
    assert "ref=" not in xml
    for text in ("Spend", "Revenue", "Blended ROAS", "Amazon ₹29.4L", "ACOS ~307%"):
        assert f">{text}</Text>" in xml, text
    assert '>₹114.9<Span fontSize="17">L</Span></Text>' in xml   # one-letter units: 0.6 x 28
    assert '>0.33<Span fontSize="17">x</Span></Text>' in xml
    assert res["components"]["kpis"] == {"items": 3, "values_placed": 3, "labels_placed": 3, "notes_placed": 2,
                                        "notes_planned": 2, "bypassed": 0}


def test_values_share_one_start_size_and_carry_peer_ids():
    xml = E.fill_refs(full(), PLAN)["xml"]
    vals = re.findall(r'<Text ([^>]*id="kpiv1-kpis-(\d)"[^>]*)>', xml)
    assert [v[1] for v in vals] == ["0", "1", "2"]
    assert {re.search(r'fontSize="(\d+)"', v[0]).group(1) for v in vals} == {str(E.VALUE_PX)}
    assert all('bold="true"' in v[0] for v in vals)


def test_hero_only_on_the_focus_value():
    xml = slide(tile(0, value_attrs=' size="hero"') + tile(1, note=False) + tile(2, value_attrs=' size="hero"'))
    res = E.fill_refs(xml, PLAN)
    assert 'id="kpih1-kpis-2"' in res["xml"] and f'fontSize="{E.HERO_PX}"' in res["xml"]
    assert 'id="kpiv1-kpis-0"' in res["xml"] and "size=" not in res["xml"]
    assert codes(res) == ["NODE_ATTR_IGNORED"]


def test_a_one_item_kpi_row_is_a_hero():
    plan = {"components": [{"component_id": "hero", "kind": "kpi_row",
                            "content_data": {"kpi_labels": ["ROAS"], "kpi_values": ["0.33x"]}}]}
    res = E.fill_refs('<Slide><VStack><Text ref="hero.0.label"/><Text ref="hero.0.value"/></VStack></Slide>', plan)
    assert res["ok"] and 'id="kpih1-hero-0"' in res["xml"]


def test_label_and_note_sizes_come_from_the_ramp():
    xml = slide(tile(0).replace('<Text ref="kpis.0.label"/>', '<Text ref="kpis.0.label" fontSize="40"/>')
                + tile(1, note=False) + tile(2))
    out = E.fill_refs(xml, PLAN)["xml"]
    assert f'fontSize="{E.LABEL_PX}"' in re.search(r"<Text[^>]*>Spend</Text>", out).group(0)


# ── validation codes ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("ref", ["kpis.3.value", "nope.0.value", "kpis.0.delta", "kpis.value", "title.0.label"])
def test_unknown_ref_is_an_error(ref):
    res = E.fill_refs(full().replace("</HStack>", f'<Text ref="{ref}"/></HStack>'), PLAN)
    assert "NODE_REF_UNKNOWN" in codes(res) and not res["ok"]


def test_ref_on_a_non_text_is_unknown():
    res = E.fill_refs(full().replace("</HStack>", '<VStack ref="kpis.0.value"/></HStack>'), PLAN)
    assert "NODE_REF_UNKNOWN" in codes(res)


def test_duplicate_ref_is_an_error():
    res = E.fill_refs(full().replace("</HStack>", '<Text ref="kpis.0.value"/></HStack>'), PLAN)
    assert codes(res) == ["NODE_REF_DUPLICATE"] and not res["ok"]


def test_missing_value_is_an_error_missing_label_a_warning():
    xml = slide(tile(0) + tile(1, note=False) + '<VStack><Text ref="kpis.2.note"/></VStack>')
    res = E.fill_refs(xml, PLAN)
    assert "NODE_ITEM_MISSING" in codes(res) and not res["ok"]
    missing = [i for i in res["issues"] if i["code"] == "NODE_FIELD_MISSING"]
    assert [i["ref"] for i in missing] == ["kpis.2.label"] and missing[0]["severity"] == "warning"


def test_missing_note_is_a_warning():
    res = E.fill_refs(slide(tile(0, note=False) + tile(1, note=False) + tile(2)), PLAN)
    assert res["ok"] and [i["ref"] for i in res["issues"]] == ["kpis.0.note"]


def test_typed_value_is_bypassed_not_missing():
    xml = slide(tile(0) + tile(1, note=False) + '<VStack><Text ref="kpis.2.label"/><Text fontSize="40">0.33x</Text>'
                '<Text ref="kpis.2.note"/></VStack>')
    res = E.fill_refs(xml, PLAN)
    assert res["ok"] and codes(res) == ["NODE_BYPASSED"] and res["components"]["kpis"]["bypassed"] == 1


def test_attrs_ignored_font_size_text_and_literal_colour():
    xml = slide(tile(0, value_attrs=' fontSize="60" color="#FF0000"') + tile(1, note=False) + tile(2))
    xml = xml.replace('<Text ref="kpis.1.value"/>', '<Text ref="kpis.1.value">₹99L</Text>')
    res = E.fill_refs(xml, PLAN)
    msgs = [i["message"] for i in res["issues"] if i["code"] == "NODE_ATTR_IGNORED"]
    assert len(msgs) == 3, msgs
    assert "#FF0000" not in res["xml"] and "₹99L" not in res["xml"] and 'fontSize="60"' not in res["xml"]


def test_note_ref_without_a_plan_note_is_removed():
    res = E.fill_refs(slide(tile(0) + tile(1) + tile(2)), PLAN)
    assert res["ok"] and codes(res) == ["NODE_ATTR_IGNORED"]
    assert "kpis.1.note" not in res["xml"]


def test_focus_drawn_apart_but_unnamed_is_reported():
    xml = slide(tile(0, extra=' borderRadius="8"').replace("$surfaceAlt", "$panelDark") + tile(1, note=False) + tile(2))
    res = E.fill_refs(xml, PLAN)   # item 0 stands apart, the plan singles out item 2
    assert [i["code"] for i in res["issues"]] == ["NODE_FOCUS_UNNAMED"] and res["issues"][0]["severity"] == "report"
    named = slide(tile(0) + tile(1, note=False) + tile(2).replace("$surfaceAlt", "$panelDark"))
    assert E.fill_refs(named, PLAN)["issues"] == []


def test_kpi_tiles_lose_border_radius_other_cards_keep_it():
    xml = slide(tile(0, extra=' borderRadius="12"') + tile(1, note=False) + tile(2, extra=' borderRadius="8"')
                + '<VStack backgroundColor="$surfaceAlt" borderRadius="12"><Text>Takeaway</Text></VStack>')
    out = E.fill_refs(xml, PLAN)["xml"]
    assert out.count("borderRadius") == 1 and 'borderRadius="12"><Text>Takeaway' in out


def test_already_filled_values_count_as_placed():
    """A repaired slide comes back filled (no refs): its values are not 'missing'."""
    filled = E.fill_refs(full(), PLAN)["xml"]
    again = E.fill_refs(filled, PLAN)
    assert again["ok"] and "NODE_ITEM_MISSING" not in codes(again)


# ── colours ──────────────────────────────────────────────────────────────────

def test_role_default_colours():
    out = E.fill_refs(full(), PLAN)["xml"]
    assert re.search(r'<Text[^>]*color="\$accentText"[^>]*>Spend<', out)
    assert 'color="$textMain"' in value_tag(out, "kpiv1-kpis-0")
    assert re.search(r'<Text[^>]*color="\$textMuted"[^>]*>Amazon', out)


def test_tone_ink_and_own_token_wins():
    plan = {"components": [dict(PLAN["components"][1], content_data=dict(PLAN["components"][1]["content_data"],
                                                                        kpi_tones=["", "good", "bad"]))]}
    xml = full().replace('<Text ref="kpis.2.label"/>', '<Text ref="kpis.2.label" color="$warningText"/>')
    out = E.fill_refs(xml, plan)["xml"]
    assert 'color="$positiveText"' in value_tag(out, "kpiv1-kpis-1")
    assert 'color="$negativeText"' in value_tag(out, "kpiv1-kpis-2")
    assert re.search(r'color="\$warningText"[^>]*>Blended ROAS<', out)


def test_text_on_a_dark_fill_defaults_to_light_ink():
    xml = slide(tile(0) + tile(1, note=False) + tile(2).replace("$surfaceAlt", "$panelDark"))
    out = E.fill_refs(xml, PLAN)["xml"]
    assert 'color="$onPanelDark"' in value_tag(out, "kpiv1-kpis-2")
    assert re.search(r'color="\$onPanelDark"[^>]*>Blended ROAS<', out)


def test_fill_writes_no_literal_colour():
    out = E.fill_refs(full(), PLAN)["xml"]
    assert all(c.startswith("$") for c in re.findall(r'color="([^"]*)"', out))


_PALETTES = yaml.safe_load(open("src/knowledge/theme/palettes.yaml", encoding="utf-8"))["palettes"]


@pytest.mark.parametrize("name", sorted(_PALETTES))
def test_panel_dark_reads_on_every_palette(name):
    p = _PALETTES[name]
    d = derive_tokens(p)
    assert contrast(d["panelDark"], d["onPanelDark"]) >= TEXT_MIN
    # dark on every palette: darker than the light ink it carries
    assert contrast(d["panelDark"], "FFFFFF") >= TEXT_MIN


def test_authored_panel_tokens_win():
    p = dict(_PALETTES["graphite-dark"], panelDark="101010", onPanelDark="F0F0F0")
    d = derive_tokens(p)
    assert (d["panelDark"], d["onPanelDark"]) == ("101010", "F0F0F0")


def test_soften_dark_panels_also_takes_panel_dark():
    from src.compiler.normalizer import has_dark_panel, soften_dark_panels
    xml = '<VStack backgroundColor="$panelDark"><Text color="$onPanelDark">x</Text></VStack>'
    out, n = soften_dark_panels(xml)
    assert has_dark_panel(xml) and n == 1 and "$panelDark" not in out and 'color="$textMain"' in out


# ── value parser (V15) ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("value,parts", [
    ("$48.2M", ("$48.2", "M")), ("₹4.2 Cr", ("₹4.2", " Cr")), ("114%", ("114", "%")), ("0.33x", ("0.33", "x")),
    ("-1.4 pts", ("-1.4", " pts")), ("14 months", ("14", " months")), ("15 min/wk", ("15", " min/wk")),
    ("₹1,234", ("₹1,234", "")), ("₹29.4L / ₹85.5L", ("₹29.4L / ₹85.5L", "")),
    ("Q3 FY26", ("Q3 FY26", "")), ("  7.5×  ", ("7.5", "×")),
])
def test_split_value_is_verbatim(value, parts):
    assert split_value(value) == parts
    assert "".join(split_value(value)) == value.strip()


def test_unit_px():
    assert unit_px(44) == 20
    assert unit_px(28, 0.42) == 14   # never below the floor


@pytest.mark.parametrize("values,share", [
    (["114%", "0.33x", "$48.2M"], 0.6), (["₹4.2 Cr", "114%"], 0.5), (["-1.4 pts"], 0.5),
    (["14 months", "72.1%"], 0.42), (["Q3 FY26"], 0.45),
])
def test_unit_share_follows_the_longest_unit(values, share):
    assert unit_share(values) == share


@pytest.mark.parametrize("value,prose", [
    ("Generic search consumed the largest budget pool and returned around 0.29x ROAS.", True),
    ("Brand campaigns were strong", True), ("0.33x", False), ("14 months", False), ("Q3 FY26", False),
    ("₹29.4L / ₹85.5L", False), ("", False),
])
def test_is_sentence(value, prose):
    assert is_sentence(value) is prose


def test_sentence_value_is_drawn_as_body_text():
    plan = {"components": [{"component_id": "k", "kind": "kpi_row", "content_data": {
        "kpi_labels": ["Generic search", "Brand"],
        "kpi_values": ["Generic search consumed the largest budget pool and returned around 0.29x ROAS.", "0.99x"]}}]}
    xml = ('<Slide><VStack><HStack><VStack><Text ref="k.0.label"/><Text ref="k.0.value" bold="true"/></VStack>'
           '<VStack><Text ref="k.1.label"/><Text ref="k.1.value"/></VStack></HStack></VStack></Slide>')
    res = E.fill_refs(xml, plan)
    assert res["ok"] and "NODE_VALUE_TEXT" in codes(res)
    prose = re.search(r"<Text[^>]*>Generic search consumed[^<]*</Text>", res["xml"]).group(0)
    assert f'fontSize="{E.BODY_PX}"' in prose and "bold" not in prose and "kpiv" not in prose
    assert 'id="kpiv1-k-1"' in res["xml"]


def test_plan_check_reasks_on_sentence_kpi_values():
    from src.agents.plan_checks import KPI_VALUE_TEXT, REASK_CODES, finalize_plan, find_problems, reask_context
    plan = {"components": [{"component_id": "k", "kind": "kpi_row", "count": 2, "content_data": {
        "kpi_labels": ["Generic search", "Brand"],
        "kpi_values": ["Generic search consumed the largest budget pool.", "0.99x"]}}]}
    problems = find_problems(plan, "brief")
    assert [p["code"] for p in problems] == [KPI_VALUE_TEXT] and KPI_VALUE_TEXT in REASK_CODES
    assert "card_grid" in reask_context(problems)["directive"]
    finalize_plan(plan, "brief")
    assert any(f["code"] == KPI_VALUE_TEXT for f in plan["plan_flags"])
    ok = {"components": [dict(plan["components"][0], content_data={"kpi_labels": ["A"], "kpi_values": ["0.99x"]})]}
    assert not find_problems(ok, "brief")


# ── prompt line, generator, validator ─────────────────────────────────────────

def test_prompt_line_has_ids_lengths_focus_and_no_values():
    line = E.prompt_line(PLAN["components"][1])
    assert '<Text ref="kpis.<index>.<field>"/>' in line and "3 items" in line and "no note for item 1" in line
    assert 'Focus item: 2 ("Blended ROAS")' in line and "$panelDark" in line and "label row" in line
    for v in ("₹114.9L", "₹37.4L", "0.33x", "Amazon ₹29.4L", "ACOS"):
        assert v not in line, v


def test_mode_reads_pom_blocks(monkeypatch):
    monkeypatch.delenv("POM_BLOCKS", raising=False)
    assert E.mode() == "kpi"   # the default since 2026-10-11
    monkeypatch.setenv("POM_BLOCKS", "off")
    assert E.mode() == "off"
    monkeypatch.setenv("POM_BLOCKS", "slots")
    assert E.mode() == "kpi"


def _gen_state():
    from src.state import initial_state
    state = initial_state(run_id="kpi-ref-test", raw_request="QBR", deck_min_threshold=0)
    state["slide_plans"] = [{"slide_index": 0, "slide_title": "ROAS fell", "components": PLAN["components"],
                             "content_data": {"kpi_values": ["₹114.9L"], "title": "ROAS fell"}}]
    state["contract"] = {"theme_element": "<Theme />"}
    return state


def test_generator_prompt_under_kpi_has_refs_not_values(monkeypatch):
    from src.agents.generator import _render_prompts
    monkeypatch.setenv("POM_BLOCKS", "kpi")
    _, user = _render_prompts(_gen_state())
    assert "KPI REFS for kpis" in user and "₹114.9L" not in user and "0.33x" not in user
    monkeypatch.setenv("POM_BLOCKS", "off")
    _, user = _render_prompts(_gen_state())
    assert "KPI REFS" not in user and "₹114.9L" in user


def test_validator_blocks_on_ref_errors_and_fills_otherwise(monkeypatch, tmp_path):
    from src.agents import validator
    monkeypatch.setenv("POM_BLOCKS", "kpi")
    state = _gen_state()
    state["current_xml"] = full().replace("</HStack>", '<Text ref="kpis.9.value"/></HStack>')
    out = validator.validator_node(state)
    assert not out["compile_result"]["ok"] and out["compile_result"]["retryable"]
    assert out["compile_result"]["diagnostics"][0]["type"] == "NODE_REF_UNKNOWN"

    seen = {}

    def stop(xml, out_dir):
        seen["xml"] = xml
        return {"ok": False, "diagnostics": [{"type": "X", "message": "stop"}], "warnings": []}
    monkeypatch.setattr(validator, "validate_xml", stop)
    state["current_xml"] = full()
    out = validator.validator_node(state)
    assert "ref=" not in seen["xml"] and ">Blended ROAS</Text>" in seen["xml"]


# ── fit-grow: the values of one component are peers wherever they sit ───────────

def test_fit_grow_sizes_ref_values_as_one_group_and_the_hero_alone(tmp_path):
    from tests.unit.test_fit_grow_tables import _compile
    plan = {"components": [{"component_id": "k", "kind": "kpi_row", "design_hint": "highlight ROAS as the hero",
                            "content_data": {"kpi_labels": ["Spend", "Revenue", "ROAS", "Orders", "AOV"],
                                             "kpi_values": ["₹114.9L", "₹37.4L", "0.33x", "12,840", "₹291"]}}]}
    small = lambda i, w: (f'<VStack w="{w}" padding="16" gap="6" backgroundColor="$surfaceAlt">'
                          f'<Text ref="k.{i}.label"/><Text ref="k.{i}.value"/></VStack>')
    skel = ('<Slide><VStack w="1280" h="720" padding="40" gap="20" backgroundColor="$surface">'
            '<Text fontSize="36" bold="true" color="$textMain">ROAS is 0.33x</Text><HStack grow="1" gap="12" alignItems="stretch">'
            '<VStack w="40%" padding="28" backgroundColor="$panelDark" justifyContent="center">'
            '<Text ref="k.2.label"/><Text ref="k.2.value" size="hero"/></VStack>'
            f'<VStack grow="1" gap="12"><HStack grow="1" gap="12" alignItems="stretch">{small(0, "40%")}{small(1, "58%")}</HStack>'
            f'<HStack grow="1" gap="12" alignItems="stretch">{small(3, "58%")}{small(4, "40%")}</HStack></VStack>'
            '</HStack></VStack></Slide>')
    res = E.fill_refs(skel, plan)
    assert res["ok"], res["issues"]
    from src.agents.style_resolver import resolve_theme
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + "\n" + res["xml"], encoding="utf-8")
    out = _compile(xml, tmp_path / "o")
    peers = {int(v) for v in re.findall(r'<Text[^>]*fontSize="(\d+)"[^>]*id="kpiv1-k-\d"', out["xml"])}
    hero = [int(v) for v in re.findall(r'<Text[^>]*fontSize="(\d+)"[^>]*id="kpih1-k-2"', out["xml"])]
    assert len(peers) == 1 and peers.pop() > E.VALUE_PX, out["fitGrow"]
    assert hero and hero[0] > E.HERO_PX, out["fitGrow"]
    assert not any(w["code"] == "WORD_TOO_WIDE" for w in out.get("warnings", [])), out.get("warnings")


def test_fit_grow_keeps_a_lower_weight_component_at_or_below_the_hero_row(tmp_path):
    """Paid check 2026-10-11: a "peer" row of two wide tiles grew to 92 px under the "hero" row at 72."""
    from src.agents.style_resolver import resolve_theme
    from tests.unit.test_fit_grow_tables import _compile
    plan = {"components": [
        {"component_id": "top", "kind": "kpi_row", "weight": "hero", "content_data": {
            "kpi_labels": ["Spend", "Revenue", "ROAS"], "kpi_values": ["₹114.9L", "₹37.4L", "0.33x"]}},
        {"component_id": "low", "kind": "kpi_row", "weight": "peer", "content_data": {
            "kpi_labels": ["Amazon ROAS", "Zepto ROAS"], "kpi_values": ["0.34x", "0.32x"]}}]}
    tile = lambda c, i, w: (f'<VStack w="{w}" padding="20" gap="8" backgroundColor="$surfaceAlt" justifyContent="center">'
                            f'<Text ref="{c}.{i}.label"/><Text ref="{c}.{i}.value"/></VStack>')
    skel = ('<Slide><VStack w="1280" h="720" padding="48" gap="20" backgroundColor="$surface">'
            '<Text fontSize="36" bold="true" color="$textMain">Spend is at scale</Text>'
            f'<HStack grow="3" gap="18" alignItems="stretch">{"".join(tile("top", i, "max") for i in range(3))}</HStack>'
            f'<HStack gap="18" alignItems="stretch">{"".join(tile("low", i, "max") for i in range(2))}</HStack>'
            '</VStack></Slide>')
    res = E.fill_refs(skel, plan)
    assert 'id="kpiv0-top-0"' in res["xml"] and 'id="kpiv1-low-0"' in res["xml"]
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + "\n" + res["xml"], encoding="utf-8")
    out = _compile(xml, tmp_path / "o")
    size = lambda pre: {int(v) for v in re.findall(rf'<Text[^>]*fontSize="(\d+)"[^>]*id="{pre}-\d"', out["xml"])}
    top, low = size("kpiv0-top"), size("kpiv1-low")
    assert len(top) == 1 and len(low) == 1 and max(low) <= max(top), (top, low, out["fitGrow"])
    assert max(low) > E.VALUE_PX, out["fitGrow"]   # the content-sized row still grew


# ── after the full decks (2026-10-12): dark-tile colours, rows that span, icons above labels ──────

def test_kpi_text_on_a_dark_tile_gets_the_readable_colour():
    """QBR deck: the LLM wrote $accentText for ARR and a green delta on a $textMain tile (LOW_CONTRAST 2)."""
    dark = tile(0).replace('backgroundColor="$surfaceAlt"', 'backgroundColor="$textMain"').replace(
        'ref="kpis.0.value"', 'ref="kpis.0.value" color="$accentText"').replace(
        'ref="kpis.0.note"', 'ref="kpis.0.note" color="$positiveText"').replace(
        'ref="kpis.0.label"', 'ref="kpis.0.label" color="$surfaceAlt"')
    res = E.fill_refs(slide(dark + tile(1, note=False) + tile(2)), PLAN)
    assert value_tag(res["xml"], "kpiv1-kpis-0").count('color="$surface"') == 1
    assert '<Text color="$surfaceAlt" fontSize="16">Spend</Text>' in res["xml"]   # a colour that reads stays
    assert sum(i["code"] == "NODE_ATTR_IGNORED" for i in res["issues"]) == 2, res["issues"]


def test_a_row_of_content_sized_tiles_spans_its_width_and_loses_its_spacer():
    """CHEFFIN 4 + 3 grid: w="max" tiles and an empty <VStack w="max"/> left the row of 3 short."""
    sized = lambda i, **kw: tile(i, extra=' w="max"', **kw)
    xml = slide(sized(0) + sized(1, note=False) + sized(2) + '<VStack w="max"/>')
    out = E.fill_refs(xml, PLAN)["xml"]
    assert '<VStack w="max"/>' not in out and out.count('grow="1"') == 3
    fixed = slide(tile(0, extra=' w="30%"') + tile(1, note=False) + tile(2) + '<VStack w="max"/>')
    assert '<VStack w="max"/>' in E.fill_refs(fixed, PLAN)["xml"]   # widths the LLM set: row left alone


def test_fit_grow_puts_the_icon_above_the_label_in_a_sparse_tile(tmp_path):
    """CHEFFIN slide 1: five narrow tiles in a grow="3" row, numbers bound by the width, half empty."""
    from src.agents.style_resolver import resolve_theme
    from tests.unit.test_fit_grow_tables import _compile
    plan = {"components": [{"component_id": "k", "kind": "kpi_row", "content_data": {
        "kpi_labels": ["Combined spend", "Combined revenue", "Combined ROAS", "FLIPCART ROAS", "ZAROMA ROAS"],
        "kpi_values": ["₹114.9L", "₹37.4L", "0.33x", "0.34x", "0.32x"]}}]}
    t = lambda i: (f'<VStack w="max" padding="20" gap="8" backgroundColor="$surfaceAlt" justifyContent="center">'
                   f'<HStack gap="8" alignItems="center"><Icon name="percent" size="24" color="$accent"/>'
                   f'<Text ref="k.{i}.label"/></HStack><Text ref="k.{i}.value"/></VStack>')
    skel = ('<Slide><VStack w="1280" h="720" padding="48" gap="28" backgroundColor="$surface">'
            '<Text fontSize="36" bold="true" color="$textMain">Spending at scale</Text>'
            f'<HStack grow="3" gap="18" alignItems="stretch">{"".join(t(i) for i in range(5))}</HStack>'
            '<VStack grow="1" padding="22" backgroundColor="$surfaceAlt"><Text fontSize="16" color="$textMain">'
            'Both platforms show the same issue: CPC is too high for AOV and CVR.</Text></VStack></VStack></Slide>')
    xml = tmp_path / "t.xml"
    xml.write_text(resolve_theme("corporate-slate")["element"] + "\n" + E.fill_refs(skel, plan)["xml"], encoding="utf-8")
    out = _compile(xml, tmp_path / "o")
    assert out["xml"].count('<VStack alignItems="start"') == 5 and "<HStack gap=\"8\"" not in out["xml"], out["fitGrow"]
    assert out["xml"].count('<Text alignSelf="stretch"') == 5


def test_validator_keeps_the_llm_xml_before_the_fill(monkeypatch, tmp_path):
    from src.agents import validator
    monkeypatch.setenv("POM_BLOCKS", "kpi")
    monkeypatch.setattr(validator, "validate_xml",
                        lambda xml, out_dir: {"ok": False, "diagnostics": [{"type": "X", "message": "stop"}], "warnings": []})
    state = _gen_state()
    state["run_id"] = f"kpi-ref-test-{tmp_path.name}"
    state["current_xml"] = full()
    validator.validator_node(state)
    from pathlib import Path
    saved = Path(validator.__file__).resolve().parents[2] / "output" / "runs" / state["run_id"] / "generated.xml"
    try:
        assert saved.read_text(encoding="utf-8") == full()
    finally:
        import shutil
        shutil.rmtree(saved.parent, ignore_errors=True)


def test_a_ref_wrapped_in_a_styled_text_takes_the_wrappers_place():
    """Full decks 2026-10-12: <Text fontSize color><Text ref/></Text> on 2 of 4 KPI slides (INVALID_CHILD,
    then a repair that drew the labels twice)."""
    wrapped = (f'<VStack backgroundColor="$surfaceAlt"><Text fontSize="14" color="$textMuted"><Text ref="kpis.{0}.label"/></Text>'
               f'<Text fontSize="30" bold="true" color="$positiveText"><Text ref="kpis.0.value"/></Text>'
               f'<Text ref="kpis.0.note"/></VStack>')
    res = E.fill_refs(slide(wrapped + tile(1, note=False) + tile(2)), PLAN)
    assert res["ok"] and "</Text></Text>" not in res["xml"]
    assert '<Text fontSize="16" color="$textMuted">Spend</Text>' in res["xml"]
    assert 'color="$positiveText"' in value_tag(res["xml"], "kpiv1-kpis-0")
    assert sum("was wrapped" in i["message"] for i in res["issues"]) == 2
