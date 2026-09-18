# Repair Budget Split: Compile vs Visual Critic

## Problem

The current repair loop uses a single shared `retry_budget=3` for both
compile failures and visual critic failures. This creates two issues:

### 1. Unpredictable cost from ping-pong

Compile repairs and visual critic repairs interleave in a single loop.
A visual repair can break compilation, which triggers compile repairs,
which may then fail the critic again:

```
generator -> compile OK -> critic FAIL
  -> repairer(1) PATCH  -> compile FAIL  (visual fix broke XML)
  -> repairer(2) REGEN  -> compile OK    -> critic FAIL
  -> repairer(3) PATCH  -> budget gone   -> ships with issues
```

The critic ran twice, the repairer ran three times, and the result may
be worse than the original compiled output.

### 2. Visual repair can downgrade a working slide to placeholder

The worst-case scenario: we start with a slide that compiles fine but
has visual issues. The visual repair breaks compilation. The compile
repair loop can't fix it. The route sends us to `placeholder_node`:

```
generator -> compile OK -> critic FAIL
  -> visual repair -> compile FAIL
    -> compile repairer(1) -> compile FAIL
    -> compile repairer(2) -> compile FAIL
    -> compile repairer(3) -> budget gone -> PLACEHOLDER
```

We went from a **working slide** (just visually imperfect) to a
**"Slide could not be generated"** fallback. That's strictly worse.

## Solution: Separate Budgets with Safe Discard

Split into two independent budgets and run them as sequential phases:

```
retry_budget: int = 3          # compile repair attempts
visual_repair_budget: int = 1  # visual critic repair attempts (new)
```

### Phase 1: Compile Loop (existing, unchanged)

```
generator -> validator
  compile FAIL & retryable? -> repairer -> validator (loop, up to retry_budget)
  compile FAIL & exhausted? -> placeholder_node -> done
  compile OK? -> Phase 2
```

### Phase 2: Visual Critic (new safe behavior)

```
compile OK -> critic
  critic PASS? -> done
  critic FAIL & visual_repair_budget > 0?
    -> visual repairer (PATCH only, using critic's repair_hints)
    -> validator
      compile OK?  -> accept repaired XML -> done (skip re-critic)
      compile FAIL? -> DISCARD repair, keep pre-repair XML -> done
  critic FAIL & visual_repair_budget == 0? -> done (advisory only)
```

Key safety rule: **if a visual repair breaks compilation, discard it
and keep the original compiled XML.** Never re-enter the compile repair
loop from a visual repair failure.

### Why skip re-running the critic after visual repair?

Running the critic again after a visual repair could trigger another
repair attempt, creating a mini ping-pong. With `visual_repair_budget=1`
(the default), we take one shot and accept the result. The visual repair
had the critic's `repair_hints` (strategy, affected_nodes, fix
descriptions) — if one targeted fix can't solve it, more attempts
rarely help.

## Cost Comparison

| Scenario                          | Current (shared=3) | Split (compile=3, visual=1) |
|-----------------------------------|--------------------|-----------------------------|
| Best: compile OK, critic OK      | 2 calls            | 2 calls                     |
| Compile OK, critic fix in 1      | 4 calls            | 4 calls                     |
| Compile needs 2, critic OK       | 5 calls            | 5 calls                     |
| Compile needs 2, critic needs 1  | 7-9 (ping-pong)    | 7 (capped)                  |
| Worst case                       | 10-13              | 10 (hard ceiling)           |
| Visual repair breaks compile     | placeholder risk   | safe discard                |

## Configuration

- `visual_repair_budget=1` (default): one repair attempt after critic
- `visual_repair_budget=0`: critic is advisory only (report issues, no repair)
- `visual_repair_budget=2`: two attempts (for experimentation)

The budget is exposed in `initial_state()` and the API layer, same as
`retry_budget`.

## Files Changed

- `src/state.py` — add `visual_repair_budget` field
- `src/graph.py` — new `visual_repair_node`, updated routing
- `src/agents/visual_repairer.py` — new node: runs PATCH, validates, discards on failure
- `src/graph.py` — `route_after_critic` routes to visual_repairer instead of repairer
