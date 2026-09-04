# POM XML Generation MVP — End-to-End Flow (for senior engineering review)

> **Status:** Phases 1–7 + 9 code-complete and verified offline. Phase 8 (live
> baseline-vs-selective experiment) is blocked on OpenAI account credits.
> **Compiler:** `@hirokisakabe/pom` v10.3.0, verified empirically (see
> `MEMORY.md` / `pom-mvp-v10-constraints`).

---

## 1. What this system is and why it exists

### Hypothesis under test

> A small, **structured, component-specific POM context** produces more accurate
> POM XML from an LLM than pasting the full ~12k-token `llm.txt` reference doc
> into the prompt.

The previous PoC (2-file script: `user.txt` + `llm.txt` → GPT → XML) failed
consistently because the model **leaks HTML/CSS priors into POM XML**:
`<div>/<br>/<p>`, `style=`/`class=`, `width`/`height` instead of `w`/`h`,
`#FF0000` instead of `FF0000`, `w="0"`. The 12k-token reference doc did not
suppress this — arguably it made it worse.

### What we built

A CLI pipeline that:

1. Turns a natural-language slide request into a **semantic IR** (no XML).
2. **Deterministically** selects only the POM constructs that slide needs from a
   YAML knowledge base → a `GenerationContract` (allowlist + blocklist +
   verified examples + layout pattern).
3. Builds a prompt from the contract (**selective** strategy) or from the full
   `llm.txt` (**baseline** strategy — the control).
4. Calls the LLM, sanitizes the response, compiles it to `.pptx` via a Node
   subprocess, scores the result, and — on failure — feeds diagnostics back for
   one bounded repair attempt.
5. Writes every intermediate artifact to disk so runs are auditable and
   re-scorable without the LLM.

Both strategies are fully implemented; **comparing them is the entire point of
the MVP.** A negative result (selective doesn't help) is still a valid outcome.

---

## 2. Top-level architecture

```
                          ┌─────────────────────────  PYTHON LAYER  ─────────────────────────┐
 request / test-case ───► │  slide_ir → context_selector → prompt_builder → llm_client       │
                          │       │            │                 │              │             │
                          │   SlideIR   GenerationContract   (system,user)   raw XML          │
                          │                                                     │             │
                          │                          pre_validator ◄────────────┘             │
                          │                               │ cleaned XML                       │
                          │                               ▼                                   │
                          │                        compiler_client ──subprocess──► node/      │
                          │                               │                       compile-   │
                          │                        CompileResult ◄──JSON────────── pom.js     │
                          │                               │                                   │
                          │                          evaluator → evaluation.json              │
                          │                               │                                   │
                          │            [fail & budget left]│ repair prompt → loop back to LLM │
                          └───────────────────────────────────────────────────────────────────┘
```

Node layer is a **thin, stateless wrapper**: read XML → `buildPptx(xml, {w:1280,
h:720})` → write `presentation.pptx` + `compile-result.json` → exit 0/1. It
contains no business logic. Python **never parses Node stderr** — only the JSON
result file.

---

## 3. The pipeline, step by step

Entry point: `python/generate.py :: run()`. Deck mode (`python/deck.py`) calls
the same `run()` once per slide.

### Step 0 — Build the SlideIR (`slide_ir.py`)

**Input:** either `--request "..."` (+ optional `--objective`, `--component`,
`--theme`, `--supplied`) or `--test-case-file tests/cases/*.yaml`.

**Output:** `SlideIR` (Pydantic) — a semantic description with **no POM XML**:

```
SlideIR{ objective, request (verbatim), components[SlideComponent{kind, spec}],
         supplied_content{}, theme_hint: dark|light }
```

- Component detection is **regex keyword heuristics**, not an LLM call
  (`_KEYWORD_MAP`: "kpi"/"metric" → `kpi_row`, "chart"/"graph"/"trend" → `chart`,
  "table"/"grid" → `table`, "bullet"/"agenda" → `bullet_list`,
  "narrative"/"summary" → `narrative`).
- A title is assumed unless the request says "no title" / "untitled".
- If only a title is detected, a `narrative` body is added.
- `--component` flags or a test case's explicit `components:` list override the
  heuristic entirely.

**Design rationale:** the step that decides *what goes on the slide* must be
deterministic, or the experiment would be comparing prompt strategies **and** a
nondeterministic planning step at the same time.

Written to: `slide-ir.json`.

### Step 1 — Context selection (`context_selector.py`) — *selective strategy only*

**Input:** `SlideIR`. **Output:** `GenerationContract`.

```
GenerationContract{ allowed_nodes[], allowed_attributes{node:[attr]},
                    forbidden_tags[], forbidden_attributes[],
                    theme_element (verbatim <Theme .../>),
                    layout_pattern (text), examples[] (verbatim XML), notes[] }
```

Knowledge base read from `pom-knowledge/` (all YAML + verified example XML):

| Dir | Contents | Used for |
|---|---|---|
| `core/nodes.yaml` | Phase A allowlist + phase_b/phase_c node metadata + per-node `node_attributes` | node & attribute selection |
| `core/validation.yaml` | `forbidden_tags`, `forbidden_attributes`, `translations` (wrong→right), `semantic_rules` | blocklist + notes |
| `theme/default.yaml` | `theme_element` (dark) / `theme_element_light` | the `<Theme>` element |
| `components/{text,shape,chart,table,list}.yaml` | structure hints + `pitfalls` | notes |
| `layouts/{title-content,kpi-row,two-column,chart-table}.yaml` | structure + rules + verified example | layout pattern |
| `examples/*.xml` | **compile-verified** slides (0 warnings) | reference examples |

Selection logic:

- **Nodes** (`_select_nodes`): always `Slide, Theme, VStack, Text, Shape` +
  inline `B/I/Span/Mark`. Add `HStack, Span` for `kpi_row`;
  `HStack, Chart, ChartSeries, ChartDataPoint` for `chart`;
  `HStack, Table, Col, Tr, Td` for `table`; `Ul, Li` for `bullet_list`.
- **Attributes** (`_node_attributes` + curated box-model subset): stacks get
  `gap/alignItems/justifyContent` + box attrs; inline/table-part/series nodes get
  only their own typed attrs; `Chart/Ul/Ol` get size-only; `Text/Shape` get own +
  box attrs. This is a **curated subset** — enough for Phase A layouts without
  drowning the prompt.
- **Layout** (`_select_layout`): chart+table → `chart-table`; (chart|table)+
  narrative → `two-column`; `kpi_row` → `kpi-row`; else → `title-content`.
- **Examples** (`_select_examples`): picks 1–2 matching verified XML files.
- **Notes**: wrong→right translation table, semantic rules, component pitfalls,
  KPI numeral note.

Written to: `contract.json`.

**Baseline strategy skips this step entirely** — no contract is built.

### Step 2 — Prompt building (`prompt_builder.py`)

Wording lives in **editable templates** under `prompts/` (`prompts/README.md`).
This module only does a literal `{{key}}` → value substitution
(regex `\{\{([a-z_]+)\}\}`). An unresolved `{{token}}` **raises `KeyError`** and
never reaches the model. Empty section → `(none)` (except `{{supplied_content}}`
→ `""`).

| Strategy | System template | User template | Key placeholders |
|---|---|---|---|
| `selective` | `system-selective.txt` | `user-selective.txt` | `forbidden_tags`, `forbidden_attrs`, `allowed_nodes`, `allowed_attributes`, `theme`, `layout_pattern`, `examples`, `notes` / `objective`, `components`, `request`, `supplied_content` |
| `baseline` | `system-baseline.txt` | `user-baseline.txt` | `reference` (full `llm.txt`, ~12.5k tok) / `request` |

The selective system prompt leads with a **FORBIDDEN TAGS / FORBIDDEN ATTRS**
block *before* any reference material — this is the core mitigation for HTML
leakage. Selective prompt sizes: ~1.9k tok (text) to ~4.1k tok (mixed) vs
~12.5k tok baseline.

Written to: `prompt-system.txt`, `prompt-user.txt`.

### Step 3 — Generation (`llm_client.py`)

- OpenAI **Chat Completions only** (`client.chat.completions.create`) — never
  the Responses API.
- Model / temperature (0.2) / max_tokens from `.env` via `config.py`. No key
  ever hardcoded.
- Returns `LLMResponse{ text, tokens{input,output}, model, finish_reason }`.
- `OpenAIError` (auth / quota / rate limit) is wrapped into a clean
  `RuntimeError` — no traceback dump.
- Optional LangSmith tracing when `LANGSMITH_TRACING=true`.

**Test / dry-run seam:** `run()` accepts an `xml_provider(system, user, attempt)
-> (xml, TokenUsage)` callable.
- `--dry-run` → provider returns a canned example XML (`text-slide.xml`), no API
  key needed. Exercises the whole pipeline below this point.
- `test_retry.py` → provider returns canned bad-then-good XML to drive the retry
  loop with no API.
- Otherwise → real `LLMClient().complete()`.

Written to: `response-raw.xml` (and `response-raw-retry{n}.xml`).

### Step 4 — Pre-validation / sanitize (`pre_validator.py`)

Runs on the raw LLM text **before** the compiler. Two jobs:

**(a) Normalize (auto-fix, non-blocking):**
- Strip markdown ``` fences.
- Strip leading `#` from color values (`color="#FFF"` → `color="FFF"`).
- Drop `<br>` / `<hr>` (tree-preserving).
- Drop `gap="0"` / `padding="0"` / `margin="0"`.

**(b) Detect contamination the compiler will NOT catch (blocking):**
- HTML tags (`<div>`, `<p>`, `<span>`, `<ul>`, `<table>`, …) → `HTML_TAG`
- Miscased POM tags (`<text>`, `<table>`) → `MISCASED_TAG`
- Unknown tags → `UNKNOWN_TAG` (distinguishes real-but-out-of-scope POM nodes
  from genuinely unknown)
- Forbidden attributes (`style`, `class`, `className`, `width`, `height`,
  `font-size`, `onclick`, `id`, …) → `HTML_ATTR` (with `<Col width="...">`
  exempted — the one place `width` is legal)
- Zero / negative dimensions on `w/h/fontSize/minW/...` → `ZERO_DIM`

**Why (b) matters — verified v10.3.0 behavior:** POM's XML parser **silently
drops** stray HTML like `</br>` and **tolerates** a leading `#` on colors. So a
slide contaminated with HTML **"compiles successfully"**. If the experiment is to
mean anything, the pre-validator must record these itself. This is why a
"blocking" pre-validation issue is a **retry trigger even when compilation
succeeds**.

`PreValidationResult.blocking` = "any issue that was not auto-fixed".

Written to: `cleaned.xml` (and `cleaned-retry{n}.xml`), later copied to
`final.xml`.

### Step 5 — Compilation (`compiler_client.py` → `node/compile-pom.js`)

- Writes cleaned XML to `<out_dir>/input.xml`.
- `subprocess.run(["node", "compile-pom.js", input, out_dir], cwd=node/)`,
  120s timeout, UTF-8 with `errors="replace"` (Node prints emoji).
- Node: `buildPptx(xml, {w:1280, h:720})` → on success writes
  `presentation.pptx`; always writes `compile-result.json`; exits 0/1.
- Python reads **only** `compile-result.json` → `CompileResult`. Raises
  `CompilerError` **only** for harness failures (node missing, no result file).

**Error classification** (`classifyError` in `compile-pom.js`, mirrored in
`models.py`):

| Shape | `error.name` | Diagnostic type(s) | Stage | Retryable? |
|---|---|---|---|---|
| Unknown tag | `ParseXmlError` (has `.errors[]`) | `UNKNOWN_TAG` | parse | yes |
| Unknown attribute | `ParseXmlError` | `UNKNOWN_ATTRIBUTE` | parse | yes |
| Other parse error | `ParseXmlError` | `PARSE_ERROR` | parse | yes |
| Layout problem (out of bounds, overlap) | `DiagnosticsError` (has `.diagnostics[]`) | `DIAGNOSTIC` | layout | yes |
| Zero/negative/non-finite dim | plain `Error` | `INVALID_VALUE` (msg contains "must be a finite positive") | render | yes |
| Anything else | plain `Error` | `RENDER_ERROR` | render | **no** |

`buildPptx` may also return **non-fatal `diagnostics`** on success — these are
surfaced as `warnings` (e.g. `NODE_OUT_OF_BOUNDS`) and **fail the `passed`
check** even though a `.pptx` was produced.

Written to: `input.xml`, `compile-result.json`, `presentation.pptx` (on success),
`compile-stderr.txt` (manual-debug only).

### Step 6 — Retry loop (`generate.py`, bounded by `RETRY_BUDGET`, default 1)

```
needs_retry = (compile failed AND compile is retryable) OR pre_validation.blocking
```

Per retry attempt:
1. `problems` = non-auto-fixed pre-validation issues + compile diagnostics.
2. `prompt_builder.build_repair(original_user_prompt, problems)` →
   `repair-user.txt` template ({{previous_user}} + {{problems}}). **System
   prompt unchanged.**
3. Re-run the LLM (or canned provider) → pre-validate → compile again.
4. Token usage accumulates across attempts.

`RetryOutcome{ attempted, attempts, succeeded, reason, diagnostics_fed_back }` is
recorded. `succeeded` = final attempt compiled clean **and** not blocking.

Written to: `prompt-user-retry{n}.txt`, `response-raw-retry{n}.xml`,
`cleaned-retry{n}.xml`.

### Step 7 — Evaluation (`evaluator.py`)

Purely mechanical — every field derived from artifacts already on disk, so runs
can be re-scored later without the LLM.

```
EvaluationResult{
  run_id, strategy, test_case, request,
  generation{ xml_returned, markdown_fences_found, html_tags_found[],
              html_attributes_found[], hash_colors_found[], zero_values_found[] },
  pre_validation{ issues_found, auto_fixed, blocking, issues[] },
  compilation{ status, error_type, diagnostics[], warnings[], retryable },
  artifacts{ pptx_created, pptx_path },
  components{ required[], present[], missing[], completion_rate },
  tokens{ input, output, total },
  retry{ attempted, attempts, succeeded, reason, diagnostics_fed_back },
  passed: bool
}
```

**Component presence** is detected from the compiled XML by heuristic regex
(title = first `<Text>` with `fontSize>=28` or bold; narrative = a `<Text>` body
>80 chars; kpi_row = `<HStack>` with ≥2 nested stacks; chart/table/list =
tag presence).

```
passed = compiled.ok
     AND no compile warnings
     AND no HTML tags/attrs survived sanitizing
     AND no required component missing
```

Written to: `evaluation.json`. `final.xml` is the definitive cleaned XML that
produced the final compile result — **downstream tooling (deck assembly) reads
`final.xml`, not `cleaned*.xml`**.

---

## 4. Experiment runner (`experiment.py`) — Phase 5/8

```
python python/experiment.py                                   # all 9 cases × {baseline, selective}
python python/experiment.py --dry-run                         # plumbing only, no API
python python/experiment.py --cases kpi-row,text-only --strategies selective
```

- Runs the full matrix `tests/cases/*.yaml` × strategies. One failing run does
  not kill the matrix (caught, recorded as `error`).
- Per-run stdout captured to `run.log`; artifacts under
  `output/experiments/<ts>/<case>/<strategy>/<run_id>/`.
- `report.json` + `report.md`: per-strategy totals (compiled, passed,
  HTML-contamination count, compile-warning count, retried, retry_recovered,
  token totals, avg component completion) and a per-case table.
- Headline metric: **input-token reduction (selective vs baseline)** and
  **pass-rate / contamination delta**.

The 9 cases: `text-only`, `title-and-narrative`, `kpi-row`, `single-chart`,
`single-table`, `chart-and-narrative`, `table-and-narrative`, `chart-and-table`,
`mixed-executive-slide`.

---

## 5. Deck mode (`deck.py`) — Phase 9

```
python python/deck.py --deck-file tests/decks/quarterly-review.yaml --strategy selective
```

1. `from_spec(yaml)` → `DeckIR{ title, objective, theme_hint, slides[SlideIR] }`.
2. For each slide: `generate.run(..., run_id="slide-NN")` — the **full
   single-slide pipeline**, including per-slide retry. Reads each slide's
   `final.xml`.
3. `assemble_deck()`: **strip every per-slide `<Theme>`**, keep the `<Slide>`
   blocks, **prepend exactly one canonical `<Theme>`** (from `theme/default.yaml`,
   dark or light). Cross-slide theme consistency is enforced *structurally*, not
   by prompting.
4. Compile the whole deck **once** → `deck/presentation.pptx`.
5. `deck-evaluation.json`: per-slide summaries + deck-level pass/fail +
   `theme_consistent` flag (did any slide emit a `<Theme>` ≠ canonical).

```
deck.passed = deck compiled AND no deck warnings AND every slide passed AND theme_consistent
```

---

## 6. Per-run artifact inventory (`output/runs/<run_id>/`)

| File | Written by | Purpose |
|---|---|---|
| `slide-ir.json` | generate | semantic IR |
| `contract.json` | context_selector | selective context (selective only) |
| `prompt-system.txt` / `prompt-user.txt` | prompt_builder | exact prompt sent |
| `response-raw.xml` | llm_client / provider | raw model output |
| `cleaned.xml` | pre_validator | sanitized XML |
| `input.xml` | compiler_client | exact bytes handed to Node |
| `compile-result.json` | compile-pom.js | compile status + diagnostics + warnings |
| `presentation.pptx` | compile-pom.js | the deliverable (on success) |
| `compile-stderr.txt` | compiler_client | human debug only |
| `final.xml` | generate | definitive final XML (deck assembly reads this) |
| `evaluation.json` | evaluator | machine-readable score |
| `prompt-user-retry{n}.txt`, `response-raw-retry{n}.xml`, `cleaned-retry{n}.xml` | retry loop | per-retry artifacts |

---

## 7. Key design decisions — worth scrutiny in review

1. **Deterministic planning (SlideIR + context selection).** No LLM in the "what
   goes on the slide" or "what context to supply" steps — otherwise the
   experiment confounds prompt strategy with a nondeterministic planner.
   *Risk:* regex component detection is brittle; a misclassified request gives
   the wrong contract. Mitigated by explicit `--component` / test-case overrides.

2. **Pre-validator duplicates rules from `core/validation.yaml`.** The rule
   tables in `pre_validator.py` (`FORBIDDEN_TAGS`, `FORBIDDEN_ATTRS`, `POM_TAGS`)
   are hand-maintained copies. *Risk:* drift. There is a comment "keep in sync"
   but no test asserting it.

3. **Pre-validator must catch what the compiler silently accepts.** HTML drop +
   `#`-color tolerance in POM v10.3.0 means "compiles" ≠ "clean". Blocking
   pre-validation is therefore a retry trigger on its own. This is central to
   experiment integrity.

4. **`RENDER_ERROR` is non-retryable.** Only classified error types
   (`UNKNOWN_TAG/ATTRIBUTE`, `PARSE_ERROR`, `INVALID_VALUE`, `DIAGNOSTIC`) get a
   repair attempt. An unclassified render error stops the run.

5. **Retry keeps the system prompt fixed**, appends problems to the *user*
   message. Budget default 1 (diminishing returns assumed beyond 1).

6. **Curated attribute subset**, not the full box model, in the selective
   contract. Deliberate — keeps the prompt small — but means a valid attribute
   the model wants may be absent from the allowlist. The system prompt hedges
   with "plus w, h, grow, padding, margin on any layout/content node."

7. **Node layer is intentionally dumb.** All classification logic is mirrored on
   both sides of the subprocess boundary (`compile-pom.js` + `models.py`).
   *Risk:* two implementations of the same classification.

8. **`passed` is strict**: any compile warning (e.g. `NODE_OUT_OF_BOUNDS`) fails
   the run even with a valid `.pptx`. Reasonable for an accuracy experiment;
   worth confirming that's the intended bar.

9. **Portability.** All paths derived from `config.py` location; `pathlib`
   throughout; `.env` for all secrets/model config; `llm.txt` expected one level
   above the project (`config.LLM_TXT`).

---

## 8. Known gaps / open items

- **Phase 8 not run** — no live baseline-vs-selective numbers yet (OpenAI account
  has no credits: `429 insufficient_quota`). All 8 offline checks in
  `MIGRATION.md §5` pass.
- Component-presence detection in `evaluator.py` is heuristic regex — may
  under/over-count on unusual but valid structures.
- No automated test asserting `pre_validator.py` rule tables match
  `core/validation.yaml`.
- `deck.py` theme handling uses regex (`_THEME_RE`, `_SLIDE_RE`) on XML text, not
  a parser — fine for well-formed model output, fragile on edge cases.
- Retry budget, model, temperature all tunable via `.env`; not swept.

---

## 9. How to review this quickly

```bash
# offline, no API key — exercises everything except the real LLM call
node node/compile-pom.js pom-knowledge/examples/mixed-slide.xml output/test/mix
python python/generate.py --request "test title slide" --dry-run
python python/experiment.py --dry-run
python python/deck.py --deck-file tests/decks/quarterly-review.yaml --dry-run
python python/test_retry.py      # retry loop, canned bad→good XML
python python/test_deck.py       # deck assembly, fake per-slide provider
```

Then read, in order: `python/models.py` (vocabulary) → `python/generate.py::run`
(orchestration) → `python/context_selector.py` (the hypothesis) →
`python/pre_validator.py` (the integrity guard) → `prompts/system-selective.txt`
(what the model actually sees).
