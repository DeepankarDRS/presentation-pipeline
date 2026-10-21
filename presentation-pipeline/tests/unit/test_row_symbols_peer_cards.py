"""Short symbols between w="max" boxes get a width; same-styled cards in one row share one height (2026-10-21).

XTSY 4 (gpt-6.1-sol): a "→" Text between w="max" phase cards was squeezed to 0 px ("width must be a finite positive
EMU value"); the repair pinned widths and set alignItems="start", leaving the cards at unequal heights.
"""

from src.compiler.grow_fallback import size_row_symbols, stretch_peer_cards
from src.compiler.normalizer import normalize_xml
from src.compiler.repair_guidance import SQUEEZE_GUIDANCE, build_error_guidance

CARD = '<VStack w="max" padding="18" backgroundColor="$surfaceAlt" border.color="$border" border.width="1"><Text>{}</Text></VStack>'


def _row(align: str = "stretch", arrow: str = '<Text fontSize="20" alignSelf="center">→</Text>') -> str:
    cards = [CARD.format("Phase one with a long line of text"), CARD.format("Phase two")]
    return f'<HStack gap="14" alignItems="{align}">{cards[0]}{arrow}{cards[1]}</HStack>'


def test_arrow_between_w_max_cards_gets_a_width_from_its_font_size():
    xml, note = size_row_symbols(_row())
    assert note and '<Text w="24" fontSize="20" alignSelf="center">→</Text>' in xml


def test_arrow_with_a_width_or_long_text_is_left_alone():
    assert size_row_symbols(_row(arrow='<Text w="20" fontSize="20">→</Text>'))[1] is None
    assert size_row_symbols(_row(arrow='<Text fontSize="20">then</Text>'))[1] is None


def test_arrow_in_a_wrapping_row_is_left_alone():
    assert size_row_symbols(_row().replace('alignItems="stretch"', 'alignItems="stretch" flexWrap="wrap"'))[1] is None


def test_arrow_in_a_row_without_w_max_is_left_alone():
    xml = '<HStack><VStack w="200" backgroundColor="$surface"><Text>a</Text></VStack><Text>→</Text></HStack>'
    assert size_row_symbols(xml)[1] is None


def test_row_of_same_styled_cards_aligned_start_stretches_and_the_arrow_keeps_its_place():
    xml, note = stretch_peer_cards(_row(align="start", arrow='<Text w="20">→</Text>'))
    assert note and 'alignItems="stretch"' in xml and '<Text alignSelf="start" w="20">→</Text>' in xml


def test_a_focus_card_with_another_fill_still_counts_as_a_peer():
    dark = CARD.replace("$surfaceAlt", "$panelDark").format("Focus")
    xml = f'<HStack alignItems="start">{CARD.format("a")}{dark}</HStack>'
    assert stretch_peer_cards(xml)[1]


def test_cards_of_different_structure_or_with_a_height_are_left_alone():
    other = '<VStack padding="8" backgroundColor="$surface"><Text>b</Text></VStack>'
    assert stretch_peer_cards(f'<HStack alignItems="start">{CARD.format("a")}{other}</HStack>')[1] is None
    tall = CARD.replace('w="max"', 'w="max" h="300"').format("b")
    assert stretch_peer_cards(f'<HStack alignItems="start">{CARD.format("a")}{tall}</HStack>')[1] is None


def test_normalizer_reports_both_codes():
    slide = f'<Slide><VStack w="1280" h="720">{_row(align="start")}</VStack></Slide>'
    codes = {i["code"] for i in normalize_xml(slide)["issues"]}
    assert {"ROW_SYMBOL_SIZED", "PEER_CARDS_STRETCHED"} <= codes


def test_squeeze_error_gets_width_only_repair_guidance():
    diag = {"type": "RENDER_ERROR", "message": "addTextBox: width must be a finite positive EMU value"}
    guidance = build_error_guidance([], [diag])
    assert SQUEEZE_GUIDANCE in guidance and "Keep every alignItems" in guidance
