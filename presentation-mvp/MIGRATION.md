# Migration checklist

Moving `presentation-mvp/` to the test machine (Windows, Python 3.11.9).

## 1. Copy the project

Copy the whole `presentation-mvp/` folder. **Skip** these (regenerated locally):

- `output/`            – run artifacts
- `node/node_modules/` – reinstalled by npm
- `.env`               – secrets; never copy between machines
- `python/__pycache__/`

**Must travel with the code** (the pipeline fails without them):

| Folder | Why |
|--------|-----|
| `prompts/` | **Required.** `prompt_builder.py` loads `system-selective.txt` / `user-selective.txt` / `repair-user.txt` at runtime. A missing file raises `FileNotFoundError`. |
| `pom-knowledge/` | YAML knowledge base + compile-verified example XML the context selector reads. Includes `theme/palettes.yaml` — the theme library (see *Themes* below). |
| `theme.yaml` (project root, optional) | Picks the deck-wide palette + token overrides. Absent = library default (`corporate-slate`). |
| `tests/cases/` | The 9 single-slide test cases. |
| `tests/decks/` | Deck-mode specs. |
| `node/compile-pom.js`, `node/package.json` | The compiler wrapper. |
| `python/` | All pipeline modules. |
| `requirements.txt`, `.env.example` | deps, config template. |

`llm.txt` (one level **above** `presentation-mvp/`) is the source document the
`pom-knowledge/` YAML base was distilled from — kept for provenance (the
`# Source: llm.txt "..."` comments cite it). The pipeline does not read it.

## 2. Node compiler

```bash
cd node
npm install          # installs @hirokisakabe/pom ^10.3.0
cd ..
```

## 3. Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configure `.env`

```bash
copy .env.example .env
```

Then edit `.env`:

- `OPENAI_API_KEY` – real key (required for live runs)
- `OPENAI_MODEL`   – `gpt-4o` (default) or `gpt-4.1`
- Leave `OPENAI_BASE_URL` **commented out** – an empty value makes the SDK build a hostless URL and fail with "Connection error".
- **Add credits to the OpenAI account.** A valid key with no balance returns HTTP 429 `insufficient_quota` and every live run fails.

## 5. Offline smoke test (no API key needed)

```bash
node node/compile-pom.js pom-knowledge/examples/mixed-slide.xml output/test/mix
python python/generate.py --request "test title slide" --dry-run
python python/deck.py --deck-file tests/decks/quarterly-review.yaml --dry-run
python python/test_retry.py
python python/test_deck.py
python python/test_theme.py
python python/test_prevalidator.py
```

Expected: compile `success`; generate ends `evaluation: PASS`; deck prints
`deck compile: success`; `test_retry` → `all retry cases passed`; `test_deck` →
`deck assembly test passed`; `test_theme` → `theme test passed`;
`test_prevalidator` → `pre-validator contract test passed`.

## 6. First live run

```bash
python python/generate.py --test-case-file tests/cases/title-and-narrative.yaml
```

Artifacts land in `output/runs/<id>/`: `prompt-system.txt`, `prompt-user.txt`,
`slide-ir.json`, `contract.json`, `response-raw.xml`, `cleaned.xml`,
`compile-result.json`, `evaluation.json`, `presentation.pptx`. If a retry
happened: `prompt-user-retry1.txt`, `response-raw-retry1.xml`,
`cleaned-retry1.xml` (and `evaluation.json` `retry` block records
attempts / reason / succeeded). Retry count is set by `RETRY_BUDGET` in `.env`
(default 1); a retry fires on a retryable compile error **or** a blocking
pre-validator issue.

Offline retry-loop check (no API): `python python/test_retry.py`

## 7. Batch the test cases

```bash
for c in tests/cases/*.yaml; do python python/generate.py --test-case-file "$c"; done
```

Each writes an `output/runs/<id>/` with `evaluation.json`.

## 7b. Deck mode

```bash
python python/deck.py --deck-file tests/decks/quarterly-review.yaml
```

Generates each slide through the single-slide pipeline, strips per-slide
`<Theme>`, assembles under one canonical theme, compiles once. Output:
`output/decks/<id>/` with `slide-01/ slide-02/ …`, `deck.xml`, `deck/presentation.pptx`,
`deck-evaluation.json` (per-slide + deck-level pass/fail, `theme_consistent`).

## 8. Send back for tuning

- 3–4 `response-raw.xml` files, especially failing ones
- any `compile-result.json` with a `RENDER_ERROR` / `DIAGNOSTIC`
- any `evaluation.json` with `UNKNOWN_ATTR` pre-validator issues

These feed retry-logic and prompt/pre-validator tuning against real
model output.

## Themes

The `<Theme>` palette is no longer hard-coded. The library lives in
`pom-knowledge/theme/palettes.yaml` — 14 named palettes (10 light, 4 dark), each
a complete token set, all WCAG-contrast-checked at load time by `python/theme.py`.

**Selecting a palette** (first match wins):

1. `--theme <name>` CLI flag on `generate.py` / `deck.py`
2. a test-case / deck-spec `theme:` field (e.g. `theme: warm-editorial`)
3. a project-root `theme.yaml`:
   ```yaml
   theme: emerald-clean          # a palettes.yaml name, or legacy dark/light
   tokens:                       # optional per-token overrides
     accent: "0052CC"
   chartColors: ["0052CC", "36B37E", "FFAB00"]
   ```
4. the library default, `corporate-slate`

`dark` / `light` still work as aliases (`graphite-dark` / `corporate-slate`).

**Fallbacks (warnings, never hard errors):** an unknown palette name → default
palette; token overrides that push body-text contrast below 4.5:1 → overrides
ignored; a broken palette itself below the floor → default palette. All
fallbacks print a `theme: …` line to stderr.

**Charts on dark palettes:** POM v10.3.0 hard-codes chart axis text to black.
Dark palettes carry `chartSurface` / `chartInk`; wrap a chart in
`<VStack backgroundColor="$chartSurface" …>` so its axis labels stay readable.
Light palettes need no wrapper. The context selector adds this instruction to
the prompt automatically when a slide has a chart.

**Tables:** every `<Td>` must set `backgroundColor` + `color` — unstyled cells
render with PowerPoint's white default table style. The knowledge base examples
and the prompt notes now enforce this.

Check the library any time: `python python/test_theme.py`

## Editing prompts later

The wording is in `prompts/*.txt` — edit freely, keep the `{{placeholder}}`
tokens intact. See `prompts/README.md`. No code change needed.
