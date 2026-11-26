# Visual critic redesign (2026-11-20)

What the visual critic receives and returns, and how its findings become a fix. Decided with the user in one
discussion session; built on branch `claude/visual-critic-redesign-97a35e`.

## Why

- The critic ran on `gpt-4.1` with 800 output tokens and a fixed JSON form: every "good" verdict was 15 tokens.
- It saw ~9 KB of drawn XML the repair could not edit, the whole `<Theme>` dump and raw warning strings; `SLIDE_DENSE`
  reached it as text and nothing acted on it. Its checklist was written when the LLM drew every node by hand.
- From 2026-10-14 to 2026-11-20 the critic never ran at all (`critic_schema` lacked `Literal`, fixed in f28d3fa).
- The deck assembler normalized and fit-grew every slide a second time: that would undo the visual fixer's values, and
  a whole-deck `<!-- fit-grow: off -->` would have switched fit-grow off for every slide. (Correction 2026-11-25: the
  "1 of 11 slides came out different" first given here compared an un-normalized slide; normalized, 0 of 11 differ.)

Research the decisions rest on: Set-of-Mark prompting (arXiv 2310.11441: marks the model can name beat raw
coordinates); EditPPT (2608.20381: a vision validator names the defect and the shapes, repairs as tool calls);
UICrit / AutoPresent (measured geometry belongs to code, judgement to the VLM); CODESTRUCT (2604.05407) and the
deterministic GitOps edits (2609.00227: the model proposes, code applies); Diff-XYZ (2510.12487) and Aider's edit
formats (search/replace best for strong models); Claude Code `str_replace` and Codex `apply_patch`; Genspark's
`check_slide_layout` loop (measured ERROR rules, one-element edits; its agent once graded itself "0 errors").

## Decisions (user)

| # | Decision |
|---|---|
| 1 | Every component has an id. Code stamps `id="cmp-<component_id>"` on the outer box a ref tag becomes (or keeps the node's own, `tbl-<id>`, `kpig-<id>`, `cardg-<id>`); the generator writes `id="<component_id>"` on a hand-drawn component's box; `NODE_ID_MISSING` (warning) when it does not. |
| 2 | Code first: a defect code measured and could not fix (`SLIDE_DENSE`, a geometry spill / collision / off-slide at tier error, `AUTOFIT_SHRANK`) goes straight to the fixer as a re-layout, with no vision call. |
| 3 | Fixes are search/replace edits `{old, new}`; code applies them (each `old` must match exactly once); a failed match or compile goes back to the model once. A fixed op list was rejected as too limited; a whole-XML rewrite as drift-prone. |
| 4 | Separate critic (fresh eyes, judges per component) and fixer (a reasoning model, writes the edits). |
| 5 | Critic model: gpt-4.1 (cap 800 -> 3000) vs a reasoning model, decided on one paid check. |
| 6 | Critic input: clean + marked screenshot (numbered boxes from geometry.json), the generator's ref-tag XML with one comment per component (`[n] id · kind · variant · w×h · needs ...`), measured facts in plain words, the planner's layout intent and design hints, the theme's colour roles (not the whole theme). A fixed system prompt (the variant catalogue included) for every slide: a cacheable prefix. Checklist: message, hierarchy, visible defects, colour, variant fit, balance, completeness of the hand-drawn parts. Output: observations first, then a verdict per component + one for the slide; "ok" needs evidence; owner `slide` or `code_defect`; `regenerate` only for a wrong plan. The regex that dropped size / empty-space findings is gone. |
| 7 | `code_defect` findings are written to `output/runs/<run_id>/code-defects.jsonl` for a fix in code; the fixer may still work around them. Per-element syntax inside nodes: deferred to its own session (user). |
| 8 | The fixer edits the XML the slide was DRAWN from (`drawn.xml`, after fit-grow), not the ref tags; nothing changes a value after it: compile with `<!-- fit-grow: off -->`, then code checks only. |
| 9 | One fix per slide. Kept only when the code checks pass: compiles; geometry errors, low-contrast texts and POM shrinking no worse than before; no word or number inside a code-drawn component changed; no number that was not on the slide. No critic re-review, no judge call. |
| 10 | The deck is built from each slide as drawn (`slide_router` saves `drawn.xml`; `assemble_deck_xml` combines under one Theme with fit-grow off, no second normalize), critic on or off. The web UI's edited slides (never fitted) keep the old normalize + fit (`drawn=False`). |
| 11 | Variant nudging for the generator / planner: out of scope here (its own session). |

Changed earlier decision: `LOW_CONTRAST` was report-only and never shown to the critic (2026-09-29); it is now a
measured fact the critic judges (checklist: colour, text that does not read on its fill). It never sends a slide
straight to the fixer.

## What runs where

```
generator ref-tag XML (ids on every component)
  -> validator: expand (cmp- ids) -> normalize -> palette / readable passes -> compile (fit-grow ONCE) -> audits
       writes drawn.xml, geometry.json; component_boxes / component_variants in normalize_result
  -> critic: slide_facts (components, boxes, marks, facts)
       measured defect  -> strategy relayout (no vision call)
       else vision      -> verdicts -> strategy fix | regenerate | none
  -> visual_repairer (once): edits on drawn.xml, compile with fit-grow off, code checks -> kept or slide as it was
  -> slide_router saves drawn.xml -> deck_assembler compiles the slides as drawn (fit-grow off)
```

POM's own autoFit still shrinks a slide taller than the page; compile now reports it (`AUTOFIT_SHRANK`, a geometry
pass with and without autoFit) and a fix that triggers it is rolled back.

## Files

`src/agents/slide_facts.py` (new), `critic.py`, `visual_critic.py`, `critic_schema.py`, `visual_repairer.py`,
`prompts/visual_critic/*.j2`, `prompts/generator/user.j2` (hand-drawn id line), `compiler/nodes/compose.py`
(`stamp`), `tile_groups.py`, `composed.py` (`unmarked`), `validator.py`, `deck_nodes.py`, `compiler_client.py`
(`drawn_xml`), `node/compile-pom.js` (`drawn.xml`, `AUTOFIT_SHRANK`), `node/fit-grow.js` (`SLIDE_DENSE` spills
carry their ids), `graph.py` (one fix, then done), `models.yaml`, `scripts/critic_check.py`.

## Checks

- Stamping ids changes no fitted slide (8 fixture slides, with / without the stamp).
- Deck as drawn: every deck slide's geometry and XML equal the slide compiled alone (11 fixture slides, 2 decks).
- Paid re-run of the six 4 Nov failures (`nodes-b6`, 2026-11-25, $0.154): 6/6 compiled, 5/6 first try, 0 placeholders,
  0 plan words lost; hand-drawn ids 0/12 because `id` was not an allowed attribute (fixed after it).
- `python -m scripts.critic_check`: free steps 2, 4-8 pass on the build PC; 1 and 3 need PowerPoint (test PC).

## Open

- The paid check: `deck-overflow-repair` with the critic on gpt-4.1 and on gpt-6.1-sol.
- The user's blind marks / GEOM calibration (`docs/eval/audit-calibration/`) against the new critic's verdicts.
- The slide editor (`slide_edit_service`) still uses its own patch loop with the new critic's output.
