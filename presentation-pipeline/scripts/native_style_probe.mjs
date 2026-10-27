// native_style_probe.mjs: build many one-slide POM probes with one POM import (scripts/native_style_probe.py).
//
//   node scripts/native_style_probe.mjs <probes.json> <results.json>
//
// probes.json = [{id, xml}] (each a whole deck XML: Theme + one Slide). For each probe: parseXml, then buildPptx with the
// deck fonts, then the slide + chart XML of the pptx (sha1, so the harness can tell an applied attribute from an
// ignored one by comparing against its baseline). No fit-grow, no pptx post-process: this probes POM itself.
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";

const pom = await import(new URL("../src/node/node_modules/@hirokisakabe/pom/dist/index.js", import.meta.url));
const JSZip = (await import(new URL("../src/node/node_modules/jszip/lib/index.js", import.meta.url))).default;
const { loadFonts } = await import(new URL("../src/node/fonts.js", import.meta.url));
const fonts = loadFonts();
const SLIDE = { w: 1280, h: 720 };

const probes = JSON.parse(await readFile(process.argv[2], "utf8"));
const out = [];
for (const p of probes) {
  const r = { id: p.id };
  try {
    pom.parseXml(p.xml);
  } catch (e) {
    r.stage = "parse";
    r.error = Array.isArray(e.errors) ? e.errors.map(String).join(" | ") : String(e.message || e);
    out.push(r);
    continue;
  }
  try {
    const { pptx, diagnostics } = await pom.buildPptx(p.xml, SLIDE, { fonts });
    const zip = await JSZip.loadAsync(await pptx.write({ outputType: "nodebuffer" }));
    const names = Object.keys(zip.files).filter((n) => /^ppt\/(slides\/slide\d+|charts\/chart\d+)\.xml$/.test(n)).sort();
    let xml = "";
    for (const n of names) xml += await zip.file(n).async("string");
    xml = xml.replace(/ (?:name|descr)="[^"]*"/g, "");   // object names carry counters, not style
    r.stage = "ok";
    r.sha = createHash("sha1").update(xml).digest("hex");
    r.len = xml.length;
    if (Array.isArray(diagnostics) && diagnostics.length) r.diagnostics = diagnostics.map((d) => `${d.code}: ${d.message}`);
  } catch (e) {
    r.stage = "build";
    r.error = Array.isArray(e.diagnostics) ? e.diagnostics.map((d) => d.message || String(d)).join(" | ") : String(e.message || e);
  }
  out.push(r);
}
await writeFile(process.argv[3], JSON.stringify(out, null, 1), "utf8");
process.stderr.write(`probed ${out.length}\n`);
