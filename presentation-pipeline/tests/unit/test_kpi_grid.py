"""KPI_ROWS (src/compiler/kpi_grid.py, 2026-10-07) and the generator's layout rules."""

from src.agents.capacity import capacity, layout_rules
from src.compiler.kpi_grid import kpi_rows


def _tile(label: str, value: str) -> str:
    return (f'<VStack w="max" padding="18" backgroundColor="$surfaceAlt"><Text fontSize="14">{label}</Text>'
            f'<Text fontSize="34" bold="true">{value}</Text></VStack>')


def _slide(n: int, extra: str = "") -> str:
    tiles = "".join(_tile(f"M{i}", f"{i}2.1%") for i in range(n))
    return ('<Slide><VStack w="1280" h="720" padding="36" gap="18">'
            '<VStack gap="5"><Text fontSize="14">EYEBROW</Text><Text fontSize="30">Headline</Text></VStack>'
            f'<HStack gap="18" alignItems="stretch" grow="1">{tiles}</HStack>{extra}</VStack></Slide>')


def test_four_lone_tiles_become_two_rows_of_two():
    xml, note = kpi_rows(_slide(4))
    assert "rows of 2+2" in note
    assert xml.count('w="49%"') == 4 and xml.count("<HStack") == 2


def test_five_tiles_become_three_plus_two():
    xml, note = kpi_rows(_slide(5))
    assert "rows of 3+2" in note and xml.count('w="32%"') == 5


def test_left_alone_beside_another_band_or_with_three_tiles():
    assert kpi_rows(_slide(3))[1] == ""
    beside = '<VStack backgroundColor="$surfaceAlt"><Table><Tr><Td>a</Td></Tr></Table></VStack>'
    assert kpi_rows(_slide(4, beside))[1] == ""


def test_layout_rules_render_from_capacity():
    text = layout_rules()
    lay = capacity()["layout"]
    assert f"at most {capacity()['kpi_row']['per_row'][1]} per row" in text
    assert f"at least {lay['kpi_tile_min_w']}px" in text
    assert "{" not in text
