"""Embed TrueType fonts in a .pptx the way PowerPoint does (font embedding test, §13 R1).

    python -m scripts.embed_fonts in.pptx out.pptx \
        --font "Inter:regular=src/node/fonts/Inter-Regular.ttf,bold=src/node/fonts/Inter-Bold.ttf" \
        --font "JetBrains Mono:regular=src/node/fonts/JetBrainsMono-Regular.ttf"

PowerPoint keeps embedded fonts as Embedded OpenType parts (ppt/fonts/*.fntdata,
content type application/x-fontdata) listed in presentation.xml <p:embeddedFontLst>.
This writes uncompressed EOT (version 0x00020001: header + the TrueType file), which
the EOT spec allows. Experiment only: not wired into the compiler. The OFL licence of
Inter / JetBrains Mono allows embedding in documents.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

from src.compiler.font_embed import eot

REL_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"


def embed(src: Path, dst: Path, fonts: dict[str, dict[str, Path]]) -> None:
    """fonts: {family: {face: ttf path}}, face in regular / bold / italic / boldItalic."""
    with zipfile.ZipFile(src) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    ids = [int(i) for i in re.findall(r'Id="rId(\d+)"', rels)]
    nxt = max(ids, default=0) + 1
    entries, k = "", 0
    for family, faces in fonts.items():
        face_xml = ""
        for face, path in faces.items():
            k += 1
            name = f"font{k}.fntdata"
            parts[f"ppt/fonts/{name}"] = eot(path.read_bytes())
            rid = f"rId{nxt}"
            nxt += 1
            rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{REL_FONT}" Target="fonts/{name}"/></Relationships>')
            face_xml += f'<p:{face} r:id="{rid}"/>'
        pitch = 1 if "mono" in family.lower() else 2  # fixed / variable pitch
        entries += f'<p:embeddedFont><p:font typeface="{family}" pitchFamily="{pitch}" charset="0"/>{face_xml}</p:embeddedFont>'
    lst = f"<p:embeddedFontLst>{entries}</p:embeddedFontLst>"
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
    ap.add_argument("--font", action="append", required=True,
                    help='"Family:regular=path,bold=path,italic=path,boldItalic=path" (repeatable)')
    a = ap.parse_args()
    fonts = {}
    for spec in a.font:
        family, faces = spec.split(":", 1)
        fonts[family] = {k: Path(v) for k, v in (f.split("=", 1) for f in faces.split(","))}
    embed(a.src, a.dst, fonts)
    print(f"{a.dst}: embedded " + "; ".join(f"{f} ({', '.join(v)})" for f, v in fonts.items()))


if __name__ == "__main__":
    main()
