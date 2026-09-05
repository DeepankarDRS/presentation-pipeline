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


def test_table_missing_dimensions():
    xml = '<Slide><VStack w="1280" h="720"><Table><Tr><Td>A</Td></Tr></Table></VStack></Slide>'
    issues = audit_layout(xml)
    codes = [i["code"] for i in issues]
    assert "MISSING_DIMS" in codes


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
