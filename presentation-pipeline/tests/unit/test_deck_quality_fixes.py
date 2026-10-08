"""Deck-quality fixes from the hand-written QBR comparison (docs/eval/hand-qbr, 2026-10-08)."""
from __future__ import annotations

from pydantic import BaseModel

from src.compiler.compiler_client import deck_font
from src.compiler.normalizer import normalize_xml, strip_control_chars
from src.utils.llm_client import unpack_raw


def test_control_chars_become_one_space():
    assert strip_control_chars("Q2 FY26 42.3\x7f Q3 FY26") == ("Q2 FY26 42.3 Q3 FY26", 1)
    assert strip_control_chars("a\tb\nc") == ("a\tb\nc", 0)


def test_normalizer_removes_control_chars():
    xml = '<Slide><VStack w="1280" h="720"><Text fontSize="16">$28.1M\x7f$14.4M</Text></VStack></Slide>'
    out = normalize_xml(xml)
    text = out["cleaned_xml"]
    assert "\x7f" not in text and "$28.1M $14.4M" in text


class _Slide(BaseModel):
    subtitle: str
    items: list[str]


def test_parsed_llm_result_is_cleaned():
    parsed, _ = unpack_raw({"parsed": _Slide(subtitle="A\x7f B", items=["x\x14y"]), "raw": None})
    assert parsed.subtitle == "A B" and parsed.items == ["x y"]


def test_deck_font_fills_missing_family_only():
    xml = '<Text fontSize="14">a</Text><Td fontFamily="X">b</Td><TextBox>'
    assert deck_font(xml, "Inter") == '<Text fontFamily="Inter" fontSize="14">a</Text><Td fontFamily="X">b</Td><TextBox>'
    assert deck_font(xml, "none") == xml


def test_examples_off_by_default():
    import src.agents.context_builder as cb
    assert cb.EXAMPLES_ON is False
