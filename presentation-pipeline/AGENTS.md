# AGENTS.md — context for Cursor / any coding agent

Prompt → LangGraph pipeline → LLM writes POM XML → Node.js compiler (`@hirokisakabe/pom` v10.3.0) → `.pptx`.

## Read first
- `ARCHITECTURE.md` — system overview, graph nodes, compiler bridge
- `CODE_FLOW.md` — which function runs when, which `PresentationState` keys change
- `llm.txt` — POM XML reference
- `.cursor/rules/` — project memory carried over from Claude Code (working style is always applied; the rest load when relevant)

## Setup on a new machine
```bash
uv sync                               # or: pip install -e ".[dev]"
cp .env.example .env                  # set OPENAI_API_KEY
npm install --prefix src/node         # POM compiler
npm install --prefix frontend         # Angular UI
```

## Run
- API: `python -m src.api` (uvicorn, port 8000)
- CLI: `python -m src.graph`
- Frontend: `npm run start --prefix frontend` (port 4200, proxies to API)
- Tests: `pytest` (LLM and compiler are mocked — no key or Node needed)
- See a slide without an API key: `python scripts/render_check.py` (needs LibreOffice) — details in `.cursor/rules/offline-render-loop.mdc`

## Next task (ready to implement)
**`docs/nesting-enforcement-plan.md`**: make invalid node nesting (e.g. HStack/Icon inside `<Td>`/`<Li>`) impossible. It has step-by-step, pre-tested code. Implement it in order and verify with its "Verify" section. The permanent rule is `.cursor/rules/pom-nesting-content-model.mdc`.

## Where work stands (2026-09-23)
- Branch `feat/golden-reference-grounding`. Latest commits: fit-grow pass (`dd5c152`), layout archetype system (`d2b75b6`), 14pt minimum font.
- Uncommitted when handed off: edits to `src/knowledge/core/house-style.yaml` and `src/prompts/generator/system.j2`, plus `llm_test/` churn.
- Note: `production-plan.mdc` says "no archetypes" (2026-09-03) but `d2b75b6` later added a layout archetype system — the newer commit reflects the current direction; confirm with the user if it matters.
- Memory rules mentioning `presentation-mvp/` refer to the older sibling MVP folder, not this repo.
