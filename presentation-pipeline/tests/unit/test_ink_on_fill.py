"""Text ink that cannot read on its light fill (look2 blind marks 2026-11-13: pairs 26, 27, 17, 31)."""
from src.compiler.ink_on_fill import fix_ink_on_fill
from src.compiler.normalizer import normalize_xml


def test_dark_card_inks_on_a_light_fill_become_ink():
    xml = ('<Slide><VStack backgroundColor="$accentSoft"><Text color="$accentText">Phase 4</Text>'
           '<Ul color="$onPanelDark"><Li>Portfolio scaling</Li></Ul><Text color="$onPanelDark">03</Text></VStack></Slide>')
    out, n = fix_ink_on_fill(xml)
    assert n == 2
    assert '<Ul color="$textMain">' in out and '<Text color="$textMain">03</Text>' in out
    assert '<Text color="$accentText">Phase 4</Text>' in out


def test_tint_token_as_text_colour_becomes_its_text_token():
    xml = ('<Slide><VStack backgroundColor="$accentSoft"><Text color="$textMain">unlocked through '
           '<Span color="$positiveSoft">visibility</Span></Text></VStack></Slide>')
    out, n = fix_ink_on_fill(xml)
    assert n == 1 and '<Span color="$positiveText">' in out


def test_text_on_dark_fills_and_layers_and_marks_is_left_alone():
    xml = ('<Slide><VStack backgroundColor="$panelDark"><Text color="$onPanelDark">62%</Text>'
           '<Span color="$positiveSoft">up</Span></VStack>'
           '<Layer backgroundColor="$surfaceAlt"><Shape fill.color="$accent"/><Text color="$surfaceAlt">Web</Text></Layer>'
           '<VStack backgroundColor="$surface"><Text color="$textMain"><Mark color="$accentSoft">key</Mark></Text>'
           '<HStack><Shape backgroundColor="$accent"/><Icon name="rocket" color="$onAccent"/></HStack></VStack>'
           '<Table header.backgroundColor="$panelDark" header.color="$surface"/></Slide>')
    out, n = fix_ink_on_fill(xml)
    assert n == 0 and out == xml


def test_nearest_fill_wins_and_the_slide_is_a_surface():
    xml = ('<Slide><VStack backgroundColor="$panelDark"><VStack backgroundColor="$surfaceAlt">'
           '<Text color="$surfaceAlt">ARR</Text></VStack><Text color="$surface">on dark</Text></VStack>'
           '<Text color="$onAccent">loose</Text></Slide>')
    out, n = fix_ink_on_fill(xml)
    assert n == 2
    assert '<Text color="$textMain">ARR</Text>' in out and '<Text color="$surface">on dark</Text>' in out
    assert '<Text color="$textMain">loose</Text>' in out


def test_normalizer_reports_it():
    res = normalize_xml('<Slide><VStack backgroundColor="$accentSoft"><Text color="$onPanelDark">x</Text></VStack></Slide>')
    assert any(i["code"] == "INK_ON_FILL" for i in res["issues"])
    assert '$onPanelDark' not in res["cleaned_xml"]


def test_light_focus_card_ink_from_cards_is_kept():
    """cards.assemble (db9781c) already gives a light-filled focus card light-card ink ($textMuted body);
    fix_ink_on_fill must leave that alone, and must not touch a dark fill's light ink."""
    from tests.unit.test_cards import card_el, run
    for fill in ("$accentSoft", "$surfaceAlt", "$negativeDark"):
        xml = run(f'<CardGrid ref="plan"><Card ref="plan.3" backgroundColor="{fill}"/></CardGrid>')["xml"]
        out, n = fix_ink_on_fill(xml)
        assert n == 0 and out == xml, fill
        if fill.endswith("Soft"):
            inks = {e.get("color") for e in card_el(out, "plan", 3).iter("Text")}
            assert "$onPanelDark" not in inks and "$onAccent" not in inks
