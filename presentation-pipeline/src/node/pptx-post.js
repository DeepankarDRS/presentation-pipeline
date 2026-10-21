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

import JSZip from "jszip";
import { DECK_FONT, POM_FAMILY } from "./fonts.js";

const SLIDE_RE = /^ppt\/slides\/slide\d+\.xml$/;
const POM_TYPEFACE = new RegExp(`(<a:(?:latin|ea|cs)\\b[^>]*?\\stypeface=")${POM_FAMILY}"`, "g");

/** Name the deck font in every run of one slide's XML that POM wrote in its default family. */
export function deckTypeface(slideXml, family = DECK_FONT) {
  return family ? slideXml.replace(POM_TYPEFACE, `$1${family}"`) : slideXml;
}

/** Anchor every table cell of one slide's XML in the middle. */
export function centreCells(slideXml) {
  return slideXml.replace(/<a:tc\b[\s\S]*?<\/a:tc>/g, (tc) => tc
    // the cell's own text body (PowerPoint reads tcPr, LibreOffice may read bodyPr)
    .replace(/<a:bodyPr\b([^>]*?)\sanchor="t"/, '<a:bodyPr$1 anchor="ctr"')
    .replace(/<a:tcPr\b(?![^>]*\sanchor=)/, '<a:tcPr anchor="ctr"'));
}

/** Post-process a built .pptx (Buffer in, Buffer out). */
export async function postProcessPptx(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  for (const name of Object.keys(zip.files).filter((n) => SLIDE_RE.test(n))) {
    const xml = await zip.file(name).async("string");
    const out = deckTypeface(centreCells(xml));
    if (out !== xml) zip.file(name, out);
  }
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}
