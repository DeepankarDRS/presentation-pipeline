"""Diagram item colours (2026-11-12): the LLM picks each item's fill from the palette; code supplies an order ramp
($step1..5 / $onStep1..5), makes every item label readable, and notes overuse (COLOR_BALANCE, report only)."""

import re

import pytest

from src.agents.style_resolver import resolve_theme, theme_names
from src.compiler.layout_audit import REPORT_ONLY_CODES, audit_layout
from src.compiler.normalizer import readable_item_text
from src.compiler.palette_tokens import STEP_EDGE_MIN, _lch, contrast

THEME = resolve_theme("mbb-blue")["element"]


def _tokens(name):
    return dict(re.findall(r'(\w+)="([0-9A-F]{6})"', resolve_theme(name)["element"]))


@pytest.mark.parametrize("name", theme_names())
def test_step_ramp_passes_the_order_checks(name):
    t, dark = _tokens(name), resolve_theme(name)["is_dark"]
    steps = [t[f"step{i}"] for i in range(1, 6)]
    L = [_lch(s)[0] for s in steps]
    assert all((b > a) if dark else (b < a) for a, b in zip(L, L[1:])), "monotone from the card outward"
    assert min(abs(b - a) for a, b in zip(L, L[1:])) >= 0.06, "visible steps"
    assert contrast(steps[0], t["surfaceAlt"]) >= STEP_EDGE_MIN - 0.01, "the step nearest the card shows on it"
    for i, s in enumerate(steps, 1):
        assert contrast(t[f"onStep{i}"], s) >= 4.5, f"onStep{i}"


def _pyramid(*levels):
    body = "".join(f"<PyramidLevel label=\"L{i}\" {a} />" for i, a in enumerate(levels))
    return f'<Slide><VStack w="1280" h="720"><Pyramid direction="up">{body}</Pyramid></VStack></Slide>'


def test_label_on_a_step_takes_its_on_step_ink():
    out, n = readable_item_text(_pyramid('color="$step5"'), THEME)
    assert n == 1 and 'color="$step5" textColor="$onStep5"' in out


def test_a_readable_llm_text_colour_is_kept_and_an_unreadable_one_replaced():
    xml = _pyramid('color="$accentSoft" textColor="$textMain"', 'color="$accent" textColor="$textMain"')
    out, n = readable_item_text(xml, THEME)
    assert n == 1
    assert 'color="$accentSoft" textColor="$textMain"' in out           # 4.5:1+ already: the LLM's choice stays
    assert 'color="$accent" textColor="$textMain"' not in out           # black on navy: replaced
    assert readable_item_text(out, THEME) == (out, 0)                   # idempotent


def test_every_item_type_and_hex_fills():
    xml = ('<Slide><VStack w="1280" h="720">'
           '<ProcessArrow><ProcessArrowStep label="a" color="$accent" /></ProcessArrow>'
           '<Flow><FlowNode id="a" text="a" color="F44336" textColor="FF9800" /></Flow>'
           '<Tree><TreeItem label="r" color="$step1"><TreeItem label="c" color="$accentSoft" /></TreeItem></Tree>'
           '</VStack></Slide>')
    out, n = readable_item_text(xml, THEME)
    tok = _tokens("mbb-blue")
    for tag in re.findall(r"<(?:ProcessArrowStep|FlowNode|TreeItem)\b[^>]*>", out):
        fill = re.search(r'\scolor="([^"]+)"', tag).group(1)
        ink = re.search(r'textColor="\$(\w+)"', tag).group(1)
        bg = tok[fill[1:]] if fill.startswith("$") else fill
        assert contrast(tok[ink], bg) >= 4.5, tag


def test_no_theme_no_change():
    xml = _pyramid('color="$accent"')
    assert readable_item_text(xml, "") == (xml, 0)


def _codes(xml):
    return [i for i in audit_layout(xml) if i["code"] == "COLOR_BALANCE"]


def test_color_balance_notes_overuse_only():
    calm = _pyramid(*['color="$accentSoft"'] * 3, 'color="$accent"', 'color="$neutral"')
    assert _codes(calm) == []
    ramp = _pyramid(*[f'color="$step{i}"' for i in range(1, 6)])
    assert _codes(ramp) == []                                            # the ramp counts as one colour
    rainbow = _pyramid('color="F44336"', 'color="FF9800"', 'color="FFEB3B"', 'color="4CAF50"')
    assert "4 colours" in _codes(rainbow)[0]["message"]
    loud = _pyramid('color="$accent"', 'color="$accent"', 'color="$accentSoft"', 'color="$accent"')
    assert "none stands out" in _codes(loud)[0]["message"]
    status = _pyramid('color="$positive"', 'color="$positive"', 'color="$warning"', 'color="$negative"',
                      'color="$neutral"')
    assert _codes(status) == []                                          # status colours count as one family
    mixed = _pyramid('color="$step1"', 'color="$step3"', 'color="$negative"')
    assert "status" in _codes(mixed)[0]["message"]
    assert "COLOR_BALANCE" in REPORT_ONLY_CODES


def test_recipes_offer_the_choice_and_no_hex():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "src/knowledge/core/recipes.yaml").read_text(encoding="utf-8")
    assert text.count("YOUR choice per item") >= 6 and "$step1..$step5" in text


@pytest.mark.parametrize("name", theme_names())
def test_every_listed_fill_gets_a_readable_label(name):
    """Every fill the recipes offer, on every palette: code finds a label colour at 4.5:1 or better."""
    el = resolve_theme(name)["element"]
    t = _tokens(name)
    fills = ["$accent", "$accentSoft", "$neutral", "$surfaceAlt"] + [f"$step{i}" for i in range(1, 6)] + [
        f"${r}{s}" for r in ("positive", "warning", "negative") for s in ("", "Soft")]
    out, _ = readable_item_text(_pyramid(*[f'color="{f}"' for f in fills]), el)
    for fill, ink in re.findall(r'color="\$(\w+)" textColor="\$(\w+)"', out):
        assert contrast(t[ink], t[fill]) >= 4.5, (fill, ink)


def test_line_breaks_in_diagram_labels_become_spaces():
    """Paid run 2026-11-12: the LLM wrote label="Category&#10;leadership"; POM printed the entity as text."""
    from src.compiler.normalizer import normalize_xml
    xml = ('<Slide><VStack w="1280" h="720"><Pyramid direction="up">'
           '<PyramidLevel label="Category&#10;leadership" color="$step1" />'
           '<PyramidLevel label="Loyal &#xA; subscribers" color="$step2" /></Pyramid>'
           '<Matrix><MatrixItem label="+ Bundle offers&#10;+ Referral program" x="0.2" y="0.8" /></Matrix>'
           '<Text fontSize="16">kept&#10;as is</Text></VStack></Slide>')
    res = normalize_xml(xml)
    out = res["cleaned_xml"]
    assert 'label="Category leadership"' in out and 'label="Loyal subscribers"' in out
    assert 'label="+ Bundle offers + Referral program"' in out
    assert "&#10;" not in out.split("<Text")[0]
    assert "LABEL_BREAK_REMOVED" in [i["code"] for i in res["issues"]]
    assert "LABEL_BREAK_REMOVED" not in [i["code"] for i in normalize_xml(out)["issues"]]
