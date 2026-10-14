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


def test_card_rows_share_a_growing_bands_height():
    """XTSY layout-batch: band grow="2", rows without grow -> lower half of the slide empty."""
    from src.compiler.grow_fallback import share_row_height
    grid = f'<VStack grow="2" gap="14"><HStack gap="14">{TILE}{TILE}</HStack><HStack gap="14">{TILE}</HStack></VStack>'
    xml, note = share_row_height(slide(HEADER, grid, CALLOUT))
    assert xml.count('<HStack grow="1" gap="14">') == 2 and "2 card row" in note
    assert share_row_height(xml) == (xml, None)                      # idempotent
    fixed = grid.replace('<HStack gap="14">', '<HStack grow="1" gap="14">', 1)
    assert share_row_height(slide(HEADER, fixed))[1] is None         # one row already flexible: leave it


# KPI / card tiles as the expansion writes them (tiles.py: boxed VStacks, value ids kpiv-)
KTILE = ('<VStack padding="16" backgroundColor="$surfaceAlt" border.color="$border" border.width="1" grow="1">'
         '<Text>ARR</Text><Text id="kpiv0-k-{i}">$48M</Text></VStack>')


def test_long_text_box_in_w_max_beside_tiles_shares_the_row():
    """Same-plan pair 1.4 (CHEFFIN 1): a 110-character bullet in w="max" took 1015 of 1184 px from two tiles."""
    from src.compiler.grow_fallback import unsqueeze_text_boxes
    text = "Both platforms show the same structural issue: CPC is too high relative to AOV and CVR."
    tiles = '<VStack grow="1"><HStack id="kpig-k">' + KTILE.format(i=0) + KTILE.format(i=1) + "</HStack></VStack>"
    box = f'<VStack padding="24" w="max"><Ul><Li>{text}</Li></Ul></VStack>'
    xml, note = unsqueeze_text_boxes(slide(HEADER, f'<HStack gap="28" grow="1">{tiles}{box}</HStack>'))
    assert '<VStack padding="24" grow="1">' in xml and 'w="max"' not in xml and note
    assert unsqueeze_text_boxes(xml)[1] is None
    # beside other text (agency 2: a w="max" checklist beside a grow="2" quote) it keeps its content width
    quote = f'<VStack grow="2"><Text>{text}</Text></VStack>'
    src = slide(HEADER, f'<HStack gap="24">{quote}{box}</HStack>')
    assert unsqueeze_text_boxes(src) == (src, None)
    # a short label in w="max" beside tiles is not squeezing anything
    short = '<VStack w="max"><Text>Both platforms</Text></VStack>'
    src = slide(HEADER, f'<HStack gap="28">{tiles}{short}</HStack>')
    assert unsqueeze_text_boxes(src) == (src, None)
