"""ZIP-level merge of single-slide POM PPTX files.

Each POM-compiled PPTX has exactly one slide with identical theme/master/layout
structure. This module concatenates them at the OPC (ZIP) level, preserving
charts, embedded workbooks, and all relationship references — without
re-compiling POM XML.
"""

from __future__ import annotations

import logging
import os
import re
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

_OOXML_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_PRES_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def merge_pptx_files(pptx_paths: list[Path], output_path: Path) -> Path:
    """Merge single-slide PPTX files into one multi-slide PPTX.

    Uses the first file as the base (its theme, masters, layouts stay).
    For each additional file, copies its slide XML, rels, and all referenced
    parts (charts, embeddings) with renumbered IDs.

    Returns the output path on success, raises on failure.
    """
    if not pptx_paths:
        raise ValueError("No PPTX files to merge")

    if len(pptx_paths) == 1:
        import shutil
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pptx_paths[0], output_path)
        return output_path

    parts: dict[str, bytes] = {}
    with zipfile.ZipFile(pptx_paths[0]) as z:
        for item in z.infolist():
            parts[item.filename] = z.read(item.filename)

    ct_xml = etree.fromstring(parts["[Content_Types].xml"])
    pres_xml = etree.fromstring(parts["ppt/presentation.xml"])
    pres_rels_xml = etree.fromstring(parts["ppt/_rels/presentation.xml.rels"])

    max_rid = 0
    for rel in pres_rels_xml:
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            max_rid = max(max_rid, int(rid[3:]))

    chart_counter = 0
    embed_counter = 0
    for name in parts:
        m = re.match(r"ppt/charts/chart(\d+)\.xml", name)
        if m:
            chart_counter = max(chart_counter, int(m.group(1)))
        m = re.match(r"ppt/embeddings/.*?(\d+)\.\w+", name)
        if m:
            embed_counter = max(embed_counter, int(m.group(1)))

    slide_num = 1

    for src_path in pptx_paths[1:]:
        slide_num += 1

        with zipfile.ZipFile(src_path) as src_zip:
            src_slide = src_zip.read("ppt/slides/slide1.xml")
            try:
                src_slide_rels = etree.fromstring(
                    src_zip.read("ppt/slides/_rels/slide1.xml.rels")
                )
            except KeyError:
                src_slide_rels = None

            new_slide_rels = etree.Element("Relationships", xmlns=_OOXML_NS)

            if src_slide_rels is not None:
                for rel in src_slide_rels:
                    rel_type = rel.get("Type")
                    target = rel.get("Target")

                    if "slideLayout" in rel_type:
                        new_rel = deepcopy(rel)
                        new_rel.set("Target", "../slideLayouts/slideLayout1.xml")
                        new_slide_rels.append(new_rel)

                    elif "chart" in rel_type:
                        chart_counter += 1
                        src_chart_file = target.replace("../charts/", "")
                        src_chart_path = "ppt/charts/" + src_chart_file
                        new_chart_path = f"ppt/charts/chart{chart_counter}.xml"

                        parts[new_chart_path] = src_zip.read(src_chart_path)

                        src_chart_rels_path = (
                            "ppt/charts/_rels/"
                            + src_chart_file.replace(".xml", ".xml.rels")
                        )
                        try:
                            chart_rels = etree.fromstring(
                                src_zip.read(src_chart_rels_path)
                            )
                            new_chart_rels = deepcopy(chart_rels)

                            for crel in new_chart_rels:
                                ctarget = crel.get("Target", "")
                                if "embeddings" in ctarget:
                                    embed_counter += 1
                                    src_embed_file = ctarget.replace(
                                        "../embeddings/", ""
                                    )
                                    ext = os.path.splitext(src_embed_file)[1]
                                    new_embed_file = f"workbook{embed_counter}{ext}"
                                    new_embed_path = (
                                        f"ppt/embeddings/{new_embed_file}"
                                    )

                                    parts[new_embed_path] = src_zip.read(
                                        "ppt/embeddings/" + src_embed_file
                                    )
                                    crel.set(
                                        "Target",
                                        f"../embeddings/{new_embed_file}",
                                    )

                                    etree.SubElement(
                                        ct_xml,
                                        "Override",
                                        PartName=f"/{new_embed_path}",
                                        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    )

                            new_chart_rels_path = (
                                f"ppt/charts/_rels/chart{chart_counter}.xml.rels"
                            )
                            parts[new_chart_rels_path] = etree.tostring(
                                new_chart_rels,
                                xml_declaration=True,
                                encoding="UTF-8",
                                standalone=True,
                            )
                        except KeyError:
                            pass

                        new_rel = deepcopy(rel)
                        new_rel.set(
                            "Target", f"../charts/chart{chart_counter}.xml"
                        )
                        new_slide_rels.append(new_rel)

                        etree.SubElement(
                            ct_xml,
                            "Override",
                            PartName=f"/{new_chart_path}",
                            ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
                        )
                    else:
                        new_rel = deepcopy(rel)
                        new_slide_rels.append(new_rel)

            new_slide_path = f"ppt/slides/slide{slide_num}.xml"
            parts[new_slide_path] = src_slide

            new_rels_path = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
            parts[new_rels_path] = etree.tostring(
                new_slide_rels,
                xml_declaration=True,
                encoding="UTF-8",
                standalone=True,
            )

            max_rid += 1
            new_rid = f"rId{max_rid}"
            etree.SubElement(
                pres_rels_xml,
                "Relationship",
                Id=new_rid,
                Type=f"{_REL_NS}/slide",
                Target=f"slides/slide{slide_num}.xml",
            )

            sld_id_list = pres_xml.find(f"{{{_PRES_NS}}}sldIdLst")
            if sld_id_list is None:
                sld_id_list = etree.SubElement(
                    pres_xml, f"{{{_PRES_NS}}}sldIdLst"
                )

            max_sld_id = 255
            for sld_id in sld_id_list:
                sid = int(sld_id.get("id", "255"))
                max_sld_id = max(max_sld_id, sid)

            new_sld_id = etree.SubElement(
                sld_id_list, f"{{{_PRES_NS}}}sldId"
            )
            new_sld_id.set("id", str(max_sld_id + 1))
            new_sld_id.set(f"{{{_REL_NS}}}id", new_rid)

            etree.SubElement(
                ct_xml,
                "Override",
                PartName=f"/{new_slide_path}",
                ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
            )

    parts["[Content_Types].xml"] = etree.tostring(
        ct_xml, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    parts["ppt/presentation.xml"] = etree.tostring(
        pres_xml, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    parts["ppt/_rels/presentation.xml.rels"] = etree.tostring(
        pres_rels_xml, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, data in sorted(parts.items()):
            zf.writestr(path, data)

    logger.info(f"pptx_merge: merged {slide_num} slides → {output_path}")
    return output_path
