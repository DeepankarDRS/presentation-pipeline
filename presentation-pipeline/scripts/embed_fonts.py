"""Embed TrueType fonts in a .pptx the way PowerPoint does (font embedding test, §13 R1).

    python -m scripts.embed_fonts in.pptx out.pptx --family Inter \
        --regular src/node/fonts/Inter-Regular.ttf --bold src/node/fonts/Inter-Bold.ttf

PowerPoint keeps embedded fonts as Embedded OpenType parts (ppt/fonts/*.fntdata,
content type application/x-fontdata) listed in presentation.xml <p:embeddedFontLst>.
This writes uncompressed EOT (version 0x00020001: header + the TrueType file), which
the EOT spec allows. Experiment only: not wired into the compiler. The OFL licence of
Inter / JetBrains Mono allows embedding in documents.
"""

from __future__ import annotations

import argparse
import re
import struct
import zipfile
from pathlib import Path

REL_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"


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


def embed(src: Path, dst: Path, family: str, faces: dict[str, Path]) -> None:
    with zipfile.ZipFile(src) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    ids = [int(i) for i in re.findall(r'Id="rId(\d+)"', rels)]
    nxt = max(ids, default=0) + 1
    face_xml = ""
    for k, (face, path) in enumerate(faces.items(), start=1):
        name = f"font{k}.fntdata"
        parts[f"ppt/fonts/{name}"] = eot(path.read_bytes())
        rid = f"rId{nxt}"
        nxt += 1
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{REL_FONT}" Target="fonts/{name}"/></Relationships>')
        face_xml += f'<p:{face} r:id="{rid}"/>'
    lst = (f'<p:embeddedFontLst><p:embeddedFont><p:font typeface="{family}" pitchFamily="2" charset="0"/>'
           f"{face_xml}</p:embeddedFont></p:embeddedFontLst>")
    # schema order: ... sldSz, notesSz, smartTags?, embeddedFontLst, custShowLst?, ..., defaultTextStyle
    m = re.search(r"<p:notesSz[^>]*/>", pres)
    pres = pres[: m.end()] + lst + pres[m.end():]
    pres = re.sub(r"<p:presentation\b", '<p:presentation embedTrueTypeFonts="1"', pres, count=1)
    ct = parts["[Content_Types].xml"].decode("utf-8")
    if 'Extension="fntdata"' not in ct:
        ct = ct.replace("<Types ", "<Types ", 1).replace(
            "<Default ", '<Default Extension="fntdata" ContentType="application/x-fontdata"/><Default ', 1)
    parts["ppt/presentation.xml"] = pres.encode("utf-8")
    parts["ppt/_rels/presentation.xml.rels"] = rels.encode("utf-8")
    parts["[Content_Types].xml"] = ct.encode("utf-8")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in parts.items():
            z.writestr(n, data)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--family", required=True)
    for face in ("regular", "bold", "italic", "boldItalic"):
        ap.add_argument(f"--{face}", type=Path)
    a = ap.parse_args()
    faces = {f: getattr(a, f) for f in ("regular", "bold", "italic", "boldItalic") if getattr(a, f)}
    embed(a.src, a.dst, a.family, faces)
    print(f"{a.dst}: embedded {a.family} ({', '.join(faces)})")


if __name__ == "__main__":
    main()
