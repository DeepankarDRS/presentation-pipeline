"""fit-grow on a growing KPI row (2026-10-06 neutral-kpi run, CHEFFIN exec summary; LLM-free, real compiler).

s15 one kpi_row of five tiles with grow="1" above a callout without grow: the tiles stretched to
    ~400 px around a label and a number, the callout stayed one 14 px line, and the shrink guard
    left "₹114.9L" at 41 px beside four numbers at 60 px.
"""

import re

from tests.unit.test_fit_grow_tables import _FIT, _compile


def test_callout_shares_the_height_and_kpi_values_keep_one_size(tmp_path):
    on = _compile(_FIT / "s15-kpi-row-of-five-beside-callout.xml", tmp_path / "on")
    assert any("text band takes a share" in r and "beside a sparse KPI row" in r for r in on["fitGrow"]), on["fitGrow"]
    values = [int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" color="\$(?:textMain|negative)" bold="true">[₹0-9]', on["xml"])]
    assert len(values) == 5 and len(set(values)) == 1 and values[0] >= 40, values
    callout = re.search(r'<VStack(?=[^>]*\sgrow="1")(?=[^>]*\sjustifyContent="center")[^>]*>\s*<Text[^>]*\sfontSize="(\d+)"', on["xml"])
    assert callout and int(callout.group(1)) >= 24, on["xml"]
    assert not any(w["code"] == "WORD_TOO_WIDE" for w in on.get("warnings", [])), on.get("warnings")


def test_kpi_values_of_a_row_are_evened_after_the_guard(tmp_path):
    """The guard shrinks one word at a time; the row's numbers then take the smallest size."""
    tile = ('<VStack w="{w}" padding="18" gap="6" backgroundColor="$surfaceAlt" justifyContent="center">'
            '<Text fontSize="14" color="$textMuted">{label}</Text>'
            '<Text fontSize="60" color="$textMain" bold="true">{value}</Text></VStack>')
    tiles = "".join(tile.format(w=w, label=l, value=v) for w, l, v in
                    [(170, "Spend", "₹114.9L"), (300, "Revenue", "₹37.4L"), (300, "ROAS", "0.33x")])
    xml = tmp_path / "t.xml"
    xml.write_text('<Theme surfaceAlt="FFFFFF" textMain="16202E" textMuted="55627A" /><Slide>'
                   f'<VStack w="1280" h="720" padding="36" gap="18"><HStack gap="14">{tiles}</HStack></VStack></Slide>',
                   encoding="utf-8")
    on = _compile(xml, tmp_path / "on")
    values = {int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" color="\$textMain" bold="true">', on["xml"])}
    assert len(values) == 1 and values.pop() < 60, on["fitGrow"]
    assert any("KPI values share one size" in r for r in on["fitGrow"]), on["fitGrow"]
