// Table cell margins (user 2026-11-02: on; POM writes 0, so text touched a fill's edge and the next column's text).
// One margin per table, from its average column width: 8% of it, 4 to 12 px. A flat 12 px broke words in narrow
// columns (replay: a 7-column table at 446 px, "Hyderabad" in 96 px). pptx-post writes it into every cell; fit-grow
// measures each column less twice it. POM_CELL_MARGIN sets the largest margin; 0 turns margins off.

const MAX = Number(process.env.POM_CELL_MARGIN ?? 12);

/** The left / right margin (px) of every cell of a table `tableW` px wide with `cols` columns. */
export function cellMargin(tableW, cols) {
  if (!(MAX > 0) || !(cols > 0) || !(tableW > 0)) return 0;
  return Math.max(Math.min(4, MAX), Math.min(MAX, Math.round(0.08 * tableW / cols)));
}
