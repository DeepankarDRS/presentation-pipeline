# Presentation Pipeline — In-Depth Flow & Critical Review

> Companion to [`CODE_FLOW.md`](CODE_FLOW.md). Hand-traced from source 2026-09-05.
> Part 1 explains the flow and the design problems it *solves*.
> Part 2 is an adversarial review — bugs, gaps, and design smells, ranked.

---

# PART 1 — The flow, and what it solves

## 1.1 The core problem

Turn a natural-language request into a valid PowerPoint. The hard part is not the
PPTX — the Node `@hirokisakabe/pom` compiler does that — it's getting an LLM to
emit **valid POM XML**: correct tag casing, no HTML contamination, allowed
attributes per node, positive dimensions, theme tokens instead of raw hex, content
that fits a 1280×720 slide. LLMs fail all of these routinely.

The pipeline is essentially a **generate → mechanically verify → repair loop**
wrapped around that compiler, with an LLM planner in front and an LLM critic and a
mechanical scorer behind.

## 1.2 The eleven nodes and why each exists

| Node | LLM | Solves |
|---|---|---|
| `questionnaire` | – | Interactive-only. Collects audience/density/theme/slide-count so the planner isn't guessing. Skipped entirely in API/batch mode. |
| `planner` | ✅ structured | Decomposes the request into a **component list + density + layout hint** per slide. Deliberately *not* archetype-based — the generator keeps creative freedom. Produces `core_hook` (narrative anchor) and `content_data_json` (invented-or-supplied values). |
| `style_resolver` | – | Turns a palette name into a literal `<Theme>` element + chart color list. Runs **once**; decoupled so any node can call `resolve_theme()`. |
| `context_builder` | – | The "contract" builder. From the component kinds it selects **only** the POM nodes, per-node attribute whitelists, forbidden lists, pitfalls/notes, one compressed example, and a layout skeleton relevant to this slide. This is the token-budget lever (minimal / standard / dense tiers). |
| `generator` | ✅ free text | Renders tiered Jinja prompts from the contract + plan + data, calls the LLM, stores raw XML. |
| `validator` | – | Ground truth. `normalize_xml` (strip fences, `#`-hex, `<br>/<hr>`, `spacing→gap`, `fontWeight→bold`, flag zero dims, extract `<Notes>`) → `parseXml` (fast structural check) → `buildPptx` (real compile). Also runs `audit_layout` (mechanical spatial checks). Never parses Node stderr — reads `compile-result.json`. |
| `repairer` | ✅ free text | Two strategies: **PATCH** (feed back failing XML + targeted guidance, fix in place) and **REGENERATE** (rebuild from the plan, seeded with a verified skeleton when one fits). Routed by error class (`needs_regeneration`), stall (≥65% error-signature overlap), and attempt number. Loops back to `validator`, not `generator`. |
| `critic` | ✅ structured | Post-compile quality gate for what the compiler can't see: component completeness vs plan, supplied-value fidelity, structural sanity, slide-type coherence, theme adherence. `auto` = high-severity issue → fail → repair. `manual` = human A/R/E checkpoint. `off` = skip. |
| `slide_router` | – | Deck-only. Saves the slide's **normalized** XML (`normalize_result.cleaned_xml`) into `completed_slides`, bumps `current_slide_index`, **resets every per-slide key** (xml, results, retry counters) for the next iteration. |
| `deck_assembler` | – | Deck-only. `assemble_deck_xml()` regex-extracts every `<Slide>` block, re-normalizes + puts one `<Theme>` back, runs **one final compile** with a bounded (2×) repair loop. |
| `evaluator` | – | Mechanical scoring. `passed = compile_ok AND critic_ok`. Sums tokens/cost from `generation_history`, writes `run-manifest.json`. Terminal node. |

## 1.3 State discipline

`PresentationState` is one flat `TypedDict` ([`state.py:81`](src/state.py)). Nodes
return **partial dicts**; LangGraph merges. Only two keys accumulate
(`operator.add`): `generation_history` and `completed_slides`. Everything else is
last-write-wins. This is clean and is the pipeline's best structural decision — you
can read any node in isolation and know exactly what it touches (see the index
table in `CODE_FLOW.md §6`).

## 1.4 Cases the pipeline genuinely handles well

1. **Markdown fences / `#` hex / `spacing` / `fontWeight` / zero gaps** — auto-fixed
   silently in `normalize_xml`, no retry cost. ([`normalizer.py:101-150`](src/compiler/normalizer.py))
2. **HTML contamination that POM silently swallows** (`<div>`, `</br>` inside
   `<Text>`) — the memory notes confirm POM *drops these without erroring*, so a
   contaminated slide would "compile" wrong. `pre_validate` + normalizer catch it
   before the compile. This is the single most important thing the pipeline does.
3. **Miscased tags** (`<slide>` vs `<Slide>`) — `MISCASED_TAG`, blocking, with a
   targeted "POM is case-sensitive" repair hint.
4. **Contract-aware unknown attributes** — `pre_validate(xml, contract)` checks
   every `<Node attr>` against the per-node whitelist *before* wasting a compile,
   feeding node+attr into the repair prompt.
5. **Retryable vs non-retryable compile errors** —
   [`compiler_client.py:36-42`](src/compiler/compiler_client.py) only loops on
   `{UNKNOWN_TAG, UNKNOWN_ATTRIBUTE, PARSE_ERROR, INVALID_VALUE, INVALID_CHILD,
   THEME_ERROR, DIAGNOSTIC}`; a harness/timeout error sets `retryable=False` so the
   loop doesn't burn budget on something it can't fix.
6. **Stall / structural / attempt ≥ 3 → REGENERATE** — otherwise PATCH in place;
   the pass after a REGENERATE is a PATCH cleanup.
7. **Dark-theme chart axis bug** — POM v10.3.0 hardcodes chart axis text to black;
   `context_builder` injects a "wrap `<Chart>` in `$chartSurface` VStack" note only
   for dark palettes. ([`context_builder.py:288-293`](src/agents/context_builder.py))
8. **Unstyled table cells** — POM emits no fill so PowerPoint's white default takes
   over; contract forces explicit `backgroundColor`+`color` on every `<Td>`.
9. **Token budget** — tiered prompt assembly keeps maximal-density under the ~6K
   target vs the ~12.5K full-KB baseline (memory: baseline removed after it
   hallucinated attributes).
10. **Fail-open critic** — a critic LLM exception returns `[]` (slide passes) rather
    than dead-ending the run. Reasonable for a quality gate; risky as a guarantee
    (Part 2 #6).

---

# PART 2 — Critical review

Ranked. Severity = impact × likelihood.

## 🔴 High

### 1. Deck mode silently ignores the critic in the final verdict
Per-slide flow is `critic_node` (writes `critic_result`) → `route_after_critic` →
`slide_router`, and `slide_router` **resets `critic_result` to `None`**
([`deck_nodes.py:45`](src/agents/deck_nodes.py)). After the loop, `deck_assembler`
never sets it. So in `evaluator`:
```python
critic_ok = critic_result.get("passed", True)   # → True, always, in deck mode
passed = compile_ok and critic_ok
```
A 10-slide deck where slide 4's critic failed and repair exhausted its budget still
reports `passed=True` as long as the final assembly compiles. **The critic is
effectively disabled for decks.** Fix: accumulate per-slide critic results (e.g.
into `completed_slides`) and have `evaluator` AND them.

### 2. The assembled deck gets weaker validation and repair than a single slide — PARTLY ADDRESSED
`slide_router` now persists each slide's *normalized* XML (`normalize_result.cleaned_xml`),
and `assemble_deck_xml()` re-runs `normalize_xml` + `ensure_single_theme` on the combined
document — so per-slide auto-fixes (br/hr, `#`-hex, `spacing=`, `fontWeight=`) no longer
resurface at the deck compile. The deck repair loop also now uses the real
`build_patch_prompts` (contract + knowledge) instead of a one-line prompt.
Still open: no `route_after_deck_assembler` graph loop, `MAX_DECK_REPAIR_ATTEMPTS = 2`
vs. a single slide's `retry_budget = 4`, and structural/cross-slide issues (conflicting
ids, etc.) still only get the inline loop.

_Original finding:_ `deck_assembler` regex-extracted `<Slide>` blocks, concatenated, and
called `compile_xml` once with a one-line repair fallback and no normalization.

### 3. Stall detection compares mismatched signature namespaces — RESOLVED
Fixed: `AttemptRecord` now persists `error_sigs` (canonical `error_signatures()`
output) and `repairer` compares that directly instead of round-tripping through
display strings.

_Original finding:_
`repairer` builds `curr_sigs` from live `pre_issues` + `compile_diags` via
`error_signatures()` — compile diagnostics become `"COMPILE:<type>:<msg[:40]>"`.
But `prev_sigs` is reconstructed from `generation_history[].errors_in`, which
`_collect_problems` stored as `"<type>: <message>"` strings, then re-parsed as
`{"code": e.split(":")[0], "message": e}` and passed to `error_signatures` **as
`pre_issues`** ([`repairer.py:174-177`](src/agents/repairer.py)). So a compile
error that recurs identically produces `COMPILE:UNKNOWN_TAG:...` this round and
`UNKNOWN_TAG:div` (or a `:msg[:40]` fallback) from last round — **they never
match**, overlap ratio stays low, `is_stalled` returns `False`. Consequence: tier
rarely escalates on real compile-error stalls; the pipeline PATCH-loops 3× and
gives up. Fix: persist the structured `pre_issues`/`compile_diags` (or their
signatures) on the `AttemptRecord`, don't round-trip through display strings.

### 4. "Escalating" retry doesn't escalate by attempt — RESOLVED
Fixed: the 3-tier ladder was replaced with two strategies (PATCH / REGENERATE).
`_choose_strategy` routes by error class (`needs_regeneration` → structural /
post-autoFit overflow), stall, and attempt number — attempt 1 is always PATCH,
attempt ≥ 3 (or a structural error, or a stall) is REGENERATE, and the pass right
after a REGENERATE is a PATCH cleanup. `retry_budget` bumped 3 → 4 so that
cleanup pass fits.

_Original finding:_ `retry_tier` only advanced on `is_stalled`; otherwise pinned
at PATCH, so SIMPLIFY/TEMPLATE were near-dead code.

### 5. Speaker notes are captured and then thrown away
`normalize_xml` extracts `<Notes>` into `speaker_notes` **and strips it from the
XML that gets compiled** ([`normalizer.py:162-165`](src/compiler/normalizer.py)).
`validator` returns it to state (happy path only — not on the parse-fail/fallback
returns). `slide_router` copies it into `completed_slides[].speaker_notes`. Then:
`deck_assembler` never re-injects it, single-slide mode never surfaces it, and
`evaluator`/the manifest don't mention it. **Net result: speaker notes requested by
the user never reach the .pptx.** Either keep `<Notes>` in the compiled XML (if POM
supports it) or re-inject per slide during assembly.

## 🟠 Medium

### 6. Critic is fail-open on a fragile path
`_run_ai_check` returns `[]` on *any* exception ([`critic.py:77-79`](src/agents/critic.py)),
and it uses `with_structured_output(CriticOutput, method="json_schema")` which
raises on malformed output. A model that consistently trips the schema parser makes
the critic a silent no-op — `passed` degrades to "did it compile". At minimum log
this at `error` with a run-level counter and surface "critic degraded" in the
manifest.

### 7. Planner's layout-variety work is discarded before generation
`planner._enforce_layout_variety` swaps `layout_pattern` on adjacent duplicate
slides ([`planner.py:111-130`](src/agents/planner.py)). But `context_builder.build_contract`
**recomputes `layout_pattern` from component kinds** via `_select_layout` and puts
*that* in the contract ([`context_builder.py:435`](src/agents/context_builder.py)).
The generator's system prompt gets the recomputed one; the plan's
`layout_pattern` reaches the generator only indirectly through the freeform
`layout_hint`. So two adjacent chart-slides still get the same layout skeleton.
Variety enforcement is mostly theatre.

### 8. `state["mode"]` is dead state
Set by `planner` and `initial_state`, **read nowhere** (grep-confirmed). All
routing keys off `len(slide_plans)`. That means: if `deck_min_threshold=0` but the
planner returns 4 slides, `mode="single"` yet the run goes through the full
`slide_router`/`deck_assembler` loop anyway. `mode` is misleading — either wire it
into `_slide_done_target`/`route_after_slide_router` or delete it.

> **Partly addressed (2026-09-06):** `planner_node` now sets
> `mode = "deck" if len(slide_plans) > 1 else "single"`, so `mode` tracks the same
> predicate the routing uses. `deck_min_threshold` was repurposed as the planner's
> *target slide count* (fed into the prompt) and no longer gates `mode`. `mode`/
> `deck_plan` are still not *read* anywhere — deleting them is the remaining cleanup.

### 9. `data_provenance` only exists on the planner path
`_compute_provenance` runs only in `planner._slide_to_state`
([`planner.py:103`](src/agents/planner.py)). The `test_case.components` path
(`route_after_start` → `style_resolver`, plan built later by
`context_builder._build_default_plan`) never sets it, so `evaluator`'s
user/sample tally is `0/0` for those runs and the critic can't check "supplied
values present" against provenance.

### 10. `_build_default_plan` produces an under-specified plan
[`context_builder.py:460-498`](src/agents/context_builder.py) — no `slide_type`, no
`content_data`, `slide_index=0` hardcoded, `count=1` for every component (ignores
"4 KPIs" in the request). The generator then gets `slide_type=""`. The non-planner
path is a second-class citizen.

### 11. API run store is in-process and single-worker
`_runs: dict` ([`api.py:95`](src/api.py)) — no persistence, breaks under
`uvicorn --workers > 1` and across `--reload`. `/generate` runs the entire graph
inside the streaming response via a background thread that **is not cancelled if
the client disconnects** — a closed browser tab leaves the pipeline (and its LLM
spend) running. `_estimate_progress` is magic-number curve-fitting
([`api.py:130-136`](src/api.py)) that can stall at 99% or jump. No auth, no rate
limit.

### 12. Cost/pricing silently returns $0 for unrecognized models
`get_pricing` → `{"input": 0.0, "output": 0.0}` for any model not in
`models.yaml::pricing` ([`llm_client.py:72-76`](src/utils/llm_client.py)). Azure
deployments (whose `model` is a deployment name) won't match `gpt-4.1-mini`, so
Azure runs report `cost=$0` with no warning. `models_used[0]` as "primary model"
is order-dependent on a `set()` → nondeterministic.

### 13. `deck_assembler` theme/slide extraction is regex on untrusted LLM output
`_extract_slide_block` = `<Slide\b[^>]*>.*?</Slide>` with `DOTALL` + non-greedy
([`deck_nodes.py:61`](src/agents/deck_nodes.py)). Fails on: a slide with no closing
tag, `<Slide/>` self-closed, or (non-greedy) stops at the first `</Slide>` which is
fine unless a slide legitimately contains the substring. A dropped slide only logs
a warning — the deck silently ships with fewer slides than planned, and `evaluator`
doesn't compare `len(completed_slides)` to `len(slide_plans)`.

## 🟡 Low / smells

### 14. `validator` returns `speaker_notes` only on the happy path
Lines 76-89 and 95-104 (fallback/parse-fail returns) omit it, so a slide that
needed one repair round loses its notes if the *first* attempt was the one with
`<Notes>`. Minor because the successful pass re-extracts, but inconsistent.

### 15. `generation_history` mixes slides in deck mode
`AttemptRecord.attempt` = `retry_count`, which `slide_router` resets to 0 per
slide, so the manifest's `steps[]` has repeated `attempt=0` rows across slides with
no `slide_index`. The evaluator's "component completion rate" (docstring promise)
isn't actually computed anywhere.

### 16. `layout_issues` feeds only the critic, never the repairer directly — PARTLY ADDRESSED
`validator._promote_severe_layout_warnings` now turns the compiler's own
post-autoFit overflow warnings (`AUTOFIT_OVERFLOW`, `NODE_OUT_OF_BOUNDS`,
`SCALE_BELOW_THRESHOLD`) into a retryable failure, so genuine overflow reaches the
repairer (→ REGENERATE) instead of silently passing. `audit_layout`'s own issues
(`ROOT_SIZE` / `FONT_TOO_SMALL` / `MISSING_DIMS`) are still critic-only.

_Original finding:_ `audit_layout` `severity: high` issues were passed to the
critic prompt as text only, never turned into `problems`.

### 17. `_ZERO_DIM_RE` in normalizer vs memory note
Memory says a bare `<Shape w="0">` "slips through POM silently". Normalizer flags
*all* zero dims as blocking (good) — but it only matches
`w|h|minW|maxW|minH|maxH|fontSize`, not `grow`, and not zero dims written as
`"0.0"` in some locales. Edge.

### 18. No integration test for the deck path
`test_full_pipeline.py` forces `deck_min_threshold=0` everywhere → every case runs
single-slide. The `slide_router → context_builder` loop, `deck_assembler` regex
extraction, and bugs #1/#2/#13 above are **not covered by any integration test**.
`test_deck_nodes.py` tests the nodes in isolation, which is exactly where bug #1
(cross-node state reset) hides.

### 19. `route_after_validator` / `route_after_critic` duplicate the budget logic
Same `budget/count/_slide_done_target` block copy-pasted
([`graph.py:78-85`](src/graph.py) and [`graph.py:100-107`](src/graph.py)). One
helper would remove the risk of them drifting.

### 20. `resolve_theme` special-cases `"corporate-slate"` by string
[`style_resolver.py:64`](src/agents/style_resolver.py) — `if not theme_name or
theme_name == "corporate-slate": return DEFAULT_THEME`. If `palettes.yaml` ever
defines `corporate-slate` with different tokens, the hardcoded `DEFAULT_THEME`
wins and diverges silently.

---

# PART 3 — Recommended priority order

1. **Fix deck-mode critic accounting** (#1) — correctness of the headline `passed` flag.
2. **Add validation + bounded retry after `deck_assembler`** (#2).
3. ~~Fix stall-detection signatures (#3) and decide tier-escalation policy (#4)~~ — DONE (error_sigs persisted; 3 tiers → PATCH/REGENERATE).
4. **Re-inject speaker notes at assembly / keep `<Notes>` through compile** (#5).
5. **Add a real deck integration test** (#18) — it would have caught #1, #2, #13.
6. Then the medium cluster: wire `layout_pattern` through (#7), delete or use `mode` (#8), provenance on all paths (#9), critic-degraded signal (#6).
7. API hardening (#11, #12) before any real multi-user exposure.
