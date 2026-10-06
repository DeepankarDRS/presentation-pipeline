"""Subset-embed the open fonts a finished .pptx names (§14.6 step 0; derived-nodes-design §13 R1 / R4).

POM measures text with the font files in src/node/fonts/ (Inter, JetBrains Mono), so a deck that
names those fonts is only laid out right where they are drawn. A machine without them substitutes
another font ~6% narrower and the layout drifts (R1); PowerPoint on the test PC matched the
LibreOffice render once the fonts were embedded (R4). This module embeds them the way PowerPoint
does: an Embedded OpenType part per face (ppt/fonts/fontN.fntdata, uncompressed EOT) listed in
presentation.xml <p:embeddedFontLst>.

* Only families the deck's runs name AND whose files we have are embedded; faces regular / bold
  (and italic when a run uses it and the file exists). A deck that names none is returned
  byte-identical - the LLM path writes no fontFamily today, so for it this is a no-op.
* Each face is subset to Basic Latin + Latin-1 + general punctuation + the currency / arrow /
  maths marks the blocks use, plus every character the deck sets in that face. GPOS kerning and
  the name table are kept, so measured widths still match. Full Inter Regular is 411 KB, so
  subsetting keeps a deck under the ~300 KB target.
* Fonts whose OS/2 fsType forbids embedding are skipped. Never fatal: `embed_deck_fonts` returns a
  report with the reason and leaves the file as it was.

Run once on the FINAL deck file (after the combined compile or the ZIP-level merge): the per-slide
files used for screenshots are not embedded.
"""

from __future__ import annotations

import io
import logging
import re
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).resolve().parent.parent / "node" / "fonts"
REL_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

# characters every embedded face keeps, so text edited in PowerPoint stays in the font
BASE_CHARS = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "".join(chr(c) for c in range(0xA0, 0x100))
    + "".join(chr(c) for c in range(0x2010, 0x2028)) + "".join(chr(c) for c in range(0x2030, 0x205F))
    + "₹€←↑→↓↔−•≈≠≤≥✓✕"
)


# ── Embedded OpenType ───────────────────────────────────────────────────────

def _tables(ttf: bytes) -> dict[str, bytes]:
    num = struct.unpack(">H", ttf[4:6])[0]
    out = {}
    for i in range(num):
        tag, _, off, length = struct.unpack(">4sIII", ttf[12 + 16 * i: 28 + 16 * i])
        out[tag.decode("latin1")] = ttf[off: off + length]
    return out


def _name(names: bytes, name_id: int) -> str:
    count, start = struct.unpack(">HH", names[2:6])
    for i in range(count):
        pid, eid, lid, nid, length, off = struct.unpack(">HHHHHH", names[6 + 12 * i: 18 + 12 * i])
        if nid == name_id and pid == 3 and eid in (0, 1, 10):
            return names[start + off: start + off + length].decode("utf-16-be")
    return ""


def eot(ttf: bytes) -> bytes:
    """Uncompressed EOT (spec version 0x00020001) wrapping a TrueType file."""
    t = _tables(ttf)
    os2, head, names = t["OS/2"], t["head"], t["name"]
    panose = os2[32:42]
    weight = struct.unpack(">H", os2[4:6])[0]
    fs_type = struct.unpack(">H", os2[8:10])[0]
    ur = struct.unpack(">IIII", os2[42:58])
    fs_selection = struct.unpack(">H", os2[62:64])[0]
    cpr = struct.unpack(">II", os2[78:86]) if len(os2) >= 86 else (0, 0)
    checksum_adj = struct.unpack(">I", head[8:12])[0]

    def s(text: str) -> bytes:
        raw = text.encode("utf-16-le")
        return struct.pack("<H", len(raw)) + raw

    body = (panose + struct.pack("<BBI", 1, 1 if fs_selection & 1 else 0, weight)
            + struct.pack("<HH", fs_type, 0x504C) + struct.pack("<IIII", *ur) + struct.pack("<II", *cpr)
            + struct.pack("<I", checksum_adj) + struct.pack("<IIII", 0, 0, 0, 0)
            + struct.pack("<H", 0) + s(_name(names, 1))
            + struct.pack("<H", 0) + s(_name(names, 2))
            + struct.pack("<H", 0) + s(_name(names, 5))
            + struct.pack("<H", 0) + s(_name(names, 4))
            + struct.pack("<H", 0) + s(""))
    header_size = 4 * 4 + len(body)  # EOTSize, FontDataSize, Version, Flags
    return struct.pack("<IIII", header_size + len(ttf), len(ttf), 0x00020001, 0) + body + ttf


# ── the fonts we can embed ──────────────────────────────────────────────────

def _face_of(font) -> tuple[str, str]:
    """(family, face) of a fontTools TTFont: face in regular / bold / italic / boldItalic."""
    names = font["name"]
    family = (names.getDebugName(16) or names.getDebugName(1) or "").strip()
    bold = font["OS/2"].usWeightClass >= 600 or bool(font["head"].macStyle & 1)
    italic = bool(font["head"].macStyle & 2) or bool(font["OS/2"].fsSelection & 1)
    return family, ("boldItalic" if bold and italic else "bold" if bold else "italic" if italic else "regular")


def available_fonts(fonts_dir: Path = FONTS_DIR) -> dict[str, dict[str, Path]]:
    """{family: {face: ttf path}} for every .ttf in the fonts folder (family names as the files give them)."""
    from fontTools.ttLib import TTFont

    out: dict[str, dict[str, Path]] = {}
    for path in sorted(fonts_dir.glob("*.ttf")):
        try:
            font = TTFont(path, lazy=True)
            family, face = _face_of(font)
            font.close()
        except Exception as exc:  # a broken file must not stop the others
            logger.warning(f"font_embed: cannot read {path.name}: {exc}")
            continue
        if family:
            out.setdefault(family, {})[face] = path
    return out


def subset_ttf(path: Path, chars: str) -> bytes:
    """The font file reduced to `chars` (+ the glyphs they need), keeping kerning, names and OS/2."""
    from fontTools import subset

    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.glyph_names = False
    opts.hinting = True
    font = subset.load_font(str(path), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    font.close()
    return buf.getvalue()


# ── what the deck uses ──────────────────────────────────────────────────────

def faces_used(parts: dict[str, bytes]) -> dict[tuple[str, str], set[str]]:
    """{(typeface, face): characters} over every run of every slide ("" typeface = theme default)."""
    from lxml import etree

    used: dict[tuple[str, str], set[str]] = {}
    for name, data in parts.items():
        if not re.fullmatch(r"ppt/slides/slide\d+\.xml", name):
            continue
        root = etree.fromstring(data)
        for run in root.iter(f"{{{_A}}}r"):
            props = run.find(f"{{{_A}}}rPr")
            latin = props.find(f"{{{_A}}}latin") if props is not None else None
            family = latin.get("typeface", "") if latin is not None else ""
            bold = props is not None and props.get("b") in ("1", "true")
            italic = props is not None and props.get("i") in ("1", "true")
            face = "boldItalic" if bold and italic else "bold" if bold else "italic" if italic else "regular"
            text = "".join(t.text or "" for t in run.iter(f"{{{_A}}}t"))
            used.setdefault((family, face), set()).update(text)
    return used


# ── the embedding ───────────────────────────────────────────────────────────

def _strip_embedded(parts: dict[str, bytes]) -> None:
    """Remove fonts embedded earlier (list, relationships, parts), so embedding twice is the same as once."""
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    pres = re.sub(r"<p:embeddedFontLst>.*?</p:embeddedFontLst>", "", pres, flags=re.S)
    pres = re.sub(r"\s(embedTrueTypeFonts|saveSubsetFonts)=\"[^\"]*\"", "", pres)
    parts["ppt/presentation.xml"] = pres.encode("utf-8")
    rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    rels = re.sub(rf'<Relationship\b[^>]*Type="{re.escape(REL_FONT)}"[^>]*/>', "", rels)
    parts["ppt/_rels/presentation.xml.rels"] = rels.encode("utf-8")
    for name in [n for n in parts if n.startswith("ppt/fonts/")]:
        del parts[name]


def embed_deck_fonts(pptx: Path, out: Path | None = None, fonts_dir: Path = FONTS_DIR) -> dict[str, Any]:
    """Embed the open fonts the deck names (subset). In place unless `out` is given.

    Returns {"embedded": [{family, face, bytes}], "skipped": [reason, ...], "added_bytes": int}.
    The file is left untouched (or copied unchanged to `out`) when nothing is embedded or anything fails.
    """
    pptx = Path(pptx)
    report: dict[str, Any] = {"embedded": [], "skipped": [], "added_bytes": 0}
    dest = Path(out) if out else pptx
    try:
        with zipfile.ZipFile(pptx) as z:
            infos = z.infolist()
            parts = {i.filename: z.read(i.filename) for i in infos}
        order = [i.filename for i in infos]
        have = available_fonts(fonts_dir)
        by_name = {family.lower(): (family, faces) for family, faces in have.items()}
        wanted: dict[str, dict[str, set[str]]] = {}
        for (typeface, face), chars in faces_used(parts).items():
            hit = by_name.get(typeface.lower())
            if not hit:
                continue
            family, faces = hit
            if face not in faces:  # a bold-italic run in a family without that file: draw with what we embed
                report["skipped"].append(f"{family} {face}: no font file")
                continue
            wanted.setdefault(family, {}).setdefault(face, set()).update(chars)
        if not wanted:
            if dest != pptx:
                dest.write_bytes(pptx.read_bytes())
            return report

        from fontTools.ttLib import TTFont

        _strip_embedded(parts)
        pres = parts["ppt/presentation.xml"].decode("utf-8")
        rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
        nxt = max([int(i) for i in re.findall(r'Id="rId(\d+)"', rels)], default=0) + 1
        entries, k = "", 0
        for family, faces in wanted.items():
            face_xml = ""
            for face, chars in faces.items():
                path = have[family][face]
                font = TTFont(path, lazy=True)
                fs_type = font["OS/2"].fsType
                font.close()
                if fs_type & 0x0002:  # restricted licence embedding
                    report["skipped"].append(f"{family} {face}: its licence does not allow embedding")
                    continue
                data = eot(subset_ttf(path, BASE_CHARS + "".join(sorted(chars))))
                k += 1
                part = f"ppt/fonts/font{k}.fntdata"
                parts[part] = data
                order.append(part)
                rid = f"rId{nxt}"
                nxt += 1
                rels = rels.replace("</Relationships>",
                                    f'<Relationship Id="{rid}" Type="{REL_FONT}" Target="fonts/font{k}.fntdata"/></Relationships>')
                face_xml += f'<p:{face} r:id="{rid}"/>'
                report["embedded"].append({"family": family, "face": face, "bytes": len(data)})
            if face_xml:
                pitch = 1 if "mono" in family.lower() else 2  # fixed / variable pitch
                entries += (f'<p:embeddedFont><p:font typeface="{family}" pitchFamily="{pitch}" charset="0"/>'
                            f'{face_xml}</p:embeddedFont>')
        if not entries:
            if dest != pptx:
                dest.write_bytes(pptx.read_bytes())
            return report
        # schema order: ... sldSz, notesSz, smartTags?, embeddedFontLst, custShowLst?, ..., defaultTextStyle
        m = re.search(r"<p:notesSz[^>]*/>", pres) or re.search(r"<p:sldSz[^>]*/>", pres)
        pres = pres[: m.end()] + f"<p:embeddedFontLst>{entries}</p:embeddedFontLst>" + pres[m.end():]
        pres = re.sub(r"<p:presentation\b", '<p:presentation embedTrueTypeFonts="1" saveSubsetFonts="1"', pres, count=1)
        ct = parts["[Content_Types].xml"].decode("utf-8")
        if 'Extension="fntdata"' not in ct:
            ct = ct.replace("<Default ", '<Default Extension="fntdata" ContentType="application/x-fontdata"/><Default ', 1)
        parts["ppt/presentation.xml"] = pres.encode("utf-8")
        parts["ppt/_rels/presentation.xml.rels"] = rels.encode("utf-8")
        parts["[Content_Types].xml"] = ct.encode("utf-8")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx", dir=dest.parent) as tmp:
            tmp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as z:
                for name in dict.fromkeys(order):
                    if name in parts:
                        z.writestr(name, parts[name])
            tmp_path.replace(dest)
        finally:
            tmp_path.unlink(missing_ok=True)
        report["added_bytes"] = sum(e["bytes"] for e in report["embedded"])
    except Exception as exc:  # embedding is a nicety: the deck as compiled stays valid
        logger.warning(f"font_embed: skipped ({type(exc).__name__}: {exc})")
        report = {"embedded": [], "skipped": [f"failed: {type(exc).__name__}: {exc}"], "added_bytes": 0}
        if dest != pptx and pptx.exists():
            dest.write_bytes(pptx.read_bytes())
    return report


def embed_warnings(report: dict[str, Any]) -> list[dict[str, str]]:
    """Compile-result style warnings for what could not be embedded."""
    return [{"code": "FONT_EMBED_SKIPPED", "message": reason} for reason in report.get("skipped", [])]
