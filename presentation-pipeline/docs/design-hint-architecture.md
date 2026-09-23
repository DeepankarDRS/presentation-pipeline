# Design hints, nesting and icons — how invalid node combinations are prevented

Implemented 2026-09-23. Replaces `docs/nesting-enforcement-plan.md`.

## Principle

Core nodes (`Table/Col/Tr/Td`, `Ul/Ol/Li`, `Text`, `Chart`, `Timeline`, `Flow`, `Tree`, `Matrix`, `ProcessArrow`, `Pyramid` and their items) have **fixed syntax** — never extend or bend them. Richer visuals are **derived components composed around core nodes** with `VStack`/`HStack`: cards, KPI tiles, icon + text rows, a card header with an icon. A table stays a table; if per-row icons are the point, the planner picks a kind that supports them (`bullet_list` → icon rows, `kpi_row` → icon tiles).

## The bug this fixes

A table row got `<Td><HStack><Icon/><Text/></HStack></Td>`. POM rejected the whole table with a misleading `<Table>: Missing required attribute "rows"`, so the repairer chased the wrong error. (An Icon inside `<Li>` is worse: it compiles and POM silently drops the icon.)

Root cause, three layers that lined up:
1. **Planner** (`slide_component_planner/system.j2`, `planner_schema.py`): design_hint was mandatory and had to be "distinctive", while the only enrichment it was taught was icons/sparklines "using nested VStack/HStack" — for *any* component, including tables and lists. The JSON-schema description sent to OpenAI said the same. Saved runs showed 45% of `bullet_list` hints asking for icons/dots/arrows.
2. **Generator** (`generator/system.j2`): "Translate it into POM attributes — do not ignore it" plus an unscoped recipe `<HStack><Icon/><Text/></HStack>` "per item" — so "row icons" was applied inside `<Td>`.
3. **Validation**: `nodes.yaml` already defined allowed children per node, but only `Li` was checked (hardcoded copy, after compile).

## Layers (defense in depth)

| Layer | File | What it does |
|---|---|---|
| Rules as data | `knowledge/core/nodes.yaml` (`children:`) | Only authority on nesting |
| | `knowledge/core/hint-capabilities.yaml` | Treatments each component kind may receive (+ `never:`) and the POM technique for each |
| | `knowledge/core/icon-names.txt` | Exact POM icon set (generated) |
| | `knowledge/components/icon.yaml` `recommended_names` | Curated vocabulary shown to the generator |
| Planner | `agents/hint_capabilities.py` → `slide_component_planner/system.j2`, `planner_schema.py` | Hints chosen only from the kind's treatments; no logos; pick another kind if icons are essential |
| Generator | `context_builder.py` → `generator/system.j2` (techniques for THIS slide's kinds + icon names), `generator/user.j2` (`scope:` line per component) | Builds intents at the right place; out-of-scope intents skipped |
| Auto-fix (no LLM) | `compiler/content_model.py::flatten_text_containers`, `compiler/icons.py::fix_icon_names` via `normalizer.normalize_xml` | Td/Li with Icon+Text → plain text; icon name respelled to exact slug, else the Icon is removed (no fuzzy guessing) |
| Hard stop | `content_model.find_violations` (in `normalize_xml`) + `nesting_compile_failure` in `validator_node`, `normalize_and_compile`, `slide_edit_service` | Any remaining bad pair → `INVALID_CHILD`, compiler skipped, precise `NESTING FIX` guidance; repair policy unchanged (PATCH first) |

Icon errors and the common Td/Li slip never cost a retry. Other nesting errors cost one PATCH with an accurate message instead of a misleading one.

## Prompt budget (long-run rule)

Guidance scales with the slide, not with the catalogue: the generator sees techniques only for the component kinds on the slide, and each component gets a one-line `scope:` in the user prompt. Duplicate static text was removed to pay for it. Generator system prompt (chars/4): few 7919→7738, standard 8960→8811, many 11802→11850 — all within the test budgets (8000/9000/12000), none raised. Planner system prompt 6394→6985 (no budget test).

## How to extend

- **New POM node / nesting rule**: add `children:` in `nodes.yaml` + a case in `tests/unit/test_content_model.py`. No code change.
- **New visual treatment**: add it under `treatments:` in `hint-capabilities.yaml` and list it on the kinds that support it. Tests check every kind is covered, no dead treatments, and that technique snippets are validly nested.
- **New component kind**: add to `planner_schema.ComponentKindLiteral` **and** `hint-capabilities.yaml` `kinds:` (test enforces).
- **POM upgrade**: `python -m scripts.export_icon_names` (a test fails until the list matches the installed POM).

## Tests

`tests/unit/test_content_model.py`, `test_icons.py`, `test_hint_capabilities.py`, plus `test_repairer.py::test_invalid_child_guidance_and_signature` and `scripts/verify_li_nesting.py` (compiles the Li case with the real compiler).
