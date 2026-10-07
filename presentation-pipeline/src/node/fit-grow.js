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
//   3a. share height — a KPI row beside a sparse growing text band gets the same
//                     grow, so both have room to fill.
//   3b. KPI values  — a sparse row of stat tiles grows its hero numbers (and
//                     their inline unit <Span>s) together, up to 96px; a lone hero
//                     stat card (short number >= 48px) up to 120px.
//   4. text         — in each stack under ~70% full, fonts grow together until
//                     ~88% full, as the composer sizes cards: titles and body by
//                     s, labels and icons by sqrt(s); card title <= 48px, body
//                     <= 28px and <= title / 1.3; each box's stat number and
//                     slide headlines outside cards untouched. Past the caps the
//                     rest goes into gaps and line height (<= 1.45). Peer cards
//                     in a row scale as one group; a card title may wrap onto two
//                     more lines; text with an inline <Span fontSize> keeps its size.
//   5. headings     — a heading that wraps one line more at 85% of its width
//                     (the renderer's font runs wider) gets minH for that line;
//                     a heading in a loaded font (src/node/fonts/) is measured at
//                     full width, so it never gets one.
//
// It edits the ORIGINAL XML text (only size attributes change), and measures
// with POM's own layout engine so its numbers match what buildPptx will do.
// That engine is internal to POM (not exported), hence the exact version pin
// in package.json. Any failure returns the input XML unchanged.

import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { loadFonts } from "./fonts.js";

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
const MAX_SCALE = 3.0;
const FIXED_FONT = 24;      // >= this outside a card is a title / KPI number: not grown as text (KPI numbers: growStats)
// Card text fills its card the way the composer does (scripts/phase0b/render.py
// fill_card_text; user, 2026-10-04 and 2026-10-06: grow the type into the empty space,
// don't shrink the card): a card title up to 48px, body up to 28px and at most
// title / 1.3, labels (caps / letter-spaced) by sqrt(s); icons grow by sqrt(s) up to 56px.
// In a KPI tile only the number is big: its label / delta lines stay <= 0.45x the number.
const TITLE_CAP = 48;
const BODY_CAP = 28;
const LABEL_CAP = 24;
const TITLE_RATIO = 1.3;
const ICON_CAP = 56;
const STAT_SIDE = 0.45;
const ANCHOR_TEXT_MAX = 12;  // a box's stat anchor is a short number ("$48.2M", "0.33x")
const LINE_HEIGHT_MAX = 1.45; // spare space past the font caps goes to gaps first, line height stays readable
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
  const ctx = createBuildContext("auto", loadFonts());
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
      const f = c.fontSize ?? TD_FONT; // POM draws a <Td> without fontSize at 18 px
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
      const f0 = Math.max(14, ...n.rows.flatMap((r) => r.cells.map((c) => c.fontSize ?? TD_FONT)));
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
//             rows (<= ROW_CAP, <= ROW_GROW x their text; compile-pom centres
//             cell text vertically, so a taller row reads as air, not a gap),
//             into empty slide space or dead
//             space in its own card: only the table and its ancestors change size
//             (a peer card stretched by a taller row would just gain dead space).

const TD_FONT = 18;  // POM's <Td> default fontSize
const TD_BODY = 14;  // written into cells without fontSize
const ROW_PAD = 8;   // px around a cell's lines (POM writes Td margins of 0)
const ROW_CAP = 96;  // px — spare-height growth of the main table's rows
const ROW_GROW = 2;  // x a row's text height
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
async function growMainTable(xml, id, report, onlyTable, caps = { font: TD_FONT_CAP, row: ROW_CAP, grow: ROW_GROW }) {
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
  const fontFor = (k) => (c) => Math.min(Math.round((c.fontSize ?? TD_FONT) * k), Math.max(c.fontSize ?? TD_FONT, caps.font));
  const atFont = (k) => {
    const plan = planTable(n, grid, W, fontFor(k), L.ctx, declared);
    const rows = declared.map((d, i) => rowFor(d, plan.need[i]));
    return { plan, rows, xml: writeTable(xml, id, { widths: plan.widths, rows, fontOf: k > 1 ? fontFor(k) : null }) };
  };
  const kMax = sized || !onlyTable ? 1 : Math.max(1, caps.font / f0);
  const k = kMax > 1 ? await bisect(1, kMax, (x) => {
    const a = atFont(x);
    return a.plan.valid && tableFits(a.xml, id, before, keep);
  }) : 1;
  const grownFont = cells.some((c) => fontFor(k)(c) !== (c.fontSize ?? TD_FONT));
  const K = atFont(grownFont ? k : 1);

  // then rows, each up to min(ROW_CAP, ROW_GROW x its text) (never below where it is)
  const cap = K.rows.map((r, i) => Math.max(r, Math.min(caps.row, Math.round(caps.grow * K.plan.need[i]))));
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

// --- phase 3a: grow the stat values of a sparse KPI tile row --------------------
// A tile's hero number (the one text >= FIXED_FONT, often "₹114.9<Span>L</Span>")
// is frozen by phase 3b, so a KPI row given the slide's spare height showed a
// 30px number in a tall, empty tile. Peer tiles in one HStack scale their numbers
// together (one type size across the row), inline <Span fontSize> units with them,
// up to STAT_CAP, without wrapping a number or changing any width.

const STAT_CAP = 96;          // composer: a KPI number takes the largest size its tile allows
// A lone hero stat: Genspark draws the headline's number at 120-244 px on 1920 (80-160
// on our 1280). Only a short numeric anchor ("0.33x", "₹114.9L") in a card qualifies,
// so a headline or title in a card never grows here.
const HERO_CAP = 120;
const HERO_TEXT_MAX = 12;
const HERO_MIN = 48;         // drawn as a hero already (recipe: 72); side microstats (~30) are not

/** The single largest text (>= FIXED_FONT) inside a tile, or null. */
function statAnchor(tile) {
  const texts = [];
  let rigid = false;
  walk(tile, (n) => {
    if (RIGID.has(n.type)) rigid = true;
    if (n.id && n.type === "text") texts.push(n);
  });
  if (rigid || texts.length < 2) return null;
  const size = (t) => t.fontSize ?? 24;
  const top = Math.max(...texts.map(size));
  const tops = texts.filter((t) => size(t) === top);
  return top >= FIXED_FONT && tops.length === 1 ? tops[0] : null;
}

// --- phase 3a: a KPI row shares the spare height of a sparse text band ------------
// The generator gives grow to one band. When that band is a callout of two lines, it takes
// all the spare height while the KPI tiles beside it stay at content height: the callout
// text stops at its cap below the headline and the tiles count as full, so their numbers
// never grow (2026-10-06 exec summary: callout 18% full, tiles untouched). A row of stat
// tiles without grow / h next to such a band gets the same grow; growStats and growText
// then fill both.

function statRow(n) {
  if (n.type !== "hstack") return false;
  const tiles = (n.children ?? []).filter((c) => STACKS.has(c.type) && c.id);
  return tiles.length >= 2 && tiles.every(statAnchor);
}

// The other way round too: when the KPI row is the one growing band, its tiles stretch to
// the slide's spare height around a label and a number while the callout under it stays one
// cramped line (2026-10-06 neutral-kpi run: tiles ~400px tall, ~90px of content). A boxed
// text band without grow / h beside it gets the same grow; growStats and growText fill both.
const textBand = (c) => c.id && STACKS.has(c.type) && hasBoxStyle(c) && !hasRigid(c) && !statRow(c)
  && textTargets(c).length && c.h === undefined && c.grow === undefined;

async function shareHeight(xml, report) {
  const L = await layout(xml);
  const edits = [];
  try {
    for (const root of L.slides) walk(root, (p) => {
      if (p.type !== "vstack") return;
      const kids = p.children ?? [];
      const growing = kids.filter((c) => c.grow !== undefined);
      if (growing.length !== 1) return;
      const g = growing[0];
      if (!g.id || !STACKS.has(g.type) || hasRigid(g) || !textTargets(g).length) return;
      if (fill(g, L).ratio >= LOW_FILL) return;
      if (statRow(g)) {
        for (const r of kids) if (r !== g && textBand(r)) edits.push([r.id, g.grow, "text"]);
        return;
      }
      for (const r of kids) {
        if (r !== g && r.id && statRow(r) && r.h === undefined && r.grow === undefined) edits.push([r.id, g.grow, "kpi"]);
      }
    });
  } finally { L.free(); }
  for (const [id, grow, what] of edits) {
    // a text band's type stops at its cap: centred, the rest of its share is even padding
    const band = what === "text" && !/\sjustifyContent\s*=/.test(xml.slice(findElement(xml, id).start, findElement(xml, id).openEnd));
    xml = setAttrs(xml, id, band ? { grow, justifyContent: "center" } : { grow });
    report.push(what === "text" ? `text band takes a share of the spare height (grow=${grow}) beside a sparse KPI row`
      : `KPI row takes a share of the spare height (grow=${grow}) beside a sparse text band`);
  }
  return xml;
}

/** Scale fontSize on one element's open tag and on every <Span fontSize> inside it. */
function scaleTextFont(xml, id, s, cap = STAT_CAP) {
  const el = findElement(xml, id);
  if (!el) return xml;
  const grow = (v) => String(Math.min(Math.round(Number(v) * s), cap));
  const body = xml.slice(el.start, el.end).replace(/(<(?:Text|Span)\b[^>]*?\sfontSize\s*=\s*")([\d.]+)(")/g,
    (m, a, v, b) => a + grow(v) + b);
  return xml.slice(0, el.start) + body + xml.slice(el.end);
}

async function growStats(xml, report) {
  const L = await layout(xml);
  const groups = [];
  try {
    for (const root of L.slides) walk(root, (n) => {
      if (n.type !== "hstack") return;
      const tiles = (n.children ?? []).filter((c) => STACKS.has(c.type) && c.id);
      if (tiles.length < 2) return;
      const anchors = tiles.map(statAnchor);
      if (anchors.some((a) => !a)) return;
      const f0 = Math.min(...anchors.map((a) => a.fontSize ?? 24));
      if (f0 >= STAT_CAP) return;
      const ratio = Math.max(...tiles.map((t) => fill(t, L).ratio));
      if (ratio < LOW_FILL) groups.push({ ids: tiles.map((t) => t.id), anchors: anchors.map((a) => a.id), f0, ratio, cap: STAT_CAP });
    });
    // a lone hero stat (the one number the headline rests on) grows past tile size
    const grouped = new Set(groups.flatMap((g) => g.ids));
    for (const root of L.slides) walk(root, (n, parent) => {
      if (!parent || n.type !== "vstack" || !n.id || grouped.has(n.id) || !hasBoxStyle(n)) return; // not the slide root
      if (parent?.type === "hstack" && (parent.children ?? []).filter((c) => STACKS.has(c.type) && statAnchor(c)).length > 1) return;
      const a = statAnchor(n);
      const text = a ? (a.text ?? (a.runs ?? []).map((r) => r.text).join("")) : "";
      if (!a || !/\d/.test(text) || text.trim().length > HERO_TEXT_MAX) return;
      if ((a.fontSize ?? 24) < HERO_MIN || (a.fontSize ?? 24) >= HERO_CAP) return;
      const ratio = fill(n, L).ratio;
      if (ratio < LOW_FILL) groups.push({ ids: [n.id], anchors: [a.id], f0: a.fontSize ?? 24, ratio, cap: HERO_CAP, hero: true });
    });
  } finally { L.free(); }
  for (const g of groups) {
    const apply = (src, s) => g.anchors.reduce((x, id) => scaleTextFont(x, id, s, g.cap), src);
    const unpinned = xml;
    xml = await pinWidths(xml, g.ids);
    const r = await search(xml, g.ids, apply, g.cap / g.f0, g.anchors, 0, g.anchors);
    if (r.best <= 1.05) { xml = unpinned; continue; }
    xml = apply(xml, r.best);
    report.push(`${g.hero ? "hero stat" : "KPI values"} x${r.best.toFixed(2)} (${g.f0} -> ${Math.min(Math.round(g.f0 * r.best), g.cap)}px), `
      + `fill ${Math.round(g.ratio * 100)}% -> ${Math.round(r.ratio * 100)}%`);
  }
  return xml;
}

// --- phase 3b: grow text inside sparse text-only stacks ------------------------

function textTargets(stack) {
  // inside a card (a box with background / border / padding) every text may grow, even one
  // the LLM wrote at >= 24px; outside one, >= 24px is a slide headline and stays
  const boxed = hasBoxStyle(stack);
  // next to a diagram / table / chart, a card's text is its header: header-sized at most
  // ("Optimization Timeline" grew to ~40px and pushed its timeline out of the card)
  const beside = hasRigid(stack) ? LABEL_CAP : Infinity;
  const out = [];
  const frozen = [];   // sizes of texts in the box that do not grow here
  let smallestFixed = Infinity;
  walk(stack, (n, parent) => {
    if (!n.id || !["text", "ul", "ol"].includes(n.type)) return;
    const f = n.fontSize ?? 24;
    // inline <Span fontSize> / <Li fontSize> keep their own size: growing only
    // the outer size would break the proportion, so leave these nodes alone
    const sized = (runs) => (runs ?? []).some((r) => r.fontSize !== undefined);
    const spans = n.type === "text" ? sized(n.runs) : n.items.some((i) => i.fontSize !== undefined || sized(i.runs));
    if (spans || (f >= FIXED_FONT && !boxed)) {
      if (f >= FIXED_FONT) smallestFixed = Math.min(smallestFixed, f);
      frozen.push(n.type === "text" ? Math.max(f, ...(n.runs ?? []).map((r) => r.fontSize ?? 0)) : f);
      return;
    }
    const text = n.text ?? (n.runs ?? []).map((r) => r.text).join("");
    const label = /[A-Z]/.test(text) && text === text.toUpperCase() || n.letterSpacing !== undefined;
    const title = n.type === "text" && !!n.bold && !label;
    const sig = parent ? `${parent.type}(${(parent.children ?? []).map((k) => k.type).join(",")})` : "";
    out.push({ id: n.id, f, text, sig, title, label: n.type === "text" && label, heading: title || (n.type === "text" && label) });
  });
  // a stat value / hero number (a short number >= 1.5x the smallest text in the box) is
  // the box's anchor: frozen here (growStats sizes it)
  const sizes = out.map((t) => t.f);
  const anchor = Math.max(...sizes);
  const isAnchor = (t) => t.f === anchor && shortNumber(t.text);
  // a stat tile: a card whose one big text is a short number ("₹59.8 Cr"; not a header
  // stack's headline, nor a sentence with a digit in it: "Unlocking H2 growth ...")
  const big = boxed ? statAnchor(stack) : null;
  const shortNumber = (t) => /\d/.test(t) && t.trim().length <= ANCHOR_TEXT_MAX;
  let stat = big !== null && shortNumber(big.text ?? (big.runs ?? []).map((r) => r.text).join(""));
  if (out.length > 1 && anchor >= 1.5 * Math.min(...sizes) && out.some(isAnchor)) {
    smallestFixed = Math.min(smallestFixed, anchor);
    stat = boxed;
    for (let i = out.length - 1; i >= 0; i--) if (isAnchor(out[i])) { frozen.push(out[i].f); out.splice(i, 1); }
  }
  // keep hierarchy: grown text stays well below the KPI number / title it sits with; in a
  // stat tile nothing but the number is a title ("+18% QoQ" is bold, not a heading)
  // (0.62x a small number: labels of a 22px number may reach 13px; 0.45x a big one: the
  // delta under a 55px number stays 24px, not 34)
  const ceiling = Math.floor(stat ? Math.min(smallestFixed * 0.62, Math.max(smallestFixed * STAT_SIDE, 16))
    : smallestFixed * 0.62);
  for (const t of out) {
    if (stat && t.title) Object.assign(t, { title: false, label: true });
    const cap = t.title ? TITLE_CAP : t.label ? LABEL_CAP : BODY_CAP;
    // grown text stays 2px below every bigger text in the box that does not grow (a label
    // under a "₹59.8 Cr" with an inline unit size never passes the number)
    const above = Math.min(...frozen.filter((f) => f > t.f)) - 2;
    t.cap = Math.max(t.f, Math.min(cap, ceiling, above, beside));
  }
  return out;
}

// titles and body grow by s (the LLM's proportion), labels by sqrt(s)
const scaled = (t, s) => Math.min(Math.round(t.f * (t.label ? Math.sqrt(s) : s)), t.cap);

/** Sizes at factor s; a body stays at most 1/1.3 of every larger card title (composer rule). */
function sizesAt(targets, s) {
  const titles = targets.filter((t) => t.title);
  return targets.map((t) => {
    let size = scaled(t, s);
    if (!t.heading) for (const h of titles) if (h.f > t.f) size = Math.min(size, Math.max(t.f, Math.floor(scaled(h, s) / TITLE_RATIO)));
    return size;
  });
}

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
    const visit = (n, parent, root) => {
      if (found || !STACKS.has(n.type)) return;
      // the slide root is not a card: its spare height belongs to its bands
      if (parent && n.id && !done.has(n.id)) {
        const targets = textTargets(n);
        const f = targets.length ? fill(n, L) : null;
        if (f && f.ratio < LOW_FILL && f.inner - f.content > MIN_SLACK) {
          const sameW = (m, ref) => m.w === ref.w || (PINNED.has(m.id) && PINNED.has(ref.id));
          const peerOf = (ref) => (m) => STACKS.has(m.type) && m.id && sameW(m, ref) && !hasRigid(m) && textTargets(m).length;
          let members = parent?.type === "hstack" && peerOf(n)(n) ? parent.children.filter(peerOf(n)) : [n];
          // a sparse row of peer tiles grows as its tiles, in one group: grown as one
          // block first, "ARR" (caps = label) and "Gross Margin" (body) got different
          // sizes, and a label grown to 24px then counted as a frozen title
          const tiles = n.type === "hstack" ? (n.children ?? []).filter((c) => STACKS.has(c.type)) : [];
          if (tiles.length >= 2 && tiles.every(peerOf(tiles[0]))) members = tiles;
          const ids = members.map((m) => m.id);
          const lists = members.map((m) => textTargets(m));
          // peer tiles: the same text slot has the same role in every tile
          if (lists.length > 1 && lists.every((l) => l.length === lists[0].length)) {
            lists[0].forEach((_, i) => {
              const role = lists.find((l) => l[i].heading)?.[i];
              if (role) for (const l of lists) Object.assign(l[i], { heading: true, title: role.title, label: role.label, cap: Math.max(l[i].f, role.cap) });
            });
          }
          const icons = [], texts = [];
          for (const m of members) walk(m, (d) => {
            if (d.type === "icon" && d.id) icons.push({ id: d.id, f: d.size ?? 24 });
            if (["text", "ul", "ol"].includes(d.type) && d.id) texts.push(d.id);
          });
          // a text whose word is already wider than its box does not grow (the guard shrinks it)
          const over = wordsOver(L, texts);
          // rows of the same shape (icon + text, ...) at the same size are peers: one role, so
          // a bold first item ("Milk 500ml: 12.4") does not grow while its siblings are held
          const bySlot = new Map();
          for (const t of lists.flat()) if (t.sig.startsWith("hstack")) bySlot.set(`${t.sig}:${t.f}`, [...(bySlot.get(`${t.sig}:${t.f}`) ?? []), t]);
          for (const group of bySlot.values()) {
            const role = group.length > 1 && group.find((t) => t.title);
            if (role) for (const t of group) Object.assign(t, { title: true, heading: true, label: false, cap: Math.max(...group.map((g) => g.cap)) });
          }
          found = { ids, seen: [n.id, ...ids], targets: lists.flat().filter((t) => !over.has(t.id)), icons, texts,
            ratio: Math.max(...members.map((m) => fill(m, L).ratio)) };
          return;
        }
      }
      (n.children ?? []).forEach((c) => visit(c, n, root));
    };
    L.slides.forEach((r) => visit(r, null, r));
    return found;
  } finally { L.free(); }
}

/**
 * Pin each stack in a row (HStack child) to its current width. A card's width in a row
 * follows its text, so growing its text moves the boundary with its neighbour (CHEFFIN
 * "Closing Statement" beside a table card: every size changed the table's width, nothing grew;
 * peer KPI tiles re-balanced as their labels grew). Pinned, text grows into the box it has.
 * growStats pins too, so every phase measures the same layout (a flexible card gives its
 * children a pixel more than a pinned one: a number grown to the edge was then 1px over).
 */
// ids this pass pinned (pinWidths): their w is fit-grow's, not the generator's, so pinned
// tiles that were peers (w="max" each) stay peers
const PINNED = new Set();

async function pinWidths(xml, ids) {
  const L = await layout(xml);
  const edits = [];
  try {
    for (const root of L.slides) walk(root, (n, parent) => {
      // flexible widths only (none / "max"): a "56%" or "160" is the author's width
      if (parent?.type === "hstack" && n.id && ids.includes(n.id) && (n.w === undefined || n.w === "max")) edits.push([n.id, Math.round(L.box(n).w * 100) / 100]);
    });
  } finally { L.free(); }
  edits.forEach(([id]) => PINNED.add(id));
  return edits.reduce((x, [id, w]) => setAttrs(x, id, { w }), xml);
}

async function growText(xml, report) {
  // Outermost first, re-evaluated after every change: growing a parent may
  // already fill its children, or leave one of them still sparse.
  const done = new Set();
  for (let c; done.size < 24 && (c = await nextCandidate(xml, done));) {
    c.seen.forEach((id) => done.add(id));
    // stage 1: font sizes
    const applyFont = (src, s) => {
      const sizes = sizesAt(c.targets, s);
      const x = c.targets.reduce((acc, t, i) => setAttrs(acc, t.id, { fontSize: sizes[i] }), src);
      return c.icons.reduce((acc, ic) => setAttrs(acc, ic.id,
        { size: Math.max(ic.f, Math.min(Math.round(ic.f * Math.sqrt(s)), ICON_CAP)) }), x);
    };
    const headings = c.targets.filter((t) => t.heading).map((t) => t.id);
    // a card title may wrap onto up to two more lines, as in the composer (its card has the
    // room; fill / overflow are still checked): at 85% of its width a title at the wrap edge
    // otherwise held every text in its card group at x1.05 (slide "Q4 Priorities", 2026-10-06)
    if (!c.targets.length && !c.icons.length) continue;
    const unpinned = xml;
    xml = await pinWidths(xml, c.ids);
    // every text in the group is checked: peer tiles re-balance their widths as labels grow,
    // and a KPI number that fitted could lose its room (s11: one tile's number shrunk by the guard)
    let font = await search(xml, c.ids, applyFont, MAX_SCALE, headings, 2, c.texts);
    // growing everything together blocked early (a title in a row beside an icon cannot wrap,
    // so it widens its card and squeezes a neighbour: CHEFFIN "Closing Statement" stayed x1.03):
    // grow the rest with the titles kept at their size
    if (font.best < 1.2 && font.ratio < LOW_FILL && c.targets.some((t) => t.title) && c.targets.some((t) => !t.title)) {
      const kept = c.targets.map((t) => (t.title ? { ...t, cap: t.f } : t));
      const applyKept = (src, sc) => {
        const sizes = sizesAt(kept, sc);
        return kept.reduce((acc, t, i) => setAttrs(acc, t.id, { fontSize: sizes[i] }), src);
      };
      const rest = await search(xml, c.ids, applyKept, MAX_SCALE, headings, 2, c.texts);
      if (rest.best > font.best) { c.targets = kept; c.icons = []; font = rest; }  // icons sit in the title row
    }
    if (sizesAt(c.targets, font.best).every((f, i) => f === c.targets[i].f)) font.best = 1; // all already at their caps
    if (font.best > 1) xml = applyFont(xml, font.best);

    // stage 2: once fonts hit their caps, spread the rest into gaps and line height
    let spacing = { best: 1, ratio: font.ratio };
    if (font.ratio < LOW_FILL) {
      const T = await layout(xml);
      const lines = [], gaps = [];
      // body text only: titles / labels / KPI numbers keep their line height (composer: titles 1.2)
      const grown = new Set(c.targets.filter((t) => !t.heading).map((t) => t.id));
      try {
        for (const id of c.ids) walk(T.byId.get(id), (n) => {
          if (!n.id) return;
          if (grown.has(n.id)) lines.push({ id: n.id, lh: n.lineHeight ?? 1.3 });
          // vertical gaps only: an HStack's gap adds no height, it takes width from the cards
          // in the row (a second pass grew a row's gap 12 -> 19 -> 30 and shrank its words)
          if (n.type === "vstack" && typeof n.gap === "number" && n.gap > 0) gaps.push({ id: n.id, g: n.gap });
        });
      } finally { T.free(); }
      const applySpacing = (src, t) => {
        let x = lines.reduce((acc, l) => setAttrs(acc, l.id,
          { lineHeight: Math.min(Math.round(l.lh * t * 100) / 100, Math.max(l.lh, LINE_HEIGHT_MAX)) }), src);
        x = gaps.reduce((acc, g) => setAttrs(acc, g.id, { gap: Math.round(g.g * (1 + 1.5 * (t - 1))) }), x);
        return x;
      };
      spacing = await search(xml, c.ids, applySpacing, 1.4, headings);
      if (spacing.best > 1) xml = applySpacing(xml, spacing.best);
    }

    if (font.best === 1 && spacing.best === 1) { xml = unpinned; continue; }
    const bodyAt = Math.max(0, c.targets.findIndex((t) => !t.heading));
    report.push(`text x${font.best.toFixed(2)} (e.g. ${c.targets[bodyAt].f} -> ${sizesAt(c.targets, font.best)[bodyAt]}pt)`
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
 * A font loaded from src/node/fonts/ is measured with its real widths, so no
 * margin: 85% there reserved lines the renderer never draws (§10g-1).
 */
function lineCount(n, L, margin = 0.85) {
  const b = L.box(n);
  const fs = n.fontSize ?? 24, lh = n.lineHeight ?? 1.3;
  const family = n.fontFamily ?? "Noto Sans JP";
  const real = L.ctx.fontRegistry.hasFont(family, n.bold ? "bold" : "normal");
  const { heightPx } = measureText(n.text ?? (n.runs ?? []).map((r) => r.text).join(""),
    Math.max(0, b.w - b.pl - b.pr) * (real ? 1 : margin), { fontFamily: family, fontSizePx: fs,
      lineHeight: lh, fontWeight: n.bold ? "bold" : "normal", letterSpacingPx: n.letterSpacing },
    L.ctx.textMeasurementMode, L.ctx.fontRegistry);
  return Math.round(heightPx / (fs * lh));
}

// --- phase 5: reserve the renderer's extra line for headings --------------------
// The renderer's font runs wider than POM's measuring font: a headline POM lays out
// on 1 line wraps to 2 on the slide and runs into the subtitle or the card below
// (CHEFFIN cf98c42b5371 slides 1, 3, 4). A heading (>= 20px) whose line count at 85%
// of its width is higher gets minH for those lines, when the slide has the room.
// Headings in a loaded font (src/node/fonts/) are measured at full width (lineCount),
// so they only get minH if POM itself would wrap them, i.e. never.

const HEADING_PX = 20;
const CHIP_PX = 12;

/** A card whose width is its content's: no w of its own, in a VStack that does not stretch it. */
function chip(card, up) {
  const p = up.get(card);
  return !!p && STACKS.has(card.type) && card.w === undefined && p.type === "vstack"
    && ["start", "end", "center"].includes(p.alignItems);
}

async function reserveWrap(xml, report) {
  const L = await layout(xml);
  const edits = [];
  try {
    for (const root of L.slides) {
      // the room a heading may take: its card's free height when it sits in a card (a slide
      // whose bands fill it has no spare, yet a grown card title has room inside its card:
      // "Q4 Priorities" 2026-10-06, a 3-line title drawn in a 2-line box over the body),
      // else the slide's
      const spare = new Map([[root, SLIDE.h - natural(root, L)]]);
      const roomOf = (n, up) => {
        for (let a = up.get(n); a; a = up.get(a)) {
          if (a === root) return a;
          if (STACKS.has(a.type) && hasBoxStyle(a)) {
            if (!spare.has(a)) { const f = fill(a, L); spare.set(a, Math.max(0, f.inner - f.content)); }
            return a;
          }
        }
        return root;
      };
      const up = new Map();
      walk(root, (n, parent) => { if (parent) up.set(n, parent); });
      walk(root, (n) => {
        // headings; and any text in a card sized to its content (a chip): the renderer wraps it
        // and then shrinks it to fit the one-line box (cover "Prepared by Paxcom India." at 14px)
        if (!n.id || n.type !== "text") return;
        if ((n.fontSize ?? 24) < (chip(roomOf(n, up), up) ? CHIP_PX : HEADING_PX)) return;
        const fs = n.fontSize ?? 24, lh = n.lineHeight ?? 1.3;
        const have = Math.round(L.box(n).h / (fs * lh));
        const need = lineCount(n, L);
        const extra = Math.ceil((need - have) * fs * lh);
        // the card's own free height first; a card sized to its content (a chip) grows with
        // its text, so the rest may come from the slide's spare height, as before
        const box = roomOf(n, up);
        const own = box === root ? 0 : Math.min(extra, spare.get(box));
        if (need > have && extra - own <= Math.max(0, spare.get(root))) {   // an over-full slide has none to lend
          if (box !== root) spare.set(box, spare.get(box) - own);
          spare.set(root, spare.get(root) - (extra - own));
          edits.push([n.id, Math.ceil(need * fs * lh), have, need]);
        }
      });
    }
  } finally { L.free(); }
  for (const [id, minH, have, need] of edits) {
    xml = setAttrs(xml, id, { minH });
    report.push(`heading ${have} -> ${need} lines reserved (renderer wraps wider than POM)`);
  }
  return xml;
}

/** Width of every node outside the candidate stacks (their own content may reflow). */
function outsideWidths(L, ids) {
  const inside = new Set();
  for (const id of ids) walk(L.byId.get(id), (n) => n.id && inside.add(n.id));
  const out = new Map();
  for (const root of L.slides) walk(root, (n) => { if (n.id && !inside.has(n.id)) out.set(n.id, L.box(n).w); });
  return out;
}

/**
 * Binary-search the largest factor in [1, max] for `apply` such that the
 * fullest candidate stays <= TARGET_FILL, no stack on the slide overflows more than it
 * already did (flex boxes may resize; nothing may overrun), no heading in
 * `keepLines` wraps onto more than `lineSlack` extra lines, and nothing outside the candidates changes
 * width (a w="max" card whose text grows takes width from its neighbour: gj-h1
 * slide 12's summary panel squeezed the KPI table beside it until its rows spilled).
 */
const GROW_WRAP_MARGIN = 0.8;

/** Per card id: the height the renderer's extra heading lines need (85%-width lines beyond POM's). */
function wrapNeed(L, ids) {
  const need = new Map();
  for (const id of ids) {
    const n = L.byId.get(id);
    if (!n || n.type !== "text") continue;
    const fs = n.fontSize ?? 24, lh = n.lineHeight ?? 1.3;
    // a stricter margin than reserveWrap's 85%: big bold text in a narrow card wraps more on the
    // slide than 85% predicts (CHEFFIN closing note at 42px: 5 lines drawn, 4 predicted)
    const extra = (lineCount(n, L, GROW_WRAP_MARGIN) - Math.round(L.box(n).h / (fs * lh))) * fs * lh;
    if (extra > 0) { const card = cardOf(L, n); need.set(card.id, (need.get(card.id) ?? 0) + extra); }
  }
  return need;
}

/** The nearest box-styled stack around n (its card), else the slide root. */
function cardOf(L, n) {
  if (!L.up) {
    L.up = new Map();
    for (const root of L.slides) walk(root, (d, parent) => { if (parent) L.up.set(d, parent); });
  }
  let a = L.up.get(n), last = n;
  for (; a; last = a, a = L.up.get(a)) if (STACKS.has(a.type) && hasBoxStyle(a)) return a;
  return last;
}

/** Ids (text / list) whose longest word is wider than their box (renderer slack for an unloaded font). */
/** px by which a text's / list's widest unbreakable piece runs past its box (0 when it fits). */
function overBy(L, n) {
  if (!n || !["text", "ul", "ol"].includes(n.type)) return 0;
  const family = n.fontFamily ?? "Noto Sans JP";
  const b = L.box(n);
  const list = n.type !== "text";
  const room = (b.w - b.pl - b.pr - (list ? 36 : 0)) * (exact(L.ctx, family, n.bold) ? 1 : GUARD_SLACK);
  const texts = list ? n.items.map((i) => i.text ?? (i.runs ?? []).map((r) => r.text).join(""))
    : [n.text ?? (n.runs ?? []).map((r) => r.text).join("")];
  if (room <= 0) return 0;
  return Math.max(0, widestPiece(texts, family, n.fontSize ?? 24, n.bold, n.letterSpacing, L.ctx).w - room);
}

function wordsOver(L, ids) {
  return new Set(ids.filter((id) => overBy(L, L.byId.get(id)) > 0.5));
}

/** Every text on the slide already wider than its box -> by how many px (growth may not make these worse). */
function overAll(L) {
  const out = new Map();
  for (const root of L.slides) walk(root, (n) => { const o = n.id ? overBy(L, n) : 0; if (o > 0.5) out.set(n.id, o); });
  return out;
}

async function search(xml, ids, apply, max, keepLines = [], lineSlack = 0, words = []) {
  const fullest = (L) => Math.max(...ids.map((id) => fill(L.byId.get(id), L).ratio));
  const B = await layout(xml);
  let before, ratio, lines0, slideMax, widths, over0, need0, tight0;
  try {
    before = overflows(B);
    widths = outsideWidths(B, ids);
    ratio = fullest(B);
    // a slide already past 720 (a squeezed table elsewhere) may not grow, but a sparse
    // card on it may still fill its own box (CHEFFIN slide 4 "Traffic Mix Impact",
    // 35% full on a 728px slide, was left at 14px)
    slideMax = B.slides.map((r) => Math.max(natural(r, B), SLIDE.h) + 1);
    // a heading only 1 line in POM counts as 1 even if the 85% margin wraps it
    lines0 = new Map(keepLines.map((k) => [k, lineCount(B.byId.get(k), B)]));
    over0 = wordsOver(B, words);
    tight0 = overAll(B);
    need0 = wrapNeed(B, keepLines);
  } finally { B.free(); }
  let lo = 1, hi = max, best = 1;
  for (let i = 0; i < 7; i++) {
    const s = (lo + hi) / 2;
    const T = await layout(apply(xml, s));
    try {
      const r = fullest(T);
      let ok = r <= TARGET_FILL && T.slides.every((r, j) => natural(r, T) <= slideMax[j]);
      for (const [k, o] of overflows(T)) if (o > Math.max(before.get(k) ?? 0, 0) + 1) ok = false;
      for (const [k, l0] of lines0) if (lineCount(T.byId.get(k), T) > Math.max(l0, 1) + lineSlack) ok = false;
      // the lines the renderer draws beyond POM's (85% width) need height in their card: a
      // phase may not take it (cover 2026-10-06: a chip title's second line ran out of the chip;
      // CHEFFIN closing note: the spacing phase took the room of the statement's 5th line, which
      // then ran into "+18%"). A card already short of it at the start may not get shorter.
      for (const [id, h] of wrapNeed(T, keepLines)) {
        const f = fill(T.byId.get(id), T);
        if (h > f.inner - f.content + 1 && h > (need0.get(id) ?? 0) + 1) ok = false;
      }
      for (const [k, w] of widths) if (Math.abs(T.box(T.byId.get(k)).w - w) > 1) ok = false;
      // growing never makes a word wider than its box (composer: never past the longest word)
      for (const k of wordsOver(T, words)) if (!over0.has(k)) ok = false;
      // nor makes any word on the slide (more) too wide, also outside the growing boxes: growth in one
      // column narrowed the KPI tiles beside it and broke "₹59.8" (gj-h1 slide 14, 2026-10-07 replay)
      for (const [k, o] of overAll(T)) if (o > (tight0.get(k) ?? 0) + 1) ok = false;
      if (ok) { best = s; ratio = r; lo = s; } else hi = s;
    } finally { T.free(); }
  }
  return { best, ratio };
}

// --- phase 6: shrink guard -------------------------------------------------------
// fit-grow only grows, so a word wider than its box (a long header in a narrow table
// column, "Recommendation" at 18px in a 110px cell, "₹114.9L" in a narrow KPI tile, a
// long label in a narrow chevron) stayed a word the renderer breaks mid-word (§10g R1:
// 7 left in the real-font run). For every text / list / table / processArrow label whose
// longest unbreakable piece (a word, or the part after a hyphen) is wider than the space
// it gets, at the size it has now:
//   1. widen   — a table column takes width from the columns that have spare; a column fit-grow
//                pinned takes it from its wider pinned neighbour (never an author's width);
//   2. shrink  — the type goes down to the largest size at which the piece fits, never
//                below its floor (14px; a number or title >= 28px keeps >= 28);
//   3. report  — a piece still too wide becomes a WORD_TOO_WIDE warning
//                (compile-result.json warnings), which the critic / checking loop sees.
// Every edit is tried and kept only if the slide's total overflow is lower afterwards: a
// smaller label can narrow a tile that was sized by it and break the number beside it
// (R1 replay, gj-h1 slide 14). It never grows anything and runs after every growing phase,
// so a size the growers chose is checked too. Running it twice changes nothing. A font that
// is not loaded from src/node/fonts/ is measured by POM in another font than the renderer
// draws, so it gets 8% of slack; a loaded font is exact.

const GUARD_FLOOR_BODY = 14;
const GUARD_FLOOR_BIG = 28;
const GUARD_SLACK = 0.92;       // share of the box an unloaded font may fill
const GUARD_TABLE_SAFE = 0.85;  // share of a table column a word may fill (as planTable: cell insets)
const GUARD_ROUNDS = 4;
const GUARD_MAX_WARNINGS = 5;

const guardFloor = (fs) => (fs >= GUARD_FLOOR_BIG ? GUARD_FLOOR_BIG : Math.min(fs, GUARD_FLOOR_BODY));
const pieces = (text) => String(text ?? "").split(/\s+/).flatMap((w) => w.split(/(?<=[-–—])/)).filter(Boolean);

/** The widest unbreakable piece of the texts at font size `fs`: { word, w }. */
function widestPiece(texts, family, fs, bold, spacing, ctx) {
  let widest = { word: "", w: 0 };
  for (const word of texts.flatMap(pieces)) {
    const w = measureText(word, Infinity, { fontFamily: family, fontSizePx: fs, lineHeight: 1.3,
      fontWeight: bold ? "bold" : "normal", letterSpacingPx: spacing },
    ctx.textMeasurementMode, ctx.fontRegistry).widthPx;
    if (w > widest.w) widest = { word, w };
  }
  return widest;
}

const exact = (ctx, family, bold) => ctx.fontRegistry.hasFont(family, bold ? "bold" : "normal");

/**
 * The largest size <= fs at which the piece (`at(f)` -> { w }) fits `room`; the floor when none does.
 * Widths are not exactly linear in the size, so the estimate is checked and nudged either way:
 * the answer does not depend on where it started, which keeps a second pass from changing it.
 */
function guardSize(fs, at, room) {
  const floor = guardFloor(fs);
  let f = Math.max(floor, Math.min(fs, Math.floor(fs * (room / at(fs).w))));
  while (f < fs && at(f + 1).w <= room + 0.5) f += 1;
  while (f > floor && at(f).w > room + 0.5) f -= 1;
  return f;
}

/** Every text / list / chevron / table on the slide with a piece wider than its box. */
async function scanWords(xml) {
  const L = await layout(xml);
  const ctx = L.ctx;
  const found = [];   // { id, kind, fs, own, room, at(f) -> widest piece, table? }
  const up = new Map();   // node -> parent
  for (const root of L.slides) walk(root, (n, parent) => { if (parent) up.set(n, parent); });
  // every box this pass pinned (w was flexible) around the text, innermost first, that has a pinned,
  // wider neighbour in its row: a tile beside a wider tile, then the column beside a wider column
  const columns = (n) => {
    const out = [];
    for (let a = n; up.get(a); a = up.get(a)) {
      const row = up.get(a);
      if (row.type !== "hstack" || !PINNED.has(a.id)) continue;
      const sib = (row.children ?? []).filter((c) => c !== a && PINNED.has(c.id))
        .sort((x, y) => L.box(y).w - L.box(x).w)[0];
      if (sib && L.box(sib).w > L.box(a).w) out.push({ id: a.id, w: L.box(a).w, sib: sib.id, sibW: L.box(sib).w });
    }
    return out;
  };
  try {
    for (const root of L.slides) walk(root, (n) => {
      if (!n.id) return;
      const family = n.fontFamily ?? "Noto Sans JP";
      const slack = (bold) => (exact(ctx, family, bold) ? 1 : GUARD_SLACK);
      if (n.type === "text") {
        const runs = n.runs ?? [];
        const fs = Math.max(n.fontSize ?? 24, ...runs.map((r) => r.fontSize ?? n.fontSize ?? 24));
        const b = L.box(n);
        const room = (b.w - b.pl - b.pr) * slack(n.bold);
        const text = n.text ?? runs.map((r) => r.text).join("");
        const at = (f) => widestPiece([text], family, f, n.bold, n.letterSpacing, ctx);
        if (room > 0 && at(fs).w > room + 0.5) found.push({ id: n.id, kind: "text", fs, own: n.fontSize, room, at, columns: columns(n) });
      } else if (n.type === "ul" || n.type === "ol") {
        if (n.items.some((i) => i.fontSize !== undefined || (i.runs ?? []).some((r) => r.fontSize !== undefined))) return;
        const fs = n.fontSize ?? 24;
        const b = L.box(n);
        const room = (b.w - b.pl - b.pr - 36) * slack(n.bold);
        const texts = n.items.map((i) => i.text ?? (i.runs ?? []).map((r) => r.text).join(""));
        const at = (f) => widestPiece(texts, family, f, n.bold, undefined, ctx);
        if (room > 0 && at(fs).w > room + 0.5) found.push({ id: n.id, kind: "list item", fs, own: fs, room, at });
      } else if (n.type === "processArrow") {
        if (!n.steps.length) return;
        const fs = n.fontSize ?? 14;
        const depth = (n.itemHeight ?? 80) * ARROW_DEPTH_RATIO;   // POM's text box: width - depth on each side
        const room = ((n.itemWidth ?? 150) - 2 * depth) * slack(false);
        const at = (f) => widestPiece(n.steps.map((s) => s.label), family, f, n.bold, undefined, ctx);
        if (room > 0 && at(fs).w > room + 0.5) found.push({ id: n.id, kind: "process step", fs, own: fs, room, at });
      } else if (n.type === "table") {
        const grid = cellGrid(n);
        if (!grid || !n.rows.length) return;
        const W = L.box(n).w;
        const widths = resolveColumnWidths(n, W);
        const cells = grid.flat().filter(({ span }) => span === 1);
        const needAt = (fontOf) => {   // per column: the width its longest piece needs
          const need = widths.map(() => 0), word = widths.map(() => "");
          for (const { c, col } of cells) {
            const wide = widestPiece([cellText(c)], c.fontFamily ?? "Noto Sans JP", fontOf(c), c.bold, undefined, ctx);
            if (wide.w / GUARD_TABLE_SAFE > need[col]) { need[col] = wide.w / GUARD_TABLE_SAFE; word[col] = wide.word; }
          }
          return { need, word };
        };
        const now = needAt((c) => c.fontSize ?? TD_FONT);
        if (now.need.some((x, i) => x > widths[i] + 0.5)) {
          found.push({ id: n.id, kind: "table cell", table: true, widths, need: now.need, W, needAt,
            fs0: Math.max(...cells.map(({ c }) => c.fontSize ?? TD_FONT)) });
        }
      }
    });
  } finally { L.free(); }
  // a box shares its width with what is beside the text (tiles in a column): widen it by what the word
  // lacks, scaled by the word's share of the box
  for (const t of found) for (const c of t.columns ?? []) c.need = Math.ceil(c.w * (t.at(t.fs).w - t.room) / t.room) + 2;
  return found;
}

/** The XML with one finding fixed as far as the rules allow (the same XML when nothing can be done). */
function guardEdit(xml, t, widen = 0) {
  if (t.table) {
    const { widths, need, W } = t;
    const deficit = widths.map((w, i) => Math.max(0, need[i] - w));
    const spare = widths.map((w, i) => Math.max(0, w - Math.max(need[i], 20)));
    if (sum(spare) >= sum(deficit)) {
      const give = sum(deficit) / sum(spare);
      const next = intWidths(widths.map((w, i) => (deficit[i] > 0 ? w + deficit[i] : w - spare[i] * give)), W);
      return { xml: writeTable(xml, t.id, { widths: next }), note: `table columns widened for words wider than their column -> [${next.join(", ")}]` };
    }
    // shrink: the largest table type size (every cell scaled with it) at which every column's longest
    // piece fits its unchanged width; the floor when none does
    const fontAt = (f) => (c) => {
      const own = c.fontSize ?? TD_FONT;
      return Math.max(guardFloor(own), Math.min(own, Math.round(own * f / t.fs0)));
    };
    const fits = (f) => { const n = t.needAt(fontAt(f)).need; return n.every((x, i) => x <= widths[i] + 0.5); };
    let fs = t.fs0;
    while (fs > guardFloor(t.fs0) && !fits(fs)) fs -= 1;
    if (fs >= t.fs0) return { xml, note: null };
    return { xml: writeTable(xml, t.id, { fontOf: fontAt(fs) }), note: `table cell text ${t.fs0} -> ${fs}px (a word is wider than its column)` };
  }
  if (widen !== false && t.columns?.[widen]) {
    // a box fit-grow pinned takes the px its word lacks from its wider pinned neighbour (gj-h1 slide 14:
    // "₹59.8" needs 88px in a KPI tile of a 405px column beside a 789px one); kept only if the slide gains
    const c = t.columns[widen], need = c.need;
    if (c.sibW - need > c.w + need) {
      const out = setAttrs(setAttrs(xml, c.id, { w: Math.round(c.w + need) }), c.sib, { w: Math.round(c.sibW - need) });
      return { xml: out, note: `column widened by ${need}px for "${t.at(t.fs).word}" (from its pinned neighbour)` };
    }
  }
  const fs = guardSize(t.fs, t.at, t.room);
  if (fs >= t.fs) return { xml, note: null };
  let out;
  if (t.kind === "text") {
    out = scaleTextFont(xml, t.id, fs / t.fs, Infinity);   // the open tag's size and every <Span fontSize>
    if (t.own === undefined) out = setAttrs(out, t.id, { fontSize: Math.round(24 * fs / t.fs) });  // POM's default is 24
  } else {
    out = setAttrs(xml, t.id, { fontSize: fs });
  }
  return { xml: out, note: `word "${t.at(t.fs).word}" wider than its box: ${t.kind} ${t.fs} -> ${fs}px` };
}

/** Total px the findings run past their boxes (a table: past its columns). */
function overflow(found) {
  return found.reduce((total, t) => total + (t.table
    ? sum(t.need.map((x, i) => Math.max(0, x - t.widths[i])))
    : Math.max(0, t.at(t.fs).w - t.room)), 0);
}

async function guardWords(xml, report, warnings) {
  let found = await scanWords(xml);
  for (let round = 0; round < GUARD_ROUNDS && found.length; round++) {
    let progress = false;
    for (const t of found) {
      // widen each pinned box around the text, innermost first, then shrink (widen = false)
      for (const widen of [...(t.columns ?? []).keys(), false]) {
        const edit = guardEdit(xml, t, widen);
        if (!edit.note) continue;
        const after = await scanWords(edit.xml);
        // keep an edit only when the slide's total overflow (px) goes down and no piece elsewhere is newly
        // too wide: a smaller label can narrow the tile that was sized by it and break the number beside
        // it (R1 replay: "Projected" -> "₹59.8"), which the total shows even when the count does not
        const before = new Set(found.map((f) => f.id));
        if (overflow(after) >= overflow(found) - 0.5 || after.some((f) => !before.has(f.id))) continue;
        xml = edit.xml;
        found = after;
        report.push(edit.note);
        progress = true;
        break;
      }
      if (progress) break;   // the findings changed: take them again from the new layout
    }
    if (!progress) break;
  }
  const out = [];
  for (const t of found) {
    if (t.table) {
      const i = t.need.findIndex((x, j) => x > t.widths[j] + 0.5);
      const now = t.needAt((c) => c.fontSize ?? TD_FONT);
      out.push({ code: "WORD_TOO_WIDE", message: `table cell: "${now.word[i]}" is ${Math.round(now.need[i] * GUARD_TABLE_SAFE)}px wide at`
        + ` ${t.fs0}px and needs ${Math.round(now.need[i])}px of column with cell insets, its column has ${Math.round(t.widths[i])}px`
        + ` (the renderer may break it; no other column has room and the type is at its smallest)` });
    } else {
      const wide = t.at(t.fs);
      const smallest = guardSize(t.fs, t.at, t.room);
      const why = t.at(smallest).w > t.room + 0.5 ? `it does not fit even at ${smallest}px, the smallest allowed`
        : "a smaller size would break another word";
      out.push({ code: "WORD_TOO_WIDE", message: `${t.kind}: "${wide.word}" is ${Math.round(wide.w)}px wide at ${t.fs}px, its box has ${Math.round(t.room)}px`
        + ` (the renderer will break it; ${why})` });
    }
  }
  // the critic reads these: five per slide is enough to see the problem
  warnings.push(...out.slice(0, GUARD_MAX_WARNINGS));
  if (out.length > GUARD_MAX_WARNINGS) {
    warnings.push({ code: "WORD_TOO_WIDE", message: `and ${out.length - GUARD_MAX_WARNINGS} more words wider than their boxes on this slide` });
  }
  return xml;
}

// --- phase 6: the numbers of a KPI row keep one size ---------------------------
// The guard shrinks one word at a time, so one tile's number could end smaller than its
// peers' ("₹114.9L" 41px beside four at 60px). Peer numbers take the smallest size in the row
// (user, 2026-10-04: peers share a size); a smaller size never makes a word wider.

// The rows are found BEFORE the guard: statRow needs each tile's number >= 24px, and the guard
// can take one below it (gj-h1 Blinkit: "₹7.31" 24 -> 17px), after which the row was no longer
// recognised and stayed 23 / 17 / 24 / 24 / 24 / 24px.

/** The KPI rows of the slide: per row, its tiles' ids and their numbers' ids. */
async function statRows(xml) {
  const L = await layout(xml);
  const rows = [];
  try {
    for (const root of L.slides) walk(root, (n, parent) => {
      if (!statRow(n)) return;
      const tiles = n.children.filter((c) => STACKS.has(c.type) && c.id);
      const row = { tiles: tiles.map((c) => c.id), ids: tiles.map((c) => statAnchor(c).id) };
      // stat rows stacked in one VStack with the same % tile width are one grid (kpi_grid.py's
      // 2+2 / 3+2): one number size. Tiers of different widths (hero + supporting) keep theirs.
      const pct = JSON.stringify(tiles[0].w);
      row.pct = /%/.test(pct) && tiles.every((c) => JSON.stringify(c.w) === pct) ? pct : null;
      const prev = rows[rows.length - 1];
      if (prev && row.pct && prev.pct === row.pct && parent && parent.type === "vstack" && prev.parent === parent) {
        prev.tiles.push(...row.tiles);
        prev.ids.push(...row.ids);
      } else rows.push({ ...row, parent });
    });
  } finally { L.free(); }
  return rows.map(({ tiles, ids }) => ({ tiles, ids }));
}

// A tile's label and delta grow with its number (≈ 0.3 x, ≤ 24 px; user 2026-10-07: 14 px
// labels under 96 px numbers read as an afterthought). Kept only if nothing spills.
const SIDE_RATIO = 0.3;
const SIDE_CAP = 24;

async function growStatSides(xml, report, rows) {
  const L = await layout(xml);
  const edits = [];
  try {
    for (const { tiles, ids } of rows) {
      const anchor = Math.min(...ids.map((id) => L.byId.get(id)?.fontSize ?? 24));
      const target = Math.min(SIDE_CAP, Math.round(anchor * SIDE_RATIO));
      for (const t of tiles) walk(L.byId.get(t), (n) => {
        if (n.type !== "text" || !n.id || ids.includes(n.id)) return;
        if ((n.runs ?? []).some((r) => r.fontSize !== undefined)) return;
        if ((n.fontSize ?? 24) < target) edits.push([n.id, target]);
      });
    }
  } finally { L.free(); }
  if (!edits.length) return xml;
  let out = xml;
  for (const [id, fs] of edits) out = setAttrs(out, id, { fontSize: fs });
  const T = await layout(out);
  try {
    if (spillsOf(T).length || overSlide(T) > 0) return xml;
  } finally { T.free(); }
  report.push(`KPI labels / deltas grow with their numbers (-> ${Math.max(...edits.map((e) => e[1]))}px)`);
  return out;
}

async function evenStats(xml, report, rows) {
  const L = await layout(xml);
  const uneven = [];
  try {
    for (const { tiles, ids } of rows) {
      const fs = ids.map((id) => L.byId.get(id)?.fontSize ?? 24);
      if (Math.max(...fs) - Math.min(...fs) >= 1) uneven.push({ tiles, ids, fs, min: Math.min(...fs) });
    }
  } finally { L.free(); }
  for (const r of uneven) {
    // tiles sized by their content narrow when their number shrinks and squeeze their labels
    // ("ACOS" broke at 17px): they keep the width they have
    xml = await pinWidths(xml, r.tiles);
    r.ids.forEach((id, i) => { if (r.fs[i] > r.min) xml = scaleTextFont(xml, id, r.min / r.fs[i], Infinity); });
    report.push(`KPI values share one size (${Math.max(...r.fs)} -> ${r.min}px)`);
  }
  return xml;
}

// --- entry ----------------------------------------------------------------------

/** One slide (with the document's <Theme> prefix) through every phase. */
async function fitSlide(inputXml, report, warnings = []) {
  PINNED.clear();
  let xml = tagNodes(inputXml);
  xml = await respectHeights(xml, report);
  xml = await splitLists(xml, report);
  xml = await fitTables(xml, report);
  xml = await sizeTables(xml, report);
  xml = await growDiagrams(xml, report);
  xml = await shareHeight(xml, report);
  xml = await growStats(xml, report);
  xml = await growText(xml, report);
  xml = await reserveWrap(xml, report);
  if (process.env.POM_FIT_SPILL !== "0") xml = await fixSpills(xml, report, warnings);
  if (process.env.POM_FIT_CENTRE !== "0") xml = await centreBody(xml, report);
  const w0 = warnings.length;
  const rows = await statRows(xml);
  xml = await guardWords(xml, report, warnings);
  // even, then guard again (its findings were taken at the old sizes); the guard can shrink
  // one number a step further, so repeat until nothing changes (sizes only go down)
  for (let round = 0; round < 4; round++) {
    const evened = await evenStats(xml, report, rows);
    if (evened === xml) break;
    warnings.length = w0;
    xml = await guardWords(evened, report, warnings);
  }
  const sided = await growStatSides(xml, report, rows);
  if (sided !== xml) {
    warnings.length = w0;
    xml = await guardWords(sided, report, warnings);
  }
  return report.length ? untag(xml) : inputXml;
}

// --- phase 7: spills (slide-quality item 2 step 2, 2026-10-07) -----------------
//
// A component that needs more room than its box draws past it: a table's rows or
// columns (POM keeps declared widths even when they add up to more than the box),
// a text or list in a box set too small, a stack whose content is taller than its h.
// The renderer draws all of it anyway, over the next card (docs/geometry-check-2026-10-07.md).
//
//   1. give the space — a table's columns re-planned into its box (only when no
//      column gets narrower than a word), else minW; minH = what the rows / text /
//      content need. Up to 3 rounds (narrower columns can need taller rows).
//   2. if the slide is then too full, the dense order, each step tried on the
//      original XML and the space given again: gaps (>= 8) -> padding (>= 12) ->
//      fonts (>= 14), cumulative.
//   3. still too full: the XML is left as it was and SLIDE_DENSE is reported (a
//      split into two slides is a plan decision).
// POM's own autoFit only acts on a slide too tall overall, and shrinks fonts to 10 px.

const SPILL_TOL = 2;
const DENSE_STEPS = [["gap", 0.75], ["gap", 0.5], ["padding", 0.75], ["padding", 0.5],
  ["fontSize", 0.92], ["fontSize", 0.85], ["fontSize", 0.78], ["fontSize", 0.7]];
const DENSE_FLOOR = { gap: 8, padding: 12, fontSize: 14 };

function spillsOf(L) {
  const out = [];
  for (const root of L.slides) walk(root, (n, parent) => {
    if (!n.id || !parent) return; // the slide root: a too-tall slide is overSlide's, not a spill
    const b = L.box(n);
    if (n.type === "table") {
      const cw = sum(resolveColumnWidths(n, b.w));
      if (cw > b.w + SPILL_TOL) out.push({ n, kind: "w", need: cw, have: b.w });
      const rh = rowsSum(n);
      if (rh > b.h + SPILL_TOL) out.push({ n, kind: "h", need: rh, have: b.h });
    } else if (n.type === "text" || n.type === "ul" || n.type === "ol" || STACKS.has(n.type)) {
      const need = natural(n, L);
      if (need > b.h + SPILL_TOL) out.push({ n, kind: "h", need, have: b.h });
    }
  });
  return out;
}

function overSlide(L) {
  return Math.max(0, ...L.slides.map((r) => contentHeight(r, L) - SLIDE.h * 1.005));
}

/** Edits that give each spilling component the room it draws in. */
function giveSpace(xml, spills, L) {
  const parentOf = new Map();
  for (const root of L.slides) walk(root, (c, p) => p && parentOf.set(c, p));
  for (const { n, kind, need, have } of spills) {
    if (n.type === "table" && kind === "w") {
      const grid = cellGrid(n);
      // re-plan as if no width were set: candidates then all sum to the box width
      const plan = grid && planTable({ ...n, columns: n.columns.map(() => ({})) }, grid, have,
        (c) => c.fontSize ?? TD_FONT, L.ctx, resolveRowHeights(n).map(() => 0));
      if (plan && plan.valid) {
        const widths = plan.widths ?? intWidths(n.columns.map(() => have / n.columns.length), have);
        const declared = resolveRowHeights(n);
        xml = writeTable(xml, n.id, { widths, rows: declared.map((d, i) => rowFor(d, plan.need[i])) });
      } else {
        xml = setAttrs(xml, n.id, { minW: Math.ceil(need) });
        // a child's minW does not widen its parent: carry it up while the parent is narrower
        let w = need;
        for (let p = parentOf.get(n); p && p.id && parentOf.get(p); p = parentOf.get(p)) {
          const b = L.box(p);
          w += p.type === "vstack" ? b.pl + b.pr : 0;
          if (p.type === "hstack" || b.w >= w - SPILL_TOL) break;
          xml = setAttrs(xml, p.id, { minW: Math.ceil(w) });
        }
      }
    } else {
      xml = setAttrs(xml, n.id, { minH: Math.ceil(need) });
    }
  }
  return xml;
}

/** Give space for up to 3 rounds; returns { xml, spills, over } of the result. */
async function settle(xml) {
  let L = await layout(xml);
  try {
    for (let round = 0; round < 3; round++) {
      const sp = spillsOf(L);
      if (!sp.length) break;
      xml = giveSpace(xml, sp, L);
      L.free();
      L = await layout(xml);
    }
    return { xml, spills: spillsOf(L).map(({ n, kind, need, have }) => ({ id: n.id, type: n.type, kind, need, have })),
      over: overSlide(L) };
  } finally { L.free(); }
}

function scaleSpacing(xml, scales) {
  for (const [attr, s] of Object.entries(scales)) {
    const floor = DENSE_FLOOR[attr];
    xml = xml.replace(new RegExp(`(\\s${attr}\\s*=\\s*")([\\d. ]+)(")`, "g"), (m, a, v, b) =>
      a + v.trim().split(/\s+/).map((t) => {
        const x = Number(t);
        return x > floor ? Math.max(floor, Math.round(x * s)) : x;
      }).join(" ") + b);
  }
  return xml;
}

const describeSpill = (s) => `${s.type} ${s.kind === "w" ? "width" : "height"} ${Math.round(s.have)} -> ${Math.round(s.need)}px`;

async function fixSpills(xml, report, warnings) {
  const L = await layout(xml);
  let first;
  try {
    first = spillsOf(L).map(({ n, kind, need, have }) => ({ id: n.id, type: n.type, kind, need, have }));
  } finally { L.free(); }
  // stacks follow their content: name the leaves (tables / texts) when there are any
  const named = (sp) => {
    const leaves = sp.filter((s) => !STACKS.has(s.type));
    return (leaves.length ? leaves : sp).map(describeSpill).join("; ");
  };
  if (!first.length) return xml;

  let out = await settle(xml);
  if (!out.spills.length && out.over <= 0) {
    report.push(`spill fixed (space given): ${named(first)}`);
    return out.xml;
  }
  const scales = {};
  for (const [attr, s] of DENSE_STEPS) {
    scales[attr] = s;
    out = await settle(scaleSpacing(xml, scales));
    if (!out.spills.length && out.over <= 0) {
      report.push(`spill fixed (dense: ${Object.entries(scales).map(([a, v]) => `${a} x${v}`).join(", ")}): ${named(first)}`);
      return out.xml;
    }
  }
  warnings.push({ code: "SLIDE_DENSE", message: `content needs more room than the slide has after gaps, padding and `
    + `fonts down to 14px; left as generated: ${named(first)}` });
  report.push(`spill left (slide too dense): ${named(first)}`);
  return xml;
}

// --- phase 8: centre a sparse body (slide-quality item 2 step 3, 2026-10-07) -----
//
// After every growth phase (type, KPI numbers, tables, diagrams at their caps) a
// slide whose bands do not grow can still end well above the bottom: a blank band
// reads as unfinished. Cards are not shrunk and nothing is added (user,
// 2026-10-04 / 2026-10-07): the body block (everything below the header texts,
// above a trailing source line) moves down by half the free height, the source line
// to the bottom. Accepted only if nothing then spills and the slide still fits.

const CENTRE_MIN = 48;   // px of free height below which the slide is left alone
// a sparse slide's only table takes the space first (main component before centring)
const SPARSE_TABLE_CAPS = { font: 24, row: 140, grow: 2.5 };

// eyebrow / title / subtitle, alone or in plain stacks (an eyebrow row with a badge)
const headerLike = (n) => n.type === "text" || ["icon", "shape"].includes(n.type)
  || (STACKS.has(n.type) && !hasBoxStyle(n) && (n.children ?? []).every(headerLike));

function headerCount(kids, L) {
  let i = 0;
  while (i < kids.length - 1 && (kids[i].type === "text"
    || (STACKS.has(kids[i].type) && !hasBoxStyle(kids[i]) && L.box(kids[i]).h < 200
      && headerLike(kids[i])))) i++;
  return i;
}

async function centreBody(xml, report) {
  // the slide's only table grows past the normal caps into a sparse slide first
  let L = await layout(xml);
  let tableId = null, spare = 0;
  try {
    const root = L.slides[0];
    const tables = [];
    walk(root, (n) => n.type === "table" && tables.push(n));
    if (root && tables.length === 1 && tables[0].id && !(root.children ?? []).some((c) => c.grow)) {
      tableId = tables[0].id;
      spare = L.box(root).h - contentHeight(root, L);
    }
  } finally { L.free(); }
  if (tableId && spare >= CENTRE_MIN) xml = await growMainTable(xml, tableId, report, true, SPARSE_TABLE_CAPS);

  L = await layout(xml);
  let edits = null;
  try {
    const root = L.slides[0];
    if (!root || root.type !== "vstack" || root.justifyContent) return xml;
    const kids = root.children ?? [];
    if (kids.some((c) => c.grow)) return xml; // a growing band already takes the space
    const head = headerCount(kids, L);
    const last = kids[kids.length - 1];
    const caption = kids.length - head >= 2 && last.type === "text" && (last.fontSize ?? 24) <= 16
      && L.box(last).h < 50 ? last : null;
    const body = kids.slice(head, caption ? -1 : undefined);
    if (!body.length || body.some((c) => c.margin !== undefined || !c.id)) return xml;
    const rb = L.box(root);
    const free = rb.h - rb.pb - contentHeight(root, L) + rb.pb;
    if (free < CENTRE_MIN) return xml;
    const half = Math.round(free / 2);
    edits = [[body[0].id, half]];
    if (caption && caption.id && caption.margin === undefined) edits.push([caption.id, free - half]);
  } finally { L.free(); }
  let out = xml;
  for (const [id, top] of edits) out = setAttrs(out, id, { "margin.top": top });
  const T = await layout(out);
  try {
    if (spillsOf(T).length || overSlide(T) > 0) return xml;
  } finally { T.free(); }
  report.push(`sparse body centred: ${edits[0][1]}px above` + (edits[1] ? `, source line to the bottom` : ""));
  return out;
}

// Whole-pass time budget. Each slide takes ~1-3s; a deck is compiled in one
// call under a 120s subprocess timeout (compiler_client.compile_xml), so stop
// early on slow machines — remaining slides compile unchanged.
const BUDGET_MS = Number(process.env.POM_FIT_GROW_BUDGET_MS ?? 60000);

/**
 * Returns { xml, report, warnings }. `report` lists every change made (prefixed with the
 * slide number); empty when every slide was already full. `warnings` are {code, message}
 * the guard could not fix (WORD_TOO_WIDE); compile-pom.js adds them to the compile warnings. Slides are fitted
 * one at a time — each measurement only lays out its own slide. Throws only on
 * programmer error — callers should fall back to the input XML.
 */
export async function fitGrow(inputXml) {
  const first = inputXml.search(/<Slide\b/);
  if (first < 0) return { xml: inputXml, report: [], warnings: [] };
  const prefix = inputXml.slice(0, first);
  const started = Date.now();
  const report = [];
  const warnings = [];
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
        const slideWarnings = [];
        const out = await fitSlide(prefix + slide, slideReport, slideWarnings);
        slide = out.slice(out.search(/<Slide\b/));
        report.push(...slideReport.map((r) => `slide ${index}: ${r}`));
        warnings.push(...slideWarnings.map((w) => ({ ...w, message: `slide ${index}: ${w.message}` })));
      } catch (error) {
        report.push(`slide ${index}: skipped (${error && error.message ? error.message : String(error)})`);
      }
    }
    parts.push(slide);
    last = start + m[0].length;
  }
  parts.push(inputXml.slice(last));
  return { xml: report.some((r) => !r.includes("skipped")) ? prefix + parts.join("") : inputXml, report, warnings };
}

// Layout helpers for measuring tools (scripts/phase0b/measure.mjs); fit-grow itself
// does not use these exports.
export { layout, natural, squeezes, contentHeight, tagNodes, walk, rowsSum, SLIDE };
