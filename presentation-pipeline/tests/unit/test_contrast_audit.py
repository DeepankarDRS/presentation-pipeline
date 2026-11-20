"""LOW_CONTRAST — report-only contrast check in the layout audit (2026-09-29).

Genspark's linter flags text like "ZAROMA" purple on a dark panel (ratio 1.62); ours
only had the LLM critic looking at screenshots. Nothing is recoloured here.
"""

from src.compiler.layout_audit import audit_layout

THEME = '<Theme surface="F9F8F4" surfaceAlt="FFFFFF" accent="F5821F" accentAlt="5B2A86" textMain="041E42" textMuted="4E5D6E" />'


def _low(body: str) -> list[dict]:
    xml = f'{THEME}<Slide><VStack w="1280" h="720" padding="36" gap="14" alignItems="stretch" backgroundColor="$surface">{body}</VStack></Slide>'
    return [i for i in audit_layout(xml) if i["code"] == "LOW_CONTRAST"]


def test_purple_on_dark_panel_is_flagged():
    issues = _low('<VStack padding="16" backgroundColor="$textMain"><Text fontSize="16" color="$accentAlt">ZAROMA</Text></VStack>')
    assert len(issues) == 1 and "ZAROMA" in issues[0]["message"] and "#041E42" in issues[0]["message"]


def test_light_text_on_dark_panel_and_dark_text_on_light_pass():
    assert _low('<VStack padding="16" backgroundColor="$textMain"><Text fontSize="16" color="$surfaceAlt">Read-out</Text></VStack>'
                '<Text fontSize="16" color="$textMain">Body</Text>') == []


def test_large_text_uses_the_lower_ratio():
    # textMuted on surface is ~6.5; accent orange on surface ~2.4 fails even when large
    assert _low('<Text fontSize="30" bold="true" color="$textMuted">Headline</Text>') == []
    assert len(_low('<Text fontSize="30" bold="true" color="$accent">Headline</Text>')) == 1


def test_span_colour_and_table_cells_grouped_by_pair():
    rows = "".join(f'<Tr><Td backgroundColor="FFFFFF" color="$accent">cell {i}</Td></Tr>' for i in range(5))
    issues = _low(f'<VStack backgroundColor="FFFFFF"><Table><Col />{rows}</Table>'
                  '<Text fontSize="16" color="$textMain">CPC is <Span color="$accent">3x higher</Span></Text></VStack>')
    assert len(issues) == 1 and issues[0]["message"].startswith("6 text(s)")


def test_unresolved_background_is_not_judged():
    """A recipe has no <Theme>: its $textMain panel colour is unknown, not white."""
    xml = ('<Slide><VStack w="1280" h="720"><VStack backgroundColor="$textMain">'
           '<Text fontSize="14" color="D0DDD8">Insight on a dark panel</Text></VStack></VStack></Slide>')
    assert [i for i in audit_layout(xml) if i["code"] == "LOW_CONTRAST"] == []


def test_text_without_its_own_colour_is_not_judged():
    assert _low('<VStack padding="16" backgroundColor="$textMain"><Text fontSize="16">default colour</Text></VStack>') == []


def test_low_contrast_reaches_the_critic_as_a_fact_never_as_a_measured_defect():
    """2026-11-20 redesign: low contrast is a measured fact the critic judges on the screenshot (checklist: colour,
    text that does not read on its fill); it never sends a slide straight to the fixer the way a spill does."""
    from src.agents import slide_facts
    facts = slide_facts.measured_facts([], [], [{"code": "LOW_CONTRAST", "severity": "medium", "tier": "warning",
                                                 "message": "text on fill 2.1:1"}])
    assert [f.defect for f in facts] == [False]
    assert "2.1:1" in facts[0].text
