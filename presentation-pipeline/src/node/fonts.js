// fonts.js — font files POM measures text with (buildPptx options.fonts / createBuildContext).
//
// Without them POM measures "Noto Sans JP" (or no fontFamily) with its bundled Noto
// metrics and any other family with a 0.5em-per-character estimate, while the slide
// renders in the real font (derived-nodes-design §10g). Every .ttf / .otf in
// src/node/fonts/ is loaded; the family name comes from the file itself.
//
// Italic files are skipped: POM keys faces by family + normal/bold only, so an
// italic face would replace the upright one (they stay in the folder for installing).
// GSUB is hidden from POM's opentype.js 2.0.0: it throws on lookups Inter 4 and
// JetBrains Mono use (lookupType 6 format 2). Substitutions (ligatures, alternates)
// don't change advance widths or kerning (GPOS), so measurement barely moves.
// POM_FONTS=0 disables loading (the pre-fonts behaviour). No folder / no files → [].

import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import opentypeModule from "opentype.js";

const opentype = opentypeModule.default ?? opentypeModule;
const FONT_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "fonts");

let cached;

// Rename the GSUB entry in the table directory (in memory) so opentype.js skips it.
function hideGsub(buf) {
  const out = Buffer.from(buf);
  const numTables = out.readUInt16BE(4);
  for (let i = 0; i < numTables; i++) {
    const at = 12 + 16 * i;
    if (out.toString("latin1", at, at + 4) === "GSUB") out.write("xSUB", at, "latin1");
  }
  return out;
}

// A font opentype.js cannot measure would fail every buildPptx: skip it instead.
function measurable(data, file) {
  try {
    const ab = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
    opentype.parse(ab).getAdvanceWidth("Ag 0.9% ₹ →", 20, { kerning: true });
    return true;
  } catch (error) {
    console.warn(`fonts.js: skipped ${file} (${error && error.message ? error.message : error})`);
    return false;
  }
}

export function loadFonts() {
  if (process.env.POM_FONTS === "0") return [];
  if (cached) return cached;
  let files = [];
  try {
    files = readdirSync(FONT_DIR);
  } catch {
    files = [];
  }
  cached = files
    .filter((f) => /\.(ttf|otf)$/i.test(f) && !/italic/i.test(f))
    .sort()
    .map((f) => ({ file: f, data: hideGsub(readFileSync(path.join(FONT_DIR, f))) }))
    .filter(({ file, data }) => measurable(data, file))
    .map(({ data }) => ({ data }));
  return cached;
}
