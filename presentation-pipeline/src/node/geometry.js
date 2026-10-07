// geometry.js — the positioned tree POM draws from, as JSON (2026-10-07, slide-quality item 2).
//
// buildPptx does, per slide: autoFitSlide (or calcYogaLayout) -> toPositioned ->
// validatePositioned -> renderPptx. This module runs the same first two steps with
// the same fonts, so every box here is the box renderPptx draws into. It does not
// know what a component draws past its box (table rows, diagram labels): the
// Python audit (src/compiler/geometry_audit.py) reads those from the .pptx.
//
//   node src/node/geometry.js <in.xml> <out.json> [--no-autofit]
//
// Internal POM modules, so pinned like fit-grow.js.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { loadFonts } from "./fonts.js";

const POM_ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)),
  "node_modules", "@hirokisakabe", "pom");
const internal = (p) => import(pathToFileURL(path.join(POM_ROOT, "dist", p)).href);

const VERIFIED_POM = "10.3.0";
const installed = JSON.parse(readFileSync(path.join(POM_ROOT, "package.json"), "utf8")).version;
if (installed !== VERIFIED_POM) {
  throw new Error(`geometry.js verified on @hirokisakabe/pom ${VERIFIED_POM}, found ${installed}`);
}

const [{ parseXml }, { calcYogaLayout }, { autoFitSlide }, { createBuildContext },
  { freeYogaTree }, { extractLayoutResults }, { toPositioned }] = await Promise.all([
  internal("parseXml/parseXml.js"),
  internal("calcYogaLayout/calcYogaLayout.js"),
  internal("autoFit/autoFit.js"),
  internal("buildContext.js"),
  internal("shared/freeYogaTree.js"),
  internal("calcYogaLayout/types.js"),
  internal("toPositioned/toPositioned.js"),
]);

const SLIDE = { w: 1280, h: 720 };
const CONTAINERS = new Set(["vstack", "hstack", "layer"]);
const r1 = (v) => Math.round(v * 10) / 10;

function hasFrame(n) {
  // a box the reader sees as a card: its own fill, gradient, border or shadow
  return Boolean(n.backgroundColor || n.backgroundGradient || n.backgroundImage
    || (n.border && (n.border.width || n.border.color))
    || n.borderLeft || n.borderTop || n.borderRight || n.borderBottom
    || (n.shadow && n.shadow.type));
}

function simplify(n) {
  const out = { type: n.type, x: r1(n.x), y: r1(n.y), w: r1(n.w), h: r1(n.h) };
  if (n.id) out.id = n.id;
  if (CONTAINERS.has(n.type)) {
    if (hasFrame(n)) out.frame = true;
    out.children = (n.children || []).map(simplify);
  }
  return out;
}

export async function geometry(xml, { autoFit = true } = {}) {
  const ctx = createBuildContext("auto", loadFonts());
  const slides = [];
  for (const node of parseXml(xml)) {
    let map;
    try {
      map = autoFit ? await autoFitSlide(node, SLIDE, ctx) : await calcYogaLayout(node, SLIDE, ctx);
      const positioned = await toPositioned(node, ctx, extractLayoutResults(map));
      slides.push(simplify(positioned));
    } finally {
      if (map) freeYogaTree(map);
    }
  }
  return { slideSize: SLIDE, slides };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [inPath, outPath] = process.argv.slice(2);
  const g = await geometry(readFileSync(inPath, "utf8"), { autoFit: !process.argv.includes("--no-autofit") });
  writeFileSync(outPath, JSON.stringify(g), "utf8");
}
