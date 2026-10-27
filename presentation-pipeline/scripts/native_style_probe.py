"""Which style attributes does POM 10.3.0 take on each native node? LLM-free probe for composition spec §11.3 R2.

    python -m scripts.native_style_probe                 # writes docs/eval/composition-left/r2-attributes.{json,md}

For every native node (Table/Tr/Td, Chart, Ul/Li, Timeline/TimelineItem, ProcessArrow/ProcessArrowStep, Flow/FlowNode,
Pyramid/PyramidLevel, Tree/TreeItem, Matrix/MatrixItem) one baseline slide is built, then one probe slide per
attribute group on the group tag and on one item tag: the common box attributes (attributes.yaml), text attributes,
and the node's own attributes (llm.md). Colours are $tokens (the pipeline's only colours); a token value POM rejects
is retried in hex, so "hex only" shows up. Each probe is classified twice:

- POM (scripts/native_style_probe.mjs, no fit-grow, no post-process): **rejected** (parseXml / buildPptx throws),
  **applied** (the pptx slide / chart XML differs from the baseline), **ignored** (accepted, output identical).
- normalizer (normalize_xml, the pipeline's step before POM): **kept** or **dropped** (+ the issue codes it logged).

"effective" = kept by the normalizer AND applied by POM: what an LLM attribute can really do on that node today.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.style_resolver import resolve_theme  # noqa: E402
from src.compiler.normalizer import ensure_single_theme, normalize_xml  # noqa: E402

DOCS = ROOT / "docs" / "eval" / "composition-left"
WORK = ROOT / "output" / "composition-left" / "r2"

# ── baselines: {G} = the group tag's attributes, {I} = the first item's, {S} = a sub tag's ─────────────────────

BASE = {
    "Table": ('<Table w="700" cellBorder.color="$border" cellBorder.width="1"{G}><Col /><Col />'
              '<Tr{I}><Td{S}>Channel</Td><Td>ROAS</Td></Tr><Tr><Td>Search</Td><Td>4.1x</Td></Tr>'
              '<Tr><Td>Display</Td><Td>2.6x</Td></Tr></Table>'),
    "Chart": ('<Chart chartType="bar" w="700" h="360"{G}><ChartSeries name="Revenue"{I}>'
              '<ChartDataPoint label="Q1" value="6"{S} /><ChartDataPoint label="Q2" value="7" />'
              '<ChartDataPoint label="Q3" value="9" /></ChartSeries></Chart>'),
    "Ul": '<Ul fontSize="20" w="700"{G}><Li{I}>Scale exact match</Li><Li>Cut broad leakage</Li><Li>Weekly bid review</Li></Ul>',
    "Timeline": ('<Timeline direction="horizontal" w="1000" h="200"{G}><TimelineItem date="Jul" title="Activation"{I} />'
                 '<TimelineItem date="Sep" title="Festive push" description="Bundles" color="$positive" /><TimelineItem date="Nov" title="Retention" /></Timeline>'),
    "ProcessArrow": ('<ProcessArrow direction="horizontal" w="1000" h="100"{G}><ProcessArrowStep label="Audit"{I} />'
                     '<ProcessArrowStep label="Fix" /><ProcessArrowStep label="Scale" /></ProcessArrow>'),
    "Flow": ('<Flow direction="horizontal" w="1000" h="240"{G}><FlowNode id="a" shape="flowChartProcess" text="Search"{I} />'
             '<FlowNode id="b" shape="flowChartProcess" text="Cart" /><FlowNode id="c" shape="flowChartTerminator" text="Paid" />'
             '<FlowConnection from="a" to="b"{S} /><FlowConnection from="b" to="c" /></Flow>'),
    "Pyramid": ('<Pyramid direction="up" w="700" h="360"{G}><PyramidLevel label="Leadership"{I} />'
                '<PyramidLevel label="Loyal buyers" /><PyramidLevel label="Quality" /></Pyramid>'),
    "Tree": ('<Tree layout="vertical" w="800" h="360"{G}><TreeItem label="Head of Growth"{I}><TreeItem label="Performance" />'
             '<TreeItem label="Retention" /></TreeItem></Tree>'),
    "Matrix": ('<Matrix w="700" h="460"{G}><MatrixAxes x="Effort" y="Impact" /><MatrixQuadrants topLeft="Quick wins" '
               'topRight="Big bets" bottomLeft="Fill-ins" bottomRight="Avoid" /><MatrixItem label="Bundles" x="0.2" y="0.8"{I} />'
               '<MatrixItem label="Fleet" x="0.8" y="0.7" /></Matrix>'),
}
ITEM = {"Table": "Tr", "Chart": "ChartSeries", "Ul": "Li", "Timeline": "TimelineItem", "ProcessArrow": "ProcessArrowStep",
        "Flow": "FlowNode", "Pyramid": "PyramidLevel", "Tree": "TreeItem", "Matrix": "MatrixItem"}
SUB = {"Table": "Td", "Chart": "ChartDataPoint", "Flow": "FlowConnection"}

# attribute groups: name -> attribute string (one probe each). Colours as tokens; HEX[...] gives the hex retry.
BOX = {
    "backgroundColor": 'backgroundColor="$accentSoft"',
    "border": 'border.color="$accent" border.width="3"',
    "borderLeft": 'borderLeft.color="$accent" borderLeft.width="6"',
    "borderRadius": 'borderRadius="16"',
    "padding": 'padding="24"',
    "shadow": 'shadow.type="outer" shadow.blur="8" shadow.offset="3" shadow.color="000000"',
    "opacity": 'opacity="0.5"',
    "backgroundGradient": 'backgroundGradient="linear-gradient(90deg, #2563EB 0%, #0EA5E9 100%)"',
    # measured against the backgroundColor probe (REF): a radius or opacity shows only on a filled box
    "borderRadius+fill": 'backgroundColor="$accentSoft" borderRadius="16"',
    "opacity+fill": 'backgroundColor="$accentSoft" opacity="0.5"',
}
REF = {"borderRadius+fill": "backgroundColor", "opacity+fill": "backgroundColor"}
TEXT = {
    "fontSize": 'fontSize="26"', "color": 'color="$negative"', "bold": 'bold="true"', "italic": 'italic="true"',
    "fontFamily": 'fontFamily="Inter"', "textAlign": 'textAlign="center"', "lineHeight": 'lineHeight="1.8"',
    "letterSpacing": 'letterSpacing="3"', "underline": 'underline="true"', "highlight": 'highlight="$warningSoft"',
    "textColor": 'textColor="$negative"',
}
OWN = {   # the node's own attributes (llm.md), by tag
    "Table": {"defaultRowHeight": 'defaultRowHeight="56"', "cellBorder.dashType": 'cellBorder.dashType="dash"'},
    "Tr": {"height": 'height="64"'},
    "Td": {"colspan": 'colspan="2"', "strike": 'strike="true"', "subscript": 'subscript="true"'},
    "Chart": {"showLegend": 'showLegend="true"', "showTitle": 'showTitle="true" title="Revenue"',
              "chartColors": "chartColors='[\"$negative\"]'", "chartType=line": 'chartType="line"'},
    "ChartSeries": {}, "ChartDataPoint": {},
    "Ul": {"strike": 'strike="true"'},
    "Li": {"strike": 'strike="true"'},
    "Timeline": {"dateColor": 'dateColor="$negative"', "titleColor": 'titleColor="$negative"',
                 "descriptionColor": 'descriptionColor="$negative"', "connectorColor": 'connectorColor="$negative"',
                 "connectorGradient": 'connectorGradient="linear-gradient(90deg, #2563EB 0%, #DC2626 100%)"',
                 "useColorForDate": 'useColorForDate="true"', "direction=vertical": 'direction="vertical"'},
    "TimelineItem": {"description": 'description="Search scaling"', "dateColor": 'dateColor="$negative"'},
    "ProcessArrow": {"itemWidth": 'itemWidth="220"', "itemHeight": 'itemHeight="60"', "gap": 'gap="12"',
                     "strike": 'strike="true"', "direction=vertical": 'direction="vertical"'},
    "ProcessArrowStep": {},
    "Flow": {"nodeWidth": 'nodeWidth="180"', "nodeHeight": 'nodeHeight="90"', "nodeGap": 'nodeGap="40"',
             "connectorStyle": 'connectorStyle.color="$negative" connectorStyle.width="3"',
             "direction=vertical": 'direction="vertical"'},
    "FlowNode": {"shape": 'shape="flowChartDecision"', "width": 'width="200"', "height": 'height="100"'},
    "FlowConnection": {"label": 'label="Yes"', "labelColor": 'label="Yes" labelColor="$negative"'},
    "Pyramid": {"direction=down": 'direction="down"'},
    "PyramidLevel": {},
    "Tree": {"nodeShape": 'nodeShape="ellipse"', "nodeWidth": 'nodeWidth="200"', "nodeHeight": 'nodeHeight="70"',
             "levelGap": 'levelGap="100"', "siblingGap": 'siblingGap="60"',
             "connectorStyle": 'connectorStyle.color="$negative" connectorStyle.width="3"', "layout=horizontal": 'layout="horizontal"'},
    "TreeItem": {},
    "Matrix": {"axisLabelColor": 'axisLabelColor="$negative"', "quadrantLabelColor": 'quadrantLabelColor="$negative"',
               "itemLabelColor": 'itemLabelColor="$negative"'},
    "MatrixItem": {},
}
HEX = {"$accentSoft": "E3EBFC", "$accent": "2563EB", "$negative": "DC2626", "$warningSoft": "F5E9DF", "$border": "CAD5E4"}


def probes() -> list[dict]:
    """[{id, node, tag, place, attr, value, hex, xml}] incl. one baseline per node (attr = '')."""
    out = []
    for node, base in BASE.items():
        for place, tag in (("group", node), ("item", ITEM[node]), ("sub", SUB.get(node))):
            if not tag:
                continue
            groups = {**BOX, **TEXT, **OWN.get(tag, {})}
            if place == "sub" and node == "Flow":
                groups = {**{"color": 'color="$negative"'}, **OWN["FlowConnection"], "fontSize": 'fontSize="26"'}
            for name, attr in [("", "")] + list(groups.items()) if place == "group" else list(groups.items()):
                for hexed in (False, True):
                    a = attr
                    if hexed:
                        a2 = re.sub(r"\$\w+", lambda m: HEX.get(m.group(0), m.group(0)), a)
                        if a2 == a:
                            continue
                        a = a2
                    xml = put(base, {"group": "G", "item": "I", "sub": "S"}[place], a)
                    pid = f"{node}|{tag}|{name or 'BASELINE'}|{'hex' if hexed else 'token'}"
                    out.append({"id": pid, "node": node, "tag": tag, "place": place, "attr": name, "value": a,
                                "hex": hexed, "body": xml})
    return out


def put(base: str, slot: str, attr: str) -> str:
    """Write attr into the tag holding {slot}; an attribute of the same name already on that tag is replaced."""
    names = re.findall(r'([\w.]+)=', attr)
    def tag(m: re.Match) -> str:
        t = m.group(0)
        for n in names:
            t = re.sub(rf'\s{re.escape(n)}="[^"]*"', "", t)
        return t.replace("{" + slot + "}", f" {attr}" if attr else "")
    xml = re.sub(r"<[A-Za-z]+[^<>]*\{" + slot + r"\}", tag, base)
    return re.sub(r"\{[GIS]\}", "", xml)


def deck(body: str, theme: str) -> str:
    slide = (f'<Slide><VStack w="1280" h="720" padding="48" alignItems="start" backgroundColor="$surface">{body}'
             f'</VStack></Slide>')
    return ensure_single_theme(slide, theme)


def main() -> int:
    theme = resolve_theme("corporate-slate")["element"]
    WORK.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    ps = probes()
    for p in ps:
        p["xml"] = deck(p["body"], theme)
    # a second baseline per node: the pptx must be deterministic for "identical" to mean "ignored"
    ps += [{**p, "id": p["id"] + "|again"} for p in ps if p["attr"] == ""]
    (WORK / "probes.json").write_text(json.dumps([{"id": p["id"], "xml": p["xml"]} for p in ps], ensure_ascii=False),
                                      encoding="utf-8")
    subprocess.run(["node", str(ROOT / "scripts" / "native_style_probe.mjs"), str(WORK / "probes.json"),
                    str(WORK / "results.json")], check=True, timeout=1800)
    res = {r["id"]: r for r in json.loads((WORK / "results.json").read_text(encoding="utf-8"))}
    base = {p["node"]: res[p["id"]] for p in ps if p["attr"] == "" and not p["id"].endswith("again")}
    for p in ps:
        if p["id"].endswith("again"):
            assert res[p["id"]].get("sha") == base[p["node"]].get("sha"), f"{p['node']}: pptx not deterministic"
    norm_base = {p["node"]: normalize_xml(p["body"]) for p in ps if p["attr"] == ""}
    rows = []
    for p in ps:
        if p["attr"] == "" or p["id"].endswith("again"):
            continue
        r = res[p["id"]]
        if r["stage"] != "ok":
            pom = "rejected"
        else:
            ref = base[p["node"]]
            if p["attr"] in REF:
                ref = res[p["id"].replace(p["attr"], REF[p["attr"]])]
            pom = "applied" if ref.get("sha") and r["sha"] != ref["sha"] else ("ignored" if ref.get("sha") else "n/a (fill rejected)")
        n, nb = normalize_xml(p["body"]), norm_base[p["node"]]
        first, cleaned = p["value"].split("=", 1)[0], n["cleaned_xml"]
        if all(v in cleaned for v in re.findall(r"""[\w.]+=(?:"[^"]*"|'[^']*')""", p["value"])):
            kept = "kept"
        elif cleaned.count(f"{first}=") > nb["cleaned_xml"].count(f"{first}="):
            kept = "rewritten"
        else:
            kept = "dropped"
        codes = sorted({i["code"] for i in n.get("issues", [])} - {i["code"] for i in nb.get("issues", [])})
        rows.append({"node": p["node"], "tag": p["tag"], "place": p["place"], "attr": p["attr"], "value": p["value"],
                     "hex": p["hex"], "pom": pom, "error": r.get("error", "")[:240],
                     "diagnostics": r.get("diagnostics", []), "normalizer": kept,
                     "normalizer_codes": codes})
    (DOCS / "r2-attributes.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    write_md(rows)
    print(DOCS / "r2-attributes.md")
    return 0


def write_md(rows: list[dict]) -> None:
    """One table per tag: attribute -> POM (token / hex retry) and the normalizer."""
    by: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by.setdefault((r["node"], r["tag"]), []).append(r)
    lines = ["# R2: style attributes on the native nodes (POM 10.3.0, free probe)", "",
             "Generated by `python -m scripts.native_style_probe`. One probe slide per attribute on a baseline slide.",
             "**applied** = the pptx differs from the baseline; **ignored** = accepted, pptx identical; **rejected** = "
             "POM throws. *(hex)* = the `$token` was rejected and the hex value was then applied. "
             "Normalizer = `normalize_xml` keeps or drops the attribute before POM.", ""]
    for (node, tag), rs in by.items():
        lines += [f"## {node} · `<{tag}>`", "", "| attribute | POM | normalizer | note |", "|---|---|---|---|"]
        tok = {r["attr"]: r for r in rs if not r["hex"]}
        hx = {r["attr"]: r for r in rs if r["hex"]}
        for name, r in tok.items():
            pom = r["pom"]
            if pom == "rejected" and name in hx and hx[name]["pom"] != "rejected":
                pom = f"{hx[name]['pom']} *(hex only)*"
            note = r["error"].split(" | ")[0][:110] if r["pom"] == "rejected" else "; ".join(r["diagnostics"])[:110]
            nz = r["normalizer"] + (f" ({', '.join(r['normalizer_codes'])})" if r["normalizer_codes"] else "")
            lines.append(f"| `{r['value'][:60]}` | {pom} | {nz} | {note.replace('|', '/')} |")
        lines.append("")
    (DOCS / "r2-attributes.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
