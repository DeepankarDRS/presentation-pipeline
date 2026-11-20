"""What code knows about a compiled slide, per plan component, for the visual critic and the fixer (2026-11-20).

Every component has an id: code stamps id="cmp-<component id>" (or keeps the node's own, tbl-<id>) on the box a ref
tag becomes (`normalize_result["component_boxes"]`); the generator writes id="<component id>" on a hand-drawn
component's box. From geometry.json each component gets one box, a mark number (drawn on the screenshot, set-of-mark
style) and the facts code measured about it (fit-grow's SLIDE_DENSE spills, the geometry audit), in plain words.

    components(plan, normalize_result, geometry_path, tags_xml) -> [Component]
    measured_facts(comps, compile_warnings, layout_issues)      -> [Fact]
    annotate(tags_xml, comps)                                    -> the ref-tag XML with one comment per component
    draw_marks(png, comps, out_png)                              -> the marked screenshot
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.compiler.nodes import composed, spec, tile_groups, validate

# geometry-audit codes that are a measured defect at tier error: code could not fix them, the fixer re-lays the slide
DEFECT_CODES = {"GEOM_SPILL", "GEOM_COLLISION", "GEOM_OFF_SLIDE"}
SLIDE_W, SLIDE_H = 1280, 720


@dataclass
class Component:
    n: int                     # the mark number on the screenshot
    id: str                    # the plan's component_id
    kind: str
    by: str                    # "code" (a ref tag) | "hand"
    box_ids: list[str]         # the ids its box(es) carry in the drawn XML
    variant: str = ""
    box: tuple[float, float, float, float] | None = None   # x, y, w, h in slide px
    needs: list[str] = field(default_factory=list)          # "height 394 -> 519px" when code measured a shortfall


@dataclass
class Fact:
    text: str
    component: str | None      # component id, None = the slide
    defect: bool               # measured and left unfixed by code: goes straight to the fixer


def variants(kind: str) -> dict[str, str]:
    """A code-drawn kind's variant names -> their one-line look (block-variants.yaml)."""
    if kind in tile_groups.KINDS:
        return dict(tile_groups.node(kind)["prompts"])
    return {n: v.get("prompt", "") for n, v in (spec.blocks().get(kind, {}).get("variants") or {}).items()}


def _boxes(geometry: dict) -> dict[str, tuple[float, float, float, float]]:
    out: dict[str, tuple[float, float, float, float]] = {}

    def walk(nd: dict) -> None:
        if nd.get("id"):
            out.setdefault(nd["id"], (nd["x"], nd["y"], nd["w"], nd["h"]))
        for c in nd.get("children") or []:
            walk(c)
    for s in geometry.get("slides") or []:
        walk(s)
    return out


def _union(rects: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    if not rects:
        return None
    x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
    x1, y1 = max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)
    return x0, y0, x1 - x0, y1 - y0


def components(plan: dict | None, normalize_result: dict | None, geometry_path: str | Path | None,
               tags_xml: str = "") -> list[Component]:
    """The slide's plan components in plan order, numbered from 1, with their box when geometry.json has it."""
    norm = normalize_result or {}
    code_boxes: dict[str, list[str]] = norm.get("component_boxes") or {}
    geo = {}
    if geometry_path and Path(geometry_path).exists():
        geo = _boxes(json.loads(Path(geometry_path).read_text(encoding="utf-8")))
    tags = {t["attrs"]["ref"]: t for t in validate.ref_tags(tags_xml)} if tags_xml else {}
    out: list[Component] = []
    for c in (plan or {}).get("components") or []:
        cid = c.get("component_id")
        if not cid:
            continue
        kind = c.get("kind", "")
        if cid in code_boxes:
            by, ids = "code", list(code_boxes[cid])
            names = list(variants(kind))
            tag = tags.get(cid)
            variant = ((norm.get("component_variants") or {}).get(cid)
                       or (tag["attrs"].get("variant") if tag else None) or (f"{names[0]} (default)" if names else ""))
        else:
            by, ids, variant = "hand", [cid], ""
        out.append(Component(len(out) + 1, cid, kind, by, ids, variant, _union([geo[i] for i in ids if i in geo])))
    return out


def owner(ids: list[str], comps: list[Component]) -> Component | None:
    """The component the first of `ids` (innermost first) belongs to: a box id, or an inner id naming the component
    (lst-<id>, kpil-<id>-0, card-<id>-1, cmp-<id>.2)."""
    for i in ids:
        for c in comps:
            if i in c.box_ids or i == c.id:
                return c
    for i in ids:
        for c in comps:
            if c.by == "code" and re.search(rf"(?:^|-){re.escape(c.id)}(?:$|[-.])", i):
                return c
    return None


_PATH = re.compile(r"\S+(?: > \S+)+")


def _path_ids(text: str) -> list[str]:
    """The ids in a geometry-audit path ("vstack > hstack[1]#cmp-c3 > text[0]#kpil-c3-0"), innermost first."""
    m = _PATH.search(text)
    return list(reversed(re.findall(r"#([^\s>]+)", m.group(0)))) if m else []


def _name(c: Component | None) -> str:
    return f"[{c.n}] {c.id}" if c else "the slide"


def measured_facts(comps: list[Component], compile_warnings: list[dict] | None,
                   layout_issues: list[dict] | None) -> list[Fact]:
    """What code measured and could not fix, in plain words, per component. Records the shortfalls on comps."""
    facts: list[Fact] = []
    for w in compile_warnings or []:
        code = w.get("code") or w.get("type")
        if code == "SLIDE_DENSE":
            shown: set[str] = set()
            for s in w.get("spills") or []:
                c = owner(s.get("ids") or [], comps)
                if s.get("type") in ("hstack", "vstack") and c is None:
                    continue   # a bare stack follows its content: the leaf inside it names the component
                key = c.id if c else s.get("type", "")
                if key in shown:
                    continue
                shown.add(key)
                need = f'{"width" if s.get("kind") == "w" else "height"} {s["have"]} -> {s["need"]}px'
                if c:
                    c.needs.append(need)
                facts.append(Fact(f"{_name(c)}: its {s.get('type')} needs {s['need']}px of "
                                  f"{'width' if s.get('kind') == 'w' else 'height'} but has {s['have']}px; code already "
                                  "shrank gaps, padding and fonts to their floors, so it draws past its box", c.id if c else None, True))
        elif code == "AUTOFIT_SHRANK":
            facts.append(Fact("the slide was taller than the page: the renderer shrank fonts / gaps to fit", None, True))
        elif code in ("SCALE_BELOW_THRESHOLD", "WORD_TOO_WIDE"):
            facts.append(Fact(f"{w.get('message', '')}", None, False))
    for i in layout_issues or []:
        code = str(i.get("code", ""))
        if not (code.startswith("GEOM_") or code in ("LOW_CONTRAST", "PLACEHOLDER_TEXT")):
            continue
        msg = i.get("message", "")
        c = owner(_path_ids(msg), comps)
        text = _PATH.sub("a part", msg)
        defect = code in DEFECT_CODES and i.get("tier") == "error"
        facts.append(Fact(f"{_name(c)}: {text}" + ("" if defect else f" ({code}, borderline: check it on the screenshot)"
                                                    if i.get("tier") == "warning" else f" ({code})"),
                          c.id if c else None, defect))
    return facts


def comment(c: Component) -> str:
    parts = [f"[{c.n}] {c.id}", c.kind, f"variant {c.variant}" if c.variant else "drawn by hand"]
    if c.box:
        parts.append(f"{c.box[2]:.0f}x{c.box[3]:.0f}px")
    parts += [f"needs {n}" for n in c.needs]
    return "<!-- " + " · ".join(parts) + " -->"


def annotate(xml: str, comps: list[Component]) -> str:
    """`xml` with one comment before the first tag of each component (its ref tag, or its id box)."""
    spots: list[tuple[int, str]] = []
    for c in comps:
        keys = [rf'\bref="{re.escape(c.id)}(?:\.\d+)?"'] + [rf'\bid="{re.escape(i)}"' for i in c.box_ids]
        hits = [m.start() for k in keys for m in [re.search(k, xml)] if m]
        if hits:
            spots.append((xml.rfind("<", 0, min(hits)), comment(c)))
    for pos, text in sorted(spots, reverse=True):
        xml = xml[:pos] + text + "\n" + xml[pos:]
    return xml


def table(comps: list[Component]) -> str:
    """One line per component: mark, id, kind, variant, box (x, y, w, h) and shortfalls."""
    return "\n".join(f"[{c.n}] {c.id} · {c.kind} · " + (f"variant {c.variant}" if c.variant else "drawn by hand")
                     + f" · ids {', '.join(c.box_ids)}"
                     + (f" · box x{c.box[0]:.0f} y{c.box[1]:.0f} {c.box[2]:.0f}x{c.box[3]:.0f}px" if c.box else " · no box")
                     + "".join(f" · needs {n}" for n in c.needs) for c in comps)


def draw_marks(png: str | Path, comps: list[Component], out: str | Path) -> str | None:
    """The screenshot with a thin numbered box per component (Set-of-Mark). None when no component has a box."""
    from PIL import Image, ImageDraw, ImageFont
    boxed = [c for c in comps if c.box]
    if not boxed:
        return None
    img = Image.open(png).convert("RGB")
    sx, sy = img.width / SLIDE_W, img.height / SLIDE_H
    d = ImageDraw.Draw(img)
    size = max(14, round(18 * sx))
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    colour = (230, 0, 126)   # magenta: rare on slides
    for c in boxed:
        x, y, w, h = c.box
        r = (x * sx, y * sy, (x + w) * sx - 1, (y + h) * sy - 1)
        d.rectangle(r, outline=colour, width=max(2, round(2 * sx)))
        label = str(c.n)
        tw, th = d.textbbox((0, 0), label, font=font)[2:]
        d.rectangle((r[0], r[1], r[0] + tw + 8, r[1] + th + 6), fill=colour)
        d.text((r[0] + 4, r[1] + 2), label, fill=(255, 255, 255), font=font)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return str(out)


def colour_roles(theme_element: str) -> str:
    """The theme's role colours the critic judges by (accent, positive, negative, warning, surface, text), not the
    whole <Theme> token dump."""
    roles = ("accent", "positive", "negative", "warning", "surface", "surfaceAlt", "textMain", "textMuted", "border")
    found = dict(re.findall(r'\b(\w+)="([0-9A-Fa-f]{6})"', theme_element or ""))
    return ", ".join(f"{r} #{found[r]}" for r in roles if r in found)


def as_dict(c: Component) -> dict[str, Any]:
    return {"n": c.n, "id": c.id, "kind": c.kind, "by": c.by, "box_ids": c.box_ids, "variant": c.variant,
            "box": list(c.box) if c.box else None, "needs": c.needs}
