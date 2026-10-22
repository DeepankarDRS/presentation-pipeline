// Letter-spacing probe: each word in boxes whose text room is POM's count minus d px (POM writes text
// boxes with 0 insets, so a box's room is its width; widths are whole px).
// Usage: node probe.mjs probe.xml probe-meta.json, then compile probe.xml with src/node/compile-pom.js.
import { writeFileSync } from "node:fs";
const NODE = new URL("../../../../src/node/", import.meta.url);
const dist = new URL("node_modules/@hirokisakabe/pom/dist/", NODE);
const { measureText } = await import(new URL("calcYogaLayout/measureText.js", dist).href);
const { createBuildContext } = await import(new URL("buildContext.js", dist).href);
const { loadFonts } = await import(new URL("fonts.js", NODE).href);
const ctx = createBuildContext("auto", loadFonts());
const count = (t, fs, s) => measureText(t, Infinity, { fontFamily: "Inter", fontSizePx: fs, fontWeight: "bold", letterSpacingPx: s },
  ctx.textMeasurementMode, ctx.fontRegistry).widthPx - 10;
const cases = [["share", 14, 0], ["share", 14, 1], ["SHARE", 14, 0], ["SHARE", 14, 2], ["Projected", 16, 0], ["Projected", 16, 2], ["TARGETS", 15, 0], ["TARGETS", 15, 3], ["REVENUE", 18, 0], ["REVENUE", 18, 4]];
const rows = [], meta = [];
for (const [t, fs, s] of cases) {
  const c = count(t, fs, s);
  const ws = []; for (let w = Math.ceil(c) + 1; w >= Math.floor(c - Math.max(s, 2)) - 1; w--) ws.push(w);
  const ds = ws.map((w) => +(c - w).toFixed(2));
  const cells = ws.map((w) => `<Text w="${w}" fontSize="${fs}" bold="true" letterSpacing="${s}" fontFamily="Inter" backgroundColor="FDE68A">${t}</Text>`);
  rows.push(`<HStack gap="10" alignItems="start"><Text w="170" fontSize="12" fontFamily="Inter">${t} ${fs}px sp${s} count ${c.toFixed(1)}</Text>${cells.join("")}</HStack>`);
  meta.push({ t, fs, s, count: +c.toFixed(2), d: ds });
}
writeFileSync(process.argv[2], `<Theme surface="FFFFFF" textMain="111827" />\n<Slide><VStack w="1280" h="720" padding="40" gap="14" backgroundColor="FFFFFF">
<Text fontSize="14" fontFamily="Inter">Columns: room = POM count minus d (d = count - box, per row in probe-meta.json)</Text>${rows.join("\n")}</VStack></Slide>`);
writeFileSync(process.argv[3], JSON.stringify(meta, null, 1));
console.log(JSON.stringify(meta));
