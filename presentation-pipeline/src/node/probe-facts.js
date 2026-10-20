// probe-facts.js — compile the probes of knowledge/core/node-facts.yaml (2026-10-16).
//
// Each probe is one tiny slide. For each it records what POM did: compile errors, the
// warnings buildPptx returned (SCALE_BELOW_THRESHOLD ...), the positioned tree (the box
// every node got, geometry.js) and the .pptx it wrote, so the Python side
// (src/compiler/node_facts.py) can assert on what is drawn. No fit-grow, no post-process:
// a fact here is about POM itself.
//
//   node src/node/probe-facts.js <probes.json> <outDir>     probes.json: [{id, xml}]
//   node src/node/probe-facts.js --schema <out.json>        POM's own attribute rules
//
// --schema dumps, per diagram tag and child tag, every attribute POM accepts with its
// type, its enum values and whether it is required (coercionRules.js + the zod schemas
// in types.js), so knowledge files are checked against POM instead of written by hand.
// Internal POM modules, so pinned like fit-grow.js / geometry.js.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const POM_ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)),
  "node_modules", "@hirokisakabe", "pom");
const internal = (p) => import(pathToFileURL(path.join(POM_ROOT, "dist", p)).href);

const VERIFIED_POM = "10.3.0";
const installed = JSON.parse(readFileSync(path.join(POM_ROOT, "package.json"), "utf8")).version;

// tag -> [coercion key, zod schema name, {child tag: path to its item schema}]
const DIAGRAMS = {
  Flow: ["flow", "flowNodeSchema", { FlowNode: "nodes[]", FlowConnection: "connections[]" }],
  ProcessArrow: ["processArrow", "processArrowNodeSchema", { ProcessArrowStep: "steps[]" }],
  Timeline: ["timeline", "timelineNodeSchema", { TimelineItem: "items[]" }],
  Tree: ["tree", "treeNodeSchema", { TreeItem: "data" }],
  Matrix: ["matrix", "matrixNodeSchema", { MatrixAxes: "axes", MatrixQuadrants: "quadrants", MatrixItem: "items[]" }],
  Pyramid: ["pyramid", "pyramidNodeSchema", { PyramidLevel: "levels[]" }],
};

function unwrap(s) {
  let optional = false;
  for (;;) {
    const t = s.def.type;
    if (t === "optional" || t === "nullable" || t === "default") { optional = true; s = s.def.innerType; continue; }
    if (t === "lazy") { s = s.def.getter(); continue; }
    return { s, optional };
  }
}

function describe(zodField) {
  const { s, optional } = unwrap(zodField);
  const t = s.def.type;
  const out = { type: t === "enum" ? "enum" : t, required: !optional };
  if (t === "enum") out.values = s.options;
  return out;
}

function itemSchema(nodeSchema, pathSpec) {
  const key = pathSpec.replace("[]", "");
  let s = unwrap(nodeSchema.shape[key]).s;
  if (pathSpec.endsWith("[]")) s = unwrap(s.element).s;
  return s;
}

async function schema() {
  const [{ NODE_COERCION_MAP, CHILD_ELEMENT_COERCION_MAP }, types] = await Promise.all([
    internal("parseXml/coercionRules.js"), internal("types.js")]);
  const base = new Set(Object.keys(NODE_COERCION_MAP.layer));  // BASE_RULES: box attributes every node has
  const out = { pomVersion: installed, base: [...base], nodes: {} };
  for (const [tag, [key, schemaName, children]] of Object.entries(DIAGRAMS)) {
    const zod = types[schemaName];
    const dataKeys = new Set(Object.values(children).map((spec) => spec.replace("[]", "")));
    const attrs = {};
    for (const name of Object.keys(NODE_COERCION_MAP[key])) {
      // structured data (nodes, items ...) is written as child elements
      if (base.has(name) || dataKeys.has(name) || !(name in zod.shape)) continue;
      attrs[name] = describe(zod.shape[name]);
      const rule = NODE_COERCION_MAP[key][name];
      if (typeof rule === "object" && rule.type === "object") attrs[name].keys = Object.keys(rule.shape);
    }
    const kids = {};
    for (const [child, spec] of Object.entries(children)) {
      const item = itemSchema(zod, spec);
      const xmlAttrs = CHILD_ELEMENT_COERCION_MAP[child]
        ? Object.keys(CHILD_ELEMENT_COERCION_MAP[child])
        : Object.keys(item.shape).filter((k) => k !== "children");  // TreeItem: read by convertTreeItem
      kids[child] = Object.fromEntries(xmlAttrs.filter((k) => k in item.shape).map((k) => [k, describe(item.shape[k])]));
    }
    out.nodes[tag] = { attributes: attrs, children: kids };
  }
  return out;
}

async function probe(probes, outDir) {
  const [{ buildPptx }, { geometry }, { loadFonts }] = await Promise.all([
    import("@hirokisakabe/pom"), import("./geometry.js"), import("./fonts.js")]);
  const fonts = loadFonts();
  mkdirSync(outDir, { recursive: true });
  const results = [];
  for (const { id, xml } of probes) {
    const r = { id, status: "success", errors: [], warnings: [], geometry: null, pptx: null };
    try {
      const { pptx, diagnostics } = await buildPptx(xml, { w: 1280, h: 720 }, { fonts });
      r.warnings = (diagnostics ?? []).map((d) => d.code);
      const file = path.join(outDir, `${id.replace(/[^\w.-]/g, "_")}.pptx`);
      writeFileSync(file, await pptx.write({ outputType: "nodebuffer" }));
      r.pptx = file;
      r.geometry = (await geometry(xml)).slides[0];
    } catch (error) {
      r.status = "failure";
      r.errors = Array.isArray(error?.errors) ? error.errors : [String(error?.message ?? error)];
    }
    results.push(r);
  }
  return { pomVersion: installed, verifiedOn: VERIFIED_POM, results };
}

if (process.argv[2] === "--schema") {
  writeFileSync(process.argv[3], JSON.stringify(await schema(), null, 1), "utf8");
} else {
  const [inPath, outDir] = process.argv.slice(2);
  const res = await probe(JSON.parse(readFileSync(inPath, "utf8")), outDir);
  writeFileSync(path.join(outDir, "probe-results.json"), JSON.stringify(res), "utf8");
}
