# Group Composition (`66dc5e9`) — Post-Mortem

**Branch:** `group-composition`  
**Commit:** `66dc5e9`  
**Status:** Reverted from `master` — changes made output worse, not better  
**Date:** 2026-09-15  

---

## What was added

~318 lines across 12 files:

- 5 new component kinds: `icon`, `badge`, `eyebrow`, `cta`, `group`
- Recursive `children` field on `PlannerComponent` / `ComponentPlan` for single-level composition
- `_convert_component` helper in `slide_component_planner` for recursive Pydantic-to-TypedDict conversion
- `_collect_kinds` tree-walker in `context_builder` so components inside groups are visible for node/recipe/note selection
- Group rendering grammar in `house-style.yaml` (intent-to-styling map: card, dark panel, accent card, metric strip, etc.)
- `design_variety` rule to prevent repetitive visual patterns
- Strengthened `color_discipline` for cover slides
- `icon_bullet_list` and `badge` recipes in `recipes.yaml`
- Icon-in-Li pitfall note in `list.yaml`
- Job 3 (composition judgment) in `slide_component_planner/system.j2`
- Outline planner decoupled from component types (information shapes instead of concrete kinds)
- Generator `user.j2` updated for two-level group/leaf rendering

## What went wrong

**The prompt got bigger but the LLM didn't use any of it.** Zero groups appeared across 8 slides of output. The same problems (overlap, overflow, Layer misuse, long labels) persisted or worsened.

### 1. Prompt dilution

The system prompt for the slide component planner grew significantly with Job 3 (composition judgment), new kind definitions, and `design_hint` vocabulary. The LLM has a fixed attention budget — more instructions means less adherence to each one.

The existing rules that **were** working (height budgets, color discipline, component sizing) got less attention because they were now competing with group composition rules the LLM didn't understand well enough to apply.

**Evidence:** The output slides(2).txt shows the same defects as pre-commit output — Layer abuse on Slide 0, ProcessArrow with 7 steps on Slide 6, multi-word Matrix labels on Slide 2 — plus no adoption of the new composition features. The added prompt weight was pure overhead.

### 2. The outline planner rewording backfired

Changing concrete component arrows to abstract information shapes:

| Before | After |
|--------|-------|
| `-> chart` | `-> temporal/comparative data` |
| `-> KPI tile` | `-> quantitative emphasis` |
| `-> table` | `-> structured multi-attribute data` |
| `-> narrative or bullet` | `-> explanatory prose` |
| `-> flow/timeline` | `-> ordered sequence` |

The intent was to decouple the outline planner from downstream component selection. But it made the outline vaguer, giving the slide component planner less signal to work with. The planner LLM performs better with concrete component vocabulary than with abstract information-shape language.

### 3. No few-shot examples

The group rendering grammar described **rules** for how to render groups (intent-to-styling map, height budget for groups, children rendering) but never showed a complete input-to-output example.

LLMs learn patterns better from examples than from rules. The grammar was comprehensive but abstract — the generator had no concrete model to pattern-match against.

## Lessons for future attempts

1. **Validate one change at a time.** Run the pipeline with the change, compare output A/B, confirm the LLM actually adopts the new behavior before adding more.
2. **Prompt budget is finite.** Every line added to a system prompt competes with every other line. New features must earn their token cost by producing measurably better output.
3. **Few-shot > rules.** If the LLM needs to produce a new structural pattern (like groups), show it a complete example, not just the grammar.
4. **Don't abstract away useful signal.** The outline planner's concrete component names ("chart", "KPI tile") were load-bearing — the downstream planner depended on them. Replacing them with vague "information shapes" broke that dependency chain.
5. **Measure adoption, not just correctness.** The group system was architecturally sound, but "architecturally sound and never used" is worse than "simple and always used."
