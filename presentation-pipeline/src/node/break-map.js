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

// runs: a drawn text box as its paragraphs of runs, measured run by run (Table / KPI / card break map,
// 2026-10-21): a word is every non-space character between two spaces, across runs, each run at its own
// size ("₹114.9" at 95 px + "L" at 58 px is one word); lines wrap greedily at `width`, a paragraph's line
// is its lnSpc (px) or 1.2 x its largest run, plus spcBef / spcAft.
//   texts.json: [{paras: [{runs: [{text, family, px, bold, spc}], lnSpc, before, after}], width}]
async function measureRuns(texts) {
  const [{ measureText }, { createBuildContext }] = await Promise.all([
    internal("calcYogaLayout/measureText.js"), internal("buildContext.js")]);
  const ctx = createBuildContext("auto", loadFonts());
  const cache = new Map();
  const nat = (t, r) => {
    const key = `${t}\u0000${r.family}\u0000${r.px}\u0000${r.bold}\u0000${r.spc ?? 0}`;
    if (!cache.has(key)) {
      const opts = { fontFamily: r.family || "Noto Sans JP", fontSizePx: r.px, lineHeight: LINE_HEIGHT,
        fontWeight: r.bold ? "bold" : "normal", letterSpacingPx: r.spc ?? 0 };
      // without POM's 10 px box padding (fit-grow naturalWidth)
      cache.set(key, Math.max(0, measureText(t, Infinity, opts, ctx.textMeasurementMode, ctx.fontRegistry).widthPx - 10));
    }
    return cache.get(key);
  };
  const space = (r) => nat("a a", r) - nat("aa", r);
  return texts.map(({ paras, width }) => {
    let word = "", wordW = 0, lineW = 0, height = 0, lines = 0, exact = true;
    for (const p of paras) {
      // tokens: words (pieces across runs, split after a hyphen) and the spaces between them
      const toks = [];
      let cur = null;
      const flush = () => { if (cur) toks.push(cur); cur = null; };
      for (const r of p.runs) {
        exact &&= ctx.fontRegistry.hasFont(r.family || "Noto Sans JP", r.bold ? "bold" : "normal");
        for (const part of String(r.text ?? "").split(/(\s+)/)) {
          if (!part) continue;
          if (/^\s+$/.test(part)) { flush(); toks.push({ space: space(r) * part.length }); continue; }
          part.split(/(?<=[-–—])/).forEach((piece, j) => {
            if (j > 0) { flush(); }
            cur = cur ?? { text: "", w: 0 };
            cur.text += piece;
            cur.w += nat(piece, r);
          });
        }
      }
      flush();
      const maxPx = Math.max(...p.runs.map((r) => r.px), 1);
      const lh = p.lnSpc || maxPx * LINE_HEIGHT;
      let n = 1, x = 0, pending = 0;
      for (const t of toks) {
        if (t.space !== undefined) { pending += t.space; continue; }
        if (t.w > wordW) { word = t.text; wordW = t.w; }
        if (x > 0 && x + pending + t.w > width) { n += 1; lineW = Math.max(lineW, x); x = t.w; }
        else x += (x > 0 ? pending : 0) + t.w;
        if (t.w > width) {  // the renderer breaks it: its letters run on over more lines
          n += Math.ceil(t.w / width) - 1;
          x = t.w % width;
        }
        pending = 0;
      }
      lineW = Math.max(lineW, Math.min(x, width));
      lines += n;
      height += n * lh + (p.before ?? 0) + (p.after ?? 0);
    }
    return { word, wordW, lineW, height, lines, exact };
  });
}

const [mode, inPath, out] = process.argv.slice(2);
const input = JSON.parse(readFileSync(inPath, "utf8"));
if (mode === "build") {
  writeFileSync(path.join(out, "build-results.json"), JSON.stringify(await build(input, out)), "utf8");
} else if (mode === "measure") {
  writeFileSync(out, JSON.stringify(await measure(input)), "utf8");
} else if (mode === "runs") {
  writeFileSync(out, JSON.stringify(await measureRuns(input)), "utf8");
} else {
  throw new Error(`unknown mode ${mode}`);
}
