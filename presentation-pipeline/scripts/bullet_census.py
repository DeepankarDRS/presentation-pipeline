"""What the LLM really wrote on its own lists, LLM-free: can the bullet node replicate it?

    python -m scripts.bullet_census --src C:/dev/presentation-pipeline/presentation-pipeline/output

Every distinct saved slide (output/**/slides.json, galleries and replays skipped) with a bullet_list component and
<Ul> / <Ol> in its XML: the attributes on the list, on its <Li>s, the inline tags inside them, the box around the list,
the markers typed by hand. Counts slides and lists, so one odd run shows as one. Writes docs/eval/bullet-node/census.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lxml import etree  # noqa: E402

SKIP = ("composition", "gallery", "replay", "-chart-", "syntax-audit")
OUT = ROOT / "docs" / "eval" / "bullet-node" / "census.json"
_HAND_MARK = re.compile(r"^\s*(?:[•·▪◦\-–—*]\s|\d+[.)]\s)")


def lists_in(xml: str):
    try:
        root = etree.fromstring(f"<x>{re.sub(r'&(?![a-zA-Z#])', '&amp;', xml)}</x>".encode("utf-8"),
                                etree.XMLParser(recover=True, huge_tree=True))
    except etree.XMLSyntaxError:
        return []
    return [e for e in root.iter("Ul", "Ol")] if root is not None else []


def census(src: Path) -> dict:
    ul, li, inline, box = Counter(), Counter(), Counter(), Counter()
    tags, items, split, values = Counter(), Counter(), Counter(), {k: Counter() for k in ("fontSize", "lineHeight", "color")}
    seen, slides, n_lists, hand, in_card, li_colored = set(), 0, 0, 0, 0, 0
    for sj in sorted(src.rglob("slides.json")):
        rel = sj.relative_to(src).as_posix()
        if any(k in rel for k in SKIP):
            continue
        try:
            data = json.loads(sj.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for s in data if isinstance(data, list) else []:
            xml, plan = s.get("xml") or "", s.get("slide_plan") or {}
            if not xml or not any(c.get("kind") == "bullet_list" for c in plan.get("components") or []):
                continue
            h = hashlib.sha1(xml.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            found = lists_in(xml)
            if not found:
                continue
            slides += 1
            for e in found:
                n_lists += 1
                tags[e.tag] += 1
                ul.update(e.attrib.keys())
                for k, c in values.items():
                    if k in e.attrib:
                        c[e.attrib[k]] += 1
                kids = [k for k in e if isinstance(k.tag, str) and k.tag == "Li"]
                items[len(kids)] += 1
                li_colored += any("color" in k.attrib for k in kids)
                parent = e.getparent()
                if parent is not None and parent.tag in ("VStack", "HStack"):
                    box.update(k for k in parent.attrib)
                    in_card += any(k in parent.attrib for k in ("backgroundColor", "border.color", "border.width", "padding"))
                for k in kids:
                    li.update(k.attrib.keys())
                    text = "".join(k.itertext())
                    hand += bool(_HAND_MARK.match(text))
                    split[bool(re.search(r"\s[—–]\s|:\s", text))] += 1
                    for i in k.iter():
                        if i is not k and isinstance(i.tag, str):
                            inline[i.tag] += 1
                            inline.update(f"{i.tag}.{a}" for a in i.attrib)
    return {"slides": slides, "lists": n_lists, "tags": dict(tags), "lists_in_a_box": in_card, "lists_with_a_coloured_li": li_colored,
            "items_per_list": dict(sorted(items.items())), "items_with_head_split": split[True], "items_without": split[False],
            "hand_typed_markers": hand, "list_attrs": dict(ul.most_common()), "li_attrs": dict(li.most_common()),
            "inline": dict(inline.most_common()), "parent_attrs": dict(box.most_common(20)),
            "values": {k: dict(c.most_common(10)) for k, c in values.items()}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, default=ROOT / "output")
    a = ap.parse_args()
    r = census(a.src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
