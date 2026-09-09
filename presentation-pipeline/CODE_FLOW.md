# Presentation Pipeline — Line-by-Line Code & State Flow

> Hand-traced from source on 2026-09-05. Traces **which function runs when**, **which file it lives in**, and **exactly which keys of `PresentationState` change** at each step.
>
> Entry points: `src/graph.py::run()` (CLI/library) and `src/api.py::/generate` (HTTP + SSE).
> Single state object: `PresentationState` (TypedDict) defined in [`src/state.py:81`](src/state.py).

---

## 0. The state object

`PresentationState` ([`src/state.py:81-135`](src/state.py)) is a flat `TypedDict`. Every node function receives the **whole** state and returns a **partial dict** of only the keys it owns; LangGraph merges that partial back in. Two keys use `operator.add` reducers so returns are *appended* not *replaced*:

| Key | Reducer | Written by |
|---|---|---|
| `completed_slides` | `operator.add` (list concat) | `slide_router` |
| `generation_history` | `operator.add` (list concat) | `generator`, `repairer` |

Everything else is last-write-wins.

`initial_state()` ([`src/state.py:138-186`](src/state.py)) sets every key to a zero value. Notable initial values:
`mode="single"`, `retry_tier=0`, `retry_count=0`, `retry_budget=4`, `current_slide_index=0`, `passed=False`, `current_xml=""`, all result dicts `None`, all lists `[]`.

---

## 1. Startup

### `run()` — [`src/graph.py:175-214`](src/graph.py)
1. `L188-190` import + `setup_logging()`.
2. `L192` `rid = run_id or uuid.uuid4().hex[:12]` — the run id.
3. `L193` `set_context(run_id=rid)` — binds run id to the logger.
4. `L195-205` `state = initial_state(...)` — **builds the full state** from the call args (`raw_request`, `theme_name`, `deck_min_threshold`, `critic_mode`, `supplied_content`, `test_case`, `audience_context`, `interactive`).
5. `L207` `app = compile_graph()` → `build_graph().compile()` ([`src/graph.py:131-170`](src/graph.py)).
6. `L213` `final = app.invoke(state, config=config)` — runs the graph to completion, returns final state.

### API path — [`src/api.py:212-284`](src/api.py)
- `/generate` (`L212`): make `run_id` (`L215`), register `_runs[run_id] = RunRecord(status="running")` (`L216`).
- `_run_pipeline_sync()` (`L183-203`): builds `initial_state()`, then `graph.stream(state)` — yields `(node_name, state_update)` **per node** instead of one final blob.
- `event_stream()` (`L218-278`): a background thread (`_producer`, `L224`) drains the graph into a `queue`; the async side pulls items, calls `_merge_state(accumulated, state_update)` (`L253` → `L173-178`) to keep a running copy, `_build_event()` (`L260` → `L141-170`) to turn the node name into an SSE event (`planning`/`styling`/`generating_slide`/`validating`/`repairing`/`reviewing`/`assembling`/`complete`), and `_estimate_progress()` (`L258` → `L130-136`) for the % bar.

---

## 2. Graph topology — [`src/graph.py:131-165`](src/graph.py)

```
START
 └─ route_after_start ─────────────► questionnaire | planner | style_resolver
questionnaire ──► planner
planner ──► style_resolver
style_resolver ──► context_builder
context_builder ──► generator
generator ──► validator
validator ─ route_after_validator ─► repairer | critic | evaluator | slide_router
critic ─ route_after_critic ───────► repairer | evaluator | slide_router
repairer ─ route_after_repairer ───► validator            (always)
slide_router ─ route_after_slide_router ─► context_builder | deck_assembler
deck_assembler ──► evaluator
evaluator ──► END
```

Nodes registered `L135-145`; edges `L147-163`.

---

## 3. Routing functions (no state writes — read only)

### `route_after_start` — [`src/graph.py:53-63`](src/graph.py)
- `L55-57` if `state["test_case"]["components"]` present → **`"style_resolver"`** (skip planner entirely; the plan is built later by `context_builder._build_default_plan`).
- `L59-61` elif `state["interactive"]` and no `state["audience_context"]` → **`"questionnaire"`**.
- `L62-63` else → **`"planner"`**.

### `route_after_validator` — [`src/graph.py:74-93`](src/graph.py)
Reads `compile_result`, `retry_budget`, `retry_count`, `critic_mode`, `slide_plans`.
- `L76-77` `cr = compile_result`; if `not cr["ok"] and cr["retryable"]`:
  - `L80-82` if `retry_count < retry_budget` → **`"repairer"`**.
  - `L83-85` else → `_slide_done_target()` = `"slide_router"` if `len(slide_plans) > 1` else `"evaluator"`.
- `L87-88` if `critic_mode == "off"` → `_slide_done_target()`.
- `L92-93` else → **`"critic"`**.

### `route_after_critic` — [`src/graph.py:96-110`](src/graph.py)
Reads `critic_result`, `retry_budget`, `retry_count`.
- `L98-99` `cr = critic_result`; if `not cr["passed"]`:
  - `L101-104` `retry_count < retry_budget` → **`"repairer"`**.
  - `L105-107` else → `_slide_done_target()`.
- `L108-110` else (passed) → `_slide_done_target()`.

### `route_after_repairer` — [`src/graph.py:124-126`](src/graph.py)
Always returns **`"validator"`** (repairer already produced XML, so re-validate directly, skipping generator).

### `route_after_slide_router` — [`src/graph.py:113-121`](src/graph.py)
Reads `current_slide_index`, `slide_plans`.
- `L117-119` `idx < total` → **`"context_builder"`** (next slide).
- `L120-121` else → **`"deck_assembler"`**.

---

## 4. Node-by-node execution & state mutations

### 4.1 `questionnaire_node` — [`src/agents/questionnaire.py:96-147`](src/agents/questionnaire.py)
**Runs only when** `interactive=True` and `audience_context` empty (else `L98-104` return `{}` — no change).
- `L115-116` asks fixed Qs (`audience`, `data_density`) via `_ask()` (`L71-86`, blocking `input()`).
- `L119-126` loads theme names from `knowledge/theme/palettes.yaml` (`_load_palette_names`, `L55-68`), asks "Which theme?".
- `L129-130` asks `slide_count`, `focus`.
- `L132` `threshold = _slide_count_to_threshold(...)` (`L89-93`): `"Single slide" → 0`, else `3`.

**State writes** (`L143-147`):
| key | value |
|---|---|
| `audience_context` | `{audience, data_density, theme, slide_count, focus}` |
| `theme_name` | selected palette name |
| `deck_min_threshold` | target slide count: `1` / `4` / `8` / `12` |

---

### 4.2 `planner_node` — [`src/agents/planner.py:133-185`](src/agents/planner.py)
**Skipped** when `route_after_start` sent flow to `style_resolver`.
- `L137` `system_msg = _render_system()` — renders `prompts/planner/system.j2`.
- `L138` `user_msg = _render_user(state)` (`L39-52`) — injects `raw_request`, `theme_name`, `supplied_content`, `components_hint` (from `test_case`), `audience_context`.
- `L140-141` `llm = get_llm("planner")` ([`src/utils/llm_client.py:40`](src/utils/llm_client.py)), `.with_structured_output(PlannerOutput, method="json_schema")`.
- `L143-146` **LLM CALL** → `PlannerOutput` (pydantic; schema in `src/agents/planner_schema.py`).
- `L148` `core_hook = result.core_hook`.
- `L150-153` `slide_plans = [_slide_to_state(i, s, supplied) for i,s in enumerate(result.slides)]`.
  - `_slide_to_state` (`L67-104`): maps each pydantic slide → `SlidePlan` TypedDict; parses `content_data_json` (`L88-92`, falls back to `{}` on bad JSON); `_compute_provenance` (`L55-64`) tags each `content_data` key `"user"` (in `supplied_content`) or `"sample"`.
- `L155-157` `_enforce_layout_variety(slide_plans)` (`L111-130`) — mutates `layout_pattern` on adjacent content/data slides that repeat a pattern.
- `_render_user` passes `deck_min_threshold` into the planner prompt as `target_slides`; when `> 1` the prompt says "TARGET DECK SIZE: exactly N slides" so the LLM produces that many (an explicit per-slide breakdown in the request still wins).
- decide `mode`: `mode = "deck" if len(slide_plans) > 1 else "single"`, build `DeckPlan` only when `> 1`. (Previously gated on `deck_min_threshold`; now `mode` just tracks the real slide count.)

**State writes** (`L180-185`):
| key | value |
|---|---|
| `mode` | `"single"` \| `"deck"` |
| `core_hook` | narrative anchor string |
| `deck_plan` | `DeckPlan` or `None` |
| `slide_plans` | `list[SlidePlan]` |

---

### 4.3 `style_resolver_node` — [`src/agents/style_resolver.py:90-98`](src/agents/style_resolver.py)
Runs **once** per run (multi-slide loop re-enters at `context_builder`, not here).
- `L92` `theme_name = state["theme_name"]`.
- `L93` `theme = resolve_theme(theme_name)` (`L58-87`):
  - `L64-65` empty or `"corporate-slate"` → `dict(DEFAULT_THEME)` (`L38-48`).
  - `L67-71` else load `knowledge/theme/palettes.yaml`; missing → warn + default.
  - `L73-87` build `<Theme .../>` element string from the 12 `_TOKEN_KEYS`, pull `chartColors`, set `is_dark = mode=="dark"`.

**State writes** (`L95-98`):
| key | value |
|---|---|
| `theme_element` | `"<Theme surface=... />"` string |
| `resolved_theme` | `{name, mode, is_dark, chart_colors, chart_colors_json, element}` |

---

### 4.4 `context_builder_node` — [`src/agents/context_builder.py:501-521`](src/agents/context_builder.py)
Runs once per slide (re-entered per slide in deck mode).
- `L503-504` `slide_plans`, `idx = current_slide_index`.
- `L506-507` if `slide_plans` empty → `slide_plans = [_build_default_plan(state)]` (`L460-498`): source priority **test_case.components → keyword intent detection (`_detect_components_from_text`, `L44-53`) → `["title","narrative","bullet_list"]` fallback**; forces `"title"` first; sets `density`/`font_tier` by component count.
- `L509` `plan = slide_plans[idx]` (or `[0]`).
- `L511-513` `theme_info = state["resolved_theme"] or resolve_theme(state["theme_name"])`.
- `L514` `contract = build_contract(plan, theme_info)` (`L400-457`):
  - `L411` `kinds` = component kinds list.
  - `L414-416` load `core/nodes.yaml`, `core/validation.yaml`, `components/text.yaml`.
  - `L418-422` load per-kind component YAML.
  - `L424` `allowed_nodes = _select_nodes(kinds)` (`L173-200`) — base nodes + per-kind nodes + inline nodes, ordered.
  - `L425` `allowed_attributes = _select_attributes(...)` (`L224-242`) — per-node attr whitelist.
  - `L426-427` `forbidden_tags`, `forbidden_attributes` from validation.yaml (`_clean_list`).
  - `L430` `notes = _select_notes(...)` (`L247-322`) — translations, semantic rules, pitfalls, KPI numeral note, per-component structure+pitfalls, theme note, **chart literal-hex note**, **dark-theme chart-axis wrapper note**, **table Td styling note**, design-language rules.
  - `L432-433` `example = _select_example(kinds, compress)` (`L369-379`) — ≤1 XML example, compressed unless `density=="tight_fit"`.
  - `L435` `layout_pattern = _select_layout(kinds)` (`L327-350`) — picks a `layouts/*.yaml`, renders to text.
  - `L437-442` `density_tier`: `sparse→minimal`, `normal|dense→standard`, else `dense`.

**State writes** (`L521`): **only** `contract` (a dict with `allowed_nodes`, `allowed_attributes`, `forbidden_tags`, `forbidden_attributes`, `theme_element`, `theme_name`, `theme_mode`, `chart_colors`, `notes`, `example`, `layout_pattern`, `density_tier`).

---

### 4.5 `generator_node` — [`src/agents/generator.py:70-106`](src/agents/generator.py)
- `L74` `system_prompt, user_prompt = _render_prompts(state)` (`L32-68`):
  - `L36-37` `plan = slide_plans[current_slide_index]`.
  - `L42-54` **system** = `prompts/generator/system.j2` with `forbidden_*`, `theme_element`, `allowed_nodes`, `allowed_attributes`, `density_tier`, `layout_pattern`, `example`, `notes`, `core_hook`, `slide_type`.
  - `L57-66` **user** = `prompts/generator/user.j2` with `objective` (=`raw_request`), `components`, `density`, `font_tier`, `layout_hint`, `content_data`, `supplied_content`, `slide_type`.
- `L76` `llm = get_llm("generator")`.
- `L82-83` **LLM CALL** → `raw_xml = response.content` (plain text, may have ``` fences — cleaned later by normalizer).
- `L85-88` pull `tokens_in`, `tokens_out`, `model` from `response.response_metadata`.
- `L92-101` build `AttemptRecord` with `attempt=retry_count`, `tier=retry_tier`, empty `errors_in/out`, token counts, model.

**State writes** (`L103-106`):
| key | value | reducer |
|---|---|---|
| `current_xml` | raw LLM XML string | replace |
| `generation_history` | `[record]` | **append** |

---

### 4.6 `validator_node` — [`src/agents/validator.py:31-137`](src/agents/validator.py) — **no LLM**
- `L33-45` if `current_xml` blank → write failing `normalize_result`/`validate_result`/`compile_result` (`retryable=True`), `layout_issues=[]`, return.
- `L47-52` build `output_dir = output/runs/{run_id}/` (+ `retry-{n}/` when `retry_count>0`).
- `L54-56` `norm = normalize_xml(xml)` ([`src/compiler/normalizer.py`](src/compiler/normalizer.py)) → `{cleaned_xml, issues, auto_fixed, blocking, speaker_notes}`. Strips ``` fences, `#RRGGBB`→`RRGGBB`, removes `<br>/<hr>`, flags zero dims, extracts `<Notes>`.
- `L58-62` log normalize issues.
- `L64` `val_result = validate_xml(cleaned, output_dir)` ([`src/compiler/compiler_client.py:97-135`](src/compiler/compiler_client.py)) — runs `node compile-pom.js --validate-only`, reads `compile-result.json`. Returns `None` if Node/compiler unavailable.
- `L66-89` **fallback branch** (`val_result is None`): `pre_validate(xml, contract)` regex check; if `blocking` → return failing results (`retryable=True`).
- `L91-104` **parse-fail branch** (`not val_result["ok"]`): return `validate_result=val_result` + `compile_result` with those diagnostics, `retryable` from `val_result`.
- `L106-119` `compile_result = compile_xml(cleaned, output_dir)` ([`compiler_client.py:52-94`](src/compiler/compiler_client.py)) — writes `input.xml`, runs `node compile-pom.js`, reads `compile-result.json`, `_parse_result` (`L29-49`) sets `ok = status=="success"`, `pptx_path`, and `retryable = any(diag.type in {UNKNOWN_TAG, UNKNOWN_ATTRIBUTE, PARSE_ERROR, INVALID_VALUE, INVALID_CHILD, THEME_ERROR, DIAGNOSTIC})`. `CompilerError` → return `retryable=False` (harness broken, don't loop).
- `L121-123` `layout_issues = audit_layout(cleaned)` ([`src/compiler/layout_audit.py`](src/compiler/layout_audit.py)) — mechanical spatial checks.

**State writes** (`L131-137`, happy path):
| key | value |
|---|---|
| `normalize_result` | `norm` dict |
| `validate_result` | `{ok, diagnostics, warnings}` |
| `compile_result` | `{ok, pptx_path, diagnostics, warnings, retryable}` |
| `speaker_notes` | extracted `<Notes>` text |
| `layout_issues` | `list[dict]` |

---

### 4.7 `repairer_node` — [`src/agents/repairer.py:158-254`](src/agents/repairer.py)
Reached from `route_after_validator` (compile failed + retryable + budget left) **or** `route_after_critic` (critic failed + budget left).
- `L160-161` `current_tier = retry_tier`, `current_count = retry_count`.
- `L162` `problems = _collect_problems(state)` (`L63-82`) — un-auto-fixed normalize issues + compile diagnostics + `CRITIC_<SEV>: msg` lines.
- `L166` `curr_sigs = error_signatures(pre_issues, compile_diags)` ([`src/compiler/repair_guidance.py`](src/compiler/repair_guidance.py)).
- `L168-177` reconstruct `prev_sigs` from the last `generation_history` record that had `errors_in`.
- `L179` `stalled = current_count > 0 and is_stalled(prev_sigs, curr_sigs)` (≥65% signature overlap).
- **strategy choice** (`_choose_strategy`): attempt 1 → PATCH; the pass right after a REGENERATE → PATCH; `needs_regeneration(...)` / `stalled` / attempt ≥ 3 → REGENERATE; else PATCH.
- build the repair user prompt by strategy:
  - **PATCH**: `prompts/repairer/patch.j2` with `objective`, `failing_xml` (from `normalize_result.cleaned_xml`), `problems`, `guidance` (`build_error_guidance`).
  - **REGENERATE**: `prompts/repairer/regenerate.j2` with `previous_user` (original plan), `problems`, `allowed_nodes`, and `template_xml` from `_select_template(state)` (a verified skeleton, or `""` for a free-form simplified rebuild).
- `system_prompt`: PATCH → `build_patch_prompts`; REGENERATE → `_render_repair_system` (repairer `system.j2` + error-scoped knowledge).
- `L222-228` **LLM CALL** → `repaired_xml = response.content`.
- `AttemptRecord` with `attempt=current_count+1`, `tier=strategy` (1=PATCH, 2=REGENERATE), `errors_in=problems`, `error_sigs=sorted(curr_sigs)`, `stalled`.

**State writes** (`L248-254`):
| key | value | reducer |
|---|---|---|
| `current_xml` | repaired XML | replace |
| `retry_tier` | escalated tier (1-3) | replace |
| `retry_count` | `current_count + 1` | replace |
| `stall_detected` | bool | replace |
| `generation_history` | `[record]` | **append** |

→ then `route_after_repairer` always → `validator` (loop).

---

### 4.8 `critic_node` — [`src/agents/critic.py:153-181`](src/agents/critic.py)
**Skipped** when `critic_mode == "off"`. Runs after a **successful** compile.
- `L155` `mode = critic_mode`, `L156` `interactive`.
- `L159` `issues = _run_ai_check(state)` (`L63-89`):
  - `L65` `_render_prompts` (`L38-60`) — `prompts/critic/system.j2` + `user.j2` with `current_xml`, `components`, `density`, `layout_hint`, `supplied_content`, `theme_element`, `slide_type`, `layout_issues`.
  - `L67-76` **LLM CALL** `.with_structured_output(CriticOutput, method="json_schema")`; on exception → return `[]` (fail-open).
  - `L81-89` map each issue → `{severity, type, description, fix}`.
- `L161-163` count high/medium/low.
- `L165-171` **manual mode**: `_manual_checkpoint(issues, interactive)` (`L104-150`) — non-interactive auto-accepts unless a `high` issue; interactive prompts A/R/E.
- `L173-174` **auto mode**: `passed = not any(severity=="high")`.

**State writes** (`L171` / `L181`): **only** `critic_result` = `{passed: bool, issues: list}`.

→ `route_after_critic`: not passed + budget → `repairer`; else → `slide_router`/`evaluator`.

---

### 4.9 `slide_router_node` — [`src/agents/deck_nodes.py:25-50`](src/agents/deck_nodes.py)
Only reachable when `len(slide_plans) > 1`. Runs after each slide finishes.
- `L26-27` `idx = current_slide_index`, `xml = current_xml`.
- `L32-36` `completed = {slide_index: idx, xml, speaker_notes}`.

**State writes** (`L38-50`) — saves the slide and **resets per-slide state for the next iteration**:
| key | value | reducer |
|---|---|---|
| `completed_slides` | `[completed]` | **append** |
| `current_slide_index` | `idx + 1` | replace |
| `current_xml` | `""` | reset |
| `speaker_notes` | `""` | reset |
| `normalize_result` / `validate_result` / `compile_result` / `critic_result` | `None` | reset |
| `retry_tier` / `retry_count` | `0` | reset |
| `stall_detected` | `False` | reset |

→ `route_after_slide_router`: `idx < total` → `context_builder` (next slide, theme already resolved); else → `deck_assembler`.

---

### 4.10 `deck_assembler_node` — [`src/agents/deck_nodes.py:65-133`](src/agents/deck_nodes.py)
- `L67-68` `sorted_slides = sorted(completed_slides, key=slide_index)`.
- `L70-78` empty → failing `compile_result` (`retryable=False`).
- `L80-85` `theme = _extract_theme(...)` (`L53-56`, regex `<Theme .../>`) from the first slide that has one.
- `L87-93` `_extract_slide_block` (`L59-62`, regex `<Slide>...</Slide>`) from each slide.
- `L95-103` no blocks → failing `compile_result`.
- `L105` `combined_xml = theme + "\n" + "\n".join(slide_blocks)`.
- `L108-122` `compile_xml(combined_xml, output/runs/{run_id}/deck/)` — **final compile of the whole deck**. `CompilerError` → failing result but still writes `current_xml`.

**State writes** (`L129-133`):
| key | value |
|---|---|
| `current_xml` | combined multi-slide XML |
| `compile_result` | final deck compile result |
| `pptx_path` | `compile_result["pptx_path"]` |

---

### 4.11 `evaluator_node` — [`src/agents/evaluator.py:78-161`](src/agents/evaluator.py) — **no LLM**, terminal node
- `L80-83` read `run_id`, `compile_result`, `critic_result`, `generation_history`.
- `L85-87` `passed = compile_result["ok"] and critic_result.get("passed", True)`.
- `L89-90` sum `tokens_in`/`tokens_out` over history.
- `L92-97` `models_used`, `total_cost` via `_compute_cost` (`L31-36` → `get_pricing` from `models.yaml`).
- `L99` `step_summary = _build_step_summary(history)` (`L39-59`) — per-attempt cost rows.
- `L101-114` critic issue counts + `data_provenance` user/sample tally from `slide_plans`.
- `L116-146` assemble `manifest` dict.
- `L148` `_write_manifest(manifest, run_id)` (`L62-75`) → `output/runs/{run_id}/run-manifest.json`.

**State writes** (`L157-161`):
| key | value |
|---|---|
| `evaluation` | full manifest dict |
| `pptx_path` | `compile_result["pptx_path"]` |
| `passed` | final bool |

→ `evaluator → END`. `run()` returns the final state; API emits the `complete` SSE event.

---

## 5. Two canonical end-to-end traces

### 5.1 Single slide, clean compile, critic passes
```
initial_state                  → mode=single, retry_count=0, current_xml=""
route_after_start              → planner            (interactive=False, no components)
planner_node          [LLM]    → mode, core_hook, deck_plan=None, slide_plans=[1]
style_resolver_node            → theme_element, resolved_theme
context_builder_node           → contract
generator_node        [LLM]    → current_xml=<xml>, generation_history=[a0]
validator_node        [node]   → normalize_result, validate_result, compile_result{ok:True,pptx_path}, speaker_notes, layout_issues
route_after_validator          → critic             (ok, critic_mode=auto)
critic_node           [LLM]    → critic_result{passed:True}
route_after_critic             → evaluator          (len(slide_plans)==1)
evaluator_node        [node]   → evaluation, pptx_path, passed=True
END
```

### 5.2 Single slide, compile fails twice then succeeds
```
generator_node        [LLM]    → current_xml=v1, generation_history=[a0(tier0)]
validator_node                 → compile_result{ok:False, retryable:True}
route_after_validator          → repairer           (retry_count 0 < 3)
repairer_node         [LLM]    → current_xml=v2, retry_tier=1, retry_count=1, generation_history+=[a1(PATCH)]
route_after_repairer           → validator
validator_node                 → compile_result{ok:False, retryable:True}   (same errors)
route_after_validator          → repairer           (retry_count 1 < 4)
repairer_node         [LLM]    → is_stalled → retry_tier=2 (REGENERATE), retry_count=2, current_xml=v3, generation_history+=[a2]
route_after_repairer           → validator
validator_node                 → compile_result{ok:True, pptx_path}
route_after_validator          → critic → ... → evaluator
evaluator_node                 → passed = compile_ok and critic_ok
```
Budget exhaustion: once `retry_count == retry_budget (4)`, `route_after_validator`/`route_after_critic` fall through to `evaluator` (single) or `slide_router` (deck) with the last (failing) `compile_result`, so `evaluator` sets `passed=False`.

### 5.3 Deck (planner returns > 1 slide — driven by `deck_min_threshold` target or an explicit multi-slide request)
```
planner_node                   → mode=deck, slide_plans=[N], deck_plan=DeckPlan
style_resolver_node            → resolved_theme            (once)
┌── per slide i = 0..N-1 ──────────────────────────────────
│ context_builder_node         → contract                  (for slide i)
│ generator_node       [LLM]   → current_xml, generation_history+=[...]
│ validator_node               → *_result                  (+ repairer loop as needed)
│ critic_node          [LLM]   → critic_result
│ route_after_critic           → slide_router              (len>1)
│ slide_router_node            → completed_slides+=[slide i], current_slide_index=i+1, RESET per-slide keys
│ route_after_slide_router     → context_builder (i<N)  |  deck_assembler (i==N)
└──────────────────────────────────────────────────────────
deck_assembler_node   [node]   → current_xml=combined, compile_result (final), pptx_path
evaluator_node                 → evaluation, passed
END
```

---

## 6. Where each state key is written (index)

| Key | Written by (file:node) |
|---|---|
| `run_id`, `mode`, `raw_request`, `theme_name`, `test_case`, `supplied_content`, `deck_min_threshold`, `interactive`, `retry_budget` | `state.py::initial_state` |
| `audience_context`, `theme_name`, `deck_min_threshold` | `questionnaire.py::questionnaire_node` |
| `mode`, `core_hook`, `deck_plan`, `slide_plans` | `planner.py::planner_node` |
| `theme_element`, `resolved_theme` | `style_resolver.py::style_resolver_node` |
| `contract` | `context_builder.py::context_builder_node` |
| `current_xml`, `generation_history` | `generator.py::generator_node`, `repairer.py::repairer_node` |
| `normalize_result`, `validate_result`, `compile_result`, `speaker_notes`, `layout_issues` | `validator.py::validator_node` |
| `retry_tier`, `retry_count`, `stall_detected` | `repairer.py::repairer_node` (reset by `slide_router`) |
| `critic_result` | `critic.py::critic_node` |
| `completed_slides`, `current_slide_index` | `deck_nodes.py::slide_router_node` |
| `current_xml`, `compile_result`, `pptx_path` | `deck_nodes.py::deck_assembler_node` |
| `evaluation`, `pptx_path`, `passed` | `evaluator.py::evaluator_node` |

---

## 7. External calls summary

| Node | LLM? | Subprocess? | models.yaml step |
|---|---|---|---|
| questionnaire | no | no | – |
| planner | **yes** (structured `PlannerOutput`) | no | `planner` |
| style_resolver | no | no | – |
| context_builder | no | no | – |
| generator | **yes** (free text) | no | `generator` |
| validator | no | **yes** — `node compile-pom.js` (validate + compile) | – |
| repairer | **yes** (free text) | no | `repairer` |
| critic | **yes** (structured `CriticOutput`) | no | `critic` |
| slide_router | no | no | – |
| deck_assembler | no | **yes** — `node compile-pom.js` (final) | – |
| evaluator | no | no | – |

LLM construction: [`src/utils/llm_client.py:40-69`](src/utils/llm_client.py) `get_llm(step)` — merges `models.yaml` `defaults` + `steps.<step>`, provider `openai` or `azure_openai`.
Compiler bridge: [`src/compiler/compiler_client.py`](src/compiler/compiler_client.py) — always reads `compile-result.json`, never parses stderr.
