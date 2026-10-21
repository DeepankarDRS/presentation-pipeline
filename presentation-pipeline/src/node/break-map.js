// break-map.js — compile the node break-map grid (scripts/node_break_map.py, 2026-10-21).
//
//   node src/node/break-map.js build <cases.json> <outDir>     cases.json: [{id, xml, fit}]
//   node src/node/break-map.js measure <texts.json> <out.json>  texts.json: [{text, family, px, bold, width}]
//
// build: per case, fit-grow first when `fit` (as compile-pom.js does), then buildPptx with the fonts in
// src/node/fonts/, the post-process, and the positioned tree (geometry.js) of the XML that was built.
// Records POM's warnings (code + message), fit-grow's report and its WORD_TOO_WIDE warnings.
// measure: POM's own text measurement with the same fonts — the widest unbreakable piece of each text
// (fit-grow's `pieces`: words, split after a hyphen) and the height of its lines at the given width.
// Both modes run many cases in one node spawn; the Python side reads the drawn shapes from the pptx.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { loadFonts } from "./fonts.js";

const POM_DIST = path.join(path.dirname(fileURLToPath(import.meta.url)), "node_modules", "@hirokisakabe", "pom", "dist");
const internal = (p) => import(pathToFileURL(path.join(POM_DIST, p)).href);
const SLIDE = { w: 1280, h: 720 };
const LINE_HEIGHT = 1.2;  // the renderer's single line spacing (POM writes no lnSpc in diagram shapes)

async function build(cases, outDir) {
  const [{ buildPptx }, { geometry }, { fitGrow }, { postProcessPptx }] = await Promise.all([
    import("@hirokisakabe/pom"), import("./geometry.js"), import("./fit-grow.js"), import("./pptx-post.js")]);
  const fonts = loadFonts();
  mkdirSync(outDir, { recursive: true });
  const results = [];
  for (const { id, xml, fit } of cases) {
    const r = { id, status: "success", errors: [], warnings: [], fitGrow: [], geometry: null, pptx: null, xml };
    const t0 = Date.now();
    try {
      let built = xml;
      if (fit) {
        const f = await fitGrow(xml);
        r.fitGrow = f.report;
        r.warnings.push(...(f.warnings ?? []).map((w) => ({ code: w.code, message: w.message })));
        if (f.report.length) built = f.xml;
      }
      const { pptx, diagnostics } = await buildPptx(built, SLIDE, { fonts });
      r.warnings.push(...(diagnostics ?? []).map((d) => ({ code: d.code, message: d.message })));
      const file = path.join(outDir, `${id.replace(/[^\w.-]/g, "_")}.pptx`);
      writeFileSync(file, await postProcessPptx(await pptx.write({ outputType: "nodebuffer" })));
      r.pptx = file;
      r.xml = built;
      r.geometry = (await geometry(built)).slides[0];
    } catch (error) {
      r.status = "failure";
      r.errors = Array.isArray(error?.errors) ? error.errors : [String(error?.message ?? error)];
    }
    r.ms = Date.now() - t0;
    results.push(r);
  }
  return results;
}

async function measure(texts) {
  const [{ measureText }, { createBuildContext }] = await Promise.all([
    internal("calcYogaLayout/measureText.js"), internal("buildContext.js")]);
  const ctx = createBuildContext("auto", loadFonts());
  const pieces = (t) => String(t ?? "").split(/\s+/).flatMap((w) => w.split(/(?<=[-–—])/)).filter(Boolean);
  return texts.map(({ text, family, px, bold, width }) => {
    const opts = { fontFamily: family, fontSizePx: px, lineHeight: LINE_HEIGHT, fontWeight: bold ? "bold" : "normal" };
    let word = "", wordW = 0;
    for (const p of pieces(text)) {
      // widthPx carries POM's 10 px box padding (calculateResult); the word itself is 10 px narrower —
      // checked against a LibreOffice render: "Reconciliation" 97 px fits a 101 px box, 107 would not
      const w = measureText(p, Infinity, opts, ctx.textMeasurementMode, ctx.fontRegistry).widthPx - 10;
      if (w > wordW) { word = p; wordW = w; }
    }
    const m = measureText(text, Math.max(width, 1), opts, ctx.textMeasurementMode, ctx.fontRegistry);
    // measureText adds 10 px to the widest line (POM's own box padding): the line itself is widthPx - 10
    return { word, wordW, height: m.heightPx, lineW: m.widthPx - 10, lines: Math.round(m.heightPx / (px * LINE_HEIGHT)),
      exact: ctx.fontRegistry.hasFont(family, bold ? "bold" : "normal") };
  });
}

const [mode, inPath, out] = process.argv.slice(2);
const input = JSON.parse(readFileSync(inPath, "utf8"));
if (mode === "build") {
  writeFileSync(path.join(out, "build-results.json"), JSON.stringify(await build(input, out)), "utf8");
} else if (mode === "measure") {
  writeFileSync(out, JSON.stringify(await measure(input)), "utf8");
} else {
  throw new Error(`unknown mode ${mode}`);
}
