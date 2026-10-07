"""The node pass's checks (§3.2, §3.6): classify every plan component of a slide and clean
the skeleton the generator wrote, before the nodes are drawn.

    result = check_skeleton(xml, plan)
    result["xml"]         skeleton with every kept ref tag self-closing, its tag and attributes fixed
    result["components"] {component_id: {kind, tag, family, variant, status, codes}}
    result["issues"]      [{code, severity, ref, message}]
    result["ok"]          no error-severity issue (errors go to the compile repairer)

`status` (1a measure 1, first try): ok | missing | bypassed | duplicate | kind_mismatch |
children | attr | variant. `unknown_ref` tags belong to no component; they are counted on
the slide (result["unknown_refs"]).
"""

from __future__ import annotations

import html
import re
from typing import Any

from src.compiler.nodes import spec

ERROR, WARNING, REPORT = "error", "warning", "report"

SEVERITY = {
    "NODE_REF_UNKNOWN": ERROR, "NODE_REF_DUPLICATE": ERROR, "NODE_MISSING": ERROR,
    "NODE_KIND_NO_REF": ERROR, "NODE_EXPAND_FAILED": ERROR,
    "NODE_BYPASSED": WARNING, "NODE_KIND_MISMATCH": WARNING, "NODE_CHILDREN_DROPPED": WARNING,
    "NODE_ATTR_IGNORED": WARNING, "NODE_VARIANT_UNKNOWN": WARNING, "NODE_VARIANT_UNMET": WARNING,
    "NODE_NO_SIZE": WARNING, "NODE_EMPTY_PLAN": WARNING,
    "NODE_OVERFULL": REPORT, "NODE_UNDERFILLED": REPORT,
}

# component status from its codes, worst first (measure 1)
_STATUS = [("NODE_MISSING", "missing"), ("NODE_BYPASSED", "bypassed"), ("NODE_REF_DUPLICATE", "duplicate"),
           ("NODE_KIND_MISMATCH", "kind_mismatch"), ("NODE_CHILDREN_DROPPED", "children"),
           ("NODE_ATTR_IGNORED", "attr"), ("NODE_VARIANT_UNKNOWN", "variant"), ("NODE_VARIANT_UNMET", "variant")]

_OPEN = re.compile(r"<([A-Z][A-Za-z]*)\b([^<>]*?)(/?)>")
_ATTR = re.compile(r'([\w.:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
_WORD = re.compile(r"[a-z0-9₹$€£%]+(?:[.,'’][a-z0-9]+)*")
_TEXT_ATTRS = ("label", "title", "text", "date", "name")

BYPASS_SHARE = 0.5     # §3.6: >= 50% of the component's item text hand-built in the XML
ITEM_WORDS_SHARE = 0.6  # an item counts as hand-built when this share of its words is there


def attrs_of(s: str) -> dict[str, str]:
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3) for m in _ATTR.finditer(s)}


def words(text: str) -> list[str]:
    return _WORD.findall(html.unescape(text).lower())


def ref_tags(xml: str) -> list[dict[str, Any]]:
    """Every element carrying `ref`: tag, attrs, start / end offsets, its children's XML."""
    out = []
    pos = 0
    while True:
        m = _OPEN.search(xml, pos)
        if not m:
            return out
        tag, raw, selfclose = m.group(1), m.group(2), m.group(3)
        a = attrs_of(raw)
        if "ref" not in a:
            pos = m.end()
            continue
        end, body = m.end(), ""
        if not selfclose:
            depth, k = 1, m.end()
            pat = re.compile(rf"<(/?){tag}\b[^<>]*?(/?)>")
            while depth:
                n = pat.search(xml, k)
                if not n:  # unclosed: treat the rest as its body
                    k = len(xml)
                    break
                if n.group(1):
                    depth -= 1
                elif not n.group(2):
                    depth += 1
                k = n.end()
            body = xml[m.end():n.start() if n and not depth else k]
            end = k
        out.append({"tag": tag, "attrs": a, "start": m.start(), "end": end, "body": body})
        pos = end


def xml_words(xml: str) -> set[str]:
    """Words a reader sees in the XML: element text and the item attributes (label, title, ...)."""
    found = set(words(re.sub(r"<[^>]+>", " ", xml)))
    for m in _OPEN.finditer(xml):
        for k, v in attrs_of(m.group(2)).items():
            if k in _TEXT_ATTRS:
                found.update(words(v))
    return found


def hand_built_share(comp: dict, seen: set[str]) -> float:
    its = [i for i in spec.items(comp) if words(i)]
    if not its:
        return 0.0
    hit = 0
    for i in its:
        ws = words(i)
        hit += sum(w in seen for w in ws) / len(ws) >= ITEM_WORDS_SHARE
    return hit / len(its)


def empty(comp: dict) -> bool:
    cd = comp.get("content_data") or {}
    if comp.get("kind") == "kpi_row":
        return not any(str(v).strip() for v in cd.get("kpi_values") or [])
    if comp.get("kind") == "chart":
        return not (cd.get("chart_values") or cd.get("chart_series"))
    return not any(i.strip() for i in spec.items(comp))


def _tag_xml(tag: str, a: dict[str, str]) -> str:
    return f"<{tag} " + " ".join(f'{k}="{html.escape(v, quote=True)}"' for k, v in a.items()) + " />"


def check_skeleton(xml: str, plan: dict) -> dict[str, Any]:
    comps = {c["component_id"]: c for c in plan.get("components") or []}
    issues: list[dict] = []
    codes: dict[str, list[str]] = {cid: [] for cid in comps}
    info: dict[str, dict] = {}
    unknown = 0

    def flag(code: str, ref: str | None, message: str) -> None:
        issues.append({"code": code, "severity": SEVERITY[code], "ref": ref, "message": message})
        if ref in codes:
            codes[ref].append(code)

    edits: list[tuple[int, int, str]] = []   # (start, end, replacement)
    placed: set[str] = set()
    for t in ref_tags(xml):
        ref, tag, a = t["attrs"]["ref"], t["tag"], dict(t["attrs"])
        comp = comps.get(ref)
        if comp is None:
            unknown += 1
            flag("NODE_REF_UNKNOWN", None, f'<{tag} ref="{ref}">: no component "{ref}" on this slide '
                 f"(components: {', '.join(comps)})")
            edits.append((t["start"], t["end"], ""))
            continue
        kind = comp["kind"]
        if kind in spec.NO_REF_KINDS:
            flag("NODE_KIND_NO_REF", ref, f'"{ref}" is a {kind}: draw it yourself, without ref')
            edits.append((t["start"], t["end"], ""))
            continue
        if ref in placed:
            flag("NODE_REF_DUPLICATE", ref, f'ref="{ref}" is placed twice; place each component once')
            edits.append((t["start"], t["end"], ""))
            continue
        placed.add(ref)
        allowed = spec.tags_for(kind)
        if tag not in allowed:
            flag("NODE_KIND_MISMATCH", ref, f'<{tag}> for a {kind}; <{allowed[0]}> used')
            tag = allowed[0]
        if t["body"].strip():
            flag("NODE_CHILDREN_DROPPED", ref, f'<{tag} ref="{ref}"> had children; code writes them')
        keep_native = spec.NATIVE_ATTRS.get(tag, set()) if spec.family(tag) == "native" else set()
        dropped = [k for k in a if k not in spec.LAYOUT_ATTRS and k not in keep_native]
        if dropped:
            flag("NODE_ATTR_IGNORED", ref, f"<{tag} ref=\"{ref}\">: {', '.join(dropped)} removed "
                 "(content and styling of a ref node come from the plan)")
            for k in dropped:
                a.pop(k)
        variant, vcode, note = spec.resolve_variant(kind, tag, comp, a.get("variant"))
        if vcode:
            flag(vcode, ref, note)
        if variant:
            a["variant"] = variant
        else:
            a.pop("variant", None)
        if not any(k in a for k in ("w", "h", "grow", "minH")) and tag not in ("Text", "Table", "Ul"):
            flag("NODE_NO_SIZE", ref, f'<{tag} ref="{ref}"> has no w / h / grow; grow="1" used')
            a["grow"] = "1"
        if empty(comp):
            flag("NODE_EMPTY_PLAN", ref, f'"{ref}" has no content in the plan; nothing drawn')
            edits.append((t["start"], t["end"], ""))
        else:
            edits.append((t["start"], t["end"], _tag_xml(tag, a)))
        info[ref] = {"tag": tag, "variant": variant}

    cleaned = xml
    for s, e, rep in sorted(edits, reverse=True):
        cleaned = cleaned[:s] + rep + cleaned[e:]

    seen = xml_words(cleaned)
    for cid, comp in comps.items():
        if cid in placed or comp["kind"] in spec.NO_REF_KINDS or empty(comp):
            continue
        share = hand_built_share(comp, seen)
        if share >= BYPASS_SHARE:
            flag("NODE_BYPASSED", cid, f'"{cid}" has no node but {share:.0%} of its items are written by hand; kept')
        else:
            flag("NODE_MISSING", cid, f'"{cid}" ({comp["kind"]}) is not on the slide: place '
                 f'<{spec.tags_for(comp["kind"])[0]} ref="{cid}" />')

    out_comps = {}
    for cid, comp in comps.items():
        if comp["kind"] in spec.NO_REF_KINDS:
            continue
        status = next((s for code, s in _STATUS if code in codes[cid]), "ok")
        tag = (info.get(cid) or {}).get("tag") or spec.tags_for(comp["kind"])[0]
        out_comps[cid] = {"kind": comp["kind"], "tag": tag, "family": spec.family(tag),
                          "variant": (info.get(cid) or {}).get("variant"), "status": status,
                          "codes": codes[cid], "empty_plan": empty(comp)}
    return {"xml": cleaned, "components": out_comps, "issues": issues, "unknown_refs": unknown,
            "ok": not any(i["severity"] == ERROR for i in issues)}


def repair_note(issues: list[dict]) -> str:
    """The error issues as guidance for the repair call."""
    errs = [i for i in issues if i["severity"] == ERROR]
    return "\n".join(f"- {i['code']}: {i['message']}" for i in errs)
