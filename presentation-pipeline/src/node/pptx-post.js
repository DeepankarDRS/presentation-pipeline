// pptx-post.js — deterministic edits to the .pptx POM writes, after buildPptx.
//
// Table cells are vertically centred: POM's <Td> has no valign and writes every
// cell top-anchored, so a row taller than its text (fit-grow grows the main
// table's rows into spare height) shows its text glued to the top edge. Only
// cells without an explicit anchor change; running it twice changes nothing.
//
// Text POM writes in its default "Noto Sans JP" (diagram text: Flow, Tree and Matrix take no
// fontFamily) is set in the deck font (fonts.js DECK_FONT), the font the rest of the deck names and
// font_embed embeds; POM_DECK_FONT=none leaves it.
//
// Charts code drew (src/compiler/nodes/charts.py) carry a `<!-- chart-post {...} -->` comment before their
// <Chart>: POM's Chart has no data labels and no bar direction, so they are written here (chartPost):
// `labels` = each value as a data label in the plan's number format `fmt` and the ink `ink` (a $token of
// the slide's <Theme>), with no value axis; `barDir: "bar"` turns the bars, categories top-down.
//
// Lists the bullet node drew (src/compiler/nodes/bullets.py) carry `<!-- list-post {...} -->` comments: POM's <Ul> has
// no marker colour and no paragraph spacing, so they are written here (listPost), found by their first words; the text
// stays a real list. Numbered lists lose POM's startAt="1" on every paragraph (LibreOffice restarts at each: 1. 1. 1.;
// 1 is the default, so nothing else changes).

import JSZip from "jszip";
import { DECK_FONT, POM_FAMILY } from "./fonts.js";
import { cellMargin } from "./cell-margin.js";

const SLIDE_RE = /^ppt\/slides\/slide\d+\.xml$/;
const CHART_RE = /^ppt\/charts\/chart(\d+)\.xml$/;
const MARK_OR_CHART = /<!--\s*chart-post\s+(\{.*?\})\s*-->|<Chart\b/gs;
const POM_TYPEFACE = new RegExp(`(<a:(?:latin|ea|cs)\\b[^>]*?\\stypeface=")${POM_FAMILY}"`, "g");

/** Name the deck font in every run of one slide's XML that POM wrote in its default family. */
export function deckTypeface(slideXml, family = DECK_FONT) {
  return family ? slideXml.replace(POM_TYPEFACE, `$1${family}"`) : slideXml;
}

/** Anchor every table cell of one slide's XML in the middle, and give it the table's cell margins (cell-margin.js;
 * `marginOf(tableW, cols)` -> px, from the table's grid columns). */
export function centreCells(slideXml, marginOf = cellMargin) {
  return slideXml.replace(/<a:tbl>[\s\S]*?<\/a:tbl>/g, (tbl) => {
    const grid = [...tbl.matchAll(/<a:gridCol\b[^>]*\sw="(\d+)"/g)].map((m) => Number(m[1]) / 9525);
    const px = marginOf(grid.reduce((a, b) => a + b, 0), grid.length);
    const emu = String(Math.round(px * 9525));
    return tbl.replace(/<a:tc\b[\s\S]*?<\/a:tc>/g, (tc) => {
      let out = tc
        // the cell's own text body (PowerPoint reads tcPr, LibreOffice may read bodyPr)
        .replace(/<a:bodyPr\b([^>]*?)\sanchor="t"/, '<a:bodyPr$1 anchor="ctr"')
        .replace(/<a:tcPr\b(?![^>]*\sanchor=)/, '<a:tcPr anchor="ctr"');
      if (px > 0) {
        out = out.replace(/(<a:tcPr\b[^>]*?\s)marL="0"/, `$1marL="${emu}"`).replace(/(<a:tcPr\b[^>]*?\s)marR="0"/, `$1marR="${emu}"`)
          .replace(/(<a:bodyPr\b[^>]*?\s)lIns="0"/, `$1lIns="${emu}"`).replace(/(<a:bodyPr\b[^>]*?\s)rIns="0"/, `$1rIns="${emu}"`);
      }
      return out;
    });
  });
}

/** The chart-post spec of every <Chart> of a POM slide, in document order (null: none). Colour tokens are
 * resolved from the slide's <Theme>. */
function themeToken(pomXml) {
  const theme = /<Theme\b([^>]*)>/.exec(pomXml)?.[1] ?? "";
  return (v) => {
    const m = /^\$(\w+)$/.exec(String(v ?? ""));
    if (!m) return String(v ?? "").replace(/^#/, "");
    return new RegExp(`\\s${m[1]}="#?([0-9A-Fa-f]{6})"`).exec(theme)?.[1] ?? "1E293B";
  };
}

/** Per slide, the lists to post-edit: {first, gap, marker (hex)}. fit-grow writes first + gap; bullets.py the marker
 * (a split list's columns share it: their ids start with the list's). */
export function listPostSpecs(pomXml) {
  const token = themeToken(pomXml);
  return [...pomXml.matchAll(/<Slide\b[\s\S]*?<\/Slide>/g)].map(([slide]) => {
    const specs = [...slide.matchAll(/<!--\s*list-post\s+(\{.*?\})\s*-->/g)].flatMap((m) => {
      try { return [JSON.parse(m[1])]; } catch { return []; }
    });
    const markers = specs.filter((s) => s.marker);
    return specs.filter((s) => s.first).map((s) => {
      const own = markers.find((k) => s.id.startsWith(k.id));
      return { first: s.first, gap: own?.tight ? 0 : s.gap ?? 0, tight: !!own?.tight, marker: own?.marker ? token(own.marker) : null };
    });
  });
}

const unescapeXml = (s) => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");

/** One slide's XML with its lists' marker colour and point spacing; a list it cannot find stays POM's. */
export function listPost(slideXml, specs) {
  if (!specs?.length) return slideXml;
  return slideXml.replace(/<p:sp>[\s\S]*?<\/p:sp>/g, (sp) => {
    const paras = sp.match(/<a:p>[\s\S]*?<\/a:p>/g) ?? [];
    if (!paras.length || !/<a:bu(?:Char|AutoNum)\b/.test(sp)) return sp;
    const words = unescapeXml([...paras[0].matchAll(/<a:t\b[^>]*>([^<]*)<\/a:t>/g)].map((m) => m[1]).join(""));
    const spec = specs.find((s) => words.startsWith(s.first));
    if (!spec) return sp;
    let k = 0;
    const out = sp.replace(/<a:p>[\s\S]*?<\/a:p>/g, (p) => {
      let q = p;
      if (k > 0 && spec.gap >= 1) q = q.replace("</a:lnSpc>", `</a:lnSpc><a:spcBef><a:spcPts val="${Math.round(spec.gap * 75)}"/></a:spcBef>`);
      if (spec.marker) q = q.replace(/<a:bu(?:SzPct|Font|Char|AutoNum)\b/, (m) => `<a:buClr><a:srgbClr val="${spec.marker}"/></a:buClr>${m}`);
      k += 1;
      return q;
    });
    // what spacing cannot fill stays even above and below (spacing="tight": the list sits at the top of its box)
    return spec.tight ? out : out.replace(/(<a:bodyPr\b[^>]*\sanchor=")t"/, '$1ctr"');
  });
}

export function chartPostSpecs(pomXml) {
  const token = themeToken(pomXml);
  const out = [];
  let pending = null;
  for (const m of pomXml.matchAll(MARK_OR_CHART)) {
    if (m[1]) {
      try { pending = JSON.parse(m[1]); } catch { pending = null; }
      continue;
    }
    out.push(pending && { ...pending, ink: pending.ink && token(pending.ink) });
    pending = null;
  }
  return out;
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

/** One chart part's XML with its chart-post spec applied. */
export function chartPost(chartXml, spec) {
  let s = chartXml;
  if (spec.labels) {
    const lbl = `<c:dLbls><c:numFmt formatCode="${esc(spec.fmt || "General")}" sourceLinked="0"/>`
      + "<c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr><c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr>"
      + `<a:defRPr sz="1400" b="${spec.bold === "false" ? 0 : 1}"><a:solidFill><a:srgbClr val="${spec.ink || "1E293B"}"/>`
      + "</a:solidFill></a:defRPr></a:pPr><a:endParaRPr lang=\"en-US\"/></a:p></c:txPr><c:dLblPos val=\"outEnd\"/>"
      + "<c:showLegendKey val=\"0\"/><c:showVal val=\"1\"/><c:showCatName val=\"0\"/><c:showSerName val=\"0\"/>"
      + "<c:showPercent val=\"0\"/><c:showBubbleSize val=\"0\"/></c:dLbls>";
    s = s.replace(/<c:dLbls>[\s\S]*?<\/c:dLbls>(?=\s*<c:cat>)/g, "");   // pptxgenjs's own, if any
    s = s.replace(/<c:cat>/g, `${lbl}<c:cat>`);
    s = s.replace(/(<c:valAx>[\s\S]*?<c:delete val=")0(")/, (_, a, b) => `${a}1${b}`);      // the labels replace the value axis
  }
  if (spec.barDir === "bar") {
    s = s.replace('<c:barDir val="col"/>', '<c:barDir val="bar"/>');
    s = s.replace(/(<c:catAx>[\s\S]*?<c:orientation val=")minMax(")/, "$1maxMin$2");
  }
  return s;
}

/** Post-process a built .pptx (Buffer in, Buffer out). `charts`: chartPostSpecs of the POM XML (the k-th <Chart>
 * is ppt/charts/chart<k+1>.xml: POM writes the charts in document order). */
export async function postProcessPptx(buffer, { charts = [], lists = [] } = {}) {
  const zip = await JSZip.loadAsync(buffer);
  for (const name of Object.keys(zip.files).filter((n) => SLIDE_RE.test(n))) {
    const xml = await zip.file(name).async("string");
    const k = Number(/slide(\d+)\.xml$/.exec(name)[1]) - 1;
    const out = listPost(deckTypeface(centreCells(xml)), lists[k]).replace(/(<a:buAutoNum\b[^>]*?) startAt="1"/g, "$1");
    if (out !== xml) zip.file(name, out);
  }
  if (charts.some(Boolean)) {
    const parts = Object.keys(zip.files).filter((n) => CHART_RE.test(n))
      .sort((a, b) => Number(CHART_RE.exec(a)[1]) - Number(CHART_RE.exec(b)[1]));
    for (const [k, name] of parts.entries()) {
      if (!charts[k]) continue;
      const xml = await zip.file(name).async("string");
      zip.file(name, chartPost(xml, charts[k]));
    }
  }
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}
