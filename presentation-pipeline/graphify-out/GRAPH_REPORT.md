# Graph Report - presentation-pipeline  (2026-09-17)

## Corpus Check
- 103 files · ~93,822 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1385 nodes · 3070 edges · 93 communities (71 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 155 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c09b40f7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_planner.py
- test_repairer.py
- api.py
- get_llm
- audit_layout
- test_api.py
- test_full_pipeline.py
- test_critic.py
- test_evaluator.py
- api.models.ts
- test_graph.py
- repair_guidance.py
- slide_edit_service.py
- House Style Layout Grammar
- DeckSettingsFormComponent
- initial_state
- PresentationState
- repairer_node
- PlanEditorComponent
- test_context_builder.py
- test_generator.py
- _make_state
- dependencies
- Mixed Executive Slide Test Case
- questionnaire_node
- test_validator.py
- _load_yaml
- screenshot.py
- resolve_theme
- devDependencies
- schematics
- app.component.ts
- build_contract
- GenerationService
- context_builder.py
- compile_graph
- LangGraph Presentation Pipeline
- options
- node/package.json
- test_pipeline_with_hierarchical_planner
- Line-by-Line Code and State Flow
- Family B — Deck Tests
- development
- slide-review.component.ts
- frontend
- frontend/package.json
- theme.constants.ts
- Generator Node (LLM)
- critic.py
- YAML Knowledge Base
- Phase-Based Test System
- build
- OutlineSlide
- Family A — Base Prompt Tests
- resolve_slide_plan
- compile-pom.js
- screenshot-pom.js
- Planner Node (LLM)
- architect
- @angular/compiler-cli
- Golden Fixture Regression Testing
- jasmine-core
- karma
- karma-coverage
- karma-jasmine
- postcss
- conftest.py
- Test Case Phase System
- State Re-Entry Points
- presentation-pipeline
- Pitch Deck Test Case
- Pyramid Strategy Test Case
- Tree Org Chart Test Case
- LLM Test Plan (Planner & Generator)
- SlidePlan
- deck_nodes.py
- settings_to_constraints
- llm_client.py
- ensure_single_theme
- _collect_problems
- validator_node
- build_patch_prompts
- outline_planner_node
- state.py
- needs_regeneration

## God Nodes (most connected - your core abstractions)
1. `initial_state()` - 91 edges
2. `PresentationState` - 60 edges
3. `repairer_node()` - 36 edges
4. `build_graph()` - 34 edges
5. `audit_layout()` - 33 edges
6. `get_llm()` - 30 edges
7. `evaluator_node()` - 28 edges
8. `critic_node()` - 27 edges
9. `_make_state()` - 26 edges
10. `build_contract()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `POM Pipeline Architecture Overview` --semantically_similar_to--> `LangGraph Presentation Pipeline`  [INFERRED] [semantically similar]
  flow.md → ARCHITECTURE.md
- `test_manual_checkpoint_non_interactive_auto_decides()` --calls--> `_manual_checkpoint()`  [EXTRACTED]
  tests/unit/test_critic.py → src/agents/critic.py
- `test_assemble_deck_xml_no_slide_block()` --calls--> `assemble_deck_xml()`  [EXTRACTED]
  tests/unit/test_deck_nodes.py → src/agents/deck_nodes.py
- `test_assemble_deck_xml_strips_contamination()` --calls--> `assemble_deck_xml()`  [EXTRACTED]
  tests/unit/test_deck_nodes.py → src/agents/deck_nodes.py
- `test_pipeline_with_hierarchical_planner()` --uses--> `OutlineSlide`  [INFERRED]
  tests/integration/test_full_pipeline.py → src/agents/outline_planner_schema.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **POM Knowledge Core (Document + Nodes + Attributes + Validation)** — src_knowledge_core_document_document_structure, src_knowledge_core_nodes_node_allowlist, src_knowledge_core_attributes_common_attributes, src_knowledge_core_validation_validation_rules [EXTRACTED 0.95]
- **Deck Mode Multi-Slide Processing Loop** — code_flow_slide_router_node, code_flow_deck_assembler_node, architecture_context_builder_node, architecture_generator_node, architecture_validator_node [EXTRACTED 1.00]
- **Component Knowledge Base Specifications** — architecture_knowledge_base, src_knowledge_components_chart, src_knowledge_components_drawing, src_knowledge_components_flow, src_knowledge_components_list, src_knowledge_components_matrix, src_knowledge_components_process_arrow, src_knowledge_components_pyramid, src_knowledge_components_shape [EXTRACTED 1.00]
- **LLM Test Family A Base-Prompt Cases** — tests_llm_test_plan_test_plan, tests_cases_base_competitor_comparison_test_case, tests_cases_base_org_structure_test_case, tests_cases_base_overstuffed_test_case, tests_cases_base_process_overview_test_case, tests_cases_base_quarterly_metrics_test_case [EXTRACTED 1.00]
- **Core Pipeline Flow (Plan-Generate-Validate-Repair-Evaluate)** — architecture_planner_node, architecture_context_builder_node, architecture_generator_node, architecture_validator_node, architecture_critic_node, architecture_repairer_node, architecture_evaluator_node [EXTRACTED 1.00]
- **** — tests_cases_base_revenue_trend_yaml, tests_cases_base_risks_yaml, tests_cases_base_roadmap_yaml, tests_cases_base_strategy_statement_yaml, tests_cases_base_vague_yaml [EXTRACTED 1.00]
- **** — tests_cases_chart_and_narrative_yaml, tests_cases_chart_and_table_yaml, tests_cases_comparison_matrix_yaml, tests_cases_dark_theme_yaml, tests_cases_financial_report_yaml, tests_cases_flowchart_yaml, tests_cases_inline_formatting_yaml [EXTRACTED 1.00]
- **Slide Layout Composition (House Style + Design Language + Recipes)** — src_knowledge_core_house_style_house_style_grammar, src_knowledge_core_design_language_design_language, src_knowledge_core_recipes_compiled_recipes, src_knowledge_theme_palettes_palette_library [INFERRED 0.85]
- **** — tests_cases_deck_qbr_yaml, tests_cases_deck_qbr_data_yaml, tests_cases_deck_board_update_yaml, tests_cases_deck_sales_enablement_yaml, tests_cases_deck_sales_data_yaml [INFERRED 0.85]

## Communities (93 total, 14 thin omitted)

### Community 0 - "test_planner.py"
Cohesion: 0.24
Nodes (20): PlannerComponent, PlannerSlide, BaseModel, Pydantic models for the per-slide planner's structured LLM output. PlannerSlide…, Plan for a single slide., One component the slide should contain, with its own content data., _planner_slide_to_state(), Convert PlannerSlide Pydantic model to SlidePlan TypedDict. (+12 more)

### Community 1 - "test_repairer.py"
Cohesion: 0.13
Nodes (24): _choose_strategy(), Pick PATCH or REGENERATE for this attempt. The loop is "PATCH, REGENERATE…, build_error_guidance(), is_stalled(), Build targeted repair guidance from errors. Returns formatted string., True if >=threshold of current errors were also in the previous attempt., _choose(), Tests for the repairer agent with mocked LLM responses. (+16 more)

### Community 2 - "api.py"
Cohesion: 0.06
Nodes (73): Enum, FileResponse, get, post, put, _build_event(), _cleanup_old_runs(), ComponentPlanPayload (+65 more)

### Community 3 - "get_llm"
Cohesion: 0.14
Nodes (18): AzureChatOpenAI, ChatOpenAI, check_and_elicit(), elicitor_node(), Any, Elicitor agent — detects vague queries and generates clarifying questions.…, Check if context is sufficient and return clarifying questions if not. Pure LLM…, Graph node: run elicitor and write results to state. If elicitation_answers are… (+10 more)

### Community 4 - "audit_layout"
Cohesion: 0.08
Nodes (46): Element, _compile(), _find_soffice(), main(), Path, Render + audit a folder of POM XML files — the offline quality feedback loop.…, _to_pdf(), audit_layout() (+38 more)

### Community 5 - "test_api.py"
Cohesion: 0.12
Nodes (30): RuntimeError, SlideEditResult, _load_edit_session(), Load edit session from slides.json on disk., _make_critic_llm(), _make_elicitor_llm(), _make_gen_llm(), _make_outline_llm() (+22 more)

### Community 6 - "test_full_pipeline.py"
Cohesion: 0.06
Nodes (55): LogRecord, parametrize, Run the pipeline end-to-end and return the final state., run(), _format_table(), main(), Any, CLI runner — execute test cases and print a summary table. Usage: python -m… (+47 more)

### Community 7 - "test_critic.py"
Cohesion: 0.14
Nodes (42): critic_node(), _format_issues_for_display(), Format critic issues for CLI display., AI quality gate: text check + visual review + optional manual checkpoint., Render system + user prompts for the critic LLM call., _render_prompts(), CriticIssue, BaseModel (+34 more)

### Community 8 - "test_evaluator.py"
Cohesion: 0.13
Nodes (33): _build_step_summary(), _compute_cost(), evaluator_node(), Any, Write run-manifest.json to output/runs/{run_id}/., Score the run and produce a manifest., Compute cost in dollars from token counts and model pricing., Build per-attempt step summary with costs. (+25 more)

### Community 9 - "api.models.ts"
Cohesion: 0.10
Nodes (23): AmountOfText, AppView, ComponentKind, DeckSettingsSchema, EditSessionStatus, ElicitationQuestion, EvaluationSummary, EventType (+15 more)

### Community 10 - "test_graph.py"
Cohesion: 0.11
Nodes (33): Send, Route to planning pipeline, questionnaire, or skip directly to generation., route_after_critic(), route_after_start(), route_after_validator(), _multi_slide_state(), Tests for the LangGraph pipeline with stub agents., Create a state with 2 slide_plans (multi-slide mode). (+25 more)

### Community 11 - "repair_guidance.py"
Cohesion: 0.17
Nodes (19): error_signatures(), _extract_attr_from_error(), _extract_nodes_from_errors(), _extract_tag_from_error(), _find_node_attrs(), _format_attrs(), _load_knowledge_yaml(), Any (+11 more)

### Community 12 - "slide_edit_service.py"
Cohesion: 0.12
Nodes (20): _call_edit_llm(), _call_repair_llm(), edit_slide_xml(), Any, Slide edit service — LLM-powered XML editing with mini repair loop. Takes user…, Apply a user's NL edit to a slide XML, validate, and repair if needed. Returns…, Attempt screenshot, retrying once on failure. Returns path or None. A failure…, Call the LLM to apply the user's edit instruction to the XML. (+12 more)

### Community 13 - "House Style Layout Grammar"
Cohesion: 0.16
Nodes (14): Text Component (POM), Common Box/Layout Attributes, Design Language Patterns, POM Document Structure, Group Rendering Rules, Height Budget System, House Style Layout Grammar, Weight Allocation System (+6 more)

### Community 14 - "DeckSettingsFormComponent"
Cohesion: 0.11
Nodes (11): DeckSettingsFormComponent, Component, PromptFormComponent, Component, SLIDE_COUNT_TO_THRESHOLD, THEME_PALETTES, CriticMode, DeckSettings (+3 more)

### Community 15 - "initial_state"
Cohesion: 0.12
Nodes (33): deck_assembler_node(), _extract_slide_block(), _extract_theme(), Any, Extract the <Theme .../> element from XML., Extract the <Slide>...</Slide> block from XML., Combine all completed slide XMLs into one multi-slide POM document and compile., Save current slide result and advance to next slide index. (+25 more)

### Community 16 - "PresentationState"
Cohesion: 0.12
Nodes (32): Pre-generation questionnaire — collects audience/style/focus context. Presents…, _filter_supplied_content_for_slide(), plan_single_slide(), Any, Slide component planner — plans ONE slide in detail (fan-out target). Called…, Return subset of supplied_content relevant to this slide's key_messages., Plan one slide and return a SlidePlan TypedDict. Can be called directly (e.g.…, Plan all slides sequentially in a single node (SERIALIZE_SLIDES=True path). (+24 more)

### Community 17 - "repairer_node"
Cohesion: 0.19
Nodes (18): _build_repair_context(), _call_llm_and_return(), _get_compile_diags(), _get_pre_issues(), _plan_to_outline_slide(), Any, Repairer agent — two repair strategies. PATCH: feed back failing XML + errors +…, Build error context for the slide component planner during REGENERATE. (+10 more)

### Community 18 - "PlanEditorComponent"
Cohesion: 0.13
Nodes (4): emptyOutlineSlide(), PlanEditorComponent, Component, OutlineSlide

### Community 19 - "test_context_builder.py"
Cohesion: 0.13
Nodes (25): context_builder_node(), _detect_components_from_text(), Select POM nodes needed for the given component kinds., Extract component kinds by scanning text for keywords., LangGraph node: build contract from slide_plans[current_slide_index]., _select_nodes(), Tests for the context builder agent., Icon is a base node — always present regardless of component kinds. (+17 more)

### Community 20 - "test_generator.py"
Cohesion: 0.24
Nodes (19): generator_node(), Any, Render system + user prompts from the contract and slide plan., Generate POM XML via LLM using tiered prompts from the contract., _render_prompts(), _make_state(), patch, Tests for the generator agent with mocked LLM responses. (+11 more)

### Community 21 - "_make_state"
Cohesion: 0.24
Nodes (18): _make_state(), _mock_llm(), _mock_replan(), patch, Set up mocks for the REGENERATE path (plan_single_slide + build_contract)., REGENERATE now calls plan_single_slide + generator LLM instead of repairer LLM., REGENERATE passes repair_context to plan_single_slide with failed component…, test_repairer_escalates_on_stall() (+10 more)

### Community 22 - "dependencies"
Cohesion: 0.11
Nodes (19): @angular/common, @angular/compiler, @angular/core, @angular/forms, @angular/platform-browser, @angular/router, dependencies, @angular/common (+11 more)

### Community 23 - "Mixed Executive Slide Test Case"
Cohesion: 0.12
Nodes (19): Complexity Spectrum Testing, Weight Hierarchy Design Pattern, KPI Row Test Case, Matrix Prioritization Test Case, Maximal Density Test Case, Minimal Statement Test Case, Mixed Chart-Matrix Test Case, Mixed Executive Slide Test Case (+11 more)

### Community 24 - "questionnaire_node"
Cohesion: 0.17
Nodes (16): _ask(), _load_palette_names(), Any, questionnaire_node(), Collect audience context via interactive CLI questions., Return [(name, tone), ...] from palettes.yaml, light first then dark., Print numbered menu and collect user choice. Returns the selected option., Map the slide-count answer to a planner target slide count. (+8 more)

### Community 25 - "test_validator.py"
Cohesion: 0.19
Nodes (18): normalize_xml(), pre_validate(), Any, Normalize raw LLM XML output: strip fences, fix colors, remove br/hr. Returns…, Full normalize + regex-based detection fallback for when parseXml is…, Tests for the validator agent. Unit tests mock the compiler; integration tests…, test_normalize_clean_xml_passes(), test_normalize_fixes_border_accent() (+10 more)

### Community 26 - "_load_yaml"
Cohesion: 0.18
Nodes (18): _load_yaml(), Build per-node attribute lists for only the nodes we selected., Select only notes relevant to the components in this slide. When has_grammar is…, _select_attributes(), _select_notes(), Icon gets its node-specific attributes plus size attrs., shadow and backgroundGradient are in common box attrs for layout/content nodes., test_attributes_chart() (+10 more)

### Community 27 - "screenshot.py"
Cohesion: 0.13
Nodes (28): Backend, _check_screenshot_backend(), _kill_new_powerpnt_processes(), _kill_pids(), _list_powerpnt_pids(), PPTX-to-PNG screenshot service. Primary: Node.js script (screenshot-pom.js)…, Persist a failure record to disk. Log lines get missed; a file doesn't., PIDs of currently running POWERPNT.EXE processes (Windows only). (+20 more)

### Community 28 - "resolve_theme"
Cohesion: 0.20
Nodes (16): _load_yaml(), Any, Style resolver — loosely-coupled theme resolution. Public API:…, Resolve a theme name to a full theme dict. Returns: {name, mode, is_dark,…, LangGraph node: resolve theme and write to state., resolve_theme(), style_resolver_node(), Tests for the style resolver — theme resolution utility and graph node. (+8 more)

### Community 29 - "devDependencies"
Cohesion: 0.12
Nodes (17): @angular/cli, @angular-devkit/build-angular, autoprefixer, devDependencies, @angular/cli, @angular-devkit/build-angular, autoprefixer, karma-chrome-launcher (+9 more)

### Community 30 - "schematics"
Cohesion: 0.12
Nodes (17): schematics, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests, skipTests (+9 more)

### Community 31 - "app.component.ts"
Cohesion: 0.15
Nodes (9): AppComponent, Component, appConfig, ElicitationFormComponent, Component, LayoutComponent, Component, ResultViewComponent (+1 more)

### Community 32 - "build_contract"
Cohesion: 0.23
Nodes (16): build_contract(), _clean_list(), Any, Build a generation contract for one slide from its plan. Args: slide_plan: The…, _estimate_tokens(), _make_plan(), Rough token estimate: ~4 chars per token for English., Maximal-density (6 components): grammar + recipes + shrink checklist. (+8 more)

### Community 33 - "GenerationService"
Cohesion: 0.22
Nodes (3): ProgressEvent, GenerationService, Injectable

### Community 34 - "context_builder.py"
Cohesion: 0.15
Nodes (14): _all_recipes(), _build_node_attributes(), _build_node_hierarchy(), _fmt_house_style_value(), Context builder agent — assembles knowledge base into a generation contract.…, Render a compact parent -> children map for the nodes on this slide. Extracts…, node name -> node-specific attributes from nodes.yaml., Render one house-style.yaml value (str / list / dict) as prompt text. (+6 more)

### Community 35 - "compile_graph"
Cohesion: 0.21
Nodes (14): compile_graph(), Return a compiled, runnable graph., _mock_critic_llm(), patch, End-to-end: the graph runs to completion with mocked LLM + compiler., Return a mock LLM that passes through with_structured_output for the critic., End-to-end: graph runs with pre-provided slide_plans (skips planning phase)., Multi-slide: 2 pre-loaded slides, both compile, deck assembles. (+6 more)

### Community 36 - "LangGraph Presentation Pipeline"
Cohesion: 0.18
Nodes (11): LangGraph Presentation Pipeline, POM XML Markup Language, PresentationState TypedDict, Generate-Validate-Repair Retry Loop, DeckState Extended State Model, Loosely Coupled Editing Architecture, XML as Source of Truth, POM Pipeline Architecture Overview (+3 more)

### Community 37 - "options"
Cohesion: 0.21
Nodes (13): options, assets, browser, index, outputPath, polyfills, scripts, styles (+5 more)

### Community 38 - "node/package.json"
Cohesion: 0.17
Nodes (11): @hirokisakabe/pom, dependencies, @hirokisakabe/pom, description, main, name, private, scripts (+3 more)

### Community 39 - "test_pipeline_with_hierarchical_planner"
Cohesion: 0.20
Nodes (10): ElicitationQuestion, ElicitorOutput, BaseModel, Pydantic models for the elicitor agent's structured output., PlanReviewerOutput, PlanReviewIssue, BaseModel, Pydantic models for the plan reviewer agent's structured output. (+2 more)

### Community 40 - "Line-by-Line Code and State Flow"
Cohesion: 0.22
Nodes (10): Evaluator Node (Mechanical), API Path (FastAPI + SSE), Deck Assembler Node, Questionnaire Node, Slide Router Node (Deck Mode), Line-by-Line Code and State Flow, Style Resolver Node, Deck Mode Critic Accounting Bug (+2 more)

### Community 41 - "Family B — Deck Tests"
Cohesion: 0.22
Nodes (11): Family B — Deck Tests, Supplied Data Test Pattern, Deck Board Update Test Case, Deck Minimal 2-Slide Test Case, Deck Product Launch Data Test Case, Deck Product Launch Test Case, Deck QBR Data Test Case, Deck QBR Test Case (+3 more)

### Community 42 - "development"
Cohesion: 0.18
Nodes (11): serve, development, buildTarget, extractLicenses, optimization, sourceMap, proxyConfig, builder (+3 more)

### Community 43 - "slide-review.component.ts"
Cohesion: 0.18
Nodes (5): EditHistoryEntry, SlideReviewComponent, Component, SlideEditResponse, SlideInfoReview

### Community 44 - "frontend"
Cohesion: 0.20
Nodes (9): prefix, projectType, root, sourceRoot, newProjectRoot, projects, frontend, $schema (+1 more)

### Community 45 - "frontend/package.json"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, ng, start, test, watch (+1 more)

### Community 46 - "theme.constants.ts"
Cohesion: 0.22
Nodes (7): ProgressViewComponent, Component, PIPELINE_PHASES, PipelinePhase, PROGRESS_RANGES, STEP_LABELS, ThemePalette

### Community 47 - "Generator Node (LLM)"
Cohesion: 0.17
Nodes (15): Critic Node (LLM), Generator Node (LLM), Repair Guidance System, Repairer Node (LLM), Stall Detection Mechanism, Tiered Prompt Assembly, Validator Node (Mechanical), XML Normalizer (+7 more)

### Community 48 - "critic.py"
Cohesion: 0.15
Nodes (18): _manual_checkpoint(), Any, Critic agent — AI quality gate after successful compilation. Checks what the…, Present issues to user, ask Accept/Reject/Edit. Returns CriticResult., Take screenshot and run visual critic. Returns (issues, screenshot_path, usage)., Run the AI quality check and return (issues, usage)., _run_ai_check(), _run_visual_review() (+10 more)

### Community 49 - "YAML Knowledge Base"
Cohesion: 0.20
Nodes (12): Node.js Compiler Bridge, YAML Knowledge Base, POM Compiler v10.3.0 (@hirokisakabe/pom), Chart Component Spec, Dark Theme Chart Axis Bug Workaround, Drawing Component Spec (Layer/Line/Arrow/Svg), Flow Component Spec (Flowchart), List Component Spec (Ul/Ol/Li) (+4 more)

### Community 50 - "Phase-Based Test System"
Cohesion: 0.32
Nodes (8): Phase-Based Test System, Chart and Narrative Test Case, Chart and Table Test Case, Comparison Matrix Test Case, Dark Theme Test Case, Financial Report Test Case, Flowchart Test Case, Inline Formatting Test Case

### Community 51 - "build"
Cohesion: 0.25
Nodes (8): build, builder, configurations, defaultConfiguration, production, budgets, buildTarget, outputHashing

### Community 52 - "OutlineSlide"
Cohesion: 0.18
Nodes (17): OutlinePlannerOutput, OutlineSlide, BaseModel, Pydantic models for the outline planner's structured output. The outline…, Rich outline entry for one slide — enough context for slide_component_planner., Complete deck outline from the outline planner., Any, Outline replanner — regenerates a single outline slide from user feedback. Pre-… (+9 more)

### Community 53 - "Family A — Base Prompt Tests"
Cohesion: 0.33
Nodes (6): Family A — Base Prompt Tests, Base Revenue Trend Test Case, Base Risks Test Case, Base Roadmap Test Case, Base Strategy Statement Test Case, Base Vague Test Case

### Community 54 - "resolve_slide_plan"
Cohesion: 0.20
Nodes (18): _merge_content_data(), Any, Slide replanner — decides whether an edit needs a richer SlidePlan. Feedback on…, Keep original values for existing keys; only take new keys from the replan. The…, Convert an existing SlidePlan to a minimal OutlineSlide for re-planning.…, Return (possibly-updated slide_plan, generation contract) for an edit. Degrades…, resolve_slide_plan(), _slide_plan_to_outline_slide() (+10 more)

### Community 55 - "compile-pom.js"
Cohesion: 0.53
Nodes (5): classifyError(), compile(), printSummary(), SLIDE_SIZE, validate()

### Community 56 - "screenshot-pom.js"
Cohesion: 0.60
Nodes (5): findExecutable(), findImageMagick(), findSoffice(), isRealImageMagick(), main()

### Community 57 - "Planner Node (LLM)"
Cohesion: 0.25
Nodes (8): Context Builder Node, Generation Contract, Planner Node (LLM), Layout Variety Enforcement Discarded, 14-Kind Component Vocabulary, Core Hook Narrative Anchor, Data Source Provenance, Slide Type Taxonomy

### Community 58 - "architect"
Cohesion: 0.40
Nodes (5): extract-i18n, test, builder, architect, builder

### Community 81 - "LLM Test Plan (Planner & Generator)"
Cohesion: 0.19
Nodes (13): Pipeline Critical Review, Table Component (POM), Timeline Component (POM), Tree Component (POM), POM Node Allowlist (Phase Registry), POM Validation Rules & Forbidden Tags, Test Case: Architecture Diagram (Phase D), Test Case: Competitor Comparison (+5 more)

### Community 82 - "SlidePlan"
Cohesion: 0.16
Nodes (17): _build_default_plan(), Build a SlidePlan from test_case components, intent detection, or fallback., AttemptRecord, CompileResult, ComponentPlan, SlidePlan, ValidateResult, Tests for PresentationState schema and initial_state factory. (+9 more)

### Community 83 - "deck_nodes.py"
Cohesion: 0.20
Nodes (14): Deck multi-slide nodes — slide_router and deck_assembler. slide_router: saves…, Validator agent — mechanical (no LLM). Runs normalize → parseXml → buildPptx.…, compile_xml(), CompilerError, _parse_result(), Any, Path, Subprocess bridge to compile-pom.js (src/node/). The Node script writes… (+6 more)

### Community 84 - "settings_to_constraints"
Cohesion: 0.17
Nodes (14): compute_provenance(), DeckSettings, Any, BaseModel, DeckSettings — Gamma-style pre-generation form model and constraint mapping.…, Convert DeckSettings to a flat dict of planner constraints., Tag each content_data key as 'user' (from supplied_content) or 'sample'., settings_to_constraints() (+6 more)

### Community 85 - "llm_client.py"
Cohesion: 0.19
Nodes (12): _generate_final_screenshots(), Evaluator agent — mechanical scoring and run manifest. No LLM. Computes: -…, Generate screenshots from the final assembled PPTX. Always (re)renders from…, Write per-slide XML and metadata to slides.json for the edit session., _write_slides_data(), get_pricing(), get_step_config(), _load_models_config() (+4 more)

### Community 86 - "ensure_single_theme"
Cohesion: 0.18
Nodes (12): assemble_deck_xml(), Combine per-slide XML into one normalized multi-slide POM document. Extracts…, ensure_single_theme(), XML normalizer — strip fences, fix colors, remove br/hr, zero spacing. Returns…, Remove every <Theme> element (self-closing, multiline, or paired) from xml., Guarantee exactly one top-level <Theme>. Strips any <Theme> the LLM emitted…, _strip_fences(), strip_theme() (+4 more)

### Community 87 - "_collect_problems"
Cohesion: 0.15
Nodes (13): _collect_problems(), Collect error strings from normalize_result, compile_result, and critic_result., cap_diag_msg(), Strip enum listings and hard-cap length so no diagnostic bloats the prompt., The Lucide icon-name INVALID_VALUE message must not pass through raw., Single-value 'expected: <tag>' in parse errors must NOT be stripped., INVALID_VALUE enum listing must not inflate the problems list., test_cap_diag_msg_preserves_parse_error_context() (+5 more)

### Community 88 - "validator_node"
Cohesion: 0.26
Nodes (12): Any, Run the normalize → validate → compile pipeline on current_xml., validator_node(), patch, test_validator_compile_error_not_retryable(), test_validator_empty_xml(), test_validator_empty_xml_has_layout_issues_key(), test_validator_falls_back_to_pre_validate() (+4 more)

### Community 89 - "build_patch_prompts"
Cohesion: 0.18
Nodes (11): _call_deck_repair_llm(), Fix compile errors in the assembled multi-slide document, preserving all…, build_patch_prompts(), _cap_xml(), Build the (system, user) prompts for a PATCH (in-place fix) repair. Shared by…, Keep head + tail of XML so root setup and closing tags are visible., build_patch_prompts must cap failing_xml before rendering., test_build_patch_prompts() (+3 more)

### Community 90 - "outline_planner_node"
Cohesion: 0.31
Nodes (11): _get_constraints(), outline_planner_node(), Any, Parse DeckSettings dict → constraints dict for prompt injection., Plan the deck outline using an LLM with structured output., _make_structured_llm(), _mock_outline_output(), patch (+3 more)

### Community 91 - "state.py"
Cohesion: 0.39
Nodes (7): DeckPlan, OutlinePlan, OutlineSlide, PlanReview, PresentationState — single source of truth for the LangGraph pipeline. Every…, VisualCriticResult, TypedDict

### Community 92 - "needs_regeneration"
Cohesion: 0.50
Nodes (4): needs_regeneration(), True when the errors are structural — an in-place PATCH is unlikely to fix them…, test_needs_regeneration_local_errors_false(), test_needs_regeneration_structural()

## Knowledge Gaps
- **133 isolated node(s):** `$schema`, `version`, `newProjectRoot`, `projectType`, `skipTests` (+128 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 459 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initial_state()` connect `initial_state` to `test_planner.py`, `test_repairer.py`, `api.py`, `test_full_pipeline.py`, `test_critic.py`, `test_evaluator.py`, `test_graph.py`, `PresentationState`, `test_context_builder.py`, `test_generator.py`, `_make_state`, `questionnaire_node`, `test_validator.py`, `resolve_theme`, `compile_graph`, `test_pipeline_with_hierarchical_planner`, `SlidePlan`, `_collect_problems`, `validator_node`, `outline_planner_node`, `state.py`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `PresentationState` connect `PresentationState` to `get_llm`, `test_full_pipeline.py`, `test_critic.py`, `test_evaluator.py`, `test_graph.py`, `initial_state`, `repairer_node`, `test_context_builder.py`, `test_generator.py`, `questionnaire_node`, `resolve_theme`, `context_builder.py`, `critic.py`, `SlidePlan`, `deck_nodes.py`, `llm_client.py`, `_collect_problems`, `validator_node`, `outline_planner_node`, `state.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `repairer_node()` connect `repairer_node` to `build_contract`, `test_repairer.py`, `get_llm`, `repair_guidance.py`, `PresentationState`, `SlidePlan`, `_make_state`, `_collect_problems`, `build_patch_prompts`, `needs_regeneration`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `PresentationState` (e.g. with `_build_default_plan()` and `context_builder_node()`) actually correct?**
  _`PresentationState` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `repairer_node()` (e.g. with `PresentationState` and `build_graph()`) actually correct?**
  _`repairer_node()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `build_graph()` (e.g. with `context_builder_node()` and `critic_node()`) actually correct?**
  _`build_graph()` has 27 INFERRED edges - model-reasoned connections that need verification._
- **What connects `$schema`, `version`, `newProjectRoot` to the rest of the system?**
  _133 weakly-connected nodes found - possible documentation gaps or missing edges._