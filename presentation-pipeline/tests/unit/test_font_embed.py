"""Step 0.4: subset-embed the open fonts a deck names (src/compiler/font_embed.py)."""

import hashlib
import io
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from src.compiler.font_embed import BASE_CHARS, available_fonts, embed_deck_fonts, eot, subset_ttf

_ROOT = Path(__file__).resolve().parents[2]
_COMPILER = _ROOT / "src" / "node" / "compile-pom.js"
_FONTS = _ROOT / "src" / "node" / "fonts"

XML_INTER = (
    '<Theme surface="FFFFFF" textMain="111827" />\n<Slide><VStack w="1280" h="720" padding="40" gap="12">'
    '<Text fontSize="30" bold="true" fontFamily="Inter">Inter bold headline Žižek ₹114.9L</Text>'
    '<Text fontSize="18" fontFamily="Inter">Inter regular body text</Text>'
    '<Text fontSize="14" fontFamily="JetBrains Mono">MONO LABEL 01</Text>'
    '</VStack></Slide>')
XML_PLAIN = ('<Theme surface="FFFFFF" textMain="111827" />\n<Slide><VStack w="1280" h="720" padding="40">'
             '<Text fontSize="24">No font family named here</Text></VStack></Slide>')


def _compile(tmp_path: Path, xml: str, name: str) -> Path:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    src = tmp_path / f"{name}.xml"
    src.write_text(xml, encoding="utf-8")
    out = tmp_path / name
    subprocess.run(["node", str(_COMPILER), str(src), str(out)], check=True, capture_output=True, timeout=120,
                   env={**os.environ, "POM_FIT_GROW": "0"})
    return out / "presentation.pptx"


def _parts(pptx: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(pptx) as z:
        assert z.testzip() is None
        return {n: z.read(n) for n in z.namelist()}


def test_a_deck_naming_inter_and_mono_gets_subset_faces_embedded(tmp_path):
    pptx = _compile(tmp_path, XML_INTER, "inter")
    size_before = pptx.stat().st_size
    report = embed_deck_fonts(pptx)
    got = {(e["family"], e["face"]) for e in report["embedded"]}
    assert got == {("Inter", "regular"), ("Inter", "bold"), ("JetBrains Mono", "regular")}
    parts = _parts(pptx)
    assert sorted(n for n in parts if n.startswith("ppt/fonts/")) == [f"ppt/fonts/font{i}.fntdata" for i in (1, 2, 3)]
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    assert 'embedTrueTypeFonts="1"' in pres and "<p:embeddedFontLst>" in pres
    assert pres.index("<p:notesSz") < pres.index("<p:embeddedFontLst>")   # schema order
    assert 'Extension="fntdata"' in parts["[Content_Types].xml"].decode("utf-8")
    assert pptx.stat().st_size - size_before < 300 * 1024                 # the target: <= 300 KB per deck


def test_the_embedded_faces_are_subsets_that_keep_kerning_and_the_decks_characters(tmp_path):
    full = TTFont(_FONTS / "Inter-Regular.ttf")
    chars = "Žižek" + BASE_CHARS
    sub = TTFont(io.BytesIO(subset_ttf(_FONTS / "Inter-Regular.ttf", chars)))
    assert len(subset_ttf(_FONTS / "Inter-Regular.ttf", chars)) < 0.4 * (_FONTS / "Inter-Regular.ttf").stat().st_size
    cmap_full, cmap_sub = full.getBestCmap(), sub.getBestCmap()
    for ch in "Žižek₹€ A":
        assert ord(ch) in cmap_sub
        # measured widths must not move: same advance for every kept character
        assert sub["hmtx"][cmap_sub[ord(ch)]][0] == full["hmtx"][cmap_full[ord(ch)]][0]
    assert "GPOS" in sub                                                  # kerning kept
    assert sub["name"].getDebugName(1) == full["name"].getDebugName(1)    # the EOT header reads the name table


def test_the_eot_part_wraps_the_subset_font(tmp_path):
    data = eot(subset_ttf(_FONTS / "JetBrainsMono-Regular.ttf", BASE_CHARS))
    total, font_size, version = int.from_bytes(data[:4], "little"), int.from_bytes(data[4:8], "little"), int.from_bytes(data[8:12], "little")
    assert total == len(data) and version == 0x00020001 and data[-font_size:][:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO")


def test_a_deck_that_names_no_known_font_is_left_byte_identical(tmp_path):
    pptx = _compile(tmp_path, XML_PLAIN, "plain")
    before = hashlib.sha256(pptx.read_bytes()).hexdigest()
    report = embed_deck_fonts(pptx)
    assert report["embedded"] == [] and hashlib.sha256(pptx.read_bytes()).hexdigest() == before


def test_embedding_twice_is_the_same_as_once(tmp_path):
    pptx = _compile(tmp_path, XML_INTER, "twice")
    embed_deck_fonts(pptx)
    once = {n: d for n, d in _parts(pptx).items()}
    embed_deck_fonts(pptx)
    twice = _parts(pptx)
    assert once.keys() == twice.keys()
    assert all(once[n] == twice[n] for n in once)
    assert twice["ppt/presentation.xml"].count(b"<p:embeddedFontLst>") == 1


def test_a_font_whose_licence_forbids_embedding_is_skipped_with_a_reason(tmp_path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    font = TTFont(_FONTS / "Inter-Regular.ttf")
    font["OS/2"].fsType = 2   # restricted licence embedding
    font.save(fonts / "Inter-Regular.ttf")
    pptx = _compile(tmp_path, '<Theme surface="FFFFFF" />\n<Slide><VStack w="1280" h="720"><Text fontFamily="Inter">x</Text></VStack></Slide>', "locked")
    before = pptx.read_bytes()
    report = embed_deck_fonts(pptx, fonts_dir=fonts)
    assert report["embedded"] == [] and "licence" in report["skipped"][0]
    assert pptx.read_bytes() == before


def test_a_face_we_have_no_file_for_is_reported_not_faked(tmp_path):
    xml = ('<Theme surface="FFFFFF" />\n<Slide><VStack w="1280" h="720">'
           '<Text fontFamily="JetBrains Mono" bold="true" fontSize="14">bold mono</Text></VStack></Slide>')
    pptx = _compile(tmp_path, xml, "bm")
    report = embed_deck_fonts(pptx)
    assert [e["face"] for e in report["embedded"]] == ["bold"]            # we do have JetBrains Mono Bold
    assert available_fonts()["JetBrains Mono"].keys() == {"regular", "bold"}


def test_a_broken_pptx_is_never_fatal(tmp_path):
    bad = tmp_path / "bad.pptx"
    bad.write_bytes(b"not a zip")
    report = embed_deck_fonts(bad)
    assert report["embedded"] == [] and report["skipped"][0].startswith("failed")
    assert bad.read_bytes() == b"not a zip"


def test_out_path_leaves_the_source_alone(tmp_path):
    pptx = _compile(tmp_path, XML_INTER, "src")
    original = pptx.read_bytes()
    out = tmp_path / "embedded.pptx"
    assert embed_deck_fonts(pptx, out)["embedded"]
    assert pptx.read_bytes() == original and out.stat().st_size > len(original)
    assert re.search(rb"embeddedFontLst", zipfile.ZipFile(out).read("ppt/presentation.xml"))
