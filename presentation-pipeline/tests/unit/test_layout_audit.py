"""Tests for the layout audit — mechanical spatial checks on POM XML."""

from src.compiler.layout_audit import audit_layout


CLEAN_XML = """\
<Slide>
  <VStack w="1280" h="720" padding="48" gap="24" backgroundColor="$surface">
    <Text fontSize="32" bold="true" color="$textMain">Title</Text>
    <Chart w="600" h="400" chartType="bar" />
  </VStack>
</Slide>"""


def test_clean_xml_no_issues():
    issues = audit_layout(CLEAN_XML)
    assert issues == []


def test_font_too_small():
    xml = '<Slide><VStack w="1280" h="720"><Text fontSize="9">Tiny</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "FONT_TOO_SMALL" in codes
    assert any("9" in i["message"] for i in issues if i["code"] == "FONT_TOO_SMALL")


def test_font_at_minimum_ok():
    xml = '<Slide><VStack w="1280" h="720"><Text fontSize="11">OK</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "FONT_TOO_SMALL" not in codes


def test_chart_missing_dimensions():
    xml = '<Slide><VStack w="1280" h="720"><Chart chartType="bar" /></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "MISSING_DIMS" in codes


def test_chart_with_dimensions_ok():
    xml = '<Slide><VStack w="1280" h="720"><Chart w="600" h="400" chartType="bar" /></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "MISSING_DIMS" not in codes


def test_table_needs_no_dimensions():
    # A Table with no h/w sizes to its rows at full width (sizing plan F4).
    xml = '<Slide><VStack w="1280" h="720"><Table><Tr><Td>A</Td></Tr></Table></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "MISSING_DIMS" not in codes


def test_fill_node_h_max_needs_min_h():
    xml = '<Slide><VStack w="1280" h="720"><Chart h="max" chartType="bar" /><Flow grow="1" /></VStack></Slide>'
    messages = [i["message"] for i in audit_layout(xml) if i["code"] == "MISSING_DIMS"]
    assert len(messages) == 2 and all("minH" in m for m in messages)


def test_fill_node_h_max_with_min_h_ok():
    xml = ('<Slide><VStack w="1280" h="720"><Chart h="max" minH="180" chartType="bar" />'
           '<Matrix h="max" minH="260" /><ProcessArrow h="120" /></VStack></Slide>')
    assert "MISSING_DIMS" not in [i["code"] for i in audit_layout(xml)]


def test_timeline_and_pyramid_need_pixel_h():
    xml = '<Slide><VStack w="1280" h="720"><Timeline h="max" minH="150" /><Pyramid h="176" /></VStack></Slide>'
    messages = [i["message"] for i in audit_layout(xml) if i["code"] == "MISSING_DIMS"]
    assert len(messages) == 1 and messages[0].startswith("<Timeline>")


def test_vstack_child_w_max_flagged():
    # In a VStack, w="max" grows the height (F1); in an HStack it is the width share.
    xml = ('<Slide><VStack w="1280" h="720"><HStack w="max" h="150"><VStack w="max"><Text fontSize="14">a</Text>'
           '</VStack><VStack w="max"><Text fontSize="14">b</Text></VStack></HStack></VStack></Slide>')
    issues = [i for i in audit_layout(xml) if i["code"] == "VSTACK_W_MAX"]
    assert len(issues) == 1
    assert issues[0]["severity"] == "low"
    assert issues[0]["message"].startswith("1 child")


def test_root_size_missing():
    xml = '<Slide><VStack><Text fontSize="14">No dims</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "ROOT_SIZE" in codes


def test_root_size_max_ok():
    xml = '<Slide><VStack w="max" h="max"><Text fontSize="14">OK</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "ROOT_SIZE" not in codes


def test_root_size_percent_ok():
    xml = '<Slide><VStack w="100%" h="100%"><Text fontSize="14">OK</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "ROOT_SIZE" not in codes


def test_zero_dimension():
    xml = '<Slide><VStack w="0" h="720"><Text fontSize="14">Zero</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "ZERO_DIM" in codes


def test_negative_dimension():
    xml = '<Slide><VStack w="1280" h="720"><Text fontSize="-5">Neg</Text></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "ZERO_DIM" in codes


def test_deep_nesting():
    layers = '<VStack>' * 7 + '<Text fontSize="14">Deep</Text>' + '</VStack>' * 7
    xml = f'<Slide><VStack w="1280" h="720">{layers}</VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "DEEP_NESTING" in codes


def test_shallow_nesting_ok():
    xml = '<Slide><VStack w="1280" h="720"><HStack><VStack><Text fontSize="14">OK</Text></VStack></HStack></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "DEEP_NESTING" not in codes


def test_malformed_xml():
    xml = '<Slide><VStack w="1280" h="720"><Text>Unclosed'
    issues = audit_layout(xml)
    assert len(issues) == 1
    assert issues[0]["code"] == "XML_PARSE_ERROR"


def test_col_width_sum_mismatch():
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="48">
    <Table w="1184" h="400">
      <Col width="100" />
      <Col width="100" />
      <Col width="100" />
      <Tr><Td>A</Td><Td>B</Td><Td>C</Td></Tr>
    </Table>
  </VStack>
</Slide>"""
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "COL_WIDTH_SUM" in codes


def test_col_width_sum_correct():
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="48">
    <Table w="1184" h="400">
      <Col width="394" />
      <Col width="394" />
      <Col width="396" />
      <Tr><Td>A</Td><Td>B</Td><Td>C</Td></Tr>
    </Table>
  </VStack>
</Slide>"""
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "COL_WIDTH_SUM" not in codes


def test_multiple_issues():
    xml = '<Slide><VStack><Text fontSize="8">Tiny</Text><Chart /></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "ROOT_SIZE" in codes
    assert "FONT_TOO_SMALL" in codes
    assert "MISSING_DIMS" in codes
    assert len(issues) >= 3


def test_band_height_sum_overflow_flagged():
    # header (auto) + 3 content bands whose h + gaps + padding blow past 720
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="48" gap="28">
    <HStack><Text>Header</Text></HStack>
    <HStack h="320"><Text>KPI row</Text></HStack>
    <VStack h="300"><Text>Chart card</Text></VStack>
    <VStack h="140"><Text>Footer</Text></VStack>
  </VStack>
</Slide>"""
    codes = [i["code"] for i in audit_layout(xml)]
    assert "BAND_HEIGHT_SUM" in codes


def test_col_width_mixed_ok():
    """Mixed-width table: specified cols under budget, auto-fill cols present."""
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="48">
    <Table w="max" h="300">
      <Col width="420" />
      <Col />
      <Col />
      <Tr><Td>A</Td><Td>B</Td><Td>C</Td></Tr>
    </Table>
  </VStack>
</Slide>"""
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "COL_WIDTH_SUM" not in codes


def test_col_width_mixed_overflow():
    """Mixed-width table: specified cols exceed usable width."""
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="48">
    <Table w="max" h="300">
      <Col width="1000" />
      <Col width="300" />
      <Col />
      <Tr><Td>A</Td><Td>B</Td><Td>C</Td></Tr>
    </Table>
  </VStack>
</Slide>"""
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "COL_WIDTH_SUM" in codes
    assert any(i["severity"] == "high" for i in issues if i["code"] == "COL_WIDTH_SUM")


def test_col_width_all_auto_ok():
    """All-auto table: no widths specified, nothing to check."""
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="48">
    <Table w="max" h="300">
      <Col />
      <Col />
      <Col />
      <Tr><Td>A</Td><Td>B</Td><Td>C</Td></Tr>
    </Table>
  </VStack>
</Slide>"""
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "COL_WIDTH_SUM" not in codes


def test_band_height_sum_within_budget_ok():
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="36" gap="16">
    <HStack><Text>Header</Text></HStack>
    <HStack h="100"><Text>KPI row</Text></HStack>
    <VStack h="280"><Text>Chart card</Text></VStack>
    <VStack h="80"><Text>Callout</Text></VStack>
  </VStack>
</Slide>"""
    codes = [i["code"] for i in audit_layout(xml)]
    assert "BAND_HEIGHT_SUM" not in codes






def test_missing_dims_matrix_and_timeline():
    """Matrix and Timeline without explicit h should produce MISSING_DIMS."""
    xml = """\
<Slide>
  <VStack w="1280" h="720" padding="40">
    <Matrix w="max" />
    <Timeline w="max" />
  </VStack>
</Slide>"""
    issues = audit_layout(xml)
    dims_issues = [i for i in issues if i["code"] == "MISSING_DIMS"]
    tags = {i["message"].split("<")[1].split(">")[0] for i in dims_issues}
    assert "Matrix" in tags
    assert "Timeline" in tags


def test_hstack_root_column_overflow():
    """HStack-root layout with a VStack column whose heights exceed 720."""
    xml = """\
<Slide>
  <HStack w="1280" h="720" padding="0">
    <VStack w="640" padding="20" gap="10">
      <HStack h="200"><Text>Header</Text></HStack>
      <Chart w="max" h="500" />
    </VStack>
    <VStack w="640" padding="20" gap="10">
      <HStack h="60"><Text>Right header</Text></HStack>
      <Chart w="max" h="300" />
    </VStack>
  </HStack>
</Slide>"""
    issues = audit_layout(xml)
    band_issues = [i for i in issues if i["code"] == "BAND_HEIGHT_SUM"]
    assert len(band_issues) >= 1
    overflowing = [i for i in band_issues if "column 0" in i["message"]]
    assert len(overflowing) == 1


def test_hstack_root_column_within_budget_ok():
    """HStack-root with columns that fit within 720 should not trigger BAND_HEIGHT_SUM."""
    xml = """\
<Slide>
  <HStack w="1280" h="720" padding="0">
    <VStack w="640" padding="20" gap="10">
      <HStack h="80"><Text>Header</Text></HStack>
      <Chart w="max" h="300" />
    </VStack>
  </HStack>
</Slide>"""
    issues = audit_layout(xml)
    band_issues = [i for i in issues if i["code"] == "BAND_HEIGHT_SUM"]
    assert len(band_issues) == 0


def _table(cols: int, cell: str) -> str:
    row = "<Tr>" + "".join(f"<Td>{cell}</Td>" for _ in range(cols)) + "</Tr>"
    return "<Table>" + "<Col />" * cols + row * 3 + "</Table>"


def _half_width(table: str) -> str:
    return ('<Slide><VStack w="1280" h="720" padding="48"><HStack gap="16">'
            f'<VStack w="50%">{table}</VStack><VStack w="50%"><Text>Notes</Text></VStack>'
            '</HStack></VStack></Slide>')


def test_long_text_table_in_half_width_card_flagged():
    """Option B (roadmap Phase 2.4): a long-text column in a half-width card wraps into tall rows."""
    xml = _half_width(_table(6, "Shift 40% of Curd SP budget into SILB and Browse Boost for Q3 rollout"))
    issues = [i for i in audit_layout(xml) if i["code"] == "TABLE_TOO_WIDE_FOR_CARD"]
    assert len(issues) == 1 and issues[0]["severity"] == "low"


def test_many_short_columns_in_half_width_card_ok():
    """gj-h1 golden deep-dives: 5-6 short numeric columns in a half-width card are fine."""
    assert "TABLE_TOO_WIDE_FOR_CARD" not in [i["code"] for i in audit_layout(_half_width(_table(6, "12.67x")))]


def test_long_text_table_full_width_ok():
    xml = ('<Slide><VStack w="1280" h="720" padding="48">'
           + _table(4, "Shift 40% of Curd SP budget into SILB and Browse Boost for Q3 rollout")
           + "</VStack></Slide>")
    assert "TABLE_TOO_WIDE_FOR_CARD" not in [i["code"] for i in audit_layout(xml)]
