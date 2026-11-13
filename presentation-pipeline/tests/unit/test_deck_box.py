"""Deck look from the palette (palettes.yaml `cover` / `box`): normalizer.apply_box / dark_cover,
the dark cover kept out of the one-dark-panel rule, and the style_resolver fields."""

from src.agents.style_resolver import resolve_theme
from src.compiler.normalizer import apply_box, dark_cover, has_dark_panel, normalize_xml, soften_dark_panels

FRAME = resolve_theme("mbb-blue-frame")
THEME = FRAME["element"]

CONTENT = """<Slide>
  <VStack w="1280" h="720" padding="36" backgroundColor="$surface">
    <Text fontSize="14" color="$accentText">LABEL</Text>
    <HStack gap="12">
      <VStack padding="16" backgroundColor="$surfaceAlt" borderRadius="14" border.color="$border" border.width="1" shadow.blur="6" shadow.offset="2" shadow.color="000">
        <Text color="$textMain">Card</Text>
      </VStack>
      <VStack padding="16" backgroundColor="$surfaceAlt" borderLeft.color="$accent" borderLeft.width="4" borderRadius="14">
        <Text color="$textMain">Focus</Text>
      </VStack>
      <VStack padding="16" backgroundColor="$surfaceAlt" opacity="0.6" border.color="$border" border.width="1">
        <Text color="$textMuted">Faded</Text>
      </VStack>
      <VStack gap="4"><Text>no fill: layout only</Text></VStack>
      <VStack backgroundColor="$surface"><Text>same as the ground</Text></VStack>
    </HStack>
  </VStack>
</Slide>"""

COVER = """<Slide>
  <HStack w="1280" h="720" alignItems="stretch" backgroundColor="$surface">
    <VStack grow="1" padding="72" gap="20">
      <Text fontSize="16" color="$accentText">EXECUTIVE UPDATE</Text>
      <Text fontSize="60" bold="true" color="$textMain"><Span color="$accent">Q3</Span> Review</Text>
      <Shape shapeType="rect" w="96" h="6" fill.color="$accent" />
      <Text fontSize="26" color="$textMuted">Subtitle</Text>
      <VStack padding="16" backgroundColor="$surfaceAlt"><Text color="$textMain">light card</Text></VStack>
      <Text backgroundColor="$surfaceAlt" color="$textMain">filled text <Span color="$accent">span</Span></Text>
      <Table><Tr><Td backgroundColor="$surfaceAlt" color="$textMain">filled cell</Td><Td color="$textMain">bare cell</Td></Tr></Table>
    </VStack>
    <VStack w="400" padding="56" backgroundColor="$accent"><Text color="$onAccent">.</Text></VStack>
  </HStack>
</Slide>"""


def test_resolver_fields_default_and_frame():
    plain = resolve_theme("mbb-blue")
    assert plain["cover"] == "surface" and plain["box"] == {}
    assert FRAME["cover"] == "dark" and FRAME["box"]["borderRadius"] == "0"
    assert 'panelDark="051D2F"' in THEME          # authored beside the seed
    # same colours as the palette it copies, apart from the dark ground
    assert plain["element"].replace('panelDark="000000"', "").split("onPanelDark")[0] \
        == THEME.replace('panelDark="051D2F"', "").split("onPanelDark")[0]


def test_no_box_means_no_change():
    assert apply_box(CONTENT, {}) == (CONTENT, 0)


def test_apply_box_boxes_only():
    out, n = apply_box(CONTENT, FRAME["box"])
    assert n == 3                                   # the three filled / bordered cards
    root = out.split("\n")[1]
    assert "borderRadius" not in root and "shadow" not in root
    assert 'borderRadius="14"' not in out and 'shadow.blur="6"' not in out and 'border.color="$border"' not in out
    assert 'borderLeft.color="$accent" borderLeft.width="4"' in out   # accent bar kept
    faded = next(line for line in out.splitlines() if 'opacity="0.6"' in line)
    assert "shadow." not in faded and 'border.width="2"' in faded
    assert '<VStack gap="4">' in out and '<VStack backgroundColor="$surface">' in out


def test_apply_box_idempotent_and_survives_normalize():
    once, _ = apply_box(CONTENT, FRAME["box"])
    assert apply_box(once, FRAME["box"])[0] == once
    cleaned = normalize_xml(THEME + "\n" + once)["cleaned_xml"]
    assert cleaned.count('shadow.opacity="1"') == 2 and cleaned.count('border.width="2"') == 3


def test_dark_cover_root_and_text():
    out, n = dark_cover(COVER, THEME)
    assert n == 1
    root = out.split("\n")[1]
    assert 'backgroundColor="$coverDark"' in root and "$surface" not in root
    assert '<Text fontSize="60" bold="true" color="$onPanelDark"><Span color="$accentAlt">Q3</Span>' in out
    assert 'fill.color="$accentAlt"' in out
    assert '<Text fontSize="26" color="$neutral">' in out
    assert '<Text color="$textMain">light card</Text>' in out          # its own box keeps its ink
    assert '<Text backgroundColor="$surfaceAlt" color="$textMain">filled text <Span color="$accent">' in out
    assert '<Td backgroundColor="$surfaceAlt" color="$textMain">filled cell' in out
    assert '<Td color="$onPanelDark">bare cell' in out
    assert 'w="400" padding="56" backgroundColor="$accentAlt"' in out  # accent 042440 ~ ground 051D2F
    assert dark_cover(out, THEME)[0] == out


def test_dark_cover_needs_a_ground():
    assert dark_cover(COVER, "<Theme surface=\"FFFFFF\" />") == (COVER, 0)


def test_every_theme_defines_cover_dark():
    """The editor's theme switch keeps $tokens: a dark cover must compile under any palette."""
    from src.agents.style_resolver import theme_names
    assert 'coverDark="051D2F"' in THEME
    for name in theme_names():
        el = resolve_theme(name)["element"]
        panel = el.split(' panelDark="')[1][:6]
        assert f'coverDark="{panel}"' in el, name


def test_dark_ground_is_not_a_dark_panel():
    cover, _ = dark_cover(COVER, THEME)
    assert not has_dark_panel(cover)                # a dark cover leaves the deck its focus card
    closing, _ = dark_cover(CONTENT, THEME)
    soft, n = soften_dark_panels(closing)
    assert n == 0 and soft == closing               # a dark closing slide is not turned light
    panel = CONTENT.replace('<VStack gap="4">', '<VStack gap="4" backgroundColor="$panelDark">')
    assert has_dark_panel(panel)
    assert soften_dark_panels(panel)[1] == 1
