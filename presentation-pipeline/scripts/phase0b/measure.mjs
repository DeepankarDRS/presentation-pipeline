// measure.mjs — POM's own layout for Phase 0b slides (derived-nodes-design §13 R3).
//
// A long-running helper: reads one JSON request per stdin line, writes one JSON
// line back.
//   {"xml": "<Theme/><Slide>…</Slide>"}  ->
//   {"slides": [{"content": px (natural height), "overfull": px, "squashed": [{id, type, deficit, text}],
//                "slots": {id: {w, h}}, "blocks": {id: {h, natural}}}]}
// "squashed" = a text / list / stack whose content needs more height than its box
// (Yoga shrank it, so text is drawn over its neighbours); "overfull" = content
// height past the 720 px slide. Elements with an id starting "slot-" report their
// box (two-pass expansion); "blk-" ids report box height and natural height.

import { createInterface } from "node:readline";
import { pathToFileURL, fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const fg = await import(pathToFileURL(path.join(here, "..", "..", "src", "node", "fit-grow.js")).href);
const { layout, natural, squeezes, contentHeight, tagNodes, walk, SLIDE } = fg;

const SQUASH_PX = 3;

async function measure(xml) {
  const L = await layout(tagNodes(xml));
  try {
    const sq = squeezes(L);
    return L.slides.map((root) => {
      const out = { content: 0, overfull: 0, squashed: [], slots: {}, blocks: {} };
      // Yoga squeezes the slide into 720 px, so the root's natural height is the real need
      out.content = Math.round(Math.max(contentHeight(root, L), natural(root, L)));
      out.overfull = Math.max(0, out.content - SLIDE.h);
      walk(root, (n) => {
        if (!n.id) return;
        const b = L.box(n);
        if (n.id.startsWith("slot-")) out.slots[n.id] = { w: Math.round(b.w), h: Math.round(b.h) };
        if (n.id.startsWith("blk-")) out.blocks[n.id] = { h: Math.round(b.h), natural: Math.round(natural(n, L)) };
        const d = sq.get(n.id);
        if (d !== undefined && d > SQUASH_PX) {
          const text = n.text ?? (n.runs ?? []).map((r) => r.text).join("") ?? "";
          out.squashed.push({ id: n.id, type: n.type, deficit: Math.round(d), text: String(text).slice(0, 40) });
        }
      });
      return out;
    });
  } finally { L.free(); }
}

const rl = createInterface({ input: process.stdin });
for await (const line of rl) {
  if (!line.trim()) continue;
  let reply;
  try {
    reply = { slides: await measure(JSON.parse(line).xml) };
  } catch (error) {
    reply = { error: String(error && error.message ? error.message : error) };
  }
  process.stdout.write(JSON.stringify(reply) + "\n");
}
