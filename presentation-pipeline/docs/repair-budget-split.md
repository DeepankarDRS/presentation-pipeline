# Repair Budget Split: Compile vs Visual Critic

## Problem

The original repair loop used a single shared `retry_budget=3` for both
compile failures and visual critic failures. This caused two issues:

### 1. Unpredictable cost from ping-pong

Compile repairs and visual critic repairs interleaved in a single loop.
A visual repair could break compilation, triggering compile repairs,
which might then fail the critic again:

```
generator → compile OK → critic FAIL
  → repairer(1) PATCH  → compile FAIL  (visual fix broke XML)
  → repairer(2) REGEN  → compile OK    → critic FAIL
  → repairer(3) PATCH  → budget gone   → ships with issues
```

The critic ran twice, the repairer ran three times, and the result
could be worse than the original compiled output.

### 2. Visual repair could downgrade a working slide to placeholder

Worst case: a slide compiles fine but has visual issues. The visual
repair breaks compilation. The compile repair loop can't fix it.
The route sends to `placeholder_node`:

```
generator → compile OK → critic FAIL
  → visual repair → compile FAIL
    → compile repairer(1) → compile FAIL
    → compile repairer(2) → compile FAIL
    → compile repairer(3) → budget gone → PLACEHOLDER
```

A **working slide** (just visually imperfect) became a
**"Slide could not be generated"** fallback.

## Solution: Separate Budgets with Safe Discard

Two independent budgets, run as sequential phases:

```
retry_budget: int = 3          # compile repair attempts (unchanged)
visual_repair_budget: int = 1  # visual critic repair attempts (new)
```

## Full Flow

```
generator → validator
  ├─ compile FAIL & retryable?
  │    → repairer → validator  (loop, up to retry_budget=3)
  │    │   attempt 1: PATCH (unless visual_layout_broken → REGENERATE)
  │    │   attempt 2: REGENERATE (if stall/noop/structural) or PATCH (if prev was REGEN)
  │    │   attempt 3: same logic
  │    exhausted or stall? → placeholder_node → evaluator
  │
  ├─ compile FAIL & non-retryable? → placeholder_node → evaluator
  │
  ├─ compile OK & critic_mode="off"? → evaluator
  │
  └─ compile OK & critic_mode="auto"?
       → critic_node (visual critic: screenshot + vision LLM)
         │
         ├─ passed (no high-severity issues)? → evaluator
         │
         └─ failed (high-severity issues)?
              │
              ├─ visual_repair_count < visual_repair_budget?
              │    → visual_repairer_node
              │    │   reads repair_hints.strategy from critic:
              │    │     "patch"      → PATCH (1 LLM call)
              │    │     "regenerate" → REGENERATE (replan + generate, 3 LLM calls)
              │    │
              │    │   compile-checks the result:
              │    │     compile OK?   → accept repaired XML
              │    │     compile FAIL? → DISCARD repair, keep original XML
              │    │
              │    └─ → evaluator (done — no re-critic, no compile loop)
              │
              └─ visual_repair_count >= visual_repair_budget?
                   → evaluator (ships as-is, visual issues are advisory)
```

## Strategy Decision: Compile Repairer

The main repairer (`src/agents/repairer.py`) picks PATCH or REGENERATE
via `_choose_strategy()`:

| Condition | Strategy |
|---|---|
| attempt 1, no layout broken | PATCH |
| attempt 1, visual_layout_broken | REGENERATE |
| previous was REGENERATE | PATCH (cleanup pass) |
| stall / noop / truncated / structural error | REGENERATE |
| attempt >= 2 and compile still failing | REGENERATE |
| otherwise | PATCH |

REGENERATE replans the slide via `plan_single_slide` with error context
(failed component kinds, error messages), rebuilds the contract via
`build_contract`, and calls the generator LLM fresh. On failure, falls
back to PATCH.

## Strategy Decision: Visual Repairer

The visual repairer (`src/agents/visual_repairer.py`) respects the
critic's `repair_hints.strategy` directly:

| Critic says | Visual repairer does |
|---|---|
| `strategy="patch"`, `assessment="needs_tuning"` | PATCH — in-place fix for font/spacing/color issues |
| `strategy="regenerate"`, `assessment="layout_broken"` | REGENERATE — replan + generate from scratch |
| `strategy="none"`, `assessment="good"` | Not reached (critic passed) |

On any failure (LLM error, truncation, noop, compile break), the repair
is discarded and the original compiled XML is kept.

## Safety Rules

1. **Visual repairs never re-enter the compile repair loop.** After
   `visual_repairer_node`, the flow goes directly to evaluator (or
   slide_router in multi-slide mode). Never back to validator → repairer.

2. **Discard on compile failure.** If the visual repair breaks
   compilation, the original compiled XML is kept. The `pptx_path` from
   the original compile is preserved.

3. **No re-critic.** After a visual repair attempt (success or discard),
   the critic does not re-run. One shot, take or leave.

4. **Budgets are independent.** Compile repairs consuming `retry_budget`
   do not affect `visual_repair_budget` and vice versa.

## Cost Analysis

| Scenario | LLM Calls |
|---|---|
| **Best**: compile OK, critic passes | 1 generator + 1 visual critic = **2** |
| Compile OK, critic PATCH fix works | 1 gen + 1 vc + 1 patch = **3** |
| Compile OK, critic REGENERATE fix works | 1 gen + 1 vc + 1 replan + 1 gen = **4** |
| Compile needs 2 fixes, critic passes | 1 gen + 2 repair + 1 vc = **4** |
| Compile needs 2 fixes, critic PATCH fix | 1 gen + 2 repair + 1 vc + 1 patch = **5** |
| **Worst**: compile 3 fixes, critic REGEN | 1 gen + 3 repair + 1 vc + 1 replan + 1 gen = **7** |
| Visual repair breaks compile | Same as without repair (discard) |
| Compile never succeeds | 1 gen + 3 repair → placeholder, **no critic** = **4** |

Hard ceiling: **7 LLM calls** (was 10-13 with shared budget).

## Configuration

| Setting | Default | Effect |
|---|---|---|
| `retry_budget=3` | 3 | Compile repair attempts (PATCH → REGENERATE → PATCH) |
| `visual_repair_budget=1` | 1 | Visual critic repair attempts |
| `visual_repair_budget=0` | — | Critic is advisory only (report, no repair) |
| `visual_repair_budget=2` | — | Two visual repair attempts (experimental) |
| `critic_mode="auto"` | `"off"` | Must be `"auto"` to enable visual critic |

Both budgets are set in `initial_state()` and passed through the API.

## Files

| File | Change |
|---|---|
| `src/state.py` | Added `visual_repair_budget` (default 1) and `visual_repair_count` fields |
| `src/agents/visual_repairer.py` | **New.** One-shot PATCH or REGENERATE node with compile-check and discard-on-fail |
| `src/agents/validator.py` | Added `normalize_and_compile()` helper for quick compile verification |
| `src/graph.py` | Added `visual_repairer_node`, `route_after_critic` routes to it instead of main repairer |
| `src/agents/slide_edit_service.py` | Threaded `visual_issues` through `_call_repair_llm` → `build_patch_prompts` |
| `tests/unit/test_graph.py` | Updated routing tests for split-budget behavior |
