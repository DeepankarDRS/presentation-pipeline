"""look5 (2026-11-13): text on colour fills reads by real contrast; a dark item code drew from an explicit mark is kept
by the one-dark-panel-per-deck rule."""
from src.compiler.ink_on_fill import readable_on_colour_fills
from src.compiler.normalizer import soften_dark_panels

THEME = ('<Theme textMain="111827" surface="FFFFFF" surfaceAlt="F8FAFC" onPanelDark="FFFFFF" onAccent="FFFFFF" '
         'panelDark="16202E" accentSoft="DBEAFE" chart1="2563EB" chart4="38BDF8" step2="BFDBFE" onStep2="111827" '
         'inkLight="FFFFFF" inkDark="000000" textMuted="6B7280"/>')


def slide(inner: str) -> str:
    return f'<Slide><VStack backgroundColor="$surface">{inner}</VStack></Slide>'


def test_white_head_text_on_a_light_category_colour_turns_dark():
    xml = slide('<VStack backgroundColor="$chart4"><Text color="$inkLight" bold="true">Market</Text>'
                '<Icon name="map" color="$inkLight"/></VStack>')
    out, n = readable_on_colour_fills(xml, THEME)
    assert n == 2 and out.count('color="$textMain"') == 2


def test_readable_text_and_plain_fills_are_left_alone():
    dark = slide('<VStack backgroundColor="$chart1"><Text color="$inkLight" fontSize="24">Visibility</Text></VStack>')
    assert readable_on_colour_fills(dark, THEME) == (dark, 0)
    plain = slide('<VStack backgroundColor="$surfaceAlt"><Text color="$textMuted">body</Text></VStack>')
    assert readable_on_colour_fills(plain, THEME) == (plain, 0)
    assert readable_on_colour_fills(dark, "") == (dark, 0)   # no theme: nothing judged


def test_a_step_fill_takes_its_own_ink():
    xml = slide('<VStack backgroundColor="$step2"><Text color="$onPanelDark">Phase 1</Text></VStack>')
    out, n = readable_on_colour_fills(xml, THEME)
    assert n == 1 and 'color="$onStep2"' in out


def test_dark_card_drawn_from_a_mark_is_kept_free_panel_softened():
    card = '<VStack id="card-plan-2" backgroundColor="$panelDark"><Text color="$onPanelDark">Month 3</Text></VStack>'
    tile = ('<VStack backgroundColor="$panelDark"><Text id="kpil-k-1" color="$onPanelDark">GM</Text>'
            '<Text id="kpiv0-k-1" color="$onPanelDark">72%</Text></VStack>')
    free = '<VStack backgroundColor="$textMain" padding="22"><Text color="$surface">So what</Text></VStack>'
    out, n = soften_dark_panels(slide(card + tile + free))
    assert n == 1
    assert 'id="card-plan-2" backgroundColor="$panelDark"' in out and '<VStack backgroundColor="$panelDark">' in out
    assert 'backgroundColor="$accentSoft" padding="22"' in out and 'color="$textMain">So what' in out
