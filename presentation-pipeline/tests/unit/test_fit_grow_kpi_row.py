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


def test_a_kpi_row_is_evened_even_when_the_guard_takes_a_number_below_24px(tmp_path):
    """gj-h1 Blinkit (6 narrow tiles): the guard took "₹7.31" 24 -> 17px; a tile whose number is
    under 24px no longer counts as a stat tile, so the row was found too late and stayed
    23 / 17 / 24 / 24 / 24 / 24px. Rows are now found before the guard."""
    tile = ('<VStack w="104" padding="12" gap="4" backgroundColor="$surfaceAlt">'
            '<Text fontSize="12" color="$textMuted">{label}</Text>'
            '<Text fontSize="24" color="$textMain" bold="true">{value}</Text></VStack>')
    tiles = "".join(tile.format(label=l, value=v) for l, v in
                    [("Sales", "₹1.32Cr"), ("Spend", "₹7.31L"), ("CPM", "₹36"), ("ROAS", "6.3x"), ("ACOS", "15%")])
    xml = tmp_path / "t.xml"
    xml.write_text('<Theme surfaceAlt="FFFFFF" textMain="16202E" textMuted="55627A" /><Slide>'
                   f'<VStack w="1280" h="720" padding="36" gap="18"><HStack gap="10">{tiles}</HStack></VStack></Slide>',
                   encoding="utf-8")
    on = _compile(xml, tmp_path / "on")
    values = [int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)" color="\$textMain" bold="true">', on["xml"])]
    assert len(values) == 5 and len(set(values)) == 1 and values[0] < 24, (values, on["fitGrow"])


# ── a code-laid row of tiles may become two rows (regridTiles; paid check 2, QBR) ─────────────────────────────

_THEME = ('<Theme surface="F7F9FC" surfaceAlt="FFFFFF" accent="2563EB" accentText="1C5CEA" textMain="16202E" '
          'textMuted="55627A" border="CAD5E4" />')
_QBR = {"components": [{"component_id": "kpis", "kind": "kpi_row", "count": 4, "content_data": {
    "kpi_labels": ["ARR", "NRR", "Gross Margin", "CAC Payback"], "kpi_values": ["$48.2M", "114%", "72.1%", "14 months"],
    "kpi_deltas": ["+18% QoQ", "+2 pts", "-1.4 pts", "-2 months"]}}]}


def _tiles_slide(tmp_path, group, below=""):
    from src.compiler.nodes import tiles
    body = (f'<VStack gap="10"><Text fontSize="36" color="$textMain" bold="true">ARR grew while margin softened</Text></VStack>'
            f'<VStack grow="1" alignItems="stretch" justifyContent="center">{group}</VStack>{below}')
    res = tiles.fill(f'<Slide><VStack w="1280" h="720" padding="48" gap="32" alignItems="stretch" '
                     f'backgroundColor="$surface">{body}</VStack></Slide>', _QBR)
    assert res["ok"], res["issues"]
    xml = tmp_path / "t.xml"
    xml.write_text(_THEME + res["xml"], encoding="utf-8")
    return _compile(xml, tmp_path / "on")


def _values(xml):
    return [int(v) for v in re.findall(r'<Text[^>]*\sfontSize="(\d+)"[^>]*\sid="kpiv\d-kpis-\d"', xml)]


def test_a_code_laid_row_of_four_tiles_becomes_two_rows_in_a_tall_band(tmp_path, monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")
    on = _tiles_slide(tmp_path, '<KpiGrid ref="kpis"/>')
    assert any("KPI tiles of kpis in two rows" in r for r in on["fitGrow"]), on["fitGrow"]
    values = _values(on["xml"])
    assert len(values) == 4 and len(set(values)) == 1 and values[0] >= 75, (values, on["fitGrow"])   # row: 58
    labels = [int(v) for v in re.findall(r'<Text color="\$textMuted" fontSize="(\d+)">', on["xml"])]
    assert labels and min(labels) >= 20, labels   # the labels grew with the numbers
    assert on["xml"].count("<HStack") >= 2 and 'id="kpig-kpis"' in on["xml"]


def test_a_row_the_llm_asked_for_stays_a_row(tmp_path, monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")
    on = _tiles_slide(tmp_path, '<KpiGrid ref="kpis" layout="row"/>')
    assert not any("two rows" in r for r in on["fitGrow"]) and "kpig-" not in on["xml"]


def test_a_row_with_no_height_to_spare_stays_a_row(tmp_path, monkeypatch):
    monkeypatch.setenv("POM_BLOCKS", "tiles")
    filler = '<VStack h="330" backgroundColor="$surfaceAlt"><Text fontSize="18" color="$textMain">Chart</Text></VStack>'
    on = _tiles_slide(tmp_path, '<KpiGrid ref="kpis"/>', filler)
    assert not any("two rows" in r for r in on["fitGrow"]), on["fitGrow"]


def test_a_large_hero_grows_after_the_other_kpi_numbers(tmp_path, monkeypatch):
    """Paid check 2, CHEFFIN 1 r1 (the LLM's XML): with the platform tiles drawn bare on the LLM's panel the
    hero took the freed height (72 -> 99 px) and the platform row stayed at 28 px; it now goes last."""
    import json

    from scripts.kpi_replay import compile_slide
    from src.agents.style_resolver import resolve_theme
    from src.compiler.nodes import tiles
    monkeypatch.setenv("POM_BLOCKS", "tiles")
    it = next(i for i in json.loads((_FIT.parents[2] / "docs" / "eval" / "kpi-node" / "paid-inputs.json")
                                    .read_text(encoding="utf-8")) if i["case"] == "gate-deck-cheffin-full" and i["slide"] == 1)
    llm = ('<Slide><VStack w="1280" h="720" padding="48" gap="28" alignItems="stretch" backgroundColor="$surface">'
           '<VStack gap="10"><Text fontSize="14" color="$accentText" bold="true" letterSpacing="2">EXECUTIVE SUMMARY</Text>'
           '<Text fontSize="36" color="$textMain" bold="true" lineHeight="1.15">The account is spending at scale, but not '
           'yet buying profitable demand.</Text></VStack>'
           '<VStack gap="22" grow="3"><KpiGrid ref="combined_kpi_scorecard">'
           '<Kpi ref="combined_kpi_scorecard.2" variant="inverted" size="hero" /></KpiGrid>'
           '<VStack padding="20" gap="14" backgroundColor="$negativeSoft" borderRadius="12" border.color="$border" '
           'border.width="1"><KpiGrid ref="platform_roas_tiles"><Kpi ref="platform_roas_tiles.0" color="$negative" '
           'variant="filled" /><Kpi ref="platform_roas_tiles.1" color="$negative" variant="filled" /></KpiGrid></VStack>'
           '</VStack><VStack grow="1" backgroundColor="$surfaceAlt" padding="32" gap="14" borderRadius="12">'
           '<Text fontSize="18" color="$textMain" lineHeight="1.4">Both platforms show the same structural issue: CPC is '
           'too high relative to AOV and CVR.</Text></VStack></VStack></Slide>')
    res = compile_slide(tiles.fill(llm, it["plan"])["xml"], resolve_theme(it["theme"])["element"], tmp_path)["res"]
    assert res["status"] == "success"
    xml = (tmp_path / "fitted.xml").read_text(encoding="utf-8")
    size = lambda cid: [int(v) for v in re.findall(rf'fontSize="(\d+)"[^>]*id="kpi[vh]\d-{cid}-\d"', xml)]
    assert min(size("platform_roas_tiles")) >= 50, (size("platform_roas_tiles"), res["fitGrow"])   # was 28-29
    assert max(size("platform_roas_tiles")) <= max(size("combined_kpi_scorecard")), res["fitGrow"]
