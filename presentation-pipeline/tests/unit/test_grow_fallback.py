"""grow fallback: a slide whose root VStack has no growing band gets one."""

from src.compiler.grow_fallback import ensure_growing_band
from src.compiler.normalizer import normalize_xml

HEADER = '<VStack gap="4"><Text fontSize="14">LABEL</Text><Text fontSize="28" bold="true">Headline</Text></VStack>'
TILE = '<VStack w="max" padding="16" backgroundColor="$surfaceAlt"><Text fontSize="14">Spend</Text><Text fontSize="30">₹114.9L</Text></VStack>'
KPI_ROW = f'<HStack gap="14" alignItems="stretch">{TILE}{TILE}{TILE}</HStack>'
CALLOUT = '<VStack padding="16" backgroundColor="EEF2FD"><Text fontSize="14">One read-out.</Text></VStack>'


def slide(*bands: str, root: str = "VStack") -> str:
    return f'<Slide><{root} w="1280" h="720" padding="36" gap="18">{"".join(bands)}</{root}></Slide>'


def test_kpi_and_callout_slide_gets_grow_on_kpi_row():
    xml, note = ensure_growing_band(slide(HEADER, KPI_ROW, CALLOUT))
    assert note
    assert '<HStack grow="1" gap="14"' in xml
    assert xml.count('grow="1"') == 1


def test_existing_grow_is_left_alone():
    src = slide(HEADER, KPI_ROW.replace("<HStack ", '<HStack grow="2" ', 1), CALLOUT)
    assert ensure_growing_band(src) == (src, None)


def test_chart_band_preferred_over_larger_band():
    chart = '<VStack padding="18" backgroundColor="$surfaceAlt"><Chart h="max" minH="180" chartType="bar"><ChartSeries name="a"><ChartDataPoint label="x" value="1" /></ChartSeries></Chart></VStack>'
    xml, note = ensure_growing_band(slide(HEADER, KPI_ROW, chart))
    assert "chart/diagram" in note
    assert '<VStack grow="1" padding="18"' in xml


def test_table_slide_unchanged():
    """fit-grow grows the table into the spare height; a growing callout would take it."""
    table = '<VStack padding="18" backgroundColor="$surfaceAlt"><Table><Col /><Tr><Td>a</Td></Tr></Table></VStack>'
    src = slide(HEADER, table, CALLOUT)
    assert ensure_growing_band(src) == (src, None)


def test_header_and_caption_never_picked():
    src = slide(HEADER, '<Text fontSize="14">Source: brief</Text>')
    assert ensure_growing_band(src) == (src, None)


def test_hstack_root_unchanged():
    src = slide(KPI_ROW, CALLOUT, root="HStack")
    assert ensure_growing_band(src) == (src, None)


def test_normalizer_reports_grow_band_added():
    out = normalize_xml(slide(HEADER, KPI_ROW, CALLOUT))
    assert any(i["code"] == "GROW_BAND_ADDED" for i in out["issues"])
    assert not out["blocking"]
