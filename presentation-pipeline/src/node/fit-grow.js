// fit-grow.js — grow content to fill spare space inside stacks, before buildPptx.
//
// POM's own autoFit only SHRINKS (fonts, gaps, scale) when a slide overflows,
// and every diagram node (Flow/Tree/ProcessArrow/...) only scales DOWN to fit
// its box. Nothing ever grows. So a card whose box is taller than its content
// renders half empty. This pass is the missing other direction:
//
//   0. explicit h   — a band with h="150" w="max" stretched far past 150 is kept
//                     at 150 when a flexible sibling can take the space (POM's
//                     w="max" in a VStack otherwise stretches its height).
//   1. split lists  — a Ul/Ol of 4+ short items using < 45% of its width is
//                     split into two side-by-side lists (an Ol's second column
//                     continues the numbering; lists with their own id or box
//                     styling are never split).
//   2. tables       — a Table h taller than its rows: rows grow a little with
//                     their text; the box is clamped to the rows (cells cannot
//                     vertically centre, extra box = dead). Cell text grows only
//                     if every cell still fits its row.
//                     A Table without h (sized by its rows): column widths that
//                     wrap the fewest lines, rows as tall as their text, a
//                     squeezed box protected (or reported), and the slide's main
//                     table grows its text + rows into empty space.
//   3. diagrams     — a Chart/Flow/Tree/ProcessArrow absorbs the spare height of
//                     its card, then Flow/Tree/ProcessArrow nodes are enlarged
//                     to fill their box.
//   4. text         — in each stack under ~70% full, fonts grow together (body
//                     by s, headings/labels by sqrt(s); titles and each box's
//                     stat/hero number untouched) until ~88% full; past the size
//                     caps the rest goes into line height and gaps. Peer cards
//                     in a row scale as one group; headings never gain a line;
//                     text with an inline <Span fontSize> keeps its size.
//
// It edits the ORIGINAL XML text (only size attributes change), and measures
// with POM's own layout engine so its numbers match what buildPptx will do.
// That engine is internal to POM (not exported), hence the exact version pin
// in package.json. Any failure returns the input XML unchanged.

import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const POM_ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)),
  "node_modules", "@hirokisakabe", "pom");
const POM_DIST = path.join(POM_ROOT, "dist");
const internal = (p) => import(pathToFileURL(path.join(POM_DIST, p)).href);

// The internals below were verified against exactly this version. On any other
// install (stale node_modules, an upgrade) refuse to load: compile-pom.js then
// skips the pass and compiles the original XML.
const VERIFIED_POM = "10.3.0";
const installed = JSON.parse(readFileSync(path.join(POM_ROOT, "package.json"), "utf8")).version;
if (installed !== VERIFIED_POM) {
  throw new Error(`fit-grow verified on @hirokisakabe/pom ${VERIFIED_POM}, found ${installed}`);
}

const [{ parseXml }, { calcYogaLayout }, { createBuildContext }, { freeYogaTree },
  { measureText }, { measureFontLineHeightRatio }, { getNodeMetadataByTag },
  { measureTree }, { ARROW_DEPTH_RATIO }, { resolveColumnWidths, resolveRowHeights }] = await Promise.all([
  internal("parseXml/parseXml.js"),
  internal("calcYogaLayout/calcYogaLayout.js"),
  internal("buildContext.js"),
  internal("shared/freeYogaTree.js"),
  internal("calcYogaLayout/measureText.js"),
  internal("calcYogaLayout/fontLoader.js"),
  internal("registry/nodeMetadata.js"),
  internal("calcYogaLayout/measureCompositeNodes.js"),
  internal("shared/processArrowConstants.js"),
  internal("shared/tableUtils.js"),
]);

const SLIDE = { w: 1280, h: 720 };
const LOW_FILL = 0.7;       // a stack below this is "sparse" (POM measure runs ~15% wide)
const TARGET_FILL = 0.88;   // grow until this full (slack for renderer wrap drift)
const MIN_SLACK = 30;       // px — ignore smaller gaps
const MAX_SCALE = 2.0;
const FIXED_FONT = 24;      // >= this is a title / KPI number: never grown
const BODY_CAP = 22;
const HEADING_CAP = 24;
const STACKS = new Set(["vstack", "hstack"]);
const RIGID = new Set(["chart", "table", "matrix", "processArrow", "flow", "pyramid",
  "tree", "timeline", "image", "svg", "layer"]);
const ID_PREFIX = "__fg";

// --- XML text editing --------------------------------------------------------
// Only attribute values are ever changed, so the original XML (Theme, tokens,
// formatting) survives exactly. Elements are addressed by an injected id.

const TAG_RE = /<(\/?)([A-Za-z][\w.]*)((?:\s+[\w.:-]+\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)>/g;

function tagNodes(xml) {
  let n = 0;
  return xml.replace(TAG_RE, (m, close, name, attrs, self) => {
    if (close || !getNodeMetadataByTag(name) || /\sid\s*=/.test(attrs)) return m;
    return `<${name} id="${ID_PREFIX}${n++}"${attrs}${self ? " /" : ""}>`;
  });
}

const untag = (xml) => xml.replace(new RegExp(` id="${ID_PREFIX}\\d+[ab]*"`, "g"), "");

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Locate the element with this id: [start, openEnd, end) offsets. */
function findElement(xml, id) {
  // generator ids may hold regex characters ("kpi(1)", "kpi.1") or single quotes
  const idRe = new RegExp(`\\sid\\s*=\\s*("${escapeRe(id)}"|'${escapeRe(id)}')`);
  TAG_RE.lastIndex = 0;
  let m;
  while ((m = TAG_RE.exec(xml))) {
    if (m[1] || !idRe.test(m[3])) continue;
    const start = m.index, openEnd = TAG_RE.lastIndex;
    if (m[4]) return { start, openEnd, end: openEnd, name: m[2] };
    let depth = 1, t;
    while ((t = TAG_RE.exec(xml))) {
      if (t[2] !== m[2] || t[4]) continue;
      depth += t[1] ? -1 : 1;
      if (depth === 0) return { start, openEnd, end: TAG_RE.lastIndex, name: m[2] };
    }
  }
  return null;
}

function setAttrs(xml, id, attrs) {
  const el = findElement(xml, id);
  if (!el) return xml;
  let open = xml.slice(el.start, el.openEnd);
  for (const [k, v] of Object.entries(attrs)) {
    const re = new RegExp(`(\\s${k.replace(".", "\\.")}\\s*=\\s*)("[^"]*"|'[^']*')`);
    open = re.test(open) ? open.replace(re, `$1"${v}"`)
      : open.replace(new RegExp(`^<${el.name}`), `<${el.name} ${k}="${v}"`);
  }
  return xml.slice(0, el.start) + open + xml.slice(el.openEnd);
}

// --- layout + measurement (POM's own engine) -----------------------------------

async function layout(xml) {
  const ctx = createBuildContext("auto");
  const slides = parseXml(xml);
  const maps = [];
  const byId = new Map();
  for (const root of slides) {
    maps.push(await calcYogaLayout(root, SLIDE, ctx));
    walk(root, (n) => n.id && byId.set(n.id, n));
  }
  const yogaOf = (n) => { for (const m of maps) if (m.has(n)) return m.get(n); };
  const box = (n) => {
    const y = yogaOf(n);
    return { w: y.getComputedWidth(), h: y.getComputedHeight(), top: y.getComputedTop(),
      pl: y.getComputedPadding(0), pt: y.getComputedPadding(1),
      pr: y.getComputedPadding(2), pb: y.getComputedPadding(3) };
  };
  return { slides, byId, box, ctx, free: () => maps.forEach(freeYogaTree) };
}

function walk(node, fn, parent) {
  fn(node, parent);
  for (const c of node.children ?? []) walk(c, fn, node);
}

/** Natural height a node needs for its content at its current width. */
function natural(n, L) {
  const b = L.box(n);
  const innerW = Math.max(0, b.w - b.pl - b.pr);
  if (n.type === "text") {
    const fs = Math.max(n.fontSize ?? 24, ...(n.runs ?? []).map((r) => r.fontSize ?? n.fontSize ?? 24));
    const text = n.text ?? (n.runs ?? []).map((r) => r.text).join("");
    return b.pt + b.pb + measureText(text, innerW, { fontFamily: n.fontFamily ?? "Noto Sans JP",
      fontSizePx: fs, lineHeight: n.lineHeight ?? 1.3, fontWeight: n.bold ? "bold" : "normal",
      letterSpacingPx: n.letterSpacing }, L.ctx.textMeasurementMode, L.ctx.fontRegistry).heightPx;
  }
  if (n.type === "ul" || n.type === "ol") {
    const base = n.fontSize ?? 24;
    const fs = Math.max(base, ...n.items.map((i) => i.fontSize ?? base));
    const weight = n.bold ? "bold" : "normal";
    return b.pt + b.pb + measureText(n.items.map((i) => i.text).join("\n"), Math.max(0, innerW - 36),
      { fontFamily: n.fontFamily ?? "Noto Sans JP", fontSizePx: fs, fontWeight: weight,
        lineHeight: measureFontLineHeightRatio(weight) * (n.lineHeight ?? 1.3) },
      L.ctx.textMeasurementMode, L.ctx.fontRegistry).heightPx;
  }
  if (!STACKS.has(n.type)) return b.h;
  const kids = n.children ?? [];
  // rigid nodes render at their box size (a table at least its rows: POM may
  // flex-shrink its box, the pptx still writes every row); other explicit-h
  // children at their h
  const outer = kids.map((c) => (c.type === "table" ? Math.max(L.box(c).h, rowsSum(c))
    : RIGID.has(c.type) ? L.box(c).h
    : typeof c.h === "number" ? Math.min(c.h, c.maxH ?? Infinity) : natural(c, L)));
  const gap = typeof n.gap === "number" ? n.gap : 0;
  const content = n.type === "vstack"
    ? outer.reduce((s, h) => s + h, 0) + gap * Math.max(0, kids.length - 1)
    : Math.max(0, ...outer);
  return b.pt + b.pb + content;
}

/** Fraction of a stack's inner height its content uses. */
function fill(n, L) {
  const b = L.box(n);
  const inner = b.h - b.pt - b.pb;
  const content = natural(n, L) - b.pt - b.pb;
  return { inner, content, ratio: inner > 0 ? content / inner : 1 };
}

// --- phase 1: split short lists into two columns -------------------------------

const hasBoxStyle = (n) => Object.keys(n).some((k) =>
  k === "backgroundColor" || k === "backgroundGradient" || k === "padding" || k === "shadow" || k.startsWith("border"));

async function splitLists(xml, report) {
  const L = await layout(xml);
  const targets = [];
  try {
    for (const root of L.slides) walk(root, (n, parent) => {
      if ((n.type !== "ul" && n.type !== "ol") || n.items.length < 4 || !n.id) return;
      // the new row gets its width from the parent's stretch (no w="max": in a
      // VStack that is flexGrow on the HEIGHT and would balloon the row)
      if (!parent || parent.type !== "vstack" || (parent.alignItems ?? "stretch") !== "stretch") return;
      // a list with its own id (Arrow/connector target) or its own box styling
      // cannot become two lists without breaking the reference or the box
      if (!n.id.startsWith(ID_PREFIX) || hasBoxStyle(n)) return;
      const w = L.box(n).w;
      const widest = Math.max(...n.items.map((i) => measureText(i.text, Infinity,
        { fontFamily: n.fontFamily ?? "Noto Sans JP", fontSizePx: i.fontSize ?? n.fontSize ?? 24,
          fontWeight: n.bold ? "bold" : "normal", lineHeight: 1.3 },
        L.ctx.textMeasurementMode, L.ctx.fontRegistry).widthPx)) + 36;
      if (widest < 0.45 * w) targets.push(n.id);
    });
  } finally { L.free(); }

  for (const id of targets) {
    const el = findElement(xml, id);
    const open = xml.slice(el.start, el.openEnd).replace(/\s(w|h|grow)\s*=\s*("[^"]*"|'[^']*')/g, "");
    const lis = xml.slice(el.openEnd, el.end).match(/<Li\b[^>]*?(?:\/>|>[\s\S]*?<\/Li>)/g) ?? [];
    const half = Math.ceil(lis.length / 2);
    const col = (items, suffix, attrs = {}) => {
      let head = open.replace(`id="${id}"`, `id="${id}${suffix}" w="max"`);
      for (const [k, v] of Object.entries(attrs)) {
        const re = new RegExp(`\\s${k}\\s*=\\s*("[^"]*"|'[^']*')`);
        head = re.test(head) ? head.replace(re, ` ${k}="${v}"`) : head.replace(/^<(\w+)/, `<$1 ${k}="${v}"`);
      }
      return head + items.join("") + `</${el.name}>`;
    };
    // an ordered list's second column continues the numbering
    const start = Number((open.match(/\snumberStartAt\s*=\s*["']?(\d+)/) ?? [])[1] ?? 1);
    const second = el.name === "Ol" ? { numberStartAt: start + half } : {};
    const row = `<HStack gap="28" alignItems="start">${col(lis.slice(0, half), "a")}`
      + `${col(lis.slice(half), "b", second)}</HStack>`;
    xml = xml.slice(0, el.start) + row + xml.slice(el.end);
    report.push(`split ${el.name} (${lis.length} items) into 2 columns`);
  }
  return xml;
}

// --- phase 2: diagrams absorb spare card height, then fill their box -----------

const GROWABLE = new Set(["chart", "flow", "tree", "processArrow"]);

async function growDiagrams(xml, report) {
  // 2a. a lone chart/diagram in a card takes the card's unused height
  let L = await layout(xml);
  const absorb = [];
  try {
    for (const root of L.slides) walk(root, (n) => {
      if (n.type !== "vstack") return;
      const rigid = (n.children ?? []).filter((c) => RIGID.has(c.type));
      if (rigid.length !== 1 || !GROWABLE.has(rigid[0].type) || typeof rigid[0].h !== "number") return;
      const f = fill(n, L);
      const slack = f.inner - f.content;
      if (slack > MIN_SLACK) absorb.push([rigid[0].id, Math.floor(rigid[0].h + slack - 8), rigid[0].type]);
    });
  } finally { L.free(); }
  for (const [id, h, type] of absorb) {
    xml = setAttrs(xml, id, { h });
    report.push(`${type} h -> ${h} (absorbed card slack)`);
  }

  // 2b. enlarge Flow / Tree / ProcessArrow nodes to fill their box
  L = await layout(xml);
  const edits = [];
  try {
    for (const root of L.slides) walk(root, (n) => {
      if (!n.id || !["flow", "tree", "processArrow"].includes(n.type)) return;
      const b = L.box(n);
      const W = (b.w - b.pl - b.pr) * 0.97, H = (b.h - b.pt - b.pb) * 0.95;
      const e = diagramEdit(n, W, H);
      if (e) edits.push([n.id, e, n.type]);
    });
  } finally { L.free(); }
  for (const [id, e, type] of edits) {
    xml = setAttrs(xml, id, e);
    report.push(`${type} nodes -> ${JSON.stringify(e)}`);
  }
  return xml;
}

// --- phase 0: respect an explicit h --------------------------------------------
// In POM, w="max" is flexGrow:1 on the MAIN axis — inside a VStack that grows
// the HEIGHT, overriding h="150". A band the generator sized explicitly then
// balloons (a 150px KPI row renders 300px, label+number floating in it). When a
// flexible sibling exists to take that space instead, cap the band at its h.

const isFlexible = (n) => n.h === "max" || n.grow !== undefined || (n.w === "max" && typeof n.h !== "number");

async function respectHeights(xml, report) {
  const L = await layout(xml);
  const caps = [];
  try {
    for (const root of L.slides) walk(root, (p) => {
      if (p.type !== "vstack") return;
      for (const c of p.children ?? []) {
        if (!c.id || c.type === "table" || typeof c.h !== "number" || c.w !== "max" || c.maxH !== undefined) continue;
        // only real ballooning (150 -> 300), not a small share of spare height
        if (L.box(c).h <= c.h + Math.max(40, c.h * 0.25)) continue;
        if ((p.children ?? []).some((s) => s !== c && isFlexible(s))) caps.push([c.id, c.h, c.type]);
      }
    });
  } finally { L.free(); }
  for (const [id, h, type] of caps) {
    xml = setAttrs(xml, id, { maxH: h });
    report.push(`${type} kept at h=${h} (w="max" was stretching it)`);
  }
  return xml;
}

// --- tables: box = rows -------------------------------------------------------
// Table rows have fixed heights and cells have no vertical-align, so a table box
// taller than its rows is dead space. Rows grow a little (with the cell text),
// then the box is clamped to the rows so the spare height goes to its siblings.

/**
 * Does every cell still fit its row if its font grows by k? Column widths do
 * not change and rows are fixed height, so a cell that gains a line — or was
 * already wrapping — must still fit inside rowH at the larger size.
 */
function tableTextFits(n, tableW, k, rowH, ctx) {
  if (n.rows.some((r) => r.cells.some((c) => (c.rowspan ?? 1) > 1))) return false; // column positions uncertain
  const colW = resolveColumnWidths(n, tableW);
  return n.rows.every((r) => {
    let col = 0;
    return r.cells.every((c) => {
      const span = c.colspan ?? 1;
      const w = colW.slice(col, col + span).reduce((a, b) => a + b, 0) * 0.85;
      col += span;
      const f = c.fontSize ?? 14;
      const lines = (fs) => {
        const { heightPx } = measureText(c.text ?? "", w, { fontFamily: c.fontFamily ?? "Noto Sans JP",
          fontSizePx: fs, lineHeight: 1.3, fontWeight: c.bold ? "bold" : "normal" },
        ctx.textMeasurementMode, ctx.fontRegistry);
        return Math.round(heightPx / (fs * 1.3));
      };
      const f1 = Math.min(Math.round(f * k), Math.max(f, 18));
      return lines(f1) <= lines(f) && lines(f1) * f1 * 1.3 <= rowH * 0.9;
    });
  });
}

async function fitTables(xml, report) {
  const L = await layout(xml);
  const edits = [];
  try {
    for (const root of L.slides) walk(root, (n) => {
      if (n.type !== "table" || !n.id || n.rows.some((r) => r.height !== undefined)) return;
      const rows = n.rows.length;
      const rowH0 = n.defaultRowHeight ?? 32;
      const boxH = L.box(n).h;
      if (boxH <= rows * rowH0 + 8) return;
      const f0 = Math.max(14, ...n.rows.flatMap((r) => r.cells.map((c) => c.fontSize ?? 14)));
      let k = Math.min(Math.sqrt(Math.min(boxH / rows, 64) / rowH0), Math.max(1, 18 / f0));
      const rowFor = (kk) => Math.max(rowH0, Math.min(Math.floor(boxH / rows), Math.round(f0 * kk * 2.6)));
      // columns do not widen and rows are fixed height: if any cell would not
      // fit its row at the larger size, grow the rows only
      if (k > 1 && !tableTextFits(n, L.box(n).w, k, rowFor(k), L.ctx)) k = 1;
      const rowH = rowFor(k);
      edits.push([n.id, k, rowH0, rowH, rows * rowH]);
    });
  } finally { L.free(); }
  for (const [id, k, rowH0, rowH, total] of edits) {
    xml = setAttrs(xml, id, { defaultRowHeight: rowH, h: total, maxH: total });
    const el = findElement(xml, id);
    const body = xml.slice(el.openEnd, el.end).replace(/(<Td\b[^>]*?\sfontSize=")(\d+)"/g,
      (m, pre, f) => `${pre}${Math.min(Math.round(f * k), Math.max(+f, 18))}"`);
    xml = xml.slice(0, el.openEnd) + body + xml.slice(el.end);
    report.push(`table rows ${rowH0} -> ${rowH}px, cell text x${k.toFixed(2)}, box clamped to rows (${total}px)`);
  }
  return xml;
}

// --- tables sized from their text (Table without h: it sizes to its rows) -----
// POM never grows a row with its text and splits unset columns equally (F5); on
// an over-full slide it flex-shrinks the table box while the pptx still writes
// every row, so the table spills over the next band. For each such table:
//   font    — a cell without fontSize gets 14 px (house body size) instead of
//             POM's 18 px default, which is too big for a narrow table.
//   columns — of the generator's widths, "keep the set widths, content-size the
//             rest" and "content-size every column" (HTML auto layout), take the
//             one whose rows come out shortest; the generator's are replaced only
//             to save at least one text line, and never by a column narrower than
//             one of its words.
//   rows    — every row at least as tall as its wrapped text.
//   squeeze — rows tighten toward their text and minH = rows protects the box, so
//             a flexible band gives instead; if the slide still overflows, no minH
//             (POM's autoFit would shrink fonts), rows no taller than the
//             generator's (taller rows only make POM squeeze the rest of the
//             slide; the renderer grows them anyway) and the squeeze is reported.
//   spare   — the slide's main table (>= 2x any other: peer tables keep one type
//             size) grows its cell text (<= 18 px; only when it is the slide's
//             only table, so two tables never show two type sizes), then its
//             rows (<= 64 px, <= 1.5x their text), into empty slide space or dead
//             space in its own card: only the table and its ancestors change size
//             (a peer card stretched by a taller row would just gain dead space).

const TD_FONT = 18;  // POM's <Td> default fontSize
const TD_BODY = 14;  // written into cells without fontSize
const ROW_PAD = 8;   // px around a cell's lines (POM writes Td margins of 0)
const ROW_CAP = 64;
const TD_FONT_CAP = 18;

const rowsSum = (n) => resolveRowHeights(n).reduce((a, b) => a + b, 0);
// a row that holds its lines keeps its height (ROW_PAD is margin, not a line)
const rowFor = (row, need) => (need - ROW_PAD <= row ? row : need);
const sum = (a) => a.reduce((s, x) => s + x, 0);
const cellText = (c) => c.text ?? (c.runs ?? []).map((r) => r.text).join("");

/** Cells with their first column; null when a rowspan makes positions uncertain. */
function cellGrid(n) {
  if (n.rows.some((r) => r.cells.some((c) => (c.rowspan ?? 1) > 1))) return null;
  return n.rows.map((r) => {
    let col = 0;
    return r.cells.map((c) => {
      const at = { c, col, span: c.colspan ?? 1 };
      col += at.span;
      return at;
    });
  });
}

function measureCell(c, text, w, fs, ctx) {
  return measureText(text, w, { fontFamily: c.fontFamily ?? "Noto Sans JP", fontSizePx: fs,
    lineHeight: 1.3, fontWeight: c.bold ? "bold" : "normal" }, ctx.textMeasurementMode, ctx.fontRegistry);
}

/** Integer widths summing to floor(W); the rounding rest goes to the widest. */
function intWidths(ws, W) {
  const out = ws.map(Math.floor);
  const widest = out.indexOf(Math.max(...out));
  out[widest] += Math.floor(W) - sum(out);
  return out;
}

/**
 * Column widths + the row heights their text needs, at the cell fonts given by
 * fontOf. Widths are measured at 85% like tableTextFits (the renderer's font runs
 * wider than POM's). A width choice is scored by the rows it would really get,
 * never below `floor` (fewer lines inside rows that stay tall gains nothing), and
 * replaces the generator's widths only when it saves at least one text line.
 * A choice with a column narrower than one of its words is invalid (measureText
 * keeps such a word on one line; the renderer breaks it mid-word), so `valid`
 * is false only when no choice avoids that. `widths` is null when the
 * generator's widths are kept.
 */
function planTable(n, grid, W, fontOf, ctx, floor) {
  const cols = n.columns.length;
  const min = Array(cols).fill(20), pref = Array(cols).fill(20), word = Array(cols).fill(0);
  for (const row of grid) for (const { c, col, span } of row) {
    if (span !== 1) continue;
    const fs = fontOf(c), text = cellText(c);
    for (const w of text.split(/\s+/).filter(Boolean)) {
      word[col] = Math.max(word[col], measureCell(c, w, Infinity, fs, ctx).widthPx);
      min[col] = Math.max(min[col], word[col] / 0.85);
    }
    pref[col] = Math.max(pref[col], min[col], measureCell(c, text, Infinity, fs, ctx).widthPx / 0.85);
  }
  // HTML auto layout: pref widths if they fit, else min + the rest by (pref - min)
  const auto = (idx, room) => {
    const m = idx.map((i) => min[i]), p = idx.map((i) => pref[i]);
    if (sum(p) <= room) return p.map((x) => x * room / sum(p));
    if (sum(m) >= room) return m.map((x) => x * room / sum(m));
    const d = p.map((x, k) => x - m[k]);
    return m.map((x, k) => x + (room - sum(m)) * d[k] / sum(d));
  };
  const need = (widths) => grid.map((row) => Math.ceil(ROW_PAD + Math.max(0, ...row.map(({ c, col, span }) => {
    const fs = fontOf(c);
    const w = sum(widths.slice(col, col + span)) * 0.85;
    return Math.max(1, Math.round(measureCell(c, cellText(c), w, fs, ctx).heightPx / (fs * 1.3))) * fs * 1.3;
  }))));

  const candidates = [resolveColumnWidths(n, W)];
  const unset = n.columns.map((c, i) => (c.width === undefined ? i : -1)).filter((i) => i >= 0);
  const setTotal = sum(n.columns.map((c) => c.width ?? 0));
  if (unset.length && unset.length < cols && setTotal < W) {
    const w = auto(unset, W - setTotal);
    const keep = n.columns.map((c) => c.width ?? 0);
    unset.forEach((i, k) => { keep[i] = w[k]; });
    candidates.push(intWidths(keep, W));
  }
  candidates.push(intWidths(auto([...Array(cols).keys()], W), W));
  const line = Math.min(...grid.flat().map(({ c }) => fontOf(c))) * 1.3;
  let best = null;
  candidates.forEach((widths, i) => {
    const rows = need(widths);
    const cost = sum(rows.map((r, j) => rowFor(floor[j], r)));
    const valid = widths.every((w, j) => w >= word[j] - 1); // integer widths round down
    if (!best || (valid && !best.valid)
      || (valid === best.valid && cost < best.cost - (best.i === 0 ? line : 1))) best = { i, widths, rows, cost, valid };
  });
  return { widths: best.i === 0 ? null : best.widths, need: best.rows, valid: best.valid };
}

/** Rewrite a table's column widths, row heights, cell fonts and/or minH in the XML text. */
function writeTable(xml, id, { widths, rows, fontOf, minH, cellFont }) {
  if (minH !== undefined) xml = setAttrs(xml, id, { minH });
  const el = findElement(xml, id);
  let body = xml.slice(el.openEnd, el.end);
  const put = (tag, k, v) => tag.replace(new RegExp(`\\s${k}\\s*=\\s*("[^"]*"|'[^']*')`), "")
    .replace(/^<(\w+)/, `<$1 ${k}="${v}"`);
  if (widths) {
    let i = 0;
    body = /<Col\b/.test(body)
      ? body.replace(/<Col\b[^>]*?(?:\/>|>\s*<\/Col>)/g, (m) => put(m, "width", widths[i++]))
      : widths.map((w) => `<Col width="${w}" />`).join("") + body;
  }
  if (rows) {
    let i = 0;
    body = body.replace(/<Tr\b[^>]*>/g, (m) => put(m, "height", rows[i++]));
  }
  if (cellFont) body = body.replace(/<Td\b(?![^>]*\sfontSize\s*=)/g, `<Td fontSize="${cellFont}"`);
  if (fontOf) {
    body = body.replace(/<Td\b[^>]*?>/g, (m) => {
      const f = Number((m.match(/\sfontSize\s*=\s*["'](\d+(?:\.\d+)?)/) ?? [])[1] ?? TD_FONT);
      return put(m, "fontSize", fontOf({ fontSize: f }));
    });
  }
  return xml.slice(0, el.openEnd) + body + xml.slice(el.end);
}

/** Height of the slide's content as POM's autoFit measures it: furthest bottom + root padding. */
function contentHeight(root, L) {
  const bottom = (n, top) => {
    const t = top + L.box(n).top;
    let m = t + L.box(n).h;
    if (n.type !== "layer") for (const c of n.children ?? []) m = Math.max(m, bottom(c, t));
    return m;
  };
  return Math.max(0, ...(root.children ?? []).map((c) => bottom(c, 0))) + L.box(root).pb;
}

/** How far each stack's content, and each text/list, overruns its box. */
function squeezes(L) {
  const out = overflows(L);
  for (const root of L.slides) walk(root, (n) => {
    if (n.id && ["text", "ul", "ol"].includes(n.type)) out.set(n.id, natural(n, L) - L.box(n).h);
  });
  return out;
}

/**
 * The table is not squeezed, the slide stays within POM's autoFit tolerance, no
 * stack or text overruns its box more than it did (`before` = squeezes()), and
 * every `keep` ([id, h]) kept its height.
 */
async function tableFits(xml, id, before, keep = []) {
  const T = await layout(xml);
  try {
    const t = T.byId.get(id);
    if (rowsSum(t) > T.box(t).h + 1) return false;
    if (T.slides.some((r) => contentHeight(r, T) > SLIDE.h * 1.005)) return false;
    for (const [k, o] of squeezes(T)) if (o > Math.max(before.get(k) ?? 0, 0) + 1) return false;
    return keep.every(([k, h]) => Math.abs(T.box(T.byId.get(k)).h - h) <= 1);
  } finally { T.free(); }
}

/** Largest x in [lo, hi] with test(x) true (test(lo) assumed true). */
async function bisect(lo, hi, test) {
  let best = lo;
  for (let i = 0; i < 7; i++) {
    const x = (lo + hi) / 2;
    if (await test(x)) { best = x; lo = x; } else hi = x;
  }
  return best;
}

async function sizeTables(xml, report) {
  let L = await layout(xml);
  const ids = [];
  const sizes = [];
  try {
    for (const root of L.slides) walk(root, (n) => {
      if (n.type !== "table") return;
      sizes.push({ id: n.id, size: rowsSum(n) * L.box(n).w });
      if (!n.id || n.h !== undefined || !n.rows.length || !cellGrid(n)) return;
      ids.push(n.id);
    });
  } finally { L.free(); }
  sizes.sort((a, b) => b.size - a.size);
  const main = sizes.length && ids.includes(sizes[0].id)
    && (sizes.length === 1 || sizes[0].size >= 2 * sizes[1].size) ? sizes[0] : null;

  const settled = new Set(); // squeeze handled (protected or reported): no spare growth
  for (const id of ids) {
    const el = findElement(xml, id);
    if (/<Td\b(?![^>]*\sfontSize\s*=)/.test(xml.slice(el.openEnd, el.end))) {
      xml = writeTable(xml, id, { cellFont: TD_BODY });
      report.push(`table cells without fontSize -> ${TD_BODY}px (POM default ${TD_FONT})`);
    }
    // columns + rows at least as tall as their text
    L = await layout(xml);
    let declared, plan;
    try {
      const n = L.byId.get(id);
      declared = resolveRowHeights(n);
      plan = planTable(n, cellGrid(n), L.box(n).w, (c) => c.fontSize ?? TD_FONT, L.ctx, declared);
    } finally { L.free(); }
    const base = declared.map((d, i) => rowFor(d, plan.need[i]));
    const grown = sum(base) - sum(declared);
    if (plan.widths || grown > 0) {
      xml = writeTable(xml, id, { widths: plan.widths, rows: grown > 0 ? base : null });
      if (plan.widths) report.push(`table columns -> [${plan.widths.join(", ")}] (fewest wrapped lines)`);
      if (grown > 0) report.push(`table rows +${grown}px to fit their wrapped text`);
    }

    // squeezed: tighten toward the text, protect with minH if the slide then fits
    L = await layout(xml);
    let short, before, tight;
    try {
      const n = L.byId.get(id);
      short = sum(base) - L.box(n).h;
      before = squeezes(L);
      if (short > 1) tight = planTable(n, cellGrid(n), L.box(n).w, (c) => c.fontSize ?? TD_FONT, L.ctx, base.map(() => 0));
    } finally { L.free(); }
    if (short <= 1) continue;
    const loose = declared.map((d, i) => rowFor(d, tight.need[i]));
    const low = tight.need.map((r, i) => Math.min(r, loose[i])); // a kept row may hold its lines unpadded
    const rowsAt = (s) => loose.map((b, i) => Math.round(low[i] + s * (b - low[i])));
    const protect = (s) => writeTable(xml, id, { widths: tight.widths, rows: rowsAt(s), minH: sum(rowsAt(s)) });
    if (await tableFits(protect(0), id, before)) {
      const s = await bisect(0, 1, (x) => tableFits(protect(x), id, before));
      xml = protect(s);
      settled.add(id);
      report.push(`table squeezed ${Math.round(short)}px: rows ${sum(declared)} -> ${sum(rowsAt(s))}px, box protected (minH)`
        + (tight.widths ? `, columns -> [${tight.widths.join(", ")}]` : ""));
    } else {
      const rows = low.map((r, i) => Math.min(r, declared[i]));
      xml = writeTable(xml, id, { widths: tight.widths, rows });
      settled.add(id);
      report.push(`table squeezed ${Math.round(short)}px on an over-full slide: rows ${sum(declared)} -> ${sum(rows)}px`
        + ` (no taller than the generator's; the text needs ${sum(low)}px)`
        + (tight.widths ? `, columns -> [${tight.widths.join(", ")}]` : ""));
    }
  }
  if (main && !settled.has(main.id)) xml = await growMainTable(xml, main.id, report, sizes.length === 1);
  return xml;
}

/** Spare height -> the main table's cell text (<= 18 px), then its rows (capped). */
async function growMainTable(xml, id, report, onlyTable) {
  const L = await layout(xml);
  let n, W, grid, before, keep, declared;
  try {
    n = L.byId.get(id);
    W = L.box(n).w;
    grid = cellGrid(n);
    declared = resolveRowHeights(n);
    if (sum(declared) > L.box(n).h + 1) return xml; // still squeezed
    before = squeezes(L);
    const parents = new Map();
    for (const root of L.slides) walk(root, (m, parent) => parents.set(m, parent));
    const resizable = new Set();
    for (let m = n; m; m = parents.get(m)) resizable.add(m);
    keep = [];
    for (const root of L.slides) walk(root, (m) => {
      if (m.id && !resizable.has(m) && (STACKS.has(m.type) || RIGID.has(m.type))) keep.push([m.id, L.box(m).h]);
    });
  } finally { L.free(); }

  // cell text first: every cell by k, capped at max(own size, 18); proportions kept
  const cells = grid.flat().map(({ c }) => c);
  const f0 = Math.max(...cells.map((c) => c.fontSize ?? TD_FONT));
  const sized = cells.some((c) => (c.runs ?? []).some((r) => r.fontSize !== undefined));
  const fontFor = (k) => (c) => Math.min(Math.round((c.fontSize ?? TD_FONT) * k), Math.max(c.fontSize ?? TD_FONT, TD_FONT_CAP));
  const atFont = (k) => {
    const plan = planTable(n, grid, W, fontFor(k), L.ctx, declared);
    const rows = declared.map((d, i) => rowFor(d, plan.need[i]));
    return { plan, rows, xml: writeTable(xml, id, { widths: plan.widths, rows, fontOf: k > 1 ? fontFor(k) : null }) };
  };
  const kMax = sized || !onlyTable ? 1 : Math.max(1, TD_FONT_CAP / f0);
  const k = kMax > 1 ? await bisect(1, kMax, (x) => {
    const a = atFont(x);
    return a.plan.valid && tableFits(a.xml, id, before, keep);
  }) : 1;
  const grownFont = cells.some((c) => fontFor(k)(c) !== (c.fontSize ?? TD_FONT));
  const K = atFont(grownFont ? k : 1);

  // then rows, each up to min(64 px, 1.5x its text) (never below where it is)
  const cap = K.rows.map((r, i) => Math.max(r, Math.min(ROW_CAP, Math.round(1.5 * K.plan.need[i]))));
  const rowsAt = (t) => K.rows.map((r, i) => Math.round(r + t * (cap[i] - r)));
  const rowXml = (t) => writeTable(K.xml, id, { rows: rowsAt(t) });
  const t = sum(cap) > sum(K.rows) && await tableFits(rowXml(0), id, before, keep)
    ? await bisect(0, 1, (x) => tableFits(rowXml(x), id, before, keep)) : 0;
  const rows = rowsAt(t);
  if (!grownFont && sum(rows) - sum(declared) < 8) return xml;
  report.push(`main table into spare height: `
    + (grownFont ? `cell text x${k.toFixed(2)} (${f0} -> ${fontFor(k)({ fontSize: f0 })}px), ` : "")
    + `rows ${sum(declared)} -> ${sum(rows)}px`);
  return writeTable(K.xml, id, { rows });
}

function diagramEdit(n, W, H) {
  const horizontal = (n.direction ?? "horizontal") === "horizontal";
  if (n.type === "flow") {
    const count = n.nodes.length;
    if (count === 0) return null;
    const w0 = n.nodeWidth ?? 120, h0 = n.nodeHeight ?? 60;
    const gap = Math.round(Math.min(Math.max((horizontal ? W : H) * 0.035, 20), 48));
    if (horizontal) {
      const w = Math.floor((W - (count - 1) * gap) / count);
      const h = Math.floor(Math.min(H * 0.8, w * 0.85, 130));
      if (w < 80 || h <= h0 + 8) return null;
      return { nodeWidth: w, nodeHeight: Math.max(h, h0), nodeGap: gap };
    }
    const h = Math.floor(Math.min((H - (count - 1) * gap) / count, 110));
    const w = Math.floor(Math.min(W * 0.8, 320));
    if (h <= h0 + 8 && w <= w0 + 16) return null;
    return { nodeWidth: Math.max(w, w0), nodeHeight: Math.max(h, h0), nodeGap: gap };
  }
  if (n.type === "processArrow") {
    const count = n.steps.length;
    if (count === 0) return null;
    const h0 = n.itemHeight ?? 80;
    const h = Math.floor(Math.min(horizontal ? H * 0.85 : (H / count) * 1.1, 120));
    if (h <= h0 + 8) return null;
    const gap = n.gap ?? -h * ARROW_DEPTH_RATIO;
    const w = Math.floor(horizontal ? (W - (count - 1) * gap) / count : W * 0.9);
    const e = { itemHeight: h, itemWidth: w };
    if (n.fontSize) e.fontSize = Math.min(Math.round(n.fontSize * Math.sqrt(h / h0)), 20);
    return e;
  }
  // tree: uniform scale of every spacing attribute
  const intr = measureTree(n);
  const k = Math.min(W / intr.width, H / intr.height, 1.8);
  if (k < 1.1) return null;
  return { nodeWidth: Math.floor((n.nodeWidth ?? 120) * k), nodeHeight: Math.floor((n.nodeHeight ?? 40) * k),
    levelGap: Math.floor((n.levelGap ?? 60) * k), siblingGap: Math.floor((n.siblingGap ?? 20) * k) };
}

// --- phase 3: grow text inside sparse text-only stacks -------------------------

function textTargets(stack) {
  const out = [];
  let smallestFixed = Infinity;
  walk(stack, (n) => {
    if (!n.id || !["text", "ul", "ol"].includes(n.type)) return;
    const f = n.fontSize ?? 24;
    if (f >= FIXED_FONT) { smallestFixed = Math.min(smallestFixed, f); return; }
    // inline <Span fontSize> / <Li fontSize> keep their own size: growing only
    // the outer size would break the proportion, so leave these nodes alone
    const sized = (runs) => (runs ?? []).some((r) => r.fontSize !== undefined);
    if (n.type === "text" && sized(n.runs)) return;
    if (n.type !== "text" && n.items.some((i) => i.fontSize !== undefined || sized(i.runs))) return;
    const text = n.text ?? "";
    const label = /[A-Z]/.test(text) && text === text.toUpperCase();
    out.push({ id: n.id, f, heading: n.type === "text" && (n.bold || n.letterSpacing !== undefined || label) });
  });
  // a stat value / hero number (>= 1.5x the smallest text in the box) is the
  // box's anchor: frozen, like a title
  const sizes = out.map((t) => t.f);
  const anchor = Math.max(...sizes);
  if (out.length > 1 && anchor >= 1.5 * Math.min(...sizes)) {
    smallestFixed = Math.min(smallestFixed, anchor);
    for (let i = out.length - 1; i >= 0; i--) if (out[i].f === anchor) out.splice(i, 1);
  }
  // keep hierarchy: grown labels stay well below the KPI number / title they sit with
  const ceiling = Math.floor(smallestFixed * 0.62);
  for (const t of out) t.cap = Math.max(t.f, Math.min(t.heading ? HEADING_CAP : BODY_CAP, ceiling));
  return out;
}

const scaled = (t, s) => Math.min(Math.round(t.f * (t.heading ? Math.sqrt(s) : s)), t.cap);

function hasRigid(node) {
  let hit = false;
  walk(node, (d) => { if (RIGID.has(d.type)) hit = true; });
  return hit;
}

/**
 * Outermost sparse stack (not yet handled) that holds growable text. Cards side
 * by side in an HStack (same width, text only) are one group: they scale together, limited by the
 * fullest card, so a row of peer cards keeps one type size.
 */
async function nextCandidate(xml, done) {
  const L = await layout(xml);
  try {
    let found = null;
    const visit = (n, parent) => {
      if (found || !STACKS.has(n.type)) return;
      // the slide root is not a card: its spare height belongs to its bands
      if (parent && n.id && !done.has(n.id)) {
        const targets = textTargets(n);
        const f = targets.length ? fill(n, L) : null;
        if (f && f.ratio < LOW_FILL && f.inner - f.content > MIN_SLACK) {
          const peer = (m) => STACKS.has(m.type) && m.id && m.w === n.w && !hasRigid(m) && textTargets(m).length;
          const members = parent?.type === "hstack" && peer(n) ? parent.children.filter(peer) : [n];
          found = { ids: members.map((m) => m.id), targets: members.flatMap(textTargets),
            ratio: Math.max(...members.map((m) => fill(m, L).ratio)) };
          return;
        }
      }
      (n.children ?? []).forEach((c) => visit(c, n));
    };
    L.slides.forEach((r) => visit(r, null));
    return found;
  } finally { L.free(); }
}

async function growText(xml, report) {
  // Outermost first, re-evaluated after every change: growing a parent may
  // already fill its children, or leave one of them still sparse.
  const done = new Set();
  for (let c; done.size < 24 && (c = await nextCandidate(xml, done));) {
    c.ids.forEach((id) => done.add(id));
    // stage 1: font sizes
    const applyFont = (src, s) => c.targets.reduce((x, t) => setAttrs(x, t.id, { fontSize: scaled(t, s) }), src);
    const headings = c.targets.filter((t) => t.heading).map((t) => t.id);
    const font = await search(xml, c.ids, applyFont, MAX_SCALE, headings);
    if (!c.targets.some((t) => scaled(t, font.best) !== t.f)) font.best = 1; // all already at their caps
    if (font.best > 1) xml = applyFont(xml, font.best);

    // stage 2: once fonts hit their caps, spread the rest into line height + gaps
    let spacing = { best: 1, ratio: font.ratio };
    if (font.ratio < LOW_FILL) {
      const T = await layout(xml);
      const lines = [], gaps = [];
      try {
        for (const id of c.ids) walk(T.byId.get(id), (n) => {
          if (!n.id) return;
          if (["text", "ul", "ol"].includes(n.type)) lines.push({ id: n.id, lh: n.lineHeight ?? 1.3 });
          if (STACKS.has(n.type) && typeof n.gap === "number" && n.gap > 0) gaps.push({ id: n.id, g: n.gap });
        });
      } finally { T.free(); }
      const applySpacing = (src, t) => {
        let x = lines.reduce((acc, l) => setAttrs(acc, l.id,
          { lineHeight: Math.min(Math.round(l.lh * t * 100) / 100, 1.6) }), src);
        x = gaps.reduce((acc, g) => setAttrs(acc, g.id, { gap: Math.round(g.g * (1 + 1.5 * (t - 1))) }), x);
        return x;
      };
      spacing = await search(xml, c.ids, applySpacing, 1.4, headings);
      if (spacing.best > 1) xml = applySpacing(xml, spacing.best);
    }

    if (font.best === 1 && spacing.best === 1) continue;
    const body = c.targets.find((t) => !t.heading) ?? c.targets[0];
    report.push(`text x${font.best.toFixed(2)} (e.g. ${body.f} -> ${scaled(body, font.best)}pt)`
      + (spacing.best > 1 ? `, spacing x${spacing.best.toFixed(2)}` : "")
      + `, fill ${Math.round(c.ratio * 100)}% -> ${Math.round(spacing.ratio * 100)}%`);
  }
  return xml;
}

/** How far each stack's content overruns its box (<= 0 means it fits). */
function overflows(L) {
  const out = new Map();
  for (const root of L.slides) walk(root, (n) => {
    if (n.id && STACKS.has(n.type)) out.set(n.id, natural(n, L) - L.box(n).h);
  });
  return out;
}

/**
 * Lines a text node wraps to, measured at 85% of its width: the renderer's font
 * runs wider than POM's measuring font, so a heading that "just fits" in POM
 * wraps on the slide. The margin keeps grown headings on their line count.
 */
function lineCount(n, L) {
  const b = L.box(n);
  const fs = n.fontSize ?? 24, lh = n.lineHeight ?? 1.3;
  const { heightPx } = measureText(n.text ?? (n.runs ?? []).map((r) => r.text).join(""),
    Math.max(0, b.w - b.pl - b.pr) * 0.85, { fontFamily: n.fontFamily ?? "Noto Sans JP", fontSizePx: fs,
      lineHeight: lh, fontWeight: n.bold ? "bold" : "normal", letterSpacingPx: n.letterSpacing },
    L.ctx.textMeasurementMode, L.ctx.fontRegistry);
  return Math.round(heightPx / (fs * lh));
}

/**
 * Binary-search the largest factor in [1, max] for `apply` such that the
 * fullest candidate stays <= TARGET_FILL, no stack on the slide overflows more than it
 * already did (flex boxes may resize; nothing may overrun), and no heading in
 * `keepLines` wraps onto an extra line.
 */
async function search(xml, ids, apply, max, keepLines = []) {
  const fullest = (L) => Math.max(...ids.map((id) => fill(L.byId.get(id), L).ratio));
  const B = await layout(xml);
  let before, ratio, lines0;
  try {
    before = overflows(B);
    ratio = fullest(B);
    // a heading only 1 line in POM counts as 1 even if the 85% margin wraps it
    lines0 = new Map(keepLines.map((k) => [k, lineCount(B.byId.get(k), B)]));
  } finally { B.free(); }
  let lo = 1, hi = max, best = 1;
  for (let i = 0; i < 7; i++) {
    const s = (lo + hi) / 2;
    const T = await layout(apply(xml, s));
    try {
      const r = fullest(T);
      let ok = r <= TARGET_FILL && T.slides.every((r) => natural(r, T) <= SLIDE.h + 1);
      for (const [k, o] of overflows(T)) if (o > Math.max(before.get(k) ?? 0, 0) + 1) ok = false;
      for (const [k, l0] of lines0) if (lineCount(T.byId.get(k), T) > Math.max(l0, 1)) ok = false;
      if (ok) { best = s; ratio = r; lo = s; } else hi = s;
    } finally { T.free(); }
  }
  return { best, ratio };
}

// --- entry ----------------------------------------------------------------------

/** One slide (with the document's <Theme> prefix) through every phase. */
async function fitSlide(inputXml, report) {
  let xml = tagNodes(inputXml);
  xml = await respectHeights(xml, report);
  xml = await splitLists(xml, report);
  xml = await fitTables(xml, report);
  xml = await sizeTables(xml, report);
  xml = await growDiagrams(xml, report);
  xml = await growText(xml, report);
  return report.length ? untag(xml) : inputXml;
}

// Whole-pass time budget. Each slide takes ~1-3s; a deck is compiled in one
// call under a 120s subprocess timeout (compiler_client.compile_xml), so stop
// early on slow machines — remaining slides compile unchanged.
const BUDGET_MS = Number(process.env.POM_FIT_GROW_BUDGET_MS ?? 60000);

/**
 * Returns { xml, report }. `report` lists every change made (prefixed with the
 * slide number); empty when every slide was already full. Slides are fitted
 * one at a time — each measurement only lays out its own slide. Throws only on
 * programmer error — callers should fall back to the input XML.
 */
export async function fitGrow(inputXml) {
  const first = inputXml.search(/<Slide\b/);
  if (first < 0) return { xml: inputXml, report: [] };
  const prefix = inputXml.slice(0, first);
  const started = Date.now();
  const report = [];
  let index = 0;
  const parts = [];
  let last = first;
  for (const m of inputXml.slice(first).matchAll(/<Slide\b[\s\S]*?<\/Slide>/g)) {
    const start = first + m.index;
    parts.push(inputXml.slice(last, start));
    index += 1;
    let slide = m[0];
    if (Date.now() - started > BUDGET_MS) {
      report.push(`slide ${index}: skipped (time budget ${BUDGET_MS}ms used)`);
    } else {
      // one slide failing must not cost the other slides their fitting
      try {
        const slideReport = [];
        const out = await fitSlide(prefix + slide, slideReport);
        slide = out.slice(out.search(/<Slide\b/));
        report.push(...slideReport.map((r) => `slide ${index}: ${r}`));
      } catch (error) {
        report.push(`slide ${index}: skipped (${error && error.message ? error.message : String(error)})`);
      }
    }
    parts.push(slide);
    last = start + m[0].length;
  }
  parts.push(inputXml.slice(last));
  return { xml: report.some((r) => !r.includes("skipped")) ? prefix + parts.join("") : inputXml, report };
}
